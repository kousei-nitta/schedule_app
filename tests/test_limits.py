"""公開に合わせて足した、入力の上限（Task 026。ADR 0005）。

- 授業・予定・課題のメモ（notes）：前後の空白を除いて2,000字まで
- 学期の期間：開始日から終了日まで（両端を含む）366日まで
仕様は docs/architecture/api_endpoints.md。本文の大きさの上限（64KiB）は、
tests/test_security.py。
"""
import pytest

NOTES_LENGTH_ERROR = "詳細・メモは2000文字以内にしてください"
PERIOD_ERROR = "学期の期間は366日以内にしてください"


def create_semester(client, start="2026-04-01", end="2026-07-31"):
    response = client.post(
        "/api/semesters",
        json={"name": "2026年度 前期", "start_date": start, "end_date": end},
    )
    assert response.status_code == 201, response.json
    return response.json["id"]


def create_subject(client, semester_id, **extra):
    return client.post(
        "/api/subjects",
        json={
            "semester_id": semester_id,
            "subject_name": "プログラミング基礎",
            "weekday": 0,
            "start_time": "09:00",
            "end_time": "10:00",
            **extra,
        },
    )


def create_event(client, **extra):
    return client.post(
        "/api/events",
        json={
            "category": "other",
            "date": "2026-05-01",
            "start_time": "10:00",
            "end_time": "11:00",
            "title": "図書館",
            **extra,
        },
    )


def create_task(client, **extra):
    return client.post(
        "/api/tasks",
        json={
            "category": "other",
            "title": "本の返却",
            "due_datetime": "2026-05-01T12:00",
            **extra,
        },
    )


def create_with_notes(client, kind, notes):
    if kind == "subjects":
        return create_subject(client, create_semester(client), notes=notes)
    if kind == "events":
        return create_event(client, notes=notes)
    return create_task(client, notes=notes)


KINDS = ["subjects", "events", "tasks"]
# 作ったものが入っていないことを確かめる一覧
LIST_URLS = {
    "subjects": "/api/subjects",
    "events": "/api/events?start_date=2026-01-01&end_date=2026-12-31",
    "tasks": "/api/tasks",
}


# --- メモ ---


@pytest.mark.parametrize("kind", KINDS)
def test_notes_of_2000_characters_are_accepted(client, kind):
    # 前後の空白は、取り除いてから数える
    response = create_with_notes(client, kind, "  " + "メ" * 2000 + "\n")

    assert response.status_code == 201, response.json
    assert response.json["notes"] == "メ" * 2000


@pytest.mark.parametrize("kind", KINDS)
def test_notes_over_2000_characters_are_refused(client, kind):
    response = create_with_notes(client, kind, "メ" * 2001)

    assert response.status_code == 400
    assert response.json["error"]["fields"] == {"notes": NOTES_LENGTH_ERROR}
    assert client.get(LIST_URLS[kind]).json == []


@pytest.mark.parametrize("kind", KINDS)
def test_notes_over_2000_characters_are_refused_when_updating(client, kind):
    created = create_with_notes(client, kind, "短いメモ")
    item_id = created.json["id"]

    response = client.patch(
        f"/api/{kind}/{item_id}", json={"notes": "メ" * 2001}
    )

    assert response.status_code == 400
    assert response.json["error"]["fields"] == {"notes": NOTES_LENGTH_ERROR}
    assert client.get(f"/api/{kind}/{item_id}").json["notes"] == "短いメモ"


# --- 学期の期間 ---


@pytest.mark.parametrize(
    ("start", "end"),
    [
        # 366日（両端を含む）。うるう年の1年
        ("2028-01-01", "2028-12-31"),
        ("2026-04-01", "2027-04-01"),
    ],
)
def test_semester_of_366_days_is_accepted(client, start, end):
    response = client.post(
        "/api/semesters",
        json={"name": "2026年度 前期", "start_date": start, "end_date": end},
    )

    assert response.status_code == 201, response.json


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("2026-04-01", "2027-04-02"),
        ("0001-01-01", "9999-12-31"),
    ],
)
def test_semester_over_366_days_is_refused(client, start, end):
    response = client.post(
        "/api/semesters",
        json={"name": "2026年度 前期", "start_date": start, "end_date": end},
    )

    assert response.status_code == 400
    assert response.json["error"]["fields"] == {"end_date": PERIOD_ERROR}
    assert client.get("/api/semesters").json == []


def test_order_error_comes_before_period_error(client):
    response = client.post(
        "/api/semesters",
        json={
            "name": "2026年度 前期",
            "start_date": "2026-04-01",
            "end_date": "2026-04-01",
        },
    )

    assert response.json["error"]["fields"] == {
        "end_date": "終了日は開始日より後にしてください"
    }


@pytest.mark.parametrize(
    "change",
    [{"end_date": "2027-04-02"}, {"start_date": "2025-03-31"}],
)
def test_semester_update_over_366_days_is_refused(client, change):
    semester_id = create_semester(client, "2026-04-01", "2026-07-31")

    response = client.patch(f"/api/semesters/{semester_id}", json=change)

    assert response.status_code == 400
    assert response.json["error"]["fields"] == {"end_date": PERIOD_ERROR}
    semester = client.get(f"/api/semesters/{semester_id}").json
    assert (semester["start_date"], semester["end_date"]) == (
        "2026-04-01",
        "2026-07-31",
    )
