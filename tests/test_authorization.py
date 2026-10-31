"""認可（他人のデータに触れない）の網羅的なテスト。

docs/architecture/api.md の「利用者ごとのデータ（認可）」。
- 利用者A（テストの利用者）と利用者Bが、それぞれデータを持つ
- Bが、すべてのAPI（URL×メソッド）で、Aのデータを読む・変える・消す・
  参照する・一覧や候補で知ることを試し、どれもできないことを確かめる
- APIのURL×メソッドの一覧と、このファイルの CASES がずれたら、テストが
  失敗する（新しいAPIを足したら、ここにも足す）
- 未ログインでは、すべてのURL×メソッドが401
- 各テストのあとで、Aのデータが1つも変わっていないことを確かめる
"""
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.extensions import db
from app.models import Closure, Event, Semester, Subject, Task
from tests.auth_support import (
    OTHER_USERNAME,
    TEST_USER_ID,
    create_user,
    logged_in_client,
)

ROUTES_DIRECTORY = Path(__file__).resolve().parents[1] / "app" / "routes"
DATA_MODELS = [Semester, Subject, Closure, Event, Task]

# どちらの利用者も、同じ名前の学期を作る（名前の重複は、利用者ごとに
# 確かめるため、他人の学期と同じ名前でも作れる）
SEMESTER = {
    "name": "2099年度 前期",
    "start_date": "2099-04-06",
    "end_date": "2099-07-20",
}
EVENT_RANGE = "start_date=2099-04-01&end_date=2099-07-31"


def created(response) -> dict:
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def build_data(client, label: str) -> SimpleNamespace:
    """1人の利用者のデータを、APIで作る（予定は、授業の登録で自動で作る）。"""
    semester = created(client.post("/api/semesters", json=SEMESTER))
    closure = created(
        client.post(
            "/api/closures",
            json={"semester_id": semester["id"], "date": "2099-04-13"},
        )
    )
    subject = created(
        client.post(
            "/api/subjects",
            json={
                "semester_id": semester["id"],
                "subject_name": f"{label}の授業",
                "weekday": 0,
                "start_time": "09:00",
                "end_time": "10:00",
            },
        )
    )
    part_time = created(
        client.post(
            "/api/events",
            json={
                "category": "part_time",
                "date": "2099-04-08",
                "start_time": "18:00",
                "end_time": "21:00",
                "title": f"{label}の仕事",
                "employer": f"{label}の派遣会社",
            },
        )
    )
    single_class = created(
        client.post(
            "/api/events",
            json={
                "category": "class",
                "subject_id": subject["id"],
                "date": "2099-04-09",
                "start_time": "13:00",
                "end_time": "14:00",
            },
        )
    )
    assignment = created(
        client.post(
            "/api/tasks",
            json={
                "category": "assignment",
                "subject_id": subject["id"],
                "title": f"{label}の課題",
                "due_datetime": "2099-04-20T23:59",
            },
        )
    )
    other_task = created(
        client.post(
            "/api/tasks",
            json={
                "category": "other",
                "title": f"{label}のタスク",
                "due_datetime": "2099-04-21T23:59",
            },
        )
    )
    return SimpleNamespace(
        semester=semester["id"],
        closure=closure["id"],
        subject=subject["id"],
        event=part_time["id"],
        class_event=single_class["id"],
        task=assignment["id"],
        other_task=other_task["id"],
    )


def snapshot(app, user_id: int) -> dict:
    """その利用者の、5つの表のすべての行の、すべての列の値。"""
    result = {}
    with app.app_context():
        for model in DATA_MODELS:
            columns = [column.name for column in model.__table__.columns]
            rows = db.session.scalars(
                db.select(model)
                .where(model.user_id == user_id)
                .order_by(model.id)
            ).all()
            result[model.__tablename__] = [
                tuple(getattr(row, column) for column in columns)
                for row in rows
            ]
    return result


@pytest.fixture
def world(app, client):
    """利用者A（client）と、利用者B（client_b）のデータ。

    テストのあとで、Aのデータが変わっていないことを確かめる。
    """
    a = build_data(client, "A")
    b_user_id = create_user(app, OTHER_USERNAME)
    client_b = logged_in_client(app, b_user_id)
    b = build_data(client_b, "B")
    before = snapshot(app, TEST_USER_ID)
    yield SimpleNamespace(a=a, b=b, client_b=client_b, b_user_id=b_user_id)
    assert snapshot(app, TEST_USER_ID) == before


def ids_in(response) -> set[int]:
    assert response.status_code == 200
    return {item["id"] for item in response.get_json()}


def assert_not_found(response, message: str) -> None:
    assert response.status_code == 404
    assert response.get_json() == {
        "error": {"code": "not_found", "message": message}
    }


def assert_field_error(response, field: str, message: str) -> None:
    assert response.status_code == 400
    assert response.get_json()["error"]["fields"][field] == message


# --- 各APIで、BがAのデータを狙う ---


def list_semesters(w):
    assert ids_in(w.client_b.get("/api/semesters")) == {w.b.semester}


def create_semester(w):
    # 他人の学期と同じ名前でも作れる（他人の学期の名前は、関係しない）
    payload = {**SEMESTER, "name": "2099年度 後期",
               "start_date": "2099-09-21", "end_date": "2099-12-27"}
    assert w.client_b.post("/api/semesters", json=payload).status_code == 201
    # 持ち主を、本文で指定できない
    response = w.client_b.post(
        "/api/semesters", json={**payload, "name": "2098年度 後期",
                                "user_id": TEST_USER_ID}
    )
    assert_field_error(response, "user_id", "この項目は指定できません")


def get_semester(w):
    assert_not_found(
        w.client_b.get(f"/api/semesters/{w.a.semester}"),
        "学期が見つかりません",
    )


def update_semester(w):
    assert_not_found(
        w.client_b.patch(
            f"/api/semesters/{w.a.semester}",
            json={"end_date": "2099-04-10"},
        ),
        "学期が見つかりません",
    )
    # 自分の学期の名前は、他人の学期と同じ名前にできる（期間の変更で、
    # Aの予定・休講日は変わらない）
    response = w.client_b.patch(
        f"/api/semesters/{w.b.semester}",
        json={"start_date": "2099-04-01", "end_date": "2099-04-12"},
    )
    assert response.status_code == 200


def delete_semester(w):
    assert_not_found(
        w.client_b.delete(f"/api/semesters/{w.a.semester}"),
        "学期が見つかりません",
    )


def list_subjects(w):
    assert ids_in(w.client_b.get("/api/subjects")) == {w.b.subject}
    assert ids_in(
        w.client_b.get(f"/api/subjects?semester_id={w.a.semester}")
    ) == set()


def create_subject(w):
    response = w.client_b.post(
        "/api/subjects",
        json={
            "semester_id": w.a.semester,
            "subject_name": "Bの授業2",
            "weekday": 1,
            "start_time": "09:00",
            "end_time": "10:00",
        },
    )
    assert_field_error(response, "semester_id", "指定された学期が存在しません")


def get_subject(w):
    assert_not_found(
        w.client_b.get(f"/api/subjects/{w.a.subject}"), "授業が見つかりません"
    )


def update_subject(w):
    assert_not_found(
        w.client_b.patch(
            f"/api/subjects/{w.a.subject}", json={"subject_name": "乗っ取り"}
        ),
        "授業が見つかりません",
    )


def delete_subject(w):
    assert_not_found(
        w.client_b.delete(f"/api/subjects/{w.a.subject}"),
        "授業が見つかりません",
    )
    # 自分の授業を消しても、Aの予定・課題は消えない
    assert w.client_b.delete(f"/api/subjects/{w.b.subject}").status_code == 204


def list_closures(w):
    assert ids_in(w.client_b.get("/api/closures")) == {w.b.closure}
    assert ids_in(
        w.client_b.get(f"/api/closures?semester_id={w.a.semester}")
    ) == set()


def create_closure(w):
    response = w.client_b.post(
        "/api/closures",
        json={"semester_id": w.a.semester, "date": "2099-04-20"},
    )
    assert_field_error(response, "semester_id", "指定された学期が存在しません")
    # 自分の学期に、Aの授業と同じ曜日の休講日を足しても、Aの予定は消えない
    response = w.client_b.post(
        "/api/closures",
        json={"semester_id": w.b.semester, "date": "2099-04-20"},
    )
    assert response.status_code == 201


def delete_closure(w):
    assert_not_found(
        w.client_b.delete(f"/api/closures/{w.a.closure}"),
        "休講日が見つかりません",
    )
    # 自分の休講日を消しても、Aの授業の予定は作られない
    assert w.client_b.delete(f"/api/closures/{w.b.closure}").status_code == 204


def list_events(w):
    events = w.client_b.get(f"/api/events?{EVENT_RANGE}").get_json()
    titles = {event["title"] for event in events}
    assert titles == {"Bの授業", "Bの仕事"}


def list_employers(w):
    response = w.client_b.get("/api/events/employers")
    assert response.get_json() == ["Bの派遣会社"]


def create_event(w):
    response = w.client_b.post(
        "/api/events",
        json={
            "category": "class",
            "subject_id": w.a.subject,
            "date": "2099-04-10",
            "start_time": "09:00",
            "end_time": "10:00",
        },
    )
    assert_field_error(response, "subject_id", "指定された授業が存在しません")


def get_event(w):
    for event_id in (w.a.event, w.a.class_event):
        assert_not_found(
            w.client_b.get(f"/api/events/{event_id}"), "予定が見つかりません"
        )


def update_event(w):
    assert_not_found(
        w.client_b.patch(
            f"/api/events/{w.a.event}", json={"title": "乗っ取り"}
        ),
        "予定が見つかりません",
    )


def delete_event(w):
    assert_not_found(
        w.client_b.delete(f"/api/events/{w.a.event}"), "予定が見つかりません"
    )


def list_tasks(w):
    assert ids_in(w.client_b.get("/api/tasks")) == {
        w.b.task, w.b.other_task
    }
    assert ids_in(w.client_b.get("/api/tasks?is_completed=false")) == {
        w.b.task, w.b.other_task
    }


def create_task(w):
    response = w.client_b.post(
        "/api/tasks",
        json={
            "category": "assignment",
            "subject_id": w.a.subject,
            "title": "Aの科目名を読む",
            "due_datetime": "2099-04-20T23:59",
        },
    )
    assert_field_error(response, "subject_id", "指定された授業が存在しません")


def get_task(w):
    assert_not_found(
        w.client_b.get(f"/api/tasks/{w.a.task}"),
        "課題・タスクが見つかりません",
    )


def update_task(w):
    assert_not_found(
        w.client_b.patch(
            f"/api/tasks/{w.a.task}", json={"is_completed": True}
        ),
        "課題・タスクが見つかりません",
    )
    # 自分の課題の対象授業を、Aの授業にできない（Aの科目名を読ませない）
    response = w.client_b.patch(
        f"/api/tasks/{w.b.task}", json={"subject_id": w.a.subject}
    )
    assert_field_error(response, "subject_id", "指定された授業が存在しません")


def delete_task(w):
    assert_not_found(
        w.client_b.delete(f"/api/tasks/{w.a.task}"),
        "課題・タスクが見つかりません",
    )


# APIのURL（変数の部分は <id>）×メソッド → 確かめる関数
CASES = {
    ("/api/semesters", "GET"): list_semesters,
    ("/api/semesters", "POST"): create_semester,
    ("/api/semesters/<id>", "GET"): get_semester,
    ("/api/semesters/<id>", "PATCH"): update_semester,
    ("/api/semesters/<id>", "DELETE"): delete_semester,
    ("/api/subjects", "GET"): list_subjects,
    ("/api/subjects", "POST"): create_subject,
    ("/api/subjects/<id>", "GET"): get_subject,
    ("/api/subjects/<id>", "PATCH"): update_subject,
    ("/api/subjects/<id>", "DELETE"): delete_subject,
    ("/api/closures", "GET"): list_closures,
    ("/api/closures", "POST"): create_closure,
    ("/api/closures/<id>", "DELETE"): delete_closure,
    ("/api/events", "GET"): list_events,
    ("/api/events", "POST"): create_event,
    ("/api/events/employers", "GET"): list_employers,
    ("/api/events/<id>", "GET"): get_event,
    ("/api/events/<id>", "PATCH"): update_event,
    ("/api/events/<id>", "DELETE"): delete_event,
    ("/api/tasks", "GET"): list_tasks,
    ("/api/tasks", "POST"): create_task,
    ("/api/tasks/<id>", "GET"): get_task,
    ("/api/tasks/<id>", "PATCH"): update_task,
    ("/api/tasks/<id>", "DELETE"): delete_task,
}


def api_endpoints(app, include_automatic=False) -> set[tuple[str, str]]:
    """アプリの、APIのURL（変数の部分は <id>）×メソッドの一覧。"""
    automatic = set() if include_automatic else {"HEAD", "OPTIONS"}
    endpoints = set()
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith("/api"):
            continue
        path = re.sub(r"<[^>]+>", "<id>", rule.rule)
        for method in rule.methods - automatic:
            endpoints.add((path, method))
    return endpoints


def test_every_api_endpoint_has_an_authorization_case(app):
    # 新しいAPIを足したら、CASES にも足す（足し忘れると、ここで失敗する）
    assert api_endpoints(app) == set(CASES)


@pytest.mark.parametrize(
    "endpoint", sorted(CASES), ids=lambda endpoint: " ".join(endpoint)
)
def test_other_user_cannot_touch_data(world, endpoint):
    CASES[endpoint](world)


def test_logged_out_user_gets_401_everywhere(app, anonymous_client):
    for path, method in sorted(api_endpoints(app, include_automatic=True)):
        url = path.replace("<id>", "1")
        response = anonymous_client.open(url, method=method, json={})
        assert response.status_code == 401, (method, path)
        if method != "HEAD":
            assert response.get_json()["error"]["code"] == "unauthorized"


def test_child_rows_have_same_owner_as_parent(app, world):
    with app.app_context():
        pairs = [
            (Subject, Semester, Subject.semester_id),
            (Closure, Semester, Closure.semester_id),
            (Event, Subject, Event.subject_id),
            (Task, Subject, Task.subject_id),
        ]
        for child, parent, foreign_key in pairs:
            mismatched = db.session.scalar(
                db.select(db.func.count())
                .select_from(child)
                .join(parent, foreign_key == parent.id)
                .where(child.user_id != parent.user_id)
            )
            assert mismatched == 0, child.__tablename__


def test_bulk_changes_never_touch_other_users_rows(app, world):
    # 持ち主のずれた行（Aの予定・課題なのに、Bの授業を指す。あっては
    # ならないが、もしあっても）に、Bの一括の処理が届かない
    with app.app_context():
        subject_b = db.session.get(Subject, world.b.subject)
        stray_event = Event(
            user_id=TEST_USER_ID,
            subject_id=subject_b.id,
            category="class",
            # Bの授業の曜日（月曜日）の日。Bの休講日・作り直し・期間の
            # 変更・授業の削除の、どれの対象にもなる日
            date=subject_b.semester.start_date,
            start_time=subject_b.start_time,
            end_time=subject_b.end_time,
            title="Aの迷子の予定",
            is_generated=True,
        )
        stray_task = Task(
            user_id=TEST_USER_ID,
            subject_id=subject_b.id,
            category="assignment",
            title="Aの迷子の課題",
            due_datetime=db.session.get(Task, world.a.task).due_datetime,
            is_completed=False,
        )
        db.session.add_all([stray_event, stray_task])
        db.session.commit()
        stray_ids = (stray_event.id, stray_task.id)

    client_b = world.client_b
    client_b.post(
        "/api/closures",
        json={"semester_id": world.b.semester, "date": "2099-04-06"},
    )
    client_b.patch(
        f"/api/subjects/{world.b.subject}", json={"weekday": 2}
    )
    client_b.patch(
        f"/api/semesters/{world.b.semester}",
        json={"start_date": "2099-05-01"},
    )
    client_b.delete(f"/api/subjects/{world.b.subject}")

    with app.app_context():
        assert db.session.get(Event, stray_ids[0]) is not None
        assert db.session.get(Task, stray_ids[1]) is not None
        # world のあとの確かめ（Aのデータが変わらない）のため、迷子の行を
        # 消しておく
        db.session.delete(db.session.get(Event, stray_ids[0]))
        db.session.delete(db.session.get(Task, stray_ids[1]))
        db.session.commit()


def test_routes_never_get_data_by_id_without_owner():
    # routeでは、IDでデータを取るときに、持ち主も確かめる（app/ownership.py
    # の get_owned）。db.session.get は、持ち主を確かめないため、使わない
    for path in sorted(ROUTES_DIRECTORY.glob("*.py")):
        assert "db.session.get(" not in path.read_text(), path.name
