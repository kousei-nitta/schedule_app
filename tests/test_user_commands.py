"""利用者の管理のコマンド（app/cli.py。docs/development/database.md の
「利用者の管理」）のテスト。テストのDB（一時ディレクトリ）で動かす。

漏えいの確認は、インターネットにつながず、差し替えて確かめる。
"""
import urllib.error

import pytest

from app import cli, passwords
from app.extensions import db
from app.login_limits import keyed_digest
from app.models.login_failure import LoginFailure
from app.models.user import User
from app.models.user_session import UserSession
from app.passwords import BreachCheckError, verify_password
from tests.auth_support import (
    TEST_PASSWORD,
    TEST_USER_ID,
    TEST_USERNAME,
    log_in,
)

NEW_PASSWORD = "umi yama kawa sora 2099"
NEW_PASSWORD_INPUT = f"{NEW_PASSWORD}\n{NEW_PASSWORD}\n"


@pytest.fixture
def breach_results(monkeypatch):
    """漏えいの確認の結果を決める（既定は「漏えいしていない」）。"""
    result = {"value": False}

    def fake_check(password):
        if isinstance(result["value"], Exception):
            raise result["value"]
        return result["value"]

    monkeypatch.setattr(cli, "is_breached_password", fake_check)
    return result


def run(app, args, user_input=None):
    return app.test_cli_runner().invoke(args=args, input=user_input)


def find_user(app, username):
    with app.app_context():
        return db.session.scalar(
            db.select(User).where(User.username == username)
        )


def session_count(app, user_id=TEST_USER_ID):
    with app.app_context():
        return db.session.scalar(
            db.select(db.func.count())
            .select_from(UserSession)
            .where(UserSession.user_id == user_id)
        )


# --- create-user ---


def test_create_user(app, breach_results):
    result = run(app, ["create-user", "new-user"], NEW_PASSWORD_INPUT)

    assert result.exit_code == 0, result.output
    assert "利用者 new-user を作りました" in result.output
    user = find_user(app, "new-user")
    assert verify_password(user.password_hash, NEW_PASSWORD)
    # 入力したパスワードは、表示しない
    assert NEW_PASSWORD not in result.output


@pytest.mark.parametrize("username", ["Bad", "ab", "has space"])
def test_create_user_refuses_invalid_id(app, breach_results, username):
    result = run(app, ["create-user", username], NEW_PASSWORD_INPUT)

    assert result.exit_code == 1
    assert "半角英小文字" in result.output
    assert find_user(app, username) is None


def test_create_user_refuses_existing_id(app, breach_results):
    result = run(app, ["create-user", TEST_USERNAME], NEW_PASSWORD_INPUT)

    assert result.exit_code == 1
    assert "すでにいます" in result.output


def test_create_user_refuses_short_password(app, breach_results):
    result = run(
        app, ["create-user", "new-user"], "short pass\nshort pass\n"
    )

    assert result.exit_code == 1
    assert "15文字以上" in result.output
    assert find_user(app, "new-user") is None


def test_create_user_refuses_breached_password(app, breach_results):
    breach_results["value"] = True

    result = run(app, ["create-user", "new-user"], NEW_PASSWORD_INPUT)

    assert result.exit_code == 1
    assert "漏えいしたパスワードの一覧にあります" in result.output
    assert find_user(app, "new-user") is None


def test_create_user_stops_when_breach_check_is_unreachable(
    app, breach_results
):
    breach_results["value"] = BreachCheckError(
        "漏えいしたパスワードの確認ができませんでした"
    )

    result = run(app, ["create-user", "new-user"], NEW_PASSWORD_INPUT)

    assert result.exit_code == 1
    assert "--skip-breach-check" in result.output
    assert find_user(app, "new-user") is None


def test_skip_breach_check_does_not_connect(app, monkeypatch):
    def must_not_connect(request, timeout):
        raise urllib.error.URLError("つないではいけない")

    monkeypatch.setattr(
        passwords.urllib.request, "urlopen", must_not_connect
    )

    result = run(
        app,
        ["create-user", "new-user", "--skip-breach-check"],
        NEW_PASSWORD_INPUT,
    )

    assert result.exit_code == 0, result.output
    assert "確認を省きました" in result.output


def test_password_is_asked_twice(app, breach_results):
    result = run(
        app,
        ["create-user", "new-user"],
        f"{NEW_PASSWORD}\ndifferent password 2099\n" + NEW_PASSWORD_INPUT,
    )

    assert result.exit_code == 0, result.output
    assert verify_password(find_user(app, "new-user").password_hash,
                           NEW_PASSWORD)


# --- set-password ---


def test_set_password_logs_out_every_device(app, breach_results):
    log_in(app, app.test_client(), TEST_USER_ID)
    log_in(app, app.test_client(), TEST_USER_ID)

    result = run(app, ["set-password", TEST_USERNAME], NEW_PASSWORD_INPUT)

    assert result.exit_code == 0, result.output
    assert "2台を、ログアウトしました" in result.output
    user = find_user(app, TEST_USERNAME)
    assert verify_password(user.password_hash, NEW_PASSWORD)
    assert not verify_password(user.password_hash, TEST_PASSWORD)
    assert session_count(app) == 0


def test_set_password_for_owner_without_password(app, breach_results):
    with app.app_context():
        db.session.add(
            User(username="owner", password_hash=None,
                 created_at=find_user(app, TEST_USERNAME).created_at)
        )
        db.session.commit()

    result = run(app, ["set-password", "owner"], NEW_PASSWORD_INPUT)

    assert result.exit_code == 0, result.output
    assert verify_password(find_user(app, "owner").password_hash,
                           NEW_PASSWORD)


def test_set_password_refuses_unknown_user(app, breach_results):
    result = run(app, ["set-password", "no-such-user"], NEW_PASSWORD_INPUT)

    assert result.exit_code == 1
    assert "がいません" in result.output


def test_set_password_refuses_password_with_username(app, breach_results):
    password = f"{TEST_USERNAME} is my password"

    result = run(
        app, ["set-password", TEST_USERNAME], f"{password}\n{password}\n"
    )

    assert result.exit_code == 1
    assert "ログインIDを含めないでください" in result.output


# --- rename-user ---


def test_rename_user(app):
    result = run(app, ["rename-user", TEST_USERNAME, "hard-to-guess-42"])

    assert result.exit_code == 0, result.output
    assert find_user(app, TEST_USERNAME) is None
    assert find_user(app, "hard-to-guess-42").id == TEST_USER_ID


def test_rename_user_refuses_invalid_or_existing_id(app):
    invalid = run(app, ["rename-user", TEST_USERNAME, "Bad Name"])
    existing = run(app, ["rename-user", TEST_USERNAME, TEST_USERNAME])

    assert invalid.exit_code == 1
    assert existing.exit_code == 1
    assert find_user(app, TEST_USERNAME) is not None


# --- unlock-login ---


def test_unlock_login_deletes_failures_of_that_id(app):
    with app.app_context():
        for login_id in [TEST_USERNAME, TEST_USERNAME, "someone-else"]:
            now = find_user(app, TEST_USERNAME).created_at
            db.session.add(
                LoginFailure(
                    login_id_digest=keyed_digest("login_id", login_id),
                    client_digest=keyed_digest("client", "192.0.2.1"),
                    failed_at=now,
                    login_id_locked_until=now,
                    client_locked_until=now,
                )
            )
        db.session.commit()

    result = run(app, ["unlock-login", TEST_USERNAME])

    assert result.exit_code == 0, result.output
    assert "2件消しました" in result.output
    with app.app_context():
        assert db.session.scalar(
            db.select(db.func.count()).select_from(LoginFailure)
        ) == 1
