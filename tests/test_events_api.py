from datetime import date, time

import pytest
from sqlalchemy import func, select

from app.api_helpers import MAX_ID
from app.extensions import db
from app.models.event import Event
from app.models.semester import Semester
from app.models.subject import Subject
from tests.auth_support import TEST_USER_ID


START_FORMAT_MESSAGE = (
    "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
)
END_FORMAT_MESSAGE = (
    "終了日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
)
APRIL_QUERY = "start_date=2026-04-01&end_date=2026-04-30"


def make_semester(app, name="2026年度 前期"):
    with app.app_context():
        semester = Semester(
            user_id=TEST_USER_ID,
            name=name,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 7, 31),
        )
        db.session.add(semester)
        db.session.commit()
        return semester.id


def make_subject(app, semester_id, subject_name="授業"):
    """予定を作らずに、授業の行だけを作る（ORMで直接作る）。"""
    with app.app_context():
        subject = Subject(
            user_id=TEST_USER_ID,
            semester_id=semester_id,
            subject_name=subject_name,
            weekday=0,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        db.session.add(subject)
        db.session.commit()
        return subject.id


def make_event(
    app,
    event_date,
    start_time=time(9, 0),
    *,
    category="other",
    subject_id=None,
    title="予定",
    employer=None,
    is_generated=False,
):
    """予定の行を、ORMで直接作る（自動生成の予定や、カテゴリにない項目を
    持つ予定も作れるように、APIを使わない）。"""
    with app.app_context():
        event = Event(
            user_id=TEST_USER_ID,
            subject_id=subject_id,
            category=category,
            date=event_date,
            start_time=start_time,
            end_time=time(start_time.hour + 1, start_time.minute),
            title=title,
            employer=employer,
            is_generated=is_generated,
        )
        db.session.add(event)
        db.session.commit()
        return event.id


def event_ids(response):
    assert response.status_code == 200
    return [item["id"] for item in response.json]


def assert_validation_error(response, fields):
    assert response.status_code == 400
    assert response.json == {
        "error": {
            "code": "validation_error",
            "message": "入力内容に誤りがあります",
            "fields": fields,
        }
    }


def event_count(app):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(Event))


# --- 一覧（GET /api/events）：期間の中の予定 ---


def test_empty_event_list_returns_empty_array(client):
    response = client.get(f"/api/events?{APRIL_QUERY}")

    assert response.status_code == 200
    assert response.json == []


def test_event_list_returns_all_fields_of_each_event(client, app):
    semester_id = make_semester(app)
    subject_id = make_subject(app, semester_id)
    with app.app_context():
        class_event = Event(
            user_id=TEST_USER_ID,
            subject_id=subject_id,
            category="class",
            date=date(2026, 4, 6),
            start_time=time(9, 0),
            end_time=time(10, 30),
            title="プログラミング基礎",
            room="3号館201",
            notes="教科書を持参",
            is_generated=True,
        )
        part_time_event = Event(
            user_id=TEST_USER_ID,
            category="part_time",
            date=date(2026, 4, 7),
            start_time=time(17, 0),
            end_time=time(21, 45),
            title="倉庫の仕分け",
            employer="派遣会社A",
        )
        db.session.add_all([class_event, part_time_event])
        db.session.commit()
        class_event_id = class_event.id
        part_time_event_id = part_time_event.id

    response = client.get(f"/api/events?{APRIL_QUERY}")

    assert response.status_code == 200
    assert response.json == [
        {
            "id": class_event_id,
            "subject_id": subject_id,
            "category": "class",
            "date": "2026-04-06",
            "start_time": "09:00",
            "end_time": "10:30",
            "title": "プログラミング基礎",
            "room": "3号館201",
            "employer": None,
            "notes": "教科書を持参",
            "is_generated": True,
        },
        {
            "id": part_time_event_id,
            "subject_id": None,
            "category": "part_time",
            "date": "2026-04-07",
            "start_time": "17:00",
            "end_time": "21:45",
            "title": "倉庫の仕分け",
            "room": None,
            "employer": "派遣会社A",
            "notes": None,
            "is_generated": False,
        },
    ]


def test_event_list_includes_both_ends_and_excludes_outside(client, app):
    make_event(app, date(2026, 3, 31))
    first_day = make_event(app, date(2026, 4, 1))
    middle_day = make_event(app, date(2026, 4, 15))
    last_day = make_event(app, date(2026, 4, 30))
    make_event(app, date(2026, 5, 1))

    response = client.get(f"/api/events?{APRIL_QUERY}")

    assert event_ids(response) == [first_day, middle_day, last_day]


def test_event_list_orders_by_date_start_time_and_id(client, app):
    second_day = make_event(app, date(2026, 4, 2), time(9, 0))
    first_day_ten = make_event(app, date(2026, 4, 1), time(10, 0))
    first_day_nine_a = make_event(app, date(2026, 4, 1), time(9, 0))
    first_day_nine_b = make_event(app, date(2026, 4, 1), time(9, 0))

    response = client.get(f"/api/events?{APRIL_QUERY}")

    assert event_ids(response) == [
        first_day_nine_a,
        first_day_nine_b,
        first_day_ten,
        second_day,
    ]


def test_same_start_and_end_date_returns_only_that_day(client, app):
    make_event(app, date(2026, 4, 14))
    target = make_event(app, date(2026, 4, 15))
    make_event(app, date(2026, 4, 16))

    response = client.get(
        "/api/events?start_date=2026-04-15&end_date=2026-04-15"
    )

    assert event_ids(response) == [target]


def test_event_list_includes_all_categories_and_semesters(client, app):
    first_semester = make_semester(app)
    second_semester = make_semester(app, "2026年度 後期")
    first_subject = make_subject(app, first_semester)
    second_subject = make_subject(app, second_semester)
    expected = [
        make_event(
            app,
            date(2026, 4, 6),
            category="class",
            subject_id=first_subject,
            is_generated=True,
        ),
        make_event(
            app,
            date(2026, 4, 7),
            category="class",
            subject_id=second_subject,
            is_generated=True,
        ),
        make_event(
            app,
            date(2026, 4, 8),
            category="class",
            subject_id=first_subject,
        ),
        make_event(app, date(2026, 4, 9), category="part_time"),
        make_event(app, date(2026, 4, 10), category="other"),
    ]

    response = client.get(f"/api/events?{APRIL_QUERY}")

    assert event_ids(response) == expected


def test_unknown_queries_including_category_are_ignored(client, app):
    class_event = make_event(app, date(2026, 4, 6), category="class")
    part_time_event = make_event(app, date(2026, 4, 7), category="part_time")

    response = client.get(
        f"/api/events?{APRIL_QUERY}&category=class&semester_id=1&foo=bar"
    )

    assert event_ids(response) == [class_event, part_time_event]


def test_event_list_returns_events_generated_by_subject_registration(
    client, app
):
    semester_id = make_semester(app)
    created = client.post(
        "/api/subjects",
        json={
            "semester_id": semester_id,
            "subject_name": "プログラミング基礎",
            "weekday": 0,
            "start_time": "09:00",
            "end_time": "10:30",
        },
    )
    assert created.status_code == 201

    response = client.get(f"/api/events?{APRIL_QUERY}")

    assert response.status_code == 200
    assert [item["date"] for item in response.json] == [
        "2026-04-06",
        "2026-04-13",
        "2026-04-20",
        "2026-04-27",
    ]
    for item in response.json:
        assert item["subject_id"] == created.json["id"]
        assert item["category"] == "class"
        assert item["start_time"] == "09:00"
        assert item["end_time"] == "10:30"
        assert item["title"] == "プログラミング基礎"
        assert item["is_generated"] is True


def test_long_period_has_no_upper_limit(client, app):
    first = make_event(app, date(2026, 4, 1))
    second = make_event(app, date(2030, 1, 1))

    response = client.get(
        "/api/events?start_date=0001-01-01&end_date=9999-12-31"
    )

    assert event_ids(response) == [first, second]


# --- 一覧（GET /api/events）：クエリの検証 ---


@pytest.mark.parametrize(
    ("query", "fields"),
    [
        (
            "",
            {
                "start_date": "開始日は必須です",
                "end_date": "終了日は必須です",
            },
        ),
        (
            "?start_date=2026-04-01",
            {"end_date": "終了日は必須です"},
        ),
        (
            "?end_date=2026-04-30",
            {"start_date": "開始日は必須です"},
        ),
    ],
)
def test_missing_date_queries_are_validation_errors(client, query, fields):
    response = client.get(f"/api/events{query}")

    assert_validation_error(response, fields)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "2026-4-01",
        "2026/04/01",
        "20260401",
        "2026-02-30",
        "2026-13-01",
        "%202026-04-01",
        "2026-04-01T00:00",
        "%EF%BC%92026-04-01",
        "%ED%A0%80",
    ],
)
def test_malformed_start_date_query_is_validation_error(client, value):
    response = client.get(
        f"/api/events?start_date={value}&end_date=2026-04-30"
    )

    assert_validation_error(response, {"start_date": START_FORMAT_MESSAGE})


@pytest.mark.parametrize("value", ["", "2026-04-31", "abc"])
def test_malformed_end_date_query_is_validation_error(client, value):
    response = client.get(
        f"/api/events?start_date=2026-04-01&end_date={value}"
    )

    assert_validation_error(response, {"end_date": END_FORMAT_MESSAGE})


@pytest.mark.parametrize(
    ("query", "fields"),
    [
        (
            "start_date=2026-04-01&start_date=2026-04-02&end_date=2026-04-30",
            {"start_date": "開始日は1つだけ指定してください"},
        ),
        (
            "start_date=2026-04-01&end_date=2026-04-30&end_date=2026-05-31",
            {"end_date": "終了日は1つだけ指定してください"},
        ),
    ],
)
def test_repeated_date_queries_are_validation_errors(client, query, fields):
    response = client.get(f"/api/events?{query}")

    assert_validation_error(response, fields)


def test_end_date_before_start_date_is_validation_error(client):
    response = client.get(
        "/api/events?start_date=2026-04-02&end_date=2026-04-01"
    )

    assert_validation_error(
        response,
        {"end_date": "終了日は開始日以降の日付にしてください"},
    )


def test_date_query_errors_are_reported_together(client):
    response = client.get("/api/events?start_date=abc&end_date=2026-02-30")

    assert_validation_error(
        response,
        {
            "start_date": START_FORMAT_MESSAGE,
            "end_date": END_FORMAT_MESSAGE,
        },
    )


def test_period_check_is_skipped_when_start_date_is_invalid(client):
    response = client.get(
        "/api/events?start_date=2026-02-30&end_date=2026-01-01"
    )

    assert_validation_error(response, {"start_date": START_FORMAT_MESSAGE})


# --- 1件取得（GET /api/events/<id>） ---


def test_event_get_returns_same_item_as_list(client, app):
    semester_id = make_semester(app)
    subject_id = make_subject(app, semester_id)
    event_id = make_event(
        app,
        date(2026, 4, 6),
        category="class",
        subject_id=subject_id,
        title="プログラミング基礎",
        is_generated=True,
    )

    response = client.get(f"/api/events/{event_id}")
    listed = client.get(f"/api/events?{APRIL_QUERY}")

    assert response.status_code == 200
    assert response.json == listed.json[0]
    assert response.json["id"] == event_id


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/events/99999", "予定が見つかりません"),
        ("/api/events/0", "予定が見つかりません"),
        (f"/api/events/{MAX_ID}", "予定が見つかりません"),
        (f"/api/events/{MAX_ID + 1}", "URLが見つかりません"),
        ("/api/events/99999999999999999999", "URLが見つかりません"),
        ("/api/events/abc", "URLが見つかりません"),
        ("/api/events/-1", "URLが見つかりません"),
        ("/api/events/", "URLが見つかりません"),
    ],
)
def test_event_get_not_found_and_invalid_urls(client, url, message):
    response = client.get(url)

    assert response.status_code == 404
    assert response.json == {
        "error": {
            "code": "not_found",
            "message": message,
        }
    }


# --- 派遣会社の候補（GET /api/events/employers） ---


def employers(client, query=""):
    response = client.get(f"/api/events/employers{query}")
    assert response.status_code == 200
    return response.json


def test_employer_list_is_empty_without_events(client):
    assert employers(client) == []


def test_employer_list_is_empty_without_employers(client, app):
    make_event(app, date(2026, 4, 6), category="part_time")

    assert employers(client) == []


def test_employer_list_is_distinct_and_in_recent_order(client, app):
    make_event(app, date(2026, 4, 6), category="part_time", employer="A社")
    make_event(app, date(2026, 4, 7), category="part_time", employer="B社")
    make_event(app, date(2026, 4, 1), category="part_time", employer="A社")
    make_event(app, date(2026, 4, 8), category="part_time", employer="C社")
    make_event(app, date(2026, 4, 9), category="part_time", employer="B社")

    # 新しく登録した予定（idの大きいもの）の派遣会社から順に並ぶ
    # （予定の日付の順ではない）。
    assert employers(client) == ["B社", "C社", "A社"]


def test_employer_list_uses_only_part_time_events(client, app):
    make_event(app, date(2026, 4, 6), category="part_time", employer="A社")
    make_event(app, date(2026, 4, 7), category="other", employer="B社")
    make_event(app, date(2026, 4, 8), category="class", employer="C社")

    assert employers(client) == ["A社"]


def test_employer_list_compares_exact_strings(client, app):
    for employer in ["abc", "ABC", "ａｂｃ", "abc"]:
        make_event(
            app, date(2026, 4, 6), category="part_time", employer=employer
        )

    assert employers(client) == ["abc", "ａｂｃ", "ABC"]


def test_employer_list_ignores_unknown_query(client, app):
    make_event(app, date(2026, 4, 6), category="part_time", employer="A社")

    assert employers(client, "?category=other&limit=0") == ["A社"]


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_employer_list_url_accepts_only_get(client, app, method):
    make_event(app, date(2026, 4, 6), category="part_time", employer="A社")

    response = getattr(client, method)(
        "/api/events/employers", json={"employer": "B社"}
    )

    assert response.status_code == 405
    assert response.json["error"]["code"] == "method_not_allowed"
    assert employers(client) == ["A社"]
    assert event_count(app) == 1


# --- 提供しない操作（405） ---


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("put", "/api/events"),
        ("patch", "/api/events"),
        ("delete", "/api/events"),
        ("post", "/api/events/{event_id}"),
        ("put", "/api/events/{event_id}"),
    ],
)
def test_unsupported_event_methods_do_not_change_rows(
    client, app, method, url
):
    event_id = make_event(app, date(2026, 4, 6))
    url = url.format(event_id=event_id)
    before = client.get(f"/api/events/{event_id}")
    assert before.status_code == 200

    response = getattr(client, method)(url, json={"title": "変更"})

    assert response.status_code == 405
    assert response.json["error"]["code"] == "method_not_allowed"
    assert client.get(f"/api/events/{event_id}").json == before.json
    assert event_count(app) == 1
