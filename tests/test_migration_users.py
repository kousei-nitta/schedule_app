"""利用者とデータの持ち主のmigration（a750d741785a）のテスト。

前の版（42bd53808fa1）のDBにデータを入れてから上げ、件数が変わらず、
すべての行が利用者 owner（パスワードなし）のものになることを確かめる
（docs/development/database.md の「migrationの作成と適用」）。
"""
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from flask_migrate import downgrade, upgrade

from app import create_app
from app.extensions import db

MIGRATIONS = str(Path(__file__).resolve().parents[1] / "migrations")
PREVIOUS_REVISION = "42bd53808fa1"
OWNED_TABLES = ["semesters", "subjects", "closures", "events", "tasks"]

# 前の版のDBに入れる、架空のデータ（実データの形をまねる。消した行の
# あとのように、id が飛んでいる行も入れる）
OLD_ROWS = [
    "INSERT INTO semesters (name, start_date, end_date)"
    " VALUES ('2026年度 後期', '2026-09-21', '2026-12-27')",
    "INSERT INTO semesters (name, start_date, end_date)"
    " VALUES ('2026年度 前期', '2026-04-06', '2026-07-31')",
    "INSERT INTO subjects (semester_id, subject_name, weekday,"
    " start_time, end_time) VALUES (1, '架空の授業', 0,"
    " '09:00:00.000000', '10:00:00.000000')",
    "INSERT INTO closures (semester_id, date, name)"
    " VALUES (1, '2026-11-03', '架空の休講日')",
    "INSERT INTO events (subject_id, category, date, start_time, end_time,"
    " title, is_generated) VALUES (1, 'class', '2026-09-21',"
    " '09:00:00.000000', '10:00:00.000000', '架空の授業', 1)",
    "INSERT INTO events (subject_id, category, date, start_time, end_time,"
    " title, employer, is_generated) VALUES (NULL, 'part_time',"
    " '2026-09-22', '18:00:00.000000', '21:00:00.000000', '架空の仕事',"
    " '架空の派遣会社', 0)",
    "INSERT INTO tasks (subject_id, category, title, due_datetime,"
    " is_completed) VALUES (1, 'assignment', '架空の課題',"
    " '2026-10-01 23:59:00.000000', 0)",
    "INSERT INTO tasks (id, subject_id, category, title, due_datetime,"
    " notes, is_completed) VALUES (7, NULL, 'other', '架空のタスク',"
    " '2026-10-02 12:00:00.000000', '架空のメモ', 1)",
    "INSERT INTO events (id, subject_id, category, date, start_time,"
    " end_time, title, notes, is_generated) VALUES (40, NULL, 'other',"
    " '2026-09-23', '10:00:00.000000', '11:00:00.000000', '架空の予定',"
    " '架空のメモ', 0)",
]


@pytest.fixture
def migration_app(tmp_path):
    database_path = tmp_path / "old.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
        }
    )
    yield app, database_path
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def query(database_path, sql):
    with closing(sqlite3.connect(database_path)) as connection:
        return connection.execute(sql).fetchall()


def rows_without_owner(database_path):
    """5つの表の、user_id のほかのすべての列の値（id の順）。"""
    result = {}
    with closing(sqlite3.connect(database_path)) as connection:
        for table in OWNED_TABLES:
            columns = [
                row[1]
                for row in connection.execute(f"PRAGMA table_info({table})")
                if row[1] != "user_id"
            ]
            result[table] = connection.execute(
                f"SELECT {', '.join(columns)} FROM {table} ORDER BY id"
            ).fetchall()
    return result


def counts(database_path):
    return {
        table: query(database_path, f"SELECT COUNT(*) FROM {table}")[0][0]
        for table in OWNED_TABLES
    }


def test_existing_data_becomes_owner_data(migration_app):
    app, database_path = migration_app
    with app.app_context():
        upgrade(directory=MIGRATIONS, revision=PREVIOUS_REVISION)
        db.engine.dispose()
    with closing(sqlite3.connect(database_path)) as connection:
        for sql in OLD_ROWS:
            connection.execute(sql)
        connection.commit()
    counts_before = counts(database_path)
    rows_before = rows_without_owner(database_path)

    with app.app_context():
        upgrade(directory=MIGRATIONS)
        db.engine.dispose()

    # 表を作り直しても、行の中身と id は、そのまま
    assert rows_without_owner(database_path) == rows_before
    users = query(
        database_path, "SELECT id, username, password_hash FROM users"
    )
    assert users == [(1, "owner", None)]
    assert counts(database_path) == counts_before
    for table in OWNED_TABLES:
        owners = query(database_path, f"SELECT DISTINCT user_id FROM {table}")
        assert owners == [(1,)], table


def test_empty_database_gets_no_user(migration_app):
    app, database_path = migration_app

    with app.app_context():
        upgrade(directory=MIGRATIONS)
        db.engine.dispose()

    assert query(database_path, "SELECT COUNT(*) FROM users") == [(0,)]


def test_user_id_is_required_after_upgrade(migration_app):
    app, database_path = migration_app
    with app.app_context():
        upgrade(directory=MIGRATIONS)
        db.engine.dispose()

    with pytest.raises(sqlite3.IntegrityError, match="NOT NULL"):
        query(
            database_path,
            "INSERT INTO semesters (name, start_date, end_date)"
            " VALUES ('2027年度 前期', '2027-04-01', '2027-07-31')",
        )


def test_downgrade_keeps_data(migration_app):
    app, database_path = migration_app
    with app.app_context():
        upgrade(directory=MIGRATIONS, revision=PREVIOUS_REVISION)
        db.engine.dispose()
    with closing(sqlite3.connect(database_path)) as connection:
        for sql in OLD_ROWS:
            connection.execute(sql)
        connection.commit()
    counts_before = counts(database_path)

    with app.app_context():
        upgrade(directory=MIGRATIONS)
        downgrade(directory=MIGRATIONS, revision=PREVIOUS_REVISION)
        db.engine.dispose()

    assert counts(database_path) == counts_before
    tables = {row[0] for row in query(
        database_path, "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    assert "users" not in tables
