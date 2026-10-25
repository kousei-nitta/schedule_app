"""授業の編集（PATCH）・削除（DELETE）と、1件取得の件数のAPIのテスト。

授業の登録・一覧・1件取得の基本は、tests/test_subjects_api.py で確かめる。
"""

from datetime import date, datetime, time

import pytest
from sqlalchemy import func, select

from app.api_helpers import MAX_ID, UNUSABLE_CHARACTER_MESSAGE
from app.extensions import db
from app.models.closure import Closure
from app.models.event import Event
from app.models.semester import Semester
from app.models.subject import Subject
from app.models.task import Task


# 「今日」は、2026-06-15（月）に固定する（実行した日によって、結果が
# 変わらないようにするため。fixed_today を参照）。
TODAY = date(2026, 6, 15)

# 学期（2026-04-01〜2026-07-31）の月曜日。
MONDAYS = [
    date(2026, 4, 6),
    date(2026, 4, 13),
    date(2026, 4, 20),
    date(2026, 4, 27),
    date(2026, 5, 4),
    date(2026, 5, 11),
    date(2026, 5, 18),
    date(2026, 5, 25),
    date(2026, 6, 1),
    date(2026, 6, 8),
    date(2026, 6, 15),
    date(2026, 6, 22),
    date(2026, 6, 29),
    date(2026, 7, 6),
    date(2026, 7, 13),
    date(2026, 7, 20),
    date(2026, 7, 27),
]
PAST_MONDAYS = [day for day in MONDAYS if day < TODAY]
FUTURE_MONDAYS = [day for day in MONDAYS if day >= TODAY]

# 学期の、今日以降の水曜日。
FUTURE_WEDNESDAYS = [
    date(2026, 6, 17),
    date(2026, 6, 24),
    date(2026, 7, 1),
    date(2026, 7, 8),
    date(2026, 7, 15),
    date(2026, 7, 22),
    date(2026, 7, 29),
]

FORMAT_MESSAGES = {
    "start_time": (
        "開始時刻は「HH:MM」の形式（00:00〜23:59）で指定してください"
    ),
    "end_time": (
        "終了時刻は「HH:MM」の形式（00:00〜23:59）で指定してください"
    ),
}
WEEKDAY_MESSAGE = "曜日は0（月曜）〜6（日曜）の整数で指定してください"


def set_today(monkeypatch, day):
    """routeが使う「今日」（current_date）を、指定した日にする。"""
    # routeのモジュールの名前を置き換える。
    monkeypatch.setattr("app.routes.subjects.current_date", lambda: day)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    """このファイルのテストでは、「今日」を TODAY にする。"""
    set_today(monkeypatch, TODAY)


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


def subject_payload(semester_id, **overrides):
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
    return payload


def create_subject(client, semester_id, **overrides):
    """授業をAPIで登録し（予定も作られる）、授業のIDを返す。"""
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, **overrides),
    )
    assert response.status_code == 201
    return response.json["id"]


def make_closure(app, semester_id, closure_date):
    with app.app_context():
        db.session.add(Closure(semester_id=semester_id, date=closure_date))
        db.session.commit()


def make_one_off_event(app, subject_id, event_date, title="補講"):
    """授業の単発の予定（is_generated=False）を、ORMで直接作る。"""
    with app.app_context():
        event = Event(
            subject_id=subject_id,
            category="class",
            date=event_date,
            start_time=time(15, 0),
            end_time=time(16, 0),
            title=title,
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


def make_task(app, subject_id, title="レポート"):
    """課題を、ORMで直接作る（課題のAPIは、まだないため）。"""
    with app.app_context():
        task = Task(
            subject_id=subject_id,
            category="assignment" if subject_id is not None else "other",
            title=title,
            due_datetime=datetime(2026, 6, 30, 23, 59),
        )
        db.session.add(task)
        db.session.commit()
        return task.id


def generated_events(app, subject_id):
    """授業の自動生成の予定を、日付の昇順で返す（セッションから切り離す）。"""
    with app.app_context():
        events = db.session.scalars(
            select(Event)
            .where(
                Event.subject_id == subject_id,
                Event.is_generated.is_(True),
            )
            .order_by(Event.date, Event.id)
        ).all()
        db.session.expunge_all()
        return events


def generated_dates(app, subject_id):
    """授業の自動生成の予定の日付（同じ日付が2件あれば2回）。"""
    return [event.date for event in generated_events(app, subject_id)]


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


def all_task_rows(app):
    """すべての課題の値を、IDの順に返す（変わっていないことの確認用）。"""
    with app.app_context():
        tasks = db.session.scalars(select(Task).order_by(Task.id)).all()
        return [
            (task.id, task.subject_id, task.title, task.due_datetime)
            for task in tasks
        ]


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


# --- 1件取得（GET /api/subjects/<id>）の件数 ---


def test_subject_get_counts_events_and_tasks_of_the_subject(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    other_subject_id = create_subject(client, semester_id)
    make_one_off_event(app, subject_id, date(2026, 6, 16))
    make_task(app, subject_id)
    make_task(app, subject_id)
    # ほかの授業の課題と、授業に結びつかない予定・課題は、数えない。
    make_task(app, other_subject_id)
    make_part_time_event(app, date(2026, 6, 16))
    make_task(app, None)

    response = client.get(f"/api/subjects/{subject_id}")

    assert response.status_code == 200
    # 自動生成の17件と、単発の1件。
    assert response.json["event_count"] == 18
    assert response.json["task_count"] == 2


def test_subject_get_counts_are_zero_without_events_and_tasks(client, app):
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
    subject_id = create_subject(client, semester_id)

    response = client.get(f"/api/subjects/{subject_id}")

    assert response.status_code == 200
    assert response.json["event_count"] == 0
    assert response.json["task_count"] == 0


def test_counts_are_not_in_subject_list(client, app):
    semester_id = make_semester(app)
    create_subject(client, semester_id)

    response = client.get("/api/subjects")

    assert response.status_code == 200
    assert "event_count" not in response.json[0]
    assert "task_count" not in response.json[0]


@pytest.mark.parametrize("field", ["event_count", "task_count"])
def test_count_fields_in_post_request_are_rejected(client, app, field):
    semester_id = make_semester(app)

    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, **{field: 0}),
    )

    assert_validation_error(response, {field: "この項目は指定できません"})


# --- 授業の編集（PATCH）：授業の値 ---


def test_patch_changes_only_given_fields_and_returns_subject(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"room": "  5号館301　"},
    )

    assert response.status_code == 200
    # 更新後の授業を返す。付加情報（件数）は含めない。
    assert response.json == {
        "id": subject_id,
        "semester_id": semester_id,
        "subject_name": "プログラミング基礎",
        "room": "5号館301",
        "weekday": 0,
        "start_time": "09:00",
        "end_time": "10:00",
        "notes": "前期の授業",
    }
    with app.app_context():
        subject = db.session.get(Subject, subject_id)
        assert subject.room == "5号館301"
        assert subject.subject_name == "プログラミング基礎"


def test_patch_can_change_all_editable_fields(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={
            "subject_name": "  データ構造　",
            "room": "5号館301",
            "weekday": 2,
            "start_time": "13:00",
            "end_time": "14:30",
            "notes": "  後半は演習  ",
        },
    )

    assert response.status_code == 200
    expected = {
        "id": subject_id,
        "semester_id": semester_id,
        "subject_name": "データ構造",
        "room": "5号館301",
        "weekday": 2,
        "start_time": "13:00",
        "end_time": "14:30",
        "notes": "後半は演習",
    }
    assert response.json == expected
    listed = client.get(f"/api/subjects?semester_id={semester_id}")
    assert listed.json == [expected]


@pytest.mark.parametrize("empty_value", [None, "", "  ", "　"])
def test_patch_can_clear_room_and_notes(client, app, empty_value):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"room": empty_value, "notes": empty_value},
    )

    assert response.status_code == 200
    assert response.json["room"] is None
    assert response.json["notes"] is None
    for event in generated_events(app, subject_id):
        if event.date >= TODAY:
            assert event.room is None
            assert event.notes is None


# --- 授業の編集（PATCH）：今日以降の予定の作り直し ---


def test_patch_rebuilds_events_from_today_with_new_values(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={
            "subject_name": "データ構造",
            "room": "5号館301",
            "start_time": "13:00",
            "end_time": "14:30",
            "notes": "後半は演習",
        },
    )

    assert response.status_code == 200
    events = generated_events(app, subject_id)
    assert [event.date for event in events] == MONDAYS
    for event in events:
        if event.date < TODAY:
            # 今日より前の予定は、登録時の値のまま。
            values = ("プログラミング基礎", "3号館201", "前期の授業")
            times = (time(9, 0), time(10, 0))
        else:
            # 今日（を含む）以降の予定は、新しい値で作り直される。
            values = ("データ構造", "5号館301", "後半は演習")
            times = (time(13, 0), time(14, 30))
        assert (event.title, event.room, event.notes) == values
        assert (event.start_time, event.end_time) == times
        assert event.category == "class"
        assert event.employer is None


def test_patch_weekday_moves_only_events_from_today(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"weekday": 2},
    )

    assert response.status_code == 200
    # 今日より前は月曜日のまま、今日以降は水曜日になる。
    assert generated_dates(app, subject_id) == (
        PAST_MONDAYS + FUTURE_WEDNESDAYS
    )


def test_patch_restores_changed_and_deleted_future_events(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    with app.app_context():
        events = {
            event.date: event
            for event in db.session.scalars(
                select(Event).where(Event.subject_id == subject_id)
            )
        }
        # カレンダーからの個別の編集・削除の代わりに、DBを直接変える。
        events[date(2026, 6, 8)].title = "過去の個別の変更"
        events[date(2026, 6, 22)].title = "今後の個別の変更"
        events[date(2026, 6, 22)].start_time = time(11, 0)
        db.session.delete(events[date(2026, 6, 29)])
        db.session.commit()

    # 値を変えない編集でも、今日以降の予定は作り直される。
    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "プログラミング基礎"},
    )

    assert response.status_code == 200
    events = generated_events(app, subject_id)
    assert [event.date for event in events] == MONDAYS
    titles = {event.date: event.title for event in events}
    # 今日より前の個別の変更は、残る。
    assert titles[date(2026, 6, 8)] == "過去の個別の変更"
    # 今日以降の個別の変更・削除は、設定どおりに戻る。
    assert titles[date(2026, 6, 22)] == "プログラミング基礎"
    assert titles[date(2026, 6, 29)] == "プログラミング基礎"
    start_times = {event.date: event.start_time for event in events}
    assert start_times[date(2026, 6, 22)] == time(9, 0)


def test_patch_keeps_one_off_events(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    make_one_off_event(app, subject_id, date(2026, 6, 1), "過去の補講")
    # 自動生成の予定と同じ日の、単発の予定。
    make_one_off_event(app, subject_id, date(2026, 6, 22), "今後の補講")
    one_off_before = [
        row for row in all_event_rows(app) if row[-1] is False
    ]

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造"},
    )

    assert response.status_code == 200
    one_off_after = [row for row in all_event_rows(app) if row[-1] is False]
    assert one_off_after == one_off_before
    # 単発の予定がある日にも、自動生成の予定は規則どおりに作られる。
    assert generated_dates(app, subject_id) == MONDAYS


def test_patch_does_not_create_events_on_closures(client, app):
    semester_id = make_semester(app)
    other_semester_id = make_semester(app, "2026年度 後期")
    make_closure(app, semester_id, date(2026, 7, 20))
    # ほかの学期の休講日は、この授業の予定に影響しない。
    make_closure(app, other_semester_id, date(2026, 7, 13))
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造"},
    )

    assert response.status_code == 200
    dates = generated_dates(app, subject_id)
    assert date(2026, 7, 20) not in dates
    assert date(2026, 7, 13) in dates
    assert dates == [day for day in MONDAYS if day != date(2026, 7, 20)]


def test_patch_does_not_change_other_subjects_or_part_time(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    other_subject_id = create_subject(client, semester_id)
    make_part_time_event(app, date(2026, 6, 22))
    other_rows_before = [
        row
        for row in all_event_rows(app)
        if row[1] != subject_id
    ]

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造"},
    )

    assert response.status_code == 200
    other_rows_after = [
        row
        for row in all_event_rows(app)
        if row[1] != subject_id
    ]
    assert other_rows_after == other_rows_before
    assert len(generated_dates(app, other_subject_id)) == 17


def test_repeated_patch_does_not_duplicate_generated_events(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    for name in ["データ構造", "アルゴリズム", "データ構造"]:
        response = client.patch(
            f"/api/subjects/{subject_id}",
            json={"subject_name": name},
        )
        assert response.status_code == 200

    # 同じ授業・同じ日付の自動生成の予定は、1件まで。
    assert generated_dates(app, subject_id) == MONDAYS


def test_patch_before_semester_rebuilds_all_events(
    client, app, monkeypatch
):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    set_today(monkeypatch, date(2026, 3, 1))

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造"},
    )

    assert response.status_code == 200
    events = generated_events(app, subject_id)
    assert [event.date for event in events] == MONDAYS
    assert all(event.title == "データ構造" for event in events)


def test_patch_after_semester_changes_only_subject(client, app, monkeypatch):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    rows_before = all_event_rows(app)
    set_today(monkeypatch, date(2026, 8, 1))

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造"},
    )

    assert response.status_code == 200
    assert response.json["subject_name"] == "データ構造"
    # 学期が終わったあとの編集では、予定は変わらない。
    assert all_event_rows(app) == rows_before


def test_patch_on_last_day_of_semester_rebuilds_that_day(
    client, app, monkeypatch
):
    semester_id = make_semester(app)
    # 学期の終了日（2026-07-31）は金曜日。
    subject_id = create_subject(client, semester_id, weekday=4)
    set_today(monkeypatch, date(2026, 7, 31))

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造"},
    )

    assert response.status_code == 200
    titles = {
        event.date: event.title
        for event in generated_events(app, subject_id)
    }
    assert len(titles) == 18
    assert titles[date(2026, 7, 31)] == "データ構造"
    assert titles[date(2026, 7, 24)] == "プログラミング基礎"


def test_patch_failure_during_rebuild_saves_nothing(
    client, app, monkeypatch
):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    subject_before = client.get(f"/api/subjects/{subject_id}").json
    rows_before = all_event_rows(app)

    def fail(*args, **kwargs):
        raise RuntimeError("intentional test failure")

    # routeのモジュールが取り込んだ名前を置き換える。
    monkeypatch.setattr("app.routes.subjects.build_class_events_from", fail)
    app.config["PROPAGATE_EXCEPTIONS"] = False

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造"},
    )

    assert response.status_code == 500
    assert response.json["error"]["code"] == "server_error"
    # 授業の更新も、予定の削除も、保存されない。
    assert client.get(f"/api/subjects/{subject_id}").json == subject_before
    assert all_event_rows(app) == rows_before


# --- 授業の編集（PATCH）：入力の検証 ---


def test_patch_empty_object_is_validation_error_without_fields(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    rows_before = all_event_rows(app)

    response = client.patch(f"/api/subjects/{subject_id}", json={})

    assert response.status_code == 400
    assert response.json == {
        "error": {
            "code": "validation_error",
            "message": "変更する項目を指定してください",
        }
    }
    assert all_event_rows(app) == rows_before


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("subject_name", None, "科目名は必須です"),
        ("subject_name", "", "科目名は必須です"),
        ("subject_name", "　", "科目名は必須です"),
        ("subject_name", 123, "科目名は文字列で指定してください"),
        ("subject_name", "科" * 101, "科目名は100文字以内にしてください"),
        ("subject_name", "\ud800", UNUSABLE_CHARACTER_MESSAGE),
        ("room", 123, "教室は文字列で指定してください"),
        ("room", "教" * 101, "教室は100文字以内にしてください"),
        ("weekday", None, "曜日は必須です"),
        ("weekday", "", "曜日は必須です"),
        ("weekday", 7, WEEKDAY_MESSAGE),
        ("weekday", True, WEEKDAY_MESSAGE),
        ("weekday", "1", WEEKDAY_MESSAGE),
        ("start_time", None, "開始時刻は必須です"),
        ("start_time", "", "開始時刻は必須です"),
        ("start_time", "9:00", FORMAT_MESSAGES["start_time"]),
        ("end_time", None, "終了時刻は必須です"),
        ("end_time", "24:00", FORMAT_MESSAGES["end_time"]),
        ("notes", 123, "詳細・メモは文字列で指定してください"),
        ("notes", "メモ\udfff", UNUSABLE_CHARACTER_MESSAGE),
    ],
)
def test_patch_field_values_are_validated_like_post(
    client, app, field, value, message
):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={field: value},
    )

    assert_validation_error(response, {field: message})


@pytest.mark.parametrize(
    "field",
    [
        "semester_id",
        "id",
        "generated_event_count",
        "event_count",
        "task_count",
        "color",
    ],
)
def test_patch_rejects_semester_id_and_unknown_fields(client, app, field):
    semester_id = make_semester(app)
    other_semester_id = make_semester(app, "2026年度 後期")
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造", field: other_semester_id},
    )

    assert_validation_error(response, {field: "この項目は指定できません"})
    with app.app_context():
        subject = db.session.get(Subject, subject_id)
        assert subject.semester_id == semester_id
        assert subject.subject_name == "プログラミング基礎"


@pytest.mark.parametrize(
    "payload",
    [
        {"end_time": "09:00"},
        {"start_time": "10:00"},
        {"start_time": "11:00", "end_time": "10:30"},
    ],
)
def test_patch_end_time_must_be_after_start_time_after_change(
    client, app, payload
):
    semester_id = make_semester(app)
    # 今の時刻は 09:00〜10:00。本文にない時刻は、今の値と比べる。
    subject_id = create_subject(client, semester_id)

    response = client.patch(f"/api/subjects/{subject_id}", json=payload)

    assert_validation_error(
        response,
        {"end_time": "終了時刻は開始時刻より後にしてください"},
    )


@pytest.mark.parametrize(
    ("payload", "start_time", "end_time"),
    [
        ({"start_time": "09:30"}, "09:30", "10:00"),
        ({"end_time": "09:01"}, "09:00", "09:01"),
        ({"start_time": "11:00", "end_time": "12:00"}, "11:00", "12:00"),
    ],
)
def test_patch_time_change_is_accepted_when_order_is_valid(
    client, app, payload, start_time, end_time
):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(f"/api/subjects/{subject_id}", json=payload)

    assert response.status_code == 200
    assert response.json["start_time"] == start_time
    assert response.json["end_time"] == end_time


def test_patch_invalid_start_time_skips_time_order_validation(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"start_time": "invalid", "end_time": "08:00"},
    )

    assert_validation_error(
        response,
        {"start_time": FORMAT_MESSAGES["start_time"]},
    )


def test_patch_validation_errors_are_returned_together(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "", "weekday": 9, "semester_id": 2},
    )

    assert_validation_error(
        response,
        {
            "subject_name": "科目名は必須です",
            "weekday": WEEKDAY_MESSAGE,
            "semester_id": "この項目は指定できません",
        },
    )


def test_failed_patch_changes_neither_subject_nor_events(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    subject_before = client.get(f"/api/subjects/{subject_id}").json
    rows_before = all_event_rows(app)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造", "weekday": 9},
    )

    assert response.status_code == 400
    assert client.get(f"/api/subjects/{subject_id}").json == subject_before
    assert all_event_rows(app) == rows_before


@pytest.mark.parametrize("payload", [[], "abc", 123, True])
def test_patch_non_object_payload_has_no_fields(client, app, payload):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(f"/api/subjects/{subject_id}", json=payload)

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
        ('{"subject_name":', "application/json"),
        ('{"subject_name":"x"}', "text/plain"),
        ('{"subject_name":"x"}', None),
    ],
)
def test_patch_invalid_json_or_content_type_is_rejected(
    client, app, data, content_type
):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        data=data,
        content_type=content_type,
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_json"


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/subjects/99999", "授業が見つかりません"),
        ("/api/subjects/0", "授業が見つかりません"),
        (f"/api/subjects/{MAX_ID}", "授業が見つかりません"),
        ("/api/subjects/abc", "URLが見つかりません"),
        ("/api/subjects/-1", "URLが見つかりません"),
    ],
)
def test_patch_not_found_and_invalid_urls(client, url, message):
    response = client.patch(url, json={"subject_name": "データ構造"})

    assert response.status_code == 404
    assert response.json == {
        "error": {"code": "not_found", "message": message}
    }


@pytest.mark.parametrize("method", ["patch", "delete"])
@pytest.mark.parametrize("subject_id", [MAX_ID + 1, 10**20])
def test_over_limit_id_for_patch_and_delete_is_method_not_allowed(
    client, method, subject_id
):
    # 上限を超えるIDは、URLに一致しない。同じURLに、ほかのメソッドの
    # route（GET）があるため、Flaskは405を返す（docs/architecture/api.md の
    # 「404の使い分け」の注意）。
    response = getattr(client, method)(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造"},
    )

    assert response.status_code == 405
    assert response.json["error"]["code"] == "method_not_allowed"


def test_patch_missing_subject_is_404_before_reading_body(client):
    # 本文が読めなくても、授業がなければ404。
    response = client.patch(
        "/api/subjects/99999",
        data="not json",
        content_type="text/plain",
    )

    assert response.status_code == 404
    assert response.json["error"]["message"] == "授業が見つかりません"


# --- 授業の削除（DELETE） ---


def test_delete_subject_removes_its_events_and_tasks(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    make_one_off_event(app, subject_id, date(2026, 6, 1))
    make_one_off_event(app, subject_id, date(2026, 6, 22))
    make_task(app, subject_id)

    response = client.delete(f"/api/subjects/{subject_id}")

    assert response.status_code == 204
    assert response.get_data() == b""
    assert client.get(f"/api/subjects/{subject_id}").status_code == 404
    # 過去分を含む、自動生成・単発の予定と、課題が削除される。
    assert count_rows(app, Event, Event.subject_id == subject_id) == 0
    assert count_rows(app, Task, Task.subject_id == subject_id) == 0


def test_delete_subject_leaves_no_rows_without_subject(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    make_one_off_event(app, subject_id, date(2026, 6, 22))
    make_task(app, subject_id)

    response = client.delete(f"/api/subjects/{subject_id}")

    assert response.status_code == 204
    # 授業のない予定・課題（subject_id が NULL）として残らない。
    assert count_rows(app, Event, Event.subject_id.is_(None)) == 0
    assert count_rows(app, Task, Task.subject_id.is_(None)) == 0
    assert count_rows(app, Event) == 0
    assert count_rows(app, Task) == 0


def test_delete_subject_keeps_other_rows(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    other_subject_id = create_subject(client, semester_id)
    make_task(app, subject_id)
    make_task(app, other_subject_id)
    make_part_time_event(app, date(2026, 6, 22))
    make_task(app, None)
    make_closure(app, semester_id, date(2026, 7, 20))
    other_event_rows = [
        row for row in all_event_rows(app) if row[1] != subject_id
    ]
    other_task_rows = [
        row for row in all_task_rows(app) if row[1] != subject_id
    ]

    response = client.delete(f"/api/subjects/{subject_id}")

    assert response.status_code == 204
    # ほかの授業の予定・課題と、授業に結びつかない予定・課題は残る。
    assert all_event_rows(app) == other_event_rows
    assert all_task_rows(app) == other_task_rows
    assert client.get(f"/api/subjects/{other_subject_id}").status_code == 200
    assert client.get(f"/api/semesters/{semester_id}").status_code == 200
    assert count_rows(app, Closure) == 1


def test_delete_subject_ignores_body(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    # DELETE は本文を読まない（Content-Type も求めない）。
    response = client.delete(
        f"/api/subjects/{subject_id}",
        data="not json",
        content_type="text/plain",
    )

    assert response.status_code == 204


def test_deleted_subject_cannot_be_deleted_again(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    assert client.delete(f"/api/subjects/{subject_id}").status_code == 204

    response = client.delete(f"/api/subjects/{subject_id}")

    assert response.status_code == 404
    assert response.json == {
        "error": {"code": "not_found", "message": "授業が見つかりません"}
    }


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/subjects/99999", "授業が見つかりません"),
        ("/api/subjects/0", "授業が見つかりません"),
        (f"/api/subjects/{MAX_ID}", "授業が見つかりません"),
        ("/api/subjects/abc", "URLが見つかりません"),
        ("/api/subjects/-1", "URLが見つかりません"),
    ],
)
def test_delete_not_found_and_invalid_urls(client, app, url, message):
    semester_id = make_semester(app)
    create_subject(client, semester_id)
    rows_before = all_event_rows(app)

    response = client.delete(url)

    assert response.status_code == 404
    assert response.json == {
        "error": {"code": "not_found", "message": message}
    }
    assert all_event_rows(app) == rows_before


def test_delete_collection_url_is_not_allowed(client, app):
    semester_id = make_semester(app)
    create_subject(client, semester_id)

    response = client.delete("/api/subjects")

    assert response.status_code == 405
    assert count_rows(app, Subject) == 1
