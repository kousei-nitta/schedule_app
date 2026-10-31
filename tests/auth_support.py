"""テストで使う、利用者とログインの準備（tests/conftest.py などから使う）。

- テストの利用者（id 1）は、fixture app が、テストごとのDBに作る
- fixture client は、テストの利用者でログインした状態（DBにログイン中の
  端末の行を作り、Cookie を入れる。ログインの画面は通らない。scrypt の
  計算を、テストごとにしないため）
- パスワードのハッシュは、テスト全体で1回だけ計算する
- ログインの画面を通すテスト（tests/test_auth.py・test_attacks_auth.py）の
  補助（時計・ログインの送信・Cookie・失敗の記録の数）
"""
from datetime import datetime, timedelta

from app import clock
from app.extensions import db
from app.models.login_failure import LoginFailure
from app.models.user import User
from app.passwords import hash_password
from app.user_sessions import start_session

TEST_USER_ID = 1
TEST_USERNAME = "test-user"
OTHER_USERNAME = "other-user"
# E2Eの利用者のログインID（tests/e2e/。パスワードは TEST_PASSWORD）
E2E_USERNAME = "e2e-user"
# テスト専用の架空のパスワード（決まり：15文字以上、IDを含まない）
TEST_PASSWORD = "kumo sakura densha 2099"

# ログインの画面を通すテストの、時計の始まり（UTC。fixture clock_now）
START = datetime(2026, 10, 30, 3, 0, 0)
COOKIE_NAME = "schedule_session"
# 画面のフォームの送信に、ブラウザが付けるヘッダー（このアプリから）
FORM_HEADERS = {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}

# test_client が使う Host の名前（Cookie は、名前ごとに送られる）
COOKIE_DOMAINS = ["localhost", "127.0.0.1"]

_password_hashes: dict[str, str] = {}


def password_hash_for(password: str) -> str:
    """パスワードのハッシュ（同じパスワードは、1回だけ計算する）。"""
    if password not in _password_hashes:
        _password_hashes[password] = hash_password(password)
    return _password_hashes[password]


def create_user(app, username: str, password: str | None = TEST_PASSWORD):
    """利用者を作り、id を返す。password が None なら、パスワードなし。"""
    with app.app_context():
        user = User(
            username=username,
            password_hash=(
                None if password is None else password_hash_for(password)
            ),
            created_at=clock.utc_now(),
        )
        db.session.add(user)
        db.session.commit()
        return user.id


def log_in(app, client, user_id: int) -> str:
    """client を、その利用者でログインした状態にする。トークンを返す。"""
    with app.app_context():
        token = start_session(user_id)
        db.session.commit()
    for domain in COOKIE_DOMAINS:
        client.set_cookie(
            app.config["AUTH_COOKIE_NAME"], token, domain=domain
        )
    return token


def logged_in_client(app, user_id: int):
    """その利用者でログインした、新しい test_client。"""
    client = app.test_client()
    log_in(app, client, user_id)
    return client


class FakeClock:
    """テストで動かせる時計（UTC、タイムゾーンなし。fixture clock_now）。"""

    def __init__(self, start: datetime):
        self.value = start

    def __call__(self) -> datetime:
        return self.value

    def advance(self, **kwargs) -> None:
        self.value += timedelta(**kwargs)


def post_login(client, login_id, password, address=None, headers=None):
    """ログインの画面から送る（address は接続元のIPアドレス）。"""
    environ = {} if address is None else {"REMOTE_ADDR": address}
    return client.post(
        "/login",
        data={"login_id": login_id, "password": password},
        environ_base=environ,
        headers=FORM_HEADERS if headers is None else headers,
    )


def session_cookie_header(response) -> str | None:
    """応答の、ログインの Cookie の Set-Cookie（なければ None）。"""
    for header in response.headers.getlist("Set-Cookie"):
        if header.startswith(f"{COOKIE_NAME}="):
            return header
    return None


def cookie_value(response) -> str:
    """応答で入れた、ログインの Cookie の値（トークン）。"""
    header = session_cookie_header(response)
    assert header is not None
    return header.split(";", 1)[0].split("=", 1)[1]


def failure_count(app) -> int:
    """ログインの失敗の記録の数（すべての接続元・ID）。"""
    with app.app_context():
        return db.session.scalar(
            db.select(db.func.count()).select_from(LoginFailure)
        )
