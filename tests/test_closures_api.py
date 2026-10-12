from datetime import date, time

import pytest
from sqlalchemy import func, select

from app.routes import closures as closures_routes
from app.api_helpers import (
    INVALID_JSON_MESSAGE,
    MAX_ID,
    UNUSABLE_CHARACTER_MESSAGE,
)
from app.extensions import db
from app.models.closure import Closure
from app.models.event import Event
from app.models.semester import Semester


DATE_FORMAT_MESSAGE = (
    "日付は実在する日付を「YYYY-MM-DD」の形式で指定してください"
)


def make_semester(app, name="2026年度 前期"):
    with app.app_context():
        semester = Semester(
            name=name,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 7, 31),
        )
        db.session.add(semester)
        db.session.commit()
        return semester.id


def make_closure(app, semester_id, closure_date, name=None):
    with app.app_context():
        closure = Closure(
            semester_id=semester_id,
            date=closure_date,
            name=name,
        )
        db.session.add(closure)
        db.session.commit()
        return closure.id


def closure_payload(default_semester_id, **overrides):
    payload = {
        "semester_id": default_semester_id,
        "date": "2026-05-15",
    }
    payload.update(overrides)
    return payload


def assert_validation_error(response, fields):
    assert response.status_code == 400
    assert response.json == {
        "error": {
            "code": "validation_error",
            "message": "入力内容に誤りがあります",
            "fields": fields,
        }
    }


def closure_count(app):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(Closure))


def event_count(app):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(Event))


def test_closure_creation_returns_all_fields_and_matches_database(client, app):
    semester_id = make_semester(app)
    response = client.post(
        "/api/closures",
        json=closure_payload(semester_id, name="　開学記念日 "),
    )

    assert response.status_code == 201
    assert response.json == {
        "id": response.json["id"],
        "semester_id": semester_id,
        "date": "2026-05-15",
        "name": "開学記念日",
    }
    with app.app_context():
        closure = db.session.get(Closure, response.json["id"])
        assert closure is not None
        assert closure.semester_id == semester_id
        assert closure.date == date(2026, 5, 15)
        assert closure.name == "開学記念日"


@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {"name": None},
        {"name": ""},
        {"name": "  "},
        {"name": "　"},
    ],
)
def test_closure_name_is_optional_and_empty_becomes_null(
    client, app, overrides
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/closures",
        json=closure_payload(semester_id, **overrides),
    )

    assert response.status_code == 201
    assert response.json["name"] is None
    with app.app_context():
        closure = db.session.get(Closure, response.json["id"])
        assert closure is not None
        assert closure.name is None


@pytest.mark.parametrize(
    "closure_date",
    ["2026-04-01", "2026-07-31", "2026-05-16"],
)
def test_closure_dates_on_boundaries_and_weekends_are_accepted(
    client, app, closure_date
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/closures",
        json=closure_payload(semester_id, date=closure_date),
    )

    assert response.status_code == 201
    assert response.json["date"] == closure_date


@pytest.mark.parametrize("name", ["名" * 100, "😀" * 100])
def test_closure_name_up_to_100_characters_is_accepted(client, app, name):
    semester_id = make_semester(app)
    response = client.post(
        "/api/closures",
        json=closure_payload(semester_id, name=name),
    )

    assert response.status_code == 201
    assert response.json["name"] == name


def test_same_date_in_another_semester_is_accepted(client, app):
    semester_a = make_semester(app)
    semester_b = make_semester(app, "2026年度 後期")
    make_closure(app, semester_a, date(2026, 5, 15))

    response = client.post(
        "/api/closures",
        json=closure_payload(semester_b),
    )

    assert response.status_code == 201
    assert closure_count(app) == 2


def test_empty_closure_payload_reports_required_fields(client):
    response = client.post("/api/closures", json={})

    assert_validation_error(
        response,
        {
            "semester_id": "学期IDは必須です",
            "date": "日付は必須です",
        },
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("semester_id", None, "学期IDは必須です"),
        ("semester_id", "", "学期IDは必須です"),
        ("semester_id", "1", "学期IDは整数で指定してください"),
        ("semester_id", True, "学期IDは整数で指定してください"),
        ("semester_id", 1.5, "学期IDは整数で指定してください"),
        ("date", None, "日付は必須です"),
        ("date", "", "日付は必須です"),
        ("date", 20260515, DATE_FORMAT_MESSAGE),
        ("date", True, DATE_FORMAT_MESSAGE),
        ("name", 123, "名前は文字列で指定してください"),
        ("name", True, "名前は文字列で指定してください"),
        ("name", "名" * 101, "名前は100文字以内にしてください"),
    ],
)
def test_closure_fields_validate_missing_types_and_length(
    client, app, field, value, message
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/closures",
        json=closure_payload(semester_id, **{field: value}),
    )

    assert_validation_error(response, {field: message})


@pytest.mark.parametrize(
    "semester_id",
    [0, -1, MAX_ID + 1, 10**30, 99999, MAX_ID],
)
def test_invalid_or_missing_semester_references_are_validation_errors(
    client, app, semester_id
):
    make_semester(app)
    response = client.post(
        "/api/closures",
        json=closure_payload(semester_id),
    )

    assert_validation_error(
        response,
        {"semester_id": "指定された学期が存在しません"},
    )


@pytest.mark.parametrize(
    "closure_date",
    [
        "2026-5-15",
        "2026/05/15",
        "20260515",
        "2026-02-30",
        " 2026-05-15",
        "2026-05-15 ",
        "2026-05-15\n",
        "２０２６-05-15",
    ],
)
def test_malformed_closure_dates_are_rejected(client, app, closure_date):
    semester_id = make_semester(app)
    response = client.post(
        "/api/closures",
        json=closure_payload(semester_id, date=closure_date),
    )

    assert_validation_error(response, {"date": DATE_FORMAT_MESSAGE})


@pytest.mark.parametrize("closure_date", ["2026-03-31", "2026-08-01"])
def test_closure_date_outside_semester_is_rejected(
    client, app, closure_date
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/closures",
        json=closure_payload(semester_id, date=closure_date),
    )

    assert_validation_error(
        response,
        {"date": "休講日は、学期の期間内の日付にしてください"},
    )


def test_duplicate_closure_date_in_same_semester_is_rejected(client, app):
    semester_id = make_semester(app)
    make_closure(app, semester_id, date(2026, 5, 15))
    response = client.post(
        "/api/closures",
        json=closure_payload(semester_id, name="別の名前"),
    )

    assert_validation_error(
        response,
        {"date": "同じ日付の休講日がすでに登録されています"},
    )
    assert closure_count(app) == 1


def test_semester_error_skips_period_and_duplicate_checks(client, app):
    make_semester(app)
    response = client.post(
        "/api/closures",
        json=closure_payload(99999, date="2026-12-31"),
    )

    assert_validation_error(
        response,
        {"semester_id": "指定された学期が存在しません"},
    )


@pytest.mark.parametrize("field", ["id", "color", "weekday"])
def test_unknown_closure_fields_are_rejected(client, app, field):
    semester_id = make_semester(app)
    response = client.post(
        "/api/closures",
        json=closure_payload(semester_id, **{field: "unexpected"}),
    )

    assert_validation_error(
        response,
        {field: "この項目は指定できません"},
    )


def test_multiple_closure_validation_errors_are_returned_together(client):
    response = client.post(
        "/api/closures",
        json={
            "semester_id": "1",
            "date": "2026/05/15",
            "name": 123,
            "id": 1,
        },
    )

    assert_validation_error(
        response,
        {
            "semester_id": "学期IDは整数で指定してください",
            "date": DATE_FORMAT_MESSAGE,
            "name": "名前は文字列で指定してください",
            "id": "この項目は指定できません",
        },
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("date", "\ud800"),
        ("date", "2026-05-15\udc00"),
        ("name", "\ud800"),
        ("name", "  \udfff  "),
    ],
)
def test_unusable_characters_in_closure_fields_are_rejected(
    client, app, field, value
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/closures",
        json=closure_payload(semester_id, **{field: value}),
    )

    assert_validation_error(
        response,
        {field: UNUSABLE_CHARACTER_MESSAGE},
    )
    assert closure_count(app) == 0


@pytest.mark.parametrize("payload", [[], "abc", 123, True])
def test_non_object_closure_payload_has_no_fields(client, payload):
    response = client.post("/api/closures", json=payload)

    assert response.status_code == 400
    assert response.json == {
        "error": {
            "code": "validation_error",
            "message": "リクエストの本文は、JSONのオブジェクトにしてください",
        }
    }


def test_non_object_closure_null_payload_has_no_fields(client):
    response = client.post(
        "/api/closures",
        data="null",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json == {
        "error": {
            "code": "validation_error",
            "message": "リクエストの本文は、JSONのオブジェクトにしてください",
        }
    }


@pytest.mark.parametrize(
    ("data", "content_type"),
    [
        ('{"date":', "application/json"),
        ('{"date":"2026-05-15"}', "text/plain"),
        ('{"date":"2026-05-15"}', None),
    ],
)
def test_invalid_json_or_content_type_is_rejected(
    client, data, content_type
):
    response = client.post(
        "/api/closures",
        data=data,
        content_type=content_type,
    )

    assert response.status_code == 400
    assert response.json == {
        "error": {
            "code": "invalid_json",
            "message": INVALID_JSON_MESSAGE,
        }
    }


def test_empty_closure_list_returns_empty_array(client):
    response = client.get("/api/closures")

    assert response.status_code == 200
    assert response.json == []


def test_closure_list_orders_by_date_and_id_and_filters_semester(
    client, app
):
    semester_a = make_semester(app)
    semester_b = make_semester(app, "2026年度 後期")
    closure_ids = [
        make_closure(app, semester_a, date(2026, 6, 1)),
        make_closure(
            app,
            semester_b,
            date(2026, 5, 15),
            "後期の休講日",
        ),
        make_closure(app, semester_a, date(2026, 5, 15)),
        make_closure(app, semester_a, date(2026, 4, 29), "昭和の日"),
    ]

    response = client.get("/api/closures")
    assert response.status_code == 200
    assert [item["id"] for item in response.json] == [
        closure_ids[3],
        closure_ids[1],
        closure_ids[2],
        closure_ids[0],
    ]

    response_a = client.get(f"/api/closures?semester_id={semester_a}")
    assert [item["id"] for item in response_a.json] == [
        closure_ids[3],
        closure_ids[2],
        closure_ids[0],
    ]
    response_b = client.get(f"/api/closures?semester_id={semester_b}")
    assert response_b.json == [
        {
            "id": closure_ids[1],
            "semester_id": semester_b,
            "date": "2026-05-15",
            "name": "後期の休講日",
        }
    ]


@pytest.mark.parametrize("query", ["", "abc", "1.5"])
def test_invalid_semester_id_query_is_validation_error(client, query):
    response = client.get(f"/api/closures?semester_id={query}")

    assert_validation_error(
        response,
        {"semester_id": "学期IDは整数で指定してください"},
    )


def test_repeated_semester_id_query_is_validation_error(client):
    response = client.get("/api/closures?semester_id=1&semester_id=2")

    assert_validation_error(
        response,
        {"semester_id": "学期IDは1つだけ指定してください"},
    )


@pytest.mark.parametrize("query", ["0", str(MAX_ID + 1), "99999"])
def test_out_of_range_or_missing_semester_query_returns_empty(
    client, app, query
):
    semester_id = make_semester(app)
    make_closure(app, semester_id, date(2026, 5, 15))

    response = client.get(f"/api/closures?semester_id={query}")

    assert response.status_code == 200
    assert response.json == []


def test_leading_zero_semester_query_and_unknown_query(client, app):
    semester_id = make_semester(app)
    closure_id = make_closure(app, semester_id, date(2026, 5, 15))

    leading_zero = client.get(
        f"/api/closures?semester_id=00{semester_id}"
    )
    unknown = client.get("/api/closures?foo=bar")

    assert [item["id"] for item in leading_zero.json] == [closure_id]
    assert [item["id"] for item in unknown.json] == [closure_id]


def test_closure_deletion_returns_204_and_removes_only_that_row(
    client, app
):
    semester_id = make_semester(app)
    closure_id = make_closure(app, semester_id, date(2026, 5, 15))
    remaining_id = make_closure(app, semester_id, date(2026, 6, 1))

    response = client.delete(f"/api/closures/{closure_id}")

    assert response.status_code == 204
    assert response.data == b""
    assert closure_count(app) == 1
    assert [item["id"] for item in client.get("/api/closures").json] == [
        remaining_id
    ]


def test_deleted_closure_date_can_be_registered_again(client, app):
    semester_id = make_semester(app)
    closure_id = make_closure(app, semester_id, date(2026, 5, 15))
    deleted = client.delete(f"/api/closures/{closure_id}")
    created = client.post(
        "/api/closures",
        json=closure_payload(semester_id),
    )

    assert deleted.status_code == 204
    assert created.status_code == 201


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/closures/99999", "休講日が見つかりません"),
        ("/api/closures/0", "休講日が見つかりません"),
        (f"/api/closures/{MAX_ID}", "休講日が見つかりません"),
        (f"/api/closures/{MAX_ID + 1}", "URLが見つかりません"),
        ("/api/closures/abc", "URLが見つかりません"),
        ("/api/closures/-1", "URLが見つかりません"),
        ("/api/closures/", "URLが見つかりません"),
    ],
)
def test_closure_delete_not_found_and_invalid_urls(client, url, message):
    response = client.delete(url)

    assert response.status_code == 404
    assert response.json == {
        "error": {
            "code": "not_found",
            "message": message,
        }
    }


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", "/api/closures/{closure_id}"),
        ("patch", "/api/closures/{closure_id}"),
        ("put", "/api/closures/{closure_id}"),
        ("post", "/api/closures/{closure_id}"),
        ("put", "/api/closures"),
        ("patch", "/api/closures"),
        ("delete", "/api/closures"),
    ],
)
def test_unsupported_closure_methods_do_not_change_rows(
    client, app, method, url
):
    semester_id = make_semester(app)
    closure_id = make_closure(app, semester_id, date(2026, 5, 15))
    url = url.format(closure_id=closure_id)
    before = client.get("/api/closures")
    assert before.status_code == 200

    response = getattr(client, method)(url)

    assert response.status_code == 405
    assert response.json["error"]["code"] == "method_not_allowed"
    assert client.get("/api/closures").json == before.json


# --- 休講日の追加・削除と、予定（Event）の同期（Task 011） ---
# 学期は 2026-04-01（水）〜2026-07-31（金）。休講日は、金曜日の 2026-05-15。

CLOSURE_DATE = date(2026, 5, 15)


def post_subject(client, semester_id, weekday, subject_name="授業"):
    """APIで授業を登録する（学期の期間の予定が、自動で作られる）。"""
    response = client.post(
        "/api/subjects",
        json={
            "semester_id": semester_id,
            "subject_name": subject_name,
            "weekday": weekday,
            "start_time": "09:00",
            "end_time": "10:00",
        },
    )
    assert response.status_code == 201
    return response.json["id"]


def post_closure(client, semester_id, closure_date="2026-05-15"):
    response = client.post(
        "/api/closures",
        json=closure_payload(semester_id, date=closure_date),
    )
    assert response.status_code == 201
    return response.json["id"]


def add_single_event(app, subject_id, event_date):
    """カレンダーから追加した単発の予定（is_generated=False）の代わり。"""
    with app.app_context():
        db.session.add(
            Event(
                subject_id=subject_id,
                category="class",
                date=event_date,
                start_time=time(13, 0),
                end_time=time(14, 0),
                title="補講",
                is_generated=False,
            )
        )
        db.session.commit()


def events_on(app, subject_id, event_date, is_generated):
    with app.app_context():
        return db.session.scalar(
            select(func.count())
            .select_from(Event)
            .where(
                Event.subject_id == subject_id,
                Event.date == event_date,
                Event.is_generated.is_(is_generated),
            )
        )


def generated_event_count(app, subject_id):
    with app.app_context():
        return db.session.scalar(
            select(func.count())
            .select_from(Event)
            .where(
                Event.subject_id == subject_id,
                Event.is_generated.is_(True),
            )
        )


def event_snapshot(app):
    """予定の行を、idを除いて、並べた一覧にする（作り直しの比較用）。"""
    with app.app_context():
        events = db.session.scalars(select(Event)).all()
        return sorted(
            (
                event.subject_id,
                event.date,
                event.start_time,
                event.end_time,
                event.title,
                event.is_generated,
            )
            for event in events
        )


def test_closure_creation_deletes_generated_events_on_that_date(
    client, app
):
    semester_id = make_semester(app)
    friday_ids = [
        post_subject(client, semester_id, 4, "金曜1限"),
        post_subject(client, semester_id, 4, "金曜2限"),
    ]
    monday_id = post_subject(client, semester_id, 0, "月曜1限")

    post_closure(client, semester_id)

    for subject_id in friday_ids:
        assert events_on(app, subject_id, CLOSURE_DATE, True) == 0
        assert generated_event_count(app, subject_id) == 17
    assert generated_event_count(app, monday_id) == 17


def test_closure_creation_keeps_single_events(client, app):
    semester_id = make_semester(app)
    subject_id = post_subject(client, semester_id, 4)
    add_single_event(app, subject_id, CLOSURE_DATE)

    post_closure(client, semester_id)

    assert events_on(app, subject_id, CLOSURE_DATE, True) == 0
    assert events_on(app, subject_id, CLOSURE_DATE, False) == 1


def test_closure_creation_keeps_events_of_other_semesters(client, app):
    semester_id = make_semester(app)
    other_semester_id = make_semester(app, name="2026年度 後期")
    other_subject_id = post_subject(client, other_semester_id, 4)

    post_closure(client, semester_id)

    assert events_on(app, other_subject_id, CLOSURE_DATE, True) == 1
    assert generated_event_count(app, other_subject_id) == 18


def test_closure_deletion_creates_events_for_subjects_of_that_weekday(
    client, app
):
    semester_id = make_semester(app)
    closure_id = post_closure(client, semester_id)
    friday_ids = [
        post_subject(client, semester_id, 4, "金曜1限"),
        post_subject(client, semester_id, 4, "金曜2限"),
    ]
    monday_id = post_subject(client, semester_id, 0, "月曜1限")

    response = client.delete(f"/api/closures/{closure_id}")

    assert response.status_code == 204
    for subject_id in friday_ids:
        assert events_on(app, subject_id, CLOSURE_DATE, True) == 1
        assert generated_event_count(app, subject_id) == 18
    assert generated_event_count(app, monday_id) == 17


def test_event_created_by_closure_deletion_has_subject_values(client, app):
    semester_id = make_semester(app)
    closure_id = post_closure(client, semester_id)
    response = client.post(
        "/api/subjects",
        json={
            "semester_id": semester_id,
            "subject_name": "金曜1限",
            "room": "3号館201",
            "weekday": 4,
            "start_time": "09:15",
            "end_time": "10:45",
            "notes": "メモ",
        },
    )
    subject_id = response.json["id"]

    client.delete(f"/api/closures/{closure_id}")

    with app.app_context():
        event = db.session.scalars(
            select(Event).where(
                Event.subject_id == subject_id,
                Event.date == CLOSURE_DATE,
            )
        ).one()
        assert event.category == "class"
        assert event.start_time == time(9, 15)
        assert event.end_time == time(10, 45)
        assert event.title == "金曜1限"
        assert event.room == "3号館201"
        assert event.employer is None
        assert event.notes == "メモ"
        assert event.is_generated is True


def test_closure_deletion_creates_event_even_with_single_event(client, app):
    semester_id = make_semester(app)
    closure_id = post_closure(client, semester_id)
    subject_id = post_subject(client, semester_id, 4)
    add_single_event(app, subject_id, CLOSURE_DATE)

    client.delete(f"/api/closures/{closure_id}")

    # 単発の予定の有無は見ないため、自動生成の予定が作られ、両方が並ぶ。
    assert events_on(app, subject_id, CLOSURE_DATE, True) == 1
    assert events_on(app, subject_id, CLOSURE_DATE, False) == 1


def test_closure_deletion_does_not_duplicate_generated_events(client, app):
    semester_id = make_semester(app)
    subject_id = post_subject(client, semester_id, 4)
    # APIを通さずに休講日を作り、その日の自動生成の予定が残った状態にする。
    closure_id = make_closure(app, semester_id, CLOSURE_DATE)

    client.delete(f"/api/closures/{closure_id}")

    assert events_on(app, subject_id, CLOSURE_DATE, True) == 1
    assert generated_event_count(app, subject_id) == 18


def test_closure_deletion_skips_other_weekdays_and_other_semesters(
    client, app
):
    semester_id = make_semester(app)
    other_semester_id = make_semester(app, name="2026年度 後期")
    closure_id = post_closure(client, semester_id)
    monday_id = post_subject(client, semester_id, 0)
    # 曜日が違う授業は、同じ日付に単発の予定があっても、予定を作らない。
    add_single_event(app, monday_id, CLOSURE_DATE)
    other_subject_id = post_subject(client, other_semester_id, 4)

    client.delete(f"/api/closures/{closure_id}")

    assert events_on(app, monday_id, CLOSURE_DATE, True) == 0
    assert events_on(app, other_subject_id, CLOSURE_DATE, True) == 1


def test_closure_creation_then_deletion_restores_events(client, app):
    semester_id = make_semester(app)
    friday_id = post_subject(client, semester_id, 4)
    add_single_event(app, friday_id, CLOSURE_DATE)
    post_subject(client, semester_id, 0)
    before = event_snapshot(app)

    closure_id = post_closure(client, semester_id)
    assert event_snapshot(app) != before
    client.delete(f"/api/closures/{closure_id}")

    assert event_snapshot(app) == before


def test_closure_on_day_without_subjects_changes_no_events(client, app):
    semester_id = make_semester(app)
    post_subject(client, semester_id, 4)
    post_subject(client, semester_id, 0)
    before = event_snapshot(app)

    # 2026-05-16 は土曜日で、その曜日の授業はない。
    closure_id = post_closure(client, semester_id, "2026-05-16")
    assert event_snapshot(app) == before
    client.delete(f"/api/closures/{closure_id}")

    assert event_snapshot(app) == before


def test_closure_creation_failure_saves_nothing(client, app, monkeypatch):
    semester_id = make_semester(app)
    subject_id = post_subject(client, semester_id, 4)
    real_delete = closures_routes.delete_generated_class_events

    def delete_then_fail(*args, **kwargs):
        # 予定を消したあとで、commitの前に例外を起こす。
        real_delete(*args, **kwargs)
        raise RuntimeError("intentional test failure")

    monkeypatch.setattr(
        closures_routes, "delete_generated_class_events", delete_then_fail
    )
    app.config["PROPAGATE_EXCEPTIONS"] = False

    response = client.post(
        "/api/closures",
        json=closure_payload(semester_id),
    )

    assert response.status_code == 500
    assert response.json["error"]["code"] == "server_error"
    assert closure_count(app) == 0
    assert events_on(app, subject_id, CLOSURE_DATE, True) == 1


def test_closure_deletion_failure_saves_nothing(client, app, monkeypatch):
    semester_id = make_semester(app)
    closure_id = post_closure(client, semester_id)
    subject_id = post_subject(client, semester_id, 4)

    def fail(*args, **kwargs):
        raise RuntimeError("intentional test failure")

    # routeのモジュールが取り込んだ名前を置き換える。
    monkeypatch.setattr(closures_routes, "build_class_event", fail)
    app.config["PROPAGATE_EXCEPTIONS"] = False

    response = client.delete(f"/api/closures/{closure_id}")

    assert response.status_code == 500
    assert response.json["error"]["code"] == "server_error"
    assert closure_count(app) == 1
    assert events_on(app, subject_id, CLOSURE_DATE, True) == 0
