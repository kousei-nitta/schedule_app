from datetime import date, time

import pytest
from sqlalchemy import func, select

from app.api_helpers import (
    INVALID_JSON_MESSAGE,
    MAX_ID,
    UNUSABLE_CHARACTER_MESSAGE,
)
from app.extensions import db
from app.models.closure import Closure
from app.models.event import Event
from app.models.semester import Semester
from app.models.subject import Subject
from app.models.task import Task


TIME_MESSAGES = {
    "start_time": {
        "required": "開始時刻は必須です",
        "format": (
            "開始時刻は「HH:MM」の形式（00:00〜23:59）で指定してください"
        ),
    },
    "end_time": {
        "required": "終了時刻は必須です",
        "format": (
            "終了時刻は「HH:MM」の形式（00:00〜23:59）で指定してください"
        ),
    },
}


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


def subject_payload(default_semester_id, **overrides):
    payload = {
        "semester_id": default_semester_id,
        "subject_name": "プログラミング基礎",
        "weekday": 0,
        "start_time": "09:00",
        "end_time": "10:00",
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


def subject_count(app):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(Subject))


def event_count(app):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(Event))


def generated_event_dates(app, subject_id):
    """授業の自動生成の予定の日付を、昇順で返す（同じ日付が2件あれば2回）。"""
    with app.app_context():
        return list(
            db.session.scalars(
                select(Event.date)
                .where(
                    Event.subject_id == subject_id,
                    Event.is_generated.is_(True),
                )
                .order_by(Event.date)
            )
        )


def make_closure(app, semester_id, closure_date):
    with app.app_context():
        db.session.add(Closure(semester_id=semester_id, date=closure_date))
        db.session.commit()


def test_subject_creation_returns_all_fields_and_matches_database(
    client, app
):
    semester_id = make_semester(app)
    payload = subject_payload(
        semester_id,
        subject_name="  プログラミング基礎　",
        room="  3号館201  ",
        weekday=2,
        start_time="09:15",
        end_time="10:45",
        notes="  前期の授業  ",
    )

    response = client.post("/api/subjects", json=payload)
    assert response.status_code == 201
    assert response.json == {
        "id": response.json["id"],
        "semester_id": semester_id,
        "subject_name": "プログラミング基礎",
        "room": "3号館201",
        "weekday": 2,
        "start_time": "09:15",
        "end_time": "10:45",
        "notes": "前期の授業",
        "generated_event_count": 18,
    }

    with app.app_context():
        subject = db.session.get(Subject, response.json["id"])
        assert subject is not None
        assert subject.semester_id == semester_id
        assert subject.subject_name == "プログラミング基礎"
        assert subject.room == "3号館201"
        assert subject.weekday == 2
        assert subject.start_time == time(9, 15)
        assert subject.end_time == time(10, 45)
        assert subject.notes == "前期の授業"


def test_subject_creation_with_required_fields_uses_null_optional_values(
    client, app
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id),
    )
    assert response.status_code == 201
    assert set(response.json) == {
        "id",
        "semester_id",
        "subject_name",
        "room",
        "weekday",
        "start_time",
        "end_time",
        "notes",
        "generated_event_count",
    }
    assert response.json["room"] is None
    assert response.json["notes"] is None


@pytest.mark.parametrize("empty_value", ["", "  ", "　", None])
def test_optional_subject_strings_normalize_empty_to_null(
    client, app, empty_value
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(
            semester_id,
            room=empty_value,
            notes=empty_value,
        ),
    )
    assert response.status_code == 201
    assert response.json["room"] is None
    assert response.json["notes"] is None


def test_subject_string_length_limits_and_unlimited_notes(client, app):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(
            semester_id,
            subject_name="  " + "科" * 100 + "  ",
            room="教" * 100,
            notes="詳" * 10000,
        ),
    )
    assert response.status_code == 201
    assert len(response.json["subject_name"]) == 100
    assert len(response.json["room"]) == 100
    assert len(response.json["notes"]) == 10000


@pytest.mark.parametrize(
    ("weekday", "start_time", "end_time"),
    [(0, "00:00", "00:01"), (6, "23:58", "23:59"), (3, "07:30", "21:45")],
)
def test_subject_accepts_weekday_and_time_boundaries(
    client, app, weekday, start_time, end_time
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(
            semester_id,
            weekday=weekday,
            start_time=start_time,
            end_time=end_time,
        ),
    )
    assert response.status_code == 201
    assert response.json["weekday"] == weekday
    assert response.json["start_time"] == start_time
    assert response.json["end_time"] == end_time


def test_duplicate_subject_rows_are_allowed_and_each_get_events(
    client, app
):
    semester_id = make_semester(app)
    payload = subject_payload(semester_id)
    first = client.post("/api/subjects", json=payload)
    second = client.post("/api/subjects", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json["id"] != second.json["id"]
    # 同じ内容の授業を2回登録すると、それぞれに予定が1組ずつ作られる。
    assert first.json["generated_event_count"] == 17
    assert second.json["generated_event_count"] == 17
    assert generated_event_dates(app, first.json["id"]) == (
        generated_event_dates(app, second.json["id"])
    )
    with app.app_context():
        assert db.session.scalar(
            select(func.count()).select_from(Event)
        ) == 34
        assert db.session.scalar(
            select(func.count()).select_from(Task)
        ) == 0


def test_empty_subject_payload_reports_all_required_fields(client):
    response = client.post("/api/subjects", json={})
    assert_validation_error(
        response,
        {
            "semester_id": "学期IDは必須です",
            "subject_name": "科目名は必須です",
            "weekday": "曜日は必須です",
            "start_time": "開始時刻は必須です",
            "end_time": "終了時刻は必須です",
        },
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("semester_id", None, "学期IDは必須です"),
        ("semester_id", "", "学期IDは必須です"),
        ("semester_id", "1", "学期IDは整数で指定してください"),
        ("semester_id", True, "学期IDは整数で指定してください"),
        ("semester_id", False, "学期IDは整数で指定してください"),
        ("semester_id", 1.5, "学期IDは整数で指定してください"),
        ("semester_id", [1], "学期IDは整数で指定してください"),
        ("semester_id", {}, "学期IDは整数で指定してください"),
        ("subject_name", "", "科目名は必須です"),
        ("subject_name", "   ", "科目名は必須です"),
        ("subject_name", "　", "科目名は必須です"),
        ("subject_name", None, "科目名は必須です"),
        ("subject_name", 123, "科目名は文字列で指定してください"),
        ("subject_name", True, "科目名は文字列で指定してください"),
        ("subject_name", [], "科目名は文字列で指定してください"),
        ("weekday", None, "曜日は必須です"),
        ("weekday", "", "曜日は必須です"),
        ("weekday", "1", "曜日は0（月曜）〜6（日曜）の整数で指定してください"),
        (
            "weekday",
            True,
            "曜日は0（月曜）〜6（日曜）の整数で指定してください",
        ),
        ("weekday", 1.0, "曜日は0（月曜）〜6（日曜）の整数で指定してください"),
        ("weekday", [0], "曜日は0（月曜）〜6（日曜）の整数で指定してください"),
    ],
)
def test_required_subject_fields_validate_missing_and_types(
    client, app, field, value, message
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, **{field: value}),
    )
    assert_validation_error(response, {field: message})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("room", 123, "教室は文字列で指定してください"),
        ("room", True, "教室は文字列で指定してください"),
        ("notes", 123, "詳細・メモは文字列で指定してください"),
        ("notes", True, "詳細・メモは文字列で指定してください"),
    ],
)
def test_optional_subject_fields_validate_types(
    client, app, field, value, message
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, **{field: value}),
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
        "/api/subjects",
        json=subject_payload(semester_id),
    )
    assert_validation_error(
        response,
        {"semester_id": "指定された学期が存在しません"},
    )


@pytest.mark.parametrize("weekday", [-1, 7, 100])
def test_weekday_out_of_range_is_rejected(client, app, weekday):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, weekday=weekday),
    )
    assert_validation_error(
        response,
        {"weekday": "曜日は0（月曜）〜6（日曜）の整数で指定してください"},
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("subject_name", "科" * 101, "科目名は100文字以内にしてください"),
        ("room", "教" * 101, "教室は100文字以内にしてください"),
    ],
)
def test_subject_name_and_room_over_length_are_rejected(
    client, app, field, value, message
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, **{field: value}),
    )
    assert_validation_error(response, {field: message})


@pytest.mark.parametrize("field", ["start_time", "end_time"])
@pytest.mark.parametrize("value", [None, ""])
def test_missing_subject_times_are_required(client, app, field, value):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, **{field: value}),
    )
    assert_validation_error(
        response,
        {field: TIME_MESSAGES[field]["required"]},
    )


@pytest.mark.parametrize("field", ["start_time", "end_time"])
@pytest.mark.parametrize(
    "value",
    [
        900,
        True,
        "9:00",
        "09:0",
        "0900",
        "09:00:00",
        "24:00",
        "09:60",
        "ab:cd",
        " 09:00",
        "09:00 ",
        "09:00\n",
        "０９：００",
    ],
)
def test_malformed_subject_times_are_rejected(client, app, field, value):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, **{field: value}),
    )
    assert_validation_error(
        response,
        {field: TIME_MESSAGES[field]["format"]},
    )


@pytest.mark.parametrize(
    ("start_time", "end_time"),
    [("09:00", "09:00"), ("10:00", "09:59")],
)
def test_end_time_must_be_after_start_time(
    client, app, start_time, end_time
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(
            semester_id,
            start_time=start_time,
            end_time=end_time,
        ),
    )
    assert_validation_error(
        response,
        {"end_time": "終了時刻は開始時刻より後にしてください"},
    )


def test_invalid_start_time_skips_time_order_validation(client, app):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(
            semester_id,
            start_time="invalid",
            end_time="08:00",
        ),
    )
    assert_validation_error(
        response,
        {
            "start_time": (
                "開始時刻は「HH:MM」の形式（00:00〜23:59）で指定してください"
            )
        },
    )


@pytest.mark.parametrize("field", ["color", "id", "events"])
def test_unknown_subject_fields_are_rejected(client, app, field):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, **{field: "unexpected"}),
    )
    assert_validation_error(response, {field: "この項目は指定できません"})


def test_multiple_subject_validation_errors_are_returned_together(client, app):
    make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(
            99999,
            weekday=7,
            start_time="10:00",
            end_time="09:00",
        ),
    )
    assert_validation_error(
        response,
        {
            "semester_id": "指定された学期が存在しません",
            "weekday": "曜日は0（月曜）〜6（日曜）の整数で指定してください",
            "end_time": "終了時刻は開始時刻より後にしてください",
        },
    )


@pytest.mark.parametrize("payload", [[], "abc", 123, True])
def test_non_object_subject_payload_has_no_fields(client, payload):
    response = client.post("/api/subjects", json=payload)
    assert response.status_code == 400
    assert response.json == {
        "error": {
            "code": "validation_error",
            "message": "リクエストの本文は、JSONのオブジェクトにしてください",
        }
    }


def test_null_subject_payload_has_no_fields(client):
    response = client.post(
        "/api/subjects",
        data="null",
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_error"
    assert "fields" not in response.json["error"]


@pytest.mark.parametrize(
    ("data", "content_type"),
    [
        ('{"subject_name":', "application/json"),
        ('{"subject_name":"x"}', "text/plain"),
        ('{"subject_name":"x"}', None),
    ],
)
def test_invalid_json_or_content_type_is_rejected(client, data, content_type):
    response = client.post(
        "/api/subjects",
        data=data,
        content_type=content_type,
    )
    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_json"


def test_json_charset_is_accepted(client, app):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        data=(
            '{"semester_id":'
            f'{semester_id},"subject_name":"科目","weekday":0,'
            '"start_time":"09:00","end_time":"10:00"}'
        ),
        content_type="application/json; charset=utf-8",
    )
    assert response.status_code == 201


def test_failed_subject_post_does_not_change_row_count(client, app):
    semester_id = make_semester(app)
    before_count = subject_count(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, weekday=9),
    )
    assert response.status_code == 400
    assert subject_count(app) == before_count


def test_empty_subject_list_returns_empty_array(client):
    response = client.get("/api/subjects")
    assert response.status_code == 200
    assert response.json == []


def test_subject_list_orders_by_weekday_time_and_id_and_filters_semester(
    client, app
):
    first_semester_id = make_semester(app, "2026年度 前期")
    second_semester_id = make_semester(app, "2026年度 後期")
    entries = [
        (first_semester_id, "水曜遅", 2, time(10, 0)),
        (first_semester_id, "水曜早2", 2, time(9, 0)),
        (first_semester_id, "水曜早1", 2, time(9, 0)),
        (second_semester_id, "火曜", 1, time(12, 0)),
        (second_semester_id, "月曜遅", 0, time(10, 0)),
        (second_semester_id, "月曜早", 0, time(8, 0)),
    ]
    created_ids = {}
    with app.app_context():
        for semester_id, name, weekday, start_time in entries:
            subject = Subject(
                semester_id=semester_id,
                subject_name=name,
                weekday=weekday,
                start_time=start_time,
                end_time=time(start_time.hour + 1, start_time.minute),
            )
            db.session.add(subject)
            db.session.flush()
            created_ids[name] = subject.id
        db.session.commit()

    all_subjects = client.get("/api/subjects")
    assert all_subjects.status_code == 200
    assert [subject["subject_name"] for subject in all_subjects.json] == [
        "月曜早",
        "月曜遅",
        "火曜",
        "水曜早2",
        "水曜早1",
        "水曜遅",
    ]
    assert all_subjects.json[3]["id"] == created_ids["水曜早2"]
    assert all_subjects.json[4]["id"] == created_ids["水曜早1"]

    filtered = client.get(
        f"/api/subjects?semester_id={first_semester_id}"
    )
    assert {item["semester_id"] for item in filtered.json} == {
        first_semester_id
    }
    assert len(filtered.json) == 3


@pytest.mark.parametrize(
    "semester_text",
    [
        "",
        "abc",
        "-1",
        "1.5",
        "１",
        " 1",
        "1 ",
    ],
)
def test_invalid_semester_id_query_is_validation_error(client, semester_text):
    response = client.get(f"/api/subjects?semester_id={semester_text}")
    assert_validation_error(
        response,
        {"semester_id": "学期IDは整数で指定してください"},
    )


def test_repeated_semester_id_query_is_validation_error(client):
    response = client.get("/api/subjects?semester_id=1&semester_id=2")
    assert_validation_error(
        response,
        {"semester_id": "学期IDは1つだけ指定してください"},
    )


@pytest.mark.parametrize(
    "semester_text",
    [
        "0",
        "000",
        str(MAX_ID + 1),
        "99999999999999999999",
        "9" * 5000,
        "99999",
    ],
)
def test_out_of_range_or_missing_semester_query_returns_empty(
    client, semester_text
):
    response = client.get(f"/api/subjects?semester_id={semester_text}")
    assert response.status_code == 200
    assert response.json == []


def test_leading_zero_semester_query_and_unknown_query(client, app):
    semester_id = make_semester(app)
    with app.app_context():
        db.session.add(
            Subject(
                semester_id=semester_id,
                subject_name="科目",
                weekday=0,
                start_time=time(9, 0),
                end_time=time(10, 0),
            )
        )
        db.session.commit()

    for zero_padded_id in ("001", "0000000000000000000001"):
        result = client.get(
            f"/api/subjects?semester_id={zero_padded_id}"
        )
        assert len(result.json) == 1
        assert result.json[0]["semester_id"] == semester_id
    assert len(client.get("/api/subjects?foo=bar").json) == 1


def test_subject_get_returns_created_subject(client, app):
    semester_id = make_semester(app)
    created = client.post(
        "/api/subjects",
        json=subject_payload(semester_id),
    )
    expected = dict(created.json)
    # 作成のレスポンスにだけ付ける付加情報は、1件取得には含めない。
    del expected["generated_event_count"]
    # 1件取得にだけ付ける付加情報（授業を削除すると一緒に削除される件数）。
    expected["event_count"] = 17
    expected["task_count"] = 0
    assert client.get(f"/api/subjects/{created.json['id']}").json == (
        expected
    )


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/subjects/99999", "授業が見つかりません"),
        ("/api/subjects/0", "授業が見つかりません"),
        (f"/api/subjects/{MAX_ID}", "授業が見つかりません"),
        (f"/api/subjects/{MAX_ID + 1}", "URLが見つかりません"),
        ("/api/subjects/99999999999999999999", "URLが見つかりません"),
        ("/api/subjects/abc", "URLが見つかりません"),
        ("/api/subjects/-1", "URLが見つかりません"),
        ("/api/subjects/", "URLが見つかりません"),
    ],
)
def test_subject_get_not_found_and_invalid_urls(client, url, message):
    response = client.get(url)
    assert response.status_code == 404
    assert response.json["error"] == {
        "code": "not_found",
        "message": message,
    }


@pytest.mark.parametrize(
    ("method", "url"),
    [
        # 1件のURLのPATCH・DELETEは、授業の編集・削除として提供する
        # （tests/test_subjects_update_delete_api.py）。
        ("put", "/api/subjects/{subject_id}"),
        ("put", "/api/subjects"),
        ("patch", "/api/subjects"),
        ("delete", "/api/subjects"),
        ("post", "/api/subjects/{subject_id}"),
    ],
)
def test_unsupported_subject_methods_do_not_change_rows(
    client, app, method, url
):
    semester_id = make_semester(app)
    with app.app_context():
        subject = Subject(
            semester_id=semester_id,
            subject_name="登録済み授業",
            weekday=0,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        db.session.add(subject)
        db.session.commit()
        subject_id = subject.id

    url = url.format(subject_id=subject_id)
    before_subject = client.get(f"/api/subjects/{subject_id}")
    assert before_subject.status_code == 200
    before_count = subject_count(app)
    response = getattr(client, method)(url)
    assert response.status_code == 405
    assert response.json["error"]["code"] == "method_not_allowed"
    after_subject = client.get(f"/api/subjects/{subject_id}")
    assert after_subject.json == before_subject.json
    assert subject_count(app) == before_count


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("subject_name", "\ud800"),
        ("subject_name", "  \ud800  "),
        ("room", "\udfff"),
        ("notes", "メモ\ud800"),
        ("start_time", "\ud800"),
        ("end_time", "09:00\udc00"),
    ],
)
def test_unusable_characters_in_subject_fields_are_rejected(
    client, app, field, value
):
    semester_id = make_semester(app)
    before_count = subject_count(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, **{field: value}),
    )
    assert_validation_error(
        response,
        {field: UNUSABLE_CHARACTER_MESSAGE},
    )
    assert subject_count(app) == before_count


def test_invalid_utf8_subject_body_is_invalid_json(client, app):
    semester_id = make_semester(app)
    before_count = subject_count(app)
    body = (
        f'{{"semester_id": {semester_id}, "subject_name": "'.encode()
        + b"\xff"
        + b'", "weekday": 0, "start_time": "09:00", "end_time": "10:00"}'
    )
    response = client.post(
        "/api/subjects",
        data=body,
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json["error"] == {
        "code": "invalid_json",
        "message": INVALID_JSON_MESSAGE,
    }
    assert subject_count(app) == before_count == 0


def test_surrogate_pairs_in_subject_strings_are_accepted(client, app):
    semester_id = make_semester(app)
    payload = subject_payload(
        semester_id,
        subject_name="😀" * 100,
        room="教室😀",
        notes="メモ😀",
    )
    response = client.post("/api/subjects", json=payload)
    assert response.status_code == 201
    assert response.json["subject_name"] == payload["subject_name"]
    assert response.json["room"] == payload["room"]
    assert response.json["notes"] == payload["notes"]


def test_surrogate_pairs_count_as_one_character_for_subject_name(
    client, app
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, subject_name="😀" * 101),
    )
    assert_validation_error(
        response,
        {"subject_name": "科目名は100文字以内にしてください"},
    )


def test_unusable_character_and_other_errors_are_reported_together(
    client, app
):
    semester_id = make_semester(app)
    before_count = subject_count(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(
            semester_id,
            subject_name="\ud800",
            weekday=7,
        ),
    )
    assert_validation_error(
        response,
        {
            "subject_name": UNUSABLE_CHARACTER_MESSAGE,
            "weekday": "曜日は0（月曜）〜6（日曜）の整数で指定してください",
        },
    )
    assert subject_count(app) == before_count


def test_lone_surrogate_field_name_is_unknown_field(client, app):
    semester_id = make_semester(app)
    body = (
        f'{{"semester_id": {semester_id}, "subject_name": "科目", '
        '"weekday": 0, "start_time": "09:00", "end_time": "10:00", '
        '"\\ud800": 1}'
    )
    response = client.post(
        "/api/subjects",
        data=body,
        content_type="application/json",
    )
    assert_validation_error(
        response,
        {"\ud800": "この項目は指定できません"},
    )


def test_invalid_bytes_in_semester_id_query_are_validation_error(client):
    response = client.get("/api/subjects?semester_id=%ED%A0%80")
    assert_validation_error(
        response,
        {"semester_id": "学期IDは整数で指定してください"},
    )


# --- 授業の登録による予定（Event）の自動生成（Task 011） ---


def test_subject_creation_generates_events_with_subject_values(client, app):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(
            semester_id,
            subject_name="  プログラミング基礎　",
            room="3号館201",
            notes="前期の授業",
        ),
    )

    assert response.status_code == 201
    assert response.json["generated_event_count"] == 17
    subject_id = response.json["id"]
    with app.app_context():
        events = db.session.scalars(
            select(Event)
            .where(Event.subject_id == subject_id)
            .order_by(Event.date)
        ).all()
        assert len(events) == 17
        assert events[0].date == date(2026, 4, 6)
        assert events[-1].date == date(2026, 7, 27)
        for event in events:
            assert event.date.weekday() == 0
            assert event.category == "class"
            assert event.start_time == time(9, 0)
            assert event.end_time == time(10, 0)
            assert event.title == "プログラミング基礎"
            assert event.room == "3号館201"
            assert event.employer is None
            assert event.notes == "前期の授業"
            assert event.is_generated is True


def test_subject_creation_skips_closures_of_its_semester_only(client, app):
    semester_id = make_semester(app)
    other_semester_id = make_semester(app, name="2026年度 後期")
    make_closure(app, semester_id, date(2026, 5, 4))
    make_closure(app, semester_id, date(2026, 7, 20))
    # ほかの学期の休講日は、この学期の授業の予定に影響しない。
    make_closure(app, other_semester_id, date(2026, 4, 13))

    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id),
    )

    assert response.status_code == 201
    assert response.json["generated_event_count"] == 15
    dates = generated_event_dates(app, response.json["id"])
    assert len(dates) == 15
    assert date(2026, 5, 4) not in dates
    assert date(2026, 7, 20) not in dates
    assert date(2026, 4, 13) in dates


def test_subject_creation_without_matching_days_returns_zero(client, app):
    with app.app_context():
        # 2026-04-01（水）〜2026-04-02（木）の学期に、月曜日はない。
        semester = Semester(
            name="2026年度 前期",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 2),
        )
        db.session.add(semester)
        db.session.commit()
        semester_id = semester.id

    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, weekday=0),
    )

    assert response.status_code == 201
    assert response.json["generated_event_count"] == 0
    assert subject_count(app) == 1
    assert event_count(app) == 0


def test_subject_creation_when_all_days_are_closures_returns_zero(
    client, app
):
    with app.app_context():
        # 2026-04-06（月）〜2026-04-12（日）の月曜日は、4/6の1日だけ。
        semester = Semester(
            name="2026年度 前期",
            start_date=date(2026, 4, 6),
            end_date=date(2026, 4, 12),
        )
        db.session.add(semester)
        db.session.commit()
        semester_id = semester.id
    make_closure(app, semester_id, date(2026, 4, 6))

    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, weekday=0),
    )

    assert response.status_code == 201
    assert response.json["generated_event_count"] == 0
    assert event_count(app) == 0


def test_generated_event_count_is_not_in_subject_list(client, app):
    semester_id = make_semester(app)
    client.post("/api/subjects", json=subject_payload(semester_id))

    response = client.get("/api/subjects")

    assert response.status_code == 200
    assert len(response.json) == 1
    assert "generated_event_count" not in response.json[0]


def test_generated_event_count_in_request_is_rejected(client, app):
    semester_id = make_semester(app)

    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, generated_event_count=17),
    )

    assert_validation_error(
        response,
        {"generated_event_count": "この項目は指定できません"},
    )
    assert subject_count(app) == 0
    assert event_count(app) == 0


def test_failed_subject_post_creates_no_events(client, app):
    semester_id = make_semester(app)

    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, weekday=9),
    )

    assert response.status_code == 400
    assert event_count(app) == 0


def test_event_generation_failure_saves_neither_subject_nor_events(
    client, app, monkeypatch
):
    semester_id = make_semester(app)

    def fail(*args, **kwargs):
        raise RuntimeError("intentional test failure")

    # routeのモジュールが取り込んだ名前を置き換える。
    monkeypatch.setattr("app.routes.subjects.build_class_events", fail)
    app.config["PROPAGATE_EXCEPTIONS"] = False

    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id),
    )

    assert response.status_code == 500
    assert response.json["error"]["code"] == "server_error"
    assert subject_count(app) == 0
    assert event_count(app) == 0
