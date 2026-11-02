"""DBのバックアップ（app/backup.py）と、手動のコマンド backup-db の確認。

元のDBは、migrationで作った雛形のDB（conftest.py の template_db）を、
pytestの一時ディレクトリにコピーして使う。バックアップも、一時ディレクトリ
の中（DBと同じフォルダの backups/）にだけできる。
"""
import hashlib
import shutil
import sqlite3
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

import pytest
from flask import Flask

from app import backup
from app import create_app
from app.backup import (
    AUTO_BACKUP_KEEP_COUNT,
    BackupError,
    BackupExistsError,
    auto_backup_path,
    backup_real_database_on_startup,
    create_backup,
    create_daily_backup,
    manual_backup_path,
    remove_old_auto_backups,
)
from app.config import DEFAULT_DATABASE_URI
from app.extensions import db


TODAY = date(2026, 10, 25)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table_dump(path: Path) -> list[str]:
    """DBの中身（スキーマとデータ）を、SQLの文の一覧にする。"""
    with closing(sqlite3.connect(path)) as connection:
        return list(connection.iterdump())


@pytest.fixture
def source_db(template_db: Path, tmp_path: Path) -> Path:
    """バックアップする元のDB（一時ディレクトリの app.db）。学期が1件ある。"""
    database_path = tmp_path / "app.db"
    shutil.copy2(template_db, database_path)
    with closing(sqlite3.connect(database_path)) as connection:
        # データの持ち主の利用者（id 1。パスワードなし）
        connection.execute(
            "INSERT INTO users (username, password_hash, created_at)"
            " VALUES ('test-user', NULL, '2026-10-30 00:00:00')"
        )
        connection.execute(
            "INSERT INTO semesters (user_id, name, start_date, end_date)"
            " VALUES (1, '2026年度 後期', '2026-09-21', '2026-12-27')"
        )
        connection.commit()
    return database_path


def test_create_backup_copies_database(source_db, tmp_path):
    hash_before = file_hash(source_db)
    backup_path = tmp_path / "backups" / "app-copy.db"

    counts = create_backup(source_db, backup_path)

    assert table_dump(backup_path) == table_dump(source_db)
    assert counts["semesters"] == 1
    assert counts["events"] == 0
    assert "alembic_version" in counts
    # 元のDBは変わらない。途中のファイルは残らない
    assert file_hash(source_db) == hash_before
    assert list((tmp_path / "backups").iterdir()) == [backup_path]


def test_create_backup_does_not_overwrite_existing_file(source_db, tmp_path):
    backup_path = tmp_path / "backups" / "app-copy.db"
    backup_path.parent.mkdir()
    backup_path.write_bytes(b"existing")

    with pytest.raises(BackupError, match="すでにあります"):
        create_backup(source_db, backup_path)

    assert backup_path.read_bytes() == b"existing"


def test_create_backup_fails_without_source(tmp_path):
    backup_path = tmp_path / "backups" / "app-copy.db"

    with pytest.raises(BackupError, match="見つかりません"):
        create_backup(tmp_path / "missing.db", backup_path)

    assert not (tmp_path / "missing.db").exists()
    assert not (tmp_path / "backups").exists()


def test_create_backup_leaves_other_process_partial_file(source_db, tmp_path):
    # ほかの処理（別のプロセス番号）の途中のファイルは、消さない
    backup_path = tmp_path / "backups" / "app-copy.db"
    other_partial = tmp_path / "backups" / "app-copy.db.99999999.partial"
    other_partial.parent.mkdir()
    other_partial.write_bytes(b"other process")

    create_backup(source_db, backup_path)

    assert table_dump(backup_path) == table_dump(source_db)
    assert other_partial.read_bytes() == b"other process"
    assert sorted(path.name for path in backup_path.parent.iterdir()) == [
        "app-copy.db",
        "app-copy.db.99999999.partial",
    ]


def test_create_backup_does_not_overwrite_file_made_meanwhile(
    source_db, tmp_path, monkeypatch
):
    # コピーの間に、ほかの処理が同じ名前のバックアップを作った場合も、
    # そのファイルを上書きしない
    backup_path = tmp_path / "backups" / "app-copy.db"
    original_copy = backup.copy_and_verify

    def copy_while_other_process_finishes(database_path, copy_path):
        counts = original_copy(database_path, copy_path)
        backup_path.write_bytes(b"made by other process")
        return counts

    monkeypatch.setattr(
        backup, "copy_and_verify", copy_while_other_process_finishes
    )

    with pytest.raises(BackupExistsError):
        create_backup(source_db, backup_path)

    assert backup_path.read_bytes() == b"made by other process"
    assert list(backup_path.parent.iterdir()) == [backup_path]


def test_create_daily_backup_made_meanwhile_is_not_an_error(
    source_db, tmp_path, monkeypatch
):
    # 同時に起動したほかの処理が、その日の分を先に作った場合は、作成済み
    def other_process_made_it(database_path, backup_path):
        backup_path.parent.mkdir(exist_ok=True)
        backup_path.write_bytes(b"made by other process")
        raise BackupExistsError("同じ名前のバックアップが、すでにあります")

    monkeypatch.setattr(backup, "create_backup", other_process_made_it)

    assert create_daily_backup(source_db, TODAY) is None


def test_create_daily_backup_exists_error_without_file_is_raised(
    source_db, tmp_path, monkeypatch
):
    # 「すでにある」と言われても、ファイルがなければ、作成済みとしない
    def exists_error_without_file(database_path, backup_path):
        raise BackupExistsError("同じ名前のバックアップが、すでにあります")

    monkeypatch.setattr(backup, "create_backup", exists_error_without_file)

    with pytest.raises(BackupExistsError):
        create_daily_backup(source_db, TODAY)


def test_create_backup_when_backup_directory_is_broken_link(
    source_db, tmp_path
):
    # backups が、リンク先のないシンボリックリンク（外部のディスクを
    # 外した、など）のときは、「すでにある」ではなく、失敗にする
    (tmp_path / "backups").symlink_to(tmp_path / "missing-disk")
    backup_path = tmp_path / "backups" / "app-copy.db"

    with pytest.raises(BackupError, match="リンク先がありません") as error:
        create_backup(source_db, backup_path)

    assert not isinstance(error.value, BackupExistsError)


def test_startup_backup_warns_when_backup_directory_is_broken_link(
    source_db, tmp_path, capsys
):
    (tmp_path / "backups").symlink_to(tmp_path / "missing-disk")
    bare_app = make_bare_app(tmp_path, DEFAULT_DATABASE_URI)

    backup_real_database_on_startup(bare_app, TODAY)

    output = capsys.readouterr().out
    assert "警告：自動のバックアップを作れませんでした" in output
    assert "作成済み" not in output


def test_create_backup_removes_partial_companions_on_failure(
    source_db, tmp_path, monkeypatch
):
    # 失敗したとき（ディスクがいっぱい、など）、途中のファイルと、SQLiteが
    # その横に作ったファイル（-journal）を残さない
    def fail_after_writing(database_path, copy_path):
        copy_path.write_bytes(b"half")
        copy_path.with_name(copy_path.name + "-journal").write_bytes(b"j")
        raise sqlite3.OperationalError("database or disk is full")

    monkeypatch.setattr(backup, "copy_and_verify", fail_after_writing)
    backup_path = tmp_path / "backups" / "app-copy.db"

    with pytest.raises(BackupError, match="disk is full"):
        create_backup(source_db, backup_path)

    assert list((tmp_path / "backups").iterdir()) == []


def test_create_backup_when_backup_directory_is_a_file(source_db, tmp_path):
    (tmp_path / "backups").write_bytes(b"not a folder")
    backup_path = tmp_path / "backups" / "app-copy.db"

    with pytest.raises(BackupError, match="フォルダでないもの"):
        create_backup(source_db, backup_path)

    assert (tmp_path / "backups").read_bytes() == b"not a folder"


# 書きかけの記録（-journal）の見出しの先頭の8バイト（印）と、続く4バイト
# （記録の数）。SQLiteは、DBのファイルを書き換える前に（commit のときと、
# 大きな書き込みでキャッシュが溢れたとき）、見出しにこの印を書く。印の
# ある記録が「書きかけ」（hot journal）で、DBを開くときに取り消しが要る。
# 印が 0 の記録は、書きかけではない（DBのファイルは、まだ書き換えられて
# いない）。記録の数の 0xFFFFFFFF は「ファイルの終わりまで」で、同期しない
# モード（synchronous = OFF）で SQLite が書くのと同じ見出しになる。形は、
# SQLiteの資料「Database File Format」の「The Rollback Journal」のとおり
JOURNAL_MAGIC = bytes.fromhex("d9d505f920a163d7")
RECORDS_TO_END = (0xFFFFFFFF).to_bytes(4, "big")


def make_hot_journal(database_path: Path, target_path: Path) -> None:
    """書きかけの記録（hot journal）が残ったDBを、target_path に作る。

    アプリが、DBのファイルを書き換える直前（記録に印を書いたあと）で
    止まった状態と同じ。書き込みの途中の、DBと -journal を写し、写した
    記録の見出しに、印を書く。元のDBの書き込みは取り消す。

    KomaのMac（SQLite 3.54.0）では、cache_size を小さくしても、commit の
    前にDBを書き換えず、印は 0 のままだった（理由は確かめていない）。
    どの環境でも同じ状態を作るため、印は、ここで書く。
    """
    journal_path = database_path.with_name(database_path.name + "-journal")
    target_journal = target_path.with_name(target_path.name + "-journal")
    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        # 今ある行を変えて、記録に、元のページの中身を控えさせる
        connection.execute("UPDATE semesters SET name = name || '+'")
        connection.execute(
            "INSERT INTO closures (user_id, semester_id, date, name)"
            " VALUES (1, 1, '2026-10-01', '書きかけの休講日')"
        )
        shutil.copy2(database_path, target_path)
        shutil.copy2(journal_path, target_journal)
        connection.rollback()

    journal = bytearray(target_journal.read_bytes())
    journal[0:12] = JOURNAL_MAGIC + RECORDS_TO_END
    target_journal.write_bytes(bytes(journal))


def test_journal_header_matches_what_sqlite_writes(source_db):
    # 上の準備で書く見出しが、この環境の SQLite が自分で書く見出し
    # （同期しないモード）と同じこと（Macの SQLite でも、ここで確かめる）
    journal_path = source_db.with_name(source_db.name + "-journal")
    with closing(sqlite3.connect(source_db)) as connection:
        connection.execute("PRAGMA synchronous = OFF")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("UPDATE semesters SET name = name || '+'")
        header = journal_path.read_bytes()[:12]
        connection.rollback()

    assert header == JOURNAL_MAGIC + RECORDS_TO_END


def test_hot_journal_helper_makes_a_real_hot_journal(source_db, tmp_path):
    # 上の準備が、本物の書きかけの記録を作ること（テストの空振りを防ぐ）：
    # 読み書きで開くと、SQLiteが書きかけとして扱い、記録を当てて消す
    # （書きかけでない記録は、読むだけでは消えない）。写したDBは、
    # commit 済みの中身のまま
    hot_path = tmp_path / "hot" / "app.db"
    hot_path.parent.mkdir()
    make_hot_journal(source_db, hot_path)
    hot_journal = hot_path.with_name("app.db-journal")

    with closing(sqlite3.connect(hot_path)) as connection:
        names = connection.execute("SELECT name FROM semesters").fetchall()
        check = connection.execute("PRAGMA integrity_check").fetchone()[0]

    assert not hot_journal.exists()
    assert names == [("2026年度 後期",)]
    assert check == "ok"


def test_backup_fails_with_hot_journal_and_changes_nothing(
    source_db, tmp_path
):
    hot_path = tmp_path / "hot" / "app.db"
    hot_path.parent.mkdir()
    make_hot_journal(source_db, hot_path)
    hot_journal = hot_path.with_name("app.db-journal")
    hashes_before = (file_hash(hot_path), file_hash(hot_journal))

    with pytest.raises(
        BackupError, match="書きかけの記録（app.db-journal）"
    ) as error:
        create_backup(hot_path, tmp_path / "hot" / "backups" / "copy.db")

    # 失敗の理由が、書きかけの記録を取り消せないことであること
    sqlite_error = error.value.__cause__
    assert sqlite_error.sqlite_errorname == "SQLITE_READONLY_ROLLBACK"
    # バックアップから戻す作業の途中なら、画面を開かずに止めるように、と添える
    assert "画面を開かないでください" in str(error.value)
    assert "Ctrl+C" in str(error.value)

    # 読み取り専用で開くため、DBも -journal も変えない
    assert (file_hash(hot_path), file_hash(hot_journal)) == hashes_before
    assert list((tmp_path / "hot" / "backups").iterdir()) == []


def test_no_hot_journal_hint_for_other_failures(
    source_db, tmp_path, monkeypatch
):
    # -journal があっても（書き込み中のアプリ、取り消しの要らない古い記録）、
    # 別の理由で失敗したときは、書きかけの記録の案内をしない
    source_db.with_name("app.db-journal").write_bytes(b"\0" * 512)

    def fail_with_disk_full(database_path, copy_path):
        raise sqlite3.OperationalError("database or disk is full")

    monkeypatch.setattr(backup, "copy_and_verify", fail_with_disk_full)

    with pytest.raises(BackupError, match="disk is full") as error:
        create_backup(source_db, tmp_path / "backups" / "copy.db")

    assert "書きかけの記録" not in str(error.value)


def test_backup_copies_only_committed_rows_while_app_writes(
    source_db, tmp_path
):
    # アプリが書き込みの途中（commit の前）でも、バックアップは待たずに、
    # commit 済みの内容だけを写す
    with closing(sqlite3.connect(source_db)) as writer:
        writer.execute("BEGIN IMMEDIATE")
        writer.execute(
            "INSERT INTO semesters (user_id, name, start_date, end_date)"
            " VALUES (1, '2027年度 前期', '2027-04-01', '2027-07-31')"
        )
        backup_path = tmp_path / "backups" / "app-copy.db"

        counts = create_backup(source_db, backup_path)

        writer.rollback()
    assert counts["semesters"] == 1
    assert table_dump(backup_path) == table_dump(source_db)


def test_create_backup_removes_copy_when_counts_differ(
    source_db, tmp_path, monkeypatch
):
    # 2回目に数えた件数（コピーの件数）だけ、違う値を返すようにする
    calls = []

    def fake_counts(connection):
        calls.append(connection)
        return {"semesters": len(calls)}

    monkeypatch.setattr(backup, "table_row_counts", fake_counts)
    backup_path = tmp_path / "backups" / "app-copy.db"

    with pytest.raises(BackupError, match="件数が、元のDBと違います"):
        create_backup(source_db, backup_path)

    assert list((tmp_path / "backups").iterdir()) == []


def test_create_backup_removes_copy_when_check_fails(
    source_db, tmp_path, monkeypatch
):
    monkeypatch.setattr(
        backup, "integrity_check_result", lambda connection: "broken page"
    )
    backup_path = tmp_path / "backups" / "app-copy.db"

    with pytest.raises(BackupError, match="broken page"):
        create_backup(source_db, backup_path)

    assert list((tmp_path / "backups").iterdir()) == []


def test_copy_and_verify_does_not_create_missing_source(tmp_path):
    # 元のDBがないとき、ファイルを作らずに失敗する（mode=ro の効果の1つ）
    missing_path = tmp_path / "missing.db"

    with pytest.raises(sqlite3.Error):
        backup.copy_and_verify(missing_path, tmp_path / "copy.db")

    assert not missing_path.exists()


def test_copy_and_verify_source_connection_cannot_write(
    source_db, tmp_path, monkeypatch
):
    # 元のDBの接続（最初に件数を数える接続）では、書き込めないこと
    # （読み取り専用 mode=ro で開いていること）を、書き込みを試して確かめる
    original_counts = backup.table_row_counts
    write_errors = []

    def counts_with_write_probe(connection):
        if not write_errors:
            with pytest.raises(sqlite3.OperationalError) as error:
                connection.execute("PRAGMA user_version = 7")
            write_errors.append(str(error.value))
        return original_counts(connection)

    monkeypatch.setattr(backup, "table_row_counts", counts_with_write_probe)

    backup.copy_and_verify(source_db, tmp_path / "copy.db")

    assert "readonly" in write_errors[0]


def test_backup_paths(tmp_path):
    database_path = tmp_path / "app.db"

    assert auto_backup_path(database_path, TODAY) == (
        tmp_path / "backups" / "app-20261025-auto.db"
    )
    now = datetime(2026, 10, 25, 15, 30, 12)
    assert manual_backup_path(database_path, now, "before-024") == (
        tmp_path / "backups" / "app-20261025-153012-before-024.db"
    )
    assert manual_backup_path(database_path, now, "manual").name == (
        "app-20261025-153012-manual.db"
    )


@pytest.mark.parametrize(
    "label", ["", "前", "before 024", "a/b", "../x", "a" * 41]
)
def test_manual_backup_path_rejects_bad_label(tmp_path, label):
    now = datetime(2026, 10, 25, 15, 30, 12)

    with pytest.raises(BackupError, match="ラベル"):
        manual_backup_path(tmp_path / "app.db", now, label)


def test_create_daily_backup_once_per_day(source_db, tmp_path):
    first_path = create_daily_backup(source_db, TODAY)

    assert first_path == tmp_path / "backups" / "app-20261025-auto.db"
    assert table_dump(first_path) == table_dump(source_db)
    hash_first = file_hash(first_path)

    # 同じ日の2回目は、作らない（作成済みのファイルも変えない）
    assert create_daily_backup(source_db, TODAY) is None
    assert file_hash(first_path) == hash_first

    # 次の日は、新しく作る
    next_path = create_daily_backup(source_db, date(2026, 10, 26))
    assert next_path == tmp_path / "backups" / "app-20261026-auto.db"
    assert next_path.exists()


def test_remove_old_auto_backups_keeps_newest(tmp_path):
    database_path = tmp_path / "app.db"
    directory = tmp_path / "backups"
    directory.mkdir()
    auto_names = [
        f"app-202609{day:02d}-auto.db" for day in range(1, 31)
    ] + ["app-20261001-auto.db", "app-20261002-auto.db"]
    for name in auto_names:
        (directory / name).write_bytes(b"auto")
    # 自動のもの以外は、消さない
    other_names = [
        "app-20250101-120000-manual.db",
        "app-20250101-120000-before-009.db",
        "demo-20250101-auto.db",
        "app-20250101-auto.db.partial",
        "app-2025010-auto.db",
        "app-20250101-auto.db.bak",
    ]
    for name in other_names:
        (directory / name).write_bytes(b"other")

    removed = remove_old_auto_backups(database_path, TODAY)

    assert sorted(path.name for path in removed) == [
        "app-20260901-auto.db",
        "app-20260902-auto.db",
    ]
    remaining = sorted(path.name for path in directory.iterdir())
    expected = sorted(set(auto_names[2:]) | set(other_names))
    assert remaining == expected
    assert AUTO_BACKUP_KEEP_COUNT == 30


def test_remove_old_auto_backups_ignores_future_dates(tmp_path):
    # 日付が今日より後の名前のファイルは、数えず、消さない（今日作った
    # ものが、古いものとして消えないように）
    database_path = tmp_path / "app.db"
    directory = tmp_path / "backups"
    directory.mkdir()
    future_names = [f"app-202711{day:02d}-auto.db" for day in range(1, 31)]
    for name in future_names + ["app-20261025-auto.db"]:
        (directory / name).write_bytes(b"auto")

    removed = remove_old_auto_backups(database_path, TODAY)

    assert removed == []
    assert (directory / "app-20261025-auto.db").exists()
    assert len(list(directory.iterdir())) == 31


def test_remove_old_auto_backups_without_directory(tmp_path):
    assert remove_old_auto_backups(tmp_path / "app.db", TODAY) == []


def make_bare_app(instance_path: Path, uri: str) -> Flask:
    """instance/ を一時ディレクトリにした、空のFlaskアプリを作る。

    実データのDBは、instance/ の app.db（ここでは一時ディレクトリの中）。
    """
    bare_app = Flask(__name__, instance_path=str(instance_path))
    bare_app.config["SQLALCHEMY_DATABASE_URI"] = uri
    return bare_app


def test_startup_backup_for_real_database(source_db, tmp_path, capsys):
    bare_app = make_bare_app(tmp_path, DEFAULT_DATABASE_URI)

    backup_real_database_on_startup(bare_app, TODAY)

    backup_path = tmp_path / "backups" / "app-20261025-auto.db"
    assert table_dump(backup_path) == table_dump(source_db)
    output = capsys.readouterr().out
    assert f"自動のバックアップを作りました：{backup_path}" in output

    backup_real_database_on_startup(bare_app, TODAY)

    assert "今日の分は、作成済みです" in capsys.readouterr().out


def test_startup_backup_removes_old_auto_backups(source_db, tmp_path, capsys):
    directory = tmp_path / "backups"
    directory.mkdir()
    for day in range(1, 31):
        (directory / f"app-202609{day:02d}-auto.db").write_bytes(b"auto")
    bare_app = make_bare_app(tmp_path, DEFAULT_DATABASE_URI)

    backup_real_database_on_startup(bare_app, TODAY)

    names = sorted(path.name for path in directory.iterdir())
    assert len(names) == 30
    assert "app-20260901-auto.db" not in names
    assert "app-20261025-auto.db" in names
    assert "古い自動のバックアップを1個消しました" in capsys.readouterr().out


def test_startup_backup_skips_other_database(tmp_path, capsys):
    other_path = tmp_path / "demo.db"
    other_path.write_bytes(b"")
    bare_app = make_bare_app(tmp_path, f"sqlite:///{other_path}")

    backup_real_database_on_startup(bare_app, TODAY)

    assert not (tmp_path / "backups").exists()
    assert "実データのDBではない" in capsys.readouterr().out


def test_startup_backup_skips_non_file_database(tmp_path, capsys):
    bare_app = make_bare_app(
        tmp_path, "postgresql://user:secret@localhost/schedule"
    )

    backup_real_database_on_startup(bare_app, TODAY)

    output = capsys.readouterr().out
    assert "SQLiteのファイルではないため、作りません" in output
    assert not (tmp_path / "backups").exists()


def test_startup_backup_skips_missing_real_database(tmp_path, capsys):
    bare_app = make_bare_app(tmp_path, DEFAULT_DATABASE_URI)

    backup_real_database_on_startup(bare_app, TODAY)

    assert not (tmp_path / "app.db").exists()
    assert not (tmp_path / "backups").exists()
    assert "まだない" in capsys.readouterr().out


def test_startup_backup_failure_does_not_raise(
    source_db, tmp_path, capsys, monkeypatch
):
    def failing_backup(database_path, today):
        raise BackupError("ディスクがいっぱいです")

    monkeypatch.setattr(backup, "create_daily_backup", failing_backup)
    bare_app = make_bare_app(tmp_path, DEFAULT_DATABASE_URI)

    backup_real_database_on_startup(bare_app, TODAY)

    output = capsys.readouterr().out
    assert "警告：自動のバックアップを作れませんでした" in output
    assert "ディスクがいっぱいです" in output


def test_startup_backup_unexpected_error_does_not_raise(
    source_db, tmp_path, capsys, monkeypatch
):
    # BackupError でない、思いがけない例外でも、起動は続ける
    def failing_backup(database_path, today):
        raise RuntimeError("思いがけない失敗")

    monkeypatch.setattr(backup, "create_daily_backup", failing_backup)
    bare_app = make_bare_app(tmp_path, DEFAULT_DATABASE_URI)

    backup_real_database_on_startup(bare_app, TODAY)

    output = capsys.readouterr().out
    assert "警告：自動のバックアップを作れませんでした" in output
    assert "思いがけない失敗" in output


def test_startup_backup_reports_failed_removal_separately(
    source_db, tmp_path, capsys, monkeypatch
):
    def failing_removal(database_path, today):
        raise OSError("消せません")

    monkeypatch.setattr(backup, "remove_old_auto_backups", failing_removal)
    bare_app = make_bare_app(tmp_path, DEFAULT_DATABASE_URI)

    backup_real_database_on_startup(bare_app, TODAY)

    # 今日のバックアップは作れていて、そのことと、消せなかったことを表示する
    assert (tmp_path / "backups" / "app-20261025-auto.db").exists()
    output = capsys.readouterr().out
    assert "自動のバックアップを作りました" in output
    assert "警告：古い自動のバックアップを消せませんでした" in output
    assert "作れませんでした" not in output


def test_backup_db_command(app, tmp_path):
    # app は conftest.py のfixture（DBは一時ディレクトリの test.db）
    runner = app.test_cli_runner()

    result = runner.invoke(args=["backup-db", "--label", "before-024"])

    assert result.exit_code == 0, result.output
    backups = list((tmp_path / "backups").iterdir())
    assert len(backups) == 1
    assert backups[0].name.startswith("test-")
    assert backups[0].name.endswith("-before-024.db")
    assert f"バックアップを作りました：{backups[0]}" in result.output
    assert "semesters 0件" in result.output
    assert table_dump(backups[0]) == table_dump(tmp_path / "test.db")


def test_backup_db_command_default_label(app, tmp_path):
    result = app.test_cli_runner().invoke(args=["backup-db"])

    assert result.exit_code == 0, result.output
    backups = list((tmp_path / "backups").iterdir())
    assert backups[0].name.endswith("-manual.db")


def test_backup_db_command_rejects_bad_label(app, tmp_path):
    result = app.test_cli_runner().invoke(args=["backup-db", "--label", "前"])

    assert result.exit_code == 1
    assert "ラベル" in result.output
    assert not (tmp_path / "backups").exists()


def test_backup_db_command_rejects_memory_database():
    memory_app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"}
    )

    result = memory_app.test_cli_runner().invoke(args=["backup-db"])

    assert result.exit_code == 1
    assert "SQLiteのファイルのDBだけ" in result.output
    with memory_app.app_context():
        db.engine.dispose()
