"""本番のURLを、外（KomaのMac）から点検する（Task 026）。

Claude の作業環境からは、本番に届かないため、Koma が Mac で動かす。
Python の標準のライブラリだけを使う（.venv がなくても動く）。Python 3.10
以上が要る（Mac に最初から入っている python3 は 3.9 のため、python3.14 で
動かす）。手順は docs/development/deploy.md。

使い方（URL は、PUBLIC_ORIGIN と同じ形。https://<名前>.alwaysdata.net）：
    python3.14 scripts/check_public.py URL
        ふだんの点検（ログインなし）
    python3.14 scripts/check_public.py --login URL
        ログインして、Cookie・本文の上限・ログアウトも（本番に、端末の印が
        1つ増える）
    python3.14 scripts/check_public.py --rate-limit URL
        接続元の偽装（Mac の接続元が、1時間ログインできなくなる）
    python3.14 scripts/check_public.py --probe URL
        下見：scripts/echo_headers_wsgi.py を置いたとき（Mac の公開の
        アドレスを尋ねる）

それぞれの確かめは「✓」「✗」で表示し、1つでも ✗ なら、終了コード1で終わる。
本番のURLは、リポジトリ・Issue・PRに書かない。
"""
import argparse
import getpass
import http.client
import ipaddress
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
# CSP の script-src（ないときは default-src）に、あってはいけない値
# （どこからでも・インラインのスクリプトを許すもの）
WIDE_SCRIPT_SOURCES = {
    "*",
    "https:",
    "http:",
    "data:",
    "blob:",
    "'unsafe-inline'",
    "'unsafe-eval'",
    "'unsafe-hashes'",
    "'strict-dynamic'",
}
ORIGIN_PATTERN = re.compile(r"https://([a-z0-9.-]+)")
LOGIN_FORM = "application/x-www-form-urlencoded"
# 接続元を偽るときの値は、資料の例のためのアドレスの範囲（192.0.2.0/24）
# から選ぶ（本物の接続元には、ならない）
FAKE_ADDRESS_PREFIX = "192.0.2."
# 接続元に使えるかを見るヘッダー
ADDRESS_HEADERS = ("X-Real-IP", "X-Forwarded-For", "X-Client-IP")
# 下線の名前。WSGI では、X-Real-IP と X_Real_IP が、どちらも
# HTTP_X_REAL_IP になる。プロキシが下線の名前を消さないと、偽の値が
# 届きうる（同じ種類の弱さ：CVE-2015-0219）
UNDERSCORE_NAMES = {
    "X-Real-IP": "X_Real_IP",
    "X-Forwarded-For": "X_Forwarded_For",
    "X-Client-IP": "X_Client_IP",
    "X-Forwarded-Proto": "X_Forwarded_Proto",
}
# Python の版の下限（docs/architecture/security.md の「開発の環境」）
MIN_PYTHON = (3, 14, 10)


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


def csp_directives(csp: str) -> dict[str, list[str]]:
    """CSP を、指示ごとの値の一覧にする（同じ指示の2つ目は、ブラウザと
    同じく無視する）。"""
    directives: dict[str, list[str]] = {}
    for part in csp.split(";"):
        words = part.split()
        if words:
            directives.setdefault(words[0].lower(), words[1:])
    return directives


def is_narrow_script_source(source: str) -> bool:
    """スクリプトの出どころとして、狭い（1つのファイルまで決まる）か。

    'self'・'none' と、https のファイルのURL（パスまで。* を含まず、
    / で終わらない）だけを狭いとする。
    """
    if source in ("'self'", "'none'"):
        return True
    if not source.startswith("https://") or "*" in source:
        return False
    path = source.removeprefix("https://").partition("/")[2]
    return path != "" and not source.endswith("/")


def csp_problems(csp: str, *, login_page: bool = False) -> list[str]:
    """CSP の問題の一覧（指示ごとに、値を比べる）。"""
    problems = []
    directives = csp_directives(csp)
    for name, expected in (
        ("default-src", ["'self'"]),
        ("object-src", ["'none'"]),
        ("frame-ancestors", ["'none'"]),
    ):
        if directives.get(name) != expected:
            problems.append(
                f"CSP の {name} が {directives.get(name)!r}（{expected!r} の"
                "はず）"
            )
    scripts = directives.get("script-src", directives.get("default-src", []))
    for source in scripts:
        if source in WIDE_SCRIPT_SOURCES or not is_narrow_script_source(
            source
        ):
            problems.append(f"CSP の script-src に {source} がある")
    for name, values in directives.items():
        for weak in ("'unsafe-inline'", "'unsafe-eval'"):
            if weak in values:
                problems.append(f"CSP の {name} に {weak} がある")
    if login_page and directives.get("script-src") != ["'none'"]:
        problems.append("ログインの画面の CSP に script-src 'none' がない")
    return problems


def answered_by_app(response: "Response") -> bool:
    """応答が、アプリのもの（アプリだけが付ける CSP がある）か。"""
    return response.header("Content-Security-Policy") is not None


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
    problems.extend(
        csp_problems(
            lowered.get("content-security-policy", ""), login_page=login_page
        )
    )
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


def parse_address(value: str | None):
    """値が1つの IP アドレスなら、そのアドレス（でなければ None）。"""
    if value is None:
        return None
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def environ_key(header_name: str) -> str:
    """ヘッダーの名前に対応する WSGI の environ の名前（HTTP_X_REAL_IP）。"""
    return "HTTP_" + header_name.upper().replace("-", "_")


def same_client(address, my_address) -> bool:
    """同じ接続元か。IPv6 は、アプリと同じく /64 の範囲で比べる（Mac は、
    一時的な IPv6 のアドレスを、接続ごとに変えうるため）。"""
    if address is None or address.version != my_address.version:
        return False
    if address.version == 6:
        network = ipaddress.ip_network(f"{my_address}/64", strict=False)
        return address in network
    return address == my_address


def address_header_state(received: list[str | None], my_address) -> str:
    """接続元のヘッダーに届いた値（偽りかたごと）から、使えるかを決める。

    使える（"使える"）のは、どの要求でも、偽の値が混ざらず、値が1つの
    アドレスで、この Mac の公開のアドレスと同じ接続元のとき。
    """
    if any(v is not None and FAKE_ADDRESS_PREFIX in v for v in received):
        return "偽の値が届く（使えない）"
    if any(v is None for v in received):
        return "届かないことがある（使えない）"
    addresses = [parse_address(v) for v in received]
    if any(
        a is not None and a.version != my_address.version for a in addresses
    ):
        return (
            "IPv4 と IPv6 が違う（届いた値と同じ種類の、この Mac の"
            "アドレスで、入れ直す）"
        )
    if not all(same_client(a, my_address) for a in addresses):
        return "この Mac のアドレスと違う（使えない）"
    return "使える"


def version_tuple(text: str) -> tuple[int, ...]:
    """「3.14.10」→ (3, 14, 10)。読めなければ空。"""
    try:
        return tuple(int(part) for part in text.split("."))
    except ValueError:
        return ()


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
    # プロキシが、ほかの名前に自分で答えると、アプリの Host の確かめは、
    # 外からは確かめられない（そのときは、tests/test_security.py で確かめて
    # いる）。どちらが答えたかを表示する
    if answered_by_app(other_host):
        print(
            f"  （ほかの名前の Host に、アプリが {other_host.status} で"
            "答えた）"
        )
    else:
        print(
            f"  （ほかの名前の Host に、プロキシが {other_host.status} で"
            "答えた。アプリには届かない）"
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
        fake = f"{FAKE_ADDRESS_PREFIX}{secrets.randbelow(250) + 1}"
        spoofed = {"Forwarded": f"for={fake}"}
        for name in ADDRESS_HEADERS:
            spoofed[name] = fake
            spoofed[UNDERSCORE_NAMES[name]] = fake
        response = target.request(
            "POST",
            "/login",
            target.same_origin_headers()
            | {"Content-Type": LOGIN_FORM}
            | spoofed,
            login_form(f"check-{secrets.token_hex(6)}", secrets.token_hex(8)),
        )
        statuses.append(response.status)
    report.check(
        statuses[-1] == 429,
        "接続元を偽っても、接続元ごとの制限が働く（11回目は 429）",
        str(statuses),
    )


def probe_headers(target: Target, report: Report) -> None:
    """下見：echo_headers_wsgi.py を置いた状態で、プロキシの振る舞いを見る。

    偽の接続元を、ふつうの名前と、下線の名前で、別々に送る。どちらでも、
    偽の値が混ざらず、この Mac の公開のアドレスになるヘッダーだけを、
    CLIENT_ADDRESS_HEADER の候補にする。
    """
    my_address = parse_address(
        input(
            "この Mac の公開のアドレス（ターミナルで "
            "curl https://api64.ipify.org の結果。IPv4 か IPv6）："
        )
    )
    if my_address is None:
        report.check(False, "この Mac の公開のアドレス", "アドレスの形でない")
        return
    hyphen = {
        "X-Real-IP": f"{FAKE_ADDRESS_PREFIX}10",
        "X-Forwarded-For": f"{FAKE_ADDRESS_PREFIX}11",
        "X-Client-IP": f"{FAKE_ADDRESS_PREFIX}12",
        "Forwarded": f"for={FAKE_ADDRESS_PREFIX}13",
        "X-Forwarded-Proto": "http",
    }
    underscore = {
        UNDERSCORE_NAMES[name]: f"{FAKE_ADDRESS_PREFIX}2{number}"
        for number, name in enumerate(ADDRESS_HEADERS)
    }
    underscore["X_Forwarded_Proto"] = "http"
    reports = []
    for spoofed in (hyphen, underscore):
        response = target.request("GET", "/", spoofed)
        try:
            reports.append(json.loads(response.body))
        except ValueError:
            if spoofed is underscore and 400 <= response.status < 500:
                # プロキシが、下線の名前のヘッダーのある要求を断った
                # （偽の値は、アプリに届かない。いちばん安全な作り）
                print(
                    f"下線の名前のヘッダーは、プロキシが断った"
                    f"（{response.status}。安全）"
                )
                continue
            report.check(
                False, "下見のアプリの応答（JSON）", str(response.status)
            )
            return
    seen = reports[0]
    print(f"REMOTE_ADDR：{seen.get('REMOTE_ADDR')!r}")
    candidates = []
    for name in ADDRESS_HEADERS:
        received = [
            r.get("headers", {}).get(environ_key(name)) for r in reports
        ]
        state = address_header_state(received, my_address)
        print(f"{name}：{received!r} … {state}")
        if state == "使える":
            candidates.append(name)
    print(f"CLIENT_ADDRESS_HEADER の候補：{candidates or 'なし'}")
    protos = [
        r.get("headers", {}).get("HTTP_X_FORWARDED_PROTO") for r in reports
    ]
    report.check(
        all(proto == "https" for proto in protos),
        "X-Forwarded-Proto が https に上書きされる（下線の名前を含む）",
        repr(protos),
    )
    report.check(
        bool(candidates),
        "接続元のヘッダーに、偽の値が届かず、この Mac のアドレスになる",
    )
    report.check(seen.get("workers") == 1, "uWSGI のワーカーが1つ",
                 repr(seen.get("workers")))
    python = str(seen.get("python", ""))
    print(f"Python：{python}、SQLite：{seen.get('sqlite')}")
    report.check(
        version_tuple(python) >= MIN_PYTHON,
        "Python 3.14.10 以上",
        repr(python),
    )
    filesystem = str(seen.get("home_filesystem"))
    report.check(
        not filesystem.startswith(("nfs", "cifs", "smb", "fuse", "9p")),
        f"ホームのファイルシステムがローカル（{filesystem}）",
        "ネットワークのファイルシステムでは、SQLite が壊れうる",
    )
    print(
        f"uWSGI の待ち受け：{seen.get('uwsgi_sockets')!r}"
        "（この行を Claude に伝える。アカウント名は <アカウント名> に"
        "置き換える。ほかの利用者から届くかを判断する）"
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
