# タスク021: 学期の編集・削除

| 項目 | 内容 |
|---|---|
| Task ID | 021 |
| Task名 | 学期の編集・削除のAPI（`PATCH`・`DELETE /api/semesters/<id>`、期間の変更の、授業の予定・休講日への反映、1件取得の件数）と、その画面（授業モードの学期の「編集」「削除」）、003-Hの残り（405の `Allow`、`assert`、`Semester.query`） |
| ブランチ | `feature/021-semester-edit-delete`（Komaが作成・切替済みの状態で渡される） |

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに停止して報告する。

**このタスクには、承認ゲートはない（DBの構造を変えないため、migrationを作らない）。** 段階1・2を順に進め、「Copilot確認手順」を実施したら、結果を報告して応答を終える。途中で止まるのは、「注意」の停止の条件に当たったときだけ。**止まるときは、報告を書いて応答を終える。質問の機能（選択肢を出して回答を待つ機能）は使わない**（`.github/copilot-instructions.md` の「止まる場面の応答」）。

**ファイルは、手で書き写さない。** 7つのファイルの全文は、このTask MDの付録にある。各段階の始めに、「全文からファイルを作るスクリプト」を実行して作る（013-N1）。付録の全文は、スクリプトが読む。付録を読んで書き写す必要はない（本文の要点・差分・確認の手順を読む）。

**報告には、コマンドの出力を、要約せずに、そのまま貼る**（014-L1）。「全文からファイルを作るスクリプト」の出力と、「Copilot確認手順」の1（実施前）の出力も、文章にまとめずに、そのまま貼る（019-N1）。「Copilot確認手順」の1・2・6は、各コマンドの前に、`echo` で見出しを出すように書いてある。**見出しの行も含めて、出力をそのまま貼る**（018-N1・019-N1）。設計資料の確認（1）は、長い行を出さないように、件数（`grep -c`）で書いてある（020-N1）。「注意」の最後の報告の項目を参照。

**このTask MDのスクリプトとコマンドには、バックスラッシュ（`\`）の書き方を使っていない**（016-N1。改行は、スクリプトの中で `newline = chr(10)` として表す。`grep` は、`-F`（文字どおりに探す）と `-e`（探す文字列を1つずつ指定）で書く）。**コマンドは、書いてあるとおりに実行する。`grep` の `-e` を足す・減らすことも含め、書き換えた場合は、どこをどう書き換えたかを、報告に書く**（017-N1）。

## 目的
学期の名前と期間を、あとから直せるようにし、授業のない学期を削除できるようにする。設計資料（`docs/architecture.md` の「学期API」「繰り返し予定の扱い」の「学期の期間の変更と予定の同期」「API共通ルール」「JavaScriptの構成（ES modules）」「モード間の連携（`CustomEvent`）」、`docs/ui_ux.md` の「授業モード」の「学期（タブと登録）」）の仕様を、そのまま実装する。2026-10-20に決めた次のことを含む（それまでの未決定事項「学期の変更・削除時の扱い」）。

- 期間の変更は、変わった部分だけを反映する：新しい期間の外になった日の、自動生成の授業の予定と休講日を削除し、新しく期間に入った日（前の期間の外の日）に、授業の予定を作る（休講日を除く）。今日より前の日にも適用する（「今日」を使わない）。両方の期間に入る日の予定（個別に変更・削除したものを含む）、単発の予定、課題は変えない。名前だけの変更では、予定も休講日も変えない
- 授業がある学期は、削除できない（409 `conflict`）。授業がない学期は、その学期の休講日と一緒に削除する
- 学期の1件取得に、付加情報 `subject_count`・`closure_count` を足す（削除の確認に使う）
- 画面：本文の学期名の右に「編集」「削除」。編集は、登録とは別のモーダル（注意書きつき）。削除は、件数を出す確認のモーダル。編集のあとは、同じ学期でも `semester-selected` を発行する（休講日の一覧と、授業の登録先の学期名を作り直してもらうため）
- 003-Hの残り：APIの405の応答に、`Allow` ヘッダー（使えるメソッドを、名前の順に並べたもの）を付ける。`app/routes/semesters.py` の `assert` をなくし、`Semester.query` を、ほかのrouteと同じ `db.select`・`db.session.get` の書き方にそろえる

**DBの構造は変えない**（migrationなし）。

| 段階 | 内容 | 挙動の変化 | 段階の終わりの `pytest` |
|---|---|---|---|
| 1 | 003-Hと学期のAPI：`app/api_helpers.py`（405の `Allow`、409の `conflict`）、`app/routes/semesters.py`（`PATCH`・`DELETE`、1件取得の件数、期間の変更の同期、登録と編集の検証の共通化、`assert` をなくす、`db.select` にそろえる）、`app/class_events.py`（先頭のdocstringだけ）、`tests/test_semesters_api.py`（405のテストの直しと、`Allow` のテスト）、`tests/test_semesters_update_delete_api.py`（新規。87件） | `PATCH`・`DELETE /api/semesters/<id>` が使える（今は405）。学期の1件取得に件数が付く。APIの405に `Allow` が付く | **1119件**（1021 ＋ 11 ＋ 87） |
| 2 | 画面：`app/templates/index.html`（学期名の右の「編集」「削除」、編集・削除のモーダル）、`app/static/js/semesters.js`（編集・削除、`semester-selected` の再発行） | 授業モードから、学期を編集・削除できる | **1119件**（Pythonを変えない） |

## 前提（Task 020完了時点の状態）

| 区分 | 内容 |
|---|---|
| すでにある | 学期・授業・休講日のAPIと画面（学期は、一覧・1件取得・登録だけ）、授業の編集・削除（Task 014・015）、予定API（Task 012・019）、カレンダー（Task 013・018・020）、課題・タスクのAPIと画面（Task 016・017）。pytest（**1021件**。`main` の `252349f` で確認） |
| まだない | `PATCH`・`DELETE /api/semesters/<id>`（今は405）、学期の1件取得の件数、APIの405の `Allow`（今は付かない。通常のHTMLページの405には、Flaskの標準で付く）、`tests/test_semesters_update_delete_api.py`、学期の「編集」「削除」の画面 |
| DBの構造 | 変えない（初期migration `0280f6cf8d09` と、休講日の `42bd53808fa1`）。**migrationは不要**。モデル（`app/models/`）も変えない |
| 開発用DB | `instance/app.db` は、Komaの実際の開発用DB（すべてのテーブルが0件。2026-10-20、Task 020の確認のあとにKomaが確認）。**Copilotは、書き込まない。サーバーを起動しない（`python run.py` を実行しない）**。読むのは、「Copilot確認手順」のハッシュと件数だけ。**`sqlite3` は、必ず `-readonly` を付けて実行する**（011-L1） |
| 設計資料 | このタスクの前に、更新した設計資料が `main` に反映されている。`docs/architecture.md` の「繰り返し予定の扱い」の下に「学期の期間の変更と予定の同期」の節があり、「学期API」に `PATCH`・`DELETE`・1件取得の件数があり、「API共通ルール」に405の `Allow` と、409の `conflict`（授業がある学期の削除）がある。未決定事項の表から「学期の変更・削除時の扱い」が外れている。`docs/ui_ux.md` の「学期（タブと登録）」に「編集」「削除」の小節がある。`docs/requirements.md` の「学期」から、未決定の文が外れている |
| 「今日」 | 学期のAPIは、「今日」を使わない（期間の変更は、今日より前の日にも適用する）。テストの結果は、実行した日によらない |
| 確認 | JavaScriptの自動テストはない。画面の動きは、Komaの確認（確認用のサーバーでのブラウザ確認。ブラウザの操作はClaude）で確かめる。Copilotは、ブラウザでの確認をしない |

## Source of Truth
- `docs/architecture.md`：「データ設計」の「共通の約束」（削除の連動）・Semester・Event（`is_generated`）・Closure、「繰り返し予定の扱い」（「授業の予定を作る・消すのは、次の場面だけ」、「休講日の変更と予定の同期」の「1件まで」、「学期の期間の変更と予定の同期」、「同じ授業・同じ日付に単発の予定がある場合」）、「授業のEventの生成処理」、「API共通ルール」（「URLとメソッド」の405と `Allow`、「レスポンスの付加情報」、`PATCH`、「エラー」の409、「404の使い分け」）、「学期API」、「JavaScriptの構成（ES modules）」（`semesters.js`、モーダルの規則、モーダルの中で始める要求の規則、`try` で囲む範囲、`textContent`、名前つきの引数）、「モード間の連携（`CustomEvent`）」（`semester-selected`）、「自動テスト（pytest）」の「テストの書き方」、「ディレクトリ構成」
- `docs/ui_ux.md`：「授業モード」の「学期（タブと登録）」（「表示」「編集」「削除」「編集・削除の共通」）と「休講日」
- `docs/requirements.md`：「学期」
- `.github/copilot-instructions.md`：進め方、「止まる場面の応答」、コーディング方針、「テスト」

## 実装対象ファイル

| 区分 | ファイル | 段階 | 内容 | 全文 |
|---|---|---|---|---|
| 変更 | `app/api_helpers.py` | 1 | 405のエラーハンドラーで `Allow` を付ける。`ERROR_STATUS_CODES` に `"conflict": 409` を足す。ほかの関数は変えない | 付録A |
| 変更 | `app/routes/semesters.py` | 1 | 編集（`update_semester`）・削除（`delete_semester`）・1件取得の件数、期間の変更の同期（`sync_period_change`）、登録と編集の検証の共通化（`validate_semester_values`）。`assert` をなくし、`Semester.query` を `db.select` にする | 付録B |
| 変更 | `app/class_events.py` | 1 | 先頭のdocstringだけ（使う場面に、学期の期間の変更を足す）。関数は変えない | 付録C |
| 変更 | `tests/test_semesters_api.py` | 1 | 1件取得の期待値（件数）、提供しない操作の405のテストの組（4 → 5）と `Allow` の確認、すべてのリソースの405の `Allow` のテスト（9件）、HTMLページの405のテスト（1件） | 付録D |
| 新規 | `tests/test_semesters_update_delete_api.py` | 1 | 学期の編集・削除と、1件取得の件数のAPIのテスト（87件） | 付録E |
| 変更 | `app/templates/index.html` | 2 | 学期名の右の「編集」「削除」と、編集・削除の確認のモーダル | 付録F |
| 変更 | `app/static/js/semesters.js` | 2 | 編集のモーダル、削除の確認のモーダル、`selectSemester`・`loadSemesters` の名前つきの引数、`aria-label` | 付録G |

上の7ファイル以外は、変更しない（`__pycache__/` などの、`.gitignore` の対象は除く）。**7ファイルとも、このTask MDの付録に全文がある。「全文からファイルを作るスクリプト」で作り、手で書き写さない。書き込んだあとに、手で直さない。** 全文を変える必要があると判断した場合は、変えずに停止して報告する。

## 非対象（このタスクでは作らない・変更しない）
- モデル（`app/models/`）、`migrations/`（**新しいmigrationを作らない。`flask db` のコマンドを、一切実行しない**）、`requirements.txt`（**ライブラリを追加しない**）、`pytest.ini`、`run.py`、`app/__init__.py`、`app/categories.py`
- `app/routes/` の、`semesters.py` 以外のファイル（`subjects.py`・`closures.py`・`events.py`・`tasks.py`・`main.py`）
- `app/templates/base.html`、`app/static/css/style.css`、`app/static/js/` の `semesters.js` 以外のファイル（`main.js`・`ui.js`・`api.js` など。`semester-selected` を購読する `subjects.js`・`closures.js` も変えない）
- `index.html` の、上の「内容」に書いた部分以外
- `tests/` の、上の2つ以外のファイル（`conftest.py`・`test_subjects_api.py`・`test_subjects_update_delete_api.py`・`test_closures_api.py`・`test_events_api.py`・`test_events_create_update_delete_api.py`・`test_tasks_api.py`・`test_api_helpers.py`・`test_class_events.py`・`test_setup.py` を含む）
- `docs/`、`.github/`、`.gitignore`
- 作らないもの：授業の所属学期の付け替え（付け替えない、と決めている）、授業がある学期をまとめて削除する仕組み、期間の長さの上限の検証、休講日の編集、曜日の読み替え
- 開発用DB（`instance/app.db`）への書き込み、サーバーの起動（`python run.py` も、「Komaの確認」の確認用のサーバーも、起動しない）、ブラウザでの確認

## 全文からファイルを作るスクリプト（013-N1）
各段階の始めに、リポジトリのルートで、`.venv` を有効にして実行する。段階1は `python - 1`、段階2は `python - 2`（`-` のあとの数字が段階）。このTask MDの付録の、「`<!-- 全文: パス -->`」の印の行の直後のコードブロックを、そのパスのファイルに、そのまま書き込む（その段階のファイルだけ）。新規のファイルも、このスクリプトが作る。

```
python - 1 <<'EOF'
import sys
from pathlib import Path

# 段階ごとに書き込むファイル（このTask MDの「実装対象ファイル」と同じ）。
STAGE_FILES = {
    "1": [
        "app/api_helpers.py",
        "app/routes/semesters.py",
        "app/class_events.py",
        "tests/test_semesters_api.py",
        "tests/test_semesters_update_delete_api.py",
    ],
    "2": [
        "app/templates/index.html",
        "app/static/js/semesters.js",
    ],
}
MARK_START = "<!-- 全文: "
MARK_END = " -->"
newline = chr(10)
fence = "`" * 3


def read_full_texts(task_path):
    """Task MDの「<!-- 全文: パス -->」の行の直後のコードブロックを、
    {パス: 全文} の辞書にする。"""
    lines = Path(task_path).read_text(encoding="utf-8").split(newline)
    full_texts = {}
    for index, line in enumerate(lines):
        if not (line.startswith(MARK_START) and line.endswith(MARK_END)):
            continue
        if not lines[index + 1].startswith(fence):
            continue
        file_name = line[len(MARK_START):-len(MARK_END)]
        # コードブロックの終わりは、「```」だけの行。
        end = lines.index(fence, index + 2)
        full_texts[file_name] = newline.join(lines[index + 2:end]) + newline
    return full_texts


stage = sys.argv[1]
full_texts = read_full_texts("docs/tasks/021_semester_edit_delete.md")
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
| 1（`python - 1`） | `全文の数：7`、`app/api_helpers.py：書き込み（467行）`、`app/routes/semesters.py：書き込み（358行）`、`app/class_events.py：書き込み（102行）`、`tests/test_semesters_api.py：書き込み（518行）`、`tests/test_semesters_update_delete_api.py：書き込み（1077行）` |
| 2（`python - 2`） | `全文の数：7`、`app/templates/index.html：書き込み（898行）`、`app/static/js/semesters.js：書き込み（507行）` |

- 出力が上と違う場合（全文の数・行数・エラー）は、ほかの作業をせずに停止して報告する
- 段階の終わりの「全文との比較」（「Copilot確認手順」の4）で「不一致」が出た場合は、手で直さず、その段階のスクリプトをもう一度実行して、全文に戻す。戻したことと、違っていた理由（分かれば）を、報告に書く（013-N1）
- **スクリプトの出力は、報告に、そのまま貼る**（019-N1）

## 段階1：003-Hと学期のAPI

（テストの405の直しと、routeの追加を、同じ段階で行わないと、テストが通らないため、APIとテストを1つの段階にした）

### 1-1. `app/api_helpers.py`（全文：付録A）
405のエラーハンドラー（`handle_method_not_allowed`）で、Werkzeugが求めた、そのURLで使えるメソッド（`error.valid_methods`）を、名前の順に `, ` でつないで、`Allow` ヘッダーに入れる（`docs/architecture.md` の「API共通ルール」の「URLとメソッド」）。`ERROR_STATUS_CODES` に `"conflict": 409` を足す（学期の削除で使う）。通常のHTMLページの405は、今までどおり（Flaskの標準のまま）。

`main` からの差分（確認用）：

```diff
--- a/app/api_helpers.py
+++ b/app/api_helpers.py
@@ -4,7 +4,12 @@ from datetime import date, datetime, time
 from typing import Any
 
 from flask import Flask, Response, jsonify, request
-from werkzeug.exceptions import BadRequest, HTTPException, InternalServerError
+from werkzeug.exceptions import (
+    BadRequest,
+    HTTPException,
+    InternalServerError,
+    MethodNotAllowed,
+)
 
 
 # IDの上限（SQLiteのINTEGERの最大値）。これを超える数をDBに渡すとエラーになるため、IDを受け取るURLでは、この値までに制限する
@@ -15,6 +20,7 @@ ERROR_STATUS_CODES = {
     "validation_error": 400,
     "not_found": 404,
     "method_not_allowed": 405,
+    "conflict": 409,
     "server_error": 500,
 }
 
@@ -64,13 +70,19 @@ def register_api_error_handlers(app: Flask) -> None:
         return api_error_response("not_found", "URLが見つかりません")
 
     @app.errorhandler(405)
-    def handle_method_not_allowed(error: HTTPException):
+    def handle_method_not_allowed(error: MethodNotAllowed):
         if not is_api_path(request.path):
             return error
-        return api_error_response(
+        response, status = api_error_response(
             "method_not_allowed",
             "このURLでは、そのメソッドは使えません",
         )
+        # そのURLで使えるメソッドを、Allow ヘッダーで知らせる（405の応答に
+        # 付ける決まり）。Werkzeugが渡すメソッドの並びは、決まっていない
+        # ため、名前の順に並べる。
+        if error.valid_methods:
+            response.headers["Allow"] = ", ".join(sorted(error.valid_methods))
+        return response, status
 
     @app.errorhandler(InternalServerError)
     def handle_internal_server_error(error: InternalServerError):
```

### 1-2. `app/routes/semesters.py`（全文：付録B）
要点（`docs/architecture.md` の「学期API」「学期の期間の変更と予定の同期」）：

| 名前 | 内容 |
|---|---|
| `SEMESTER_FIELDS` | 登録・編集で受け付ける項目（`name`・`start_date`・`end_date`） |
| `END_DATE_ORDER_MESSAGE`・`SEMESTER_HAS_SUBJECTS_MESSAGE` | 「終了日は開始日より後にしてください」・「授業が登録されている学期は削除できません。先に、授業をすべて削除してください」 |
| `is_duplicate_name(name, current_id)` | 同じ名前の、ほかの学期があるか（`current_id` の学期は除く。登録では `None`） |
| `validate_semester_values(payload, *, partial, current_id)` | 登録（`partial=False`）と編集（`partial=True`）の項目の検証（授業の `validate_subject_values` と同じ形）。規則・メッセージ・順序は、今の登録の検証と同じ（学期名の文字数は、`validate_required_string` の `max_length` で数える。結果は同じ）。開始日と終了日の前後は、呼び出し側が比べる |
| `count_semester_subjects`・`count_semester_closures` | 学期の授業・休講日の件数 |
| `sync_period_change(semester, previous_start_date, previous_end_date)` | 期間の変更の同期（commitしない）：新しい期間の外の、学期の授業の自動生成の予定と、学期の休講日を削除し、新しく期間に入った日（前の期間の外の日）に、学期の授業の予定を作る（`class_event_dates` で日付を求め、`build_class_event` で作る。休講日を除く）。作った予定は、`db.session.add_all` で明示的に追加する |
| `get_semesters` | `Semester.query` を `db.session.scalars(db.select(Semester)...)` にした（並びは変えない） |
| `get_semester` | 付加情報 `subject_count`・`closure_count` を足す |
| `create_semester` | `validate_semester_values` を使う。`assert` をなくした（挙動は変えない） |
| `update_semester`（新規、`PATCH`） | 学期がなければ、本文を読む前に404。`read_patch_object`。検証のあと、前後の検査（変更後の値どうし。誤りは `end_date`）。誤りがなければ、学期に書き込み、期間が変わったときだけ `sync_period_change`。1回のcommit。200で、更新後の学期（付加情報なし） |
| `delete_semester`（新規、`DELETE`） | 学期がなければ404。授業があれば409（`conflict`、`SEMESTER_HAS_SUBJECTS_MESSAGE`）。なければ、学期の休講日を先に削除し、学期を削除する（1回のcommit）。204 |

- 学期のAPIは、「今日」を使わない（`date.today()` を呼ばない）
- `assert` と `.query` は、`app/` のPythonのファイルに残らない（「Copilot確認手順」の6で確かめる）

### 1-3. `app/class_events.py`（全文：付録C）
先頭のdocstringだけ。関数は変えない。

`main` からの差分（確認用）：

```diff
--- a/app/class_events.py
+++ b/app/class_events.py
@@ -1,7 +1,7 @@
 """授業の予定（Event）の生成。
 
 授業の登録、休講日の削除による予定の作成、授業全体の編集による
-予定の作り直しから使う部品。
+予定の作り直し、学期の期間の変更による予定の作成から使う部品。
 DBの読み書き（セッションへの追加・commit）は行わない。休講日の日付の
 取得と、データの保存は、各routeが担当する。「今日」の日付も、この
 ファイルでは求めない（作り直しの開始日は、routeが引数で渡す）。
```

### 1-4. `tests/test_semesters_api.py`（全文：付録D）

| 変えること | テスト | 件数 |
|---|---|---|
| 1件取得の期待値に、付加情報（`subject_count: 0`・`closure_count: 0`）を足す | `test_semester_creation_get_and_ordering` | 1（変わらない） |
| 提供しない操作の405のテストから、提供するようになった2つ（`PATCH`・`DELETE /api/semesters/1`）を外し、`PATCH`・`DELETE /api/semesters` と `PUT /api/semesters/1` を足す。`Allow` を確かめる | `test_unsupported_semester_methods_return_json_405` | 4 → 5 |
| すべてのリソースの405に、名前の順の `Allow` が付く | `test_api_405_has_allow_header_in_name_order` | 9（新規） |
| 通常のHTMLページの405は、HTMLのまま | `test_regular_page_405_remains_html` | 1（新規） |
| ファイルの合計 | | 50 → **61** |

ほかのテスト（45件）は変えない。

`main` からの差分（確認用）：

```diff
--- a/tests/test_semesters_api.py
+++ b/tests/test_semesters_api.py
@@ -94,9 +94,10 @@ def test_semester_creation_get_and_ordering(client):
         "2099年度 後期",
         "2099年度 前期",
     ]
+    # 1件取得には、付加情報（授業と休講日の件数）が付く。
     assert client.get(
         f"/api/semesters/{created_objects[0]['id']}"
-    ).json == created_objects[0]
+    ).json == {**created_objects[0], "subject_count": 0, "closure_count": 0}
 
 
 @pytest.mark.parametrize(
@@ -420,15 +421,18 @@ def test_semester_and_url_not_found_responses(client, url, message):
 
 
 @pytest.mark.parametrize(
-    ("method", "url"),
+    ("method", "url", "allow"),
     [
-        ("delete", "/api/semesters/1"),
-        ("patch", "/api/semesters/1"),
-        ("put", "/api/semesters"),
-        ("post", "/api/semesters/1"),
+        ("put", "/api/semesters", "GET, HEAD, OPTIONS, POST"),
+        ("patch", "/api/semesters", "GET, HEAD, OPTIONS, POST"),
+        ("delete", "/api/semesters", "GET, HEAD, OPTIONS, POST"),
+        ("put", "/api/semesters/1", "DELETE, GET, HEAD, OPTIONS, PATCH"),
+        ("post", "/api/semesters/1", "DELETE, GET, HEAD, OPTIONS, PATCH"),
     ],
 )
-def test_unsupported_semester_methods_return_json_405(client, method, url):
+def test_unsupported_semester_methods_return_json_405(
+    client, method, url, allow
+):
     response = getattr(client, method)(url)
     assert_api_error(
         response,
@@ -436,6 +440,42 @@ def test_unsupported_semester_methods_return_json_405(client, method, url):
         "method_not_allowed",
         "このURLでは、そのメソッドは使えません",
     )
+    assert response.headers["Allow"] == allow
```

（このあとの、`Allow` のテスト（`test_api_405_has_allow_header_in_name_order`）と、HTMLページの405のテスト（`test_regular_page_405_remains_html`）の追加は、付録Dの全文を参照）

### 1-5. `tests/test_semesters_update_delete_api.py`（新規。全文：付録E）
- 学期（2026-04-01〜2026-07-31）を、ORMで直接作る（`make_semester`）。授業は、APIで登録する（自動生成の予定が作られる。`create_subject`）。休講日・単発の予定・アルバイト・課題は、ORMで直接作る
- 期待する日付は、アプリのコードを使わずに、テストの中の `days_of_weekday` で求める
- 変わっていないことは、すべての行の値（`all_rows`：学期・授業・予定・休講日・課題）を、操作の前後で比べて確かめる
- 学期のAPIは「今日」を使わないため、「今日」を固定しない

| 確かめること（`docs/architecture.md` の「学期API」「学期の期間の変更と予定の同期」） | テスト | 件数 |
|---|---|---|
| 1件取得の件数（ほかの学期の授業・休講日は数えない） | `test_semester_get_counts_subjects_and_closures` | 1 |
| 件数は、1件取得のレスポンスにだけ付く（一覧・登録・編集にはない） | `test_counts_are_only_in_semester_get` | 1 |
| 件数の項目は、登録・編集のリクエストでは400 | `test_count_fields_in_request_are_rejected` | 4 |
| 編集：名前の変更（200、レスポンス、DBの行） | `test_patch_name_returns_updated_semester` | 1 |
| 編集：名前だけの変更では、予定・休講日は変わらない | `test_patch_name_only_keeps_events_and_closures` | 1 |
| 編集：今の名前のまま送ってよい | `test_patch_same_name_as_itself_is_accepted` | 1 |
| 編集：ほかの学期の名前は400 | `test_patch_name_of_another_semester_is_rejected` | 1 |
| 編集：名前の検証（登録と同じ） | `test_patch_name_is_validated_like_post` | 8 |
| 編集：日付の検証（登録と同じ） | `test_patch_dates_are_validated_like_post` | 12 |
| 編集：終了日は開始日より後（変更後の値どうし。誤りは `end_date`） | `test_patch_end_date_must_be_after_start_date_after_change` | 5 |
| 編集：日付に誤りがあれば、前後は比べない | `test_patch_invalid_date_skips_date_order_validation` | 1 |
| 編集：`id`・未知の項目は400 | `test_patch_rejects_unknown_and_read_only_fields` | 2 |
| 編集：`{}` は400（`fields` なし） | `test_patch_empty_object_is_validation_error_without_fields` | 1 |
| 編集：本文がオブジェクトでない（`null` を含む） | `test_patch_non_object_payload_has_no_fields` | 5 |
| 編集：JSONが読めない・`Content-Type` が違う | `test_patch_invalid_json_or_content_type_is_rejected` | 3 |
| 編集：誤りは、まとめて返す | `test_patch_validation_errors_are_returned_together` | 1 |
| 編集：検証の誤りでは、何も変えない | `test_failed_patch_changes_nothing` | 1 |
| 編集の404の使い分け | `test_patch_not_found_and_invalid_urls` | 5 |
| 編集：学期がなければ、本文を読む前に404 | `test_patch_missing_semester_is_404_before_reading_body` | 1 |
| 上限を超えるIDの `PATCH`・`DELETE` は405 | `test_over_limit_id_for_patch_and_delete_is_method_not_allowed` | 4 |
| 期間：終了日を早めると、そのあとの自動生成の予定が消える | `test_shrinking_end_date_deletes_generated_events_after_it` | 1 |
| 期間：開始日を遅らせると、その前の自動生成の予定が消える | `test_shrinking_start_date_deletes_generated_events_before_it` | 1 |
| 期間：終了日を遅らせると、新しく入った日に予定ができる | `test_extending_end_date_creates_events_for_new_days` | 1 |
| 期間：開始日を早めると、新しく入った日（過去）に予定ができる | `test_extending_start_date_creates_events_for_new_days` | 1 |
| 期間：ずらすと、片側が消え、反対側にできる | `test_shifting_period_deletes_one_side_and_creates_the_other` | 1 |
| 期間：重ならない期間に移すと、すべて入れ替わる | `test_moving_period_without_overlap_replaces_all_events` | 1 |
| 期間：学期のすべての授業に反映する | `test_period_change_affects_all_subjects_of_the_semester` | 1 |
| 期間：両方の期間に入る日の予定は、個別の変更・削除も含めて、そのまま | `test_events_in_both_periods_are_kept_as_they_are` | 1 |
| 期間：新しく作る予定は、授業の今の値 | `test_new_events_use_current_subject_values` | 1 |
| 期間：単発の予定・アルバイトは、新しい期間の外でも残る | `test_period_change_keeps_one_off_and_unrelated_events` | 1 |
| 期間：新しい期間の外の休講日は消え、残った休講日には予定がないまま | `test_period_change_deletes_closures_outside_new_period` | 1 |
| 期間：授業のない学期の期間の変更 | `test_period_change_of_semester_without_subjects` | 1 |
| 期間：ほかの学期と課題は変わらない | `test_period_change_does_not_change_other_semesters_or_tasks` | 1 |
| 期間：縮めて戻すと、予定が1件ずつ戻る（二重にならない） | `test_shrink_then_extend_restores_events_without_duplicates` | 1 |
| 期間：今と同じ日付の指定では、何も変わらない | `test_patch_with_same_dates_changes_nothing` | 1 |
| 期間：途中で例外が起きたら、何も保存されない（500） | `test_period_change_failure_saves_nothing` | 1 |
| 期間：一覧の並びが、新しい開始日で決まる | `test_period_change_updates_semester_list_order` | 1 |
| 削除：学期と、その休講日が消える（204） | `test_delete_semester_removes_it_and_its_closures` | 1 |
| 削除：ほかの行は変わらない | `test_delete_semester_keeps_other_rows` | 1 |
| 削除：授業がある学期は409で、何も変わらない | `test_delete_semester_with_subjects_is_conflict` | 1 |
| 削除：授業を削除すれば、学期を削除できる | `test_semester_can_be_deleted_after_its_subjects_are_deleted` | 1 |
| 削除は本文を読まない | `test_delete_semester_ignores_body` | 1 |
| 削除した学期を、もう一度削除すると404 | `test_deleted_semester_cannot_be_deleted_again` | 1 |
| 削除の404の使い分け | `test_delete_not_found_and_invalid_urls` | 5 |
| 合計 | | **87** |

## 段階2：画面

### 2-1. `app/templates/index.html`（全文：付録F）
要点（足すだけ。既存の部分の中身は変えない）：
- 学期の本文（`semester-detail`）の学期名（`semester-detail-name`）を、`d-flex` の行に入れ、右に「編集」（`semester-edit-button`。`btn-outline-secondary btn-sm`）と「削除」（`semester-delete-button`。`btn-outline-danger btn-sm`）を置く。2つのボタンは、`data-bs-toggle="modal"` で、それぞれのモーダルを開く（`docs/architecture.md` の「JavaScriptの構成」の、決まった操作で開くモーダル。開いた対象は、選択中の学期）
- 学期の登録のモーダル（`semester-modal`）のあとに、2つのモーダルを足す（`<main>` の外。`fade`）
  - 学期の編集（`semester-edit-modal`。フォーム `semester-edit-form`）：見出し「学期を編集」、フォームの上部のエラー（`semester-edit-form-error`）、年度（`semester-edit-year`）・種別（`semester-edit-term`）と、まとめたエラー（`semester-edit-name-error`）、開始日・終了日（`semester-edit-start-date`・`semester-edit-end-date` と、それぞれの `-error`）、注意書き（`semester-edit-notice`。`alert alert-warning small`。文は `docs/ui_ux.md` の「編集」のとおり）。ボタンは「キャンセル」（`data-bs-dismiss`）と「保存する」（`semester-edit-submit-button`、`type="submit"`、`aria-describedby="semester-edit-notice"`）。入力の形は、登録のモーダルと同じ
  - 学期の削除（`semester-delete-modal`）：見出し「学期を削除」、対象（`semester-delete-target`）、件数の取得中（`semester-delete-loading`「授業と休講日の件数を確認しています…」）、件数（`semester-delete-counts`。最初は隠す）、エラー（`semester-delete-error`）、「削除は取り消せません。」（`semester-delete-warning`）。モーダルと「削除する」ボタン（`semester-delete-submit-button`。最初は `disabled`）の `aria-describedby` は、`semester-delete-target semester-delete-counts semester-delete-warning`。「キャンセル」（`semester-delete-cancel-button`）

### 2-2. `app/static/js/semesters.js`（全文：付録G）
要点（`docs/ui_ux.md` の「学期（タブと登録）」、`docs/architecture.md` の「JavaScriptの構成」「モード間の連携」）：
- 共通の小さな関数：`semesterName(year, term)`（登録と編集で、学期名を組み立てる）、`semesterPeriod(semester)`（「2026年9月21日 〜 2026年12月27日」。本文と削除の確認で使う）、`selectedSemester()`（選択中の学期。なければ `null`）
- `renderDetail`：本文の名前・期間に加え、「編集」「削除」の `aria-label`（「「2026年度 前期」を編集」「…を削除」）を入れる
- `selectSemester(id, { notifySameSemester = false } = {})`：`notifySameSemester` が `true` なら、同じ学期を選び直したときも `semester-selected` を発行する（選択中の学期を編集したとき）。それ以外は、今と同じ
- `loadSemesters({ preferredId = null, notifySameSemester = false } = {})`：引数を、名前つきの引数にした（今は、位置の引数 `preferredId`）。登録のあとは `loadSemesters({ preferredId: created.id })`（挙動は今と同じ）
- 編集：モーダルを開くとき（`show.bs.modal`）に、選択中の学期の値を入れる（`fillEditForm`。学期名を、正規表現 `SEMESTER_NAME_PATTERN` で年度と種別に分ける）。最初のフォーカスは年度。保存（`submitSemesterEdit`）では、すべての項目を `PATCH` で送る。成功したら、モーダルを閉じ（`hideModal`）、`loadSemesters({ preferredId: 編集した学期, notifySameSemester: true })`
- 削除：モーダルを開くとき（`show.bs.modal`）に、学期の1件取得で件数を取得する（`prepareDeleteModal`）。授業があれば、件数の行に「削除できません」の文を出し、「削除は取り消せません。」を隠し、「削除する」は押せないまま。授業がなければ、休講日の件数の文を出し、「削除する」を押せるようにする。最初のフォーカスは「キャンセル」。削除（`submitSemesterDelete`）に成功したら、モーダルを閉じ、`loadSemesters()`（今の学期の規則で選び直す。0件なら空状態）
- 編集・削除とも、モーダルを開くたびに増やす通し番号（`editSerial`・`deleteSerial`）で、開き直したあとに届いた古い応答で、今のモーダルの表示を変えない（`subjects.js` と同じ形）。`try` で囲むのは、要求（`apiRequest`）だけ
- 編集・削除のモーダルは、`trackModalShowing` を初期化で1回ずつ呼ぶ（成功したら `hideModal` で閉じるため）。`window.bootstrap.Modal` は、直接は使わない（ボタンの `data-bs-toggle` で開くため）。`show.bs.modal` の取り消し（`preventDefault`）はしない（`trackModalShowing` の記録が残るため）。ボタンは、学期を選んでいるとき（学期の本文を表示しているとき）だけ見えるため、開くときには、選択中の学期が必ずある

### 2-3. 変わる挙動・変わらない挙動

| 操作 | 変わる・変わらない |
|---|---|
| 授業モードの学期の本文 | 学期名の右に「編集」「削除」が足される |
| 学期の登録 | 変わらない（見た目・動き・メッセージ） |
| 学期のタブの切り替え、休講日、授業 | 変わらない。学期を編集したあとは、同じ学期のまま、休講日と授業の一覧を取得し直す |
| カレンダー、課題・タスクモード | 変わらない（学期の期間を変えた結果は、カレンダーのモードを開いたときに取得し直して、表示される） |
| APIの405 | `Allow` ヘッダーが付く（本文は変わらない） |
| 学期の `PATCH`・`DELETE` | 405 から、編集・削除になる |
| 学期の1件取得 | 付加情報 `subject_count`・`closure_count` が付く |

## JavaScriptの共通の規則
`.github/copilot-instructions.md` の「コーディング方針」のJavaScriptの規則と、`docs/architecture.md` の「JavaScriptの構成（ES modules）」の規則（`innerHTML` などを使わない、`textContent` で表示する、`fetch` は `api.js` だけ、`try` で囲むのは要求だけ、名前つきの引数、モードのファイル同士は `import` しない、1行は80文字以内）。付録の全文は、これらに合っている（「Copilot確認手順」の3・6で確かめる）。

## 変更してよい既存のテスト

| ファイル | 変えてよいこと | 変えないこと |
|---|---|---|
| `tests/test_semesters_api.py` | `test_semester_creation_get_and_ordering` の1件取得の期待値、`test_unsupported_semester_methods_return_json_405` の組と `Allow` の確認、`test_api_405_has_allow_header_in_name_order`・`test_regular_page_405_remains_html` の追加（付録Dの全文のとおり） | ほかのテスト（45件） |

- このタスクでの「既存のテスト」は、作業の開始時からあるすべてのテスト（1021件）。上の1ファイルの、上に書いた部分を除き、変えない。**既存のテストが、想定外に失敗した場合**は、テストの期待値や、ほかの仕様を直さない。原因を調べ、そこで実装を止めて、チャットで報告する。特に、授業・休講日・予定・課題・タスクのテスト（`test_subjects_api.py`・`test_subjects_update_delete_api.py`・`test_closures_api.py`・`test_events_api.py`・`test_events_create_update_delete_api.py`・`test_tasks_api.py`）は、変えずに通ること（それぞれの405のテストは、状態コードとエラーのコードだけを確かめているため、`Allow` が付いても通る）

## 実装手順
1. ブランチ・作業ツリーの確認。設計資料が更新されていることを確認する（「Copilot確認手順」の1の `grep`）。更新されていなければ、何も変更せずに停止して報告する
2. 作業の前の状態を記録する：開発用DBの有無・ハッシュ・件数（「Copilot確認手順」の1。**`sqlite3` は `-readonly` を付ける**）。`python -m pytest -q` が1021件、すべて合格すること（合格しなければ、何も変更せずに停止して報告する）。**1の出力は、見出しの行も含めて、報告に、そのまま貼るために控える**（019-N1）
3. **（段階1）** 「全文からファイルを作るスクリプト」を `python - 1` で実行する（出力を控える）。「Copilot確認手順」の2を実施し、`python -m pytest -q` が1119件、すべて合格すること。「全文との比較」（「Copilot確認手順」の4）を `python - 1` で実行し、5ファイルとも「一致」
4. **（段階2）** スクリプトを `python - 2` で実行する（出力を控える）。「Copilot確認手順」の2の `pytest`（2-1）を実施し、1119件、すべて合格すること。「全文との比較」を `python - 2` で実行し、7ファイルとも「一致」
5. 「Copilot確認手順」の3・5・6・7を実施する
6. 結果を報告して、応答を終える（コマンドの出力は、要約せずに、そのまま貼る。サーバーを起動していないこと、ブラウザでの確認をしていないことを明記する）

## 完了条件
- `python -m pytest -q` が、作業の前に **1021件**、段階1・段階2の終わりに **1119件**、すべて合格する（失敗・エラー・スキップが0件）
- 変更・新規のファイルが、「実装対象ファイル」の7つだけ
- 7ファイルが、このTask MDの全文と1文字も違わない（「Copilot確認手順」の4が、段階1の終わりに5ファイル、段階2の終わりに7ファイルとも「一致」）
- `app/`・`tests/`・`run.py` のPythonのファイルに、79文字を超える行がない。`app/static/js/` のJavaScriptのファイルに、80文字を超える行がない
- 「Copilot確認手順」の5（画面のHTMLの確認）と6（検索と差分）が、期待どおり
- 実施の前後で、開発用DB（`instance/app.db`）のハッシュと、`semesters`・`subjects`・`closures`・`events`・`tasks` の件数が同じ
- 「Komaの確認」が、期待どおり
- レビューで承認される

## Copilot確認手順
**`sqlite3` は、必ず `-readonly` を付けて実行する**（011-L1）。**それぞれのコマンドの出力を、要約せずに、`echo` の見出しの行も含めて、そのまま報告に貼る**（014-L1・018-N1・019-N1）。**コマンドは、書いてあるとおりに実行する（書き換えた場合は、報告に書く。016-N1・017-N1）。**

```
# 1. 実施前（出力は、見出しの行も含めて、そのまま報告に貼る。019-N1）
echo "== 1-1 ブランチ（feature/021-semester-edit-delete）"
git branch --show-current
echo "== 1-2 作業ツリー（変更なし）"
git status
echo "== 1-3 設計資料：学期の期間の変更の節（1）"
grep -c -F "#### 学期の期間の変更と予定の同期" docs/architecture.md
echo "== 1-4 設計資料：未決定事項の表の、学期の変更・削除の行（0。外れている）"
grep -c -F "| 学期の変更・削除時の扱い |" docs/architecture.md
echo "== 1-5 設計資料：学期の PATCH・DELETE の行（2）"
grep -c -F -e '| `PATCH /api/semesters/<id>` |' -e '| `DELETE /api/semesters/<id>` |' docs/architecture.md
echo "== 1-6 設計資料：405の Allow と、409の行（2）"
grep -c -F -e '`Allow` ヘッダーを付ける' -e '| 409 | `conflict` |' docs/architecture.md
echo "== 1-7 設計資料：学期の編集・削除の画面の小節（2）"
grep -c -F -e "**編集**（モーダル。2026-10-20に決定）" -e "**削除**（確認のモーダル。2026-10-20に決定）" docs/ui_ux.md
echo "== 1-8 要求定義：学期の未決定の文（0。外れている）"
grep -c -F "学期の変更・削除の扱いは、現時点では未決定" docs/requirements.md
echo "== 1-9 止まる場面の応答（4）"
grep -c -F "止まる場面の応答" .github/copilot-instructions.md
echo "== 1-10 開発用DB（存在すること。なければ、何も変更せずに停止して報告する）"
ls -l instance/app.db
shasum -a 256 instance/app.db
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"
echo "== 1-11 pytest（1021 passed）"
python -m pytest -q

# 2. 各段階の終わり（2-1は段階1・段階2とも。2-2は段階1の終わり）
echo "== 2-1 pytest（1119 passed）"
python -m pytest -q
echo "== 2-2 テストの件数（61・87・86・97。86と97は、変わらない）"
python -m pytest -q --co tests/test_semesters_api.py | tail -1
python -m pytest -q --co tests/test_semesters_update_delete_api.py | tail -1
python -m pytest -q --co tests/test_subjects_update_delete_api.py | tail -1
python -m pytest -q --co tests/test_closures_api.py | tail -1

# 3. 1行の長さ（出力がなければ合格。Pythonは79文字、JavaScriptは80文字まで。migrations/ は対象外）
python - <<'EOF'
from pathlib import Path
python_paths = [*Path("app").rglob("*.py"), *Path("tests").glob("*.py"), Path("run.py")]
for paths, limit in [(python_paths, 79), (sorted(Path("app/static/js").glob("*.js")), 80)]:
    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, 1):
            if len(line) > limit:
                print(f"{path}:{number}: {len(line)}")
EOF

# 4. 全文との比較（011-N1・013-N1）。段階1の終わりは「python - 1」、段階2の終わりは「python - 2」
python - 1 <<'EOF'
import difflib
import sys
from pathlib import Path

# 段階ごとのファイル（「全文からファイルを作るスクリプト」と同じ）。
STAGE_FILES = {
    "1": [
        "app/api_helpers.py",
        "app/routes/semesters.py",
        "app/class_events.py",
        "tests/test_semesters_api.py",
        "tests/test_semesters_update_delete_api.py",
    ],
    "2": [
        "app/templates/index.html",
        "app/static/js/semesters.js",
    ],
}
MARK_START = "<!-- 全文: "
MARK_END = " -->"
newline = chr(10)
fence = "`" * 3


def read_full_texts(task_path):
    """Task MDの「<!-- 全文: パス -->」の行の直後のコードブロックを、
    {パス: 全文} の辞書にする（「全文からファイルを作るスクリプト」と同じ）。"""
    lines = Path(task_path).read_text(encoding="utf-8").split(newline)
    full_texts = {}
    for index, line in enumerate(lines):
        if not (line.startswith(MARK_START) and line.endswith(MARK_END)):
            continue
        if not lines[index + 1].startswith(fence):
            continue
        file_name = line[len(MARK_START):-len(MARK_END)]
        end = lines.index(fence, index + 2)
        full_texts[file_name] = newline.join(lines[index + 2:end]) + newline
    return full_texts


stage = sys.argv[1]
expected_files = read_full_texts("docs/tasks/021_semester_edit_delete.md")
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
    print(newline.join(diff))
EOF

# 5. 画面のHTMLの確認（段階2の終わり。DBを使わない。開発用DBは開かない）
python - <<'EOF'
import re
import tempfile
from pathlib import Path

from app import create_app

newline = chr(10)
EXPECTED_IDS = [
    "semester-edit-button", "semester-delete-button",
    "semester-edit-modal", "semester-edit-modal-title", "semester-edit-form",
    "semester-edit-form-error", "semester-edit-year", "semester-edit-term",
    "semester-edit-name-error", "semester-edit-start-date",
    "semester-edit-start-date-error", "semester-edit-end-date",
    "semester-edit-end-date-error", "semester-edit-notice",
    "semester-edit-submit-button",
    "semester-delete-modal", "semester-delete-modal-title",
    "semester-delete-target", "semester-delete-loading",
    "semester-delete-counts", "semester-delete-error",
    "semester-delete-warning", "semester-delete-cancel-button",
    "semester-delete-submit-button",
]
ORDER = [
    "semester-detail-name", "semester-edit-button", "semester-delete-button",
    "semester-detail-period", "closure-section", "semester-modal",
    "semester-edit-modal", "semester-delete-modal", "subject-modal",
]

with tempfile.TemporaryDirectory() as work_directory:
    database_path = Path(work_directory) / "check.db"
    app = create_app(
        {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"}
    )
    client = app.test_client()
    html = client.get("/").get_data(as_text=True)
    ids = re.findall(' id="([^"]+)"', html)
    print("新しいidの数:", len(EXPECTED_IDS))
    print("新しいidで、1つでないもの:", [i for i in EXPECTED_IDS if ids.count(i) != 1])
    print("重複したid:", sorted({i for i in ids if ids.count(i) > 1}))
    positions = [html.index(f'id="{i}"') for i in ORDER]
    print("並び:", positions == sorted(positions))
    print("モーダルは<main>の外:", html.index("</main>") < positions[5])
    print("モーダルを開くボタン:", re.findall('data-bs-target="(#semester-[a-z-]+)"', html))
    print("説明（aria-describedby）:", re.findall('aria-describedby="(semester-[^"]+)"', html))
    # JavaScriptが getElement("…") で使うidと、semesters.js の「"semester-…"」の
    # 文字列のid（イベント名の semester-selected を除く）が、HTMLにあること。
    missing = []
    get_element = 'getElement[(][ ' + newline + ']*"([^"]+)"'
    for path in sorted(Path("app/static/js").glob("*.js")):
        text = path.read_text(encoding="utf-8")
        for element_id in re.findall(get_element, text):
            if element_id not in ids:
                missing.append(f"{path.name}:{element_id}")
    text = Path("app/static/js/semesters.js").read_text(encoding="utf-8")
    for element_id in re.findall('"(semester-[a-z-]+)"', text):
        if element_id != "semester-selected" and element_id not in ids:
            missing.append(f"semesters.js:{element_id}")
    print("JavaScriptのidで、HTMLにないもの:", missing)
    for name in ["js/semesters.js", "js/ui.js", "js/main.js"]:
        response = client.get(f"/static/{name}")
        print(name, response.status_code, response.mimetype)
        response.close()
EOF

# 6. 検索と差分（段階2の終わり。各コマンドの前の echo の見出しも、出力として貼る。018-N1）
echo "== 6-1 .query（出力なし。Semester.query などを使わない）"
grep -rn -F --include="*.py" ".query" app/
echo "== 6-2 assert（出力なし。app/ に assert を書かない）"
grep -rn -F --include="*.py" "assert " app/
echo "== 6-3 学期のroute（5件：get・get・post・patch・delete の順）"
grep -n -F "@semesters_bp." app/routes/semesters.py
echo "== 6-4 commit（3件：登録・編集・削除で1回ずつ）"
grep -n -F "commit()" app/routes/semesters.py
echo "== 6-5 conflict（2件：api_helpers.py の ERROR_STATUS_CODES と、semesters.py の削除）"
grep -rn -F --include="*.py" '"conflict"' app/
echo "== 6-6 Allow（1件：api_helpers.py の405のエラーハンドラー）"
grep -rn -F --include="*.py" '"Allow"' app/
echo "== 6-7 今日（1件：subjects.py の current_date の中だけ。学期のAPIは使わない）"
grep -rn -F --include="*.py" -e "date.today" -e "datetime.now" app/
echo "== 6-8 削除の連動（出力なし）"
grep -rn -F --include="*.py" -e "cascade" -e "ondelete" app/
echo "== 6-9 semesters.py の予定の作成（3件：import 1と、class_event_dates・build_class_event の呼び出し各1）"
grep -n -F -e "build_class_event" -e "class_event_dates" app/routes/semesters.py
echo "== 6-10 使わない書き方（出力なし）"
grep -rn -F -e innerHTML -e outerHTML -e insertAdjacentHTML -e "document.write" -e "eval(" -e localStorage -e sessionStorage -e setTimeout -e "export default" -e "var " -e ".style" -e "confirm(" app/static/js/
echo "== 6-11 fetch を呼ぶ場所（1件：api.js）"
grep -rn -F " fetch(" app/static/js/
echo "== 6-12 semester-selected（6件。ファイルと行番号だけを出す：closures.js 1、semesters.js 3（コメント2、発行1）、subjects.js 1、main.js 1（コメント））"
grep -rn -F "semester-selected" app/static/js/ | cut -d: -f1,2
echo "== 6-13 trackModalShowing・hideModal（26件：calendar.js 2、event_forms.js 6、semesters.js 6、subjects.js 4、tasks.js 6、ui.js 2（定義））"
grep -rn -F -e "trackModalShowing(" -e "hideModal(" app/static/js/ | cut -d: -f1 | sort | uniq -c
echo "== 6-14 window.bootstrap.Modal（8件：semesters.js にはない）"
grep -rn -F "window.bootstrap.Modal" app/static/js/ | cut -d: -f1 | sort | uniq -c
echo "== 6-15 semesters.js の export（1件：initSemesters）"
grep -n -F "export " app/static/js/semesters.js
echo "== 6-16 HTMLの onclick・style 属性（出力なし）"
grep -n -F -e onclick -e "style=" app/templates/index.html app/templates/base.html
echo "== 6-17 変更したファイルの行数（6行：15 3 api_helpers.py、1 1 class_events.py、285 56 semesters.py、275 17 semesters.js、78 1 index.html、47 7 test_semesters_api.py）"
git diff --numstat app/api_helpers.py app/class_events.py app/routes/semesters.py app/static/js/semesters.js app/templates/index.html tests/test_semesters_api.py
echo "== 6-18 新しいテストのファイルの行数（1077）"
wc -l tests/test_semesters_update_delete_api.py
echo "== 6-19 変えないファイル（出力なし）"
git diff --stat -- app/models/ app/__init__.py app/categories.py app/routes/subjects.py app/routes/closures.py app/routes/events.py app/routes/tasks.py app/routes/main.py migrations/ tests/conftest.py tests/test_api_helpers.py tests/test_class_events.py tests/test_closures_api.py tests/test_events_api.py tests/test_events_create_update_delete_api.py tests/test_setup.py tests/test_subjects_api.py tests/test_subjects_update_delete_api.py tests/test_tasks_api.py requirements.txt pytest.ini run.py app/templates/base.html app/static/css/ app/static/js/main.js app/static/js/ui.js app/static/js/api.js app/static/js/dates.js app/static/js/categories.js app/static/js/current_semester.js app/static/js/subject_options.js app/static/js/task_display.js app/static/js/subjects.js app/static/js/closures.js app/static/js/calendar.js app/static/js/event_forms.js app/static/js/tasks.js

# 7. 実施後
echo "== 7-1 開発用DB（実施前と同じ）"
shasum -a 256 instance/app.db
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"
echo "== 7-2 git status（変更：6ファイル。新規：test_semesters_update_delete_api.py）"
git status
echo "== 7-3 git diff --stat"
git diff --stat
```

| 確認 | 期待する結果 |
|---|---|
| 実施前（1） | 各見出しの括弧の中のとおり（1-3〜1-9は、件数の数字だけが出る） |
| `python -m pytest -q` | 実施前1021件、段階1・段階2の終わり1119件が、すべて合格。失敗・エラー・スキップが0件。`migrations/env.py` の `DeprecationWarning` は、出ても構わない（報告する） |
| テストの件数（2-2） | 上から `61 tests collected`・`87 tests collected`・`86 tests collected`・`97 tests collected` |
| 1行の長さ（3） | 出力なし |
| 全文との比較（4） | `全文の数：7` と、段階1の終わりは5ファイル、段階2の終わりは7ファイルとも「一致」。「不一致」が出たら、手で直さず、その段階の「全文からファイルを作るスクリプト」をもう一度実行して全文に戻し、2からやり直す（戻したことを報告する）。Task MDの全文のほうを変える必要があると判断した場合は、停止して報告する |
| 画面のHTMLの確認（5） | 「新しいidの数: 24」「新しいidで、1つでないもの: []」「重複したid: []」「並び: True」「モーダルは<main>の外: True」「モーダルを開くボタン: ['#semester-modal', '#semester-modal', '#semester-modal', '#semester-edit-modal', '#semester-delete-modal']」「説明（aria-describedby）: ['semester-edit-notice', 'semester-delete-target semester-delete-counts semester-delete-warning', 'semester-delete-target semester-delete-counts semester-delete-warning']」「JavaScriptのidで、HTMLにないもの: []」。3つのJavaScriptのファイルが `200 text/javascript` |
| 検索と差分（6） | 各見出しの括弧の中のとおり（件数が違う場合は、その見出しと出力を報告に書く） |
| 開発用DB | 実施の前後で、ハッシュと、5つのテーブルの件数が同じ |
| `git status` | 変更：`app/api_helpers.py`、`app/class_events.py`、`app/routes/semesters.py`、`app/static/js/semesters.js`、`app/templates/index.html`、`tests/test_semesters_api.py`。新規（`??`）：`tests/test_semesters_update_delete_api.py`。`app/models/`・`migrations/`・`docs/`・`.github/`・`requirements.txt`・`run.py`・`instance/`・ほかのPython・JavaScriptのファイル・`base.html`・`style.css` に変更なし |

`.pytest_cache/` や `__pycache__/` が `git status` に表示される場合は、`.gitignore` を変更せず、報告する。**Copilotは、サーバーを起動せず、ブラウザでの確認もしない**（Claude と Koma が行う）。報告に、そのことを明記する。

## Komaの確認
順序：（1）pytest →（2）commit・push とレビューの依頼 →（3）ブラウザでの確認（確認用のサーバー）→（4）開発用DBでの、読み取りだけの確認 →（5）マージ。

### 1. pytest
`python -m pytest -q` を自分で実行し、**1119件、すべて合格**することを確かめる。

### 2. push とレビューの依頼
featureブランチを commit・push する（PRを作ってもよい）。新規のファイル（`tests/test_semesters_update_delete_api.py`）も、commitに含める。Copilotの完了報告を共有して、Claudeにレビューを頼む。**pushは、マージではない。レビューの承認の前に、マージしない。** 修正が必要になった場合は、同じブランチでCopilotが直し、もう一度pushしてレビューを受ける。

### 3. ブラウザでの確認（確認用のサーバー）
レビューで「承認可能」になったあとに行う。**ブラウザの操作は、Claudeが、ブラウザのパネルまたはChromeで行う。Komaは、サーバーの起動・停止、確認用のデータの登録、DBのハッシュの確認、後片付けを行う**（roadmap の「進め方の決定の記録」、2026-10-12）。

#### 確認の安全のしくみ
- **開発用DBは使わない。** 確認用のDB（`/tmp/schedule-app-check-021/check.db`）を、migrationで作り、そのDBで起動した確認用のサーバーで確かめる（Task 010〜020と同じ方法）。開発用DBには、何も残らない
- 確認用のデータ（下の「確認用のデータの登録」）は、確認用のDBの場所を指定して、すべてアプリのAPIで登録する。**このスクリプトは、確認用のDBだけに書き込む**
- 確認の途中の、APIの直接の呼び出し（E3の学期・授業の登録、E4の授業の削除、各項目の読み取り）は、確認用のDBの、確認のために登録したデータに限る（roadmap の「進め方の決定の記録」、2026-10-12）
- ブラウザは、BootstrapとFullCalendarを、インターネット（jsDelivr）から読み込む。インターネットにつながった状態で行う
- 確認の前後で、開発用DBのハッシュが同じことを確かめる

#### 確認の日付と、確認の書き方
- 確認用のデータの日付は、**データを登録した日（このMacの「今日」。以下 T）からの相対**で決める。下の表の日付の例は、**T が 2026年10月21日（水）の場合**（Claudeが、実際の T に読み替える。`setValue` に入れる日付も、読み替える）。確認は、日付をまたがずに行う（日付をまたいだ場合は、後片付けをしてから、準備からやり直す）
- **どの手順も、T の曜日によらない**（週表示の移動を使わない。カレンダーは、今日から28日間の一覧表示で確かめる。020-N3）。空き枠を押す手順はない（020-N2）
- 画面の表示は、DOMで確かめる（スクリーンショットは、古いことがある。018-N2）。カレンダーに、ほかの場所の変更を反映させるときは、画面下の「カレンダー」を押す（カレンダーのモードを開くたびに、取得し直す。018-N2）
- 「押す」は、マウスで押す（JavaScriptの `click()` を使わない。フォーカスの確認は、押したボタンにフォーカスがあることが前提のため）。入力欄への入力は、キーボードで入力するか、下の「確認用の関数」の `setValue` を使う（年度・日付の欄は、`setValue` を使ってよい）
- ページを開き直したら、「確認用の関数」を、もう一度コンソールに貼る

#### 準備
1. `python run.py` が起動していれば、Ctrl＋Cで止める（確認用のサーバーも、5001番を使うため）。開発用DBのハッシュを控える
   ```
   shasum -a 256 instance/app.db
   ```
2. 下の「確認用のサーバーの起動」のコマンドで、確認用のサーバーを起動する（このターミナルは、確認の間、開いたままにする）
3. 別のターミナルを開き、リポジトリのルートで、`.venv` を有効にして、下の「確認用のデータの登録」を実行する（1回だけ）
4. Claudeが、ブラウザで `http://127.0.0.1:5001/` を開き、ページを開き直す（ブラウザの幅は、1200px以上にする）
5. Claudeが、コンソールに、下の「確認用の関数」を貼る

#### 確認用のサーバーの起動
ブランチ `feature/021-semester-edit-delete` のまま、リポジトリのルートで、`.venv` を有効にして、次を実行する（行の先頭に空白を入れずにコピーする）。

```
python - <<'EOF'
from pathlib import Path

from flask_migrate import upgrade

from app import create_app

# 確認用のDB（開発用DBとは別のファイル）。止めて起動し直しても、残る。
check_directory = Path("/tmp/schedule-app-check-021")
check_directory.mkdir(exist_ok=True)
database_path = check_directory / "check.db"
app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"})
with app.app_context():
    upgrade(directory="migrations")
print(f"確認用のDB：{database_path}", flush=True)
app.run(host="127.0.0.1", port=5001, debug=False)
EOF
```

期待する出力：初めての起動では、`Running upgrade  -> 0280f6cf8d09, initial tables` と `Running upgrade 0280f6cf8d09 -> 42bd53808fa1, add closures table`、「確認用のDB：/tmp/schedule-app-check-021/check.db」、`Running on http://127.0.0.1:5001`。起動し直したときは、`Running upgrade` の行が出ない。

#### 確認用のデータの登録
確認用のサーバーを起動したあとに、別のターミナルで、1回だけ実行する（行の先頭に空白を入れずにコピーする）。

```
python - <<'EOF'
from datetime import date, timedelta
from pathlib import Path

from app import create_app

# 確認用のDBだけに書き込む（開発用DBは使わない）。DBは、確認用のサーバーが、
# 起動のときにmigrationで作っておいたものを使う。
database_path = Path("/tmp/schedule-app-check-021/check.db")
if not database_path.exists():
    raise SystemExit("確認用のDBがありません。先に、確認用のサーバーを起動してください")
app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"})
client = app.test_client()
# 日付は、今日（このMacの日付。ブラウザの「今日」と同じ）からの相対で決める。
today = date.today()
WEEKDAYS = "月火水木金土日"


def day(offset):
    return (today + timedelta(days=offset)).isoformat()


def send(method, url, body, expected_status):
    response = client.open(url, method=method, json=body)
    if response.status_code != expected_status:
        raise SystemExit(f"中止：{method} {url} {response.status_code} {response.get_json()}")
    return response.get_json()


def class_event_ids(subject_id, offset):
    events = client.get(f"/api/events?start_date={day(offset)}&end_date={day(offset)}").get_json()
    return [event["id"] for event in events if event["subject_id"] == subject_id]


# 学期・休講日・授業は、すべてAPIで登録する（休講日は、授業より先に登録する）。
semesters = [
    send("POST", "/api/semesters", {"name": "2026年度 後期", "start_date": day(-42), "end_date": day(42)}, 201),
    send("POST", "/api/semesters", {"name": "2025年度 後期", "start_date": day(-400), "end_date": day(-300)}, 201),
]
closures = [
    send("POST", "/api/closures", {"semester_id": semesters[0]["id"], "date": day(7), "name": "テスト：休講日1"}, 201),
    send("POST", "/api/closures", {"semester_id": semesters[0]["id"], "date": day(35), "name": "テスト：休講日2"}, 201),
    send("POST", "/api/closures", {"semester_id": semesters[1]["id"], "date": day(-350), "name": "テスト：前の学期の休講日"}, 201),
]
subjects = [
    send("POST", "/api/subjects", {"semester_id": semesters[0]["id"], "subject_name": "テスト：今日の曜日の授業", "weekday": today.weekday(), "start_time": "13:00", "end_time": "14:30", "room": "3号館201"}, 201),
    send("POST", "/api/subjects", {"semester_id": semesters[0]["id"], "subject_name": "テスト：2日後の曜日の授業", "weekday": (today.weekday() + 2) % 7, "start_time": "09:00", "end_time": "10:00"}, 201),
]
# 14日後の授業1の予定を、その日だけ編集しておく（期間を変えても、両方の
# 期間に入る日の予定は変わらないことを、確かめるため）。
edited_ids = class_event_ids(subjects[0]["id"], 14)
send("PATCH", f"/api/events/{edited_ids[0]}", {"room": "テスト：5号館101"}, 200)
print(f"今日：{today.isoformat()}（{WEEKDAYS[today.weekday()]}）")
print("学期のid：", [semester["id"] for semester in semesters])
print("休講日のid：", [closure["id"] for closure in closures])
print("授業のid：", [subject["id"] for subject in subjects])
print("授業の予定の件数：", [subject["generated_event_count"] for subject in subjects])
print("14日後・21日後の授業1の予定のid：", edited_ids, class_event_ids(subjects[0]["id"], 21))
EOF
```

期待する出力（T が 2026-10-21 の場合）：

```
今日：2026-10-21（水）
学期のid： [1, 2]
休講日のid： [1, 2, 3]
授業のid： [1, 2]
授業の予定の件数： [11, 12]
14日後・21日後の授業1の予定のid： [8] [9]
```

1行目の日付が、今日（T）。どの曜日でも、2行目以降は同じになる。2回目に実行すると、「中止：POST /api/semesters 400 …」で止まり、何も増えない（そのままでよい）。

以下、idは、この出力のとおり。

| 種類 | id：内容 |
|---|---|
| 学期 | 1：「2026年度 後期」（T−42〜T+42。例：2026-09-09〜2026-12-02）、2：「2025年度 後期」（T−400〜T−300。例：2025-09-16〜2025-12-25。授業なし） |
| 休講日 | 1：テスト：休講日1（学期1、T+7。例：2026-10-28）、2：テスト：休講日2（学期1、T+35。例：2026-11-25）、3：テスト：前の学期の休講日（学期2、T−350） |
| 授業 | 1：テスト：今日の曜日の授業（学期1、T と同じ曜日、13:00〜14:30、3号館201。自動生成の予定11件（T+7・T+35は休講日）。T+14 の予定（id 8）は、教室を「テスト：5号館101」に変えてある。T+21 の予定は id 9）、2：テスト：2日後の曜日の授業（学期1、T+2 と同じ曜日、09:00〜10:00。自動生成の予定12件） |

#### 確認用の関数
コンソールに、そのまま貼る（ページを開き直したら、もう一度貼る）。`setValue(id, value)` は、入力欄に値を入れ、入力したときと同じイベントを起こす。`semesterState()` は、授業モードの学期の表示（`tabs` はタブの名前（選択中のタブには「（選択中）」）、`name`・`period` は本文、`buttons` は「編集」「削除」の `aria-label`、`closures` は休講日の一覧の行、`focus` はフォーカスのある要素の `id`）を返す。`editFormState()` は、学期の編集のモーダルの状態（`values` は年度・種別・開始日・終了日、`errors` は学期名・開始日・終了日の下のエラー、`formError` はフォームの上部のエラー）を返す。`deleteState()` は、学期の削除の確認のモーダルの状態（隠れている行は `null`。`warning` は「削除は取り消せません。」が見えているか、`submit` は「削除する」ボタンの文字と、押せないか）を返す。`eventCounts()` は、授業1・授業2の予定の件数（授業の1件取得の `event_count`）を返す。`listCounts()` は、カレンダーの一覧表示の、授業1・授業2の行の数を返す。

```
window.setValue = (id, value) => { const input = document.getElementById(id); input.value = value; input.dispatchEvent(new Event("input", { bubbles: true })); input.dispatchEvent(new Event("change", { bubbles: true })); };
window.semesterState = () => ({ tabs: [...document.querySelectorAll("#semester-tabs [role=tab]")].map((tab) => `${tab.textContent}${tab.getAttribute("aria-selected") === "true" ? "（選択中）" : ""}`), name: document.getElementById("semester-detail-name").textContent, period: document.getElementById("semester-detail-period").textContent, buttons: ["semester-edit-button", "semester-delete-button"].map((id) => document.getElementById(id).getAttribute("aria-label")), closures: [...document.querySelectorAll("#closure-list li div")].map((row) => row.textContent), focus: document.activeElement.id });
window.editFormState = () => ({ values: ["year", "term", "start-date", "end-date"].map((id) => document.getElementById(`semester-edit-${id}`).value), errors: ["name", "start-date", "end-date"].map((id) => document.getElementById(`semester-edit-${id}-error`).textContent), formError: document.getElementById("semester-edit-form-error").textContent, focus: document.activeElement.id });
window.deleteState = () => { const element = (id) => document.getElementById(`semester-delete-${id}`); const shown = (id) => !element(id).classList.contains("d-none"); return { target: element("target").textContent, loading: shown("loading"), counts: shown("counts") ? element("counts").textContent : null, error: shown("error") ? element("error").textContent : null, warning: shown("warning"), submit: [element("submit-button").textContent, element("submit-button").disabled], focus: document.activeElement.id }; };
window.eventCounts = async () => Promise.all([1, 2].map(async (id) => (await (await fetch(`/api/subjects/${id}`)).json()).event_count));
window.listCounts = () => ["テスト：今日の曜日の授業", "テスト：2日後の曜日の授業"].map((title) => [...document.querySelectorAll(".fc-list-event-title")].filter((cell) => cell.textContent.includes(title)).length);
```

#### A. 表示

| No | 操作 | 期待する結果 |
|---|---|---|
| A1 | 画面下の「授業」を押す。`semesterState()` を実行する | 本文の「2026年度 後期」の右に、「編集」（グレーの枠）と「削除」（赤い枠）のボタン。結果の `tabs` は `["2026年度 後期（選択中）", "2025年度 後期"]`、`name` は `"2026年度 後期"`、`period` は `"2026年9月9日 〜 2026年12月2日"`、`buttons` は `["「2026年度 後期」を編集", "「2026年度 後期」を削除"]`、`closures` は `["2026年10月28日（水）テスト：休講日1", "2026年11月25日（水）テスト：休講日2"]` |

#### B. 編集のモーダルと、入力エラー

| No | 操作 | 期待する結果 |
|---|---|---|
| B1 | 「編集」を押す。`editFormState()` を実行する | モーダル「学期を編集」が開く。上から、年度・種別、開始日、終了日、黄色の枠の注意書き（「期間を変えると、新しい期間から外れる日の、授業の予定（…）と休講日は、削除されます。…変わりません。」）。下に「キャンセル」「保存する」。結果は `{ values: ["2026", "後期", "2026-09-09", "2026-12-02"], errors: ["", "", ""], formError: "", focus: "semester-edit-year" }` |
| B2 | `setValue("semester-edit-year", "2025")` を実行し、「保存する」を押す。`editFormState()` を実行する。Escapeキーを押す | 年度・種別の下に、赤い字で「同じ名前の学期がすでに登録されています」。結果の `errors` は `["同じ名前の学期がすでに登録されています", "", ""]`、`focus` は `"semester-edit-submit-button"`（017-N2）。Escapeキーで閉じる |
| B3 | 「編集」を押す。`editFormState()` を実行する。`setValue("semester-edit-end-date", "2026-09-09")`（開始日と同じ日）を実行し、「保存する」を押す。`editFormState()` を実行する。「キャンセル」を押す | 1つ目：B2の入力とエラーが消え、今の値に戻っている（`values` は B1 と同じ、`errors` は `["", "", ""]`）。2つ目：終了日の下に「終了日は開始日より後にしてください」（`errors` は `["", "", "終了日は開始日より後にしてください"]`）。「キャンセル」で閉じる（保存しない） |

#### C. 期間を縮める
両方の期間に入る日の予定は変わらず、新しい期間の外の、自動生成の予定と休講日が消えることを確かめる。

| No | 操作 | 期待する結果 |
|---|---|---|
| C1 | 画面下の「カレンダー」を押す。「一覧」を押す。`listCounts()` を実行する | 今日から28日間の一覧表示。結果は `[3, 4]`（授業1は、T・T+14・T+21。T+7は休講日。授業2は、T+2・T+9・T+16・T+23） |
| C2 | 画面下の「授業」を押す。「編集」を押す。`setValue("semester-edit-end-date", "2026-11-10")`（T+20）を実行し、「保存する」を押す。`semesterState()` と `await eventCounts()` を実行する | モーダルが閉じる。結果の `period` は `"2026年9月9日 〜 2026年11月10日"`、`closures` は `["2026年10月28日（水）テスト：休講日1"]`（T+35 の休講日2は、新しい期間の外のため、削除された）、`focus` は `"semester-edit-button"`。`eventCounts()` は `[8, 9]`（授業1は T+21・T+28・T+42、授業2は T+23・T+30・T+37 の、それぞれ3件が削除された） |
| C3 | `(await (await fetch("/api/events/8")).json()).room` と `(await fetch("/api/events/9")).status` を実行する | 1つ目は `"テスト：5号館101"`（両方の期間に入る T+14 の予定は、個別に変えた教室のまま）。2つ目は `404`（T+21 の予定は、削除された） |
| C4 | 画面下の「カレンダー」を押す（予定を取得し直す）。`listCounts()` を実行する | 一覧表示のまま。結果は `[2, 3]`（授業1は T・T+14、授業2は T+2・T+9・T+16） |

#### D. 期間を広げる・名前を変える

| No | 操作 | 期待する結果 |
|---|---|---|
| D1 | 画面下の「授業」を押す。「編集」を押す。`setValue("semester-edit-end-date", "2026-12-02")`（T+42。元の終了日）を実行し、「保存する」を押す。`semesterState()` と `await eventCounts()` を実行する | 結果の `period` は `"2026年9月9日 〜 2026年12月2日"`、`closures` は `["2026年10月28日（水）テスト：休講日1"]`（削除された休講日2は、戻らない）。`eventCounts()` は `[12, 12]`（授業1は、T+21・T+28・T+42 と、休講日2がなくなった T+35 の4件が作られた。授業2は、3件が作られた） |
| D2 | 「編集」を押す。種別で「前期」を選び、「保存する」を押す。`semesterState()` と `await eventCounts()` を実行する | タブと本文の名前が「2026年度 前期」になる。結果の `tabs` は `["2026年度 前期（選択中）", "2025年度 後期"]`、`buttons` は `["「2026年度 前期」を編集", "「2026年度 前期」を削除"]`、`period` は D1 と同じ。`eventCounts()` は `[12, 12]`（名前だけの変更では、予定は変わらない） |
| D3 | 「授業を追加」を押す。「閉じる」を押す | 授業の登録のモーダルの上部が「登録先の学期：2026年度 前期」（新しい名前） |

#### H. 405の Allow

| No | 操作 | 期待する結果 |
|---|---|---|
| H1 | `(await fetch("/api/semesters", { method: "PUT" })).headers.get("Allow")` と `(await fetch("/api/semesters/1", { method: "POST" })).headers.get("Allow")` を実行する | 1つ目は `"GET, HEAD, OPTIONS, POST"`、2つ目は `"DELETE, GET, HEAD, OPTIONS, PATCH"` |

#### E. 削除

| No | 操作 | 期待する結果 |
|---|---|---|
| E1 | 「削除」を押す。`deleteState()` を実行する。「キャンセル」を押す。`document.activeElement.id` を実行する | モーダル「学期を削除」が開く。結果は `{ target: "「2026年度 前期」（2026年9月9日 〜 2026年12月2日）を削除します。", loading: false, counts: "この学期には、授業が2件登録されているため、削除できません。先に、この画面の授業の一覧から、授業をすべて削除してください。", error: null, warning: false, submit: ["削除する", true], focus: "semester-delete-cancel-button" }`（「削除は取り消せません。」は出ず、「削除する」は押せない）。2つ目の結果は `"semester-delete-button"` |
| E2 | タブの「2025年度 後期」を押す。「削除」を押す。`deleteState()` を実行する。「削除する」を押す。`semesterState()` と `(await (await fetch("/api/closures")).json()).map((closure) => closure.id)` を実行する | 1つ目は `{ target: "「2025年度 後期」（2025年9月16日 〜 2025年12月25日）を削除します。", loading: false, counts: "この学期の休講日1件も、まとめて削除されます。", error: null, warning: true, submit: ["削除する", false], focus: "semester-delete-cancel-button" }`。削除すると、モーダルが閉じ、結果の `tabs` は `["2026年度 前期（選択中）"]`。休講日のidは `[1]`（前の学期の休講日（id 3）も、削除された） |
| E3 | コンソールで、下の「E3の1」を実行する（学期「2027年度 前期」の登録）。ページを開き直し、「確認用の関数」を貼る。画面下の「授業」を押し、タブの「2027年度 前期」を押す。「削除」を押す。`deleteState()` を実行する。コンソールで、下の「E3の2」を実行する（ほかの場所で授業が登録された場合の再現）。「削除する」を押す。`deleteState()` を実行する。Escapeキーを押す | 「E3の1」の結果は `2`（学期のid。削除した学期のidが、使い直される）。1つ目の `deleteState()` は、`target` が `"「2027年度 前期」（2027年5月9日 〜 2027年8月17日）を削除します。"`、`counts` が `"この学期の休講日0件も、まとめて削除されます。"`、`submit` が `["削除する", false]`。「E3の2」の結果は `201`。「削除する」を押すと、モーダルの中に、赤い枠で「授業が登録されている学期は削除できません。先に、授業をすべて削除してください」（2つ目の `deleteState()` の `error`）。`submit` は `["削除する", false]`、`focus` は `"semester-delete-submit-button"`。Escapeキーで閉じる |

```
// E3の1（学期の登録。日付は、T+200〜T+300 に読み替える）
(await (await fetch("/api/semesters", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: "2027年度 前期", start_date: "2027-05-09", end_date: "2027-08-17" }) })).json()).id
// E3の2（学期2への授業の登録）
(await fetch("/api/subjects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ semester_id: 2, subject_name: "テスト：あとから足した授業", weekday: 0, start_time: "09:00", end_time: "10:00" }) })).status
```

#### S. サーバーに接続できないとき

| No | 操作 | 期待する結果 |
|---|---|---|
| S1 | **Komaが、確認用のサーバーを止める（Ctrl＋C）。** Claudeが、「削除」を押す（選択中は「2027年度 前期」）。`deleteState()` を実行する。「キャンセル」を押す | 結果の `loading` は `false`、`counts` は `null`、`error` は `"サーバーに接続できませんでした。時間をおいて、もう一度お試しください"`、`submit` は `["削除する", true]`（押せない） |
| S2 | 「編集」を押す。「保存する」を押す。`editFormState()` を実行する。Escapeキーを押す | フォームの上部に、赤い枠で「サーバーに接続できませんでした。時間をおいて、もう一度お試しください」（結果の `formError`）。`focus` は `"semester-edit-submit-button"`。Escapeキーで閉じる |
| S3 | **Komaが、「確認用のサーバーの起動」のコマンドで、確認用のサーバーを起動し直す**（ターミナルで↑キーを押すと、前のコマンドを呼び出せる）。Claudeが、「削除」を押す。`deleteState()` を実行する。「キャンセル」を押す | 結果の `counts` は `"この学期には、授業が1件登録されているため、削除できません。先に、この画面の授業の一覧から、授業をすべて削除してください。"`、`error` は `null` |

#### F. すべて削除して、空にする

| No | 操作 | 期待する結果 |
|---|---|---|
| F1 | `(await fetch("/api/subjects/3", { method: "DELETE" })).status` を実行する（E3で登録した授業の削除）。「削除」を押す。`deleteState()` を実行する。「削除する」を押す。`semesterState()` を実行する | 1つ目は `204`。`deleteState()` の `counts` は `"この学期の休講日0件も、まとめて削除されます。"`、`submit` は `["削除する", false]`。削除すると、モーダルが閉じ、結果の `tabs` は `["2026年度 前期（選択中）"]` |
| F2 | 授業の一覧で、「テスト：今日の曜日の授業」の「削除」を押し、「削除する」を押す。「テスト：2日後の曜日の授業」も、同じく削除する。本文の「削除」を押す。`deleteState()` を実行する。「削除する」を押す | 授業の一覧が「この学期には、まだ授業が登録されていません」になる。`deleteState()` の `counts` は `"この学期の休講日1件も、まとめて削除されます。"`。削除すると、「学期がまだ登録されていません。最初の学期を登録してください」と「最初の学期を登録する」ボタンだけになる（タブ・「編集」「削除」・休講日・授業の欄は出ない） |
| F3 | `[(await (await fetch("/api/semesters")).json()).length, (await (await fetch("/api/closures")).json()).length, (await (await fetch("/api/events?start_date=2025-01-01&end_date=2027-12-31")).json()).length]` を実行する | `[0, 0, 0]` |

#### X. 確認の全体を通して

| No | 確認 | 期待する結果 |
|---|---|---|
| X1 | コンソール | JavaScriptの例外（`Uncaught …`）が出ていない。想定した記録（B2・B3の400、C3の404、H1の405、E3の409、サーバーを止めている間（S1・S2）の接続の失敗（`net::ERR_CONNECTION_REFUSED`）の「Failed to load resource」）は、除く（010-N1） |

#### 後片付け
1. 確認用のサーバーを止める（Ctrl＋C）
2. 確認用のDBのフォルダを消す
   ```
   rm -r /tmp/schedule-app-check-021
   ```
3. 開発用DBのハッシュが、準備の1と同じことを確かめる
   ```
   shasum -a 256 instance/app.db
   ```

ハッシュが変わっていた場合は、開発用DBを操作せずに、Claudeに伝える。

### 4. 開発用DBでの、読み取りだけの確認
3が期待どおりなら、開発用DBで起動して、画面が開くことだけを確かめる（**登録・編集・削除はしない**）。

```
shasum -a 256 instance/app.db          # 控える
python run.py                          # 開発用DBで起動
# ブラウザでの確認のあと、サーバーを Ctrl+C で止めてから
shasum -a 256 instance/app.db          # 起動の前と同じ
```

| 確認 | 期待 |
|---|---|
| ブラウザで開き、ページを開き直す。画面下の「授業」を押す | 「学期がまだ登録されていません。最初の学期を登録してください」と「最初の学期を登録する」ボタン（開発用DBに学期がないため。「編集」「削除」は出ない）。コンソールに、JavaScriptの例外がない |
| 最後のハッシュ | 起動の前と同じ |

### 5. マージ
1〜4が期待どおりで、レビューで承認されたら、マージする。このタスクは、DBの構造を変えないため、開発用DBへのmigrationの適用はない。開発用DBのデータも変えないため、バックアップは要らない。

マージのあとは、授業モードから、学期の名前・期間を編集でき、授業のない学期を削除できる。開発用DBで、期間を変えたり、学期を削除したりすると、予定・休講日が削除される（元に戻せない。`docs/architecture.md` の「開発中の注意」）。

## Git操作
**Git commit / push / ブランチ操作 / マージは行わない**（`git branch --show-current`、`git status`、`git diff` のような読み取りだけのコマンドは除く）。

## 注意
- **停止して報告する条件**（ファイルを変更せず、実装を止め、チャットで「問題点・発生理由・変更した場合の影響・推奨案（必要なら）」を報告する）
  - ブランチの不一致、作業ツリーの想定外の変更
  - 設計資料が更新されていない（実装手順の1）、または、設計資料とこのTask MDの間に、矛盾・不足がある
  - 設計資料にない判断が必要になった（特に、`docs/architecture.md` の「未決定事項」や、`docs/ui_ux.md` の「未決定」に触れる場合）
  - 「全文からファイルを作るスクリプト」の出力が、期待と違う（全文の数・行数・エラー）
  - 「変更しない」と定めたもの（モデル、ほかのroute、ほかのJavaScriptのファイル、既存のテストなど）を変更しないと実装できない。または、7ファイルの全文を変える必要があると判断した
  - 開発用DB（`instance/app.db`）がない
  - 作業の前の `python -m pytest` が、1021件すべて合格しない
  - **既存のテスト**（作業の開始時からある1021件。「変更してよい既存のテスト」の部分を除く）**が、想定外に失敗した**。テストの期待値や、ほかの仕様を直さずに、原因を調べて報告する
  - DBの構造の変更（migration）や、モデルの変更、ライブラリの追加、このTask MDに書いたもの以外のAPIの変更が必要だと判断した
  - 実施の前後で、`instance/app.db` が変わった
- **止まるときは、報告を書いて、その応答を終える。質問の機能は使わない。** 再開するのは、Komaの新しいメッセージが、判断や再開を明確に示したときだけ（無回答や「続けて」だけの返事は、再開の指示ではない）。`.github/copilot-instructions.md` の「止まる場面の応答」
- **開発用DBを `sqlite3` で開くときは、必ず `-readonly` を付ける**（SELECTだけでも、付けずに開かない。011-L1）。`flask db` のコマンドを、一切実行しない。ライブラリを追加しない。サーバーを起動しない（`python run.py` も、「Komaの確認」の確認用のサーバーも）。「確認用のデータの登録」のスクリプトも、実行しない（Komaが行う）。ブラウザでの確認もしない
- 期待する結果と異なる結果が出た場合は、確認を飛ばさず、原因を直してから、すべての確認をやり直す（ただし、既存のテストの想定外の失敗は、上の停止の条件に従う。全文との「不一致」は、手で直さず、スクリプトで全文に戻す）
- 設計資料に書かれていない仕様は、自分で決めない
- 作業と関係のない操作（自分の過去のセッションの検索など）は、行わない（019-N2）
- **最後の報告には、次を含め、コマンドの出力は、要約せずに、そのまま貼る**（014-L1・019-N1）：変更・新規のファイル、**「Copilot確認手順」の1（実施前）の出力（`echo` の見出しの行と、ブランチ・`git status`・設計資料の `grep -c` の数字・開発用DBのハッシュ・件数・`pytest` の最後の行を含む）**、**「全文からファイルを作るスクリプト」の出力（段階1・2）**、各段階の終わりの `pytest` の出力（`echo` の見出しと最後の行）とテストの件数（2-2）、1行の長さの確認の出力、全文との比較の出力（段階1：5ファイル、段階2：7ファイルの「一致」。スクリプトで全文に戻した場合は、そのこと）、画面のHTMLの確認の出力、検索と差分の出力（`echo` の見出しの行も含めて、そのまま。018-N1）、実施後の開発用DBのハッシュ・件数、`git status`・`git diff --stat` の出力、コマンドを書き換えたかどうか（書き換えていなければ「書き換えなし」）、サーバーの起動とブラウザでの確認をしていないこと、気になった点

## 付録：全文
「全文からファイルを作るスクリプト」と「全文との比較」が使う。各ファイルの全文は、「`<!-- 全文: パス -->`」の印の行の直後のコードブロック。**この付録を、手で書き写さない。** 本文の要点・差分と食い違う場合は、作業をせずに停止して報告する。

### 付録A. `app/api_helpers.py`

<!-- 全文: app/api_helpers.py -->
```
import re
from collections.abc import Collection
from datetime import date, datetime, time
from typing import Any

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import (
    BadRequest,
    HTTPException,
    InternalServerError,
    MethodNotAllowed,
)


# IDの上限（SQLiteのINTEGERの最大値）。これを超える数をDBに渡すとエラーになるため、IDを受け取るURLでは、この値までに制限する
MAX_ID = 2**63 - 1

ERROR_STATUS_CODES = {
    "invalid_json": 400,
    "validation_error": 400,
    "not_found": 404,
    "method_not_allowed": 405,
    "conflict": 409,
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
    def handle_method_not_allowed(error: MethodNotAllowed):
        if not is_api_path(request.path):
            return error
        response, status = api_error_response(
            "method_not_allowed",
            "このURLでは、そのメソッドは使えません",
        )
        # そのURLで使えるメソッドを、Allow ヘッダーで知らせる（405の応答に
        # 付ける決まり）。Werkzeugが渡すメソッドの並びは、決まっていない
        # ため、名前の順に並べる。
        if error.valid_methods:
            response.headers["Allow"] = ", ".join(sorted(error.valid_methods))
        return response, status

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

### 付録B. `app/routes/semesters.py`

<!-- 全文: app/routes/semesters.py -->
```
import re
from datetime import date
from typing import Any

from flask import Blueprint, jsonify

from app.api_helpers import (
    MAX_ID,
    api_error_response,
    format_date,
    read_json_object,
    read_patch_object,
    validate_allowed_fields,
    validate_required_date,
    validate_required_string,
)
from app.class_events import build_class_event, class_event_dates
from app.extensions import db
from app.models.closure import Closure
from app.models.event import Event
from app.models.semester import Semester
from app.models.subject import Subject


semesters_bp = Blueprint(
    "semesters",
    __name__,
    url_prefix="/api/semesters",
)

# 学期の登録（POST）と編集（PATCH）で受け付ける項目。
SEMESTER_FIELDS = {"name", "start_date", "end_date"}

END_DATE_ORDER_MESSAGE = "終了日は開始日より後にしてください"
SEMESTER_HAS_SUBJECTS_MESSAGE = (
    "授業が登録されている学期は削除できません。"
    "先に、授業をすべて削除してください"
)


def semester_to_dict(semester: Semester) -> dict[str, Any]:
    """学期をAPIレスポンス用の辞書に変換する。"""
    return {
        "id": semester.id,
        "name": semester.name,
        "start_date": format_date(semester.start_date),
        "end_date": format_date(semester.end_date),
    }


def is_duplicate_name(name: str, current_id: int | None) -> bool:
    """同じ名前の、ほかの学期があるか（完全一致で比べる）。

    current_id は、編集する学期のID（自分自身は除く）。登録では None。
    """
    statement = db.select(Semester.id).where(Semester.name == name)
    if current_id is not None:
        statement = statement.where(Semester.id != current_id)
    return db.session.scalar(statement) is not None


def validate_semester_values(
    payload: dict[str, Any],
    *,
    partial: bool,
    current_id: int | None,
) -> tuple[dict[str, Any], dict[str, str]]:
    """学期の項目を検査し、（値、エラー）の組を返す。

    登録（POST）と編集（PATCH）で、同じ規則で検査するために使う。
    - partial=False（登録）：すべての項目を検査する。必須の項目が
      本文になければ、必須のエラーにする
    - partial=True（編集）：本文に含まれる項目だけを検査する。含まれない
      項目は、値にもエラーにも入れない（今の値のまま変えない）
    current_id は、同じ名前の検査で除く学期のID（編集する学期。登録では
    None）。値は、誤りのない項目だけを入れる（キーは、Semesterの列の名前と
    同じ）。開始日と終了日の前後の検査は、呼び出し側が行う（編集では、
    今の値と組み合わせて比べるため）。
    """
    values: dict[str, Any] = {}
    errors: dict[str, str] = {}

    if not partial or "name" in payload:
        name, error = validate_required_string(
            payload,
            "name",
            "学期名は必須です",
            "学期名は文字列で指定してください",
            max_length=50,
            length_message="学期名は50文字以内にしてください",
        )
        if error is None and re.fullmatch(
            r"[0-9]{4}年度 (前期|後期)", name
        ) is None:
            # fullmatchにより、前後の改行や余分な文字も含めて形式違反にできる。
            error = "学期名は「2026年度 前期」の形式で指定してください"
        if error is None and is_duplicate_name(name, current_id):
            error = "同じ名前の学期がすでに登録されています"
        if error is None:
            values["name"] = name
        else:
            errors["name"] = error

    if not partial or "start_date" in payload:
        start_date, error = validate_required_date(
            payload,
            "start_date",
            "開始日は必須です",
            "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください",
        )
        if error is None:
            values["start_date"] = start_date
        else:
            errors["start_date"] = error

    if not partial or "end_date" in payload:
        end_date, error = validate_required_date(
            payload,
            "end_date",
            "終了日は必須です",
            "終了日は実在する日付を「YYYY-MM-DD」の形式で指定してください",
        )
        if error is None:
            values["end_date"] = end_date
        else:
            errors["end_date"] = error

    return values, errors


def count_semester_subjects(semester_id: int) -> int:
    """学期の授業の件数を返す。"""
    return db.session.scalar(
        db.select(db.func.count())
        .select_from(Subject)
        .where(Subject.semester_id == semester_id)
    )


def count_semester_closures(semester_id: int) -> int:
    """学期の休講日の件数を返す。"""
    return db.session.scalar(
        db.select(db.func.count())
        .select_from(Closure)
        .where(Closure.semester_id == semester_id)
    )


def sync_period_change(
    semester: Semester,
    previous_start_date: date,
    previous_end_date: date,
) -> None:
    """学期の期間の変更を、授業の予定と休講日に反映する（commitしない）。

    期間の変更は、「どの日が学期か」の訂正のため、休講日の同期と同じく、
    今日より前の日にも適用する。
    - 新しい期間の外になった日の、自動生成の予定（is_generated=True）と、
      休講日を削除する
    - 新しく期間に入った日（前の期間の外の日）に、学期の授業の予定を作る
      （休講日を除く）。自動生成の予定は、学期の期間の中にだけあるため、
      作る日には、同じ授業の自動生成の予定はない
    両方の期間に入る日の予定（個別に変更・削除したものを含む）と、単発の
    予定（is_generated=False）は、変えない。
    """
    start_date = semester.start_date
    end_date = semester.end_date

    # 新しい期間の外になった日の、自動生成の予定と休講日を削除する。
    semester_subject_ids = db.select(Subject.id).where(
        Subject.semester_id == semester.id
    )
    db.session.execute(
        db.delete(Event).where(
            Event.subject_id.in_(semester_subject_ids),
            Event.is_generated.is_(True),
            db.or_(Event.date < start_date, Event.date > end_date),
        )
    )
    db.session.execute(
        db.delete(Closure).where(
            Closure.semester_id == semester.id,
            db.or_(Closure.date < start_date, Closure.date > end_date),
        )
    )

    # 新しく期間に入った日に、学期の授業の予定を作る。
    # 予定を作らない日は、新しい期間の中に残った休講日。
    excluded_dates = set(
        db.session.scalars(
            db.select(Closure.date).where(Closure.semester_id == semester.id)
        )
    )
    subjects = db.session.scalars(
        db.select(Subject)
        .where(Subject.semester_id == semester.id)
        .order_by(Subject.id.asc())
    ).all()
    events = []
    for subject in subjects:
        dates = class_event_dates(
            start_date,
            end_date,
            subject.weekday,
            excluded_dates,
        )
        for event_date in dates:
            # 前の期間の中の日は、予定がすでにある（または、個別に削除
            # した）ため、作らない。
            if previous_start_date <= event_date <= previous_end_date:
                continue
            events.append(build_class_event(subject, event_date))
    # 予定は、明示的に追加する（授業との関係だけでは、セッションに入らない）。
    db.session.add_all(events)


@semesters_bp.get("")
def get_semesters():
    semesters = db.session.scalars(
        db.select(Semester).order_by(
            Semester.start_date.desc(),
            Semester.id.desc(),
        )
    ).all()
    return jsonify([semester_to_dict(semester) for semester in semesters])


@semesters_bp.get(f"/<int(max={MAX_ID}):semester_id>")
def get_semester(semester_id: int):
    semester = db.session.get(Semester, semester_id)
    if semester is None:
        return api_error_response("not_found", "学期が見つかりません")

    response = semester_to_dict(semester)
    # 1件取得のレスポンスにだけ付ける付加情報（DBには保存しない）。
    # 学期の削除の確認に使う（授業があれば削除できない。休講日は、
    # 学期と一緒に削除される）。
    response["subject_count"] = count_semester_subjects(semester.id)
    response["closure_count"] = count_semester_closures(semester.id)
    return jsonify(response)


@semesters_bp.post("")
def create_semester():
    payload, error_response = read_json_object()
    if error_response is not None:
        return error_response

    values, fields = validate_semester_values(
        payload,
        partial=False,
        current_id=None,
    )

    start_date = values.get("start_date")
    end_date = values.get("end_date")
    # 前後の検査は、開始日と終了日の両方に誤りがないときだけ行う。
    if (
        start_date is not None
        and end_date is not None
        and end_date <= start_date
    ):
        fields["end_date"] = END_DATE_ORDER_MESSAGE

    fields.update(validate_allowed_fields(payload, SEMESTER_FIELDS))

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    semester = Semester(
        name=values["name"],
        start_date=start_date,
        end_date=end_date,
    )
    db.session.add(semester)
    db.session.commit()
    return jsonify(semester_to_dict(semester)), 201


@semesters_bp.patch(f"/<int(max={MAX_ID}):semester_id>")
def update_semester(semester_id: int):
    # 対象の学期がなければ、本文を読む前に404にする。
    semester = db.session.get(Semester, semester_id)
    if semester is None:
        return api_error_response("not_found", "学期が見つかりません")

    # 項目が1つもない本文（{}）も、誤りにする（API共通ルール）。
    payload, error_response = read_patch_object()
    if error_response is not None:
        return error_response

    values, fields = validate_semester_values(
        payload,
        partial=True,
        current_id=semester.id,
    )

    # 前後の検査は、変更後の値どうしで行う。本文に含まれない日付は、
    # 今の値を使う。本文の日付に誤りがあれば、検査しない。
    if "start_date" not in fields and "end_date" not in fields:
        start_date = values.get("start_date", semester.start_date)
        end_date = values.get("end_date", semester.end_date)
        if end_date <= start_date:
            fields["end_date"] = END_DATE_ORDER_MESSAGE

    fields.update(validate_allowed_fields(payload, SEMESTER_FIELDS))

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    previous_start_date = semester.start_date
    previous_end_date = semester.end_date
    # 本文に含まれていた項目だけを、学期に書き込む
    # （values のキーは、Semesterの列の名前と同じ）。
    for field_name, value in values.items():
        setattr(semester, field_name, value)

    # 期間が変わったときだけ、授業の予定と休講日に反映する（名前だけの
    # 変更では、予定も休講日も変えない）。
    if (semester.start_date, semester.end_date) != (
        previous_start_date,
        previous_end_date,
    ):
        sync_period_change(semester, previous_start_date, previous_end_date)
    # 学期の更新と、予定・休講日の削除・作成を、1回のcommitで保存する。
    db.session.commit()
    return jsonify(semester_to_dict(semester))


@semesters_bp.delete(f"/<int(max={MAX_ID}):semester_id>")
def delete_semester(semester_id: int):
    semester = db.session.get(Semester, semester_id)
    if semester is None:
        return api_error_response("not_found", "学期が見つかりません")

    # 授業がある学期は、削除できない（授業の予定・課題を、まとめて消さない
    # ため。先に、授業を1件ずつ削除してもらう）。
    if count_semester_subjects(semester.id) > 0:
        return api_error_response("conflict", SEMESTER_HAS_SUBJECTS_MESSAGE)

    # 学期の休講日を、学期より先に、明示的に削除する（「データ設計」の
    # 「共通の約束」）。学期だけを削除すると、休講日が、semester_id が
    # NULL の行として残る。
    db.session.execute(
        db.delete(Closure).where(Closure.semester_id == semester.id)
    )
    db.session.delete(semester)
    # 休講日と学期の削除を、1回のcommitで保存する。
    db.session.commit()
    return "", 204
```

### 付録C. `app/class_events.py`

<!-- 全文: app/class_events.py -->
```
"""授業の予定（Event）の生成。

授業の登録、休講日の削除による予定の作成、授業全体の編集による
予定の作り直し、学期の期間の変更による予定の作成から使う部品。
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

### 付録D. `tests/test_semesters_api.py`

<!-- 全文: tests/test_semesters_api.py -->
```
from datetime import date

import pytest

from app.api_helpers import (
    INVALID_JSON_MESSAGE,
    MAX_ID,
    UNUSABLE_CHARACTER_MESSAGE,
)
from app.extensions import db
from app.models.semester import Semester


def create_semester(client, name, start_date, end_date):
    return client.post(
        "/api/semesters",
        json={
            "name": name,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


def assert_api_error(response, status, code, message, fields=None):
    assert response.status_code == status
    assert response.is_json
    assert response.json == {
        "error": {
            "code": code,
            "message": message,
            **({"fields": fields} if fields is not None else {}),
        }
    }


def test_empty_semester_list_is_json(client):
    response = client.get("/api/semesters")
    assert response.status_code == 200
    assert response.is_json
    assert response.json == []


def test_semester_creation_get_and_ordering(client):
    created = [
        create_semester(
            client,
            "2099年度 前期",
            "2099-04-06",
            "2099-07-20",
        ),
        create_semester(
            client,
            "2099年度 後期",
            "2099-09-21",
            "2099-12-27",
        ),
        create_semester(
            client,
            "2100年度 前期",
            "2099-12-01",
            "2100-03-31",
        ),
        create_semester(
            client,
            "2100年度 後期",
            "2099-12-01",
            "2100-03-31",
        ),
    ]

    expected_keys = {"id", "name", "start_date", "end_date"}
    created_objects = []
    for response, expected_name in zip(
        created,
        (
            "2099年度 前期",
            "2099年度 後期",
            "2100年度 前期",
            "2100年度 後期",
        ),
    ):
        assert response.status_code == 201
        assert set(response.json) == expected_keys
        assert isinstance(response.json["id"], int)
        assert response.json["name"] == expected_name
        created_objects.append(response.json)

    listing = client.get("/api/semesters")
    assert listing.status_code == 200
    assert [item["name"] for item in listing.json] == [
        "2100年度 後期",
        "2100年度 前期",
        "2099年度 後期",
        "2099年度 前期",
    ]
    # 1件取得には、付加情報（授業と休講日の件数）が付く。
    assert client.get(
        f"/api/semesters/{created_objects[0]['id']}"
    ).json == {**created_objects[0], "subject_count": 0, "closure_count": 0}


@pytest.mark.parametrize(
    ("payload", "expected_fields"),
    [
        (
            {
                "name": "2026年度 前期",
                "start_date": "2026-04-01",
                "end_date": "2026-07-31",
            },
            {"name": "同じ名前の学期がすでに登録されています"},
        ),
        ({"name": "前期"}, {"name": "学期名は「2026年度 前期」の形式で指定してください"}),
        ({"name": "２０２６年度 前期"}, {"name": "学期名は「2026年度 前期」の形式で指定してください"}),
        ({"name": "2026年度 前期\n"}, {"name": "学期名は「2026年度 前期」の形式で指定してください"}),
        ({"name": " 2026年度 前期"}, {"name": "学期名は「2026年度 前期」の形式で指定してください"}),
        ({"name": "あ" * 51}, {"name": "学期名は50文字以内にしてください"}),
        (
            {},
            {
                "name": "学期名は必須です",
                "start_date": "開始日は必須です",
                "end_date": "終了日は必須です",
            },
        ),
        (
            {"name": 123, "start_date": 20260401, "end_date": None},
            {
                "name": "学期名は文字列で指定してください",
                "start_date": (
                    "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
                ),
                "end_date": "終了日は必須です",
            },
        ),
        (
            {
                "name": "2026年度 前期",
                "start_date": "20260401",
                "end_date": "2026-07-31",
            },
            {
                "start_date": (
                    "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
                )
            },
        ),
        (
            {
                "name": "2026年度 前期",
                "start_date": "2026/04/01",
                "end_date": "2026-07-31",
            },
            {
                "start_date": (
                    "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
                )
            },
        ),
        (
            {
                "name": "2026年度 前期",
                "start_date": "2026-4-1",
                "end_date": "2026-07-31",
            },
            {
                "start_date": (
                    "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
                )
            },
        ),
        (
            {
                "name": "2026年度 前期",
                "start_date": "2026-02-30",
                "end_date": "2026-07-31",
            },
            {
                "start_date": (
                    "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
                )
            },
        ),
        (
            {
                "name": "2026年度 前期",
                "start_date": "2026-04-01\n",
                "end_date": "2026-07-31",
            },
            {
                "start_date": (
                    "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください"
                )
            },
        ),
        (
            {
                "name": "2026年度 前期",
                "start_date": "2026-04-01",
                "end_date": "2026-04-01",
            },
            {"end_date": "終了日は開始日より後にしてください"},
        ),
        (
            {
                "name": "2026年度 前期",
                "start_date": "2026-04-01",
                "end_date": "2026-03-31",
            },
            {"end_date": "終了日は開始日より後にしてください"},
        ),
        (
            {
                "name": "2026年度 前期",
                "start_date": "2026-04-01",
                "end_date": "2026-07-31",
                "color": "red",
            },
            {"color": "この項目は指定できません"},
        ),
        (
            {
                "id": 5,
                "name": "2026年度 前期",
                "start_date": "2026-04-01",
                "end_date": "2026-07-31",
            },
            {"id": "この項目は指定できません"},
        ),
    ],
)
def test_invalid_semester_payloads_have_expected_fields(
    client, app, payload, expected_fields
):
    request_payload = payload
    if payload and set(payload) != {
        "name",
        "start_date",
        "end_date",
    }:
        request_payload = {
            "name": "2026年度 前期",
            "start_date": "2026-04-01",
            "end_date": "2026-07-31",
            **payload,
        }

    if expected_fields == {"name": "同じ名前の学期がすでに登録されています"}:
        with app.app_context():
            db.session.add(
                Semester(
                    name="2026年度 前期",
                    start_date=date(2026, 4, 1),
                    end_date=date(2026, 7, 31),
                )
            )
            db.session.commit()

    before_count = semester_count(app)
    response = client.post("/api/semesters", json=request_payload)
    assert_api_error(
        response,
        400,
        "validation_error",
        "入力内容に誤りがあります",
        expected_fields,
    )
    assert semester_count(app) == before_count


def semester_count(app):
    with app.app_context():
        return db.session.query(Semester).count()


@pytest.mark.parametrize("payload", [[], None, "abc", 123, True])
def test_non_object_semester_payload_has_no_fields(client, payload):
    if payload is None:
        response = client.post(
            "/api/semesters",
            data="null",
            content_type="application/json",
        )
    else:
        response = client.post("/api/semesters", json=payload)
    assert_api_error(
        response,
        400,
        "validation_error",
        "リクエストの本文は、JSONのオブジェクトにしてください",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "2026年度 前期\ud800"),
        ("name", "\ud800"),
        ("start_date", "2026-04-01\ud800"),
        ("end_date", "\udfff"),
    ],
)
def test_unusable_characters_in_semester_fields_are_rejected(
    client, app, field, value
):
    payload = {
        "name": "2026年度 前期",
        "start_date": "2026-04-01",
        "end_date": "2026-07-31",
    }
    payload[field] = value

    response = client.post("/api/semesters", json=payload)
    assert_api_error(
        response,
        400,
        "validation_error",
        "入力内容に誤りがあります",
        {field: UNUSABLE_CHARACTER_MESSAGE},
    )
    assert semester_count(app) == 0


def test_invalid_utf8_semester_body_is_invalid_json(client, app):
    before_count = semester_count(app)
    response = client.post(
        "/api/semesters",
        data=(
            b'{"name": "\xff", "start_date": "2026-04-01", '
            b'"end_date": "2026-07-31"}'
        ),
        content_type="application/json",
    )
    assert_api_error(
        response,
        400,
        "invalid_json",
        INVALID_JSON_MESSAGE,
    )
    assert semester_count(app) == before_count


def test_surrogate_pair_in_semester_name_is_format_error(client, app):
    before_count = semester_count(app)
    response = create_semester(
        client,
        "2026年度 前期😀",
        "2026-04-01",
        "2026-07-31",
    )
    assert_api_error(
        response,
        400,
        "validation_error",
        "入力内容に誤りがあります",
        {"name": "学期名は「2026年度 前期」の形式で指定してください"},
    )
    assert semester_count(app) == before_count


@pytest.mark.parametrize(
    ("data", "content_type"),
    [
        ('{"name":', "application/json"),
        ('{"name":"x"}', "text/plain"),
        ('{"name":"x"}', None),
    ],
)
def test_invalid_json_content(client, data, content_type):
    response = client.post(
        "/api/semesters",
        data=data,
        content_type=content_type,
    )
    assert_api_error(
        response,
        400,
        "invalid_json",
        (
            "リクエストの本文がJSONとして読めません。"
            "Content-Typeを application/json にして、JSONで送ってください"
        ),
    )


def test_json_content_type_with_charset_is_accepted(client):
    response = client.post(
        "/api/semesters",
        data=(
            '{"name":"2026年度 前期","start_date":"2026-04-01",'
            '"end_date":"2026-07-31"}'
        ),
        content_type="application/json; charset=utf-8",
    )
    assert response.status_code == 201


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/semesters/99999", "学期が見つかりません"),
        ("/api/semesters/0", "学期が見つかりません"),
        (f"/api/semesters/{MAX_ID}", "学期が見つかりません"),
        (f"/api/semesters/{MAX_ID + 1}", "URLが見つかりません"),
        ("/api/semesters/99999999999999999999", "URLが見つかりません"),
        ("/api/semesters/abc", "URLが見つかりません"),
        ("/api/semesters/-1", "URLが見つかりません"),
        ("/api/semesters/", "URLが見つかりません"),
        ("/api/unknown", "URLが見つかりません"),
        ("/api", "URLが見つかりません"),
    ],
)
def test_semester_and_url_not_found_responses(client, url, message):
    assert_api_error(
        client.get(url),
        404,
        "not_found",
        message,
    )


@pytest.mark.parametrize(
    ("method", "url", "allow"),
    [
        ("put", "/api/semesters", "GET, HEAD, OPTIONS, POST"),
        ("patch", "/api/semesters", "GET, HEAD, OPTIONS, POST"),
        ("delete", "/api/semesters", "GET, HEAD, OPTIONS, POST"),
        ("put", "/api/semesters/1", "DELETE, GET, HEAD, OPTIONS, PATCH"),
        ("post", "/api/semesters/1", "DELETE, GET, HEAD, OPTIONS, PATCH"),
    ],
)
def test_unsupported_semester_methods_return_json_405(
    client, method, url, allow
):
    response = getattr(client, method)(url)
    assert_api_error(
        response,
        405,
        "method_not_allowed",
        "このURLでは、そのメソッドは使えません",
    )
    assert response.headers["Allow"] == allow


@pytest.mark.parametrize(
    ("method", "url", "allow"),
    [
        ("put", "/api/subjects", "GET, HEAD, OPTIONS, POST"),
        ("post", "/api/subjects/1", "DELETE, GET, HEAD, OPTIONS, PATCH"),
        ("get", "/api/closures/1", "DELETE, OPTIONS"),
        ("patch", "/api/closures/1", "DELETE, OPTIONS"),
        ("put", "/api/events", "GET, HEAD, OPTIONS, POST"),
        ("put", "/api/events/1", "DELETE, GET, HEAD, OPTIONS, PATCH"),
        ("post", "/api/events/employers", "GET, HEAD, OPTIONS"),
        ("put", "/api/tasks", "GET, HEAD, OPTIONS, POST"),
        ("put", "/api/tasks/1", "DELETE, GET, HEAD, OPTIONS, PATCH"),
    ],
)
def test_api_405_has_allow_header_in_name_order(client, method, url, allow):
    # API共通ルール：405の応答には、そのURLで使えるメソッドを、名前の順に
    # 並べた Allow ヘッダーを付ける（すべてのリソースで同じ）。
    response = getattr(client, method)(url)
    assert response.status_code == 405
    assert response.json["error"]["code"] == "method_not_allowed"
    assert response.headers["Allow"] == allow


def test_regular_page_405_remains_html(client):
    # 通常のHTMLページの405は、変えない（Flaskの標準のHTMLのまま）。
    response = client.post("/")
    assert response.status_code == 405
    assert response.content_type.startswith("text/html")
    assert set(response.headers["Allow"].split(", ")) == {
        "GET",
        "HEAD",
        "OPTIONS",
    }


def test_regular_page_errors_remain_html_and_cors_is_disabled(client):
    assert client.get("/").content_type.startswith("text/html")
    assert client.get("/missing-page").content_type.startswith("text/html")
    assert client.post("/").content_type.startswith("text/html")

    response = client.get(
        "/api/semesters",
        headers={"Origin": "http://example.com"},
    )
    preflight = client.options(
        "/api/semesters",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    for result in (response, preflight):
        assert not any(
            name.lower().startswith("access-control-")
            for name, _ in result.headers
        )


def test_api_internal_error_is_json_and_regular_error_is_html(client, app):
    def fail():
        raise RuntimeError("intentional test failure")

    app.config["PROPAGATE_EXCEPTIONS"] = False
    app.add_url_rule("/api/test-error", "api_test_error", fail)
    app.add_url_rule("/test-error", "test_error", fail)

    assert_api_error(
        client.get("/api/test-error"),
        500,
        "server_error",
        "サーバーでエラーが発生しました",
    )
    assert client.get("/test-error").content_type.startswith("text/html")
```

### 付録E. `tests/test_semesters_update_delete_api.py`

<!-- 全文: tests/test_semesters_update_delete_api.py -->
```
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
```

### 付録F. `app/templates/index.html`

<!-- 全文: app/templates/index.html -->
```
{% extends "base.html" %}

{% block content %}
<main class="container mb-5 pb-3">
  <div class="tab-content">
    <section class="tab-pane fade show active" id="calendar-pane" role="tabpanel" aria-labelledby="calendar-tab" tabindex="0">
      <div id="calendar-load-error" class="alert alert-danger d-none" role="alert">
        <p id="calendar-load-error-message" class="mb-2"></p>
        <button type="button" id="calendar-retry-button" class="btn btn-outline-danger btn-sm">再読み込み</button>
      </div>

      <div id="calendar-content">
        <div class="d-flex flex-wrap align-items-center gap-3 mb-2">
          <span id="calendar-filter-label" class="text-muted small">表示するカテゴリ</span>
          <div id="calendar-filter" class="d-flex flex-wrap gap-3" role="group" aria-labelledby="calendar-filter-label"></div>
          <span id="calendar-loading" class="text-muted small d-none">読み込み中…</span>
        </div>
        <div id="event-added-notice" class="alert alert-success d-flex flex-wrap align-items-center gap-2 py-2 d-none" role="status">
          <span id="event-added-notice-message" class="me-auto text-break"></span>
          <button type="button" id="event-repeat-button" class="btn btn-success btn-sm">同じ内容で別の日も登録</button>
          <button type="button" id="event-added-notice-close-button" class="btn-close" aria-label="閉じる"></button>
        </div>
        <div class="row g-3">
          <div class="col-lg-9">
            <div id="calendar-view"></div>
          </div>
          <div class="col-lg-3">
            <section id="calendar-deadline-panel" class="card" aria-labelledby="calendar-deadline-heading">
              <div class="card-body p-2">
                <h2 id="calendar-deadline-heading" class="h6 mb-1">直近の締切</h2>
                <p class="text-muted small mb-2">期限切れと、今日から7日後までの、未完了の課題・タスク</p>
                <div id="calendar-deadline-loading" class="text-muted small">読み込み中…</div>
                <div id="calendar-deadline-load-error" class="alert alert-danger d-none mb-0" role="alert">
                  <p id="calendar-deadline-load-error-message" class="mb-2"></p>
                  <button type="button" id="calendar-deadline-retry-button" class="btn btn-outline-danger btn-sm">再読み込み</button>
                </div>
                <div id="calendar-deadline-content" class="d-none">
                  <div id="calendar-deadline-action-error" class="alert alert-danger d-none mb-2" role="alert"></div>
                  <p id="calendar-deadline-empty" class="text-muted small mb-0 d-none">直近の締切はありません</p>
                  <ul id="calendar-deadline-list" class="list-unstyled mb-0 d-none"></ul>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </section>
    <section class="tab-pane fade" id="subjects-pane" role="tabpanel" aria-labelledby="subjects-tab" tabindex="0">
      <div id="semester-loading" class="text-muted">読み込み中…</div>

      <div id="semester-load-error" class="alert alert-danger d-none" role="alert">
        <p id="semester-load-error-message" class="mb-2"></p>
        <button type="button" id="semester-retry-button" class="btn btn-outline-danger btn-sm">再読み込み</button>
      </div>

      <div id="semester-empty" class="text-center py-5 d-none">
        <p>学期がまだ登録されていません。最初の学期を登録してください</p>
        <button type="button" id="semester-empty-open-button" class="btn btn-primary"
                data-bs-toggle="modal" data-bs-target="#semester-modal">最初の学期を登録する</button>
      </div>

      <div id="semester-content" class="d-none">
        <div id="semester-banner" class="alert alert-info d-flex justify-content-between align-items-center d-none" role="alert">
          <span>新しい学期を登録しますか</span>
          <button type="button" id="semester-banner-open-button" class="btn btn-primary btn-sm"
                  data-bs-toggle="modal" data-bs-target="#semester-modal">登録する</button>
        </div>
        <div class="d-flex align-items-end gap-2 mb-3">
          <ul id="semester-tabs" class="nav nav-tabs flex-nowrap overflow-x-auto flex-grow-1" role="tablist"></ul>
          <button type="button" id="semester-open-button" class="btn btn-outline-primary btn-sm text-nowrap"
                  data-bs-toggle="modal" data-bs-target="#semester-modal">新しい学期を登録する</button>
        </div>
        <div id="semester-detail" role="tabpanel">
          <div class="d-flex align-items-center gap-2 mb-2">
            <h2 id="semester-detail-name" class="h5 mb-0"></h2>
            <button type="button" id="semester-edit-button" class="btn btn-outline-secondary btn-sm"
                    data-bs-toggle="modal" data-bs-target="#semester-edit-modal">編集</button>
            <button type="button" id="semester-delete-button" class="btn btn-outline-danger btn-sm"
                    data-bs-toggle="modal" data-bs-target="#semester-delete-modal">削除</button>
          </div>
          <p id="semester-detail-period" class="text-muted"></p>
          <div id="closure-section" class="mt-4">
            <h3 class="h6 mb-2">休講日</h3>
            <div id="closure-semester-error" class="text-danger small mb-2"></div>
            <div id="closure-form-error" class="alert alert-danger d-none" role="alert"></div>
            <div id="closure-loading" class="text-muted mb-3 d-none">読み込み中…</div>
            <div id="closure-load-error" class="alert alert-danger d-none" role="alert">
              <p id="closure-load-error-message" class="mb-2"></p>
              <button type="button" id="closure-retry-button" class="btn btn-outline-danger btn-sm">再読み込み</button>
            </div>
            <p id="closure-empty" class="text-muted d-none">休講日は登録されていません</p>
            <ul id="closure-list" class="list-group mb-3 d-none"></ul>
            <form id="closure-form">
              <div class="row g-2">
                <div class="col-md-4">
                  <label for="closure-date" class="form-label">日付</label>
                  <input type="date" id="closure-date" class="form-control" required>
                  <div id="closure-date-error" class="text-danger small mt-1"></div>
                </div>
                <div class="col-md-8">
                  <label for="closure-name" class="form-label">名前（任意）</label>
                  <input type="text" id="closure-name" class="form-control" placeholder="例：開学記念日">
                  <div id="closure-name-error" class="text-danger small mt-1"></div>
                </div>
              </div>
              <button type="submit" id="closure-submit-button" class="btn btn-primary btn-sm mt-2">追加する</button>
            </form>
          </div>
          <div id="subject-section" class="mt-4">
            <div class="d-flex justify-content-between align-items-center mb-2">
              <h3 class="h6 mb-0">授業</h3>
              <button type="button" id="subject-add-button" class="btn btn-primary btn-sm"
                      data-bs-toggle="modal" data-bs-target="#subject-modal">授業を追加</button>
            </div>
            <div id="subject-loading" class="text-muted d-none">読み込み中…</div>
            <div id="subject-load-error" class="alert alert-danger d-none" role="alert">
              <p id="subject-load-error-message" class="mb-2"></p>
              <button type="button" id="subject-retry-button" class="btn btn-outline-danger btn-sm">再読み込み</button>
            </div>
            <p id="subject-empty" class="text-muted d-none">この学期には、まだ授業が登録されていません</p>
            <div id="subject-list" class="table-responsive d-none">
              <table class="table table-sm align-middle">
                <thead>
                  <tr>
                    <th scope="col">曜日</th>
                    <th scope="col">時間</th>
                    <th scope="col">科目名</th>
                    <th scope="col">教室</th>
                    <th scope="col" class="text-end">操作</th>
                  </tr>
                </thead>
                <tbody id="subject-table-body"></tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </section>
    <section class="tab-pane fade" id="tasks-pane" role="tabpanel" aria-labelledby="tasks-tab" tabindex="0">
      <div id="task-loading" class="text-muted d-none">読み込み中…</div>
      <div id="task-load-error" class="alert alert-danger d-none" role="alert">
        <p id="task-load-error-message" class="mb-2"></p>
        <button type="button" id="task-retry-button" class="btn btn-outline-danger btn-sm">再読み込み</button>
      </div>
      <div id="task-content" class="d-none">
        <div id="task-action-error" class="alert alert-danger d-none" role="alert"></div>
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h2 class="h6 mb-0">未完了</h2>
          <button type="button" id="task-add-button" class="btn btn-primary btn-sm"
                  data-bs-toggle="modal" data-bs-target="#task-modal">課題を追加</button>
        </div>
        <p id="task-incomplete-empty" class="text-muted d-none">未完了の課題・タスクはありません</p>
        <div id="task-incomplete-list" class="table-responsive d-none">
          <table class="table table-sm align-middle task-table">
            <thead>
              <tr>
                <th scope="col" class="task-col-completed">完了</th>
                <th scope="col" class="task-col-due">締切</th>
                <th scope="col">課題名</th>
                <th scope="col" class="task-col-subject">対象授業</th>
                <th scope="col" class="task-col-actions text-end">操作</th>
              </tr>
            </thead>
            <tbody id="task-incomplete-body"></tbody>
          </table>
        </div>
        <h2 class="h6 mt-4 mb-2">完了</h2>
        <p id="task-completed-empty" class="text-muted d-none">完了した課題・タスクはありません</p>
        <div id="task-completed-list" class="table-responsive d-none">
          <table class="table table-sm align-middle task-table">
            <thead>
              <tr>
                <th scope="col" class="task-col-completed">完了</th>
                <th scope="col" class="task-col-due">締切</th>
                <th scope="col">課題名</th>
                <th scope="col" class="task-col-subject">対象授業</th>
                <th scope="col" class="task-col-actions text-end">操作</th>
              </tr>
            </thead>
            <tbody id="task-completed-body"></tbody>
          </table>
        </div>
      </div>
    </section>
  </div>
</main>

<nav class="nav nav-pills nav-fill fixed-bottom bg-light p-2" role="tablist" aria-label="表示モード">
  <button class="nav-link active" id="calendar-tab" data-bs-toggle="pill" data-bs-target="#calendar-pane" type="button" role="tab" aria-controls="calendar-pane" aria-selected="true">カレンダー</button>
  <button class="nav-link" id="subjects-tab" data-bs-toggle="pill" data-bs-target="#subjects-pane" type="button" role="tab" aria-controls="subjects-pane" aria-selected="false">授業</button>
  <button class="nav-link" id="tasks-tab" data-bs-toggle="pill" data-bs-target="#tasks-pane" type="button" role="tab" aria-controls="tasks-pane" aria-selected="false">課題・タスク</button>
</nav>

<div class="modal fade" id="semester-modal" tabindex="-1" aria-labelledby="semester-modal-title" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <form id="semester-form">
        <div class="modal-header">
          <h2 class="modal-title h5" id="semester-modal-title">新しい学期を登録する</h2>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="閉じる"></button>
        </div>
        <div class="modal-body">
          <div id="semester-form-error" class="alert alert-danger d-none" role="alert"></div>
          <div class="mb-3">
            <div class="row g-2">
              <div class="col-6">
                <label for="semester-year" class="form-label">年度</label>
                <input type="number" id="semester-year" class="form-control" required>
              </div>
              <div class="col-6">
                <label for="semester-term" class="form-label">種別</label>
                <select id="semester-term" class="form-select" required>
                  <option value="前期">前期</option>
                  <option value="後期">後期</option>
                </select>
              </div>
            </div>
            <div id="semester-name-error" class="text-danger small mt-1"></div>
          </div>
          <div class="mb-3">
            <label for="semester-start-date" class="form-label">開始日</label>
            <input type="date" id="semester-start-date" class="form-control" required>
            <div id="semester-start-date-error" class="text-danger small mt-1"></div>
          </div>
          <div class="mb-3">
            <label for="semester-end-date" class="form-label">終了日</label>
            <input type="date" id="semester-end-date" class="form-control" required>
            <div id="semester-end-date-error" class="text-danger small mt-1"></div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
          <button type="submit" id="semester-submit-button" class="btn btn-primary">登録する</button>
        </div>
      </form>
    </div>
  </div>
</div>

<div class="modal fade" id="semester-edit-modal" tabindex="-1" aria-labelledby="semester-edit-modal-title" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <form id="semester-edit-form">
        <div class="modal-header">
          <h2 class="modal-title h5" id="semester-edit-modal-title">学期を編集</h2>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="閉じる"></button>
        </div>
        <div class="modal-body">
          <div id="semester-edit-form-error" class="alert alert-danger d-none" role="alert"></div>
          <div class="mb-3">
            <div class="row g-2">
              <div class="col-6">
                <label for="semester-edit-year" class="form-label">年度</label>
                <input type="number" id="semester-edit-year" class="form-control" required>
              </div>
              <div class="col-6">
                <label for="semester-edit-term" class="form-label">種別</label>
                <select id="semester-edit-term" class="form-select" required>
                  <option value="前期">前期</option>
                  <option value="後期">後期</option>
                </select>
              </div>
            </div>
            <div id="semester-edit-name-error" class="text-danger small mt-1"></div>
          </div>
          <div class="mb-3">
            <label for="semester-edit-start-date" class="form-label">開始日</label>
            <input type="date" id="semester-edit-start-date" class="form-control" required>
            <div id="semester-edit-start-date-error" class="text-danger small mt-1"></div>
          </div>
          <div class="mb-3">
            <label for="semester-edit-end-date" class="form-label">終了日</label>
            <input type="date" id="semester-edit-end-date" class="form-control" required>
            <div id="semester-edit-end-date-error" class="text-danger small mt-1"></div>
          </div>
          <div id="semester-edit-notice" class="alert alert-warning small mb-0">
            期間を変えると、新しい期間から外れる日の、授業の予定（授業の登録で作られたもの。カレンダーで個別に変更したものを含む）と休講日は、削除されます。新しく期間に入る日には、授業の予定が作られます。両方の期間に入る日の予定と、カレンダーから追加した単発の予定（補講など）、課題は、変わりません。
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
          <button type="submit" id="semester-edit-submit-button" class="btn btn-primary" aria-describedby="semester-edit-notice">保存する</button>
        </div>
      </form>
    </div>
  </div>
</div>

<div class="modal fade" id="semester-delete-modal" tabindex="-1" aria-labelledby="semester-delete-modal-title" aria-describedby="semester-delete-target semester-delete-counts semester-delete-warning" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title h5" id="semester-delete-modal-title">学期を削除</h2>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="閉じる"></button>
      </div>
      <div class="modal-body">
        <p id="semester-delete-target" class="mb-2"></p>
        <p id="semester-delete-loading" class="text-muted mb-2">授業と休講日の件数を確認しています…</p>
        <p id="semester-delete-counts" class="mb-2 d-none"></p>
        <div id="semester-delete-error" class="alert alert-danger d-none" role="alert"></div>
        <p id="semester-delete-warning" class="text-danger mb-0">削除は取り消せません。</p>
      </div>
      <div class="modal-footer">
        <button type="button" id="semester-delete-cancel-button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
        <button type="button" id="semester-delete-submit-button" class="btn btn-danger" aria-describedby="semester-delete-target semester-delete-counts semester-delete-warning" disabled>削除する</button>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="subject-modal" tabindex="-1" aria-labelledby="subject-modal-title" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <form id="subject-form">
        <div class="modal-header">
          <h2 class="modal-title h5" id="subject-modal-title">授業を追加</h2>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="閉じる"></button>
        </div>
        <div class="modal-body">
          <p class="mb-1">登録先の学期：<strong id="subject-modal-semester"></strong></p>
          <div id="subject-semester-error" class="text-danger small mb-2"></div>
          <div id="subject-form-success" class="alert alert-success d-none" role="status"></div>
          <div id="subject-form-error" class="alert alert-danger d-none" role="alert"></div>
          <div class="mb-3">
            <label for="subject-name" class="form-label">科目名</label>
            <input type="text" id="subject-name" class="form-control" required>
            <div id="subject-name-error" class="text-danger small mt-1"></div>
          </div>
          <div class="mb-3">
            <label for="subject-room" class="form-label">教室（任意）</label>
            <input type="text" id="subject-room" class="form-control">
            <div id="subject-room-error" class="text-danger small mt-1"></div>
          </div>
          <div class="mb-3">
            <label for="subject-weekday" class="form-label">曜日</label>
            <select id="subject-weekday" class="form-select" required>
              <option value="0">月曜日</option>
              <option value="1">火曜日</option>
              <option value="2">水曜日</option>
              <option value="3">木曜日</option>
              <option value="4">金曜日</option>
              <option value="5">土曜日</option>
              <option value="6">日曜日</option>
            </select>
            <div id="subject-weekday-error" class="text-danger small mt-1"></div>
          </div>
          <div class="row g-2 mb-3">
            <div class="col-6">
              <label for="subject-start-time" class="form-label">開始時刻</label>
              <select id="subject-start-time" class="form-select" required>
                <option value="09:00">09:00</option>
                <option value="10:00">10:00</option>
                <option value="11:00">11:00</option>
                <option value="12:00">12:00</option>
                <option value="13:00">13:00</option>
                <option value="14:00">14:00</option>
                <option value="15:00">15:00</option>
                <option value="16:00">16:00</option>
                <option value="17:00">17:00</option>
                <option value="18:00">18:00</option>
              </select>
              <div id="subject-start-time-error" class="text-danger small mt-1"></div>
            </div>
            <div class="col-6">
              <label for="subject-end-time" class="form-label">終了時刻</label>
              <select id="subject-end-time" class="form-select" required>
                <option value="10:00">10:00</option>
                <option value="11:00">11:00</option>
                <option value="12:00">12:00</option>
                <option value="13:00">13:00</option>
                <option value="14:00">14:00</option>
                <option value="15:00">15:00</option>
                <option value="16:00">16:00</option>
                <option value="17:00">17:00</option>
                <option value="18:00">18:00</option>
                <option value="19:00">19:00</option>
              </select>
              <div id="subject-end-time-error" class="text-danger small mt-1"></div>
            </div>
          </div>
          <div class="mb-3">
            <label for="subject-notes" class="form-label">詳細・メモ（任意）</label>
            <textarea id="subject-notes" class="form-control" rows="3"></textarea>
            <div id="subject-notes-error" class="text-danger small mt-1"></div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">閉じる</button>
          <button type="submit" id="subject-submit-button" class="btn btn-primary">登録する</button>
        </div>
      </form>
    </div>
  </div>
</div>

<div class="modal fade" id="subject-edit-modal" tabindex="-1" aria-labelledby="subject-edit-modal-title" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <form id="subject-edit-form">
        <div class="modal-header">
          <h2 class="modal-title h5" id="subject-edit-modal-title">授業を編集</h2>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="閉じる"></button>
        </div>
        <div class="modal-body">
          <p class="mb-1">学期：<strong id="subject-edit-modal-semester"></strong></p>
          <p class="text-muted small mb-3">学期は変更できません。誤った場合は、授業を削除して、正しい学期に登録し直してください。</p>
          <div id="subject-edit-form-error" class="alert alert-danger d-none" role="alert"></div>
          <div class="mb-3">
            <label for="subject-edit-name" class="form-label">科目名</label>
            <input type="text" id="subject-edit-name" class="form-control" required>
            <div id="subject-edit-name-error" class="text-danger small mt-1"></div>
          </div>
          <div class="mb-3">
            <label for="subject-edit-room" class="form-label">教室（任意）</label>
            <input type="text" id="subject-edit-room" class="form-control">
            <div id="subject-edit-room-error" class="text-danger small mt-1"></div>
          </div>
          <div class="mb-3">
            <label for="subject-edit-weekday" class="form-label">曜日</label>
            <select id="subject-edit-weekday" class="form-select" required>
              <option value="0">月曜日</option>
              <option value="1">火曜日</option>
              <option value="2">水曜日</option>
              <option value="3">木曜日</option>
              <option value="4">金曜日</option>
              <option value="5">土曜日</option>
              <option value="6">日曜日</option>
            </select>
            <div id="subject-edit-weekday-error" class="text-danger small mt-1"></div>
          </div>
          <div class="row g-2 mb-3">
            <div class="col-6">
              <label for="subject-edit-start-time" class="form-label">開始時刻</label>
              <select id="subject-edit-start-time" class="form-select" required>
                <option value="09:00">09:00</option>
                <option value="10:00">10:00</option>
                <option value="11:00">11:00</option>
                <option value="12:00">12:00</option>
                <option value="13:00">13:00</option>
                <option value="14:00">14:00</option>
                <option value="15:00">15:00</option>
                <option value="16:00">16:00</option>
                <option value="17:00">17:00</option>
                <option value="18:00">18:00</option>
              </select>
              <div id="subject-edit-start-time-error" class="text-danger small mt-1"></div>
            </div>
            <div class="col-6">
              <label for="subject-edit-end-time" class="form-label">終了時刻</label>
              <select id="subject-edit-end-time" class="form-select" required>
                <option value="10:00">10:00</option>
                <option value="11:00">11:00</option>
                <option value="12:00">12:00</option>
                <option value="13:00">13:00</option>
                <option value="14:00">14:00</option>
                <option value="15:00">15:00</option>
                <option value="16:00">16:00</option>
                <option value="17:00">17:00</option>
                <option value="18:00">18:00</option>
                <option value="19:00">19:00</option>
              </select>
              <div id="subject-edit-end-time-error" class="text-danger small mt-1"></div>
            </div>
          </div>
          <div class="mb-3">
            <label for="subject-edit-notes" class="form-label">詳細・メモ（任意）</label>
            <textarea id="subject-edit-notes" class="form-control" rows="3"></textarea>
            <div id="subject-edit-notes-error" class="text-danger small mt-1"></div>
          </div>
          <div id="subject-edit-notice" class="alert alert-warning small mb-0">
            保存すると、今日以降（今日を含む）のこの授業の予定が、新しい内容で作り直されます。カレンダーで個別に変更・削除した日も、元に戻ります。今日より前の予定と、カレンダーから追加した単発の授業（補講など）は、変わりません。
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
          <button type="submit" id="subject-edit-submit-button" class="btn btn-primary" aria-describedby="subject-edit-notice">保存する</button>
        </div>
      </form>
    </div>
  </div>
</div>

<div class="modal fade" id="subject-delete-modal" tabindex="-1" aria-labelledby="subject-delete-modal-title" aria-describedby="subject-delete-target subject-delete-counts subject-delete-warning" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title h5" id="subject-delete-modal-title">授業を削除</h2>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="閉じる"></button>
      </div>
      <div class="modal-body">
        <p id="subject-delete-target" class="mb-2"></p>
        <p id="subject-delete-loading" class="text-muted mb-2">予定と課題の件数を確認しています…</p>
        <p id="subject-delete-counts" class="mb-2 d-none"></p>
        <div id="subject-delete-error" class="alert alert-danger d-none" role="alert"></div>
        <p id="subject-delete-warning" class="text-danger mb-0">削除は取り消せません。</p>
      </div>
      <div class="modal-footer">
        <button type="button" id="subject-delete-cancel-button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
        <button type="button" id="subject-delete-submit-button" class="btn btn-danger" aria-describedby="subject-delete-target subject-delete-counts subject-delete-warning" disabled>削除する</button>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="task-modal" tabindex="-1" aria-labelledby="task-modal-title" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <form id="task-form">
        <div class="modal-header">
          <h2 class="modal-title h5" id="task-modal-title">課題を追加</h2>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="閉じる"></button>
        </div>
        <div class="modal-body">
          <div id="task-form-error" class="alert alert-danger d-none" role="alert"></div>
          <div class="mb-3">
            <label for="task-title" class="form-label">課題名</label>
            <input type="text" id="task-title" class="form-control" required>
            <div id="task-title-error" class="text-danger small mt-1"></div>
          </div>
          <div class="mb-3">
            <label for="task-subject" class="form-label">対象授業</label>
            <select id="task-subject" class="form-select" required aria-describedby="task-subject-note"></select>
            <div id="task-subject-note" class="form-text"></div>
            <div id="task-subject-error" class="text-danger small mt-1"></div>
          </div>
          <div class="mb-3">
            <div class="row g-2">
              <div class="col-7">
                <label for="task-due-date" class="form-label">締切日</label>
                <input type="date" id="task-due-date" class="form-control" required>
              </div>
              <div class="col-5">
                <label for="task-due-time" class="form-label">締切時刻</label>
                <input type="time" id="task-due-time" class="form-control" required>
              </div>
            </div>
            <div id="task-due-error" class="text-danger small mt-1"></div>
          </div>
          <div class="mb-3">
            <label for="task-notes" class="form-label">詳細・メモ（任意）</label>
            <textarea id="task-notes" class="form-control" rows="3"></textarea>
            <div id="task-notes-error" class="text-danger small mt-1"></div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
          <button type="submit" id="task-submit-button" class="btn btn-primary">登録する</button>
        </div>
      </form>
    </div>
  </div>
</div>

<div class="modal fade" id="task-edit-modal" tabindex="-1" aria-labelledby="task-edit-modal-title" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <form id="task-edit-form">
        <div class="modal-header">
          <h2 class="modal-title h5" id="task-edit-modal-title"></h2>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="閉じる"></button>
        </div>
        <div class="modal-body">
          <div id="task-edit-form-error" class="alert alert-danger d-none" role="alert"></div>
          <div class="mb-3">
            <label for="task-edit-title" id="task-edit-title-label" class="form-label"></label>
            <input type="text" id="task-edit-title" class="form-control" required>
            <div id="task-edit-title-error" class="text-danger small mt-1"></div>
          </div>
          <div id="task-edit-subject-row" class="mb-3">
            <label for="task-edit-subject" class="form-label">対象授業</label>
            <select id="task-edit-subject" class="form-select" required aria-describedby="task-edit-subject-note"></select>
            <div id="task-edit-subject-note" class="form-text"></div>
            <div id="task-edit-subject-error" class="text-danger small mt-1"></div>
          </div>
          <div class="mb-3">
            <div class="row g-2">
              <div class="col-7">
                <label for="task-edit-due-date" class="form-label">締切日</label>
                <input type="date" id="task-edit-due-date" class="form-control" required>
              </div>
              <div class="col-5">
                <label for="task-edit-due-time" class="form-label">締切時刻</label>
                <input type="time" id="task-edit-due-time" class="form-control" required>
              </div>
            </div>
            <div id="task-edit-due-error" class="text-danger small mt-1"></div>
          </div>
          <div class="mb-3">
            <label for="task-edit-notes" class="form-label">詳細・メモ（任意）</label>
            <textarea id="task-edit-notes" class="form-control" rows="3"></textarea>
            <div id="task-edit-notes-error" class="text-danger small mt-1"></div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
          <button type="submit" id="task-edit-submit-button" class="btn btn-primary">保存する</button>
        </div>
      </form>
    </div>
  </div>
</div>

<div class="modal fade" id="task-delete-modal" tabindex="-1" aria-labelledby="task-delete-modal-title" aria-describedby="task-delete-target task-delete-warning" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title h5" id="task-delete-modal-title">課題・タスクを削除</h2>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="閉じる"></button>
      </div>
      <div class="modal-body">
        <p id="task-delete-target" class="mb-2"></p>
        <div id="task-delete-error" class="alert alert-danger d-none" role="alert"></div>
        <p id="task-delete-warning" class="text-danger mb-0">削除は取り消せません。</p>
      </div>
      <div class="modal-footer">
        <button type="button" id="task-delete-cancel-button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
        <button type="button" id="task-delete-submit-button" class="btn btn-danger" aria-describedby="task-delete-target task-delete-warning">削除する</button>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="event-modal" tabindex="-1" aria-labelledby="event-modal-title" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title h5 text-break" id="event-modal-title"></h2>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="閉じる"></button>
      </div>
      <div class="modal-body">
        <dl class="mb-0 text-break">
          <div class="row mb-2">
            <dt class="col-4">カテゴリ</dt>
            <dd class="col-8 mb-0"><span id="event-modal-category-icon" class="me-1" aria-hidden="true"></span><span id="event-modal-category"></span></dd>
          </div>
          <div class="row mb-2">
            <dt class="col-4">日付</dt>
            <dd id="event-modal-date" class="col-8 mb-0"></dd>
          </div>
          <div class="row mb-2">
            <dt class="col-4">時間</dt>
            <dd id="event-modal-time" class="col-8 mb-0"></dd>
          </div>
          <div id="event-modal-room-row" class="row mb-2">
            <dt class="col-4">教室</dt>
            <dd id="event-modal-room" class="col-8 mb-0"></dd>
          </div>
          <div id="event-modal-employer-row" class="row mb-2">
            <dt class="col-4">派遣会社</dt>
            <dd id="event-modal-employer" class="col-8 mb-0"></dd>
          </div>
          <div id="event-modal-notes-row" class="row mb-2">
            <dt class="col-4">詳細・メモ</dt>
            <dd id="event-modal-notes" class="col-8 mb-0 text-pre-wrap"></dd>
          </div>
        </dl>
      </div>
      <div class="modal-footer">
        <button type="button" id="event-modal-delete-button" class="btn btn-outline-danger me-auto">削除</button>
        <button type="button" id="event-modal-edit-button" class="btn btn-primary">編集</button>
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">閉じる</button>
      </div>
    </div>
  </div>
</div>
<div class="modal fade" id="task-detail-modal" tabindex="-1" aria-labelledby="task-detail-modal-title" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title h5 text-break" id="task-detail-modal-title"></h2>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="閉じる"></button>
      </div>
      <div class="modal-body">
        <div id="task-detail-error" class="alert alert-danger d-none" role="alert"></div>
        <dl class="mb-3 text-break">
          <div class="row mb-2">
            <dt class="col-4">カテゴリ</dt>
            <dd class="col-8 mb-0"><span id="task-detail-category-icon" class="me-1" aria-hidden="true"></span><span id="task-detail-category"></span></dd>
          </div>
          <div class="row mb-2">
            <dt class="col-4">締切</dt>
            <dd class="col-8 mb-0"><span id="task-detail-due"></span><span id="task-detail-overdue" class="badge text-bg-danger ms-1 d-none">期限切れ</span></dd>
          </div>
          <div id="task-detail-subject-row" class="row mb-2">
            <dt class="col-4">対象授業</dt>
            <dd id="task-detail-subject" class="col-8 mb-0"></dd>
          </div>
          <div id="task-detail-notes-row" class="row mb-2">
            <dt class="col-4">詳細・メモ</dt>
            <dd id="task-detail-notes" class="col-8 mb-0 text-pre-wrap"></dd>
          </div>
        </dl>
        <div class="form-check">
          <input type="checkbox" id="task-detail-completed" class="form-check-input">
          <label class="form-check-label" for="task-detail-completed">完了</label>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" id="task-detail-delete-button" class="btn btn-outline-danger me-auto">削除</button>
        <button type="button" id="task-detail-edit-button" class="btn btn-primary">編集</button>
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">閉じる</button>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="event-add-modal" tabindex="-1" aria-labelledby="event-add-modal-title" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <form id="event-add-form">
        <div class="modal-header">
          <h2 class="modal-title h5" id="event-add-modal-title">予定を追加</h2>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="閉じる"></button>
        </div>
        <div class="modal-body">
          <div id="event-add-form-error" class="alert alert-danger d-none" role="alert"></div>
          <fieldset class="mb-3">
            <legend class="form-label fs-6">カテゴリ</legend>
            <div class="btn-group">
              <input type="radio" class="btn-check" name="event-add-category" id="event-add-category-class" value="class">
              <label class="btn btn-outline-primary" for="event-add-category-class">授業（補講など）</label>
              <input type="radio" class="btn-check" name="event-add-category" id="event-add-category-part-time" value="part_time">
              <label class="btn btn-outline-primary" for="event-add-category-part-time">アルバイト</label>
              <input type="radio" class="btn-check" name="event-add-category" id="event-add-category-other" value="other">
              <label class="btn btn-outline-primary" for="event-add-category-other">その他</label>
            </div>
          </fieldset>
          <fieldset id="event-add-other-type-row" class="mb-3">
            <legend class="form-label fs-6">その他の種類</legend>
            <div class="form-check form-check-inline">
              <input type="radio" class="form-check-input" name="event-add-other-type" id="event-add-other-type-timed" value="timed">
              <label class="form-check-label" for="event-add-other-type-timed">時間指定あり</label>
            </div>
            <div class="form-check form-check-inline">
              <input type="radio" class="form-check-input" name="event-add-other-type" id="event-add-other-type-deadline" value="deadline">
              <label class="form-check-label" for="event-add-other-type-deadline">締切のみ</label>
            </div>
          </fieldset>
          <div id="event-add-subject-row" class="mb-3">
            <label for="event-add-subject" class="form-label">授業</label>
            <select id="event-add-subject" class="form-select" required aria-describedby="event-add-subject-note"></select>
            <div id="event-add-subject-note" class="form-text"></div>
            <div id="event-add-subject-error" class="text-danger small mt-1"></div>
          </div>
          <div id="event-add-title-row" class="mb-3">
            <label for="event-add-title" id="event-add-title-label" class="form-label"></label>
            <input type="text" id="event-add-title" class="form-control" required>
            <div id="event-add-title-error" class="text-danger small mt-1"></div>
          </div>
          <div id="event-add-employer-row" class="mb-3">
            <label for="event-add-employer" class="form-label">派遣会社（任意）</label>
            <input type="text" id="event-add-employer" class="form-control" list="event-employer-options" autocomplete="off">
            <div id="event-add-employer-error" class="text-danger small mt-1"></div>
          </div>
          <div id="event-add-date-row" class="mb-3">
            <label for="event-add-date" class="form-label">日付</label>
            <input type="date" id="event-add-date" class="form-control" required>
            <div id="event-add-date-error" class="text-danger small mt-1"></div>
          </div>
          <div id="event-add-time-row" class="row g-2 mb-3">
            <div class="col-6">
              <label for="event-add-start-time" class="form-label">開始時刻</label>
              <input type="time" id="event-add-start-time" class="form-control" required>
              <div id="event-add-start-time-error" class="text-danger small mt-1"></div>
            </div>
            <div class="col-6">
              <label for="event-add-end-time" class="form-label">終了時刻</label>
              <input type="time" id="event-add-end-time" class="form-control" required>
              <div id="event-add-end-time-error" class="text-danger small mt-1"></div>
            </div>
          </div>
          <div id="event-add-due-row" class="mb-3">
            <div class="row g-2">
              <div class="col-7">
                <label for="event-add-due-date" class="form-label">締切日</label>
                <input type="date" id="event-add-due-date" class="form-control" required>
              </div>
              <div class="col-5">
                <label for="event-add-due-time" class="form-label">締切時刻</label>
                <input type="time" id="event-add-due-time" class="form-control" required>
              </div>
            </div>
            <div id="event-add-due-error" class="text-danger small mt-1"></div>
          </div>
          <div id="event-add-room-row" class="mb-3">
            <label for="event-add-room" class="form-label">教室（任意）</label>
            <input type="text" id="event-add-room" class="form-control">
            <div id="event-add-room-error" class="text-danger small mt-1"></div>
          </div>
          <div class="mb-3">
            <label for="event-add-notes" class="form-label">詳細・メモ（任意）</label>
            <textarea id="event-add-notes" class="form-control" rows="3"></textarea>
            <div id="event-add-notes-error" class="text-danger small mt-1"></div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
          <button type="submit" id="event-add-submit-button" class="btn btn-primary">登録する</button>
        </div>
      </form>
    </div>
  </div>
</div>

<div class="modal fade" id="event-edit-modal" tabindex="-1" aria-labelledby="event-edit-modal-title" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <form id="event-edit-form">
        <div class="modal-header">
          <h2 class="modal-title h5" id="event-edit-modal-title">予定を編集</h2>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="閉じる"></button>
        </div>
        <div class="modal-body">
          <div id="event-edit-form-error" class="alert alert-danger d-none" role="alert"></div>
          <p class="mb-3">カテゴリ：<span id="event-edit-category-icon" class="me-1" aria-hidden="true"></span><span id="event-edit-category"></span></p>
          <div id="event-edit-subject-row" class="mb-3">
            <div class="form-label mb-0">授業</div>
            <p id="event-edit-subject" class="mb-0 text-break"></p>
          </div>
          <div id="event-edit-title-row" class="mb-3">
            <label for="event-edit-title" id="event-edit-title-label" class="form-label"></label>
            <input type="text" id="event-edit-title" class="form-control" required>
            <div id="event-edit-title-error" class="text-danger small mt-1"></div>
          </div>
          <div id="event-edit-employer-row" class="mb-3">
            <label for="event-edit-employer" class="form-label">派遣会社（任意）</label>
            <input type="text" id="event-edit-employer" class="form-control" list="event-employer-options" autocomplete="off">
            <div id="event-edit-employer-error" class="text-danger small mt-1"></div>
          </div>
          <div id="event-edit-date-row" class="mb-3">
            <label for="event-edit-date" class="form-label">日付</label>
            <input type="date" id="event-edit-date" class="form-control" required>
            <div id="event-edit-date-error" class="text-danger small mt-1"></div>
          </div>
          <div id="event-edit-fixed-date-row" class="mb-3">
            <div class="form-label mb-0">日付</div>
            <p id="event-edit-fixed-date" class="mb-1"></p>
            <p class="small text-muted mb-0">授業の登録で作られた予定のため、日付は変えられません。別の日に移すときは、この予定を削除して、移す先の日に、単発の授業（補講など）を追加してください。授業全体を編集すると、今日以降のこの授業の予定は、授業の設定どおりに作り直されます（ここで変えた内容も、元に戻ります）。</p>
          </div>
          <div class="row g-2 mb-3">
            <div class="col-6">
              <label for="event-edit-start-time" class="form-label">開始時刻</label>
              <input type="time" id="event-edit-start-time" class="form-control" required>
              <div id="event-edit-start-time-error" class="text-danger small mt-1"></div>
            </div>
            <div class="col-6">
              <label for="event-edit-end-time" class="form-label">終了時刻</label>
              <input type="time" id="event-edit-end-time" class="form-control" required>
              <div id="event-edit-end-time-error" class="text-danger small mt-1"></div>
            </div>
          </div>
          <div id="event-edit-room-row" class="mb-3">
            <label for="event-edit-room" class="form-label">教室（任意）</label>
            <input type="text" id="event-edit-room" class="form-control">
            <div id="event-edit-room-error" class="text-danger small mt-1"></div>
          </div>
          <div class="mb-3">
            <label for="event-edit-notes" class="form-label">詳細・メモ（任意）</label>
            <textarea id="event-edit-notes" class="form-control" rows="3"></textarea>
            <div id="event-edit-notes-error" class="text-danger small mt-1"></div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
          <button type="submit" id="event-edit-submit-button" class="btn btn-primary">保存する</button>
        </div>
      </form>
    </div>
  </div>
</div>

<div class="modal fade" id="event-delete-modal" tabindex="-1" aria-labelledby="event-delete-modal-title" aria-describedby="event-delete-target event-delete-generated-note event-delete-warning" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title h5" id="event-delete-modal-title">予定を削除</h2>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="閉じる"></button>
      </div>
      <div class="modal-body">
        <p id="event-delete-target" class="mb-2 text-break"></p>
        <p id="event-delete-generated-note" class="mb-2 d-none"></p>
        <div id="event-delete-error" class="alert alert-danger d-none" role="alert"></div>
        <p id="event-delete-warning" class="text-danger mb-0">削除は取り消せません。</p>
      </div>
      <div class="modal-footer">
        <button type="button" id="event-delete-cancel-button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
        <button type="button" id="event-delete-submit-button" class="btn btn-danger" aria-describedby="event-delete-target event-delete-generated-note event-delete-warning">削除する</button>
      </div>
    </div>
  </div>
</div>

<datalist id="event-employer-options"></datalist>
{% endblock %}

{% block scripts %}
<script type="module" src="{{ url_for('static', filename='js/main.js') }}"></script>
{% endblock %}
```

### 付録G. `app/static/js/semesters.js`

<!-- 全文: app/static/js/semesters.js -->
```
import { apiRequest } from "./api.js";
import { chooseCurrentSemester } from "./current_semester.js";
import { formatJapaneseDate, localDateString } from "./dates.js";
import {
  clearFormErrors,
  errorMessageOf,
  getElement,
  hideModal,
  setSubmitting,
  setVisible,
  showApiError,
  trackModalShowing,
} from "./ui.js";

let semesters = [];
let selectedId = null;
// 編集・削除の対象の学期（選択中の学期の値のコピー）。モーダルを開くときに
// 入れる。
let editingSemester = null;
let deletingSemester = null;
// 編集・削除のモーダルを開くたびに増やす通し番号。閉じて開き直したあとに
// 届いた古い応答で、今のモーダルの表示を変えないために使う。
let editSerial = 0;
let deleteSerial = 0;

// 学期名の形（「2026年度 前期」。APIが検査する）。編集のときに、年度と
// 種別に分けるために使う。
const SEMESTER_NAME_PATTERN = /^([0-9]{4})年度 (前期|後期)$/;

const SEMESTER_FIELDS = {
  name: {
    inputIds: ["semester-year", "semester-term"],
    messageId: "semester-name-error",
  },
  start_date: {
    inputIds: ["semester-start-date"],
    messageId: "semester-start-date-error",
  },
  end_date: {
    inputIds: ["semester-end-date"],
    messageId: "semester-end-date-error",
  },
};

const SEMESTER_FORM_ERROR_ID = "semester-form-error";
const SEMESTER_SUBMIT_LABELS = {
  idle: "登録する",
  busy: "登録中…",
};
const SEMESTER_EDIT_FIELDS = {
  name: {
    inputIds: ["semester-edit-year", "semester-edit-term"],
    messageId: "semester-edit-name-error",
  },
  start_date: {
    inputIds: ["semester-edit-start-date"],
    messageId: "semester-edit-start-date-error",
  },
  end_date: {
    inputIds: ["semester-edit-end-date"],
    messageId: "semester-edit-end-date-error",
  },
};
const SEMESTER_EDIT_FORM_ERROR_ID = "semester-edit-form-error";
const SEMESTER_EDIT_SUBMIT_LABELS = {
  idle: "保存する",
  busy: "保存中…",
};
const SEMESTER_DELETE_SUBMIT_LABELS = {
  idle: "削除する",
  busy: "削除中…",
};

// 年度と種別から、学期名（「2026年度 前期」）を組み立てる。
function semesterName(year, term) {
  return `${year}年度 ${term}`;
}

// 学期の期間を表す文字列（「2026年9月21日 〜 2026年12月27日」）。
function semesterPeriod(semester) {
  return (
    `${formatJapaneseDate(semester.start_date)} 〜 ` +
    `${formatJapaneseDate(semester.end_date)}`
  );
}

// 選択中の学期（なければ null）。
function selectedSemester() {
  return semesters.find((semester) => semester.id === selectedId) ?? null;
}

function clearSemesterFormErrors() {
  clearFormErrors(SEMESTER_FIELDS, SEMESTER_FORM_ERROR_ID);
}

function resetForm() {
  const now = new Date();
  // getMonth()は0始まり（3は4月、7は8月）。
  const year = now.getFullYear() - (now.getMonth() < 3 ? 1 : 0);
  const term = now.getMonth() >= 3 && now.getMonth() <= 7 ? "前期" : "後期";
  const form = getElement("semester-form");
  const submitButton = getElement("semester-submit-button");

  // モーダルを開くたび前回の入力や失敗表示を残さず、今日に基づく初期値から始める。
  form.reset();
  getElement("semester-year").value = String(year);
  getElement("semester-term").value = term;
  getElement("semester-start-date").value = "";
  getElement("semester-end-date").value = "";
  setSubmitting(submitButton, false, SEMESTER_SUBMIT_LABELS);
  clearSemesterFormErrors();
}

function renderTabs() {
  const tabs = getElement("semester-tabs");
  const fragment = document.createDocumentFragment();

  for (const semester of semesters) {
    const item = document.createElement("li");
    item.className = "nav-item";
    item.setAttribute("role", "presentation");

    const button = document.createElement("button");
    button.type = "button";
    button.id = `semester-tab-${semester.id}`;
    button.className = "nav-link";
    button.setAttribute("role", "tab");
    button.setAttribute("aria-controls", "semester-detail");
    button.textContent = semester.name;
    button.addEventListener("click", () => {
      selectSemester(semester.id);
    });

    item.append(button);
    fragment.append(item);
  }

  tabs.replaceChildren(fragment);
}

function updateTabSelection() {
  for (const item of getElement("semester-tabs").children) {
    const button = item.querySelector('[role="tab"]');
    const selected = button.id === `semester-tab-${selectedId}`;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-selected", selected ? "true" : "false");
  }

  const selected = selectedSemester();
  if (selected !== null) {
    getElement("semester-detail").setAttribute(
      "aria-labelledby",
      `semester-tab-${selected.id}`,
    );
  }
}

function renderBanner() {
  const today = localDateString();
  const hasCurrentSemester = semesters.some(
    (semester) => semester.start_date <= today && today <= semester.end_date,
  );
  setVisible(getElement("semester-banner"), !hasCurrentSemester);
}

function renderDetail() {
  const selected = selectedSemester();
  if (selected === null) {
    return;
  }

  getElement("semester-detail-name").textContent = selected.name;
  getElement("semester-detail-period").textContent = semesterPeriod(selected);
  // 読み上げで、どの学期のボタンかが分かるように、aria-label に学期名を
  // 入れる。
  getElement("semester-edit-button").setAttribute(
    "aria-label",
    `「${selected.name}」を編集`,
  );
  getElement("semester-delete-button").setAttribute(
    "aria-label",
    `「${selected.name}」を削除`,
  );
}

// 学期を選ぶ。選択中の学期が変わったときに、semester-selected を発行する。
// notifySameSemester が true なら、同じ学期を選び直したときも発行する
// （選択中の学期を編集したとき。休講日の一覧や、授業の登録先の学期名を、
// 新しい値で作り直してもらうため）。
function selectSemester(id, { notifySameSemester = false } = {}) {
  const previousId = selectedId;
  selectedId = id;

  updateTabSelection();
  renderDetail();

  if (previousId !== id || notifySameSemester) {
    const selected = selectedSemester();
    const semester =
      selected === null
        ? null
        : {
            id: selected.id,
            name: selected.name,
            start_date: selected.start_date,
            end_date: selected.end_date,
          };
    // 状態変更と通知をここに集約し、購読側が更新済みの画面を扱えるよう描画後に発行する。
    document.dispatchEvent(
      new CustomEvent("semester-selected", {
        detail: { semester },
      }),
    );
  }
}

function showLoading() {
  setVisible(getElement("semester-loading"), true);
  setVisible(getElement("semester-load-error"), false);
  setVisible(getElement("semester-empty"), false);
  setVisible(getElement("semester-content"), false);
}

function showLoadError(error) {
  getElement("semester-load-error-message").textContent =
    errorMessageOf(error);
  setVisible(getElement("semester-loading"), false);
  setVisible(getElement("semester-load-error"), true);
  setVisible(getElement("semester-empty"), false);
  setVisible(getElement("semester-content"), false);
}

function showEmpty() {
  setVisible(getElement("semester-loading"), false);
  setVisible(getElement("semester-load-error"), false);
  setVisible(getElement("semester-empty"), true);
  setVisible(getElement("semester-content"), false);
}

function showContent() {
  setVisible(getElement("semester-loading"), false);
  setVisible(getElement("semester-load-error"), false);
  setVisible(getElement("semester-empty"), false);
  setVisible(getElement("semester-content"), true);
  renderBanner();
}

// 学期の一覧を取得し、学期を選ぶ。preferredId の学期があれば、その学期を
// 選ぶ（なければ、今の学期の規則で選ぶ）。notifySameSemester は、
// selectSemester と同じ。
async function loadSemesters({
  preferredId = null,
  notifySameSemester = false,
} = {}) {
  showLoading();
  try {
    semesters = await apiRequest("GET", "/api/semesters");
    if (semesters.length === 0) {
      showEmpty();
      selectSemester(null);
      return;
    }

    const preferred = semesters.find(
      (semester) => semester.id === preferredId,
    );
    const initial =
      preferred ?? chooseCurrentSemester(semesters, localDateString());
    showContent();
    renderTabs();
    selectSemester(initial.id, { notifySameSemester });
  } catch (error) {
    showLoadError(error);
  }
}

async function submitSemester(event) {
  event.preventDefault();
  clearSemesterFormErrors();

  const submitButton = getElement("semester-submit-button");
  setSubmitting(submitButton, true, SEMESTER_SUBMIT_LABELS);

  const name = semesterName(
    getElement("semester-year").value,
    getElement("semester-term").value,
  );
  const startDate = getElement("semester-start-date").value;
  const endDate = getElement("semester-end-date").value;

  // try で囲むのは、登録の要求だけにする（成功後の処理の例外を、
  // 「登録の失敗」として表示しないため）。
  let created;
  try {
    created = await apiRequest("POST", "/api/semesters", {
      name,
      start_date: startDate,
      end_date: endDate,
    });
  } catch (error) {
    showApiError(error, SEMESTER_FIELDS, SEMESTER_FORM_ERROR_ID);
    setSubmitting(submitButton, false, SEMESTER_SUBMIT_LABELS);
    return;
  }

  // 表示のアニメーションの途中でも、表示が終わってから閉じる（ui.js）。
  hideModal(getElement("semester-modal"));
  await loadSemesters({ preferredId: created.id });
}

// 編集のモーダルを開くたびに、選択中の学期の今の値を入力欄に入れ、
// エラーの表示を消す。「編集」ボタンは、学期の本文（学期を選んでいる
// ときだけ表示する）にあり、data-bs-toggle で、このモーダルを開く。
function fillEditForm() {
  editSerial += 1;
  editingSemester = { ...selectedSemester() };
  const match = SEMESTER_NAME_PATTERN.exec(editingSemester.name);

  getElement("semester-edit-form").reset();
  if (match !== null) {
    getElement("semester-edit-year").value = match[1];
    getElement("semester-edit-term").value = match[2];
  }
  getElement("semester-edit-start-date").value = editingSemester.start_date;
  getElement("semester-edit-end-date").value = editingSemester.end_date;
  clearFormErrors(SEMESTER_EDIT_FIELDS, SEMESTER_EDIT_FORM_ERROR_ID);
  setSubmitting(
    getElement("semester-edit-submit-button"),
    false,
    SEMESTER_EDIT_SUBMIT_LABELS,
  );
}

async function submitSemesterEdit(event) {
  event.preventDefault();
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = editSerial;
  const semesterId = editingSemester.id;
  clearFormErrors(SEMESTER_EDIT_FIELDS, SEMESTER_EDIT_FORM_ERROR_ID);

  const submitButton = getElement("semester-edit-submit-button");
  setSubmitting(submitButton, true, SEMESTER_EDIT_SUBMIT_LABELS);

  // try で囲むのは、編集の要求だけにする（登録と同じ理由）。
  // すべての項目を送る（変えていない項目も、今の値のまま送る）。
  try {
    await apiRequest("PATCH", `/api/semesters/${semesterId}`, {
      name: semesterName(
        getElement("semester-edit-year").value,
        getElement("semester-edit-term").value,
      ),
      start_date: getElement("semester-edit-start-date").value,
      end_date: getElement("semester-edit-end-date").value,
    });
  } catch (error) {
    if (startedSerial !== editSerial) {
      return;
    }
    showApiError(error, SEMESTER_EDIT_FIELDS, SEMESTER_EDIT_FORM_ERROR_ID);
    setSubmitting(submitButton, false, SEMESTER_EDIT_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === editSerial) {
    hideModal(getElement("semester-edit-modal"));
  }
  // 同じ学期でも、semester-selected を発行する（期間の外になった休講日は
  // 削除されているため、休講日の一覧を取得し直してもらう。授業の登録先の
  // 学期名も、新しい名前にする）。
  await loadSemesters({ preferredId: semesterId, notifySameSemester: true });
}

function showDeleteError(error) {
  const deleteError = getElement("semester-delete-error");
  deleteError.textContent = errorMessageOf(error);
  setVisible(deleteError, true);
}

function hideDeleteError() {
  const deleteError = getElement("semester-delete-error");
  deleteError.replaceChildren();
  setVisible(deleteError, false);
}

// 削除の確認のモーダルを開くたびに、選択中の学期を表示し、授業と休講日の
// 件数を、学期の1件取得（subject_count・closure_count）で取得する。授業が
// ある学期は、削除できない（「削除する」ボタンは、押せないまま）。
// 「削除」ボタンは、「編集」ボタンと同じく、data-bs-toggle で開く。
async function prepareDeleteModal() {
  const currentSerial = ++deleteSerial;
  deletingSemester = { ...selectedSemester() };
  const semester = deletingSemester;
  const loading = getElement("semester-delete-loading");
  const counts = getElement("semester-delete-counts");
  const warning = getElement("semester-delete-warning");
  const submitButton = getElement("semester-delete-submit-button");

  getElement("semester-delete-target").textContent =
    `「${semester.name}」（${semesterPeriod(semester)}）を削除します。`;
  counts.replaceChildren();
  setVisible(counts, false);
  setVisible(loading, true);
  setVisible(warning, true);
  hideDeleteError();
  submitButton.textContent = SEMESTER_DELETE_SUBMIT_LABELS.idle;
  submitButton.disabled = true;

  let detail;
  try {
    detail = await apiRequest("GET", `/api/semesters/${semester.id}`);
  } catch (error) {
    // モーダルを開き直していたら、今のモーダルの表示を変えない。
    if (currentSerial !== deleteSerial) {
      return;
    }
    setVisible(loading, false);
    // 件数を取得できなかったときは、「削除する」ボタンを押せないままにする。
    showDeleteError(error);
    return;
  }

  if (currentSerial !== deleteSerial) {
    return;
  }
  setVisible(loading, false);
  if (detail.subject_count > 0) {
    counts.textContent =
      `この学期には、授業が${detail.subject_count}件登録されているため、` +
      "削除できません。先に、この画面の授業の一覧から、" +
      "授業をすべて削除してください。";
    setVisible(counts, true);
    setVisible(warning, false);
    return;
  }
  counts.textContent =
    `この学期の休講日${detail.closure_count}件も、まとめて削除されます。`;
  setVisible(counts, true);
  submitButton.disabled = false;
}

async function submitSemesterDelete() {
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = deleteSerial;
  const semesterId = deletingSemester.id;
  hideDeleteError();

  const submitButton = getElement("semester-delete-submit-button");
  setSubmitting(submitButton, true, SEMESTER_DELETE_SUBMIT_LABELS);

  // try で囲むのは、削除の要求だけにする（登録と同じ理由）。
  try {
    await apiRequest("DELETE", `/api/semesters/${semesterId}`);
  } catch (error) {
    if (startedSerial !== deleteSerial) {
      return;
    }
    showDeleteError(error);
    setSubmitting(submitButton, false, SEMESTER_DELETE_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === deleteSerial) {
    hideModal(getElement("semester-delete-modal"));
  }
  // 削除した学期はないため、今の学期の規則で、学期を選び直す。
  await loadSemesters();
}

export function initSemesters() {
  getElement("semester-retry-button").addEventListener("click", () => {
    loadSemesters();
  });
  const modal = getElement("semester-modal");
  // 登録に成功したら、JavaScriptから閉じるため、表示の途中かを記録する。
  trackModalShowing(modal);
  modal.addEventListener("show.bs.modal", resetForm);
  getElement("semester-form").addEventListener("submit", submitSemester);

  // 編集・削除のモーダルも、成功したら、JavaScriptから閉じるため、
  // 表示の途中かを記録する（ui.js の hideModal）。
  const editModal = getElement("semester-edit-modal");
  trackModalShowing(editModal);
  editModal.addEventListener("show.bs.modal", fillEditForm);
  editModal.addEventListener("shown.bs.modal", () => {
    getElement("semester-edit-year").focus();
  });
  getElement("semester-edit-form").addEventListener(
    "submit",
    submitSemesterEdit,
  );

  const deleteModal = getElement("semester-delete-modal");
  trackModalShowing(deleteModal);
  deleteModal.addEventListener("show.bs.modal", prepareDeleteModal);
  // 取り消せない操作のため、最初のフォーカスは「キャンセル」に置く。
  deleteModal.addEventListener("shown.bs.modal", () => {
    getElement("semester-delete-cancel-button").focus();
  });
  getElement("semester-delete-submit-button").addEventListener(
    "click",
    submitSemesterDelete,
  );

  loadSemesters();
}
```
