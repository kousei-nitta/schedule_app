"""本番のURLを、外（KomaのMac）から点検する（Task 026）。

Claude の作業環境からは、本番に届かないため、Koma が Mac で動かす。
Python の標準のライブラリだけを使う（.venv がなくても動く）。
手順は docs/development/deploy.md。

使い方（URL は、PUBLIC_ORIGIN と同じ形。https://<名前>.alwaysdata.net）：
    python scripts/check_public.py URL
        ふだんの点検（ログインなし）
    python scripts/check_public.py --login URL
        ログインして、Cookie・本文の上限・ログアウトも
    python scripts/check_public.py --rate-limit URL
        接続元の偽装（Mac の接続元が、1時間ログインできなくなる）
    python scripts/check_public.py --probe URL
        下見：scripts/echo_headers_wsgi.py を置いたとき

それぞれの確かめは「✓」「✗」で表示し、1つでも ✗ なら、終了コード1で終わる。
本番のURLは、リポジトリ・Issue・PRに書かない。
"""
import argparse
import getpass
import http.client
import json
import re
import secrets
import ssl
import sys
from dataclasses import dataclass, field

# どの応答にも付くはずのヘッダーと値（app/security.py）
EXPECTED_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "X-Robots-Tag": "noindex, nofollow",
    "Cache-Control": "no-store",
}
HSTS_MIN_SECONDS = 31536000
# 応答の本文に、あってはいけないもの（DB・Git・秘密・エラーの詳細）
LEAK_MARKERS = [
    b"SQLite format 3",
    b"ref: refs/",
    b"[core]",
    b"SECRET_KEY",
    b"Traceback (most recent call last)",
    b"Werkzeug Debugger",
]
# 外から見えてはいけないパス（どれも、ログインの画面への移動・401・404 の
# どれかになるはず）
HIDDEN_PATHS = [
    "/.git/HEAD",
    "/.git/config",
    "/.env",
    "/app.db",
    "/instance/app.db",
    "/instance/secret_key",
    "/data/app.db",
    "/backups/",
    "/wsgi.py",
    "/run.py",
    "/requirements.txt",
    "/static/../instance/app.db",
    "/static/%2e%2e/instance/app.db",
    "/static/../../wsgi.py",
    "/console",
    "/?__debugger__=yes&cmd=resource&f=debugger.js",
]
ORIGIN_PATTERN = re.compile(r"https://([a-z0-9.-]+)")
LOGIN_FORM = "application/x-www-form-urlencoded"


@dataclass
class Response:
    status: int
    headers: list[tuple[str, str]]
    body: bytes
    tls_version: str | None = None

    def header(self, name: str) -> str | None:
        """そのヘッダーの最初の値（大文字・小文字を区別しない）。"""
        for key, value in self.headers:
            if key.lower() == name.lower():
                return value
        return None

    def header_list(self, name: str) -> list[str]:
        return [v for k, v in self.headers if k.lower() == name.lower()]


@dataclass
class Report:
    failures: list[str] = field(default_factory=list)

    def check(self, ok: bool, name: str, detail: str = "") -> None:
        if ok:
            print(f"✓ {name}")
        else:
            print(f"✗ {name}" + (f"：{detail}" if detail else ""))
            self.failures.append(name)


# --- 判定（応答の中身だけを見る。tests/test_check_public.py） ---


def security_header_problems(
    headers: dict[str, str], *, login_page: bool = False
) -> list[str]:
    """セキュリティのヘッダーの問題の一覧（なければ空）。"""
    problems = []
    lowered = {key.lower(): value for key, value in headers.items()}
    for name, expected in EXPECTED_HEADERS.items():
        value = lowered.get(name.lower())
        if value != expected:
            problems.append(f"{name} が {value!r}（{expected!r} のはず）")
    hsts = lowered.get("strict-transport-security", "")
    match = re.search(r"max-age=(\d+)", hsts)
    if match is None or int(match.group(1)) < HSTS_MIN_SECONDS:
        problems.append(f"Strict-Transport-Security が {hsts!r}")
    csp = lowered.get("content-security-policy", "")
    for directive in (
        "default-src 'self'",
        "frame-ancestors 'none'",
        "object-src 'none'",
    ):
        if directive not in csp:
            problems.append(f"CSP に {directive} がない")
    for weak in ("'unsafe-inline'", "'unsafe-eval'"):
        if weak in csp:
            problems.append(f"CSP に {weak} がある")
    if login_page and "script-src 'none'" not in csp:
        problems.append("ログインの画面の CSP に script-src 'none' がない")
    if "camera=()" not in lowered.get("permissions-policy", ""):
        problems.append("Permissions-Policy がない")
    server = lowered.get("server", "")
    if re.search(r"\d", server):
        problems.append(f"Server に版が出ている（{server!r}）")
    if "x-powered-by" in lowered:
        problems.append("X-Powered-By がある")
    return problems


def cookie_problems(set_cookie: str, expected_name: str) -> list[str]:
    """Set-Cookie の属性の問題の一覧（なければ空）。"""
    parts = [part.strip() for part in set_cookie.split(";")]
    name = parts[0].split("=", 1)[0]
    attributes = {part.split("=", 1)[0].lower(): part for part in parts[1:]}
    problems = []
    if name != expected_name:
        problems.append(f"名前が {name}（{expected_name} のはず）")
    if "secure" not in attributes:
        problems.append("Secure がない")
    if "httponly" not in attributes:
        problems.append("HttpOnly がない")
    if attributes.get("samesite", "").lower() != "samesite=strict":
        problems.append("SameSite=Strict でない")
    if attributes.get("path", "").lower() != "path=/":
        problems.append("Path=/ でない")
    if "domain" in attributes:
        problems.append("Domain がある")
    return problems


def leaked_markers(body: bytes) -> list[str]:
    """本文に含まれる、あってはいけないもの。"""
    return [
        marker.decode() for marker in LEAK_MARKERS if marker in body
    ]


def single_address(value: str | None) -> bool:
    """値が、1つの IP アドレスに見えるか（数字・a〜f・. と : だけ）。"""
    if value is None:
        return False
    return re.fullmatch(r"[0-9a-fA-F.:]+", value) is not None


# --- 通信 ---


class Target:
    """点検する本番のURL（https://名前）。"""

    def __init__(self, origin: str) -> None:
        match = ORIGIN_PATTERN.fullmatch(origin)
        if match is None:
            raise SystemExit(
                "URL は https://<名前> の形にしてください（末尾の / なし）"
            )
        self.origin = origin
        self.host = match.group(1)

    def request(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        *,
        https: bool = True,
    ) -> Response:
        if https:
            connection = http.client.HTTPSConnection(
                self.host, timeout=30, context=ssl.create_default_context()
            )
        else:
            connection = http.client.HTTPConnection(self.host, timeout=30)
        try:
            # TLS の版は、つないだすぐあとに読む（応答を読み終えると、
            # 接続が閉じられることがあるため）
            connection.connect()
            tls_version = connection.sock.version() if https else None
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return Response(
                response.status,
                response.getheaders(),
                response.read(),
                tls_version,
            )
        finally:
            connection.close()

    def same_origin_headers(self) -> dict[str, str]:
        """このアプリの画面から送ったときに、ブラウザが付けるヘッダー。"""
        return {"Origin": self.origin, "Sec-Fetch-Site": "same-origin"}


def login_form(login_id: str, password: str) -> bytes:
    from urllib.parse import urlencode

    return urlencode({"login_id": login_id, "password": password}).encode()


# --- 点検 ---


def check_basics(target: Target, report: Report) -> None:
    """ログインなしでできる点検。"""
    plain = target.request("GET", "/login", https=False)
    location = plain.header("Location") or ""
    report.check(
        plain.status in (301, 302, 307, 308)
        and location.startswith(f"https://{target.host}/"),
        "http:// は https:// へ移される",
        f"{plain.status} {location!r}",
    )
    report.check(
        not plain.header_list("Set-Cookie"),
        "http:// の応答に Cookie が付かない",
    )

    login_page = target.request("GET", "/login")
    report.check(login_page.status == 200, "ログインの画面が開く",
                 str(login_page.status))
    report.check(
        login_page.tls_version in ("TLSv1.2", "TLSv1.3"),
        "TLS 1.2 以上",
        str(login_page.tls_version),
    )
    problems = security_header_problems(
        dict(login_page.headers), login_page=True
    )
    report.check(not problems, "セキュリティのヘッダー", "、".join(problems))

    top = target.request("GET", "/")
    report.check(
        top.status == 303
        and (top.header("Location") or "").endswith("/login"),
        "ログインなしのトップは、ログインの画面へ",
        f"{top.status} {top.header('Location')!r}",
    )
    api = target.request("GET", "/api/semesters")
    report.check(
        api.status == 401 and b'"unauthorized"' in api.body,
        "ログインなしの API は 401",
        str(api.status),
    )

    other_host = target.request("GET", "/login", {"Host": "evil.example"})
    report.check(
        other_host.status != 200,
        "ほかの名前の Host は受け付けない",
        str(other_host.status),
    )
    forwarded_host = target.request(
        "GET", "/", {"X-Forwarded-Host": "evil.example"}
    )
    report.check(
        b"evil.example" not in forwarded_host.body
        and "evil.example" not in (forwarded_host.header("Location") or ""),
        "X-Forwarded-Host を偽っても、応答が変わらない",
    )

    cross_site = target.request(
        "POST",
        "/login",
        {
            "Origin": "https://evil.example",
            "Sec-Fetch-Site": "cross-site",
            "Content-Type": LOGIN_FORM,
        },
        login_form("check-user", "x"),
    )
    report.check(
        cross_site.status == 403,
        "ほかのサイトからのログインの送信は 403",
        str(cross_site.status),
    )
    no_headers = target.request(
        "POST",
        "/login",
        {"Content-Type": LOGIN_FORM},
        login_form("check-user", "x"),
    )
    report.check(
        no_headers.status == 403,
        "Origin も Sec-Fetch-Site もない送信は 403",
        str(no_headers.status),
    )
    too_large = target.request(
        "POST",
        "/login",
        target.same_origin_headers() | {"Content-Type": LOGIN_FORM},
        b"login_id=x&password=" + b"a" * (17 * 1024),
    )
    report.check(
        too_large.status == 413,
        "大きすぎるログインの送信は 413",
        str(too_large.status),
    )

    for path in HIDDEN_PATHS:
        response = target.request("GET", path)
        leaks = leaked_markers(response.body)
        report.check(
            response.status != 200 and not leaks,
            f"見えないこと：{path}",
            f"{response.status} {leaks}",
        )
    missing = target.request("GET", "/static/no-such-file.js")
    report.check(
        missing.status == 404 and not leaked_markers(missing.body),
        "404 の応答に、エラーの詳細が出ない",
        str(missing.status),
    )


def check_logged_in(target: Target, report: Report) -> None:
    """ログインして、Cookie・API・本文の上限・ログアウトを確かめる。"""
    login_id = getpass.getpass("ログインID（表示されません）：")
    password = getpass.getpass("パスワード（表示されません）：")
    response = target.request(
        "POST",
        "/login",
        target.same_origin_headers() | {"Content-Type": LOGIN_FORM},
        login_form(login_id, password),
    )
    if response.status != 303:
        report.check(False, "ログインできる", str(response.status))
        return
    cookies = {}
    for header in response.header_list("Set-Cookie"):
        name = header.split("=", 1)[0]
        cookies[name] = header
        problems = cookie_problems(header, name)
        report.check(
            not problems, f"Cookie の属性：{name}", "、".join(problems)
        )
    for name in ("__Host-schedule_session", "__Host-schedule_device"):
        report.check(name in cookies, f"Cookie がある：{name}")
    session = cookies.get("__Host-schedule_session", "").split(";", 1)[0]
    if not session:
        return
    cookie_header = {"Cookie": session}

    api = target.request("GET", "/api/semesters", cookie_header)
    report.check(api.status == 200, "ログインのあとの API", str(api.status))
    big = target.request(
        "POST",
        "/api/semesters",
        cookie_header | {"Content-Type": "application/json"},
        b'{"name": "' + b"a" * (70 * 1024) + b'"}',
    )
    report.check(
        big.status == 413 and b'"too_large"' in big.body,
        "64KiB を超える本文は 413",
        str(big.status),
    )
    logout = target.request(
        "POST", "/logout", cookie_header | target.same_origin_headers()
    )
    report.check(
        logout.status == 303 and logout.header("Clear-Site-Data") is not None,
        "ログアウトできる",
        str(logout.status),
    )


def check_rate_limit(target: Target, report: Report) -> None:
    """接続元を偽るヘッダーを付けても、接続元ごとの制限が働くか。"""
    answer = input(
        "この点検は、存在しないIDで11回失敗し、この Mac の接続元を、"
        "1時間ログインできなくします（端末の印のある端末は使えます）。"
        "続けるなら yes：",
    )
    if answer.strip() != "yes":
        print("接続元の点検を、とばしました")
        return
    statuses = []
    for _ in range(11):
        fake = f"192.0.2.{secrets.randbelow(250) + 1}"
        response = target.request(
            "POST",
            "/login",
            target.same_origin_headers()
            | {
                "Content-Type": LOGIN_FORM,
                "X-Real-IP": fake,
                "X-Forwarded-For": fake,
                "X-Client-IP": fake,
                "Forwarded": f"for={fake}",
            },
            login_form(f"check-{secrets.token_hex(6)}", secrets.token_hex(8)),
        )
        statuses.append(response.status)
    report.check(
        statuses[-1] == 429,
        "接続元を偽っても、接続元ごとの制限が働く（11回目は 429）",
        str(statuses),
    )


def probe_headers(target: Target, report: Report) -> None:
    """下見：echo_headers_wsgi.py を置いた状態で、プロキシの振る舞いを見る。"""
    spoofed = {
        "X-Real-IP": "192.0.2.10",
        "X-Forwarded-For": "192.0.2.11",
        "X-Client-IP": "192.0.2.12",
        "Forwarded": "for=192.0.2.13",
        "X-Forwarded-Proto": "http",
    }
    response = target.request("GET", "/", spoofed)
    try:
        seen = json.loads(response.body)
    except ValueError:
        report.check(False, "下見のアプリの応答（JSON）", str(response.status))
        return
    headers = seen.get("headers", {})
    print(f"REMOTE_ADDR：{seen.get('REMOTE_ADDR')!r}")
    for name, value in spoofed.items():
        key = "HTTP_" + name.upper().replace("-", "_")
        received = headers.get(key)
        if received is None:
            state = "届かない"
        elif value in received:
            state = "偽の値がそのまま届く（使えない）"
        else:
            state = "上書きされる"
        print(f"{name}：{received!r} … {state}")
    candidates = []
    for name in ("X-Real-IP", "X-Forwarded-For", "X-Client-IP"):
        received = headers.get("HTTP_" + name.upper().replace("-", "_"))
        if single_address(received) and spoofed[name] not in received:
            candidates.append(name)
    print(
        f"CLIENT_ADDRESS_HEADER の候補：{candidates or 'なし'}"
        "（値が、この Mac の公開のアドレスと同じかも確かめる）"
    )
    report.check(
        headers.get("HTTP_X_FORWARDED_PROTO") == "https",
        "X-Forwarded-Proto が https に上書きされる",
        repr(headers.get("HTTP_X_FORWARDED_PROTO")),
    )
    report.check(bool(candidates), "上書きされる接続元のヘッダーがある")
    report.check(seen.get("workers") == 1, "uWSGI のワーカーが1つ",
                 repr(seen.get("workers")))
    print(f"Python：{seen.get('python')}、SQLite：{seen.get('sqlite')}")
    report.check(
        str(seen.get("python", "")).startswith("3.14."),
        "Python 3.14",
        repr(seen.get("python")),
    )
    filesystem = str(seen.get("home_filesystem"))
    report.check(
        not filesystem.startswith(("nfs", "cifs", "smb", "fuse", "9p")),
        f"ホームのファイルシステムがローカル（{filesystem}）",
        "ネットワークのファイルシステムでは、SQLite が壊れうる",
    )


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(description="本番のURLの点検")
    parser.add_argument("url", help="https://<名前>（末尾の / なし）")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--login", action="store_true",
                       help="ログインして、Cookie と本文の上限も確かめる")
    group.add_argument("--rate-limit", action="store_true",
                       help="接続元の偽装を確かめる（1時間制限される）")
    group.add_argument("--probe", action="store_true",
                       help="下見のアプリで、プロキシの振る舞いを見る")
    options = parser.parse_args(arguments)
    target = Target(options.url)
    report = Report()
    if options.probe:
        probe_headers(target, report)
    elif options.rate_limit:
        check_rate_limit(target, report)
    elif options.login:
        check_logged_in(target, report)
    else:
        check_basics(target, report)
    if report.failures:
        print(f"\n✗ が {len(report.failures)}件あります")
        return 1
    print("\nすべて ✓ です")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
