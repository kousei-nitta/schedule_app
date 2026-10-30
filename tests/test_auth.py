"""ログイン（docs/architecture/security.md の「ログイン」）のテスト。

- 既定で拒否（ログインの画面と静的ファイルのほかは、ログインが要る）
- ログイン・ログアウト・ログイン中の端末の期限
- ログインの試行の制限
- ほかのサイトからの要求（Sec-Fetch-Site・Origin）
- ヘッダーとログ

時刻は、app/clock.py の utc_now を差し替えて決める（fixture clock_now）。
"""
import hashlib
import logging
import re
from datetime import datetime, timedelta

import pytest

from app import clock
from app.extensions import db
from app.login_limits import (
    CLIENT_LOCK_STEPS,
    CLIENT_WINDOW,
    LOGIN_ID_LOCK_STEPS,
    LOGIN_ID_WINDOW,
    client_key,
    keyed_digest,
    lock_time,
)
from app.models.login_failure import LoginFailure
from app.models.semester import Semester
from app.models.user_session import UserSession
from app.passwords import PASSWORD_HASH_METHOD
from app.routes import auth as auth_routes
from app.routes.auth import (
    DUMMY_PASSWORD_HASH,
    LOGIN_FAILED_MESSAGE,
)
from tests.auth_support import (
    OTHER_USERNAME,
    TEST_PASSWORD,
    TEST_USER_ID,
    TEST_USERNAME,
    create_user,
    log_in,
)

START = datetime(2026, 10, 30, 3, 0, 0)
COOKIE_NAME = "schedule_session"
OTHER_ADDRESS = "198.51.100.7"
# 画面のフォームの送信に、ブラウザが付けるヘッダー（このアプリから）
FORM_HEADERS = {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}

UNAUTHORIZED_BODY = {
    "error": {"code": "unauthorized", "message": "ログインしてください"}
}
FORBIDDEN_BODY = {
    "error": {
        "code": "forbidden",
        "message": "リクエストを受け付けられません",
    }
}
SEMESTER_PAYLOAD = {
    "name": "2099年度 前期",
    "start_date": "2099-04-06",
    "end_date": "2099-07-20",
}


class FakeClock:
    """テストで動かせる時計（UTC、タイムゾーンなし）。"""

    def __init__(self, start: datetime):
        self.value = start

    def __call__(self) -> datetime:
        return self.value

    def advance(self, **kwargs) -> None:
        self.value += timedelta(**kwargs)


@pytest.fixture
def clock_now(monkeypatch) -> FakeClock:
    fake = FakeClock(START)
    monkeypatch.setattr(clock, "utc_now", fake)
    return fake


def post_login(client, login_id, password, address=None, headers=None):
    environ = {} if address is None else {"REMOTE_ADDR": address}
    return client.post(
        "/login",
        data={"login_id": login_id, "password": password},
        environ_base=environ,
        headers=FORM_HEADERS if headers is None else headers,
    )


def session_cookie_header(response) -> str | None:
    for header in response.headers.getlist("Set-Cookie"):
        if header.startswith(f"{COOKIE_NAME}="):
            return header
    return None


def cookie_value(response) -> str:
    header = session_cookie_header(response)
    assert header is not None
    return header.split(";", 1)[0].split("=", 1)[1]


def session_rows(app, user_id=TEST_USER_ID) -> list[UserSession]:
    with app.app_context():
        return list(
            db.session.scalars(
                db.select(UserSession).where(UserSession.user_id == user_id)
            )
        )


def failure_count(app) -> int:
    with app.app_context():
        return db.session.scalar(
            db.select(db.func.count()).select_from(LoginFailure)
        )


def add_failures(app, login_id, address, times):
    """ログインの失敗の記録を、時刻を指定して足す。

    断る期限は、アプリ（app/login_limits.py の reserve_attempt）と同じ
    決め方で、その時点の数から決める（断っている間かどうかは見ない）。
    """
    with app.app_context():
        login_id_digest = keyed_digest("login_id", login_id)
        client_digest = keyed_digest("client", client_key(address))
        for failed_at in sorted(times):
            login_id_count = 1 + db.session.scalar(
                db.select(db.func.count())
                .select_from(LoginFailure)
                .where(
                    LoginFailure.login_id_digest == login_id_digest,
                    LoginFailure.failed_at > failed_at - LOGIN_ID_WINDOW,
                )
            )
            client_count = 1 + db.session.scalar(
                db.select(db.func.count())
                .select_from(LoginFailure)
                .where(
                    LoginFailure.client_digest == client_digest,
                    LoginFailure.failed_at > failed_at - CLIENT_WINDOW,
                )
            )
            db.session.add(
                LoginFailure(
                    login_id_digest=login_id_digest,
                    client_digest=client_digest,
                    failed_at=failed_at,
                    login_id_locked_until=failed_at
                    + lock_time(login_id_count, LOGIN_ID_LOCK_STEPS),
                    client_locked_until=failed_at
                    + lock_time(client_count, CLIENT_LOCK_STEPS),
                )
            )
            db.session.flush()
        db.session.commit()


def semester_count(app) -> int:
    with app.app_context():
        return db.session.scalar(
            db.select(db.func.count()).select_from(Semester)
        )


# --- 既定で拒否 ---


def test_page_redirects_to_login_when_logged_out(anonymous_client):
    response = anonymous_client.get("/")

    assert response.status_code == 303
    assert response.headers["Location"] == "/login"


def test_api_is_unauthorized_when_logged_out(anonymous_client):
    response = anonymous_client.get("/api/semesters")

    assert response.status_code == 401
    assert response.json == UNAUTHORIZED_BODY


@pytest.mark.parametrize(
    "path", ["/api/no-such-url", "/api", "/api/semesters/1"]
)
def test_unknown_api_url_is_unauthorized_when_logged_out(
    anonymous_client, path
):
    # どんなURLがあるかを、ログインの前に知らせない
    response = anonymous_client.get(path)

    assert response.status_code == 401
    assert response.json == UNAUTHORIZED_BODY


def test_unknown_page_redirects_to_login_when_logged_out(anonymous_client):
    response = anonymous_client.get("/no-such-page")

    assert response.status_code == 303
    assert response.headers["Location"] == "/login"


def test_unknown_page_is_404_when_logged_in(client):
    assert client.get("/no-such-page").status_code == 404


def test_login_page_is_public_and_has_no_scripts(anonymous_client):
    response = anonymous_client.get("/login")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="login-form"' in html
    # パスワードを入れる画面に、JavaScriptを読み込まない
    assert "<script" not in html
    assert 'autocomplete="username"' in html
    assert 'autocomplete="current-password"' in html


def test_static_file_is_public(anonymous_client):
    response = anonymous_client.get("/static/css/style.css")

    assert response.status_code == 200
    response.close()


def test_login_page_redirects_to_top_when_logged_in(client):
    response = client.get("/login")

    assert response.status_code == 303
    assert response.headers["Location"] == "/"


def test_logged_out_user_cannot_change_data(app, anonymous_client):
    response = anonymous_client.post("/api/semesters", json=SEMESTER_PAYLOAD)

    assert response.status_code == 401
    assert semester_count(app) == 0


def test_untrusted_host_is_still_bad_request_when_logged_out(
    anonymous_client,
):
    # 信頼しない Host は、ログインの確かめより先に、400 のまま
    response = anonymous_client.get(
        "/api/semesters", headers={"Host": "evil.example"}
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "bad_request"


# --- ログイン ---


def test_login_succeeds_and_sets_session_cookie(app, anonymous_client):
    response = post_login(anonymous_client, TEST_USERNAME, TEST_PASSWORD)

    assert response.status_code == 303
    assert response.headers["Location"] == "/"
    header = session_cookie_header(response)
    assert "HttpOnly" in header
    assert "SameSite=Strict" in header
    assert "Path=/" in header
    assert "Max-Age=2592000" in header
    # ローカル（HTTP）では Secure を付けない（設定。公開でオン）
    assert "Secure" not in header
    assert anonymous_client.get("/api/semesters").status_code == 200


def test_login_stores_only_token_digest(app, anonymous_client):
    response = post_login(anonymous_client, TEST_USERNAME, TEST_PASSWORD)
    token = cookie_value(response)

    [row] = session_rows(app)
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", token)
    assert row.token_digest == hashlib.sha256(token.encode()).hexdigest()
    assert row.token_digest != token


def test_login_replaces_previous_session_of_the_browser(app, client):
    # ログインの前に持っていたトークンは、ログインで消え、新しいものになる
    [old_row] = session_rows(app)

    response = post_login(client, TEST_USERNAME, TEST_PASSWORD)

    [new_row] = session_rows(app)
    new_token = cookie_value(response)
    assert new_row.token_digest != old_row.token_digest
    assert new_row.token_digest == (
        hashlib.sha256(new_token.encode()).hexdigest()
    )


def test_login_accepts_full_width_password(anonymous_client):
    # 入力の方法による違い（全角の英数字）は、NFKCで同じになる
    full_width = TEST_PASSWORD.translate(
        {code: code + 0xFEE0 for code in range(0x21, 0x7F)}
    )
    assert full_width != TEST_PASSWORD

    response = post_login(anonymous_client, TEST_USERNAME, full_width)

    assert response.status_code == 303


@pytest.mark.parametrize(
    "login_id, password",
    [
        (TEST_USERNAME, "wrong password for test"),
        ("no-such-user", TEST_PASSWORD),
        ("Invalid ID!", TEST_PASSWORD),
        ("", ""),
    ],
)
def test_failed_login_has_same_response(
    app, anonymous_client, login_id, password
):
    response = post_login(anonymous_client, login_id, password)

    assert response.status_code == 401
    assert LOGIN_FAILED_MESSAGE in response.get_data(as_text=True)
    assert session_cookie_header(response) is None
    assert session_rows(app) == []


def test_failed_login_bodies_do_not_reveal_whether_id_exists(
    anonymous_client,
):
    wrong_password = post_login(
        anonymous_client, TEST_USERNAME, "wrong password for test"
    )
    unknown_id = post_login(anonymous_client, "no-such-user", TEST_PASSWORD)

    assert wrong_password.get_data() == unknown_id.get_data()


def test_login_without_form_fields_is_a_failure(anonymous_client):
    response = anonymous_client.post("/login", data={}, headers=FORM_HEADERS)

    assert response.status_code == 401


@pytest.mark.parametrize(
    "variant", ["TEST-USER", " test-user", "test-user ", "ｔｅｓｔ-ｕｓｅｒ"]
)
def test_login_id_is_not_normalized(app, anonymous_client, variant):
    # 書き方を変えたIDは、別のIDで、ログインできない（総当たりの数え方の
    # 抜け道にならない）。決まりに合わないIDは、計算せずに失敗にする
    response = post_login(anonymous_client, variant, TEST_PASSWORD)

    assert response.status_code == 401
    assert session_rows(app) == []


def test_invalid_id_and_long_password_are_not_hashed(
    anonymous_client, monkeypatch
):
    checked = []
    monkeypatch.setattr(
        auth_routes,
        "verify_password",
        lambda password_hash, password: checked.append(password_hash),
    )

    post_login(anonymous_client, "Not Valid", TEST_PASSWORD)
    post_login(anonymous_client, TEST_USERNAME, "x" * 513)

    assert checked == []


def test_user_without_password_cannot_log_in(app, anonymous_client):
    create_user(app, "owner", password=None)

    response = post_login(anonymous_client, "owner", "")

    assert response.status_code == 401


def test_unknown_id_is_checked_against_dummy_hash(
    anonymous_client, monkeypatch
):
    # IDがなくても、同じ計算（scrypt）をする（時間で、IDの有無を
    # 知られないため）
    checked = []
    original = auth_routes.verify_password

    def record(password_hash, password):
        checked.append(password_hash)
        return original(password_hash, password)

    monkeypatch.setattr(auth_routes, "verify_password", record)

    post_login(anonymous_client, "no-such-user", TEST_PASSWORD)

    assert checked == [DUMMY_PASSWORD_HASH]


def test_dummy_hash_uses_same_method_as_real_hashes():
    assert DUMMY_PASSWORD_HASH.startswith(PASSWORD_HASH_METHOD + "$")


def test_failure_is_recorded_before_password_is_checked(
    app, anonymous_client, monkeypatch
):
    # 同時の試行で、数え漏れないよう、確かめる前に記録してある
    counts = []
    original = auth_routes.verify_password

    def record(password_hash, password):
        counts.append(failure_count(app))
        return original(password_hash, password)

    monkeypatch.setattr(auth_routes, "verify_password", record)

    post_login(anonymous_client, TEST_USERNAME, TEST_PASSWORD)

    assert counts == [1]
    assert failure_count(app) == 0


def test_failure_record_keeps_only_digests(app, anonymous_client):
    typed_id = "typed-login-id"

    post_login(anonymous_client, typed_id, "wrong password for test")

    with app.app_context():
        [failure] = db.session.scalars(db.select(LoginFailure)).all()
        assert failure.login_id_digest == keyed_digest("login_id", typed_id)
        assert failure.client_digest == keyed_digest(
            "client", "127.0.0.1"
        )
    assert re.fullmatch(r"[0-9a-f]{64}", failure.login_id_digest)
    assert typed_id not in failure.login_id_digest


# --- ログインの試行の制限 ---


@pytest.mark.parametrize(
    "count, expected",
    [
        (4, timedelta(0)),
        (5, timedelta(minutes=15)),
        (9, timedelta(minutes=15)),
        (10, timedelta(hours=1)),
        (19, timedelta(hours=1)),
        (20, timedelta(hours=24)),
        (21, timedelta(hours=24)),
    ],
)
def test_lock_time_steps(count, expected):
    assert lock_time(count, LOGIN_ID_LOCK_STEPS) == expected


def test_four_failures_do_not_lock(app, anonymous_client, clock_now):
    add_failures(app, TEST_USERNAME, "127.0.0.1", [START] * 4)

    response = post_login(anonymous_client, TEST_USERNAME, TEST_PASSWORD)

    assert response.status_code == 303


def test_five_failures_lock_even_correct_password(
    app, anonymous_client, clock_now
):
    add_failures(app, TEST_USERNAME, "127.0.0.1", [START] * 5)
    clock_now.advance(minutes=14, seconds=59)

    response = post_login(anonymous_client, TEST_USERNAME, TEST_PASSWORD)

    assert response.status_code == 429
    assert "約1分後" in response.get_data(as_text=True)
    assert session_rows(app) == []
    # 断った試行は、失敗に数えない
    assert failure_count(app) == 5


def test_lock_ends_after_fifteen_minutes(app, anonymous_client, clock_now):
    add_failures(app, TEST_USERNAME, "127.0.0.1", [START] * 5)
    clock_now.advance(minutes=15)

    response = post_login(anonymous_client, TEST_USERNAME, TEST_PASSWORD)

    assert response.status_code == 303


def test_login_id_lock_applies_from_any_address(
    app, anonymous_client, clock_now
):
    # 他人（ほかの接続元）の失敗でも、IDごとに断る（分散した総当たり）
    add_failures(app, TEST_USERNAME, OTHER_ADDRESS, [START] * 5)

    response = post_login(anonymous_client, TEST_USERNAME, TEST_PASSWORD)

    assert response.status_code == 429


@pytest.mark.parametrize(
    "count, waited, expected_status",
    [
        (10, timedelta(minutes=59), 429),
        (10, timedelta(hours=1), 303),
        (20, timedelta(hours=23, minutes=59), 429),
        (20, timedelta(hours=24), 303),
    ],
)
def test_longer_locks(
    app, anonymous_client, clock_now, count, waited, expected_status
):
    times = [START + timedelta(minutes=index) for index in range(count)]
    add_failures(app, TEST_USERNAME, OTHER_ADDRESS, times)
    clock_now.value = max(times) + waited

    response = post_login(anonymous_client, TEST_USERNAME, TEST_PASSWORD)

    assert response.status_code == expected_status


def test_failures_older_than_a_day_are_ignored_and_deleted(
    app, anonymous_client, clock_now
):
    add_failures(
        app, TEST_USERNAME, OTHER_ADDRESS, [START - timedelta(hours=25)] * 4
    )

    response = post_login(anonymous_client, TEST_USERNAME, TEST_PASSWORD)

    assert response.status_code == 303
    assert failure_count(app) == 0


def test_long_lock_is_kept_after_its_failures_leave_the_window(
    app, anonymous_client, clock_now
):
    # 11時間かけて20回失敗すると、20回目から24時間断る。1回目が24時間の
    # 窓から外れても、早く解けない
    times = [
        START + timedelta(minutes=35 * index) for index in range(20)
    ]
    add_failures(app, TEST_USERNAME, OTHER_ADDRESS, times)
    clock_now.value = max(times) + timedelta(hours=23, minutes=59)

    locked = post_login(anonymous_client, TEST_USERNAME, TEST_PASSWORD)
    clock_now.advance(minutes=1)
    unlocked = post_login(anonymous_client, TEST_USERNAME, TEST_PASSWORD)

    assert locked.status_code == 429
    assert unlocked.status_code == 303


def test_failure_rows_are_kept_while_their_lock_lasts(
    app, anonymous_client, clock_now
):
    times = [START + timedelta(minutes=index) for index in range(20)]
    add_failures(app, TEST_USERNAME, OTHER_ADDRESS, times)
    clock_now.value = max(times) + timedelta(hours=23)

    post_login(anonymous_client, "someone-else", "wrong password for test")

    # 24時間より古い行も、その行で始まった制限が続く間は、消さない
    assert failure_count(app) == 21


def test_unknown_id_is_locked_the_same_way(app, anonymous_client, clock_now):
    add_failures(app, "no-such-user", OTHER_ADDRESS, [START] * 5)

    response = post_login(anonymous_client, "no-such-user", TEST_PASSWORD)

    assert response.status_code == 429


def test_success_forgets_only_failures_from_the_same_address(
    app, anonymous_client, clock_now
):
    add_failures(app, TEST_USERNAME, "127.0.0.1", [START] * 2)
    add_failures(app, TEST_USERNAME, OTHER_ADDRESS, [START] * 2)

    response = post_login(anonymous_client, TEST_USERNAME, TEST_PASSWORD)

    assert response.status_code == 303
    # ほかの接続元の失敗（他人の試行かもしれない）は、残る
    assert failure_count(app) == 2


def test_address_lock_after_ten_failures_in_an_hour(
    app, anonymous_client, clock_now
):
    # 同じ接続元から、いろいろなIDを試す（IDごとの数には届かない）
    for index in range(10):
        add_failures(
            app, f"guess-{index}", OTHER_ADDRESS,
            [START + timedelta(seconds=index)],
        )
    clock_now.advance(minutes=59)

    locked = post_login(
        anonymous_client, TEST_USERNAME, TEST_PASSWORD, address=OTHER_ADDRESS
    )
    other_address = post_login(
        anonymous_client, TEST_USERNAME, TEST_PASSWORD
    )

    assert locked.status_code == 429
    assert other_address.status_code == 303


def test_address_lock_ends_after_an_hour(app, anonymous_client, clock_now):
    for index in range(10):
        add_failures(
            app, f"guess-{index}", OTHER_ADDRESS,
            [START + timedelta(seconds=index)],
        )
    clock_now.advance(hours=1, seconds=9)

    response = post_login(
        anonymous_client, TEST_USERNAME, TEST_PASSWORD, address=OTHER_ADDRESS
    )

    assert response.status_code == 303


@pytest.mark.parametrize(
    "first, second, same",
    [
        ("2001:db8:1:2:aaaa::1", "2001:db8:1:2:bbbb::2", True),
        ("2001:db8:1:2::1", "2001:db8:1:3::1", False),
        ("::ffff:192.0.2.1", "192.0.2.1", True),
        # IPv4 の人を、/64 で1つにまとめない
        ("::ffff:192.0.2.1", "::ffff:198.51.100.7", False),
        ("192.0.2.1", "192.0.2.2", False),
    ],
)
def test_client_key_groups_ipv6_by_64(first, second, same):
    assert (client_key(first) == client_key(second)) is same


@pytest.mark.parametrize("address", [None, "", "not an address"])
def test_client_key_without_readable_address(address):
    assert client_key(address) == "unknown"


def test_busy_password_checks_are_refused_without_counting(
    app, anonymous_client, monkeypatch
):
    # 確かめる枠が空かないときは、計算せずに断る（503）。失敗に数えない
    import threading

    busy = threading.BoundedSemaphore(1)
    busy.acquire()
    monkeypatch.setattr(auth_routes, "PASSWORD_CHECK_SLOTS", busy)
    monkeypatch.setattr(auth_routes, "PASSWORD_CHECK_WAIT_SECONDS", 0)

    response = post_login(anonymous_client, TEST_USERNAME, TEST_PASSWORD)

    assert response.status_code == 503
    assert failure_count(app) == 0


def test_simultaneous_attempts_are_counted_one_by_one(app):
    # 失敗が4回のIDに、同時に20件の試行が来ても、受け付けるのは1件だけ
    # （「断るかの判断」と「記録」を、1つずつ行う）
    import threading

    from app.login_limits import reserve_attempt

    add_failures(app, TEST_USERNAME, OTHER_ADDRESS, [START] * 4)
    results = []

    def attempt():
        with app.app_context():
            failure, until = reserve_attempt(
                keyed_digest("login_id", TEST_USERNAME),
                keyed_digest("client", OTHER_ADDRESS),
                START + timedelta(seconds=1),
            )
            results.append(failure is not None)
            db.session.remove()

    threads = [threading.Thread(target=attempt) for _ in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results.count(True) == 1
    assert failure_count(app) == 5


# --- ログイン中の端末の期限 ---


def make_session(app, client, clock_now, **age):
    """ログインして、時計を age だけ進める。"""
    log_in(app, client, TEST_USER_ID)
    clock_now.advance(**age)


def test_session_is_valid_just_before_idle_timeout(
    app, anonymous_client, clock_now
):
    make_session(
        app, anonymous_client, clock_now, days=13, hours=23, minutes=59
    )

    assert anonymous_client.get("/api/semesters").status_code == 200


def test_session_expires_after_fourteen_idle_days(
    app, anonymous_client, clock_now
):
    make_session(app, anonymous_client, clock_now, days=14)

    response = anonymous_client.get("/api/semesters")

    assert response.status_code == 401
    assert session_rows(app) == []
    # 使えない Cookie は、ブラウザから消す
    header = session_cookie_header(response)
    assert header is not None and "Max-Age=0" in header


def test_using_session_extends_idle_timeout(
    app, anonymous_client, clock_now
):
    make_session(app, anonymous_client, clock_now, days=10)
    assert anonymous_client.get("/api/semesters").status_code == 200

    clock_now.advance(days=10)

    assert anonymous_client.get("/api/semesters").status_code == 200


def test_session_expires_thirty_days_after_login_even_if_used(
    app, anonymous_client, clock_now
):
    log_in(app, anonymous_client, TEST_USER_ID)
    for _ in range(3):
        clock_now.advance(days=10)
        anonymous_client.get("/api/semesters")

    assert anonymous_client.get("/api/semesters").status_code == 401


def test_last_used_is_updated_at_most_hourly(
    app, anonymous_client, clock_now
):
    log_in(app, anonymous_client, TEST_USER_ID)
    clock_now.advance(minutes=59)
    anonymous_client.get("/api/semesters")
    [row] = session_rows(app)
    assert row.last_used_at == START

    clock_now.advance(minutes=1)
    anonymous_client.get("/api/semesters")

    [row] = session_rows(app)
    assert row.last_used_at == START + timedelta(hours=1)


@pytest.mark.parametrize(
    "token", ["short", "x" * 43 + "!", "a" * 43, "../" * 20]
)
def test_unknown_or_malformed_token_is_logged_out(
    app, anonymous_client, token
):
    anonymous_client.set_cookie(COOKIE_NAME, token)

    response = anonymous_client.get("/api/semesters")

    assert response.status_code == 401
    assert session_cookie_header(response) is not None


# --- ログアウト ---


def test_logout_ends_only_this_session(app, client):
    other_device = app.test_client()
    log_in(app, other_device, TEST_USER_ID)
    token = client.get_cookie(COOKIE_NAME, domain="localhost").value

    response = client.post("/logout", headers=FORM_HEADERS)

    assert response.status_code == 303
    assert response.headers["Location"] == "/login"
    assert response.headers["Clear-Site-Data"] == '"cache", "storage"'
    assert "Max-Age=0" in session_cookie_header(response)
    assert len(session_rows(app)) == 1
    # 盗まれたCookie（同じトークン）も、もう使えない
    stolen = app.test_client()
    stolen.set_cookie(COOKIE_NAME, token)
    assert stolen.get("/api/semesters").status_code == 401
    assert other_device.get("/api/semesters").status_code == 200


def test_logout_all_ends_every_session_of_the_user(app, client):
    other_device = app.test_client()
    log_in(app, other_device, TEST_USER_ID)
    other_user_id = create_user(app, OTHER_USERNAME)
    other_user = app.test_client()
    log_in(app, other_user, other_user_id)

    response = client.post("/logout-all", headers=FORM_HEADERS)

    assert response.status_code == 303
    assert response.headers["Clear-Site-Data"] == '"cache", "storage"'
    assert session_rows(app) == []
    assert other_device.get("/api/semesters").status_code == 401
    # ほかの利用者は、ログインしたまま
    assert other_user.get("/api/semesters").status_code == 200


def test_logout_needs_post(client):
    assert client.get("/logout").status_code == 405
    assert client.get("/logout-all").status_code == 405


def test_logout_when_logged_out_goes_to_login(anonymous_client):
    response = anonymous_client.post("/logout", headers=FORM_HEADERS)

    assert response.status_code == 303
    assert response.headers["Location"] == "/login"


def test_top_page_shows_user_and_session_count(app, client):
    other_device = app.test_client()
    log_in(app, other_device, TEST_USER_ID)

    html = client.get("/").get_data(as_text=True)

    assert f">{TEST_USERNAME}</button>" in html
    assert "ログイン中の端末：2台" in html


# --- ほかのサイトからの要求 ---


@pytest.mark.parametrize("site", ["cross-site", "same-site"])
def test_cross_site_api_write_is_forbidden(app, client, site):
    response = client.post(
        "/api/semesters",
        json=SEMESTER_PAYLOAD,
        headers={"Sec-Fetch-Site": site},
    )

    assert response.status_code == 403
    assert response.json == FORBIDDEN_BODY
    assert semester_count(app) == 0


def test_cross_site_api_read_is_forbidden(client):
    response = client.get(
        "/api/semesters",
        headers={
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Dest": "script",
        },
    )

    assert response.status_code == 403


def test_cross_site_api_navigation_is_forbidden(client):
    # API は、ほかのサイトのリンクから開かれても断る
    response = client.get(
        "/api/semesters",
        headers={
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Dest": "document",
        },
    )

    assert response.status_code == 403


@pytest.mark.parametrize("site", ["same-origin", "none"])
def test_same_origin_and_user_initiated_requests_are_allowed(
    app, client, site
):
    response = client.post(
        "/api/semesters",
        json=SEMESTER_PAYLOAD,
        headers={"Sec-Fetch-Site": site},
    )

    assert response.status_code == 201


def test_page_navigation_from_other_site_is_allowed(client):
    response = client.get(
        "/",
        headers={
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Dest": "document",
        },
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "mode, dest", [("no-cors", "image"), ("navigate", "iframe")]
)
def test_page_embedding_from_other_site_is_forbidden(client, mode, dest):
    response = client.get(
        "/",
        headers={
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": mode,
            "Sec-Fetch-Dest": dest,
        },
    )

    assert response.status_code == 403


def test_cross_site_login_is_forbidden(app, anonymous_client):
    # ほかのサイトから、攻撃者のIDでログインさせる攻撃（ログインのCSRF）
    response = post_login(
        anonymous_client,
        TEST_USERNAME,
        TEST_PASSWORD,
        headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate",
                 "Sec-Fetch-Dest": "document"},
    )

    assert response.status_code == 403
    assert session_rows(app) == []


@pytest.mark.parametrize("path", ["/login", "/logout", "/logout-all"])
def test_form_post_without_browser_headers_is_forbidden(app, client, path):
    # 今のブラウザは、フォームの送信に、Origin か Sec-Fetch-Site を必ず
    # 付ける。どちらもない画面のフォームの送信は、断る
    response = client.post(
        path, data={"login_id": TEST_USERNAME, "password": TEST_PASSWORD}
    )

    assert response.status_code == 403
    assert len(session_rows(app)) == 1


def test_cross_site_logout_is_forbidden(app, client):
    response = client.post(
        "/logout",
        headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate",
                 "Sec-Fetch-Dest": "document"},
    )

    assert response.status_code == 403
    assert len(session_rows(app)) == 1


@pytest.mark.parametrize(
    "origin", ["https://evil.example", "http://localhost.evil.example", "null"]
)
def test_write_with_other_origin_is_forbidden(app, client, origin):
    response = client.post(
        "/api/semesters", json=SEMESTER_PAYLOAD, headers={"Origin": origin}
    )

    assert response.status_code == 403
    assert semester_count(app) == 0


def test_write_with_own_origin_is_allowed(client):
    response = client.post(
        "/api/semesters",
        json=SEMESTER_PAYLOAD,
        headers={"Origin": "http://localhost"},
    )

    assert response.status_code == 201


def test_cross_site_rejection_is_logged_safely(client, caplog):
    with caplog.at_level(logging.WARNING, logger="app.auth"):
        client.post(
            "/api/semesters",
            json=SEMESTER_PAYLOAD,
            headers={
                "Sec-Fetch-Site": "cross-site",
                "Origin": "https://evil.example\tforged",
            },
        )

    assert "ほかのサイトからの要求を断りました" in caplog.text
    # 要求から来た値は、そのまま書かない（制御文字で、行を偽らせない）
    assert "'https://evil.example\\tforged'" in caplog.text


def test_untrusted_host_is_bad_request_for_every_entry(anonymous_client):
    for method, path in [("GET", "/"), ("GET", "/api/x"), ("POST", "/login")]:
        response = anonymous_client.open(
            path, method=method, headers={"Host": "evil.example"}
        )
        assert response.status_code == 400, (method, path)


def test_login_page_opened_from_other_site_reloads_once(anonymous_client):
    # Cookie（SameSite=Strict）が送られないため、1回だけ開き直す
    from_other_site = anonymous_client.get(
        "/login",
        headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate",
                 "Sec-Fetch-Dest": "document"},
    ).get_data(as_text=True)
    from_this_app = anonymous_client.get(
        "/login", headers={"Sec-Fetch-Site": "same-origin"}
    ).get_data(as_text=True)

    assert '<meta http-equiv="refresh" content="0">' in from_other_site
    assert "http-equiv" not in from_this_app


def test_login_page_allows_no_scripts(anonymous_client):
    policy = anonymous_client.get("/login").headers["Content-Security-Policy"]

    assert "script-src 'none'" in policy


def test_no_other_cookies_are_set(anonymous_client):
    # Flask の署名つきのセッション（session）は使わない
    response = post_login(anonymous_client, TEST_USERNAME, TEST_PASSWORD)
    page = anonymous_client.get("/")

    for current in (response, page):
        for header in current.headers.getlist("Set-Cookie"):
            assert header.startswith(f"{COOKIE_NAME}=")


# --- ヘッダー ---


@pytest.mark.parametrize("path", ["/", "/api/semesters", "/login"])
def test_personal_responses_are_not_stored(client, path):
    response = client.get(path)

    assert response.headers["Cache-Control"] == "no-store"


def test_static_files_may_be_cached(client):
    response = client.get("/static/css/style.css")

    assert response.headers.get("Cache-Control") != "no-store"
    response.close()


@pytest.mark.parametrize(
    "path", ["/", "/login", "/api/semesters", "/static/css/style.css"]
)
def test_isolation_headers_on_every_response(anonymous_client, path):
    response = anonymous_client.get(path)

    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"
    assert response.headers["Permissions-Policy"] == (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    )
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
    response.close()


# --- ログ ---


def test_logs_never_contain_passwords_tokens_or_typed_ids(
    app, anonymous_client, caplog
):
    typed_id = "mistyped-secret-id"
    with caplog.at_level(logging.INFO, logger="app.auth"):
        post_login(anonymous_client, typed_id, "wrong password for test")
        response = post_login(
            anonymous_client, TEST_USERNAME, TEST_PASSWORD
        )
        anonymous_client.post("/logout", headers=FORM_HEADERS)

    token = cookie_value(response)
    assert "ログインに失敗しました（利用者：不明なID" in caplog.text
    assert f"ログインしました（利用者：{TEST_USER_ID}" in caplog.text
    assert "ログアウトしました" in caplog.text
    for secret in [typed_id, TEST_PASSWORD, "wrong password", token]:
        assert secret not in caplog.text
