"""DBの切り替え（環境変数 DATABASE_URL）と、DBのファイルの場所の確認。

アプリ全体（create_app）は作らず、Flaskの空のアプリに、設定と
instance/ の場所（pytestの一時ディレクトリ）を与えて確かめる。
DBには接続しない。
"""
import os
from pathlib import Path

import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from app.config import DEFAULT_DATABASE_URI, database_uri
from app.database_files import (
    database_file_path,
    describe_database,
    is_in_real_backup_directory,
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


def test_same_file_with_other_path_is_real_database(tmp_path):
    # パスの文字は違っても、同じファイル（ハードリンク）なら実データのDB。
    # macOSの大文字・小文字の違い（APP.db）は、下のテストで確かめる
    real_path = tmp_path / "app.db"
    real_path.write_bytes(b"real data")
    alias_path = tmp_path / "alias.db"
    os.link(real_path, alias_path)
    other_path = tmp_path / "other.db"
    other_path.write_bytes(b"real data")
    bare_app = make_bare_app(tmp_path, DEFAULT_DATABASE_URI)

    assert is_real_database(alias_path, bare_app)
    # 中身が同じでも、別のファイルは実データのDBではない
    assert not is_real_database(other_path, bare_app)


def test_other_case_name_is_real_database(tmp_path):
    # macOSの既定のように、大文字・小文字を区別しないファイルシステムでだけ
    # 動く（CIや、Claudeの作業環境では skip）。一時ディレクトリの中だけで
    # 確かめる（実データのDBで APP.db を試さない）
    (tmp_path / "probe").write_bytes(b"")
    if not (tmp_path / "PROBE").exists():
        pytest.skip("大文字・小文字を区別するファイルシステム")
    (tmp_path / "app.db").write_bytes(b"real data")
    bare_app = make_bare_app(tmp_path, DEFAULT_DATABASE_URI)

    assert is_real_database(tmp_path / "APP.db", bare_app)


def test_other_case_name_is_real_database_before_it_exists(tmp_path):
    # 実データのDBがまだなく、ファイルで比べられないときも、同じフォルダの、
    # 大文字・小文字だけが違う名前は、実データのDBとして扱う（どの環境でも）
    bare_app = make_bare_app(tmp_path, DEFAULT_DATABASE_URI)

    assert is_real_database(tmp_path / "APP.db", bare_app)
    assert is_real_database(tmp_path / "App.DB", bare_app)
    # ほかのフォルダの app.db や、名前が違うものは、実データのDBではない
    assert not is_real_database(tmp_path / "backups" / "APP.db", bare_app)
    assert not is_real_database(tmp_path / "app2.db", bare_app)


def test_in_real_backup_directory(tmp_path):
    backups = tmp_path / "backups"
    (backups / "old").mkdir(parents=True)
    bare_app = make_bare_app(tmp_path, DEFAULT_DATABASE_URI)

    assert is_in_real_backup_directory(backups / "x.db", bare_app)
    assert is_in_real_backup_directory(backups / "old" / "x.db", bare_app)
    assert is_in_real_backup_directory(
        tmp_path / "sub" / ".." / "backups" / "x.db", bare_app
    )
    assert not is_in_real_backup_directory(tmp_path / "x.db", bare_app)
    assert not is_in_real_backup_directory(tmp_path / "app.db", bare_app)
    assert not is_in_real_backup_directory(
        tmp_path / "other" / "backups" / "x.db", bare_app
    )


def test_in_real_backup_directory_through_link(tmp_path):
    # 別の名前（シンボリックリンク）で、同じフォルダを指していても、中と扱う
    instance_path = tmp_path / "instance"
    (instance_path / "backups").mkdir(parents=True)
    link_path = tmp_path / "link"
    os.symlink(instance_path / "backups", link_path)
    bare_app = make_bare_app(instance_path, DEFAULT_DATABASE_URI)

    assert is_in_real_backup_directory(link_path / "x.db", bare_app)


def test_other_case_backup_directory_is_real_backup_directory(tmp_path):
    # 大文字・小文字を区別しないファイルシステム（macOSの既定）でだけ動く
    (tmp_path / "probe").write_bytes(b"")
    if not (tmp_path / "PROBE").exists():
        pytest.skip("大文字・小文字を区別するファイルシステム")
    (tmp_path / "backups").mkdir()
    bare_app = make_bare_app(tmp_path, DEFAULT_DATABASE_URI)

    assert is_in_real_backup_directory(tmp_path / "BACKUPS" / "x.db", bare_app)


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
