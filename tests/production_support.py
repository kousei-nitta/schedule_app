"""本番の設定（APP_ENV=production）のアプリを、テストで作る補助。

本番のアプリは、production_settings で作った設定を、test_config で渡して
作る（環境変数を変えずに済むため）。DBは、一時ディレクトリの中の、
持ち主だけのフォルダ（700）に置く。fixture は tests/conftest.py
（production_app・keep_umask）。
"""

from app.extensions import db
from app.proxy import PublicProxyMiddleware
from scripts.check_public import Response, Target
from tests.auth_support import TEST_PASSWORD, TEST_USERNAME

PUBLIC_HOST = "schedule.example"
PUBLIC_ORIGIN = f"https://{PUBLIC_HOST}"
SECRET = "s" * 40
OWNER_ADDRESS = "198.51.100.20"


def production_environment(tmp_path) -> dict[str, str]:
    """本番の環境変数（DBのフォルダは、持ち主だけの 700 で作る）。"""
    data_directory = tmp_path / "data"
    data_directory.mkdir(mode=0o700, exist_ok=True)
    return {
        "APP_ENV": "production",
        "PUBLIC_ORIGIN": PUBLIC_ORIGIN,
        "SECRET_KEY": SECRET,
        "DATABASE_URL": f"sqlite:///{data_directory / 'app.db'}",
        "CLIENT_ADDRESS_HEADER": "X-Real-IP",
    }


class PublicClient:
    """プロキシの後ろの本番に、ブラウザから届いた要求のように送る client。

    ブラウザ → プロキシ（HTTPS を終える）→ アプリ（HTTP）。プロキシが付ける
    ヘッダー（X-Real-IP・X-Forwarded-Proto）を付け、Host を本番の名前にする。
    """

    def __init__(self, app, address=OWNER_ADDRESS):
        self.client = app.test_client()
        self.client.environ_base.update(
            {
                "HTTP_X_REAL_IP": address,
                "HTTP_X_FORWARDED_PROTO": "https",
                # アプリが直接見る接続元は、プロキシのアドレス
                "REMOTE_ADDR": "10.0.0.1",
            }
        )

    def open(self, path, **kwargs):
        kwargs.setdefault("base_url", f"http://{PUBLIC_HOST}")
        return self.client.open(path, **kwargs)

    def get(self, path, **kwargs):
        return self.open(path, method="GET", **kwargs)

    def post(self, path, **kwargs):
        return self.open(path, method="POST", **kwargs)


def public_client(app, address=OWNER_ADDRESS):
    return PublicClient(app, address)


FORM = {"Origin": PUBLIC_ORIGIN, "Sec-Fetch-Site": "same-origin"}


def post_public_login(client, password=TEST_PASSWORD, headers=None):
    return client.post(
        "/login",
        data={"login_id": TEST_USERNAME, "password": password},
        headers=FORM if headers is None else headers,
    )


def seen_environ(header="X-Real-IP", **environ):
    """層を通ったあとに、アプリが受け取る environ（断られたら None）。"""
    seen = {}

    def inner_app(inner_environ, start_response):
        seen.update(inner_environ)
        start_response("200 OK", [])
        return [b""]

    statuses = []
    middleware = PublicProxyMiddleware(inner_app, header)
    middleware(environ, lambda status, headers: statuses.append(status))
    return seen if statuses == ["200 OK"] else None


def table_names(app) -> set[str]:
    with app.app_context():
        return set(db.inspect(db.engine).get_table_names())


class ProxyTarget(Target):
    """ホストのプロキシの代わり：http は https へ移し、https はアプリへ
    渡す（下線の入った名前のヘッダーを捨て、X-Real-IP を、本当の接続元で
    上書きし、X-Forwarded-Proto を付ける）。
    """

    def __init__(self, app):
        super().__init__(PUBLIC_ORIGIN)
        self.client = app.test_client(use_cookies=False)

    def request(self, method, path, headers=None, body=None, *, https=True):
        if not https:
            location = f"https://{self.host}{path}"
            return Response(301, [("Location", location)], b"")
        sent = {
            name: value
            for name, value in (headers or {}).items()
            if "_" not in name
        }
        sent["X-Real-IP"] = OWNER_ADDRESS
        sent["X-Forwarded-Proto"] = "https"
        response = self.client.open(
            path,
            method=method,
            headers=sent,
            data=body,
            base_url=f"http://{PUBLIC_HOST}",
        )
        return Response(
            response.status_code,
            list(response.headers.items()),
            response.get_data(),
            "TLSv1.3",
        )
