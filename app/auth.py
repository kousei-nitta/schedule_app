"""ログインの状態の読み込み・既定での拒否・ほかのサイトからの要求の拒否。

仕様は docs/architecture/security.md の「ログイン」「CSRF」。
create_app から register_auth(app) を呼ぶ。要求ごとに、次の順で確かめる。
1. ほかのサイトからの要求なら、断る（403）
2. Cookie のトークンから、ログインしている利用者を読む
3. 公開するもの（ログインの画面・静的ファイル）でなく、ログインして
   いなければ、断る（画面はログインの画面へ、APIは401）

既定で拒否：新しい画面やAPIを足しても、何もしなければ、ログインが
要る（足し忘れで、公開されてしまうことがない）。
"""
import logging

from flask import (
    Flask,
    Response,
    abort,
    current_app,
    g,
    redirect,
    request,
    url_for,
)
from werkzeug.exceptions import SecurityError

from app.api_helpers import api_error_response, is_api_path
from app.extensions import db
from app.models.user import User
from app.user_sessions import clear_session_cookie, find_session

# 認証の出来事のログ（成功・失敗・制限・ログアウト・断った要求）。
# パスワード・トークン・打ち込まれたログインIDは、出さない
auth_logger = logging.getLogger("app.auth")
auth_logger.setLevel(logging.INFO)

# ログインしなくても使えるもの（routeの名前）。ここにないものは、
# すべてログインが要る
PUBLIC_ENDPOINTS = {"auth.login", "static"}

# データを変えないメソッド
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

# ブラウザが付ける「どこから始まった要求か」（Sec-Fetch-Site）のうち、
# 受け付けるもの。same-origin：このアプリの画面から。none：アドレス欄に
# 打った・ブックマーク（利用者の操作）
ALLOWED_FETCH_SITES = {"same-origin", "none"}

FORBIDDEN_MESSAGE = "リクエストを受け付けられません"
UNAUTHORIZED_MESSAGE = "ログインしてください"


def current_user() -> User | None:
    """この要求の、ログインしている利用者（いなければ None）。"""
    return g.get("current_user")


def current_user_id() -> int:
    """この要求の、ログインしている利用者のid。

    ログインが要るroute（既定で拒否のため、公開するもののほかすべて）
    だけで使う。いなければ、例外にする（他人や持ち主のないデータを、
    誤って扱わないよう、止める）。
    """
    user = current_user()
    if user is None:
        raise RuntimeError(
            "ログインしていない要求で、利用者のデータを扱おうとしました"
        )
    return user.id


def client_address() -> str:
    """接続元のアドレス（ログ用）。"""
    return request.remote_addr or "不明"


def own_origin() -> str:
    """このアプリの Origin（例：http://127.0.0.1:5001）。"""
    return f"{request.scheme}://{request.host}"


def is_rejected_host() -> bool:
    """信頼しない Host の要求か（Flaskが400にする。ここでは何もしない）。"""
    return isinstance(request.routing_exception, SecurityError)


def is_cross_site_request() -> bool:
    """ほかのサイトから始まった要求で、断るべきものか。

    1. Sec-Fetch-Site（今のブラウザが必ず付ける）が、same-origin・none で
       なければ断る。ただし、ほかのサイトのリンクから、画面を開くこと
       （画面への GET のページ移動）は許す。APIは、読み取りも断る
    2. データを変えるメソッドで、Origin が、このアプリと違えば断る
       （null を含む）
    3. 画面のフォームの送信（ログイン・ログアウト）は、どちらのヘッダーも
       なければ断る（今のブラウザは、フォームの送信に、必ず付ける）
    APIは、どちらのヘッダーもない要求（ブラウザでないもの）を通す
    （CSRF は、利用者のブラウザを使う攻撃のため。ほかのサイトは、
    application/json を、事前の確かめなしに送れない）。
    """
    fetch_site = request.headers.get("Sec-Fetch-Site")
    if fetch_site is not None and fetch_site not in ALLOWED_FETCH_SITES:
        is_page_navigation = (
            not is_api_path(request.path)
            and request.method == "GET"
            and request.headers.get("Sec-Fetch-Mode") == "navigate"
            and request.headers.get("Sec-Fetch-Dest", "document")
            == "document"
        )
        if not is_page_navigation:
            return True

    if request.method not in SAFE_METHODS:
        origin = request.headers.get("Origin")
        if origin is not None and origin != own_origin():
            return True
        if (
            origin is None
            and fetch_site is None
            and not is_api_path(request.path)
        ):
            return True
    return False


def reject_cross_site_request() -> Response | tuple[Response, int] | None:
    """ほかのサイトからの要求を断る（before_request）。"""
    if is_rejected_host() or not is_cross_site_request():
        return None
    # 要求から来た値は、%r で書く（改行などで、偽の行を作らせない）
    auth_logger.warning(
        "ほかのサイトからの要求を断りました"
        "（%s %r、Sec-Fetch-Site：%r、Origin：%r、接続元：%s）",
        request.method,
        request.path,
        request.headers.get("Sec-Fetch-Site"),
        request.headers.get("Origin"),
        client_address(),
    )
    if is_api_path(request.path):
        return api_error_response("forbidden", FORBIDDEN_MESSAGE)
    abort(403)


def load_current_user() -> None:
    """Cookie のトークンから、ログインしている利用者を読む（before_request）。

    g は、1つのアプリのコンテキストの中で、要求をまたいで残ることがある
    （デモデータの作成など）。前の要求の利用者を使わないよう、毎回、
    初めに空にする。
    """
    g.current_user = None
    g.user_session = None
    g.clear_session_cookie = False
    if is_rejected_host():
        return

    token = request.cookies.get(current_app.config["AUTH_COOKIE_NAME"])
    if token is None:
        return
    session = find_session(token)
    user = None
    if session is not None:
        user = db.session.get(User, session.user_id)
    if session is None or user is None:
        # 期限切れ・ログアウト済み・偽物の Cookie は、ブラウザから消す
        g.clear_session_cookie = True
        return
    g.current_user = user
    g.user_session = session


def require_login() -> Response | tuple[Response, int] | None:
    """ログインしていなければ断る（before_request。既定で拒否）。

    存在しないURLも、ログインしていなければ同じに断る（どんなURLが
    あるかを、ログインの前に知らせない）。
    """
    if is_rejected_host() or request.endpoint in PUBLIC_ENDPOINTS:
        return None
    if current_user() is not None:
        return None
    if is_api_path(request.path):
        return api_error_response("unauthorized", UNAUTHORIZED_MESSAGE)
    return redirect(url_for("auth.login"), code=303)


def clear_invalid_cookie(response: Response) -> Response:
    """使えない Cookie を、ブラウザから消す（after_request）。"""
    if g.get("clear_session_cookie"):
        clear_session_cookie(response)
    return response


def register_auth(app: Flask) -> None:
    """ログインの確かめを、アプリに登録する（create_app から呼ぶ）。"""
    # Flask の既定のログの出力先（標準エラー）は、app.logger を初めて
    # 使ったときに作られる。app.auth のログが、親の app のロガーへ伝わり、
    # そこから表示されるように、ここで作っておく
    app.logger.debug("ログインの確かめを登録しました")

    app.before_request(reject_cross_site_request)
    app.before_request(load_current_user)
    app.before_request(require_login)
    app.after_request(clear_invalid_cookie)
