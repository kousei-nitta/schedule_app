"""本番の設定（APP_ENV=production）と、プロキシの後ろの接続元（Task 026）。

仕様は docs/architecture/security.md の「本番の設定」。本番のアプリの
作り方は、tests/production_support.py と、fixture production_app
（tests/conftest.py）。
"""
import logging
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest
from flask_migrate import downgrade, stamp, upgrade

from app import create_app
from app.config import (
    PROJECT_ROOT,
    ConfigError,
    production_settings,
    settings_from_environment,
)
from app.env_file import environment_with_env_file, read_env_file
from app.proxy import PublicProxyMiddleware
from tests.auth_support import TEST_PASSWORD, TEST_USERNAME
from tests.production_support import (
    OWNER_ADDRESS,
    PUBLIC_HOST,
    PUBLIC_ORIGIN,
    SECRET,
    production_environment,
)

MIGRATIONS = str(PROJECT_ROOT / "migrations")


class PublicClient:
    """プロキシの後ろの本番に、ブラウザから届いた要求のように送る client。

    ブラウザ → プロキシ（HTTPS を終える）→ アプリ（HTTP）。プロキシが付ける
    ヘッダー（X-Real-IP・X-Forwarded-Proto）を付け、Host を本番の名前にする。
    """

    def __init__(self, app, address=OWNER_ADDRESS):
        self.client = app.test_client()
        self.client.environ_base.update(
            {
                "HTTP_X_REAL_IP": address,
                "HTTP_X_FORWARDED_PROTO": "https",
                # アプリが直接見る接続元は、プロキシのアドレス
                "REMOTE_ADDR": "10.0.0.1",
            }
        )

    def open(self, path, **kwargs):
        kwargs.setdefault("base_url", f"http://{PUBLIC_HOST}")
        return self.client.open(path, **kwargs)

    def get(self, path, **kwargs):
        return self.open(path, method="GET", **kwargs)

    def post(self, path, **kwargs):
        return self.open(path, method="POST", **kwargs)


def public_client(app, address=OWNER_ADDRESS):
    return PublicClient(app, address)


FORM = {"Origin": PUBLIC_ORIGIN, "Sec-Fetch-Site": "same-origin"}


def post_public_login(client, password=TEST_PASSWORD, headers=None):
    return client.post(
        "/login",
        data={"login_id": TEST_USERNAME, "password": password},
        headers=FORM if headers is None else headers,
    )


# --- 環境変数から設定を決める ---


def test_local_without_app_env():
    settings = settings_from_environment({})

    assert settings == {"SQLALCHEMY_DATABASE_URI": "sqlite:///app.db"}


@pytest.mark.parametrize("value", ["prod", "Production", "local", "1"])
def test_unknown_app_env_refuses_to_start(value):
    # 書き間違いで、黙ってローカルの扱いにならない
    with pytest.raises(ConfigError, match="production だけ"):
        settings_from_environment({"APP_ENV": value})


def test_public_origin_without_production_refuses_to_start():
    with pytest.raises(ConfigError, match="APP_ENV=production"):
        settings_from_environment({"PUBLIC_ORIGIN": PUBLIC_ORIGIN})


def test_production_settings_follow_public_origin(tmp_path):
    environment = production_environment(tmp_path)

    settings = settings_from_environment(environment)

    assert settings["PRODUCTION"] is True
    assert settings["PUBLIC_ORIGIN"] == PUBLIC_ORIGIN
    assert settings["TRUSTED_HOSTS"] == [PUBLIC_HOST]
    assert settings["AUTH_COOKIE_NAME"] == "__Host-schedule_session"
    assert settings["DEVICE_COOKIE_NAME"] == "__Host-schedule_device"
    assert settings["AUTH_COOKIE_SECURE"] is True
    assert settings["SECRET_KEY"] == SECRET
    assert settings["CLIENT_ADDRESS_HEADER"] == "X-Real-IP"


@pytest.mark.parametrize(
    "origin",
    [
        "",
        "http://schedule.example",
        "https://schedule.example/",
        "https://schedule.example:443",
        "https://schedule.example/app",
        "https://Schedule.example",
        "https://localhost",
        "https://schedule.example?x=1",
        "https://user@schedule.example",
        " https://schedule.example/ ",
    ],
)
def test_wrong_public_origin_refuses_to_start(tmp_path, origin):
    environment = production_environment(tmp_path) | {"PUBLIC_ORIGIN": origin}

    with pytest.raises(ConfigError, match="PUBLIC_ORIGIN"):
        settings_from_environment(environment)


@pytest.mark.parametrize("secret", ["", "short", "x" * 31])
def test_production_needs_long_secret_key_in_environment(tmp_path, secret):
    environment = production_environment(tmp_path) | {"SECRET_KEY": secret}

    with pytest.raises(ConfigError, match="SECRET_KEY"):
        settings_from_environment(environment)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "sqlite:///app.db",
        "sqlite://",
        "sqlite:///:memory:",
        "postgresql://user:pass@db.example/app",
        "not a url",
        f"sqlite:///{PROJECT_ROOT / 'instance' / 'app.db'}",
        f"sqlite:///{PROJECT_ROOT / 'prod.db'}",
    ],
)
def test_wrong_production_database_refuses_to_start(tmp_path, url):
    environment = production_environment(tmp_path) | {"DATABASE_URL": url}

    with pytest.raises(ConfigError, match="DATABASE_URL|DB"):
        settings_from_environment(environment)


@pytest.mark.parametrize("header", ["", "X Real IP", "X-Real-IP:", "日本"])
def test_wrong_client_address_header_refuses_to_start(tmp_path, header):
    environment = production_environment(tmp_path) | {
        "CLIENT_ADDRESS_HEADER": header
    }

    with pytest.raises(ConfigError, match="CLIENT_ADDRESS_HEADER"):
        settings_from_environment(environment)


def test_remote_addr_may_be_the_client_address(tmp_path):
    environment = production_environment(tmp_path) | {
        "CLIENT_ADDRESS_HEADER": "REMOTE_ADDR"
    }

    settings = settings_from_environment(environment)

    assert settings["CLIENT_ADDRESS_HEADER"] == "REMOTE_ADDR"


def test_production_config_must_match_public_origin(
    template_db, tmp_path, keep_umask
):
    # 手で設定を上書きして、Host や Cookie がずれたら、起動しない
    settings = production_settings(production_environment(tmp_path))
    for wrong in (
        {"TRUSTED_HOSTS": ["other.example"]},
        {"AUTH_COOKIE_NAME": "schedule_session"},
        {"DEVICE_COOKIE_NAME": "schedule_device"},
        {"CLIENT_ADDRESS_HEADER": None},
    ):
        with pytest.raises(ConfigError, match="本番の設定"):
            create_app({"TESTING": True, **settings, **wrong})


# --- 設定のファイル ---


def write_env_file(path, text, mode=0o600):
    path.write_text(text, encoding="utf-8")
    path.chmod(mode)
    return path


def test_env_file_is_read(tmp_path):
    path = write_env_file(
        tmp_path / "production.env",
        "# 本番の設定\n\nAPP_ENV=production\n PUBLIC_ORIGIN = "
        f"{PUBLIC_ORIGIN}\nSECRET_KEY={SECRET}\n",
    )

    merged = environment_with_env_file(
        {"SCHEDULE_ENV_FILE": str(path), "HOME": "/home/x"}
    )

    assert merged["APP_ENV"] == "production"
    assert merged["PUBLIC_ORIGIN"] == PUBLIC_ORIGIN
    assert merged["SECRET_KEY"] == SECRET
    assert merged["HOME"] == "/home/x"


def test_without_env_file_environment_is_used_as_is():
    assert environment_with_env_file({"APP_ENV": "x"}) == {"APP_ENV": "x"}


@pytest.mark.parametrize("mode", [0o640, 0o604, 0o644])
def test_env_file_readable_by_others_is_refused(tmp_path, mode):
    path = write_env_file(tmp_path / "production.env", "APP_ENV=x\n", mode)

    with pytest.raises(ConfigError, match="chmod 600"):
        read_env_file(path)


def test_missing_env_file_is_refused(tmp_path):
    with pytest.raises(ConfigError, match="読めません"):
        read_env_file(tmp_path / "none.env")


def test_env_file_that_is_a_directory_is_refused(tmp_path):
    with pytest.raises(ConfigError, match="ふつうのファイル"):
        read_env_file(tmp_path)


@pytest.mark.parametrize(
    "text",
    ["SECRET=abc\n", "DEBUG=1\n", "no equals sign\n", "export APP_ENV=x\n"],
)
def test_env_file_with_unknown_lines_is_refused(tmp_path, text):
    path = write_env_file(tmp_path / "production.env", text)

    with pytest.raises(ConfigError, match="1 行目") as error:
        read_env_file(path)
    # 値（秘密かもしれない）を、エラーの文に入れない
    assert "abc" not in str(error.value)


def test_env_file_with_duplicate_names_is_refused(tmp_path):
    path = write_env_file(
        tmp_path / "production.env", "APP_ENV=production\nAPP_ENV=x\n"
    )

    with pytest.raises(ConfigError, match="2回"):
        read_env_file(path)


def test_same_name_in_environment_and_env_file_is_refused(tmp_path):
    path = write_env_file(tmp_path / "production.env", "APP_ENV=production\n")

    with pytest.raises(ConfigError, match="両方"):
        environment_with_env_file(
            {"SCHEDULE_ENV_FILE": str(path), "APP_ENV": "production"}
        )


# --- 本番の起動のときの確かめ ---


def test_production_app_starts(production_app):
    assert production_app.config["PRODUCTION"] is True
    assert isinstance(production_app.wsgi_app, PublicProxyMiddleware)


def test_production_sets_private_umask(production_app):
    current = os.umask(0o077)
    os.umask(current)

    assert current == 0o077


def test_debug_mode_refuses_to_start(tmp_path, keep_umask, monkeypatch):
    monkeypatch.setenv("FLASK_DEBUG", "1")
    settings = production_settings(production_environment(tmp_path))

    with pytest.raises(ConfigError, match="デバッグモード"):
        create_app({"TESTING": True, **settings})


@pytest.mark.parametrize("workers", [2, 4])
def test_more_than_one_uwsgi_worker_refuses_to_start(
    tmp_path, keep_umask, monkeypatch, workers
):
    # uWSGI の中だけにあるモジュール（uwsgi）を、テストで差し替える
    monkeypatch.setitem(sys.modules, "uwsgi", SimpleNamespace(numproc=workers))
    settings = production_settings(production_environment(tmp_path))

    with pytest.raises(ConfigError, match="ワーカーを1つ"):
        create_app({"TESTING": True, **settings})


def test_one_uwsgi_worker_starts(tmp_path, keep_umask, monkeypatch):
    monkeypatch.setitem(sys.modules, "uwsgi", SimpleNamespace(numproc=1))
    settings = production_settings(production_environment(tmp_path))

    assert create_app({"TESTING": True, **settings}).config["PRODUCTION"]


@pytest.mark.parametrize("mode", [0o750, 0o755, 0o701])
def test_database_directory_open_to_others_refuses_to_start(
    tmp_path, keep_umask, mode
):
    settings = production_settings(production_environment(tmp_path))
    (tmp_path / "data").chmod(mode)

    with pytest.raises(ConfigError, match="chmod 700"):
        create_app({"TESTING": True, **settings})


def test_missing_database_directory_refuses_to_start(tmp_path, keep_umask):
    settings = production_settings(production_environment(tmp_path))
    (tmp_path / "data").rmdir()

    with pytest.raises(ConfigError, match="mkdir -m 700"):
        create_app({"TESTING": True, **settings})


def test_run_py_refuses_production(tmp_path):
    # run.py（Flask の開発用のサーバー）は、本番では起動しない
    environment = {
        "PATH": os.environ.get("PATH", ""),
        **production_environment(tmp_path),
    }

    result = subprocess.run(
        [sys.executable, "run.py"],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode != 0
    assert "run.py を使いません" in result.stderr


# --- プロキシの後ろの接続元（app/proxy.py） ---


def seen_environ(header="X-Real-IP", **environ):
    """層を通ったあとに、アプリが受け取る environ（断られたら None）。"""
    seen = {}

    def inner_app(inner_environ, start_response):
        seen.update(inner_environ)
        start_response("200 OK", [])
        return [b""]

    statuses = []
    middleware = PublicProxyMiddleware(inner_app, header)
    middleware(environ, lambda status, headers: statuses.append(status))
    return seen if statuses == ["200 OK"] else None


def test_client_address_comes_from_the_chosen_header():
    seen = seen_environ(
        REMOTE_ADDR="10.0.0.1",
        HTTP_X_REAL_IP=" 203.0.113.5 ",
        HTTP_X_FORWARDED_FOR="192.0.2.99",
        HTTP_X_FORWARDED_PROTO="https",
    )

    assert seen["REMOTE_ADDR"] == "203.0.113.5"
    assert seen["wsgi.url_scheme"] == "https"


def test_ipv6_client_address_is_normalized():
    seen = seen_environ(
        HTTP_X_REAL_IP="2001:DB8:0:0::1", HTTP_X_FORWARDED_PROTO="https"
    )

    assert seen["REMOTE_ADDR"] == "2001:db8::1"


@pytest.mark.parametrize(
    "value",
    [None, "", "unknown", "203.0.113.5, 10.0.0.1", "203.0.113.5:443", "a b"],
)
def test_missing_or_wrong_client_address_is_rejected(value):
    environ = {"HTTP_X_FORWARDED_PROTO": "https", "REMOTE_ADDR": "10.0.0.1"}
    if value is not None:
        environ["HTTP_X_REAL_IP"] = value

    assert seen_environ(**environ) is None


@pytest.mark.parametrize("proto", [None, "http", "HTTPS", "https, http"])
def test_request_not_over_https_is_rejected(proto):
    environ = {"HTTP_X_REAL_IP": "203.0.113.5"}
    if proto is not None:
        environ["HTTP_X_FORWARDED_PROTO"] = proto

    assert seen_environ(**environ) is None


def test_remote_addr_setting_uses_the_server_address():
    seen = seen_environ(
        header="REMOTE_ADDR",
        REMOTE_ADDR="203.0.113.7",
        HTTP_X_REAL_IP="192.0.2.1",
        HTTP_X_FORWARDED_PROTO="https",
    )

    assert seen["REMOTE_ADDR"] == "203.0.113.7"


def test_rejected_request_does_not_reach_the_app(production_app):
    client = production_app.test_client()

    response = client.get(
        "/login",
        headers={"Host": PUBLIC_HOST, "X-Forwarded-Proto": "https"},
    )

    assert response.status_code == 400
    assert response.headers["Cache-Control"] == "no-store"


def test_spoofed_forwarded_for_does_not_change_the_logged_address(
    production_app, caplog
):
    client = public_client(production_app, address="203.0.113.5")

    with caplog.at_level(logging.WARNING, logger="app.auth"):
        response = post_public_login(
            client,
            password="wrong password for test",
            headers=FORM | {"X-Forwarded-For": "192.0.2.99"},
        )

    assert response.status_code == 401
    assert "'203.0.113.5'" in caplog.text
    assert "192.0.2.99" not in caplog.text


# --- 本番のヘッダー・Cookie・Host・Origin ---


def test_production_responses_have_hsts(production_app):
    response = public_client(production_app).get("/login")

    assert response.status_code == 200
    assert response.headers["Strict-Transport-Security"] == (
        "max-age=31536000"
    )


def test_local_responses_have_no_hsts(anonymous_client):
    response = anonymous_client.get("/login")

    assert "Strict-Transport-Security" not in response.headers


def test_login_cookie_uses_host_prefix_and_secure(production_app):
    response = post_public_login(public_client(production_app))

    assert response.status_code == 303
    cookies = response.headers.getlist("Set-Cookie")
    # ログインの Cookie と、端末の印の Cookie の2つ。どちらも __Host-
    assert sorted(cookie.split("=", 1)[0] for cookie in cookies) == [
        "__Host-schedule_device",
        "__Host-schedule_session",
    ]
    for cookie in cookies:
        attributes = cookie.split("; ")
        assert "Secure" in attributes
        assert "HttpOnly" in attributes
        assert "SameSite=Strict" in attributes
        assert "Path=/" in attributes
        assert not any(a.lower().startswith("domain=") for a in attributes)


def test_logged_in_production_client_can_use_the_api(production_app):
    client = public_client(production_app)
    post_public_login(client)

    response = client.get("/api/semesters")

    assert response.status_code == 200


def test_other_host_is_rejected_in_production(production_app):
    client = public_client(production_app)

    response = client.get("/login", headers={"Host": "evil.example"})

    assert response.status_code == 400


@pytest.mark.parametrize(
    "origin",
    ["http://schedule.example", "https://evil.example", "null"],
)
def test_origin_must_be_the_public_origin(production_app, origin):
    response = post_public_login(
        public_client(production_app),
        headers={"Origin": origin, "Sec-Fetch-Site": "same-origin"},
    )

    assert response.status_code == 403


# --- 本番で、DBを壊しうる操作を断る（migrations/env.py） ---


def test_upgrade_is_allowed_in_production(production_app):
    with production_app.app_context():
        upgrade(directory=MIGRATIONS)


def table_names(app) -> set[str]:
    from app.extensions import db

    with app.app_context():
        return set(db.inspect(db.engine).get_table_names())


def test_downgrade_is_refused_in_production(production_app, capsys):
    tables_before = table_names(production_app)

    # Flask-Migrate は、エラーを表示して、終了コード1で終わる
    with production_app.app_context(), pytest.raises(SystemExit):
        downgrade(directory=MIGRATIONS)

    assert "この操作" in capsys.readouterr().err
    assert table_names(production_app) == tables_before


def test_stamp_is_refused_in_production(production_app, capsys):
    with production_app.app_context(), pytest.raises(SystemExit):
        stamp(directory=MIGRATIONS, revision="base")

    assert "この操作" in capsys.readouterr().err


def test_downgrade_is_allowed_locally(app):
    # ローカル（テストのDB）では、今までどおり使える
    with app.app_context():
        downgrade(directory=MIGRATIONS)

    assert "trusted_devices" not in table_names(app)


# --- コマンド ---


def test_commands_show_production_and_the_database(production_app):
    runner = production_app.test_cli_runner()

    result = runner.invoke(args=["show-settings"])

    assert result.exit_code == 0, result.output
    assert "環境：本番（APP_ENV=production）" in result.output
    assert "本番の実データのDB" in result.output
    assert f"PUBLIC_ORIGIN：{PUBLIC_ORIGIN}" in result.output
    assert "接続元のヘッダー：X-Real-IP" in result.output
    assert "DBのフォルダの権限：700" in result.output
    # 秘密の鍵の値は出さない
    assert SECRET not in result.output
    assert "SECRET_KEY：あり（40文字）" in result.output


def test_local_commands_show_local(app):
    result = app.test_cli_runner().invoke(args=["show-settings"])

    assert result.exit_code == 0, result.output
    assert "環境：ローカル" in result.output


def test_demo_database_is_refused_in_production(production_app):
    result = production_app.test_cli_runner().invoke(
        args=["create-demo-db"], input="x\n"
    )

    assert result.exit_code == 1
    assert "本番（APP_ENV=production）では、デモデータを作れません" in (
        result.output
    )


def test_demo_username_is_refused_in_production(production_app):
    runner = production_app.test_cli_runner()

    created = runner.invoke(args=["create-user", "demo"], input="x\n")
    renamed = runner.invoke(args=["rename-user", TEST_USERNAME, "demo"])

    assert created.exit_code == 1
    assert renamed.exit_code == 1
    assert "デモの利用者のID" in created.output
    assert "デモの利用者のID" in renamed.output
