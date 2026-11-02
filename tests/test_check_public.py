"""本番の点検のスクリプト（scripts/check_public.py。Task 026）。

本物の本番には届かないため、プロキシの代わりをする偽の Target で、本番の
設定のアプリ（fixture production_app）に送り、スクリプトの確かめと、
アプリの振る舞いが合っていることを確かめる。判定の関数は、作った応答で
確かめる。
"""
import pytest

from scripts import check_public
from scripts.check_public import (
    Report,
    Response,
    Target,
    check_basics,
    check_logged_in,
    check_rate_limit,
    cookie_problems,
    leaked_markers,
    security_header_problems,
)
from tests.auth_support import TEST_PASSWORD, TEST_USERNAME
from tests.production_support import OWNER_ADDRESS, PUBLIC_HOST, PUBLIC_ORIGIN


class ProxyTarget(Target):
    """ホストのプロキシの代わり：http は https へ移し、https はアプリへ
    渡す（X-Real-IP を、本当の接続元で上書きし、X-Forwarded-Proto を付ける）。
    """

    def __init__(self, app):
        super().__init__(PUBLIC_ORIGIN)
        self.client = app.test_client(use_cookies=False)

    def request(self, method, path, headers=None, body=None, *, https=True):
        if not https:
            location = f"https://{self.host}{path}"
            return Response(301, [("Location", location)], b"")
        sent = dict(headers or {})
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
    assert isinstance(report["home_filesystem"], str)
