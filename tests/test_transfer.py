"""本番の毎日のバックアップ（daily-backup）と、移行の写し
（make-transfer-copy。app/transfer.py）。Task 026。

手順は docs/development/deploy.md。実データのDB（instance/app.db）には
触れない（DBは、すべて pytest の一時ディレクトリ）。
"""
import hashlib
import os
import sqlite3
import stat
from contextlib import closing
from datetime import datetime

import pytest

from app import clock
from app.backup import BackupError
from app.config import PROJECT_ROOT
from app.extensions import db
from app import transfer
from app.transfer import make_transfer_copy
from tests.auth_support import TEST_PASSWORD, TEST_USERNAME, post_login

# --- 毎日のバックアップ（本番の定期実行のタスク） ---


def backups_of(app) -> list[str]:
    directory = app_database_path(app).parent / "backups"
    if not directory.is_dir():
        return []
    return sorted(path.name for path in directory.iterdir())


def app_database_path(app):
    from app.database_files import database_file_path

    return database_file_path(app)


def test_daily_backup_in_production(production_app, monkeypatch):
    # UTC の 2026-11-01 15:30 は、日本の 2026-11-02
    utc = datetime(2026, 11, 1, 15, 30)
    monkeypatch.setattr(clock, "utc_now", lambda: utc)
    runner = production_app.test_cli_runner()

    first = runner.invoke(args=["daily-backup"])
    second = runner.invoke(args=["daily-backup"])

    assert first.exit_code == 0, first.output
    assert "バックアップを作りました" in first.output
    assert second.exit_code == 0, second.output
    assert "今日の分は、作成済みです" in second.output
    assert backups_of(production_app) == ["app-20261102-auto.db"]
    # 本番では、持ち主だけが読める（umask 077）
    backup = app_database_path(production_app).parent / "backups"
    mode = stat.S_IMODE((backup / "app-20261102-auto.db").stat().st_mode)
    assert mode == 0o600


def test_daily_backup_keeps_thirty(production_app, monkeypatch):
    backup_directory = app_database_path(production_app).parent / "backups"
    backup_directory.mkdir()
    for day in range(1, 33):
        (backup_directory / f"app-202610{day:02d}-auto.db").write_bytes(b"")
    # 手動のバックアップは、数えず、消さない
    manual = backup_directory / "app-20261001-120000-before-026.db"
    manual.write_bytes(b"")
    utc = datetime(2026, 11, 1, 3, 0)
    monkeypatch.setattr(clock, "utc_now", lambda: utc)

    result = production_app.test_cli_runner().invoke(args=["daily-backup"])

    assert result.exit_code == 0, result.output
    names = backups_of(production_app)
    auto = [name for name in names if name.endswith("-auto.db")]
    assert len(auto) == 30
    assert auto[-1] == "app-20261101-auto.db"
    assert manual.name in names
    assert "消しました" in result.output


def test_daily_backup_fails_with_exit_code_one(production_app):
    # 作れないとき（例：DBのファイルがない）は、終了コード1（定期実行の
    # タスクの記録に残る）。バックアップのファイルは残らない
    with production_app.app_context():
        db.engine.dispose()
    app_database_path(production_app).unlink()

    result = production_app.test_cli_runner().invoke(args=["daily-backup"])

    assert result.exit_code == 1, result.output
    assert "Error:" in result.output
    assert [n for n in backups_of(production_app) if n.endswith(".db")] == []


def test_daily_backup_refuses_other_databases(app):
    # ローカルで、実データのDB（instance/app.db）でないDB（テストのDB）
    result = app.test_cli_runner().invoke(args=["daily-backup"])

    assert result.exit_code == 1
    assert "実データのDBだけ" in result.output


# --- 移行の写し ---

DELETED_TEXT = "deleted-secret-note-text"


def database_with_data(app) -> None:
    """持ち主のログイン・失敗・端末の印・消した行のあるDBにする。"""
    # ほかの接続元からの失敗（成功しても消えない）と、持ち主のログイン
    post_login(
        app.test_client(),
        TEST_USERNAME,
        "wrong password for test",
        "203.0.113.9",
    )
    client = app.test_client()
    post_login(client, TEST_USERNAME, TEST_PASSWORD)
    created = client.post(
        "/api/semesters",
        json={
            "name": "2026年度 後期",
            "start_date": "2026-09-28",
            "end_date": "2027-01-10",
        },
    )
    assert created.status_code == 201


def raw_rows(path, table) -> int:
    with closing(sqlite3.connect(path)) as connection:
        row = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return row[0]


def add_deleted_row_without_secure_delete(path) -> None:
    """secure_delete なしで、行を足して消す（中身が空き領域に残る）。"""
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("PRAGMA secure_delete = OFF")
        connection.execute(
            "INSERT INTO closures (user_id, semester_id, date, name)"
            " VALUES (1, 1, '2026-10-01', ?)",
            (DELETED_TEXT * 50,),
        )
        connection.commit()
        connection.execute("DELETE FROM closures")
        connection.commit()


def file_hash(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def source_database(app):
    database_with_data(app)
    path = app_database_path(app)
    add_deleted_row_without_secure_delete(path)
    from app.extensions import db

    with app.app_context():
        db.engine.dispose()
    return path


def test_transfer_work_files_are_private(
    source_database, tmp_path, monkeypatch, keep_umask
):
    # 途中のファイル（.work・.partial）も、600 で作る（作る間に、ほかの
    # 人に読まれない）。終わったら、umask を元に戻す
    seen = {}
    original_check = transfer.check_transfer_copy

    def check_and_record_modes(partial_path, source_counts):
        work_path = partial_path.with_name(
            partial_path.name.replace(".partial", ".work")
        )
        for name, path in (("work", work_path), ("partial", partial_path)):
            seen[name] = stat.S_IMODE(path.stat().st_mode)
        return original_check(partial_path, source_counts)

    monkeypatch.setattr(
        transfer, "check_transfer_copy", check_and_record_modes
    )
    os.umask(0o022)
    output = tmp_path / "transfer.db"

    make_transfer_copy(source_database, output)

    assert seen == {"work": 0o600, "partial": 0o600}
    current = os.umask(0o022)
    assert current == 0o022


def test_transfer_copy_leaves_out_sessions_failures_and_free_space(
    source_database, tmp_path
):
    assert DELETED_TEXT.encode() in source_database.read_bytes()
    before = file_hash(source_database)
    output = tmp_path / "out" / "transfer.db"
    output.parent.mkdir()

    result = make_transfer_copy(source_database, output)

    # 元のDBは変わらない
    assert file_hash(source_database) == before
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert result["removed"] == {
        "user_sessions": 1,
        "login_failures": 1,
        "trusted_devices": 1,
    }
    for table in ("user_sessions", "login_failures", "trusted_devices"):
        assert raw_rows(output, table) == 0
    assert raw_rows(output, "semesters") == 1
    assert raw_rows(output, "users") == 1
    assert result["version"] == raw_version(source_database)
    with closing(sqlite3.connect(output)) as connection:
        assert connection.execute("PRAGMA freelist_count").fetchone() == (0,)
        assert connection.execute("PRAGMA integrity_check").fetchone() == (
            "ok",
        )
    # 消した行の中身も、セッションのトークンのハッシュも、写しにない
    assert DELETED_TEXT.encode() not in output.read_bytes()
    # 途中のファイルは残らない
    assert sorted(path.name for path in output.parent.iterdir()) == [
        "transfer.db"
    ]


def raw_version(path) -> str:
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0]


def test_transfer_copy_refuses_public_username(source_database, tmp_path):
    with closing(sqlite3.connect(source_database)) as connection:
        connection.execute("UPDATE users SET username = 'owner'")
        connection.commit()
    output = tmp_path / "transfer.db"

    with pytest.raises(BackupError, match="rename-user"):
        make_transfer_copy(source_database, output)

    assert list(tmp_path.glob("transfer.db*")) == []


def test_transfer_copy_refuses_existing_output(source_database, tmp_path):
    output = tmp_path / "transfer.db"
    output.write_bytes(b"keep")

    with pytest.raises(BackupError, match="すでにファイル"):
        make_transfer_copy(source_database, output)

    assert output.read_bytes() == b"keep"


def test_transfer_command_output_must_be_outside_repository(app):
    result = app.test_cli_runner().invoke(
        args=["make-transfer-copy", str(PROJECT_ROOT / "transfer.db")]
    )

    assert result.exit_code == 1
    assert "リポジトリのフォルダの外" in result.output
    assert not (PROJECT_ROOT / "transfer.db").exists()


def test_transfer_command(source_database, app, tmp_path):
    output = tmp_path / "transfer.db"

    result = app.test_cli_runner().invoke(
        args=["make-transfer-copy", str(output)]
    )

    assert result.exit_code == 0, result.output
    assert "移行の写しを作りました" in result.output
    assert "user_sessions 1件" in result.output
    assert output.is_file()


def test_transfer_command_is_refused_in_production(production_app, tmp_path):
    result = production_app.test_cli_runner().invoke(
        args=["make-transfer-copy", str(tmp_path / "transfer.db")]
    )

    assert result.exit_code == 1
    assert "Mac（ローカル）で作ります" in result.output
