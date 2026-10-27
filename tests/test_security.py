"""セキュリティの守り（docs/architecture/security.md）のテスト。

- Hostヘッダーの検査（TRUSTED_HOSTS）
- セキュリティのヘッダー（CSPを含む）と、要求ごとのnonce
- 入れ子が深すぎるJSON
- テンプレートに、CSPで止まる書き方（インラインのスクリプトなど）がないこと
"""
import re
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.api_helpers import INVALID_JSON_MESSAGE
from app.extensions import db
from app.models.semester import Semester


TEMPLATE_DIRECTORY = (
    Path(__file__).resolve().parents[1] / "app" / "templates"
)

SEMESTER_PAYLOAD = {
    "name": "2099年度 前期",
    "start_date": "2099-04-06",
    "end_date": "2099-07-20",
}

BAD_REQUEST_BODY = {
    "error": {
        "code": "bad_request",
        "message": "リクエストを受け付けられません",
    }
}

# 信頼しない Host（悪意のあるサイトの名前を 127.0.0.1 に向けた場合など）
UNTRUSTED_HOSTS = [
    "evil.example",
    "evil.example:5001",
    # 信頼する名前で始まる・終わるだけの、別の名前
    "127.0.0.1.evil.example",
    "localhost.evil.example",
    "evil-localhost",
]


def semester_count(app) -> int:
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(Semester))


def nonce_in_policy(policy: str) -> str:
    match = re.search(r"'nonce-([^']+)'", policy)
    assert match is not None
    return match.group(1)


def csp_directives(policy: str) -> dict[str, list[str]]:
    """CSPの値を、「種類 → 許すものの一覧」の辞書にする。"""
    directives = {}
    for part in policy.split(";"):
        name, *sources = part.split()
        directives[name] = sources
    return directives


# --- Hostヘッダーの検査 ---


def test_trusted_hosts_are_local_names_only(app):
    assert app.config["TRUSTED_HOSTS"] == ["127.0.0.1", "localhost"]


@pytest.mark.parametrize(
    "host",
    ["127.0.0.1:5001", "127.0.0.1", "localhost:5001", "localhost"],
)
def test_trusted_hosts_are_accepted(client, host):
    api_response = client.get("/api/semesters", headers={"Host": host})
    page_response = client.get("/", headers={"Host": host})

    assert api_response.status_code == 200
    assert page_response.status_code == 200


@pytest.mark.parametrize("host", UNTRUSTED_HOSTS)
def test_untrusted_host_is_rejected_with_json_for_api(client, host):
    response = client.get("/api/semesters", headers={"Host": host})

    assert response.status_code == 400
    assert response.is_json
    assert response.json == BAD_REQUEST_BODY


@pytest.mark.parametrize("host", UNTRUSTED_HOSTS)
def test_untrusted_host_is_rejected_with_html_for_page(client, host):
    # 通常のHTMLページのエラーは、Flaskの標準のHTMLのまま
    response = client.get("/", headers={"Host": host})

    assert response.status_code == 400
    assert response.mimetype == "text/html"


@pytest.mark.parametrize("host", UNTRUSTED_HOSTS)
def test_untrusted_host_cannot_change_data(app, client, host):
    response = client.post(
        "/api/semesters",
        json=SEMESTER_PAYLOAD,
        headers={"Host": host},
    )

    assert response.status_code == 400
    assert response.json == BAD_REQUEST_BODY
    assert semester_count(app) == 0


def test_trusted_host_can_change_data(app, client):
    # 上のテストの比べる相手（同じ本文が、信頼する Host なら通る）
    response = client.post(
        "/api/semesters",
        json=SEMESTER_PAYLOAD,
        headers={"Host": "127.0.0.1:5001"},
    )

    assert response.status_code == 201
    assert semester_count(app) == 1


# --- セキュリティのヘッダー ---


@pytest.mark.parametrize(
    ("method", "url", "headers", "status"),
    [
        ("GET", "/", {}, 200),
        ("GET", "/api/semesters", {}, 200),
        ("GET", "/static/js/main.js", {}, 200),
        ("GET", "/static/css/style.css", {}, 200),
        ("GET", "/api/no-such-url", {}, 404),
        ("GET", "/no-such-page", {}, 404),
        ("DELETE", "/api/semesters", {}, 405),
        ("GET", "/api/semesters", {"Host": "evil.example"}, 400),
    ],
)
def test_security_headers_are_on_every_response(
    client, method, url, headers, status
):
    response = client.open(url, method=method, headers=headers)

    assert response.status_code == status
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "same-origin"
    assert "Content-Security-Policy" in response.headers


def test_security_headers_are_on_server_error(app, client):
    # 予期しない例外の500（JSON）にも付く
    def broken_view():
        raise RuntimeError("テストのための例外")

    app.add_url_rule("/api/test-broken", view_func=broken_view)
    app.config["PROPAGATE_EXCEPTIONS"] = False

    response = client.get("/api/test-broken")

    assert response.status_code == 500
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in response.headers


def test_security_headers_are_on_response_from_earlier_before_request(app):
    # nonce を作る before_request より先に、ほかの before_request が応答を
    # 返した場合（ログインのタスクで足す検査など）も、500にならず、
    # ヘッダーが付く
    def refuse_early():
        return "先に断る", 403

    app.before_request_funcs.setdefault(None, []).insert(0, refuse_early)

    response = app.test_client().get("/")

    assert response.status_code == 403
    assert response.headers["X-Frame-Options"] == "DENY"
    assert re.fullmatch(
        r"[A-Za-z0-9_-]{22}",
        nonce_in_policy(response.headers["Content-Security-Policy"]),
    )


def test_content_security_policy_directives(client):
    response = client.get("/")
    policy = response.headers["Content-Security-Policy"]
    nonce = nonce_in_policy(policy)

    assert csp_directives(policy) == {
        "default-src": ["'self'"],
        "script-src": [
            "'self'",
            "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/"
            "bootstrap.bundle.min.js",
            "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.21/"
            "index.global.min.js",
        ],
        "style-src": [
            "'self'",
            "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/"
            "bootstrap.min.css",
            f"'nonce-{nonce}'",
        ],
        "img-src": ["'self'", "data:"],
        "font-src": ["'self'", "data:"],
        "connect-src": ["'self'"],
        "object-src": ["'none'"],
        "base-uri": ["'none'"],
        "form-action": ["'self'"],
        "frame-ancestors": ["'none'"],
    }


def test_content_security_policy_never_allows_inline_or_eval(client):
    policy = client.get("/").headers["Content-Security-Policy"]

    assert "'unsafe-inline'" not in policy
    assert "'unsafe-eval'" not in policy
    # CDN（jsDelivr）の、ほかのファイルを読ませない（ファイルまで指定する）
    assert "https://cdn.jsdelivr.net " not in policy + " "
    assert "https://cdn.jsdelivr.net/npm/ " not in policy + " "


def test_page_passes_the_nonce_of_its_own_response(client):
    response = client.get("/")
    nonce = nonce_in_policy(response.headers["Content-Security-Policy"])
    html = response.get_data(as_text=True)

    # FullCalendarの <script> に、その応答のCSPと同じ nonce が付く
    assert re.search(
        r'<script src="[^"]*fullcalendar@[^"]*"[^>]* nonce="'
        + re.escape(nonce)
        + '"',
        html,
    )


def test_nonce_changes_for_every_request(client):
    nonces = {
        nonce_in_policy(client.get("/").headers["Content-Security-Policy"])
        for _ in range(5)
    }

    assert len(nonces) == 5


def test_nonce_is_long_random_text(client):
    nonce = nonce_in_policy(client.get("/").headers["Content-Security-Policy"])

    # secrets.token_urlsafe(16)：16バイトの乱数を、22文字の英数字・-・_ に
    assert re.fullmatch(r"[A-Za-z0-9_-]{22}", nonce)


def test_nonce_changes_within_one_app_context(app):
    # デモデータ（app/demo_data.py）は、1つのアプリのコンテキストの中で
    # 何度も要求を送る。その場合も、要求ごとに違う値になる
    with app.app_context():
        client = app.test_client()
        first = client.get("/").headers["Content-Security-Policy"]
        second = client.get("/").headers["Content-Security-Policy"]

    assert nonce_in_policy(first) != nonce_in_policy(second)


# --- 入れ子が深すぎるJSON ---


@pytest.mark.parametrize("opening", ["[", '{"name":'])
def test_too_deeply_nested_json_is_invalid_json(app, client, opening):
    # 100万段：Pythonの版（3.14 は 1万段でも読める）によらず、
    # json が RecursionError になる深さ
    depth = 1_000_000
    closing = "]" if opening == "[" else "}"
    body = opening * depth + "1" + closing * depth

    response = client.post(
        "/api/semesters",
        data=body,
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json == {
        "error": {"code": "invalid_json", "message": INVALID_JSON_MESSAGE}
    }
    assert semester_count(app) == 0


def test_too_deeply_nested_json_is_invalid_json_for_patch(client):
    # PATCH（read_patch_object）も、read_json_object を通る
    created = client.post("/api/semesters", json=SEMESTER_PAYLOAD)
    semester_id = created.json["id"]
    depth = 1_000_000

    response = client.patch(
        f"/api/semesters/{semester_id}",
        data="[" * depth + "]" * depth,
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_json"
    assert client.get(f"/api/semesters/{semester_id}").json["name"] == (
        SEMESTER_PAYLOAD["name"]
    )


# --- テンプレートの書き方 ---


def template_texts() -> dict[str, str]:
    """テンプレートの文を返す。コメント（Jinjaの {# #}、HTMLの <!-- -->）は
    除く（説明の中の「<style>」などの文字を、書き方の誤りと見ないため）。
    """
    texts = {
        str(path.relative_to(TEMPLATE_DIRECTORY)): re.sub(
            r"\{#.*?#\}|<!--.*?-->",
            "",
            path.read_text(encoding="utf-8"),
            flags=re.DOTALL,
        )
        # フォルダの中に置いたテンプレートも含める
        for path in sorted(TEMPLATE_DIRECTORY.rglob("*.html"))
    }
    assert texts  # テンプレートが見つからないまま、空振りしないように
    return texts


def test_templates_have_no_inline_scripts():
    # CSPは、インラインのスクリプトを止める（src のない <script>）
    for name, text in template_texts().items():
        for tag in re.findall(r"<script\b[^>]*>", text):
            assert " src=" in tag, f"{name}: {tag}"


def test_templates_have_no_inline_styles_or_event_attributes():
    # CSPは、<style>・style 属性・onclick などの属性も止める
    for name, text in template_texts().items():
        assert re.search(r"<style\b", text) is None, name
        assert re.search(r"\sstyle\s*=", text) is None, name
        assert re.search(r"\son[a-z]+\s*=", text) is None, name


def test_cdn_files_in_templates_are_allowed_by_policy(client):
    # base.html のCDNのURLを変えたのに、CSP（app/security.py）を
    # 変え忘れると、画面が動かなくなるため
    policy = client.get("/").headers["Content-Security-Policy"]
    allowed = csp_directives(policy)
    cdn_urls = []
    for text in template_texts().values():
        for tag in re.findall(r"<(?:script|link)\b[^>]*>", text):
            match = re.search(r'(?:src|href)="(https://[^"]+)"', tag)
            if match is None:
                continue
            if tag.startswith("<script"):
                directive = "script-src"
            else:
                directive = "style-src"
            cdn_urls.append(match.group(1))
            assert match.group(1) in allowed[directive], tag

    assert len(cdn_urls) == 3  # Bootstrap（CSS・JS）と FullCalendar
