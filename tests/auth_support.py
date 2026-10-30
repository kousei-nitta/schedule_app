"""テストで使う、利用者とログインの準備（tests/conftest.py などから使う）。

- テストの利用者（id 1）は、fixture app が、テストごとのDBに作る
- fixture client は、テストの利用者でログインした状態（DBにログイン中の
  端末の行を作り、Cookie を入れる。ログインの画面は通らない。scrypt の
  計算を、テストごとにしないため）
- パスワードのハッシュは、テスト全体で1回だけ計算する
"""
from app import clock
from app.extensions import db
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
