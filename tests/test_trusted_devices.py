"""一度ログインした端末の印（app/trusted_devices.py）と、全体の上限・
パスワードの確かめの枠（Task 026。ADR 0005）。

仕様は docs/architecture/security.md の「ログインの試行の制限」。
時刻は、app/clock.py の utc_now を差し替える（fixture clock_now）。
"""
import logging
import threading
from datetime import timedelta

import pytest

from app.extensions import db
from app.login_limits import GLOBAL_FAILURE_LIMIT
from app.models.trusted_device import TrustedDevice
from app.passwords import MAX_PASSWORD_INPUT_LENGTH
from app.routes import auth as auth_routes
from app.trusted_devices import (
    DEVICE_LIFETIME,
    MAX_DEVICE_FAILURES,
    MAX_DEVICES_PER_USER,
    reserve_device_attempt,
)
from app.user_sessions import token_digest
from tests.auth_support import (
    DEVICE_COOKIE_NAME,
    FORM_HEADERS,
    OTHER_USERNAME,
    START,
    TEST_PASSWORD,
    TEST_USER_ID,
    TEST_USERNAME,
    add_recent_failures,
    create_user,
    device_cookie_header,
    device_cookie_value,
    failure_count,
    post_login,
)

WRONG_PASSWORD = "wrong password for test"
ATTACKER_ADDRESS = "203.0.113.9"
OWNER_ADDRESS = "198.51.100.20"


def devices_of(app, user_id=TEST_USER_ID) -> list[TrustedDevice]:
    with app.app_context():
        return list(
            db.session.scalars(
                db.select(TrustedDevice)
                .where(TrustedDevice.user_id == user_id)
                .order_by(TrustedDevice.id)
            )
        )


def owner_with_device(app, clock_now):
    """持ち主が、いつもの端末で1回ログインし、ログアウトした client。

    client は、端末の印の Cookie を持っている。
    """
    owner = app.test_client()
    response = post_login(owner, TEST_USERNAME, TEST_PASSWORD, OWNER_ADDRESS)
    assert response.status_code == 303
    owner.post("/logout", headers=FORM_HEADERS)
    return owner


def lock_out(app, clock_now, login_id=TEST_USERNAME, failures=5):
    """攻撃者が、そのIDで失敗を重ね、IDごとの制限を始める。"""
    attacker = app.test_client()
    for _ in range(failures):
        post_login(attacker, login_id, WRONG_PASSWORD, ATTACKER_ADDRESS)
    locked = post_login(app.test_client(), login_id, TEST_PASSWORD)
    assert locked.status_code == 429


# --- 印を渡す・作り替える ---


def test_login_sets_device_cookie(app, anonymous_client, clock_now):
    response = post_login(anonymous_client, TEST_USERNAME, TEST_PASSWORD)

    header = device_cookie_header(response)
    assert header is not None
    attributes = header.split("; ")
    assert "HttpOnly" in attributes
    assert "SameSite=Strict" in attributes
    assert "Path=/" in attributes
    assert f"Max-Age={int(DEVICE_LIFETIME.total_seconds())}" in attributes
    assert not any(a.lower().startswith("domain=") for a in attributes)
    # DBには、印の SHA-256 だけ
    [device] = devices_of(app)
    assert device.token_digest == token_digest(device_cookie_value(response))
    assert device.failure_count == 0
    assert device.created_at == START


def test_each_login_replaces_the_device_token(app, clock_now):
    owner = owner_with_device(app, clock_now)
    [first] = devices_of(app)

    clock_now.advance(days=1)
    response = post_login(owner, TEST_USERNAME, TEST_PASSWORD, OWNER_ADDRESS)

    [second] = devices_of(app)
    assert second.token_digest == token_digest(device_cookie_value(response))
    assert second.token_digest != first.token_digest
    assert second.created_at == START + timedelta(days=1)


def test_devices_are_limited_per_user(app, clock_now):
    tokens = []
    for number in range(MAX_DEVICES_PER_USER + 2):
        clock_now.value = START + timedelta(minutes=number)
        response = post_login(
            app.test_client(), TEST_USERNAME, TEST_PASSWORD
        )
        tokens.append(token_digest(device_cookie_value(response)))

    remaining = {device.token_digest for device in devices_of(app)}
    assert remaining == set(tokens[-MAX_DEVICES_PER_USER:])


def test_unknown_device_cookie_is_ignored(app, anonymous_client, clock_now):
    anonymous_client.set_cookie(DEVICE_COOKIE_NAME, "x" * 43)

    response = post_login(anonymous_client, TEST_USERNAME, TEST_PASSWORD)

    assert response.status_code == 303


# --- 印のある道：制限の間もログインできる ---


def test_device_can_log_in_while_login_id_is_locked(app, clock_now):
    owner = owner_with_device(app, clock_now)
    lock_out(app, clock_now)

    response = post_login(owner, TEST_USERNAME, TEST_PASSWORD, OWNER_ADDRESS)

    assert response.status_code == 303


def test_device_can_log_in_while_its_address_is_locked(app, clock_now):
    owner = owner_with_device(app, clock_now)
    # 同じ接続元（大学の Wi-Fi など）から、ほかの人が10回失敗した
    other = app.test_client()
    for number in range(10):
        post_login(other, f"someone-{number}", WRONG_PASSWORD, OWNER_ADDRESS)
    assert post_login(
        app.test_client(), TEST_USERNAME, TEST_PASSWORD, OWNER_ADDRESS
    ).status_code == 429

    response = post_login(owner, TEST_USERNAME, TEST_PASSWORD, OWNER_ADDRESS)

    assert response.status_code == 303


def test_expired_device_does_not_bypass_limits(app, clock_now):
    owner = owner_with_device(app, clock_now)
    clock_now.advance(seconds=DEVICE_LIFETIME.total_seconds())
    lock_out(app, clock_now)

    response = post_login(owner, TEST_USERNAME, TEST_PASSWORD, OWNER_ADDRESS)

    assert response.status_code == 429


def test_device_of_another_user_does_not_bypass_limits(app, clock_now):
    create_user(app, OTHER_USERNAME)
    other = app.test_client()
    assert post_login(other, OTHER_USERNAME, TEST_PASSWORD).status_code == 303
    other.post("/logout", headers=FORM_HEADERS)
    lock_out(app, clock_now)

    # ほかの利用者の印を持って、持ち主のIDで試す
    response = post_login(other, TEST_USERNAME, TEST_PASSWORD)

    assert response.status_code == 429


@pytest.mark.parametrize("typed", ["TEST-USER", " test-user", "test-user "])
def test_device_needs_exactly_the_same_login_id(app, clock_now, typed):
    owner = owner_with_device(app, clock_now)
    lock_out(app, clock_now, login_id=typed)

    response = post_login(owner, typed, TEST_PASSWORD, OWNER_ADDRESS)

    assert response.status_code == 429


def test_device_of_user_without_password_is_not_trusted(app, clock_now):
    owner = owner_with_device(app, clock_now)
    with app.app_context():
        user = db.session.get(auth_routes.User, TEST_USER_ID)
        user.password_hash = None
        db.session.commit()
    lock_out(app, clock_now)

    response = post_login(owner, TEST_USERNAME, TEST_PASSWORD, OWNER_ADDRESS)

    assert response.status_code == 429


# --- 印ごとの失敗の数 ---


def test_device_failures_are_not_recorded_as_login_failures(app, clock_now):
    owner = owner_with_device(app, clock_now)

    response = post_login(owner, TEST_USERNAME, WRONG_PASSWORD, OWNER_ADDRESS)

    assert response.status_code == 401
    assert failure_count(app) == 0
    [device] = devices_of(app)
    assert device.failure_count == 1


def test_device_is_disabled_after_failures(app, clock_now, caplog):
    owner = owner_with_device(app, clock_now)

    with caplog.at_level(logging.WARNING, logger="app.auth"):
        for _ in range(MAX_DEVICE_FAILURES):
            response = post_login(
                owner, TEST_USERNAME, WRONG_PASSWORD, OWNER_ADDRESS
            )
            assert response.status_code == 401

    assert devices_of(app) == []
    assert "端末の印を、続けての失敗で無効にしました" in caplog.text
    # 以後は、印のない道（失敗が記録される）
    post_login(owner, TEST_USERNAME, WRONG_PASSWORD, OWNER_ADDRESS)
    assert failure_count(app) == 1


def test_device_is_disabled_after_too_long_passwords(app, clock_now, caplog):
    # 長すぎるパスワードは、確かめずに失敗にする（利用者を読まない）。
    # 印のある道では、それでも、印の持ち主でログに残し、5回で無効にする
    # （別の目のレビューで、5回目が500になることが分かった）
    owner = owner_with_device(app, clock_now)
    too_long = "a" * (MAX_PASSWORD_INPUT_LENGTH + 1)

    with caplog.at_level(logging.WARNING, logger="app.auth"):
        for _ in range(MAX_DEVICE_FAILURES):
            response = post_login(
                owner, TEST_USERNAME, too_long, OWNER_ADDRESS
            )
            assert response.status_code == 401

    assert devices_of(app) == []
    assert (
        "端末の印を、続けての失敗で無効にしました"
        f"（利用者：{TEST_USER_ID}、" in caplog.text
    )
    assert "不明なID" not in caplog.text


def test_device_with_other_login_ids_is_used_up(app, clock_now, caplog):
    # 有効な印が、持ち主と違うIDと一緒に届いたら、印のない道で扱い、
    # 印の失敗にも数える（盗まれた印で、持ち主のIDを探るのは、5回まで。
    # 攻撃のテストで見つけた）
    owner = owner_with_device(app, clock_now)

    with caplog.at_level(logging.WARNING, logger="app.auth"):
        for number in range(MAX_DEVICE_FAILURES):
            response = post_login(
                owner, f"guess-{number}", WRONG_PASSWORD, OWNER_ADDRESS
            )
            assert response.status_code == 401

    assert devices_of(app) == []
    assert "端末の印を、続けての失敗で無効にしました" in caplog.text
    # 印のない道でも扱ったので、ふつうの失敗としても記録された
    assert failure_count(app) == MAX_DEVICE_FAILURES


def test_success_resets_device_failures(app, clock_now):
    owner = owner_with_device(app, clock_now)
    for _ in range(MAX_DEVICE_FAILURES - 1):
        post_login(owner, TEST_USERNAME, WRONG_PASSWORD, OWNER_ADDRESS)

    response = post_login(owner, TEST_USERNAME, TEST_PASSWORD, OWNER_ADDRESS)

    assert response.status_code == 303
    [device] = devices_of(app)
    assert device.failure_count == 0


def test_reservation_never_exceeds_the_limit(app, clock_now):
    # 同時に送られた試行でも、上限を超えて数えない（1つの UPDATE 文）
    owner_with_device(app, clock_now)
    [device] = devices_of(app)
    with app.app_context():
        db.session.execute(
            db.update(TrustedDevice).values(
                failure_count=MAX_DEVICE_FAILURES - 1
            )
        )
        db.session.commit()

        first = reserve_device_attempt(device.id, START)
        second = reserve_device_attempt(device.id, START)

    assert (first, second) == (True, False)


def test_concurrent_wrong_passwords_are_limited(
    app, clock_now, caplog, monkeypatch
):
    # 本物のスレッドで、同時に送る（印ごとの上限を超えて試せない）。
    # 遅い環境でも、枠の待ちで503にならないよう、待つ時間を長くする
    monkeypatch.setattr(auth_routes, "PASSWORD_CHECK_WAIT_SECONDS", 60)
    owner = owner_with_device(app, clock_now)
    token = owner.get_cookie(DEVICE_COOKIE_NAME).value
    results = []

    def attempt():
        client = app.test_client()
        client.set_cookie(DEVICE_COOKIE_NAME, token)
        response = post_login(
            client, TEST_USERNAME, WRONG_PASSWORD, ATTACKER_ADDRESS
        )
        results.append(response.status_code)

    threads = [threading.Thread(target=attempt) for _ in range(12)]
    with caplog.at_level(logging.WARNING, logger="app.auth"):
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    assert len(results) == 12
    assert devices_of(app) == []
    # 印のある道で確かめたのは、上限の数まで。残りは、印のない道
    # （IDごとの制限で、やがて断られる）
    trusted_failures = caplog.text.count(
        f"ログインに失敗しました（利用者：{TEST_USER_ID}、印のある端末"
    )
    assert trusted_failures == MAX_DEVICE_FAILURES


# --- 印を消すとき ---


def test_logout_keeps_the_device(app, clock_now):
    owner = app.test_client()
    post_login(owner, TEST_USERNAME, TEST_PASSWORD, OWNER_ADDRESS)

    response = owner.post("/logout", headers=FORM_HEADERS)

    assert device_cookie_header(response) is None
    assert len(devices_of(app)) == 1


def test_logout_all_removes_devices_and_cookie(app, clock_now):
    other_device = app.test_client()
    post_login(other_device, TEST_USERNAME, TEST_PASSWORD)
    owner = app.test_client()
    post_login(owner, TEST_USERNAME, TEST_PASSWORD, OWNER_ADDRESS)
    assert len(devices_of(app)) == 2

    response = owner.post("/logout-all", headers=FORM_HEADERS)

    assert devices_of(app) == []
    header = device_cookie_header(response)
    assert header is not None and "Max-Age=0" in header


def test_set_password_removes_devices(app, clock_now, monkeypatch):
    owner_with_device(app, clock_now)
    monkeypatch.setattr(
        "app.cli.is_breached_password", lambda password: False
    )

    result = app.test_cli_runner().invoke(
        args=["set-password", TEST_USERNAME],
        input="another long password 77\nanother long password 77\n",
    )

    assert result.exit_code == 0, result.output
    assert devices_of(app) == []


# --- 全体の上限 ---


def test_global_limit_refuses_without_recording(app, clock_now, caplog):
    add_recent_failures(
        app, GLOBAL_FAILURE_LIMIT, START - timedelta(minutes=59)
    )

    with caplog.at_level(logging.WARNING, logger="app.auth"):
        response = post_login(
            app.test_client(), TEST_USERNAME, TEST_PASSWORD
        )

    assert response.status_code == 503
    assert failure_count(app) == GLOBAL_FAILURE_LIMIT
    assert "全体の上限" in caplog.text


def test_below_global_limit_is_accepted(app, clock_now):
    add_recent_failures(
        app, GLOBAL_FAILURE_LIMIT - 1, START - timedelta(minutes=59)
    )
    # 1時間より前の失敗は、数えない
    add_recent_failures(app, 10, START - timedelta(hours=1))

    response = post_login(app.test_client(), TEST_USERNAME, TEST_PASSWORD)

    assert response.status_code == 303


def test_device_can_log_in_over_global_limit(app, clock_now):
    owner = owner_with_device(app, clock_now)
    add_recent_failures(app, GLOBAL_FAILURE_LIMIT, START)

    response = post_login(owner, TEST_USERNAME, TEST_PASSWORD, OWNER_ADDRESS)

    assert response.status_code == 303


# --- パスワードの確かめの枠 ---


def test_device_has_its_own_password_check_slot(app, clock_now, monkeypatch):
    owner = owner_with_device(app, clock_now)
    # 印のない道の枠が、ふさがっている
    busy = threading.BoundedSemaphore(1)
    busy.acquire()
    monkeypatch.setattr(auth_routes, "PASSWORD_CHECK_SLOTS", busy)
    monkeypatch.setattr(auth_routes, "PASSWORD_CHECK_WAIT_SECONDS", 0)

    refused = post_login(app.test_client(), TEST_USERNAME, TEST_PASSWORD)
    accepted = post_login(owner, TEST_USERNAME, TEST_PASSWORD, OWNER_ADDRESS)

    assert refused.status_code == 503
    assert accepted.status_code == 303


def test_busy_device_slot_does_not_count_a_failure(
    app, clock_now, monkeypatch
):
    owner = owner_with_device(app, clock_now)
    busy = threading.BoundedSemaphore(1)
    busy.acquire()
    monkeypatch.setattr(auth_routes, "TRUSTED_PASSWORD_CHECK_SLOTS", busy)
    monkeypatch.setattr(auth_routes, "PASSWORD_CHECK_WAIT_SECONDS", 0)

    response = post_login(owner, TEST_USERNAME, WRONG_PASSWORD, OWNER_ADDRESS)

    assert response.status_code == 503
    [device] = devices_of(app)
    assert device.failure_count == 0
