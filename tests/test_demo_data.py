"""デモ用の架空のデータ（app/demo_data.py、コマンド create-demo-db）の確認。

デモのDBは、pytestの一時ディレクトリにだけ作る。実データのDBを断る確認は、
instance/ を一時ディレクトリにした空のFlaskアプリで行う。
"""
import hashlib
import os
from datetime import date
from pathlib import Path

import pytest
from flask import Flask

from app import create_app
from app.config import DEFAULT_DATABASE_URI
from app.demo_data import (
    DemoDataError,
    create_demo_database,
    semester_name,
    semester_period,
)
from app.extensions import db
from app.models import Event, Task


# 水曜日。学期は 2026-09-14（月）〜2026-12-27（日）になる
TODAY = date(2026, 10, 21)


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


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 4, 1), "2026年度 前期"),
        (date(2026, 9, 30), "2026年度 前期"),
        (date(2026, 10, 1), "2026年度 後期"),
        (date(2027, 1, 10), "2026年度 後期"),
        (date(2027, 3, 31), "2026年度 後期"),
    ],
)
def test_semester_name(today, expected):
    assert semester_name(today) == expected


def test_semester_period_contains_today():
    start_date, end_date = semester_period(TODAY)

    assert start_date == date(2026, 9, 14)
    assert end_date == date(2026, 12, 27)
    assert start_date.weekday() == 0
    assert end_date.weekday() == 6


def test_create_demo_database(demo_app, tmp_path):
    counts = create_demo_database(demo_app, TODAY)

    assert counts == {
        "学期": 1,
        "授業": 6,
        "休講日": 2,
        "予定": 94,
        "課題・タスク": 6,
    }
    assert (tmp_path / "demo.db").exists()

    client = demo_app.test_client()
    semesters = client.get("/api/semesters").get_json()
    assert semesters == [
        {
            "id": semesters[0]["id"],
            "name": "2026年度 後期",
            "start_date": "2026-09-14",
            "end_date": "2026-12-27",
        }
    ]
    closures = client.get("/api/closures").get_json()
    closure_dates = [closure["date"] for closure in closures]
    assert closure_dates == ["2026-09-28", "2026-10-28"]


def test_demo_events(demo_app):
    create_demo_database(demo_app, TODAY)

    with demo_app.app_context():
        events = db.session.scalars(db.select(Event)).all()
        generated = [event for event in events if event.is_generated]
        single = [event for event in events if not event.is_generated]

        # 6つの授業×15週。休講日の2日（月曜日と水曜日）の授業の予定はない
        assert len(generated) == 6 * 15 - 2
        generated_dates = {event.date.isoformat() for event in generated}
        assert "2026-09-28" not in generated_dates
        assert "2026-10-28" not in generated_dates

        assert sorted(event.category for event in single) == [
            "class",
            "other",
            "other",
            "part_time",
            "part_time",
            "part_time",
        ]


def test_demo_tasks(demo_app):
    create_demo_database(demo_app, TODAY)

    with demo_app.app_context():
        tasks = db.session.scalars(db.select(Task)).all()
        completed = [task for task in tasks if task.is_completed]
        overdue = [
            task
            for task in tasks
            if not task.is_completed and task.due_datetime.date() < TODAY
        ]
        others = [task for task in tasks if task.category == "other"]

        assert len(tasks) == 6
        assert [task.title for task in completed] == ["小レポート 第1回"]
        assert [task.title for task in overdue] == ["演習問題 第5回"]
        assert [task.subject_id for task in others] == [None]


def test_create_demo_db_command(demo_app, tmp_path):
    result = demo_app.test_cli_runner().invoke(args=["create-demo-db"])

    assert result.exit_code == 0, result.output
    database_path = tmp_path / "demo.db"
    assert f"デモデータのDBを作りました：{database_path}" in result.output
    assert "授業 6件" in result.output


def test_command_refuses_existing_file(demo_app, tmp_path):
    database_path = tmp_path / "demo.db"
    database_path.write_bytes(b"existing")

    result = demo_app.test_cli_runner().invoke(args=["create-demo-db"])

    assert result.exit_code == 1
    assert "すでにあります" in result.output
    assert database_path.read_bytes() == b"existing"


def test_command_replaces_existing_file(demo_app, tmp_path):
    database_path = tmp_path / "demo.db"
    database_path.write_bytes(b"not a database")

    result = demo_app.test_cli_runner().invoke(
        args=["create-demo-db", "--replace"]
    )

    assert result.exit_code == 0, result.output
    response = demo_app.test_client().get("/api/subjects")
    assert len(response.get_json()) == 6


def make_bare_app(instance_path: Path, uri: str) -> Flask:
    """instance/ を一時ディレクトリにした、空のFlaskアプリを作る。"""
    bare_app = Flask(__name__, instance_path=str(instance_path))
    bare_app.config["SQLALCHEMY_DATABASE_URI"] = uri
    return bare_app


def test_refuses_missing_real_database(tmp_path):
    bare_app = make_bare_app(tmp_path, DEFAULT_DATABASE_URI)

    with pytest.raises(DemoDataError, match="実データのDB"):
        create_demo_database(bare_app, TODAY, replace=True)

    assert list(tmp_path.iterdir()) == []


def test_refuses_existing_real_database_even_with_replace(tmp_path):
    real_path = tmp_path / "app.db"
    real_path.write_bytes(b"real data")
    hash_before = file_hash(real_path)
    # 別の書き方で、実データのDBを指しても断る
    other_spelling = tmp_path / "sub" / ".." / "app.db"
    bare_app = make_bare_app(tmp_path, f"sqlite:///{other_spelling}")

    with pytest.raises(DemoDataError, match="実データのDB"):
        create_demo_database(bare_app, TODAY, replace=True)

    assert file_hash(real_path) == hash_before
    assert sorted(path.name for path in tmp_path.iterdir()) == ["app.db"]


def test_refuses_real_database_with_same_file_other_name(tmp_path):
    # 実データのDBと同じファイル（ハードリンク）を指しても断る。macOSで
    # 大文字・小文字だけが違う名前（APP.db）を指定した場合と同じ形
    real_path = tmp_path / "app.db"
    real_path.write_bytes(b"real data")
    hash_before = file_hash(real_path)
    alias_path = tmp_path / "alias.db"
    os.link(real_path, alias_path)
    bare_app = make_bare_app(tmp_path, f"sqlite:///{alias_path}")

    with pytest.raises(DemoDataError, match="実データのDB"):
        create_demo_database(bare_app, TODAY, replace=True)

    assert alias_path.exists()
    assert file_hash(real_path) == hash_before


def test_refuses_non_file_database(tmp_path):
    bare_app = make_bare_app(tmp_path, "sqlite://")

    with pytest.raises(DemoDataError, match="SQLiteのファイルのDBだけ"):
        create_demo_database(bare_app, TODAY)
