# タスク016: 課題・タスクのAPI

| 項目 | 内容 |
|---|---|
| Task ID | 016 |
| Task名 | 課題・タスクのAPI（`/api/tasks` の一覧・1件取得・登録・編集・削除）と、カテゴリの許可値の一元管理（`app/categories.py`）、日時・真偽値・決まった値の検証、`PATCH` の空の本文の検査の共通化 |
| ブランチ | `feature/016-tasks-api`（Komaが作成・切替済みの状態で渡される） |

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに停止して報告する。

**このタスクには、承認ゲートはない（DBの構造を変えないため、migrationを作らない）。** 段階1・2を順に進め、「Copilot確認手順」を実施したら、結果を報告して応答を終える。途中で止まるのは、「注意」の停止の条件に当たったときだけ。**止まるときは、報告を書いて応答を終える。質問の機能（選択肢を出して回答を待つ機能）は使わない**（`.github/copilot-instructions.md` の「止まる場面の応答」）。

**ファイルは、手で書き写さない。** 9つのファイルの全文は、このTask MDの付録にある。各段階の始めに、「全文からファイルを作るスクリプト」を実行して作る（013-N1）。付録の全文は、スクリプトが読む。付録を読んで書き写す必要はない（本文の要点・差分・確認の手順を読む）。

**報告には、コマンドの出力を、要約せずに、そのまま貼る**（014-L1）。「注意」の最後の報告の項目を参照。

## 目的
課題と、その他（締切のみ）を扱う、課題・タスクのAPI（`/api/tasks`）を作る。一覧（完了の状態での絞り込み）・1件取得・登録・編集（完了・未完了の切り替えを含む）・削除を提供する。あわせて、カテゴリの保存値と許可値を `app/categories.py` で一元管理し（2026-10-15に決定。それまでの未決定事項「categoryの入力の検証と、許可値の管理」）、日時・真偽値・決まった値から選ぶ文字列の検証と、`PATCH` の空の本文（`{}`）の検査を、`app/api_helpers.py` の共通の関数にする。設計資料（`docs/architecture.md` の「課題・タスクAPI」「データ設計」の「共通の約束」「カテゴリの保存値の置き場所」「Task」、「API共通ルール」）の仕様を、そのまま実装する。**画面とDBの構造は変えない**（課題・タスクモードの画面は、後続のタスクで作る）。

次の2段階で、この順に行う。

| 段階 | 内容 | 挙動の変化 | 段階の終わりの `pytest` |
|---|---|---|---|
| 1 | 共通の部品：`app/categories.py`（新規）、`app/class_events.py`（定数を `categories.py` から読む）、`app/api_helpers.py`（関数の追加）、`app/routes/subjects.py`（空の本文の検査を `read_patch_object` に置き換え）、`tests/test_class_events.py`（`import` の変更）、`tests/test_api_helpers.py`（テスト57件の追加） | 変わらない（授業の `PATCH` の `{}` の応答は同じ。新しい関数は、まだ課題からは使わない） | **626件**（569＋57） |
| 2 | 課題・タスクのAPI：`app/routes/tasks.py`（新規）、`app/__init__.py`（登録）、`tests/test_tasks_api.py`（新規。161件） | `/api/tasks` が使えるようになる（今は404） | **787件**（626＋161） |

## 前提（Task 015完了時点の状態）

| 区分 | 内容 |
|---|---|
| すでにある | 学期・授業・休講日のAPIと画面、授業の編集・削除（Task 014・015）、予定API（読み取りだけ）、カレンダー表示、pytest（**569件**。`main` の `27fcdae` で確認） |
| まだない | `/api/tasks`（今は、URLが見つからず404）、`app/categories.py`、`app/routes/tasks.py`、`tests/test_tasks_api.py` |
| DBの構造 | 変えない。`tasks` テーブルは、初期migration（`0280f6cf8d09`）にある。**migrationは不要**。モデル（`app/models/task.py`）も変えない |
| 開発用DB | `instance/app.db` は、Komaの実際の開発用DB（すべてのテーブルが0件。2026-10-15、Task 015の確認のあとにKomaが確認）。**Copilotは、書き込まない。サーバーを起動しない（`python run.py` を実行しない）**。読むのは、「Copilot確認手順」のハッシュと件数だけ。**`sqlite3` は、必ず `-readonly` を付けて実行する**（011-L1） |
| 設計資料 | このタスクの前に、更新した設計資料が `main` に反映されている。`docs/architecture.md` に「課題・タスクAPI」「カテゴリの保存値の置き場所」の節があり、未決定事項から「categoryの入力の検証と、許可値の管理」が外れている |
| 画面 | 変えない。ブラウザでの確認はない。APIの動作は、pytestと、Komaの確認用のサーバーでの `curl` で確かめる |
| 「今日」 | 課題・タスクのAPIは、「今日」を使わない（期限切れの判定は、画面が行う）。テストの結果は、実行した日によらない |

## Source of Truth
- `docs/architecture.md`：「データ設計」の「共通の約束」（`category`）・「カテゴリの保存値の置き場所：`app/categories.py`」・Task、「授業のEventの生成処理」（`EVENT_CATEGORY_CLASS`）、「API共通ルール」（「リクエストとレスポンス（JSON）」の `PATCH`・「レスポンスの付加情報」・文字列・「真偽値」・「決まった値から選ぶ文字列」・「ほかのリソースのIDを参照する項目」、「日付・時刻・日時」、「404の使い分け」、「API共通処理の補助モジュール」）、「授業API」（`PATCH` の空の本文、削除）、「課題・タスクAPI」、「自動テスト（pytest）」、「ディレクトリ構成」
- `docs/requirements.md`：「カテゴリ」、「予定の登録」（課題・タスクモード、その他）、「予定の編集・削除」、「課題の完了管理」
- `docs/ui_ux.md`：「カレンダーモード」の「共通」（「直近の締切」欄の「今日」）、「課題・タスクモード」
- `.github/copilot-instructions.md`：進め方、「止まる場面の応答」、コーディング方針、「テスト」

## 実装対象ファイル

| 区分 | ファイル | 段階 | 内容 | 全文 |
|---|---|---|---|---|
| 新規 | `app/categories.py` | 1 | カテゴリの保存値の定数と、許可値の一覧 | 付録A |
| 変更 | `app/class_events.py` | 1 | `EVENT_CATEGORY_CLASS` の定義を消し、`app/categories.py` から `import` する | 付録B |
| 変更 | `app/api_helpers.py` | 1 | `EMPTY_PATCH_MESSAGE`・`read_patch_object`・`validate_required_boolean`・`validate_required_choice`・`parse_datetime`・`format_datetime`・`validate_required_datetime` を足す | 付録C |
| 変更 | `app/routes/subjects.py` | 1 | `update_subject` の、本文の読み取りと空の本文の検査を、`read_patch_object` に置き換える | 付録D |
| 変更 | `tests/test_class_events.py` | 1 | `EVENT_CATEGORY_CLASS` を `app.categories` から `import` する | 付録E |
| 変更 | `tests/test_api_helpers.py` | 1 | 新しい関数のテスト（57件）と、その `import` を足す | 付録F |
| 新規 | `app/routes/tasks.py` | 2 | 課題・タスクのAPI | 付録G |
| 変更 | `app/__init__.py` | 2 | `tasks_bp` を登録する | 付録H |
| 新規 | `tests/test_tasks_api.py` | 2 | 課題・タスクのAPIのテスト（161件） | 付録I |

上の9ファイル以外は、変更しない（`__pycache__/` などの、`.gitignore` の対象は除く）。**9ファイルとも、このTask MDの付録に全文がある。「全文からファイルを作るスクリプト」で作り、手で書き写さない。書き込んだあとに、手で直さない。** 全文を変える必要があると判断した場合は、変えずに停止して報告する。

## 非対象（このタスクでは作らない・変更しない）
- モデル（`app/models/`）、`migrations/`（**新しいmigrationを作らない。`flask db` のコマンドを、一切実行しない**）、`requirements.txt`（**ライブラリを追加しない**）、`pytest.ini`、`run.py`
- `app/routes/` の、`subjects.py`・`tasks.py` 以外のファイル（`semesters.py`・`closures.py`・`events.py`・`main.py`）
- `app/templates/`、`app/static/`（画面は変えない。課題・タスクモードの画面と、カレンダーの締切の表示は、後続のタスク）
- `tests/` の、上の3つ以外のファイル（`conftest.py`・`test_subjects_api.py`・`test_subjects_update_delete_api.py` を含む）
- `docs/`、`.github/`、`.gitignore`
- 作らないもの：課題・タスクの画面、予定の登録・編集・削除（`/api/events` の `POST`・`PATCH`・`DELETE` は405のまま。`EVENT_CATEGORIES` は定義するだけで、まだ使わない）、締切日時の期間や対象授業で絞り込むクエリ、学期の変更・削除
- 持ち越しの003-H・013-L1・015-L1（このタスクでは扱わない）
- 開発用DB（`instance/app.db`）への書き込み、サーバーの起動（`python run.py` も、「Komaの確認」の確認用のサーバーも、起動しない）

## 全文からファイルを作るスクリプト（013-N1）
各段階の始めに、リポジトリのルートで、`.venv` を有効にして実行する。段階1は `python - 1`、段階2は `python - 2`（`-` のあとの数字が段階）。このTask MDの付録の、「`<!-- 全文: パス -->`」の印の直後のコードブロックを、そのパスのファイルに、そのまま書き込む（その段階のファイルだけ）。

```
python - 1 <<'EOF'
import re
import sys
from pathlib import Path

# 段階ごとに書き込むファイル（このTask MDの「実装対象ファイル」と同じ）。
STAGE_FILES = {
    "1": [
        "app/categories.py",
        "app/class_events.py",
        "app/api_helpers.py",
        "app/routes/subjects.py",
        "tests/test_class_events.py",
        "tests/test_api_helpers.py",
    ],
    "2": [
        "app/routes/tasks.py",
        "app/__init__.py",
        "tests/test_tasks_api.py",
    ],
}

stage = sys.argv[1]
# このTask MDの「<!-- 全文: パス -->」の直後のコードブロックを、
# そのファイルの全文として取り出す。
fence = "`" * 3
task_text = Path("docs/tasks/016_tasks_api.md").read_text(encoding="utf-8")
pattern = re.compile(
    "<!-- 全文: (\\S+) -->\n" + fence + "[a-z]+\n(.*?)" + fence + "\n",
    re.S,
)
full_texts = dict(pattern.findall(task_text))
print(f"全文の数：{len(full_texts)}")
for file_name in STAGE_FILES[stage]:
    text = full_texts[file_name]
    Path(file_name).write_text(text, encoding="utf-8")
    print(f"{file_name}：書き込み（{len(text.splitlines())}行）")
EOF
```

期待する出力：

| 段階 | 出力 |
|---|---|
| 1（`python - 1`） | `全文の数：9`、`app/categories.py：書き込み（29行）`、`app/class_events.py：書き込み（102行）`、`app/api_helpers.py：書き込み（455行）`、`app/routes/subjects.py：書き込み（404行）`、`tests/test_class_events.py：書き込み（278行）`、`tests/test_api_helpers.py：書き込み（711行）` |
| 2（`python - 2`） | `全文の数：9`、`app/routes/tasks.py：書き込み（332行）`、`app/__init__.py：書き込み（60行）`、`tests/test_tasks_api.py：書き込み（983行）` |

- 出力が上と違う場合（全文の数・行数・エラー）は、ほかの作業をせずに停止して報告する
- 段階の終わりの「全文との比較」（「Copilot確認手順」の4）で「不一致」が出た場合は、手で直さず、その段階のスクリプトをもう一度実行して、全文に戻す。戻したことと、違っていた理由（分かれば）を、報告に書く（013-N1）

## 段階1：共通の部品（挙動は変わらない）

### 1-1. `app/categories.py`（新規。全文：付録A）
要点：
- 予定（Event）のカテゴリの保存値 `EVENT_CATEGORY_CLASS`・`EVENT_CATEGORY_PART_TIME`・`EVENT_CATEGORY_OTHER` と、その許可値のタプル `EVENT_CATEGORIES`
- 課題・タスク（Task）のカテゴリの保存値 `TASK_CATEGORY_ASSIGNMENT`・`TASK_CATEGORY_OTHER` と、その許可値のタプル `TASK_CATEGORIES`
- 定数だけを持つ（関数・DBの操作・Flaskの処理を持たない）。`EVENT_CATEGORIES` は、このタスクでは、まだどこからも使わない（予定の登録・編集を作るタスクで使う）

### 1-2. `app/class_events.py`（全文：付録B）
`EVENT_CATEGORY_CLASS` の定義を消し、`app/categories.py` から `import` する。関数は変えない。`main` からの差分（確認用。ファイルは、スクリプトで作る）：

```diff
--- a/app/class_events.py
+++ b/app/class_events.py
@@ -9,15 +9,14 @@ DBの読み書き（セッションへの追加・commit）は行わない。休
 
 from datetime import date, timedelta
 
+# 授業の予定のカテゴリの保存値は、app/categories.py の定数を使う
+# （文字列 "class" を、ほかの場所に直接書かない）。
+from app.categories import EVENT_CATEGORY_CLASS
 from app.models.event import Event
 from app.models.semester import Semester
 from app.models.subject import Subject
 
 
-# 授業の予定のカテゴリの保存値。文字列 "class" を、ほかの場所に直接書かない。
-EVENT_CATEGORY_CLASS = "class"
-
-
 def class_event_dates(
     start_date: date,
     end_date: date,
```

### 1-3. `app/api_helpers.py`（全文：付録C）
要点（追加だけ。既存の関数は変えない）：

| 名前 | 種類 | 内容 |
|---|---|---|
| `EMPTY_PATCH_MESSAGE` | 定数 | 「変更する項目を指定してください」（授業の `PATCH` の今のメッセージと同じ） |
| `read_patch_object()` | 関数 | `read_json_object()` で本文を読み、項目が1つもないオブジェクト（`{}`）を、400（`validation_error`、`fields` なし）にする |
| `validate_required_boolean` | 関数 | 必須の真偽値。JSONの `true`・`false` だけ。未指定・`null`・空文字は必須のエラー。数値・文字列は型の誤り |
| `validate_required_choice` | 関数 | 決まった値（`choices`）から選ぶ、必須の文字列。完全に一致する文字列だけ。未指定・`null`・空文字は必須のエラー。型の誤りと、値にないものは、同じメッセージ。使用できない文字は `UNUSABLE_CHARACTER_MESSAGE` |
| `parse_datetime`・`format_datetime` | 関数 | `YYYY-MM-DDTHH:MM`（秒なし）と `datetime` の変換。形式を正規表現で先に確かめてから、`datetime.fromisoformat` で変換する。出力は `isoformat(timespec="minutes")` |
| `validate_required_datetime` | 関数 | 必須の日時。`validate_required_date` と同じ形（文字列でない値は形式の誤り、使用できない文字は形式の検査の前） |

`main` からの差分（確認用）：

```diff
--- a/app/api_helpers.py
+++ b/app/api_helpers.py
@@ -1,5 +1,6 @@
 import re
-from datetime import date, time
+from collections.abc import Collection
+from datetime import date, datetime, time
 from typing import Any
 
 from flask import Flask, Response, jsonify, request
@@ -22,6 +23,7 @@ INVALID_JSON_MESSAGE = (
     "Content-Typeを application/json にして、JSONで送ってください"
 )
 UNUSABLE_CHARACTER_MESSAGE = "使用できない文字が含まれています"
+EMPTY_PATCH_MESSAGE = "変更する項目を指定してください"
 
 
 def contains_unusable_character(value: str) -> bool:
@@ -102,6 +104,26 @@ def read_json_object() -> tuple[
     return payload, None
 
 
+def read_patch_object() -> tuple[
+    dict[str, Any] | None,
+    tuple[Response, int] | None,
+]:
+    """PATCHの本文を読み、項目が1つもないオブジェクト（{}）を誤りにする。
+
+    本文の読み取りは、read_json_object と同じ。{} は、特定の項目に
+    結びつかない誤りのため、fields を付けない。
+    """
+    payload, error_response = read_json_object()
+    if error_response is not None:
+        return None, error_response
+    if not payload:
+        return None, api_error_response(
+            "validation_error",
+            EMPTY_PATCH_MESSAGE,
+        )
+    return payload, None
+
+
 def read_id_query(
     name: str,
     multiple_message: str,
@@ -249,6 +271,50 @@ def validate_required_integer(
     return value, None
 
 
+def validate_required_boolean(
+    payload: dict[str, Any],
+    field: str,
+    required_message: str,
+    type_message: str,
+) -> tuple[bool | None, str | None]:
+    """必須の真偽値を検査する。JSONの true・false だけを受け付ける。
+
+    数値（0・1）や文字列（"true" など）は、型の誤りにする。
+    """
+    value = payload.get(field)
+    if field not in payload or value is None or value == "":
+        return None, required_message
+    if not isinstance(value, bool):
+        return None, type_message
+    return value, None
+
+
+def validate_required_choice(
+    payload: dict[str, Any],
+    field: str,
+    choices: Collection[str],
+    required_message: str,
+    choice_message: str,
+) -> tuple[str | None, str | None]:
+    """決まった値（choices）の中から選ぶ、必須の文字列を検査する。
+
+    カテゴリ（category）に使う。choices のどれかと完全に一致する文字列
+    だけを受け付ける（前後の空白を取り除かない）。文字列でない値と、
+    choices にない値は、どちらも choice_message を返す。使用できない
+    文字（孤立サロゲート）を含む場合は、UNUSABLE_CHARACTER_MESSAGE を返す。
+    """
+    value = payload.get(field)
+    if field not in payload or value is None or value == "":
+        return None, required_message
+    if not isinstance(value, str):
+        return None, choice_message
+    if contains_unusable_character(value):
+        return None, UNUSABLE_CHARACTER_MESSAGE
+    if value not in choices:
+        return None, choice_message
+    return value, None
+
+
 def parse_time(value: Any) -> time | None:
     """HH:MMの厳密な形式と時刻の範囲を確認して変換する。"""
     if not isinstance(value, str):
@@ -338,3 +404,52 @@ def validate_required_date(
     if parsed_value is None:
         return None, format_message
     return parsed_value, None
+
+
+def parse_datetime(value: Any) -> datetime | None:
+    """YYYY-MM-DDTHH:MMの形式と実在性を確認して日時に変換する。"""
+    if not isinstance(value, str):
+        return None
+
+    # fromisoformatは秒や別の書式も受理するため、先に厳密な形式を確認する。
+    if (
+        re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}", value)
+        is None
+    ):
+        return None
+    try:
+        return datetime.fromisoformat(value)
+    except ValueError:
+        return None
+
+
+def format_datetime(value: datetime) -> str:
+    """日時をAPIのYYYY-MM-DDTHH:MM形式にする（秒は出さない）。"""
+    return value.isoformat(timespec="minutes")
+
+
+def validate_required_datetime(
+    payload: dict[str, Any],
+    field: str,
+    required_message: str,
+    format_message: str,
+) -> tuple[datetime | None, str | None]:
+    """必須の日時を検査し、Pythonのdatetimeかエラーメッセージを返す。
+
+    文字列でない値は、日付・時刻と同じく、format_messageを返す。
+    使用できない文字（孤立サロゲート）を含む場合は、
+    UNUSABLE_CHARACTER_MESSAGEを返す。この検査は、型の検査のあと、
+    形式の検査より前に、常に行う。
+    """
+    value = payload.get(field)
+    if field not in payload or value is None or value == "":
+        return None, required_message
+    if not isinstance(value, str):
+        return None, format_message
+    if contains_unusable_character(value):
+        return None, UNUSABLE_CHARACTER_MESSAGE
+
+    parsed_value = parse_datetime(value)
+    if parsed_value is None:
+        return None, format_message
+    return parsed_value, None
```

### 1-4. `app/routes/subjects.py`（全文：付録D）
`update_subject` の、本文の読み取り（`read_json_object`）と空の本文の検査を、`read_patch_object` に置き換える。応答（ステータス・メッセージ・`fields` なし）は変わらない（既存のテスト `test_patch_empty_object_is_validation_error_without_fields` で確かめる）。ほかの関数は変えない。`main` からの差分（確認用）：

```diff
--- a/app/routes/subjects.py
+++ b/app/routes/subjects.py
@@ -9,6 +9,7 @@ from app.api_helpers import (
     format_time,
     read_id_query,
     read_json_object,
+    read_patch_object,
     validate_allowed_fields,
     validate_optional_string,
     validate_required_integer,
@@ -339,15 +340,10 @@ def update_subject(subject_id: int):
     if subject is None:
         return api_error_response("not_found", "授業が見つかりません")
 
-    payload, error_response = read_json_object()
+    # 項目が1つもない本文（{}）も、誤りにする（API共通ルール）。
+    payload, error_response = read_patch_object()
     if error_response is not None:
         return error_response
-    # 項目が1つもない本文（{}）は、誤りにする（API共通ルール）。
-    if not payload:
-        return api_error_response(
-            "validation_error",
-            "変更する項目を指定してください",
-        )
 
     values, fields = validate_subject_values(payload, partial=True)
 
```

### 1-5. `tests/test_class_events.py`（全文：付録E）
`EVENT_CATEGORY_CLASS` を、`app.categories` から `import` する（テストの中身は変えない。25件のまま）。`main` からの差分（確認用）：

```diff
--- a/tests/test_class_events.py
+++ b/tests/test_class_events.py
@@ -2,8 +2,8 @@ from datetime import date, time, timedelta
 
 import pytest
 
+from app.categories import EVENT_CATEGORY_CLASS
 from app.class_events import (
-    EVENT_CATEGORY_CLASS,
     build_class_event,
     build_class_events,
     build_class_events_from,
```

### 1-6. `tests/test_api_helpers.py`（全文：付録F）
`import` に新しい関数を足し、ファイルの末尾にテストを足す（既存の112件は変えない。112件 → 169件）。`main` からの差分のうち、`import` の部分（確認用。末尾に足すテストは、付録Fの全文を参照）：

```diff
--- a/tests/test_api_helpers.py
+++ b/tests/test_api_helpers.py
@@ -1,18 +1,24 @@
-from datetime import date, time
+from datetime import date, datetime, time
 
 import pytest
 from flask import Flask
 
 from app.api_helpers import (
+    EMPTY_PATCH_MESSAGE,
     MAX_ID,
     UNUSABLE_CHARACTER_MESSAGE,
     contains_unusable_character,
+    format_datetime,
     format_time,
     parse_time,
     read_id_query,
+    read_patch_object,
     validate_optional_string,
+    validate_required_boolean,
+    validate_required_choice,
     validate_required_integer,
     validate_required_date,
+    validate_required_datetime,
     validate_required_string,
     validate_required_time,
 )
```

| 確かめること（`docs/architecture.md` の「API共通ルール」「日付・時刻・日時」） | テスト | 件数 |
|---|---|---|
| 日時を `datetime` に変換する（うるう日を含む） | `test_validate_required_datetime_converts_value` | 3 |
| 日時の未指定・`null`・空文字は、必須のエラー | `test_validate_required_datetime_reports_required` | 3 |
| 文字列でない日時は、形式の誤り | `test_validate_required_datetime_reports_non_string_as_format_error` | 3 |
| 形式の誤り（日付だけ、空白・小文字の `t`、秒、タイムゾーン、24時、60分、実在しない日、0埋めなし、区切りなし、前後の空白、全角の数字） | `test_validate_required_datetime_reports_format_error` | 14 |
| 日時の使用できない文字 | `test_validate_required_datetime_rejects_unusable_characters` | 2 |
| 日時の出力は、秒を出さない | `test_format_datetime_omits_seconds` | 2 |
| 真偽値の `true`・`false` を受け付ける | `test_validate_required_boolean_accepts_booleans` | 2 |
| 真偽値の未指定・`null`・空文字は、必須のエラー | `test_validate_required_boolean_checks_required` | 3 |
| 真偽値でない値（`0`・`1`・`1.0`・`"true"`・`"false"`・配列・オブジェクト）は、型の誤り | `test_validate_required_boolean_rejects_non_booleans` | 7 |
| 決まった値を受け付ける | `test_validate_required_choice_accepts_choices` | 2 |
| 決まった値の未指定・`null`・空文字は、必須のエラー | `test_validate_required_choice_checks_required` | 3 |
| 決まった値にないもの（別のカテゴリ、大文字、前後の空白、日本語、数値、真偽値、配列）は、同じメッセージ | `test_validate_required_choice_rejects_other_values` | 8 |
| 決まった値の使用できない文字 | `test_validate_required_choice_rejects_unusable_characters` | 2 |
| `read_patch_object`：項目がある本文を返す | `test_read_patch_object_returns_payload` | 1 |
| `read_patch_object`：`{}` は400（`fields` なし） | `test_read_patch_object_rejects_empty_object` | 1 |
| `read_patch_object`：オブジェクトでない本文は、`read_json_object` と同じ誤り | `test_read_patch_object_keeps_read_json_object_errors` | 1 |
| 合計 | | **57** |

## 段階2：課題・タスクのAPI

### 2-1. `app/routes/tasks.py`（新規。全文：付録G）
ファイルの構成（上から順に）：

| 名前 | 種類 | 内容 |
|---|---|---|
| `tasks_bp` | Blueprint | `url_prefix="/api/tasks"` |
| `CREATE_FIELDS`・`UPDATE_FIELDS` | 定数 | 登録・編集で受け付ける項目。登録は `is_completed` を、編集は `category` を受け付けない |
| `CATEGORY_MESSAGE`・`COMPLETED_MESSAGE`・`OTHER_SUBJECT_MESSAGE` | 定数 | カテゴリ・完了の状態・その他の対象授業のメッセージ（登録・編集・一覧のクエリで共通） |
| `task_to_dict` | 関数 | レスポンスの辞書。付加情報 `subject_name`（対象授業の今の科目名。その他は `None`）を含める |
| `read_completed_query` | 関数 | 一覧のクエリ `is_completed` の読み取り（小文字の `true`・`false` だけ） |
| `validate_task_values(payload, *, partial)` | 関数 | タイトル・締切日時・詳細／メモの検証。登録（`partial=False`）と編集（`partial=True`。本文にある項目だけ）で共通 |
| `validate_task_subject_id(payload, category)` | 関数 | 対象授業の検証。課題は必須（整数・存在する授業）、その他は `null` か項目なしだけ |
| `get_tasks` | route | `GET /api/tasks`。並びは `due_datetime`・`id` の昇順 |
| `get_task` | route | `GET /api/tasks/<id>` |
| `create_task` | route | `POST`。下の順序 |
| `update_task` | route | `PATCH`。下の順序 |
| `delete_task` | route | `DELETE`。その行だけを削除する |

`create_task`（`POST`）の処理の順序：
1. 本文を読む（`read_json_object`）
2. カテゴリを検証する（`validate_required_choice`。許可値は `TASK_CATEGORIES`）
3. タイトル・締切日時・詳細／メモを検証する（`validate_task_values(payload, partial=False)`）
4. カテゴリに誤りがなければ、対象授業を、そのカテゴリの規則で検証する（`validate_task_subject_id`）。カテゴリに誤りがあれば、対象授業は検証しない
5. 受け付けない項目（`id`・`is_completed`・`subject_name`・未知の項目）のエラー
6. 誤りがあれば、400で、まとめて返す（何も保存しない）
7. `is_completed=False` で作り、1回のcommit。201で、作成した課題・タスクを返す

`update_task`（`PATCH`）の処理の順序：
1. 課題・タスクを取得する。なければ404（「課題・タスクが見つかりません」）。本文は読まない
2. 本文を読む（`read_patch_object`。`Content-Type`・JSON・オブジェクト・空の本文の検査）
3. 本文にある項目を検証する（`validate_task_values(payload, partial=True)`）
4. 本文に `is_completed` があれば、検証する（`validate_required_boolean`）
5. 本文に `subject_id` があれば、**今のカテゴリ**の規則で検証する（`validate_task_subject_id(payload, task.category)`）
6. 受け付けない項目（`category`・`id`・`subject_name`・未知の項目）のエラー
7. 誤りがあれば、400で、まとめて返す（何も変えない）
8. 本文にあった項目だけを書き込み、1回のcommit。200で、更新後の課題・タスクを返す

注意：
- カテゴリの保存値の文字列（`"assignment"`・`"other"`）を、`tasks.py` に直接書かない。`app/categories.py` の定数（`TASK_CATEGORIES`・`TASK_CATEGORY_OTHER`）を使う
- `PATCH`・`DELETE` のURLに、上限（`MAX_ID`）を超えるIDを指定すると、405になる（`GET` は404）。授業と同じく、Flaskの仕組みによるもので、直さない（`docs/architecture.md` の「404の使い分け」の注意。テスト `test_over_limit_id_for_patch_and_delete_is_method_not_allowed`）
- 「今日」を使わない（`date.today()`・`datetime.now()` を書かない）

### 2-2. `app/__init__.py`（全文：付録H）
`tasks_bp` を、予定のAPIのあとに登録する。`main` からの差分（確認用）：

```diff
--- a/app/__init__.py
+++ b/app/__init__.py
@@ -53,4 +53,8 @@ def create_app(test_config: dict[str, Any] | None = None):
     from app.routes.events import events_bp
 
     app.register_blueprint(events_bp)
+
+    from app.routes.tasks import tasks_bp
+
+    app.register_blueprint(tasks_bp)
     return app
```

### 2-3. `tests/test_tasks_api.py`（新規。全文：付録I）
- 授業は、ORMで直接作る（予定は作らない。課題のテストには要らないため）。学期は 2026-09-21〜2027-01-29
- 課題・タスクは、APIで登録する
- 変わっていないことは、すべての課題・タスクの値（`all_task_rows`）を、操作の前後で比べて確かめる
- 「今日」を使わないため、日付を固定する仕組みはない（実行した日によって、結果が変わらない）

| 確かめること（`docs/architecture.md` の「課題・タスクAPI」） | テスト | 件数 |
|---|---|---|
| 課題の登録：201、すべての項目（`subject_name` を含む。未完了） | `test_create_assignment_returns_task` | 1 |
| 課題の登録：DBの行（締切日時の秒は0） | `test_create_assignment_saves_row` | 1 |
| その他の登録：対象授業の項目がない・`null` | `test_create_other_without_subject` | 2 |
| タイトルの前後の空白（全角を含む）を除き、空のメモは `null` | `test_create_strips_title_and_clears_blank_notes` | 1 |
| 過去の締切日時も受け付ける | `test_create_accepts_past_due_datetime` | 1 |
| タイトルは200字まで | `test_create_accepts_title_of_200_characters` | 1 |
| カテゴリの検証（必須、許可値・型、使用できない文字） | `test_create_category_is_validated` | 12 |
| タイトルの検証 | `test_create_title_is_validated` | 7 |
| 締切日時の検証 | `test_create_due_datetime_is_validated` | 10 |
| 詳細／メモの検証 | `test_create_notes_is_validated` | 2 |
| 課題の対象授業の検証（必須・型・範囲・存在） | `test_create_assignment_subject_id_is_validated` | 10 |
| その他に、存在する授業を指定すると400 | `test_create_other_rejects_existing_subject_id` | 1 |
| その他に、`null` 以外の値（`0`・空文字・文字列・存在しないID）を指定すると400 | `test_create_other_rejects_any_subject_id_value` | 4 |
| カテゴリに誤りがあれば、対象授業は検証しない | `test_create_invalid_category_skips_subject_id_validation` | 1 |
| `id`・`is_completed`・`subject_name`・未知の項目は400 | `test_create_rejects_unknown_and_read_only_fields` | 4 |
| 誤りは、まとめて返す | `test_create_validation_errors_are_returned_together` | 1 |
| 検証の誤りでは、何も保存しない | `test_failed_create_saves_nothing` | 1 |
| 本文がオブジェクトでない（`null` を含む） | `test_create_non_object_payload_has_no_fields` | 5 |
| JSONが読めない・`Content-Type` が違う | `test_create_invalid_json_or_content_type_is_rejected` | 3 |
| 一覧：0件なら空の配列 | `test_task_list_is_empty_without_tasks` | 1 |
| 一覧：締切日時・IDの昇順 | `test_task_list_is_ordered_by_due_datetime_and_id` | 1 |
| 一覧の要素は、登録のレスポンスと同じ形 | `test_task_list_items_are_same_as_created_tasks` | 1 |
| 一覧：`is_completed` の絞り込み | `test_task_list_filters_by_completion` | 2 |
| 一覧：`is_completed` の誤り（空文字・大文字・数字・空白など） | `test_task_list_rejects_invalid_completion_query` | 8 |
| 一覧：`is_completed` の複数回の指定 | `test_task_list_rejects_repeated_completion_query` | 1 |
| 一覧：未知のクエリは無視する | `test_task_list_ignores_unknown_query` | 1 |
| `subject_name` は、授業の今の科目名 | `test_subject_name_is_current_subject_name` | 1 |
| 1件取得 | `test_task_get_returns_task` | 1 |
| 1件取得の404の使い分け | `test_task_get_not_found_and_invalid_urls` | 8 |
| 編集：本文にある項目だけを変える | `test_patch_changes_only_given_fields` | 1 |
| 編集：変えられる項目をすべて変える（課題の対象授業を含む） | `test_patch_can_change_all_editable_fields` | 1 |
| 編集：完了の取り消し | `test_patch_completion_can_be_undone` | 1 |
| 編集：メモを `null` にする | `test_patch_can_clear_notes` | 3 |
| 編集：その他の対象授業に `null` を受け付ける | `test_patch_other_accepts_null_subject_id` | 1 |
| 編集：その他に授業を指定すると400 | `test_patch_other_rejects_subject_id` | 1 |
| 編集：課題の対象授業の検証 | `test_patch_assignment_subject_id_is_validated` | 5 |
| 編集：各項目の検証（タイトル・締切日時・メモ・完了の状態） | `test_patch_field_values_are_validated` | 15 |
| 編集：カテゴリ（同じ値を含む）・`id`・`subject_name`・未知の項目は400 | `test_patch_rejects_category_and_unknown_fields` | 5 |
| 編集：`{}` は400（`fields` なし） | `test_patch_empty_object_is_validation_error_without_fields` | 1 |
| 編集：誤りは、まとめて返す | `test_patch_validation_errors_are_returned_together` | 1 |
| 編集：検証の誤りでは、何も変えない | `test_failed_patch_changes_nothing` | 1 |
| 編集：本文がオブジェクトでない | `test_patch_non_object_payload_has_no_fields` | 5 |
| 編集：JSONが読めない・`Content-Type` が違う | `test_patch_invalid_json_or_content_type_is_rejected` | 3 |
| 編集の404の使い分け | `test_patch_not_found_and_invalid_urls` | 5 |
| 編集：課題・タスクがなければ、本文を読む前に404 | `test_patch_missing_task_is_404_before_reading_body` | 1 |
| 削除：その行だけを削除する（授業は残る） | `test_delete_task_removes_only_that_task` | 1 |
| 削除は本文を読まない | `test_delete_task_ignores_body` | 1 |
| 削除した課題・タスクを、もう一度削除すると404 | `test_deleted_task_cannot_be_deleted_again` | 1 |
| 削除の404の使い分け | `test_delete_not_found_and_invalid_urls` | 5 |
| 上限を超えるIDの `PATCH`・`DELETE` は405 | `test_over_limit_id_for_patch_and_delete_is_method_not_allowed` | 4 |
| 提供しないメソッドは405（行は変わらない） | `test_unsupported_task_methods_do_not_change_rows` | 5 |
| 授業の削除で、その授業の課題だけが消える | `test_deleting_subject_removes_only_its_tasks` | 1 |
| 合計 | | **161** |

## 変更してよい既存のテスト

| ファイル | 変えてよいこと | 変えないこと |
|---|---|---|
| `tests/test_class_events.py` | `EVENT_CATEGORY_CLASS` の `import` の場所（付録Eの全文のとおり） | テストの中身（25件） |
| `tests/test_api_helpers.py` | `import` に新しい関数を足し、末尾にテストを足すこと（付録Fの全文のとおり） | 既存の112件 |

- このタスクでの「既存のテスト」は、作業の開始時からあるすべてのテスト（569件）。上の2ファイルの `import` を除き、変えない。**既存のテストが、想定外に失敗した場合**は、テストの期待値や、ほかの仕様を直さない。原因を調べ、そこで実装を止めて、チャットで報告する。特に、授業の `PATCH` の `{}` のテスト（`tests/test_subjects_update_delete_api.py` の `test_patch_empty_object_is_validation_error_without_fields`）は、変えずに通ること（`read_patch_object` に置き換えても、応答が同じことの確認）

## 実装手順
1. ブランチ・作業ツリーの確認。設計資料が更新されていることを確認する（「Copilot確認手順」の1の `grep`）。更新されていなければ、何も変更せずに停止して報告する
2. 作業の前の状態を記録する：開発用DBの有無・ハッシュ・件数（「Copilot確認手順」の1。**`sqlite3` は `-readonly` を付ける**）。`python -m pytest -q` が569件、すべて合格すること（合格しなければ、何も変更せずに停止して報告する）
3. **（段階1）** 「全文からファイルを作るスクリプト」を `python - 1` で実行する。`python -m pytest -q` が626件、すべて合格すること。「全文との比較」（「Copilot確認手順」の4）を `python - 1` で実行し、6ファイルとも「一致」
4. **（段階2）** スクリプトを `python - 2` で実行する。`python -m pytest -q` が787件、すべて合格すること。「全文との比較」を `python - 2` で実行し、9ファイルとも「一致」
5. 「Copilot確認手順」の2・3・5・6を実施する
6. 結果を報告して、応答を終える（コマンドの出力は、要約せずに、そのまま貼る。サーバーを起動していないこと、`curl` での確認をしていないことを明記する）

各段階の終わりに、`python -m pytest -q` の結果（件数・警告）と、全文との比較の結果を控えておく（最終報告に、出力をそのまま貼る）。

## 完了条件
- `python -m pytest -q` が、作業の前に **569件**、段階1の終わりに **626件**、段階2の終わりに **787件**、すべて合格する（失敗・エラー・スキップが0件）
- 変更・追加したファイルが、「実装対象ファイル」の9つだけ
- 9ファイルが、このTask MDの全文と1文字も違わない（「Copilot確認手順」の4が、段階1の終わりに6ファイル、段階2の終わりに9ファイルとも「一致」）
- `app/`・`tests/`・`run.py` のPythonのファイルに、79文字を超える行がない
- 実施の前後で、開発用DB（`instance/app.db`）のハッシュと、`semesters`・`subjects`・`closures`・`events`・`tasks` の件数が同じ
- 「Komaの確認」が、期待どおり
- レビューで承認される

## Copilot確認手順
**`sqlite3` は、必ず `-readonly` を付けて実行する**（011-L1）。**それぞれのコマンドの出力を、要約せずに、そのまま報告に貼る**（014-L1）。`grep` の「または」は、`-E` と `|` で書いてある（015-N1）。コマンドは、書いてあるとおりに実行する（書き換えた場合は、報告に書く）。

```
# 1. 実施前
git branch --show-current      # feature/016-tasks-api
git status                     # 変更なし
grep -n "### 課題・タスクAPI" docs/architecture.md                     # 1件
grep -n "#### カテゴリの保存値の置き場所" docs/architecture.md         # 1件
grep -n "categoryの入力の検証" docs/architecture.md                   # 出力なし（未決定事項から外れている）
grep -c -E "read_patch_object|validate_required_choice|validate_required_datetime" docs/architecture.md   # 1以上
grep -n "そのまま貼る" .github/copilot-instructions.md                 # 1件
ls -l instance/app.db          # 存在すること（なければ、何も変更せずに停止して報告する）
shasum -a 256 instance/app.db
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"
python -m pytest -q            # 569 passed

# 2. 各段階の終わり
python -m pytest -q            # 段階1：626 passed、段階2：787 passed
python -m pytest -q --co tests/test_api_helpers.py | tail -1               # 段階1・2：169 tests collected
python -m pytest -q --co tests/test_class_events.py | tail -1              # 段階1・2：25 tests collected
python -m pytest -q --co tests/test_subjects_update_delete_api.py | tail -1 # 段階1・2：86 tests collected
python -m pytest -q --co tests/test_tasks_api.py | tail -1                 # 段階2：161 tests collected

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

# 4. 全文との比較（011-N1・013-N1）。段階1の終わりは「python - 1」、段階2の終わりは「python - 2」
python - 1 <<'EOF'
import difflib
import re
import sys
from pathlib import Path

# 段階ごとのファイル（「全文からファイルを作るスクリプト」と同じ）。
STAGE_FILES = {
    "1": [
        "app/categories.py",
        "app/class_events.py",
        "app/api_helpers.py",
        "app/routes/subjects.py",
        "tests/test_class_events.py",
        "tests/test_api_helpers.py",
    ],
    "2": [
        "app/routes/tasks.py",
        "app/__init__.py",
        "tests/test_tasks_api.py",
    ],
}

stage = sys.argv[1]
# このTask MDの「<!-- 全文: パス -->」の直後のコードブロックを、
# そのファイルの期待する全文として取り出し、今のファイルと比べる。
fence = "`" * 3
task_text = Path("docs/tasks/016_tasks_api.md").read_text(encoding="utf-8")
pattern = re.compile(
    "<!-- 全文: (\\S+) -->\n" + fence + "[a-z]+\n(.*?)" + fence + "\n",
    re.S,
)
expected_files = dict(pattern.findall(task_text))
print(f"全文の数：{len(expected_files)}")
# その段階までに書き込んだファイルを、すべて比べる。
targets = [
    file_name
    for key in sorted(STAGE_FILES)
    if key <= stage
    for file_name in STAGE_FILES[key]
]
for file_name in targets:
    expected = expected_files[file_name]
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

# 5. 検索と差分（段階2の終わり）
grep -rn -E --include="*.py" '"(class|part_time|assignment|other)"' app/   # 7件：app/categories.py の定数5件と説明1件、app/class_events.py のコメント1件
grep -n "@tasks_bp\." app/routes/tasks.py                          # 5件：get・get・post・patch・delete の順
grep -n "commit()" app/routes/tasks.py                             # 3件：登録・編集・削除で1回ずつ
grep -rn --include="*.py" "read_patch_object()" app/              # 3件：api_helpers.py の定義、subjects.py と tasks.py の呼び出し
grep -rn --include="*.py" "変更する項目を指定してください" app/     # 1件：api_helpers.py の EMPTY_PATCH_MESSAGE
grep -rn -E --include="*.py" "date\.today|datetime\.now" app/        # 1件：app/routes/subjects.py の current_date の中
grep -rn -E --include="*.py" "cascade|ondelete" app/               # 出力なし
git diff --numstat app/__init__.py app/api_helpers.py app/class_events.py app/routes/subjects.py tests/test_api_helpers.py tests/test_class_events.py   # 6行：4 0（app/__init__.py）、116 1（app/api_helpers.py）、3 4（app/class_events.py）、3 7（app/routes/subjects.py）、247 1（tests/test_api_helpers.py）、1 1（tests/test_class_events.py）
git diff --stat -- app/models/ app/routes/semesters.py app/routes/closures.py app/routes/events.py app/routes/main.py app/static/ app/templates/ migrations/ tests/conftest.py tests/test_closures_api.py tests/test_events_api.py tests/test_semesters_api.py tests/test_setup.py tests/test_subjects_api.py tests/test_subjects_update_delete_api.py requirements.txt pytest.ini run.py   # 出力なし

# 6. 実施後
shasum -a 256 instance/app.db  # 実施前と同じ
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"   # 実施前と同じ
git status                     # 変更：6つ。新規：3つ
git diff --stat
```

| 確認 | 期待する結果 |
|---|---|
| `python -m pytest -q` | 実施前569件、段階1の終わり626件、段階2の終わり787件が、すべて合格。失敗・エラー・スキップが0件。`migrations/env.py` の `DeprecationWarning` は、出ても構わない（報告する） |
| 1行の長さ（3） | 出力なし |
| 全文との比較（4） | `全文の数：9` と、段階1の終わりは6ファイル、段階2の終わりは9ファイルとも「一致」。「不一致」が出たら、手で直さず、その段階の「全文からファイルを作るスクリプト」をもう一度実行して全文に戻し、2からやり直す（戻したことを報告する）。Task MDの全文のほうを変える必要があると判断した場合は、停止して報告する |
| 検索と差分（5） | 上のコメントのとおり（件数が違う場合は、その行を報告に書く） |
| 開発用DB | 実施の前後で、ハッシュと、5つのテーブルの件数が同じ |
| `git status` | 変更：`app/__init__.py`、`app/api_helpers.py`、`app/class_events.py`、`app/routes/subjects.py`、`tests/test_api_helpers.py`、`tests/test_class_events.py`。新規：`app/categories.py`、`app/routes/tasks.py`、`tests/test_tasks_api.py`。`app/models/`・`migrations/`・`app/static/`・`app/templates/`・`docs/`・`.github/`・`requirements.txt`・`run.py`・`instance/` に変更なし |

`.pytest_cache/` や `__pycache__/` が `git status` に表示される場合は、`.gitignore` を変更せず、報告する。**Copilotは、サーバーを起動せず、`curl` での確認もしない。** 報告に、そのことを明記する。

## Komaの確認
順序：（1）pytest →（2）commit・push とレビューの依頼 →（3）APIの確認（確認用のサーバー）→（4）マージ。**ブラウザでの確認は、このタスクにはない**（画面を変えないため。roadmap の「進め方の決定の記録」、2026-10-11）。

### 1. pytest
`python -m pytest -q` を自分で実行し、**787件、すべて合格**することを確かめる。

### 2. push とレビューの依頼
featureブランチを commit・push する（PRを作ってもよい）。Copilotの完了報告を共有して、Claudeにレビューを頼む。**pushは、マージではない。レビューの承認の前に、マージしない。** 修正が必要になった場合は、同じブランチでCopilotが直し、もう一度pushしてレビューを受ける。

### 3. APIの確認（確認用のサーバー）
レビューで「承認可能」になったあとに行う。**開発用DBは使わない。** 確認用のDB（`/tmp/schedule-app-check-016/check.db`）を、migrationで作り、そのDBで起動した確認用のサーバーに、`curl` で要求する（Task 012・014と同じ方法）。開発用DBには、何も残らない。課題・タスクのAPIは「今日」を使わないため、結果は、確認する日によらない。

#### 準備
1. `python run.py` が起動していれば、Ctrl＋Cで止める（確認用のサーバーも、5001番を使うため）。開発用DBのハッシュを控える
   ```
   shasum -a 256 instance/app.db
   ```
2. ブランチ `feature/016-tasks-api` のまま、リポジトリのルートで、`.venv` を有効にして、次を実行する（行の先頭に空白を入れずにコピーする。このターミナルは、確認の間、開いたままにする）

```
python - <<'EOF'
from pathlib import Path

from flask_migrate import upgrade

from app import create_app

# 確認用のDB（開発用DBとは別のファイル）。止めて起動し直しても、残る。
check_directory = Path("/tmp/schedule-app-check-016")
check_directory.mkdir(exist_ok=True)
database_path = check_directory / "check.db"
app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"})
with app.app_context():
    upgrade(directory="migrations")
print(f"確認用のDB：{database_path}", flush=True)
app.run(host="127.0.0.1", port=5001, debug=False)
EOF
```

期待する出力：`Running upgrade  -> 0280f6cf8d09, initial tables` と `Running upgrade 0280f6cf8d09 -> 42bd53808fa1, add closures table`、「確認用のDB：/tmp/schedule-app-check-016/check.db」、`Running on http://127.0.0.1:5001`。

3. 別のターミナルを開き、リポジトリのルートで、`.venv` を有効にして、`BASE=http://127.0.0.1:5001` を実行しておく

#### 確認（別のターミナルで、上から順に実行する）
C1・C2は、確認用のDBに、学期と授業を1件ずつ登録する。

```
# C1. 学期（2026-09-21〜2027-01-29）
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X POST $BASE/api/semesters -H 'Content-Type: application/json' -d '{"name": "2026年度 後期", "start_date": "2026-09-21", "end_date": "2027-01-29"}'
# C2. 月曜日の授業
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X POST $BASE/api/subjects -H 'Content-Type: application/json' -d '{"semester_id": 1, "subject_name": "テスト：月曜1限", "weekday": 0, "start_time": "09:00", "end_time": "10:30"}'
# C3. 課題の登録
curl -s -X POST $BASE/api/tasks -H 'Content-Type: application/json' -d '{"category": "assignment", "subject_id": 1, "title": "テスト：レポート第1回", "due_datetime": "2026-10-20T23:59", "notes": "A4で2枚"}' | python -m json.tool --no-ensure-ascii
# C4. その他（締切のみ）の登録
curl -s -X POST $BASE/api/tasks -H 'Content-Type: application/json' -d '{"category": "other", "title": "テスト：健康診断の予約", "due_datetime": "2026-10-19T17:00"}' | python -m json.tool --no-ensure-ascii
# C5. 一覧
curl -s $BASE/api/tasks | python -m json.tool --no-ensure-ascii
# C6. 課題を完了にする
curl -s -X PATCH $BASE/api/tasks/1 -H 'Content-Type: application/json' -d '{"is_completed": true}' | python -m json.tool --no-ensure-ascii
# C7. 完了の状態の絞り込み（IDだけを表示する。2つのコマンド）
curl -s "$BASE/api/tasks?is_completed=false" | python -c 'import json, sys; print([task["id"] for task in json.load(sys.stdin)])'
curl -s "$BASE/api/tasks?is_completed=true" | python -c 'import json, sys; print([task["id"] for task in json.load(sys.stdin)])'
# C8. カテゴリは変えられない
curl -s -X PATCH $BASE/api/tasks/1 -H 'Content-Type: application/json' -d '{"category": "other"}' | python -m json.tool --no-ensure-ascii
# C9. その他に授業を指定する
curl -s -X POST $BASE/api/tasks -H 'Content-Type: application/json' -d '{"category": "other", "subject_id": 1, "title": "x", "due_datetime": "2026-10-19T17:00"}' | python -m json.tool --no-ensure-ascii
# C10. 締切日時の形式の誤り（空白でつなぐ）
curl -s -X POST $BASE/api/tasks -H 'Content-Type: application/json' -d '{"category": "assignment", "subject_id": 1, "title": "x", "due_datetime": "2026-10-20 23:59"}' | python -m json.tool --no-ensure-ascii
# C11. 一覧のクエリの誤り
curl -s "$BASE/api/tasks?is_completed=yes" | python -m json.tool --no-ensure-ascii
# C12. 授業の1件取得（課題の件数）
curl -s $BASE/api/subjects/1 | python -m json.tool --no-ensure-ascii
# C13. 授業の科目名を変えると、課題の subject_name も変わる（2つのコマンド）
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X PATCH $BASE/api/subjects/1 -H 'Content-Type: application/json' -d '{"subject_name": "テスト：月曜2限"}'
curl -s $BASE/api/tasks/1 | python -m json.tool --no-ensure-ascii
# C14. その他の削除と、削除のあとの1件取得（2つのコマンド）
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X DELETE $BASE/api/tasks/2
curl -s $BASE/api/tasks/2 | python -m json.tool --no-ensure-ascii
# C15. 授業の削除と、削除のあとの一覧（2つのコマンド）
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X DELETE $BASE/api/subjects/1
curl -s $BASE/api/tasks; echo
```

| No | 期待する結果 |
|---|---|
| C1・C2 | `HTTP 201` |
| C3 | `"id": 1`、`"category": "assignment"`、`"subject_id": 1`、`"subject_name": "テスト：月曜1限"`、`"title": "テスト：レポート第1回"`、`"due_datetime": "2026-10-20T23:59"`、`"notes": "A4で2枚"`、`"is_completed": false` |
| C4 | `"id": 2`、`"category": "other"`、`"subject_id": null`、`"subject_name": null`、`"due_datetime": "2026-10-19T17:00"`、`"notes": null`、`"is_completed": false` |
| C5 | 2件。締切日時の順で、1件目が `"id": 2`（10/19）、2件目が `"id": 1`（10/20）。各要素は、C3・C4の応答と同じ |
| C6 | C3の応答で、`"is_completed": true` だけが違う |
| C7 | 1つ目：`[2]`、2つ目：`[1]` |
| C8 | `validation_error`、`fields` に `"category": "この項目は指定できません"` だけ |
| C9 | `validation_error`、`fields` に `"subject_id": "その他（締切のみ）には、授業を指定できません"` だけ |
| C10 | `validation_error`、`fields` に `"due_datetime": "締切日時は実在する日時を「YYYY-MM-DDTHH:MM」の形式で指定してください"` だけ |
| C11 | `validation_error`、`fields` に `"is_completed": "完了の状態は「true」か「false」で指定してください"` だけ |
| C12 | `"task_count": 1`（その他は、授業に結びつかないため数えない）、`"event_count": 19` |
| C13 | 1つ目：`HTTP 200`。2つ目：`"subject_name": "テスト：月曜2限"`（ほかの項目は、C6の応答と同じ） |
| C14 | 1つ目：`HTTP 204`。2つ目：`not_found`、`"message": "課題・タスクが見つかりません"` |
| C15 | 1つ目：`HTTP 204`。2つ目：`[]`（授業の削除で、その授業の課題も削除された） |

（応答の項目は、Flaskが項目名の順に並べて返すため、表示の順は、設計資料の例と違う。中身が同じなら、期待どおり）

#### 後片付け
1. 確認用のサーバーを止める（Ctrl＋C）
2. 確認用のDBのフォルダを消す
   ```
   rm -r /tmp/schedule-app-check-016
   ```
3. 開発用DBのハッシュが、準備の1と同じことを確かめる
   ```
   shasum -a 256 instance/app.db
   ```

ハッシュが変わっていた場合は、開発用DBを操作せずに、Claudeに伝える。

### 4. マージ
1〜3が期待どおりで、レビューで承認されたら、マージする。このタスクは、DBの構造を変えないため、開発用DBへのmigrationの適用はない。開発用DBのデータも変えないため、バックアップは要らない。

マージのあとは、開発用DBのサーバー（`python run.py`）でも、課題・タスクのAPIが使える。画面はまだないため、開発用DBの課題・タスクを、APIで登録・編集・削除する場合は、先にバックアップを取る（`docs/architecture.md` の「開発中の注意」）。

## Git操作
**Git commit / push / ブランチ操作 / マージは行わない**（`git branch --show-current`、`git status`、`git diff` のような読み取りだけのコマンドは除く）。

## 注意
- **停止して報告する条件**（ファイルを変更せず、実装を止め、チャットで「問題点・発生理由・変更した場合の影響・推奨案（必要なら）」を報告する）
  - ブランチの不一致、作業ツリーの想定外の変更
  - 設計資料が更新されていない（実装手順の1）、または、設計資料とこのTask MDの間に、矛盾・不足がある
  - 設計資料にない判断が必要になった（特に、`docs/architecture.md` の「未決定事項」に触れる場合）
  - 「全文からファイルを作るスクリプト」の出力が、期待と違う（全文の数・行数・エラー）
  - 「変更しない」と定めたもの（モデル、ほかのroute、画面のファイル、既存のテストなど）を変更しないと実装できない。または、9ファイルの全文を変える必要があると判断した
  - 開発用DB（`instance/app.db`）がない
  - 作業の前の `python -m pytest` が、569件すべて合格しない
  - **既存のテスト**（作業の開始時からある569件）**が、想定外に失敗した**。テストの期待値や、ほかの仕様を直さずに、原因を調べて報告する
  - DBの構造の変更（migration）や、モデルの変更、ライブラリの追加、このTask MDに書いたもの以外のAPIの変更が必要だと判断した
  - 実施の前後で、`instance/app.db` が変わった
- **止まるときは、報告を書いて、その応答を終える。質問の機能は使わない。** 再開するのは、Komaの新しいメッセージが、判断や再開を明確に示したときだけ（無回答や「続けて」だけの返事は、再開の指示ではない）。`.github/copilot-instructions.md` の「止まる場面の応答」
- **開発用DBを `sqlite3` で開くときは、必ず `-readonly` を付ける**（SELECTだけでも、付けずに開かない。011-L1）。`flask db` のコマンドを、一切実行しない。ライブラリを追加しない。サーバーを起動しない（`python run.py` も、「Komaの確認」の確認用のサーバーも）
- 期待する結果と異なる結果が出た場合は、確認を飛ばさず、原因を直してから、すべての確認をやり直す（ただし、既存のテストの想定外の失敗は、上の停止の条件に従う。全文との「不一致」は、手で直さず、スクリプトで全文に戻す）
- 設計資料に書かれていない仕様は、自分で決めない
- **最後の報告には、次を含め、コマンドの出力は、要約せずに、そのまま貼る**（014-L1）：変更・追加したファイル、「全文からファイルを作るスクリプト」の出力（段階1・2）、作業の前と各段階の `pytest` の件数と警告（最後の行）、テストの件数の確認（「Copilot確認手順」の2の `--co`）の出力、1行の長さの確認の出力、全文との比較の出力（段階1：6ファイル、段階2：9ファイルの「一致」。スクリプトで全文に戻した場合は、そのこと）、検索と差分の出力（各コマンドと、その出力）、開発用DBの前後のハッシュ・件数、`git status`・`git diff --stat` の出力、サーバーの起動と `curl` の確認をしていないこと、気になった点

## 付録：全文
「全文からファイルを作るスクリプト」と「全文との比較」が使う。各ファイルの全文は、「`<!-- 全文: パス -->`」の印の直後のコードブロック。**この付録を、手で書き写さない。** 本文の要点・差分と食い違う場合は、作業をせずに停止して報告する。

### 付録A. `app/categories.py`

<!-- 全文: app/categories.py -->
```python
"""カテゴリの保存値（DBの category の値）と、APIで受け付ける値の一覧。

カテゴリの保存値は、このファイルの定数だけで持ち、ほかのファイルに
文字列（"class" など）を直接書かない。画面に出す表示名・色・アイコンは、
画面側の対応表（app/static/js/categories.js）で持つ。
"""

# 予定（Event）のカテゴリ。
EVENT_CATEGORY_CLASS = "class"
EVENT_CATEGORY_PART_TIME = "part_time"
EVENT_CATEGORY_OTHER = "other"

# 予定のAPIで category を受け付けるときの許可値（予定の登録・編集を
# 作るタスクで使う）。
EVENT_CATEGORIES = (
    EVENT_CATEGORY_CLASS,
    EVENT_CATEGORY_PART_TIME,
    EVENT_CATEGORY_OTHER,
)

# 課題・タスク（Task）のカテゴリ。
TASK_CATEGORY_ASSIGNMENT = "assignment"
TASK_CATEGORY_OTHER = "other"

# 課題・タスクのAPIで category を受け付けるときの許可値。
TASK_CATEGORIES = (
    TASK_CATEGORY_ASSIGNMENT,
    TASK_CATEGORY_OTHER,
)
```

### 付録B. `app/class_events.py`

<!-- 全文: app/class_events.py -->
```python
"""授業の予定（Event）の生成。

授業の登録、休講日の削除による予定の作成、授業全体の編集による
予定の作り直しから使う部品。
DBの読み書き（セッションへの追加・commit）は行わない。休講日の日付の
取得と、データの保存は、各routeが担当する。「今日」の日付も、この
ファイルでは求めない（作り直しの開始日は、routeが引数で渡す）。
"""

from datetime import date, timedelta

# 授業の予定のカテゴリの保存値は、app/categories.py の定数を使う
# （文字列 "class" を、ほかの場所に直接書かない）。
from app.categories import EVENT_CATEGORY_CLASS
from app.models.event import Event
from app.models.semester import Semester
from app.models.subject import Subject


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


def build_class_events_from(
    subject: Subject,
    semester: Semester,
    excluded_dates: set[date],
    from_date: date,
) -> list[Event]:
    """from_date以降の、授業の自動生成の予定を作る（セッションには追加しない）。

    授業全体の編集による作り直しで使う。対象の期間は、from_date（含む）と
    学期の開始日の遅いほうから、学期の終了日まで。from_dateが学期の
    終了日より後なら、空の一覧を返す。
    """
    start_date = max(from_date, semester.start_date)
    dates = class_event_dates(
        start_date,
        semester.end_date,
        subject.weekday,
        excluded_dates,
    )
    return [build_class_event(subject, event_date) for event_date in dates]
```

### 付録C. `app/api_helpers.py`

<!-- 全文: app/api_helpers.py -->
```python
import re
from collections.abc import Collection
from datetime import date, datetime, time
from typing import Any

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import BadRequest, HTTPException, InternalServerError


# IDの上限（SQLiteのINTEGERの最大値）。これを超える数をDBに渡すとエラーになるため、IDを受け取るURLでは、この値までに制限する
MAX_ID = 2**63 - 1

ERROR_STATUS_CODES = {
    "invalid_json": 400,
    "validation_error": 400,
    "not_found": 404,
    "method_not_allowed": 405,
    "server_error": 500,
}

INVALID_JSON_MESSAGE = (
    "リクエストの本文がJSONとして読めません。"
    "Content-Typeを application/json にして、JSONで送ってください"
)
UNUSABLE_CHARACTER_MESSAGE = "使用できない文字が含まれています"
EMPTY_PATCH_MESSAGE = "変更する項目を指定してください"


def contains_unusable_character(value: str) -> bool:
    """UTF-8に変換できない孤立サロゲートが含まれるか確認する。"""
    return any(
        0xD800 <= ord(character) <= 0xDFFF
        for character in value
    )


def api_error_response(
    code: str,
    message: str,
    fields: dict[str, str] | None = None,
) -> tuple[Response, int]:
    """共通形式のAPIエラーレスポンスを作る。"""
    error: dict[str, Any] = {"code": code, "message": message}
    if fields is not None:
        error["fields"] = fields
    return jsonify({"error": error}), ERROR_STATUS_CODES[code]


def is_api_path(path: str) -> bool:
    """APIのエラーだけをJSONにするため、パスの境界を確認する。"""
    return path == "/api" or path.startswith("/api/")


def register_api_error_handlers(app: Flask) -> None:
    """APIの404・405・500をJSON形式で返すハンドラーを登録する。"""

    @app.errorhandler(404)
    def handle_not_found(error: HTTPException):
        # API以外の画面には影響させず、Flask標準のHTMLエラーを維持する。
        if not is_api_path(request.path):
            return error

        # URLそのものが存在しない場合のメッセージ。データが存在しない場合は、各routeが返す。
        return api_error_response("not_found", "URLが見つかりません")

    @app.errorhandler(405)
    def handle_method_not_allowed(error: HTTPException):
        if not is_api_path(request.path):
            return error
        return api_error_response(
            "method_not_allowed",
            "このURLでは、そのメソッドは使えません",
        )

    @app.errorhandler(InternalServerError)
    def handle_internal_server_error(error: InternalServerError):
        if not is_api_path(request.path):
            return error
        return api_error_response(
            "server_error",
            "サーバーでエラーが発生しました",
        )


def read_json_object() -> tuple[
    dict[str, Any] | None,
    tuple[Response, int] | None,
]:
    """application/jsonの本文を読み、JSONオブジェクトだけを受け付ける。"""
    if request.mimetype != "application/json":
        return None, api_error_response("invalid_json", INVALID_JSON_MESSAGE)

    try:
        # silent=TrueではJSONのnullと解析失敗が同じNoneになるため、例外で判別する。
        payload = request.get_json()
    except BadRequest:
        return None, api_error_response("invalid_json", INVALID_JSON_MESSAGE)

    if not isinstance(payload, dict):
        return None, api_error_response(
            "validation_error",
            "リクエストの本文は、JSONのオブジェクトにしてください",
        )
    return payload, None


def read_patch_object() -> tuple[
    dict[str, Any] | None,
    tuple[Response, int] | None,
]:
    """PATCHの本文を読み、項目が1つもないオブジェクト（{}）を誤りにする。

    本文の読み取りは、read_json_object と同じ。{} は、特定の項目に
    結びつかない誤りのため、fields を付けない。
    """
    payload, error_response = read_json_object()
    if error_response is not None:
        return None, error_response
    if not payload:
        return None, api_error_response(
            "validation_error",
            EMPTY_PATCH_MESSAGE,
        )
    return payload, None


def read_id_query(
    name: str,
    multiple_message: str,
    format_message: str,
) -> tuple[bool, int | None, str | None]:
    """一覧の絞り込みのクエリで指定されたIDを読み取る。

    戻り値は、（指定の有無、ID、エラーメッセージ）の組。
    - 指定がない：(False, None, None)
    - 2回以上の指定：(True, None, multiple_message)
    - 数字だけでない（空文字・符号・小数・全角数字・空白など）：
      (True, None, format_message)
    - 数字だけだが、1〜MAX_IDの外（0、MAX_IDより大きい数）：
      (True, None, None)。該当するデータがないため、呼び出し側は、
      DBに問い合わせずに、空の一覧を返す
    - それ以外：(True, ID, None)
    DBは読まない（IDのデータが存在するかは、確かめない）。
    """
    values = request.args.getlist(name)
    if not values:
        return False, None, None
    if len(values) > 1:
        return True, None, multiple_message

    text = values[0]
    if re.fullmatch(r"[0-9]+", text) is None:
        return True, None, format_message

    # MAX_IDより大きい数をDBに渡すとOverflowErrorになり、非常に長い
    # 数字の文字列をint()に渡すとValueErrorになるため、int()の前に、
    # 先頭の0を取り除いた桁数と値で、MAX_IDと比べる。
    normalized_text = text.lstrip("0")
    maximum_text = str(MAX_ID)
    if normalized_text == "" or len(normalized_text) > len(maximum_text):
        return True, None, None
    if (
        len(normalized_text) == len(maximum_text)
        and normalized_text > maximum_text
    ):
        return True, None, None
    return True, int(normalized_text), None


def validate_allowed_fields(
    payload: dict[str, Any],
    allowed_fields: set[str],
) -> dict[str, str]:
    """許可されていない項目や読み取り専用項目をエラーにする。"""
    return {
        field: "この項目は指定できません"
        for field in payload
        if field not in allowed_fields
    }


def validate_required_string(
    payload: dict[str, Any],
    field: str,
    required_message: str,
    type_message: str,
    *,
    max_length: int | None = None,
    length_message: str | None = None,
    strip: bool = False,
) -> tuple[str | None, str | None]:
    """必須文字列を検査し、値またはエラーメッセージを返す。

    使用できない文字（孤立サロゲート）を含む場合は、
    UNUSABLE_CHARACTER_MESSAGEを返す。この検査は、引数の指定に関係なく、
    型の検査のあと、前後の空白の除去と長さの検査より前に、常に行う。
    """
    if max_length is not None and length_message is None:
        raise ValueError("max_lengthを指定する場合はlength_messageが必要です")

    value = payload.get(field)
    if field not in payload or value is None or value == "":
        return None, required_message
    if not isinstance(value, str):
        return None, type_message
    if contains_unusable_character(value):
        return None, UNUSABLE_CHARACTER_MESSAGE
    if strip:
        value = value.strip()
        if value == "":
            return None, required_message
    if max_length is not None and len(value) > max_length:
        return None, length_message
    return value, None


def validate_optional_string(
    payload: dict[str, Any],
    field: str,
    type_message: str,
    *,
    max_length: int | None = None,
    length_message: str | None = None,
) -> tuple[str | None, str | None]:
    """任意文字列を検査して正規化し、値またはエラーを返す。

    使用できない文字（孤立サロゲート）を含む場合は、
    UNUSABLE_CHARACTER_MESSAGEを返す。この検査は、引数の指定に関係なく、
    型の検査のあと、前後の空白の除去と長さの検査より前に、常に行う。
    """
    if max_length is not None and length_message is None:
        raise ValueError("max_lengthを指定する場合はlength_messageが必要です")

    value = payload.get(field)
    if field not in payload or value is None:
        return None, None
    if not isinstance(value, str):
        return None, type_message
    if contains_unusable_character(value):
        return None, UNUSABLE_CHARACTER_MESSAGE

    value = value.strip()
    if value == "":
        return None, None
    if max_length is not None and len(value) > max_length:
        return None, length_message
    return value, None


def validate_required_integer(
    payload: dict[str, Any],
    field: str,
    required_message: str,
    type_message: str,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
    range_message: str | None = None,
) -> tuple[int | None, str | None]:
    """必須整数を検査し、必要に応じて範囲も確認する。"""
    value = payload.get(field)
    if field not in payload or value is None or value == "":
        return None, required_message
    if isinstance(value, bool) or not isinstance(value, int):
        return None, type_message
    if (
        (min_value is not None and value < min_value)
        or (max_value is not None and value > max_value)
    ):
        return None, range_message or type_message
    return value, None


def validate_required_boolean(
    payload: dict[str, Any],
    field: str,
    required_message: str,
    type_message: str,
) -> tuple[bool | None, str | None]:
    """必須の真偽値を検査する。JSONの true・false だけを受け付ける。

    数値（0・1）や文字列（"true" など）は、型の誤りにする。
    """
    value = payload.get(field)
    if field not in payload or value is None or value == "":
        return None, required_message
    if not isinstance(value, bool):
        return None, type_message
    return value, None


def validate_required_choice(
    payload: dict[str, Any],
    field: str,
    choices: Collection[str],
    required_message: str,
    choice_message: str,
) -> tuple[str | None, str | None]:
    """決まった値（choices）の中から選ぶ、必須の文字列を検査する。

    カテゴリ（category）に使う。choices のどれかと完全に一致する文字列
    だけを受け付ける（前後の空白を取り除かない）。文字列でない値と、
    choices にない値は、どちらも choice_message を返す。使用できない
    文字（孤立サロゲート）を含む場合は、UNUSABLE_CHARACTER_MESSAGE を返す。
    """
    value = payload.get(field)
    if field not in payload or value is None or value == "":
        return None, required_message
    if not isinstance(value, str):
        return None, choice_message
    if contains_unusable_character(value):
        return None, UNUSABLE_CHARACTER_MESSAGE
    if value not in choices:
        return None, choice_message
    return value, None


def parse_time(value: Any) -> time | None:
    """HH:MMの厳密な形式と時刻の範囲を確認して変換する。"""
    if not isinstance(value, str):
        return None
    if re.fullmatch(r"[0-9]{2}:[0-9]{2}", value) is None:
        return None

    hour, minute = (int(part) for part in value.split(":"))
    try:
        return time(hour, minute)
    except ValueError:
        return None


def format_time(value: time) -> str:
    """時刻をAPIのHH:MM形式にする。"""
    return value.strftime("%H:%M")


def validate_required_time(
    payload: dict[str, Any],
    field: str,
    required_message: str,
    format_message: str,
) -> tuple[time | None, str | None]:
    """必須時刻を検査し、Pythonのtimeかエラーメッセージを返す。

    使用できない文字（孤立サロゲート）を含む場合は、
    UNUSABLE_CHARACTER_MESSAGEを返す。この検査は、型の検査のあと、
    形式の検査より前に、常に行う。
    """
    value = payload.get(field)
    if field not in payload or value is None or value == "":
        return None, required_message
    if not isinstance(value, str):
        return None, format_message
    if contains_unusable_character(value):
        return None, UNUSABLE_CHARACTER_MESSAGE

    parsed_value = parse_time(value)
    if parsed_value is None:
        return None, format_message
    return parsed_value, None


def parse_date(value: Any) -> date | None:
    """YYYY-MM-DDの形式と実在性を確認して日付に変換する。"""
    if not isinstance(value, str):
        return None

    # fromisoformatは区切りのない日付も受理するため、先に厳密な形式を確認する。
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def format_date(value: date) -> str:
    """日付をAPIのYYYY-MM-DD形式にする。"""
    return value.isoformat()


def validate_required_date(
    payload: dict[str, Any],
    field: str,
    required_message: str,
    format_message: str,
) -> tuple[date | None, str | None]:
    """必須の日付を検査し、Pythonのdateかエラーメッセージを返す。

    文字列でない値は、時刻と同じく、format_messageを返す。
    使用できない文字（孤立サロゲート）を含む場合は、
    UNUSABLE_CHARACTER_MESSAGEを返す。この検査は、型の検査のあと、
    形式の検査より前に、常に行う。
    """
    value = payload.get(field)
    if field not in payload or value is None or value == "":
        return None, required_message
    if not isinstance(value, str):
        return None, format_message
    if contains_unusable_character(value):
        return None, UNUSABLE_CHARACTER_MESSAGE

    parsed_value = parse_date(value)
    if parsed_value is None:
        return None, format_message
    return parsed_value, None


def parse_datetime(value: Any) -> datetime | None:
    """YYYY-MM-DDTHH:MMの形式と実在性を確認して日時に変換する。"""
    if not isinstance(value, str):
        return None

    # fromisoformatは秒や別の書式も受理するため、先に厳密な形式を確認する。
    if (
        re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}", value)
        is None
    ):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def format_datetime(value: datetime) -> str:
    """日時をAPIのYYYY-MM-DDTHH:MM形式にする（秒は出さない）。"""
    return value.isoformat(timespec="minutes")


def validate_required_datetime(
    payload: dict[str, Any],
    field: str,
    required_message: str,
    format_message: str,
) -> tuple[datetime | None, str | None]:
    """必須の日時を検査し、Pythonのdatetimeかエラーメッセージを返す。

    文字列でない値は、日付・時刻と同じく、format_messageを返す。
    使用できない文字（孤立サロゲート）を含む場合は、
    UNUSABLE_CHARACTER_MESSAGEを返す。この検査は、型の検査のあと、
    形式の検査より前に、常に行う。
    """
    value = payload.get(field)
    if field not in payload or value is None or value == "":
        return None, required_message
    if not isinstance(value, str):
        return None, format_message
    if contains_unusable_character(value):
        return None, UNUSABLE_CHARACTER_MESSAGE

    parsed_value = parse_datetime(value)
    if parsed_value is None:
        return None, format_message
    return parsed_value, None
```

### 付録D. `app/routes/subjects.py`

<!-- 全文: app/routes/subjects.py -->
```python
from datetime import date
from typing import Any

from flask import Blueprint, jsonify

from app.api_helpers import (
    MAX_ID,
    api_error_response,
    format_time,
    read_id_query,
    read_json_object,
    read_patch_object,
    validate_allowed_fields,
    validate_optional_string,
    validate_required_integer,
    validate_required_string,
    validate_required_time,
)
from app.class_events import build_class_events, build_class_events_from
from app.extensions import db
from app.models.closure import Closure
from app.models.event import Event
from app.models.semester import Semester
from app.models.subject import Subject
from app.models.task import Task


subjects_bp = Blueprint(
    "subjects",
    __name__,
    url_prefix="/api/subjects",
)

# 授業の編集（PATCH）で受け付ける項目。学期（semester_id）は、変えられない
# （誤った場合は、授業を削除して、正しい学期に登録し直す）。
UPDATE_FIELDS = {
    "subject_name",
    "room",
    "weekday",
    "start_time",
    "end_time",
    "notes",
}
# 授業の登録（POST）で受け付ける項目。
CREATE_FIELDS = UPDATE_FIELDS | {"semester_id"}

END_TIME_ORDER_MESSAGE = "終了時刻は開始時刻より後にしてください"


def subject_to_dict(subject: Subject) -> dict[str, Any]:
    """授業をAPIレスポンス用の辞書に変換する。"""
    return {
        "id": subject.id,
        "semester_id": subject.semester_id,
        "subject_name": subject.subject_name,
        "room": subject.room,
        "weekday": subject.weekday,
        "start_time": format_time(subject.start_time),
        "end_time": format_time(subject.end_time),
        "notes": subject.notes,
    }


def current_date() -> date:
    """授業全体の編集で、予定を作り直す基準の「今日」を返す。

    サーバー（Flaskを動かしているPC）のローカルの日付。テストで日付を
    固定できるように、関数にしておく（テストでは、monkeypatch で
    置き換える）。
    """
    return date.today()


def validate_subject_values(
    payload: dict[str, Any],
    *,
    partial: bool,
) -> tuple[dict[str, Any], dict[str, str]]:
    """授業の項目（学期を除く）を検査し、（値、エラー）の組を返す。

    登録（POST）と編集（PATCH）で、同じ規則で検査するために使う。
    - partial=False（登録）：すべての項目を検査する。必須の項目が
      本文になければ、必須のエラーにする
    - partial=True（編集）：本文に含まれる項目だけを検査する。含まれない
      項目は、値にもエラーにも入れない（今の値のまま変えない）
    値は、誤りのない項目だけを入れる（キーは、Subjectの列の名前と同じ）。
    開始時刻と終了時刻の前後の検査は、呼び出し側が行う（編集では、
    今の値と組み合わせて比べるため）。
    """
    values: dict[str, Any] = {}
    errors: dict[str, str] = {}

    if not partial or "subject_name" in payload:
        subject_name, error = validate_required_string(
            payload,
            "subject_name",
            "科目名は必須です",
            "科目名は文字列で指定してください",
            strip=True,
            max_length=100,
            length_message="科目名は100文字以内にしてください",
        )
        if error is None:
            values["subject_name"] = subject_name
        else:
            errors["subject_name"] = error

    if not partial or "room" in payload:
        room, error = validate_optional_string(
            payload,
            "room",
            "教室は文字列で指定してください",
            max_length=100,
            length_message="教室は100文字以内にしてください",
        )
        if error is None:
            values["room"] = room
        else:
            errors["room"] = error

    if not partial or "weekday" in payload:
        weekday, error = validate_required_integer(
            payload,
            "weekday",
            "曜日は必須です",
            "曜日は0（月曜）〜6（日曜）の整数で指定してください",
            min_value=0,
            max_value=6,
            range_message="曜日は0（月曜）〜6（日曜）の整数で指定してください",
        )
        if error is None:
            values["weekday"] = weekday
        else:
            errors["weekday"] = error

    if not partial or "start_time" in payload:
        start_time, error = validate_required_time(
            payload,
            "start_time",
            "開始時刻は必須です",
            "開始時刻は「HH:MM」の形式（00:00〜23:59）で指定してください",
        )
        if error is None:
            values["start_time"] = start_time
        else:
            errors["start_time"] = error

    if not partial or "end_time" in payload:
        end_time, error = validate_required_time(
            payload,
            "end_time",
            "終了時刻は必須です",
            "終了時刻は「HH:MM」の形式（00:00〜23:59）で指定してください",
        )
        if error is None:
            values["end_time"] = end_time
        else:
            errors["end_time"] = error

    if not partial or "notes" in payload:
        notes, error = validate_optional_string(
            payload,
            "notes",
            "詳細・メモは文字列で指定してください",
        )
        if error is None:
            values["notes"] = notes
        else:
            errors["notes"] = error

    return values, errors


def semester_closure_dates(semester_id: int) -> set[date]:
    """学期の休講日の日付を返す（予定を作らない日）。"""
    return set(
        db.session.scalars(
            db.select(Closure.date).where(Closure.semester_id == semester_id)
        )
    )


def delete_generated_events_from(subject_id: int, from_date: date) -> None:
    """授業の、from_date以降の自動生成の予定を削除する（commitしない）。

    授業全体の編集による作り直しで使う。単発の予定（is_generated=False）と、
    from_dateより前の予定は削除しない。
    """
    db.session.execute(
        db.delete(Event).where(
            Event.subject_id == subject_id,
            Event.is_generated.is_(True),
            Event.date >= from_date,
        )
    )


def count_subject_events(subject_id: int) -> int:
    """授業の予定（自動生成・単発とも、過去分を含む）の件数を返す。"""
    return db.session.scalar(
        db.select(db.func.count())
        .select_from(Event)
        .where(Event.subject_id == subject_id)
    )


def count_subject_tasks(subject_id: int) -> int:
    """授業の課題の件数を返す。"""
    return db.session.scalar(
        db.select(db.func.count())
        .select_from(Task)
        .where(Task.subject_id == subject_id)
    )


@subjects_bp.get("")
def get_subjects():
    specified, semester_id, query_error = read_id_query(
        "semester_id",
        "学期IDは1つだけ指定してください",
        "学期IDは整数で指定してください",
    )
    if query_error is not None:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            {"semester_id": query_error},
        )

    statement = db.select(Subject)
    if specified:
        if semester_id is None:
            # 範囲外のIDに当たる学期はないため、空の一覧を返す。
            return jsonify([])
        statement = statement.where(Subject.semester_id == semester_id)

    statement = statement.order_by(
        Subject.weekday.asc(),
        Subject.start_time.asc(),
        Subject.id.asc(),
    )
    subjects = db.session.scalars(statement).all()
    return jsonify([subject_to_dict(subject) for subject in subjects])


@subjects_bp.get(f"/<int(max={MAX_ID}):subject_id>")
def get_subject(subject_id: int):
    subject = db.session.get(Subject, subject_id)
    if subject is None:
        return api_error_response("not_found", "授業が見つかりません")

    response = subject_to_dict(subject)
    # 1件取得のレスポンスにだけ付ける付加情報（DBには保存しない）。
    # 授業を削除すると一緒に削除される件数で、削除の確認に使う。
    response["event_count"] = count_subject_events(subject.id)
    response["task_count"] = count_subject_tasks(subject.id)
    return jsonify(response)


@subjects_bp.post("")
def create_subject():
    payload, error_response = read_json_object()
    if error_response is not None:
        return error_response

    fields: dict[str, str] = {}
    semester: Semester | None = None

    semester_id, semester_id_error = validate_required_integer(
        payload,
        "semester_id",
        "学期IDは必須です",
        "学期IDは整数で指定してください",
    )
    if semester_id_error is not None:
        fields["semester_id"] = semester_id_error
    elif semester_id is not None:
        # 範囲外のIDをDBに渡すと、SQLiteでOverflowErrorになるため先に確認する。
        if not 1 <= semester_id <= MAX_ID:
            fields["semester_id"] = "指定された学期が存在しません"
        else:
            semester = db.session.get(Semester, semester_id)
            if semester is None:
                fields["semester_id"] = "指定された学期が存在しません"

    values, value_errors = validate_subject_values(payload, partial=False)
    fields.update(value_errors)

    start_time = values.get("start_time")
    end_time = values.get("end_time")
    # 前後の検査は、開始時刻と終了時刻の両方に誤りがないときだけ行う。
    if (
        start_time is not None
        and end_time is not None
        and end_time <= start_time
    ):
        fields["end_time"] = END_TIME_ORDER_MESSAGE

    fields.update(validate_allowed_fields(payload, CREATE_FIELDS))

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    # 予定を作らない日（学期の休講日）を、先に取得する。
    excluded_dates = semester_closure_dates(semester.id)

    subject = Subject(
        semester_id=semester_id,
        subject_name=values["subject_name"],
        room=values["room"],
        weekday=values["weekday"],
        start_time=start_time,
        end_time=end_time,
        notes=values["notes"],
    )
    db.session.add(subject)
    events = build_class_events(subject, semester, excluded_dates)
    # 予定も、明示的に追加する。授業を先に追加したあとで作った予定は、
    # 授業との関係だけではセッションに入らず、エラーにならないまま
    # 保存されないため。
    db.session.add_all(events)
    # 授業と予定を1回のcommitで保存する。commitの前に例外が起きた場合は、
    # どちらも保存されない。
    db.session.commit()

    response = subject_to_dict(subject)
    # 作成のレスポンスにだけ付ける付加情報（DBには保存しない）。
    response["generated_event_count"] = len(events)
    return jsonify(response), 201


@subjects_bp.patch(f"/<int(max={MAX_ID}):subject_id>")
def update_subject(subject_id: int):
    # 対象の授業がなければ、本文を読む前に404にする。
    subject = db.session.get(Subject, subject_id)
    if subject is None:
        return api_error_response("not_found", "授業が見つかりません")

    # 項目が1つもない本文（{}）も、誤りにする（API共通ルール）。
    payload, error_response = read_patch_object()
    if error_response is not None:
        return error_response

    values, fields = validate_subject_values(payload, partial=True)

    # 前後の検査は、変更後の値どうしで行う。本文に含まれない時刻は、
    # 今の値を使う。本文の時刻に誤りがあれば、検査しない。
    if "start_time" not in fields and "end_time" not in fields:
        start_time = values.get("start_time", subject.start_time)
        end_time = values.get("end_time", subject.end_time)
        if end_time <= start_time:
            fields["end_time"] = END_TIME_ORDER_MESSAGE

    fields.update(validate_allowed_fields(payload, UPDATE_FIELDS))

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    # 本文に含まれていた項目だけを、授業に書き込む
    # （values のキーは、Subjectの列の名前と同じ）。
    for field_name, value in values.items():
        setattr(subject, field_name, value)

    # 今日以降の自動生成の予定を、授業の新しい値で作り直す。
    # 変わった項目によらず、毎回作り直す（個別に変更・削除した日も、
    # 設定どおりに戻すため）。単発の予定と、今日より前の予定は変えない。
    today = current_date()
    delete_generated_events_from(subject.id, today)
    events = build_class_events_from(
        subject,
        subject.semester,
        semester_closure_dates(subject.semester_id),
        today,
    )
    # 予定は、明示的に追加する（授業との関係だけでは、セッションに入らない）。
    db.session.add_all(events)
    # 授業の更新と、予定の削除・作成を、1回のcommitで保存する。
    db.session.commit()
    return jsonify(subject_to_dict(subject))


@subjects_bp.delete(f"/<int(max={MAX_ID}):subject_id>")
def delete_subject(subject_id: int):
    subject = db.session.get(Subject, subject_id)
    if subject is None:
        return api_error_response("not_found", "授業が見つかりません")

    # 授業に結びつく予定（自動生成・単発とも、過去分を含む）と課題を、
    # 授業より先に、明示的に削除する（「データ設計」の「共通の約束」）。
    # 授業だけを削除すると、予定と課題が、subject_id が NULL の行として残る。
    db.session.execute(db.delete(Event).where(Event.subject_id == subject.id))
    db.session.execute(db.delete(Task).where(Task.subject_id == subject.id))
    db.session.delete(subject)
    # 予定・課題・授業の削除を、1回のcommitで保存する。
    db.session.commit()
    return "", 204
```

### 付録E. `tests/test_class_events.py`

<!-- 全文: tests/test_class_events.py -->
```python
from datetime import date, time, timedelta

import pytest

from app.categories import EVENT_CATEGORY_CLASS
from app.class_events import (
    build_class_event,
    build_class_events,
    build_class_events_from,
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


# --- 授業全体の編集による作り直し（build_class_events_from） ---


def test_build_class_events_from_includes_from_date():
    subject = make_subject()

    # 2026-06-15は月曜日。その日を含む。
    events = build_class_events_from(
        subject, make_semester(), set(), date(2026, 6, 15)
    )

    assert [event.date for event in events] == [
        day for day in MONDAYS_FROM_APRIL_1 if day >= date(2026, 6, 15)
    ]
    assert all(event.subject is subject for event in events)
    assert all(event.is_generated is True for event in events)


def test_build_class_events_from_starts_at_next_matching_day():
    # 2026-06-16は火曜日。次の月曜日（6/22）から。
    events = build_class_events_from(
        make_subject(), make_semester(), set(), date(2026, 6, 16)
    )

    assert [event.date for event in events] == [
        date(2026, 6, 22),
        date(2026, 6, 29),
        date(2026, 7, 6),
        date(2026, 7, 13),
        date(2026, 7, 20),
        date(2026, 7, 27),
    ]


def test_build_class_events_from_before_semester_uses_whole_semester():
    events = build_class_events_from(
        make_subject(), make_semester(), set(), date(2026, 3, 1)
    )

    assert [event.date for event in events] == MONDAYS_FROM_APRIL_1


def test_build_class_events_from_on_last_day_includes_it():
    # 学期の終了日（2026-07-31）は金曜日。
    events = build_class_events_from(
        make_subject(weekday=4), make_semester(), set(), date(2026, 7, 31)
    )

    assert [event.date for event in events] == [date(2026, 7, 31)]


def test_build_class_events_from_after_semester_returns_empty_list():
    events = build_class_events_from(
        make_subject(), make_semester(), set(), date(2026, 8, 1)
    )

    assert events == []


def test_build_class_events_from_skips_excluded_dates():
    events = build_class_events_from(
        make_subject(),
        make_semester(),
        {date(2026, 5, 4), date(2026, 7, 20)},
        date(2026, 7, 1),
    )

    assert [event.date for event in events] == [
        date(2026, 7, 6),
        date(2026, 7, 13),
        date(2026, 7, 27),
    ]
```

### 付録F. `tests/test_api_helpers.py`

<!-- 全文: tests/test_api_helpers.py -->
```python
from datetime import date, datetime, time

import pytest
from flask import Flask

from app.api_helpers import (
    EMPTY_PATCH_MESSAGE,
    MAX_ID,
    UNUSABLE_CHARACTER_MESSAGE,
    contains_unusable_character,
    format_datetime,
    format_time,
    parse_time,
    read_id_query,
    read_patch_object,
    validate_optional_string,
    validate_required_boolean,
    validate_required_choice,
    validate_required_integer,
    validate_required_date,
    validate_required_datetime,
    validate_required_string,
    validate_required_time,
)


def test_unusable_character_message_constant():
    assert UNUSABLE_CHARACTER_MESSAGE == "使用できない文字が含まれています"


@pytest.mark.parametrize(
    "value",
    ["\ud800", "\udbff", "\udc00", "\udfff", "a\ud800b"],
)
def test_contains_unusable_character_detects_lone_surrogates(value):
    assert contains_unusable_character(value) is True


@pytest.mark.parametrize(
    "value",
    ["", "abc", "日本語", "😀", "\ud7ff", "\ue000"],
)
def test_contains_unusable_character_accepts_other_text(value):
    assert contains_unusable_character(value) is False


@pytest.mark.parametrize(
    "value",
    ["\ud800", "科目\udc00", " \ud800 "],
)
def test_validate_required_string_rejects_unusable_characters(value):
    assert validate_required_string(
        {"value": value},
        "value",
        "必須",
        "型",
        strip=True,
        max_length=100,
        length_message="長さ",
    ) == (None, UNUSABLE_CHARACTER_MESSAGE)


def test_validate_required_string_rejects_unusable_characters_by_default():
    assert validate_required_string(
        {"value": "\ud800"},
        "value",
        "必須",
        "型",
    ) == (None, UNUSABLE_CHARACTER_MESSAGE)


@pytest.mark.parametrize(
    "value",
    ["\ud800", "  \udfff  ", "メモ\ud800"],
)
def test_validate_optional_string_rejects_unusable_characters(value):
    assert validate_optional_string(
        {"value": value},
        "value",
        "型",
    ) == (None, UNUSABLE_CHARACTER_MESSAGE)


@pytest.mark.parametrize("value", ["\ud800", "09:00\udc00"])
def test_validate_required_time_rejects_unusable_characters(value):
    assert validate_required_time(
        {"value": value},
        "value",
        "必須",
        "形式",
    ) == (None, UNUSABLE_CHARACTER_MESSAGE)


def test_surrogate_pairs_count_as_one_character():
    assert validate_required_string(
        {"value": "😀😀"},
        "value",
        "必須",
        "型",
        max_length=2,
        length_message="長さ",
    ) == ("😀😀", None)


@pytest.mark.parametrize(
    "value",
    ["00:00", "09:00", "23:59"],
)
def test_parse_time_accepts_valid_times(value):
    assert parse_time(value) == time.fromisoformat(value)


@pytest.mark.parametrize(
    "value",
    [
        "24:00",
        "09:60",
        "9:00",
        "09:0",
        "0900",
        "09:00:00",
        " 09:00",
        "09:00 ",
        "09:00\n",
        "０９：００",
        "ab:cd",
        "",
        900,
        None,
    ],
)
def test_parse_time_rejects_invalid_values(value):
    assert parse_time(value) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [(time(9, 0), "09:00"), (time(23, 59), "23:59")],
)
def test_format_time(value, expected):
    assert format_time(value) == expected


@pytest.mark.parametrize(
    "payload",
    [{}, {"value": None}, {"value": ""}],
)
def test_validate_required_time_reports_required(payload):
    assert validate_required_time(
        payload,
        "value",
        "必須",
        "形式",
    ) == (None, "必須")


def test_validate_required_time_reports_format_and_converts_value():
    assert validate_required_time(
        {"value": "9:00"},
        "value",
        "必須",
        "形式",
    ) == (None, "形式")
    assert validate_required_time(
        {"value": "09:00"},
        "value",
        "必須",
        "形式",
    ) == (time(9, 0), None)


@pytest.mark.parametrize("value", [900, True])
def test_validate_required_time_reports_non_string_as_format_error(value):
    assert validate_required_time(
        {"value": value},
        "value",
        "必須",
        "形式",
    ) == (None, "形式")


def test_validate_required_string_keeps_legacy_behavior_by_default():
    assert validate_required_string(
        {"value": "  "},
        "value",
        "必須",
        "型",
    ) == ("  ", None)
    assert validate_required_string(
        {"value": " x "},
        "value",
        "必須",
        "型",
    ) == (" x ", None)


@pytest.mark.parametrize(
    "payload",
    [{}, {"value": None}, {"value": ""}],
)
def test_validate_required_string_checks_required(payload):
    assert validate_required_string(
        payload,
        "value",
        "必須",
        "型",
    ) == (None, "必須")


@pytest.mark.parametrize("value", [123, True, []])
def test_validate_required_string_reports_type_error(value):
    assert validate_required_string(
        {"value": value},
        "value",
        "必須",
        "型",
    ) == (None, "型")


def test_validate_required_string_strip_and_length():
    assert validate_required_string(
        {"value": "　x　"},
        "value",
        "必須",
        "型",
        strip=True,
        max_length=1,
        length_message="長さ",
    ) == ("x", None)
    assert validate_required_string(
        {"value": "x" * 100},
        "value",
        "必須",
        "型",
        strip=True,
        max_length=100,
        length_message="長さ",
    ) == ("x" * 100, None)
    assert validate_required_string(
        {"value": "x" * 101},
        "value",
        "必須",
        "型",
        max_length=100,
        length_message="長さ",
    ) == (None, "長さ")
    assert validate_required_string(
        {"value": "　"},
        "value",
        "必須",
        "型",
        strip=True,
    ) == (None, "必須")


def test_validate_required_string_requires_length_message():
    with pytest.raises(ValueError):
        validate_required_string(
            {"value": "x"},
            "value",
            "必須",
            "型",
            max_length=1,
        )


@pytest.mark.parametrize(
    "payload",
    [{}, {"value": None}, {"value": ""}, {"value": "  "}, {"value": "　"}],
)
def test_validate_optional_string_normalizes_empty_values(payload):
    assert validate_optional_string(
        payload,
        "value",
        "型",
    ) == (None, None)


def test_validate_optional_string_checks_type_and_length():
    assert validate_optional_string(
        {"value": 123},
        "value",
        "型",
    ) == (None, "型")
    assert validate_optional_string(
        {"value": "　教室　"},
        "value",
        "型",
        max_length=2,
        length_message="長さ",
    ) == ("教室", None)
    assert validate_optional_string(
        {"value": "x" * 101},
        "value",
        "型",
        max_length=100,
        length_message="長さ",
    ) == (None, "長さ")


@pytest.mark.parametrize("value", [True, False, 1.0, "1", [1], {}])
def test_validate_required_integer_rejects_non_integer_types(value):
    assert validate_required_integer(
        {"value": value},
        "value",
        "必須",
        "型",
    ) == (None, "型")


@pytest.mark.parametrize("payload", [{}, {"value": None}, {"value": ""}])
def test_validate_required_integer_checks_required(payload):
    assert validate_required_integer(
        payload,
        "value",
        "必須",
        "型",
    ) == (None, "必須")


@pytest.mark.parametrize("value", [-1, 0, 1, 2])
def test_validate_required_integer_checks_inclusive_range(value):
    expected = (value, None) if 0 <= value <= 1 else (None, "範囲")
    assert validate_required_integer(
        {"value": value},
        "value",
        "必須",
        "型",
        min_value=0,
        max_value=1,
        range_message="範囲",
    ) == expected


def test_validate_required_integer_defaults_range_message_to_type_message():
    assert validate_required_integer(
        {"value": -1},
        "value",
        "必須",
        "型",
        min_value=0,
    ) == (None, "型")


@pytest.mark.parametrize("value", [-10, 0, 10])
def test_validate_required_integer_accepts_integers_without_range(value):
    assert validate_required_integer(
        {"value": value},
        "value",
        "必須",
        "型",
    ) == (value, None)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-04-01", date(2026, 4, 1)),
        ("2028-02-29", date(2028, 2, 29)),
    ],
)
def test_validate_required_date_converts_value(value, expected):
    assert validate_required_date(
        {"value": value},
        "value",
        "必須",
        "形式",
    ) == (expected, None)


@pytest.mark.parametrize("payload", [{}, {"value": None}, {"value": ""}])
def test_validate_required_date_reports_required(payload):
    assert validate_required_date(
        payload,
        "value",
        "必須",
        "形式",
    ) == (None, "必須")


@pytest.mark.parametrize("value", [20260401, True])
def test_validate_required_date_reports_non_string_as_format_error(value):
    assert validate_required_date(
        {"value": value},
        "value",
        "必須",
        "形式",
    ) == (None, "形式")


@pytest.mark.parametrize(
    "value",
    [
        "2026-4-1",
        "2026/04/01",
        "20260401",
        "2026-02-30",
        " 2026-04-01",
        "2026-04-01 ",
        "２０２６-04-01",
    ],
)
def test_validate_required_date_reports_format_error(value):
    assert validate_required_date(
        {"value": value},
        "value",
        "必須",
        "形式",
    ) == (None, "形式")


@pytest.mark.parametrize("value", ["\ud800", "2026-04-01\udc00"])
def test_validate_required_date_rejects_unusable_characters(value):
    assert validate_required_date(
        {"value": value},
        "value",
        "必須",
        "形式",
    ) == (None, UNUSABLE_CHARACTER_MESSAGE)


def read_semester_id_query(query_string):
    # read_id_queryは、要求のクエリを読むため、DBを使わない最小の
    # Flaskアプリで、要求の中の状態を作って呼ぶ。
    request_app = Flask(__name__)
    with request_app.test_request_context(query_string=query_string):
        return read_id_query("semester_id", "複数", "形式")


@pytest.mark.parametrize(
    "query_string",
    [{}, {"foo": "bar"}],
)
def test_read_id_query_without_value_is_not_specified(query_string):
    assert read_semester_id_query(query_string) == (False, None, None)


def test_read_id_query_rejects_repeated_values():
    assert read_semester_id_query(
        {"semester_id": ["1", "2"]}
    ) == (True, None, "複数")


@pytest.mark.parametrize(
    "value",
    ["", "abc", "-1", "1.5", "１", " 1", "1 "],
)
def test_read_id_query_rejects_non_digit_text(value):
    assert read_semester_id_query(
        {"semester_id": value}
    ) == (True, None, "形式")


@pytest.mark.parametrize(
    "value",
    ["0", "000", str(MAX_ID + 1), "9" * 5000],
)
def test_read_id_query_out_of_range_matches_nothing(value):
    assert read_semester_id_query(
        {"semester_id": value}
    ) == (True, None, None)


@pytest.mark.parametrize(
    ("value", "expected_id"),
    [("1", 1), ("001", 1), (str(MAX_ID), MAX_ID)],
)
def test_read_id_query_returns_id(value, expected_id):
    assert read_semester_id_query(
        {"semester_id": value}
    ) == (True, expected_id, None)


# --- 日時（Task 016） ---


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-10-12T23:59", datetime(2026, 10, 12, 23, 59)),
        ("2026-01-01T00:00", datetime(2026, 1, 1, 0, 0)),
        ("2028-02-29T12:30", datetime(2028, 2, 29, 12, 30)),
    ],
)
def test_validate_required_datetime_converts_value(value, expected):
    assert validate_required_datetime(
        {"value": value},
        "value",
        "必須",
        "形式",
    ) == (expected, None)


@pytest.mark.parametrize("payload", [{}, {"value": None}, {"value": ""}])
def test_validate_required_datetime_reports_required(payload):
    assert validate_required_datetime(
        payload,
        "value",
        "必須",
        "形式",
    ) == (None, "必須")


@pytest.mark.parametrize("value", [202610122359, True, ["2026-10-12T23:59"]])
def test_validate_required_datetime_reports_non_string_as_format_error(
    value,
):
    assert validate_required_datetime(
        {"value": value},
        "value",
        "必須",
        "形式",
    ) == (None, "形式")


@pytest.mark.parametrize(
    "value",
    [
        "2026-10-12",
        "2026-10-12 23:59",
        "2026-10-12t23:59",
        "2026-10-12T23:59:00",
        "2026-10-12T23:59Z",
        "2026-10-12T23:59+09:00",
        "2026-10-12T24:00",
        "2026-10-12T23:60",
        "2026-02-30T10:00",
        "2026-10-12T9:00",
        "2026-10-12T0900",
        " 2026-10-12T23:59",
        "2026-10-12T23:59 ",
        "２０２６-10-12T23:59",
    ],
)
def test_validate_required_datetime_reports_format_error(value):
    assert validate_required_datetime(
        {"value": value},
        "value",
        "必須",
        "形式",
    ) == (None, "形式")


@pytest.mark.parametrize("value", ["\ud800", "2026-10-12T23:59\udc00"])
def test_validate_required_datetime_rejects_unusable_characters(value):
    assert validate_required_datetime(
        {"value": value},
        "value",
        "必須",
        "形式",
    ) == (None, UNUSABLE_CHARACTER_MESSAGE)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (datetime(2026, 1, 2, 3, 4), "2026-01-02T03:04"),
        (datetime(2026, 1, 2, 3, 4, 59), "2026-01-02T03:04"),
    ],
)
def test_format_datetime_omits_seconds(value, expected):
    assert format_datetime(value) == expected


# --- 真偽値（Task 016） ---


@pytest.mark.parametrize("value", [True, False])
def test_validate_required_boolean_accepts_booleans(value):
    assert validate_required_boolean(
        {"value": value},
        "value",
        "必須",
        "型",
    ) == (value, None)


@pytest.mark.parametrize("payload", [{}, {"value": None}, {"value": ""}])
def test_validate_required_boolean_checks_required(payload):
    assert validate_required_boolean(
        payload,
        "value",
        "必須",
        "型",
    ) == (None, "必須")


@pytest.mark.parametrize("value", [0, 1, 1.0, "true", "false", [], {}])
def test_validate_required_boolean_rejects_non_booleans(value):
    assert validate_required_boolean(
        {"value": value},
        "value",
        "必須",
        "型",
    ) == (None, "型")


# --- 決まった値から選ぶ文字列（カテゴリ。Task 016） ---


CHOICES = ("assignment", "other")


@pytest.mark.parametrize("value", ["assignment", "other"])
def test_validate_required_choice_accepts_choices(value):
    assert validate_required_choice(
        {"value": value},
        "value",
        CHOICES,
        "必須",
        "選択肢",
    ) == (value, None)


@pytest.mark.parametrize("payload", [{}, {"value": None}, {"value": ""}])
def test_validate_required_choice_checks_required(payload):
    assert validate_required_choice(
        payload,
        "value",
        CHOICES,
        "必須",
        "選択肢",
    ) == (None, "必須")


@pytest.mark.parametrize(
    "value",
    [
        "class",
        "Assignment",
        " assignment",
        "assignment ",
        "課題",
        1,
        True,
        ["assignment"],
    ],
)
def test_validate_required_choice_rejects_other_values(value):
    assert validate_required_choice(
        {"value": value},
        "value",
        CHOICES,
        "必須",
        "選択肢",
    ) == (None, "選択肢")


@pytest.mark.parametrize("value", ["\ud800", "assignment\udc00"])
def test_validate_required_choice_rejects_unusable_characters(value):
    assert validate_required_choice(
        {"value": value},
        "value",
        CHOICES,
        "必須",
        "選択肢",
    ) == (None, UNUSABLE_CHARACTER_MESSAGE)


# --- PATCHの本文の読み取り（Task 016） ---


def call_read_patch_object(**request_options):
    # read_patch_objectは、要求の本文を読むため、DBを使わない最小の
    # Flaskアプリで、要求の中の状態を作って呼ぶ。
    request_app = Flask(__name__)
    with request_app.test_request_context(method="PATCH", **request_options):
        payload, error_response = read_patch_object()
        if error_response is None:
            return payload, None
        response, status = error_response
        return payload, (status, response.get_json())


def test_read_patch_object_returns_payload():
    assert call_read_patch_object(json={"title": "レポート"}) == (
        {"title": "レポート"},
        None,
    )


def test_read_patch_object_rejects_empty_object():
    assert call_read_patch_object(json={}) == (
        None,
        (
            400,
            {
                "error": {
                    "code": "validation_error",
                    "message": EMPTY_PATCH_MESSAGE,
                }
            },
        ),
    )


def test_read_patch_object_keeps_read_json_object_errors():
    assert call_read_patch_object(json=[]) == (
        None,
        (
            400,
            {
                "error": {
                    "code": "validation_error",
                    "message": (
                        "リクエストの本文は、JSONのオブジェクトにしてください"
                    ),
                }
            },
        ),
    )
```

### 付録G. `app/routes/tasks.py`

<!-- 全文: app/routes/tasks.py -->
```python
from typing import Any

from flask import Blueprint, jsonify, request

from app.api_helpers import (
    MAX_ID,
    api_error_response,
    format_datetime,
    read_json_object,
    read_patch_object,
    validate_allowed_fields,
    validate_optional_string,
    validate_required_boolean,
    validate_required_choice,
    validate_required_datetime,
    validate_required_integer,
    validate_required_string,
)
from app.categories import TASK_CATEGORIES, TASK_CATEGORY_OTHER
from app.extensions import db
from app.models.subject import Subject
from app.models.task import Task


tasks_bp = Blueprint(
    "tasks",
    __name__,
    url_prefix="/api/tasks",
)

# 課題・タスクの登録（POST）で受け付ける項目。完了の状態（is_completed）は
# 受け付けない（登録した課題・タスクは、常に未完了）。
CREATE_FIELDS = {
    "category",
    "subject_id",
    "title",
    "due_datetime",
    "notes",
}
# 課題・タスクの編集（PATCH）で受け付ける項目。カテゴリ（category）は、
# 変えられない（誤った場合は、削除して登録し直す）。
UPDATE_FIELDS = {
    "subject_id",
    "title",
    "due_datetime",
    "notes",
    "is_completed",
}

CATEGORY_MESSAGE = "カテゴリは「assignment」か「other」で指定してください"
COMPLETED_MESSAGE = "完了の状態は「true」か「false」で指定してください"
OTHER_SUBJECT_MESSAGE = "その他（締切のみ）には、授業を指定できません"


def task_to_dict(task: Task) -> dict[str, Any]:
    """課題・タスクをAPIレスポンス用の辞書に変換する。

    subject_name は、対象授業の今の科目名（付加情報。DBには保存しない）。
    対象授業がない場合（その他）は、None。
    """
    return {
        "id": task.id,
        "subject_id": task.subject_id,
        "subject_name": (
            task.subject.subject_name if task.subject is not None else None
        ),
        "category": task.category,
        "title": task.title,
        "due_datetime": format_datetime(task.due_datetime),
        "notes": task.notes,
        "is_completed": task.is_completed,
    }


def read_completed_query() -> tuple[bool, bool | None, str | None]:
    """一覧の絞り込みのクエリ is_completed を読み取る。

    戻り値は、（指定の有無、値、エラーメッセージ）の組。
    - 指定がない：(False, None, None)
    - 2回以上の指定：(True, None, 1つだけ指定するメッセージ)
    - 「true」「false」（小文字）以外（空文字・大文字・数字・空白を含む）：
      (True, None, COMPLETED_MESSAGE)
    - それ以外：(True, True または False, None)
    使うのが課題・タスクの一覧だけのため、このファイルに置く。
    """
    values = request.args.getlist("is_completed")
    if not values:
        return False, None, None
    if len(values) > 1:
        return True, None, "完了の状態は1つだけ指定してください"
    if values[0] == "true":
        return True, True, None
    if values[0] == "false":
        return True, False, None
    return True, None, COMPLETED_MESSAGE


def validate_task_values(
    payload: dict[str, Any],
    *,
    partial: bool,
) -> tuple[dict[str, Any], dict[str, str]]:
    """課題・タスクの項目（タイトル・締切日時・詳細／メモ）を検査する。

    登録（POST）と編集（PATCH）で、同じ規則で検査するために使う。
    - partial=False（登録）：3つの項目を検査する。必須の項目が本文に
      なければ、必須のエラーにする
    - partial=True（編集）：本文に含まれる項目だけを検査する
    戻り値は、（値、エラー）の組。値は、誤りのない項目だけを入れる
    （キーは、Taskの列の名前と同じ）。カテゴリ・対象授業・完了の状態は、
    呼び出し側が検査する。
    """
    values: dict[str, Any] = {}
    errors: dict[str, str] = {}

    if not partial or "title" in payload:
        title, error = validate_required_string(
            payload,
            "title",
            "タイトルは必須です",
            "タイトルは文字列で指定してください",
            strip=True,
            max_length=200,
            length_message="タイトルは200文字以内にしてください",
        )
        if error is None:
            values["title"] = title
        else:
            errors["title"] = error

    if not partial or "due_datetime" in payload:
        due_datetime, error = validate_required_datetime(
            payload,
            "due_datetime",
            "締切日時は必須です",
            "締切日時は実在する日時を「YYYY-MM-DDTHH:MM」の形式で"
            "指定してください",
        )
        if error is None:
            values["due_datetime"] = due_datetime
        else:
            errors["due_datetime"] = error

    if not partial or "notes" in payload:
        notes, error = validate_optional_string(
            payload,
            "notes",
            "詳細・メモは文字列で指定してください",
        )
        if error is None:
            values["notes"] = notes
        else:
            errors["notes"] = error

    return values, errors


def validate_task_subject_id(
    payload: dict[str, Any],
    category: str,
) -> tuple[int | None, str | None]:
    """対象授業（subject_id）を、カテゴリの規則で検査する。

    - 課題（assignment）：必須。整数で、その授業が存在すること
    - その他（other）：指定できない（項目がないか、null だけを受け付ける）
    戻り値は、（値、エラーメッセージ）の組。その他の値は、常に None。
    """
    if category == TASK_CATEGORY_OTHER:
        # その他（締切のみ）は、授業に結びつかない。
        if payload.get("subject_id") is not None:
            return None, OTHER_SUBJECT_MESSAGE
        return None, None

    subject_id, error = validate_required_integer(
        payload,
        "subject_id",
        "授業IDは必須です",
        "授業IDは整数で指定してください",
    )
    if error is not None:
        return None, error
    # 範囲外のIDをDBに渡すと、SQLiteでOverflowErrorになるため先に確認する。
    if not 1 <= subject_id <= MAX_ID:
        return None, "指定された授業が存在しません"
    if db.session.get(Subject, subject_id) is None:
        return None, "指定された授業が存在しません"
    return subject_id, None


@tasks_bp.get("")
def get_tasks():
    specified, is_completed, query_error = read_completed_query()
    if query_error is not None:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            {"is_completed": query_error},
        )

    statement = db.select(Task)
    if specified:
        statement = statement.where(Task.is_completed.is_(is_completed))
    statement = statement.order_by(
        Task.due_datetime.asc(),
        Task.id.asc(),
    )
    tasks = db.session.scalars(statement).all()
    return jsonify([task_to_dict(task) for task in tasks])


@tasks_bp.get(f"/<int(max={MAX_ID}):task_id>")
def get_task(task_id: int):
    task = db.session.get(Task, task_id)
    if task is None:
        return api_error_response("not_found", "課題・タスクが見つかりません")
    return jsonify(task_to_dict(task))


@tasks_bp.post("")
def create_task():
    payload, error_response = read_json_object()
    if error_response is not None:
        return error_response

    fields: dict[str, str] = {}

    category, category_error = validate_required_choice(
        payload,
        "category",
        TASK_CATEGORIES,
        "カテゴリは必須です",
        CATEGORY_MESSAGE,
    )
    if category_error is not None:
        fields["category"] = category_error

    values, value_errors = validate_task_values(payload, partial=False)
    fields.update(value_errors)

    # 対象授業の規則は、カテゴリによって変わるため、カテゴリに誤りが
    # ないときだけ検査する。
    subject_id = None
    if category is not None:
        subject_id, subject_id_error = validate_task_subject_id(
            payload, category
        )
        if subject_id_error is not None:
            fields["subject_id"] = subject_id_error

    fields.update(validate_allowed_fields(payload, CREATE_FIELDS))

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    task = Task(
        category=category,
        subject_id=subject_id,
        title=values["title"],
        due_datetime=values["due_datetime"],
        notes=values["notes"],
        is_completed=False,
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task_to_dict(task)), 201


@tasks_bp.patch(f"/<int(max={MAX_ID}):task_id>")
def update_task(task_id: int):
    # 対象の課題・タスクがなければ、本文を読む前に404にする。
    task = db.session.get(Task, task_id)
    if task is None:
        return api_error_response("not_found", "課題・タスクが見つかりません")

    # 項目が1つもない本文（{}）も、誤りにする（API共通ルール）。
    payload, error_response = read_patch_object()
    if error_response is not None:
        return error_response

    values, fields = validate_task_values(payload, partial=True)

    if "is_completed" in payload:
        is_completed, error = validate_required_boolean(
            payload,
            "is_completed",
            "完了の状態は必須です",
            COMPLETED_MESSAGE,
        )
        if error is None:
            values["is_completed"] = is_completed
        else:
            fields["is_completed"] = error

    # 対象授業は、今のカテゴリ（変えられない）の規則で検査する。
    if "subject_id" in payload:
        subject_id, error = validate_task_subject_id(payload, task.category)
        if error is None:
            values["subject_id"] = subject_id
        else:
            fields["subject_id"] = error

    fields.update(validate_allowed_fields(payload, UPDATE_FIELDS))

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    # 本文に含まれていた項目だけを、課題・タスクに書き込む
    # （values のキーは、Taskの列の名前と同じ）。
    for field_name, value in values.items():
        setattr(task, field_name, value)
    db.session.commit()
    return jsonify(task_to_dict(task))


@tasks_bp.delete(f"/<int(max={MAX_ID}):task_id>")
def delete_task(task_id: int):
    task = db.session.get(Task, task_id)
    if task is None:
        return api_error_response("not_found", "課題・タスクが見つかりません")

    # 課題・タスクは、子の行を持たないため、この行だけを削除する。
    db.session.delete(task)
    db.session.commit()
    return "", 204
```

### 付録H. `app/__init__.py`

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

    from app.routes.tasks import tasks_bp

    app.register_blueprint(tasks_bp)
    return app
```

### 付録I. `tests/test_tasks_api.py`

<!-- 全文: tests/test_tasks_api.py -->
```python
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
```
