"""DBの切り替え（環境変数 DATABASE_URL）と、DBのファイルの場所の確認。

アプリ全体（create_app）は作らず、Flaskの空のアプリに、設定と
instance/ の場所（pytestの一時ディレクトリ）を与えて確かめる。
DBには接続しない。
"""
from pathlib import Path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from app.config import DEFAULT_DATABASE_URI, database_uri
from app.database_files import (
    database_file_path,
    describe_database,
    is_real_database,
    real_database_path,
)


def make_bare_app(instance_path: Path, uri: str) -> Flask:
    """instance/ を一時ディレクトリにした、空のFlaskアプリを作る。"""
    bare_app = Flask(__name__, instance_path=str(instance_path))
    bare_app.config["SQLALCHEMY_DATABASE_URI"] = uri
    return bare_app


def test_database_uri_uses_default_without_environment_variable():
    assert database_uri({}) == DEFAULT_DATABASE_URI
    assert DEFAULT_DATABASE_URI == "sqlite:///app.db"


def test_database_uri_uses_default_when_environment_variable_is_empty():
    assert database_uri({"DATABASE_URL": ""}) == DEFAULT_DATABASE_URI


def test_database_uri_uses_environment_variable():
    environment = {"DATABASE_URL": "sqlite:///demo.db"}

    assert database_uri(environment) == "sqlite:///demo.db"


def test_relative_sqlite_path_is_in_instance_directory(tmp_path):
    bare_app = make_bare_app(tmp_path, "sqlite:///demo.db")

    assert database_file_path(bare_app) == tmp_path / "demo.db"


def test_absolute_sqlite_path_is_used_as_is(tmp_path):
    database_path = tmp_path / "other" / "check.db"
    bare_app = make_bare_app(tmp_path, f"sqlite:///{database_path}")

    assert database_file_path(bare_app) == database_path


def test_file_path_matches_flask_sqlalchemy(tmp_path):
    # Flask-SQLAlchemyが実際に使うファイルと、同じパスになること
    for uri in ["sqlite:///demo.db", f"sqlite:///{tmp_path / 'a.db'}"]:
        bare_app = make_bare_app(tmp_path, uri)
        extension = SQLAlchemy()
        extension.init_app(bare_app)
        with bare_app.app_context():
            engine_path = Path(extension.engine.url.database)
            extension.engine.dispose()

        assert database_file_path(bare_app) == engine_path


def test_non_file_databases_have_no_file_path(tmp_path):
    uris = [
        "sqlite://",
        "sqlite:///:memory:",
        "postgresql://user:secret@localhost/schedule",
    ]
    for uri in uris:
        bare_app = make_bare_app(tmp_path, uri)

        assert database_file_path(bare_app) is None


def test_real_database_is_app_db_in_instance_directory(tmp_path):
    bare_app = make_bare_app(tmp_path, DEFAULT_DATABASE_URI)

    assert real_database_path(bare_app) == tmp_path / "app.db"
    assert is_real_database(tmp_path / "app.db", bare_app)
    assert is_real_database(tmp_path / "sub" / ".." / "app.db", bare_app)
    assert not is_real_database(tmp_path / "demo.db", bare_app)
    assert not is_real_database(tmp_path / "backups" / "app.db", bare_app)


def test_describe_real_database(tmp_path):
    bare_app = make_bare_app(tmp_path, DEFAULT_DATABASE_URI)

    message = describe_database(bare_app)

    assert message == f"DB：{tmp_path / 'app.db'}（実データのDB）"


def test_describe_other_sqlite_database(tmp_path):
    bare_app = make_bare_app(tmp_path, "sqlite:///demo.db")

    message = describe_database(bare_app)

    assert message == (
        f"DB：{tmp_path / 'demo.db'}"
        "（実データのDBではありません。DATABASE_URL で指定）"
    )


def test_describe_hides_password(tmp_path):
    uri = "postgresql://user:secret@localhost/schedule"
    bare_app = make_bare_app(tmp_path, uri)

    message = describe_database(bare_app)

    assert "secret" not in message
    assert message == (
        "DB：postgresql://user:***@localhost/schedule"
        "（実データのDBではありません）"
    )
