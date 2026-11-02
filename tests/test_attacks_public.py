"""攻撃のテスト（公開：プロキシの後ろ・本番の設定・端末の印・データ）。

Task 026 の実装に、攻撃のテストの担当（エージェント）が、攻撃者として
試したことのうち、残す価値のあるもの（tests/test_production.py・
test_trusted_devices.py・test_transfer.py・test_check_public.py に、
まだないもの）。
- 受け入れた弱さと、見つけてまだ直していない弱さを再現するテストは、
  xfail(strict=True, raises=AssertionError) を付ける（今は「予想どおり
  失敗」）。直したら、印を外す（外さないと、XPASS で失敗する）
- 守られていることを確かめるテスト
本番の設定のアプリは fixture production_app。要求は、プロキシの後ろに
ブラウザから届いたように送る（tests/test_production.py の PublicClient）。
"""
import io
import logging
import re
import sqlite3
import stat
import threading
from contextlib import closing

import pytest
from click.testing import CliRunner
from flask.cli import FlaskGroup
from sqlalchemy.exc import IntegrityError

from app import create_app
from app.backup import BackupError
from app.config import PROJECT_ROOT, ConfigError, production_settings
from app.database_files import database_file_path
from app.env_file import environment_with_env_file, read_env_file
from app.extensions import db
from app.login_limits import GLOBAL_FAILURE_LIMIT, client_key
from app.models.login_failure import LoginFailure
from app.models.trusted_device import TrustedDevice
from app.models.user_session import UserSession
from app.routes import auth as auth_routes
from app.transfer import make_transfer_copy
from app.trusted_devices import MAX_DEVICE_FAILURES, MAX_DEVICES_PER_USER
from scripts.check_public import (
    EXPECTED_HEADERS,
    Report,
    Response,
    check_basics,
    security_header_problems,
)
from tests.auth_support import (
    OTHER_USERNAME,
    START,
    TEST_PASSWORD,
    TEST_USER_ID,
    TEST_USERNAME,
    add_recent_failures,
    create_user,
    failure_count,
    post_login,
)
from tests.production_support import (
    FORM,
    OWNER_ADDRESS,
    PUBLIC_HOST,
    ProxyTarget,
    post_public_login,
    production_environment,
    public_client,
    seen_environ,
    table_names,
)

WRONG_PASSWORD = "wrong password for test"
ATTACKER_ADDRESS = "203.0.113.9"
DEVICE_COOKIE = "__Host-schedule_device"
SESSION_COOKIE = "__Host-schedule_session"
# 2人目の利用者（架空）のパスワード
OTHER_PASSWORD = "umi yama kawa 2098 tori"
# エラーの応答・ログに出てはいけない、利用者のデータの代わり
SECRET_TEXT = "attack-secret-value-7f3a"


# --- 補助 ---


def post_bad_id(client, number, headers=None):
    """決まりに合わないID（大文字と空白）で送る。

    パスワードを確かめない（scrypt を計算しない）が、失敗として数える。
    攻撃者には、安い試行。
    """
    return client.post(
        "/login",
        data={"login_id": f"Bad ID {number}", "password": "x"},
        headers=FORM if headers is None else headers,
    )


def owner_with_device(app):
    """持ち主が、いつもの端末で1回ログインし、ログアウトした client。

    client は、端末の印の Cookie（__Host-schedule_device）を持っている。
    """
    owner = public_client(app)
    assert post_public_login(owner).status_code == 303
    owner.post("/logout", headers=FORM)
    return owner


def device_token_of(client) -> str:
    cookie = client.client.get_cookie(DEVICE_COOKIE, domain=PUBLIC_HOST)
    assert cookie is not None
    return cookie.value


def client_with_cookie(app, name, value, address=ATTACKER_ADDRESS):
    """Cookie を1つ持たせた、ほかの端末の client（盗んだ印など）。"""
    client = public_client(app, address)
    client.client.set_cookie(name, value, domain=PUBLIC_HOST)
    return client


def lock_out_owner_id(app):
    """攻撃者が、持ち主のIDで5回失敗し、IDごとの制限を始める。"""
    attacker = public_client(app, ATTACKER_ADDRESS)
    for _ in range(5):
        post_public_login(attacker, password=WRONG_PASSWORD)
    newcomer = public_client(app, "192.0.2.77")
    assert post_public_login(newcomer).status_code == 429


def device_count(app) -> int:
    with app.app_context():
        return db.session.scalar(
            db.select(db.func.count()).select_from(TrustedDevice)
        )


def post_other_user(client):
    return client.post(
        "/login",
        data={"login_id": OTHER_USERNAME, "password": OTHER_PASSWORD},
        headers=FORM,
    )


# --- 1. 接続元（プロキシの後ろ。app/proxy.py） ---

# 利用者が自由に付けられる、接続元を名乗るヘッダー
SPOOF_HEADERS = [
    "X-Forwarded-For",
    "X-Client-IP",
    "True-Client-IP",
    "CF-Connecting-IP",
    "X-Cluster-Client-IP",
    "Client-IP",
    "X-Originating-IP",
]


def test_forwarding_headers_do_not_move_the_address_count(production_app):
    # 攻撃者は、X-Real-IP（プロキシが上書きする）のほかを毎回変える
    attacker = public_client(production_app, ATTACKER_ADDRESS)
    statuses = []
    for number in range(11):
        fake = f"192.0.2.{number + 1}"
        headers = FORM | {name: fake for name in SPOOF_HEADERS}
        headers["Forwarded"] = f"for={fake}"
        statuses.append(post_bad_id(attacker, number, headers).status_code)

    assert statuses == [401] * 10 + [429]
    # 持ち主（ほかの接続元）は、攻撃者の接続元の制限を受けない
    owner = public_client(production_app)
    assert post_public_login(owner).status_code == 303


@pytest.mark.parametrize(
    "value",
    [
        "[2001:db8::1]",
        "[2001:db8::1]:443",
        "203.0.113.5,198.51.100.1",
        "203.0.113.5;proxy",
        "203.0.113.5 198.51.100.1",
        "127.1",
        "2130706433",
        "0x7f000001",
        "203.0.113.005",
        "２０３.０.１１３.５",
    ],
)
def test_odd_client_address_spellings_are_rejected(value):
    # 1つのアドレスの決まった書き方でなければ、アプリに渡さない（400）
    assert (
        seen_environ(HTTP_X_REAL_IP=value, HTTP_X_FORWARDED_PROTO="https")
        is None
    )


def test_ipv6_zone_ids_do_not_split_the_address_count():
    # 「%名前」（ゾーン）は、アドレスとして読めるが、/64 で1つに数える
    keys = set()
    for zone in ("a", "b", "eth0"):
        seen = seen_environ(
            HTTP_X_REAL_IP=f"2001:db8::1%{zone}",
            HTTP_X_FORWARDED_PROTO="https",
        )
        keys.add(client_key(seen["REMOTE_ADDR"]))

    assert keys == {"2001:db8::/64"}


def test_many_networks_fill_only_up_to_the_global_limit(production_app):
    # IPv6 の /48 を1つ持つ攻撃者は、/64 を変えながら、決まりに合わない
    # ID（計算のいらない試行）を送り、接続元ごとの制限を回り込む。
    # 失敗の行は、全体の上限で止まり、印のある本人の端末は入れる
    owner = owner_with_device(production_app)
    for number in range(GLOBAL_FAILURE_LIMIT):
        attacker = public_client(production_app, f"2001:db8:1:{number:x}::1")
        assert post_bad_id(attacker, number).status_code == 401

    newcomer = public_client(production_app, "2001:db8:1:ffff::1")
    assert post_bad_id(newcomer, 999).status_code == 503
    assert failure_count(production_app) == GLOBAL_FAILURE_LIMIT
    assert post_public_login(owner).status_code == 303


# --- 2. Host・Origin・Cookie・ヘッダー（本番） ---


@pytest.mark.parametrize(
    "host",
    [
        "SCHEDULE.EXAMPLE",
        "schedule.example.",
        "schedule.example.evil.example",
        "evil.example",
        "schedule.example@evil.example",
    ],
)
@pytest.mark.parametrize("path", ["/login", "/api/semesters"])
def test_other_host_spellings_are_rejected(production_app, host, path):
    response = public_client(production_app).get(
        path, headers={"Host": host}
    )

    assert response.status_code == 400
    assert "Strict-Transport-Security" in response.headers
    if path.startswith("/api"):
        # API は、決まった JSON（断った名前を、書き戻さない）
        assert response.get_json()["error"]["code"] == "bad_request"
        assert b"evil" not in response.data


def test_rejected_host_is_not_reflected_as_markup(production_app):
    # 画面の400（Flask の標準）は、断った Host を文に入れるが、
    # エスケープし、CSP も付く（ブラウザの攻撃者は Host を変えられない）
    host = 'evil.example"><svg onload=alert(1)>'

    response = public_client(production_app).get(
        "/login", headers={"Host": host}
    )

    assert response.status_code == 400
    assert b"<svg" not in response.data
    csp = response.headers["Content-Security-Policy"]
    assert "'unsafe-inline'" not in csp


@pytest.mark.parametrize(
    "origin",
    [
        "https://schedule.example:443",
        "https://SCHEDULE.EXAMPLE",
        "https://schedule.example.",
        "https://schedule.example/",
        "https://schedule.example.evil.example",
        "https://evil.example/https://schedule.example",
        "https://schedule.example, https://evil.example",
    ],
)
def test_other_origin_spellings_are_forbidden(production_app, origin):
    client = public_client(production_app)

    response = post_public_login(
        client, headers={"Origin": origin, "Sec-Fetch-Site": "same-origin"}
    )

    assert response.status_code == 403


def test_cookies_without_host_prefix_are_ignored_in_production(
    production_app,
):
    # __Host- のない名前の Cookie は、ほかのサブドメインからも置ける。
    # 本番では、その名前の印・ログインを使わない
    owner = owner_with_device(production_app)
    token = device_token_of(owner)
    lock_out_owner_id(production_app)

    thief = client_with_cookie(
        production_app, "schedule_device", token, OWNER_ADDRESS
    )
    assert post_public_login(thief).status_code == 429

    logged_in = public_client(production_app, "192.0.2.80")
    with production_app.app_context():
        from app.user_sessions import start_session

        session_token = start_session(TEST_USER_ID)
        db.session.commit()
    logged_in.client.set_cookie(
        "schedule_session", session_token, domain=PUBLIC_HOST
    )
    assert logged_in.get("/api/semesters").status_code == 401


@pytest.mark.parametrize(
    ("method", "path", "headers", "data", "status"),
    [
        ("GET", "/login", {}, None, 200),
        ("GET", "/", {}, None, 303),
        ("GET", "/api/semesters", {}, None, 401),
        ("GET", "/static/css/style.css", {}, None, 200),
        ("GET", "/static/no-such-file.css", {}, None, 404),
        (
            "POST",
            "/api/semesters",
            {"Sec-Fetch-Site": "cross-site", "Origin": "https://evil.example"},
            None,
            403,
        ),
        ("POST", "/login", FORM, b"a" * (17 * 1024), 413),
        ("GET", "/login", {"Host": "evil.example"}, None, 400),
    ],
)
def test_every_kind_of_response_has_hsts_and_security_headers(
    production_app, method, path, headers, data, status
):
    response = public_client(production_app).open(
        path,
        method=method,
        headers=headers,
        data=data,
        content_type="application/x-www-form-urlencoded",
    )

    assert response.status_code == status
    assert response.headers["Strict-Transport-Security"] == (
        "max-age=31536000"
    )
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in (
        response.headers["Content-Security-Policy"]
    )


def test_logout_all_clears_cookies_with_host_prefix_attributes(
    production_app,
):
    # ブラウザは、__Host- の Cookie を、Secure・Path=/・Domain なしの
    # Set-Cookie でしか、消さない（属性が違うと、消えずに残る）
    client = public_client(production_app)
    post_public_login(client)

    response = client.post("/logout-all", headers=FORM)

    cleared = {
        header.split("=", 1)[0]: header.split("; ")
        for header in response.headers.getlist("Set-Cookie")
    }
    assert set(cleared) == {SESSION_COOKIE, DEVICE_COOKIE}
    for attributes in cleared.values():
        assert "Secure" in attributes
        assert "Path=/" in attributes
        assert "Max-Age=0" in attributes
        assert not any(a.lower().startswith("domain=") for a in attributes)


# --- 3. 端末の印（app/trusted_devices.py・app/routes/auth.py） ---


def test_stolen_device_token_gives_only_five_guesses(production_app):
    # 共用のPCなどから、印を盗んだ攻撃者（ほかの接続元）。IDの制限の間も、
    # 印で5回だけ試せる。そのあとは、ふつうの制限を受ける
    owner = owner_with_device(production_app)
    lock_out_owner_id(production_app)
    thief = client_with_cookie(
        production_app, DEVICE_COOKIE, device_token_of(owner)
    )

    statuses = [
        post_public_login(thief, password=WRONG_PASSWORD).status_code
        for _ in range(MAX_DEVICE_FAILURES + 1)
    ]

    assert statuses == [401] * MAX_DEVICE_FAILURES + [429]
    assert device_count(production_app) == 0
    # 正しいパスワードでも、使い切った印では入れない
    assert post_public_login(thief).status_code == 429


def test_long_password_on_device_path_is_logged_as_failure(
    production_app, caplog
):
    # 本番と同じく、例外を500の応答にする（テストの既定では、例外が出る）
    production_app.config["PROPAGATE_EXCEPTIONS"] = False
    owner = owner_with_device(production_app)
    thief = client_with_cookie(
        production_app, DEVICE_COOKIE, device_token_of(owner)
    )

    with caplog.at_level(logging.WARNING, logger="app.auth"):
        statuses = [
            post_public_login(thief, password="x" * 600).status_code
            for _ in range(MAX_DEVICE_FAILURES)
        ]

    assert device_count(production_app) == 0
    assert statuses == [401] * MAX_DEVICE_FAILURES
    assert "端末の印を、続けての失敗で無効にしました" in caplog.text


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "受け入れた弱さ（Low）：利用者ごとの印は10個まで、作った順に古いもの"
        "から消す。Cookie を残さないログイン（点検のスクリプトの --login・"
        "プライベートブラウズ）を10回すると、ログインし直していない端末の印が"
        "消える。パスワードを知っている人（持ち主）の操作でしか起きないため、"
        "手順書に注意を書いた（docs/development/deploy.md の「点検する」、"
        "docs/architecture/security.md の「端末の印」）"
    ),
)
def test_cookieless_logins_do_not_evict_the_owner_device(production_app):
    owner = owner_with_device(production_app)
    for _ in range(MAX_DEVICES_PER_USER):
        cookieless = public_client(production_app, "192.0.2.60")
        assert post_public_login(cookieless).status_code == 303
    lock_out_owner_id(production_app)

    assert post_public_login(owner).status_code == 303


def test_stolen_device_token_does_not_reveal_the_login_id(production_app):
    owner = owner_with_device(production_app)
    thief = client_with_cookie(
        production_app, DEVICE_COOKIE, device_token_of(owner)
    )
    # 攻撃者は、先に自分の接続元を制限させる（10回。計算のいらない試行）
    for number in range(10):
        post_bad_id(thief, number)

    answers = {}
    for candidate in ["guess-one", "guess-two", TEST_USERNAME]:
        response = thief.post(
            "/login",
            data={"login_id": candidate, "password": WRONG_PASSWORD},
            headers=FORM,
        )
        answers[candidate] = response.status_code

    # どのIDでも、同じ応答（IDが分からない）
    assert len(set(answers.values())) == 1, answers


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "受け入れた弱さ（Low。利用者が2人以上のとき）：印のある道の確かめの"
        "枠（1つ）は、すべての利用者で共有。ほかの利用者が、正しいパスワード"
        "で何度もログインすると、持ち主の印のある端末は503になりうる。今の"
        "利用者は持ち主だけ。利用者を増やす段階4で決める"
        "（docs/architecture/security.md の「端末の印」）"
    ),
)
def test_other_user_cannot_hold_the_device_slot(production_app, monkeypatch):
    create_user(production_app, OTHER_USERNAME, OTHER_PASSWORD)
    owner = owner_with_device(production_app)
    other = public_client(production_app, "192.0.2.50")
    assert post_other_user(other).status_code == 303
    other.post("/logout", headers=FORM)

    # ほかの利用者の確かめ（印のある道）が、途中のあいだに送る
    started = threading.Event()
    release = threading.Event()
    original_verify = auth_routes.verify_password

    def slow_for_other_user(password_hash, password):
        if password == OTHER_PASSWORD:
            started.set()
            release.wait(10)
        return original_verify(password_hash, password)

    monkeypatch.setattr(auth_routes, "verify_password", slow_for_other_user)
    monkeypatch.setattr(auth_routes, "PASSWORD_CHECK_WAIT_SECONDS", 0)
    thread = threading.Thread(target=post_other_user, args=(other,))
    thread.start()
    assert started.wait(10)
    try:
        response = post_public_login(owner)
    finally:
        release.set()
        thread.join()

    assert response.status_code == 303


# --- 4. 全体の上限（1時間に300） ---


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "受け入れた弱さ（Low）：全体の上限の確かめは、試行の制限の鍵の外。"
        "同時の試行は、上限を、同時に動く数（uWSGI の threads。4）まで超え"
        "うる。数行のため、ディスクと計算の守りには影響しない"
        "（docs/architecture/security.md の「ログインの試行の制限」）"
    ),
)
def test_global_limit_is_not_overshot_by_concurrent_attempts(
    app, clock_now, monkeypatch
):
    add_recent_failures(app, GLOBAL_FAILURE_LIMIT - 1, START)
    parties = 3
    barrier = threading.Barrier(parties, timeout=10)
    original_check = auth_routes.too_many_recent_failures

    def check_at_the_same_time(now):
        # 3つの試行が、そろって上限を確かめてから、先へ進む
        result = original_check(now)
        barrier.wait()
        return result

    monkeypatch.setattr(
        auth_routes, "too_many_recent_failures", check_at_the_same_time
    )

    def attempt(number):
        post_login(
            app.test_client(),
            f"Bad ID {number}",
            "x",
            f"203.0.113.{number + 10}",
        )

    threads = [
        threading.Thread(target=attempt, args=(number,))
        for number in range(parties)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert failure_count(app) <= GLOBAL_FAILURE_LIMIT


# --- 5. 本番の設定の取り違え ---


def test_flask_run_is_refused_in_production(
    tmp_path, keep_umask, monkeypatch
):
    # 本番で flask run（--debugger を付けると、app.debug がオフのまま、
    # Werkzeug のデバッガー付きで起動する）を断る。本物の flask run と
    # 同じく、アプリは run の中で作る（見つけたとき、断れなかった）
    started = []
    # 本当には起動しない（サーバーを起動する関数を差し替える）
    monkeypatch.setattr(
        "flask.cli.run_simple",
        lambda *args, **kwargs: started.append(kwargs),
    )
    settings = production_settings(production_environment(tmp_path))
    group = FlaskGroup(
        create_app=lambda: create_app({"TESTING": True, **settings}),
        load_dotenv=False,
    )

    result = CliRunner().invoke(group, ["run", "--debugger"])

    assert started == []
    assert isinstance(result.exception, ConfigError)


@pytest.mark.parametrize("value", ["true", "yes", "on", "True"])
def test_debug_flag_spellings_refuse_to_start(
    tmp_path, keep_umask, monkeypatch, value
):
    monkeypatch.setenv("FLASK_DEBUG", value)
    settings = production_settings(production_environment(tmp_path))

    with pytest.raises(ConfigError, match="デバッグモード"):
        create_app({"TESTING": True, **settings})


def test_env_file_symlink_to_open_file_is_refused(tmp_path):
    # リンク自身でなく、リンク先の権限で判断する
    target = tmp_path / "shared.env"
    target.write_text("APP_ENV=production\n", encoding="utf-8")
    target.chmod(0o644)
    link = tmp_path / "production.env"
    link.symlink_to(target)

    with pytest.raises(ConfigError, match="chmod 600"):
        read_env_file(link)


def test_env_file_inside_database_directory_is_refused(tmp_path):
    environment = production_environment(tmp_path)
    env_file = tmp_path / "data" / "production.env"
    env_file.write_text(
        "".join(f"{name}={value}\n" for name, value in environment.items()),
        encoding="utf-8",
    )
    env_file.chmod(0o600)

    refused = False
    try:
        environment_with_env_file({"SCHEDULE_ENV_FILE": str(env_file)})
    except ConfigError:
        refused = True

    assert refused


def test_database_directory_symlink_to_open_directory_is_refused(
    tmp_path, keep_umask
):
    open_directory = tmp_path / "open"
    open_directory.mkdir(mode=0o755)
    open_directory.chmod(0o755)
    link = tmp_path / "data-link"
    link.symlink_to(open_directory, target_is_directory=True)
    environment = production_environment(tmp_path) | {
        "DATABASE_URL": f"sqlite:///{link / 'app.db'}"
    }
    settings = production_settings(environment)

    with pytest.raises(ConfigError, match="chmod 700"):
        create_app({"TESTING": True, **settings})


# --- 6. 本文の上限とエラーの応答 ---

TOO_LARGE_JSON = b'{"name": "' + b"a" * (64 * 1024) + b'"}'


@pytest.mark.parametrize(
    "path", ["/api/semesters", "/api/subjects", "/api/events", "/api/tasks"]
)
def test_too_large_api_bodies_are_413_json_in_production(
    production_app, path
):
    client = public_client(production_app)
    post_public_login(client)

    response = client.post(
        path, data=TOO_LARGE_JSON, content_type="application/json"
    )

    assert response.status_code == 413
    assert response.get_json()["error"]["code"] == "too_large"
    assert "Strict-Transport-Security" in response.headers


def test_body_without_length_over_the_limit_is_not_accepted(production_app):
    # 長さ（Content-Length）のない本文（chunked）。サーバーが本文の終わり
    # を知らせる（wsgi.input_terminated）場合も、上限より多くは読まない
    client = public_client(production_app)
    post_public_login(client)
    body = b'{"name": "' + b"a" * (200 * 1024) + b'"}'

    response = client.post(
        "/api/semesters",
        input_stream=io.BytesIO(body),
        content_type="application/json",
        environ_overrides={"wsgi.input_terminated": True},
    )

    assert response.status_code == 413
    assert response.get_json()["error"]["code"] == "too_large"


def test_sql_error_messages_hide_user_data(production_app):
    # 例外の文（ログに出る）に、SQLの引数（利用者のデータ）を入れない
    with production_app.app_context():
        message = ""
        try:
            db.session.execute(
                db.text("INSERT INTO users (username) VALUES (:name)"),
                {"name": SECRET_TEXT},
            )
        except IntegrityError as error:
            message = str(error)
        db.session.rollback()

    assert "users" in message
    assert SECRET_TEXT not in message


def test_unexpected_errors_leak_nothing_in_production(production_app):
    def broken():
        raise RuntimeError(SECRET_TEXT)

    # 最初の要求の前に足す（テストの中だけの URL。app/ には入れない）
    production_app.add_url_rule("/api/attack-broken", "api_broken", broken)
    production_app.add_url_rule("/attack-broken", "page_broken", broken)
    production_app.config["PROPAGATE_EXCEPTIONS"] = False
    client = public_client(production_app)
    post_public_login(client)

    api = client.get("/api/attack-broken")
    page = client.get("/attack-broken")

    assert api.status_code == 500
    assert api.get_json()["error"]["code"] == "server_error"
    assert page.status_code == 500
    for response in (api, page):
        assert SECRET_TEXT.encode() not in response.data
        assert b"Traceback" not in response.data
        assert b"__debugger__" not in response.data
        assert "Strict-Transport-Security" in response.headers


# --- 7. データの保護 ---


def login_digests(app) -> list[str]:
    """ログイン中の端末・端末の印・失敗の記録の、DBの中の値（16進数）。"""
    with app.app_context():
        digests = [
            *db.session.scalars(db.select(UserSession.token_digest)),
            *db.session.scalars(db.select(TrustedDevice.token_digest)),
            *db.session.scalars(db.select(LoginFailure.login_id_digest)),
            *db.session.scalars(db.select(LoginFailure.client_digest)),
        ]
        db.engine.dispose()
    return digests


def test_transfer_copy_keeps_no_login_digests(app, tmp_path):
    # 失敗の記録（ほかの接続元）と、持ち主のログイン（端末の行と印）
    post_login(
        app.test_client(), TEST_USERNAME, WRONG_PASSWORD, ATTACKER_ADDRESS
    )
    post_login(app.test_client(), TEST_USERNAME, TEST_PASSWORD)
    source = database_file_path(app)
    digests = login_digests(app)
    assert len(digests) == 4
    assert all(digest.encode() in source.read_bytes() for digest in digests)
    output = tmp_path / "out" / "transfer.db"
    output.parent.mkdir()

    make_transfer_copy(source, output)

    # 行だけでなく、索引・空き領域にも、値のかけらが残らない
    copied = output.read_bytes()
    assert [d for d in digests if d.encode() in copied] == []


def test_transfer_copy_refuses_demo_user(app, tmp_path):
    source = database_file_path(app)
    with app.app_context():
        db.engine.dispose()
    with closing(sqlite3.connect(source)) as connection:
        connection.execute("UPDATE users SET username = 'demo'")
        connection.commit()

    refused = False
    try:
        make_transfer_copy(source, tmp_path / "transfer.db")
    except BackupError:
        refused = True

    assert refused


def test_transfer_command_refuses_link_into_repository(app, tmp_path):
    # 出力先が、リポジトリの中を指すリンク（まだない先）でも断る
    target = PROJECT_ROOT / "attack-transfer-target.db"
    link = tmp_path / "transfer.db"
    link.symlink_to(target)

    result = app.test_cli_runner().invoke(
        args=["make-transfer-copy", str(link)]
    )

    assert result.exit_code == 1
    assert "リポジトリのフォルダの外" in result.output
    assert not target.exists()


def test_daily_backup_folder_is_private(production_app):
    result = production_app.test_cli_runner().invoke(args=["daily-backup"])

    assert result.exit_code == 0, result.output
    backups = database_file_path(production_app).parent / "backups"
    assert stat.S_IMODE(backups.stat().st_mode) == 0o700
    for path in backups.iterdir():
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def migration_version(app) -> str:
    with app.app_context():
        return db.session.scalar(
            db.text("SELECT version_num FROM alembic_version")
        )


@pytest.mark.parametrize(
    "args",
    [
        ["db", "upgrade", "a750d741785a"],
        ["db", "stamp", "head", "--purge"],
        ["db", "downgrade", "head:base", "--sql"],
        ["db", "downgrade", "--", "-1"],
    ],
)
def test_production_database_does_not_go_back(production_app, args):
    # 古い版への upgrade・stamp の --purge・SQLだけの downgrade・相対の
    # downgrade でも、本番のDBの形と「どこまで当てたか」は変わらない
    tables = table_names(production_app)
    version = migration_version(production_app)

    production_app.test_cli_runner().invoke(args=args)

    assert table_names(production_app) == tables
    assert migration_version(production_app) == version
    assert "trusted_devices" in tables


# --- 8. 日本時間（app/clock.py） ---

# サーバーの時計・タイムゾーンで、時刻・日付を決める書き方
SERVER_CLOCK_PATTERNS = [
    r"\butcnow\b",
    r"\bfromtimestamp\b",
    r"\btime\.time\(",
    r"\blocaltime\b",
    r"\bdatetime\.(?:now|today)\b",
    r"\bdate\.today\b",
    r"\bfunc\.(?:now|current_date|current_timestamp)\b",
    r"CURRENT_(?:DATE|TIME|TIMESTAMP)",
    r"server_default",
    r"['\"]now['\"]",
    r"from datetime import [^\n]*\bas\b",
    r"import datetime as",
]


def test_no_server_clock_outside_clock_module():
    paths = [
        *sorted((PROJECT_ROOT / "app").rglob("*.py")),
        PROJECT_ROOT / "run.py",
        PROJECT_ROOT / "wsgi.py",
    ]
    found = []
    for path in paths:
        if path.name == "clock.py":
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in SERVER_CLOCK_PATTERNS:
            for match in re.finditer(pattern, text):
                line = text.count("\n", 0, match.start()) + 1
                found.append(f"{path.relative_to(PROJECT_ROOT)}:{line}")

    assert found == []


# --- 9. 点検のスクリプト（scripts/check_public.py） ---


def good_headers(**changes) -> dict[str, str]:
    """点検が ✓ にするはずの、アプリの応答のヘッダー。"""
    headers = dict(EXPECTED_HEADERS)
    headers["Strict-Transport-Security"] = "max-age=31536000"
    headers["Permissions-Policy"] = "camera=(), microphone=()"
    headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; object-src 'none'; "
        "frame-ancestors 'none'"
    )
    headers.update(changes)
    return headers


def test_header_check_passes_the_good_headers():
    assert security_header_problems(good_headers()) == []


@pytest.mark.parametrize(
    "csp",
    [
        "default-src 'self' *; object-src 'none'; frame-ancestors 'none'",
        "default-src 'self'; script-src 'self' https: data:; "
        "object-src 'none'; frame-ancestors 'none'",
    ],
)
def test_header_check_finds_weak_script_sources(csp):
    headers = good_headers(**{"Content-Security-Policy": csp})

    assert security_header_problems(headers) != []


class ProxyAnswersOtherHosts(ProxyTarget):
    """ほかの名前の Host には、プロキシが自分で答える（アプリに届かない）。"""

    def request(self, method, path, headers=None, body=None, *, https=True):
        if (headers or {}).get("Host") == "evil.example":
            return Response(
                404,
                [("Content-Type", "text/html")],
                b"<h1>Site not found</h1>",
                "TLSv1.3",
            )
        return super().request(method, path, headers, body, https=https)


def test_host_check_tells_who_answered(production_app, capsys):
    # プロキシが、ほかの名前の Host に自分で答えると、アプリの確かめは、
    # 外からは見えない。点検は、✓ にするが、答えたのがプロキシだと表示
    # する（見つけたときは、何も言わずに ✓ にしていた）
    report = Report()

    check_basics(ProxyAnswersOtherHosts(production_app), report)

    output = capsys.readouterr().out
    assert "✓ ほかの名前の Host は受け付けない" in output
    assert "プロキシが 404 で答えた" in output


def test_host_check_shows_the_app_answer(production_app, capsys):
    # プロキシが、そのままアプリへ渡すときは、アプリが 400 で断る
    report = Report()

    check_basics(ProxyTarget(production_app), report)

    assert "アプリが 400 で答えた" in capsys.readouterr().out
