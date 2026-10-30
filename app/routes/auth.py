"""ログイン・ログアウトの画面（docs/ui_ux.md の「ログイン」）。

処理の順序と理由は、docs/architecture/security.md の「ログイン」。
"""
import threading

from flask import Blueprint, Response, g, redirect, render_template
from flask import request, url_for

from app import clock
from app.auth import auth_logger, client_address, current_user
from app.extensions import db
from app.login_limits import (
    cancel_attempt,
    client_key,
    forget_failures,
    keyed_digest,
    remaining_minutes,
    reserve_attempt,
)
from app.models.user import User
from app.passwords import (
    MAX_PASSWORD_INPUT_LENGTH,
    is_valid_username,
    verify_password,
)
from app.user_sessions import (
    clear_session_cookie,
    end_all_sessions,
    set_session_cookie,
    start_session,
)

auth_bp = Blueprint("auth", __name__)

LOGIN_FAILED_MESSAGE = "ログインIDかパスワードが違います"
LOGIN_BUSY_MESSAGE = (
    "混み合っています。少し時間をおいて、もう一度お試しください"
)
LOGIN_LOCKED_MESSAGE = (
    "ログインの失敗が続いたため、しばらくログインできません。"
    "約{minutes}分後に、もう一度お試しください"
)

# ログインIDがない・パスワードのない利用者のときに、確かめに使う
# ハッシュ（だれのパスワードでもない、乱数の文字列のハッシュ）。
# IDがあるときと同じ計算をして、かかる時間から、IDの有無を
# 知られないようにする。方式は app/passwords.py と同じ
DUMMY_PASSWORD_HASH = (
    "scrypt:32768:8:3$RtKwXM6bprvmUkrs$"
    "78f207ac067383e74fcbc1122416d45a70a44ef765cbcc74c0ef29d058a2959e"
    "969ecd0743d17286330d20feda524798871b7c4d319e196d6b7caeaa3b71d7df"
)

# ログアウトのときに、ブラウザに残ったデータ（キャッシュ・保存領域）を
# 消してもらう
CLEAR_SITE_DATA = '"cache", "storage"'

# パスワードの確かめ（scrypt。1回に32MiBのメモリー）を、同時にいくつまで
# 行うか。ログインの前に重い計算をさせて、サーバーのメモリーやCPUを
# 使い切らせないため。空かなければ、待つ時間（秒）のあと、断る（503）
PASSWORD_CHECK_SLOTS = threading.BoundedSemaphore(2)
PASSWORD_CHECK_WAIT_SECONDS = 5


def render_login(
    error_message: str | None = None,
    status: int = 200,
    *,
    reload_once: bool = False,
) -> tuple[str, int]:
    return (
        render_template(
            "login.html",
            error_message=error_message,
            reload_once=reload_once,
        ),
        status,
    )


def opened_from_other_site() -> bool:
    """ほかのサイトのリンクから開いた（ページの移動）か。

    Cookie は SameSite=Strict のため、そのときは送られず、ログイン中でも
    ログインの画面になる。画面を1回だけ開き直すと（このアプリの中からの
    移動になる）、Cookie が送られ、ログイン中なら、そのまま使える。
    """
    return request.headers.get("Sec-Fetch-Site") in ("cross-site", "same-site")


def find_user_for_login(login_id: str) -> User | None:
    """ログインIDの利用者（形式が違う・いないときは None）。"""
    if not is_valid_username(login_id):
        return None
    return db.session.scalar(db.select(User).where(User.username == login_id))


def logged_out_response() -> Response:
    """ログアウトしたあとの応答（ログインの画面へ。Cookieとデータを消す）。"""
    response = redirect(url_for("auth.login"), code=303)
    clear_session_cookie(response)
    response.headers["Clear-Site-Data"] = CLEAR_SITE_DATA
    return response


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if current_user() is not None:
            return redirect("/", code=303)
        return render_login(reload_once=opened_from_other_site())
    return attempt_login()


def attempt_login():
    """ログインを試す（POST /login）。

    順序：①試行の制限を確かめ、先に失敗として記録する ②パスワードを
    確かめる（IDがあってもなくても、同じ計算をする）③合っていれば、
    記録を消し、新しいトークンで、ログイン中の端末を作る。
    決まりに合わないID（ありえないID）と、長すぎるパスワードは、計算せずに
    失敗にする（決まりは公開しているため、時間で分かっても、何も漏れない）。
    """
    login_id = request.form.get("login_id", "")
    password = request.form.get("password", "")
    now = clock.utc_now()
    login_id_digest = keyed_digest("login_id", login_id)
    client_digest = keyed_digest("client", client_key(request.remote_addr))

    failure, locked_until = reserve_attempt(
        login_id_digest, client_digest, now
    )
    if locked_until is not None:
        auth_logger.warning(
            "ログインを断りました（試行の制限。接続元：%s）",
            client_address(),
        )
        message = LOGIN_LOCKED_MESSAGE.format(
            minutes=remaining_minutes(locked_until, now)
        )
        return render_login(message, 429)

    password_matches = False
    if (
        is_valid_username(login_id)
        and len(password) <= MAX_PASSWORD_INPUT_LENGTH
    ):
        if not PASSWORD_CHECK_SLOTS.acquire(
            timeout=PASSWORD_CHECK_WAIT_SECONDS
        ):
            # 確かめなかったので、失敗に数えない
            cancel_attempt(failure)
            auth_logger.warning(
                "ログインを断りました（混雑。接続元：%s）", client_address()
            )
            return render_login(LOGIN_BUSY_MESSAGE, 503)
        try:
            user = find_user_for_login(login_id)
            if user is not None and user.password_hash is not None:
                password_matches = verify_password(
                    user.password_hash, password
                )
            else:
                verify_password(DUMMY_PASSWORD_HASH, password)
        finally:
            PASSWORD_CHECK_SLOTS.release()
    else:
        user = None

    if not password_matches:
        auth_logger.warning(
            "ログインに失敗しました（利用者：%s、接続元：%s）",
            user.id if user is not None else "不明なID",
            client_address(),
        )
        return render_login(LOGIN_FAILED_MESSAGE, 401)

    # 成功：この接続元からの、このIDの失敗の記録を消す。この端末の前の
    # ログインがあれば消し、新しいトークンにする（ログインの前に仕込まれた
    # トークンを、そのまま使わせない）
    forget_failures(login_id_digest, client_digest)
    if g.get("user_session") is not None:
        db.session.delete(g.user_session)
    token = start_session(user.id)
    db.session.commit()
    auth_logger.info(
        "ログインしました（利用者：%s、接続元：%s）",
        user.id,
        client_address(),
    )
    response = redirect("/", code=303)
    set_session_cookie(response, token)
    return response


@auth_bp.post("/logout")
def logout():
    """この端末だけ、ログアウトする。"""
    user_id = current_user().id
    db.session.delete(g.user_session)
    db.session.commit()
    auth_logger.info(
        "ログアウトしました（利用者：%s、接続元：%s）",
        user_id,
        client_address(),
    )
    return logged_out_response()


@auth_bp.post("/logout-all")
def logout_all():
    """すべての端末で、ログアウトする（スマホをなくしたときなど）。"""
    user_id = current_user().id
    count = end_all_sessions(user_id)
    db.session.commit()
    auth_logger.info(
        "すべての端末でログアウトしました（利用者：%s、%s台、接続元：%s）",
        user_id,
        count,
        client_address(),
    )
    return logged_out_response()
