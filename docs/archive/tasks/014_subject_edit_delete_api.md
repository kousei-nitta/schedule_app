# タスク014: 授業の編集・削除のAPI

| 項目 | 内容 |
|---|---|
| Task ID | 014 |
| Task名 | 授業の編集・削除のAPI（`PATCH`・`DELETE /api/subjects/<id>`、今日以降の予定の作り直し、1件取得の件数） |
| ブランチ | `feature/014-subject-edit-delete-api`（Komaが作成・切替済みの状態で渡される） |

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに停止して報告する。

**このタスクには、承認ゲートはない（DBの構造を変えないため、migrationを作らない）。** 段階1・2を順に進め、「Copilot確認手順」を実施したら、結果を報告して応答を終える。途中で止まるのは、「注意」の停止の条件に当たったときだけ。**止まるときは、報告を書いて応答を終える。質問の機能（選択肢を出して回答を待つ機能）は使わない**（`.github/copilot-instructions.md` の「止まる場面の応答」）。

**ファイルは、手で書き写さない。** 5つのファイルの全文は、このTask MDの付録にある。各段階の始めに、「全文からファイルを作るスクリプト」を実行して作る（013-N1。Task 013で、全文を取り出すときの誤りで、3つのファイルが一時的に全文と違ったため）。付録の全文は、スクリプトが読む。付録を読んで書き写す必要はない（本文の要点・差分・確認の手順を読む）。

## 目的
授業全体の編集（`PATCH /api/subjects/<id>`）と、授業全体の削除（`DELETE /api/subjects/<id>`）のAPIを作る。編集では、今日以降の自動生成の予定を、授業の新しい値で作り直す。削除では、授業と、その授業の予定・課題を、まとめて削除する。あわせて、授業の1件取得（`GET /api/subjects/<id>`）に、削除の確認に使う件数（`event_count`・`task_count`）を足す。設計資料（`docs/architecture.md` の「授業全体の編集による作り直し」「授業API」、「API共通ルール」の「`PATCH`（一部の項目の更新）」「レスポンスの付加情報」、「データ設計」の「共通の約束」の削除の連動）の仕様を、そのまま実装する。**画面とDBの構造は変えない**（授業の編集・削除の画面は、Task 015で作る）。

次の2段階で、この順に行う。

| 段階 | 内容 | 挙動の変化 | 段階の終わりの `pytest` |
|---|---|---|---|
| 1 | 作り直しの関数：`app/class_events.py` に `build_class_events_from` を足し、`tests/test_class_events.py` に、そのテスト（6件）を足す | 変わらない（新しい関数は、まだどこからも使わない） | **484件**（478＋6） |
| 2 | 授業API：`app/routes/subjects.py`（編集・削除・件数と、登録・編集で共通の検証）、`tests/test_subjects_api.py`（既存のテスト2件の変更）、`tests/test_subjects_update_delete_api.py`（新規。86件） | 授業の `PATCH`・`DELETE` が使えるようになる（今は405）。1件取得に件数が付く | **569件**（484−1＋86） |

段階2の「−1」は、`tests/test_subjects_api.py` の405のテストの組が、6組から5組になるため（2-2）。

## 前提（Task 013完了時点の状態）

| 区分 | 内容 |
|---|---|
| すでにある | 学期・授業・休講日のAPIと画面、予定API（`GET /api/events`・`GET /api/events/<id>`）、カレンダー表示（Task 013）、pytest（**478件**。`main` の `c3a66cb` で確認） |
| まだない | 授業の `PATCH`・`DELETE`（今は405）、`build_class_events_from`、`tests/test_subjects_update_delete_api.py` |
| DBの構造 | 変えない（初期migration `0280f6cf8d09` と、休講日の `42bd53808fa1`）。**migrationは不要**。モデルに `cascade` などを足さない（削除の連動は、routeで明示的に行う） |
| 開発用DB | `instance/app.db` は、Komaの実際の開発用DB（すべてのテーブルが0件。2026-10-13、Task 013の確認のあとにKomaが確認）。**Copilotは、書き込まない。サーバーを起動しない（`python run.py` を実行しない）**。読むのは、「Copilot確認手順」のハッシュと件数だけ。**`sqlite3` は、必ず `-readonly` を付けて実行する**（011-L1） |
| 設計資料 | このタスクの前に、更新した設計資料が `main` に反映されている。`docs/architecture.md` に「授業全体の編集による作り直し」の節があり、未決定事項から「授業編集時の「今日」の基準」「授業削除時のEvent・Task削除方式」が外れている |
| 画面 | 変えない。ブラウザでの確認はない。APIの動作は、pytestと、Komaの確認用のサーバーでの `curl` で確かめる |
| 「今日」 | 編集の作り直しの「今日」は、サーバーの日付（`routes/subjects.py` の `current_date`。`date.today()`）。**テストは、`current_date` を置き換えて、日付を固定する**ため、実行した日によって結果が変わらない |

## Source of Truth
- `docs/architecture.md`：「データ設計」の「共通の約束」（削除の連動）・Subject、「繰り返し予定の扱い」（「編集・削除の仕様」「授業全体の編集による作り直し」「同じ授業・同じ日付に単発の予定がある場合」）、「授業のEventの生成処理」、「API共通ルール」（「リクエストとレスポンス（JSON）」の `PATCH` と「レスポンスの付加情報」、「404の使い分け」）、「授業API」、「自動テスト（pytest）」
- `docs/requirements.md`：「学期」、「予定の編集・削除」
- `docs/ui_ux.md`：「授業」（授業全体の編集・削除）
- `.github/copilot-instructions.md`：進め方、「止まる場面の応答」、コーディング方針、「テスト」

## 実装対象ファイル

| 区分 | ファイル | 段階 | 内容 | 全文 |
|---|---|---|---|---|
| 変更 | `app/class_events.py` | 1 | `build_class_events_from` を足す。冒頭の説明を直す | 付録A |
| 変更 | `tests/test_class_events.py` | 1 | `build_class_events_from` のテスト（6件）と、その `import` を足す | 付録B |
| 変更 | `app/routes/subjects.py` | 2 | 編集（`PATCH`）・削除（`DELETE`）・1件取得の件数。登録と編集で共通の検証の関数 | 付録C |
| 変更 | `tests/test_subjects_api.py` | 2 | 既存のテスト2件の変更（2-2の差分） | 付録D |
| 新規 | `tests/test_subjects_update_delete_api.py` | 2 | 編集・削除・件数のテスト（86件） | 付録E |

上の5ファイル以外は、変更しない（`__pycache__/` などの、`.gitignore` の対象は除く）。**5ファイルとも、このTask MDの付録に全文がある。「全文からファイルを作るスクリプト」で作り、手で書き写さない。書き込んだあとに、手で直さない。** 全文を変える必要があると判断した場合は、変えずに停止して報告する。

## 非対象（このタスクでは作らない・変更しない）
- モデル（`app/models/`。**`cascade` などを足さない**）、`migrations/`（**新しいmigrationを作らない。`flask db` のコマンドを、一切実行しない**）、`requirements.txt`（**ライブラリを追加しない**）、`pytest.ini`、`run.py`
- `app/api_helpers.py`（空の本文 `{}` の検査は、`routes/subjects.py` に置く。`api_helpers.py` へ移すかは、2つ目のリソースが `PATCH` を提供するときに決める）、`app/__init__.py`、`app/routes/` のほかのファイル
- `app/templates/`、`app/static/`（画面は変えない。授業の編集・削除の画面は、Task 015）
- `tests/` の、上の3つ以外のファイル（`conftest.py` を含む）
- `docs/`、`.github/`、`.gitignore`
- 作らないもの：学期の変更・削除（`PATCH`・`DELETE /api/semesters/<id>` は405のまま）、授業の学期の付け替え、予定の登録・編集・削除（`/api/events`）、課題・タスクのAPI
- 持ち越しの003-H・010-N2・013-L1（このタスクでは扱わない）
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
    "1": ["app/class_events.py", "tests/test_class_events.py"],
    "2": [
        "app/routes/subjects.py",
        "tests/test_subjects_api.py",
        "tests/test_subjects_update_delete_api.py",
    ],
}

stage = sys.argv[1]
# このTask MDの「<!-- 全文: パス -->」の直後のコードブロックを、
# そのファイルの全文として取り出す。
fence = "`" * 3
task_text = Path("docs/tasks/014_subject_edit_delete_api.md").read_text(
    encoding="utf-8"
)
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
| 1（`python - 1`） | `全文の数：5`、`app/class_events.py：書き込み（103行）`、`tests/test_class_events.py：書き込み（278行）` |
| 2（`python - 2`） | `全文の数：5`、`app/routes/subjects.py：書き込み（408行）`、`tests/test_subjects_api.py：書き込み（1052行）`、`tests/test_subjects_update_delete_api.py：書き込み（1032行）` |

- 出力が上と違う場合（全文の数・行数・エラー）は、ほかの作業をせずに停止して報告する
- 段階の終わりの「全文との比較」（「Copilot確認手順」の4）で「不一致」が出た場合は、手で直さず、その段階のスクリプトをもう一度実行して、全文に戻す。戻したことと、違っていた理由（分かれば）を、報告に書く（013-N1）

## 段階1：作り直しの関数（挙動は変わらない）

### 1-1. `app/class_events.py`（全文：付録A）
要点：
- `build_class_events_from(subject, semester, excluded_dates, from_date)`：`from_date`（routeが渡す「今日」）と学期の開始日の遅いほうから、学期の終了日までの、授業の曜日に当たる日（`excluded_dates` の日を除く）の予定を作る。`from_date` が学期の終了日より後なら、空の一覧を返す
- 「今日」を求めない。DBを読まない。セッションを操作しない（ほかの関数と同じ）
- 既存の3つの関数（`class_event_dates`・`build_class_event`・`build_class_events`）は変えない

`main` からの差分（確認用。ファイルは、スクリプトで作る）：

```diff
--- a/app/class_events.py
+++ b/app/class_events.py
@@ -1,8 +1,10 @@
 """授業の予定（Event）の生成。
 
-授業の登録と、休講日の削除による予定の作成から使う部品。
+授業の登録、休講日の削除による予定の作成、授業全体の編集による
+予定の作り直しから使う部品。
 DBの読み書き（セッションへの追加・commit）は行わない。休講日の日付の
-取得と、データの保存は、各routeが担当する。
+取得と、データの保存は、各routeが担当する。「今日」の日付も、この
+ファイルでは求めない（作り直しの開始日は、routeが引数で渡す）。
 """
 
 from datetime import date, timedelta
@@ -77,3 +79,25 @@ def build_class_events(
         excluded_dates,
     )
     return [build_class_event(subject, event_date) for event_date in dates]
+
+
+def build_class_events_from(
+    subject: Subject,
+    semester: Semester,
+    excluded_dates: set[date],
+    from_date: date,
+) -> list[Event]:
+    """from_date以降の、授業の自動生成の予定を作る（セッションには追加しない）。
+
+    授業全体の編集による作り直しで使う。対象の期間は、from_date（含む）と
+    学期の開始日の遅いほうから、学期の終了日まで。from_dateが学期の
+    終了日より後なら、空の一覧を返す。
+    """
+    start_date = max(from_date, semester.start_date)
+    dates = class_event_dates(
+        start_date,
+        semester.end_date,
+        subject.weekday,
+        excluded_dates,
+    )
+    return [build_class_event(subject, event_date) for event_date in dates]
```

### 1-2. `tests/test_class_events.py`（全文：付録B）
`main` からの差分（確認用）：

```diff
--- a/tests/test_class_events.py
+++ b/tests/test_class_events.py
@@ -6,6 +6,7 @@ from app.class_events import (
     EVENT_CATEGORY_CLASS,
     build_class_event,
     build_class_events,
+    build_class_events_from,
     class_event_dates,
 )
 from app.models.semester import Semester
@@ -201,3 +202,77 @@ def test_build_class_events_returns_empty_list_without_matching_days():
     )
 
     assert build_class_events(make_subject(), semester, set()) == []
+
+
+# --- 授業全体の編集による作り直し（build_class_events_from） ---
+
+
+def test_build_class_events_from_includes_from_date():
+    subject = make_subject()
+
+    # 2026-06-15は月曜日。その日を含む。
+    events = build_class_events_from(
+        subject, make_semester(), set(), date(2026, 6, 15)
+    )
+
+    assert [event.date for event in events] == [
+        day for day in MONDAYS_FROM_APRIL_1 if day >= date(2026, 6, 15)
+    ]
+    assert all(event.subject is subject for event in events)
+    assert all(event.is_generated is True for event in events)
+
+
+def test_build_class_events_from_starts_at_next_matching_day():
+    # 2026-06-16は火曜日。次の月曜日（6/22）から。
+    events = build_class_events_from(
+        make_subject(), make_semester(), set(), date(2026, 6, 16)
+    )
+
+    assert [event.date for event in events] == [
+        date(2026, 6, 22),
+        date(2026, 6, 29),
+        date(2026, 7, 6),
+        date(2026, 7, 13),
+        date(2026, 7, 20),
+        date(2026, 7, 27),
+    ]
+
+
+def test_build_class_events_from_before_semester_uses_whole_semester():
+    events = build_class_events_from(
+        make_subject(), make_semester(), set(), date(2026, 3, 1)
+    )
+
+    assert [event.date for event in events] == MONDAYS_FROM_APRIL_1
+
+
+def test_build_class_events_from_on_last_day_includes_it():
+    # 学期の終了日（2026-07-31）は金曜日。
+    events = build_class_events_from(
+        make_subject(weekday=4), make_semester(), set(), date(2026, 7, 31)
+    )
+
+    assert [event.date for event in events] == [date(2026, 7, 31)]
+
+
+def test_build_class_events_from_after_semester_returns_empty_list():
+    events = build_class_events_from(
+        make_subject(), make_semester(), set(), date(2026, 8, 1)
+    )
+
+    assert events == []
+
+
+def test_build_class_events_from_skips_excluded_dates():
+    events = build_class_events_from(
+        make_subject(),
+        make_semester(),
+        {date(2026, 5, 4), date(2026, 7, 20)},
+        date(2026, 7, 1),
+    )
+
+    assert [event.date for event in events] == [
+        date(2026, 7, 6),
+        date(2026, 7, 13),
+        date(2026, 7, 27),
+    ]
```

| 確かめること（`docs/architecture.md` の「授業のEventの生成処理」） | テスト | 件数 |
|---|---|---|
| `from_date` の日を含む。授業との関係・`is_generated` | `test_build_class_events_from_includes_from_date` | 1 |
| `from_date` が授業の曜日でなければ、次の該当日から | `test_build_class_events_from_starts_at_next_matching_day` | 1 |
| `from_date` が学期の開始日より前なら、学期の期間全体 | `test_build_class_events_from_before_semester_uses_whole_semester` | 1 |
| `from_date` が学期の終了日なら、その日を含む | `test_build_class_events_from_on_last_day_includes_it` | 1 |
| `from_date` が学期の終了日より後なら、空の一覧 | `test_build_class_events_from_after_semester_returns_empty_list` | 1 |
| 休講日を除く | `test_build_class_events_from_skips_excluded_dates` | 1 |
| 合計 | | **6** |

## 段階2：授業API

### 2-1. `app/routes/subjects.py`（全文：付録C）
ファイルの構成（上から順に）：

| 名前 | 種類 | 内容 |
|---|---|---|
| `UPDATE_FIELDS`・`CREATE_FIELDS` | 定数（新規） | 編集・登録で受け付ける項目。編集は `semester_id` を受け付けない |
| `END_TIME_ORDER_MESSAGE` | 定数（新規） | 「終了時刻は開始時刻より後にしてください」（登録・編集で共通） |
| `subject_to_dict` | 関数 | 変えない |
| `current_date` | 関数（新規） | 作り直しの「今日」（`date.today()`）。テストで置き換える |
| `validate_subject_values(payload, *, partial)` | 関数（新規） | 授業の項目（学期を除く6つ）の検証。登録（`partial=False`）と編集（`partial=True`。本文にある項目だけ）で共通。今の `create_subject` の中の検証を、そのまま移した（メッセージと、項目ごとの検査は変えない） |
| `semester_closure_dates` | 関数（新規） | 学期の休講日の日付の集合。今の `create_subject` の中の処理を移した（登録と編集で使う） |
| `delete_generated_events_from` | 関数（新規） | 授業の、`from_date` 以降の自動生成の予定を削除する（commitしない） |
| `count_subject_events`・`count_subject_tasks` | 関数（新規） | 1件取得の件数 |
| `get_subjects` | route | 変えない |
| `get_subject` | route | 件数（`event_count`・`task_count`）を足す |
| `create_subject` | route | 検証を `validate_subject_values` に、休講日の取得を `semester_closure_dates` に置き換える（挙動は変えない。既存の登録のテストで確かめる） |
| `update_subject` | route（新規） | `PATCH`。下の順序 |
| `delete_subject` | route（新規） | `DELETE`。下の順序 |

`update_subject`（`PATCH`）の処理の順序：
1. 授業を取得する。なければ404（「授業が見つかりません」）。本文は読まない
2. 本文を読む（`read_json_object`。`Content-Type`・JSON・オブジェクトの検査）
3. 空の本文（`{}`）は、400（「変更する項目を指定してください」。`fields` なし）
4. 本文にある項目を検証する（`validate_subject_values(payload, partial=True)`）
5. 時刻の前後：本文の時刻に誤りがなければ、変更後の値どうしで比べる（本文にない時刻は、今の値）。違反は `end_time` のエラー
6. 受け付けない項目（`semester_id`・`id`・付加情報・未知の項目）のエラー
7. 誤りがあれば、400で、まとめて返す（授業も予定も変えない）
8. 本文にあった項目だけを、授業に書き込む
9. 「今日」（`current_date()`）以降の、その授業の自動生成の予定を削除し、`build_class_events_from` で作り直す（休講日を除く）。作った予定は、`db.session.add_all` で、明示的にセッションに追加する
10. 1回のcommit。200で、更新後の授業を返す（付加情報なし）

`delete_subject`（`DELETE`）の処理の順序：
1. 授業を取得する。なければ404（「授業が見つかりません」）。本文は読まない
2. その授業の予定（`Event.subject_id` が一致。自動生成・単発の両方、過去分を含む）を削除する
3. その授業の課題（`Task.subject_id` が一致）を削除する
4. 授業を削除する（`db.session.delete`）
5. 1回のcommit。204（本文なし）

注意：
- 2・3を省いて授業だけを削除すると、予定と課題が、`subject_id` が `NULL` の行として残る（ORMが、`relationship` を通して書き換えるため。設計のときに、一時的なDBで確かめた）。順序（予定・課題 → 授業）を変えない。テスト `test_delete_subject_leaves_no_rows_without_subject` で確かめる
- モデルに `cascade` を足して、2・3を省く書き方にしない（`docs/architecture.md` の「データ設計」の「共通の約束」）
- `PATCH`・`DELETE` のURLに、上限（`MAX_ID`）を超えるIDを指定すると、405になる（`GET` は404）。Flaskの仕組みによるもので、`docs/architecture.md` の「404の使い分け」の注意に書いた挙動。直さない（テスト `test_over_limit_id_for_patch_and_delete_is_method_not_allowed`）

### 2-2. `tests/test_subjects_api.py`（全文：付録D）
既存のテスト2件だけを変える。`main` からの差分（確認用）：

```diff
--- a/tests/test_subjects_api.py
+++ b/tests/test_subjects_api.py
@@ -685,6 +685,9 @@ def test_subject_get_returns_created_subject(client, app):
     expected = dict(created.json)
     # 作成のレスポンスにだけ付ける付加情報は、1件取得には含めない。
     del expected["generated_event_count"]
+    # 1件取得にだけ付ける付加情報（授業を削除すると一緒に削除される件数）。
+    expected["event_count"] = 17
+    expected["task_count"] = 0
     assert client.get(f"/api/subjects/{created.json['id']}").json == (
         expected
     )
@@ -715,8 +718,9 @@ def test_subject_get_not_found_and_invalid_urls(client, url, message):
 @pytest.mark.parametrize(
     ("method", "url"),
     [
-        ("patch", "/api/subjects/{subject_id}"),
-        ("delete", "/api/subjects/{subject_id}"),
+        # 1件のURLのPATCH・DELETEは、授業の編集・削除として提供する
+        # （tests/test_subjects_update_delete_api.py）。
+        ("put", "/api/subjects/{subject_id}"),
         ("put", "/api/subjects"),
         ("patch", "/api/subjects"),
         ("delete", "/api/subjects"),
```

| テスト | 変更 | 理由 |
|---|---|---|
| `test_subject_get_returns_created_subject` | 期待値に `event_count`（17）と `task_count`（0）を足す | 1件取得に、付加情報の件数が付くため |
| `test_unsupported_subject_methods_do_not_change_rows` | 1件のURLの `patch`・`delete` の組を外し、`put` の組を足す（6組 → 5組） | 1件のURLの `PATCH`・`DELETE` を提供するため（405でなくなる）。`PUT` は、引き続き405 |

### 2-3. `tests/test_subjects_update_delete_api.py`（新規。全文：付録E）
- 「今日」は、このファイルのテストで自動で使うfixture（`fixed_today`）で、**2026-06-15（月）に固定する**。学期は 2026-04-01〜2026-07-31（`make_semester`）で、月曜日の授業の予定は17件（今日より前が10件、今日以降が7件）
- 学期の前・後の「今日」を確かめるテストは、`set_today` で、その日に置き換える
- 授業は、APIで登録する（予定も作られる）。予定・課題を作るAPIがないもの（単発の予定・アルバイト・課題）は、ORMで直接作る
- 予定が変わらないことは、すべての予定の値（`all_event_rows`）を、操作の前後で比べて確かめる

| 確かめること（`docs/architecture.md`） | テスト | 件数 |
|---|---|---|
| 1件取得の件数（自動生成・単発の予定、課題。ほかの授業・授業のない行は数えない） | `test_subject_get_counts_events_and_tasks_of_the_subject` | 1 |
| 予定・課題がなければ0 | `test_subject_get_counts_are_zero_without_events_and_tasks` | 1 |
| 件数は一覧に含めない | `test_counts_are_not_in_subject_list` | 1 |
| 件数を登録の本文に含めると400 | `test_count_fields_in_post_request_are_rejected` | 2 |
| 本文にある項目だけを変え、更新後の授業を返す（付加情報なし。前後の空白の除去） | `test_patch_changes_only_given_fields_and_returns_subject` | 1 |
| 6つの項目をすべて変えられる | `test_patch_can_change_all_editable_fields` | 1 |
| 教室・メモを `null` にできる（今日以降の予定も `null`） | `test_patch_can_clear_room_and_notes` | 4 |
| 今日（を含む）以降は新しい値、今日より前は元の値 | `test_patch_rebuilds_events_from_today_with_new_values` | 1 |
| 曜日の変更は、今日以降の予定だけを動かす | `test_patch_weekday_moves_only_events_from_today` | 1 |
| 値が同じでも作り直し、今日以降の個別の変更・削除は戻る。今日より前の個別の変更は残る | `test_patch_restores_changed_and_deleted_future_events` | 1 |
| 単発の予定は変わらない。同じ日にも自動生成の予定を作る | `test_patch_keeps_one_off_events` | 1 |
| 休講日には作らない（ほかの学期の休講日は関係ない） | `test_patch_does_not_create_events_on_closures` | 1 |
| ほかの授業の予定・アルバイトは変わらない | `test_patch_does_not_change_other_subjects_or_part_time` | 1 |
| 同じ授業・同じ日付の自動生成の予定は1件まで | `test_repeated_patch_does_not_duplicate_generated_events` | 1 |
| 今日が学期の前なら、期間全体を作り直す | `test_patch_before_semester_rebuilds_all_events` | 1 |
| 今日が学期の後なら、予定は変わらない | `test_patch_after_semester_changes_only_subject` | 1 |
| 今日が学期の終了日なら、その日を作り直す | `test_patch_on_last_day_of_semester_rebuilds_that_day` | 1 |
| 作り直しの途中の例外では、何も保存しない（1回のcommit） | `test_patch_failure_during_rebuild_saves_nothing` | 1 |
| `{}` は400（`fields` なし） | `test_patch_empty_object_is_validation_error_without_fields` | 1 |
| 各項目の検証は、登録と同じ（必須の項目の `null`・空文字、型、文字数、範囲、形式、使用できない文字） | `test_patch_field_values_are_validated_like_post` | 20 |
| `semester_id`・`id`・付加情報・未知の項目は400（学期は変わらない） | `test_patch_rejects_semester_id_and_unknown_fields` | 6 |
| 時刻の前後は、変更後の値どうし（本文にない時刻は今の値）。違反は `end_time` | `test_patch_end_time_must_be_after_start_time_after_change` | 3 |
| 前後が正しければ、時刻を変えられる | `test_patch_time_change_is_accepted_when_order_is_valid` | 3 |
| 開始時刻に誤りがあれば、前後を比べない | `test_patch_invalid_start_time_skips_time_order_validation` | 1 |
| 誤りは、まとめて返す | `test_patch_validation_errors_are_returned_together` | 1 |
| 検証の誤りでは、授業も予定も変わらない | `test_failed_patch_changes_neither_subject_nor_events` | 1 |
| 本文がオブジェクトでない | `test_patch_non_object_payload_has_no_fields` | 4 |
| JSONが読めない・`Content-Type` が違う | `test_patch_invalid_json_or_content_type_is_rejected` | 3 |
| 404の使い分け（「授業が見つかりません」と「URLが見つかりません」） | `test_patch_not_found_and_invalid_urls` | 5 |
| 上限を超えるIDの `PATCH`・`DELETE` は405（「404の使い分け」の注意） | `test_over_limit_id_for_patch_and_delete_is_method_not_allowed` | 4 |
| 授業がなければ、本文を読む前に404 | `test_patch_missing_subject_is_404_before_reading_body` | 1 |
| 削除：その授業の予定（自動生成・単発、過去分を含む）と課題が消える | `test_delete_subject_removes_its_events_and_tasks` | 1 |
| 削除：`subject_id` が `NULL` の行として残らない | `test_delete_subject_leaves_no_rows_without_subject` | 1 |
| 削除：ほかの授業の予定・課題、授業のない予定・課題、学期、休講日は残る | `test_delete_subject_keeps_other_rows` | 1 |
| 削除は本文を読まない | `test_delete_subject_ignores_body` | 1 |
| 削除した授業を、もう一度削除すると404 | `test_deleted_subject_cannot_be_deleted_again` | 1 |
| 削除の404の使い分け | `test_delete_not_found_and_invalid_urls` | 5 |
| 一覧のURLの `DELETE` は405 | `test_delete_collection_url_is_not_allowed` | 1 |
| 合計 | | **86** |

## 変更してよい既存のテスト

| ファイル | 変えてよいこと | 変えないこと |
|---|---|---|
| `tests/test_subjects_api.py` | 2-2の2件（付録Dの全文のとおり） | ほかのテスト。特に、授業の登録の検証・保存のテストは、検証を `validate_subject_values` に移したあとも、変えずに通ること（移した処理が、元と同じ挙動であることの確認） |
| `tests/test_class_events.py` | `import` に `build_class_events_from` を足し、末尾にテストを足すこと（付録Bの全文のとおり） | 既存の19件 |

- このタスクでの「既存のテスト」は、作業の開始時からあるすべてのテスト（478件）。上の2件を除き、**既存のテストが、想定外に失敗した場合**は、テストの期待値や、ほかの仕様を直さない。原因を調べ、そこで実装を止めて、チャットで報告する

## 実装手順
1. ブランチ・作業ツリーの確認。設計資料が更新されていることを確認する（「Copilot確認手順」の1の `grep`）。更新されていなければ、何も変更せずに停止して報告する
2. 作業の前の状態を記録する：開発用DBの有無・ハッシュ・件数（「Copilot確認手順」の1。**`sqlite3` は `-readonly` を付ける**）。`python -m pytest -q` が478件、すべて合格すること（合格しなければ、何も変更せずに停止して報告する）
3. **（段階1）** 「全文からファイルを作るスクリプト」を `python - 1` で実行する。`python -m pytest -q` が484件、すべて合格すること。「全文との比較」（「Copilot確認手順」の4）を `python - 1` で実行し、2ファイルとも「一致」
4. **（段階2）** スクリプトを `python - 2` で実行する。`python -m pytest -q` が569件、すべて合格すること。「全文との比較」を `python - 2` で実行し、5ファイルとも「一致」
5. 「Copilot確認手順」の2・3・5・6を実施する
6. 結果を報告して、応答を終える（サーバーを起動していないこと、`curl` での確認をしていないことを明記する）

各段階の終わりに、`python -m pytest -q` の結果（件数・警告）と、全文との比較の結果を控えておく（最終報告に書く）。

## 完了条件
- `python -m pytest -q` が、作業の前に **478件**、段階1の終わりに **484件**、段階2の終わりに **569件**、すべて合格する（失敗・エラー・スキップが0件）
- 変更したファイルが、「実装対象ファイル」の5つだけ
- 5ファイルが、このTask MDの全文と1文字も違わない（「Copilot確認手順」の4が、段階1の終わりに2ファイル、段階2の終わりに5ファイルとも「一致」）
- `app/`・`tests/`・`run.py` のPythonのファイルに、79文字を超える行がない
- 実施の前後で、開発用DB（`instance/app.db`）のハッシュと、`semesters`・`subjects`・`closures`・`events`・`tasks` の件数が同じ
- 「Komaの確認」が、期待どおり
- レビューで承認される

## Copilot確認手順
**`sqlite3` は、必ず `-readonly` を付けて実行する**（付けずに開くと、読むだけでも、開発用DBを書き込み可能な状態で開くことになる。011-L1）。

```
# 1. 実施前
git branch --show-current      # feature/014-subject-edit-delete-api
git status                     # 変更なし
grep -n "#### 授業全体の編集による作り直し" docs/architecture.md     # 1件
grep -n "授業編集時の「今日」の基準\|授業削除時のEvent・Task削除方式" docs/architecture.md   # 出力なし（未決定事項から外れている）
grep -n "build_class_events_from" docs/architecture.md             # 数件
grep -n "レスポンスの付加情報" docs/architecture.md                 # 数件
grep -n "止まる場面の応答" .github/copilot-instructions.md         # 数件
ls -l instance/app.db          # 存在すること（なければ、何も変更せずに停止して報告する）
shasum -a 256 instance/app.db
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"
python -m pytest -q            # 478 passed

# 2. 各段階の終わり
python -m pytest -q            # 段階1：484 passed、段階2：569 passed
python -m pytest -q --co tests/test_class_events.py | tail -1                  # 段階1・2：25 tests collected
python -m pytest -q --co tests/test_subjects_api.py | tail -1                  # 段階2：146 tests collected
python -m pytest -q --co tests/test_subjects_update_delete_api.py | tail -1    # 段階2：86 tests collected

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
    "1": ["app/class_events.py", "tests/test_class_events.py"],
    "2": [
        "app/routes/subjects.py",
        "tests/test_subjects_api.py",
        "tests/test_subjects_update_delete_api.py",
    ],
}

stage = sys.argv[1]
# このTask MDの「<!-- 全文: パス -->」の直後のコードブロックを、
# そのファイルの期待する全文として取り出し、今のファイルと比べる。
fence = "`" * 3
task_text = Path("docs/tasks/014_subject_edit_delete_api.md").read_text(
    encoding="utf-8"
)
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
grep -rn "cascade\|ondelete" app/                      # 出力なし
grep -rn "date.today" app/                             # 1件：app/routes/subjects.py の current_date の中
grep -n "@subjects_bp\." app/routes/subjects.py        # 5件：get・get・post・patch・delete の順
grep -n "current_date()" app/routes/subjects.py        # 2件：定義と、update_subject の中の呼び出し
grep -n "commit()" app/routes/subjects.py              # 3件：登録・編集・削除で1回ずつ
grep -n "add_all" app/routes/subjects.py               # 2件：登録・編集
grep -n "db.delete(\|session.delete(" app/routes/subjects.py   # 4件：編集の予定の削除、削除の予定・課題・授業
git diff --numstat app/class_events.py tests/test_class_events.py tests/test_subjects_api.py   # 26 2、75 0、6 2
git diff --stat -- app/models/ app/api_helpers.py app/__init__.py app/routes/semesters.py app/routes/closures.py app/routes/events.py app/routes/main.py app/static/ app/templates/ migrations/ tests/conftest.py tests/test_api_helpers.py tests/test_closures_api.py tests/test_events_api.py tests/test_semesters_api.py tests/test_setup.py requirements.txt pytest.ini run.py   # 出力なし

# 6. 実施後
shasum -a 256 instance/app.db  # 実施前と同じ
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"   # 実施前と同じ
git status                     # 変更：4つ。新規：tests/test_subjects_update_delete_api.py
git diff --stat
```

| 確認 | 期待する結果 |
|---|---|
| `python -m pytest -q` | 実施前478件、段階1の終わり484件、段階2の終わり569件が、すべて合格。失敗・エラー・スキップが0件。`migrations/env.py` の `DeprecationWarning` は、出ても構わない（報告する） |
| 1行の長さ（3） | 出力なし |
| 全文との比較（4） | `全文の数：5` と、段階1の終わりは2ファイル、段階2の終わりは5ファイルとも「一致」。「不一致」が出たら、手で直さず、その段階の「全文からファイルを作るスクリプト」をもう一度実行して全文に戻し、2からやり直す（戻したことを報告する）。Task MDの全文のほうを変える必要があると判断した場合は、停止して報告する |
| 検索と差分（5） | 上のコメントのとおり（件数が違う場合は、その行を報告に書く） |
| 開発用DB | 実施の前後で、ハッシュと、5つのテーブルの件数が同じ |
| `git status` | 変更：`app/class_events.py`、`app/routes/subjects.py`、`tests/test_class_events.py`、`tests/test_subjects_api.py`。新規：`tests/test_subjects_update_delete_api.py`。`app/models/`・`migrations/`・`app/static/`・`app/templates/`・`docs/`・`.github/`・`requirements.txt`・`run.py`・`instance/` に変更なし |

`.pytest_cache/` や `__pycache__/` が `git status` に表示される場合は、`.gitignore` を変更せず、報告する。**Copilotは、サーバーを起動せず、`curl` での確認もしない。** 報告に、そのことを明記する。

## Komaの確認
順序：（1）pytest →（2）commit・push とレビューの依頼 →（3）APIの確認（確認用のサーバー）→（4）マージ。**ブラウザでの確認は、このタスクにはない**（画面を変えないため。roadmap の「進め方の決定の記録」、2026-10-11）。

### 1. pytest
`python -m pytest -q` を自分で実行し、**569件、すべて合格**することを確かめる。

### 2. push とレビューの依頼
featureブランチを commit・push する（PRを作ってもよい）。Copilotの完了報告を共有して、Claudeにレビューを頼む。**pushは、マージではない。レビューの承認の前に、マージしない。** 修正が必要になった場合は、同じブランチでCopilotが直し、もう一度pushしてレビューを受ける。

### 3. APIの確認（確認用のサーバー）
レビューで「承認可能」になったあとに行う。**開発用DBは使わない。** 確認用のDB（`/tmp/schedule-app-check-014/check.db`）を、migrationで作り、そのDBで起動した確認用のサーバーに、`curl` で要求する（Task 012と同じ方法）。開発用DBには、何も残らない。

この確認では、サーバーの「今日」（確認する日の、Macの日付）で、予定が作り直されることを確かめる。学期は「2026年度 後期」（2026-09-21〜2027-01-29）にする（**2027-01-29までに確認する**。今日が学期の中にあるため）。

#### 準備
1. `python run.py` が起動していれば、Ctrl＋Cで止める（確認用のサーバーも、5001番を使うため）。開発用DBのハッシュを控える
   ```
   shasum -a 256 instance/app.db
   ```
2. ブランチ `feature/014-subject-edit-delete-api` のまま、リポジトリのルートで、`.venv` を有効にして、次を実行する（行の先頭に空白を入れずにコピーする。このターミナルは、確認の間、開いたままにする）

```
python - <<'EOF'
from pathlib import Path

from flask_migrate import upgrade

from app import create_app

# 確認用のDB（開発用DBとは別のファイル）。止めて起動し直しても、残る。
check_directory = Path("/tmp/schedule-app-check-014")
check_directory.mkdir(exist_ok=True)
database_path = check_directory / "check.db"
app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"})
with app.app_context():
    upgrade(directory="migrations")
print(f"確認用のDB：{database_path}", flush=True)
app.run(host="127.0.0.1", port=5001, debug=False)
EOF
```

期待する出力：`Running upgrade  -> 0280f6cf8d09, initial tables` と `Running upgrade 0280f6cf8d09 -> 42bd53808fa1, add closures table`、「確認用のDB：/tmp/schedule-app-check-014/check.db」、`Running on http://127.0.0.1:5001`。

3. 別のターミナルを開き、リポジトリのルートで、`.venv` を有効にして、`BASE=http://127.0.0.1:5001` を実行しておく

#### 確認（別のターミナルで、上から順に実行する）
B1〜B3は、確認用のDBに、学期・休講日・授業を1件ずつ登録する（授業の登録で、予定が18件作られる）。

```
# B1. 学期（2026-09-21〜2027-01-29）
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X POST $BASE/api/semesters -H 'Content-Type: application/json' -d '{"name": "2026年度 後期", "start_date": "2026-09-21", "end_date": "2027-01-29"}'
# B2. 休講日（2026-11-23）
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X POST $BASE/api/closures -H 'Content-Type: application/json' -d '{"semester_id": 1, "date": "2026-11-23", "name": "勤労感謝の日"}'
# B3. 月曜日の授業（9:00〜10:30）
curl -s -X POST $BASE/api/subjects -H 'Content-Type: application/json' -d '{"semester_id": 1, "subject_name": "テスト：月曜1限", "weekday": 0, "start_time": "09:00", "end_time": "10:30", "room": "3号館201"}' | python -m json.tool --no-ensure-ascii
# B4. 1件取得（件数つき）
curl -s $BASE/api/subjects/1 | python -m json.tool --no-ensure-ascii
# B5. 授業全体の編集（科目名と時刻）
curl -s -X PATCH $BASE/api/subjects/1 -H 'Content-Type: application/json' -d '{"subject_name": "テスト：月曜2限", "start_time": "10:40", "end_time": "12:10"}' | python -m json.tool --no-ensure-ascii
# B6. 予定を、今日より前と、今日以降に分けて数える（2つのコマンド）
curl -s "$BASE/api/events?start_date=2026-09-21&end_date=2027-01-29" -o /tmp/schedule-app-check-014/events.json
python - <<'EOF'
import json
from datetime import date
from pathlib import Path

today = date.today().isoformat()
events = json.loads(Path("/tmp/schedule-app-check-014/events.json").read_text())
before = [e for e in events if e["date"] < today]
after = [e for e in events if e["date"] >= today]
print("今日", today)
print("今日より前", len(before), sorted({(e["title"], e["start_time"], e["end_time"]) for e in before}))
print("今日以降", len(after), sorted({(e["title"], e["start_time"], e["end_time"]) for e in after}))
print("合計", len(events), "日付の重複", len(events) - len({e["date"] for e in events}))
EOF
# B7. 空の本文
curl -s -X PATCH $BASE/api/subjects/1 -H 'Content-Type: application/json' -d '{}' | python -m json.tool --no-ensure-ascii
# B8. 学期は変えられない
curl -s -X PATCH $BASE/api/subjects/1 -H 'Content-Type: application/json' -d '{"semester_id": 2}' | python -m json.tool --no-ensure-ascii
# B9. 終了時刻だけを、今の開始時刻（10:40）より前にする
curl -s -X PATCH $BASE/api/subjects/1 -H 'Content-Type: application/json' -d '{"end_time": "10:00"}' | python -m json.tool --no-ensure-ascii
# B10. 存在しない授業の編集
curl -s -X PATCH $BASE/api/subjects/99999 -H 'Content-Type: application/json' -d '{"subject_name": "x"}' | python -m json.tool --no-ensure-ascii
# B11. 授業の削除
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X DELETE $BASE/api/subjects/1
# B12. 削除のあと（授業・予定・休講日）
curl -s $BASE/api/subjects/1 | python -m json.tool --no-ensure-ascii
curl -s "$BASE/api/events?start_date=2026-09-21&end_date=2027-01-29"; echo
curl -s $BASE/api/closures | python -m json.tool --no-ensure-ascii
# B13. もう一度削除
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X DELETE $BASE/api/subjects/1
```

| No | 期待する結果 |
|---|---|
| B1・B2 | `HTTP 201` |
| B3 | `"generated_event_count": 18`（2026-09-21〜2027-01-25の月曜日19日から、休講日の11/23を除く）、`"id": 1` |
| B4 | B3の授業の項目に、`"event_count": 18` と `"task_count": 0` が付く。`generated_event_count` はない |
| B5 | `"subject_name": "テスト：月曜2限"`、`"start_time": "10:40"`、`"end_time": "12:10"`、`"room": "3号館201"`（変えていない項目は、そのまま）、`"semester_id": 1`。`event_count`・`generated_event_count` はない |
| B6 | 1行目に、確認した日の「今日」。「今日より前」の件数と「今日以降」の件数の合計が18で、「日付の重複 0」。「今日より前」は `('テスト：月曜1限', '09:00', '10:30')` だけ、「今日以降」は `('テスト：月曜2限', '10:40', '12:10')` だけ。例：2026-10-13（火）〜10-19（月）に確認した場合は、「今日より前 4」と「今日以降 14」（9/21・9/28・10/5・10/12の4件は、編集の前の値のまま。今日が月曜日なら、今日の予定は「今日以降」に入る） |
| B7 | `validation_error`、`"message": "変更する項目を指定してください"`、`fields` はない |
| B8 | `validation_error`、`fields` に `"semester_id": "この項目は指定できません"` だけ |
| B9 | `validation_error`、`fields` に `"end_time": "終了時刻は開始時刻より後にしてください"` だけ |
| B10 | `not_found`、`"message": "授業が見つかりません"` |
| B11 | `HTTP 204` |
| B12 | 1つ目：`not_found`、「授業が見つかりません」。2つ目：`[]`（予定が残っていない）。3つ目：休講日の1件（`"date": "2026-11-23"`）が残る |
| B13 | `HTTP 404` |

（応答の項目は、Flaskが項目名の順に並べて返すため、表示の順は、設計資料の例と違う。中身が同じなら、期待どおり）

#### 後片付け
1. 確認用のサーバーを止める（Ctrl＋C）
2. 確認用のDBのフォルダを消す
   ```
   rm -r /tmp/schedule-app-check-014
   ```
3. 開発用DBのハッシュが、準備の1と同じことを確かめる
   ```
   shasum -a 256 instance/app.db
   ```

ハッシュが変わっていた場合は、開発用DBを操作せずに、Claudeに伝える。

### 4. マージ
1〜3が期待どおりで、レビューで承認されたら、マージする。このタスクは、DBの構造を変えないため、開発用DBへのmigrationの適用はない。開発用DBのデータも変えないため、バックアップは要らない。

マージのあとは、開発用DBのサーバー（`python run.py`）でも、授業の `PATCH`・`DELETE` が使える。画面はまだないため、開発用DBの授業を、APIで編集・削除する場合は、先にバックアップを取る（`docs/architecture.md` の「開発中の注意」）。

## Git操作
**Git commit / push / ブランチ操作 / マージは行わない**（`git branch --show-current`、`git status`、`git diff` のような読み取りだけのコマンドは除く）。

## 注意
- **停止して報告する条件**（ファイルを変更せず、実装を止め、チャットで「問題点・発生理由・変更した場合の影響・推奨案（必要なら）」を報告する）
  - ブランチの不一致、作業ツリーの想定外の変更
  - 設計資料が更新されていない（実装手順の1）、または、設計資料とこのTask MDの間に、矛盾・不足がある
  - 設計資料にない判断が必要になった（特に、`docs/architecture.md` の「未決定事項」（「学期の変更・削除時の扱い」など）に触れる場合）
  - 「全文からファイルを作るスクリプト」の出力が、期待と違う（全文の数・行数・エラー）
  - 「変更しない」と定めたもの（モデル、`api_helpers.py`、ほかのroute、画面のファイル、既存のテストの2-2以外の部分など）を変更しないと実装できない。または、5ファイルの全文を変える必要があると判断した
  - 開発用DB（`instance/app.db`）がない
  - 作業の前の `python -m pytest` が、478件すべて合格しない
  - **既存のテスト**（作業の開始時からある478件。2-2の2件を除く）**が、想定外に失敗した**。テストの期待値や、ほかの仕様を直さずに、原因を調べて報告する
  - テストの結果が、実行した日によって変わると判断した（「今日」を固定していないテストがある、など）
  - DBの構造の変更（migration）や、モデルの変更（`cascade` など）、このTask MDに書いたもの以外のAPIの変更が必要だと判断した
  - 実施の前後で、`instance/app.db` が変わった
- **止まるときは、報告を書いて、その応答を終える。質問の機能は使わない。** 再開するのは、Komaの新しいメッセージが、判断や再開を明確に示したときだけ（無回答や「続けて」だけの返事は、再開の指示ではない）。`.github/copilot-instructions.md` の「止まる場面の応答」
- **開発用DBを `sqlite3` で開くときは、必ず `-readonly` を付ける**（SELECTだけでも、付けずに開かない。011-L1）。`flask db` のコマンドを、一切実行しない。ライブラリを追加しない。サーバーを起動しない（`python run.py` も、「Komaの確認」の確認用のサーバーも）
- 期待する結果と異なる結果が出た場合は、確認を飛ばさず、原因を直してから、すべての確認をやり直す（ただし、既存のテストの想定外の失敗は、上の停止の条件に従う。全文との「不一致」は、手で直さず、スクリプトで全文に戻す）
- 設計資料に書かれていない仕様は、自分で決めない
- 最後の報告に、次を含める：変更したファイル、「全文からファイルを作るスクリプト」の出力（段階1・2）、作業の前と各段階の `pytest` の件数と警告、1行の長さの確認の結果、全文との比較の結果（段階1：2ファイル、段階2：5ファイルの「一致」。スクリプトで全文に戻した場合は、そのこと）、検索と差分の結果、開発用DBの前後のハッシュ・件数、`git status`・`git diff --stat`、サーバーの起動と `curl` の確認をしていないこと、気になった点

## 付録：全文
「全文からファイルを作るスクリプト」と「全文との比較」が使う。各ファイルの全文は、「`<!-- 全文: パス -->`」の印の直後のコードブロック。**この付録を、手で書き写さない。** 本文の要点・差分と食い違う場合は、作業をせずに停止して報告する。

### 付録A. `app/class_events.py`

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

### 付録B. `tests/test_class_events.py`

<!-- 全文: tests/test_class_events.py -->
```python
from datetime import date, time, timedelta

import pytest

from app.class_events import (
    EVENT_CATEGORY_CLASS,
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

### 付録C. `app/routes/subjects.py`

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

    payload, error_response = read_json_object()
    if error_response is not None:
        return error_response
    # 項目が1つもない本文（{}）は、誤りにする（API共通ルール）。
    if not payload:
        return api_error_response(
            "validation_error",
            "変更する項目を指定してください",
        )

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

### 付録D. `tests/test_subjects_api.py`

<!-- 全文: tests/test_subjects_api.py -->
```python
from datetime import date, time

import pytest
from sqlalchemy import func, select

from app.api_helpers import (
    INVALID_JSON_MESSAGE,
    MAX_ID,
    UNUSABLE_CHARACTER_MESSAGE,
)
from app.extensions import db
from app.models.closure import Closure
from app.models.event import Event
from app.models.semester import Semester
from app.models.subject import Subject
from app.models.task import Task


TIME_MESSAGES = {
    "start_time": {
        "required": "開始時刻は必須です",
        "format": (
            "開始時刻は「HH:MM」の形式（00:00〜23:59）で指定してください"
        ),
    },
    "end_time": {
        "required": "終了時刻は必須です",
        "format": (
            "終了時刻は「HH:MM」の形式（00:00〜23:59）で指定してください"
        ),
    },
}


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


def subject_payload(default_semester_id, **overrides):
    payload = {
        "semester_id": default_semester_id,
        "subject_name": "プログラミング基礎",
        "weekday": 0,
        "start_time": "09:00",
        "end_time": "10:00",
    }
    payload.update(overrides)
    return payload


def assert_validation_error(response, fields):
    assert response.status_code == 400
    assert response.json == {
        "error": {
            "code": "validation_error",
            "message": "入力内容に誤りがあります",
            "fields": fields,
        }
    }


def subject_count(app):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(Subject))


def event_count(app):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(Event))


def generated_event_dates(app, subject_id):
    """授業の自動生成の予定の日付を、昇順で返す（同じ日付が2件あれば2回）。"""
    with app.app_context():
        return list(
            db.session.scalars(
                select(Event.date)
                .where(
                    Event.subject_id == subject_id,
                    Event.is_generated.is_(True),
                )
                .order_by(Event.date)
            )
        )


def make_closure(app, semester_id, closure_date):
    with app.app_context():
        db.session.add(Closure(semester_id=semester_id, date=closure_date))
        db.session.commit()


def test_subject_creation_returns_all_fields_and_matches_database(
    client, app
):
    semester_id = make_semester(app)
    payload = subject_payload(
        semester_id,
        subject_name="  プログラミング基礎　",
        room="  3号館201  ",
        weekday=2,
        start_time="09:15",
        end_time="10:45",
        notes="  前期の授業  ",
    )

    response = client.post("/api/subjects", json=payload)
    assert response.status_code == 201
    assert response.json == {
        "id": response.json["id"],
        "semester_id": semester_id,
        "subject_name": "プログラミング基礎",
        "room": "3号館201",
        "weekday": 2,
        "start_time": "09:15",
        "end_time": "10:45",
        "notes": "前期の授業",
        "generated_event_count": 18,
    }

    with app.app_context():
        subject = db.session.get(Subject, response.json["id"])
        assert subject is not None
        assert subject.semester_id == semester_id
        assert subject.subject_name == "プログラミング基礎"
        assert subject.room == "3号館201"
        assert subject.weekday == 2
        assert subject.start_time == time(9, 15)
        assert subject.end_time == time(10, 45)
        assert subject.notes == "前期の授業"


def test_subject_creation_with_required_fields_uses_null_optional_values(
    client, app
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id),
    )
    assert response.status_code == 201
    assert set(response.json) == {
        "id",
        "semester_id",
        "subject_name",
        "room",
        "weekday",
        "start_time",
        "end_time",
        "notes",
        "generated_event_count",
    }
    assert response.json["room"] is None
    assert response.json["notes"] is None


@pytest.mark.parametrize("empty_value", ["", "  ", "　", None])
def test_optional_subject_strings_normalize_empty_to_null(
    client, app, empty_value
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(
            semester_id,
            room=empty_value,
            notes=empty_value,
        ),
    )
    assert response.status_code == 201
    assert response.json["room"] is None
    assert response.json["notes"] is None


def test_subject_string_length_limits_and_unlimited_notes(client, app):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(
            semester_id,
            subject_name="  " + "科" * 100 + "  ",
            room="教" * 100,
            notes="詳" * 10000,
        ),
    )
    assert response.status_code == 201
    assert len(response.json["subject_name"]) == 100
    assert len(response.json["room"]) == 100
    assert len(response.json["notes"]) == 10000


@pytest.mark.parametrize(
    ("weekday", "start_time", "end_time"),
    [(0, "00:00", "00:01"), (6, "23:58", "23:59"), (3, "07:30", "21:45")],
)
def test_subject_accepts_weekday_and_time_boundaries(
    client, app, weekday, start_time, end_time
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(
            semester_id,
            weekday=weekday,
            start_time=start_time,
            end_time=end_time,
        ),
    )
    assert response.status_code == 201
    assert response.json["weekday"] == weekday
    assert response.json["start_time"] == start_time
    assert response.json["end_time"] == end_time


def test_duplicate_subject_rows_are_allowed_and_each_get_events(
    client, app
):
    semester_id = make_semester(app)
    payload = subject_payload(semester_id)
    first = client.post("/api/subjects", json=payload)
    second = client.post("/api/subjects", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json["id"] != second.json["id"]
    # 同じ内容の授業を2回登録すると、それぞれに予定が1組ずつ作られる。
    assert first.json["generated_event_count"] == 17
    assert second.json["generated_event_count"] == 17
    assert generated_event_dates(app, first.json["id"]) == (
        generated_event_dates(app, second.json["id"])
    )
    with app.app_context():
        assert db.session.scalar(
            select(func.count()).select_from(Event)
        ) == 34
        assert db.session.scalar(
            select(func.count()).select_from(Task)
        ) == 0


def test_empty_subject_payload_reports_all_required_fields(client):
    response = client.post("/api/subjects", json={})
    assert_validation_error(
        response,
        {
            "semester_id": "学期IDは必須です",
            "subject_name": "科目名は必須です",
            "weekday": "曜日は必須です",
            "start_time": "開始時刻は必須です",
            "end_time": "終了時刻は必須です",
        },
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("semester_id", None, "学期IDは必須です"),
        ("semester_id", "", "学期IDは必須です"),
        ("semester_id", "1", "学期IDは整数で指定してください"),
        ("semester_id", True, "学期IDは整数で指定してください"),
        ("semester_id", False, "学期IDは整数で指定してください"),
        ("semester_id", 1.5, "学期IDは整数で指定してください"),
        ("semester_id", [1], "学期IDは整数で指定してください"),
        ("semester_id", {}, "学期IDは整数で指定してください"),
        ("subject_name", "", "科目名は必須です"),
        ("subject_name", "   ", "科目名は必須です"),
        ("subject_name", "　", "科目名は必須です"),
        ("subject_name", None, "科目名は必須です"),
        ("subject_name", 123, "科目名は文字列で指定してください"),
        ("subject_name", True, "科目名は文字列で指定してください"),
        ("subject_name", [], "科目名は文字列で指定してください"),
        ("weekday", None, "曜日は必須です"),
        ("weekday", "", "曜日は必須です"),
        ("weekday", "1", "曜日は0（月曜）〜6（日曜）の整数で指定してください"),
        ("weekday", True, "曜日は0（月曜）〜6（日曜）の整数で指定してください"),
        ("weekday", 1.0, "曜日は0（月曜）〜6（日曜）の整数で指定してください"),
        ("weekday", [0], "曜日は0（月曜）〜6（日曜）の整数で指定してください"),
    ],
)
def test_required_subject_fields_validate_missing_and_types(
    client, app, field, value, message
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, **{field: value}),
    )
    assert_validation_error(response, {field: message})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("room", 123, "教室は文字列で指定してください"),
        ("room", True, "教室は文字列で指定してください"),
        ("notes", 123, "詳細・メモは文字列で指定してください"),
        ("notes", True, "詳細・メモは文字列で指定してください"),
    ],
)
def test_optional_subject_fields_validate_types(
    client, app, field, value, message
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, **{field: value}),
    )
    assert_validation_error(response, {field: message})


@pytest.mark.parametrize(
    "semester_id",
    [0, -1, MAX_ID + 1, 10**30, 99999, MAX_ID],
)
def test_invalid_or_missing_semester_references_are_validation_errors(
    client, app, semester_id
):
    make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id),
    )
    assert_validation_error(
        response,
        {"semester_id": "指定された学期が存在しません"},
    )


@pytest.mark.parametrize("weekday", [-1, 7, 100])
def test_weekday_out_of_range_is_rejected(client, app, weekday):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, weekday=weekday),
    )
    assert_validation_error(
        response,
        {"weekday": "曜日は0（月曜）〜6（日曜）の整数で指定してください"},
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("subject_name", "科" * 101, "科目名は100文字以内にしてください"),
        ("room", "教" * 101, "教室は100文字以内にしてください"),
    ],
)
def test_subject_name_and_room_over_length_are_rejected(
    client, app, field, value, message
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, **{field: value}),
    )
    assert_validation_error(response, {field: message})


@pytest.mark.parametrize("field", ["start_time", "end_time"])
@pytest.mark.parametrize("value", [None, ""])
def test_missing_subject_times_are_required(client, app, field, value):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, **{field: value}),
    )
    assert_validation_error(
        response,
        {field: TIME_MESSAGES[field]["required"]},
    )


@pytest.mark.parametrize("field", ["start_time", "end_time"])
@pytest.mark.parametrize(
    "value",
    [
        900,
        True,
        "9:00",
        "09:0",
        "0900",
        "09:00:00",
        "24:00",
        "09:60",
        "ab:cd",
        " 09:00",
        "09:00 ",
        "09:00\n",
        "０９：００",
    ],
)
def test_malformed_subject_times_are_rejected(client, app, field, value):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, **{field: value}),
    )
    assert_validation_error(
        response,
        {field: TIME_MESSAGES[field]["format"]},
    )


@pytest.mark.parametrize(
    ("start_time", "end_time"),
    [("09:00", "09:00"), ("10:00", "09:59")],
)
def test_end_time_must_be_after_start_time(
    client, app, start_time, end_time
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(
            semester_id,
            start_time=start_time,
            end_time=end_time,
        ),
    )
    assert_validation_error(
        response,
        {"end_time": "終了時刻は開始時刻より後にしてください"},
    )


def test_invalid_start_time_skips_time_order_validation(client, app):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(
            semester_id,
            start_time="invalid",
            end_time="08:00",
        ),
    )
    assert_validation_error(
        response,
        {
            "start_time": (
                "開始時刻は「HH:MM」の形式（00:00〜23:59）で指定してください"
            )
        },
    )


@pytest.mark.parametrize("field", ["color", "id", "events"])
def test_unknown_subject_fields_are_rejected(client, app, field):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, **{field: "unexpected"}),
    )
    assert_validation_error(response, {field: "この項目は指定できません"})


def test_multiple_subject_validation_errors_are_returned_together(client, app):
    make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(
            99999,
            weekday=7,
            start_time="10:00",
            end_time="09:00",
        ),
    )
    assert_validation_error(
        response,
        {
            "semester_id": "指定された学期が存在しません",
            "weekday": "曜日は0（月曜）〜6（日曜）の整数で指定してください",
            "end_time": "終了時刻は開始時刻より後にしてください",
        },
    )


@pytest.mark.parametrize("payload", [[], "abc", 123, True])
def test_non_object_subject_payload_has_no_fields(client, payload):
    response = client.post("/api/subjects", json=payload)
    assert response.status_code == 400
    assert response.json == {
        "error": {
            "code": "validation_error",
            "message": "リクエストの本文は、JSONのオブジェクトにしてください",
        }
    }


def test_null_subject_payload_has_no_fields(client):
    response = client.post(
        "/api/subjects",
        data="null",
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_error"
    assert "fields" not in response.json["error"]


@pytest.mark.parametrize(
    ("data", "content_type"),
    [
        ('{"subject_name":', "application/json"),
        ('{"subject_name":"x"}', "text/plain"),
        ('{"subject_name":"x"}', None),
    ],
)
def test_invalid_json_or_content_type_is_rejected(client, data, content_type):
    response = client.post(
        "/api/subjects",
        data=data,
        content_type=content_type,
    )
    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_json"


def test_json_charset_is_accepted(client, app):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        data=(
            '{"semester_id":'
            f'{semester_id},"subject_name":"科目","weekday":0,'
            '"start_time":"09:00","end_time":"10:00"}'
        ),
        content_type="application/json; charset=utf-8",
    )
    assert response.status_code == 201


def test_failed_subject_post_does_not_change_row_count(client, app):
    semester_id = make_semester(app)
    before_count = subject_count(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, weekday=9),
    )
    assert response.status_code == 400
    assert subject_count(app) == before_count


def test_empty_subject_list_returns_empty_array(client):
    response = client.get("/api/subjects")
    assert response.status_code == 200
    assert response.json == []


def test_subject_list_orders_by_weekday_time_and_id_and_filters_semester(
    client, app
):
    first_semester_id = make_semester(app, "2026年度 前期")
    second_semester_id = make_semester(app, "2026年度 後期")
    entries = [
        (first_semester_id, "水曜遅", 2, time(10, 0)),
        (first_semester_id, "水曜早2", 2, time(9, 0)),
        (first_semester_id, "水曜早1", 2, time(9, 0)),
        (second_semester_id, "火曜", 1, time(12, 0)),
        (second_semester_id, "月曜遅", 0, time(10, 0)),
        (second_semester_id, "月曜早", 0, time(8, 0)),
    ]
    created_ids = {}
    with app.app_context():
        for semester_id, name, weekday, start_time in entries:
            subject = Subject(
                semester_id=semester_id,
                subject_name=name,
                weekday=weekday,
                start_time=start_time,
                end_time=time(start_time.hour + 1, start_time.minute),
            )
            db.session.add(subject)
            db.session.flush()
            created_ids[name] = subject.id
        db.session.commit()

    all_subjects = client.get("/api/subjects")
    assert all_subjects.status_code == 200
    assert [subject["subject_name"] for subject in all_subjects.json] == [
        "月曜早",
        "月曜遅",
        "火曜",
        "水曜早2",
        "水曜早1",
        "水曜遅",
    ]
    assert all_subjects.json[3]["id"] == created_ids["水曜早2"]
    assert all_subjects.json[4]["id"] == created_ids["水曜早1"]

    filtered = client.get(
        f"/api/subjects?semester_id={first_semester_id}"
    )
    assert {item["semester_id"] for item in filtered.json} == {
        first_semester_id
    }
    assert len(filtered.json) == 3


@pytest.mark.parametrize(
    "semester_text",
    [
        "",
        "abc",
        "-1",
        "1.5",
        "１",
        " 1",
        "1 ",
    ],
)
def test_invalid_semester_id_query_is_validation_error(client, semester_text):
    response = client.get(f"/api/subjects?semester_id={semester_text}")
    assert_validation_error(
        response,
        {"semester_id": "学期IDは整数で指定してください"},
    )


def test_repeated_semester_id_query_is_validation_error(client):
    response = client.get("/api/subjects?semester_id=1&semester_id=2")
    assert_validation_error(
        response,
        {"semester_id": "学期IDは1つだけ指定してください"},
    )


@pytest.mark.parametrize(
    "semester_text",
    [
        "0",
        "000",
        str(MAX_ID + 1),
        "99999999999999999999",
        "9" * 5000,
        "99999",
    ],
)
def test_out_of_range_or_missing_semester_query_returns_empty(
    client, semester_text
):
    response = client.get(f"/api/subjects?semester_id={semester_text}")
    assert response.status_code == 200
    assert response.json == []


def test_leading_zero_semester_query_and_unknown_query(client, app):
    semester_id = make_semester(app)
    with app.app_context():
        db.session.add(
            Subject(
                semester_id=semester_id,
                subject_name="科目",
                weekday=0,
                start_time=time(9, 0),
                end_time=time(10, 0),
            )
        )
        db.session.commit()

    for zero_padded_id in ("001", "0000000000000000000001"):
        result = client.get(
            f"/api/subjects?semester_id={zero_padded_id}"
        )
        assert len(result.json) == 1
        assert result.json[0]["semester_id"] == semester_id
    assert len(client.get("/api/subjects?foo=bar").json) == 1


def test_subject_get_returns_created_subject(client, app):
    semester_id = make_semester(app)
    created = client.post(
        "/api/subjects",
        json=subject_payload(semester_id),
    )
    expected = dict(created.json)
    # 作成のレスポンスにだけ付ける付加情報は、1件取得には含めない。
    del expected["generated_event_count"]
    # 1件取得にだけ付ける付加情報（授業を削除すると一緒に削除される件数）。
    expected["event_count"] = 17
    expected["task_count"] = 0
    assert client.get(f"/api/subjects/{created.json['id']}").json == (
        expected
    )


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/subjects/99999", "授業が見つかりません"),
        ("/api/subjects/0", "授業が見つかりません"),
        (f"/api/subjects/{MAX_ID}", "授業が見つかりません"),
        (f"/api/subjects/{MAX_ID + 1}", "URLが見つかりません"),
        ("/api/subjects/99999999999999999999", "URLが見つかりません"),
        ("/api/subjects/abc", "URLが見つかりません"),
        ("/api/subjects/-1", "URLが見つかりません"),
        ("/api/subjects/", "URLが見つかりません"),
    ],
)
def test_subject_get_not_found_and_invalid_urls(client, url, message):
    response = client.get(url)
    assert response.status_code == 404
    assert response.json["error"] == {
        "code": "not_found",
        "message": message,
    }


@pytest.mark.parametrize(
    ("method", "url"),
    [
        # 1件のURLのPATCH・DELETEは、授業の編集・削除として提供する
        # （tests/test_subjects_update_delete_api.py）。
        ("put", "/api/subjects/{subject_id}"),
        ("put", "/api/subjects"),
        ("patch", "/api/subjects"),
        ("delete", "/api/subjects"),
        ("post", "/api/subjects/{subject_id}"),
    ],
)
def test_unsupported_subject_methods_do_not_change_rows(
    client, app, method, url
):
    semester_id = make_semester(app)
    with app.app_context():
        subject = Subject(
            semester_id=semester_id,
            subject_name="登録済み授業",
            weekday=0,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        db.session.add(subject)
        db.session.commit()
        subject_id = subject.id

    url = url.format(subject_id=subject_id)
    before_subject = client.get(f"/api/subjects/{subject_id}")
    assert before_subject.status_code == 200
    before_count = subject_count(app)
    response = getattr(client, method)(url)
    assert response.status_code == 405
    assert response.json["error"]["code"] == "method_not_allowed"
    after_subject = client.get(f"/api/subjects/{subject_id}")
    assert after_subject.json == before_subject.json
    assert subject_count(app) == before_count


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("subject_name", "\ud800"),
        ("subject_name", "  \ud800  "),
        ("room", "\udfff"),
        ("notes", "メモ\ud800"),
        ("start_time", "\ud800"),
        ("end_time", "09:00\udc00"),
    ],
)
def test_unusable_characters_in_subject_fields_are_rejected(
    client, app, field, value
):
    semester_id = make_semester(app)
    before_count = subject_count(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, **{field: value}),
    )
    assert_validation_error(
        response,
        {field: UNUSABLE_CHARACTER_MESSAGE},
    )
    assert subject_count(app) == before_count


def test_invalid_utf8_subject_body_is_invalid_json(client, app):
    semester_id = make_semester(app)
    before_count = subject_count(app)
    body = (
        f'{{"semester_id": {semester_id}, "subject_name": "'.encode()
        + b"\xff"
        + b'", "weekday": 0, "start_time": "09:00", "end_time": "10:00"}'
    )
    response = client.post(
        "/api/subjects",
        data=body,
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json["error"] == {
        "code": "invalid_json",
        "message": INVALID_JSON_MESSAGE,
    }
    assert subject_count(app) == before_count == 0


def test_surrogate_pairs_in_subject_strings_are_accepted(client, app):
    semester_id = make_semester(app)
    payload = subject_payload(
        semester_id,
        subject_name="😀" * 100,
        room="教室😀",
        notes="メモ😀",
    )
    response = client.post("/api/subjects", json=payload)
    assert response.status_code == 201
    assert response.json["subject_name"] == payload["subject_name"]
    assert response.json["room"] == payload["room"]
    assert response.json["notes"] == payload["notes"]


def test_surrogate_pairs_count_as_one_character_for_subject_name(
    client, app
):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, subject_name="😀" * 101),
    )
    assert_validation_error(
        response,
        {"subject_name": "科目名は100文字以内にしてください"},
    )


def test_unusable_character_and_other_errors_are_reported_together(
    client, app
):
    semester_id = make_semester(app)
    before_count = subject_count(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(
            semester_id,
            subject_name="\ud800",
            weekday=7,
        ),
    )
    assert_validation_error(
        response,
        {
            "subject_name": UNUSABLE_CHARACTER_MESSAGE,
            "weekday": "曜日は0（月曜）〜6（日曜）の整数で指定してください",
        },
    )
    assert subject_count(app) == before_count


def test_lone_surrogate_field_name_is_unknown_field(client, app):
    semester_id = make_semester(app)
    body = (
        f'{{"semester_id": {semester_id}, "subject_name": "科目", '
        '"weekday": 0, "start_time": "09:00", "end_time": "10:00", '
        '"\\ud800": 1}'
    )
    response = client.post(
        "/api/subjects",
        data=body,
        content_type="application/json",
    )
    assert_validation_error(
        response,
        {"\ud800": "この項目は指定できません"},
    )


def test_invalid_bytes_in_semester_id_query_are_validation_error(client):
    response = client.get("/api/subjects?semester_id=%ED%A0%80")
    assert_validation_error(
        response,
        {"semester_id": "学期IDは整数で指定してください"},
    )


# --- 授業の登録による予定（Event）の自動生成（Task 011） ---


def test_subject_creation_generates_events_with_subject_values(client, app):
    semester_id = make_semester(app)
    response = client.post(
        "/api/subjects",
        json=subject_payload(
            semester_id,
            subject_name="  プログラミング基礎　",
            room="3号館201",
            notes="前期の授業",
        ),
    )

    assert response.status_code == 201
    assert response.json["generated_event_count"] == 17
    subject_id = response.json["id"]
    with app.app_context():
        events = db.session.scalars(
            select(Event)
            .where(Event.subject_id == subject_id)
            .order_by(Event.date)
        ).all()
        assert len(events) == 17
        assert events[0].date == date(2026, 4, 6)
        assert events[-1].date == date(2026, 7, 27)
        for event in events:
            assert event.date.weekday() == 0
            assert event.category == "class"
            assert event.start_time == time(9, 0)
            assert event.end_time == time(10, 0)
            assert event.title == "プログラミング基礎"
            assert event.room == "3号館201"
            assert event.employer is None
            assert event.notes == "前期の授業"
            assert event.is_generated is True


def test_subject_creation_skips_closures_of_its_semester_only(client, app):
    semester_id = make_semester(app)
    other_semester_id = make_semester(app, name="2026年度 後期")
    make_closure(app, semester_id, date(2026, 5, 4))
    make_closure(app, semester_id, date(2026, 7, 20))
    # ほかの学期の休講日は、この学期の授業の予定に影響しない。
    make_closure(app, other_semester_id, date(2026, 4, 13))

    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id),
    )

    assert response.status_code == 201
    assert response.json["generated_event_count"] == 15
    dates = generated_event_dates(app, response.json["id"])
    assert len(dates) == 15
    assert date(2026, 5, 4) not in dates
    assert date(2026, 7, 20) not in dates
    assert date(2026, 4, 13) in dates


def test_subject_creation_without_matching_days_returns_zero(client, app):
    with app.app_context():
        # 2026-04-01（水）〜2026-04-02（木）の学期に、月曜日はない。
        semester = Semester(
            name="2026年度 前期",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 2),
        )
        db.session.add(semester)
        db.session.commit()
        semester_id = semester.id

    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, weekday=0),
    )

    assert response.status_code == 201
    assert response.json["generated_event_count"] == 0
    assert subject_count(app) == 1
    assert event_count(app) == 0


def test_subject_creation_when_all_days_are_closures_returns_zero(
    client, app
):
    with app.app_context():
        # 2026-04-06（月）〜2026-04-12（日）の月曜日は、4/6の1日だけ。
        semester = Semester(
            name="2026年度 前期",
            start_date=date(2026, 4, 6),
            end_date=date(2026, 4, 12),
        )
        db.session.add(semester)
        db.session.commit()
        semester_id = semester.id
    make_closure(app, semester_id, date(2026, 4, 6))

    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, weekday=0),
    )

    assert response.status_code == 201
    assert response.json["generated_event_count"] == 0
    assert event_count(app) == 0


def test_generated_event_count_is_not_in_subject_list(client, app):
    semester_id = make_semester(app)
    client.post("/api/subjects", json=subject_payload(semester_id))

    response = client.get("/api/subjects")

    assert response.status_code == 200
    assert len(response.json) == 1
    assert "generated_event_count" not in response.json[0]


def test_generated_event_count_in_request_is_rejected(client, app):
    semester_id = make_semester(app)

    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, generated_event_count=17),
    )

    assert_validation_error(
        response,
        {"generated_event_count": "この項目は指定できません"},
    )
    assert subject_count(app) == 0
    assert event_count(app) == 0


def test_failed_subject_post_creates_no_events(client, app):
    semester_id = make_semester(app)

    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, weekday=9),
    )

    assert response.status_code == 400
    assert event_count(app) == 0


def test_event_generation_failure_saves_neither_subject_nor_events(
    client, app, monkeypatch
):
    semester_id = make_semester(app)

    def fail(*args, **kwargs):
        raise RuntimeError("intentional test failure")

    # routeのモジュールが取り込んだ名前を置き換える。
    monkeypatch.setattr("app.routes.subjects.build_class_events", fail)
    app.config["PROPAGATE_EXCEPTIONS"] = False

    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id),
    )

    assert response.status_code == 500
    assert response.json["error"]["code"] == "server_error"
    assert subject_count(app) == 0
    assert event_count(app) == 0
```

### 付録E. `tests/test_subjects_update_delete_api.py`

<!-- 全文: tests/test_subjects_update_delete_api.py -->
```python
"""授業の編集（PATCH）・削除（DELETE）と、1件取得の件数のAPIのテスト。

授業の登録・一覧・1件取得の基本は、tests/test_subjects_api.py で確かめる。
"""

from datetime import date, datetime, time

import pytest
from sqlalchemy import func, select

from app.api_helpers import MAX_ID, UNUSABLE_CHARACTER_MESSAGE
from app.extensions import db
from app.models.closure import Closure
from app.models.event import Event
from app.models.semester import Semester
from app.models.subject import Subject
from app.models.task import Task


# 「今日」は、2026-06-15（月）に固定する（実行した日によって、結果が
# 変わらないようにするため。fixed_today を参照）。
TODAY = date(2026, 6, 15)

# 学期（2026-04-01〜2026-07-31）の月曜日。
MONDAYS = [
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
PAST_MONDAYS = [day for day in MONDAYS if day < TODAY]
FUTURE_MONDAYS = [day for day in MONDAYS if day >= TODAY]

# 学期の、今日以降の水曜日。
FUTURE_WEDNESDAYS = [
    date(2026, 6, 17),
    date(2026, 6, 24),
    date(2026, 7, 1),
    date(2026, 7, 8),
    date(2026, 7, 15),
    date(2026, 7, 22),
    date(2026, 7, 29),
]

FORMAT_MESSAGES = {
    "start_time": (
        "開始時刻は「HH:MM」の形式（00:00〜23:59）で指定してください"
    ),
    "end_time": (
        "終了時刻は「HH:MM」の形式（00:00〜23:59）で指定してください"
    ),
}
WEEKDAY_MESSAGE = "曜日は0（月曜）〜6（日曜）の整数で指定してください"


def set_today(monkeypatch, day):
    """routeが使う「今日」（current_date）を、指定した日にする。"""
    # routeのモジュールの名前を置き換える。
    monkeypatch.setattr("app.routes.subjects.current_date", lambda: day)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    """このファイルのテストでは、「今日」を TODAY にする。"""
    set_today(monkeypatch, TODAY)


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


def subject_payload(semester_id, **overrides):
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
    return payload


def create_subject(client, semester_id, **overrides):
    """授業をAPIで登録し（予定も作られる）、授業のIDを返す。"""
    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, **overrides),
    )
    assert response.status_code == 201
    return response.json["id"]


def make_closure(app, semester_id, closure_date):
    with app.app_context():
        db.session.add(Closure(semester_id=semester_id, date=closure_date))
        db.session.commit()


def make_one_off_event(app, subject_id, event_date, title="補講"):
    """授業の単発の予定（is_generated=False）を、ORMで直接作る。"""
    with app.app_context():
        event = Event(
            subject_id=subject_id,
            category="class",
            date=event_date,
            start_time=time(15, 0),
            end_time=time(16, 0),
            title=title,
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


def make_task(app, subject_id, title="レポート"):
    """課題を、ORMで直接作る（課題のAPIは、まだないため）。"""
    with app.app_context():
        task = Task(
            subject_id=subject_id,
            category="assignment" if subject_id is not None else "other",
            title=title,
            due_datetime=datetime(2026, 6, 30, 23, 59),
        )
        db.session.add(task)
        db.session.commit()
        return task.id


def generated_events(app, subject_id):
    """授業の自動生成の予定を、日付の昇順で返す（セッションから切り離す）。"""
    with app.app_context():
        events = db.session.scalars(
            select(Event)
            .where(
                Event.subject_id == subject_id,
                Event.is_generated.is_(True),
            )
            .order_by(Event.date, Event.id)
        ).all()
        db.session.expunge_all()
        return events


def generated_dates(app, subject_id):
    """授業の自動生成の予定の日付（同じ日付が2件あれば2回）。"""
    return [event.date for event in generated_events(app, subject_id)]


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


def all_task_rows(app):
    """すべての課題の値を、IDの順に返す（変わっていないことの確認用）。"""
    with app.app_context():
        tasks = db.session.scalars(select(Task).order_by(Task.id)).all()
        return [
            (task.id, task.subject_id, task.title, task.due_datetime)
            for task in tasks
        ]


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


# --- 1件取得（GET /api/subjects/<id>）の件数 ---


def test_subject_get_counts_events_and_tasks_of_the_subject(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    other_subject_id = create_subject(client, semester_id)
    make_one_off_event(app, subject_id, date(2026, 6, 16))
    make_task(app, subject_id)
    make_task(app, subject_id)
    # ほかの授業の課題と、授業に結びつかない予定・課題は、数えない。
    make_task(app, other_subject_id)
    make_part_time_event(app, date(2026, 6, 16))
    make_task(app, None)

    response = client.get(f"/api/subjects/{subject_id}")

    assert response.status_code == 200
    # 自動生成の17件と、単発の1件。
    assert response.json["event_count"] == 18
    assert response.json["task_count"] == 2


def test_subject_get_counts_are_zero_without_events_and_tasks(client, app):
    with app.app_context():
        # 2026-04-01（水）〜2026-04-02（木）の学期に、月曜日はない。
        semester = Semester(
            name="2026年度 前期",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 2),
        )
        db.session.add(semester)
        db.session.commit()
        semester_id = semester.id
    subject_id = create_subject(client, semester_id)

    response = client.get(f"/api/subjects/{subject_id}")

    assert response.status_code == 200
    assert response.json["event_count"] == 0
    assert response.json["task_count"] == 0


def test_counts_are_not_in_subject_list(client, app):
    semester_id = make_semester(app)
    create_subject(client, semester_id)

    response = client.get("/api/subjects")

    assert response.status_code == 200
    assert "event_count" not in response.json[0]
    assert "task_count" not in response.json[0]


@pytest.mark.parametrize("field", ["event_count", "task_count"])
def test_count_fields_in_post_request_are_rejected(client, app, field):
    semester_id = make_semester(app)

    response = client.post(
        "/api/subjects",
        json=subject_payload(semester_id, **{field: 0}),
    )

    assert_validation_error(response, {field: "この項目は指定できません"})


# --- 授業の編集（PATCH）：授業の値 ---


def test_patch_changes_only_given_fields_and_returns_subject(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"room": "  5号館301　"},
    )

    assert response.status_code == 200
    # 更新後の授業を返す。付加情報（件数）は含めない。
    assert response.json == {
        "id": subject_id,
        "semester_id": semester_id,
        "subject_name": "プログラミング基礎",
        "room": "5号館301",
        "weekday": 0,
        "start_time": "09:00",
        "end_time": "10:00",
        "notes": "前期の授業",
    }
    with app.app_context():
        subject = db.session.get(Subject, subject_id)
        assert subject.room == "5号館301"
        assert subject.subject_name == "プログラミング基礎"


def test_patch_can_change_all_editable_fields(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={
            "subject_name": "  データ構造　",
            "room": "5号館301",
            "weekday": 2,
            "start_time": "13:00",
            "end_time": "14:30",
            "notes": "  後半は演習  ",
        },
    )

    assert response.status_code == 200
    expected = {
        "id": subject_id,
        "semester_id": semester_id,
        "subject_name": "データ構造",
        "room": "5号館301",
        "weekday": 2,
        "start_time": "13:00",
        "end_time": "14:30",
        "notes": "後半は演習",
    }
    assert response.json == expected
    listed = client.get(f"/api/subjects?semester_id={semester_id}")
    assert listed.json == [expected]


@pytest.mark.parametrize("empty_value", [None, "", "  ", "　"])
def test_patch_can_clear_room_and_notes(client, app, empty_value):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"room": empty_value, "notes": empty_value},
    )

    assert response.status_code == 200
    assert response.json["room"] is None
    assert response.json["notes"] is None
    for event in generated_events(app, subject_id):
        if event.date >= TODAY:
            assert event.room is None
            assert event.notes is None


# --- 授業の編集（PATCH）：今日以降の予定の作り直し ---


def test_patch_rebuilds_events_from_today_with_new_values(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={
            "subject_name": "データ構造",
            "room": "5号館301",
            "start_time": "13:00",
            "end_time": "14:30",
            "notes": "後半は演習",
        },
    )

    assert response.status_code == 200
    events = generated_events(app, subject_id)
    assert [event.date for event in events] == MONDAYS
    for event in events:
        if event.date < TODAY:
            # 今日より前の予定は、登録時の値のまま。
            values = ("プログラミング基礎", "3号館201", "前期の授業")
            times = (time(9, 0), time(10, 0))
        else:
            # 今日（を含む）以降の予定は、新しい値で作り直される。
            values = ("データ構造", "5号館301", "後半は演習")
            times = (time(13, 0), time(14, 30))
        assert (event.title, event.room, event.notes) == values
        assert (event.start_time, event.end_time) == times
        assert event.category == "class"
        assert event.employer is None


def test_patch_weekday_moves_only_events_from_today(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"weekday": 2},
    )

    assert response.status_code == 200
    # 今日より前は月曜日のまま、今日以降は水曜日になる。
    assert generated_dates(app, subject_id) == (
        PAST_MONDAYS + FUTURE_WEDNESDAYS
    )


def test_patch_restores_changed_and_deleted_future_events(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    with app.app_context():
        events = {
            event.date: event
            for event in db.session.scalars(
                select(Event).where(Event.subject_id == subject_id)
            )
        }
        # カレンダーからの個別の編集・削除の代わりに、DBを直接変える。
        events[date(2026, 6, 8)].title = "過去の個別の変更"
        events[date(2026, 6, 22)].title = "今後の個別の変更"
        events[date(2026, 6, 22)].start_time = time(11, 0)
        db.session.delete(events[date(2026, 6, 29)])
        db.session.commit()

    # 値を変えない編集でも、今日以降の予定は作り直される。
    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "プログラミング基礎"},
    )

    assert response.status_code == 200
    events = generated_events(app, subject_id)
    assert [event.date for event in events] == MONDAYS
    titles = {event.date: event.title for event in events}
    # 今日より前の個別の変更は、残る。
    assert titles[date(2026, 6, 8)] == "過去の個別の変更"
    # 今日以降の個別の変更・削除は、設定どおりに戻る。
    assert titles[date(2026, 6, 22)] == "プログラミング基礎"
    assert titles[date(2026, 6, 29)] == "プログラミング基礎"
    start_times = {event.date: event.start_time for event in events}
    assert start_times[date(2026, 6, 22)] == time(9, 0)


def test_patch_keeps_one_off_events(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    make_one_off_event(app, subject_id, date(2026, 6, 1), "過去の補講")
    # 自動生成の予定と同じ日の、単発の予定。
    make_one_off_event(app, subject_id, date(2026, 6, 22), "今後の補講")
    one_off_before = [
        row for row in all_event_rows(app) if row[-1] is False
    ]

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造"},
    )

    assert response.status_code == 200
    one_off_after = [row for row in all_event_rows(app) if row[-1] is False]
    assert one_off_after == one_off_before
    # 単発の予定がある日にも、自動生成の予定は規則どおりに作られる。
    assert generated_dates(app, subject_id) == MONDAYS


def test_patch_does_not_create_events_on_closures(client, app):
    semester_id = make_semester(app)
    other_semester_id = make_semester(app, "2026年度 後期")
    make_closure(app, semester_id, date(2026, 7, 20))
    # ほかの学期の休講日は、この授業の予定に影響しない。
    make_closure(app, other_semester_id, date(2026, 7, 13))
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造"},
    )

    assert response.status_code == 200
    dates = generated_dates(app, subject_id)
    assert date(2026, 7, 20) not in dates
    assert date(2026, 7, 13) in dates
    assert dates == [day for day in MONDAYS if day != date(2026, 7, 20)]


def test_patch_does_not_change_other_subjects_or_part_time(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    other_subject_id = create_subject(client, semester_id)
    make_part_time_event(app, date(2026, 6, 22))
    other_rows_before = [
        row
        for row in all_event_rows(app)
        if row[1] != subject_id
    ]

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造"},
    )

    assert response.status_code == 200
    other_rows_after = [
        row
        for row in all_event_rows(app)
        if row[1] != subject_id
    ]
    assert other_rows_after == other_rows_before
    assert len(generated_dates(app, other_subject_id)) == 17


def test_repeated_patch_does_not_duplicate_generated_events(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    for name in ["データ構造", "アルゴリズム", "データ構造"]:
        response = client.patch(
            f"/api/subjects/{subject_id}",
            json={"subject_name": name},
        )
        assert response.status_code == 200

    # 同じ授業・同じ日付の自動生成の予定は、1件まで。
    assert generated_dates(app, subject_id) == MONDAYS


def test_patch_before_semester_rebuilds_all_events(
    client, app, monkeypatch
):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    set_today(monkeypatch, date(2026, 3, 1))

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造"},
    )

    assert response.status_code == 200
    events = generated_events(app, subject_id)
    assert [event.date for event in events] == MONDAYS
    assert all(event.title == "データ構造" for event in events)


def test_patch_after_semester_changes_only_subject(client, app, monkeypatch):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    rows_before = all_event_rows(app)
    set_today(monkeypatch, date(2026, 8, 1))

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造"},
    )

    assert response.status_code == 200
    assert response.json["subject_name"] == "データ構造"
    # 学期が終わったあとの編集では、予定は変わらない。
    assert all_event_rows(app) == rows_before


def test_patch_on_last_day_of_semester_rebuilds_that_day(
    client, app, monkeypatch
):
    semester_id = make_semester(app)
    # 学期の終了日（2026-07-31）は金曜日。
    subject_id = create_subject(client, semester_id, weekday=4)
    set_today(monkeypatch, date(2026, 7, 31))

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造"},
    )

    assert response.status_code == 200
    titles = {
        event.date: event.title
        for event in generated_events(app, subject_id)
    }
    assert len(titles) == 18
    assert titles[date(2026, 7, 31)] == "データ構造"
    assert titles[date(2026, 7, 24)] == "プログラミング基礎"


def test_patch_failure_during_rebuild_saves_nothing(
    client, app, monkeypatch
):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    subject_before = client.get(f"/api/subjects/{subject_id}").json
    rows_before = all_event_rows(app)

    def fail(*args, **kwargs):
        raise RuntimeError("intentional test failure")

    # routeのモジュールが取り込んだ名前を置き換える。
    monkeypatch.setattr("app.routes.subjects.build_class_events_from", fail)
    app.config["PROPAGATE_EXCEPTIONS"] = False

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造"},
    )

    assert response.status_code == 500
    assert response.json["error"]["code"] == "server_error"
    # 授業の更新も、予定の削除も、保存されない。
    assert client.get(f"/api/subjects/{subject_id}").json == subject_before
    assert all_event_rows(app) == rows_before


# --- 授業の編集（PATCH）：入力の検証 ---


def test_patch_empty_object_is_validation_error_without_fields(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    rows_before = all_event_rows(app)

    response = client.patch(f"/api/subjects/{subject_id}", json={})

    assert response.status_code == 400
    assert response.json == {
        "error": {
            "code": "validation_error",
            "message": "変更する項目を指定してください",
        }
    }
    assert all_event_rows(app) == rows_before


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("subject_name", None, "科目名は必須です"),
        ("subject_name", "", "科目名は必須です"),
        ("subject_name", "　", "科目名は必須です"),
        ("subject_name", 123, "科目名は文字列で指定してください"),
        ("subject_name", "科" * 101, "科目名は100文字以内にしてください"),
        ("subject_name", "\ud800", UNUSABLE_CHARACTER_MESSAGE),
        ("room", 123, "教室は文字列で指定してください"),
        ("room", "教" * 101, "教室は100文字以内にしてください"),
        ("weekday", None, "曜日は必須です"),
        ("weekday", "", "曜日は必須です"),
        ("weekday", 7, WEEKDAY_MESSAGE),
        ("weekday", True, WEEKDAY_MESSAGE),
        ("weekday", "1", WEEKDAY_MESSAGE),
        ("start_time", None, "開始時刻は必須です"),
        ("start_time", "", "開始時刻は必須です"),
        ("start_time", "9:00", FORMAT_MESSAGES["start_time"]),
        ("end_time", None, "終了時刻は必須です"),
        ("end_time", "24:00", FORMAT_MESSAGES["end_time"]),
        ("notes", 123, "詳細・メモは文字列で指定してください"),
        ("notes", "メモ\udfff", UNUSABLE_CHARACTER_MESSAGE),
    ],
)
def test_patch_field_values_are_validated_like_post(
    client, app, field, value, message
):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={field: value},
    )

    assert_validation_error(response, {field: message})


@pytest.mark.parametrize(
    "field",
    [
        "semester_id",
        "id",
        "generated_event_count",
        "event_count",
        "task_count",
        "color",
    ],
)
def test_patch_rejects_semester_id_and_unknown_fields(client, app, field):
    semester_id = make_semester(app)
    other_semester_id = make_semester(app, "2026年度 後期")
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造", field: other_semester_id},
    )

    assert_validation_error(response, {field: "この項目は指定できません"})
    with app.app_context():
        subject = db.session.get(Subject, subject_id)
        assert subject.semester_id == semester_id
        assert subject.subject_name == "プログラミング基礎"


@pytest.mark.parametrize(
    "payload",
    [
        {"end_time": "09:00"},
        {"start_time": "10:00"},
        {"start_time": "11:00", "end_time": "10:30"},
    ],
)
def test_patch_end_time_must_be_after_start_time_after_change(
    client, app, payload
):
    semester_id = make_semester(app)
    # 今の時刻は 09:00〜10:00。本文にない時刻は、今の値と比べる。
    subject_id = create_subject(client, semester_id)

    response = client.patch(f"/api/subjects/{subject_id}", json=payload)

    assert_validation_error(
        response,
        {"end_time": "終了時刻は開始時刻より後にしてください"},
    )


@pytest.mark.parametrize(
    ("payload", "start_time", "end_time"),
    [
        ({"start_time": "09:30"}, "09:30", "10:00"),
        ({"end_time": "09:01"}, "09:00", "09:01"),
        ({"start_time": "11:00", "end_time": "12:00"}, "11:00", "12:00"),
    ],
)
def test_patch_time_change_is_accepted_when_order_is_valid(
    client, app, payload, start_time, end_time
):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(f"/api/subjects/{subject_id}", json=payload)

    assert response.status_code == 200
    assert response.json["start_time"] == start_time
    assert response.json["end_time"] == end_time


def test_patch_invalid_start_time_skips_time_order_validation(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"start_time": "invalid", "end_time": "08:00"},
    )

    assert_validation_error(
        response,
        {"start_time": FORMAT_MESSAGES["start_time"]},
    )


def test_patch_validation_errors_are_returned_together(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "", "weekday": 9, "semester_id": 2},
    )

    assert_validation_error(
        response,
        {
            "subject_name": "科目名は必須です",
            "weekday": WEEKDAY_MESSAGE,
            "semester_id": "この項目は指定できません",
        },
    )


def test_failed_patch_changes_neither_subject_nor_events(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    subject_before = client.get(f"/api/subjects/{subject_id}").json
    rows_before = all_event_rows(app)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造", "weekday": 9},
    )

    assert response.status_code == 400
    assert client.get(f"/api/subjects/{subject_id}").json == subject_before
    assert all_event_rows(app) == rows_before


@pytest.mark.parametrize("payload", [[], "abc", 123, True])
def test_patch_non_object_payload_has_no_fields(client, app, payload):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(f"/api/subjects/{subject_id}", json=payload)

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
        ('{"subject_name":', "application/json"),
        ('{"subject_name":"x"}', "text/plain"),
        ('{"subject_name":"x"}', None),
    ],
)
def test_patch_invalid_json_or_content_type_is_rejected(
    client, app, data, content_type
):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    response = client.patch(
        f"/api/subjects/{subject_id}",
        data=data,
        content_type=content_type,
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_json"


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/subjects/99999", "授業が見つかりません"),
        ("/api/subjects/0", "授業が見つかりません"),
        (f"/api/subjects/{MAX_ID}", "授業が見つかりません"),
        ("/api/subjects/abc", "URLが見つかりません"),
        ("/api/subjects/-1", "URLが見つかりません"),
    ],
)
def test_patch_not_found_and_invalid_urls(client, url, message):
    response = client.patch(url, json={"subject_name": "データ構造"})

    assert response.status_code == 404
    assert response.json == {
        "error": {"code": "not_found", "message": message}
    }


@pytest.mark.parametrize("method", ["patch", "delete"])
@pytest.mark.parametrize("subject_id", [MAX_ID + 1, 10**20])
def test_over_limit_id_for_patch_and_delete_is_method_not_allowed(
    client, method, subject_id
):
    # 上限を超えるIDは、URLに一致しない。同じURLに、ほかのメソッドの
    # route（GET）があるため、Flaskは405を返す（docs/architecture.md の
    # 「404の使い分け」の注意）。
    response = getattr(client, method)(
        f"/api/subjects/{subject_id}",
        json={"subject_name": "データ構造"},
    )

    assert response.status_code == 405
    assert response.json["error"]["code"] == "method_not_allowed"


def test_patch_missing_subject_is_404_before_reading_body(client):
    # 本文が読めなくても、授業がなければ404。
    response = client.patch(
        "/api/subjects/99999",
        data="not json",
        content_type="text/plain",
    )

    assert response.status_code == 404
    assert response.json["error"]["message"] == "授業が見つかりません"


# --- 授業の削除（DELETE） ---


def test_delete_subject_removes_its_events_and_tasks(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    make_one_off_event(app, subject_id, date(2026, 6, 1))
    make_one_off_event(app, subject_id, date(2026, 6, 22))
    make_task(app, subject_id)

    response = client.delete(f"/api/subjects/{subject_id}")

    assert response.status_code == 204
    assert response.get_data() == b""
    assert client.get(f"/api/subjects/{subject_id}").status_code == 404
    # 過去分を含む、自動生成・単発の予定と、課題が削除される。
    assert count_rows(app, Event, Event.subject_id == subject_id) == 0
    assert count_rows(app, Task, Task.subject_id == subject_id) == 0


def test_delete_subject_leaves_no_rows_without_subject(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    make_one_off_event(app, subject_id, date(2026, 6, 22))
    make_task(app, subject_id)

    response = client.delete(f"/api/subjects/{subject_id}")

    assert response.status_code == 204
    # 授業のない予定・課題（subject_id が NULL）として残らない。
    assert count_rows(app, Event, Event.subject_id.is_(None)) == 0
    assert count_rows(app, Task, Task.subject_id.is_(None)) == 0
    assert count_rows(app, Event) == 0
    assert count_rows(app, Task) == 0


def test_delete_subject_keeps_other_rows(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    other_subject_id = create_subject(client, semester_id)
    make_task(app, subject_id)
    make_task(app, other_subject_id)
    make_part_time_event(app, date(2026, 6, 22))
    make_task(app, None)
    make_closure(app, semester_id, date(2026, 7, 20))
    other_event_rows = [
        row for row in all_event_rows(app) if row[1] != subject_id
    ]
    other_task_rows = [
        row for row in all_task_rows(app) if row[1] != subject_id
    ]

    response = client.delete(f"/api/subjects/{subject_id}")

    assert response.status_code == 204
    # ほかの授業の予定・課題と、授業に結びつかない予定・課題は残る。
    assert all_event_rows(app) == other_event_rows
    assert all_task_rows(app) == other_task_rows
    assert client.get(f"/api/subjects/{other_subject_id}").status_code == 200
    assert client.get(f"/api/semesters/{semester_id}").status_code == 200
    assert count_rows(app, Closure) == 1


def test_delete_subject_ignores_body(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)

    # DELETE は本文を読まない（Content-Type も求めない）。
    response = client.delete(
        f"/api/subjects/{subject_id}",
        data="not json",
        content_type="text/plain",
    )

    assert response.status_code == 204


def test_deleted_subject_cannot_be_deleted_again(client, app):
    semester_id = make_semester(app)
    subject_id = create_subject(client, semester_id)
    assert client.delete(f"/api/subjects/{subject_id}").status_code == 204

    response = client.delete(f"/api/subjects/{subject_id}")

    assert response.status_code == 404
    assert response.json == {
        "error": {"code": "not_found", "message": "授業が見つかりません"}
    }


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("/api/subjects/99999", "授業が見つかりません"),
        ("/api/subjects/0", "授業が見つかりません"),
        (f"/api/subjects/{MAX_ID}", "授業が見つかりません"),
        ("/api/subjects/abc", "URLが見つかりません"),
        ("/api/subjects/-1", "URLが見つかりません"),
    ],
)
def test_delete_not_found_and_invalid_urls(client, app, url, message):
    semester_id = make_semester(app)
    create_subject(client, semester_id)
    rows_before = all_event_rows(app)

    response = client.delete(url)

    assert response.status_code == 404
    assert response.json == {
        "error": {"code": "not_found", "message": message}
    }
    assert all_event_rows(app) == rows_before


def test_delete_collection_url_is_not_allowed(client, app):
    semester_id = make_semester(app)
    create_subject(client, semester_id)

    response = client.delete("/api/subjects")

    assert response.status_code == 405
    assert count_rows(app, Subject) == 1
```
