"""攻撃のテスト（ログイン・試行の制限・ほかのサイト・既定で拒否）。

Task 025 の実装に、攻撃のテストの担当（エージェント）が、攻撃者として
試したことのうち、残す価値のあるもの（tests/test_auth.py に、まだないもの）。
- 受け入れた弱さ（今は直さないもの）を再現するテストは、
  xfail(strict=True, raises=AssertionError) を付ける（今は「予想どおり
  失敗」）。直したら、印を外す（外さないと、XPASS で失敗する）
- 見つかって直した弱さのテストと、守られていることを確かめるテスト
時刻は、app/clock.py の utc_now を差し替える（fixture clock_now）。
"""
import io
import re
import threading
from datetime import timedelta
from urllib.parse import urlencode

import pytest
from werkzeug.test import EnvironBuilder

from app.api_helpers import is_api_path
from app.auth import PUBLIC_ENDPOINTS
from app.extensions import db
from app.login_limits import client_key
from app.models.user_session import UserSession
from app.passwords import PASSWORD_HASH_METHOD
from app.routes import auth as auth_routes
from app.routes.auth import DUMMY_PASSWORD_HASH
from app.security import SECURITY_HEADERS
from app.user_sessions import start_session
from tests.auth_support import (
    COOKIE_NAME,
    FORM_HEADERS,
    START,
    TEST_PASSWORD,
    TEST_USERNAME,
    cookie_value,
    create_user,
    failure_count,
    post_login,
    session_cookie_header,
)

# ほかのサイトのページから、ブラウザが送る要求のヘッダー
CROSS_SITE_FETCH = {
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
}
CROSS_SITE_NAVIGATION = {
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Dest": "document",
}
WRONG_PASSWORD = "wrong password for test"
ATTACKER_ADDRESS = "203.0.113.9"
OWNER_ADDRESS = "198.51.100.20"


def all_sessions(app) -> list[UserSession]:
    with app.app_context():
        return list(db.session.scalars(db.select(UserSession)))


# --- 直した弱さ：HEAD /login が、ログインの試行になっていた ---
#
# login は、GET でなければ、すべて attempt_login に渡していた。Flask は
# HEAD を GET の route で受けるため、HEAD もログインの試行になっていた。
# HEAD は「データを変えない」メソッドとして、app/auth.py の Origin の
# 検査と「ヘッダーのないフォームの送信は断る」の対象から外れている。
# 今は、POST だけがログインを試す（app/routes/auth.py の login）


def test_head_request_cannot_log_in(app, anonymous_client):
    response = anonymous_client.open(
        "/login",
        method="HEAD",
        data={"login_id": TEST_USERNAME, "password": TEST_PASSWORD},
    )

    assert session_cookie_header(response) is None
    assert all_sessions(app) == []


def test_head_request_is_not_counted_as_login_failure(app, anonymous_client):
    for _ in range(3):
        anonymous_client.open("/login", method="HEAD")

    assert failure_count(app) == 0


# --- 受け入れた弱さ：1つの接続元で、持ち主を締め出し続けられる ---


@pytest.mark.xfail(
    strict=True,
    # 弱さの再現（assert の失敗）だけを「予想どおり」にする。ほかの
    # 例外（500 の応答での KeyError など）は、ふつうの失敗にする
    raises=AssertionError,
    reason=(
        "受け入れた弱さ：ログインIDごとの制限は、だれの失敗でも始まり、"
        "正しいパスワードも断る。IDを知っていれば、1つの接続元から1分に"
        "1回送るだけで、持ち主を締め出せる。今は、IDを推測されにくいものに"
        "する（rename-user。IDの有無は応答から分からない）ことで防ぐ。"
        "一度ログインした端末の印（device cookie）を足すかは、公開"
        "（Task 026）の前に決める（docs/roadmap.md の持ち越し）"
    ),
)
def test_one_address_cannot_keep_owner_locked_out(app, clock_now):
    # 攻撃の前に、持ち主は、いつもの端末で1回ログインしている
    owner = app.test_client()
    first = post_login(owner, TEST_USERNAME, TEST_PASSWORD, OWNER_ADDRESS)
    assert first.status_code == 303
    owner.post("/logout", headers=FORM_HEADERS)

    attacker = app.test_client()
    owner_results = []
    attacker_hashed_failures = 0
    # 6時間、攻撃者は1分に1回、間違ったパスワードを送る。持ち主は、
    # 30分ごとに、いつもの接続元から、正しいパスワードで試す
    for minute in range(6 * 60):
        clock_now.value = START + timedelta(minutes=minute)
        response = post_login(
            attacker, TEST_USERNAME, WRONG_PASSWORD, ATTACKER_ADDRESS
        )
        if response.status_code == 401:
            attacker_hashed_failures += 1
        if minute % 30 == 29:
            response = post_login(
                owner, TEST_USERNAME, TEST_PASSWORD, OWNER_ADDRESS
            )
            owner_results.append(response.status_code)
            if response.status_code == 303:
                owner.post("/logout", headers=FORM_HEADERS)

    # 攻撃者の360回の要求のうち、確かめられた（失敗に数えた）ものは
    # 少ない（断られた要求は数えられないため、送り続けても損がない）
    assert owner_results == [303] * len(owner_results), (
        f"持ち主の結果：{owner_results}、"
        f"攻撃者の失敗に数えた回数：{attacker_hashed_failures}"
    )


# --- 直した弱さ：ログインの失敗の記録に、索引がなかった ---
#
# 試行のたびに表を全部読み（20万行で1回約0.17秒、手元の計測）、その間、
# ほかのログインを ATTEMPT_LOCK で待たせていた。接続元を変えながら
# （IPv6 の /64 など）行を増やすと、持ち主のログインが遅くなった


@pytest.mark.parametrize("column", ["login_id_digest", "client_digest"])
def test_failure_lookups_use_an_index(app, column):
    # app/login_limits.py の count_failures と同じ形の問い合わせ
    with app.app_context():
        plan = db.session.execute(
            db.text(
                "EXPLAIN QUERY PLAN SELECT count(*) FROM login_failures "
                f"WHERE {column} = :digest AND failed_at > :since"
            ),
            {"digest": "0" * 64, "since": START.isoformat(sep=" ")},
        ).all()

    details = " ".join(str(row[-1]) for row in plan)
    assert "INDEX" in details, details


# --- 守り：IDの有無が、応答から分からない ---


def comparable(response) -> tuple:
    """応答の、状態・本文・ヘッダー（要求ごとに変わる nonce を除く）。"""
    headers = dict(response.headers)
    headers["Content-Security-Policy"] = re.sub(
        r"'nonce-[^']+'", "'nonce-?'", headers["Content-Security-Policy"]
    )
    return response.status_code, response.get_data(), headers


def test_every_kind_of_failure_has_identical_response(app, anonymous_client):
    # 状態コード・本文だけでなく、ヘッダー（Cookie を含む）も同じ
    create_user(app, "no-password", password=None)
    responses = [
        post_login(anonymous_client, TEST_USERNAME, WRONG_PASSWORD),
        post_login(anonymous_client, "no-such-user", TEST_PASSWORD),
        post_login(anonymous_client, "no-password", TEST_PASSWORD),
        post_login(anonymous_client, "Not A Valid ID", TEST_PASSWORD),
    ]

    first = comparable(responses[0])
    assert first[0] == 401
    for response in responses[1:]:
        assert comparable(response) == first
    assert all(session_cookie_header(r) is None for r in responses)


@pytest.mark.parametrize(
    "login_id", [TEST_USERNAME, "no-such-user", "no-password"]
)
def test_same_password_work_whether_or_not_id_exists(
    app, anonymous_client, monkeypatch, login_id
):
    # ID がある・ない・パスワードのない利用者で、同じ強さの scrypt を
    # 1回だけ計算する（かかる時間で、IDの有無を知られない）
    create_user(app, "no-password", password=None)
    hashes = []
    original = auth_routes.verify_password

    def record(password_hash, password):
        hashes.append(password_hash)
        return original(password_hash, password)

    monkeypatch.setattr(auth_routes, "verify_password", record)

    post_login(anonymous_client, login_id, WRONG_PASSWORD)

    assert len(hashes) == 1
    assert hashes[0].startswith(PASSWORD_HASH_METHOD + "$")


def test_password_matching_dummy_hash_never_logs_in(
    app, anonymous_client, monkeypatch
):
    # ダミーのハッシュのパスワードが、万一知られても、IDのない人・
    # パスワードのない利用者として、ログインできない
    create_user(app, "no-password", password=None)
    monkeypatch.setattr(
        auth_routes,
        "verify_password",
        lambda password_hash, password: password_hash == DUMMY_PASSWORD_HASH,
    )

    for login_id in ["no-password", "no-such-user"]:
        response = post_login(anonymous_client, login_id, "known dummy pass")
        assert response.status_code == 401
    assert all_sessions(app) == []


# --- 守り：トークン ---


def test_token_digest_from_database_cannot_be_used_as_cookie(app, client):
    # DBが漏れても、DBの値（SHA-256）からは、Cookie を作れない
    [row] = all_sessions(app)
    for forged in [row.token_digest, row.token_digest[:43]]:
        thief = app.test_client()
        thief.set_cookie(COOKIE_NAME, forged)
        assert thief.get("/api/semesters").status_code == 401


def test_login_never_adopts_a_token_planted_before_login(
    app, anonymous_client
):
    # 攻撃者が、ブラウザに仕込んだトークン（セッションの固定化）
    planted = "A" * 43
    anonymous_client.set_cookie(COOKIE_NAME, planted)

    response = post_login(anonymous_client, TEST_USERNAME, TEST_PASSWORD)

    assert cookie_value(response) != planted
    attacker = app.test_client()
    attacker.set_cookie(COOKIE_NAME, planted)
    assert attacker.get("/api/semesters").status_code == 401


# --- 守り：試行の制限 ---


def test_refused_attempts_compute_no_hashes(
    app, anonymous_client, clock_now, monkeypatch
):
    # 断っている間は、scrypt を計算しない（断られる要求を大量に送って、
    # CPUとメモリーを使わせることができない）
    for _ in range(5):
        post_login(anonymous_client, TEST_USERNAME, WRONG_PASSWORD)
    hashes = []
    monkeypatch.setattr(
        auth_routes,
        "verify_password",
        lambda password_hash, password: hashes.append(password_hash),
    )

    for _ in range(20):
        response = post_login(anonymous_client, TEST_USERNAME, TEST_PASSWORD)
        assert response.status_code == 429

    assert hashes == []
    assert failure_count(app) == 5


def test_attacker_own_success_does_not_reset_address_count(
    app, clock_now
):
    # 攻撃者が、自分のIDで成功しても、同じ接続元からの、ほかのIDへの失敗は
    # 消えない（接続元ごとの制限を、自分のログインで戻せない）
    create_user(app, "attacker-own")
    attacker = app.test_client()
    for index in range(9):
        post_login(
            attacker, f"guess-{index}", WRONG_PASSWORD, ATTACKER_ADDRESS
        )
    success = post_login(
        attacker, "attacker-own", TEST_PASSWORD, ATTACKER_ADDRESS
    )
    assert success.status_code == 303

    tenth = post_login(attacker, "guess-9", WRONG_PASSWORD, ATTACKER_ADDRESS)
    eleventh = post_login(
        attacker, TEST_USERNAME, TEST_PASSWORD, ATTACKER_ADDRESS
    )

    assert tenth.status_code == 401
    assert eleventh.status_code == 429


@pytest.mark.parametrize(
    "variant",
    [
        "2001:DB8:1:2::1",
        "2001:0db8:0001:0002:0000:0000:0000:0001",
        "2001:db8:1:2::1%eth0",
        "2001:db8:1:2:ffff:ffff:ffff:ffff",
    ],
)
def test_ipv6_spellings_share_one_address_count(variant):
    # 大文字・省略しない形・ゾーンID・/64 の中の別のアドレスは、同じ数え方
    assert client_key(variant) == client_key("2001:db8:1:2::1")


def test_huge_inputs_are_failures_without_hashing(
    app, anonymous_client, monkeypatch
):
    # 本文の上限（16KiB）より小さいが、決まり（IDは32文字、パスワードは
    # 512文字）より長い入力
    hashes = []
    monkeypatch.setattr(
        auth_routes,
        "verify_password",
        lambda password_hash, password: hashes.append(password_hash),
    )

    response = post_login(anonymous_client, "a" * 5_000, "b" * 5_000)
    long_password = post_login(anonymous_client, TEST_USERNAME, "c" * 10_000)

    assert response.status_code == 401
    assert long_password.status_code == 401
    assert hashes == []
    assert all_sessions(app) == []


# 直した弱さ：ログインの前の POST /login に、本文の大きさの上限が
# なかった（Werkzeug は、urlencoded の本文を、上限なしで、すべて
# メモリーに読む。MAX_FORM_MEMORY_SIZE は multipart にだけ効く）
def test_login_refuses_huge_body_before_reading_it(app, anonymous_client):
    response = post_login(anonymous_client, TEST_USERNAME, "c" * 5_000_000)

    assert response.status_code == 413
    # 本文を読む前に断るので、試行として記録しない
    assert failure_count(app) == 0


def chunked_login_environ(body: bytes) -> dict:
    """長さ（Content-Length）のない、chunked のログインの送信。"""
    builder = EnvironBuilder(
        path="/login",
        method="POST",
        headers=FORM_HEADERS,
        data=body,
        content_type="application/x-www-form-urlencoded",
    )
    environ = builder.get_environ()
    environ.pop("CONTENT_LENGTH", None)
    environ["HTTP_TRANSFER_ENCODING"] = "chunked"
    # 本文の終わりを、サーバーが知っている（Werkzeug の開発用サーバーが
    # chunked を受けたときと同じ）
    environ["wsgi.input_terminated"] = True
    environ["wsgi.input"] = io.BytesIO(body)
    return environ


# 直した弱さ：長さのない本文は、16KiB で黙って切られて読まれ、413 に
# ならなかった（切られたパスワードで、失敗として記録された）
@pytest.mark.parametrize("password", ["short", "c" * 5_000_000])
def test_login_refuses_body_without_length(app, anonymous_client, password):
    body = urlencode({"login_id": TEST_USERNAME, "password": password})

    response = anonymous_client.open(chunked_login_environ(body.encode()))

    assert response.status_code == 411
    # 読まずに断るので、試行として記録しない
    assert failure_count(app) == 0
    assert session_cookie_header(response) is None


# --- 守り：ほかのサイトからの要求 ---


@pytest.mark.parametrize("path", ["/login", "/logout", "/logout-all"])
def test_same_site_form_posts_are_forbidden(app, client, path):
    # 同じ「サイト」の別のサブドメイン（公開したときの、ほかの人の
    # サブドメインなど）からの送信も断る
    response = client.post(
        path,
        data={"login_id": TEST_USERNAME, "password": TEST_PASSWORD},
        headers={**CROSS_SITE_NAVIGATION, "Sec-Fetch-Site": "same-site"},
    )

    assert response.status_code == 403
    assert len(all_sessions(app)) == 1


@pytest.mark.parametrize(
    "method", ["HEAD", "OPTIONS", "PUT", "PATCH", "DELETE"]
)
def test_cross_site_api_requests_of_every_method_are_forbidden(
    client, method
):
    response = client.open(
        "/api/semesters", method=method, headers=CROSS_SITE_FETCH
    )

    assert response.status_code == 403


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_old_browser_writes_with_other_origin_are_forbidden(client, method):
    # Sec-Fetch-Site を付けない古いブラウザでも、Origin で断る
    response = client.open(
        "/api/semesters/1",
        method=method,
        json={"name": "乗っ取り"},
        headers={"Origin": "https://evil.example"},
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    "path_info", ["//api/semesters", "/api//semesters", "/api/semesters/"]
)
def test_cross_site_api_path_variants_are_forbidden(client, path_info):
    # パスの書き方を変えて、API でない（画面への移動として許す）と
    # 誤らせることはできない
    response = client.get(
        "/",
        headers=CROSS_SITE_NAVIGATION,
        environ_overrides={"PATH_INFO": path_info},
    )

    assert response.status_code == 403


# --- 守り：既定で拒否 ---


def test_only_login_page_and_static_files_are_public():
    # 公開するものを増やすときは、意図して、ここも変える
    assert PUBLIC_ENDPOINTS == {"auth.login", "static"}


def test_every_url_and_method_needs_login(app, anonymous_client):
    # API だけでなく、画面・ログアウトを含む、すべての URL×メソッド
    for rule in app.url_map.iter_rules():
        if rule.endpoint in PUBLIC_ENDPOINTS:
            continue
        url = re.sub(r"<[^>]+>", "1", rule.rule)
        for method in sorted(rule.methods):
            response = anonymous_client.open(
                url,
                method=method,
                json=None if method in ("GET", "HEAD") else {},
                headers=FORM_HEADERS,
            )
            if is_api_path(url):
                assert response.status_code == 401, (method, url)
            else:
                assert response.status_code == 303, (method, url)
                assert response.headers["Location"] == "/login"


@pytest.mark.parametrize(
    "path_info",
    [
        "//api/semesters",
        "/api//semesters",
        "/API/semesters",
        "/api/semesters/",
        "/Login/../api/semesters",
        "/static/../api/semesters",
        "/static//../../instance/app.db",
    ],
)
def test_path_variants_never_reach_data_when_logged_out(
    anonymous_client, path_info
):
    response = anonymous_client.get(
        "/", environ_overrides={"PATH_INFO": path_info}
    )

    assert response.status_code in (303, 401, 404), path_info
    assert b"[" != response.get_data()[:1]


@pytest.mark.parametrize(
    "path",
    [
        "/static/../run.py",
        "/static/%2e%2e/templates/index.html",
        "/static/..%2f..%2frun.py",
        "/static/js/../../templates/index.html",
        "/static/%2e%2e%2f%2e%2e%2fconfig.py",
    ],
)
def test_static_route_serves_nothing_outside_static(anonymous_client, path):
    response = anonymous_client.get(path)

    assert response.status_code == 404
    body = response.get_data(as_text=True)
    assert "import " not in body
    assert "{%" not in body


# --- 守り：断る応答・ログインの応答にも、ヘッダーが付く ---


# 応答の作り方（client：ログイン済み、anonymous：未ログイン）
def logged_out_api(client, anonymous, monkeypatch):
    return anonymous.get("/api/semesters")


def logged_out_page(client, anonymous, monkeypatch):
    return anonymous.get("/")


def cross_site_api(client, anonymous, monkeypatch):
    return client.get("/api/semesters", headers=CROSS_SITE_FETCH)


def cross_site_logout(client, anonymous, monkeypatch):
    return client.post("/logout", headers=CROSS_SITE_FETCH)


def failed_login(client, anonymous, monkeypatch):
    return post_login(anonymous, TEST_USERNAME, WRONG_PASSWORD)


def successful_login(client, anonymous, monkeypatch):
    return post_login(anonymous, TEST_USERNAME, TEST_PASSWORD)


def locked_login(client, anonymous, monkeypatch):
    for _ in range(5):
        post_login(anonymous, TEST_USERNAME, WRONG_PASSWORD)
    return post_login(anonymous, TEST_USERNAME, TEST_PASSWORD)


def busy_login(client, anonymous, monkeypatch):
    busy = threading.BoundedSemaphore(1)
    busy.acquire()
    monkeypatch.setattr(auth_routes, "PASSWORD_CHECK_SLOTS", busy)
    monkeypatch.setattr(auth_routes, "PASSWORD_CHECK_WAIT_SECONDS", 0)
    return post_login(anonymous, TEST_USERNAME, TEST_PASSWORD)


def logout_everywhere(client, anonymous, monkeypatch):
    return client.post("/logout-all", headers=FORM_HEADERS)


RESPONSE_KINDS = {
    "API 401": (logged_out_api, 401),
    "画面 303": (logged_out_page, 303),
    "API 403": (cross_site_api, 403),
    "画面 403": (cross_site_logout, 403),
    "ログイン 401": (failed_login, 401),
    "ログイン 303": (successful_login, 303),
    "ログイン 429": (locked_login, 429),
    "ログイン 503": (busy_login, 503),
    "ログアウト 303": (logout_everywhere, 303),
}


@pytest.mark.parametrize("kind", sorted(RESPONSE_KINDS))
def test_auth_responses_have_all_security_headers(
    client, anonymous_client, monkeypatch, clock_now, kind
):
    make_response, status = RESPONSE_KINDS[kind]

    response = make_response(client, anonymous_client, monkeypatch)

    assert response.status_code == status
    for name, value in SECURITY_HEADERS.items():
        assert response.headers.get(name) == value, name
    assert "frame-ancestors 'none'" in (
        response.headers["Content-Security-Policy"]
    )
    assert response.headers["Cache-Control"] == "no-store"


def test_failed_login_page_keeps_no_typed_values(anonymous_client):
    # 失敗の画面に、打ち込んだIDやパスワードを書き戻さない（画面の
    # キャッシュや、肩越しに見られることから守る）
    typed_id = "typed-login-id"
    response = post_login(anonymous_client, typed_id, "typed secret value")
    html = response.get_data(as_text=True)

    assert typed_id not in html
    assert "typed secret value" not in html


def test_session_count_in_menu_is_own_only(app, client):
    # 利用者のメニューの「ログイン中の端末の数」に、他人の端末を数えない
    other_id = create_user(app, "someone-else")
    with app.app_context():
        for _ in range(3):
            start_session(other_id)
        db.session.commit()

    html = client.get("/").get_data(as_text=True)

    assert "ログイン中の端末：1台" in html
