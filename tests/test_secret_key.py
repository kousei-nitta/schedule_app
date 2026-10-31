"""秘密の鍵（SECRET_KEY。app/secret_key.py）と、Cookie の設定の守りの
テスト。instance/ には触れず、一時ディレクトリで確かめる。
"""
import stat

import pytest

from app import create_app
from app.config import check_cookie_security
from app.secret_key import SecretKeyError, load_secret_key

LONG_KEY = "k" * 32


def test_environment_variable_is_used(tmp_path):
    key = load_secret_key(str(tmp_path), {"SECRET_KEY": f"  {LONG_KEY}  "})

    assert key == LONG_KEY
    # 環境変数があれば、ファイルを作らない
    assert list(tmp_path.iterdir()) == []


def test_short_environment_variable_is_refused(tmp_path):
    with pytest.raises(SecretKeyError, match="短すぎます"):
        load_secret_key(str(tmp_path), {"SECRET_KEY": "k" * 31})


def test_key_file_is_created_for_owner_only_and_reused(tmp_path):
    first = load_secret_key(str(tmp_path), {})
    second = load_secret_key(str(tmp_path), {})

    key_file = tmp_path / "secret_key"
    assert first == second
    assert len(first) == 64
    assert stat.S_IMODE(key_file.stat().st_mode) == 0o600


def test_key_file_readable_by_others_is_made_private(tmp_path):
    key_file = tmp_path / "secret_key"
    key_file.write_text(LONG_KEY)
    key_file.chmod(0o644)

    assert load_secret_key(str(tmp_path), {}) == LONG_KEY
    assert stat.S_IMODE(key_file.stat().st_mode) == 0o600


def test_short_key_file_is_refused(tmp_path):
    (tmp_path / "secret_key").write_text("short")

    with pytest.raises(SecretKeyError):
        load_secret_key(str(tmp_path), {})


def test_test_apps_get_a_random_key_without_files(tmp_path):
    database = f"sqlite:///{tmp_path / 'x.db'}"
    first = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": database})
    second = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": database})

    assert len(first.config["SECRET_KEY"]) == 64
    assert first.config["SECRET_KEY"] != second.config["SECRET_KEY"]


def test_local_hosts_may_use_cookies_without_secure():
    check_cookie_security(
        {
            "TRUSTED_HOSTS": ["127.0.0.1", "localhost"],
            "AUTH_COOKIE_SECURE": False,
        }
    )


@pytest.mark.parametrize("hosts", [[], None])
def test_empty_trusted_hosts_refuse_to_start(tmp_path, hosts):
    # 空・None では、Flask が Host を確かめなくなるため、起動しない
    with pytest.raises(RuntimeError, match="TRUSTED_HOSTS"):
        create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'x.db'}",
                "TRUSTED_HOSTS": hosts,
            }
        )


def test_public_host_without_secure_cookie_refuses_to_start(tmp_path):
    with pytest.raises(RuntimeError, match="AUTH_COOKIE_SECURE"):
        create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'x.db'}",
                "TRUSTED_HOSTS": ["schedule.example"],
            }
        )


def test_public_host_with_secure_cookie_starts(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'x.db'}",
            "TRUSTED_HOSTS": ["schedule.example"],
            "AUTH_COOKIE_SECURE": True,
        }
    )

    assert app.config["AUTH_COOKIE_SECURE"] is True
