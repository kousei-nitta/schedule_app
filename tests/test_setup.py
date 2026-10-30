import hashlib
from datetime import date
from pathlib import Path

import pytest
from alembic import command
from flask import current_app
from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db
from app.models.semester import Semester
from tests.auth_support import TEST_USER_ID


def database_path_from_app(app) -> Path:
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    return Path(uri.removeprefix("sqlite:///"))


def test_database_is_in_pytest_temporary_directory(app, tmp_path):
    database_path = database_path_from_app(app).resolve()
    project_root = Path(__file__).resolve().parents[1]
    assert database_path != (project_root / "instance" / "app.db").resolve()
    assert database_path.is_relative_to(tmp_path.resolve())


def test_migrations_create_all_expected_tables(app):
    with app.app_context():
        tables = set(inspect(db.engine).get_table_names())

    assert {
        "users",
        "user_sessions",
        "login_failures",
        "semesters",
        "subjects",
        "events",
        "tasks",
        "closures",
        "alembic_version",
    } <= tables


def test_models_and_migrations_have_no_differences(app):
    # モデルの定義と、migrationで作ったテスト用DBを比べる（`flask db check` と
    # 同じ確認）。モデルを変えたのに、migrationを作り忘れていると、
    # 差の内容（足りないテーブル・列など）を出して失敗する。
    migrations_directory = Path(__file__).resolve().parents[1] / "migrations"
    with app.app_context():
        migrate = current_app.extensions["migrate"].migrate
        command.check(migrate.get_config(str(migrations_directory)))


def table_design(app, table_name: str):
    """表の列（名前 → 型・NULL可否）・主キー・外部キー・一意の制約。"""
    with app.app_context():
        inspector = inspect(db.engine)
        columns = {
            column["name"]: (str(column["type"]), column["nullable"])
            for column in inspector.get_columns(table_name)
        }
        primary_key = inspector.get_pk_constraint(table_name)
        foreign_keys = sorted(
            (
                foreign_key["name"],
                foreign_key["constrained_columns"],
                foreign_key["referred_table"],
                foreign_key["referred_columns"],
            )
            for foreign_key in inspector.get_foreign_keys(table_name)
        )
        unique_constraints = [
            (constraint["name"], constraint["column_names"])
            for constraint in inspector.get_unique_constraints(table_name)
        ]
    return columns, primary_key, foreign_keys, unique_constraints


def user_id_foreign_key(table_name: str):
    return (f"fk_{table_name}_user_id_users", ["user_id"], "users", ["id"])


def test_closures_table_matches_design(app):
    columns, primary_key, foreign_keys, unique = table_design(app, "closures")

    assert columns == {
        "id": ("INTEGER", False),
        "user_id": ("INTEGER", False),
        "semester_id": ("INTEGER", False),
        "date": ("DATE", False),
        "name": ("VARCHAR(100)", True),
    }
    assert primary_key == {
        "constrained_columns": ["id"],
        "name": "pk_closures",
    }
    assert foreign_keys == [
        (
            "fk_closures_semester_id_semesters",
            ["semester_id"],
            "semesters",
            ["id"],
        ),
        user_id_foreign_key("closures"),
    ]
    assert unique == []


def test_users_table_matches_design(app):
    columns, primary_key, foreign_keys, unique = table_design(app, "users")

    assert columns == {
        "id": ("INTEGER", False),
        "username": ("VARCHAR(32)", False),
        "password_hash": ("VARCHAR(255)", True),
        "created_at": ("DATETIME", False),
    }
    assert primary_key == {"constrained_columns": ["id"], "name": "pk_users"}
    assert foreign_keys == []
    assert unique == [("uq_users_username", ["username"])]


def test_user_sessions_table_matches_design(app):
    columns, primary_key, foreign_keys, unique = table_design(
        app, "user_sessions"
    )

    assert columns == {
        "id": ("INTEGER", False),
        "user_id": ("INTEGER", False),
        "token_digest": ("VARCHAR(64)", False),
        "created_at": ("DATETIME", False),
        "last_used_at": ("DATETIME", False),
    }
    assert primary_key == {
        "constrained_columns": ["id"],
        "name": "pk_user_sessions",
    }
    assert foreign_keys == [user_id_foreign_key("user_sessions")]
    assert unique == []


def test_login_failures_table_matches_design(app):
    columns, primary_key, foreign_keys, unique = table_design(
        app, "login_failures"
    )

    assert columns == {
        "id": ("INTEGER", False),
        "login_id_digest": ("VARCHAR(64)", False),
        "client_digest": ("VARCHAR(64)", False),
        "failed_at": ("DATETIME", False),
    }
    assert primary_key == {
        "constrained_columns": ["id"],
        "name": "pk_login_failures",
    }
    assert foreign_keys == []
    assert unique == []


@pytest.mark.parametrize(
    "table_name", ["semesters", "subjects", "events", "tasks", "closures"]
)
def test_data_tables_have_owner(app, table_name):
    # 5つの表の、データの持ち主（利用者）の列と、外部キー
    columns, _, foreign_keys, _ = table_design(app, table_name)

    assert columns["user_id"] == ("INTEGER", False)
    assert user_id_foreign_key(table_name) in foreign_keys


def test_test_database_is_a_private_copy(app, template_db, tmp_path):
    # 雛形や共有DBを直接使う誤りを検出し、各テストが空のコピーから
    # 始まることを確認する。
    app_database_path = database_path_from_app(app).resolve()
    assert app_database_path.parent == tmp_path.resolve()
    assert app_database_path != template_db.resolve()
    template_hash_before = hashlib.sha256(template_db.read_bytes()).hexdigest()

    with app.app_context():
        db.session.add(
            Semester(
                user_id=TEST_USER_ID,
                name="2026年度 前期",
                start_date=date(2026, 4, 1),
                end_date=date(2026, 7, 31),
            )
        )
        db.session.commit()
        assert db.session.scalar(
            text("SELECT COUNT(*) FROM semesters")
        ) == 1

    assert hashlib.sha256(template_db.read_bytes()).hexdigest() == (
        template_hash_before
    )


def test_create_app_requires_test_database_uri():
    with pytest.raises(ValueError, match="SQLALCHEMY_DATABASE_URI"):
        create_app({"TESTING": True})


def test_client_can_get_homepage(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
