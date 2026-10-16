# タスク017: 課題・タスクモードの画面

| 項目 | 内容 |
|---|---|
| Task ID | 017 |
| Task名 | 課題・タスクモードの画面（一覧（未完了・完了）、完了の切り替え、課題の追加、編集、削除の確認）と、今の学期を選ぶ規則の共通化（`current_semester.js`）、015-L1 |
| ブランチ | `feature/017-tasks-ui`（Komaが作成・切替済みの状態で渡される） |

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに停止して報告する。

**このタスクには、承認ゲートはない（DBの構造を変えないため、migrationを作らない）。** 段階1・2を順に進め、「Copilot確認手順」を実施したら、結果を報告して応答を終える。途中で止まるのは、「注意」の停止の条件に当たったときだけ。**止まるときは、報告を書いて応答を終える。質問の機能（選択肢を出して回答を待つ機能）は使わない**（`.github/copilot-instructions.md` の「止まる場面の応答」）。

**ファイルは、手で書き写さない。** 8つのファイルの全文は、このTask MDの付録にある。各段階の始めに、「全文からファイルを作るスクリプト」を実行して作る（013-N1）。付録の全文は、スクリプトが読む。付録を読んで書き写す必要はない（本文の要点・差分・確認の手順を読む）。

**報告には、コマンドの出力を、要約せずに、そのまま貼る**（014-L1）。「注意」の最後の報告の項目を参照。

**このTask MDのスクリプトとコマンドには、バックスラッシュ（`\`）の書き方を使っていない**（016-N1。改行は、スクリプトの中で `newline = chr(10)` として表す。`grep` は、`-F`（文字どおりに探す）と `-e`（探す文字列を1つずつ指定）で書く）。**コマンドは、書いてあるとおりに実行する。書き換えた場合は、どこをどう書き換えたかを、報告に書く。**

## 目的
課題・タスクモード（今は「課題・タスク（準備中）」の表示だけ）に、課題と、その他（締切のみ）の一覧（未完了・完了）、完了の切り替え、課題の追加、編集、削除の確認を作る（Task 016で作った `/api/tasks` を使う）。設計資料（`docs/ui_ux.md` の「課題・タスクモード」、`docs/architecture.md` の「JavaScriptの構成（ES modules）」と「課題・タスクAPI」、`docs/requirements.md` の「予定の登録」「予定の編集・削除」「課題の完了管理」）の仕様を、そのまま実装する。あわせて、今の学期を選ぶ規則（授業モードの学期の初期選択）を、`semesters.js` から新しい `current_semester.js` に移し（課題の対象授業の選択肢が、2つ目の利用者になるため）、持ち越しの015-L1（授業の削除の確認のモーダルと、編集の「保存する」の説明（`aria-describedby`））を直す。**Python・API・DBの構造は変えない**（pytestは787件のまま）。

次の2段階で、この順に行う。

| 段階 | 内容 | 挙動の変化 | 段階の終わりの `pytest` |
|---|---|---|---|
| 1 | 共通の部品：`current_semester.js`（新規。今の学期を選ぶ規則）、`semesters.js`（その規則を `current_semester.js` から使う）、`dates.js`（今の日時の文字列と、日時の表示）、`categories.js`（課題・タスクのカテゴリの対応表）、`style.css`（課題の色と、課題・タスクの一覧の列の幅） | 変わらない（授業モードの学期の初期選択は同じ。足した関数・対応表・classは、まだ使わない） | **787件**（Pythonを変えない） |
| 2 | 画面：`index.html`（課題・タスクモードの本体、追加・編集・削除の確認の3つのモーダル、015-L1）、`tasks.js`（新規）、`main.js`（`initTasks` を呼ぶ） | 課題・タスクモードが使えるようになる。授業の削除の確認のモーダルと、編集の「保存する」に、説明（`aria-describedby`）が付く | **787件** |

## 前提（Task 016完了時点の状態）

| 区分 | 内容 |
|---|---|
| すでにある | 学期・授業・休講日のAPIと画面、予定API、カレンダー表示（Task 013）、授業の編集・削除のAPIと画面（Task 014・015）、課題・タスクのAPI（`GET`・`POST /api/tasks`、`GET`・`PATCH`・`DELETE /api/tasks/<id>`。Task 016）。pytest（**787件**。`main` の `a807bb4` で確認） |
| まだない | 課題・タスクモードの画面（`index.html` の `tasks-pane` は「課題・タスク（準備中）」の1行だけ）、`tasks.js`、`current_semester.js`、`categories.js` の課題・タスクの対応表、`dates.js` の日時の関数 |
| DBの構造 | 変えない（初期migration `0280f6cf8d09` と、休講日の `42bd53808fa1`）。**migrationは不要** |
| 開発用DB | `instance/app.db` は、Komaの実際の開発用DB（すべてのテーブルが0件。2026-10-15、Task 016の確認のあとにKomaが確認）。**Copilotは、書き込まない。サーバーを起動しない（`python run.py` を実行しない）**。読むのは、「Copilot確認手順」のハッシュと件数だけ。**`sqlite3` は、必ず `-readonly` を付けて実行する**（011-L1） |
| 設計資料 | このタスクの前に、更新した設計資料が `main` に反映されている。`docs/ui_ux.md` の「課題・タスクモード」に、「一覧」「完了の切り替え」「追加（モーダル）」「編集（モーダル）」「削除（確認のモーダル）」がある。`docs/architecture.md` の「JavaScriptの構成（ES modules）」に、`current_semester.js` の行がある。`docs/requirements.md` の「課題・タスクモード」に、「今の学期の授業から選ぶ」がある |
| 確認 | JavaScriptの自動テストはない。画面の動きは、Komaの確認（確認用のサーバーでのブラウザ確認。ブラウザの操作はClaude）で確かめる。Copilotは、ブラウザでの確認をしない |

## Source of Truth
- `docs/ui_ux.md`：「課題・タスクモード」（「一覧」「完了の切り替え」「追加（モーダル）」「編集（モーダル）」「削除（確認のモーダル）」「追加・編集・削除の共通」「カレンダーとの関係」）、「授業モード」の「学期（タブと登録）」の「初期選択」、「授業」の「編集」「削除」（015-L1の説明）、「色・アイコン」
- `docs/architecture.md`：「JavaScriptの構成（ES modules）」（`tasks.js`・`current_semester.js`・`dates.js`・`categories.js` の役割、規則。特に、モーダルの規則、モーダルの中で始める要求の規則、`try` で囲む範囲、`textContent`、DOMの `id`、名前つきの引数）、「課題・タスクAPI」、「API共通ルール」の「日付・時刻・日時」、「`api.js` の仕様」、「開発中の注意（アプリの中で直せないデータ）」
- `docs/requirements.md`：「予定の登録」の「課題・タスクモード」、「予定の編集・削除」、「課題の完了管理」
- `.github/copilot-instructions.md`：進め方、「止まる場面の応答」、コーディング方針（JavaScript）

## 実装対象ファイル

| 区分 | ファイル | 段階 | 内容 | 全文 |
|---|---|---|---|---|
| 新規 | `app/static/js/current_semester.js` | 1 | 今の学期を選ぶ規則 `chooseCurrentSemester(semesters, today)`（`semesters.js` の `chooseInitialSemester` を移したもの） | 付録A |
| 変更 | `app/static/js/semesters.js` | 1 | `chooseInitialSemester` を消し、`current_semester.js` の `chooseCurrentSemester` を使う | 付録B |
| 変更 | `app/static/js/dates.js` | 1 | `localDateTimeString`・`formatJapaneseDateTime` を足す | 付録C |
| 変更 | `app/static/js/categories.js` | 1 | 課題・タスクの対応表 `TASK_CATEGORIES` と `taskCategoryOf` を足す（対応表を引く処理を、中の関数 `categoryOf` にまとめる） | 付録D |
| 変更 | `app/static/css/style.css` | 1 | 課題の色（`.category-assignment`）と、課題・タスクの一覧の列の幅（`.task-table`・`.task-col-…`） | 付録E |
| 変更 | `app/templates/index.html` | 2 | 課題・タスクモードの本体、3つのモーダル（追加・編集・削除の確認）、015-L1 | 付録F |
| 新規 | `app/static/js/tasks.js` | 2 | 課題・タスクモードの一覧・完了の切り替え・追加・編集・削除の確認 | 付録G |
| 変更 | `app/static/js/main.js` | 2 | `initTasks()` を呼ぶ | 付録H |

上の8ファイル以外は、変更しない（`__pycache__/` などの、`.gitignore` の対象は除く）。**8ファイルとも、このTask MDの付録に全文がある。「全文からファイルを作るスクリプト」で作り、手で書き写さない。書き込んだあとに、手で直さない。** 全文を変える必要があると判断した場合は、変えずに停止して報告する。

## 非対象（このタスクでは作らない・変更しない）
- Pythonのファイル（`app/` の `.py`、`run.py`）、`tests/`（**テストは変えない・足さない**）、`migrations/`（**`flask db` のコマンドを、一切実行しない**）、`requirements.txt`（**ライブラリを追加しない**）、`pytest.ini`
- `app/templates/base.html`、`app/static/js/` の上の6つ以外のファイル（`api.js`・`ui.js`・`calendar.js`・`subjects.js`・`closures.js`）
- `index.html` の、課題・タスクモードの本体、新しい3つのモーダル、015-L1の3か所（授業の削除の確認のモーダルの `aria-describedby`、その「削除は取り消せません。」の `id`、「削除する」と、授業の編集の「保存する」の `aria-describedby`）以外の部分
- `docs/`、`.github/`、`.gitignore`
- 作らないもの：カレンダーへの締切の表示（週表示の「締切」の行、月表示の印、「直近の締切」欄、絞り込みへの課題の追加、詳細パネルからの完了の切り替え）、その他（締切のみ）の追加（カレンダーから追加するタスクで作る）、追加・編集・削除のあとのメッセージ（一覧の表示の変化で分かるため、出さない）、連続登録
- 持ち越しの003-H・013-L1（このタスクでは扱わない。013-L1は、`calendar.js` を変えるタスクで扱う）
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
        "app/static/js/current_semester.js",
        "app/static/js/semesters.js",
        "app/static/js/dates.js",
        "app/static/js/categories.js",
        "app/static/css/style.css",
    ],
    "2": [
        "app/templates/index.html",
        "app/static/js/tasks.js",
        "app/static/js/main.js",
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
full_texts = read_full_texts("docs/tasks/017_tasks_ui.md")
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
| 1（`python - 1`） | `全文の数：8`、`app/static/js/current_semester.js：書き込み（42行）`、`app/static/js/semesters.js：書き込み（249行）`、`app/static/js/dates.js：書き込み（43行）`、`app/static/js/categories.js：書き込み（59行）`、`app/static/css/style.css：書き込み（81行）` |
| 2（`python - 2`） | `全文の数：8`、`app/templates/index.html：書き込み（564行）`、`app/static/js/tasks.js：書き込み（657行）`、`app/static/js/main.js：書き込み（16行）` |

- 出力が上と違う場合（全文の数・行数・エラー）は、ほかの作業をせずに停止して報告する
- 段階の終わりの「全文との比較」（「Copilot確認手順」の4）で「不一致」が出た場合は、手で直さず、その段階のスクリプトをもう一度実行して、全文に戻す。戻したことと、違っていた理由（分かれば）を、報告に書く（013-N1）

## 段階1：共通の部品（挙動は変わらない）

### 1-1. `app/static/js/current_semester.js`（新規。全文：付録A）
要点：
- `chooseCurrentSemester(semesters, today)`：今の学期を選ぶ（`docs/ui_ux.md` の「授業モード」の学期の「初期選択」の1〜3）。`semesters` は、学期のAPIの一覧の並び（開始日の新しい順）の配列、`today` は `YYYY-MM-DD`。学期が0件なら `null`
- 中身は、今の `semesters.js` の `chooseInitialSemester(items, today)` と同じ（引数の名前を `items` から `semesters` に変え、関数の前に規則のコメントを足しただけ）
- 公開する関数は、この1つ。DOMとAPIは扱わない（`dates.js`・`categories.js` と同じ、複数のモードで使う部品）

### 1-2. `app/static/js/semesters.js`（全文：付録B）
要点：`chooseInitialSemester` を消し、`current_semester.js` の `chooseCurrentSemester` を `import` して使う。授業モードの学期の初期選択は変わらない。

`main` からの差分（確認用）：

```diff
--- a/app/static/js/semesters.js
+++ b/app/static/js/semesters.js
@@ -1,4 +1,5 @@
 import { apiRequest } from "./api.js";
+import { chooseCurrentSemester } from "./current_semester.js";
 import { formatJapaneseDate, localDateString } from "./dates.js";
 import {
   clearFormErrors,
@@ -35,40 +36,6 @@ const SEMESTER_SUBMIT_LABELS = {
   busy: "登録中…",
 };
 
-function chooseInitialSemester(items, today) {
-  // YYYY-MM-DDは桁が固定されているため、文字列の大小が日付の前後と一致する。
-  const current = items.find(
-    (semester) => semester.start_date <= today && today <= semester.end_date,
-  );
-  if (current !== undefined) {
-    return current;
-  }
-
-  let next = null;
-  for (const semester of items) {
-    if (
-      semester.start_date > today &&
-      (next === null || semester.start_date < next.start_date)
-    ) {
-      next = semester;
-    }
-  }
-  if (next !== null) {
-    return next;
-  }
-
-  let mostRecent = null;
-  for (const semester of items) {
-    if (
-      mostRecent === null ||
-      semester.end_date > mostRecent.end_date
-    ) {
-      mostRecent = semester;
-    }
-  }
-  return mostRecent;
-}
-
 function clearSemesterFormErrors() {
   clearFormErrors(SEMESTER_FIELDS, SEMESTER_FORM_ERROR_ID);
 }
@@ -227,7 +194,7 @@ async function loadSemesters(preferredId = null) {
       (semester) => semester.id === preferredId,
     );
     const initial =
-      preferred ?? chooseInitialSemester(semesters, localDateString());
+      preferred ?? chooseCurrentSemester(semesters, localDateString());
     showContent();
     renderTabs();
     selectSemester(initial.id);
```

### 1-3. `app/static/js/dates.js`（全文：付録C）
要点：2つの関数を足す。既存の3つの関数は変えない。
- `localDateTimeString(date = new Date())`：今の日時の文字列（`YYYY-MM-DDTHH:MM`。課題・タスクのAPIの締切日時と同じ形。秒は持たない）。期限切れの判定に使う
- `formatJapaneseDateTime(dateTimeString)`：日時の表示（「2026年10月20日（火） 23:59」）。日付の部分は `formatJapaneseDateWithWeekday` を使う

`main` からの差分（確認用）：

```diff
--- a/app/static/js/dates.js
+++ b/app/static/js/dates.js
@@ -26,3 +26,18 @@ export function formatJapaneseDateWithWeekday(dateString) {
   const weekday = new Date(year, month - 1, day).getDay();
   return `${formatJapaneseDate(dateString)}（${WEEKDAY_LABELS[weekday]}）`;
 }
+
+// 今の日時の文字列（「YYYY-MM-DDTHH:MM」。課題・タスクのAPIの締切日時と
+// 同じ形）。秒は持たない。ブラウザのローカルの日時から作る。
+export function localDateTimeString(date = new Date()) {
+  const hours = String(date.getHours()).padStart(2, "0");
+  const minutes = String(date.getMinutes()).padStart(2, "0");
+  return `${localDateString(date)}T${hours}:${minutes}`;
+}
+
+// 日時の表示（例：「2026年10月20日（火） 23:59」）。dateTimeString は
+// 「YYYY-MM-DDTHH:MM」。
+export function formatJapaneseDateTime(dateTimeString) {
+  const [dateString, timeString] = dateTimeString.split("T");
+  return `${formatJapaneseDateWithWeekday(dateString)} ${timeString}`;
+}
```

### 1-4. `app/static/js/categories.js`（全文：付録D）
要点：
- 課題・タスク（Task）のカテゴリの対応表 `TASK_CATEGORIES`（`assignment`：課題・✅・`category-assignment`、`other`：その他・⭐・`category-other`）と、`taskCategoryOf(category)` を足す（`docs/ui_ux.md` の「色・アイコン」。その他は、予定のその他と同じ色・アイコン）
- 対応表を引く処理（対応表にない値は、保存値をそのまま表示名にする）を、中の関数 `categoryOf(categories, category)`（`export` しない）にまとめ、`eventCategoryOf` と `taskCategoryOf` から使う。`eventCategoryOf` の結果は変わらない
- 予定のカテゴリの説明のコメントにあった「課題・タスク（Task）のカテゴリは、課題・タスクの画面を作るタスクで足す。」の1行を消す（このタスクで足すため）

`main` からの差分（確認用）：

```diff
--- a/app/static/js/categories.js
+++ b/app/static/js/categories.js
@@ -5,7 +5,6 @@
 // （JavaScriptでは、色の値を持たない）。
 
 // 予定（Event）のカテゴリ。並びは、カレンダーの絞り込みの選択肢の並び。
-// 課題・タスク（Task）のカテゴリは、課題・タスクの画面を作るタスクで足す。
 export const EVENT_CATEGORIES = {
   class: {
     label: "授業",
@@ -24,12 +23,37 @@ export const EVENT_CATEGORIES = {
   },
 };
 
-// 予定のカテゴリの保存値に対応する項目を返す。対応表にない値は、
-// DBに入らない想定だが、画面が止まらないように、保存値をそのまま
-// 表示名にし、アイコンと色のclassを付けない。
-export function eventCategoryOf(category) {
-  if (Object.prototype.hasOwnProperty.call(EVENT_CATEGORIES, category)) {
-    return EVENT_CATEGORIES[category];
+// 課題・タスク（Task）のカテゴリ。その他（締切のみ）は、予定のその他と
+// 同じ色・アイコンを使う。
+export const TASK_CATEGORIES = {
+  assignment: {
+    label: "課題",
+    icon: "✅",
+    className: "category-assignment",
+  },
+  other: {
+    label: "その他",
+    icon: "⭐",
+    className: "category-other",
+  },
+};
+
+// 対応表（categories）から、保存値（category）に対応する項目を返す。
+// 対応表にない値は、DBに入らない想定だが、画面が止まらないように、
+// 保存値をそのまま表示名にし、アイコンと色のclassを付けない。
+function categoryOf(categories, category) {
+  if (Object.prototype.hasOwnProperty.call(categories, category)) {
+    return categories[category];
   }
   return { label: category, icon: "", className: "" };
 }
+
+// 予定のカテゴリの保存値に対応する項目を返す。
+export function eventCategoryOf(category) {
+  return categoryOf(EVENT_CATEGORIES, category);
+}
+
+// 課題・タスクのカテゴリの保存値に対応する項目を返す。
+export function taskCategoryOf(category) {
+  return categoryOf(TASK_CATEGORIES, category);
+}
```

### 1-5. `app/static/css/style.css`（全文：付録E）
要点：
- 課題の色 `.category-assignment`（背景・枠 `#fd7e14`、文字 `#000000`。`docs/ui_ux.md` の「色・アイコン」の値）。予定の色と同じく、FullCalendarのCSSの変数で書く。このタスクの画面では、まだ使わない（カレンダーに締切を表示するタスクで使う。`categories.js` の対応表の `className` が、ないclassを指さないように、ここで足す）
- 課題・タスクの一覧の2つの表（未完了・完了）の列の幅（`.task-table` に `table-layout: fixed`。完了の列 `3rem`、締切 `26%`、対象授業 `17%`、操作 `8rem`、課題名は残りの幅）。2つの表で、列の位置をそろえるため（中身に合わせた幅にすると、表ごとにずれる）

`main` からの差分（確認用）：

```diff
--- a/app/static/css/style.css
+++ b/app/static/css/style.css
@@ -12,6 +12,12 @@
   --fc-event-text-color: #ffffff;
 }
 
+.category-assignment {
+  --fc-event-bg-color: #fd7e14;
+  --fc-event-border-color: #fd7e14;
+  --fc-event-text-color: #000000;
+}
+
 .category-part-time {
   --fc-event-bg-color: #146c43;
   --fc-event-border-color: #146c43;
@@ -47,3 +53,29 @@
 .text-pre-wrap {
   white-space: pre-wrap;
 }
+
+/*
+  課題・タスクの一覧（未完了・完了の2つの表）。列の幅を決めて、2つの表の
+  列をそろえる（幅を中身に合わせると、表ごとにずれるため）。完了と操作の
+  列は、中身が入る幅、締切と対象授業の列は、表の幅に対する割合。課題名の
+  列は、残りの幅を使う。
+*/
+.task-table {
+  table-layout: fixed;
+}
+
+.task-col-completed {
+  width: 3rem;
+}
+
+.task-col-due {
+  width: 26%;
+}
+
+.task-col-subject {
+  width: 17%;
+}
+
+.task-col-actions {
+  width: 8rem;
+}
```

## 段階2：課題・タスクモードの画面

### 2-1. `app/templates/index.html`（全文：付録F）
要点：
- 課題・タスクモード（`tasks-pane`）の「課題・タスク（準備中）」の1行を、次に置き換える（上から）：読み込み中（`task-loading`。最初は隠す）、取得の失敗（`task-load-error`。メッセージと「再読み込み」）、本体（`task-content`。最初は隠す）。本体の中は、完了の切り替えのエラー（`task-action-error`）、見出し「未完了」と「課題を追加」ボタン（`task-add-button`。`data-bs-toggle="modal"` で `task-modal` を開く）、未完了の0件の文言と表、見出し「完了」、完了の0件の文言と表。2つの表の見出しは、「完了」「締切」「課題名」「対象授業」「操作」（右寄せ）。表には `task-table`、見出しのセルには列の幅のclassを付ける
- 授業の削除の確認のモーダル（`subject-delete-modal`）のあと、予定の詳細パネル（`event-modal`）の前に、3つのモーダルを足す（どれも `<main>` の外。`fade` を付ける）
  - 追加（`task-modal`）：見出し「課題を追加」、フォームの上部のエラー、課題名、対象授業（`select`。選択肢は空。`tasks.js` が作る）と、その下の説明（`task-subject-note`。`select` の `aria-describedby`）、締切日（`type="date"`）・締切時刻（`type="time"`）と、その下のエラー（2つに共通の `task-due-error`）、詳細・メモ、「キャンセル」「登録する」。課題名・対象授業・締切日・締切時刻に `required`
  - 編集（`task-edit-modal`）：見出し（`task-edit-modal-title`。文言は `tasks.js` が入れる）、フォームの上部のエラー、課題名（タイトル）の欄（ラベル `task-edit-title-label` の文言は `tasks.js` が入れる）、対象授業の行（`task-edit-subject-row`。その他では隠す）、締切日・締切時刻、詳細・メモ、「キャンセル」「保存する」
  - 削除の確認（`task-delete-modal`）：見出し「課題・タスクを削除」、対象（`task-delete-target`）、エラー（`task-delete-error`。最初は隠す）、「削除は取り消せません。」（`task-delete-warning`）、「キャンセル」（`task-delete-cancel-button`）「削除する」（`task-delete-submit-button`）。モーダルと「削除する」に、`aria-describedby="task-delete-target task-delete-warning"`
- 015-L1（授業のモーダル）：
  - 削除の確認のモーダル（`subject-delete-modal`）と「削除する」（`subject-delete-submit-button`）に、`aria-describedby="subject-delete-target subject-delete-counts subject-delete-warning"`。「削除は取り消せません。」の `<p>` に `id="subject-delete-warning"`
  - 編集の「保存する」（`subject-edit-submit-button`）に、`aria-describedby="subject-edit-notice"`
- 文言は、`docs/ui_ux.md` の「課題・タスクモード」のとおり

015-L1で変わる行（確認用。`main` の行（`-`）と、このタスクの行（`+`）だけを並べた。前後の行は省いた。課題・タスクモードの本体と3つのモーダルの全文は、付録F）：

```diff
-          <button type="submit" id="subject-edit-submit-button" class="btn btn-primary">保存する</button>
+          <button type="submit" id="subject-edit-submit-button" class="btn btn-primary" aria-describedby="subject-edit-notice">保存する</button>
-<div class="modal fade" id="subject-delete-modal" tabindex="-1" aria-labelledby="subject-delete-modal-title" aria-hidden="true">
+<div class="modal fade" id="subject-delete-modal" tabindex="-1" aria-labelledby="subject-delete-modal-title" aria-describedby="subject-delete-target subject-delete-counts subject-delete-warning" aria-hidden="true">
-        <p class="text-danger mb-0">削除は取り消せません。</p>
+        <p id="subject-delete-warning" class="text-danger mb-0">削除は取り消せません。</p>
-        <button type="button" id="subject-delete-submit-button" class="btn btn-danger" disabled>削除する</button>
+        <button type="button" id="subject-delete-submit-button" class="btn btn-danger" aria-describedby="subject-delete-target subject-delete-counts subject-delete-warning" disabled>削除する</button>
```

足すDOMの `id`（53個）：

| 場所 | `id` |
|---|---|
| 課題・タスクモードの本体（13個） | `task-loading`、`task-load-error`、`task-load-error-message`、`task-retry-button`、`task-content`、`task-action-error`、`task-add-button`、`task-incomplete-empty`、`task-incomplete-list`、`task-incomplete-body`、`task-completed-empty`、`task-completed-list`、`task-completed-body` |
| 追加のモーダル（15個） | `task-modal`、`task-modal-title`、`task-form`、`task-form-error`、`task-title`・`task-title-error`、`task-subject`・`task-subject-note`・`task-subject-error`、`task-due-date`・`task-due-time`・`task-due-error`、`task-notes`・`task-notes-error`、`task-submit-button` |
| 編集のモーダル（17個） | `task-edit-modal`、`task-edit-modal-title`、`task-edit-form`、`task-edit-form-error`、`task-edit-title-label`・`task-edit-title`・`task-edit-title-error`、`task-edit-subject-row`・`task-edit-subject`・`task-edit-subject-note`・`task-edit-subject-error`、`task-edit-due-date`・`task-edit-due-time`・`task-edit-due-error`、`task-edit-notes`・`task-edit-notes-error`、`task-edit-submit-button` |
| 削除の確認のモーダル（7個） | `task-delete-modal`、`task-delete-modal-title`、`task-delete-target`、`task-delete-error`、`task-delete-warning`、`task-delete-cancel-button`、`task-delete-submit-button` |
| 015-L1（1個） | `subject-delete-warning` |

行のチェックボックスとボタンの `id` は、`task-complete-<id>`・`task-edit-<id>`・`task-delete-<id>`（`tasks.js` が作る。授業の `subject-edit-<id>` と同じ形）。

### 2-2. `app/static/js/tasks.js`（新規。全文：付録G）
ファイルの構成（上から順に）：

| 名前 | 種類 | 内容 |
|---|---|---|
| `ASSIGNMENT`・`DEFAULT_DUE_TIME`・`SUBJECT_PLACEHOLDER`・`SUBJECT_LOADING_NOTE` | 定数 | 課題のカテゴリの保存値 `"assignment"`、締切時刻の初期値 `"23:59"`、対象授業の先頭の選択肢「選択してください」、取得中の説明「授業を読み込み中…」 |
| `TASK_FIELDS`・`TASK_FORM_ERROR_ID`・`TASK_SUBMIT_LABELS` | 定数 | 追加フォームの項目（APIの `fields` の項目名 → 入力欄とエラーの表示先。`due_datetime` は、締切日・締切時刻の2つの入力欄）、エラーの表示先、ボタンの文言 |
| `TASK_EDIT_FIELDS`・`TASK_EDIT_FORM_ERROR_ID`・`TASK_EDIT_SUBMIT_LABELS`・`TASK_DELETE_SUBMIT_LABELS` | 定数 | 編集フォームの項目、エラーの表示先、ボタンの文言（「保存する」「保存中…」、「削除する」「削除中…」） |
| `requestSerial` | 変数 | 一覧の取得の通し番号（選択に依存する取得と同じ考え方で、古い応答を捨てる） |
| `editingTask`・`deletingTask` | 変数 | 編集・削除の対象（一覧の行の値のコピー） |
| `addSerial`・`editSerial`・`deleteSerial` | 変数 | 追加・編集・削除のモーダルを開くたびに増やす通し番号（モーダルの中で始める要求の規則） |
| `taskLabel` | 関数 | 課題・タスクを表す文字列「「タイトル」（締切 2026年10月20日（火） 23:59）」。`aria-label` と、削除の確認の文言で使う |
| `dueDateTimeOf` | 関数 | 締切日と締切時刻の入力欄の値を、APIの日時 `YYYY-MM-DDTHH:MM` にする |
| `showTaskLoading`・`showTaskLoadError` | 関数 | 一覧の読み込み中・取得の失敗の表示 |
| `showActionError`・`hideActionError` | 関数 | 完了の切り替えのエラーの表示・消去（一覧の上部） |
| `createTaskRow(task, overdueBefore)` | 関数 | 一覧の1行（完了のチェックボックス、締切と「期限切れ」の印、アイコン・見えないカテゴリ名・タイトル・メモ、対象授業（なければ「—」）、「編集」「削除」）。`overdueBefore` は、期限切れの判定に使う今の日時（完了の表では `null`） |
| `renderTaskTable` | 関数 | 1つの表の行を作り直す（0件なら、表を隠して、0件の文言を出す）。引数は名前つき（`bodyId`・`listId`・`emptyId`・`overdueBefore`） |
| `renderTasks` | 関数 | 一覧を、未完了（APIの並び）と完了（APIの並びの逆）に分けて表示する。期限切れは、表示するときの日時（`localDateTimeString()`）で判定する |
| `loadTasks({ showLoading = true } = {})` | 関数 | `GET /api/tasks` で一覧を取得する（下の順序） |
| `toggleTaskCompleted(task, checkbox)` | 関数 | 完了の切り替え（下の順序） |
| `renderSubjectOptions(select, subjects, extraSubject)` | 関数 | 対象授業のプルダウンの選択肢を作り直す。先頭は「選択してください」（値は空）。`extraSubject`（`{ id, subject_name }` か `null`）は、今の学期の授業にない、課題の今の対象授業（編集のとき） |
| `fetchCurrentSubjects` | 関数 | `GET /api/semesters` の結果から、`chooseCurrentSemester` で今の学期を選び、`GET /api/subjects?semester_id=<id>` で、その学期の授業を取得する。学期が0件なら、2つ目の要求をせず、`{ semester: null, subjects: [] }` |
| `subjectNoteOf(semester, subjects)` | 関数 | 対象授業の欄の下の説明（学期がない、授業がない、「2026年度 後期の授業から選びます」の3つ） |
| `prepareAddModal` | 関数 | 追加のモーダルの `show.bs.modal`（下の順序） |
| `submitTask` | 関数 | 課題の登録（下の順序） |
| `openEditModal`・`prepareEditModal`・`submitTaskEdit` | 関数 | 編集（下の順序） |
| `openDeleteModal`・`showDeleteError`・`hideDeleteError`・`prepareDeleteModal`・`submitTaskDelete` | 関数 | 削除の確認と削除（下の順序） |
| `initTasks` | 関数（`export`） | 課題・タスクのモードのタブ（`tasks-tab`）の `shown.bs.tab` で、切り替えのエラーを消して一覧を取得する。「再読み込み」。3つのモーダルに、`trackModalShowing` と、イベント（`show.bs.modal`・`shown.bs.modal`・`submit`・`click`）を付ける |

`loadTasks`（一覧の取得）の順序：
1. `requestSerial` を増やして控える。`showLoading` が `true` なら、読み込み中を表示する（一覧を隠す）
2. `GET /api/tasks`（`try` で囲むのは、この要求だけ）
3. どちらの場合も、新しい取得を始めていれば（`requestSerial` が違えば）、何もしない
4. 失敗：取得の失敗（メッセージと「再読み込み」）を表示する
5. 成功：`renderTasks` で表示する

一覧の取得は、モードを開くたび（`shown.bs.tab`）と「再読み込み」では、読み込み中を表示して行い、完了の切り替え・追加・編集・削除の成功のあとは、`loadTasks({ showLoading: false })`（今の一覧を出したまま）で行う（授業の一覧と同じ形）。ページを開いたときには取得しない（課題・タスクのモードは、最初は隠れているため）。

`toggleTaskCompleted`（完了の切り替え）の順序：
1. 切り替えのエラーを消し、チェックボックスを押せなくする
2. `PATCH /api/tasks/<id>` に `{ is_completed: <チェックボックスの今の状態> }`（`try` で囲むのは、この要求だけ）
3. 失敗：チェックを元に戻し、押せるようにし、エラーを一覧の上部に表示する
4. 成功：一覧を取得し直す（行が、もう一方の表へ移る）

`prepareAddModal`（追加のモーダルを開くとき）の順序：
1. `addSerial` を増やして控える。フォームを初期値に戻す（課題名・締切日・詳細／メモは空、締切時刻は `23:59`）。エラーを消し、「登録する」を戻す。対象授業の選択肢を「選択してください」だけにし、説明を「授業を読み込み中…」にする
2. `fetchCurrentSubjects()`（`try` で囲むのは、この要求だけ）
3. どちらの場合も、モーダルを開き直していれば（`addSerial` が違えば）、何もしない
4. 失敗：説明を消し、エラーを、フォームの上部に表示する（`showApiError`）。選択肢は「選択してください」だけのまま（必須のため、登録はブラウザの入力チェックで止まる）
5. 成功：今の学期の授業で選択肢を作り直し、説明を `subjectNoteOf` の文言にする

`submitTask`（課題の登録）の順序：
1. 既定の送信を止める。今の `addSerial` を控える。エラーを消し、「登録する」を「登録中…」（無効）にする
2. `POST /api/tasks` に `category`（`"assignment"`）・`subject_id`（選んだ授業のid。数値）・`title`・`due_datetime`（`dueDateTimeOf`）・`notes` を送る（`try` で囲むのは、この要求だけ）
3. 失敗：モーダルを開き直していれば、何もしない。そうでなければ、エラーを表示し（`showApiError`）、ボタンを戻す（モーダルは開いたまま）
4. 成功：モーダルを開き直していなければ、`hideModal` で閉じる。一覧を取得し直す

`prepareEditModal`（編集のモーダルを開くとき）の順序：
1. `editSerial` を増やして控える。見出し（課題は「課題を編集」、その他は「その他（締切のみ）を編集」）とラベル（「課題名」か「タイトル」）を入れる。今の値（タイトル・締切日・締切時刻・詳細／メモ）を入れ、エラーを消し、「保存する」を戻す
2. 対象授業の行を、課題なら表示、その他なら隠す。その他では、プルダウンを無効にする（`disabled`。隠した欄の必須の入力チェックで、保存が止まらないようにするため）。その他は、選択肢を「選択してください」だけにし、説明を消して、ここで終わる
3. 課題：選択肢を「選択してください」と今の対象授業だけにして、今の対象授業を選ぶ。説明を「授業を読み込み中…」にする
4. `fetchCurrentSubjects()`（`try` で囲むのは、この要求だけ）。どちらの場合も、モーダルを開き直していれば、何もしない
5. 失敗：説明を消し、エラーを、フォームの上部に表示する（選択肢は、3のまま。ほかの項目は保存できる）
6. 成功：今の学期の授業で選択肢を作り直す。今の対象授業が、今の学期の授業にない場合は、選択肢に足す（「選択してください」のすぐ下）。今の対象授業を選び、説明を `subjectNoteOf` の文言にする

`submitTaskEdit`（編集の保存）の順序：
1. 既定の送信を止める。今の `editSerial` と、対象を控える。エラーを消し、「保存する」を「保存中…」（無効）にする
2. `PATCH /api/tasks/<id>` に、`title`・`due_datetime`・`notes` と、課題なら `subject_id` を送る（変えていない項目も、今の値のまま送る。`try` で囲むのは、この要求だけ）
3. 失敗：モーダルを開き直していれば、何もしない。そうでなければ、エラーを表示し、ボタンを戻す
4. 成功：モーダルを開き直していなければ、`hideModal` で閉じる。一覧を取得し直す

削除：
- `prepareDeleteModal`（削除の確認のモーダルの `show.bs.modal`）：`deleteSerial` を増やす。対象の文字列「「タイトル」（締切 …）を削除します。」を表示し、エラーを消し、「削除する」を戻す（件数の取得はない。課題・タスクは、一緒に削除されるデータを持たないため）
- `submitTaskDelete`：今の `deleteSerial` と、対象のidを控える。エラーを消し、「削除する」を「削除中…」（無効）にする。`DELETE /api/tasks/<id>`（`try` で囲むのは、この要求だけ）。失敗：モーダルを開き直していれば、何もしない。そうでなければ、エラーをモーダルの中に表示し、ボタンを戻す。成功：モーダルを開き直していなければ、`hideModal` で閉じる。一覧を取得し直す

注意：
- 編集・削除のモーダルは、JavaScriptから開く（`window.bootstrap.Modal.getOrCreateInstance(...).show()`）。値は、`show.bs.modal` で入れる（授業の編集・削除と同じ形）
- 削除の確認に、ブラウザ標準の `confirm` を使わない
- 追加・編集・削除のあとに、メッセージを出さない（`docs/ui_ux.md`）
- 期限切れは、締切日時の文字列（`YYYY-MM-DDTHH:MM`）と、今の日時の文字列の大小で比べる（桁が固定されているため。日付の文字列の比べ方と同じ）。締切日時と同じ分は、期限切れではない
- 課題・タスクのモードは、ほかのモードと `CustomEvent` でつながらない（`semester-selected` を購読しない。今の学期は、モーダルを開くたびに、学期の一覧から決める）

### 2-3. `app/static/js/main.js`（全文：付録H）
要点：`tasks.js` の `initTasks` を `import` し、`initSemesters()` のあと、`initCalendar()` の前に呼ぶ（カレンダーは、最後のまま）。

`main` からの差分（確認用）：

```diff
--- a/app/static/js/main.js
+++ b/app/static/js/main.js
@@ -2,12 +2,15 @@ import { initCalendar } from "./calendar.js";
 import { initClosures } from "./closures.js";
 import { initSemesters } from "./semesters.js";
 import { initSubjects } from "./subjects.js";
+import { initTasks } from "./tasks.js";
 
 // 今後のモードの初期化も、ここに足す。
 // semester-selectedを購読する側を、イベントを発行する側より先に初期化する。
 initSubjects();
 initClosures();
 initSemesters();
+// 課題・タスクは、ほかのモードとイベントでつながらない。
+initTasks();
 // カレンダーは、ほかのモードとイベントでつながらない。予期しない例外で、
 // ほかのモードの初期化が止まらないように、最後に初期化する。
 initCalendar();
```

### 2-4. 変わる挙動・変わらない挙動

| 操作 | 変わる・変わらない |
|---|---|
| 課題・タスクモード | 「課題・タスク（準備中）」の代わりに、一覧（未完了・完了）、完了の切り替え、「課題を追加」、各行の「編集」「削除」が使える |
| 授業モード（学期の初期選択） | 変わらない（規則を `current_semester.js` に移しただけ） |
| 授業の編集・削除 | 見た目と動きは変わらない。削除の確認のモーダルと「削除する」、編集の「保存する」に、読み上げの説明（`aria-describedby`）が付く |
| 授業の登録・休講日・学期の登録 | 変わらない |
| カレンダー | 変わらない（課題の色のclassを足したが、まだ使わない。締切は、まだ表示しない） |
| API・DB | 変わらない |

## JavaScriptの共通の規則
`.github/copilot-instructions.md` の「コーディング方針」のJavaScriptの規則と、`docs/architecture.md` の「JavaScriptの構成（ES modules）」の規則（`innerHTML` などを使わない、`textContent` で表示する、`fetch` は `api.js` だけ、`try` で囲むのは要求だけ、名前つきの引数、モードのファイル同士は `import` しない、1行は80文字以内）。付録の全文は、これらに合っている（「Copilot確認手順」の3・6で確かめる）。

## 変更してよい既存のテスト
なし（Pythonを変えないため、テストは変えない・足さない）。**既存のテスト（787件）が、想定外に失敗した場合**は、原因を調べ、そこで実装を止めて、チャットで報告する。

## 実装手順
1. ブランチ・作業ツリーの確認。設計資料が更新されていることを確認する（「Copilot確認手順」の1の `grep`）。更新されていなければ、何も変更せずに停止して報告する
2. 作業の前の状態を記録する：開発用DBの有無・ハッシュ・件数（「Copilot確認手順」の1。**`sqlite3` は `-readonly` を付ける**）。`python -m pytest -q` が787件、すべて合格すること（合格しなければ、何も変更せずに停止して報告する）
3. **（段階1）** 「全文からファイルを作るスクリプト」を `python - 1` で実行する。`python -m pytest -q` が787件、すべて合格すること。「全文との比較」（「Copilot確認手順」の4）を `python - 1` で実行し、5ファイルとも「一致」
4. **（段階2）** スクリプトを `python - 2` で実行する。`python -m pytest -q` が787件、すべて合格すること。「全文との比較」を `python - 2` で実行し、8ファイルとも「一致」
5. 「Copilot確認手順」の2・3・5・6・7を実施する
6. 結果を報告して、応答を終える（コマンドの出力は、要約せずに、そのまま貼る。サーバーを起動していないこと、ブラウザでの確認をしていないことを明記する）

各段階の終わりに、`python -m pytest -q` の結果（件数・警告）と、全文との比較の結果を控えておく（最終報告に、出力をそのまま貼る）。

## 完了条件
- `python -m pytest -q` が、作業の前と、段階1・段階2の終わりに、**787件**すべて合格する（失敗・エラー・スキップが0件）
- 変更・新規のファイルが、「実装対象ファイル」の8つだけ
- 8ファイルが、このTask MDの全文と1文字も違わない（「Copilot確認手順」の4が、段階1の終わりに5ファイル、段階2の終わりに8ファイルとも「一致」）
- `app/static/js/` のJavaScriptのファイルに、80文字を超える行がない
- 「Copilot確認手順」の5（画面のHTMLの確認）と6（検索と差分）が、期待どおり
- 実施の前後で、開発用DB（`instance/app.db`）のハッシュと、`semesters`・`subjects`・`closures`・`events`・`tasks` の件数が同じ
- 「Komaの確認」が、期待どおり
- レビューで承認される

## Copilot確認手順
**`sqlite3` は、必ず `-readonly` を付けて実行する**（011-L1）。**それぞれのコマンドの出力を、要約せずに、そのまま報告に貼る**（014-L1）。**コマンドは、書いてあるとおりに実行する（書き換えた場合は、報告に書く。016-N1）。**

```
# 1. 実施前
git branch --show-current      # feature/017-tasks-ui
git status                     # 変更なし
grep -c -F "current_semester.js" docs/architecture.md          # 3以上
grep -n -F -e "### 完了の切り替え" -e "### 削除（確認のモーダル）" docs/ui_ux.md   # 2件（課題・タスクモードの節）
grep -c -F "015-L1" docs/ui_ux.md                               # 2以上
grep -n -F "今の学期の授業から選ぶ" docs/requirements.md        # 1件
grep -n -F "止まる場面の応答" .github/copilot-instructions.md  # 数件
ls -l instance/app.db          # 存在すること（なければ、何も変更せずに停止して報告する）
shasum -a 256 instance/app.db
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"
python -m pytest -q            # 787 passed

# 2. 各段階の終わり
python -m pytest -q            # 段階1・段階2とも 787 passed

# 3. 1行の長さ（出力がなければ合格）
python - <<'EOF'
from pathlib import Path
for path in sorted(Path("app/static/js").glob("*.js")):
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, 1):
        if len(line) > 80:
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
        "app/static/js/current_semester.js",
        "app/static/js/semesters.js",
        "app/static/js/dates.js",
        "app/static/js/categories.js",
        "app/static/css/style.css",
    ],
    "2": [
        "app/templates/index.html",
        "app/static/js/tasks.js",
        "app/static/js/main.js",
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
expected_files = read_full_texts("docs/tasks/017_tasks_ui.md")
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
    "task-loading", "task-load-error", "task-load-error-message",
    "task-retry-button", "task-content", "task-action-error",
    "task-add-button", "task-incomplete-empty", "task-incomplete-list",
    "task-incomplete-body", "task-completed-empty", "task-completed-list",
    "task-completed-body",
    "task-modal", "task-modal-title", "task-form", "task-form-error",
    "task-title", "task-title-error", "task-subject", "task-subject-note",
    "task-subject-error", "task-due-date", "task-due-time", "task-due-error",
    "task-notes", "task-notes-error", "task-submit-button",
    "task-edit-modal", "task-edit-modal-title", "task-edit-form",
    "task-edit-form-error", "task-edit-title-label", "task-edit-title",
    "task-edit-title-error", "task-edit-subject-row", "task-edit-subject",
    "task-edit-subject-note", "task-edit-subject-error",
    "task-edit-due-date", "task-edit-due-time", "task-edit-due-error",
    "task-edit-notes", "task-edit-notes-error", "task-edit-submit-button",
    "task-delete-modal", "task-delete-modal-title", "task-delete-target",
    "task-delete-error", "task-delete-warning", "task-delete-cancel-button",
    "task-delete-submit-button",
    "subject-delete-warning",
]
ORDER = [
    "tasks-pane", "task-incomplete-body", "task-completed-body",
    "subject-delete-modal", "task-modal", "task-edit-modal",
    "task-delete-modal", "event-modal",
]
DESCRIBED_BY = [
    'aria-describedby="subject-delete-target subject-delete-counts '
    'subject-delete-warning"',
    'aria-describedby="subject-edit-notice"',
    'aria-describedby="task-delete-target task-delete-warning"',
    'aria-describedby="task-subject-note"',
    'aria-describedby="task-edit-subject-note"',
]

with tempfile.TemporaryDirectory() as work_directory:
    database_path = Path(work_directory) / "check.db"
    app = create_app(
        {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"}
    )
    client = app.test_client()
    html = client.get("/").get_data(as_text=True)
    ids = re.findall(' id="([^"]+)"', html)
    print("新しいid:", [ids.count(i) for i in EXPECTED_IDS])
    print("重複したid:", sorted({i for i in ids if ids.count(i) > 1}))
    positions = [html.index(f'id="{i}"') for i in ORDER]
    print("並び:", positions == sorted(positions))
    print("モーダルは<main>の外:", html.index("</main>") < positions[3])
    print("準備中の表示:", html.count("課題・タスク（準備中）"))
    print("説明（aria-describedby）:", [html.count(d) for d in DESCRIBED_BY])
    print("課題・タスクの表:", html.count("task-table"))
    # JavaScriptが getElement("…") で使うidと、tasks.js の「"task-…"」の
    # 文字列のidが、HTMLにあること。
    missing = []
    get_element = 'getElement[(][ ' + newline + ']*"([^"]+)"'
    for path in sorted(Path("app/static/js").glob("*.js")):
        text = path.read_text(encoding="utf-8")
        for element_id in re.findall(get_element, text):
            if element_id not in ids:
                missing.append(f"{path.name}:{element_id}")
    tasks_text = Path("app/static/js/tasks.js").read_text(encoding="utf-8")
    for element_id in re.findall('"(task-[a-z-]+)"', tasks_text):
        if element_id not in ids:
            missing.append(f"tasks.js:{element_id}")
    print("JavaScriptのidで、HTMLにないもの:", missing)
    for name in [
        "js/current_semester.js", "js/semesters.js", "js/dates.js",
        "js/categories.js", "js/tasks.js", "js/main.js", "css/style.css",
    ]:
        response = client.get(f"/static/{name}")
        print(name, response.status_code, response.mimetype)
        response.close()
EOF

# 6. 検索と差分（段階2の終わり）
grep -rn -F -e innerHTML -e outerHTML -e insertAdjacentHTML -e "document.write" -e "eval(" -e localStorage -e sessionStorage -e setTimeout -e "export default" -e "var " -e ".style" -e "confirm(" app/static/js/   # 出力なし
grep -rn -F "fetch(" app/static/js/                                # api.js の中の1件だけ
grep -rn -F "chooseInitialSemester" app/static/js/                 # 出力なし
grep -rn -F "chooseCurrentSemester" app/static/js/                 # 5件：current_semester.js 1（定義）、semesters.js 2、tasks.js 2
grep -rn -F -e "trackModalShowing(" -e "hideModal(" app/static/js/ # 14件：ui.js 2（定義）、semesters.js 2、subjects.js 4、tasks.js 6
grep -rn -F "window.bootstrap.Modal" app/static/js/                # 6件：calendar.js 1、ui.js 1、subjects.js 2、tasks.js 2
grep -rn -F -e '"assignment"' -e '"other"' app/static/js/          # 1件：tasks.js の ASSIGNMENT の定義
grep -n -F "export " app/static/js/dates.js app/static/js/categories.js app/static/js/current_semester.js app/static/js/tasks.js   # 11件：dates.js 5、categories.js 4、current_semester.js 1、tasks.js 1（initTasks）
grep -n -F -e onclick -e "style=" app/templates/index.html app/templates/base.html   # 出力なし
git diff --numstat app/static/js/semesters.js app/static/js/dates.js app/static/js/categories.js app/static/css/style.css app/templates/index.html app/static/js/main.js
wc -l app/static/js/current_semester.js app/static/js/tasks.js
git diff --stat -- app/*.py app/routes/ app/models/ migrations/ tests/ requirements.txt pytest.ini run.py app/templates/base.html app/static/js/api.js app/static/js/ui.js app/static/js/calendar.js app/static/js/subjects.js app/static/js/closures.js   # 出力なし

# 7. 実施後
shasum -a 256 instance/app.db  # 実施前と同じ
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"   # 実施前と同じ
git status                     # 変更：6ファイル。新規：current_semester.js・tasks.js
git diff --stat
```

| 確認 | 期待する結果 |
|---|---|
| `python -m pytest -q` | 実施前、段階1・段階2の終わりとも、787件がすべて合格。失敗・エラー・スキップが0件。`migrations/env.py` の `DeprecationWarning` は、出ても構わない（報告する） |
| 1行の長さ（3） | 出力なし |
| 全文との比較（4） | `全文の数：8` と、段階1の終わりは5ファイル、段階2の終わりは8ファイルとも「一致」。「不一致」が出たら、手で直さず、その段階の「全文からファイルを作るスクリプト」をもう一度実行して全文に戻し、2からやり直す（戻したことを報告する）。Task MDの全文のほうを変える必要があると判断した場合は、停止して報告する |
| 画面のHTMLの確認（5） | 「新しいid:」のあとが、`1` が53個の一覧。「重複したid: []」。「並び: True」「モーダルは<main>の外: True」「準備中の表示: 0」「説明（aria-describedby）: [2, 1, 2, 1, 1]」「課題・タスクの表: 2」「JavaScriptのidで、HTMLにないもの: []」。6つのJavaScriptのファイルが `200 text/javascript`、`css/style.css` が `200 text/css` |
| 検索と差分（6） | 上のコメントのとおり。`git diff --numstat` は、`2 35 app/static/js/semesters.js`、`15 0 app/static/js/dates.js`、`31 7 app/static/js/categories.js`、`32 0 app/static/css/style.css`、`166 5 app/templates/index.html`、`3 0 app/static/js/main.js`（表示の順は、Gitの並びでよい）。`wc -l` は、`42 app/static/js/current_semester.js`、`657 app/static/js/tasks.js`。件数が違う場合は、その行を報告に書く |
| 開発用DB | 実施の前後で、ハッシュと、5つのテーブルの件数が同じ |
| `git status` | 変更：`app/static/css/style.css`、`app/static/js/categories.js`、`app/static/js/dates.js`、`app/static/js/main.js`、`app/static/js/semesters.js`、`app/templates/index.html`。新規（`??`）：`app/static/js/current_semester.js`、`app/static/js/tasks.js`。Pythonのファイル・`migrations/`・`tests/`・`docs/`・`.github/`・`requirements.txt`・`run.py`・`instance/`・ほかのJavaScriptのファイル・`base.html` に変更なし |

`.pytest_cache/` や `__pycache__/` が `git status` に表示される場合は、`.gitignore` を変更せず、報告する。**Copilotは、サーバーを起動せず、ブラウザでの確認もしない**（Claude と Koma が行う）。報告に、そのことを明記する。

## Komaの確認
順序：（1）pytest →（2）commit・push とレビューの依頼 →（3）ブラウザでの確認（確認用のサーバー）→（4）開発用DBでの、読み取りだけの確認 →（5）マージ。

### 1. pytest
`python -m pytest -q` を自分で実行し、**787件、すべて合格**することを確かめる。

### 2. push とレビューの依頼
featureブランチを commit・push する（PRを作ってもよい）。新規の2ファイル（`current_semester.js`・`tasks.js`）も、commitに含める。Copilotの完了報告を共有して、Claudeにレビューを頼む。**pushは、マージではない。レビューの承認の前に、マージしない。** 修正が必要になった場合は、同じブランチでCopilotが直し、もう一度pushしてレビューを受ける。

### 3. ブラウザでの確認（確認用のサーバー）
レビューで「承認可能」になったあとに行う。**ブラウザの操作は、Claudeが、ブラウザのパネルまたはChromeで行う。Komaは、サーバーの起動・停止、確認用のデータの登録、DBのハッシュの確認、後片付けを行う**（roadmap の「進め方の決定の記録」、2026-10-12）。

#### 確認の安全のしくみ
- **開発用DBは使わない。** 確認用のDB（`/tmp/schedule-app-check-017/check.db`）を、migrationで作り、そのDBで起動した確認用のサーバーで確かめる（Task 010〜016と同じ方法）。開発用DBには、何も残らない
- 確認用のデータ（下の「確認用のデータの登録」）は、確認用のDBの場所を指定して、すべてアプリのAPIで登録する（課題・タスクも、Task 016のAPIで登録できる）。**このスクリプトは、確認用のDBだけに書き込む**
- 確認の途中の、APIの直接の呼び出し（D4・A6の登録・削除、各項目の読み取り）は、確認用のDBの、確認のために登録したデータに限る（roadmap の「進め方の決定の記録」、2026-10-12）
- ブラウザは、BootstrapとFullCalendarを、インターネット（jsDelivr）から読み込む。インターネットにつながった状態で行う
- 確認の前後で、開発用DBのハッシュが同じことを確かめる

#### 確認の日付
期待する結果は、確認の日（ブラウザの「今日」）が **2026-10-16〜2026-11-29** の間にあることを前提にしている（確認用の学期「2026年度 後期」（2026-09-21〜2027-01-29）が今日を含み、締切が2026-10-01・2026-07-20の課題は期限切れ、2026-11-30以降の課題・タスクは期限切れでないため。A6で登録する学期（2026-10-01〜2026-12-31）も、今日を含む）。この範囲の外の日に行う場合は、行う前にClaudeに伝える。下の表の日付の例は、2026-10-16（金）に確認した場合。

#### 準備
1. `python run.py` が起動していれば、Ctrl＋Cで止める（確認用のサーバーも、5001番を使うため）。開発用DBのハッシュを控える
   ```
   shasum -a 256 instance/app.db
   ```
2. 下の「確認用のサーバーの起動」のコマンドで、確認用のサーバーを起動する（このターミナルは、確認の間、開いたままにする）
3. 別のターミナルを開き、リポジトリのルートで、`.venv` を有効にして、下の「確認用のデータの登録」を実行する（1回だけ）
4. Claudeが、ブラウザで `http://127.0.0.1:5001/` を開き、強制再読み込みをする

#### 確認用のサーバーの起動
ブランチ `feature/017-tasks-ui` のまま、リポジトリのルートで、`.venv` を有効にして、次を実行する（行の先頭に空白を入れずにコピーする）。

```
python - <<'EOF'
from pathlib import Path

from flask_migrate import upgrade

from app import create_app

# 確認用のDB（開発用DBとは別のファイル）。止めて起動し直しても、残る。
check_directory = Path("/tmp/schedule-app-check-017")
check_directory.mkdir(exist_ok=True)
database_path = check_directory / "check.db"
app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"})
with app.app_context():
    upgrade(directory="migrations")
print(f"確認用のDB：{database_path}", flush=True)
app.run(host="127.0.0.1", port=5001, debug=False)
EOF
```

期待する出力：初めての起動では、`Running upgrade  -> 0280f6cf8d09, initial tables` と `Running upgrade 0280f6cf8d09 -> 42bd53808fa1, add closures table`、「確認用のDB：/tmp/schedule-app-check-017/check.db」、`Running on http://127.0.0.1:5001`。起動し直したときは、`Running upgrade` の行が出ない。

#### 確認用のデータの登録
確認用のサーバーを起動したあとに、別のターミナルで、1回だけ実行する（行の先頭に空白を入れずにコピーする）。

```
python - <<'EOF'
from pathlib import Path

from app import create_app

# 確認用のDBだけに書き込む（開発用DBは使わない）。DBは、確認用のサーバーが、
# 起動のときにmigrationで作っておいたものを使う。
database_path = Path("/tmp/schedule-app-check-017/check.db")
if not database_path.exists():
    raise SystemExit("確認用のDBがありません。先に、確認用のサーバーを起動してください")
app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"})
client = app.test_client()
newline = chr(10)


def send(method, url, body, expected_status):
    response = client.open(url, method=method, json=body)
    if response.status_code != expected_status:
        raise SystemExit(f"中止：{method} {url} {response.status_code} {response.get_json()}")
    return response.get_json()


# 学期・授業・課題・タスクは、すべてAPIで登録する。
autumn = send("POST", "/api/semesters", {"name": "2026年度 後期", "start_date": "2026-09-21", "end_date": "2027-01-29"}, 201)
spring = send("POST", "/api/semesters", {"name": "2026年度 前期", "start_date": "2026-04-06", "end_date": "2026-07-31"}, 201)
subjects = [
    send("POST", "/api/subjects", {"semester_id": autumn["id"], "subject_name": "テスト：月曜1限", "weekday": 0, "start_time": "09:00", "end_time": "10:00", "room": "3号館201"}, 201),
    send("POST", "/api/subjects", {"semester_id": autumn["id"], "subject_name": "テスト：水曜2限", "weekday": 2, "start_time": "10:40", "end_time": "12:10"}, 201),
    send("POST", "/api/subjects", {"semester_id": spring["id"], "subject_name": "テスト：前期の授業", "weekday": 4, "start_time": "09:00", "end_time": "10:00"}, 201),
]
tasks = [
    {"category": "assignment", "subject_id": subjects[0]["id"], "title": "テスト：レポート", "due_datetime": "2026-11-30T23:59", "notes": "A4で2枚" + newline + "手書き不可"},
    {"category": "assignment", "subject_id": subjects[0]["id"], "title": "テスト：期限切れの課題", "due_datetime": "2026-10-01T23:59"},
    {"category": "other", "title": "テスト：その他の締切", "due_datetime": "2026-12-01T17:00"},
    {"category": "assignment", "subject_id": subjects[1]["id"], "title": "テスト：完了した課題", "due_datetime": "2026-10-05T23:59"},
    {"category": "assignment", "subject_id": subjects[2]["id"], "title": "テスト：前期の課題", "due_datetime": "2026-07-20T23:59"},
    {"category": "assignment", "subject_id": subjects[1]["id"], "title": "テスト：完了した課題2", "due_datetime": "2026-10-10T12:00"},
]
created = [send("POST", "/api/tasks", task, 201) for task in tasks]
# 4番目と6番目を、完了にする。
for index in (3, 5):
    send("PATCH", f"/api/tasks/{created[index]['id']}", {"is_completed": True}, 200)
print("授業のid：", [subject["id"] for subject in subjects])
print("課題・タスクのid：", [task["id"] for task in created])
print("一覧の完了の状態：", [task["is_completed"] for task in client.get("/api/tasks").get_json()])
EOF
```

期待する出力：`授業のid： [1, 2, 3]`、`課題・タスクのid： [1, 2, 3, 4, 5, 6]`、`一覧の完了の状態： [False, False, True, True, False, False]`（一覧は、締切日時の早い順。4番目と6番目の課題を、完了にした）。2回目に実行すると、「中止：POST /api/semesters 400 …」で止まり、何も増えない（そのままでよい）。

以下、idは、この出力のとおり。

| 種類 | id：内容 |
|---|---|
| 授業 | 1：テスト：月曜1限（2026年度 後期）、2：テスト：水曜2限（2026年度 後期）、3：テスト：前期の授業（2026年度 前期） |
| 課題・タスク | 1：テスト：レポート（授業1、2026-11-30 23:59、メモ2行）、2：テスト：期限切れの課題（授業1、2026-10-01 23:59）、3：テスト：その他の締切（その他、2026-12-01 17:00）、4：テスト：完了した課題（授業2、2026-10-05 23:59、完了）、5：テスト：前期の課題（授業3、2026-07-20 23:59）、6：テスト：完了した課題2（授業2、2026-10-10 12:00、完了） |

#### L. 一覧（ページを開いた状態から）

| No | 操作 | 期待する結果 |
|---|---|---|
| L1 | 画面下の「課題・タスク」を押す | 見出し「未完了」と、その右に「課題を追加」ボタン。表の見出しは「完了」「締切」「課題名」「対象授業」「操作」（「操作」は右寄せ）。未完了の行は、上から、①「2026年7月20日（月） 23:59」と赤い「期限切れ」、「✅ テスト：前期の課題」、「テスト：前期の授業」 ②「2026年10月1日（木） 23:59」と「期限切れ」、「✅ テスト：期限切れの課題」、「テスト：月曜1限」 ③「2026年11月30日（月） 23:59」（印なし）、「✅ テスト：レポート」（その下に小さく「A4で2枚」「手書き不可」の2行）、「テスト：月曜1限」 ④「2026年12月1日（火） 17:00」、「⭐ テスト：その他の締切」、「—」。見出し「完了」の表は、①「2026年10月10日（土） 12:00」「✅ テスト：完了した課題2」「テスト：水曜2限」 ②「2026年10月5日（月） 23:59」「✅ テスト：完了した課題」「テスト：水曜2限」（締切の新しい順。チェックが入っている。期限切れの印はない）。各行の右端に、「編集」（グレーの枠）と「削除」（赤の枠）。2つの表の列の位置がそろっている |
| L2 | コンソールで、`[...document.querySelectorAll("#task-incomplete-body tr")].map((tr) => [tr.querySelector("input").getAttribute("aria-label"), tr.querySelector(".visually-hidden").textContent])` と、`[...document.querySelectorAll("#task-incomplete-body tr:first-child button")].map((b) => b.getAttribute("aria-label"))` を実行する | 1つ目：`[["「テスト：前期の課題」（締切 2026年7月20日（月） 23:59）の完了", "課題："], ["「テスト：期限切れの課題」（締切 2026年10月1日（木） 23:59）の完了", "課題："], ["「テスト：レポート」（締切 2026年11月30日（月） 23:59）の完了", "課題："], ["「テスト：その他の締切」（締切 2026年12月1日（火） 17:00）の完了", "その他："]]`。2つ目：`["「テスト：前期の課題」（締切 2026年7月20日（月） 23:59）を編集", "「テスト：前期の課題」（締切 2026年7月20日（月） 23:59）を削除"]` |

#### T. 完了の切り替え

| No | 操作 | 期待する結果 |
|---|---|---|
| T1 | 「テスト：レポート」の行のチェックボックスを押す | 確認は出ない。行が、完了の表の一番上（締切が最も新しい）に移る。未完了の表は、①前期の課題 ②期限切れの課題 ③その他の締切 の3行 |
| T2 | 完了の表の「テスト：レポート」のチェックを外す | 行が、未完了の表の③（2026年11月30日）に戻る（L1と同じ並び） |
| T3 | **Komaが、確認用のサーバーを止める（Ctrl＋C）。** Claudeが、「テスト：期限切れの課題」のチェックボックスを押す | 一覧の上部に、赤い枠で「サーバーに接続できませんでした。時間をおいて、もう一度お試しください」。チェックは外れたまま（元に戻る）で、押せる。行は、未完了の表に残る |
| T4 | **Komaが、「確認用のサーバーの起動」のコマンドで、確認用のサーバーを起動し直す**（ターミナルで↑キーを押すと、前のコマンドを呼び出せる）。Claudeが、画面下の「カレンダー」を押し、もう一度「課題・タスク」を押す | 赤い枠のエラーが消える。一覧は、L1と同じ（未完了4行、完了2行） |

#### A. 課題の追加

| No | 操作 | 期待する結果 |
|---|---|---|
| A1 | 「課題を追加」を押す | モーダル「課題を追加」が開く。項目は、上から「課題名」「対象授業」「締切日」と「締切時刻」（横に並ぶ）「詳細・メモ（任意）」。対象授業の選択肢は、「選択してください」（選ばれている）「テスト：月曜1限」「テスト：水曜2限」の3つ（前期の授業は出ない）。その下に、小さく「2026年度 後期の授業から選びます」。締切日は空欄、締切時刻は「23:59」。ボタンは「キャンセル」と「登録する」。課題名の欄にカーソルがある |
| A2 | 課題名を空白2つ（「  」）、対象授業を「テスト：月曜1限」、締切日を 2026-11-02 にして、「登録する」を押す | 課題名の欄が赤い枠になり、その下に「タイトルは必須です」（APIのメッセージのまま）。モーダルは開いたまま。ボタンは「登録する」に戻り、押せる |
| A3 | 課題名を「テスト：追加した課題」、対象授業を「テスト：水曜2限」、締切日を 2026-12-10 にし、詳細・メモに「メモ1行目」と改行して「2行目」を入れて、「登録する」を押す。コンソールで、`await (await fetch("/api/tasks/7")).json()` を実行する | モーダルが閉じる（メッセージは出ない）。未完了の表の一番下（⑤）に、「2026年12月10日（木） 23:59」「✅ テスト：追加した課題」（その下に「メモ1行目」「2行目」）「テスト：水曜2限」。応答は、`category: "assignment"`、`subject_id: 2`、`subject_name: "テスト：水曜2限"`、`title: "テスト：追加した課題"`、`due_datetime: "2026-12-10T23:59"`、`notes: "メモ1行目\n2行目"`、`is_completed: false` |
| A4 | 「課題を追加」を押す（入力欄が、A1の初期値に戻っていることを確かめる）。課題名を「テスト：今日0時の課題」、対象授業を「テスト：月曜1限」、締切日を**今日**、締切時刻を「00:00」にして、「登録する」を押す | 開いたとき、課題名・詳細・メモ・締切日が空、対象授業が「選択してください」、締切時刻が「23:59」、エラーの表示がない。登録すると、未完了の表の③に、今日の日付（例：「2026年10月16日（金） 00:00」）と赤い「期限切れ」（今日の0時は、今より前のため）、「✅ テスト：今日0時の課題」「テスト：月曜1限」 |
| A5 | コンソールで、下の「A5のスクリプト」を実行し、2秒待つ。そのあと、`document.querySelectorAll(".modal-backdrop").length` を実行する | モーダルが開き、閉じる（開き始めてすぐ、表示の途中で登録が成功しても、表示が終わってから閉じる。`hideModal`）。2つ目の結果が `0`（背景の暗い幕が残っていない）。未完了の表の一番下に、「2026年12月24日（木） 23:59」「✅ テスト：すぐ登録」「テスト：月曜1限」 |

A5のスクリプト（コンソールに、そのまま貼る）：

```
document.getElementById("task-add-button").click();
const select = document.getElementById("task-subject");
await new Promise((resolve) => {
  const timer = setInterval(() => {
    if (select.options.length > 1) {
      clearInterval(timer);
      resolve();
    }
  }, 5);
});
document.getElementById("task-title").value = "テスト：すぐ登録";
select.value = select.options[1].value;
document.getElementById("task-due-date").value = "2026-12-24";
document.getElementById("task-form").requestSubmit();
```

#### E. 編集

| No | 操作 | 期待する結果 |
|---|---|---|
| E1 | 「テスト：レポート」の行の「編集」を押す | モーダル「課題を編集」が開く。課題名「テスト：レポート」、対象授業「テスト：月曜1限」（選択肢は「選択してください」「テスト：月曜1限」「テスト：水曜2限」）、その下に「2026年度 後期の授業から選びます」、締切日 2026-11-30、締切時刻「23:59」、詳細・メモ「A4で2枚」「手書き不可」の2行。ボタンは「キャンセル」と「保存する」。課題名の欄にカーソルがある |
| E2 | 対象授業を「テスト：水曜2限」、締切時刻を「18:00」にして、「保存する」を押す。コンソールで、`await (await fetch("/api/tasks/1")).json()` を実行する | モーダルが閉じる。一覧の「テスト：レポート」の行が、「2026年11月30日（月） 18:00」「テスト：水曜2限」になる。応答は、`subject_id: 2`、`due_datetime: "2026-11-30T18:00"`、`notes: "A4で2枚\n手書き不可"`、`title: "テスト：レポート"`（変えていない項目は、そのまま） |
| E3 | 「テスト：前期の課題」の「編集」を押す。対象授業の選択肢を確かめる。課題名を「テスト：前期の課題（編集）」にして、「保存する」を押す。コンソールで、`await (await fetch("/api/tasks/5")).json()` を実行する | 対象授業は「テスト：前期の授業」を選んだ状態（空欄にならない）。選択肢は、「選択してください」「テスト：前期の授業」「テスト：月曜1限」「テスト：水曜2限」（今の学期にない、今の対象授業が、「選択してください」のすぐ下に足される）。保存するとモーダルが閉じ、応答は、`title: "テスト：前期の課題（編集）"`、`subject_id: 3`（変わらない） |
| E4 | 「テスト：その他の締切」の「編集」を押す。締切日を 2026-12-02 にし、詳細・メモに空白2つ（「  」）を入れて、「保存する」を押す。コンソールで、`await (await fetch("/api/tasks/3")).json()` を実行する | モーダルの見出しは「その他（締切のみ）を編集」。項目は、上から「タイトル」「締切日」と「締切時刻」「詳細・メモ（任意）」（対象授業の欄はない）。保存するとモーダルが閉じ、一覧の行が「2026年12月2日（水） 17:00」になる。応答は、`category: "other"`、`due_datetime: "2026-12-02T17:00"`、`notes: null`、`subject_id: null` |
| E5 | 「テスト：期限切れの課題」の「編集」を押す。課題名を空白2つにして、「保存する」を押す。そのあと「キャンセル」を押す | 課題名の欄の下に「タイトルは必須です」。モーダルは開いたまま。ボタンは「保存する」に戻る。「キャンセル」で閉じ、一覧の課題名は「テスト：期限切れの課題」のまま |

#### D. 削除

| No | 操作 | 期待する結果 |
|---|---|---|
| D1 | 完了の表の「テスト：完了した課題」の「削除」を押す。コンソールで、`document.activeElement.id` と、`["task-delete-modal", "task-delete-submit-button"].map((id) => document.getElementById(id).getAttribute("aria-describedby"))` を実行する | モーダル「課題・タスクを削除」が開く。上から、「「テスト：完了した課題」（締切 2026年10月5日（月） 23:59）を削除します。」、赤い字で「削除は取り消せません。」。ボタンは「キャンセル」と「削除する」（赤。押せる）。1つ目：`"task-delete-cancel-button"`（最初のフォーカスは「キャンセル」）。2つ目：`["task-delete-target task-delete-warning", "task-delete-target task-delete-warning"]` |
| D2 | 「キャンセル」を押す | モーダルが閉じる。一覧は変わらない |
| D3 | もう一度「テスト：完了した課題」の「削除」を押し、「削除する」を押す。コンソールで、`(await fetch("/api/tasks/4")).status` を実行する | ボタンが「削除中…」になり、モーダルが閉じる。完了の表が、「テスト：完了した課題2」の1行になる。結果は `404` |
| D4 | コンソールで、`(await fetch("/api/tasks/6", { method: "DELETE" })).status` を実行する（ほかの場所で削除された場合の再現。確認用のデータに限る）。そのあと、完了の表に残っている「テスト：完了した課題2」の「削除」を押し、「削除する」を押す | 1つ目：`204`。モーダルの中に、赤い枠で「課題・タスクが見つかりません」。ボタンは「削除する」に戻り、押せる。モーダルは開いたまま。「キャンセル」で閉じる（一覧は、取得し直さないため、行は残る） |

#### S. 授業モード（変わらないことと、015-L1）

| No | 操作 | 期待する結果 |
|---|---|---|
| S1 | 画面下の「授業」を押す | 学期「2026年度 後期」が選ばれている（`current_semester.js` に移した初期選択）。期間「2026年9月21日 〜 2027年1月29日」。授業は「テスト：月曜1限」「テスト：水曜2限」の2行 |
| S2 | コンソールで、`["subject-delete-modal", "subject-delete-submit-button", "subject-edit-submit-button"].map((id) => document.getElementById(id).getAttribute("aria-describedby"))` と、`document.getElementById("subject-delete-warning").textContent` を実行する | 1つ目：`["subject-delete-target subject-delete-counts subject-delete-warning", "subject-delete-target subject-delete-counts subject-delete-warning", "subject-edit-notice"]`。2つ目：`"削除は取り消せません。"`（015-L1） |
| S3 | 「テスト：水曜2限」の「削除」を押し、件数が出たら「削除する」を押す。そのあと、画面下の「課題・タスク」を押す | 件数は「この授業の予定19件（今日より前の分を含む）と、課題2件も、まとめて削除されます。」（E2で移した「テスト：レポート」と、A3の「テスト：追加した課題」）。削除のあと、課題・タスクモードを開くと、取得し直され、未完了の表は、①「テスト：前期の課題（編集）」②「テスト：期限切れの課題」③「テスト：今日0時の課題」④「テスト：その他の締切」（2026年12月2日）⑤「テスト：すぐ登録」の5行。完了の表は、「完了した課題・タスクはありません」（D4の「テスト：完了した課題2」の行も、消えている） |

#### A6. 今の学期に授業がない場合（確認の最後に行う。学期は削除できないため）

| No | 操作 | 期待する結果 |
|---|---|---|
| A6 | コンソールで、`(await fetch("/api/semesters", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: "2027年度 前期", start_date: "2026-10-01", end_date: "2026-12-31" }) })).status` を実行する（確認用の学期。名前と期間は合っていないが、今日を含み、開始日が「2026年度 後期」より新しいため、今の学期になる）。「課題を追加」を押し、対象授業の欄を確かめて、「キャンセル」を押す。「テスト：期限切れの課題」の「編集」を押し、対象授業の欄を確かめて、「キャンセル」を押す | 1つ目：`201`。追加のモーダルの対象授業は、「選択してください」だけで、その下に「2027年度 前期には、授業が登録されていません。授業モードで、授業を登録してください」。編集のモーダルの対象授業は、「テスト：月曜1限」を選んだ状態で、選択肢は「選択してください」「テスト：月曜1限」の2つ（今の学期にない、今の対象授業）。説明は、追加と同じ文言 |

#### X. 確認の全体を通して

| No | 確認 | 期待する結果 |
|---|---|---|
| X1 | コンソール | JavaScriptの例外（`Uncaught …`）が出ていない。想定した400・404の応答（A2・E5の400、D3・D4の404）の「Failed to load resource」と、サーバーを止めている間（T3）の接続の失敗の記録（`net::ERR_CONNECTION_REFUSED`）は、除く（010-N1） |

#### 後片付け
1. 確認用のサーバーを止める（Ctrl＋C）
2. 確認用のDBのフォルダを消す
   ```
   rm -r /tmp/schedule-app-check-017
   ```
3. 開発用DBのハッシュが、準備の1と同じことを確かめる
   ```
   shasum -a 256 instance/app.db
   ```

ハッシュが変わっていた場合は、開発用DBを操作せずに、Claudeに伝える。

### 4. 開発用DBでの、読み取りだけの確認
3が期待どおりなら、開発用DBで起動して、画面が開くことだけを確かめる（登録・編集・削除・完了の切り替えはしない）。

```
shasum -a 256 instance/app.db          # 控える
python run.py                          # 開発用DBで起動
# ブラウザでの確認のあと、サーバーを Ctrl+C で止めてから
shasum -a 256 instance/app.db          # 起動の前と同じ
```

| 確認 | 期待 |
|---|---|
| ブラウザで開き、強制再読み込みして、画面下の「課題・タスク」を押す | 課題・タスクが0件のため、「未完了の課題・タスクはありません」「完了した課題・タスクはありません」と、「課題を追加」ボタン（**押さない**）。コンソールに、JavaScriptの例外がない |
| 最後のハッシュ | 起動の前と同じ |

### 5. マージ
1〜4が期待どおりで、レビューで承認されたら、マージする。このタスクは、DBの構造を変えないため、開発用DBへのmigrationの適用はない。開発用DBのデータも変えないため、バックアップは要らない。

マージのあとは、開発用DBのサーバー（`python run.py`）の課題・タスクモードで、課題の登録・編集・削除・完了の切り替えができる。削除は取り消せない（確認のモーダルで、対象を確かめてから削除する）。

## Git操作
**Git commit / push / ブランチ操作 / マージは行わない**（`git branch --show-current`、`git status`、`git diff` のような読み取りだけのコマンドは除く）。

## 注意
- **停止して報告する条件**（ファイルを変更せず、実装を止め、チャットで「問題点・発生理由・変更した場合の影響・推奨案（必要なら）」を報告する）
  - ブランチの不一致、作業ツリーの想定外の変更
  - 設計資料が更新されていない（実装手順の1）、または、設計資料とこのTask MDの間に、矛盾・不足がある
  - 設計資料にない判断が必要になった（特に、`docs/architecture.md` の「未決定事項」や、`docs/ui_ux.md` の「未決定」に触れる場合）
  - 「全文からファイルを作るスクリプト」の出力が、期待と違う（全文の数・行数・エラー）
  - 「変更しない」と定めたもの（Pythonのファイル、テスト、ほかのJavaScriptのファイル、`base.html` など）を変更しないと実装できない。または、8ファイルの全文を変える必要があると判断した
  - ライブラリのインストール・ダウンロードが必要だと判断した
  - 開発用DB（`instance/app.db`）がない
  - 作業の前の `python -m pytest` が、787件すべて合格しない
  - **既存のテスト**（787件）**が、想定外に失敗した**。テストの期待値や、ほかの仕様を直さずに、原因を調べて報告する
  - APIの変更や、DBの構造の変更（migration）が必要だと判断した
  - 実施の前後で、`instance/app.db` が変わった
- **止まるときは、報告を書いて、その応答を終える。質問の機能は使わない。** 再開するのは、Komaの新しいメッセージが、判断や再開を明確に示したときだけ（無回答や「続けて」だけの返事は、再開の指示ではない）。`.github/copilot-instructions.md` の「止まる場面の応答」
- **開発用DBを `sqlite3` で開くときは、必ず `-readonly` を付ける**（SELECTだけでも、付けずに開かない。011-L1）。`flask db` のコマンドを、一切実行しない。ライブラリを追加しない。サーバーを起動しない（`python run.py` も、「Komaの確認」の確認用のサーバーも）。「確認用のデータの登録」のスクリプトも、実行しない（Komaが行う）。ブラウザでの確認もしない
- 期待する結果と異なる結果が出た場合は、確認を飛ばさず、原因を直してから、すべての確認をやり直す（ただし、既存のテストの想定外の失敗は、上の停止の条件に従う。全文との「不一致」は、手で直さず、スクリプトで全文に戻す）
- 設計資料に書かれていない仕様は、自分で決めない
- **最後の報告には、次を含め、コマンドの出力は、要約せずに、そのまま貼る**（014-L1）：変更・新規のファイル、「全文からファイルを作るスクリプト」の出力（段階1・2）、作業の前と各段階の `pytest` の件数と警告（最後の行）、1行の長さの確認の出力、全文との比較の出力（段階1：5ファイル、段階2：8ファイルの「一致」。スクリプトで全文に戻した場合は、そのこと）、画面のHTMLの確認の出力、検索と差分の出力（各コマンドと、その出力）、開発用DBの前後のハッシュ・件数、`git status`・`git diff --stat` の出力、コマンドを書き換えた場合は、その箇所と理由（016-N1）、サーバーの起動とブラウザでの確認をしていないこと、気になった点

## 付録：全文
「全文からファイルを作るスクリプト」と「全文との比較」が使う。各ファイルの全文は、「`<!-- 全文: パス -->`」の印の行の直後のコードブロック。**この付録を、手で書き写さない。** 本文の要点・差分と食い違う場合は、作業をせずに停止して報告する。

### 付録A. `app/static/js/current_semester.js`

<!-- 全文: app/static/js/current_semester.js -->
```javascript
// 今の学期を選ぶ規則。複数のモードで使うため、このファイルにまとめる
// （授業モードの学期の初期選択と、課題の対象授業の選択肢）。
// DOMとAPIは扱わない。

// semesters は、学期のAPIの一覧の並び（開始日の新しい順。タブの並び）の
// 配列。today は「YYYY-MM-DD」。学期が0件なら null を返す。
// 1. 今日を含む学期（複数あれば、並びで先の学期）
// 2. なければ、今日より後に始まる学期のうち、最も早く始まるもの
// 3. なければ、最も最近終わった学期（終了日が最も新しいもの）
export function chooseCurrentSemester(semesters, today) {
  // YYYY-MM-DDは桁が固定されているため、文字列の大小が日付の前後と一致する。
  const current = semesters.find(
    (semester) => semester.start_date <= today && today <= semester.end_date,
  );
  if (current !== undefined) {
    return current;
  }

  let next = null;
  for (const semester of semesters) {
    if (
      semester.start_date > today &&
      (next === null || semester.start_date < next.start_date)
    ) {
      next = semester;
    }
  }
  if (next !== null) {
    return next;
  }

  let mostRecent = null;
  for (const semester of semesters) {
    if (
      mostRecent === null ||
      semester.end_date > mostRecent.end_date
    ) {
      mostRecent = semester;
    }
  }
  return mostRecent;
}
```

### 付録B. `app/static/js/semesters.js`

<!-- 全文: app/static/js/semesters.js -->
```javascript
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

  const selected = semesters.find((semester) => semester.id === selectedId);
  if (selected !== undefined) {
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
  const selected = semesters.find((semester) => semester.id === selectedId);
  if (selected === undefined) {
    return;
  }

  getElement("semester-detail-name").textContent = selected.name;
  getElement("semester-detail-period").textContent =
    `${formatJapaneseDate(selected.start_date)} 〜 ` +
    `${formatJapaneseDate(selected.end_date)}`;
}

function selectSemester(id) {
  const previousId = selectedId;
  selectedId = id;

  updateTabSelection();
  renderDetail();

  if (previousId !== id) {
    const selected = semesters.find((semester) => semester.id === id);
    const semester =
      selected === undefined
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

async function loadSemesters(preferredId = null) {
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
    selectSemester(initial.id);
  } catch (error) {
    showLoadError(error);
  }
}

async function submitSemester(event) {
  event.preventDefault();
  clearSemesterFormErrors();

  const submitButton = getElement("semester-submit-button");
  setSubmitting(submitButton, true, SEMESTER_SUBMIT_LABELS);

  const name =
    `${getElement("semester-year").value}年度 ` +
    getElement("semester-term").value;
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
  await loadSemesters(created.id);
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
  loadSemesters();
}
```

### 付録C. `app/static/js/dates.js`

<!-- 全文: app/static/js/dates.js -->
```javascript
// 日付の補助処理。複数のモードで使うため、このファイルにまとめる。
// 日付は、APIと同じ「YYYY-MM-DD」の文字列で受け渡す。

// Date.getDay()の並び（0=日曜〜6=土曜）の曜日の表示。授業の曜日
// （0=月曜〜6=日曜。DB・APIと同じ）とは並びが違うため、混ぜて使わない。
const WEEKDAY_LABELS = ["日", "月", "火", "水", "木", "金", "土"];

export function localDateString(date = new Date()) {
  // toISOString()はUTC日付に変換するため、ローカル日付が前日になることがある。
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function formatJapaneseDate(dateString) {
  const [year, month, day] = dateString.split("-").map(Number);
  return `${year}年${month}月${day}日`;
}

export function formatJapaneseDateWithWeekday(dateString) {
  const [year, month, day] = dateString.split("-").map(Number);
  // new Date("YYYY-MM-DD")はUTCの0時として読まれ、タイムゾーンによっては
  // 前の日の曜日になる。年・月・日を分けて渡し、ローカルの日付として作る
  // （月は0始まり）。
  const weekday = new Date(year, month - 1, day).getDay();
  return `${formatJapaneseDate(dateString)}（${WEEKDAY_LABELS[weekday]}）`;
}

// 今の日時の文字列（「YYYY-MM-DDTHH:MM」。課題・タスクのAPIの締切日時と
// 同じ形）。秒は持たない。ブラウザのローカルの日時から作る。
export function localDateTimeString(date = new Date()) {
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${localDateString(date)}T${hours}:${minutes}`;
}

// 日時の表示（例：「2026年10月20日（火） 23:59」）。dateTimeString は
// 「YYYY-MM-DDTHH:MM」。
export function formatJapaneseDateTime(dateTimeString) {
  const [dateString, timeString] = dateTimeString.split("T");
  return `${formatJapaneseDateWithWeekday(dateString)} ${timeString}`;
}
```

### 付録D. `app/static/js/categories.js`

<!-- 全文: app/static/js/categories.js -->
```javascript
// カテゴリの対応表。DBの保存値（APIの category）から、画面に出す
// 表示名・アイコン・色のclassを引く。複数のモードで使うため、
// このファイルにまとめる（モードのファイル同士は、互いを import しない）。
// 色の値は、style.css の、className と同じ名前のclassに書く
// （JavaScriptでは、色の値を持たない）。

// 予定（Event）のカテゴリ。並びは、カレンダーの絞り込みの選択肢の並び。
export const EVENT_CATEGORIES = {
  class: {
    label: "授業",
    icon: "📖",
    className: "category-class",
  },
  part_time: {
    label: "アルバイト",
    icon: "💼",
    className: "category-part-time",
  },
  other: {
    label: "その他",
    icon: "⭐",
    className: "category-other",
  },
};

// 課題・タスク（Task）のカテゴリ。その他（締切のみ）は、予定のその他と
// 同じ色・アイコンを使う。
export const TASK_CATEGORIES = {
  assignment: {
    label: "課題",
    icon: "✅",
    className: "category-assignment",
  },
  other: {
    label: "その他",
    icon: "⭐",
    className: "category-other",
  },
};

// 対応表（categories）から、保存値（category）に対応する項目を返す。
// 対応表にない値は、DBに入らない想定だが、画面が止まらないように、
// 保存値をそのまま表示名にし、アイコンと色のclassを付けない。
function categoryOf(categories, category) {
  if (Object.prototype.hasOwnProperty.call(categories, category)) {
    return categories[category];
  }
  return { label: category, icon: "", className: "" };
}

// 予定のカテゴリの保存値に対応する項目を返す。
export function eventCategoryOf(category) {
  return categoryOf(EVENT_CATEGORIES, category);
}

// 課題・タスクのカテゴリの保存値に対応する項目を返す。
export function taskCategoryOf(category) {
  return categoryOf(TASK_CATEGORIES, category);
}
```

### 付録E. `app/static/css/style.css`

<!-- 全文: app/static/css/style.css -->
```css
/* 独自のスタイル。Bootstrapにない指定だけを、ここに書く。 */

/*
  カテゴリの色（docs/ui_ux.md の「色・アイコン」）。FullCalendarは、
  予定の色をCSSの変数で受け取るため、カテゴリのclass（categories.js の
  className）に、変数を設定する。色の見本（.category-swatch）も、
  同じ変数を使う。
*/
.category-class {
  --fc-event-bg-color: #0a58ca;
  --fc-event-border-color: #0a58ca;
  --fc-event-text-color: #ffffff;
}

.category-assignment {
  --fc-event-bg-color: #fd7e14;
  --fc-event-border-color: #fd7e14;
  --fc-event-text-color: #000000;
}

.category-part-time {
  --fc-event-bg-color: #146c43;
  --fc-event-border-color: #146c43;
  --fc-event-text-color: #ffffff;
}

.category-other {
  --fc-event-bg-color: #6c757d;
  --fc-event-border-color: #6c757d;
  --fc-event-text-color: #ffffff;
}

/*
  Bootstrapは、<a> の文字を、青い下線つきにする。FullCalendarは、日付の
  見出しや「＋N件」に <a> を使うため、FullCalendarの本来の見た目
  （通常の文字。クリックできる日付は、マウスを重ねると下線）に戻す。
*/
.fc a {
  color: inherit;
  text-decoration: none;
}

/* カレンダーの絞り込みの選択肢に添える、カテゴリの色の見本 */
.category-swatch {
  display: inline-block;
  width: 0.75em;
  height: 0.75em;
  border-radius: 0.2em;
  background-color: var(--fc-event-bg-color);
}

/* 改行を、そのまま改行して表示する（予定の詳細パネルのメモ） */
.text-pre-wrap {
  white-space: pre-wrap;
}

/*
  課題・タスクの一覧（未完了・完了の2つの表）。列の幅を決めて、2つの表の
  列をそろえる（幅を中身に合わせると、表ごとにずれるため）。完了と操作の
  列は、中身が入る幅、締切と対象授業の列は、表の幅に対する割合。課題名の
  列は、残りの幅を使う。
*/
.task-table {
  table-layout: fixed;
}

.task-col-completed {
  width: 3rem;
}

.task-col-due {
  width: 26%;
}

.task-col-subject {
  width: 17%;
}

.task-col-actions {
  width: 8rem;
}
```

### 付録F. `app/templates/index.html`

<!-- 全文: app/templates/index.html -->
```html
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
        <div id="calendar-view"></div>
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
          <h2 id="semester-detail-name" class="h5"></h2>
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
        <h2 class="modal-title h5" id="event-modal-title"></h2>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="閉じる"></button>
      </div>
      <div class="modal-body">
        <dl class="mb-0">
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
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">閉じる</button>
      </div>
    </div>
  </div>
</div>
{% endblock %}

{% block scripts %}
<script type="module" src="{{ url_for('static', filename='js/main.js') }}"></script>
{% endblock %}
```

### 付録G. `app/static/js/tasks.js`

<!-- 全文: app/static/js/tasks.js -->
```javascript
import { apiRequest } from "./api.js";
import { taskCategoryOf } from "./categories.js";
import { chooseCurrentSemester } from "./current_semester.js";
import {
  formatJapaneseDateTime,
  localDateString,
  localDateTimeString,
} from "./dates.js";
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

// 課題のカテゴリの保存値（categories.js の TASK_CATEGORIES のキー）。
// このモードで追加できるのは、課題だけ。
const ASSIGNMENT = "assignment";
// 締切時刻の初期値（課題は、23:59の締切が多いため）。
const DEFAULT_DUE_TIME = "23:59";
const SUBJECT_PLACEHOLDER = "選択してください";
const SUBJECT_LOADING_NOTE = "授業を読み込み中…";

const TASK_FIELDS = {
  title: {
    inputIds: ["task-title"],
    messageId: "task-title-error",
  },
  subject_id: {
    inputIds: ["task-subject"],
    messageId: "task-subject-error",
  },
  due_datetime: {
    inputIds: ["task-due-date", "task-due-time"],
    messageId: "task-due-error",
  },
  notes: {
    inputIds: ["task-notes"],
    messageId: "task-notes-error",
  },
};
const TASK_FORM_ERROR_ID = "task-form-error";
const TASK_SUBMIT_LABELS = {
  idle: "登録する",
  busy: "登録中…",
};
const TASK_EDIT_FIELDS = {
  title: {
    inputIds: ["task-edit-title"],
    messageId: "task-edit-title-error",
  },
  subject_id: {
    inputIds: ["task-edit-subject"],
    messageId: "task-edit-subject-error",
  },
  due_datetime: {
    inputIds: ["task-edit-due-date", "task-edit-due-time"],
    messageId: "task-edit-due-error",
  },
  notes: {
    inputIds: ["task-edit-notes"],
    messageId: "task-edit-notes-error",
  },
};
const TASK_EDIT_FORM_ERROR_ID = "task-edit-form-error";
const TASK_EDIT_SUBMIT_LABELS = {
  idle: "保存する",
  busy: "保存中…",
};
const TASK_DELETE_SUBMIT_LABELS = {
  idle: "削除する",
  busy: "削除中…",
};

// 一覧の取得の通し番号（古い応答で、今の一覧を上書きしないため）。
let requestSerial = 0;
// 編集・削除の対象の課題・タスク（一覧の行の値のコピー）。
let editingTask = null;
let deletingTask = null;
// 追加・編集・削除のモーダルを開くたびに増やす通し番号。閉じて開き直した
// あとに届いた古い応答で、今のモーダルの表示を変えないために使う。
let addSerial = 0;
let editSerial = 0;
let deleteSerial = 0;

// 課題・タスクを表す文字列（例：「レポート第1回」（締切 2026年10月20日（火）
// 23:59））。同じタイトルの課題・タスクを、締切で区別できるようにする。
function taskLabel(task) {
  return (
    `「${task.title}」` +
    `（締切 ${formatJapaneseDateTime(task.due_datetime)}）`
  );
}

// 締切日と締切時刻の入力欄の値を、APIの日時（YYYY-MM-DDTHH:MM）にする。
function dueDateTimeOf(dateInputId, timeInputId) {
  const date = getElement(dateInputId).value;
  const time = getElement(timeInputId).value;
  return `${date}T${time}`;
}

function showTaskLoading() {
  setVisible(getElement("task-loading"), true);
  setVisible(getElement("task-load-error"), false);
  setVisible(getElement("task-content"), false);
}

function showTaskLoadError(error) {
  getElement("task-load-error-message").textContent = errorMessageOf(error);
  setVisible(getElement("task-loading"), false);
  setVisible(getElement("task-load-error"), true);
  setVisible(getElement("task-content"), false);
}

function showActionError(error) {
  const actionError = getElement("task-action-error");
  actionError.textContent = errorMessageOf(error);
  setVisible(actionError, true);
}

function hideActionError() {
  const actionError = getElement("task-action-error");
  actionError.replaceChildren();
  setVisible(actionError, false);
}

// 一覧の1行を作る。overdueBefore は、期限切れの判定に使う今の日時
// （YYYY-MM-DDTHH:MM）。完了の表では null（期限切れを出さない）。
function createTaskRow(task, overdueBefore) {
  const category = taskCategoryOf(task.category);
  const label = taskLabel(task);
  const row = document.createElement("tr");

  const completedCell = document.createElement("td");
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.id = `task-complete-${task.id}`;
  checkbox.className = "form-check-input";
  checkbox.checked = task.is_completed;
  checkbox.setAttribute("aria-label", `${label}の完了`);
  checkbox.addEventListener("change", () => {
    toggleTaskCompleted(task, checkbox);
  });
  completedCell.append(checkbox);
  row.append(completedCell);

  const dueCell = document.createElement("td");
  dueCell.textContent = formatJapaneseDateTime(task.due_datetime);
  // 締切日時が今より前なら、期限切れ（YYYY-MM-DDTHH:MMは桁が固定されて
  // いるため、文字列の大小で前後を比べられる）。
  if (overdueBefore !== null && task.due_datetime < overdueBefore) {
    const badge = document.createElement("span");
    badge.className = "badge text-bg-danger ms-1";
    badge.textContent = "期限切れ";
    dueCell.append(badge);
  }
  row.append(dueCell);

  const titleCell = document.createElement("td");
  const titleLine = document.createElement("div");
  const icon = document.createElement("span");
  icon.className = "me-1";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = category.icon;
  // アイコンは読み上げないため、カテゴリの表示名を、見えない文字で添える。
  const categoryName = document.createElement("span");
  categoryName.className = "visually-hidden";
  categoryName.textContent = `${category.label}：`;
  titleLine.append(icon, categoryName, task.title);
  titleCell.append(titleLine);
  if (task.notes !== null) {
    const notes = document.createElement("div");
    notes.className = "text-muted small text-pre-wrap";
    notes.textContent = task.notes;
    titleCell.append(notes);
  }
  row.append(titleCell);

  const subjectCell = document.createElement("td");
  subjectCell.textContent = task.subject_name ?? "—";
  row.append(subjectCell);

  const actions = document.createElement("td");
  actions.className = "text-end text-nowrap";

  const editButton = document.createElement("button");
  editButton.type = "button";
  editButton.id = `task-edit-${task.id}`;
  editButton.className = "btn btn-outline-secondary btn-sm";
  editButton.textContent = "編集";
  editButton.setAttribute("aria-label", `${label}を編集`);
  editButton.addEventListener("click", () => {
    openEditModal(task);
  });
  actions.append(editButton);

  const deleteButton = document.createElement("button");
  deleteButton.type = "button";
  deleteButton.id = `task-delete-${task.id}`;
  deleteButton.className = "btn btn-outline-danger btn-sm ms-1";
  deleteButton.textContent = "削除";
  deleteButton.setAttribute("aria-label", `${label}を削除`);
  deleteButton.addEventListener("click", () => {
    openDeleteModal(task);
  });
  actions.append(deleteButton);

  row.append(actions);
  return row;
}

// 1つの表（未完了か完了）の行を作り直す。0件なら、表を隠して、
// 0件の文言を出す。
function renderTaskTable(tasks, { bodyId, listId, emptyId, overdueBefore }) {
  const fragment = document.createDocumentFragment();
  for (const task of tasks) {
    fragment.append(createTaskRow(task, overdueBefore));
  }
  getElement(bodyId).replaceChildren(fragment);
  setVisible(getElement(emptyId), tasks.length === 0);
  setVisible(getElement(listId), tasks.length > 0);
}

// 一覧を、未完了と完了の2つの表に分けて表示する。APIの並びは、締切日時の
// 早い順。未完了は、そのまま（期限切れが上に来る）。完了は、逆にして、
// 締切日時の新しい順にする。期限切れは、表示するときの日時で判定する。
function renderTasks(tasks) {
  const incomplete = tasks.filter((task) => !task.is_completed);
  const completed = tasks.filter((task) => task.is_completed).reverse();

  renderTaskTable(incomplete, {
    bodyId: "task-incomplete-body",
    listId: "task-incomplete-list",
    emptyId: "task-incomplete-empty",
    overdueBefore: localDateTimeString(),
  });
  renderTaskTable(completed, {
    bodyId: "task-completed-body",
    listId: "task-completed-list",
    emptyId: "task-completed-empty",
    overdueBefore: null,
  });
  setVisible(getElement("task-loading"), false);
  setVisible(getElement("task-load-error"), false);
  setVisible(getElement("task-content"), true);
}

async function loadTasks({ showLoading = true } = {}) {
  const currentRequest = ++requestSerial;
  if (showLoading) {
    showTaskLoading();
  }

  let tasks;
  try {
    tasks = await apiRequest("GET", "/api/tasks");
  } catch (error) {
    // 新しい取得を始めていたら、古い取得の結果で、画面を変えない。
    if (currentRequest !== requestSerial) {
      return;
    }
    showTaskLoadError(error);
    return;
  }

  if (currentRequest !== requestSerial) {
    return;
  }
  renderTasks(tasks);
}

// 完了の切り替え（チェックボックス）。確認は出さない。成功したら、一覧を
// 取得し直す（行が、もう一方の表へ移る）。失敗したら、チェックを元に戻し、
// エラーを一覧の上部に出す。
async function toggleTaskCompleted(task, checkbox) {
  hideActionError();
  checkbox.disabled = true;

  // try で囲むのは、切り替えの要求だけにする（成功後の処理の例外を、
  // 「切り替えの失敗」として表示しないため）。
  try {
    await apiRequest("PATCH", `/api/tasks/${task.id}`, {
      is_completed: checkbox.checked,
    });
  } catch (error) {
    checkbox.checked = !checkbox.checked;
    checkbox.disabled = false;
    showActionError(error);
    return;
  }

  await loadTasks({ showLoading: false });
}

// 対象授業のプルダウンの選択肢を作る。先頭は「選択してください」（値は空）。
// extraSubject は、今の学期の授業の一覧にない、課題の今の対象授業（編集の
// とき。{ id, subject_name }）。ないときは null。
function renderSubjectOptions(select, subjects, extraSubject) {
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = SUBJECT_PLACEHOLDER;
  const options = [placeholder];
  const items =
    extraSubject === null ? subjects : [extraSubject, ...subjects];
  for (const subject of items) {
    const option = document.createElement("option");
    option.value = String(subject.id);
    option.textContent = subject.subject_name;
    options.push(option);
  }
  select.replaceChildren(...options);
}

// 今の学期（授業モードで最初に選ばれる学期と同じ規則。current_semester.js）
// と、その学期の授業の一覧を取得する。学期が0件なら、semester は null。
async function fetchCurrentSubjects() {
  const semesters = await apiRequest("GET", "/api/semesters");
  const semester = chooseCurrentSemester(semesters, localDateString());
  if (semester === null) {
    return { semester: null, subjects: [] };
  }
  const subjects = await apiRequest(
    "GET",
    `/api/subjects?semester_id=${semester.id}`,
  );
  return { semester, subjects };
}

// 対象授業の欄の下に出す説明。
function subjectNoteOf(semester, subjects) {
  if (semester === null) {
    return (
      "学期が登録されていません。" +
      "授業モードで、学期と授業を登録してください"
    );
  }
  if (subjects.length === 0) {
    return (
      `${semester.name}には、授業が登録されていません。` +
      "授業モードで、授業を登録してください"
    );
  }
  return `${semester.name}の授業から選びます`;
}

// 追加のモーダルを開くたびに、入力欄を初期値に戻し、今の学期の授業を
// 取得して、対象授業の選択肢を作る。
async function prepareAddModal() {
  const currentSerial = ++addSerial;
  const select = getElement("task-subject");
  const note = getElement("task-subject-note");

  getElement("task-form").reset();
  getElement("task-title").value = "";
  getElement("task-due-date").value = "";
  getElement("task-due-time").value = DEFAULT_DUE_TIME;
  getElement("task-notes").value = "";
  clearFormErrors(TASK_FIELDS, TASK_FORM_ERROR_ID);
  setSubmitting(
    getElement("task-submit-button"),
    false,
    TASK_SUBMIT_LABELS,
  );
  // 授業を取得するまでは、「選択してください」だけ（必須のため、
  // ブラウザの入力チェックで、登録は止まる）。
  renderSubjectOptions(select, [], null);
  note.textContent = SUBJECT_LOADING_NOTE;

  let result;
  try {
    result = await fetchCurrentSubjects();
  } catch (error) {
    // モーダルを開き直していたら、今のモーダルの表示を変えない。
    if (currentSerial !== addSerial) {
      return;
    }
    note.replaceChildren();
    showApiError(error, TASK_FIELDS, TASK_FORM_ERROR_ID);
    return;
  }

  if (currentSerial !== addSerial) {
    return;
  }
  renderSubjectOptions(select, result.subjects, null);
  note.textContent = subjectNoteOf(result.semester, result.subjects);
}

async function submitTask(event) {
  event.preventDefault();
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = addSerial;
  clearFormErrors(TASK_FIELDS, TASK_FORM_ERROR_ID);

  const submitButton = getElement("task-submit-button");
  setSubmitting(submitButton, true, TASK_SUBMIT_LABELS);

  // try で囲むのは、登録の要求だけにする（成功後の処理の例外を、
  // 「登録の失敗」として表示しないため）。
  try {
    await apiRequest("POST", "/api/tasks", {
      category: ASSIGNMENT,
      subject_id: Number(getElement("task-subject").value),
      title: getElement("task-title").value,
      due_datetime: dueDateTimeOf("task-due-date", "task-due-time"),
      notes: getElement("task-notes").value,
    });
  } catch (error) {
    if (startedSerial !== addSerial) {
      return;
    }
    showApiError(error, TASK_FIELDS, TASK_FORM_ERROR_ID);
    setSubmitting(submitButton, false, TASK_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === addSerial) {
    hideModal(getElement("task-modal"));
  }
  await loadTasks({ showLoading: false });
}

// 一覧の「編集」ボタン。対象を控えて、編集のモーダルを開く（入力欄は、
// モーダルを開くとき（show.bs.modal）に入れる）。
function openEditModal(task) {
  editingTask = { ...task };
  window.bootstrap.Modal.getOrCreateInstance(
    getElement("task-edit-modal"),
  ).show();
}

// 編集のモーダルを開くたびに、対象の今の値を入力欄に入れ、エラーの表示を
// 消す。課題は、今の学期の授業を取得して、対象授業の選択肢を作る。
// その他（締切のみ）は、対象授業の欄を出さない。
async function prepareEditModal() {
  const currentSerial = ++editSerial;
  const task = editingTask;
  const isAssignment = task.category === ASSIGNMENT;
  const select = getElement("task-edit-subject");
  const note = getElement("task-edit-subject-note");

  getElement("task-edit-form").reset();
  getElement("task-edit-modal-title").textContent = isAssignment
    ? "課題を編集"
    : "その他（締切のみ）を編集";
  getElement("task-edit-title-label").textContent = isAssignment
    ? "課題名"
    : "タイトル";
  const [dueDate, dueTime] = task.due_datetime.split("T");
  getElement("task-edit-title").value = task.title;
  getElement("task-edit-due-date").value = dueDate;
  getElement("task-edit-due-time").value = dueTime;
  getElement("task-edit-notes").value = task.notes ?? "";
  clearFormErrors(TASK_EDIT_FIELDS, TASK_EDIT_FORM_ERROR_ID);
  setSubmitting(
    getElement("task-edit-submit-button"),
    false,
    TASK_EDIT_SUBMIT_LABELS,
  );

  setVisible(getElement("task-edit-subject-row"), isAssignment);
  // 隠した欄の入力チェック（必須）で、保存が止まらないように、
  // その他では、プルダウンを無効にする。
  select.disabled = !isAssignment;
  if (!isAssignment) {
    renderSubjectOptions(select, [], null);
    note.replaceChildren();
    return;
  }

  // 授業を取得するまでは、今の対象授業だけを選んだ状態にする（取得に
  // 失敗しても、ほかの項目は保存できる）。
  const currentSubject = {
    id: task.subject_id,
    subject_name: task.subject_name,
  };
  renderSubjectOptions(select, [], currentSubject);
  select.value = String(task.subject_id);
  note.textContent = SUBJECT_LOADING_NOTE;

  let result;
  try {
    result = await fetchCurrentSubjects();
  } catch (error) {
    if (currentSerial !== editSerial) {
      return;
    }
    note.replaceChildren();
    showApiError(error, TASK_EDIT_FIELDS, TASK_EDIT_FORM_ERROR_ID);
    return;
  }

  if (currentSerial !== editSerial) {
    return;
  }
  // 今の対象授業が、今の学期の授業にない場合（ほかの学期の授業の課題）は、
  // 選択肢に足す（足さないと、空欄になり、保存すると必須のエラーになる）。
  const inCurrentSemester = result.subjects.some(
    (subject) => subject.id === task.subject_id,
  );
  renderSubjectOptions(
    select,
    result.subjects,
    inCurrentSemester ? null : currentSubject,
  );
  select.value = String(task.subject_id);
  note.textContent = subjectNoteOf(result.semester, result.subjects);
}

async function submitTaskEdit(event) {
  event.preventDefault();
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = editSerial;
  const task = editingTask;
  clearFormErrors(TASK_EDIT_FIELDS, TASK_EDIT_FORM_ERROR_ID);

  const submitButton = getElement("task-edit-submit-button");
  setSubmitting(submitButton, true, TASK_EDIT_SUBMIT_LABELS);

  // すべての項目を送る（変えていない項目も、今の値のまま送る）。
  // 対象授業は、課題だけ（その他は、授業を指定できない）。
  const body = {
    title: getElement("task-edit-title").value,
    due_datetime: dueDateTimeOf("task-edit-due-date", "task-edit-due-time"),
    notes: getElement("task-edit-notes").value,
  };
  if (task.category === ASSIGNMENT) {
    body.subject_id = Number(getElement("task-edit-subject").value);
  }

  // try で囲むのは、編集の要求だけにする（登録と同じ理由）。
  try {
    await apiRequest("PATCH", `/api/tasks/${task.id}`, body);
  } catch (error) {
    if (startedSerial !== editSerial) {
      return;
    }
    showApiError(error, TASK_EDIT_FIELDS, TASK_EDIT_FORM_ERROR_ID);
    setSubmitting(submitButton, false, TASK_EDIT_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === editSerial) {
    hideModal(getElement("task-edit-modal"));
  }
  await loadTasks({ showLoading: false });
}

// 一覧の「削除」ボタン。対象を控えて、削除の確認のモーダルを開く。
function openDeleteModal(task) {
  deletingTask = { ...task };
  window.bootstrap.Modal.getOrCreateInstance(
    getElement("task-delete-modal"),
  ).show();
}

function showDeleteError(error) {
  const deleteError = getElement("task-delete-error");
  deleteError.textContent = errorMessageOf(error);
  setVisible(deleteError, true);
}

function hideDeleteError() {
  const deleteError = getElement("task-delete-error");
  deleteError.replaceChildren();
  setVisible(deleteError, false);
}

// 削除の確認のモーダルを開くたびに、対象を表示し、エラーを消す。
function prepareDeleteModal() {
  deleteSerial += 1;
  getElement("task-delete-target").textContent =
    `${taskLabel(deletingTask)}を削除します。`;
  hideDeleteError();
  setSubmitting(
    getElement("task-delete-submit-button"),
    false,
    TASK_DELETE_SUBMIT_LABELS,
  );
}

async function submitTaskDelete() {
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = deleteSerial;
  const taskId = deletingTask.id;
  hideDeleteError();

  const submitButton = getElement("task-delete-submit-button");
  setSubmitting(submitButton, true, TASK_DELETE_SUBMIT_LABELS);

  // try で囲むのは、削除の要求だけにする（登録と同じ理由）。
  try {
    await apiRequest("DELETE", `/api/tasks/${taskId}`);
  } catch (error) {
    if (startedSerial !== deleteSerial) {
      return;
    }
    showDeleteError(error);
    setSubmitting(submitButton, false, TASK_DELETE_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === deleteSerial) {
    hideModal(getElement("task-delete-modal"));
  }
  await loadTasks({ showLoading: false });
}

export function initTasks() {
  // 課題・タスクのモードを開くたびに、一覧を取得し直す（ほかのモードでの
  // 授業の削除などを反映し、期限切れを、開いたときの日時で判定するため）。
  // 前の切り替えのエラーは消す。
  getElement("tasks-tab").addEventListener("shown.bs.tab", () => {
    hideActionError();
    loadTasks();
  });
  getElement("task-retry-button").addEventListener("click", () => {
    loadTasks();
  });

  // 追加・編集・削除のモーダルは、成功したら、JavaScriptから閉じるため、
  // 表示の途中かを記録する（ui.js の hideModal）。
  const addModal = getElement("task-modal");
  trackModalShowing(addModal);
  addModal.addEventListener("show.bs.modal", prepareAddModal);
  addModal.addEventListener("shown.bs.modal", () => {
    getElement("task-title").focus();
  });
  getElement("task-form").addEventListener("submit", submitTask);

  const editModal = getElement("task-edit-modal");
  trackModalShowing(editModal);
  editModal.addEventListener("show.bs.modal", prepareEditModal);
  editModal.addEventListener("shown.bs.modal", () => {
    getElement("task-edit-title").focus();
  });
  getElement("task-edit-form").addEventListener("submit", submitTaskEdit);

  const deleteModal = getElement("task-delete-modal");
  trackModalShowing(deleteModal);
  deleteModal.addEventListener("show.bs.modal", prepareDeleteModal);
  // 取り消せない操作のため、最初のフォーカスは「キャンセル」に置く。
  deleteModal.addEventListener("shown.bs.modal", () => {
    getElement("task-delete-cancel-button").focus();
  });
  getElement("task-delete-submit-button").addEventListener(
    "click",
    submitTaskDelete,
  );
}
```

### 付録H. `app/static/js/main.js`

<!-- 全文: app/static/js/main.js -->
```javascript
import { initCalendar } from "./calendar.js";
import { initClosures } from "./closures.js";
import { initSemesters } from "./semesters.js";
import { initSubjects } from "./subjects.js";
import { initTasks } from "./tasks.js";

// 今後のモードの初期化も、ここに足す。
// semester-selectedを購読する側を、イベントを発行する側より先に初期化する。
initSubjects();
initClosures();
initSemesters();
// 課題・タスクは、ほかのモードとイベントでつながらない。
initTasks();
// カレンダーは、ほかのモードとイベントでつながらない。予期しない例外で、
// ほかのモードの初期化が止まらないように、最後に初期化する。
initCalendar();
```

