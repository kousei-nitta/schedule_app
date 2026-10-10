from datetime import date

import pytest

from app.api_helpers import (
    INVALID_JSON_MESSAGE,
    MAX_ID,
    UNUSABLE_CHARACTER_MESSAGE,
)
from app.extensions import db
from app.models.semester import Semester


def create_semester(client, name, start_date, end_date):
    return client.post(
        "/api/semesters",
        json={
            "name": name,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


def assert_api_error(response, status, code, message, fields=None):
    assert response.status_code == status
    assert response.is_json
    assert response.json == {
        "error": {
            "code": code,
            "message": message,
            **({"fields": fields} if fields is not None else {}),
        }
    }


def test_empty_semester_list_is_json(client):
    response = client.get("/api/semesters")
    assert response.status_code == 200
    assert response.is_json
    assert response.json == []


def test_semester_creation_get_and_ordering(client):
    created = [
        create_semester(
            client,
            "2099年度 前期",
            "2099-04-06",
            "2099-07-20",
        ),
        create_semester(
            client,
            "2099年度 後期",
            "2099-09-21",
            "2099-12-27",
        ),
        create_semester(
            client,
            "2100年度 前期",
            "2099-12-01",
            "2100-03-31",
        ),
        create_semester(
            client,
            "2100年度 後期",
            "2099-12-01",
            "2100-03-31",
        ),
    ]

    expected_keys = {"id", "name", "start_date", "end_date"}
    created_objects = []
    for response, expected_name in zip(
        created,
        (
            "2099年度 前期",
            "2099年度 後期",
            "2100年度 前期",
            "2100年度 後期",
        ),
    ):
        assert response.status_code == 201
        assert set(response.json) == expected_keys
        assert isinstance(response.json["id"], int)
        assert response.json["name"] == expected_name
        created_objects.append(response.json)

    listing = client.get("/api/semesters")
    assert listing.status_code == 200
    assert [item["name"] for item in listing.json] == [
        "2100年度 後期",
        "2100年度 前期",
        "2099年度 後期",
        "2099年度 前期",
    ]
    assert client.get(
        f"/api/semesters/{created_objects[0]['id']}"
    ).json == created_objects[0]


@pytest.mark.parametrize(
    ("payload", "expected_fields"),
    [
        (
            {
                "name": "2026年度 前期",
                "start_date": "2026-04-01",
                "end_date": "2026-07-31",
            },
            {"name": "同じ名前の学期がすでに登録されています"},
        ),
        ({"name": "前期"}, {"name": "学期名は「2026年度 前期」の形式で指定してください"}),
        ({"name": "２０２６年度 前期"}, {"name": "学期名は「2026年度 前期」の形式で指定してください"}),
        ({"name": "2026年度 前期\n"}, {"name": "学期名は「2026年度 前期」の形式で指定してください"}),
        ({"name": " 2026年度 前期"}, {"name": "学期名は「2026年度 前期」の形式で指定してください"}),
        ({"name": "あ" * 51}, {"name": "学期名は50文字以内にしてください"}),
        (
            {},
            {
                "name": "学期名は必須です",
                "start_date": "開始日は必須です",
                "end_date": "終了日は必須です",
            },
        ),
        (
            {"name": 123, "start_date": 20260401, "end_date": None},
            {
                "name": "学期名は文字列で指定してください",
                "start_date": (
                    "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
                ),
                "end_date": "終了日は必須です",
            },
        ),
        (
            {
                "name": "2026年度 前期",
                "start_date": "20260401",
                "end_date": "2026-07-31",
            },
            {
                "start_date": (
                    "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
                )
            },
        ),
        (
            {
                "name": "2026年度 前期",
                "start_date": "2026/04/01",
                "end_date": "2026-07-31",
            },
            {
                "start_date": (
                    "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
                )
            },
        ),
        (
            {
                "name": "2026年度 前期",
                "start_date": "2026-4-1",
                "end_date": "2026-07-31",
            },
            {
                "start_date": (
                    "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
                )
            },
        ),
        (
            {
                "name": "2026年度 前期",
                "start_date": "2026-02-30",
                "end_date": "2026-07-31",
            },
            {
                "start_date": (
                    "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
                )
            },
        ),
        (
            {
                "name": "2026年度 前期",
                "start_date": "2026-04-01\n",
                "end_date": "2026-07-31",
            },
            {
                "start_date": (
                    "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
                )
            },
        ),
        (
            {
                "name": "2026年度 前期",
                "start_date": "2026-04-01",
                "end_date": "2026-04-01",
            },
            {"end_date": "終了日は開始日より後にしてください"},
        ),
        (
            {
                "name": "2026年度 前期",
                "start_date": "2026-04-01",
                "end_date": "2026-03-31",
            },
            {"end_date": "終了日は開始日より後にしてください"},
        ),
        (
            {
                "name": "2026年度 前期",
                "start_date": "2026-04-01",
                "end_date": "2026-07-31",
                "color": "red",
            },
            {"color": "この項目は指定できません"},
        ),
        (
            {
                "id": 5,
                "name": "2026年度 前期",
                "start_date": "2026-04-01",
                "end_date": "2026-07-31",
            },
            {"id": "この項目は指定できません"},
        ),
    ],
)
def test_invalid_semester_payloads_have_expected_fields(
    client, app, payload, expected_fields
):
    request_payload = payload
    if payload and set(payload) != {
        "name",
        "start_date",
        "end_date",
    }:
        request_payload = {
            "name": "2026年度 前期",
            "start_date": "2026-04-01",
            "end_date": "2026-07-31",
            **payload,
        }

    if expected_fields == {"name": "同じ名前の学期がすでに登録されています"}:
        with app.app_context():
            db.session.add(
                Semester(
                    name="2026年度 前期",
                    start_date=date(2026, 4, 1),
                    end_date=date(2026, 7, 31),
                )
            )
            db.session.commit()

    before_count = semester_count(app)
    response = client.post("/api/semesters", json=request_payload)
    assert_api_error(
        response,
        400,
        "validation_error",
        "入力内容に誤りがあります",
        expected_fields,
    )
    assert semester_count(app) == before_count


def semester_count(app):
    with app.app_context():
        return db.session.query(Semester).count()


@pytest.mark.parametrize("payload", [[], None, "abc", 123, True])
def test_non_object_semester_payload_has_no_fields(client, payload):
    if payload is None:
        response = client.post(
            "/api/semesters",
            data="null",
            content_type="application/json",
        )
    else:
        response = client.post("/api/semesters", json=payload)
    assert_api_error(
        response,
        400,
        "validation_error",
        "リクエストの本文は、JSONのオブジェクトにしてください",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "2026年度 前期\ud800"),
        ("name", "\ud800"),
        ("start_date", "2026-04-01\ud800"),
        ("end_date", "\udfff"),
    ],
)
def test_unusable_characters_in_semester_fields_are_rejected(
    client, app, field, value
):
    payload = {
        "name": "2026年度 前期",
        "start_date": "2026-04-01",
        "end_date": "2026-07-31",
    }
    payload[field] = value

    response = client.post("/api/semesters", json=payload)
    assert_api_error(
        response,
        400,
        "validation_error",
        "入力内容に誤りがあります",
        {field: UNUSABLE_CHARACTER_MESSAGE},
    )
    assert semester_count(app) == 0


def test_invalid_utf8_semester_body_is_invalid_json(client, app):
    before_count = semester_count(app)
    response = client.post(
        "/api/semesters",
        data=(
            b'{"name": "\xff", "start_date": "2026-04-01", '
            b'"end_date": "2026-07-31"}'
        ),
        content_type="application/json",
    )
    assert_api_error(
        response,
        400,
        "invalid_json",
        INVALID_JSON_MESSAGE,
    )
    assert semester_count(app) == before_count


def test_surrogate_pair_in_semester_name_is_format_error(client, app):
    before_count = semester_count(app)
    response = create_semester(
        client,
        "2026年度 前期😀",
        "2026-04-01",
        "2026-07-31",
    )
    assert_api_error(
        response,
        400,
        "validation_error",
        "入力内容に誤りがあります",
        {"name": "学期名は「2026年度 前期」の形式で指定してください"},
    )
    assert semester_count(app) == before_count


@pytest.mark.parametrize(
    ("data", "content_type"),
    [
        ('{"name":', "application/json"),
        ('{"name":"x"}', "text/plain"),
        ('{"name":"x"}', None),
    ],
)
def test_invalid_json_content(client, data, content_type):
    response = client.post(
        "/api/semesters",
        data=data,
        content_type=content_type,
    )
    assert_api_error(
        response,
        400,
        "invalid_json",
        (
            "リクエストの本文がJSONとして読めません。"
            "Content-Typeを application/json にして、JSONで送ってください"
        ),
    )


def test_json_content_type_with_charset_is_accepted(client):
    response = client.post(
        "/api/semesters",
        data=(
            '{"name":"2026年度 前期","start_date":"2026-04-01",'
            '"end_date":"2026-07-31"}'
        ),
        content_type="application/json; charset=utf-8",
    )
    assert response.status_code == 201


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/semesters/99999", "学期が見つかりません"),
        ("/api/semesters/0", "学期が見つかりません"),
        (f"/api/semesters/{MAX_ID}", "学期が見つかりません"),
        (f"/api/semesters/{MAX_ID + 1}", "URLが見つかりません"),
        ("/api/semesters/99999999999999999999", "URLが見つかりません"),
        ("/api/semesters/abc", "URLが見つかりません"),
        ("/api/semesters/-1", "URLが見つかりません"),
        ("/api/semesters/", "URLが見つかりません"),
        ("/api/unknown", "URLが見つかりません"),
        ("/api", "URLが見つかりません"),
    ],
)
def test_semester_and_url_not_found_responses(client, url, message):
    assert_api_error(
        client.get(url),
        404,
        "not_found",
        message,
    )


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("delete", "/api/semesters/1"),
        ("patch", "/api/semesters/1"),
        ("put", "/api/semesters"),
        ("post", "/api/semesters/1"),
    ],
)
def test_unsupported_semester_methods_return_json_405(client, method, url):
    response = getattr(client, method)(url)
    assert_api_error(
        response,
        405,
        "method_not_allowed",
        "このURLでは、そのメソッドは使えません",
    )


def test_regular_page_errors_remain_html_and_cors_is_disabled(client):
    assert client.get("/").content_type.startswith("text/html")
    assert client.get("/missing-page").content_type.startswith("text/html")
    assert client.post("/").content_type.startswith("text/html")

    response = client.get(
        "/api/semesters",
        headers={"Origin": "http://example.com"},
    )
    preflight = client.options(
        "/api/semesters",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    for result in (response, preflight):
        assert not any(
            name.lower().startswith("access-control-")
            for name, _ in result.headers
        )


def test_api_internal_error_is_json_and_regular_error_is_html(client, app):
    def fail():
        raise RuntimeError("intentional test failure")

    app.config["PROPAGATE_EXCEPTIONS"] = False
    app.add_url_rule("/api/test-error", "api_test_error", fail)
    app.add_url_rule("/test-error", "test_error", fail)

    assert_api_error(
        client.get("/api/test-error"),
        500,
        "server_error",
        "サーバーでエラーが発生しました",
    )
    assert client.get("/test-error").content_type.startswith("text/html")
