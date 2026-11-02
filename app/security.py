"""セキュリティのヘッダー（CSPを含む）を、すべての応答に付ける。

仕様は docs/architecture/security.md の「セキュリティのヘッダー」。
"""
import secrets

from flask import Flask, Response, g, request

# CDN（jsDelivr）から読み込むファイル。templates/base.html の
# <script>・<link> と同じURLにする（版を変えるときは、両方を変える。
# tests/test_security.py が、base.html のCDNのURLが、すべてCSPで
# 許されていることを確かめる）。
CDN_PREFIX = "https://cdn.jsdelivr.net/npm/"
BOOTSTRAP_CSS_URL = (
    CDN_PREFIX + "bootstrap@5.3.8/dist/css/bootstrap.min.css"
)
BOOTSTRAP_JS_URL = (
    CDN_PREFIX + "bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"
)
FULLCALENDAR_JS_URL = (
    CDN_PREFIX + "fullcalendar@6.1.21/index.global.min.js"
)

# CSP以外のヘッダー
SECURITY_HEADERS = {
    # 宣言した種類（Content-Type）と違うものとして、ブラウザに読ませない
    "X-Content-Type-Options": "nosniff",
    # ほかのサイトの枠（iframe）の中に表示させない（クリックジャッキング
    # の対策。CSPの frame-ancestors と同じ。古いブラウザのため両方付ける）
    "X-Frame-Options": "DENY",
    # ほかのサイトへ、URL（Referer）を送らない。no-referrer にしないのは、
    # フォームの送信（ログインの画面など）の Origin ヘッダーが null になり、
    # Origin の検査（app/auth.py）に使えなくなるため
    "Referrer-Policy": "same-origin",
    # ほかのサイトの窓（window.open など）と、このアプリの窓を切り離す
    # （ほかのサイトから、このアプリの窓を操作・観察させない）
    "Cross-Origin-Opener-Policy": "same-origin",
    # このアプリの応答（APIのJSON・画面・静的ファイル）を、ほかのサイトの
    # ページに読み込ませない（<script src> や <img src> での読み込みを含む）
    "Cross-Origin-Resource-Policy": "same-origin",
    # 使わないブラウザの機能を、使えないようにする（万一、スクリプトが
    # 入り込んでも、カメラ・マイク・位置情報などを使わせない）
    "Permissions-Policy": (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    ),
    # 公開したとき（Task 026）、検索エンジンに載せない（ログインの画面の
    # URLを、検索で見つけさせない）
    "X-Robots-Tag": "noindex, nofollow",
}

# 個人のデータを含む応答（画面・API）を、ブラウザやプロキシに保存させない
# （共用のPCで、ログアウトのあとに「戻る」で見えたり、途中の機器に
# 残ったりしないように）。静的ファイル（JavaScript・CSS）は、個人の
# データを含まないため、対象にしない
NO_STORE = "no-store"

# スクリプトを1つも許さない画面（routeの名前）
NO_SCRIPT_ENDPOINTS = {"auth.login"}


def content_security_policy(nonce: str, allow_scripts: bool = True) -> str:
    """CSP（ページが読み込んでよいものの一覧）の値を作る。

    nonce は、FullCalendarが差し込む <style> だけに渡す、要求ごとの
    使い捨ての値。インラインのスクリプト・スタイル（'unsafe-inline'）と、
    文字列からのコードの実行（'unsafe-eval'）は、許さない。
    allow_scripts が False なら、スクリプトを1つも許さない（ログインの
    画面。パスワードを入れる画面では、万一入り込んでも動かさない）。
    """
    if allow_scripts:
        # スクリプト：自分のファイル（main.js など）と、CDNの2つの
        # ファイルだけ（jsDelivrの、ほかのファイルは読ませない）
        script_sources = (
            f"'self' {BOOTSTRAP_JS_URL} {FULLCALENDAR_JS_URL}"
        )
    else:
        script_sources = "'none'"
    directives = [
        # 下で決めていない種類は、自分のサイトからだけ
        "default-src 'self'",
        f"script-src {script_sources}",
        # スタイル：自分の style.css、BootstrapのCSS、FullCalendarが
        # 差し込む <style>（nonce つき）
        f"style-src 'self' {BOOTSTRAP_CSS_URL} 'nonce-{nonce}'",
        # BootstrapのCSSは、選択欄の矢印などに data: の画像を使う
        "img-src 'self' data:",
        # FullCalendarのCSSは、ボタンのアイコンに data: のフォントを使う
        "font-src 'self' data:",
        # fetch は、自分のAPIだけ
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
    return "; ".join(directives)


def current_csp_nonce() -> str:
    """この要求のnonceを返す。まだなければ作る。

    ふつうは、下の before_request が、要求の始めに作る。ほかの
    before_request が先に応答を返した場合など、作られていないときも、
    ここで作る（ヘッダーが付かない・500になる、ということがないように）。
    ただし、1つのアプリのコンテキストの中で何度も要求を送る場合
    （デモデータの作成）は、g に前の要求の値が残っているため、その値を
    使う。先に応答を返すのは、画面のページでない応答（断る応答）なので、
    害はない。
    """
    if "csp_nonce" not in g:
        g.csp_nonce = secrets.token_urlsafe(16)
    return g.csp_nonce


def register_security_headers(app: Flask) -> None:
    """要求ごとのnonceを作り、すべての応答にヘッダーを付ける処理を登録する。"""

    @app.before_request
    def create_csp_nonce() -> None:
        # 要求ごとに、新しい値を作る（ほかの要求と同じ値を使わないため）。
        # g は、アプリのコンテキストに属するため、デモデータのように、1つの
        # コンテキストの中で何度も要求を送る場合は、前の要求の値が残って
        # いる。そのため、あるかどうかに関係なく、ここで作り直す
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.context_processor
    def provide_csp_nonce() -> dict[str, str]:
        # テンプレートで {{ csp_nonce }} として使う（base.html）
        return {"csp_nonce": current_csp_nonce()}

    @app.after_request
    def add_security_headers(response: Response) -> Response:
        # 画面・API・静的ファイル・エラーの、すべての応答に付ける
        for name, value in SECURITY_HEADERS.items():
            response.headers[name] = value
        response.headers["Content-Security-Policy"] = (
            content_security_policy(
                current_csp_nonce(),
                allow_scripts=request.endpoint not in NO_SCRIPT_ENDPOINTS,
            )
        )
        if request.endpoint != "static":
            response.headers["Cache-Control"] = NO_STORE
        return response
