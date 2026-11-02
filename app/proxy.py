"""本番：プロキシの後ろで、接続元とスキームを決める WSGI の層。

仕様は docs/architecture/security.md の「本番の設定」の「接続元」。
本番では、利用者のブラウザ → ホストのプロキシ（HTTPSを終える）→ この
アプリ、の順に届く。アプリが直接見る接続元（REMOTE_ADDR）は、プロキシの
アドレスになりうるため、プロキシが付けるヘッダーから、本当の接続元を読む。

- 読むのは、設定 CLIENT_ADDRESS_HEADER の1つのヘッダーだけ（プロキシが、
  利用者の送った同じ名前のヘッダーを、必ず上書きすると、下見で確かめた
  もの）。ほかのヘッダー（X-Forwarded-For など）は、利用者が自由に
  送れるため、読まない（ProxyFix を使わない理由）
- そのヘッダーが、1つのアドレスでなければ、400（接続元の分からない要求を、
  試行の制限やログで扱わない）
- プロキシは、利用者との通信が HTTPS かどうかを、X-Forwarded-Proto で
  知らせる。https でなければ、400（パスワードや Cookie を、暗号化されて
  いない通信で扱わない。ふつうは、ホストの「Force HTTPS」で、ここに
  届く前に HTTPS へ移される）
"""
import ipaddress
from collections.abc import Callable, Iterable

from app.config import REMOTE_ADDR

# この層が断るときの応答（Flask の外のため、ヘッダーは最小限を自分で付ける）
REJECT_STATUS = "400 Bad Request"
REJECT_BODY = "Bad Request\n".encode("utf-8")
REJECT_HEADERS = [
    ("Content-Type", "text/plain; charset=utf-8"),
    ("Content-Length", str(len(REJECT_BODY))),
    ("Cache-Control", "no-store"),
    ("X-Content-Type-Options", "nosniff"),
]


def environ_key(header_name: str) -> str:
    """ヘッダーの名前を、WSGI の environ の名前にする。

    例：X-Real-IP → HTTP_X_REAL_IP。REMOTE_ADDR は、そのまま。
    """
    if header_name == REMOTE_ADDR:
        return REMOTE_ADDR
    return "HTTP_" + header_name.upper().replace("-", "_")


def single_address(value: str | None) -> str | None:
    """値が、1つの IP アドレスなら、その書き方をそろえて返す。ほかは None。

    カンマで区切った複数の値（X-Forwarded-For の形）は、どれが本当の
    接続元か分からないため、受け付けない。
    """
    if value is None:
        return None
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


class PublicProxyMiddleware:
    """本番のアプリの前に置く WSGI の層（create_app が付ける）。"""

    def __init__(
        self, wsgi_app: Callable, client_address_header: str
    ) -> None:
        self.wsgi_app = wsgi_app
        self.client_address_key = environ_key(client_address_header)

    def __call__(
        self, environ: dict, start_response: Callable
    ) -> Iterable[bytes]:
        address = single_address(environ.get(self.client_address_key))
        is_https = environ.get("HTTP_X_FORWARDED_PROTO") == "https"
        if address is None or not is_https:
            start_response(REJECT_STATUS, REJECT_HEADERS)
            return [REJECT_BODY]
        environ["REMOTE_ADDR"] = address
        environ["wsgi.url_scheme"] = "https"
        return self.wsgi_app(environ, start_response)
