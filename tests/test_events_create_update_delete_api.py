"""予定の登録（POST）・編集（PATCH）・削除（DELETE）のAPIのテスト。

予定の一覧・1件取得・派遣会社の候補は、tests/test_events_api.py で
確かめる。
"""

from datetime import date, time

import pytest
from sqlalchemy import func, select

from app.api_helpers import MAX_ID, UNUSABLE_CHARACTER_MESSAGE
from app.extensions import db
from app.models.closure import Closure
from app.models.event import Event
from app.models.semester import Semester
from app.models.subject import Subject
from app.models.task import Task


# 「今日」は、2026-06-15（月）に固定する（授業全体の編集による作り直しとの
# 関係を確かめるテストのため。予定APIは「今日」を使わない）。
TODAY = date(2026, 6, 15)
# 学期（2026-04-01〜2026-07-31）の、今日より後の月曜日（授業の曜日）。
FUTURE_MONDAY = date(2026, 6, 22)

CATEGORY_MESSAGE = (
    "カテゴリは「class」「part_time」「other」のどれかで指定してください"
)
DATE_MESSAGE = "日付は実在する日付を「YYYY-MM-DD」の形式で指定してください"
TIME_MESSAGES = {
    "start_time": (
        "開始時刻は「HH:MM」の形式（00:00〜23:59）で指定してください"
    ),
    "end_time": (
        "終了時刻は「HH:MM」の形式（00:00〜23:59）で指定してください"
    ),
}
TIME_REQUIRED_MESSAGES = {
    "start_time": "開始時刻は必須です",
    "end_time": "終了時刻は必須です",
}
END_TIME_ORDER_MESSAGE = "終了時刻は開始時刻より後にしてください"
GENERATED_DATE_MESSAGE = (
    "自動生成の授業の予定は、日付を変えられません（別の日に移すときは、"
    "この予定を削除して、移す先の日に単発の授業を追加してください）"
)
NOT_APPLICABLE_MESSAGES = {
    "subject_id": "授業IDは、授業の予定にだけ指定できます",
    "title": (
        "授業の予定には、タイトルを指定できません（授業の科目名になります）"
    ),
    "room": "教室は、授業の予定にだけ指定できます",
    "employer": "派遣会社は、アルバイトの予定にだけ指定できます",
}
NOT_ALLOWED_MESSAGE = "この項目は指定できません"
OBJECT_MESSAGE = "リクエストの本文は、JSONのオブジェクトにしてください"

# 本文から項目を除くことを表す値（項目がない場合の検証に使う）。
MISSING = object()


def set_today(monkeypatch, day):
    """授業のrouteが使う「今日」（current_date）を、指定した日にする。"""
    monkeypatch.setattr("app.routes.subjects.current_date", lambda: day)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    """このファイルのテストでは、「今日」を TODAY にする。"""
    set_today(monkeypatch, TODAY)


def make_semester(app):
    with app.app_context():
        semester = Semester(
            name="2026年度 前期",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 7, 31),
        )
        db.session.add(semester)
        db.session.commit()
        return semester.id


def make_subject(app, semester_id, subject_name="プログラミング基礎"):
    """授業を、ORMで直接作る（自動生成の予定は作らない）。"""
    with app.app_context():
        subject = Subject(
            semester_id=semester_id,
            subject_name=subject_name,
            room="3号館201",
            weekday=0,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        db.session.add(subject)
        db.session.commit()
        return subject.id


def create_subject_with_events(client, semester_id):
    """月曜日の授業をAPIで登録し（自動生成の予定も作られる）、IDを返す。"""
    response = client.post(
        "/api/subjects",
        json={
            "semester_id": semester_id,
            "subject_name": "プログラミング基礎",
            "room": "3号館201",
            "weekday": 0,
            "start_time": "09:00",
            "end_time": "10:00",
            "notes": "前期の授業",
        },
    )
    assert response.status_code == 201
    return response.json["id"]


@pytest.fixture
def semester_id(app):
    return make_semester(app)


@pytest.fixture
def subject_id(app, semester_id):
    return make_subject(app, semester_id)


def class_payload(subject_id, **overrides):
    payload = {
        "category": "class",
        "subject_id": subject_id,
        "date": "2026-06-20",
        "start_time": "15:00",
        "end_time": "16:30",
        "room": "5号館101",
        "notes": "補講",
    }
    payload.update(overrides)
    return payload


def part_time_payload(**overrides):
    payload = {
        "category": "part_time",
        "date": "2026-06-20",
        "start_time": "17:00",
        "end_time": "21:00",
        "title": "倉庫の仕分け",
        "employer": "派遣会社A",
        "notes": "軍手を持参",
    }
    payload.update(overrides)
    return payload


def other_payload(**overrides):
    payload = {
        "category": "other",
        "date": "2026-06-21",
        "start_time": "10:00",
        "end_time": "12:00",
        "title": "歯医者",
        "notes": "診察券",
    }
    payload.update(overrides)
    return payload


def payload_for(category, class_subject_id, **overrides):
    """カテゴリの、登録の本文を返す。

    class_subject_id は、授業の本文の subject_id（ほかのカテゴリでは
    使わない）。
    """
    if category == "class":
        return class_payload(class_subject_id, **overrides)
    if category == "part_time":
        return part_time_payload(**overrides)
    return other_payload(**overrides)


def replace_field(payload, field, value):
    """本文の1つの項目を、value にする（MISSING なら、項目を除く）。"""
    payload = dict(payload)
    if value is MISSING:
        payload.pop(field, None)
    else:
        payload[field] = value
    return payload


def create_event(client, payload):
    """予定をAPIで登録し、レスポンスの本文を返す。"""
    response = client.post("/api/events", json=payload)
    assert response.status_code == 201
    return response.json


def event_count(app):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(Event))


def all_event_rows(app):
    """すべての予定の値を、IDの順に返す（変わっていないことの確認用）。"""
    with app.app_context():
        events = db.session.scalars(select(Event).order_by(Event.id)).all()
        return [
            (
                event.id,
                event.subject_id,
                event.category,
                event.date,
                event.start_time,
                event.end_time,
                event.title,
                event.room,
                event.employer,
                event.notes,
                event.is_generated,
            )
            for event in events
        ]


def events_on(app, subject_id, event_date, *, is_generated):
    """授業の、その日の予定（自動生成か単発か）を、IDの順に返す。"""
    with app.app_context():
        statement = (
            select(Event)
            .where(
                Event.subject_id == subject_id,
                Event.date == event_date,
                Event.is_generated.is_(is_generated),
            )
            .order_by(Event.id)
        )
        return [
            (event.id, event.room, event.title)
            for event in db.session.scalars(statement)
        ]


def generated_event_id(app, subject_id, event_date):
    """授業の、その日の自動生成の予定のIDを返す（1件だけのはず）。"""
    events = events_on(app, subject_id, event_date, is_generated=True)
    assert len(events) == 1
    return events[0][0]


def assert_validation_error(response, fields):
    assert response.status_code == 400
    assert response.json == {
        "error": {
            "code": "validation_error",
            "message": "入力内容に誤りがあります",
            "fields": fields,
        }
    }


# --- 登録（POST） ---


def test_create_class_event_returns_event(client, subject_id):
    response = client.post("/api/events", json=class_payload(subject_id))

    assert response.status_code == 201
    assert response.json == {
        "id": response.json["id"],
        "subject_id": subject_id,
        "category": "class",
        "date": "2026-06-20",
        "start_time": "15:00",
        "end_time": "16:30",
        "title": "プログラミング基礎",
        "room": "5号館101",
        "employer": None,
        "notes": "補講",
        "is_generated": False,
    }


def test_create_class_event_saves_row(client, app, subject_id):
    created = create_event(client, class_payload(subject_id))

    assert all_event_rows(app) == [
        (
            created["id"],
            subject_id,
            "class",
            date(2026, 6, 20),
            time(15, 0),
            time(16, 30),
            "プログラミング基礎",
            "5号館101",
            None,
            "補講",
            False,
        )
    ]


def test_create_part_time_event_returns_event(client, app):
    response = client.post("/api/events", json=part_time_payload())

    assert response.status_code == 201
    assert response.json == {
        "id": response.json["id"],
        "subject_id": None,
        "category": "part_time",
        "date": "2026-06-20",
        "start_time": "17:00",
        "end_time": "21:00",
        "title": "倉庫の仕分け",
        "room": None,
        "employer": "派遣会社A",
        "notes": "軍手を持参",
        "is_generated": False,
    }
    assert event_count(app) == 1


def test_create_other_event_returns_event(client, app):
    response = client.post("/api/events", json=other_payload())

    assert response.status_code == 201
    assert response.json == {
        "id": response.json["id"],
        "subject_id": None,
        "category": "other",
        "date": "2026-06-21",
        "start_time": "10:00",
        "end_time": "12:00",
        "title": "歯医者",
        "room": None,
        "employer": None,
        "notes": "診察券",
        "is_generated": False,
    }
    assert event_count(app) == 1


@pytest.mark.parametrize(
    ("category", "omitted"),
    [
        ("class", ["room", "notes"]),
        ("part_time", ["employer", "notes"]),
        ("other", ["notes"]),
    ],
)
def test_create_optional_fields_can_be_omitted(
    client, subject_id, category, omitted
):
    payload = payload_for(category, subject_id)
    for field in omitted:
        del payload[field]

    created = create_event(client, payload)

    for field in omitted:
        assert created[field] is None


@pytest.mark.parametrize(
    ("category", "overrides", "expected"),
    [
        (
            "part_time",
            {"title": "　 倉庫の仕分け ", "employer": " ", "notes": "  "},
            {"title": "倉庫の仕分け", "employer": None, "notes": None},
        ),
        (
            "class",
            {"room": "　", "notes": ""},
            {"room": None, "notes": None},
        ),
    ],
)
def test_create_strips_strings_and_clears_blank_optional_fields(
    client, subject_id, category, overrides, expected
):
    created = create_event(
        client, payload_for(category, subject_id, **overrides)
    )

    for field, value in expected.items():
        assert created[field] == value


def test_create_class_title_is_subject_name_at_creation(
    client, app, subject_id
):
    created = create_event(client, class_payload(subject_id))
    with app.app_context():
        db.session.get(Subject, subject_id).subject_name = "データ構造"
        db.session.commit()

    response = client.get(f"/api/events/{created['id']}")

    # 単発の予定のタイトルは、登録したときの科目名の控え。
    assert response.json["title"] == "プログラミング基礎"


@pytest.mark.parametrize(
    "event_date",
    ["2020-01-01", "2026-03-31", "2026-08-10", "2026-06-17"],
)
def test_create_class_event_accepts_any_date(client, subject_id, event_date):
    # 過去の日付、学期の期間の外の日付、授業の曜日と違う日も受け付ける。
    created = create_event(
        client, class_payload(subject_id, date=event_date)
    )

    assert created["date"] == event_date


def test_create_class_event_on_closure_date_is_accepted(
    client, app, semester_id, subject_id
):
    with app.app_context():
        db.session.add(Closure(semester_id=semester_id, date=FUTURE_MONDAY))
        db.session.commit()

    created = create_event(
        client, class_payload(subject_id, date=FUTURE_MONDAY.isoformat())
    )

    assert events_on(app, subject_id, FUTURE_MONDAY, is_generated=False) == [
        (created["id"], "5号館101", "プログラミング基礎")
    ]


def test_create_class_event_beside_generated_event_is_accepted(
    client, app, semester_id
):
    subject_id = create_subject_with_events(client, semester_id)
    generated = events_on(app, subject_id, FUTURE_MONDAY, is_generated=True)

    created = create_event(
        client, class_payload(subject_id, date=FUTURE_MONDAY.isoformat())
    )

    # 同じ授業・同じ日付に、自動生成の予定と単発の予定が並ぶ。
    assert events_on(app, subject_id, FUTURE_MONDAY, is_generated=True) == (
        generated
    )
    assert events_on(app, subject_id, FUTURE_MONDAY, is_generated=False) == [
        (created["id"], "5号館101", "プログラミング基礎")
    ]


def test_create_accepts_times_outside_class_hours(client):
    created = create_event(
        client, part_time_payload(start_time="00:00", end_time="23:59")
    )

    assert (created["start_time"], created["end_time"]) == ("00:00", "23:59")


@pytest.mark.parametrize(
    ("category", "field", "max_length"),
    [
        ("part_time", "title", 200),
        ("other", "title", 200),
        ("part_time", "employer", 100),
        ("class", "room", 100),
    ],
)
def test_create_accepts_maximum_lengths(
    client, subject_id, category, field, max_length
):
    value = "あ" * max_length

    created = create_event(
        client, payload_for(category, subject_id, **{field: value})
    )

    assert created[field] == value


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (MISSING, "カテゴリは必須です"),
        (None, "カテゴリは必須です"),
        ("", "カテゴリは必須です"),
        ("assignment", CATEGORY_MESSAGE),
        ("Other", CATEGORY_MESSAGE),
        (" other", CATEGORY_MESSAGE),
        ("その他", CATEGORY_MESSAGE),
        (1, CATEGORY_MESSAGE),
        (True, CATEGORY_MESSAGE),
        (["other"], CATEGORY_MESSAGE),
        ("\ud800", UNUSABLE_CHARACTER_MESSAGE),
    ],
)
def test_create_category_is_validated(client, value, message):
    payload = replace_field(other_payload(), "category", value)

    response = client.post("/api/events", json=payload)

    assert_validation_error(response, {"category": message})


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (MISSING, "日付は必須です"),
        (None, "日付は必須です"),
        ("", "日付は必須です"),
        ("2026-6-20", DATE_MESSAGE),
        ("2026/06/20", DATE_MESSAGE),
        ("20260620", DATE_MESSAGE),
        ("2026-02-30", DATE_MESSAGE),
        ("2026-06-20T10:00", DATE_MESSAGE),
        (" 2026-06-20", DATE_MESSAGE),
        (20260620, DATE_MESSAGE),
        ("2026-06-20\ud800", UNUSABLE_CHARACTER_MESSAGE),
    ],
)
def test_create_date_is_validated(client, value, message):
    payload = replace_field(other_payload(), "date", value)

    response = client.post("/api/events", json=payload)

    assert_validation_error(response, {"date": message})


@pytest.mark.parametrize("field", ["start_time", "end_time"])
@pytest.mark.parametrize(
    ("value", "kind"),
    [
        (MISSING, "required"),
        ("", "required"),
        ("9:00", "format"),
        ("24:00", "format"),
        ("10:00:00", "format"),
        (1000, "format"),
        ("\ud800", "unusable"),
    ],
)
def test_create_time_is_validated(client, field, value, kind):
    payload = replace_field(other_payload(), field, value)
    messages = {
        "required": TIME_REQUIRED_MESSAGES[field],
        "format": TIME_MESSAGES[field],
        "unusable": UNUSABLE_CHARACTER_MESSAGE,
    }

    response = client.post("/api/events", json=payload)

    # 時刻の誤りがあると、開始と終了の前後は比べない。
    assert_validation_error(response, {field: messages[kind]})


@pytest.mark.parametrize(
    ("start_time", "end_time"),
    [("10:00", "10:00"), ("10:00", "09:59"), ("22:00", "02:00")],
)
def test_create_end_time_must_be_after_start_time(
    client, start_time, end_time
):
    # 日付をまたぐ予定（22:00〜翌2:00）も、1件では登録できない。
    payload = part_time_payload(start_time=start_time, end_time=end_time)

    response = client.post("/api/events", json=payload)

    assert_validation_error(response, {"end_time": END_TIME_ORDER_MESSAGE})


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (1, "詳細・メモは文字列で指定してください"),
        ("メモ\ud800", UNUSABLE_CHARACTER_MESSAGE),
    ],
)
def test_create_notes_is_validated(client, value, message):
    response = client.post("/api/events", json=other_payload(notes=value))

    assert_validation_error(response, {"notes": message})


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (MISSING, "授業IDは必須です"),
        (None, "授業IDは必須です"),
        ("", "授業IDは必須です"),
        ("1", "授業IDは整数で指定してください"),
        (1.5, "授業IDは整数で指定してください"),
        (True, "授業IDは整数で指定してください"),
        (0, "指定された授業が存在しません"),
        (-1, "指定された授業が存在しません"),
        (MAX_ID + 1, "指定された授業が存在しません"),
        (99999, "指定された授業が存在しません"),
    ],
)
def test_create_class_subject_id_is_validated(
    client, subject_id, value, message
):
    payload = replace_field(class_payload(subject_id), "subject_id", value)

    response = client.post("/api/events", json=payload)

    assert_validation_error(response, {"subject_id": message})


@pytest.mark.parametrize("category", ["part_time", "other"])
@pytest.mark.parametrize(
    ("value", "message"),
    [
        (MISSING, "タイトルは必須です"),
        (None, "タイトルは必須です"),
        ("", "タイトルは必須です"),
        ("　 ", "タイトルは必須です"),
        (1, "タイトルは文字列で指定してください"),
        ("あ" * 201, "タイトルは200文字以内にしてください"),
        ("仕分け\ud800", UNUSABLE_CHARACTER_MESSAGE),
    ],
)
def test_create_title_is_validated(client, category, value, message):
    payload = replace_field(payload_for(category, None), "title", value)

    response = client.post("/api/events", json=payload)

    assert_validation_error(response, {"title": message})


@pytest.mark.parametrize(
    ("category", "field", "value", "message"),
    [
        ("class", "room", 1, "教室は文字列で指定してください"),
        ("class", "room", "あ" * 101, "教室は100文字以内にしてください"),
        ("class", "room", "\ud800", UNUSABLE_CHARACTER_MESSAGE),
        ("part_time", "employer", 1, "派遣会社は文字列で指定してください"),
        (
            "part_time",
            "employer",
            "あ" * 101,
            "派遣会社は100文字以内にしてください",
        ),
        ("part_time", "employer", "\ud800", UNUSABLE_CHARACTER_MESSAGE),
    ],
)
def test_create_room_and_employer_are_validated(
    client, subject_id, category, field, value, message
):
    payload = payload_for(category, subject_id, **{field: value})

    response = client.post("/api/events", json=payload)

    assert_validation_error(response, {field: message})


@pytest.mark.parametrize(
    ("category", "field", "value"),
    [
        ("class", "title", "補講"),
        ("class", "title", ""),
        ("class", "employer", "派遣会社A"),
        ("class", "employer", "\ud800"),
        ("part_time", "subject_id", "SUBJECT"),
        ("part_time", "subject_id", 0),
        ("part_time", "room", "3号館201"),
        ("part_time", "room", ""),
        ("other", "subject_id", "SUBJECT"),
        ("other", "room", "3号館201"),
        ("other", "employer", "派遣会社A"),
        ("other", "employer", ""),
    ],
)
def test_create_rejects_fields_not_for_category(
    client, subject_id, category, field, value
):
    # "SUBJECT" は、存在する授業のIDに置き換える。
    if value == "SUBJECT":
        value = subject_id
    payload = payload_for(category, subject_id, **{field: value})

    response = client.post("/api/events", json=payload)

    assert_validation_error(
        response, {field: NOT_APPLICABLE_MESSAGES[field]}
    )


@pytest.mark.parametrize(
    ("category", "field"),
    [
        ("class", "title"),
        ("class", "employer"),
        ("part_time", "subject_id"),
        ("part_time", "room"),
        ("other", "subject_id"),
        ("other", "room"),
        ("other", "employer"),
    ],
)
def test_create_accepts_null_for_fields_not_for_category(
    client, subject_id, category, field
):
    payload = payload_for(category, subject_id, **{field: None})

    created = create_event(client, payload)

    expected_title = {
        "class": "プログラミング基礎",
        "part_time": "倉庫の仕分け",
        "other": "歯医者",
    }[category]
    assert created["title"] == expected_title
    if field != "title":
        assert created[field] is None


def test_create_invalid_category_skips_category_fields(client):
    # カテゴリに誤りがあると、カテゴリによって変わる項目の規則が決まらない
    # ため、検査しない。
    payload = other_payload(
        category="assignment",
        subject_id=99999,
        title="",
        room=1,
        employer=1,
    )

    response = client.post("/api/events", json=payload)

    assert_validation_error(response, {"category": CATEGORY_MESSAGE})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", 1),
        ("is_generated", False),
        ("is_generated", True),
        ("location", "体育館"),
    ],
)
def test_create_rejects_unknown_and_read_only_fields(client, field, value):
    payload = other_payload(**{field: value})

    response = client.post("/api/events", json=payload)

    assert_validation_error(response, {field: NOT_ALLOWED_MESSAGE})


def test_create_validation_errors_are_returned_together(client):
    response = client.post(
        "/api/events",
        json={
            "category": "part_time",
            "date": "2026-06-31",
            "start_time": "21:00",
            "end_time": "17:00",
            "title": "",
            "room": "3号館201",
            "is_generated": False,
        },
    )

    assert_validation_error(
        response,
        {
            "date": DATE_MESSAGE,
            "end_time": END_TIME_ORDER_MESSAGE,
            "title": "タイトルは必須です",
            "room": NOT_APPLICABLE_MESSAGES["room"],
            "is_generated": NOT_ALLOWED_MESSAGE,
        },
    )


def test_failed_create_saves_nothing(client, app, subject_id):
    response = client.post(
        "/api/events", json=class_payload(subject_id, title="補講")
    )

    assert response.status_code == 400
    assert event_count(app) == 0


@pytest.mark.parametrize("body", ["[]", '"予定"', "1", "true", "null"])
def test_create_non_object_payload_has_no_fields(client, body):
    response = client.post(
        "/api/events", data=body, content_type="application/json"
    )

    assert response.status_code == 400
    assert response.json == {
        "error": {"code": "validation_error", "message": OBJECT_MESSAGE}
    }


@pytest.mark.parametrize(
    ("data", "content_type"),
    [
        ('{"title":', "application/json"),
        ('{"title":"x"}', "text/plain"),
        ('{"title":"x"}', None),
    ],
)
def test_create_invalid_json_or_content_type_is_rejected(
    client, data, content_type
):
    response = client.post(
        "/api/events", data=data, content_type=content_type
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_json"


def test_created_event_is_in_list_and_get(client):
    created = create_event(client, other_payload())

    listed = client.get(
        "/api/events?start_date=2026-06-21&end_date=2026-06-21"
    )
    fetched = client.get(f"/api/events/{created['id']}")

    assert listed.json == [created]
    assert fetched.json == created


# --- 編集（PATCH） ---


def test_patch_changes_only_given_fields(client):
    created = create_event(client, part_time_payload())

    response = client.patch(
        f"/api/events/{created['id']}", json={"title": " 棚卸し "}
    )

    assert response.status_code == 200
    assert response.json == dict(created, title="棚卸し")
    assert client.get(f"/api/events/{created['id']}").json == response.json


def test_patch_part_time_can_change_all_editable_fields(client):
    created = create_event(client, part_time_payload())

    response = client.patch(
        f"/api/events/{created['id']}",
        json={
            "date": "2026-06-27",
            "start_time": "18:00",
            "end_time": "22:30",
            "title": "棚卸し",
            "employer": "派遣会社B",
            "notes": "動きやすい服装",
        },
    )

    assert response.status_code == 200
    assert response.json == {
        "id": created["id"],
        "subject_id": None,
        "category": "part_time",
        "date": "2026-06-27",
        "start_time": "18:00",
        "end_time": "22:30",
        "title": "棚卸し",
        "room": None,
        "employer": "派遣会社B",
        "notes": "動きやすい服装",
        "is_generated": False,
    }


def test_patch_other_can_change_all_editable_fields(client):
    created = create_event(client, other_payload())

    response = client.patch(
        f"/api/events/{created['id']}",
        json={
            "date": "2026-07-01",
            "start_time": "13:00",
            "end_time": "14:00",
            "title": "眼科",
            "notes": None,
        },
    )

    assert response.status_code == 200
    assert response.json == dict(
        created,
        date="2026-07-01",
        start_time="13:00",
        end_time="14:00",
        title="眼科",
        notes=None,
    )


def test_patch_one_off_class_event_can_change_date_time_room_and_notes(
    client, subject_id
):
    created = create_event(client, class_payload(subject_id))

    response = client.patch(
        f"/api/events/{created['id']}",
        json={
            "date": "2026-06-27",
            "start_time": "13:00",
            "end_time": "14:30",
            "room": "5号館102",
            "notes": "補講（教室変更）",
        },
    )

    assert response.status_code == 200
    assert response.json == dict(
        created,
        date="2026-06-27",
        start_time="13:00",
        end_time="14:30",
        room="5号館102",
        notes="補講（教室変更）",
    )


def test_patch_generated_event_changes_time_room_notes_and_stays_generated(
    client, app, semester_id
):
    subject_id = create_subject_with_events(client, semester_id)
    event_id = generated_event_id(app, subject_id, FUTURE_MONDAY)

    response = client.patch(
        f"/api/events/{event_id}",
        json={
            "start_time": "10:00",
            "end_time": "11:00",
            "room": "3号館301",
            "notes": "この日だけ教室変更",
        },
    )

    assert response.status_code == 200
    assert response.json == {
        "id": event_id,
        "subject_id": subject_id,
        "category": "class",
        "date": FUTURE_MONDAY.isoformat(),
        "start_time": "10:00",
        "end_time": "11:00",
        "title": "プログラミング基礎",
        "room": "3号館301",
        "employer": None,
        "notes": "この日だけ教室変更",
        "is_generated": True,
    }


@pytest.mark.parametrize(
    "value", ["2026-06-23", FUTURE_MONDAY.isoformat(), None, "abc"]
)
def test_patch_generated_event_rejects_date(client, app, semester_id, value):
    subject_id = create_subject_with_events(client, semester_id)
    event_id = generated_event_id(app, subject_id, FUTURE_MONDAY)
    before = all_event_rows(app)

    # 今と同じ日付や null でも、日付は変えられない。
    response = client.patch(f"/api/events/{event_id}", json={"date": value})

    assert_validation_error(response, {"date": GENERATED_DATE_MESSAGE})
    assert all_event_rows(app) == before


@pytest.mark.parametrize(
    ("category", "field", "value"),
    [
        ("part_time", "employer", None),
        ("part_time", "employer", ""),
        ("part_time", "employer", "　"),
        ("class", "room", None),
        ("class", "room", " "),
        ("other", "notes", None),
        ("other", "notes", "  "),
    ],
)
def test_patch_can_clear_optional_fields(
    client, subject_id, category, field, value
):
    created = create_event(client, payload_for(category, subject_id))

    response = client.patch(
        f"/api/events/{created['id']}", json={field: value}
    )

    assert response.status_code == 200
    assert response.json == dict(created, **{field: None})


@pytest.mark.parametrize(
    ("category", "field"),
    [
        ("class", "title"),
        ("class", "employer"),
        ("part_time", "room"),
        ("other", "room"),
        ("other", "employer"),
    ],
)
def test_patch_accepts_null_for_fields_not_for_category(
    client, subject_id, category, field
):
    created = create_event(client, payload_for(category, subject_id))

    response = client.patch(
        f"/api/events/{created['id']}", json={field: None}
    )

    assert response.status_code == 200
    assert response.json == created


@pytest.mark.parametrize(
    ("category", "field", "value"),
    [
        ("class", "title", "補講"),
        ("class", "title", ""),
        ("class", "employer", "派遣会社A"),
        ("part_time", "room", "3号館201"),
        ("other", "room", "3号館201"),
        ("other", "employer", "派遣会社A"),
    ],
)
def test_patch_rejects_fields_not_for_category(
    client, subject_id, category, field, value
):
    created = create_event(client, payload_for(category, subject_id))

    response = client.patch(
        f"/api/events/{created['id']}", json={field: value}
    )

    assert_validation_error(
        response, {field: NOT_APPLICABLE_MESSAGES[field]}
    )


@pytest.mark.parametrize(
    ("category", "field", "value", "message"),
    [
        ("part_time", "date", None, "日付は必須です"),
        ("part_time", "date", "", "日付は必須です"),
        ("part_time", "date", "2026-02-30", DATE_MESSAGE),
        ("part_time", "date", "\ud800", UNUSABLE_CHARACTER_MESSAGE),
        ("part_time", "start_time", None, "開始時刻は必須です"),
        ("part_time", "start_time", "24:00", TIME_MESSAGES["start_time"]),
        ("part_time", "end_time", "", "終了時刻は必須です"),
        ("part_time", "end_time", "9:00", TIME_MESSAGES["end_time"]),
        ("part_time", "title", None, "タイトルは必須です"),
        ("part_time", "title", "　 ", "タイトルは必須です"),
        ("part_time", "title", 1, "タイトルは文字列で指定してください"),
        (
            "part_time",
            "title",
            "あ" * 201,
            "タイトルは200文字以内にしてください",
        ),
        ("other", "title", "", "タイトルは必須です"),
        ("part_time", "employer", 1, "派遣会社は文字列で指定してください"),
        (
            "part_time",
            "employer",
            "あ" * 101,
            "派遣会社は100文字以内にしてください",
        ),
        ("class", "room", 1, "教室は文字列で指定してください"),
        ("class", "room", "あ" * 101, "教室は100文字以内にしてください"),
        ("class", "date", None, "日付は必須です"),
        ("other", "notes", 1, "詳細・メモは文字列で指定してください"),
        ("other", "notes", "\ud800", UNUSABLE_CHARACTER_MESSAGE),
    ],
)
def test_patch_field_values_are_validated(
    client, subject_id, category, field, value, message
):
    created = create_event(client, payload_for(category, subject_id))

    response = client.patch(
        f"/api/events/{created['id']}", json={field: value}
    )

    assert_validation_error(response, {field: message})


@pytest.mark.parametrize(
    "payload",
    [
        {"start_time": "21:00"},
        {"end_time": "16:59"},
        {"start_time": "20:00", "end_time": "19:00"},
    ],
)
def test_patch_end_time_must_be_after_start_time_after_change(
    client, payload
):
    # 今の予定は 17:00〜21:00。本文にない時刻は、今の値と比べる。
    created = create_event(client, part_time_payload())

    response = client.patch(f"/api/events/{created['id']}", json=payload)

    assert_validation_error(response, {"end_time": END_TIME_ORDER_MESSAGE})


def test_patch_time_change_is_accepted_when_order_is_valid(client):
    created = create_event(client, part_time_payload())

    response = client.patch(
        f"/api/events/{created['id']}",
        json={"start_time": "22:00", "end_time": "23:59"},
    )

    assert response.status_code == 200
    assert response.json["start_time"] == "22:00"
    assert response.json["end_time"] == "23:59"


def test_patch_invalid_start_time_skips_time_order_validation(client):
    created = create_event(client, part_time_payload())

    response = client.patch(
        f"/api/events/{created['id']}", json={"start_time": "abc"}
    )

    assert_validation_error(
        response, {"start_time": TIME_MESSAGES["start_time"]}
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("category", "other"),
        ("category", "part_time"),
        ("subject_id", 1),
        ("subject_id", None),
        ("is_generated", True),
        ("is_generated", False),
        ("id", 1),
        ("location", "体育館"),
    ],
)
def test_patch_rejects_category_subject_and_unknown_fields(
    client, field, value
):
    created = create_event(client, part_time_payload())

    response = client.patch(
        f"/api/events/{created['id']}", json={field: value}
    )

    assert_validation_error(response, {field: NOT_ALLOWED_MESSAGE})


def test_patch_class_event_rejects_same_subject_id(client, subject_id):
    created = create_event(client, class_payload(subject_id))

    response = client.patch(
        f"/api/events/{created['id']}", json={"subject_id": subject_id}
    )

    assert_validation_error(response, {"subject_id": NOT_ALLOWED_MESSAGE})


def test_patch_empty_object_is_validation_error_without_fields(client):
    created = create_event(client, other_payload())

    response = client.patch(f"/api/events/{created['id']}", json={})

    assert response.status_code == 400
    assert response.json == {
        "error": {
            "code": "validation_error",
            "message": "変更する項目を指定してください",
        }
    }


def test_patch_validation_errors_are_returned_together(client):
    created = create_event(client, part_time_payload())

    response = client.patch(
        f"/api/events/{created['id']}",
        json={
            "date": "2026-06-31",
            "title": "",
            "room": "3号館201",
            "category": "other",
        },
    )

    assert_validation_error(
        response,
        {
            "date": DATE_MESSAGE,
            "title": "タイトルは必須です",
            "room": NOT_APPLICABLE_MESSAGES["room"],
            "category": NOT_ALLOWED_MESSAGE,
        },
    )


def test_failed_patch_changes_nothing(client, app):
    created = create_event(client, part_time_payload())
    before = all_event_rows(app)

    response = client.patch(
        f"/api/events/{created['id']}",
        json={"title": "棚卸し", "date": "2026-06-31"},
    )

    assert response.status_code == 400
    assert all_event_rows(app) == before


def test_patch_changes_only_that_event(client, app, semester_id):
    subject_id = create_subject_with_events(client, semester_id)
    created = create_event(client, part_time_payload())
    event_id = generated_event_id(app, subject_id, FUTURE_MONDAY)
    before = [row for row in all_event_rows(app) if row[0] != event_id]

    response = client.patch(
        f"/api/events/{event_id}", json={"room": "3号館301"}
    )

    assert response.status_code == 200
    after = [row for row in all_event_rows(app) if row[0] != event_id]
    assert after == before
    assert client.get(f"/api/events/{created['id']}").json == created


@pytest.mark.parametrize("body", ["[]", '"予定"', "1", "true", "null"])
def test_patch_non_object_payload_has_no_fields(client, body):
    created = create_event(client, other_payload())

    response = client.patch(
        f"/api/events/{created['id']}",
        data=body,
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json == {
        "error": {"code": "validation_error", "message": OBJECT_MESSAGE}
    }


@pytest.mark.parametrize(
    ("data", "content_type"),
    [
        ('{"title":', "application/json"),
        ('{"title":"x"}', "text/plain"),
        ('{"title":"x"}', None),
    ],
)
def test_patch_invalid_json_or_content_type_is_rejected(
    client, data, content_type
):
    created = create_event(client, other_payload())

    response = client.patch(
        f"/api/events/{created['id']}", data=data, content_type=content_type
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_json"


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/events/99999", "予定が見つかりません"),
        ("/api/events/0", "予定が見つかりません"),
        (f"/api/events/{MAX_ID}", "予定が見つかりません"),
        ("/api/events/abc", "URLが見つかりません"),
        ("/api/events/-1", "URLが見つかりません"),
    ],
)
def test_patch_not_found_and_invalid_urls(client, url, message):
    response = client.patch(url, json={"title": "棚卸し"})

    assert response.status_code == 404
    assert response.json == {
        "error": {"code": "not_found", "message": message}
    }


def test_patch_missing_event_is_404_before_reading_body(client):
    response = client.patch(
        "/api/events/99999", data="not json", content_type="text/plain"
    )

    assert response.status_code == 404
    assert response.json["error"]["message"] == "予定が見つかりません"


# --- 削除（DELETE） ---


def test_delete_one_off_event_removes_only_that_event(client):
    deleted = create_event(client, part_time_payload())
    kept = create_event(client, other_payload())

    response = client.delete(f"/api/events/{deleted['id']}")

    assert response.status_code == 204
    assert response.data == b""
    listed = client.get(
        "/api/events?start_date=2026-06-01&end_date=2026-06-30"
    )
    assert listed.json == [kept]


def test_delete_generated_event_removes_only_that_day(
    client, app, semester_id
):
    subject_id = create_subject_with_events(client, semester_id)
    event_id = generated_event_id(app, subject_id, FUTURE_MONDAY)
    before = [row for row in all_event_rows(app) if row[0] != event_id]

    response = client.delete(f"/api/events/{event_id}")

    assert response.status_code == 204
    assert all_event_rows(app) == before
    assert events_on(app, subject_id, FUTURE_MONDAY, is_generated=True) == []


def test_delete_event_keeps_subject_closures_and_tasks(
    client, app, semester_id, subject_id
):
    with app.app_context():
        db.session.add(
            Closure(semester_id=semester_id, date=date(2026, 6, 29))
        )
        db.session.commit()
    task = client.post(
        "/api/tasks",
        json={
            "category": "assignment",
            "subject_id": subject_id,
            "title": "レポート",
            "due_datetime": "2026-06-30T23:59",
        },
    ).json
    created = create_event(client, class_payload(subject_id))

    response = client.delete(f"/api/events/{created['id']}")

    assert response.status_code == 204
    with app.app_context():
        assert db.session.get(Subject, subject_id) is not None
        assert db.session.scalar(
            select(func.count()).select_from(Closure)
        ) == 1
        assert db.session.get(Task, task["id"]) is not None


def test_delete_event_ignores_body(client):
    created = create_event(client, other_payload())

    response = client.delete(
        f"/api/events/{created['id']}",
        data="not json",
        content_type="text/plain",
    )

    assert response.status_code == 204


def test_deleted_event_cannot_be_deleted_again(client):
    created = create_event(client, other_payload())
    client.delete(f"/api/events/{created['id']}")

    response = client.delete(f"/api/events/{created['id']}")

    assert response.status_code == 404
    assert response.json["error"]["message"] == "予定が見つかりません"


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/events/99999", "予定が見つかりません"),
        ("/api/events/0", "予定が見つかりません"),
        (f"/api/events/{MAX_ID}", "予定が見つかりません"),
        ("/api/events/abc", "URLが見つかりません"),
        ("/api/events/-1", "URLが見つかりません"),
    ],
)
def test_delete_not_found_and_invalid_urls(client, url, message):
    response = client.delete(url)

    assert response.status_code == 404
    assert response.json == {
        "error": {"code": "not_found", "message": message}
    }


@pytest.mark.parametrize("method", ["patch", "delete"])
@pytest.mark.parametrize(
    "event_id_text", [str(MAX_ID + 1), "99999999999999999999"]
)
def test_over_limit_id_for_patch_and_delete_is_method_not_allowed(
    client, method, event_id_text
):
    # docs/architecture.md の「404の使い分け」の注意（Flaskの仕組みにより、
    # 同じURLにほかのメソッドのrouteがあると、405になる）。
    response = getattr(client, method)(f"/api/events/{event_id_text}")

    assert response.status_code == 405
    assert response.json["error"]["code"] == "method_not_allowed"


# --- 授業の編集・削除、休講日との関係 ---


def test_one_off_class_event_is_kept_by_subject_patch(
    client, app, semester_id
):
    subject_id = create_subject_with_events(client, semester_id)
    created = create_event(
        client, class_payload(subject_id, date=FUTURE_MONDAY.isoformat())
    )

    response = client.patch(
        f"/api/subjects/{subject_id}", json={"subject_name": "データ構造"}
    )

    # 単発の予定は、作り直しの対象外で、タイトルも登録したときのまま。
    assert response.status_code == 200
    assert client.get(f"/api/events/{created['id']}").json == created


def test_edited_generated_event_is_rebuilt_by_subject_patch(
    client, app, semester_id
):
    subject_id = create_subject_with_events(client, semester_id)
    event_id = generated_event_id(app, subject_id, FUTURE_MONDAY)
    client.patch(f"/api/events/{event_id}", json={"room": "3号館301"})

    response = client.patch(
        f"/api/subjects/{subject_id}", json={"notes": "教室は3号館201"}
    )

    # 今日以降の自動生成の予定は、授業の設定どおりに作り直される。
    assert response.status_code == 200
    events = events_on(app, subject_id, FUTURE_MONDAY, is_generated=True)
    assert [(room, title) for _, room, title in events] == [
        ("3号館201", "プログラミング基礎")
    ]


def test_deleted_generated_event_is_restored_by_subject_patch(
    client, app, semester_id
):
    subject_id = create_subject_with_events(client, semester_id)
    event_id = generated_event_id(app, subject_id, FUTURE_MONDAY)
    client.delete(f"/api/events/{event_id}")

    response = client.patch(
        f"/api/subjects/{subject_id}", json={"room": "3号館202"}
    )

    assert response.status_code == 200
    events = events_on(app, subject_id, FUTURE_MONDAY, is_generated=True)
    assert [room for _, room, _ in events] == ["3号館202"]


def test_closure_creation_deletes_edited_generated_event_only(
    client, app, semester_id
):
    subject_id = create_subject_with_events(client, semester_id)
    event_id = generated_event_id(app, subject_id, FUTURE_MONDAY)
    client.patch(f"/api/events/{event_id}", json={"room": "3号館301"})
    one_off = create_event(
        client, class_payload(subject_id, date=FUTURE_MONDAY.isoformat())
    )

    response = client.post(
        "/api/closures",
        json={"semester_id": semester_id, "date": FUTURE_MONDAY.isoformat()},
    )

    # 個別に編集した自動生成の予定も削除され、単発の予定は残る。
    assert response.status_code == 201
    assert events_on(app, subject_id, FUTURE_MONDAY, is_generated=True) == []
    assert client.get(f"/api/events/{one_off['id']}").json == one_off


def test_closure_deletion_restores_deleted_generated_event(
    client, app, semester_id
):
    subject_id = create_subject_with_events(client, semester_id)
    event_id = generated_event_id(app, subject_id, FUTURE_MONDAY)
    client.delete(f"/api/events/{event_id}")
    closure = client.post(
        "/api/closures",
        json={"semester_id": semester_id, "date": FUTURE_MONDAY.isoformat()},
    ).json

    response = client.delete(f"/api/closures/{closure['id']}")

    # 個別に削除したことは記録しないため、休講日の削除で、予定が作られる。
    assert response.status_code == 204
    events = events_on(app, subject_id, FUTURE_MONDAY, is_generated=True)
    assert len(events) == 1


def test_subject_deletion_removes_its_one_off_events_only(
    client, app, subject_id
):
    create_event(client, class_payload(subject_id))
    part_time = create_event(client, part_time_payload())
    other = create_event(client, other_payload())

    response = client.delete(f"/api/subjects/{subject_id}")

    assert response.status_code == 204
    listed = client.get(
        "/api/events?start_date=2026-06-01&end_date=2026-06-30"
    )
    assert listed.json == [part_time, other]


def test_registered_and_edited_employers_are_candidates(client):
    first = create_event(client, part_time_payload(employer="派遣会社A"))
    create_event(client, part_time_payload(employer="派遣会社B"))
    client.patch(
        f"/api/events/{first['id']}", json={"employer": "派遣会社C"}
    )

    response = client.get("/api/events/employers")

    # 派遣会社Aを持つ予定は、編集で、なくなった。
    assert response.json == ["派遣会社B", "派遣会社C"]
