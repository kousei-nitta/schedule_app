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
    # 同じサイトへの POST の Origin ヘッダーが null になり、ログインの
    # タスク（Task 025）で、Origin の検査に使えなくなるため
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


def register_security_headers(app: Flask) -> None:
    """要求ごとのnonceを作り、すべての応答にヘッダーを付ける処理を登録する。"""

    @app.before_request
    def create_csp_nonce() -> None:
        # 要求ごとに、新しい値を作る（ほかの要求と同じ値を使わないため）。
        # before_request は、URLが見つからない・Hostを断る場合も含めて、
        # after_request より先に必ず動く
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.context_processor
    def provide_csp_nonce() -> dict[str, str]:
        # テンプレートで {{ csp_nonce }} として使う（base.html）
        return {"csp_nonce": g.csp_nonce}

    @app.after_request
    def add_security_headers(response: Response) -> Response:
        # 画面・API・静的ファイル・エラーの、すべての応答に付ける
        for name, value in SECURITY_HEADERS.items():
            response.headers[name] = value
        response.headers["Content-Security-Policy"] = (
            content_security_policy(g.csp_nonce)
        )
        return response
