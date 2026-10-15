"""課題・タスクのAPI（/api/tasks）のテスト。"""

from datetime import date, datetime, time

import pytest
from sqlalchemy import func, select

from app.api_helpers import MAX_ID, UNUSABLE_CHARACTER_MESSAGE
from app.extensions import db
from app.models.semester import Semester
from app.models.subject import Subject
from app.models.task import Task


CATEGORY_MESSAGE = "カテゴリは「assignment」か「other」で指定してください"
DATETIME_MESSAGE = (
    "締切日時は実在する日時を「YYYY-MM-DDTHH:MM」の形式で指定してください"
)
COMPLETED_MESSAGE = "完了の状態は「true」か「false」で指定してください"
OTHER_SUBJECT_MESSAGE = "その他（締切のみ）には、授業を指定できません"
NOT_ALLOWED_MESSAGE = "この項目は指定できません"
OBJECT_MESSAGE = "リクエストの本文は、JSONのオブジェクトにしてください"

# 本文から項目を除くことを表す値（項目がない場合の検証に使う）。
MISSING = object()


def make_semester(app):
    with app.app_context():
        semester = Semester(
            name="2026年度 後期",
            start_date=date(2026, 9, 21),
            end_date=date(2027, 1, 29),
        )
        db.session.add(semester)
        db.session.commit()
        return semester.id


def make_subject(app, semester_id, subject_name="プログラミング基礎"):
    """授業を、ORMで直接作る（課題のテストには、予定が要らないため）。"""
    with app.app_context():
        subject = Subject(
            semester_id=semester_id,
            subject_name=subject_name,
            weekday=0,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        db.session.add(subject)
        db.session.commit()
        return subject.id


@pytest.fixture
def semester_id(app):
    return make_semester(app)


@pytest.fixture
def subject_id(app, semester_id):
    return make_subject(app, semester_id)


def assignment_payload(subject_id, **overrides):
    payload = {
        "category": "assignment",
        "subject_id": subject_id,
        "title": "レポート第1回",
        "due_datetime": "2026-10-20T23:59",
        "notes": "A4で2枚",
    }
    payload.update(overrides)
    return payload


def other_payload(**overrides):
    payload = {
        "category": "other",
        "title": "健康診断の予約",
        "due_datetime": "2026-10-31T17:00",
    }
    payload.update(overrides)
    return payload


def replace_field(payload, field, value):
    """本文の1つの項目を、value にする（MISSING なら、項目を除く）。"""
    payload = dict(payload)
    if value is MISSING:
        del payload[field]
    else:
        payload[field] = value
    return payload


def create_task(client, payload):
    """課題・タスクをAPIで登録し、レスポンスの本文を返す。"""
    response = client.post("/api/tasks", json=payload)
    assert response.status_code == 201
    return response.json


def task_count(app):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(Task))


def all_task_rows(app):
    """すべての課題・タスクの値を、IDの順に返す（変わっていないことの確認用）。"""
    with app.app_context():
        tasks = db.session.scalars(select(Task).order_by(Task.id)).all()
        return [
            (
                task.id,
                task.subject_id,
                task.category,
                task.title,
                task.due_datetime,
                task.notes,
                task.is_completed,
            )
            for task in tasks
        ]


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


def test_create_assignment_returns_task(client, subject_id):
    response = client.post("/api/tasks", json=assignment_payload(subject_id))

    assert response.status_code == 201
    assert response.json == {
        "id": response.json["id"],
        "category": "assignment",
        "subject_id": subject_id,
        "subject_name": "プログラミング基礎",
        "title": "レポート第1回",
        "due_datetime": "2026-10-20T23:59",
        "notes": "A4で2枚",
        "is_completed": False,
    }


def test_create_assignment_saves_row(client, app, subject_id):
    created = create_task(client, assignment_payload(subject_id))

    assert all_task_rows(app) == [
        (
            created["id"],
            subject_id,
            "assignment",
            "レポート第1回",
            datetime(2026, 10, 20, 23, 59),
            "A4で2枚",
            False,
        )
    ]


@pytest.mark.parametrize("subject_value", [MISSING, None])
def test_create_other_without_subject(client, app, subject_value):
    payload = replace_field(
        other_payload(subject_id=None), "subject_id", subject_value
    )

    response = client.post("/api/tasks", json=payload)

    assert response.status_code == 201
    assert response.json == {
        "id": response.json["id"],
        "category": "other",
        "subject_id": None,
        "subject_name": None,
        "title": "健康診断の予約",
        "due_datetime": "2026-10-31T17:00",
        "notes": None,
        "is_completed": False,
    }
    assert task_count(app) == 1


def test_create_strips_title_and_clears_blank_notes(client, subject_id):
    created = create_task(
        client,
        assignment_payload(subject_id, title="　 レポート ", notes="  "),
    )

    assert created["title"] == "レポート"
    assert created["notes"] is None


def test_create_accepts_past_due_datetime(client, subject_id):
    created = create_task(
        client,
        assignment_payload(subject_id, due_datetime="2020-01-01T00:00"),
    )

    assert created["due_datetime"] == "2020-01-01T00:00"


def test_create_accepts_title_of_200_characters(client, subject_id):
    created = create_task(
        client, assignment_payload(subject_id, title="あ" * 200)
    )

    assert created["title"] == "あ" * 200


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (MISSING, "カテゴリは必須です"),
        (None, "カテゴリは必須です"),
        ("", "カテゴリは必須です"),
        ("class", CATEGORY_MESSAGE),
        ("part_time", CATEGORY_MESSAGE),
        ("Assignment", CATEGORY_MESSAGE),
        (" assignment", CATEGORY_MESSAGE),
        ("課題", CATEGORY_MESSAGE),
        (1, CATEGORY_MESSAGE),
        (True, CATEGORY_MESSAGE),
        (["assignment"], CATEGORY_MESSAGE),
        ("\ud800", UNUSABLE_CHARACTER_MESSAGE),
    ],
)
def test_create_category_is_validated(client, subject_id, value, message):
    payload = replace_field(
        assignment_payload(subject_id), "category", value
    )

    response = client.post("/api/tasks", json=payload)

    assert_validation_error(response, {"category": message})


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (MISSING, "タイトルは必須です"),
        (None, "タイトルは必須です"),
        ("", "タイトルは必須です"),
        ("　 ", "タイトルは必須です"),
        (1, "タイトルは文字列で指定してください"),
        ("あ" * 201, "タイトルは200文字以内にしてください"),
        ("レポート\ud800", UNUSABLE_CHARACTER_MESSAGE),
    ],
)
def test_create_title_is_validated(client, subject_id, value, message):
    payload = replace_field(assignment_payload(subject_id), "title", value)

    response = client.post("/api/tasks", json=payload)

    assert_validation_error(response, {"title": message})


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (MISSING, "締切日時は必須です"),
        (None, "締切日時は必須です"),
        ("", "締切日時は必須です"),
        ("2026-10-20", DATETIME_MESSAGE),
        ("2026-10-20 23:59", DATETIME_MESSAGE),
        ("2026-10-20T23:59:00", DATETIME_MESSAGE),
        ("2026-10-20T24:00", DATETIME_MESSAGE),
        ("2026-02-30T10:00", DATETIME_MESSAGE),
        (20261020, DATETIME_MESSAGE),
        ("2026-10-20T23:59\ud800", UNUSABLE_CHARACTER_MESSAGE),
    ],
)
def test_create_due_datetime_is_validated(
    client, subject_id, value, message
):
    payload = replace_field(
        assignment_payload(subject_id), "due_datetime", value
    )

    response = client.post("/api/tasks", json=payload)

    assert_validation_error(response, {"due_datetime": message})


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (1, "詳細・メモは文字列で指定してください"),
        ("メモ\ud800", UNUSABLE_CHARACTER_MESSAGE),
    ],
)
def test_create_notes_is_validated(client, subject_id, value, message):
    payload = replace_field(assignment_payload(subject_id), "notes", value)

    response = client.post("/api/tasks", json=payload)

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
def test_create_assignment_subject_id_is_validated(
    client, subject_id, value, message
):
    payload = replace_field(
        assignment_payload(subject_id), "subject_id", value
    )

    response = client.post("/api/tasks", json=payload)

    assert_validation_error(response, {"subject_id": message})


def test_create_other_rejects_existing_subject_id(client, subject_id):
    response = client.post(
        "/api/tasks", json=other_payload(subject_id=subject_id)
    )

    assert_validation_error(response, {"subject_id": OTHER_SUBJECT_MESSAGE})


@pytest.mark.parametrize("value", [0, "", "1", 99999])
def test_create_other_rejects_any_subject_id_value(client, value):
    response = client.post("/api/tasks", json=other_payload(subject_id=value))

    assert_validation_error(response, {"subject_id": OTHER_SUBJECT_MESSAGE})


def test_create_invalid_category_skips_subject_id_validation(client):
    # カテゴリに誤りがあると、対象授業の規則が決まらないため、検査しない。
    payload = other_payload(category="class")

    response = client.post("/api/tasks", json=payload)

    assert_validation_error(response, {"category": CATEGORY_MESSAGE})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", 1),
        ("is_completed", False),
        ("subject_name", "プログラミング基礎"),
        ("priority", "high"),
    ],
)
def test_create_rejects_unknown_and_read_only_fields(
    client, subject_id, field, value
):
    payload = assignment_payload(subject_id, **{field: value})

    response = client.post("/api/tasks", json=payload)

    assert_validation_error(response, {field: NOT_ALLOWED_MESSAGE})


def test_create_validation_errors_are_returned_together(client):
    response = client.post(
        "/api/tasks",
        json={
            "category": "assignment",
            "title": "",
            "due_datetime": "2026-10-20",
            "is_completed": True,
        },
    )

    assert_validation_error(
        response,
        {
            "subject_id": "授業IDは必須です",
            "title": "タイトルは必須です",
            "due_datetime": DATETIME_MESSAGE,
            "is_completed": NOT_ALLOWED_MESSAGE,
        },
    )


def test_failed_create_saves_nothing(client, app, subject_id):
    response = client.post(
        "/api/tasks", json=assignment_payload(subject_id, title="")
    )

    assert response.status_code == 400
    assert task_count(app) == 0


@pytest.mark.parametrize("body", ["[]", '"レポート"', "1", "true", "null"])
def test_create_non_object_payload_has_no_fields(client, body):
    response = client.post(
        "/api/tasks", data=body, content_type="application/json"
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
        "/api/tasks", data=data, content_type=content_type
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_json"


# --- 一覧（GET /api/tasks） ---


def test_task_list_is_empty_without_tasks(client):
    response = client.get("/api/tasks")

    assert response.status_code == 200
    assert response.json == []


def test_task_list_is_ordered_by_due_datetime_and_id(client, subject_id):
    later_first = create_task(
        client,
        assignment_payload(subject_id, due_datetime="2026-10-20T23:59"),
    )
    earliest = create_task(
        client, other_payload(due_datetime="2026-10-19T09:00")
    )
    later_second = create_task(
        client,
        assignment_payload(subject_id, due_datetime="2026-10-20T23:59"),
    )
    middle = create_task(
        client, other_payload(due_datetime="2026-10-20T09:00")
    )

    response = client.get("/api/tasks")

    assert [task["id"] for task in response.json] == [
        earliest["id"],
        middle["id"],
        later_first["id"],
        later_second["id"],
    ]


def test_task_list_items_are_same_as_created_tasks(client, subject_id):
    assignment = create_task(client, assignment_payload(subject_id))
    other = create_task(client, other_payload())

    response = client.get("/api/tasks")

    assert response.json == [assignment, other]


@pytest.mark.parametrize(
    ("query", "expected_titles"),
    [
        ("true", ["完了した課題"]),
        ("false", ["未完了の課題", "未完了のその他"]),
    ],
)
def test_task_list_filters_by_completion(
    client, subject_id, query, expected_titles
):
    create_task(client, assignment_payload(subject_id, title="未完了の課題"))
    completed = create_task(
        client, assignment_payload(subject_id, title="完了した課題")
    )
    create_task(client, other_payload(title="未完了のその他"))
    client.patch(
        f"/api/tasks/{completed['id']}", json={"is_completed": True}
    )

    response = client.get(f"/api/tasks?is_completed={query}")

    assert response.status_code == 200
    assert [task["title"] for task in response.json] == expected_titles


@pytest.mark.parametrize(
    "value",
    ["", "True", "FALSE", "1", "0", "yes", " true", "false "],
)
def test_task_list_rejects_invalid_completion_query(client, value):
    response = client.get(
        "/api/tasks", query_string={"is_completed": value}
    )

    assert_validation_error(response, {"is_completed": COMPLETED_MESSAGE})


def test_task_list_rejects_repeated_completion_query(client):
    response = client.get("/api/tasks?is_completed=true&is_completed=true")

    assert_validation_error(
        response, {"is_completed": "完了の状態は1つだけ指定してください"}
    )


def test_task_list_ignores_unknown_query(client, subject_id):
    create_task(client, assignment_payload(subject_id))
    create_task(client, other_payload())

    response = client.get("/api/tasks?subject_id=99999&foo=bar")

    assert response.status_code == 200
    assert len(response.json) == 2


def test_subject_name_is_current_subject_name(client, app, subject_id):
    created = create_task(client, assignment_payload(subject_id))
    with app.app_context():
        db.session.get(Subject, subject_id).subject_name = "データ構造"
        db.session.commit()

    response = client.get(f"/api/tasks/{created['id']}")

    assert response.json["subject_name"] == "データ構造"


# --- 1件取得（GET /api/tasks/<id>） ---


def test_task_get_returns_task(client, subject_id):
    created = create_task(client, assignment_payload(subject_id))

    response = client.get(f"/api/tasks/{created['id']}")

    assert response.status_code == 200
    assert response.json == created


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/tasks/99999", "課題・タスクが見つかりません"),
        ("/api/tasks/0", "課題・タスクが見つかりません"),
        (f"/api/tasks/{MAX_ID}", "課題・タスクが見つかりません"),
        (f"/api/tasks/{MAX_ID + 1}", "URLが見つかりません"),
        ("/api/tasks/99999999999999999999", "URLが見つかりません"),
        ("/api/tasks/abc", "URLが見つかりません"),
        ("/api/tasks/-1", "URLが見つかりません"),
        ("/api/tasks/", "URLが見つかりません"),
    ],
)
def test_task_get_not_found_and_invalid_urls(client, url, message):
    response = client.get(url)

    assert response.status_code == 404
    assert response.json == {
        "error": {"code": "not_found", "message": message}
    }


# --- 編集（PATCH） ---


def test_patch_changes_only_given_fields(client, subject_id):
    created = create_task(client, assignment_payload(subject_id))

    response = client.patch(
        f"/api/tasks/{created['id']}", json={"title": " レポート第2回 "}
    )

    assert response.status_code == 200
    assert response.json == dict(created, title="レポート第2回")
    assert client.get(f"/api/tasks/{created['id']}").json == response.json


def test_patch_can_change_all_editable_fields(
    client, app, semester_id, subject_id
):
    other_subject_id = make_subject(app, semester_id, "データ構造")
    created = create_task(client, assignment_payload(subject_id))

    response = client.patch(
        f"/api/tasks/{created['id']}",
        json={
            "subject_id": other_subject_id,
            "title": "演習問題",
            "due_datetime": "2026-11-02T09:00",
            "notes": "第3章",
            "is_completed": True,
        },
    )

    assert response.status_code == 200
    assert response.json == {
        "id": created["id"],
        "category": "assignment",
        "subject_id": other_subject_id,
        "subject_name": "データ構造",
        "title": "演習問題",
        "due_datetime": "2026-11-02T09:00",
        "notes": "第3章",
        "is_completed": True,
    }


def test_patch_completion_can_be_undone(client, subject_id):
    created = create_task(client, assignment_payload(subject_id))
    url = f"/api/tasks/{created['id']}"
    client.patch(url, json={"is_completed": True})

    response = client.patch(url, json={"is_completed": False})

    assert response.status_code == 200
    assert response.json == created


@pytest.mark.parametrize("value", [None, "", "  "])
def test_patch_can_clear_notes(client, subject_id, value):
    created = create_task(client, assignment_payload(subject_id))

    response = client.patch(
        f"/api/tasks/{created['id']}", json={"notes": value}
    )

    assert response.status_code == 200
    assert response.json["notes"] is None


def test_patch_other_accepts_null_subject_id(client):
    created = create_task(client, other_payload())

    response = client.patch(
        f"/api/tasks/{created['id']}", json={"subject_id": None}
    )

    assert response.status_code == 200
    assert response.json == created


def test_patch_other_rejects_subject_id(client, subject_id):
    created = create_task(client, other_payload())

    response = client.patch(
        f"/api/tasks/{created['id']}", json={"subject_id": subject_id}
    )

    assert_validation_error(response, {"subject_id": OTHER_SUBJECT_MESSAGE})


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (None, "授業IDは必須です"),
        ("", "授業IDは必須です"),
        ("1", "授業IDは整数で指定してください"),
        (0, "指定された授業が存在しません"),
        (99999, "指定された授業が存在しません"),
    ],
)
def test_patch_assignment_subject_id_is_validated(
    client, subject_id, value, message
):
    created = create_task(client, assignment_payload(subject_id))

    response = client.patch(
        f"/api/tasks/{created['id']}", json={"subject_id": value}
    )

    assert_validation_error(response, {"subject_id": message})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("title", None, "タイトルは必須です"),
        ("title", "", "タイトルは必須です"),
        ("title", "　 ", "タイトルは必須です"),
        ("title", 1, "タイトルは文字列で指定してください"),
        ("title", "あ" * 201, "タイトルは200文字以内にしてください"),
        ("title", "\ud800", UNUSABLE_CHARACTER_MESSAGE),
        ("due_datetime", None, "締切日時は必須です"),
        ("due_datetime", "2026-11-02", DATETIME_MESSAGE),
        ("due_datetime", "\ud800", UNUSABLE_CHARACTER_MESSAGE),
        ("notes", 1, "詳細・メモは文字列で指定してください"),
        ("is_completed", None, "完了の状態は必須です"),
        ("is_completed", "", "完了の状態は必須です"),
        ("is_completed", "true", COMPLETED_MESSAGE),
        ("is_completed", 1, COMPLETED_MESSAGE),
        ("is_completed", 0, COMPLETED_MESSAGE),
    ],
)
def test_patch_field_values_are_validated(
    client, subject_id, field, value, message
):
    created = create_task(client, assignment_payload(subject_id))

    response = client.patch(
        f"/api/tasks/{created['id']}", json={field: value}
    )

    assert_validation_error(response, {field: message})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("category", "other"),
        ("category", "assignment"),
        ("id", 1),
        ("subject_name", "データ構造"),
        ("priority", "high"),
    ],
)
def test_patch_rejects_category_and_unknown_fields(
    client, subject_id, field, value
):
    created = create_task(client, assignment_payload(subject_id))

    response = client.patch(
        f"/api/tasks/{created['id']}", json={field: value}
    )

    assert_validation_error(response, {field: NOT_ALLOWED_MESSAGE})


def test_patch_empty_object_is_validation_error_without_fields(
    client, subject_id
):
    created = create_task(client, assignment_payload(subject_id))

    response = client.patch(f"/api/tasks/{created['id']}", json={})

    assert response.status_code == 400
    assert response.json == {
        "error": {
            "code": "validation_error",
            "message": "変更する項目を指定してください",
        }
    }


def test_patch_validation_errors_are_returned_together(client, subject_id):
    created = create_task(client, assignment_payload(subject_id))

    response = client.patch(
        f"/api/tasks/{created['id']}",
        json={
            "title": "",
            "is_completed": "yes",
            "category": "other",
        },
    )

    assert_validation_error(
        response,
        {
            "title": "タイトルは必須です",
            "is_completed": COMPLETED_MESSAGE,
            "category": NOT_ALLOWED_MESSAGE,
        },
    )


def test_failed_patch_changes_nothing(client, app, subject_id):
    create_task(client, assignment_payload(subject_id))
    before = all_task_rows(app)

    response = client.patch(
        f"/api/tasks/{before[0][0]}",
        json={"title": "演習問題", "due_datetime": "2026-11-02"},
    )

    assert response.status_code == 400
    assert all_task_rows(app) == before


@pytest.mark.parametrize("body", ["[]", '"レポート"', "1", "true", "null"])
def test_patch_non_object_payload_has_no_fields(client, subject_id, body):
    created = create_task(client, assignment_payload(subject_id))

    response = client.patch(
        f"/api/tasks/{created['id']}",
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
    client, subject_id, data, content_type
):
    created = create_task(client, assignment_payload(subject_id))

    response = client.patch(
        f"/api/tasks/{created['id']}", data=data, content_type=content_type
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_json"


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/tasks/99999", "課題・タスクが見つかりません"),
        ("/api/tasks/0", "課題・タスクが見つかりません"),
        (f"/api/tasks/{MAX_ID}", "課題・タスクが見つかりません"),
        ("/api/tasks/abc", "URLが見つかりません"),
        ("/api/tasks/-1", "URLが見つかりません"),
    ],
)
def test_patch_not_found_and_invalid_urls(client, url, message):
    response = client.patch(url, json={"title": "演習問題"})

    assert response.status_code == 404
    assert response.json == {
        "error": {"code": "not_found", "message": message}
    }


def test_patch_missing_task_is_404_before_reading_body(client):
    response = client.patch(
        "/api/tasks/99999", data="not json", content_type="text/plain"
    )

    assert response.status_code == 404
    assert response.json["error"]["message"] == "課題・タスクが見つかりません"


# --- 削除（DELETE） ---


def test_delete_task_removes_only_that_task(client, app, subject_id):
    deleted = create_task(client, assignment_payload(subject_id))
    kept = create_task(client, other_payload())

    response = client.delete(f"/api/tasks/{deleted['id']}")

    assert response.status_code == 204
    assert response.data == b""
    assert client.get("/api/tasks").json == [kept]
    with app.app_context():
        assert db.session.get(Subject, subject_id) is not None


def test_delete_task_ignores_body(client, subject_id):
    created = create_task(client, assignment_payload(subject_id))

    response = client.delete(
        f"/api/tasks/{created['id']}",
        data="not json",
        content_type="text/plain",
    )

    assert response.status_code == 204


def test_deleted_task_cannot_be_deleted_again(client, subject_id):
    created = create_task(client, assignment_payload(subject_id))
    client.delete(f"/api/tasks/{created['id']}")

    response = client.delete(f"/api/tasks/{created['id']}")

    assert response.status_code == 404
    assert response.json["error"]["message"] == "課題・タスクが見つかりません"


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/tasks/99999", "課題・タスクが見つかりません"),
        ("/api/tasks/0", "課題・タスクが見つかりません"),
        (f"/api/tasks/{MAX_ID}", "課題・タスクが見つかりません"),
        ("/api/tasks/abc", "URLが見つかりません"),
        ("/api/tasks/-1", "URLが見つかりません"),
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
    "task_id_text", [str(MAX_ID + 1), "99999999999999999999"]
)
def test_over_limit_id_for_patch_and_delete_is_method_not_allowed(
    client, method, task_id_text
):
    # docs/architecture.md の「404の使い分け」の注意（Flaskの仕組みにより、
    # 同じURLにほかのメソッドのrouteがあると、405になる）。
    response = getattr(client, method)(f"/api/tasks/{task_id_text}")

    assert response.status_code == 405
    assert response.json["error"]["code"] == "method_not_allowed"


# --- 提供しないメソッド ---


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("put", "/api/tasks/{task_id}"),
        ("post", "/api/tasks/{task_id}"),
        ("put", "/api/tasks"),
        ("patch", "/api/tasks"),
        ("delete", "/api/tasks"),
    ],
)
def test_unsupported_task_methods_do_not_change_rows(
    client, app, subject_id, method, url
):
    created = create_task(client, assignment_payload(subject_id))
    before = all_task_rows(app)

    response = getattr(client, method)(url.format(task_id=created["id"]))

    assert response.status_code == 405
    assert response.json["error"]["code"] == "method_not_allowed"
    assert all_task_rows(app) == before


# --- 授業の削除との関係 ---


def test_deleting_subject_removes_only_its_tasks(
    client, app, semester_id, subject_id
):
    other_subject_id = make_subject(app, semester_id, "データ構造")
    create_task(client, assignment_payload(subject_id))
    kept_assignment = create_task(
        client, assignment_payload(other_subject_id)
    )
    kept_other = create_task(client, other_payload())

    response = client.delete(f"/api/subjects/{subject_id}")

    assert response.status_code == 204
    assert client.get("/api/tasks").json == [kept_assignment, kept_other]
