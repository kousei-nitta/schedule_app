"""攻撃のテスト（認可・DBに残る値・デモのDB・パスワードの決まり）。

Task 025 の実装に、攻撃のテストの担当（エージェント）が、攻撃者として
試したことのうち、残す価値のあるもの（tests/test_authorization.py・
tests/test_passwords.py に、まだないもの）。
- 受け入れた弱さ（今は直さないもの）を再現するテストは、
  xfail(strict=True) を付ける（今は「予想どおり失敗」）。直したら、印を
  外す（外さないと、XPASS で失敗する）
- 見つかって直した弱さのテストと、守られていることを確かめるテスト
"""
from datetime import date
from pathlib import Path

import pytest

from app import create_app
from app.demo_data import DEMO_USERNAME, create_demo_database
from app.extensions import db
from app.models import Semester, Subject, Task, User, UserSession
from app.passwords import password_rule_errors
from tests.auth_support import (
    OTHER_USERNAME,
    TEST_PASSWORD,
    TEST_USER_ID,
    create_user,
    logged_in_client,
)

SEMESTER = {
    "name": "2099年度 前期",
    "start_date": "2099-04-06",
    "end_date": "2099-07-20",
}
OTHER_TASK = {
    "category": "other",
    "title": "架空のタスク",
    "due_datetime": "2099-04-21T23:59",
}


@pytest.fixture
def client_b(app):
    """もう1人の利用者（B）でログインした client。"""
    return logged_in_client(app, create_user(app, OTHER_USERNAME))


def create_semester_and_subject(client) -> tuple[int, int]:
    semester = client.post("/api/semesters", json=SEMESTER).get_json()
    subject = client.post(
        "/api/subjects",
        json={
            "semester_id": semester["id"],
            "subject_name": "架空の授業",
            "weekday": 0,
            "start_time": "09:00",
            "end_time": "10:00",
        },
    ).get_json()
    return semester["id"], subject["id"]


def owned_rows(app, user_id: int) -> dict:
    with app.app_context():
        return {
            model.__tablename__: db.session.scalar(
                db.select(db.func.count())
                .select_from(model)
                .where(model.user_id == user_id)
            )
            for model in (Semester, Subject, Task)
        }


# --- 受け入れた弱さ：IDの番号から、他人の操作が分かる ---


@pytest.mark.xfail(
    strict=True,
    reason=(
        "受け入れた弱さ：IDが、すべての利用者で1つの通し番号。Bは、"
        "自分のデータを2回作ると、その間にAが作った件数が分かる（中身は"
        "分からない）。利用者が増える段階4で決める"
        "（docs/open_questions.md の「将来の検討事項」）"
    ),
)
def test_ids_do_not_reveal_other_users_activity(client, client_b):
    first = client_b.post("/api/tasks", json=OTHER_TASK).get_json()["id"]
    second = client_b.post("/api/tasks", json=OTHER_TASK).get_json()["id"]
    gap_without_a = second - first

    for _ in range(3):
        client.post("/api/tasks", json=OTHER_TASK)
    third = client_b.post("/api/tasks", json=OTHER_TASK).get_json()["id"]
    gap_with_a = third - second

    # Aが何をしても、Bに見えるIDの並びは変わらない
    assert gap_with_a == gap_without_a


# --- 守り：IDの書き方を変えても、他人のデータに届かない ---


def id_spellings(object_id: int) -> list[str]:
    """同じ数を表す、ほかの書き方（URLに入れる）。"""
    text = str(object_id)
    return [
        "0" + text,
        # 全角の数字・アラビア・インド数字（Werkzeug の int は、
        # Unicode の数字も受け付ける）
        text.translate({code: code + 0xFEE0 for code in range(0x30, 0x3A)}),
        text.translate({code: code + 0x0630 for code in range(0x30, 0x3A)}),
    ]


@pytest.mark.parametrize("resource", ["semesters", "subjects"])
@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
def test_id_spellings_never_reach_other_users_data(
    app, client, client_b, resource, method
):
    semester_id, subject_id = create_semester_and_subject(client)
    object_id = semester_id if resource == "semesters" else subject_id
    before = owned_rows(app, TEST_USER_ID)

    for spelling in id_spellings(object_id):
        response = client_b.open(
            f"/api/{resource}/{spelling}",
            method=method,
            json={"subject_name": "乗っ取り"} if method == "PATCH" else None,
        )
        assert response.status_code == 404, spelling

    assert owned_rows(app, TEST_USER_ID) == before


@pytest.mark.parametrize(
    "make_value",
    [
        str,
        float,
        lambda value: [value],
        lambda value: {"id": value},
        lambda value: True,
        lambda value: -value,
        lambda value: value + 2**63,
    ],
    ids=["文字列", "小数", "配列", "オブジェクト", "真偽値", "負", "大きな数"],
)
def test_odd_reference_types_never_reach_other_users_subject(
    app, client, client_b, make_value
):
    # 本文で参照するIDの型を変えても、Aの授業を参照できない
    # （型の誤りか「存在しません」になり、課題は作られない）
    _, subject_id = create_semester_and_subject(client)

    response = client_b.post(
        "/api/tasks",
        json={
            "category": "assignment",
            "subject_id": make_value(subject_id),
            "title": "Aの科目名を読む",
            "due_datetime": "2099-04-20T23:59",
        },
    )

    assert response.status_code == 400
    assert "subject_id" in response.get_json()["error"]["fields"]
    assert "架空の授業" not in response.get_data(as_text=True)
    assert owned_rows(app, TEST_USER_ID)["tasks"] == 0


# --- 直した弱さ：消したデータが、DBのファイルに残っていた ---
#
# SQLite の secure_delete がオフで、消した課題のメモが、DBのファイルの
# 空き領域に、そのまま残っていた（ファイルやバックアップが漏れると、
# 消したはずの個人の情報が読める）。今は、つなぐたびにオンにする
# （app/extensions.py）


def test_deleted_notes_do_not_remain_in_database_file(app, client):
    secret = "deleted-note-that-must-not-remain-0123456789"
    task = client.post(
        "/api/tasks", json={**OTHER_TASK, "notes": secret}
    ).get_json()
    assert client.delete(f"/api/tasks/{task['id']}").status_code == 204

    with app.app_context():
        database_path = Path(db.engine.url.database)
        db.session.remove()
        db.engine.dispose()

    assert secret.encode() not in database_path.read_bytes()


# --- 直した弱さ：デモのDBに、だれも使わないログインが残っていた ---
#
# demo_client が作った、ログイン中の端末の行が残り、利用者のメニューの
# 「ログイン中の端末」が1台多く見えていた（知らないログインに気づく
# ための数が当てにならない）


@pytest.fixture
def demo_app(tmp_path: Path):
    """DBを一時ディレクトリの demo.db（まだないファイル）にしたアプリ。"""
    test_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'demo.db'}",
        }
    )
    yield test_app
    with test_app.app_context():
        db.session.remove()
        db.engine.dispose()


def test_demo_database_has_no_leftover_login(demo_app):
    create_demo_database(demo_app, date(2026, 10, 21), password=TEST_PASSWORD)

    with demo_app.app_context():
        demo_id = db.session.scalar(
            db.select(User.id).where(User.username == DEMO_USERNAME)
        )
        count = db.session.scalar(
            db.select(db.func.count())
            .select_from(UserSession)
            .where(UserSession.user_id == demo_id)
        )

    assert count == 0


# --- 直した弱さ：漏えいの確認を省くと、弱いパスワードが通っていた ---
#
# 手元の決まりが「長さ・IDを含む・1文字の繰り返しだけ・制御文字」だけで、
# --skip-breach-check のときは、連番や、ほぼ同じ文字の並びも通っていた
# （NIST SP 800-63B-4 は、繰り返し・連番を断る一覧を求める）


@pytest.mark.parametrize(
    "password",
    [
        "aaaaaaaaaaaaaab",
        "abababababababab",
        "123456789012345",
        "abcdefghijklmnop",
        "              x",
    ],
)
def test_weak_patterns_are_refused_without_breach_check(password):
    assert password_rule_errors(password, "owner") != []
