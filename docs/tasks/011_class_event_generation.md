# タスク011: 授業の予定の自動生成と、休講日の同期

| 項目 | 内容 |
|---|---|
| Task ID | 011 |
| Task名 | 授業の予定の自動生成と、休講日の同期 |
| ブランチ | `feature/011-class-event-generation`（Komaが作成・切替済みの状態で渡される） |

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに停止して報告する。

**このタスクには、承認ゲートはない（DBの構造を変えないため、migrationを作らない）。** 段階1〜4を順に進め、「Copilot確認手順」を実施したら、結果を報告して応答を終える。途中で止まるのは、「注意」の停止の条件に当たったときだけ。**止まるときは、報告を書いて応答を終える。質問の機能（選択肢を出して回答を待つ機能）は使わない**（`.github/copilot-instructions.md` の「止まる場面の応答」）。

## 目的
授業を登録したときに、学期の期間の授業の予定（Event）を、実際の行としてまとめて作る（予定の自動生成）。あわせて、休講日の追加・削除を、登録済みの予定に反映する（休講日の同期）。設計資料（`docs/architecture.md` の「繰り返し予定の扱い」「休講日の変更と予定の同期」）の最終的な仕様を、そのまま実装する。画面では、授業の登録の成功メッセージに、作った予定の件数を出す。Task 006のレビューで持ち越した、画面のLow 5件（006-L1〜L5）も直す。

次の4段階で、この順に行う。

| 段階 | 内容 | 挙動の変化 | 段階の終わりの `pytest` |
|---|---|---|---|
| 1 | `app/class_events.py`（予定の日付の計算と、予定の作成）と、その単体テスト | なし（まだ、どこからも使わない） | **413件**（394＋19） |
| 2 | 授業の登録で、予定を作る（`generated_event_count`） | 授業の登録で、予定ができる | **421件**（＋8。既存の4件の期待値を直す） |
| 3 | 休講日の追加・削除で、予定を同期する | 休講日の追加で、その日の予定が消え、削除で作られる | **431件**（＋12、−2。途中の段階のテスト2件を置き換える） |
| 4 | 画面：授業の登録の成功メッセージと、006-L1〜L5 | 成功メッセージに件数が出る | **431件**（JavaScriptの自動テストはない） |

## 前提（Task 010完了時点の状態）

| 区分 | 内容 |
|---|---|
| すでにある | 学期API・授業API（登録は、授業の行だけを作る）・休講日API（登録・削除は、休講日の行だけを扱い、予定を同期しない）、学期・授業・休講日の画面、pytest（**394件**。`main` の `3cfc5a1` で確認） |
| まだない | `app/class_events.py`、`tests/test_class_events.py`、予定（Event）を作る・消す処理、`generated_event_count` |
| DBの構造 | 変えない（初期migration `0280f6cf8d09` と、休講日の `42bd53808fa1`）。`events` テーブルには、必要な列（「データ設計」の Event）が、すべてある。**migrationは不要** |
| 開発用DB | `instance/app.db` は、Komaの実際の開発用DB（学期・授業・休講日は0件。2026-10-12にKomaが確認）。**Copilotは、書き込まない。サーバーを起動しない（`python run.py` を実行しない）**。読むのは、「Copilot確認手順」のハッシュと件数だけ。予定の自動生成を入れたコードを、開発用DBで初めて動かす前の手順（バックアップと件数の確認）は、Komaが行う（「Komaの確認」の4） |
| 設計資料 | このタスクの前に、更新した設計資料が `main` に反映されている。`docs/architecture.md` の「休講日の変更と予定の同期」の末尾が「実装の経緯」になっている（「最終的な仕様と、実装の途中の段階」は、なくなっている）。「予定の自動生成より前に登録した授業」に、授業が0件の場合の扱いがある。「JavaScriptの構成」の `ui.js` の行に、`getElement` の挙動がある。規則に、`try` の範囲と、真偽値の位置引数の規則がある。`docs/ui_ux.md` の「休講日」の「削除」から、途中の段階の一文が消えている |
| JavaScriptの確認 | JavaScriptの自動テストはない。Copilotはブラウザを使えないため、画面の動作は、確認用のサーバーとブラウザで確かめる（「Komaの確認」）。Copilotは、コードの検索・差分で確かめる |

## Source of Truth
- `docs/architecture.md`：「データ設計」の「繰り返し予定の扱い」（生成の規則、各Eventの値、「休講日の変更と予定の同期」、「同じ授業・同じ日付に単発の予定がある場合」、「予定の自動生成より前に登録した授業」、「授業のEventの生成処理：`app/class_events.py`」）、「API共通ルール」の「作成のレスポンスの付加情報」、「授業API」、「休講日API」、「自動テスト（pytest）」の「テストの書き方」、「JavaScriptの構成（ES modules）」（`ui.js` の行と、規則）
- `docs/ui_ux.md`：「授業モード」の授業の登録（登録済みのメッセージ）、「休講日」
- `docs/tasks/006_subjects_ui.md`・`docs/tasks/010_closures_ui.md`：授業・休講日の画面の作り
- `.github/copilot-instructions.md`：進め方、「止まる場面の応答」、コーディング方針、「テスト」

## 実装対象ファイル

| 区分 | ファイル | 段階 | 内容 |
|---|---|---|---|
| 新規 | `app/class_events.py` | 1 | 予定の日付の計算と、予定の作成（3つの関数と、定数 `EVENT_CATEGORY_CLASS`） |
| 新規 | `tests/test_class_events.py` | 1 | 上の単体テスト（19件。DBを使わない） |
| 変更 | `app/routes/subjects.py` | 2 | 授業の登録で、予定を作る。`generated_event_count` |
| 変更 | `tests/test_subjects_api.py` | 2 | 既存の4件の期待値と、新しいテスト8件 |
| 変更 | `app/routes/closures.py` | 3 | 休講日の追加・削除で、予定を同期する |
| 変更 | `tests/test_closures_api.py` | 3 | 途中の段階のテスト2件を、新しいテスト12件に置き換える |
| 変更 | `app/static/js/subjects.js` | 4 | 成功メッセージ、006-L1・L2 |
| 変更 | `app/static/js/closures.js` | 4 | 006-L1・L2と同じ形を直す |
| 変更 | `app/static/js/semesters.js` | 4 | 006-L4、006-L1と同じ形を直す |
| 変更 | `app/static/js/ui.js` | 4 | 006-L3・L5 |

上の10ファイル以外は、変更しない（`__pycache__/` などの、`.gitignore` の対象は除く）。

## 非対象（このタスクでは作らない・変更しない）
- モデル（`app/models/`）、`migrations/`（**新しいmigrationを作らない。`flask db` のコマンドを、一切実行しない**）、`requirements.txt`（**ライブラリを追加しない**）、`pytest.ini`、`run.py`
- `app/api_helpers.py`、`app/routes/semesters.py`、`app/routes/main.py`、`app/__init__.py`
- `app/templates/`（HTMLは変えない）、`app/static/js/api.js`・`dates.js`・`main.js`
- `tests/conftest.py`・`test_setup.py`・`test_api_helpers.py`・`test_semesters_api.py`
- `docs/`、`.github/`、`.gitignore`
- 予定の一覧API（`GET /api/events`。Task 012）、カレンダー（Task 013）、授業の編集・削除（Task 014・015）
- 予定をまとめて作り直す専用の入口（APIなど）。既存の授業に、あとから予定を作る処理（未決定事項「自動生成より前に登録した授業のうち、残すものの扱い」）
- `docs/ui_ux.md` の「未決定」（曜日ごとの授業日数の表示など）
- Task 003の持ち越しの残り（003-H）、010-N2（休講日の「削除」ボタンの `aria-label`）
- 開発用DB（`instance/app.db`）への書き込み、サーバーの起動（`python run.py` も、「Komaの確認」の確認用のサーバーも、起動しない）

## 段階1：`app/class_events.py` と単体テスト（挙動を変えない）

### 1-1. `app/class_events.py`（新規）
次のとおりに書く（動作を確かめたコード）。`docs/architecture.md` の「授業のEventの生成処理」のとおり、DB・`db.session`・「今日」を使わない。

```python
"""授業の予定（Event）の生成。

授業の登録と、休講日の削除による予定の作成から使う部品。
DBの読み書き（セッションへの追加・commit）は行わない。休講日の日付の
取得と、データの保存は、各routeが担当する。
"""

from datetime import date, timedelta

from app.models.event import Event
from app.models.semester import Semester
from app.models.subject import Subject


# 授業の予定のカテゴリの保存値。文字列 "class" を、ほかの場所に直接書かない。
EVENT_CATEGORY_CLASS = "class"


def class_event_dates(
    start_date: date,
    end_date: date,
    weekday: int,
    excluded_dates: set[date],
) -> list[date]:
    """期間の中で、曜日が一致する日を、昇順で返す。

    start_date・end_date は両端を含む。weekday は 0=月曜〜6=日曜
    （date.weekday() と同じ）。excluded_dates（学期の休講日の日付）に
    含まれる日は除く。休講日の渡し忘れを防ぐため、省略できない引数にする。
    該当する日がなければ、空の一覧を返す。
    """
    # 最初の該当日までの日数。Pythonの % は、負の数でも 0〜6 を返す。
    days_until_first = (weekday - start_date.weekday()) % 7
    current = start_date + timedelta(days=days_until_first)

    dates = []
    while current <= end_date:
        if current not in excluded_dates:
            dates.append(current)
        current += timedelta(days=7)
    return dates


def build_class_event(subject: Subject, event_date: date) -> Event:
    """授業と日付から、自動生成の予定を1件作る（セッションには追加しない）。

    授業の値を予定に写す方法は、この関数の1か所にまとめる。授業との関係は
    relationship で結ぶため、授業の id が採番される前でも作れる。
    """
    return Event(
        subject=subject,
        category=EVENT_CATEGORY_CLASS,
        date=event_date,
        start_time=subject.start_time,
        end_time=subject.end_time,
        title=subject.subject_name,
        room=subject.room,
        employer=None,
        notes=subject.notes,
        is_generated=True,
    )


def build_class_events(
    subject: Subject,
    semester: Semester,
    excluded_dates: set[date],
) -> list[Event]:
    """学期の期間全体の、授業の自動生成の予定を作る（セッションには追加しない）。

    学期は、routeが取得済みのものを受け取る（この関数の中で、DBを読まない）。
    """
    dates = class_event_dates(
        semester.start_date,
        semester.end_date,
        subject.weekday,
        excluded_dates,
    )
    return [build_class_event(subject, event_date) for event_date in dates]
```

- `excluded_dates` は、省略できない引数（既定値を付けない）
- 文字列 `"class"` は、このファイルの定数 `EVENT_CATEGORY_CLASS` の1か所にだけ書く

### 1-2. `tests/test_class_events.py`（新規）
次のとおりに書く（19件。アプリもDBも作らずに、関数を直接呼ぶ）。

```python
from datetime import date, time, timedelta

import pytest

from app.class_events import (
    EVENT_CATEGORY_CLASS,
    build_class_event,
    build_class_events,
    class_event_dates,
)
from app.models.semester import Semester
from app.models.subject import Subject


# docs/architecture.md の例：2026-04-01（水）〜2026-07-31（金）の月曜日。
MONDAYS_FROM_APRIL_1 = [
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


def make_subject(**overrides):
    values = {
        "semester_id": 1,
        "subject_name": "プログラミング基礎",
        "room": "3号館201",
        "weekday": 0,
        "start_time": time(9, 0),
        "end_time": time(10, 0),
        "notes": "前期の授業",
    }
    values.update(overrides)
    return Subject(**values)


def make_semester():
    return Semester(
        id=1,
        name="2026年度 前期",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 7, 31),
    )


def test_dates_match_the_documented_example():
    dates = class_event_dates(date(2026, 4, 1), date(2026, 7, 31), 0, set())

    assert dates == MONDAYS_FROM_APRIL_1


@pytest.mark.parametrize(
    ("weekday", "count", "first", "last"),
    [
        (0, 17, date(2026, 4, 6), date(2026, 7, 27)),
        (1, 17, date(2026, 4, 7), date(2026, 7, 28)),
        (2, 18, date(2026, 4, 1), date(2026, 7, 29)),
        (3, 18, date(2026, 4, 2), date(2026, 7, 30)),
        (4, 18, date(2026, 4, 3), date(2026, 7, 31)),
        (5, 17, date(2026, 4, 4), date(2026, 7, 25)),
        (6, 17, date(2026, 4, 5), date(2026, 7, 26)),
    ],
)
def test_dates_for_each_weekday_are_weekly_and_ascending(
    weekday, count, first, last
):
    dates = class_event_dates(
        date(2026, 4, 1), date(2026, 7, 31), weekday, set()
    )

    assert len(dates) == count
    assert dates[0] == first
    assert dates[-1] == last
    assert all(day.weekday() == weekday for day in dates)
    assert all(
        later - earlier == timedelta(days=7)
        for earlier, later in zip(dates, dates[1:])
    )


def test_start_and_end_dates_are_included():
    # 開始日・終了日とも月曜日。
    dates = class_event_dates(date(2026, 4, 6), date(2026, 4, 20), 0, set())

    assert dates == [date(2026, 4, 6), date(2026, 4, 13), date(2026, 4, 20)]


def test_single_day_period_returns_that_day_when_weekday_matches():
    dates = class_event_dates(date(2026, 4, 6), date(2026, 4, 6), 0, set())

    assert dates == [date(2026, 4, 6)]


def test_period_without_the_weekday_returns_empty_list():
    # 2026-04-01（水）〜2026-04-02（木）に、月曜日はない。
    dates = class_event_dates(date(2026, 4, 1), date(2026, 4, 2), 0, set())

    assert dates == []


def test_excluded_dates_are_removed():
    dates = class_event_dates(
        date(2026, 4, 1),
        date(2026, 7, 31),
        0,
        {date(2026, 5, 4), date(2026, 7, 20)},
    )

    assert len(dates) == 15
    assert date(2026, 5, 4) not in dates
    assert date(2026, 7, 20) not in dates


def test_excluded_dates_of_other_weekdays_or_outside_do_not_matter():
    dates = class_event_dates(
        date(2026, 4, 1),
        date(2026, 7, 31),
        0,
        {date(2026, 5, 5), date(2026, 3, 30), date(2026, 8, 3)},
    )

    assert dates == MONDAYS_FROM_APRIL_1


def test_all_days_excluded_returns_empty_list():
    dates = class_event_dates(
        date(2026, 4, 6),
        date(2026, 4, 12),
        0,
        {date(2026, 4, 6)},
    )

    assert dates == []


def test_excluded_dates_argument_is_required():
    with pytest.raises(TypeError):
        class_event_dates(date(2026, 4, 1), date(2026, 7, 31), 0)


def test_build_class_event_copies_subject_values():
    subject = make_subject()

    event = build_class_event(subject, date(2026, 4, 6))

    assert event.subject is subject
    assert event.category == EVENT_CATEGORY_CLASS == "class"
    assert event.date == date(2026, 4, 6)
    assert event.start_time == time(9, 0)
    assert event.end_time == time(10, 0)
    assert event.title == "プログラミング基礎"
    assert event.room == "3号館201"
    assert event.employer is None
    assert event.notes == "前期の授業"
    assert event.is_generated is True


def test_build_class_event_keeps_null_room_and_notes():
    subject = make_subject(room=None, notes=None)

    event = build_class_event(subject, date(2026, 4, 6))

    assert event.room is None
    assert event.notes is None


def test_build_class_events_uses_semester_period_and_excluded_dates():
    subject = make_subject()

    events = build_class_events(
        subject, make_semester(), {date(2026, 5, 4)}
    )

    assert [event.date for event in events] == [
        day for day in MONDAYS_FROM_APRIL_1 if day != date(2026, 5, 4)
    ]
    assert all(event.subject is subject for event in events)
    assert all(event.is_generated is True for event in events)


def test_build_class_events_returns_empty_list_without_matching_days():
    semester = Semester(
        id=1,
        name="2026年度 前期",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 2),
    )

    assert build_class_events(make_subject(), semester, set()) == []
```

段階1の終わりに、`python -m pytest -q` が **413件、すべて合格**すること。

## 段階2：授業の登録で、予定を作る

### 2-1. `app/routes/subjects.py`
行番号は、`main`（このタスクを始める時点、`3cfc5a1`）のもの。次の差分のとおりに変える。

1. `import` に、`build_class_events`（`app.class_events`）と `Closure` を足す（17行目の前後）
2. 学期の存在の確認（111行目）で、取得した学期を、変数 `semester` に残す（87行目の次に、`semester: Semester | None = None` を足す）
3. 保存（189〜200行目）：先に、その学期の休講日の日付を取得する → 授業を `db.session.add` → `build_class_events` で予定を作る → `db.session.add_all(events)` → 1回の `commit`。レスポンスは、授業の辞書に `generated_event_count`（作った予定の件数）を足したもの
   - この順序は変えない。休講日の日付の取得は、授業を追加する前に行う。予定は、必ず `add_all` で明示的に追加する（`docs/architecture.md` の「授業のEventの生成処理」。授業を先に追加したあとで作った予定は、授業との関係だけではセッションに入らず、エラーにならないまま保存されない。作業用のコピーで確かめた）
   - `subject_to_dict` は変えない（`GET` のレスポンスには、`generated_event_count` を含めない）

```diff
--- a/app/routes/subjects.py
+++ b/app/routes/subjects.py
@@ -14,7 +14,9 @@ from app.api_helpers import (
     validate_required_string,
     validate_required_time,
 )
+from app.class_events import build_class_events
 from app.extensions import db
+from app.models.closure import Closure
 from app.models.semester import Semester
 from app.models.subject import Subject
 
@@ -85,6 +87,7 @@ def create_subject():
         return error_response
 
     fields: dict[str, str] = {}
+    semester: Semester | None = None
     allowed_fields = {
         "semester_id",
         "subject_name",
@@ -108,7 +111,8 @@ def create_subject():
         if not 1 <= semester_id <= MAX_ID:
             fields["semester_id"] = "指定された学期が存在しません"
         else:
-            if db.session.get(Semester, semester_id) is None:
+            semester = db.session.get(Semester, semester_id)
+            if semester is None:
                 fields["semester_id"] = "指定された学期が存在しません"
 
     subject_name, subject_name_error = validate_required_string(
@@ -186,6 +190,15 @@ def create_subject():
             fields,
         )
 
+    # 予定を作らない日（学期の休講日）を、先に取得する。
+    excluded_dates = set(
+        db.session.scalars(
+            db.select(Closure.date).where(
+                Closure.semester_id == semester.id
+            )
+        )
+    )
+
     subject = Subject(
         semester_id=semester_id,
         subject_name=subject_name,
@@ -196,5 +209,16 @@ def create_subject():
         notes=notes,
     )
     db.session.add(subject)
+    events = build_class_events(subject, semester, excluded_dates)
+    # 予定も、明示的に追加する。授業を先に追加したあとで作った予定は、
+    # 授業との関係だけではセッションに入らず、エラーにならないまま
+    # 保存されないため。
+    db.session.add_all(events)
+    # 授業と予定を1回のcommitで保存する。commitの前に例外が起きた場合は、
+    # どちらも保存されない。
     db.session.commit()
-    return jsonify(subject_to_dict(subject)), 201
+
+    response = subject_to_dict(subject)
+    # 作成のレスポンスにだけ付ける付加情報（DBには保存しない）。
+    response["generated_event_count"] = len(events)
+    return jsonify(response), 201
```

### 2-2. `tests/test_subjects_api.py`
次の差分のとおりに変える。

- `import` に `Closure` を足す。`subject_count` の次に、補助関数 `event_count`・`generated_event_dates`・`make_closure` を足す
- 既存の4件の期待値を直す（「変更してよい既存のテスト」）
- ファイルの末尾に、新しいテスト8件を足す（`# --- 授業の登録による予定（Event）の自動生成（Task 011） ---` から下）

```diff
--- a/tests/test_subjects_api.py
+++ b/tests/test_subjects_api.py
@@ -9,6 +9,7 @@ from app.api_helpers import (
     UNUSABLE_CHARACTER_MESSAGE,
 )
 from app.extensions import db
+from app.models.closure import Closure
 from app.models.event import Event
 from app.models.semester import Semester
 from app.models.subject import Subject
@@ -71,6 +72,32 @@ def subject_count(app):
         return db.session.scalar(select(func.count()).select_from(Subject))
 
 
+def event_count(app):
+    with app.app_context():
+        return db.session.scalar(select(func.count()).select_from(Event))
+
+
+def generated_event_dates(app, subject_id):
+    """授業の自動生成の予定の日付を、昇順で返す（同じ日付が2件あれば2回）。"""
+    with app.app_context():
+        return list(
+            db.session.scalars(
+                select(Event.date)
+                .where(
+                    Event.subject_id == subject_id,
+                    Event.is_generated.is_(True),
+                )
+                .order_by(Event.date)
+            )
+        )
+
+
+def make_closure(app, semester_id, closure_date):
+    with app.app_context():
+        db.session.add(Closure(semester_id=semester_id, date=closure_date))
+        db.session.commit()
+
+
 def test_subject_creation_returns_all_fields_and_matches_database(
     client, app
 ):
@@ -96,6 +123,7 @@ def test_subject_creation_returns_all_fields_and_matches_database(
         "start_time": "09:15",
         "end_time": "10:45",
         "notes": "前期の授業",
+        "generated_event_count": 18,
     }
 
     with app.app_context():
@@ -128,6 +156,7 @@ def test_subject_creation_with_required_fields_uses_null_optional_values(
         "start_time",
         "end_time",
         "notes",
+        "generated_event_count",
     }
     assert response.json["room"] is None
     assert response.json["notes"] is None
@@ -191,7 +220,7 @@ def test_subject_accepts_weekday_and_time_boundaries(
     assert response.json["end_time"] == end_time
 
 
-def test_duplicate_subject_rows_are_allowed_and_do_not_create_events_or_tasks(
+def test_duplicate_subject_rows_are_allowed_and_each_get_events(
     client, app
 ):
     semester_id = make_semester(app)
@@ -202,10 +231,16 @@ def test_duplicate_subject_rows_are_allowed_and_do_not_create_events_or_tasks(
     assert first.status_code == 201
     assert second.status_code == 201
     assert first.json["id"] != second.json["id"]
+    # 同じ内容の授業を2回登録すると、それぞれに予定が1組ずつ作られる。
+    assert first.json["generated_event_count"] == 17
+    assert second.json["generated_event_count"] == 17
+    assert generated_event_dates(app, first.json["id"]) == (
+        generated_event_dates(app, second.json["id"])
+    )
     with app.app_context():
         assert db.session.scalar(
             select(func.count()).select_from(Event)
-        ) == 0
+        ) == 34
         assert db.session.scalar(
             select(func.count()).select_from(Task)
         ) == 0
@@ -647,8 +682,11 @@ def test_subject_get_returns_created_subject(client, app):
         "/api/subjects",
         json=subject_payload(semester_id),
     )
+    expected = dict(created.json)
+    # 作成のレスポンスにだけ付ける付加情報は、1件取得には含めない。
+    del expected["generated_event_count"]
     assert client.get(f"/api/subjects/{created.json['id']}").json == (
-        created.json
+        expected
     )
 
 
@@ -837,3 +875,174 @@ def test_invalid_bytes_in_semester_id_query_are_validation_error(client):
         response,
         {"semester_id": "学期IDは整数で指定してください"},
     )
+
+
+# --- 授業の登録による予定（Event）の自動生成（Task 011） ---
+
+
+def test_subject_creation_generates_events_with_subject_values(client, app):
+    semester_id = make_semester(app)
+    response = client.post(
+        "/api/subjects",
+        json=subject_payload(
+            semester_id,
+            subject_name="  プログラミング基礎　",
+            room="3号館201",
+            notes="前期の授業",
+        ),
+    )
+
+    assert response.status_code == 201
+    assert response.json["generated_event_count"] == 17
+    subject_id = response.json["id"]
+    with app.app_context():
+        events = db.session.scalars(
+            select(Event)
+            .where(Event.subject_id == subject_id)
+            .order_by(Event.date)
+        ).all()
+        assert len(events) == 17
+        assert events[0].date == date(2026, 4, 6)
+        assert events[-1].date == date(2026, 7, 27)
+        for event in events:
+            assert event.date.weekday() == 0
+            assert event.category == "class"
+            assert event.start_time == time(9, 0)
+            assert event.end_time == time(10, 0)
+            assert event.title == "プログラミング基礎"
+            assert event.room == "3号館201"
+            assert event.employer is None
+            assert event.notes == "前期の授業"
+            assert event.is_generated is True
+
+
+def test_subject_creation_skips_closures_of_its_semester_only(client, app):
+    semester_id = make_semester(app)
+    other_semester_id = make_semester(app, name="2026年度 後期")
+    make_closure(app, semester_id, date(2026, 5, 4))
+    make_closure(app, semester_id, date(2026, 7, 20))
+    # ほかの学期の休講日は、この学期の授業の予定に影響しない。
+    make_closure(app, other_semester_id, date(2026, 4, 13))
+
+    response = client.post(
+        "/api/subjects",
+        json=subject_payload(semester_id),
+    )
+
+    assert response.status_code == 201
+    assert response.json["generated_event_count"] == 15
+    dates = generated_event_dates(app, response.json["id"])
+    assert len(dates) == 15
+    assert date(2026, 5, 4) not in dates
+    assert date(2026, 7, 20) not in dates
+    assert date(2026, 4, 13) in dates
+
+
+def test_subject_creation_without_matching_days_returns_zero(client, app):
+    with app.app_context():
+        # 2026-04-01（水）〜2026-04-02（木）の学期に、月曜日はない。
+        semester = Semester(
+            name="2026年度 前期",
+            start_date=date(2026, 4, 1),
+            end_date=date(2026, 4, 2),
+        )
+        db.session.add(semester)
+        db.session.commit()
+        semester_id = semester.id
+
+    response = client.post(
+        "/api/subjects",
+        json=subject_payload(semester_id, weekday=0),
+    )
+
+    assert response.status_code == 201
+    assert response.json["generated_event_count"] == 0
+    assert subject_count(app) == 1
+    assert event_count(app) == 0
+
+
+def test_subject_creation_when_all_days_are_closures_returns_zero(
+    client, app
+):
+    with app.app_context():
+        # 2026-04-06（月）〜2026-04-12（日）の月曜日は、4/6の1日だけ。
+        semester = Semester(
+            name="2026年度 前期",
+            start_date=date(2026, 4, 6),
+            end_date=date(2026, 4, 12),
+        )
+        db.session.add(semester)
+        db.session.commit()
+        semester_id = semester.id
+    make_closure(app, semester_id, date(2026, 4, 6))
+
+    response = client.post(
+        "/api/subjects",
+        json=subject_payload(semester_id, weekday=0),
+    )
+
+    assert response.status_code == 201
+    assert response.json["generated_event_count"] == 0
+    assert event_count(app) == 0
+
+
+def test_generated_event_count_is_not_in_subject_list(client, app):
+    semester_id = make_semester(app)
+    client.post("/api/subjects", json=subject_payload(semester_id))
+
+    response = client.get("/api/subjects")
+
+    assert response.status_code == 200
+    assert len(response.json) == 1
+    assert "generated_event_count" not in response.json[0]
+
+
+def test_generated_event_count_in_request_is_rejected(client, app):
+    semester_id = make_semester(app)
+
+    response = client.post(
+        "/api/subjects",
+        json=subject_payload(semester_id, generated_event_count=17),
+    )
+
+    assert_validation_error(
+        response,
+        {"generated_event_count": "この項目は指定できません"},
+    )
+    assert subject_count(app) == 0
+    assert event_count(app) == 0
+
+
+def test_failed_subject_post_creates_no_events(client, app):
+    semester_id = make_semester(app)
+
+    response = client.post(
+        "/api/subjects",
+        json=subject_payload(semester_id, weekday=9),
+    )
+
+    assert response.status_code == 400
+    assert event_count(app) == 0
+
+
+def test_event_generation_failure_saves_neither_subject_nor_events(
+    client, app, monkeypatch
+):
+    semester_id = make_semester(app)
+
+    def fail(*args, **kwargs):
+        raise RuntimeError("intentional test failure")
+
+    # routeのモジュールが取り込んだ名前を置き換える。
+    monkeypatch.setattr("app.routes.subjects.build_class_events", fail)
+    app.config["PROPAGATE_EXCEPTIONS"] = False
+
+    response = client.post(
+        "/api/subjects",
+        json=subject_payload(semester_id),
+    )
+
+    assert response.status_code == 500
+    assert response.json["error"]["code"] == "server_error"
+    assert subject_count(app) == 0
+    assert event_count(app) == 0
```

段階2の終わりに、`python -m pytest -q` が **421件、すべて合格**すること（`tests/test_closures_api.py` の途中の段階のテスト2件も、この時点では合格する。休講日のAPIは、まだ変えていないため）。

## 段階3：休講日の追加・削除で、予定を同期する

### 3-1. `app/routes/closures.py`
次の差分のとおりに変える。

1. `import` に、`date`（`datetime`）、`build_class_event`（`app.class_events`）、`Event`、`Subject` を足す
2. `closure_to_dict` の次に、2つの関数を足す。どちらも、`commit` をしない（routeの中で、1回だけ `commit` する）
   - `delete_generated_class_events(semester_id, event_date)`：その学期の授業の、その日付の**自動生成の予定**（`is_generated=True`）を削除する。単発の予定は削除しない
   - `build_missing_class_events(semester_id, event_date)`：その学期の授業のうち、`weekday` がその日付の曜日と同じで、その日付の**自動生成の予定がない**授業の分だけ、`build_class_event` で予定を作って返す（セッションには追加しない）。単発の予定の有無は見ない
3. 登録（`create_closure`）：休講日を `add` → `delete_generated_class_events` → 1回の `commit`
4. 削除（`delete_closure`）：休講日の学期と日付を控える → 休講日を `delete` → `build_missing_class_events` → `add_all` → 1回の `commit`
   - この順序（休講日の追加・削除を先に行い、そのあとで予定を消す・作る）は変えない。例外のテスト（3-2）が、途中で例外が起きたときに、どちらも保存されないことを確かめるため

```diff
--- a/app/routes/closures.py
+++ b/app/routes/closures.py
@@ -1,3 +1,4 @@
+from datetime import date
 from typing import Any
 
 from flask import Blueprint, jsonify
@@ -13,9 +14,12 @@ from app.api_helpers import (
     validate_required_date,
     validate_required_integer,
 )
+from app.class_events import build_class_event
 from app.extensions import db
 from app.models.closure import Closure
+from app.models.event import Event
 from app.models.semester import Semester
+from app.models.subject import Subject
 
 
 closures_bp = Blueprint(
@@ -35,6 +39,57 @@ def closure_to_dict(closure: Closure) -> dict[str, Any]:
     }
 
 
+def delete_generated_class_events(semester_id: int, event_date: date) -> None:
+    """学期の授業の、その日付の自動生成の予定を削除する（commitしない）。
+
+    休講日の追加で使う。単発の予定（is_generated=False）は削除しない。
+    """
+    semester_subject_ids = db.select(Subject.id).where(
+        Subject.semester_id == semester_id
+    )
+    db.session.execute(
+        db.delete(Event).where(
+            Event.subject_id.in_(semester_subject_ids),
+            Event.date == event_date,
+            Event.is_generated.is_(True),
+        )
+    )
+
+
+def build_missing_class_events(
+    semester_id: int,
+    event_date: date,
+) -> list[Event]:
+    """その日付の自動生成の予定がない授業の分だけ、予定を作る（追加しない）。
+
+    休講日の削除で使う。対象は、学期の授業のうち、曜日がその日付の曜日と
+    同じ授業。同じ授業・同じ日付の自動生成の予定を2件にしないため、
+    すでにある授業は除く。単発の予定（is_generated=False）の有無は見ない。
+    """
+    subjects = db.session.scalars(
+        db.select(Subject)
+        .where(
+            Subject.semester_id == semester_id,
+            Subject.weekday == event_date.weekday(),
+        )
+        .order_by(Subject.id.asc())
+    ).all()
+    subject_ids_with_event = set(
+        db.session.scalars(
+            db.select(Event.subject_id).where(
+                Event.subject_id.in_([subject.id for subject in subjects]),
+                Event.date == event_date,
+                Event.is_generated.is_(True),
+            )
+        )
+    )
+    return [
+        build_class_event(subject, event_date)
+        for subject in subjects
+        if subject.id not in subject_ids_with_event
+    ]
+
+
 @closures_bp.get("")
 def get_closures():
     specified, semester_id, query_error = read_id_query(
@@ -135,6 +190,9 @@ def create_closure():
         name=name,
     )
     db.session.add(closure)
+    # 休講日には授業の予定を作らないため、その日の自動生成の予定を消す。
+    delete_generated_class_events(semester_id, closure_date)
+    # 休講日の追加と予定の削除を、1回のcommitで保存する。
     db.session.commit()
     return jsonify(closure_to_dict(closure)), 201
 
@@ -145,6 +203,13 @@ def delete_closure(closure_id: int):
     if closure is None:
         return api_error_response("not_found", "休講日が見つかりません")
 
+    semester_id = closure.semester_id
+    closure_date = closure.date
     db.session.delete(closure)
+    # 休講日でなくなった日に、その曜日の授業の自動生成の予定を作る。
+    events = build_missing_class_events(semester_id, closure_date)
+    # 予定は、明示的に追加する（授業との関係だけでは、セッションに入らない）。
+    db.session.add_all(events)
+    # 休講日の削除と予定の作成を、1回のcommitで保存する。
     db.session.commit()
     return "", 204
```

### 3-2. `tests/test_closures_api.py`
次の差分のとおりに変える。

- `import` に `from app.routes import closures as closures_routes` を足す（例外のテストで、routeのモジュールの関数を置き換えるため）。`from app.models.subject import Subject` を消す（使わなくなるため）
- `make_friday_subject`（`main` の47〜59行目）を消す（途中の段階のテストだけが使っていたため）
- 途中の段階のテスト2件（`main` の603〜650行目、`test_closure_creation_does_not_change_events_before_sync`・`test_closure_deletion_does_not_create_events_before_sync`）を消し、ファイルの末尾を、新しい補助関数とテスト12件（`# --- 休講日の追加・削除と、予定（Event）の同期（Task 011） ---` から下）に置き換える

```diff
--- a/tests/test_closures_api.py
+++ b/tests/test_closures_api.py
@@ -3,6 +3,7 @@ from datetime import date, time
 import pytest
 from sqlalchemy import func, select
 
+from app.routes import closures as closures_routes
 from app.api_helpers import (
     INVALID_JSON_MESSAGE,
     MAX_ID,
@@ -12,7 +13,6 @@ from app.extensions import db
 from app.models.closure import Closure
 from app.models.event import Event
 from app.models.semester import Semester
-from app.models.subject import Subject
 
 
 DATE_FORMAT_MESSAGE = (
@@ -44,20 +44,6 @@ def make_closure(app, semester_id, closure_date, name=None):
         return closure.id
 
 
-def make_friday_subject(app, semester_id):
-    with app.app_context():
-        subject = Subject(
-            semester_id=semester_id,
-            subject_name="金曜の授業",
-            weekday=4,
-            start_time=time(9, 0),
-            end_time=time(10, 0),
-        )
-        db.session.add(subject)
-        db.session.commit()
-        return subject.id
-
-
 def closure_payload(default_semester_id, **overrides):
     payload = {
         "semester_id": default_semester_id,
@@ -600,51 +586,303 @@ def test_unsupported_closure_methods_do_not_change_rows(
     assert client.get("/api/closures").json == before.json
 
 
-def test_closure_creation_does_not_change_events_before_sync(client, app):
-    semester_id = make_semester(app)
-    subject_id = make_friday_subject(app, semester_id)
+# --- 休講日の追加・削除と、予定（Event）の同期（Task 011） ---
+# 学期は 2026-04-01（水）〜2026-07-31（金）。休講日は、金曜日の 2026-05-15。
+
+CLOSURE_DATE = date(2026, 5, 15)
+
+
+def post_subject(client, semester_id, weekday, subject_name="授業"):
+    """APIで授業を登録する（学期の期間の予定が、自動で作られる）。"""
+    response = client.post(
+        "/api/subjects",
+        json={
+            "semester_id": semester_id,
+            "subject_name": subject_name,
+            "weekday": weekday,
+            "start_time": "09:00",
+            "end_time": "10:00",
+        },
+    )
+    assert response.status_code == 201
+    return response.json["id"]
+
+
+def post_closure(client, semester_id, closure_date="2026-05-15"):
+    response = client.post(
+        "/api/closures",
+        json=closure_payload(semester_id, date=closure_date),
+    )
+    assert response.status_code == 201
+    return response.json["id"]
+
+
+def add_single_event(app, subject_id, event_date):
+    """カレンダーから追加した単発の予定（is_generated=False）の代わり。"""
     with app.app_context():
-        db.session.add_all(
-            [
-                Event(
-                    subject_id=subject_id,
-                    category="class",
-                    date=date(2026, 5, 15),
-                    start_time=time(9, 0),
-                    end_time=time(10, 0),
-                    title="金曜の授業",
-                    is_generated=True,
-                ),
-                Event(
-                    subject_id=subject_id,
-                    category="class",
-                    date=date(2026, 5, 15),
-                    start_time=time(10, 0),
-                    end_time=time(11, 0),
-                    title="単発の授業",
-                    is_generated=False,
-                ),
-            ]
+        db.session.add(
+            Event(
+                subject_id=subject_id,
+                category="class",
+                date=event_date,
+                start_time=time(13, 0),
+                end_time=time(14, 0),
+                title="補講",
+                is_generated=False,
+            )
         )
         db.session.commit()
 
-    # Eventの同期を入れる前の段階では、休講日の登録で予定を変えない。
+
+def events_on(app, subject_id, event_date, is_generated):
+    with app.app_context():
+        return db.session.scalar(
+            select(func.count())
+            .select_from(Event)
+            .where(
+                Event.subject_id == subject_id,
+                Event.date == event_date,
+                Event.is_generated.is_(is_generated),
+            )
+        )
+
+
+def generated_event_count(app, subject_id):
+    with app.app_context():
+        return db.session.scalar(
+            select(func.count())
+            .select_from(Event)
+            .where(
+                Event.subject_id == subject_id,
+                Event.is_generated.is_(True),
+            )
+        )
+
+
+def event_snapshot(app):
+    """予定の行を、idを除いて、並べた一覧にする（作り直しの比較用）。"""
+    with app.app_context():
+        events = db.session.scalars(select(Event)).all()
+        return sorted(
+            (
+                event.subject_id,
+                event.date,
+                event.start_time,
+                event.end_time,
+                event.title,
+                event.is_generated,
+            )
+            for event in events
+        )
+
+
+def test_closure_creation_deletes_generated_events_on_that_date(
+    client, app
+):
+    semester_id = make_semester(app)
+    friday_ids = [
+        post_subject(client, semester_id, 4, "金曜1限"),
+        post_subject(client, semester_id, 4, "金曜2限"),
+    ]
+    monday_id = post_subject(client, semester_id, 0, "月曜1限")
+
+    post_closure(client, semester_id)
+
+    for subject_id in friday_ids:
+        assert events_on(app, subject_id, CLOSURE_DATE, True) == 0
+        assert generated_event_count(app, subject_id) == 17
+    assert generated_event_count(app, monday_id) == 17
+
+
+def test_closure_creation_keeps_single_events(client, app):
+    semester_id = make_semester(app)
+    subject_id = post_subject(client, semester_id, 4)
+    add_single_event(app, subject_id, CLOSURE_DATE)
+
+    post_closure(client, semester_id)
+
+    assert events_on(app, subject_id, CLOSURE_DATE, True) == 0
+    assert events_on(app, subject_id, CLOSURE_DATE, False) == 1
+
+
+def test_closure_creation_keeps_events_of_other_semesters(client, app):
+    semester_id = make_semester(app)
+    other_semester_id = make_semester(app, name="2026年度 後期")
+    other_subject_id = post_subject(client, other_semester_id, 4)
+
+    post_closure(client, semester_id)
+
+    assert events_on(app, other_subject_id, CLOSURE_DATE, True) == 1
+    assert generated_event_count(app, other_subject_id) == 18
+
+
+def test_closure_deletion_creates_events_for_subjects_of_that_weekday(
+    client, app
+):
+    semester_id = make_semester(app)
+    closure_id = post_closure(client, semester_id)
+    friday_ids = [
+        post_subject(client, semester_id, 4, "金曜1限"),
+        post_subject(client, semester_id, 4, "金曜2限"),
+    ]
+    monday_id = post_subject(client, semester_id, 0, "月曜1限")
+
+    response = client.delete(f"/api/closures/{closure_id}")
+
+    assert response.status_code == 204
+    for subject_id in friday_ids:
+        assert events_on(app, subject_id, CLOSURE_DATE, True) == 1
+        assert generated_event_count(app, subject_id) == 18
+    assert generated_event_count(app, monday_id) == 17
+
+
+def test_event_created_by_closure_deletion_has_subject_values(client, app):
+    semester_id = make_semester(app)
+    closure_id = post_closure(client, semester_id)
+    response = client.post(
+        "/api/subjects",
+        json={
+            "semester_id": semester_id,
+            "subject_name": "金曜1限",
+            "room": "3号館201",
+            "weekday": 4,
+            "start_time": "09:15",
+            "end_time": "10:45",
+            "notes": "メモ",
+        },
+    )
+    subject_id = response.json["id"]
+
+    client.delete(f"/api/closures/{closure_id}")
+
+    with app.app_context():
+        event = db.session.scalars(
+            select(Event).where(
+                Event.subject_id == subject_id,
+                Event.date == CLOSURE_DATE,
+            )
+        ).one()
+        assert event.category == "class"
+        assert event.start_time == time(9, 15)
+        assert event.end_time == time(10, 45)
+        assert event.title == "金曜1限"
+        assert event.room == "3号館201"
+        assert event.employer is None
+        assert event.notes == "メモ"
+        assert event.is_generated is True
+
+
+def test_closure_deletion_creates_event_even_with_single_event(client, app):
+    semester_id = make_semester(app)
+    closure_id = post_closure(client, semester_id)
+    subject_id = post_subject(client, semester_id, 4)
+    add_single_event(app, subject_id, CLOSURE_DATE)
+
+    client.delete(f"/api/closures/{closure_id}")
+
+    # 単発の予定の有無は見ないため、自動生成の予定が作られ、両方が並ぶ。
+    assert events_on(app, subject_id, CLOSURE_DATE, True) == 1
+    assert events_on(app, subject_id, CLOSURE_DATE, False) == 1
+
+
+def test_closure_deletion_does_not_duplicate_generated_events(client, app):
+    semester_id = make_semester(app)
+    subject_id = post_subject(client, semester_id, 4)
+    # APIを通さずに休講日を作り、その日の自動生成の予定が残った状態にする。
+    closure_id = make_closure(app, semester_id, CLOSURE_DATE)
+
+    client.delete(f"/api/closures/{closure_id}")
+
+    assert events_on(app, subject_id, CLOSURE_DATE, True) == 1
+    assert generated_event_count(app, subject_id) == 18
+
+
+def test_closure_deletion_skips_other_weekdays_and_other_semesters(
+    client, app
+):
+    semester_id = make_semester(app)
+    other_semester_id = make_semester(app, name="2026年度 後期")
+    closure_id = post_closure(client, semester_id)
+    monday_id = post_subject(client, semester_id, 0)
+    # 曜日が違う授業は、同じ日付に単発の予定があっても、予定を作らない。
+    add_single_event(app, monday_id, CLOSURE_DATE)
+    other_subject_id = post_subject(client, other_semester_id, 4)
+
+    client.delete(f"/api/closures/{closure_id}")
+
+    assert events_on(app, monday_id, CLOSURE_DATE, True) == 0
+    assert events_on(app, other_subject_id, CLOSURE_DATE, True) == 1
+
+
+def test_closure_creation_then_deletion_restores_events(client, app):
+    semester_id = make_semester(app)
+    friday_id = post_subject(client, semester_id, 4)
+    add_single_event(app, friday_id, CLOSURE_DATE)
+    post_subject(client, semester_id, 0)
+    before = event_snapshot(app)
+
+    closure_id = post_closure(client, semester_id)
+    assert event_snapshot(app) != before
+    client.delete(f"/api/closures/{closure_id}")
+
+    assert event_snapshot(app) == before
+
+
+def test_closure_on_day_without_subjects_changes_no_events(client, app):
+    semester_id = make_semester(app)
+    post_subject(client, semester_id, 4)
+    post_subject(client, semester_id, 0)
+    before = event_snapshot(app)
+
+    # 2026-05-16 は土曜日で、その曜日の授業はない。
+    closure_id = post_closure(client, semester_id, "2026-05-16")
+    assert event_snapshot(app) == before
+    client.delete(f"/api/closures/{closure_id}")
+
+    assert event_snapshot(app) == before
+
+
+def test_closure_creation_failure_saves_nothing(client, app, monkeypatch):
+    semester_id = make_semester(app)
+    subject_id = post_subject(client, semester_id, 4)
+    real_delete = closures_routes.delete_generated_class_events
+
+    def delete_then_fail(*args, **kwargs):
+        # 予定を消したあとで、commitの前に例外を起こす。
+        real_delete(*args, **kwargs)
+        raise RuntimeError("intentional test failure")
+
+    monkeypatch.setattr(
+        closures_routes, "delete_generated_class_events", delete_then_fail
+    )
+    app.config["PROPAGATE_EXCEPTIONS"] = False
+
     response = client.post(
         "/api/closures",
         json=closure_payload(semester_id),
     )
 
-    assert response.status_code == 201
-    assert event_count(app) == 2
+    assert response.status_code == 500
+    assert response.json["error"]["code"] == "server_error"
+    assert closure_count(app) == 0
+    assert events_on(app, subject_id, CLOSURE_DATE, True) == 1
 
 
-def test_closure_deletion_does_not_create_events_before_sync(client, app):
+def test_closure_deletion_failure_saves_nothing(client, app, monkeypatch):
     semester_id = make_semester(app)
-    make_friday_subject(app, semester_id)
-    closure_id = make_closure(app, semester_id, date(2026, 5, 15))
+    closure_id = post_closure(client, semester_id)
+    subject_id = post_subject(client, semester_id, 4)
+
+    def fail(*args, **kwargs):
+        raise RuntimeError("intentional test failure")
+
+    # routeのモジュールが取り込んだ名前を置き換える。
+    monkeypatch.setattr(closures_routes, "build_class_event", fail)
+    app.config["PROPAGATE_EXCEPTIONS"] = False
 
-    # Eventの同期を入れる前の段階では、休講日の削除で予定を作らない。
     response = client.delete(f"/api/closures/{closure_id}")
 
-    assert response.status_code == 204
-    assert event_count(app) == 0
+    assert response.status_code == 500
+    assert response.json["error"]["code"] == "server_error"
+    assert closure_count(app) == 1
+    assert events_on(app, subject_id, CLOSURE_DATE, True) == 0
```

段階3の終わりに、`python -m pytest -q` が **431件、すべて合格**すること。

### 3-3. テストで確かめること（段階2・3の対応表）
`docs/architecture.md` の「自動テスト（pytest）」の「テストの書き方」と、「休講日の変更と予定の同期」の規則との対応。

| 規則 | テスト |
|---|---|
| 授業の登録：`generated_event_count` と、自動生成の予定の行数が一致する。各予定の値 | `test_subject_creation_generates_events_with_subject_values` |
| 授業の登録：休講日（その学期のものだけ）の日には作らない | `test_subject_creation_skips_closures_of_its_semester_only` |
| 該当する日がない（期間にその曜日がない／すべて休講日）：201で0件 | `test_subject_creation_without_matching_days_returns_zero`・`test_subject_creation_when_all_days_are_closures_returns_zero` |
| `generated_event_count` は、作成のレスポンスにだけ含め、リクエストでは受け付けない | `test_generated_event_count_is_not_in_subject_list`・`test_generated_event_count_in_request_is_rejected`・`test_subject_get_returns_created_subject` |
| 授業の登録の途中の例外で、授業も予定も保存しない | `test_event_generation_failure_saves_neither_subject_nor_events` |
| 休講日の追加：その学期の授業の、その日の自動生成の予定を消す。単発の予定と、ほかの学期の予定は変えない | `test_closure_creation_deletes_generated_events_on_that_date`・`test_closure_creation_keeps_single_events`・`test_closure_creation_keeps_events_of_other_semesters` |
| 休講日の削除：その曜日の授業に、授業の今の値で1件ずつ作る。単発の予定があっても作る。曜日の違う授業・ほかの学期には作らない。2件にしない | `test_closure_deletion_creates_events_for_subjects_of_that_weekday`・`test_event_created_by_closure_deletion_has_subject_values`・`test_closure_deletion_creates_event_even_with_single_event`・`test_closure_deletion_skips_other_weekdays_and_other_semesters`・`test_closure_deletion_does_not_duplicate_generated_events` |
| 追加と削除は逆の操作。授業のない曜日の休講日は、予定を変えない | `test_closure_creation_then_deletion_restores_events`・`test_closure_on_day_without_subjects_changes_no_events` |
| 休講日の追加・削除の途中の例外で、どちらも保存しない（1回のcommit） | `test_closure_creation_failure_saves_nothing`・`test_closure_deletion_failure_saves_nothing` |

これらのテストが、実装の誤りを見つけられることは、作業用のコピーで、実装をわざと9通りに壊して確かめた（commitを先に行う、`add_all` を外す、単発の予定も消す、曜日やほかの学期で絞らない、二重に作る、休講日を無視する。どれも、いずれかのテストが失敗した）。

## 段階4：画面（授業の登録の成功メッセージと、006-L1〜L5）

### 4-1. `app/static/js/subjects.js`
- 成功メッセージ：`docs/ui_ux.md` の「登録済みのメッセージ」のとおり、`generated_event_count` が1以上なら「「科目名」を登録しました（予定N件を作成）」、0なら「「科目名」を登録しました（学期の期間内に、この曜日の授業日がないため、予定は作成されませんでした）」。文言を作る関数 `subjectCreatedMessage(created)` を足す
- 006-L1：`submitSubject` の `try` を、登録の要求（`apiRequest`）だけに絞る。成功後の処理（メッセージ、入力欄を戻す、フォーカス、一覧の取得し直し）は、`try` の外に書く
- 006-L2：`resetSubjectForm(clearSuccess = true)` を `resetSubjectForm({ clearSuccess = true } = {})` に、`loadSubjects(showLoading = true)` を `loadSubjects({ showLoading = true } = {})` に変え、呼び出しを `resetSubjectForm({ clearSuccess: false })`・`loadSubjects({ showLoading: false })` にする（引数なしの呼び出しは、そのまま）

```diff
--- a/app/static/js/subjects.js
+++ b/app/static/js/subjects.js
@@ -47,7 +47,7 @@ const SUBJECT_SUBMIT_LABELS = {
   busy: "登録中…",
 };
 
-function resetSubjectForm(clearSuccess = true) {
+function resetSubjectForm({ clearSuccess = true } = {}) {
   getElement("subject-form").reset();
   getElement("subject-name").value = "";
   getElement("subject-room").value = "";
@@ -159,7 +159,7 @@ function renderSubjects(subjects) {
   setVisible(getElement("subject-list"), subjects.length > 0);
 }
 
-async function loadSubjects(showLoading = true) {
+async function loadSubjects({ showLoading = true } = {}) {
   if (currentSemester === null) {
     clearSubjectList();
     return;
@@ -189,6 +189,18 @@ async function loadSubjects(showLoading = true) {
   }
 }
 
+// 登録済みのメッセージ。作成された予定の件数によって、文言を変える。
+function subjectCreatedMessage(created) {
+  const registered = `「${created.subject_name}」を登録しました`;
+  if (created.generated_event_count === 0) {
+    return (
+      `${registered}（学期の期間内に、この曜日の授業日がないため、` +
+      "予定は作成されませんでした）"
+    );
+  }
+  return `${registered}（予定${created.generated_event_count}件を作成）`;
+}
+
 async function submitSubject(event) {
   event.preventDefault();
   clearFormErrors(SUBJECT_FIELDS, "subject-form-error");
@@ -199,8 +211,11 @@ async function submitSubject(event) {
   const submitButton = getElement("subject-submit-button");
   setSubmitting(submitButton, true, SUBJECT_SUBMIT_LABELS);
 
+  // try で囲むのは、登録の要求だけにする。登録の成功後の処理で例外が
+  // 起きた場合に、「登録の失敗」として表示しないため。
+  let created;
   try {
-    const created = await apiRequest("POST", "/api/subjects", {
+    created = await apiRequest("POST", "/api/subjects", {
       semester_id: currentSemester.id,
       subject_name: getElement("subject-name").value,
       room: getElement("subject-room").value,
@@ -209,16 +224,17 @@ async function submitSubject(event) {
       end_time: getElement("subject-end-time").value,
       notes: getElement("subject-notes").value,
     });
-
-    success.textContent = `「${created.subject_name}」を登録しました`;
-    setVisible(success, true);
-    resetSubjectForm(false);
-    getElement("subject-name").focus();
-    await loadSubjects(false);
   } catch (error) {
     showApiError(error, SUBJECT_FIELDS, "subject-form-error");
     setSubmitting(submitButton, false, SUBJECT_SUBMIT_LABELS);
+    return;
   }
+
+  success.textContent = subjectCreatedMessage(created);
+  setVisible(success, true);
+  resetSubjectForm({ clearSuccess: false });
+  getElement("subject-name").focus();
+  await loadSubjects({ showLoading: false });
 }
 
 export function initSubjects() {
```

### 4-2. `app/static/js/closures.js`（006-L1・L2と同じ形）
- `loadClosures(showLoading = true)` を、`loadClosures({ showLoading = true } = {})` にし、呼び出しを `loadClosures({ showLoading: false })` にする
- `submitClosure`・`deleteClosure` の `try` を、要求だけに絞る。学期の切り替えの確認（`startedSelection !== selectionSerial`）は、失敗のとき（`catch` の中）と、成功のとき（`try` のあと）の両方に残す（Task 010の規則：応答が届いたときに選択が変わっていれば、画面を変えない）

```diff
--- a/app/static/js/closures.js
+++ b/app/static/js/closures.js
@@ -122,7 +122,7 @@ function renderClosures(closures) {
   setVisible(list, closures.length > 0);
 }
 
-async function loadClosures(showLoading = true) {
+async function loadClosures({ showLoading = true } = {}) {
   if (currentSemester === null) {
     clearClosureList();
     return;
@@ -161,25 +161,29 @@ async function submitClosure(event) {
   const submitButton = getElement("closure-submit-button");
   setSubmitting(submitButton, true, CLOSURE_SUBMIT_LABELS);
 
+  // try で囲むのは、追加の要求だけにする（成功後の処理の例外を、
+  // 「追加の失敗」として表示しないため）。
   try {
     await apiRequest("POST", "/api/closures", {
       semester_id: currentSemester.id,
       date: getElement("closure-date").value,
       name: getElement("closure-name").value,
     });
-    if (startedSelection !== selectionSerial) {
-      return;
-    }
-    resetClosureForm();
-    getElement("closure-date").focus();
-    await loadClosures(false);
   } catch (error) {
     if (startedSelection !== selectionSerial) {
       return;
     }
     showApiError(error, CLOSURE_FIELDS, CLOSURE_FORM_ERROR_ID);
     setSubmitting(submitButton, false, CLOSURE_SUBMIT_LABELS);
+    return;
+  }
+
+  if (startedSelection !== selectionSerial) {
+    return;
   }
+  resetClosureForm();
+  getElement("closure-date").focus();
+  await loadClosures({ showLoading: false });
 }
 
 async function deleteClosure(closureId, button) {
@@ -188,19 +192,22 @@ async function deleteClosure(closureId, button) {
   clearClosureErrors();
   setSubmitting(button, true, CLOSURE_DELETE_LABELS);
 
+  // try で囲むのは、削除の要求だけにする（追加と同じ理由）。
   try {
     await apiRequest("DELETE", `/api/closures/${closureId}`);
-    if (startedSelection !== selectionSerial) {
-      return;
-    }
-    await loadClosures(false);
   } catch (error) {
     if (startedSelection !== selectionSerial) {
       return;
     }
     showApiError(error, CLOSURE_FIELDS, CLOSURE_FORM_ERROR_ID);
     setSubmitting(button, false, CLOSURE_DELETE_LABELS);
+    return;
+  }
+
+  if (startedSelection !== selectionSerial) {
+    return;
   }
+  await loadClosures({ showLoading: false });
 }
 
 export function initClosures() {
```

### 4-3. `app/static/js/semesters.js`
- 006-L4：`renderTabs()` の最後の `updateTabSelection();`（`main` の120行目）を消す。`renderTabs()` を呼ぶのは `loadSemesters()` だけで、その直後の `selectSemester()` が、必ず `updateTabSelection()` を呼ぶため（`main` の164行目。こちらは消さない）
- 006-L1と同じ形：`submitSemester` の `try` を、登録の要求だけに絞る（`closeSemesterModal()` と `loadSemesters(created.id)` を、`try` の外に出す）

```diff
--- a/app/static/js/semesters.js
+++ b/app/static/js/semesters.js
@@ -117,7 +117,6 @@ function renderTabs() {
   }
 
   tabs.replaceChildren(fragment);
-  updateTabSelection();
 }
 
 function updateTabSelection() {
@@ -269,18 +268,23 @@ async function submitSemester(event) {
   const startDate = getElement("semester-start-date").value;
   const endDate = getElement("semester-end-date").value;
 
+  // try で囲むのは、登録の要求だけにする（成功後の処理の例外を、
+  // 「登録の失敗」として表示しないため）。
+  let created;
   try {
-    const created = await apiRequest("POST", "/api/semesters", {
+    created = await apiRequest("POST", "/api/semesters", {
       name,
       start_date: startDate,
       end_date: endDate,
     });
-    closeSemesterModal();
-    await loadSemesters(created.id);
   } catch (error) {
     showApiError(error, SEMESTER_FIELDS, SEMESTER_FORM_ERROR_ID);
     setSubmitting(submitButton, false, SEMESTER_SUBMIT_LABELS);
+    return;
   }
+
+  closeSemesterModal();
+  await loadSemesters(created.id);
 }
 
 export function initSemesters() {
```

### 4-4. `app/static/js/ui.js`
- 006-L3：ファイルの冒頭に、`fieldMap` の形のコメントを書き、公開する6つの関数の直前に、引数の形を、日本語で1〜2行で書く
- 006-L5：`getElement` は、要素が見つからない場合、`null` を返さず、`Error`（メッセージ「要素が見つかりません：<id>」）を投げる。今の画面で使うidは、すべて `index.html` にある（作業用のコピーで、`getElement`・`fieldMap`・定数のidを照合した）
- 公開する関数は、6つのまま（増やさない・名前を変えない）

```diff
--- a/app/static/js/ui.js
+++ b/app/static/js/ui.js
@@ -1,13 +1,26 @@
 import { ApiError } from "./api.js";
 
+// 複数のモードで使う、表示とフォームの共通処理。
+// fieldMap は { 項目名: { inputIds: [入力欄のid], messageId: エラー表示のid } }
+// の形（項目名は、APIの fields の項目名と同じ）。
+
+// idの要素を返す。見つからない場合は、idの書き間違いに気づけるように、
+// idを含むエラーを投げる（null を返すと、あとで分かりにくい例外になるため）。
 export function getElement(id) {
-  return document.getElementById(id);
+  const element = document.getElementById(id);
+  if (element === null) {
+    throw new Error(`要素が見つかりません：${id}`);
+  }
+  return element;
 }
 
+// visible が true なら表示し、false なら隠す（Bootstrapの d-none）。
 export function setVisible(element, visible) {
   element.classList.toggle("d-none", !visible);
 }
 
+// 画面に出すエラーメッセージを返す。ApiError でない例外は、
+// 固定のメッセージにし、詳細を console.error に出す。
 export function errorMessageOf(error) {
   if (error instanceof ApiError) {
     return error.message;
@@ -30,6 +43,7 @@ function showFormMessage(formErrorId, message) {
   setVisible(formError, true);
 }
 
+// fieldMap の項目のエラー表示と、フォームの上部のエラー（formErrorId）を消す。
 export function clearFormErrors(fieldMap, formErrorId) {
   for (const field of Object.values(fieldMap)) {
     getElement(field.messageId).replaceChildren();
@@ -43,6 +57,8 @@ export function clearFormErrors(fieldMap, formErrorId) {
   setVisible(formError, false);
 }
 
+// API のエラーを表示する。fields の項目は、fieldMap の項目の下に出し、
+// それ以外は、フォームの上部（formErrorId）に出す。
 export function showApiError(error, fieldMap, formErrorId) {
   clearFormErrors(fieldMap, formErrorId);
 
@@ -72,6 +88,7 @@ export function showApiError(error, fieldMap, formErrorId) {
   showFormMessage(formErrorId, errorMessageOf(error));
 }
 
+// 送信中の表示。labels は { idle: 通常の文字, busy: 送信中の文字 } の形。
 export function setSubmitting(button, submitting, labels) {
   button.disabled = submitting;
   button.textContent = submitting ? labels.busy : labels.idle;
```

### 4-5. 変わる挙動・変わらない挙動

| 場面 | 変更後 |
|---|---|
| 授業の登録の成功 | メッセージに「（予定N件を作成）」、または0件の文言が付く。入力欄が戻り、科目名にフォーカスが移ること、モーダルが開いたままであることは、変わらない |
| 授業・学期・休講日の登録・削除の失敗 | 変わらない（エラーの表示と、ボタンの戻り方） |
| 学期のタブ、初期の選択、バナー | 変わらない（006-L4は、表示の結果を変えない） |
| 休講日の追加・削除の画面 | 変わらない（予定の件数は、画面に出さない。`docs/ui_ux.md`） |
| 存在しないidで `getElement` を呼んだとき | `null` ではなく、「要素が見つかりません：<id>」のエラー（今の画面では起きない） |

## JavaScriptの共通の規則
`.github/copilot-instructions.md` の「コーディング方針（JavaScript）」と、`docs/architecture.md` の「JavaScriptの構成（ES modules）」の規則に従う（名前つきの `export`、`innerHTML` などの禁止、`textContent`、`fetch` は `api.js` の中だけ、日本語のコメント、など）。次の点を、特に守る。
- `try` で囲むのは、要求（`apiRequest`）だけ。成功後の処理は、`try` の外
- 意味が呼び出し側から読めない真偽値を、位置の引数で渡さない（`setVisible`・`setSubmitting` は、そのまま）
- JavaScriptの1行は、80文字以内

## 変更してよい既存のテスト

| ファイル | 変更してよいもの | それ以外 |
|---|---|---|
| `tests/test_subjects_api.py` | 次の4件の期待値（2-2の差分のとおり）：`test_subject_creation_returns_all_fields_and_matches_database`（応答に `"generated_event_count": 18`。水曜日の授業）、`test_subject_creation_with_required_fields_uses_null_optional_values`（項目の集合に `generated_event_count`）、`test_duplicate_subject_rows_are_allowed_and_do_not_create_events_or_tasks`（名前を `test_duplicate_subject_rows_are_allowed_and_each_get_events` に変え、予定が17件ずつ・合計34件・課題0件）、`test_subject_get_returns_created_subject`（1件取得は、作成の応答から `generated_event_count` を除いたものと一致）。`import` と補助関数の追加 | 変えない |
| `tests/test_closures_api.py` | 途中の段階のテスト2件と、それだけが使う `make_friday_subject`・`Subject` の `import` を消すこと。`import` と補助関数・テストの追加（3-2の差分のとおり） | 変えない |
| ほかの `tests/` のファイル | なし | 変えない |

- このタスクでの「既存のテスト」は、作業の開始時からあるすべてのテスト。**上の表にない既存のテストが、想定外に失敗した場合**は、テストの期待値や、ほかの仕様を直さない。原因を調べ、そこで実装を止めて、チャットで報告する

## 実装手順
1. ブランチ・作業ツリーの確認。設計資料が更新されていることを確認する（「Copilot確認手順」の1の `grep`）。更新されていなければ、何も変更せずに停止して報告する
2. 作業の前の状態を記録する：開発用DBの有無・ハッシュ・件数（「Copilot確認手順」の1）。`python -m pytest -q` が394件、すべて合格すること（合格しなければ、何も変更せずに停止して報告する）
3. **（段階1）** `app/class_events.py`（1-1）→ `tests/test_class_events.py`（1-2）。`python -m pytest -q` が413件、すべて合格すること。「Copilot確認手順」の3・4
4. **（段階2）** `app/routes/subjects.py`（2-1）→ `tests/test_subjects_api.py`（2-2）。`python -m pytest -q` が421件、すべて合格すること
5. **（段階3）** `app/routes/closures.py`（3-1）→ `tests/test_closures_api.py`（3-2）。`python -m pytest -q` が431件、すべて合格すること。「Copilot確認手順」の3・5
6. **（段階4）** `subjects.js`（4-1）→ `closures.js`（4-2）→ `semesters.js`（4-3）→ `ui.js`（4-4）。`python -m pytest -q` が431件、すべて合格すること。「Copilot確認手順」の3・6
7. 「Copilot確認手順」の7を実施する
8. 結果を報告して、応答を終える（ブラウザでの確認は、していないと明記する）

各段階の終わりに、`python -m pytest -q` の結果（件数・警告）を控えておく（最終報告に書く）。

## 完了条件
- `python -m pytest -q` が、段階1の終わりに **413件**、段階2の終わりに **421件**、段階3・段階4の終わりに **431件**、すべて合格する（失敗・エラー・スキップが0件）
- 変更したファイルが、「実装対象ファイル」の10個だけ
- 各ファイルが、1-1〜4-4のコードと差分のとおり
- `app/`・`tests/`・`run.py` のPythonのファイルに、79文字を超える行がなく、`app/static/js/` のファイルに、80文字を超える行がない
- 実施の前後で、開発用DB（`instance/app.db`）のハッシュと、`semesters`・`subjects`・`closures`・`events`・`tasks` の件数が同じ
- 「Komaの確認」が、期待どおり
- レビューで承認される

## Copilot確認手順
```
# 1. 実施前
git branch --show-current      # feature/011-class-event-generation
git status                     # 変更なし
grep -n "実装の経緯" docs/architecture.md                        # 1件
grep -n "最終的な仕様と、実装の途中の段階" docs/architecture.md   # 出力なし
grep -n "要素が見つかりません" docs/architecture.md               # 1件（ui.js の行）
grep -n "止まる場面の応答" .github/copilot-instructions.md        # 数件
ls -l instance/app.db          # 存在すること（なければ、何も変更せずに停止して報告する）
shasum -a 256 instance/app.db
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"
python -m pytest -q            # 394 passed

# 2. 各段階の終わり
python -m pytest -q            # 段階1：413 passed、段階2：421 passed、段階3・4：431 passed

# 3. 1行の長さ（段階1・3・4の終わり。出力がなければ合格。migrations/ は対象外）
python - <<'EOF'
from pathlib import Path
paths = [*Path("app").rglob("*.py"), *Path("tests").glob("*.py"), Path("run.py")]
for path in paths:
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, 1):
        if len(line) > 79:
            print(f"{path}:{number}: {len(line)}")
for path in sorted(Path("app/static/js").glob("*.js")):
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, 1):
        if len(line) > 80:
            print(f"{path}:{number}: {len(line)}")
EOF

# 4. 検索（段階1の終わり）
grep -rn '"class"' app/                                   # 2件：class_events.py の15行目（コメント）と16行目（EVENT_CATEGORY_CLASS）
grep -n "db\.\|import db" app/class_events.py             # 出力なし（DBを使わない）
python -m pytest -q --co tests/test_class_events.py | tail -1   # 19 tests collected

# 5. 検索（段階3の終わり）
grep -n "build_class_event" app/routes/*.py               # 4件：closures.py の import と呼び出し、subjects.py の import と呼び出し
grep -n "add_all" app/routes/*.py                         # 2件：closures.py と subjects.py に1件ずつ
grep -n "db.session.commit()" app/routes/subjects.py app/routes/closures.py   # 授業の登録に1件、休講日の登録と削除に1件ずつ（3件）
grep -rn "before_sync\|make_friday_subject" tests/         # 出力なし
python -m pytest -q --co tests/test_subjects_api.py | tail -1   # 147 tests collected
python -m pytest -q --co tests/test_closures_api.py | tail -1   # 97 tests collected

# 6. 検索（段階4の終わり）
grep -rnE "\((false|true)\)" app/static/js/                # 出力なし
grep -n "showLoading: false\|clearSuccess: false" app/static/js/*.js   # 4件：closures.js に2件、subjects.js に2件
grep -c "^export function" app/static/js/ui.js            # 6
grep -n "要素が見つかりません" app/static/js/ui.js          # 1件
grep -n "updateTabSelection();" app/static/js/semesters.js # 1件（selectSemester の中）
grep -n "generated_event_count" app/static/js/subjects.js  # 2件
grep -rnE "innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(|localStorage|sessionStorage|setTimeout|export default|\bvar " app/static/js/   # 出力なし
grep -rn "fetch(" app/static/js/                           # api.js の中の1件だけ
git diff --stat app/templates/ app/static/js/api.js app/static/js/dates.js app/static/js/main.js   # 出力なし

# 7. 実施後
shasum -a 256 instance/app.db  # 実施前と同じ
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"   # 実施前と同じ
git status                     # 変更：「実装対象ファイル」の10個だけ
git diff --stat
```

| 確認 | 期待する結果 |
|---|---|
| `python -m pytest -q` | 実施前394件、段階1の終わり413件、段階2の終わり421件、段階3・4の終わり431件が、すべて合格。失敗・エラー・スキップが0件。`migrations/env.py` の `DeprecationWarning` は、出ても構わない（報告する） |
| 1行の長さ | 出力なし |
| 検索 | 上のコメントのとおり（件数が違う場合は、その行を報告に書く） |
| 開発用DB | 実施の前後で、ハッシュと、5つのテーブルの件数が同じ |
| `git status` | 変更：`app/routes/subjects.py`、`app/routes/closures.py`、`tests/test_subjects_api.py`、`tests/test_closures_api.py`、`app/static/js/subjects.js`、`app/static/js/closures.js`、`app/static/js/semesters.js`、`app/static/js/ui.js`。新規：`app/class_events.py`、`tests/test_class_events.py`。`app/models/`・`migrations/`・`app/templates/`・`docs/`・`.github/`・`requirements.txt`・`run.py`・`instance/` に変更なし |

`.pytest_cache/` や `__pycache__/` が `git status` に表示される場合は、`.gitignore` を変更せず、報告する。**Copilotは、サーバーを起動せず、ブラウザでの確認もしない。** 報告に、ブラウザで確認していないことを明記する。

## Komaの確認
順序：（1）pytest →（2）commit・push とレビューの依頼 →（3）ブラウザでの確認（確認用のサーバー）→（4）開発用DBの確認（予定の自動生成を入れたコードを、開発用DBで初めて動かす）→（5）マージ。

### 1. pytest
`python -m pytest -q` を自分で実行し、**431件、すべて合格**することを確かめる。

### 2. push とレビューの依頼
featureブランチを commit・push する（PRを作ってもよい）。Copilotの完了報告を共有して、Claudeにレビューを頼む。**pushは、マージではない。レビューの承認の前に、マージしない。** 修正が必要になった場合は、同じブランチでCopilotが直し、もう一度pushしてレビューを受ける。

### 3. ブラウザでの確認（確認用のサーバー）
レビューで「承認可能」になったあとに行う。**ブラウザの操作は、Claudeが、ブラウザのパネルまたはChromeで行う。Komaは、サーバーの起動・停止、`sqlite3` での確認用のDBの読み取り（K1〜K3）、DBのハッシュの確認、後片付けを行う**（roadmap の「進め方の決定の記録」、2026-10-12）。

#### 確認の安全のしくみ
- **開発用DBは使わない。** 確認用のDB（`/tmp/schedule-app-check-011/check.db`）を、migrationで作り、そのDBで起動した確認用のサーバーで確かめる（Task 010と同じ方法）。開発用DBには、何も残らない
- 予定（Event）を表示する画面は、まだない。予定の件数は、確認用のDBを `sqlite3 -readonly`（読み取りだけ）で開いて確かめる（K1〜K3）
- 確認の前後で、開発用DBのハッシュが同じことを確かめる

#### 確認の日付
期待する結果は、確認の日が **2026-09-21〜2027-01-31** の間にあることを前提にしている（R2で登録する「2026年度 後期」が、今日を含む）。この範囲の外の日に行う場合は、R1〜R4の、バナーと初期の選択の期待が変わるため、行う前にClaudeに伝える。

#### 準備
1. `python run.py` が起動していれば、Ctrl＋Cで止める（確認用のサーバーも、5001番を使うため）。開発用DBのハッシュを控える
   ```
   shasum -a 256 instance/app.db
   ```
2. 下の「確認用のサーバーの起動」のコマンドで、確認用のサーバーを起動する（このターミナルは、確認の間、開いたままにする）
3. 別のターミナルを開き、リポジトリのルートで、`DB=/tmp/schedule-app-check-011/check.db` を実行しておく（K1〜K3で使う）
4. Claudeが、ブラウザで `http://127.0.0.1:5001/` を開き、強制再読み込みをして、「授業」を押す

#### 確認用のサーバーの起動
ブランチ `feature/011-class-event-generation` のまま、リポジトリのルートで、`.venv` を有効にして、次を実行する（行の先頭に空白を入れずにコピーする）。

```
python - <<'EOF'
from pathlib import Path

from flask_migrate import upgrade

from app import create_app

# 確認用のDB（開発用DBとは別のファイル）。止めて起動し直しても、残る。
check_directory = Path("/tmp/schedule-app-check-011")
check_directory.mkdir(exist_ok=True)
database_path = check_directory / "check.db"
app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"})
with app.app_context():
    upgrade(directory="migrations")
print(f"確認用のDB：{database_path}", flush=True)
app.run(host="127.0.0.1", port=5001, debug=False)
EOF
```

期待する出力：初めての起動では、`Running upgrade  -> 0280f6cf8d09, initial tables` と `Running upgrade 0280f6cf8d09 -> 42bd53808fa1, add closures table`、「確認用のDB：/tmp/schedule-app-check-011/check.db」、`Running on http://127.0.0.1:5001`。起動し直したときは、`Running upgrade` の行が出ない。

#### R. 学期（006-L1の形・006-L4・006-L5の回帰）

| No | 操作 | 期待する結果 |
|---|---|---|
| R1 | 「最初の学期を登録する」を押し、年度2026・種別「前期」、開始日2026-04-06、終了日2026-07-31で登録する | モーダルが閉じ、「2026年度 前期」が選ばれる（タブが選択の表示になる）。バナー「新しい学期を登録しますか」が出る。休講日の欄に「休講日は登録されていません」 |
| R2 | 「新しい学期を登録する」を押し、年度2026・種別「後期」、開始日2026-09-21、終了日2027-01-31で登録する | モーダルが閉じ、「2026年度 後期」が選ばれ、タブの左に並ぶ。バナーが消える |
| R3 | もう一度「新しい学期を登録する」を押し、年度2026・種別「後期」、開始日2026-09-21、終了日2027-01-31で登録する | モーダルは閉じず、年度・種別の欄が赤枠になり、その下に「同じ名前の学期がすでに登録されています」。ボタンは「登録する」に戻る（006-L1の形を直したあとも、失敗の表示は、これまでどおり）。モーダルを閉じる |
| R4 | ページを再読み込みし、タブを「前期」「後期」と切り替える | 再読み込みの直後は「2026年度 後期」が選ばれている（選択の表示と `aria-selected="true"` が、そのタブだけ）。切り替えると、選択の表示と期間が、押したタブに移る。最後に「前期」を選んでおく |
| R5 | コンソールで、`const ui = await import("/static/js/ui.js"); try { ui.getElement("no-such-id"); } catch (error) { console.log(error.message); }` を実行する | 「要素が見つかりません：no-such-id」が出る（006-L5） |

#### S. 授業の登録と、予定の自動生成（「2026年度 前期」で）

| No | 操作 | 期待する結果 |
|---|---|---|
| S1 | 休講日の欄で、日付 2026-05-04、名前「振替休日」を追加する | 一覧に「2026年5月4日（月） 振替休日」 |
| S2 | 「授業を追加」を押し、科目名「テスト：月曜1限」、曜日「月」、9:00〜10:00、教室「3号館201」で登録する | モーダルは開いたまま、「「テスト：月曜1限」を登録しました（予定16件を作成）」。入力欄が初期値に戻り、科目名の欄にフォーカスがある（2026-04-06〜07-27の月曜日17日から、休講日の5/4を除いた16件） |
| S3 | そのまま、科目名「テスト：金曜2限」、曜日「金」、10:00〜11:00で登録する | 「「テスト：金曜2限」を登録しました（予定17件を作成）」。S2のメッセージは、この新しいメッセージに置き換わる。モーダルを閉じると、授業の一覧に2件 |
| S4 | 「新しい学期を登録する」で、年度2027・種別「前期」、開始日2027-04-01、終了日2027-04-02の学期を登録する。その学期で、科目名「テスト：月曜」、曜日「月」で授業を登録する | 「「テスト：月曜」を登録しました（学期の期間内に、この曜日の授業日がないため、予定は作成されませんでした）」（4/1は木曜日、4/2は金曜日）。モーダルを閉じる |
| S5 | 確認用のサーバーを止める（Ctrl＋C）。「2027年度 前期」で「授業を追加」を押し、科目名「接続の確認」で「登録する」を押す | フォームの上部に「サーバーに接続できませんでした。時間をおいて、もう一度お試しください」。ボタンが「登録する」に戻り、入力した科目名は残る（006-L1：失敗の表示は、これまでどおり）。モーダルを閉じ、確認用のサーバーを起動し直して、ページを再読み込みし、「授業」→「2026年度 前期」を選ぶ |

#### K1. 予定の件数（S1〜S4のあと。Komaが、別のターミナルで実行する）

```
sqlite3 -readonly $DB "SELECT s.subject_name, COUNT(*), MIN(e.date), MAX(e.date) FROM events e JOIN subjects s ON s.id = e.subject_id WHERE e.is_generated = 1 GROUP BY s.id ORDER BY s.id;"
sqlite3 -readonly $DB "SELECT s.subject_name, e.date, e.start_time, e.end_time, e.room, e.is_generated FROM events e JOIN subjects s ON s.id = e.subject_id WHERE e.date IN ('2026-05-04', '2026-06-01') ORDER BY e.date, s.id;"
```

期待する出力（1つ目。「テスト：月曜」は、予定が0件なので出ない）：

```
テスト：月曜1限|16|2026-04-06|2026-07-27
テスト：金曜2限|17|2026-04-10|2026-07-31
```

期待する出力（2つ目。休講日の5/4には、予定がない）：

```
テスト：月曜1限|2026-06-01|09:00:00.000000|10:00:00.000000|3号館201|1
```

#### C. 休講日の同期（「2026年度 前期」で）

| No | 操作 | 期待する結果 |
|---|---|---|
| C1 | 休講日の欄で、日付 2026-06-01（月）を追加する | 一覧に「2026年6月1日（月）」が足される（確認のダイアログは出ない。予定の件数は、画面に出ない） |
| K2 | Komaが、K1の2つのコマンドを、もう一度実行する | 1つ目：`テスト：月曜1限|15|2026-04-06|2026-07-27` と `テスト：金曜2限|17|2026-04-10|2026-07-31`。2つ目：出力なし（6/1の予定が消えた） |
| C2 | 「2026年5月4日（月） 振替休日」の行の「削除」を押す | その行が消える |
| K3 | Komaが、K1の2つのコマンドを、もう一度実行する | 1つ目：`テスト：月曜1限|16|2026-04-06|2026-07-27` と `テスト：金曜2限|17|2026-04-10|2026-07-31`。2つ目：`テスト：月曜1限|2026-05-04|09:00:00.000000|10:00:00.000000|3号館201|1`（5/4の予定が、授業の値で作られた） |
| C3 | 日付 2026-03-01 で追加する | 日付の欄の下に「休講日は、学期の期間内の日付にしてください」（失敗の表示は、これまでどおり） |

#### D. 送信中の表示と、途中の学期の切り替え（006-L1の形を直した `closures.js` の確認）
休講日のAPIへの要求を、ブラウザの中で2秒遅らせる。Task 010のD（`docs/tasks/010_closures_ui.md` の「遅延のスクリプト」）と同じスクリプトを、コンソールで実行する（`window.closureDelay` の名前も同じ）。**確認のためだけのもので、アプリのファイルには入れない。**

| No | 操作（「2026年度 前期」を選んだ状態から） | 期待する結果 |
|---|---|---|
| D1 | 日付 2026-06-08 で「追加する」を押す | 約2秒、ボタンが「追加中…」で押せない。そのあと、ボタンが「追加する」に戻り、入力欄が空になる。さらに約2秒後に、一覧に「2026年6月8日（月）」が出る |
| D2 | その行の「削除」を押す | その行のボタンが「削除中…」で押せない。約4秒後に、行が消える |
| D3 | 日付 2026-06-15、名前「途中」で「追加する」を押し、2秒以内に「後期」のタブを押す | すぐに後期の欄に切り替わる。入力欄は空で、ボタンは「追加する」。2秒たっても、後期の画面に、メッセージ・エラー・入力欄の変化が出ない |
| D4 | 「前期」のタブに戻る | 一覧に「2026年6月15日（月） 途中」がある（追加は、サーバーでは行われている） |
| D5 | 「2026年6月15日（月） 途中」の「削除」を押し、2秒以内に「後期」のタブを押す。そのあと「前期」に戻る | 後期の画面に、変化が出ない。前期に戻ると、6/15の行は消えている |
| D6 | ページを再読み込みする | 遅延が消える（コンソールで `typeof closureDelay` を実行すると `"undefined"`） |

#### E. 確認の全体を通して

| No | 確認 | 期待する結果 |
|---|---|---|
| E1 | コンソール | JavaScriptの例外（`Uncaught …`）が出ていない。想定した400・404の応答（R3・C3）の「Failed to load resource」の記録と、サーバーを止めている間（S5）の接続の失敗（`net::ERR_CONNECTION_REFUSED`）の記録は、除く（010-N1） |

#### 後片付け
1. 確認用のサーバーを止める（Ctrl＋C）
2. 確認用のDBのフォルダを消す
   ```
   rm -r /tmp/schedule-app-check-011
   ```
3. 開発用DBのハッシュが、準備の1と同じことを確かめる
   ```
   shasum -a 256 instance/app.db
   ```

ハッシュが変わっていた場合は、開発用DBを操作せずに、Claudeに伝える。

### 4. 開発用DBの確認（予定の自動生成を入れたコードを、開発用DBで初めて動かす）
`docs/architecture.md` の「予定の自動生成より前に登録した授業」の手順。**4-1〜4-3は、このブランチのコードで、開発用DBを使うサーバー（`python run.py`）を起動する前に行う。** 4-3の停止の条件に当たったら、4-4以降に進まず、`python run.py` も起動しないで、Claudeに伝える。

#### 4-1. バックアップ（手順1）
`python run.py` が止まっていることを確かめてから、実行する（`YYYYMMDD` は、実行する日の日付）。

```
mkdir -p instance/backups
cp -p instance/app.db instance/backups/app-YYYYMMDD-before-011.db
shasum -a 256 instance/app.db instance/backups/app-YYYYMMDD-before-011.db   # 2つのハッシュが同じ
```

戻し方（必要になった場合だけ）：サーバーを止めて、`cp -p instance/backups/app-YYYYMMDD-before-011.db instance/app.db`。

#### 4-2. 件数の記録（手順2。読み取りだけ）

```
flask --app app db current     # 42bd53808fa1 (head)
sqlite3 -readonly instance/app.db "SELECT 'semesters', COUNT(*) FROM semesters; SELECT 'subjects', COUNT(*) FROM subjects; SELECT 'closures', COUNT(*) FROM closures; SELECT 'events', COUNT(*) FROM events; SELECT 'tasks', COUNT(*) FROM tasks;"
```

期待する結果（2026-10-12の時点の開発用DB）：`semesters|0`、`subjects|0`、`closures|0`、`events|0`、`tasks|0`。

#### 4-3. 判断（手順3〜5）
- **授業（`subjects`）が0件で、予定（`events`）と課題（`tasks`）も0件**：削除するものがないため、手順3〜5（削除の対象の確認・削除）は行わない。4-4へ進む
- **それ以外**（授業が1件以上ある、または、予定・課題が0件でない）：**削除せずに停止する**（手順4の停止の条件）。4-4以降に進まず、`python run.py` も起動しないで、4-2の出力をClaudeに伝える（授業が1件以上ある場合は、未決定事項「自動生成より前に登録した授業のうち、残すものの扱い」を、先に決める）

#### 4-4. 開発用DBでの、読み取りだけの確認
開発用DBで起動して、画面が開くことだけを確かめる（登録・追加・削除はしない）。

```
python run.py                          # 開発用DBで起動（別のターミナルで、次を実行）
curl -s -w '\nHTTP %{http_code}\n' http://127.0.0.1:5001/api/subjects
# 画面の確認のあと、サーバーを Ctrl+C で止める
```

| 確認 | 期待 |
|---|---|
| ブラウザで開き、強制再読み込みして、「授業」を押す | 学期が0件のため、空状態（「学期がまだ登録されていません…」）だけ。JavaScriptの例外（`Uncaught …`）が出ていない |
| `curl` | `[]`、HTTP 200 |

#### 4-5. 実装後の件数の検証（手順6。読み取りだけ）
サーバーを止めたあと、リポジトリのルートで、次を実行する。開発用DBを、読み取り専用で開き、すべての授業の自動生成の予定が、規則（学期の期間・曜日・休講日）どおりかを確かめる（同じ授業・同じ日付に2件以上ないこと、授業に結びつかない予定がないことも確かめる）。**DBに書き込まない**（作業用のコピーで、正しいDB・誤ったDB・空のDBで動かし、DBが変わらないことを確かめた）。

```
python - <<'EOF'
import sqlite3
import sys
from collections import Counter
from datetime import date

from app.class_events import class_event_dates

# 開発用DBを、読み取り専用（mode=ro）で開く。このスクリプトは、DBに書き込まない。
database_path = sys.argv[1] if len(sys.argv) > 1 else "instance/app.db"
connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
problems = []

semesters = {
    row[0]: (date.fromisoformat(row[1]), date.fromisoformat(row[2]))
    for row in connection.execute(
        "SELECT id, start_date, end_date FROM semesters"
    )
}
closures = {}
for semester_id, closure_date in connection.execute(
    "SELECT semester_id, date FROM closures"
):
    closures.setdefault(semester_id, set()).add(
        date.fromisoformat(closure_date)
    )

subjects = connection.execute(
    "SELECT id, semester_id, weekday FROM subjects ORDER BY id"
).fetchall()
for subject_id, semester_id, weekday in subjects:
    start_date, end_date = semesters[semester_id]
    expected = class_event_dates(
        start_date, end_date, weekday, closures.get(semester_id, set())
    )
    actual = [
        date.fromisoformat(row[0])
        for row in connection.execute(
            "SELECT date FROM events WHERE subject_id = ? AND is_generated = 1"
            " ORDER BY date",
            (subject_id,),
        )
    ]
    duplicated = [
        day.isoformat() for day, count in Counter(actual).items() if count > 1
    ]
    if duplicated:
        problems.append(f"授業{subject_id}：同じ日付の予定が2件以上 {duplicated}")
    if sorted(set(actual)) != expected:
        problems.append(
            f"授業{subject_id}：規則{len(expected)}件、実際{len(actual)}件"
        )

orphans = connection.execute(
    "SELECT COUNT(*) FROM events WHERE subject_id IS NOT NULL"
    " AND subject_id NOT IN (SELECT id FROM subjects)"
).fetchone()[0]
if orphans:
    problems.append(f"授業に結びつかない予定：{orphans}件")

print(f"授業：{len(subjects)}件")
print("問題なし" if not problems else "\n".join(problems))
EOF
```

期待する出力：

```
授業：0件
問題なし
```

最後に、4-1のハッシュと同じことを確かめる。

```
shasum -a 256 instance/app.db          # 4-1の instance/app.db のハッシュと同じ
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM events;"   # 0 と 0
```

### 5. マージ
1〜4が期待どおりで、レビューで承認されたら、マージする。このタスクは、DBの構造を変えないため、開発用DBへのmigrationの適用はない。4-1のバックアップは、残しておく（`instance/` は、Gitに入らない）。

## Git操作
**Git commit / push / ブランチ操作 / マージは行わない**（`git branch --show-current`、`git status`、`git diff` のような読み取りだけのコマンドは除く）。

## 注意
- **停止して報告する条件**（ファイルを変更せず、実装を止め、チャットで「問題点・発生理由・変更した場合の影響・推奨案（必要なら）」を報告する）
  - ブランチの不一致、作業ツリーの想定外の変更
  - 設計資料が更新されていない（実装手順の1）、または、設計資料とこのTask MDの間に、矛盾・不足がある
  - 設計資料にない判断が必要になった（特に、`docs/architecture.md` の「未決定事項」や、`docs/ui_ux.md` の「未決定」に触れる場合）
  - 「変更しない」と定めたもの（モデル、`api_helpers.py`、テンプレート、`api.js`・`dates.js`・`main.js` など）を変更しないと実装できない。または、1-1〜4-4のコードと差分を変える必要があると判断した
  - 差分が、今のファイルにそのまま当てはまらない（前後の行が違う、など）
  - 開発用DB（`instance/app.db`）がない
  - 作業の前の `python -m pytest` が、394件すべて合格しない
  - **既存のテスト**（作業の開始時からあるテストのうち、「変更してよい既存のテスト」の表にないもの）**が、想定外に失敗した**。テストの期待値や、ほかの仕様を直さずに、原因を調べて報告する
  - DBの構造の変更（migration）や、APIの変更（このTask MDに書いたもの以外）が必要だと判断した
  - 実施の前後で、`instance/app.db` が変わった
- **止まるときは、報告を書いて、その応答を終える。質問の機能は使わない。** 再開するのは、Komaの新しいメッセージが、判断や再開を明確に示したときだけ（無回答や「続けて」だけの返事は、再開の指示ではない）。`.github/copilot-instructions.md` の「止まる場面の応答」
- `flask db` のコマンドを、一切実行しない。ライブラリを追加しない。サーバーを起動しない（`python run.py` も、「Komaの確認」の確認用のサーバーも）
- 期待する結果と異なる結果が出た場合は、確認を飛ばさず、原因を直してから、すべての確認をやり直す（ただし、既存のテストの想定外の失敗は、上の停止の条件に従う）
- 設計資料に書かれていない仕様は、自分で決めない
- 最後の報告に、次を含める：変更したファイル、各段階の `pytest` の件数と警告、1行の長さの確認の結果、検索の結果、開発用DBの前後のハッシュ・件数、`git status`・`git diff --stat`、ブラウザで確認していないこと、気になった点
