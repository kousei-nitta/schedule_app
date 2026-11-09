"""作業中の道具：どの要求にも「ただいま作業中です」と 503 を返す WSGI。

alwaysdata の管理画面には、サイトを止める機能がない（公式の資料
「Disabling a Website」）。実データの移行・更新・Python の修正版を
上げる間は、サイトの Application path を、このファイルに変える（アプリが
DB を開かず、書き込まないように。管理画面で保存すると、サイトは自動で
再起動する）。終わったら、wsgi.py に戻す。下見の道具を片づけたあとも、
アプリを置くまでは、これにしておく。
手順は docs/development/deploy.md。

標準のライブラリだけを使う（.venv がなくても動く）。要求の中身は読まず、
何も表示しない。
"""

BODY = (
    "ただいま作業中です。しばらくしてから、開き直してください。\n"
).encode("utf-8")
HEADERS = [
    ("Content-Type", "text/plain; charset=utf-8"),
    ("Content-Length", str(len(BODY))),
    ("Cache-Control", "no-store"),
    ("Retry-After", "600"),
    ("X-Content-Type-Options", "nosniff"),
    ("Content-Security-Policy", "default-src 'none'"),
]


def application(environ, start_response):
    start_response("503 Service Unavailable", HEADERS)
    return [BODY]
