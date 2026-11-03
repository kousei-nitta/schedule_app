"""ログイン・ログアウトの画面（docs/ui_ux.md の「ログイン」）。

処理の順序と理由は、docs/architecture/security.md の「ログイン」。
"""
import math
import threading

from flask import Blueprint, Response, abort, current_app, g, redirect
from flask import render_template, request, url_for

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
    too_many_recent_failures,
)
from app.models.user import User
from app.passwords import (
    MAX_PASSWORD_INPUT_LENGTH,
    is_valid_username,
    verify_password,
)
from app.trusted_devices import (
    cancel_device_attempt,
    clear_device_cookie,
    end_all_devices,
    find_trusted_device,
    forget_device_token,
    issue_device_token,
    remove_device_if_exhausted,
    reserve_device_attempt,
    set_device_cookie,
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
    "{wait}後に、もう一度お試しください"
)

# ログインの送信の本文の大きさの上限（バイト）。IDは32文字、パスワードは
# 512文字（正規化の前）までしか使わないため、それより十分に大きく、
# 決まりに合う入力を断らない大きさ（1文字4バイト×URLの形で3倍でも足りる）。
# ログインの前に、大きな本文を読ませて、メモリーを使わせないため。
# 超えたら、本文を読まずに、413（長さのない本文は、411）
LOGIN_MAX_CONTENT_LENGTH = 16 * 1024

# ログインIDがない・パスワードのない利用者のときに、確かめに使う
# ハッシュ（だれのパスワードでもない、乱数の文字列のハッシュ）。
# IDがあるときと同じ計算をして、かかる時間から、IDの有無を
# 知られないようにする。方式は app/passwords.py と同じ
DUMMY_PASSWORD_HASH = (
    "scrypt:32768:8:3$RtKwXM6bprvmUkrs$"
    "78f207ac067383e74fcbc1122416d45a70a44ef765cbcc74c0ef29d058a2959e"
    "969ecd0743d17286330d20feda524798871b7c4d319e196d6b7caeaa3b71d7df"
)

# ログアウトのときに、ブラウザに残ったデータ（保存領域）を消してもらう。
# "cache" は付けない：Chrome では、"cache" を付けると、ほかのサイトの
# キャッシュが多いほど、ログインの画面に移るまで遅くなる（測った値：
# 約200MBで約1秒、約600MBで約1.5秒。付けないと約0.15秒。このアプリの
# 分を探すために、キャッシュの全体を調べるためと考えられる）。個人の
# データを含む応答は、もともと保存させない（Cache-Control: no-store。
# app/security.py）ため、このアプリのキャッシュに残るのは、静的
# ファイル（個人のデータを含まない）だけ
CLEAR_SITE_DATA = '"storage"'

# パスワードの確かめ（scrypt。1回に32MiBのメモリー）を、同時にいくつまで
# 行うか。ログインの前に重い計算をさせて、サーバーのメモリーやCPUを
# 使い切らせないため。空かなければ、待つ時間（秒）のあと、断る（503）。
# 印のない端末の道と、印のある端末の道（app/trusted_devices.py）で、
# 別に1つずつ持つ（合わせて2つ）。多くの接続元から、印のない道を
# ふさがれても、本人の端末（印のある道）は、ログインできるように
PASSWORD_CHECK_SLOTS = threading.BoundedSemaphore(1)
TRUSTED_PASSWORD_CHECK_SLOTS = threading.BoundedSemaphore(1)
PASSWORD_CHECK_WAIT_SECONDS = 5


def wait_text(minutes: int) -> str:
    """断っている残りの時間の書き方（60分以上は、時間で）。"""
    if minutes >= 60:
        return f"約{math.ceil(minutes / 60)}時間"
    return f"約{minutes}分"


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
    開き直したURLには reloaded を付け、2回目は開き直さない（ブラウザの
    違いで、開き直しが続かないように）。
    """
    if "reloaded" in request.args:
        return False
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
    # ログインを試すのは、POST だけ（Flask は HEAD も、この route で
    # 受けるため、「GET でなければ」としない。HEAD は画面を返すだけ）
    if request.method == "POST":
        return attempt_login()
    if current_user() is not None:
        return redirect("/", code=303)
    return render_login(reload_once=opened_from_other_site())


def remove_exhausted_device(device_id: int, user_id: int) -> None:
    """印の失敗が上限に達していれば、印を消し、ログに残す。

    印で続けて失敗した。印が盗まれ、パスワードやIDを試されているかも
    しれない。この印は、もう使えない。
    """
    if remove_device_if_exhausted(device_id):
        auth_logger.warning(
            "端末の印を、続けての失敗で無効にしました"
            "（利用者：%s、接続元：%r）",
            user_id,
            client_address(),
        )


def attempt_login():
    """ログインを試す（POST /login）。

    2つの道がある（docs/architecture/security.md の「ログインの試行の制限」）。
    - 印のある道：この端末に、打ち込まれたIDの利用者の、有効な印がある。
      IDごと・接続元ごとの制限と、全体の上限を当てない。パスワードを
      確かめる前に、印の失敗の数を、先に1つ増やす
    - 印のない道（ふつう）：全体の上限 → 試行の制限を確かめ、先に失敗と
      して記録する
    そのあと、パスワードを確かめる（IDがあってもなくても、同じ計算をする）。
    合っていれば、記録を消し、新しいトークンでログイン中の端末を作り、
    印を作り替える。
    決まりに合わないID（ありえないID）と、長すぎるパスワードは、計算せずに
    失敗にする（決まりは公開しているため、時間で分かっても、何も漏れない）。
    """
    # 本文の長さ（Content-Length）のない送信（chunked）は、読まずに断る
    # （411）。長さがないと、Werkzeug は、上限を超えた本文を断らずに、
    # 上限で切って読む（資料の「超えたら413」にならない）。ブラウザの
    # フォームの送信には、いつも長さが付く
    if request.content_length is None:
        abort(411)
    # 本文を読む前に、大きさの上限を決める（超えたら413。読まない）
    request.max_content_length = LOGIN_MAX_CONTENT_LENGTH
    login_id = request.form.get("login_id", "")
    password = request.form.get("password", "")
    now = clock.utc_now()
    login_id_digest = keyed_digest("login_id", login_id)
    client_digest = keyed_digest("client", client_key(request.remote_addr))
    device_token = request.cookies.get(
        current_app.config["DEVICE_COOKIE_NAME"]
    )

    device = find_trusted_device(device_token, login_id, now)
    if device is not None and not device.login_id_matches:
        # 有効な印が、持ち主と違うIDと一緒に届いた（打ち間違い、または
        # 盗まれた印）。印のない道で扱うが、印の失敗にも数える（印の
        # ある道とそうでない道の応答の違いから、持ち主のIDを探らせない。
        # 試せる候補は、印の5回まで）
        if reserve_device_attempt(device.device_id, now):
            remove_exhausted_device(device.device_id, device.user_id)
        device = None
    trusted = device is not None and reserve_device_attempt(
        device.device_id, now
    )
    failure = None
    if trusted:
        slots = TRUSTED_PASSWORD_CHECK_SLOTS
    else:
        if too_many_recent_failures(now):
            # 記録も計算もしない（失敗の行と、CPUを使わせない）
            auth_logger.warning(
                "ログインを断りました（失敗が多いため、全体の上限。"
                "接続元：%r）",
                client_address(),
            )
            return render_login(LOGIN_BUSY_MESSAGE, 503)
        failure, locked_until = reserve_attempt(
            login_id_digest, client_digest, now
        )
        if locked_until is not None:
            auth_logger.warning(
                "ログインを断りました（試行の制限。接続元：%r）",
                client_address(),
            )
            message = LOGIN_LOCKED_MESSAGE.format(
                wait=wait_text(remaining_minutes(locked_until, now))
            )
            return render_login(message, 429)
        slots = PASSWORD_CHECK_SLOTS

    # 利用者と、パスワードが合ったか。決まりに合わない入力は、確かめずに
    # 失敗のまま（印のある道は、IDが印の持ち主と一致したので、決まりに合う）
    user = None
    password_matches = False
    if (
        is_valid_username(login_id)
        and len(password) <= MAX_PASSWORD_INPUT_LENGTH
    ):
        if not slots.acquire(timeout=PASSWORD_CHECK_WAIT_SECONDS):
            # 確かめなかったので、失敗に数えない
            if trusted:
                cancel_device_attempt(device.device_id)
            else:
                cancel_attempt(failure)
            auth_logger.warning(
                "ログインを断りました（混雑。接続元：%r）", client_address()
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
            slots.release()

    path_text = "印のある端末" if trusted else "印のない端末"
    if not password_matches:
        # ログに出す利用者。印のある道では、長すぎるパスワードで確かめを
        # 飛ばしても（user が None）、印の持ち主が分かっている
        if trusted:
            user_text = device.user_id
        elif user is not None:
            user_text = user.id
        else:
            user_text = "不明なID"
        auth_logger.warning(
            "ログインに失敗しました（利用者：%s、%s、接続元：%r）",
            user_text,
            path_text,
            client_address(),
        )
        if trusted:
            remove_exhausted_device(device.device_id, device.user_id)
        return render_login(LOGIN_FAILED_MESSAGE, 401)

    # 成功：印のない道では、この接続元からの、このIDの失敗の記録を消す。
    # この端末の前のログインがあれば消し、新しいトークンにする（ログインの
    # 前に仕込まれたトークンを、そのまま使わせない）。この端末の印を、
    # 作り替える（同じ利用者の古い印は消す）
    if not trusted:
        forget_failures(login_id_digest, client_digest)
    if g.get("user_session") is not None:
        db.session.delete(g.user_session)
    forget_device_token(device_token, user.id)
    token = start_session(user.id)
    new_device_token = issue_device_token(user.id, now)
    db.session.commit()
    auth_logger.info(
        "ログインしました（利用者：%s、%s、接続元：%r）",
        user.id,
        path_text,
        client_address(),
    )
    response = redirect("/", code=303)
    set_session_cookie(response, token)
    set_device_cookie(response, new_device_token)
    return response


@auth_bp.post("/logout")
def logout():
    """この端末だけ、ログアウトする。"""
    user_id = current_user().id
    db.session.delete(g.user_session)
    db.session.commit()
    auth_logger.info(
        "ログアウトしました（利用者：%s、接続元：%r）",
        user_id,
        client_address(),
    )
    return logged_out_response()


@auth_bp.post("/logout-all")
def logout_all():
    """すべての端末で、ログアウトする（スマホをなくしたときなど）。"""
    user_id = current_user().id
    count = end_all_sessions(user_id)
    # 端末の印も、すべて消す（なくした端末の印で、IDごとの制限を外して
    # 試されないため）。この端末の印の Cookie も消す
    end_all_devices(user_id)
    db.session.commit()
    auth_logger.info(
        "すべての端末でログアウトしました（利用者：%s、%s台、接続元：%r）",
        user_id,
        count,
        client_address(),
    )
    response = logged_out_response()
    clear_device_cookie(response)
    return response
