"""本番の点検のスクリプト（scripts/check_public.py。Task 026）。

本物の本番には届かないため、プロキシの代わりをする偽の Target で、本番の
設定のアプリ（fixture production_app）に送り、スクリプトの確かめと、
アプリの振る舞いが合っていることを確かめる。判定の関数は、作った応答で
確かめる。
"""
import ipaddress
import json

import pytest

from scripts import check_public
from scripts.check_public import (
    Report,
    Response,
    Target,
    check_basics,
    check_logged_in,
    address_header_state,
    check_rate_limit,
    cookie_problems,
    probe_headers,
    proto_state,
    remote_addr_state,
    leaked_markers,
    security_header_problems,
)
from tests.auth_support import TEST_PASSWORD, TEST_USERNAME
from tests.production_support import (
    OWNER_ADDRESS,
    PUBLIC_HOST,
    PUBLIC_ORIGIN,
    ProxyTarget,
)


def test_basic_checks_pass_against_production_app(production_app, capsys):
    report = Report()

    check_basics(ProxyTarget(production_app), report)

    assert report.failures == [], capsys.readouterr().out


def test_logged_in_checks_pass(production_app, monkeypatch, capsys):
    answers = iter([TEST_USERNAME, TEST_PASSWORD])
    monkeypatch.setattr(
        check_public.getpass, "getpass", lambda _: next(answers)
    )
    report = Report()

    check_logged_in(ProxyTarget(production_app), report)

    output = capsys.readouterr().out
    assert report.failures == [], output
    assert "✓ Cookie がある：__Host-schedule_device" in output


def test_rate_limit_check_passes(production_app, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    report = Report()

    check_rate_limit(ProxyTarget(production_app), report)

    assert report.failures == [], capsys.readouterr().out


class SpoofableTarget(ProxyTarget):
    """接続元のヘッダーを上書きしない（危ない）プロキシ。"""

    def request(self, method, path, headers=None, body=None, *, https=True):
        sent = dict(headers or {})
        sent.setdefault("X-Real-IP", OWNER_ADDRESS)
        sent["X-Forwarded-Proto"] = "https"
        response = self.client.open(
            path,
            method=method,
            headers=sent,
            data=body,
            base_url=f"http://{PUBLIC_HOST}",
        )
        return Response(
            response.status_code, list(response.headers.items()), b""
        )


def test_rate_limit_check_finds_spoofable_proxy(production_app, monkeypatch):
    # プロキシが X-Real-IP を上書きしないと、11回目も 429 にならない
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    report = Report()

    check_rate_limit(SpoofableTarget(production_app), report)

    assert len(report.failures) == 1


# --- 判定の関数 ---

GOOD_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "X-Robots-Tag": "noindex, nofollow",
    "Cache-Control": "no-store",
    "Strict-Transport-Security": "max-age=31536000",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'none'; object-src 'none'; "
        "frame-ancestors 'none'"
    ),
    "Permissions-Policy": "camera=(), microphone=()",
}


def test_good_headers_have_no_problems():
    assert security_header_problems(GOOD_HEADERS, login_page=True) == []


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        ({"Strict-Transport-Security": "max-age=300"}, "Strict-Transport"),
        ({"X-Frame-Options": "SAMEORIGIN"}, "X-Frame-Options"),
        ({"Server": "nginx/1.24.0"}, "Server"),
        ({"X-Powered-By": "PHP"}, "X-Powered-By"),
        (
            {
                "Content-Security-Policy": GOOD_HEADERS[
                    "Content-Security-Policy"
                ]
                + "; style-src 'unsafe-inline'"
            },
            "unsafe-inline",
        ),
    ],
)
def test_header_problems_are_found(change, problem):
    problems = security_header_problems(GOOD_HEADERS | change)

    assert any(problem in text for text in problems)


def test_server_name_without_version_is_fine():
    headers = GOOD_HEADERS | {"Server": "alwaysdata"}

    assert security_header_problems(headers) == []


def test_cookie_problems():
    good = "__Host-a=x; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=9"

    assert cookie_problems(good, "__Host-a") == []
    bad = "a=x; HttpOnly; SameSite=Lax; Path=/app; Domain=example.com"
    assert cookie_problems(bad, "__Host-a") == [
        "名前が a（__Host-a のはず）",
        "Secure がない",
        "SameSite=Strict でない",
        "Path=/ でない",
        "Domain がある",
    ]


def test_leaked_markers():
    assert leaked_markers(b"SQLite format 3\x00...") == ["SQLite format 3"]
    assert leaked_markers(b"<html>login</html>") == []


@pytest.mark.parametrize(
    "url",
    [
        "http://a.example",
        "https://a.example/",
        "https://A.example",
        "a.example",
    ],
)
def test_target_needs_https_origin(url):
    with pytest.raises(SystemExit):
        Target(url)


# --- 下見の道具（scripts/echo_headers_wsgi.py） ---


def test_echo_app_reports_headers_but_hides_cookies():
    import json

    from scripts.echo_headers_wsgi import application

    statuses = []
    body = b"".join(
        application(
            {
                "REMOTE_ADDR": "10.0.0.1",
                "wsgi.url_scheme": "http",
                "HTTP_X_REAL_IP": "203.0.113.5",
                "HTTP_COOKIE": "__Host-schedule_session=secret-token",
                "HTTP_AUTHORIZATION": "Basic secret",
            },
            lambda status, headers: statuses.append((status, headers)),
        )
    )

    report = json.loads(body)
    assert statuses[0][0] == "200 OK"
    assert ("Cache-Control", "no-store") in statuses[0][1]
    assert report["REMOTE_ADDR"] == "10.0.0.1"
    assert report["headers"]["HTTP_X_REAL_IP"] == "203.0.113.5"
    assert b"secret" not in body
    assert report["workers"] is None
    assert report["uwsgi_sockets"] is None
    assert isinstance(report["home_filesystem"], str)


# --- 作業中の道具（scripts/maintenance_wsgi.py） ---


def test_maintenance_app_answers_503_and_shows_nothing():
    # alwaysdata には、サイトを止める機能がないため、作業の間は、これを
    # サイトの入口にする（docs/development/deploy.md）
    from scripts.maintenance_wsgi import application

    seen = []
    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/login",
        "HTTP_COOKIE": "secret-cookie",
        "HTTP_X_REAL_IP": "203.0.113.5",
    }
    body = b"".join(
        application(environ, lambda status, headers: seen.append(
            (status, dict(headers))
        ))
    )

    status, headers = seen[0]
    assert status == "503 Service Unavailable"
    assert headers["Cache-Control"] == "no-store"
    assert headers["Content-Length"] == str(len(body))
    assert "作業中" in body.decode("utf-8")
    # 要求の中身を、何も返さない
    assert b"secret" not in body
    assert b"203.0.113.5" not in body


# --- 下見（--probe） ---

MAC_ADDRESS = "198.51.100.77"


class ProbeTarget(Target):
    """下見の道具を置いたサイトの代わり。proxy（送ったヘッダー → アプリに
    届くヘッダーの組の一覧）で、プロキシの振る舞いを決める。同じ名前に
    なるヘッダーは、uWSGI と同じく「, 」でつなぐ。"""

    def __init__(self, proxy, python="3.14.10", remote_addr="fd00::1"):
        super().__init__(PUBLIC_ORIGIN)
        self.proxy = proxy
        self.python = python
        self.remote_addr = remote_addr

    def request(self, method, path, headers=None, body=None, *, https=True):
        received = {}
        for name, value in self.proxy(dict(headers or {})):
            key = "HTTP_" + name.upper().replace("-", "_")
            if key in received:
                received[key] += ", " + value
            else:
                received[key] = value
        report = {
            "REMOTE_ADDR": self.remote_addr,
            "headers": received,
            "workers": 1,
            "python": self.python,
            "sqlite": "3.50.0",
            "home_filesystem": "ext4",
            "uwsgi_sockets": {"socket": ["/run/uwsgi/site.sock"]},
        }
        return Response(200, [], json.dumps(report).encode())


def proxy_added(real_ip=MAC_ADDRESS):
    # プロキシが付けるヘッダー（alwaysdata の資料：X-Real-IP と
    # X-Forwarded-Proto）
    return [("X-Real-IP", real_ip), ("X-Forwarded-Proto", "https")]


def good_proxy(headers):
    # 下線の名前を捨て、X-Real-IP と X-Forwarded-Proto を上書きする
    kept = [
        (k, v) for k, v in headers.items()
        if "_" not in k and k not in ("X-Real-IP", "X-Forwarded-Proto")
    ]
    return kept + proxy_added()


def merging_proxy(headers):
    # alwaysdata の下見で見えた振る舞い：ふつうの名前は上書きし、下線の
    # 名前は、そのまま通す（uWSGI が、本物の値とつなぐ）
    kept = [
        (k, v) for k, v in headers.items()
        if k not in ("X-Real-IP", "X-Forwarded-Proto")
    ]
    return kept + proxy_added()


def proxy_not_overwriting(headers):
    # 利用者が送った X-Real-IP・X-Forwarded-Proto を、そのまま渡す（偽れる）
    kept = list(headers.items())
    names = set(headers)
    return kept + [
        pair for pair in proxy_added() if pair[0] not in names
    ]


def proxy_trusting_forwarded_for(headers):
    # 利用者が送った X-Forwarded-For から、X-Real-IP を作る（偽れる）
    kept = [(k, v) for k, v in good_proxy(headers) if k != "X-Real-IP"]
    return kept + [("X-Real-IP", headers.get("X-Forwarded-For", MAC_ADDRESS))]


def run_probe(monkeypatch, target, address=MAC_ADDRESS):
    monkeypatch.setattr("builtins.input", lambda _: address)
    report = Report()
    probe_headers(target, report)
    return report


def test_probe_passes_with_good_proxy(monkeypatch, capsys):
    report = run_probe(monkeypatch, ProbeTarget(good_proxy))

    output = capsys.readouterr().out
    assert report.failures == [], output
    assert "CLIENT_ADDRESS_HEADER の候補：['X-Real-IP']" in output
    assert "/run/uwsgi/site.sock" in output


def test_probe_passes_with_merging_proxy(monkeypatch, capsys):
    # 下線の名前が、uWSGI で本物の値と混ざる（alwaysdata で見えた形）。
    # アプリは、値が1つでないと400で断るので、偽れない
    report = run_probe(monkeypatch, ProbeTarget(merging_proxy))

    output = capsys.readouterr().out
    assert report.failures == [], output
    assert "CLIENT_ADDRESS_HEADER の候補：['X-Real-IP']" in output
    assert "下線の名前は混ざり、アプリが400で断る" in output
    assert "'http, https'" in output


@pytest.mark.parametrize(
    "proxy", [proxy_not_overwriting, proxy_trusting_forwarded_for]
)
def test_probe_finds_fake_addresses(monkeypatch, capsys, proxy):
    # 偽の値が届くヘッダーは、候補にしない（M3。別の目のレビュー）
    report = run_probe(monkeypatch, ProbeTarget(proxy))

    assert "候補：なし" in capsys.readouterr().out
    assert report.failures


def test_probe_needs_the_mac_address(monkeypatch, capsys):
    # 値が、この Mac の公開のアドレスでなければ、候補にしない
    report = run_probe(monkeypatch, ProbeTarget(good_proxy), "203.0.113.1")

    assert "候補：なし" in capsys.readouterr().out
    assert report.failures


def test_probe_prefers_remote_addr_when_it_is_the_mac(monkeypatch, capsys):
    # X-Real-IP が混ざった値のときも、REMOTE_ADDR が Mac のアドレスの
    # まま（ヘッダーの写しでない）なら、REMOTE_ADDR を使える
    report = run_probe(
        monkeypatch, ProbeTarget(merging_proxy, remote_addr=MAC_ADDRESS)
    )

    output = capsys.readouterr().out
    assert report.failures == [], output
    assert "候補：['REMOTE_ADDR', 'X-Real-IP']" in output


def test_probe_cannot_tell_remote_addr_from_same_header(monkeypatch, capsys):
    # 下線の名前を捨てるプロキシでは、REMOTE_ADDR と X-Real-IP が同じ値に
    # なり、写しかどうかを見分けられない。REMOTE_ADDR は選ばない
    report = run_probe(
        monkeypatch, ProbeTarget(good_proxy, remote_addr=MAC_ADDRESS)
    )

    output = capsys.readouterr().out
    assert report.failures == [], output
    assert "写しと見分けられない" in output
    assert "候補：['X-Real-IP']" in output


MAC = MAC_ADDRESS
MAC_IP = [ipaddress.ip_address(MAC_ADDRESS)]


@pytest.mark.parametrize(
    ("hyphen", "underscore", "expected"),
    [
        (MAC, MAC, "使える"),
        (MAC, f"192.0.2.20, {MAC}", "使える（下線の名前は混ざり"),
        (MAC, f"{MAC}, 192.0.2.20", "使える（下線の名前は混ざり"),
        (MAC, "192.0.2.20", "下線の名前で偽れる"),
        (MAC, "192.0.2.20, 192.0.2.21", "下線の名前で偽れる"),
        (MAC, None, "届かない"),
        (f"192.0.2.10, {MAC}", MAC, "偽の値が届く"),
        ("192.0.2.10", MAC, "偽の値が届く"),
        (None, MAC, "届かない"),
        ("203.0.113.1", "203.0.113.1", "この Mac のアドレスと違う"),
    ],
)
def test_address_header_state(hyphen, underscore, expected):
    assert address_header_state(hyphen, underscore, MAC_IP).startswith(
        expected
    )


def test_address_header_state_when_proxy_refused_underscores():
    # 下線の名前の要求を、プロキシが断った（偽の値は届かない）
    state = address_header_state(MAC, None, MAC_IP, underscore_sent=False)

    assert state == "使える"


@pytest.mark.parametrize(
    ("hyphen", "underscore", "safe"),
    [
        ("https", "https", True),
        ("https", "http, https", True),
        ("https", "https, http", True),
        ("https", "http", False),
        ("https", None, False),
        ("http, https", "https", False),
        ("http", "https", False),
    ],
)
def test_proto_state(hyphen, underscore, safe):
    assert (proto_state(hyphen, underscore) is None) is safe


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([MAC, MAC], "使える"),
        (["fd00::1", "fd00::1"], "内部のアドレス（プロキシ）。毎回同じ"),
        (["fd00::1", "fd00::2"], "内部のアドレス（プロキシ）。要求ごとに違う"),
        (["203.0.113.9", "203.0.113.9"], "そのほか"),
        ([None, None], "そのほか"),
    ],
)
def test_remote_addr_state(values, expected):
    assert remote_addr_state(values, MAC_IP) == expected


def test_probe_refuses_text_that_is_not_an_address(monkeypatch):
    report = run_probe(monkeypatch, ProbeTarget(good_proxy), "my mac")

    assert report.failures == ["この Mac の公開のアドレス"]


def test_probe_needs_new_enough_python(monkeypatch):
    report = run_probe(monkeypatch, ProbeTarget(good_proxy, "3.14.8"))

    assert report.failures == ["Python 3.14.9 以上"]


def test_probe_accepts_python_3_14_9_with_a_note(monkeypatch, capsys):
    # alwaysdata が 3.14.10 を用意するまでは、3.14.9 で進める
    # （docs/development/deploy.md の「Python の版」）
    report = run_probe(monkeypatch, ProbeTarget(good_proxy, "3.14.9"))

    assert report.failures == []
    assert "3.14.10 より古い" in capsys.readouterr().out


def test_probe_has_no_note_for_python_3_14_10(monkeypatch, capsys):
    report = run_probe(monkeypatch, ProbeTarget(good_proxy, "3.14.10"))

    assert report.failures == []
    assert "3.14.10 より古い" not in capsys.readouterr().out


def test_rate_limit_check_finds_proxy_keeping_underscores(
    production_app, monkeypatch, capsys
):
    # 下線の名前を捨てないプロキシでは、偽の接続元が届き、11回目も
    # 429 にならない
    class UnderscoreTarget(ProxyTarget):
        def request(self, method, path, headers=None, body=None, **kwargs):
            sent = dict(headers or {})
            response = self.client.open(
                path,
                method=method,
                headers={"X-Forwarded-Proto": "https"}
                | {k: v for k, v in sent.items() if "_" in k}
                | {k: v for k, v in sent.items() if k == "Origin"},
                data=body,
                content_type=sent.get("Content-Type"),
                base_url=f"http://{PUBLIC_HOST}",
            )
            return Response(response.status_code, [], b"")

    monkeypatch.setattr("builtins.input", lambda _: "yes")
    report = Report()

    check_rate_limit(UnderscoreTarget(production_app), report)

    # 断られた（400）のではなく、偽の接続元で、試せてしまった（401）
    assert "下線の名前で偽っても、試せない（400 か 429）" in report.failures
    assert "[401, 401, 401]" in capsys.readouterr().out


def test_rate_limit_check_passes_with_merging_proxy(
    production_app, monkeypatch, capsys
):
    # alwaysdata で見えた形（下線の名前を捨てないが、uWSGI が本物の値と
    # つなぐ）。1回目の点検は 429、2回目は、アプリが400で断る
    class MergingProxyTarget(ProxyTarget):
        keep_underscores = True

    monkeypatch.setattr("builtins.input", lambda _: "yes")
    report = Report()

    check_rate_limit(MergingProxyTarget(production_app), report)

    output = capsys.readouterr().out
    assert report.failures == [], output
    assert "[400, 400, 400]" in output


def test_probe_compares_ipv6_by_64(monkeypatch, capsys):
    # Mac は、接続ごとに一時的な IPv6 のアドレスを使いうる。同じ /64 なら、
    # 同じ接続元とみなす（アプリの数え方と同じ）
    def ipv6_proxy(headers):
        kept = [(k, v) for k, v in good_proxy(headers) if k != "X-Real-IP"]
        return kept + [("X-Real-IP", "2001:db8:1:2::abcd")]

    report = run_probe(
        monkeypatch, ProbeTarget(ipv6_proxy), "2001:db8:1:2::1234"
    )

    assert report.failures == [], capsys.readouterr().out


def test_probe_explains_ipv4_and_ipv6_mismatch(monkeypatch, capsys):
    # Mac のアドレスに IPv6 だけを入れたが、届いたのは IPv4（安全な側の
    # 失敗。IPv4 のアドレスも入れるよう表示する）
    report = run_probe(monkeypatch, ProbeTarget(good_proxy), "2001:db8::1")

    assert "IPv4 で届いた（この Mac の IPv4 のアドレスも" in (
        capsys.readouterr().out
    )
    assert report.failures


MAC_IPV6 = "2001:db8:7:8::1"


def ipv4_then_ipv6_proxy():
    # 1回目は IPv4、2回目は IPv6 で届く（alwaysdata の下見で見えた形。
    # Mac が両方のアドレスを持つ）
    calls = []

    def proxy(headers):
        calls.append(None)
        real_ip = MAC_ADDRESS if len(calls) == 1 else MAC_IPV6
        kept = [
            (k, v) for k, v in headers.items()
            if k not in ("X-Real-IP", "X-Forwarded-Proto")
        ]
        return kept + proxy_added(real_ip)

    return proxy


def test_probe_accepts_both_mac_addresses(monkeypatch, capsys):
    # IPv4 と IPv6 の両方を入れれば、どちらで届いても、Mac とみなす
    report = run_probe(
        monkeypatch,
        ProbeTarget(ipv4_then_ipv6_proxy()),
        f"{MAC_ADDRESS} {MAC_IPV6}",
    )

    output = capsys.readouterr().out
    assert report.failures == [], output
    assert "CLIENT_ADDRESS_HEADER の候補：['X-Real-IP']" in output


def test_probe_needs_both_mac_addresses_when_both_are_used(
    monkeypatch, capsys
):
    # IPv6 だけを入れると、IPv4 で届いた1回目が合わない（下見で見えた ✗）
    report = run_probe(
        monkeypatch, ProbeTarget(ipv4_then_ipv6_proxy()), MAC_IPV6
    )

    assert "IPv4 で届いた" in capsys.readouterr().out
    assert report.failures


class CopyingRemoteAddrTarget(ProbeTarget):
    """ホストの uWSGI が、X-Real-IP の値を REMOTE_ADDR に写す（alwaysdata
    の下見で見えた形。混ざった値も、そのまま写る）。"""

    def request(self, method, path, headers=None, body=None, *, https=True):
        response = super().request(method, path, headers, body, https=https)
        report = json.loads(response.body)
        report["REMOTE_ADDR"] = report["headers"].get("HTTP_X_REAL_IP")
        return Response(200, [], json.dumps(report).encode())


def test_probe_does_not_prefer_remote_addr_copied_from_header(
    monkeypatch, capsys
):
    report = run_probe(monkeypatch, CopyingRemoteAddrTarget(merging_proxy))

    output = capsys.readouterr().out
    assert report.failures == [], output
    assert "X-Real-IP の写し" in output
    assert "CLIENT_ADDRESS_HEADER の候補：['X-Real-IP']" in output


@pytest.mark.parametrize(
    "text", ["", "my mac", "198.51.100.1 198.51.100.2 198.51.100.3"]
)
def test_probe_refuses_wrong_mac_addresses(monkeypatch, text):
    report = run_probe(monkeypatch, ProbeTarget(good_proxy), text)

    assert report.failures == ["この Mac の公開のアドレス"]


class RefusingUnderscoreTarget(ProbeTarget):
    """下線の名前のヘッダーのある要求を、プロキシが400で断る。"""

    def request(self, method, path, headers=None, body=None, *, https=True):
        if any("_" in name for name in (headers or {})):
            return Response(400, [], b"<h1>Bad Request</h1>")
        return super().request(method, path, headers, body, https=https)


def test_probe_accepts_proxy_refusing_underscores(monkeypatch, capsys):
    report = run_probe(monkeypatch, RefusingUnderscoreTarget(good_proxy))

    output = capsys.readouterr().out
    assert report.failures == [], output
    assert "プロキシが断った（400。安全）" in output
    assert "CLIENT_ADDRESS_HEADER の候補：['X-Real-IP']" in output
