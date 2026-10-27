"""セキュリティのヘッダー（CSPを含む）を、すべての応答に付ける。

仕様は docs/architecture/security.md の「セキュリティのヘッダー」。
"""
import secrets

from flask import Flask, Response, g

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
    # ログインのタスク（Task 025）で、Origin の検査に使えなくなるため
    "Referrer-Policy": "same-origin",
}


def content_security_policy(nonce: str) -> str:
    """CSP（ページが読み込んでよいものの一覧）の値を作る。

    nonce は、FullCalendarが差し込む <style> だけに渡す、要求ごとの
    使い捨ての値。インラインのスクリプト・スタイル（'unsafe-inline'）と、
    文字列からのコードの実行（'unsafe-eval'）は、許さない。
    """
    directives = [
        # 下で決めていない種類は、自分のサイトからだけ
        "default-src 'self'",
        # スクリプト：自分のファイル（main.js など）と、CDNの2つのファイル
        # だけ（jsDelivrの、ほかのファイルは読ませない）
        f"script-src 'self' {BOOTSTRAP_JS_URL} {FULLCALENDAR_JS_URL}",
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
            content_security_policy(current_csp_nonce())
        )
        return response
