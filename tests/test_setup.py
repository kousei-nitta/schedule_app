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


def test_closures_table_matches_design(app):
    with app.app_context():
        inspector = inspect(db.engine)
        columns = {
            column["name"]: (str(column["type"]), column["nullable"])
            for column in inspector.get_columns("closures")
        }
        primary_key = inspector.get_pk_constraint("closures")
        foreign_keys = [
            (
                foreign_key["name"],
                foreign_key["constrained_columns"],
                foreign_key["referred_table"],
                foreign_key["referred_columns"],
            )
            for foreign_key in inspector.get_foreign_keys("closures")
        ]

    assert columns == {
        "id": ("INTEGER", False),
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
        )
    ]


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
