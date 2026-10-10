import hashlib
import shutil
from pathlib import Path

import pytest
from flask_migrate import upgrade

from app import create_app
from app.extensions import db


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEV_DB_PATH = PROJECT_ROOT / "instance" / "app.db"


def file_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="session", autouse=True)
def protect_dev_db():
    existed_before = DEV_DB_PATH.exists()
    hash_before = file_hash(DEV_DB_PATH)
    yield
    assert DEV_DB_PATH.exists() is existed_before
    assert file_hash(DEV_DB_PATH) == hash_before


@pytest.fixture(scope="session")
def template_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    template_directory = tmp_path_factory.mktemp("schedule-template")
    template_path = template_directory / "template.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{template_path}",
        }
    )

    with app.app_context():
        upgrade(directory=str(PROJECT_ROOT / "migrations"))
        db.engine.dispose()

    return template_path


@pytest.fixture
def app(template_db: Path, tmp_path: Path):
    database_path = tmp_path / "test.db"
    shutil.copy2(template_db, database_path)

    resolved_database_path = database_path.resolve()
    resolved_temporary_root = tmp_path.resolve()
    assert resolved_database_path.is_relative_to(resolved_temporary_root)
    assert resolved_database_path != DEV_DB_PATH.resolve()

    test_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{resolved_database_path}",
        }
    )
    yield test_app

    with test_app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()
