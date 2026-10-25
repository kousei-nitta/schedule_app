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
        connection.execute(
            "INSERT INTO semesters (name, start_date, end_date)"
            " VALUES ('2026年度 後期', '2026-09-21', '2026-12-27')"
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


def test_create_backup_replaces_leftover_partial_file(source_db, tmp_path):
    backup_path = tmp_path / "backups" / "app-copy.db"
    partial_path = tmp_path / "backups" / "app-copy.db.partial"
    partial_path.parent.mkdir()
    partial_path.write_bytes(b"broken")

    create_backup(source_db, backup_path)

    assert table_dump(backup_path) == table_dump(source_db)
    assert not partial_path.exists()


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


def test_copy_and_verify_opens_source_read_only(tmp_path):
    # 元のDBは、読み取り専用（mode=ro）で開く。読み取り専用なら、ない
    # ファイルを開こうとしても、ファイルを作らずに失敗する
    missing_path = tmp_path / "missing.db"

    with pytest.raises(sqlite3.Error):
        backup.copy_and_verify(missing_path, tmp_path / "copy.db")

    assert not missing_path.exists()


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

    removed = remove_old_auto_backups(database_path)

    assert sorted(path.name for path in removed) == [
        "app-20260901-auto.db",
        "app-20260902-auto.db",
    ]
    remaining = sorted(path.name for path in directory.iterdir())
    expected = sorted(set(auto_names[2:]) | set(other_names))
    assert remaining == expected
    assert AUTO_BACKUP_KEEP_COUNT == 30


def test_remove_old_auto_backups_without_directory(tmp_path):
    assert remove_old_auto_backups(tmp_path / "app.db") == []


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
    def failing_removal(database_path):
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
