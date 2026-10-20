"""学期の編集（PATCH）・削除（DELETE）と、1件取得の件数のAPIのテスト。

学期の登録・一覧・1件取得の基本と、APIの共通の確認（405の Allow
ヘッダーなど）は、tests/test_semesters_api.py で確かめる。
学期のAPIは「今日」を使わないため、テストの結果は、実行した日によらない。
"""

from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy import func, select

from app.api_helpers import MAX_ID, UNUSABLE_CHARACTER_MESSAGE
from app.extensions import db
from app.models.closure import Closure
from app.models.event import Event
from app.models.semester import Semester
from app.models.subject import Subject
from app.models.task import Task


# 学期の期間（2026-04-01（水）〜2026-07-31（金））。
START = date(2026, 4, 1)
END = date(2026, 7, 31)

NAME_FORMAT_MESSAGE = "学期名は「2026年度 前期」の形式で指定してください"
DATE_FORMAT_MESSAGES = {
    "start_date": (
        "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
    ),
    "end_date": (
        "終了日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
    ),
}
DATE_REQUIRED_MESSAGES = {
    "start_date": "開始日は必須です",
    "end_date": "終了日は必須です",
}
END_DATE_ORDER_MESSAGE = "終了日は開始日より後にしてください"
HAS_SUBJECTS_MESSAGE = (
    "授業が登録されている学期は削除できません。"
    "先に、授業をすべて削除してください"
)


def days_of_weekday(start_date, end_date, weekday):
    """期間（両端を含む）の中で、曜日が一致する日を、昇順で返す。

    テストの期待値を、アプリのコードを使わずに求めるための関数。
    """
    days = []
    current = start_date
    while current <= end_date:
        if current.weekday() == weekday:
            days.append(current)
        current += timedelta(days=1)
    return days


MONDAYS = days_of_weekday(START, END, 0)


def make_semester(app, name="2026年度 前期", start=START, end=END):
    with app.app_context():
        semester = Semester(name=name, start_date=start, end_date=end)
        db.session.add(semester)
        db.session.commit()
        return semester.id


def create_subject(client, semester_id, **overrides):
    """授業をAPIで登録し（予定も作られる）、授業のIDを返す。"""
    payload = {
        "semester_id": semester_id,
        "subject_name": "プログラミング基礎",
        "room": "3号館201",
        "weekday": 0,
        "start_time": "09:00",
        "end_time": "10:00",
        "notes": "前期の授業",
    }
    payload.update(overrides)
    response = client.post("/api/subjects", json=payload)
    assert response.status_code == 201
    return response.json["id"]


def make_closure(app, semester_id, closure_date):
    with app.app_context():
        db.session.add(Closure(semester_id=semester_id, date=closure_date))
        db.session.commit()


def make_one_off_event(app, subject_id, event_date):
    """授業の単発の予定（is_generated=False）を、ORMで直接作る。"""
    with app.app_context():
        event = Event(
            subject_id=subject_id,
            category="class",
            date=event_date,
            start_time=time(15, 0),
            end_time=time(16, 0),
            title="補講",
            is_generated=False,
        )
        db.session.add(event)
        db.session.commit()
        return event.id


def make_part_time_event(app, event_date):
    """授業に結びつかない予定（アルバイト）を、ORMで直接作る。"""
    with app.app_context():
        event = Event(
            category="part_time",
            date=event_date,
            start_time=time(17, 0),
            end_time=time(21, 0),
            title="アルバイト",
        )
        db.session.add(event)
        db.session.commit()
        return event.id


def make_task(app, subject_id):
    """課題（授業がなければ、その他）を、ORMで直接作る。"""
    with app.app_context():
        task = Task(
            subject_id=subject_id,
            category="assignment" if subject_id is not None else "other",
            title="レポート",
            due_datetime=datetime(2026, 9, 30, 23, 59),
        )
        db.session.add(task)
        db.session.commit()
        return task.id


def generated_dates(app, subject_id):
    """授業の自動生成の予定の日付を、昇順で返す（同じ日付が2件あれば2回）。"""
    with app.app_context():
        return list(
            db.session.scalars(
                select(Event.date)
                .where(
                    Event.subject_id == subject_id,
                    Event.is_generated.is_(True),
                )
                .order_by(Event.date, Event.id)
            )
        )


def generated_event_id(app, subject_id, event_date):
    with app.app_context():
        return db.session.scalar(
            select(Event.id).where(
                Event.subject_id == subject_id,
                Event.date == event_date,
                Event.is_generated.is_(True),
            )
        )


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


def all_closure_rows(app):
    """すべての休講日の値を、IDの順に返す。"""
    with app.app_context():
        closures = db.session.scalars(
            select(Closure).order_by(Closure.id)
        ).all()
        return [
            (closure.id, closure.semester_id, closure.date, closure.name)
            for closure in closures
        ]


def all_rows(app):
    """学期・授業・予定・休講日・課題のすべての値（変わっていないことの確認用）。"""
    with app.app_context():
        semesters = [
            (semester.id, semester.name, semester.start_date,
             semester.end_date)
            for semester in db.session.scalars(
                select(Semester).order_by(Semester.id)
            )
        ]
        subjects = [
            (subject.id, subject.semester_id, subject.subject_name)
            for subject in db.session.scalars(
                select(Subject).order_by(Subject.id)
            )
        ]
        tasks = [
            (task.id, task.subject_id, task.title, task.due_datetime)
            for task in db.session.scalars(select(Task).order_by(Task.id))
        ]
    return {
        "semesters": semesters,
        "subjects": subjects,
        "events": all_event_rows(app),
        "closures": all_closure_rows(app),
        "tasks": tasks,
    }


def count_rows(app, model, *conditions):
    with app.app_context():
        return db.session.scalar(
            select(func.count()).select_from(model).where(*conditions)
        )


def assert_validation_error(response, fields):
    assert response.status_code == 400
    assert response.json == {
        "error": {
            "code": "validation_error",
            "message": "入力内容に誤りがあります",
            "fields": fields,
        }
    }


def patch_semester(client, semester_id, body):
    return client.patch(f"/api/semesters/{semester_id}", json=body)


# --- 1件取得（GET /api/semesters/<id>）の件数 ---


def test_semester_get_counts_subjects_and_closures(client, app):
    semester_id = make_semester(app)
    create_subject(client, semester_id)
    create_subject(client, semester_id, weekday=2)
    make_closure(app, semester_id, date(2026, 5, 4))
    make_closure(app, semester_id, date(2026, 5, 6))
    make_closure(app, semester_id, date(2026, 7, 20))
    # ほかの学期の授業と休講日は、数えない。
    other_id = make_semester(app, "2026年度 後期")
    create_subject(client, other_id)
    make_closure(app, other_id, date(2026, 6, 1))

    response = client.get(f"/api/semesters/{semester_id}")

    assert response.status_code == 200
    assert response.json == {
        "id": semester_id,
        "name": "2026年度 前期",
        "start_date": "2026-04-01",
        "end_date": "2026-07-31",
        "subject_count": 2,
        "closure_count": 3,
    }


def test_counts_are_only_in_semester_get(client, app):
    semester_id = make_semester(app)
    expected_keys = {"id", "name", "start_date", "end_date"}

    listing = client.get("/api/semesters")
    created = client.post(
        "/api/semesters",
        json={
            "name": "2026年度 後期",
            "start_date": "2026-09-21",
            "end_date": "2027-01-29",
        },
    )
    updated = patch_semester(client, semester_id, {"name": "2027年度 前期"})

    assert [set(item) for item in listing.json] == [expected_keys]
    assert set(created.json) == expected_keys
    assert set(updated.json) == expected_keys


@pytest.mark.parametrize("method", ["post", "patch"])
@pytest.mark.parametrize("field", ["subject_count", "closure_count"])
def test_count_fields_in_request_are_rejected(client, app, method, field):
    semester_id = make_semester(app)
    if method == "post":
        response = client.post(
            "/api/semesters",
            json={
                "name": "2026年度 後期",
                "start_date": "2026-09-21",
                "end_date": "2027-01-29",
                field: 0,
            },
        )
    else:
        response = patch_semester(client, semester_id, {field: 0})

    assert_validation_error(response, {field: "この項目は指定できません"})


# --- 学期の編集（PATCH）：名前 ---


def test_patch_name_returns_updated_semester(client, app):
    semester_id = make_semester(app)

    response = patch_semester(client, semester_id, {"name": "2027年度 後期"})

    assert response.status_code == 200
    assert response.json == {
        "id": semester_id,
        "name": "2027年度 後期",
        "start_date": "2026-04-01",
        "end_date": "2026-07-31",
    }
    with app.app_context():
        semester = db.session.get(Semester, semester_id)
        assert semester.name == "2027年度 後期"
        assert (semester.start_date, semester.end_date) == (START, END)


def test_patch_name_only_keeps_events_and_closures(client, app):
    semester_id = make_semester(app)
    create_subject(client, semester_id)
    make_closure(app, semester_id, date(2026, 5, 4))
    events_before = all_event_rows(app)
    closures_before = all_closure_rows(app)

    response = patch_semester(client, semester_id, {"name": "2027年度 後期"})

    assert response.status_code == 200
    assert all_event_rows(app) == events_before
    assert all_closure_rows(app) == closures_before


def test_patch_same_name_as_itself_is_accepted(client, app):
    semester_id = make_semester(app)

    response = patch_semester(client, semester_id, {"name": "2026年度 前期"})

    assert response.status_code == 200
    assert response.json["name"] == "2026年度 前期"


def test_patch_name_of_another_semester_is_rejected(client, app):
    semester_id = make_semester(app)
    make_semester(app, "2026年度 後期")

    response = patch_semester(client, semester_id, {"name": "2026年度 後期"})

    assert_validation_error(
        response,
        {"name": "同じ名前の学期がすでに登録されています"},
    )


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (None, "学期名は必須です"),
        ("", "学期名は必須です"),
        (123, "学期名は文字列で指定してください"),
        ("前期", NAME_FORMAT_MESSAGE),
        ("2026年度 前期\n", NAME_FORMAT_MESSAGE),
        (" 2026年度 前期", NAME_FORMAT_MESSAGE),
        ("あ" * 51, "学期名は50文字以内にしてください"),
        ("2026年度 前期\ud800", UNUSABLE_CHARACTER_MESSAGE),
    ],
)
def test_patch_name_is_validated_like_post(client, app, value, message):
    semester_id = make_semester(app)

    response = patch_semester(client, semester_id, {"name": value})

    assert_validation_error(response, {"name": message})


# --- 学期の編集（PATCH）：日付の検証 ---


@pytest.mark.parametrize("field", ["start_date", "end_date"])
@pytest.mark.parametrize(
    ("value", "kind"),
    [
        (None, "required"),
        ("", "required"),
        (20260401, "format"),
        ("2026/04/01", "format"),
        ("2026-02-30", "format"),
        ("\ud800", "unusable"),
    ],
)
def test_patch_dates_are_validated_like_post(client, app, field, value, kind):
    semester_id = make_semester(app)
    messages = {
        "required": DATE_REQUIRED_MESSAGES[field],
        "format": DATE_FORMAT_MESSAGES[field],
        "unusable": UNUSABLE_CHARACTER_MESSAGE,
    }

    response = patch_semester(client, semester_id, {field: value})

    assert_validation_error(response, {field: messages[kind]})


@pytest.mark.parametrize(
    "body",
    [
        {"start_date": "2026-07-31"},
        {"start_date": "2026-08-01"},
        {"end_date": "2026-04-01"},
        {"end_date": "2026-03-31"},
        {"start_date": "2026-05-01", "end_date": "2026-05-01"},
    ],
)
def test_patch_end_date_must_be_after_start_date_after_change(
    client, app, body
):
    # 本文に含まれない日付は、今の値を使って比べる。誤りは、本文に
    # end_date がなくても、end_date のエラーにする。
    semester_id = make_semester(app)

    response = patch_semester(client, semester_id, body)

    assert_validation_error(response, {"end_date": END_DATE_ORDER_MESSAGE})


def test_patch_invalid_date_skips_date_order_validation(client, app):
    semester_id = make_semester(app)

    response = patch_semester(
        client,
        semester_id,
        {"start_date": "2026-13-01", "end_date": "2026-03-01"},
    )

    assert_validation_error(
        response,
        {"start_date": DATE_FORMAT_MESSAGES["start_date"]},
    )


@pytest.mark.parametrize("field", ["id", "color"])
def test_patch_rejects_unknown_and_read_only_fields(client, app, field):
    semester_id = make_semester(app)

    response = patch_semester(client, semester_id, {field: 1})

    assert_validation_error(response, {field: "この項目は指定できません"})


def test_patch_empty_object_is_validation_error_without_fields(client, app):
    semester_id = make_semester(app)

    response = patch_semester(client, semester_id, {})

    assert response.status_code == 400
    assert response.json == {
        "error": {
            "code": "validation_error",
            "message": "変更する項目を指定してください",
        }
    }


@pytest.mark.parametrize("payload", [[], None, "abc", 123, True])
def test_patch_non_object_payload_has_no_fields(client, app, payload):
    semester_id = make_semester(app)
    if payload is None:
        response = client.patch(
            f"/api/semesters/{semester_id}",
            data="null",
            content_type="application/json",
        )
    else:
        response = patch_semester(client, semester_id, payload)

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
        ('{"name":', "application/json"),
        ('{"name":"2027年度 前期"}', "text/plain"),
        ('{"name":"2027年度 前期"}', None),
    ],
)
def test_patch_invalid_json_or_content_type_is_rejected(
    client, app, data, content_type
):
    semester_id = make_semester(app)

    response = client.patch(
        f"/api/semesters/{semester_id}",
        data=data,
        content_type=content_type,
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_json"


def test_patch_validation_errors_are_returned_together(client, app):
    semester_id = make_semester(app)

    response = patch_semester(
        client,
        semester_id,
        {"name": "前期", "start_date": "", "color": "red"},
    )

    assert_validation_error(
        response,
        {
            "name": NAME_FORMAT_MESSAGE,
            "start_date": "開始日は必須です",
            "color": "この項目は指定できません",
        },
    )


def test_failed_patch_changes_nothing(client, app):
    semester_id = make_semester(app)
    create_subject(client, semester_id)
    make_closure(app, semester_id, date(2026, 7, 20))
    rows_before = all_rows(app)

    # 期間の変更は正しいが、名前に誤りがある。
    response = patch_semester(
        client,
        semester_id,
        {"name": "前期", "start_date": "2026-05-01", "end_date": "2026-06-30"},
    )

    assert response.status_code == 400
    assert all_rows(app) == rows_before


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/semesters/99999", "学期が見つかりません"),
        ("/api/semesters/0", "学期が見つかりません"),
        (f"/api/semesters/{MAX_ID}", "学期が見つかりません"),
        ("/api/semesters/abc", "URLが見つかりません"),
        ("/api/semesters/-1", "URLが見つかりません"),
    ],
)
def test_patch_not_found_and_invalid_urls(client, url, message):
    response = client.patch(url, json={"name": "2027年度 前期"})

    assert response.status_code == 404
    assert response.json == {
        "error": {"code": "not_found", "message": message}
    }


def test_patch_missing_semester_is_404_before_reading_body(client):
    # 本文が読めなくても、学期がなければ404。
    response = client.patch(
        "/api/semesters/99999",
        data="not json",
        content_type="text/plain",
    )

    assert response.status_code == 404
    assert response.json["error"]["message"] == "学期が見つかりません"


@pytest.mark.parametrize("method", ["patch", "delete"])
@pytest.mark.parametrize("semester_id", [MAX_ID + 1, 10**20])
def test_over_limit_id_for_patch_and_delete_is_method_not_allowed(
    client, method, semester_id
):
    # 上限を超えるIDは、URLに一致しない。同じURLに、ほかのメソッドの
    # route（GET）があるため、Flaskは405を返す（docs/architecture.md の
    # 「404の使い分け」の注意）。
    response = getattr(client, method)(
        f"/api/semesters/{semester_id}",
        json={"name": "2027年度 前期"},
    )

    assert response.status_code == 405
    assert response.json["error"]["code"] == "method_not_allowed"


# --- 学期の編集（PATCH）：期間の変更と、予定・休講日の同期 ---


def test_shrinking_end_date_deletes_generated_events_after_it(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = patch_semester(client, semester_id, {"end_date": "2026-06-30"})

    assert response.status_code == 200
    assert response.json["end_date"] == "2026-06-30"
    assert generated_dates(app, subject_id) == [
        day for day in MONDAYS if day <= date(2026, 6, 30)
    ]


def test_shrinking_start_date_deletes_generated_events_before_it(
    client, app
):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = patch_semester(
        client, semester_id, {"start_date": "2026-05-01"}
    )

    assert response.status_code == 200
    assert generated_dates(app, subject_id) == [
        day for day in MONDAYS if day >= date(2026, 5, 1)
    ]


def test_extending_end_date_creates_events_for_new_days(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = patch_semester(client, semester_id, {"end_date": "2026-08-31"})

    assert response.status_code == 200
    assert generated_dates(app, subject_id) == days_of_weekday(
        START, date(2026, 8, 31), 0
    )


def test_extending_start_date_creates_events_for_new_days(client, app):
    # 今日より前の日にも、予定を作る（学期のAPIは「今日」を使わない）。
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = patch_semester(
        client, semester_id, {"start_date": "2026-03-01"}
    )

    assert response.status_code == 200
    assert generated_dates(app, subject_id) == days_of_weekday(
        date(2026, 3, 1), END, 0
    )


def test_shifting_period_deletes_one_side_and_creates_the_other(
    client, app
):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = patch_semester(
        client,
        semester_id,
        {"start_date": "2026-05-01", "end_date": "2026-08-31"},
    )

    assert response.status_code == 200
    assert generated_dates(app, subject_id) == days_of_weekday(
        date(2026, 5, 1), date(2026, 8, 31), 0
    )


def test_moving_period_without_overlap_replaces_all_events(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = patch_semester(
        client,
        semester_id,
        {"start_date": "2026-09-21", "end_date": "2026-12-27"},
    )

    assert response.status_code == 200
    assert generated_dates(app, subject_id) == days_of_weekday(
        date(2026, 9, 21), date(2026, 12, 27), 0
    )


def test_period_change_affects_all_subjects_of_the_semester(client, app):
    semester_id = make_semester(app)
    monday_id = create_subject(client, semester_id)
    wednesday_id = create_subject(client, semester_id, weekday=2)

    response = patch_semester(
        client,
        semester_id,
        {"start_date": "2026-04-08", "end_date": "2026-08-05"},
    )

    assert response.status_code == 200
    assert generated_dates(app, monday_id) == days_of_weekday(
        date(2026, 4, 8), date(2026, 8, 5), 0
    )
    assert generated_dates(app, wednesday_id) == days_of_weekday(
        date(2026, 4, 8), date(2026, 8, 5), 2
    )


def test_events_in_both_periods_are_kept_as_they_are(client, app):
    # 両方の期間に入る日の予定は、個別に変更・削除したものも含めて、
    # 変えない（作り直さない）。
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    edited_id = generated_event_id(app, subject_id, date(2026, 6, 8))
    edited = client.patch(
        f"/api/events/{edited_id}",
        json={"room": "5号館101", "start_time": "10:40", "end_time": "12:10"},
    )
    assert edited.status_code == 200
    deleted_id = generated_event_id(app, subject_id, date(2026, 6, 15))
    assert client.delete(f"/api/events/{deleted_id}").status_code == 204
    kept_rows = [
        row for row in all_event_rows(app) if row[3] <= date(2026, 7, 27)
    ]

    response = patch_semester(client, semester_id, {"end_date": "2026-08-31"})

    assert response.status_code == 200
    rows_after = all_event_rows(app)
    assert rows_after[: len(kept_rows)] == kept_rows
    # 個別に削除した日は、戻らない（前の期間の中の日のため）。
    assert date(2026, 6, 15) not in generated_dates(app, subject_id)
    # 新しく期間に入った日の予定だけが、足される。
    assert [row[3] for row in rows_after[len(kept_rows):]] == (
        days_of_weekday(date(2026, 8, 1), date(2026, 8, 31), 0)
    )


def test_new_events_use_current_subject_values(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    # 授業の値を、予定を作り直さずに変える（ORMで直接変える）。
    with app.app_context():
        subject = db.session.get(Subject, subject_id)
        subject.subject_name = "データ構造"
        subject.room = "5号館101"
        subject.notes = None
        db.session.commit()

    response = patch_semester(client, semester_id, {"end_date": "2026-08-10"})

    assert response.status_code == 200
    with app.app_context():
        events = db.session.scalars(
            select(Event)
            .where(Event.subject_id == subject_id)
            .order_by(Event.date)
        ).all()
        values = {
            event.date: (
                event.category,
                event.title,
                event.room,
                event.notes,
                event.start_time,
                event.end_time,
                event.employer,
                event.is_generated,
            )
            for event in events
        }
    assert values[date(2026, 8, 3)] == (
        "class",
        "データ構造",
        "5号館101",
        None,
        time(9, 0),
        time(10, 0),
        None,
        True,
    )
    assert values[date(2026, 8, 10)] == values[date(2026, 8, 3)]
    # 前の期間の中の予定は、登録したときの値のまま。
    assert values[date(2026, 7, 27)][1:4] == (
        "プログラミング基礎",
        "3号館201",
        "前期の授業",
    )


def test_period_change_keeps_one_off_and_unrelated_events(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    one_off_id = make_one_off_event(app, subject_id, date(2026, 7, 25))
    part_time_id = make_part_time_event(app, date(2026, 7, 27))
    rows_before = {row[0]: row for row in all_event_rows(app)}

    response = patch_semester(client, semester_id, {"end_date": "2026-06-30"})

    assert response.status_code == 200
    rows_after = {row[0]: row for row in all_event_rows(app)}
    # 単発の予定は、新しい期間の外でも、残る（変わらない）。
    assert rows_after[one_off_id] == rows_before[one_off_id]
    assert rows_after[part_time_id] == rows_before[part_time_id]


def test_period_change_deletes_closures_outside_new_period(client, app):
    semester_id = make_semester(app)
    make_closure(app, semester_id, date(2026, 4, 6))
    make_closure(app, semester_id, date(2026, 5, 4))
    make_closure(app, semester_id, date(2026, 7, 20))
    # 休講日のあとに登録した授業には、休講日の予定がない。
    subject_id = create_subject(client, semester_id)
    other_id = make_semester(app, "2026年度 後期")
    make_closure(app, other_id, date(2026, 7, 20))

    response = patch_semester(
        client,
        semester_id,
        {"start_date": "2026-04-10", "end_date": "2026-07-10"},
    )

    assert response.status_code == 200
    assert [row[1:3] for row in all_closure_rows(app)] == [
        (semester_id, date(2026, 5, 4)),
        (other_id, date(2026, 7, 20)),
    ]
    # 新しい期間の中に残った休講日には、予定がないまま。
    assert generated_dates(app, subject_id) == [
        day
        for day in days_of_weekday(date(2026, 4, 10), date(2026, 7, 10), 0)
        if day != date(2026, 5, 4)
    ]


def test_period_change_of_semester_without_subjects(client, app):
    semester_id = make_semester(app)
    make_closure(app, semester_id, date(2026, 7, 20))

    response = patch_semester(client, semester_id, {"end_date": "2026-06-30"})

    assert response.status_code == 200
    assert count_rows(app, Closure) == 0
    assert count_rows(app, Event) == 0


def test_period_change_does_not_change_other_semesters_or_tasks(
    client, app
):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    make_task(app, subject_id)
    make_task(app, None)
    other_id = make_semester(app, "2026年度 後期")
    other_subject_id = create_subject(client, other_id)
    other_dates = generated_dates(app, other_subject_id)
    tasks_before = all_rows(app)["tasks"]

    response = patch_semester(
        client,
        semester_id,
        {"start_date": "2026-05-01", "end_date": "2026-08-31"},
    )

    assert response.status_code == 200
    assert generated_dates(app, other_subject_id) == other_dates
    assert all_rows(app)["tasks"] == tasks_before


def test_shrink_then_extend_restores_events_without_duplicates(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    shrunk = patch_semester(client, semester_id, {"end_date": "2026-06-30"})
    restored = patch_semester(client, semester_id, {"end_date": "2026-07-31"})

    assert shrunk.status_code == 200
    assert restored.status_code == 200
    # 同じ授業・同じ日付の自動生成の予定は、1件まで。
    assert generated_dates(app, subject_id) == MONDAYS


def test_patch_with_same_dates_changes_nothing(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    deleted_id = generated_event_id(app, subject_id, date(2026, 6, 15))
    assert client.delete(f"/api/events/{deleted_id}").status_code == 204
    make_closure(app, semester_id, date(2026, 7, 20))
    rows_before = all_rows(app)

    response = patch_semester(
        client,
        semester_id,
        {"start_date": "2026-04-01", "end_date": "2026-07-31"},
    )

    assert response.status_code == 200
    assert all_rows(app) == rows_before


def test_period_change_failure_saves_nothing(client, app, monkeypatch):
    semester_id = make_semester(app)
    create_subject(client, semester_id)
    make_closure(app, semester_id, date(2026, 7, 20))
    rows_before = all_rows(app)

    def fail(*args, **kwargs):
        raise RuntimeError("intentional test failure")

    # routeのモジュールが取り込んだ名前を置き換える。
    monkeypatch.setattr("app.routes.semesters.build_class_event", fail)
    app.config["PROPAGATE_EXCEPTIONS"] = False

    response = patch_semester(
        client,
        semester_id,
        {"start_date": "2026-03-01", "end_date": "2026-06-30"},
    )

    assert response.status_code == 500
    assert response.json["error"]["code"] == "server_error"
    # 学期の更新も、予定・休講日の削除も、保存されない。
    assert all_rows(app) == rows_before


def test_period_change_updates_semester_list_order(client, app):
    first_id = make_semester(app)
    second_id = make_semester(
        app, "2026年度 後期", date(2026, 9, 21), date(2027, 1, 29)
    )

    response = patch_semester(
        client,
        first_id,
        {"start_date": "2027-04-01", "end_date": "2027-07-31"},
    )

    assert response.status_code == 200
    listing = client.get("/api/semesters").json
    assert [item["id"] for item in listing] == [first_id, second_id]


# --- 学期の削除（DELETE） ---


def test_delete_semester_removes_it_and_its_closures(client, app):
    semester_id = make_semester(app)
    make_closure(app, semester_id, date(2026, 5, 4))
    make_closure(app, semester_id, date(2026, 7, 20))

    response = client.delete(f"/api/semesters/{semester_id}")

    assert response.status_code == 204
    assert response.get_data() == b""
    assert client.get(f"/api/semesters/{semester_id}").status_code == 404
    assert count_rows(app, Closure) == 0
    # 休講日が、学期のない行として残っていない。
    assert count_rows(app, Closure, Closure.semester_id.is_(None)) == 0


def test_delete_semester_keeps_other_rows(client, app):
    semester_id = make_semester(app)
    make_closure(app, semester_id, date(2026, 5, 4))
    other_id = make_semester(app, "2026年度 後期")
    other_subject_id = create_subject(client, other_id)
    make_closure(app, other_id, date(2026, 6, 1))
    make_task(app, other_subject_id)
    make_task(app, None)
    make_part_time_event(app, date(2026, 6, 2))
    rows_before = all_rows(app)

    response = client.delete(f"/api/semesters/{semester_id}")

    assert response.status_code == 204
    rows_after = all_rows(app)
    assert rows_after["semesters"] == [
        row for row in rows_before["semesters"] if row[0] != semester_id
    ]
    assert rows_after["closures"] == [
        row for row in rows_before["closures"] if row[1] != semester_id
    ]
    for key in ["subjects", "events", "tasks"]:
        assert rows_after[key] == rows_before[key]


def test_delete_semester_with_subjects_is_conflict(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    make_one_off_event(app, subject_id, date(2026, 6, 20))
    make_task(app, subject_id)
    make_closure(app, semester_id, date(2026, 5, 4))
    rows_before = all_rows(app)

    response = client.delete(f"/api/semesters/{semester_id}")

    assert response.status_code == 409
    assert response.json == {
        "error": {"code": "conflict", "message": HAS_SUBJECTS_MESSAGE}
    }
    # 学期・授業・予定・休講日・課題は、どれも変わらない。
    assert all_rows(app) == rows_before


def test_semester_can_be_deleted_after_its_subjects_are_deleted(
    client, app
):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    assert client.delete(f"/api/semesters/{semester_id}").status_code == 409

    assert client.delete(f"/api/subjects/{subject_id}").status_code == 204
    response = client.delete(f"/api/semesters/{semester_id}")

    assert response.status_code == 204
    assert count_rows(app, Semester) == 0
    assert count_rows(app, Event) == 0


def test_delete_semester_ignores_body(client, app):
    semester_id = make_semester(app)

    response = client.delete(
        f"/api/semesters/{semester_id}",
        data="not json",
        content_type="text/plain",
    )

    assert response.status_code == 204
    assert count_rows(app, Semester) == 0


def test_deleted_semester_cannot_be_deleted_again(client, app):
    semester_id = make_semester(app)
    assert client.delete(f"/api/semesters/{semester_id}").status_code == 204

    response = client.delete(f"/api/semesters/{semester_id}")

    assert response.status_code == 404
    assert response.json["error"]["message"] == "学期が見つかりません"


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/semesters/99999", "学期が見つかりません"),
        ("/api/semesters/0", "学期が見つかりません"),
        (f"/api/semesters/{MAX_ID}", "学期が見つかりません"),
        ("/api/semesters/abc", "URLが見つかりません"),
        ("/api/semesters/-1", "URLが見つかりません"),
    ],
)
def test_delete_not_found_and_invalid_urls(client, app, url, message):
    make_semester(app)

    response = client.delete(url)

    assert response.status_code == 404
    assert response.json == {
        "error": {"code": "not_found", "message": message}
    }
    assert count_rows(app, Semester) == 1
