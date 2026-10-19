# タスク019: 予定の登録・編集・削除のAPI

| 項目 | 内容 |
|---|---|
| Task ID | 019 |
| Task名 | 予定の登録・編集・削除のAPI（`POST /api/events`・`PATCH`・`DELETE /api/events/<id>`）と、派遣会社の入力候補（`GET /api/events/employers`） |
| ブランチ | `feature/019-event-create-edit-delete-api`（Komaが作成・切替済みの状態で渡される） |

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに停止して報告する。

**このタスクには、承認ゲートはない（DBの構造を変えないため、migrationを作らない）。** 段階1を進め、「Copilot確認手順」を実施したら、結果を報告して応答を終える。途中で止まるのは、「注意」の停止の条件に当たったときだけ。**止まるときは、報告を書いて応答を終える。質問の機能（選択肢を出して回答を待つ機能）は使わない**（`.github/copilot-instructions.md` の「止まる場面の応答」）。

**ファイルは、手で書き写さない。** 4つのファイルの全文は、このTask MDの付録にある。段階の始めに、「全文からファイルを作るスクリプト」を実行して作る（013-N1）。付録の全文は、スクリプトが読む。付録を読んで書き写す必要はない（本文の要点・差分・確認の手順を読む）。

**報告には、コマンドの出力を、要約せずに、そのまま貼る**（014-L1）。「注意」の最後の報告の項目を参照。「Copilot確認手順」の5（検索と差分）は、各コマンドの前に、`echo` で見出しを出すように書いてある。**見出しの行も含めて、出力をそのまま貼る**（018-N1）。

**このTask MDのスクリプトとコマンドには、バックスラッシュ（`\`）の書き方を使っていない**（016-N1。改行は、スクリプトの中で `newline = chr(10)` として表す。`grep` は、`-F`（文字どおりに探す）と `-e`（探す文字列を1つずつ指定）で書く）。**コマンドは、書いてあるとおりに実行する。`grep` の `-e` を足す・減らすことも含め、書き換えた場合は、どこをどう書き換えたかを、報告に書く**（017-N1）。

## 目的
カレンダーから行う予定の操作（後続のタスクで作る画面）の前提になる、予定の登録・編集・削除のAPIと、アルバイトの派遣会社の入力候補のAPIを作る。設計資料（`docs/architecture.md` の「予定API」「カレンダーからの授業の予定の操作」「データ設計」のEventの注意、「API共通ルール」）の仕様を、そのまま実装する。2026-10-19に決めた次のことを含む（それまでの未決定事項「カレンダーからの授業の予定の操作と、自動生成の予定との関係」「日付をまたぐアルバイト」）。

- 登録できるのは、単発の予定（単発の授業（補講など）・アルバイト・その他（時間指定あり））。登録した予定は、常に `is_generated=false`。カテゴリによって、受け付ける項目が違う（授業は授業ID・教室、アルバイトはタイトル・派遣会社、その他はタイトル）
- 自動生成の授業の予定は、編集で日付を変えられない（時刻・教室・詳細／メモだけ）。削除はできる
- 日付をまたぐ予定（例：22:00〜翌2:00）は、1件では登録できない（終了時刻は、開始時刻より後）
- 派遣会社の候補は、アルバイトの予定の派遣会社を、重複を除いて、新しく使った順に返す

**画面とDBの構造は変えない**（カレンダーからの予定の操作の画面は、後続のタスク）。

| 段階 | 内容 | 挙動の変化 | 段階の終わりの `pytest` |
|---|---|---|---|
| 1 | `app/routes/events.py`（登録・編集・削除と、派遣会社の候補）、`app/categories.py`（コメントだけ）、`tests/test_events_api.py`（405のテストの直しと、派遣会社の候補のテスト）、`tests/test_events_create_update_delete_api.py`（新規。227件） | `POST /api/events`・`PATCH`・`DELETE /api/events/<id>`・`GET /api/events/employers` が使えるようになる（今は405・404） | **1021件**（787 − 3 ＋ 10 ＋ 227） |

（段階は1つだけ。テストの405の直しと、routeの追加を、同じ段階で行わないと、テストが通らないため。スクリプトは、これまでのTask MDと同じ形で、`python - 1` で実行する）

## 前提（Task 018完了時点の状態）

| 区分 | 内容 |
|---|---|
| すでにある | 学期・授業・休講日のAPIと画面、授業の編集・削除（Task 014・015）、予定API（一覧・1件取得だけ。Task 012）、カレンダー表示（Task 013・018）、課題・タスクのAPIと画面（Task 016・017）、`app/categories.py` の `EVENT_CATEGORIES`（Task 016で定義し、まだ使っていない）。pytest（**787件**。`main` の `531c285` で確認） |
| まだない | `POST /api/events`・`PATCH`・`DELETE /api/events/<id>`（今は405）、`GET /api/events/employers`（今は404）、`tests/test_events_create_update_delete_api.py` |
| DBの構造 | 変えない（初期migration `0280f6cf8d09` と、休講日の `42bd53808fa1`）。`events` テーブルは、初期migrationにある。**migrationは不要**。モデル（`app/models/event.py`）も変えない |
| 開発用DB | `instance/app.db` は、Komaの実際の開発用DB（すべてのテーブルが0件。2026-10-18、Task 018の確認のあとにKomaが確認）。**Copilotは、書き込まない。サーバーを起動しない（`python run.py` を実行しない）**。読むのは、「Copilot確認手順」のハッシュと件数だけ。**`sqlite3` は、必ず `-readonly` を付けて実行する**（011-L1） |
| 設計資料 | このタスクの前に、更新した設計資料が `main` に反映されている。`docs/architecture.md` の「予定API」に、登録・編集・削除と「派遣会社の候補」があり、「繰り返し予定の扱い」の下に「カレンダーからの授業の予定の操作」の節がある。未決定事項から「カレンダーからの授業の予定の操作と、自動生成の予定との関係」「日付をまたぐアルバイト」が外れている |
| 画面 | 変えない。ブラウザでの確認はない。APIの動作は、pytestと、Komaの確認用のサーバーでの `curl` で確かめる |
| 「今日」 | 予定APIは、「今日」を使わない。新しいテストのファイルは、授業全体の編集（「今日」を使う）との関係を確かめるため、授業のrouteの「今日」を 2026-06-15 に固定する（`tests/test_subjects_update_delete_api.py` と同じ方法）。テストの結果は、実行した日によらない |

## Source of Truth
- `docs/architecture.md`：「データ設計」の「共通の約束」（削除、`category`）・「カテゴリの保存値の置き場所」・Event（表と、その下の注意。日付をまたぐ予定）、「繰り返し予定の扱い」の「同じ授業・同じ日付に単発の予定がある場合」・「編集・削除の仕様」・「授業全体の編集による作り直し」・「カレンダーからの授業の予定の操作」、「休講日の変更と予定の同期」、「API共通ルール」（「URLとメソッド」の、リソースに付随する一覧・「リクエストとレスポンス（JSON）」の `PATCH`・文字列・「決まった値から選ぶ文字列」・「ほかのリソースのIDを参照する項目」、「日付・時刻・日時」、「404の使い分け」）、「予定API」、「課題・タスクAPI」（`subject_id` の規則とメッセージ）、「授業API」（時刻のメッセージ）、「自動テスト（pytest）」、「ディレクトリ構成」
- `docs/requirements.md`：「カテゴリ」、「予定の登録」（アルバイト・その他、日付をまたぐ予定）、「予定の編集・削除」
- `docs/ui_ux.md`：「カレンダーモード」の「予定の追加」「予定の確認・編集・削除」（画面は作らないが、APIの使われ方の確認のため）
- `.github/copilot-instructions.md`：進め方、「止まる場面の応答」、コーディング方針、「テスト」

## 実装対象ファイル

| 区分 | ファイル | 段階 | 内容 | 全文 |
|---|---|---|---|---|
| 変更 | `app/routes/events.py` | 1 | 登録（`create_event`）・編集（`update_event`）・削除（`delete_event`）・派遣会社の候補（`get_employers`）と、その検証の関数・定数を足す。既存の関数（`event_to_dict`・`read_date_query`・`get_events`・`get_event`）は変えない | 付録A |
| 変更 | `app/categories.py` | 1 | `EVENT_CATEGORIES` の前のコメントだけ（「予定の登録・編集を作るタスクで使う」を「予定の登録で使う」に） | 付録B |
| 変更 | `tests/test_events_api.py` | 1 | `make_event` に `employer` を足す。派遣会社の候補のテスト（10件）を足す。提供しない操作のテストから、提供するようになった3つ（`POST /api/events`、`PATCH`・`DELETE /api/events/<id>`）を外す | 付録C |
| 新規 | `tests/test_events_create_update_delete_api.py` | 1 | 予定の登録・編集・削除のAPIのテスト（227件） | 付録D |

上の4ファイル以外は、変更しない（`__pycache__/` などの、`.gitignore` の対象は除く）。**4ファイルとも、このTask MDの付録に全文がある。「全文からファイルを作るスクリプト」で作り、手で書き写さない。書き込んだあとに、手で直さない。** 全文を変える必要があると判断した場合は、変えずに停止して報告する。

## 非対象（このタスクでは作らない・変更しない）
- モデル（`app/models/`）、`migrations/`（**新しいmigrationを作らない。`flask db` のコマンドを、一切実行しない**）、`requirements.txt`（**ライブラリを追加しない**）、`pytest.ini`、`run.py`
- `app/api_helpers.py`、`app/class_events.py`、`app/__init__.py`（`events_bp` は、登録済み）、`app/routes/` の、`events.py` 以外のファイル（`semesters.py`・`subjects.py`・`closures.py`・`tasks.py`・`main.py`）
- `app/templates/`、`app/static/`（画面は変えない。カレンダーからの予定の操作の画面は、後続のタスク）
- `tests/` の、上の2つ以外のファイル（`conftest.py`・`test_subjects_api.py`・`test_subjects_update_delete_api.py`・`test_closures_api.py`・`test_tasks_api.py` を含む）
- `docs/`、`.github/`、`.gitignore`
- 作らないもの：予定の画面（追加フォーム、詳細パネルの編集・削除）、その他（締切のみ）のカレンダーからの追加、日付をまたぐ予定を1件で表す仕組み、学期の変更・削除、曜日の読み替え
- 持ち越しの003-H・017-N2（このタスクでは扱わない）
- 開発用DB（`instance/app.db`）への書き込み、サーバーの起動（`python run.py` も、「Komaの確認」の確認用のサーバーも、起動しない）

## 全文からファイルを作るスクリプト（013-N1）
段階1の始めに、リポジトリのルートで、`.venv` を有効にして実行する（`python - 1`）。このTask MDの付録の、「`<!-- 全文: パス -->`」の印の行の直後のコードブロックを、そのパスのファイルに、そのまま書き込む。新規のファイルも、このスクリプトが作る。

```
python - 1 <<'EOF'
import sys
from pathlib import Path

# 段階ごとに書き込むファイル（このTask MDの「実装対象ファイル」と同じ）。
STAGE_FILES = {
    "1": [
        "app/routes/events.py",
        "app/categories.py",
        "tests/test_events_api.py",
        "tests/test_events_create_update_delete_api.py",
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
full_texts = read_full_texts(
    "docs/tasks/019_event_create_edit_delete_api.md"
)
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
| 1（`python - 1`） | `全文の数：4`、`app/routes/events.py：書き込み（515行）`、`app/categories.py：書き込み（28行）`、`tests/test_events_api.py：書き込み（554行）`、`tests/test_events_create_update_delete_api.py：書き込み（1545行）` |

- 出力が上と違う場合（全文の数・行数・エラー）は、ほかの作業をせずに停止して報告する
- 段階の終わりの「全文との比較」（「Copilot確認手順」の4）で「不一致」が出た場合は、手で直さず、スクリプトをもう一度実行して、全文に戻す。戻したことと、違っていた理由（分かれば）を、報告に書く（013-N1）

## 段階1：予定の登録・編集・削除と、派遣会社の候補

### 1-1. `app/routes/events.py`（全文：付録A）
既存の関数は変えず、定数・検証の関数・routeを足す（`git diff --numstat` で、削除の行が0）。ファイルの構成（上から順に）：

| 名前 | 種類 | 内容 |
|---|---|---|
| `events_bp` | Blueprint | 変えない（`url_prefix="/api/events"`） |
| `UPDATE_FIELDS`・`CREATE_FIELDS` | 定数 | 編集・登録で受け付ける項目。編集は `category`・`subject_id` を、登録は `is_generated` を受け付けない（どちらも `id` は受け付けない） |
| `NOT_APPLICABLE_FIELDS`・`NOT_APPLICABLE_MESSAGES` | 定数 | カテゴリごとの、そのカテゴリにない項目（授業：`title`・`employer`、アルバイト：`subject_id`・`room`、その他：`subject_id`・`room`・`employer`）と、`null` 以外の値を指定したときのメッセージ |
| `CATEGORY_MESSAGE`・`END_TIME_ORDER_MESSAGE`・`GENERATED_DATE_MESSAGE`・`SUBJECT_NOT_FOUND_MESSAGE` | 定数 | カテゴリ・時刻の前後・自動生成の予定の日付・授業の存在のメッセージ |
| `event_to_dict` | 関数 | 変えない |
| `read_date_query` | 関数 | 変えない |
| `validate_event_values(payload, *, partial)` | 関数 | どのカテゴリにもある項目（日付・開始時刻・終了時刻・詳細／メモ）の検証。登録（`partial=False`）と編集（`partial=True`。本文にある項目だけ）で共通 |
| `validate_event_subject_id(payload)` | 関数 | 授業の予定の授業IDの検証（登録のときだけ）。必須・整数・1〜`MAX_ID`・存在する授業。規則とメッセージは、`routes/tasks.py` の課題の対象授業と同じ |
| `validate_category_fields(payload, category, *, partial)` | 関数 | カテゴリによって規則が変わる項目（授業ID・タイトル・教室・派遣会社）の検証。そのカテゴリにない項目は、項目がないか `null` だけを受け付ける。編集（`partial=True`）では、授業IDを検査しない（`validate_allowed_fields` が「この項目は指定できません」にする） |
| `get_events`・`get_event` | route | 変えない |
| `get_employers` | route | `GET /api/events/employers`。アルバイトの予定の、`null` でない派遣会社を、重複を除き、派遣会社ごとの最も大きい `id` の降順で返す |
| `create_event` | route | `POST`。下の順序 |
| `update_event` | route | `PATCH`。下の順序 |
| `delete_event` | route | `DELETE`。その行だけを削除する（自動生成の予定も） |

`create_event`（`POST`）の処理の順序：
1. 本文を読む（`read_json_object`）
2. カテゴリを検証する（`validate_required_choice`。許可値は `EVENT_CATEGORIES`）
3. 日付・時刻・詳細／メモを検証する（`validate_event_values(payload, partial=False)`）
4. 開始時刻・終了時刻の両方に誤りがなければ、終了が開始より後かを確かめる（同じ時刻も誤り。日付をまたぐ予定は、1件では登録できない）
5. カテゴリに誤りがなければ、カテゴリによって規則が変わる項目を検証する（`validate_category_fields(payload, category, partial=False)`）。カテゴリに誤りがあれば、検証しない
6. 受け付けない項目（`id`・`is_generated`・未知の項目）のエラー（`validate_allowed_fields(payload, CREATE_FIELDS)`）
7. 誤りがあれば、400で、まとめて返す（何も保存しない）
8. 授業の予定なら、タイトルに、授業の今の科目名を入れる（控え）
9. `is_generated=False` で作り、1回のcommit。201で、作成した予定を返す（そのカテゴリにない項目は `None`）

`update_event`（`PATCH`）の処理の順序：
1. 予定を取得する。なければ404（「予定が見つかりません」）。本文は読まない
2. 本文を読む（`read_patch_object`。`Content-Type`・JSON・オブジェクト・空の本文の検査）
3. 本文にある項目を検証する（`validate_event_values(payload, partial=True)`）
4. 自動生成の予定（`is_generated` が真）で、本文に `date` があれば、値によらず、`date` のエラーを `GENERATED_DATE_MESSAGE` にする（3の結果を上書きする）
5. 本文の時刻に誤りがなければ、変更後の値どうしで、終了が開始より後かを確かめる（本文にない時刻は、今の値。授業の `PATCH` と同じ）
6. カテゴリによって規則が変わる項目を、**今のカテゴリ**の規則で検証する（`validate_category_fields(payload, event.category, partial=True)`）
7. 受け付けない項目（`category`・`subject_id`・`is_generated`・`id`・未知の項目）のエラー（`validate_allowed_fields(payload, UPDATE_FIELDS)`）
8. 誤りがあれば、400で、まとめて返す（何も変えない）
9. 本文にあった項目だけを書き込み、1回のcommit。200で、更新後の予定を返す（`is_generated` は変えない）

注意：
- カテゴリの保存値の文字列（`"class"`・`"part_time"`・`"other"`）を、`events.py` に直接書かない。`app/categories.py` の定数を使う
- 「今日」を使わない（`date.today()`・`datetime.now()` を書かない）
- `PATCH`・`DELETE` のURLに、上限（`MAX_ID`）を超えるIDを指定すると、405になる（`GET` は404）。授業・課題と同じく、Flaskの仕組みによるもので、直さない（`docs/architecture.md` の「404の使い分け」の注意。テスト `test_over_limit_id_for_patch_and_delete_is_method_not_allowed`）
- `/employers` のrouteと、IDのroute（`<int(...):event_id>`）は、重ならない（`employers` は整数でないため）。`/api/events/employers` への `GET` 以外のメソッドは、405になる
- `validate_event_subject_id` は、`routes/tasks.py` の課題の対象授業の検査と同じ規則の、別の関数（学期の参照の検査が、`subjects.py` と `closures.py` に、それぞれあるのと同じ。DBを読むため、`api_helpers.py` には置かない）。`tasks.py` は変えない

### 1-2. `app/categories.py`（全文：付録B）
`EVENT_CATEGORIES` の前のコメントだけを直す（予定の登録で使うようになったため）。定数は変えない。`main` からの差分（確認用）：

```diff
--- a/app/categories.py
+++ b/app/categories.py
@@ -10,8 +10,7 @@ EVENT_CATEGORY_CLASS = "class"
 EVENT_CATEGORY_PART_TIME = "part_time"
 EVENT_CATEGORY_OTHER = "other"
 
-# 予定のAPIで category を受け付けるときの許可値（予定の登録・編集を
-# 作るタスクで使う）。
+# 予定のAPIで category を受け付けるときの許可値（予定の登録で使う）。
 EVENT_CATEGORIES = (
     EVENT_CATEGORY_CLASS,
     EVENT_CATEGORY_PART_TIME,
```

### 1-3. `tests/test_events_api.py`（全文：付録C）
`main` からの差分のうち、`make_event` の部分（確認用。末尾の派遣会社の候補のテストと、405のテストは、付録Cの全文を参照）：

```diff
--- a/tests/test_events_api.py
+++ b/tests/test_events_api.py
@@ -54,9 +54,11 @@ def make_event(
     category="other",
     subject_id=None,
     title="予定",
+    employer=None,
     is_generated=False,
 ):
-    """予定の行を、ORMで直接作る（予定を登録するAPIは、まだないため）。"""
+    """予定の行を、ORMで直接作る（自動生成の予定や、カテゴリにない項目を
+    持つ予定も作れるように、APIを使わない）。"""
     with app.app_context():
         event = Event(
             subject_id=subject_id,
@@ -65,6 +67,7 @@ def make_event(
             start_time=start_time,
             end_time=time(start_time.hour + 1, start_time.minute),
             title=title,
+            employer=employer,
             is_generated=is_generated,
         )
         db.session.add(event)
```

| 変えること | テスト | 件数 |
|---|---|---|
| 提供しない操作の405のテストから、提供するようになった3つ（`POST /api/events`、`PATCH /api/events/<id>`、`DELETE /api/events/<id>`）を外す。残るのは、`PUT`・`PATCH`・`DELETE /api/events` と、`POST`・`PUT /api/events/<id>` | `test_unsupported_event_methods_do_not_change_rows` | 8 → 5 |
| 派遣会社の候補：予定がなければ `[]` | `test_employer_list_is_empty_without_events` | 1（新規） |
| 派遣会社の候補：派遣会社のないアルバイトだけなら `[]` | `test_employer_list_is_empty_without_employers` | 1（新規） |
| 派遣会社の候補：重複を除き、新しく使った順（予定の日付の順ではない） | `test_employer_list_is_distinct_and_in_recent_order` | 1（新規） |
| 派遣会社の候補：アルバイトの予定の派遣会社だけ | `test_employer_list_uses_only_part_time_events` | 1（新規） |
| 派遣会社の候補：完全一致で比べる（大文字・小文字、全角・半角を区別） | `test_employer_list_compares_exact_strings` | 1（新規） |
| 派遣会社の候補：未知のクエリは無視する | `test_employer_list_ignores_unknown_query` | 1（新規） |
| 派遣会社の候補のURLは、`GET` だけ（ほかは405で、行は変わらない） | `test_employer_list_url_accepts_only_get` | 4（新規） |
| ファイルの合計 | | 47 → **54** |

ほかのテスト（一覧・1件取得）は変えない。

### 1-4. `tests/test_events_create_update_delete_api.py`（新規。全文：付録D）
- 学期（2026-04-01〜2026-07-31）と授業（月曜日 09:00〜10:00、「プログラミング基礎」、教室「3号館201」）を作る。自動生成の予定が要らないテストは、授業をORMで直接作る（予定は作らない）。自動生成の予定が要るテストは、授業をAPIで登録する（`create_subject_with_events`）
- 予定は、APIで登録する
- 変わっていないことは、すべての予定の値（`all_event_rows`）を、操作の前後で比べて確かめる
- 授業のrouteの「今日」を、2026-06-15（月）に固定する（`fixed_today`。授業全体の編集との関係のテストのため）。自動生成の予定の例には、今日より後の月曜日 2026-06-22（`FUTURE_MONDAY`）を使う

| 確かめること（`docs/architecture.md` の「予定API」「カレンダーからの授業の予定の操作」） | テスト | 件数 |
|---|---|---|
| 単発の授業の登録：201、すべての項目（タイトルは科目名、`is_generated` は偽） | `test_create_class_event_returns_event` | 1 |
| 単発の授業の登録：DBの行 | `test_create_class_event_saves_row` | 1 |
| アルバイトの登録：すべての項目 | `test_create_part_time_event_returns_event` | 1 |
| その他の登録：すべての項目 | `test_create_other_event_returns_event` | 1 |
| 任意の項目（教室・派遣会社・メモ）は省ける（`null`） | `test_create_optional_fields_can_be_omitted` | 3 |
| タイトルの前後の空白（全角を含む）を除き、空の任意の項目は `null` | `test_create_strips_strings_and_clears_blank_optional_fields` | 2 |
| 単発の授業のタイトルは、登録のときの科目名の控え（あとで科目名を変えても変わらない） | `test_create_class_title_is_subject_name_at_creation` | 1 |
| 日付の制限なし（過去、学期の期間の外、授業の曜日と違う日） | `test_create_class_event_accepts_any_date` | 4 |
| 休講日にも、単発の授業を登録できる | `test_create_class_event_on_closure_date_is_accepted` | 1 |
| 自動生成の予定と同じ日に、単発の授業を登録できる（並ぶ） | `test_create_class_event_beside_generated_event_is_accepted` | 1 |
| 時刻の制限なし（00:00〜23:59） | `test_create_accepts_times_outside_class_hours` | 1 |
| 文字数の上限（タイトル200字、派遣会社・教室100字）まで受け付ける | `test_create_accepts_maximum_lengths` | 4 |
| カテゴリの検証（必須、許可値・型、使用できない文字） | `test_create_category_is_validated` | 11 |
| 日付の検証 | `test_create_date_is_validated` | 11 |
| 開始時刻・終了時刻の検証 | `test_create_time_is_validated` | 14 |
| 終了は開始より後（同じ時刻、日付をまたぐ時刻も誤り） | `test_create_end_time_must_be_after_start_time` | 3 |
| 詳細／メモの検証 | `test_create_notes_is_validated` | 2 |
| 単発の授業の授業IDの検証（必須・型・範囲・存在） | `test_create_class_subject_id_is_validated` | 10 |
| アルバイト・その他のタイトルの検証 | `test_create_title_is_validated` | 14 |
| 教室（授業）・派遣会社（アルバイト）の検証 | `test_create_room_and_employer_are_validated` | 6 |
| そのカテゴリにない項目に `null` 以外（空文字を含む）を指定すると400 | `test_create_rejects_fields_not_for_category` | 12 |
| そのカテゴリにない項目の `null` は受け付ける | `test_create_accepts_null_for_fields_not_for_category` | 7 |
| カテゴリに誤りがあれば、カテゴリによって変わる項目は検証しない | `test_create_invalid_category_skips_category_fields` | 1 |
| `id`・`is_generated`・未知の項目は400 | `test_create_rejects_unknown_and_read_only_fields` | 4 |
| 誤りは、まとめて返す | `test_create_validation_errors_are_returned_together` | 1 |
| 検証の誤りでは、何も保存しない | `test_failed_create_saves_nothing` | 1 |
| 本文がオブジェクトでない（`null` を含む） | `test_create_non_object_payload_has_no_fields` | 5 |
| JSONが読めない・`Content-Type` が違う | `test_create_invalid_json_or_content_type_is_rejected` | 3 |
| 登録した予定は、一覧と1件取得で同じ形 | `test_created_event_is_in_list_and_get` | 1 |
| 編集：本文にある項目だけを変える | `test_patch_changes_only_given_fields` | 1 |
| 編集：アルバイトの、変えられる項目をすべて変える | `test_patch_part_time_can_change_all_editable_fields` | 1 |
| 編集：その他の、変えられる項目をすべて変える | `test_patch_other_can_change_all_editable_fields` | 1 |
| 編集：単発の授業は、日付・時刻・教室・メモを変えられる | `test_patch_one_off_class_event_can_change_date_time_room_and_notes` | 1 |
| 編集：自動生成の予定は、時刻・教室・メモを変えられ、`is_generated` は真のまま | `test_patch_generated_event_changes_time_room_notes_and_stays_generated` | 1 |
| 編集：自動生成の予定の日付は、値によらず400（何も変えない） | `test_patch_generated_event_rejects_date` | 4 |
| 編集：任意の項目を `null` にする | `test_patch_can_clear_optional_fields` | 7 |
| 編集：そのカテゴリにない項目の `null` は受け付ける（値は変わらない） | `test_patch_accepts_null_for_fields_not_for_category` | 5 |
| 編集：そのカテゴリにない項目に `null` 以外を指定すると400 | `test_patch_rejects_fields_not_for_category` | 6 |
| 編集：各項目の検証 | `test_patch_field_values_are_validated` | 20 |
| 編集：終了は開始より後（変更後の値どうし） | `test_patch_end_time_must_be_after_start_time_after_change` | 3 |
| 編集：前後が正しい時刻の変更は受け付ける | `test_patch_time_change_is_accepted_when_order_is_valid` | 1 |
| 編集：時刻に誤りがあれば、前後は比べない | `test_patch_invalid_start_time_skips_time_order_validation` | 1 |
| 編集：カテゴリ・授業ID・`is_generated`（同じ値・`null` を含む）・`id`・未知の項目は400 | `test_patch_rejects_category_subject_and_unknown_fields` | 8 |
| 編集：単発の授業の、同じ授業IDも400 | `test_patch_class_event_rejects_same_subject_id` | 1 |
| 編集：`{}` は400（`fields` なし） | `test_patch_empty_object_is_validation_error_without_fields` | 1 |
| 編集：誤りは、まとめて返す | `test_patch_validation_errors_are_returned_together` | 1 |
| 編集：検証の誤りでは、何も変えない | `test_failed_patch_changes_nothing` | 1 |
| 編集：その予定だけが変わる（同じ授業のほかの自動生成の予定も変わらない） | `test_patch_changes_only_that_event` | 1 |
| 編集：本文がオブジェクトでない | `test_patch_non_object_payload_has_no_fields` | 5 |
| 編集：JSONが読めない・`Content-Type` が違う | `test_patch_invalid_json_or_content_type_is_rejected` | 3 |
| 編集の404の使い分け | `test_patch_not_found_and_invalid_urls` | 5 |
| 編集：予定がなければ、本文を読む前に404 | `test_patch_missing_event_is_404_before_reading_body` | 1 |
| 削除：単発の予定は、その行だけを削除する | `test_delete_one_off_event_removes_only_that_event` | 1 |
| 削除：自動生成の予定も、その日の1件だけを削除できる | `test_delete_generated_event_removes_only_that_day` | 1 |
| 削除：授業・休講日・課題は残る | `test_delete_event_keeps_subject_closures_and_tasks` | 1 |
| 削除は本文を読まない | `test_delete_event_ignores_body` | 1 |
| 削除した予定を、もう一度削除すると404 | `test_deleted_event_cannot_be_deleted_again` | 1 |
| 削除の404の使い分け | `test_delete_not_found_and_invalid_urls` | 5 |
| 上限を超えるIDの `PATCH`・`DELETE` は405 | `test_over_limit_id_for_patch_and_delete_is_method_not_allowed` | 4 |
| 授業全体の編集で、単発の授業の予定は変わらない（タイトルも） | `test_one_off_class_event_is_kept_by_subject_patch` | 1 |
| 授業全体の編集で、編集した自動生成の予定（今日以降）は、設定どおりに作り直される | `test_edited_generated_event_is_rebuilt_by_subject_patch` | 1 |
| 授業全体の編集で、削除した自動生成の予定（今日以降）は戻る | `test_deleted_generated_event_is_restored_by_subject_patch` | 1 |
| 休講日の追加で、編集した自動生成の予定は削除され、単発の予定は残る | `test_closure_creation_deletes_edited_generated_event_only` | 1 |
| 休講日の削除で、削除していた自動生成の予定が作られる | `test_closure_deletion_restores_deleted_generated_event` | 1 |
| 授業の削除で、その授業の単発の予定は削除され、アルバイト・その他は残る | `test_subject_deletion_removes_its_one_off_events_only` | 1 |
| 登録・編集した派遣会社が、候補に反映される | `test_registered_and_edited_employers_are_candidates` | 1 |
| 合計 | | **227** |

## 変更してよい既存のテスト

| ファイル | 変えてよいこと | 変えないこと |
|---|---|---|
| `tests/test_events_api.py` | `make_event` の引数 `employer` と docstring、`test_unsupported_event_methods_do_not_change_rows` の組（8 → 5）、派遣会社の候補のテストの追加（付録Cの全文のとおり） | 一覧・1件取得のテスト（39件） |

- このタスクでの「既存のテスト」は、作業の開始時からあるすべてのテスト（787件）。上の1ファイルの、上に書いた部分を除き、変えない。**既存のテストが、想定外に失敗した場合**は、テストの期待値や、ほかの仕様を直さない。原因を調べ、そこで実装を止めて、チャットで報告する。特に、授業・休講日・課題・タスクのテスト（`test_subjects_api.py`・`test_subjects_update_delete_api.py`・`test_closures_api.py`・`test_tasks_api.py`）は、変えずに通ること

## 実装手順
1. ブランチ・作業ツリーの確認。設計資料が更新されていることを確認する（「Copilot確認手順」の1の `grep`）。更新されていなければ、何も変更せずに停止して報告する
2. 作業の前の状態を記録する：開発用DBの有無・ハッシュ・件数（「Copilot確認手順」の1。**`sqlite3` は `-readonly` を付ける**）。`python -m pytest -q` が787件、すべて合格すること（合格しなければ、何も変更せずに停止して報告する）
3. **（段階1）** 「全文からファイルを作るスクリプト」を `python - 1` で実行する。`python -m pytest -q` が1021件、すべて合格すること。「全文との比較」（「Copilot確認手順」の4）を `python - 1` で実行し、4ファイルとも「一致」
4. 「Copilot確認手順」の2・3・5・6を実施する
5. 結果を報告して、応答を終える（コマンドの出力は、要約せずに、そのまま貼る。サーバーを起動していないこと、`curl` での確認をしていないことを明記する）

段階の終わりに、`python -m pytest -q` の結果（件数・警告）と、全文との比較の結果を控えておく（最終報告に、出力をそのまま貼る）。

## 完了条件
- `python -m pytest -q` が、作業の前に **787件**、段階1の終わりに **1021件**、すべて合格する（失敗・エラー・スキップが0件）
- 変更・追加したファイルが、「実装対象ファイル」の4つだけ
- 4ファイルが、このTask MDの全文と1文字も違わない（「Copilot確認手順」の4が、4ファイルとも「一致」）
- `app/`・`tests/`・`run.py` のPythonのファイルに、79文字を超える行がない
- 「Copilot確認手順」の5（検索と差分）が、期待どおり
- 実施の前後で、開発用DB（`instance/app.db`）のハッシュと、`semesters`・`subjects`・`closures`・`events`・`tasks` の件数が同じ
- 「Komaの確認」が、期待どおり
- レビューで承認される

## Copilot確認手順
**`sqlite3` は、必ず `-readonly` を付けて実行する**（011-L1）。**それぞれのコマンドの出力を、要約せずに、そのまま報告に貼る**（014-L1）。**コマンドは、書いてあるとおりに実行する（書き換えた場合は、報告に書く。016-N1・017-N1）。**

```
# 1. 実施前
git branch --show-current      # feature/019-event-create-edit-delete-api
git status                     # 変更なし
grep -n -F "#### カレンダーからの授業の予定の操作" docs/architecture.md   # 1件
grep -n -F -e "GET /api/events/employers" docs/architecture.md        # 3件以上
grep -n -F -e "| 日付をまたぐアルバイト |" -e "| カレンダーからの授業の予定の操作と" docs/architecture.md   # 出力なし（未決定事項から外れている）
grep -n -F "日付をまたぐ予定" docs/requirements.md                    # 1件
grep -n -F "止まる場面の応答" .github/copilot-instructions.md          # 数件
ls -l instance/app.db          # 存在すること（なければ、何も変更せずに停止して報告する）
shasum -a 256 instance/app.db
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"
python -m pytest -q            # 787 passed

# 2. 段階の終わり
python -m pytest -q            # 1021 passed
python -m pytest -q --co tests/test_events_api.py | tail -1                     # 54 tests collected
python -m pytest -q --co tests/test_events_create_update_delete_api.py | tail -1 # 227 tests collected
python -m pytest -q --co tests/test_subjects_update_delete_api.py | tail -1     # 86 tests collected（変わらない）
python -m pytest -q --co tests/test_tasks_api.py | tail -1                      # 161 tests collected（変わらない）

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

# 4. 全文との比較（011-N1・013-N1）。段階1の終わりに「python - 1」
python - 1 <<'EOF'
import difflib
import sys
from pathlib import Path

# 段階ごとのファイル（「全文からファイルを作るスクリプト」と同じ）。
STAGE_FILES = {
    "1": [
        "app/routes/events.py",
        "app/categories.py",
        "tests/test_events_api.py",
        "tests/test_events_create_update_delete_api.py",
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
expected_files = read_full_texts(
    "docs/tasks/019_event_create_edit_delete_api.md"
)
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

# 5. 検索と差分（段階1の終わり。各コマンドの前の echo の見出しも、出力として貼る。018-N1）
echo "== 5-1 カテゴリの保存値の文字列（7件：categories.py の定数5件と説明1件、class_events.py のコメント1件。events.py にはない）"
grep -rn -F --include="*.py" -e '"class"' -e '"part_time"' -e '"assignment"' -e '"other"' app/
echo "== 5-2 予定のroute（6件：get・get・get（employers）・post・patch・delete の順）"
grep -n -F "@events_bp." app/routes/events.py
echo "== 5-3 commit（3件：登録・編集・削除で1回ずつ）"
grep -n -F "commit()" app/routes/events.py
echo "== 5-4 is_generated を書き込む場所（1件：登録の Event(...)。編集では変えない）"
grep -n -F "is_generated=" app/routes/events.py
echo "== 5-5 read_patch_object の呼び出し（4件：api_helpers.py の定義、subjects.py・events.py・tasks.py の呼び出し）"
grep -rn -F --include="*.py" "read_patch_object()" app/
echo "== 5-6 今日（1件：subjects.py の current_date の中だけ）"
grep -rn -F --include="*.py" -e "date.today" -e "datetime.now" app/
echo "== 5-7 削除の連動（出力なし）"
grep -rn -F --include="*.py" -e "cascade" -e "ondelete" app/
echo "== 5-8 変更したファイルの行数（3行：1 2 app/categories.py、389 0 app/routes/events.py、72 4 tests/test_events_api.py）"
git diff --numstat app/categories.py app/routes/events.py tests/test_events_api.py
echo "== 5-9 新しいテストのファイルの行数（1545）"
wc -l tests/test_events_create_update_delete_api.py
echo "== 5-10 変えないファイル（出力なし）"
git diff --stat -- app/models/ app/__init__.py app/api_helpers.py app/class_events.py app/routes/semesters.py app/routes/subjects.py app/routes/closures.py app/routes/tasks.py app/routes/main.py app/static/ app/templates/ migrations/ tests/conftest.py tests/test_api_helpers.py tests/test_class_events.py tests/test_closures_api.py tests/test_semesters_api.py tests/test_setup.py tests/test_subjects_api.py tests/test_subjects_update_delete_api.py tests/test_tasks_api.py requirements.txt pytest.ini run.py

# 6. 実施後
shasum -a 256 instance/app.db  # 実施前と同じ
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"   # 実施前と同じ
git status                     # 変更：3つ。新規：1つ
git diff --stat
```

| 確認 | 期待する結果 |
|---|---|
| `python -m pytest -q` | 実施前787件、段階1の終わり1021件が、すべて合格。失敗・エラー・スキップが0件。`migrations/env.py` の `DeprecationWarning` は、出ても構わない（報告する） |
| テストの件数（2） | 上のコメントのとおり（54・227・86・161） |
| 1行の長さ（3） | 出力なし |
| 全文との比較（4） | `全文の数：4` と、4ファイルとも「一致」。「不一致」が出たら、手で直さず、「全文からファイルを作るスクリプト」をもう一度実行して全文に戻し、2からやり直す（戻したことを報告する）。Task MDの全文のほうを変える必要があると判断した場合は、停止して報告する |
| 検索と差分（5） | 各見出しの括弧の中のとおり（件数が違う場合は、その見出しと出力を報告に書く） |
| 開発用DB | 実施の前後で、ハッシュと、5つのテーブルの件数が同じ |
| `git status` | 変更：`app/categories.py`、`app/routes/events.py`、`tests/test_events_api.py`。新規（`??`）：`tests/test_events_create_update_delete_api.py`。`app/models/`・`migrations/`・`app/static/`・`app/templates/`・`docs/`・`.github/`・`requirements.txt`・`run.py`・`instance/` に変更なし |

`.pytest_cache/` や `__pycache__/` が `git status` に表示される場合は、`.gitignore` を変更せず、報告する。**Copilotは、サーバーを起動せず、`curl` での確認もしない。** 報告に、そのことを明記する。

## Komaの確認
順序：（1）pytest →（2）commit・push とレビューの依頼 →（3）APIの確認（確認用のサーバー）→（4）マージ。**ブラウザでの確認は、このタスクにはない**（画面を変えないため。roadmap の「進め方の決定の記録」、2026-10-11）。

### 1. pytest
`python -m pytest -q` を自分で実行し、**1021件、すべて合格**することを確かめる。

### 2. push とレビューの依頼
featureブランチを commit・push する（PRを作ってもよい）。Copilotの完了報告を共有して、Claudeにレビューを頼む。**pushは、マージではない。レビューの承認の前に、マージしない。** 修正が必要になった場合は、同じブランチでCopilotが直し、もう一度pushしてレビューを受ける。

### 3. APIの確認（確認用のサーバー）
レビューで「承認可能」になったあとに行う。**開発用DBは使わない。** 確認用のDB（`/tmp/schedule-app-check-019/check.db`）を、migrationで作り、そのDBで起動した確認用のサーバーに、`curl` で要求する（Task 012・014・016と同じ方法）。開発用DBには、何も残らない。予定APIは「今日」を使わず、確認の中で授業全体の編集（「今日」を使う）もしないため、結果は、確認する日によらない。

#### 準備
1. `python run.py` が起動していれば、Ctrl＋Cで止める（確認用のサーバーも、5001番を使うため）。開発用DBのハッシュを控える
   ```
   shasum -a 256 instance/app.db
   ```
2. ブランチ `feature/019-event-create-edit-delete-api` のまま、リポジトリのルートで、`.venv` を有効にして、次を実行する（行の先頭に空白を入れずにコピーする。このターミナルは、確認の間、開いたままにする）

```
python - <<'EOF'
from pathlib import Path

from flask_migrate import upgrade

from app import create_app

# 確認用のDB（開発用DBとは別のファイル）。止めて起動し直しても、残る。
check_directory = Path("/tmp/schedule-app-check-019")
check_directory.mkdir(exist_ok=True)
database_path = check_directory / "check.db"
app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"})
with app.app_context():
    upgrade(directory="migrations")
print(f"確認用のDB：{database_path}", flush=True)
app.run(host="127.0.0.1", port=5001, debug=False)
EOF
```

期待する出力：`Running upgrade  -> 0280f6cf8d09, initial tables` と `Running upgrade 0280f6cf8d09 -> 42bd53808fa1, add closures table`、「確認用のDB：/tmp/schedule-app-check-019/check.db」、`Running on http://127.0.0.1:5001`。

3. 別のターミナルを開き、リポジトリのルートで、`.venv` を有効にして、`BASE=http://127.0.0.1:5001` を実行しておく

#### 確認（別のターミナルで、上から順に実行する）
C1・C2は、確認用のDBに、学期と、月曜日の授業を1件ずつ登録する（授業の自動生成の予定が19件でき、IDは1〜19。10/19がID 5、10/26がID 6、11/2がID 7）。予定のIDは、C3から20、21、22…と続く。

```
# C1. 学期（2026-09-21〜2027-01-29）
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X POST $BASE/api/semesters -H 'Content-Type: application/json' -d '{"name": "2026年度 後期", "start_date": "2026-09-21", "end_date": "2027-01-29"}'
# C2. 月曜日の授業（自動生成の予定が19件できる）
curl -s -X POST $BASE/api/subjects -H 'Content-Type: application/json' -d '{"semester_id": 1, "subject_name": "テスト：月曜1限", "room": "テスト：3号館201", "weekday": 0, "start_time": "09:00", "end_time": "10:30"}' | python -c 'import json, sys; print(json.load(sys.stdin)["generated_event_count"])'
# C3. 単発の授業（土曜日の補講）の登録
curl -s -X POST $BASE/api/events -H 'Content-Type: application/json' -d '{"category": "class", "subject_id": 1, "date": "2026-10-24", "start_time": "15:00", "end_time": "16:30", "room": "テスト：5号館101", "notes": "補講"}' | python -m json.tool --no-ensure-ascii
# C4. アルバイトの登録
curl -s -X POST $BASE/api/events -H 'Content-Type: application/json' -d '{"category": "part_time", "date": "2026-10-24", "start_time": "17:00", "end_time": "21:00", "title": "テスト：倉庫の仕分け", "employer": "テスト派遣A"}' | python -m json.tool --no-ensure-ascii
# C5. その他（時間指定あり）の登録
curl -s -X POST $BASE/api/events -H 'Content-Type: application/json' -d '{"category": "other", "date": "2026-10-25", "start_time": "10:00", "end_time": "12:00", "title": "テスト：歯医者"}' | python -m json.tool --no-ensure-ascii
# C6. その週の一覧（ID・日付・開始時刻・カテゴリ・自動生成かを表示する）
curl -s "$BASE/api/events?start_date=2026-10-19&end_date=2026-10-25" | python -c 'import json, sys; [print(e["id"], e["date"], e["start_time"], e["category"], e["is_generated"]) for e in json.load(sys.stdin)]'
# C7. 自動生成の予定（10/26）を、その日だけ編集する
curl -s -X PATCH $BASE/api/events/6 -H 'Content-Type: application/json' -d '{"room": "テスト：3号館301", "start_time": "10:40", "end_time": "12:10"}' | python -m json.tool --no-ensure-ascii
# C8. 自動生成の予定の日付は、変えられない
curl -s -X PATCH $BASE/api/events/6 -H 'Content-Type: application/json' -d '{"date": "2026-10-27"}' | python -m json.tool --no-ensure-ascii
# C9. 単発の予定は、日付も変えられる（アルバイトを10/31に移し、派遣会社も変える）
curl -s -X PATCH $BASE/api/events/21 -H 'Content-Type: application/json' -d '{"date": "2026-10-31", "employer": "テスト派遣B"}' | python -m json.tool --no-ensure-ascii
# C10. 日付をまたぐ時刻（22:00〜2:00）は、1件では登録できない
curl -s -X POST $BASE/api/events -H 'Content-Type: application/json' -d '{"category": "part_time", "date": "2026-10-30", "start_time": "22:00", "end_time": "02:00", "title": "テスト：夜勤"}' | python -m json.tool --no-ensure-ascii
# C11. アルバイトに教室は指定できない
curl -s -X POST $BASE/api/events -H 'Content-Type: application/json' -d '{"category": "part_time", "date": "2026-10-30", "start_time": "17:00", "end_time": "21:00", "title": "テスト：倉庫の仕分け", "room": "3号館201"}' | python -m json.tool --no-ensure-ascii
# C12. 授業の予定にタイトルは指定できない
curl -s -X POST $BASE/api/events -H 'Content-Type: application/json' -d '{"category": "class", "subject_id": 1, "date": "2026-10-31", "start_time": "15:00", "end_time": "16:30", "title": "補講"}' | python -m json.tool --no-ensure-ascii
# C13. カテゴリは変えられない
curl -s -X PATCH $BASE/api/events/22 -H 'Content-Type: application/json' -d '{"category": "part_time"}' | python -m json.tool --no-ensure-ascii
# C14. 派遣会社の候補（アルバイトをもう1件登録してから、候補を取得する。2つのコマンド）
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X POST $BASE/api/events -H 'Content-Type: application/json' -d '{"category": "part_time", "date": "2026-11-07", "start_time": "09:00", "end_time": "17:00", "title": "テスト：棚卸し", "employer": "テスト派遣A"}'
curl -s $BASE/api/events/employers | python -c 'import json, sys; print(json.load(sys.stdin))'
# C15. 自動生成の予定（11/2）の削除と、削除のあとの1件取得（2つのコマンド）
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X DELETE $BASE/api/events/7
curl -s $BASE/api/events/7 | python -m json.tool --no-ensure-ascii
# C16. 授業の1件取得（予定の件数）
curl -s $BASE/api/subjects/1 | python -c 'import json, sys; subject = json.load(sys.stdin); print(subject["event_count"], subject["task_count"])'
# C17. 10/26 を休講日にすると、編集した自動生成の予定は消え、単発の予定は残る（2つのコマンド）
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X POST $BASE/api/closures -H 'Content-Type: application/json' -d '{"semester_id": 1, "date": "2026-10-26"}'
curl -s "$BASE/api/events?start_date=2026-10-24&end_date=2026-10-26" | python -c 'import json, sys; print([e["id"] for e in json.load(sys.stdin)])'
# C18. 授業を削除すると、単発の授業の予定も消え、アルバイト・その他は残る（2つのコマンド）
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X DELETE $BASE/api/subjects/1
curl -s "$BASE/api/events?start_date=2026-09-01&end_date=2027-01-31" | python -c 'import json, sys; print([e["id"] for e in json.load(sys.stdin)])'
```

| No | 期待する結果 |
|---|---|
| C1 | `HTTP 201` |
| C2 | `19`（自動生成の予定の件数） |
| C3 | `"id": 20`、`"category": "class"`、`"subject_id": 1`、`"title": "テスト：月曜1限"`（授業の科目名）、`"date": "2026-10-24"`、`"start_time": "15:00"`、`"end_time": "16:30"`、`"room": "テスト：5号館101"`、`"employer": null`、`"notes": "補講"`、`"is_generated": false` |
| C4 | `"id": 21`、`"category": "part_time"`、`"subject_id": null`、`"title": "テスト：倉庫の仕分け"`、`"employer": "テスト派遣A"`、`"room": null`、`"notes": null`、`"is_generated": false` |
| C5 | `"id": 22`、`"category": "other"`、`"title": "テスト：歯医者"`、`"subject_id": null`、`"room": null`、`"employer": null`、`"is_generated": false` |
| C6 | 4行：`5 2026-10-19 09:00 class True`、`20 2026-10-24 15:00 class False`、`21 2026-10-24 17:00 part_time False`、`22 2026-10-25 10:00 other False` |
| C7 | `"id": 6`、`"date": "2026-10-26"`（変わらない）、`"start_time": "10:40"`、`"end_time": "12:10"`、`"room": "テスト：3号館301"`、`"title": "テスト：月曜1限"`、`"is_generated": true`（自動生成のまま） |
| C8 | `validation_error`、`fields` に `"date": "自動生成の授業の予定は、日付を変えられません（別の日に移すときは、この予定を削除して、移す先の日に単発の授業を追加してください）"` だけ |
| C9 | `"id": 21`、`"date": "2026-10-31"`、`"employer": "テスト派遣B"`（ほかの項目は、C4と同じ） |
| C10 | `validation_error`、`fields` に `"end_time": "終了時刻は開始時刻より後にしてください"` だけ |
| C11 | `validation_error`、`fields` に `"room": "教室は、授業の予定にだけ指定できます"` だけ |
| C12 | `validation_error`、`fields` に `"title": "授業の予定には、タイトルを指定できません（授業の科目名になります）"` だけ |
| C13 | `validation_error`、`fields` に `"category": "この項目は指定できません"` だけ |
| C14 | 1つ目：`HTTP 201`。2つ目：`['テスト派遣A', 'テスト派遣B']`（新しく使った順。テスト派遣Aは、いま登録した ID 23 の予定が持つ） |
| C15 | 1つ目：`HTTP 204`。2つ目：`not_found`、`"message": "予定が見つかりません"` |
| C16 | `19 0`（予定19件＝自動生成19件 − 削除1件 ＋ 単発の授業1件。課題0件） |
| C17 | 1つ目：`HTTP 201`。2つ目：`[20, 22]`（10/26の自動生成の予定（C7で編集したもの）は、休講日の追加で削除された。10/24の単発の授業は残る。アルバイトは、C9で10/31に移した） |
| C18 | 1つ目：`HTTP 204`。2つ目：`[22, 21, 23]`（授業の予定は、自動生成も単発も削除された。その他（10/25）・アルバイト（10/31・11/7）は残る） |

（JSONの応答は、Flaskが項目名の順に並べて返すため、表示の順は、設計資料の例と違う。中身が同じなら、期待どおり）

#### 後片付け
1. 確認用のサーバーを止める（Ctrl＋C）
2. 確認用のDBのフォルダを消す
   ```
   rm -r /tmp/schedule-app-check-019
   ```
3. 開発用DBのハッシュが、準備の1と同じことを確かめる
   ```
   shasum -a 256 instance/app.db
   ```

ハッシュが変わっていた場合は、開発用DBを操作せずに、Claudeに伝える。

### 4. マージ
1〜3が期待どおりで、レビューで承認されたら、マージする。このタスクは、DBの構造を変えないため、開発用DBへのmigrationの適用はない。開発用DBのデータも変えないため、バックアップは要らない。

マージのあとは、開発用DBのサーバー（`python run.py`）でも、予定の登録・編集・削除のAPIが使える。画面はまだないため、開発用DBの予定を、APIで登録・編集・削除する場合は、先にバックアップを取る（`docs/architecture.md` の「開発中の注意」）。

## Git操作
**Git commit / push / ブランチ操作 / マージは行わない**（`git branch --show-current`、`git status`、`git diff` のような読み取りだけのコマンドは除く）。

## 注意
- **停止して報告する条件**（ファイルを変更せず、実装を止め、チャットで「問題点・発生理由・変更した場合の影響・推奨案（必要なら）」を報告する）
  - ブランチの不一致、作業ツリーの想定外の変更
  - 設計資料が更新されていない（実装手順の1）、または、設計資料とこのTask MDの間に、矛盾・不足がある
  - 設計資料にない判断が必要になった（特に、`docs/architecture.md` の「未決定事項」に触れる場合）
  - 「全文からファイルを作るスクリプト」の出力が、期待と違う（全文の数・行数・エラー）
  - 「変更しない」と定めたもの（モデル、ほかのroute、`api_helpers.py`、画面のファイル、既存のテストなど）を変更しないと実装できない。または、4ファイルの全文を変える必要があると判断した
  - 開発用DB（`instance/app.db`）がない
  - 作業の前の `python -m pytest` が、787件すべて合格しない
  - **既存のテスト**（作業の開始時からある787件。「変更してよい既存のテスト」の部分を除く）**が、想定外に失敗した**。テストの期待値や、ほかの仕様を直さずに、原因を調べて報告する
  - DBの構造の変更（migration）や、モデルの変更、ライブラリの追加、このTask MDに書いたもの以外のAPIの変更が必要だと判断した
  - 実施の前後で、`instance/app.db` が変わった
- **止まるときは、報告を書いて、その応答を終える。質問の機能は使わない。** 再開するのは、Komaの新しいメッセージが、判断や再開を明確に示したときだけ（無回答や「続けて」だけの返事は、再開の指示ではない）。`.github/copilot-instructions.md` の「止まる場面の応答」
- **開発用DBを `sqlite3` で開くときは、必ず `-readonly` を付ける**（SELECTだけでも、付けずに開かない。011-L1）。`flask db` のコマンドを、一切実行しない。ライブラリを追加しない。サーバーを起動しない（`python run.py` も、「Komaの確認」の確認用のサーバーも）
- 期待する結果と異なる結果が出た場合は、確認を飛ばさず、原因を直してから、すべての確認をやり直す（ただし、既存のテストの想定外の失敗は、上の停止の条件に従う。全文との「不一致」は、手で直さず、スクリプトで全文に戻す）
- 設計資料に書かれていない仕様は、自分で決めない
- **最後の報告には、次を含め、コマンドの出力は、要約せずに、そのまま貼る**（014-L1）：変更・追加したファイル、「全文からファイルを作るスクリプト」の出力、作業の前と段階1の終わりの `pytest` の件数と警告（最後の行）、テストの件数の確認（「Copilot確認手順」の2の `--co`）の出力、1行の長さの確認の出力、全文との比較の出力（4ファイルの「一致」。スクリプトで全文に戻した場合は、そのこと）、検索と差分の出力（`echo` の見出しの行も含めて、そのまま。018-N1）、開発用DBの前後のハッシュ・件数、`git status`・`git diff --stat` の出力、コマンドを書き換えたかどうか（書き換えていなければ「書き換えなし」）、サーバーの起動と `curl` の確認をしていないこと、気になった点

## 付録：全文
「全文からファイルを作るスクリプト」と「全文との比較」が使う。各ファイルの全文は、「`<!-- 全文: パス -->`」の印の直後のコードブロック。**この付録を、手で書き写さない。** 本文の要点・差分と食い違う場合は、作業をせずに停止して報告する。

### 付録A. `app/routes/events.py`

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
    read_json_object,
    read_patch_object,
    validate_allowed_fields,
    validate_optional_string,
    validate_required_choice,
    validate_required_date,
    validate_required_integer,
    validate_required_string,
    validate_required_time,
)
from app.categories import (
    EVENT_CATEGORIES,
    EVENT_CATEGORY_CLASS,
    EVENT_CATEGORY_OTHER,
    EVENT_CATEGORY_PART_TIME,
)
from app.extensions import db
from app.models.event import Event
from app.models.subject import Subject


events_bp = Blueprint(
    "events",
    __name__,
    url_prefix="/api/events",
)

# 予定の編集（PATCH）で受け付ける項目。カテゴリ（category）と授業
# （subject_id）は、登録のあとで変えられない（誤った場合は、削除して
# 登録し直す）。
UPDATE_FIELDS = {
    "date",
    "start_time",
    "end_time",
    "title",
    "room",
    "employer",
    "notes",
}
# 予定の登録（POST）で受け付ける項目。is_generated は受け付けない
# （登録した予定は、常に単発の予定）。
CREATE_FIELDS = UPDATE_FIELDS | {"category", "subject_id"}

# カテゴリごとの、そのカテゴリにない項目（項目がないか、null だけを
# 受け付ける）。
NOT_APPLICABLE_FIELDS = {
    EVENT_CATEGORY_CLASS: ("title", "employer"),
    EVENT_CATEGORY_PART_TIME: ("subject_id", "room"),
    EVENT_CATEGORY_OTHER: ("subject_id", "room", "employer"),
}
# そのカテゴリにない項目に、null 以外の値を指定したときのメッセージ。
NOT_APPLICABLE_MESSAGES = {
    "subject_id": "授業IDは、授業の予定にだけ指定できます",
    "title": (
        "授業の予定には、タイトルを指定できません（授業の科目名になります）"
    ),
    "room": "教室は、授業の予定にだけ指定できます",
    "employer": "派遣会社は、アルバイトの予定にだけ指定できます",
}

CATEGORY_MESSAGE = (
    "カテゴリは「class」「part_time」「other」のどれかで指定してください"
)
END_TIME_ORDER_MESSAGE = "終了時刻は開始時刻より後にしてください"
GENERATED_DATE_MESSAGE = (
    "自動生成の授業の予定は、日付を変えられません（別の日に移すときは、"
    "この予定を削除して、移す先の日に単発の授業を追加してください）"
)
SUBJECT_NOT_FOUND_MESSAGE = "指定された授業が存在しません"


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


def validate_event_values(
    payload: dict[str, Any],
    *,
    partial: bool,
) -> tuple[dict[str, Any], dict[str, str]]:
    """予定の項目（日付・開始時刻・終了時刻・詳細／メモ）を検査する。

    どのカテゴリにもある項目で、登録（POST）と編集（PATCH）で、同じ規則で
    検査するために使う。
    - partial=False（登録）：4つの項目を検査する。必須の項目が本文に
      なければ、必須のエラーにする
    - partial=True（編集）：本文に含まれる項目だけを検査する
    戻り値は、（値、エラー）の組。値は、誤りのない項目だけを入れる
    （キーは、Eventの列の名前と同じ）。開始時刻と終了時刻の前後の検査は、
    呼び出し側が行う（編集では、今の値と組み合わせて比べるため）。
    """
    values: dict[str, Any] = {}
    errors: dict[str, str] = {}

    if not partial or "date" in payload:
        event_date, error = validate_required_date(
            payload,
            "date",
            "日付は必須です",
            "日付は実在する日付を「YYYY-MM-DD」の形式で指定してください",
        )
        if error is None:
            values["date"] = event_date
        else:
            errors["date"] = error

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


def validate_event_subject_id(
    payload: dict[str, Any],
) -> tuple[int | None, str | None]:
    """授業の予定の授業ID（subject_id）を検査する（登録のときだけ）。

    必須。整数で、その授業が存在すること。規則とメッセージは、課題の
    対象授業（routes/tasks.py）と同じ。DBを読むため、api_helpers.py には
    置かない。
    """
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
        return None, SUBJECT_NOT_FOUND_MESSAGE
    if db.session.get(Subject, subject_id) is None:
        return None, SUBJECT_NOT_FOUND_MESSAGE
    return subject_id, None


def validate_category_fields(
    payload: dict[str, Any],
    category: str,
    *,
    partial: bool,
) -> tuple[dict[str, Any], dict[str, str]]:
    """カテゴリによって規則が変わる項目を、そのカテゴリの規則で検査する。

    対象は、授業ID（subject_id）・タイトル（title）・教室（room）・
    派遣会社（employer）。
    - 授業：授業IDは必須、教室は任意。タイトル・派遣会社は指定できない
    - アルバイト：タイトルは必須、派遣会社は任意。授業ID・教室は
      指定できない
    - その他：タイトルは必須。授業ID・教室・派遣会社は指定できない
    指定できない項目は、項目がないか、null だけを受け付ける。
    - partial=False（登録）：上の項目を、すべて検査する
    - partial=True（編集）：本文に含まれる項目だけを検査する。授業IDは
      検査しない（編集では、値によらず受け付けないため。呼び出し側の
      validate_allowed_fields が誤りにする）
    戻り値は、（値、エラー）の組（validate_event_values と同じ形）。
    """
    values: dict[str, Any] = {}
    errors: dict[str, str] = {}

    if category == EVENT_CATEGORY_CLASS:
        if not partial:
            subject_id, error = validate_event_subject_id(payload)
            if error is None:
                values["subject_id"] = subject_id
            else:
                errors["subject_id"] = error

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
    else:
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

    if category == EVENT_CATEGORY_PART_TIME and (
        not partial or "employer" in payload
    ):
        employer, error = validate_optional_string(
            payload,
            "employer",
            "派遣会社は文字列で指定してください",
            max_length=100,
            length_message="派遣会社は100文字以内にしてください",
        )
        if error is None:
            values["employer"] = employer
        else:
            errors["employer"] = error

    # そのカテゴリにない項目は、項目がないか、null だけを受け付ける
    # （null は、値を変えない）。値の中身は見ない。
    for field_name in NOT_APPLICABLE_FIELDS[category]:
        if partial and field_name == "subject_id":
            continue
        if payload.get(field_name) is not None:
            errors[field_name] = NOT_APPLICABLE_MESSAGES[field_name]

    return values, errors


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


@events_bp.get("/employers")
def get_employers():
    """アルバイトの派遣会社の入力候補を、新しく使った順に返す。

    派遣会社ごとに、その派遣会社を持つ予定の最も大きいid（最も新しく
    登録した予定）で並べる。重複は、文字列の完全一致で除く。
    """
    statement = (
        db.select(Event.employer)
        .where(
            Event.category == EVENT_CATEGORY_PART_TIME,
            Event.employer.is_not(None),
        )
        .group_by(Event.employer)
        .order_by(db.func.max(Event.id).desc())
    )
    employers = db.session.scalars(statement).all()
    return jsonify(list(employers))


@events_bp.post("")
def create_event():
    payload, error_response = read_json_object()
    if error_response is not None:
        return error_response

    fields: dict[str, str] = {}

    category, category_error = validate_required_choice(
        payload,
        "category",
        EVENT_CATEGORIES,
        "カテゴリは必須です",
        CATEGORY_MESSAGE,
    )
    if category_error is not None:
        fields["category"] = category_error

    values, value_errors = validate_event_values(payload, partial=False)
    fields.update(value_errors)

    start_time = values.get("start_time")
    end_time = values.get("end_time")
    # 前後の検査は、開始時刻と終了時刻の両方に誤りがないときだけ行う。
    # 日付をまたぐ予定（終了が開始より前）は、1件では登録できない。
    if (
        start_time is not None
        and end_time is not None
        and end_time <= start_time
    ):
        fields["end_time"] = END_TIME_ORDER_MESSAGE

    # カテゴリによって規則が変わる項目は、カテゴリに誤りがないときだけ
    # 検査する。
    if category is not None:
        category_values, category_errors = validate_category_fields(
            payload, category, partial=False
        )
        values.update(category_values)
        fields.update(category_errors)

    fields.update(validate_allowed_fields(payload, CREATE_FIELDS))

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    if category == EVENT_CATEGORY_CLASS:
        # 授業の予定のタイトルは、授業の科目名の控え（指定できない）。
        subject = db.session.get(Subject, values["subject_id"])
        values["title"] = subject.subject_name

    # values のキーは、Eventの列の名前と同じ。そのカテゴリにない項目
    # （授業ID・教室・派遣会社）は、values になく、None のまま。
    event = Event(category=category, is_generated=False, **values)
    db.session.add(event)
    db.session.commit()
    return jsonify(event_to_dict(event)), 201


@events_bp.patch(f"/<int(max={MAX_ID}):event_id>")
def update_event(event_id: int):
    # 対象の予定がなければ、本文を読む前に404にする。
    event = db.session.get(Event, event_id)
    if event is None:
        return api_error_response("not_found", "予定が見つかりません")

    # 項目が1つもない本文（{}）も、誤りにする（API共通ルール）。
    payload, error_response = read_patch_object()
    if error_response is not None:
        return error_response

    values, fields = validate_event_values(payload, partial=True)

    # 自動生成の授業の予定は、日付を変えられない（値によらず誤り）。
    # 休講日の同期と、授業全体の編集による作り直しが、自動生成の予定は
    # 授業の曜日の日にあることを前提にしているため。
    if event.is_generated and "date" in payload:
        values.pop("date", None)
        fields["date"] = GENERATED_DATE_MESSAGE

    # 前後の検査は、変更後の値どうしで行う。本文に含まれない時刻は、
    # 今の値を使う。本文の時刻に誤りがあれば、検査しない。
    if "start_time" not in fields and "end_time" not in fields:
        start_time = values.get("start_time", event.start_time)
        end_time = values.get("end_time", event.end_time)
        if end_time <= start_time:
            fields["end_time"] = END_TIME_ORDER_MESSAGE

    # カテゴリによって規則が変わる項目は、今のカテゴリ（変えられない）の
    # 規則で検査する。
    category_values, category_errors = validate_category_fields(
        payload, event.category, partial=True
    )
    values.update(category_values)
    fields.update(category_errors)

    fields.update(validate_allowed_fields(payload, UPDATE_FIELDS))

    if fields:
        return api_error_response(
            "validation_error",
            "入力内容に誤りがあります",
            fields,
        )

    # 本文に含まれていた項目だけを、予定に書き込む（values のキーは、
    # Eventの列の名前と同じ）。is_generated は変えない。
    for field_name, value in values.items():
        setattr(event, field_name, value)
    db.session.commit()
    return jsonify(event_to_dict(event))


@events_bp.delete(f"/<int(max={MAX_ID}):event_id>")
def delete_event(event_id: int):
    event = db.session.get(Event, event_id)
    if event is None:
        return api_error_response("not_found", "予定が見つかりません")

    # 予定は、子の行を持たないため、この行だけを削除する。自動生成の
    # 予定も削除できる（削除したことは記録しない）。
    db.session.delete(event)
    db.session.commit()
    return "", 204
```

### 付録B. `app/categories.py`

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

# 予定のAPIで category を受け付けるときの許可値（予定の登録で使う）。
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

### 付録C. `tests/test_events_api.py`

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
    employer=None,
    is_generated=False,
):
    """予定の行を、ORMで直接作る（自動生成の予定や、カテゴリにない項目を
    持つ予定も作れるように、APIを使わない）。"""
    with app.app_context():
        event = Event(
            subject_id=subject_id,
            category=category,
            date=event_date,
            start_time=start_time,
            end_time=time(start_time.hour + 1, start_time.minute),
            title=title,
            employer=employer,
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


# --- 派遣会社の候補（GET /api/events/employers） ---


def employers(client, query=""):
    response = client.get(f"/api/events/employers{query}")
    assert response.status_code == 200
    return response.json


def test_employer_list_is_empty_without_events(client):
    assert employers(client) == []


def test_employer_list_is_empty_without_employers(client, app):
    make_event(app, date(2026, 4, 6), category="part_time")

    assert employers(client) == []


def test_employer_list_is_distinct_and_in_recent_order(client, app):
    make_event(app, date(2026, 4, 6), category="part_time", employer="A社")
    make_event(app, date(2026, 4, 7), category="part_time", employer="B社")
    make_event(app, date(2026, 4, 1), category="part_time", employer="A社")
    make_event(app, date(2026, 4, 8), category="part_time", employer="C社")
    make_event(app, date(2026, 4, 9), category="part_time", employer="B社")

    # 新しく登録した予定（idの大きいもの）の派遣会社から順に並ぶ
    # （予定の日付の順ではない）。
    assert employers(client) == ["B社", "C社", "A社"]


def test_employer_list_uses_only_part_time_events(client, app):
    make_event(app, date(2026, 4, 6), category="part_time", employer="A社")
    make_event(app, date(2026, 4, 7), category="other", employer="B社")
    make_event(app, date(2026, 4, 8), category="class", employer="C社")

    assert employers(client) == ["A社"]


def test_employer_list_compares_exact_strings(client, app):
    for employer in ["abc", "ABC", "ａｂｃ", "abc"]:
        make_event(
            app, date(2026, 4, 6), category="part_time", employer=employer
        )

    assert employers(client) == ["abc", "ａｂｃ", "ABC"]


def test_employer_list_ignores_unknown_query(client, app):
    make_event(app, date(2026, 4, 6), category="part_time", employer="A社")

    assert employers(client, "?category=other&limit=0") == ["A社"]


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_employer_list_url_accepts_only_get(client, app, method):
    make_event(app, date(2026, 4, 6), category="part_time", employer="A社")

    response = getattr(client, method)(
        "/api/events/employers", json={"employer": "B社"}
    )

    assert response.status_code == 405
    assert response.json["error"]["code"] == "method_not_allowed"
    assert employers(client) == ["A社"]
    assert event_count(app) == 1


# --- 提供しない操作（405） ---


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("put", "/api/events"),
        ("patch", "/api/events"),
        ("delete", "/api/events"),
        ("post", "/api/events/{event_id}"),
        ("put", "/api/events/{event_id}"),
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

### 付録D. `tests/test_events_create_update_delete_api.py`

<!-- 全文: tests/test_events_create_update_delete_api.py -->
```python
"""予定の登録（POST）・編集（PATCH）・削除（DELETE）のAPIのテスト。

予定の一覧・1件取得・派遣会社の候補は、tests/test_events_api.py で
確かめる。
"""

from datetime import date, time

import pytest
from sqlalchemy import func, select

from app.api_helpers import MAX_ID, UNUSABLE_CHARACTER_MESSAGE
from app.extensions import db
from app.models.closure import Closure
from app.models.event import Event
from app.models.semester import Semester
from app.models.subject import Subject
from app.models.task import Task


# 「今日」は、2026-06-15（月）に固定する（授業全体の編集による作り直しとの
# 関係を確かめるテストのため。予定APIは「今日」を使わない）。
TODAY = date(2026, 6, 15)
# 学期（2026-04-01〜2026-07-31）の、今日より後の月曜日（授業の曜日）。
FUTURE_MONDAY = date(2026, 6, 22)

CATEGORY_MESSAGE = (
    "カテゴリは「class」「part_time」「other」のどれかで指定してください"
)
DATE_MESSAGE = "日付は実在する日付を「YYYY-MM-DD」の形式で指定してください"
TIME_MESSAGES = {
    "start_time": (
        "開始時刻は「HH:MM」の形式（00:00〜23:59）で指定してください"
    ),
    "end_time": (
        "終了時刻は「HH:MM」の形式（00:00〜23:59）で指定してください"
    ),
}
TIME_REQUIRED_MESSAGES = {
    "start_time": "開始時刻は必須です",
    "end_time": "終了時刻は必須です",
}
END_TIME_ORDER_MESSAGE = "終了時刻は開始時刻より後にしてください"
GENERATED_DATE_MESSAGE = (
    "自動生成の授業の予定は、日付を変えられません（別の日に移すときは、"
    "この予定を削除して、移す先の日に単発の授業を追加してください）"
)
NOT_APPLICABLE_MESSAGES = {
    "subject_id": "授業IDは、授業の予定にだけ指定できます",
    "title": (
        "授業の予定には、タイトルを指定できません（授業の科目名になります）"
    ),
    "room": "教室は、授業の予定にだけ指定できます",
    "employer": "派遣会社は、アルバイトの予定にだけ指定できます",
}
NOT_ALLOWED_MESSAGE = "この項目は指定できません"
OBJECT_MESSAGE = "リクエストの本文は、JSONのオブジェクトにしてください"

# 本文から項目を除くことを表す値（項目がない場合の検証に使う）。
MISSING = object()


def set_today(monkeypatch, day):
    """授業のrouteが使う「今日」（current_date）を、指定した日にする。"""
    monkeypatch.setattr("app.routes.subjects.current_date", lambda: day)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    """このファイルのテストでは、「今日」を TODAY にする。"""
    set_today(monkeypatch, TODAY)


def make_semester(app):
    with app.app_context():
        semester = Semester(
            name="2026年度 前期",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 7, 31),
        )
        db.session.add(semester)
        db.session.commit()
        return semester.id


def make_subject(app, semester_id, subject_name="プログラミング基礎"):
    """授業を、ORMで直接作る（自動生成の予定は作らない）。"""
    with app.app_context():
        subject = Subject(
            semester_id=semester_id,
            subject_name=subject_name,
            room="3号館201",
            weekday=0,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        db.session.add(subject)
        db.session.commit()
        return subject.id


def create_subject_with_events(client, semester_id):
    """月曜日の授業をAPIで登録し（自動生成の予定も作られる）、IDを返す。"""
    response = client.post(
        "/api/subjects",
        json={
            "semester_id": semester_id,
            "subject_name": "プログラミング基礎",
            "room": "3号館201",
            "weekday": 0,
            "start_time": "09:00",
            "end_time": "10:00",
            "notes": "前期の授業",
        },
    )
    assert response.status_code == 201
    return response.json["id"]


@pytest.fixture
def semester_id(app):
    return make_semester(app)


@pytest.fixture
def subject_id(app, semester_id):
    return make_subject(app, semester_id)


def class_payload(subject_id, **overrides):
    payload = {
        "category": "class",
        "subject_id": subject_id,
        "date": "2026-06-20",
        "start_time": "15:00",
        "end_time": "16:30",
        "room": "5号館101",
        "notes": "補講",
    }
    payload.update(overrides)
    return payload


def part_time_payload(**overrides):
    payload = {
        "category": "part_time",
        "date": "2026-06-20",
        "start_time": "17:00",
        "end_time": "21:00",
        "title": "倉庫の仕分け",
        "employer": "派遣会社A",
        "notes": "軍手を持参",
    }
    payload.update(overrides)
    return payload


def other_payload(**overrides):
    payload = {
        "category": "other",
        "date": "2026-06-21",
        "start_time": "10:00",
        "end_time": "12:00",
        "title": "歯医者",
        "notes": "診察券",
    }
    payload.update(overrides)
    return payload


def payload_for(category, class_subject_id, **overrides):
    """カテゴリの、登録の本文を返す。

    class_subject_id は、授業の本文の subject_id（ほかのカテゴリでは
    使わない）。
    """
    if category == "class":
        return class_payload(class_subject_id, **overrides)
    if category == "part_time":
        return part_time_payload(**overrides)
    return other_payload(**overrides)


def replace_field(payload, field, value):
    """本文の1つの項目を、value にする（MISSING なら、項目を除く）。"""
    payload = dict(payload)
    if value is MISSING:
        payload.pop(field, None)
    else:
        payload[field] = value
    return payload


def create_event(client, payload):
    """予定をAPIで登録し、レスポンスの本文を返す。"""
    response = client.post("/api/events", json=payload)
    assert response.status_code == 201
    return response.json


def event_count(app):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(Event))


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


def events_on(app, subject_id, event_date, *, is_generated):
    """授業の、その日の予定（自動生成か単発か）を、IDの順に返す。"""
    with app.app_context():
        statement = (
            select(Event)
            .where(
                Event.subject_id == subject_id,
                Event.date == event_date,
                Event.is_generated.is_(is_generated),
            )
            .order_by(Event.id)
        )
        return [
            (event.id, event.room, event.title)
            for event in db.session.scalars(statement)
        ]


def generated_event_id(app, subject_id, event_date):
    """授業の、その日の自動生成の予定のIDを返す（1件だけのはず）。"""
    events = events_on(app, subject_id, event_date, is_generated=True)
    assert len(events) == 1
    return events[0][0]


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


def test_create_class_event_returns_event(client, subject_id):
    response = client.post("/api/events", json=class_payload(subject_id))

    assert response.status_code == 201
    assert response.json == {
        "id": response.json["id"],
        "subject_id": subject_id,
        "category": "class",
        "date": "2026-06-20",
        "start_time": "15:00",
        "end_time": "16:30",
        "title": "プログラミング基礎",
        "room": "5号館101",
        "employer": None,
        "notes": "補講",
        "is_generated": False,
    }


def test_create_class_event_saves_row(client, app, subject_id):
    created = create_event(client, class_payload(subject_id))

    assert all_event_rows(app) == [
        (
            created["id"],
            subject_id,
            "class",
            date(2026, 6, 20),
            time(15, 0),
            time(16, 30),
            "プログラミング基礎",
            "5号館101",
            None,
            "補講",
            False,
        )
    ]


def test_create_part_time_event_returns_event(client, app):
    response = client.post("/api/events", json=part_time_payload())

    assert response.status_code == 201
    assert response.json == {
        "id": response.json["id"],
        "subject_id": None,
        "category": "part_time",
        "date": "2026-06-20",
        "start_time": "17:00",
        "end_time": "21:00",
        "title": "倉庫の仕分け",
        "room": None,
        "employer": "派遣会社A",
        "notes": "軍手を持参",
        "is_generated": False,
    }
    assert event_count(app) == 1


def test_create_other_event_returns_event(client, app):
    response = client.post("/api/events", json=other_payload())

    assert response.status_code == 201
    assert response.json == {
        "id": response.json["id"],
        "subject_id": None,
        "category": "other",
        "date": "2026-06-21",
        "start_time": "10:00",
        "end_time": "12:00",
        "title": "歯医者",
        "room": None,
        "employer": None,
        "notes": "診察券",
        "is_generated": False,
    }
    assert event_count(app) == 1


@pytest.mark.parametrize(
    ("category", "omitted"),
    [
        ("class", ["room", "notes"]),
        ("part_time", ["employer", "notes"]),
        ("other", ["notes"]),
    ],
)
def test_create_optional_fields_can_be_omitted(
    client, subject_id, category, omitted
):
    payload = payload_for(category, subject_id)
    for field in omitted:
        del payload[field]

    created = create_event(client, payload)

    for field in omitted:
        assert created[field] is None


@pytest.mark.parametrize(
    ("category", "overrides", "expected"),
    [
        (
            "part_time",
            {"title": "　 倉庫の仕分け ", "employer": " ", "notes": "  "},
            {"title": "倉庫の仕分け", "employer": None, "notes": None},
        ),
        (
            "class",
            {"room": "　", "notes": ""},
            {"room": None, "notes": None},
        ),
    ],
)
def test_create_strips_strings_and_clears_blank_optional_fields(
    client, subject_id, category, overrides, expected
):
    created = create_event(
        client, payload_for(category, subject_id, **overrides)
    )

    for field, value in expected.items():
        assert created[field] == value


def test_create_class_title_is_subject_name_at_creation(
    client, app, subject_id
):
    created = create_event(client, class_payload(subject_id))
    with app.app_context():
        db.session.get(Subject, subject_id).subject_name = "データ構造"
        db.session.commit()

    response = client.get(f"/api/events/{created['id']}")

    # 単発の予定のタイトルは、登録したときの科目名の控え。
    assert response.json["title"] == "プログラミング基礎"


@pytest.mark.parametrize(
    "event_date",
    ["2020-01-01", "2026-03-31", "2026-08-10", "2026-06-17"],
)
def test_create_class_event_accepts_any_date(client, subject_id, event_date):
    # 過去の日付、学期の期間の外の日付、授業の曜日と違う日も受け付ける。
    created = create_event(
        client, class_payload(subject_id, date=event_date)
    )

    assert created["date"] == event_date


def test_create_class_event_on_closure_date_is_accepted(
    client, app, semester_id, subject_id
):
    with app.app_context():
        db.session.add(Closure(semester_id=semester_id, date=FUTURE_MONDAY))
        db.session.commit()

    created = create_event(
        client, class_payload(subject_id, date=FUTURE_MONDAY.isoformat())
    )

    assert events_on(app, subject_id, FUTURE_MONDAY, is_generated=False) == [
        (created["id"], "5号館101", "プログラミング基礎")
    ]


def test_create_class_event_beside_generated_event_is_accepted(
    client, app, semester_id
):
    subject_id = create_subject_with_events(client, semester_id)
    generated = events_on(app, subject_id, FUTURE_MONDAY, is_generated=True)

    created = create_event(
        client, class_payload(subject_id, date=FUTURE_MONDAY.isoformat())
    )

    # 同じ授業・同じ日付に、自動生成の予定と単発の予定が並ぶ。
    assert events_on(app, subject_id, FUTURE_MONDAY, is_generated=True) == (
        generated
    )
    assert events_on(app, subject_id, FUTURE_MONDAY, is_generated=False) == [
        (created["id"], "5号館101", "プログラミング基礎")
    ]


def test_create_accepts_times_outside_class_hours(client):
    created = create_event(
        client, part_time_payload(start_time="00:00", end_time="23:59")
    )

    assert (created["start_time"], created["end_time"]) == ("00:00", "23:59")


@pytest.mark.parametrize(
    ("category", "field", "max_length"),
    [
        ("part_time", "title", 200),
        ("other", "title", 200),
        ("part_time", "employer", 100),
        ("class", "room", 100),
    ],
)
def test_create_accepts_maximum_lengths(
    client, subject_id, category, field, max_length
):
    value = "あ" * max_length

    created = create_event(
        client, payload_for(category, subject_id, **{field: value})
    )

    assert created[field] == value


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (MISSING, "カテゴリは必須です"),
        (None, "カテゴリは必須です"),
        ("", "カテゴリは必須です"),
        ("assignment", CATEGORY_MESSAGE),
        ("Other", CATEGORY_MESSAGE),
        (" other", CATEGORY_MESSAGE),
        ("その他", CATEGORY_MESSAGE),
        (1, CATEGORY_MESSAGE),
        (True, CATEGORY_MESSAGE),
        (["other"], CATEGORY_MESSAGE),
        ("\ud800", UNUSABLE_CHARACTER_MESSAGE),
    ],
)
def test_create_category_is_validated(client, value, message):
    payload = replace_field(other_payload(), "category", value)

    response = client.post("/api/events", json=payload)

    assert_validation_error(response, {"category": message})


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (MISSING, "日付は必須です"),
        (None, "日付は必須です"),
        ("", "日付は必須です"),
        ("2026-6-20", DATE_MESSAGE),
        ("2026/06/20", DATE_MESSAGE),
        ("20260620", DATE_MESSAGE),
        ("2026-02-30", DATE_MESSAGE),
        ("2026-06-20T10:00", DATE_MESSAGE),
        (" 2026-06-20", DATE_MESSAGE),
        (20260620, DATE_MESSAGE),
        ("2026-06-20\ud800", UNUSABLE_CHARACTER_MESSAGE),
    ],
)
def test_create_date_is_validated(client, value, message):
    payload = replace_field(other_payload(), "date", value)

    response = client.post("/api/events", json=payload)

    assert_validation_error(response, {"date": message})


@pytest.mark.parametrize("field", ["start_time", "end_time"])
@pytest.mark.parametrize(
    ("value", "kind"),
    [
        (MISSING, "required"),
        ("", "required"),
        ("9:00", "format"),
        ("24:00", "format"),
        ("10:00:00", "format"),
        (1000, "format"),
        ("\ud800", "unusable"),
    ],
)
def test_create_time_is_validated(client, field, value, kind):
    payload = replace_field(other_payload(), field, value)
    messages = {
        "required": TIME_REQUIRED_MESSAGES[field],
        "format": TIME_MESSAGES[field],
        "unusable": UNUSABLE_CHARACTER_MESSAGE,
    }

    response = client.post("/api/events", json=payload)

    # 時刻の誤りがあると、開始と終了の前後は比べない。
    assert_validation_error(response, {field: messages[kind]})


@pytest.mark.parametrize(
    ("start_time", "end_time"),
    [("10:00", "10:00"), ("10:00", "09:59"), ("22:00", "02:00")],
)
def test_create_end_time_must_be_after_start_time(
    client, start_time, end_time
):
    # 日付をまたぐ予定（22:00〜翌2:00）も、1件では登録できない。
    payload = part_time_payload(start_time=start_time, end_time=end_time)

    response = client.post("/api/events", json=payload)

    assert_validation_error(response, {"end_time": END_TIME_ORDER_MESSAGE})


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (1, "詳細・メモは文字列で指定してください"),
        ("メモ\ud800", UNUSABLE_CHARACTER_MESSAGE),
    ],
)
def test_create_notes_is_validated(client, value, message):
    response = client.post("/api/events", json=other_payload(notes=value))

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
def test_create_class_subject_id_is_validated(
    client, subject_id, value, message
):
    payload = replace_field(class_payload(subject_id), "subject_id", value)

    response = client.post("/api/events", json=payload)

    assert_validation_error(response, {"subject_id": message})


@pytest.mark.parametrize("category", ["part_time", "other"])
@pytest.mark.parametrize(
    ("value", "message"),
    [
        (MISSING, "タイトルは必須です"),
        (None, "タイトルは必須です"),
        ("", "タイトルは必須です"),
        ("　 ", "タイトルは必須です"),
        (1, "タイトルは文字列で指定してください"),
        ("あ" * 201, "タイトルは200文字以内にしてください"),
        ("仕分け\ud800", UNUSABLE_CHARACTER_MESSAGE),
    ],
)
def test_create_title_is_validated(client, category, value, message):
    payload = replace_field(payload_for(category, None), "title", value)

    response = client.post("/api/events", json=payload)

    assert_validation_error(response, {"title": message})


@pytest.mark.parametrize(
    ("category", "field", "value", "message"),
    [
        ("class", "room", 1, "教室は文字列で指定してください"),
        ("class", "room", "あ" * 101, "教室は100文字以内にしてください"),
        ("class", "room", "\ud800", UNUSABLE_CHARACTER_MESSAGE),
        ("part_time", "employer", 1, "派遣会社は文字列で指定してください"),
        (
            "part_time",
            "employer",
            "あ" * 101,
            "派遣会社は100文字以内にしてください",
        ),
        ("part_time", "employer", "\ud800", UNUSABLE_CHARACTER_MESSAGE),
    ],
)
def test_create_room_and_employer_are_validated(
    client, subject_id, category, field, value, message
):
    payload = payload_for(category, subject_id, **{field: value})

    response = client.post("/api/events", json=payload)

    assert_validation_error(response, {field: message})


@pytest.mark.parametrize(
    ("category", "field", "value"),
    [
        ("class", "title", "補講"),
        ("class", "title", ""),
        ("class", "employer", "派遣会社A"),
        ("class", "employer", "\ud800"),
        ("part_time", "subject_id", "SUBJECT"),
        ("part_time", "subject_id", 0),
        ("part_time", "room", "3号館201"),
        ("part_time", "room", ""),
        ("other", "subject_id", "SUBJECT"),
        ("other", "room", "3号館201"),
        ("other", "employer", "派遣会社A"),
        ("other", "employer", ""),
    ],
)
def test_create_rejects_fields_not_for_category(
    client, subject_id, category, field, value
):
    # "SUBJECT" は、存在する授業のIDに置き換える。
    if value == "SUBJECT":
        value = subject_id
    payload = payload_for(category, subject_id, **{field: value})

    response = client.post("/api/events", json=payload)

    assert_validation_error(
        response, {field: NOT_APPLICABLE_MESSAGES[field]}
    )


@pytest.mark.parametrize(
    ("category", "field"),
    [
        ("class", "title"),
        ("class", "employer"),
        ("part_time", "subject_id"),
        ("part_time", "room"),
        ("other", "subject_id"),
        ("other", "room"),
        ("other", "employer"),
    ],
)
def test_create_accepts_null_for_fields_not_for_category(
    client, subject_id, category, field
):
    payload = payload_for(category, subject_id, **{field: None})

    created = create_event(client, payload)

    expected_title = {
        "class": "プログラミング基礎",
        "part_time": "倉庫の仕分け",
        "other": "歯医者",
    }[category]
    assert created["title"] == expected_title
    if field != "title":
        assert created[field] is None


def test_create_invalid_category_skips_category_fields(client):
    # カテゴリに誤りがあると、カテゴリによって変わる項目の規則が決まらない
    # ため、検査しない。
    payload = other_payload(
        category="assignment",
        subject_id=99999,
        title="",
        room=1,
        employer=1,
    )

    response = client.post("/api/events", json=payload)

    assert_validation_error(response, {"category": CATEGORY_MESSAGE})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", 1),
        ("is_generated", False),
        ("is_generated", True),
        ("location", "体育館"),
    ],
)
def test_create_rejects_unknown_and_read_only_fields(client, field, value):
    payload = other_payload(**{field: value})

    response = client.post("/api/events", json=payload)

    assert_validation_error(response, {field: NOT_ALLOWED_MESSAGE})


def test_create_validation_errors_are_returned_together(client):
    response = client.post(
        "/api/events",
        json={
            "category": "part_time",
            "date": "2026-06-31",
            "start_time": "21:00",
            "end_time": "17:00",
            "title": "",
            "room": "3号館201",
            "is_generated": False,
        },
    )

    assert_validation_error(
        response,
        {
            "date": DATE_MESSAGE,
            "end_time": END_TIME_ORDER_MESSAGE,
            "title": "タイトルは必須です",
            "room": NOT_APPLICABLE_MESSAGES["room"],
            "is_generated": NOT_ALLOWED_MESSAGE,
        },
    )


def test_failed_create_saves_nothing(client, app, subject_id):
    response = client.post(
        "/api/events", json=class_payload(subject_id, title="補講")
    )

    assert response.status_code == 400
    assert event_count(app) == 0


@pytest.mark.parametrize("body", ["[]", '"予定"', "1", "true", "null"])
def test_create_non_object_payload_has_no_fields(client, body):
    response = client.post(
        "/api/events", data=body, content_type="application/json"
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
        "/api/events", data=data, content_type=content_type
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_json"


def test_created_event_is_in_list_and_get(client):
    created = create_event(client, other_payload())

    listed = client.get(
        "/api/events?start_date=2026-06-21&end_date=2026-06-21"
    )
    fetched = client.get(f"/api/events/{created['id']}")

    assert listed.json == [created]
    assert fetched.json == created


# --- 編集（PATCH） ---


def test_patch_changes_only_given_fields(client):
    created = create_event(client, part_time_payload())

    response = client.patch(
        f"/api/events/{created['id']}", json={"title": " 棚卸し "}
    )

    assert response.status_code == 200
    assert response.json == dict(created, title="棚卸し")
    assert client.get(f"/api/events/{created['id']}").json == response.json


def test_patch_part_time_can_change_all_editable_fields(client):
    created = create_event(client, part_time_payload())

    response = client.patch(
        f"/api/events/{created['id']}",
        json={
            "date": "2026-06-27",
            "start_time": "18:00",
            "end_time": "22:30",
            "title": "棚卸し",
            "employer": "派遣会社B",
            "notes": "動きやすい服装",
        },
    )

    assert response.status_code == 200
    assert response.json == {
        "id": created["id"],
        "subject_id": None,
        "category": "part_time",
        "date": "2026-06-27",
        "start_time": "18:00",
        "end_time": "22:30",
        "title": "棚卸し",
        "room": None,
        "employer": "派遣会社B",
        "notes": "動きやすい服装",
        "is_generated": False,
    }


def test_patch_other_can_change_all_editable_fields(client):
    created = create_event(client, other_payload())

    response = client.patch(
        f"/api/events/{created['id']}",
        json={
            "date": "2026-07-01",
            "start_time": "13:00",
            "end_time": "14:00",
            "title": "眼科",
            "notes": None,
        },
    )

    assert response.status_code == 200
    assert response.json == dict(
        created,
        date="2026-07-01",
        start_time="13:00",
        end_time="14:00",
        title="眼科",
        notes=None,
    )


def test_patch_one_off_class_event_can_change_date_time_room_and_notes(
    client, subject_id
):
    created = create_event(client, class_payload(subject_id))

    response = client.patch(
        f"/api/events/{created['id']}",
        json={
            "date": "2026-06-27",
            "start_time": "13:00",
            "end_time": "14:30",
            "room": "5号館102",
            "notes": "補講（教室変更）",
        },
    )

    assert response.status_code == 200
    assert response.json == dict(
        created,
        date="2026-06-27",
        start_time="13:00",
        end_time="14:30",
        room="5号館102",
        notes="補講（教室変更）",
    )


def test_patch_generated_event_changes_time_room_notes_and_stays_generated(
    client, app, semester_id
):
    subject_id = create_subject_with_events(client, semester_id)
    event_id = generated_event_id(app, subject_id, FUTURE_MONDAY)

    response = client.patch(
        f"/api/events/{event_id}",
        json={
            "start_time": "10:00",
            "end_time": "11:00",
            "room": "3号館301",
            "notes": "この日だけ教室変更",
        },
    )

    assert response.status_code == 200
    assert response.json == {
        "id": event_id,
        "subject_id": subject_id,
        "category": "class",
        "date": FUTURE_MONDAY.isoformat(),
        "start_time": "10:00",
        "end_time": "11:00",
        "title": "プログラミング基礎",
        "room": "3号館301",
        "employer": None,
        "notes": "この日だけ教室変更",
        "is_generated": True,
    }


@pytest.mark.parametrize(
    "value", ["2026-06-23", FUTURE_MONDAY.isoformat(), None, "abc"]
)
def test_patch_generated_event_rejects_date(client, app, semester_id, value):
    subject_id = create_subject_with_events(client, semester_id)
    event_id = generated_event_id(app, subject_id, FUTURE_MONDAY)
    before = all_event_rows(app)

    # 今と同じ日付や null でも、日付は変えられない。
    response = client.patch(f"/api/events/{event_id}", json={"date": value})

    assert_validation_error(response, {"date": GENERATED_DATE_MESSAGE})
    assert all_event_rows(app) == before


@pytest.mark.parametrize(
    ("category", "field", "value"),
    [
        ("part_time", "employer", None),
        ("part_time", "employer", ""),
        ("part_time", "employer", "　"),
        ("class", "room", None),
        ("class", "room", " "),
        ("other", "notes", None),
        ("other", "notes", "  "),
    ],
)
def test_patch_can_clear_optional_fields(
    client, subject_id, category, field, value
):
    created = create_event(client, payload_for(category, subject_id))

    response = client.patch(
        f"/api/events/{created['id']}", json={field: value}
    )

    assert response.status_code == 200
    assert response.json == dict(created, **{field: None})


@pytest.mark.parametrize(
    ("category", "field"),
    [
        ("class", "title"),
        ("class", "employer"),
        ("part_time", "room"),
        ("other", "room"),
        ("other", "employer"),
    ],
)
def test_patch_accepts_null_for_fields_not_for_category(
    client, subject_id, category, field
):
    created = create_event(client, payload_for(category, subject_id))

    response = client.patch(
        f"/api/events/{created['id']}", json={field: None}
    )

    assert response.status_code == 200
    assert response.json == created


@pytest.mark.parametrize(
    ("category", "field", "value"),
    [
        ("class", "title", "補講"),
        ("class", "title", ""),
        ("class", "employer", "派遣会社A"),
        ("part_time", "room", "3号館201"),
        ("other", "room", "3号館201"),
        ("other", "employer", "派遣会社A"),
    ],
)
def test_patch_rejects_fields_not_for_category(
    client, subject_id, category, field, value
):
    created = create_event(client, payload_for(category, subject_id))

    response = client.patch(
        f"/api/events/{created['id']}", json={field: value}
    )

    assert_validation_error(
        response, {field: NOT_APPLICABLE_MESSAGES[field]}
    )


@pytest.mark.parametrize(
    ("category", "field", "value", "message"),
    [
        ("part_time", "date", None, "日付は必須です"),
        ("part_time", "date", "", "日付は必須です"),
        ("part_time", "date", "2026-02-30", DATE_MESSAGE),
        ("part_time", "date", "\ud800", UNUSABLE_CHARACTER_MESSAGE),
        ("part_time", "start_time", None, "開始時刻は必須です"),
        ("part_time", "start_time", "24:00", TIME_MESSAGES["start_time"]),
        ("part_time", "end_time", "", "終了時刻は必須です"),
        ("part_time", "end_time", "9:00", TIME_MESSAGES["end_time"]),
        ("part_time", "title", None, "タイトルは必須です"),
        ("part_time", "title", "　 ", "タイトルは必須です"),
        ("part_time", "title", 1, "タイトルは文字列で指定してください"),
        (
            "part_time",
            "title",
            "あ" * 201,
            "タイトルは200文字以内にしてください",
        ),
        ("other", "title", "", "タイトルは必須です"),
        ("part_time", "employer", 1, "派遣会社は文字列で指定してください"),
        (
            "part_time",
            "employer",
            "あ" * 101,
            "派遣会社は100文字以内にしてください",
        ),
        ("class", "room", 1, "教室は文字列で指定してください"),
        ("class", "room", "あ" * 101, "教室は100文字以内にしてください"),
        ("class", "date", None, "日付は必須です"),
        ("other", "notes", 1, "詳細・メモは文字列で指定してください"),
        ("other", "notes", "\ud800", UNUSABLE_CHARACTER_MESSAGE),
    ],
)
def test_patch_field_values_are_validated(
    client, subject_id, category, field, value, message
):
    created = create_event(client, payload_for(category, subject_id))

    response = client.patch(
        f"/api/events/{created['id']}", json={field: value}
    )

    assert_validation_error(response, {field: message})


@pytest.mark.parametrize(
    "payload",
    [
        {"start_time": "21:00"},
        {"end_time": "16:59"},
        {"start_time": "20:00", "end_time": "19:00"},
    ],
)
def test_patch_end_time_must_be_after_start_time_after_change(
    client, payload
):
    # 今の予定は 17:00〜21:00。本文にない時刻は、今の値と比べる。
    created = create_event(client, part_time_payload())

    response = client.patch(f"/api/events/{created['id']}", json=payload)

    assert_validation_error(response, {"end_time": END_TIME_ORDER_MESSAGE})


def test_patch_time_change_is_accepted_when_order_is_valid(client):
    created = create_event(client, part_time_payload())

    response = client.patch(
        f"/api/events/{created['id']}",
        json={"start_time": "22:00", "end_time": "23:59"},
    )

    assert response.status_code == 200
    assert response.json["start_time"] == "22:00"
    assert response.json["end_time"] == "23:59"


def test_patch_invalid_start_time_skips_time_order_validation(client):
    created = create_event(client, part_time_payload())

    response = client.patch(
        f"/api/events/{created['id']}", json={"start_time": "abc"}
    )

    assert_validation_error(
        response, {"start_time": TIME_MESSAGES["start_time"]}
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("category", "other"),
        ("category", "part_time"),
        ("subject_id", 1),
        ("subject_id", None),
        ("is_generated", True),
        ("is_generated", False),
        ("id", 1),
        ("location", "体育館"),
    ],
)
def test_patch_rejects_category_subject_and_unknown_fields(
    client, field, value
):
    created = create_event(client, part_time_payload())

    response = client.patch(
        f"/api/events/{created['id']}", json={field: value}
    )

    assert_validation_error(response, {field: NOT_ALLOWED_MESSAGE})


def test_patch_class_event_rejects_same_subject_id(client, subject_id):
    created = create_event(client, class_payload(subject_id))

    response = client.patch(
        f"/api/events/{created['id']}", json={"subject_id": subject_id}
    )

    assert_validation_error(response, {"subject_id": NOT_ALLOWED_MESSAGE})


def test_patch_empty_object_is_validation_error_without_fields(client):
    created = create_event(client, other_payload())

    response = client.patch(f"/api/events/{created['id']}", json={})

    assert response.status_code == 400
    assert response.json == {
        "error": {
            "code": "validation_error",
            "message": "変更する項目を指定してください",
        }
    }


def test_patch_validation_errors_are_returned_together(client):
    created = create_event(client, part_time_payload())

    response = client.patch(
        f"/api/events/{created['id']}",
        json={
            "date": "2026-06-31",
            "title": "",
            "room": "3号館201",
            "category": "other",
        },
    )

    assert_validation_error(
        response,
        {
            "date": DATE_MESSAGE,
            "title": "タイトルは必須です",
            "room": NOT_APPLICABLE_MESSAGES["room"],
            "category": NOT_ALLOWED_MESSAGE,
        },
    )


def test_failed_patch_changes_nothing(client, app):
    created = create_event(client, part_time_payload())
    before = all_event_rows(app)

    response = client.patch(
        f"/api/events/{created['id']}",
        json={"title": "棚卸し", "date": "2026-06-31"},
    )

    assert response.status_code == 400
    assert all_event_rows(app) == before


def test_patch_changes_only_that_event(client, app, semester_id):
    subject_id = create_subject_with_events(client, semester_id)
    created = create_event(client, part_time_payload())
    event_id = generated_event_id(app, subject_id, FUTURE_MONDAY)
    before = [row for row in all_event_rows(app) if row[0] != event_id]

    response = client.patch(
        f"/api/events/{event_id}", json={"room": "3号館301"}
    )

    assert response.status_code == 200
    after = [row for row in all_event_rows(app) if row[0] != event_id]
    assert after == before
    assert client.get(f"/api/events/{created['id']}").json == created


@pytest.mark.parametrize("body", ["[]", '"予定"', "1", "true", "null"])
def test_patch_non_object_payload_has_no_fields(client, body):
    created = create_event(client, other_payload())

    response = client.patch(
        f"/api/events/{created['id']}",
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
    client, data, content_type
):
    created = create_event(client, other_payload())

    response = client.patch(
        f"/api/events/{created['id']}", data=data, content_type=content_type
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_json"


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/events/99999", "予定が見つかりません"),
        ("/api/events/0", "予定が見つかりません"),
        (f"/api/events/{MAX_ID}", "予定が見つかりません"),
        ("/api/events/abc", "URLが見つかりません"),
        ("/api/events/-1", "URLが見つかりません"),
    ],
)
def test_patch_not_found_and_invalid_urls(client, url, message):
    response = client.patch(url, json={"title": "棚卸し"})

    assert response.status_code == 404
    assert response.json == {
        "error": {"code": "not_found", "message": message}
    }


def test_patch_missing_event_is_404_before_reading_body(client):
    response = client.patch(
        "/api/events/99999", data="not json", content_type="text/plain"
    )

    assert response.status_code == 404
    assert response.json["error"]["message"] == "予定が見つかりません"


# --- 削除（DELETE） ---


def test_delete_one_off_event_removes_only_that_event(client):
    deleted = create_event(client, part_time_payload())
    kept = create_event(client, other_payload())

    response = client.delete(f"/api/events/{deleted['id']}")

    assert response.status_code == 204
    assert response.data == b""
    listed = client.get(
        "/api/events?start_date=2026-06-01&end_date=2026-06-30"
    )
    assert listed.json == [kept]


def test_delete_generated_event_removes_only_that_day(
    client, app, semester_id
):
    subject_id = create_subject_with_events(client, semester_id)
    event_id = generated_event_id(app, subject_id, FUTURE_MONDAY)
    before = [row for row in all_event_rows(app) if row[0] != event_id]

    response = client.delete(f"/api/events/{event_id}")

    assert response.status_code == 204
    assert all_event_rows(app) == before
    assert events_on(app, subject_id, FUTURE_MONDAY, is_generated=True) == []


def test_delete_event_keeps_subject_closures_and_tasks(
    client, app, semester_id, subject_id
):
    with app.app_context():
        db.session.add(
            Closure(semester_id=semester_id, date=date(2026, 6, 29))
        )
        db.session.commit()
    task = client.post(
        "/api/tasks",
        json={
            "category": "assignment",
            "subject_id": subject_id,
            "title": "レポート",
            "due_datetime": "2026-06-30T23:59",
        },
    ).json
    created = create_event(client, class_payload(subject_id))

    response = client.delete(f"/api/events/{created['id']}")

    assert response.status_code == 204
    with app.app_context():
        assert db.session.get(Subject, subject_id) is not None
        assert db.session.scalar(
            select(func.count()).select_from(Closure)
        ) == 1
        assert db.session.get(Task, task["id"]) is not None


def test_delete_event_ignores_body(client):
    created = create_event(client, other_payload())

    response = client.delete(
        f"/api/events/{created['id']}",
        data="not json",
        content_type="text/plain",
    )

    assert response.status_code == 204


def test_deleted_event_cannot_be_deleted_again(client):
    created = create_event(client, other_payload())
    client.delete(f"/api/events/{created['id']}")

    response = client.delete(f"/api/events/{created['id']}")

    assert response.status_code == 404
    assert response.json["error"]["message"] == "予定が見つかりません"


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/events/99999", "予定が見つかりません"),
        ("/api/events/0", "予定が見つかりません"),
        (f"/api/events/{MAX_ID}", "予定が見つかりません"),
        ("/api/events/abc", "URLが見つかりません"),
        ("/api/events/-1", "URLが見つかりません"),
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
    "event_id_text", [str(MAX_ID + 1), "99999999999999999999"]
)
def test_over_limit_id_for_patch_and_delete_is_method_not_allowed(
    client, method, event_id_text
):
    # docs/architecture.md の「404の使い分け」の注意（Flaskの仕組みにより、
    # 同じURLにほかのメソッドのrouteがあると、405になる）。
    response = getattr(client, method)(f"/api/events/{event_id_text}")

    assert response.status_code == 405
    assert response.json["error"]["code"] == "method_not_allowed"


# --- 授業の編集・削除、休講日との関係 ---


def test_one_off_class_event_is_kept_by_subject_patch(
    client, app, semester_id
):
    subject_id = create_subject_with_events(client, semester_id)
    created = create_event(
        client, class_payload(subject_id, date=FUTURE_MONDAY.isoformat())
    )

    response = client.patch(
        f"/api/subjects/{subject_id}", json={"subject_name": "データ構造"}
    )

    # 単発の予定は、作り直しの対象外で、タイトルも登録したときのまま。
    assert response.status_code == 200
    assert client.get(f"/api/events/{created['id']}").json == created


def test_edited_generated_event_is_rebuilt_by_subject_patch(
    client, app, semester_id
):
    subject_id = create_subject_with_events(client, semester_id)
    event_id = generated_event_id(app, subject_id, FUTURE_MONDAY)
    client.patch(f"/api/events/{event_id}", json={"room": "3号館301"})

    response = client.patch(
        f"/api/subjects/{subject_id}", json={"notes": "教室は3号館201"}
    )

    # 今日以降の自動生成の予定は、授業の設定どおりに作り直される。
    assert response.status_code == 200
    events = events_on(app, subject_id, FUTURE_MONDAY, is_generated=True)
    assert [(room, title) for _, room, title in events] == [
        ("3号館201", "プログラミング基礎")
    ]


def test_deleted_generated_event_is_restored_by_subject_patch(
    client, app, semester_id
):
    subject_id = create_subject_with_events(client, semester_id)
    event_id = generated_event_id(app, subject_id, FUTURE_MONDAY)
    client.delete(f"/api/events/{event_id}")

    response = client.patch(
        f"/api/subjects/{subject_id}", json={"room": "3号館202"}
    )

    assert response.status_code == 200
    events = events_on(app, subject_id, FUTURE_MONDAY, is_generated=True)
    assert [room for _, room, _ in events] == ["3号館202"]


def test_closure_creation_deletes_edited_generated_event_only(
    client, app, semester_id
):
    subject_id = create_subject_with_events(client, semester_id)
    event_id = generated_event_id(app, subject_id, FUTURE_MONDAY)
    client.patch(f"/api/events/{event_id}", json={"room": "3号館301"})
    one_off = create_event(
        client, class_payload(subject_id, date=FUTURE_MONDAY.isoformat())
    )

    response = client.post(
        "/api/closures",
        json={"semester_id": semester_id, "date": FUTURE_MONDAY.isoformat()},
    )

    # 個別に編集した自動生成の予定も削除され、単発の予定は残る。
    assert response.status_code == 201
    assert events_on(app, subject_id, FUTURE_MONDAY, is_generated=True) == []
    assert client.get(f"/api/events/{one_off['id']}").json == one_off


def test_closure_deletion_restores_deleted_generated_event(
    client, app, semester_id
):
    subject_id = create_subject_with_events(client, semester_id)
    event_id = generated_event_id(app, subject_id, FUTURE_MONDAY)
    client.delete(f"/api/events/{event_id}")
    closure = client.post(
        "/api/closures",
        json={"semester_id": semester_id, "date": FUTURE_MONDAY.isoformat()},
    ).json

    response = client.delete(f"/api/closures/{closure['id']}")

    # 個別に削除したことは記録しないため、休講日の削除で、予定が作られる。
    assert response.status_code == 204
    events = events_on(app, subject_id, FUTURE_MONDAY, is_generated=True)
    assert len(events) == 1


def test_subject_deletion_removes_its_one_off_events_only(
    client, app, subject_id
):
    create_event(client, class_payload(subject_id))
    part_time = create_event(client, part_time_payload())
    other = create_event(client, other_payload())

    response = client.delete(f"/api/subjects/{subject_id}")

    assert response.status_code == 204
    listed = client.get(
        "/api/events?start_date=2026-06-01&end_date=2026-06-30"
    )
    assert listed.json == [part_time, other]


def test_registered_and_edited_employers_are_candidates(client):
    first = create_event(client, part_time_payload(employer="派遣会社A"))
    create_event(client, part_time_payload(employer="派遣会社B"))
    client.patch(
        f"/api/events/{first['id']}", json={"employer": "派遣会社C"}
    )

    response = client.get("/api/events/employers")

    # 派遣会社Aを持つ予定は、編集で、なくなった。
    assert response.json == ["派遣会社B", "派遣会社C"]
```
