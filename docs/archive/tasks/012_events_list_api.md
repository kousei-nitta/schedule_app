# タスク012: 予定の一覧API

| 項目 | 内容 |
|---|---|
| Task ID | 012 |
| Task名 | 予定の一覧API（`GET /api/events`・`GET /api/events/<id>`） |
| ブランチ | `feature/012-events-list-api`（Komaが作成・切替済みの状態で渡される） |

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに停止して報告する。

**このタスクには、承認ゲートはない（DBの構造を変えないため、migrationを作らない）。** 1〜3を順に進め、「Copilot確認手順」を実施したら、結果を報告して応答を終える。途中で止まるのは、「注意」の停止の条件に当たったときだけ。**止まるときは、報告を書いて応答を終える。質問の機能（選択肢を出して回答を待つ機能）は使わない**（`.github/copilot-instructions.md` の「止まる場面の応答」）。

## 目的
カレンダーに表示する予定（Event）を読み取るAPIを作る。期間（`start_date`・`end_date`。どちらも必須で、両端を含む）を指定した一覧（`GET /api/events`）と、1件取得（`GET /api/events/<id>`）。カレンダー表示（Task 013）の前提になる。予定の登録・編集・削除は、まだ提供しない（405）。設計資料（`docs/architecture.md` の「予定API（`/api/events`）」）の仕様を、そのまま実装する。

## 前提（Task 011完了時点の状態）

| 区分 | 内容 |
|---|---|
| すでにある | 学期API・授業API（登録で、学期の期間の授業の予定を作る）・休講日API（追加・削除で、予定を同期する）、学期・授業・休講日の画面、pytest（**431件**。`main` の `250be78` で確認） |
| まだない | `app/routes/events.py`、`tests/test_events_api.py`。予定（Event）を読み取るAPI |
| DBの構造 | 変えない（初期migration `0280f6cf8d09` と、休講日の `42bd53808fa1`）。`events` テーブルには、必要な列（「データ設計」の Event）が、すべてある。**migrationは不要** |
| 開発用DB | `instance/app.db` は、Komaの実際の開発用DB（すべてのテーブルが0件。2026-10-12にKomaが確認）。**Copilotは、書き込まない。サーバーを起動しない（`python run.py` を実行しない）**。読むのは、「Copilot確認手順」のハッシュと件数だけ。**`sqlite3` は、必ず `-readonly` を付けて実行する**（011-L1） |
| 設計資料 | このタスクの前に、更新した設計資料が `main` に反映されている。`docs/architecture.md` に「予定API（`/api/events`）」の節があり、`read_date_query` の置き場所が書かれている |
| 画面 | 変えない。JavaScriptの自動テストはなく、ブラウザでの確認もない（画面を変えないため）。APIの動作は、pytestと、Komaの確認用のサーバーでの `curl` で確かめる |

## Source of Truth
- `docs/architecture.md`：「API共通ルール」（「URLとメソッド」の必須のクエリ、「リクエストとレスポンス（JSON）」、「日付・時刻・日時」、「エラー」、「404の使い分け」）、「予定API（`/api/events`）」、「データ設計」の Event、「自動テスト（pytest）」
- `docs/tasks/011_class_event_generation.md`：授業の登録で作られる予定の値
- `.github/copilot-instructions.md`：進め方、「止まる場面の応答」、コーディング方針、「テスト」

## 実装対象ファイル

| 区分 | ファイル | 内容 |
|---|---|---|
| 新規 | `app/routes/events.py` | 予定の一覧・1件取得のroute、日付のクエリの読み取り（`read_date_query`）、予定をJSONにする変換（`event_to_dict`） |
| 変更 | `app/__init__.py` | `events_bp` の登録（末尾の4行の追加だけ） |
| 新規 | `tests/test_events_api.py` | 上のAPIのテスト（47件） |

上の3ファイル以外は、変更しない（`__pycache__/` などの、`.gitignore` の対象は除く）。**3ファイルとも、このTask MDに全文を書いている。全文のとおりに作る（コメント・空行・順序を含め、書き方を変えない）。** 変える必要があると判断した場合は、変えずに停止して報告する。

## 非対象（このタスクでは作らない・変更しない）
- モデル（`app/models/`）、`migrations/`（**新しいmigrationを作らない。`flask db` のコマンドを、一切実行しない**）、`requirements.txt`（**ライブラリを追加しない**）、`pytest.ini`、`run.py`
- `app/api_helpers.py`（`read_date_query` は、`routes/events.py` に置く。`api_helpers.py` へ移すかは、2つ目の利用者が出たときに決める）、`app/class_events.py`、`app/routes/` のほかのファイル
- `app/templates/`、`app/static/`（画面は変えない）
- `tests/` の既存のファイル（`conftest.py` を含む）
- `docs/`、`.github/`、`.gitignore`
- 予定の登録・編集・削除（`POST`・`PATCH`・`DELETE`。405のまま）、カレンダー表示（Task 013）、課題・タスクのAPI
- 開発用DB（`instance/app.db`）への書き込み、サーバーの起動（`python run.py` も、「Komaの確認」の確認用のサーバーも、起動しない）

## 1. `app/routes/events.py`（新規）
次の全文のとおりに作る。

要点：
- `GET /api/events`：`start_date`・`end_date` を `read_date_query` で読み取る（指定がない・複数回の指定・形式の誤りは、そのクエリのエラー）。両方に誤りがないときだけ、`end_date` が `start_date` より前かを確かめる。誤りがあれば、まとめて400（`validation_error`）。なければ、日付が期間内（両端を含む）の予定を、`date`・`start_time`・`id` の昇順で返す
- `read_date_query` は、`api_helpers.py` の `parse_date`（`YYYY-MM-DD` の厳密な形式と実在性の検査）を使う。空文字・前後の空白・全角の数字は、形式の誤り
- `GET /api/events/<id>`：IDの上限つきのURL（`MAX_ID`）。存在しなければ404（「予定が見つかりません」）
- DBへの書き込み（`add`・`delete`・`commit`）はない
- `POST`・`PATCH`・`DELETE` のrouteは作らない（Flaskが405を返し、共通のエラーハンドラーがJSONにする）

<!-- 全文: app/routes/events.py -->
```python
from datetime import date
from typing import Any

from flask import Blueprint, jsonify, request

from app.api_helpers import (
    MAX_ID,
    api_error_response,
    format_date,
    format_time,
    parse_date,
)
from app.extensions import db
from app.models.event import Event


events_bp = Blueprint(
    "events",
    __name__,
    url_prefix="/api/events",
)


def event_to_dict(event: Event) -> dict[str, Any]:
    """予定をAPIレスポンス用の辞書に変換する。"""
    return {
        "id": event.id,
        "subject_id": event.subject_id,
        "category": event.category,
        "date": format_date(event.date),
        "start_time": format_time(event.start_time),
        "end_time": format_time(event.end_time),
        "title": event.title,
        "room": event.room,
        "employer": event.employer,
        "notes": event.notes,
        "is_generated": event.is_generated,
    }


def read_date_query(
    name: str,
    required_message: str,
    multiple_message: str,
    format_message: str,
) -> tuple[date | None, str | None]:
    """一覧のクエリで指定された、必須の日付を読み取る。

    戻り値は、（日付、エラーメッセージ）の組。
    - 指定がない：(None, required_message)
    - 2回以上の指定：(None, multiple_message)
    - YYYY-MM-DDの実在する日付でない（空文字・前後の空白を含む）：
      (None, format_message)
    - それ以外：(日付, None)
    使うのが予定の一覧だけのため、このファイルに置く。2つ目の利用者が
    出たときに、api_helpers.py へ移すかを決める。
    """
    values = request.args.getlist(name)
    if not values:
        return None, required_message
    if len(values) > 1:
        return None, multiple_message

    parsed_value = parse_date(values[0])
    if parsed_value is None:
        return None, format_message
    return parsed_value, None


@events_bp.get("")
def get_events():
    fields: dict[str, str] = {}

    start_date, start_date_error = read_date_query(
        "start_date",
        "開始日は必須です",
        "開始日は1つだけ指定してください",
        "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください",
    )
    if start_date_error is not None:
        fields["start_date"] = start_date_error

    end_date, end_date_error = read_date_query(
        "end_date",
        "終了日は必須です",
        "終了日は1つだけ指定してください",
        "終了日は実在する日付を「YYYY-MM-DD」の形式で指定してください",
    )
    if end_date_error is not None:
        fields["end_date"] = end_date_error

    # 期間の前後の検査は、開始日と終了日の両方に誤りがないときだけ行う。
    if (
        start_date is not None
        and end_date is not None
        and end_date < start_date
    ):
        fields["end_date"] = "終了日は開始日以降の日付にしてください"

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    # 予定は、日付を1つだけ持つため、日付が期間内（両端を含む）の予定を返す。
    statement = (
        db.select(Event)
        .where(Event.date >= start_date, Event.date <= end_date)
        .order_by(
            Event.date.asc(),
            Event.start_time.asc(),
            Event.id.asc(),
        )
    )
    events = db.session.scalars(statement).all()
    return jsonify([event_to_dict(event) for event in events])


@events_bp.get(f"/<int(max={MAX_ID}):event_id>")
def get_event(event_id: int):
    event = db.session.get(Event, event_id)
    if event is None:
        return api_error_response("not_found", "予定が見つかりません")
    return jsonify(event_to_dict(event))
```

## 2. `app/__init__.py`（変更）
休講日の `closures_bp` の登録のあと、`return app` の前に、`events_bp` の登録の4行（空行を含む）を足す。ほかの行は変えない。差分：

```diff
     from app.routes.closures import closures_bp
 
     app.register_blueprint(closures_bp)
+
+    from app.routes.events import events_bp
+
+    app.register_blueprint(events_bp)
     return app
```

変更後の全文（「Copilot確認手順」の4で、この全文と比べる）：

<!-- 全文: app/__init__.py -->
```python
import os
from typing import Any

from flask import Flask

from app.api_helpers import register_api_error_handlers
from app.config import Config
from app.extensions import db, migrate


def create_app(test_config: dict[str, Any] | None = None):
    if (
        test_config is not None
        and "SQLALCHEMY_DATABASE_URI" not in test_config
    ):
        raise ValueError(
            "テスト設定にはSQLALCHEMY_DATABASE_URIが必要です"
        )

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config is None:
        os.makedirs(app.instance_path, exist_ok=True)
    else:
        app.config.update(test_config)

    db.init_app(app)

    # モデルをSQLAlchemyに登録するための読み込み。migrationがテーブルを
    # 見つけるために必要なので、名前は使わなくても削除しない。
    from app import models

    migrate.init_app(app, db, render_as_batch=True)

    from app.routes.main import main as main_blueprint

    app.register_blueprint(main_blueprint)

    register_api_error_handlers(app)

    from app.routes.semesters import semesters_bp

    app.register_blueprint(semesters_bp)

    from app.routes.subjects import subjects_bp

    app.register_blueprint(subjects_bp)

    from app.routes.closures import closures_bp

    app.register_blueprint(closures_bp)

    from app.routes.events import events_bp

    app.register_blueprint(events_bp)
    return app
```

## 3. `tests/test_events_api.py`（新規）
次の全文のとおりに作る。予定を登録するAPIはまだないため、テストの予定は、ORMで直接作る（`make_event`）。授業の登録で作られた予定が一覧に出ることは、授業のAPIで確かめる（`test_event_list_returns_events_generated_by_subject_registration`）。

<!-- 全文: tests/test_events_api.py -->
```python
from datetime import date, time

import pytest
from sqlalchemy import func, select

from app.api_helpers import MAX_ID
from app.extensions import db
from app.models.event import Event
from app.models.semester import Semester
from app.models.subject import Subject


START_FORMAT_MESSAGE = (
    "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
)
END_FORMAT_MESSAGE = (
    "終了日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
)
APRIL_QUERY = "start_date=2026-04-01&end_date=2026-04-30"


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


def make_subject(app, semester_id, subject_name="授業"):
    """予定を作らずに、授業の行だけを作る（ORMで直接作る）。"""
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


def make_event(
    app,
    event_date,
    start_time=time(9, 0),
    *,
    category="other",
    subject_id=None,
    title="予定",
    is_generated=False,
):
    """予定の行を、ORMで直接作る（予定を登録するAPIは、まだないため）。"""
    with app.app_context():
        event = Event(
            subject_id=subject_id,
            category=category,
            date=event_date,
            start_time=start_time,
            end_time=time(start_time.hour + 1, start_time.minute),
            title=title,
            is_generated=is_generated,
        )
        db.session.add(event)
        db.session.commit()
        return event.id


def event_ids(response):
    assert response.status_code == 200
    return [item["id"] for item in response.json]


def assert_validation_error(response, fields):
    assert response.status_code == 400
    assert response.json == {
        "error": {
            "code": "validation_error",
            "message": "入力内容に誤りがあります",
            "fields": fields,
        }
    }


def event_count(app):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(Event))


# --- 一覧（GET /api/events）：期間の中の予定 ---


def test_empty_event_list_returns_empty_array(client):
    response = client.get(f"/api/events?{APRIL_QUERY}")

    assert response.status_code == 200
    assert response.json == []


def test_event_list_returns_all_fields_of_each_event(client, app):
    semester_id = make_semester(app)
    subject_id = make_subject(app, semester_id)
    with app.app_context():
        class_event = Event(
            subject_id=subject_id,
            category="class",
            date=date(2026, 4, 6),
            start_time=time(9, 0),
            end_time=time(10, 30),
            title="プログラミング基礎",
            room="3号館201",
            notes="教科書を持参",
            is_generated=True,
        )
        part_time_event = Event(
            category="part_time",
            date=date(2026, 4, 7),
            start_time=time(17, 0),
            end_time=time(21, 45),
            title="倉庫の仕分け",
            employer="派遣会社A",
        )
        db.session.add_all([class_event, part_time_event])
        db.session.commit()
        class_event_id = class_event.id
        part_time_event_id = part_time_event.id

    response = client.get(f"/api/events?{APRIL_QUERY}")

    assert response.status_code == 200
    assert response.json == [
        {
            "id": class_event_id,
            "subject_id": subject_id,
            "category": "class",
            "date": "2026-04-06",
            "start_time": "09:00",
            "end_time": "10:30",
            "title": "プログラミング基礎",
            "room": "3号館201",
            "employer": None,
            "notes": "教科書を持参",
            "is_generated": True,
        },
        {
            "id": part_time_event_id,
            "subject_id": None,
            "category": "part_time",
            "date": "2026-04-07",
            "start_time": "17:00",
            "end_time": "21:45",
            "title": "倉庫の仕分け",
            "room": None,
            "employer": "派遣会社A",
            "notes": None,
            "is_generated": False,
        },
    ]


def test_event_list_includes_both_ends_and_excludes_outside(client, app):
    make_event(app, date(2026, 3, 31))
    first_day = make_event(app, date(2026, 4, 1))
    middle_day = make_event(app, date(2026, 4, 15))
    last_day = make_event(app, date(2026, 4, 30))
    make_event(app, date(2026, 5, 1))

    response = client.get(f"/api/events?{APRIL_QUERY}")

    assert event_ids(response) == [first_day, middle_day, last_day]


def test_event_list_orders_by_date_start_time_and_id(client, app):
    second_day = make_event(app, date(2026, 4, 2), time(9, 0))
    first_day_ten = make_event(app, date(2026, 4, 1), time(10, 0))
    first_day_nine_a = make_event(app, date(2026, 4, 1), time(9, 0))
    first_day_nine_b = make_event(app, date(2026, 4, 1), time(9, 0))

    response = client.get(f"/api/events?{APRIL_QUERY}")

    assert event_ids(response) == [
        first_day_nine_a,
        first_day_nine_b,
        first_day_ten,
        second_day,
    ]


def test_same_start_and_end_date_returns_only_that_day(client, app):
    make_event(app, date(2026, 4, 14))
    target = make_event(app, date(2026, 4, 15))
    make_event(app, date(2026, 4, 16))

    response = client.get(
        "/api/events?start_date=2026-04-15&end_date=2026-04-15"
    )

    assert event_ids(response) == [target]


def test_event_list_includes_all_categories_and_semesters(client, app):
    first_semester = make_semester(app)
    second_semester = make_semester(app, "2026年度 後期")
    first_subject = make_subject(app, first_semester)
    second_subject = make_subject(app, second_semester)
    expected = [
        make_event(
            app,
            date(2026, 4, 6),
            category="class",
            subject_id=first_subject,
            is_generated=True,
        ),
        make_event(
            app,
            date(2026, 4, 7),
            category="class",
            subject_id=second_subject,
            is_generated=True,
        ),
        make_event(
            app,
            date(2026, 4, 8),
            category="class",
            subject_id=first_subject,
        ),
        make_event(app, date(2026, 4, 9), category="part_time"),
        make_event(app, date(2026, 4, 10), category="other"),
    ]

    response = client.get(f"/api/events?{APRIL_QUERY}")

    assert event_ids(response) == expected


def test_unknown_queries_including_category_are_ignored(client, app):
    class_event = make_event(app, date(2026, 4, 6), category="class")
    part_time_event = make_event(app, date(2026, 4, 7), category="part_time")

    response = client.get(
        f"/api/events?{APRIL_QUERY}&category=class&semester_id=1&foo=bar"
    )

    assert event_ids(response) == [class_event, part_time_event]


def test_event_list_returns_events_generated_by_subject_registration(
    client, app
):
    semester_id = make_semester(app)
    created = client.post(
        "/api/subjects",
        json={
            "semester_id": semester_id,
            "subject_name": "プログラミング基礎",
            "weekday": 0,
            "start_time": "09:00",
            "end_time": "10:30",
        },
    )
    assert created.status_code == 201

    response = client.get(f"/api/events?{APRIL_QUERY}")

    assert response.status_code == 200
    assert [item["date"] for item in response.json] == [
        "2026-04-06",
        "2026-04-13",
        "2026-04-20",
        "2026-04-27",
    ]
    for item in response.json:
        assert item["subject_id"] == created.json["id"]
        assert item["category"] == "class"
        assert item["start_time"] == "09:00"
        assert item["end_time"] == "10:30"
        assert item["title"] == "プログラミング基礎"
        assert item["is_generated"] is True


def test_long_period_has_no_upper_limit(client, app):
    first = make_event(app, date(2026, 4, 1))
    second = make_event(app, date(2030, 1, 1))

    response = client.get(
        "/api/events?start_date=0001-01-01&end_date=9999-12-31"
    )

    assert event_ids(response) == [first, second]


# --- 一覧（GET /api/events）：クエリの検証 ---


@pytest.mark.parametrize(
    ("query", "fields"),
    [
        (
            "",
            {
                "start_date": "開始日は必須です",
                "end_date": "終了日は必須です",
            },
        ),
        (
            "?start_date=2026-04-01",
            {"end_date": "終了日は必須です"},
        ),
        (
            "?end_date=2026-04-30",
            {"start_date": "開始日は必須です"},
        ),
    ],
)
def test_missing_date_queries_are_validation_errors(client, query, fields):
    response = client.get(f"/api/events{query}")

    assert_validation_error(response, fields)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "2026-4-01",
        "2026/04/01",
        "20260401",
        "2026-02-30",
        "2026-13-01",
        "%202026-04-01",
        "2026-04-01T00:00",
        "%EF%BC%92026-04-01",
        "%ED%A0%80",
    ],
)
def test_malformed_start_date_query_is_validation_error(client, value):
    response = client.get(
        f"/api/events?start_date={value}&end_date=2026-04-30"
    )

    assert_validation_error(response, {"start_date": START_FORMAT_MESSAGE})


@pytest.mark.parametrize("value", ["", "2026-04-31", "abc"])
def test_malformed_end_date_query_is_validation_error(client, value):
    response = client.get(
        f"/api/events?start_date=2026-04-01&end_date={value}"
    )

    assert_validation_error(response, {"end_date": END_FORMAT_MESSAGE})


@pytest.mark.parametrize(
    ("query", "fields"),
    [
        (
            "start_date=2026-04-01&start_date=2026-04-02&end_date=2026-04-30",
            {"start_date": "開始日は1つだけ指定してください"},
        ),
        (
            "start_date=2026-04-01&end_date=2026-04-30&end_date=2026-05-31",
            {"end_date": "終了日は1つだけ指定してください"},
        ),
    ],
)
def test_repeated_date_queries_are_validation_errors(client, query, fields):
    response = client.get(f"/api/events?{query}")

    assert_validation_error(response, fields)


def test_end_date_before_start_date_is_validation_error(client):
    response = client.get(
        "/api/events?start_date=2026-04-02&end_date=2026-04-01"
    )

    assert_validation_error(
        response,
        {"end_date": "終了日は開始日以降の日付にしてください"},
    )


def test_date_query_errors_are_reported_together(client):
    response = client.get("/api/events?start_date=abc&end_date=2026-02-30")

    assert_validation_error(
        response,
        {
            "start_date": START_FORMAT_MESSAGE,
            "end_date": END_FORMAT_MESSAGE,
        },
    )


def test_period_check_is_skipped_when_start_date_is_invalid(client):
    response = client.get(
        "/api/events?start_date=2026-02-30&end_date=2026-01-01"
    )

    assert_validation_error(response, {"start_date": START_FORMAT_MESSAGE})


# --- 1件取得（GET /api/events/<id>） ---


def test_event_get_returns_same_item_as_list(client, app):
    semester_id = make_semester(app)
    subject_id = make_subject(app, semester_id)
    event_id = make_event(
        app,
        date(2026, 4, 6),
        category="class",
        subject_id=subject_id,
        title="プログラミング基礎",
        is_generated=True,
    )

    response = client.get(f"/api/events/{event_id}")
    listed = client.get(f"/api/events?{APRIL_QUERY}")

    assert response.status_code == 200
    assert response.json == listed.json[0]
    assert response.json["id"] == event_id


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/events/99999", "予定が見つかりません"),
        ("/api/events/0", "予定が見つかりません"),
        (f"/api/events/{MAX_ID}", "予定が見つかりません"),
        (f"/api/events/{MAX_ID + 1}", "URLが見つかりません"),
        ("/api/events/99999999999999999999", "URLが見つかりません"),
        ("/api/events/abc", "URLが見つかりません"),
        ("/api/events/-1", "URLが見つかりません"),
        ("/api/events/", "URLが見つかりません"),
    ],
)
def test_event_get_not_found_and_invalid_urls(client, url, message):
    response = client.get(url)

    assert response.status_code == 404
    assert response.json == {
        "error": {
            "code": "not_found",
            "message": message,
        }
    }


# --- 提供しない操作（405） ---


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("post", "/api/events"),
        ("put", "/api/events"),
        ("patch", "/api/events"),
        ("delete", "/api/events"),
        ("post", "/api/events/{event_id}"),
        ("put", "/api/events/{event_id}"),
        ("patch", "/api/events/{event_id}"),
        ("delete", "/api/events/{event_id}"),
    ],
)
def test_unsupported_event_methods_do_not_change_rows(
    client, app, method, url
):
    event_id = make_event(app, date(2026, 4, 6))
    url = url.format(event_id=event_id)
    before = client.get(f"/api/events/{event_id}")
    assert before.status_code == 200

    response = getattr(client, method)(url, json={"title": "変更"})

    assert response.status_code == 405
    assert response.json["error"]["code"] == "method_not_allowed"
    assert client.get(f"/api/events/{event_id}").json == before.json
    assert event_count(app) == 1
```

### 3-1. テストで確かめること（設計資料との対応）

| 設計資料（`docs/architecture.md` の「予定API」） | テスト | 件数 |
|---|---|---|
| 該当なしは空の配列 | `test_empty_event_list_returns_empty_array` | 1 |
| 全項目を返す（`null`・真偽値・時刻は `HH:MM`。`category` は保存値のまま） | `test_event_list_returns_all_fields_of_each_event` | 1 |
| 期間は両端を含む | `test_event_list_includes_both_ends_and_excludes_outside` | 1 |
| 並びは `date`・`start_time`・`id` の昇順 | `test_event_list_orders_by_date_start_time_and_id` | 1 |
| 同じ日なら、その1日 | `test_same_start_and_end_date_returns_only_that_day` | 1 |
| 学期・カテゴリ・`is_generated` によらない | `test_event_list_includes_all_categories_and_semesters` | 1 |
| `category` などのほかのクエリは無視 | `test_unknown_queries_including_category_are_ignored` | 1 |
| 授業の登録で作った予定が出る（DBの時刻 `09:00:00.000000` が `09:00` になる） | `test_event_list_returns_events_generated_by_subject_registration` | 1 |
| 期間の長さに上限はない | `test_long_period_has_no_upper_limit` | 1 |
| 指定がない（どちらか・両方） | `test_missing_date_queries_are_validation_errors` | 3 |
| 形式の誤り（`start_date`。空文字・前後の空白・全角の数字・UTF-8として読めない値を含む） | `test_malformed_start_date_query_is_validation_error` | 10 |
| 形式の誤り（`end_date`） | `test_malformed_end_date_query_is_validation_error` | 3 |
| 複数回の指定 | `test_repeated_date_queries_are_validation_errors` | 2 |
| `end_date` が `start_date` より前 | `test_end_date_before_start_date_is_validation_error` | 1 |
| 誤りは、まとめて返す | `test_date_query_errors_are_reported_together` | 1 |
| 前後の検査は、両方に誤りがないときだけ | `test_period_check_is_skipped_when_start_date_is_invalid` | 1 |
| 1件取得は、一覧の要素と同じ形 | `test_event_get_returns_same_item_as_list` | 1 |
| 1件取得の404（「予定が見つかりません」と「URLが見つかりません」の使い分け） | `test_event_get_not_found_and_invalid_urls` | 8 |
| `POST`・`PUT`・`PATCH`・`DELETE` は405で、予定は変わらない | `test_unsupported_event_methods_do_not_change_rows` | 8 |
| 合計 | | **47** |

## 変更してよい既存のテスト
なし（既存のテストのファイルは、すべて変えない）。

- このタスクでの「既存のテスト」は、作業の開始時からあるすべてのテスト（431件）。**既存のテストが、想定外に失敗した場合**は、テストの期待値や、ほかの仕様を直さない。原因を調べ、そこで実装を止めて、チャットで報告する

## 実装手順
1. ブランチ・作業ツリーの確認。設計資料が更新されていることを確認する（「Copilot確認手順」の1の `grep`）。更新されていなければ、何も変更せずに停止して報告する
2. 作業の前の状態を記録する：開発用DBの有無・ハッシュ・件数（「Copilot確認手順」の1。**`sqlite3` は `-readonly` を付ける**）。`python -m pytest -q` が431件、すべて合格すること（合格しなければ、何も変更せずに停止して報告する）
3. `app/routes/events.py`（1）→ `app/__init__.py`（2）→ `tests/test_events_api.py`（3）を、全文のとおりに作る
4. `python -m pytest -q` が478件（431＋47）、すべて合格すること
5. 「Copilot確認手順」の2〜5を実施する
6. 結果を報告して、応答を終える（サーバーを起動していないこと、`curl` での確認をしていないことを明記する）

## 完了条件
- `python -m pytest -q` が、作業の前に **431件**、作業の後に **478件**、すべて合格する（失敗・エラー・スキップが0件）
- 変更したファイルが、「実装対象ファイル」の3個だけ
- 3ファイルが、このTask MDの全文と1文字も違わない（「Copilot確認手順」の4が、3ファイルとも「一致」）
- `app/`・`tests/`・`run.py` のPythonのファイルに、79文字を超える行がない
- 実施の前後で、開発用DB（`instance/app.db`）のハッシュと、`semesters`・`subjects`・`closures`・`events`・`tasks` の件数が同じ
- 「Komaの確認」が、期待どおり
- レビューで承認される

## Copilot確認手順
**`sqlite3` は、必ず `-readonly` を付けて実行する**（付けずに開くと、読むだけでも、開発用DBを書き込み可能な状態で開くことになる。011-L1）。

```
# 1. 実施前
git branch --show-current      # feature/012-events-list-api
git status                     # 変更なし
grep -n "### 予定API" docs/architecture.md           # 1件
grep -n "read_date_query" docs/architecture.md       # 1件（予定APIの節）
grep -n "止まる場面の応答" .github/copilot-instructions.md   # 数件
ls -l instance/app.db          # 存在すること（なければ、何も変更せずに停止して報告する）
shasum -a 256 instance/app.db
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"
python -m pytest -q            # 431 passed

# 2. 実装の後
python -m pytest -q            # 478 passed
python -m pytest -q --co tests/test_events_api.py | tail -1   # 47 tests collected

# 3. 1行の長さ（出力がなければ合格。migrations/ は対象外）
python - <<'EOF'
from pathlib import Path
paths = [*Path("app").rglob("*.py"), *Path("tests").glob("*.py"), Path("run.py")]
for path in paths:
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, 1):
        if len(line) > 79:
            print(f"{path}:{number}: {len(line)}")
EOF

# 4. 3ファイルが、このTask MDの全文と同じこと（011-N1）
python - <<'EOF'
import difflib
import re
from pathlib import Path

# このTask MDの「<!-- 全文: パス -->」の直後のコードブロックを、
# そのファイルの期待する全文として取り出し、今のファイルと比べる。
fence = "`" * 3
task_text = Path("docs/tasks/012_events_list_api.md").read_text(
    encoding="utf-8"
)
pattern = re.compile(
    "<!-- 全文: (\\S+) -->\n" + fence + "python\n(.*?)" + fence + "\n",
    re.S,
)
expected_files = dict(pattern.findall(task_text))
print(f"全文の数：{len(expected_files)}")
for file_name, expected in expected_files.items():
    path = Path(file_name)
    actual = path.read_text(encoding="utf-8") if path.exists() else ""
    if actual == expected:
        print(f"{file_name}：一致")
        continue
    print(f"{file_name}：不一致")
    diff = difflib.unified_diff(
        expected.splitlines(),
        actual.splitlines(),
        "Task MD",
        file_name,
        lineterm="",
    )
    print("\n".join(diff))
EOF

# 5. 検索と差分
git diff --numstat app/__init__.py                 # 4	0	app/__init__.py
grep -n "events_bp" app/__init__.py                # 2件
grep -n "read_date_query" app/routes/events.py     # 3件：定義と、2回の呼び出し
grep -n "session.add\|session.delete\|commit" app/routes/events.py   # 出力なし（書き込みがない）
grep -n "methods=\|\.post(\|\.patch(\|\.delete(\|\.put(" app/routes/events.py   # 出力なし（GETだけ）
git diff --stat app/api_helpers.py app/class_events.py app/models/ app/routes/semesters.py app/routes/subjects.py app/routes/closures.py app/static/ app/templates/ migrations/ tests/conftest.py   # 出力なし

# 6. 実施後
shasum -a 256 instance/app.db  # 実施前と同じ
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"   # 実施前と同じ
git status                     # 変更：app/__init__.py。新規：app/routes/events.py、tests/test_events_api.py
git diff --stat
```

| 確認 | 期待する結果 |
|---|---|
| `python -m pytest -q` | 実施前431件、実施後478件が、すべて合格。失敗・エラー・スキップが0件。`migrations/env.py` の `DeprecationWarning` は、出ても構わない（報告する） |
| 1行の長さ | 出力なし |
| 全文との比較（4） | `全文の数：3` と、3ファイルとも「一致」。「不一致」が出たら、表示された差分を、Task MDの全文に合わせて直し、2からやり直す（Task MDの全文のほうを変える必要があると判断した場合は、停止して報告する） |
| 検索と差分（5） | 上のコメントのとおり（件数が違う場合は、その行を報告に書く） |
| 開発用DB | 実施の前後で、ハッシュと、5つのテーブルの件数が同じ |
| `git status` | 変更：`app/__init__.py`。新規：`app/routes/events.py`、`tests/test_events_api.py`。`app/models/`・`migrations/`・`app/static/`・`app/templates/`・`docs/`・`.github/`・`requirements.txt`・`run.py`・`instance/` に変更なし |

`.pytest_cache/` や `__pycache__/` が `git status` に表示される場合は、`.gitignore` を変更せず、報告する。**Copilotは、サーバーを起動せず、`curl` での確認もしない。** 報告に、そのことを明記する。

## Komaの確認
順序：（1）pytest →（2）commit・push とレビューの依頼 →（3）APIの確認（確認用のサーバー）→（4）マージ。**ブラウザでの確認は、このタスクにはない**（画面を変えないため。roadmap の「進め方の決定の記録」、2026-10-11）。

### 1. pytest
`python -m pytest -q` を自分で実行し、**478件、すべて合格**することを確かめる。

### 2. push とレビューの依頼
featureブランチを commit・push する（PRを作ってもよい）。Copilotの完了報告を共有して、Claudeにレビューを頼む。**pushは、マージではない。レビューの承認の前に、マージしない。** 修正が必要になった場合は、同じブランチでCopilotが直し、もう一度pushしてレビューを受ける。

### 3. APIの確認（確認用のサーバー）
レビューで「承認可能」になったあとに行う。**開発用DBは使わない。** 確認用のDB（`/tmp/schedule-app-check-012/check.db`）を、migrationで作り、そのDBで起動した確認用のサーバーに、`curl` で要求する（Task 010・011と同じ方法）。開発用DBには、何も残らない。

#### 準備
1. `python run.py` が起動していれば、Ctrl＋Cで止める（確認用のサーバーも、5001番を使うため）。開発用DBのハッシュを控える
   ```
   shasum -a 256 instance/app.db
   ```
2. ブランチ `feature/012-events-list-api` のまま、リポジトリのルートで、`.venv` を有効にして、次を実行する（行の先頭に空白を入れずにコピーする。このターミナルは、確認の間、開いたままにする）

```
python - <<'EOF'
from pathlib import Path

from flask_migrate import upgrade

from app import create_app

# 確認用のDB（開発用DBとは別のファイル）。止めて起動し直しても、残る。
check_directory = Path("/tmp/schedule-app-check-012")
check_directory.mkdir(exist_ok=True)
database_path = check_directory / "check.db"
app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"})
with app.app_context():
    upgrade(directory="migrations")
print(f"確認用のDB：{database_path}", flush=True)
app.run(host="127.0.0.1", port=5001, debug=False)
EOF
```

期待する出力：`Running upgrade  -> 0280f6cf8d09, initial tables` と `Running upgrade 0280f6cf8d09 -> 42bd53808fa1, add closures table`、「確認用のDB：/tmp/schedule-app-check-012/check.db」、`Running on http://127.0.0.1:5001`。

3. 別のターミナルを開き、リポジトリのルートで、`.venv` を有効にして、`BASE=http://127.0.0.1:5001` を実行しておく

#### 確認（別のターミナルで、上から順に実行する）
A1〜A3は、確認用のDBに、学期・休講日・授業を1件ずつ登録する（授業の登録で、予定が16件作られる）。

```
# A1. 学期（2026-04-06〜2026-07-31）
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X POST $BASE/api/semesters -H 'Content-Type: application/json' -d '{"name": "2026年度 前期", "start_date": "2026-04-06", "end_date": "2026-07-31"}'
# A2. 休講日（2026-05-04）
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X POST $BASE/api/closures -H 'Content-Type: application/json' -d '{"semester_id": 1, "date": "2026-05-04", "name": "振替休日"}'
# A3. 月曜日の授業（9:00〜10:30）
curl -s -X POST $BASE/api/subjects -H 'Content-Type: application/json' -d '{"semester_id": 1, "subject_name": "テスト：月曜1限", "weekday": 0, "start_time": "09:00", "end_time": "10:30", "room": "3号館201"}' | python -m json.tool --no-ensure-ascii
# A4. 休講日をはさむ期間（4/27〜5/11）
curl -s "$BASE/api/events?start_date=2026-04-27&end_date=2026-05-11" | python -m json.tool --no-ensure-ascii
# A5. 学期の期間の全体（件数・最初の日・最後の日）
curl -s "$BASE/api/events?start_date=2026-04-01&end_date=2026-07-31" | python -c 'import json, sys; events = json.load(sys.stdin); print(len(events), events[0]["date"], events[-1]["date"])'
# A6. 1日だけ（未知のクエリ category は無視される）
curl -s "$BASE/api/events?start_date=2026-04-06&end_date=2026-04-06&category=part_time" | python -c 'import json, sys; events = json.load(sys.stdin); print(len(events), events[0]["date"], events[0]["category"])'
# A7. 1件取得
curl -s $BASE/api/events/1 | python -m json.tool --no-ensure-ascii
# A8. 期間の指定がない
curl -s $BASE/api/events | python -m json.tool --no-ensure-ascii
# A9. 終了日が開始日より前
curl -s "$BASE/api/events?start_date=2026-05-11&end_date=2026-05-10" | python -m json.tool --no-ensure-ascii
# A10. 存在しない予定
curl -s $BASE/api/events/99999 | python -m json.tool --no-ensure-ascii
# A11. 提供しない操作（予定の編集・登録）
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X PATCH $BASE/api/events/1 -H 'Content-Type: application/json' -d '{"title": "変更"}'
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X POST $BASE/api/events -H 'Content-Type: application/json' -d '{}'
```

| No | 期待する結果 |
|---|---|
| A1・A2 | `HTTP 201` |
| A3 | `"generated_event_count": 16`（2026-04-06〜07-27の月曜日17日から、休講日の5/4を除く）、`"id": 1` |
| A4 | 2件。`"date": "2026-04-27"` と `"date": "2026-05-11"`（5/4は休講日のため、予定がない）。どちらも `"start_time": "09:00"`、`"end_time": "10:30"`（秒が付かない）、`"category": "class"`、`"title": "テスト：月曜1限"`、`"room": "3号館201"`、`"employer": null`、`"notes": null`、`"is_generated": true`、`"subject_id": 1` |
| A5 | `16 2026-04-06 2026-07-27` |
| A6 | `1 2026-04-06 class` |
| A7 | `"id": 1`、`"date": "2026-04-06"`、ほかの項目はA4の各要素と同じ形 |
| A8 | `validation_error`、`fields` に `"end_date": "終了日は必須です"` と `"start_date": "開始日は必須です"` |
| A9 | `validation_error`、`fields` に `"end_date": "終了日は開始日以降の日付にしてください"` だけ |
| A10 | `not_found`、`"message": "予定が見つかりません"` |
| A11 | 2行とも `HTTP 405` |

（応答の項目は、Flaskが項目名の順に並べて返すため、表示の順は、設計資料の例と違う。中身が同じなら、期待どおり）

#### 後片付け
1. 確認用のサーバーを止める（Ctrl＋C）
2. 確認用のDBのフォルダを消す
   ```
   rm -r /tmp/schedule-app-check-012
   ```
3. 開発用DBのハッシュが、準備の1と同じことを確かめる
   ```
   shasum -a 256 instance/app.db
   ```

ハッシュが変わっていた場合は、開発用DBを操作せずに、Claudeに伝える。

### 4. マージ
1〜3が期待どおりで、レビューで承認されたら、マージする。このタスクは、DBの構造を変えないため、開発用DBへのmigrationの適用はない。開発用DBのデータも変えないため、バックアップは要らない。

## Git操作
**Git commit / push / ブランチ操作 / マージは行わない**（`git branch --show-current`、`git status`、`git diff` のような読み取りだけのコマンドは除く）。

## 注意
- **停止して報告する条件**（ファイルを変更せず、実装を止め、チャットで「問題点・発生理由・変更した場合の影響・推奨案（必要なら）」を報告する）
  - ブランチの不一致、作業ツリーの想定外の変更
  - 設計資料が更新されていない（実装手順の1）、または、設計資料とこのTask MDの間に、矛盾・不足がある
  - 設計資料にない判断が必要になった（特に、`docs/architecture.md` の「未決定事項」に触れる場合）
  - 「変更しない」と定めたもの（モデル、`api_helpers.py`、既存のテスト、画面のファイルなど）を変更しないと実装できない。または、1〜3の全文を変える必要があると判断した
  - 開発用DB（`instance/app.db`）がない
  - 作業の前の `python -m pytest` が、431件すべて合格しない
  - **既存のテスト**（作業の開始時からある431件）**が、想定外に失敗した**。テストの期待値や、ほかの仕様を直さずに、原因を調べて報告する
  - DBの構造の変更（migration）や、APIの変更（このTask MDに書いたもの以外）が必要だと判断した
  - 実施の前後で、`instance/app.db` が変わった
- **止まるときは、報告を書いて、その応答を終える。質問の機能は使わない。** 再開するのは、Komaの新しいメッセージが、判断や再開を明確に示したときだけ（無回答や「続けて」だけの返事は、再開の指示ではない）。`.github/copilot-instructions.md` の「止まる場面の応答」
- **開発用DBを `sqlite3` で開くときは、必ず `-readonly` を付ける**（SELECTだけでも、付けずに開かない。011-L1）。`flask db` のコマンドを、一切実行しない。ライブラリを追加しない。サーバーを起動しない（`python run.py` も、「Komaの確認」の確認用のサーバーも）
- 期待する結果と異なる結果が出た場合は、確認を飛ばさず、原因を直してから、すべての確認をやり直す（ただし、既存のテストの想定外の失敗は、上の停止の条件に従う）
- 設計資料に書かれていない仕様は、自分で決めない
- 最後の報告に、次を含める：変更したファイル、作業の前後の `pytest` の件数と警告、1行の長さの確認の結果、全文との比較の結果（3ファイルの「一致」）、検索と差分の結果、開発用DBの前後のハッシュ・件数、`git status`・`git diff --stat`、サーバーの起動と `curl` の確認をしていないこと、気になった点
