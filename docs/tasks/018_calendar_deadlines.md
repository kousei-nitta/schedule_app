# タスク018: カレンダーへの締切の表示

| 項目 | 内容 |
|---|---|
| Task ID | 018 |
| Task名 | カレンダーへの締切の表示（週表示の「締切」の行、月表示の●の印、「直近の締切」欄、絞り込みへの課題の追加、締切の詳細パネルからの完了の切り替え）と、課題・タスクの表示の共通化（`task_display.js`）、013-L1・017-L1 |
| ブランチ | `feature/018-calendar-deadlines`（Komaが作成・切替済みの状態で渡される） |

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに停止して報告する。

**このタスクには、承認ゲートはない（DBの構造を変えないため、migrationを作らない）。** 段階1・2を順に進め、「Copilot確認手順」を実施したら、結果を報告して応答を終える。途中で止まるのは、「注意」の停止の条件に当たったときだけ。**止まるときは、報告を書いて応答を終える。質問の機能（選択肢を出して回答を待つ機能）は使わない**（`.github/copilot-instructions.md` の「止まる場面の応答」）。

**ファイルは、手で書き写さない。** 5つのファイルの全文は、このTask MDの付録にある。各段階の始めに、「全文からファイルを作るスクリプト」を実行して作る（013-N1）。付録の全文は、スクリプトが読む。付録を読んで書き写す必要はない（本文の要点・差分・確認の手順を読む）。

**報告には、コマンドの出力を、要約せずに、そのまま貼る**（014-L1）。「注意」の最後の報告の項目を参照。

**このTask MDのスクリプトとコマンドには、バックスラッシュ（`\`）の書き方を使っていない**（016-N1。改行は、スクリプトの中で `newline = chr(10)` として表す。`grep` は、`-F`（文字どおりに探す）と `-e`（探す文字列を1つずつ指定）で書く）。**コマンドは、書いてあるとおりに実行する。`grep` の `-e` を足す・減らすことも含め、書き換えた場合は、どこをどう書き換えたかを、報告に書く**（017-N1）。

## 目的
カレンダーモードに、課題・タスク（課題と、その他（締切のみ））の締切を表示する（Task 016の `/api/tasks` を使う）。週表示の時間軸の上の「締切」の行と、月表示の、●の印とタイトルの締切、カレンダーの右の「直近の締切」欄（期限切れと、今日から7日後まで）、絞り込みの「課題」、締切をクリックして開く詳細パネル（完了の切り替え）を作る。設計資料（`docs/ui_ux.md` の「カレンダーモード」、`docs/architecture.md` の「JavaScriptの構成（ES modules）」と「FullCalendarの使い方（`calendar.js`）」）の仕様を、そのまま実装する。あわせて、課題・タスクの表示の共通処理（課題・タスクを表す文字列、期限切れの判定と印、アイコンと課題名）を、`tasks.js` から新しい `task_display.js` に移し（カレンダーの「直近の締切」欄が、2つ目の利用者になるため）、持ち越しの013-L1（カレンダーの、取得のあとの例外が表示されない）と017-L1（課題・タスクの一覧で、長い文字列が右の列にはみ出す）を直す。**Python・API・DBの構造は変えない**（pytestは787件のまま）。

次の2段階で、この順に行う。

| 段階 | 内容 | 挙動の変化 | 段階の終わりの `pytest` |
|---|---|---|---|
| 1 | 共通の部品と課題・タスクモード：`task_display.js`（新規。課題・タスクの表示の共通処理）、`tasks.js`（共通処理を `task_display.js` から使う。017-L1）、`categories.js`（コメントだけ） | 課題・タスクモードの見た目と動きは同じ。区切れる場所のない長い文字列が、課題名・対象授業のセルの中で折り返す（017-L1） | **787件**（Pythonを変えない） |
| 2 | カレンダー：`index.html`（「直近の締切」欄、締切の詳細パネル、予定の詳細パネルの折り返し）、`calendar.js`（締切の表示、欄、詳細パネル、絞り込みの「課題」、表示の切り替えのボタン、013-L1） | カレンダーに締切と「直近の締切」欄が出る | **787件** |

## 前提（Task 017完了時点の状態）

| 区分 | 内容 |
|---|---|
| すでにある | 学期・授業・休講日のAPIと画面、予定API、カレンダー表示（Task 013）、授業の編集・削除（Task 014・015）、課題・タスクのAPI（Task 016）、課題・タスクモードの画面（Task 017。`tasks.js`、`current_semester.js`、`categories.js` の `TASK_CATEGORIES`・`taskCategoryOf`、`dates.js` の `localDateTimeString`・`formatJapaneseDateTime`、`style.css` の `.category-assignment`）。pytest（**787件**。`main` の `6fba14e` で確認） |
| まだない | カレンダーの締切の表示（週表示は、終日の行を出さない設定 `allDaySlot: false`）、「直近の締切」欄、締切の詳細パネル、絞り込みの「課題」、`task_display.js` |
| DBの構造 | 変えない（初期migration `0280f6cf8d09` と、休講日の `42bd53808fa1`）。**migrationは不要** |
| 開発用DB | `instance/app.db` は、Komaの実際の開発用DB（すべてのテーブルが0件。2026-10-17、Task 017の確認のあとにKomaが確認）。**Copilotは、書き込まない。サーバーを起動しない（`python run.py` を実行しない）**。読むのは、「Copilot確認手順」のハッシュと件数だけ。**`sqlite3` は、必ず `-readonly` を付けて実行する**（011-L1） |
| 設計資料 | このタスクの前に、更新した設計資料が `main` に反映されている。`docs/ui_ux.md` の「カレンダーモード」に、「締切の詳細パネル（課題・タスク）」の節と、「直近の締切」欄の詳細がある。`docs/architecture.md` の「JavaScriptの構成（ES modules）」に、`task_display.js` の行があり、「FullCalendarの使い方（`calendar.js`）」に、「締切（課題・タスク）」と「一覧表示には、締切を出さない」がある |
| 確認 | JavaScriptの自動テストはない。画面の動きは、Komaの確認（確認用のサーバーでのブラウザ確認。ブラウザの操作はClaude）で確かめる。Copilotは、ブラウザでの確認をしない |

## Source of Truth
- `docs/ui_ux.md`：「カレンダーモード」（「週表示」「月表示」「一覧表示」「共通」（絞り込み、「直近の締切」欄）、「予定の確認・編集・削除」、「締切の詳細パネル（課題・タスク）」）、「課題・タスクモード」の「一覧」（017-L1の折り返し）と「カレンダーとの関係」、「色・アイコン」
- `docs/architecture.md`：「JavaScriptの構成（ES modules）」（`calendar.js`・`task_display.js`・`tasks.js`・`categories.js` の役割、規則。特に、モーダルの規則、モーダルの中で始める要求の規則、`try` で囲む範囲、`textContent`、DOMの `id`、名前つきの引数）、「FullCalendarの使い方（`calendar.js`）」（「取得の失敗」「締切（課題・タスク）」「一覧表示には、締切を出さない」「絞り込み」「詳細パネル」）、「課題・タスクAPI」（「今日」の扱い、`?is_completed=false`）、「`api.js` の仕様」
- `docs/requirements.md`：「カレンダー表示」、「課題の完了管理」
- `.github/copilot-instructions.md`：進め方、「止まる場面の応答」、コーディング方針（JavaScript）

## 実装対象ファイル

| 区分 | ファイル | 段階 | 内容 | 全文 |
|---|---|---|---|---|
| 新規 | `app/static/js/task_display.js` | 1 | 課題・タスクの表示の共通処理（`taskLabel`・`isTaskOverdue`・`createOverdueBadge`・`createTaskTitle`） | 付録A |
| 変更 | `app/static/js/tasks.js` | 1 | 共通処理を `task_display.js` から使う（`taskLabel` を移す。期限切れの判定・印、アイコンと課題名の表示を置き換える）。課題名・対象授業のセルに `text-break`（017-L1） | 付録B |
| 変更 | `app/static/js/categories.js` | 1 | `EVENT_CATEGORIES` の並びのコメントだけ（絞り込みの並びは、`calendar.js` で決めるため） | 付録C |
| 変更 | `app/templates/index.html` | 2 | カレンダーの右の列に「直近の締切」欄。締切の詳細パネル（`task-detail-modal`）。予定の詳細パネルの見出しと項目に `text-break` | 付録D |
| 変更 | `app/static/js/calendar.js` | 2 | 締切の表示（2つ目の取得元）、「直近の締切」欄、締切の詳細パネル、絞り込みの「課題」、表示の切り替えのボタン（一覧表示では締切を出さない）、同じ日の並び、013-L1 | 付録E |

上の5ファイル以外は、変更しない（`__pycache__/` などの、`.gitignore` の対象は除く）。**5ファイルとも、このTask MDの付録に全文がある。「全文からファイルを作るスクリプト」で作り、手で書き写さない。書き込んだあとに、手で直さない。** 全文を変える必要があると判断した場合は、変えずに停止して報告する。

## 非対象（このタスクでは作らない・変更しない）
- Pythonのファイル（`app/` の `.py`、`run.py`）、`tests/`（**テストは変えない・足さない**）、`migrations/`（**`flask db` のコマンドを、一切実行しない**）、`requirements.txt`（**ライブラリを追加しない**）、`pytest.ini`
- `app/templates/base.html`、`app/static/css/style.css`、`app/static/js/` の上の4つ以外のファイル（`api.js`・`ui.js`・`dates.js`・`main.js`・`current_semester.js`・`semesters.js`・`subjects.js`・`closures.js`）
- `index.html` の、「直近の締切」欄（カレンダーの表示の場所を、2つの列に分けた部分を含む）、締切の詳細パネル、予定の詳細パネルの2か所の `text-break` 以外の部分
- `docs/`、`.github/`、`.gitignore`
- 作らないもの：その他（締切のみ）のカレンダーからの追加（カレンダーからの予定の操作を実装するタスクで、予定の追加フォームと一緒に作る）、締切の詳細パネルの編集・削除のボタン（同じタスクで決める）、「直近の締切」欄の行から詳細パネルを開く操作、カレンダーへの休講日の表示
- 持ち越しの003-H・017-N2（このタスクでは扱わない。017-N2は、ほかのモーダルの直し方を、あとで決める。新しい締切の詳細パネルでは、保存のあとにフォーカスを戻すことで、起きないようにしてある）
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
        "app/static/js/task_display.js",
        "app/static/js/tasks.js",
        "app/static/js/categories.js",
    ],
    "2": [
        "app/templates/index.html",
        "app/static/js/calendar.js",
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
full_texts = read_full_texts("docs/tasks/018_calendar_deadlines.md")
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
| 1（`python - 1`） | `全文の数：5`、`app/static/js/task_display.js：書き込み（51行）`、`app/static/js/tasks.js：書き込み（643行）`、`app/static/js/categories.js：書き込み（60行）` |
| 2（`python - 2`） | `全文の数：5`、`app/templates/index.html：書き込み（624行）`、`app/static/js/calendar.js：書き込み（698行）` |

- 出力が上と違う場合（全文の数・行数・エラー）は、ほかの作業をせずに停止して報告する
- 段階の終わりの「全文との比較」（「Copilot確認手順」の4）で「不一致」が出た場合は、手で直さず、その段階のスクリプトをもう一度実行して、全文に戻す。戻したことと、違っていた理由（分かれば）を、報告に書く（013-N1）

## 段階1：共通の部品と課題・タスクモード

### 1-1. `app/static/js/task_display.js`（新規。全文：付録A）
課題・タスクの表示の共通処理。課題・タスクモード（`tasks.js`）と、カレンダーの「直近の締切」欄（`calendar.js`）で使う（モードのファイル同士は、互いを `import` しないため。`docs/architecture.md` の「JavaScriptの構成」の `task_display.js` の行）。APIは扱わない。公開する関数は、次の4つ。

| 関数 | 内容 |
|---|---|
| `taskLabel(task)` | 課題・タスクを表す文字列「「タイトル」（締切 2026年10月20日（火） 23:59）」（`tasks.js` から移した。中身は同じ）。読み上げの名前（`aria-label`）と、削除の確認の文に使う |
| `isTaskOverdue(task, now)` | 期限切れか。未完了で、締切日時が `now`（`YYYY-MM-DDTHH:MM`）より前なら `true`。締切日時と同じ分は、期限切れではない（文字列の大小で比べる。`tasks.js` の今の判定と同じ） |
| `createOverdueBadge()` | 期限切れの印（`<span class="badge text-bg-danger ms-1">期限切れ</span>`）を作る（`tasks.js` の今の印と同じ） |
| `createTaskTitle(task)` | カテゴリのアイコン（`aria-hidden="true"`）と、見えないカテゴリ名（`visually-hidden`。「課題：」「その他：」）と、課題名を並べた `<div>` を作る（`tasks.js` の今の課題名のセルの1行目と同じ） |

### 1-2. `app/static/js/tasks.js`（全文：付録B）
要点：
- `taskLabel` を消し、`task_display.js` から `import` する。`categories.js` の `taskCategoryOf` の `import` を消す（`createTaskTitle` が使うため）
- `createTaskRow(task, overdueBefore)` を `createTaskRow(task, now)` にする。期限切れは `isTaskOverdue(task, now)`、印は `createOverdueBadge()`、課題名の1行目は `createTaskTitle(task)`。完了の表では、`isTaskOverdue` が `false` になる（未完了だけが期限切れ）ため、今までの `null`（期限切れを出さない）の代わりに、2つの表に同じ `now` を渡す
- `renderTaskTable` の名前つきの引数 `overdueBefore` を `now` にする。`renderTasks` で、`now`（`localDateTimeString()`）を1回求めて、2つの表に渡す
- 017-L1：課題名のセルと対象授業のセルに、`className = "text-break"`（Bootstrapの、どこでも折り返すclass）。区切れる場所のない長い文字列（空白のない長いURL、英数字の長いタイトル）が、右の「対象授業」「操作」の列にはみ出さないようにする（原因は、`.task-table` の `table-layout: fixed`。列の幅は変えない）
- 一覧の表示（並び・文言・印・アイコン・`aria-label`）と、完了の切り替え・追加・編集・削除の動きは変わらない

`main` からの差分（確認用）：

```diff
--- a/app/static/js/tasks.js
+++ b/app/static/js/tasks.js
@@ -1,11 +1,16 @@
 import { apiRequest } from "./api.js";
-import { taskCategoryOf } from "./categories.js";
 import { chooseCurrentSemester } from "./current_semester.js";
 import {
   formatJapaneseDateTime,
   localDateString,
   localDateTimeString,
 } from "./dates.js";
+import {
+  createOverdueBadge,
+  createTaskTitle,
+  isTaskOverdue,
+  taskLabel,
+} from "./task_display.js";
 import {
   clearFormErrors,
   errorMessageOf,
@@ -87,15 +92,6 @@ let addSerial = 0;
 let editSerial = 0;
 let deleteSerial = 0;
 
-// 課題・タスクを表す文字列（例：「レポート第1回」（締切 2026年10月20日（火）
-// 23:59））。同じタイトルの課題・タスクを、締切で区別できるようにする。
-function taskLabel(task) {
-  return (
-    `「${task.title}」` +
-    `（締切 ${formatJapaneseDateTime(task.due_datetime)}）`
-  );
-}
-
 // 締切日と締切時刻の入力欄の値を、APIの日時（YYYY-MM-DDTHH:MM）にする。
 function dueDateTimeOf(dateInputId, timeInputId) {
   const date = getElement(dateInputId).value;
@@ -128,10 +124,9 @@ function hideActionError() {
   setVisible(actionError, false);
 }
 
-// 一覧の1行を作る。overdueBefore は、期限切れの判定に使う今の日時
-// （YYYY-MM-DDTHH:MM）。完了の表では null（期限切れを出さない）。
-function createTaskRow(task, overdueBefore) {
-  const category = taskCategoryOf(task.category);
+// 一覧の1行を作る。now は、期限切れの判定に使う今の日時
+// （YYYY-MM-DDTHH:MM）。
+function createTaskRow(task, now) {
   const label = taskLabel(task);
   const row = document.createElement("tr");
 
@@ -150,28 +145,16 @@ function createTaskRow(task, overdueBefore) {
 
   const dueCell = document.createElement("td");
   dueCell.textContent = formatJapaneseDateTime(task.due_datetime);
-  // 締切日時が今より前なら、期限切れ（YYYY-MM-DDTHH:MMは桁が固定されて
-  // いるため、文字列の大小で前後を比べられる）。
-  if (overdueBefore !== null && task.due_datetime < overdueBefore) {
-    const badge = document.createElement("span");
-    badge.className = "badge text-bg-danger ms-1";
-    badge.textContent = "期限切れ";
-    dueCell.append(badge);
+  if (isTaskOverdue(task, now)) {
+    dueCell.append(createOverdueBadge());
   }
   row.append(dueCell);
 
+  // 課題名と対象授業のセルは、区切れる場所のない長い文字列（空白のない
+  // 長いURLなど）も、折り返す（右の列にはみ出さないため。017-L1）。
   const titleCell = document.createElement("td");
-  const titleLine = document.createElement("div");
-  const icon = document.createElement("span");
-  icon.className = "me-1";
-  icon.setAttribute("aria-hidden", "true");
-  icon.textContent = category.icon;
-  // アイコンは読み上げないため、カテゴリの表示名を、見えない文字で添える。
-  const categoryName = document.createElement("span");
-  categoryName.className = "visually-hidden";
-  categoryName.textContent = `${category.label}：`;
-  titleLine.append(icon, categoryName, task.title);
-  titleCell.append(titleLine);
+  titleCell.className = "text-break";
+  titleCell.append(createTaskTitle(task));
   if (task.notes !== null) {
     const notes = document.createElement("div");
     notes.className = "text-muted small text-pre-wrap";
@@ -181,6 +164,7 @@ function createTaskRow(task, overdueBefore) {
   row.append(titleCell);
 
   const subjectCell = document.createElement("td");
+  subjectCell.className = "text-break";
   subjectCell.textContent = task.subject_name ?? "—";
   row.append(subjectCell);
 
@@ -215,10 +199,10 @@ function createTaskRow(task, overdueBefore) {
 
 // 1つの表（未完了か完了）の行を作り直す。0件なら、表を隠して、
 // 0件の文言を出す。
-function renderTaskTable(tasks, { bodyId, listId, emptyId, overdueBefore }) {
+function renderTaskTable(tasks, { bodyId, listId, emptyId, now }) {
   const fragment = document.createDocumentFragment();
   for (const task of tasks) {
-    fragment.append(createTaskRow(task, overdueBefore));
+    fragment.append(createTaskRow(task, now));
   }
   getElement(bodyId).replaceChildren(fragment);
   setVisible(getElement(emptyId), tasks.length === 0);
@@ -227,22 +211,24 @@ function renderTaskTable(tasks, { bodyId, listId, emptyId, overdueBefore }) {
 
 // 一覧を、未完了と完了の2つの表に分けて表示する。APIの並びは、締切日時の
 // 早い順。未完了は、そのまま（期限切れが上に来る）。完了は、逆にして、
-// 締切日時の新しい順にする。期限切れは、表示するときの日時で判定する。
+// 締切日時の新しい順にする。期限切れは、表示するときの日時で判定する
+// （完了の表には、期限切れの印は付かない）。
 function renderTasks(tasks) {
   const incomplete = tasks.filter((task) => !task.is_completed);
   const completed = tasks.filter((task) => task.is_completed).reverse();
+  const now = localDateTimeString();
 
   renderTaskTable(incomplete, {
     bodyId: "task-incomplete-body",
     listId: "task-incomplete-list",
     emptyId: "task-incomplete-empty",
-    overdueBefore: localDateTimeString(),
+    now,
   });
   renderTaskTable(completed, {
     bodyId: "task-completed-body",
     listId: "task-completed-list",
     emptyId: "task-completed-empty",
-    overdueBefore: null,
+    now,
   });
   setVisible(getElement("task-loading"), false);
   setVisible(getElement("task-load-error"), false);
```

### 1-3. `app/static/js/categories.js`（全文：付録C）
要点：`EVENT_CATEGORIES` の前のコメントだけを変える（「並びは、カレンダーの絞り込みの選択肢の並び」を、「並びは、`app/categories.py` の `EVENT_CATEGORIES` と同じ（カレンダーの絞り込みの選択肢の並びは、`calendar.js` で決める）」にする）。対応表と関数は変えない。

`main` からの差分（確認用）：

```diff
--- a/app/static/js/categories.js
+++ b/app/static/js/categories.js
@@ -4,7 +4,8 @@
 // 色の値は、style.css の、className と同じ名前のclassに書く
 // （JavaScriptでは、色の値を持たない）。
 
-// 予定（Event）のカテゴリ。並びは、カレンダーの絞り込みの選択肢の並び。
+// 予定（Event）のカテゴリ。並びは、app/categories.py の EVENT_CATEGORIES と
+// 同じ（カレンダーの絞り込みの選択肢の並びは、calendar.js で決める）。
 export const EVENT_CATEGORIES = {
   class: {
     label: "授業",
```

## 段階2：カレンダー

### 2-1. `app/templates/index.html`（全文：付録D）
要点：
- カレンダーモード（`calendar-pane`）の `<div id="calendar-view"></div>` を、2つの列（`row g-3`。左 `col-lg-9` にカレンダー、右 `col-lg-3` に「直近の締切」欄）にする。画面の幅が992px未満では、欄はカレンダーの下に出る（Bootstrapの `lg`）。絞り込みの行と、取得の失敗の表示は、今のまま（2つの列の上）
- 「直近の締切」欄（`calendar-deadline-panel`。`section`、`card`）：見出し「直近の締切」（`calendar-deadline-heading`。`h2`、`h6`）、説明「期限切れと、今日から7日後までの、未完了の課題・タスク」、読み込み中（`calendar-deadline-loading`。最初は表示）、取得の失敗（`calendar-deadline-load-error`。メッセージと「再読み込み」。最初は隠す）、本体（`calendar-deadline-content`。最初は隠す）。本体の中は、完了の切り替えのエラー（`calendar-deadline-action-error`）、0件の文言「直近の締切はありません」（`calendar-deadline-empty`）、一覧（`calendar-deadline-list`。`ul`）。行（`li`）は `calendar.js` が作る
- 締切の詳細パネル（`task-detail-modal`）：予定の詳細パネル（`event-modal`）のあとに足す（`<main>` の外。`fade`）。見出し（`task-detail-modal-title`）、エラー（`task-detail-error`。最初は隠す）、項目（カテゴリ（アイコン `task-detail-category-icon`・表示名 `task-detail-category`）、締切（`task-detail-due` と、期限切れの印 `task-detail-overdue`。印は最初は隠す）、対象授業の行（`task-detail-subject-row`・`task-detail-subject`）、詳細・メモの行（`task-detail-notes-row`・`task-detail-notes`。`text-pre-wrap`））、「完了」のチェックボックス（`task-detail-completed`。ラベル「完了」）、「閉じる」ボタン（`data-bs-dismiss="modal"`）
- 予定の詳細パネルの見出し（`event-modal-title`）と項目の `dl` に、`text-break` を足す（締切の詳細パネルの見出しと `dl` も、`text-break`）

予定の詳細パネルで変わる行（確認用。`main` の行（`-`）と、このタスクの行（`+`）だけを並べた。「直近の締切」欄と、締切の詳細パネルの全文は、付録D）：

```diff
-        <h2 class="modal-title h5" id="event-modal-title"></h2>
+        <h2 class="modal-title h5 text-break" id="event-modal-title"></h2>
-        <dl class="mb-0">
+        <dl class="mb-0 text-break">
```

足すDOMの `id`（22個）：

| 場所 | `id` |
|---|---|
| 「直近の締切」欄（10個） | `calendar-deadline-panel`、`calendar-deadline-heading`、`calendar-deadline-loading`、`calendar-deadline-load-error`、`calendar-deadline-load-error-message`、`calendar-deadline-retry-button`、`calendar-deadline-content`、`calendar-deadline-action-error`、`calendar-deadline-empty`、`calendar-deadline-list` |
| 締切の詳細パネル（12個） | `task-detail-modal`、`task-detail-modal-title`、`task-detail-error`、`task-detail-category-icon`、`task-detail-category`、`task-detail-due`、`task-detail-overdue`、`task-detail-subject-row`、`task-detail-subject`、`task-detail-notes-row`、`task-detail-notes`、`task-detail-completed` |

欄の行のチェックボックスの `id` は、`calendar-deadline-complete-<課題・タスクのid>`（`calendar.js` が作る）。

### 2-2. `app/static/js/calendar.js`（全文：付録E）
ファイルの構成（上から順に。「今までと同じ」は、`main` と同じ中身）：

| 名前 | 種類 | 内容 |
|---|---|---|
| `WEEK_VIEW`・`MONTH_VIEW`・`LIST_VIEW` | 定数 | 表示の名前 `"timeGridWeek"`・`"dayGridMonth"`・`"listFourWeeks"`（今までと同じ値。設定の中の文字列を、この定数に置き換えた） |
| `LIST_DAYS` | 定数 | 一覧表示の日数 `28`（今までと同じ） |
| `UPCOMING_DAYS` | 定数 | 「直近の締切」欄の範囲 `7`（締切日が今日から7日後まで。`index.html` の欄の説明の日数と合わせる） |
| `DEADLINE_SOURCE_ID` | 定数 | 締切の取得元のid `"deadlines"` |
| `FILTER_CATEGORIES` | 定数 | 絞り込みの選択肢 `[保存値, 対応表の項目]` の配列。並びは、授業（`EVENT_CATEGORIES.class`）・課題（`TASK_CATEGORIES.assignment`）・アルバイト（`EVENT_CATEGORIES.part_time`）・その他（`EVENT_CATEGORIES.other`）。その他の1つの選択肢で、予定と課題・タスクのその他を切り替える（保存値が同じ `"other"`） |
| `LIST_DETAIL_FIELDS`・`LIBRARY_ERROR_MESSAGE` | 定数 | 今までと同じ |
| `calendar`・`hiddenCategories`・`requestSerial` | 変数 | 今までと同じ（`hiddenCategories` には、`"assignment"` も入る） |
| `incompleteTasks`・`taskRequestSerial` | 変数 | 未完了の課題・タスク（APIの一覧の並び。締切日時・idの昇順）と、その取得の通し番号 |
| `deadlinesShown` | 変数 | カレンダーに締切を出すか（一覧表示では `false`） |
| `detailTask`・`detailOpenedAt`・`detailSerial` | 変数 | 締切の詳細パネルの対象（コピー）、開いたときの日時（期限切れの判定に使う）、開くたびに増やす通し番号 |
| `showLoadError`・`hideLoadError`・`toApiRange`・`toCalendarEvent`・`fetchEvents` | 関数 | 今までと同じ |
| `toDeadlineEvent(task)` | 関数 | 課題・タスクを、FullCalendarの締切にする：`id`（`task-<id>`）、`title`、`start`（締切日 `YYYY-MM-DD`）、`allDay: true`、`display: "list-item"`（●の印）、`classNames`（カテゴリのclass）、`extendedProps`（`dueDateTime`：締切日時。`apiTask`：課題・タスクのコピー） |
| `fetchDeadlines(fetchInfo, successCallback, failureCallback)` | 関数 | 締切の取得元。APIを呼ばず、`incompleteTasks` から、絞り込みで外したカテゴリを除いて `toDeadlineEvent` で作り、`successCallback` ですぐに返す。`deadlinesShown` が `false` なら、空の配列。形の変換の例外は、`failureCallback` に渡す |
| `refetchDeadlines` | 関数 | 締切の取得元を、取得し直す（`calendar.getEventSourceById(DEADLINE_SOURCE_ID).refetch()`） |
| `switchView(viewType)` | 関数 | 表示の切り替えのボタン（下の順序） |
| `renderListEventContent`・`showEventDetail` | 関数 | 今までと同じ |
| `setDetailRow` | 関数 | 今までと同じ（締切の詳細パネルでも使う。コメントだけ変えた） |
| `showDeadlineLoading`・`showDeadlineLoadError` | 関数 | 欄の読み込み中・取得の失敗の表示 |
| `showDeadlineActionError`・`hideDeadlineActionError` | 関数 | 欄の完了の切り替えのエラーの表示・消去（欄の上部） |
| `createDeadlineItem(task, now)` | 関数 | 欄の1行（`li`）：完了のチェックボックス（`aria-label` は「`taskLabel` の完了」）、締切（`formatJapaneseDateTime`。期限切れなら `createOverdueBadge()`）、`createTaskTitle(task)`、対象授業（`subject_name` が `null` でなければ） |
| `renderDeadlinePanel` | 関数 | 欄を作り直す：締切日（`due_datetime` の日付の部分）が、今日から `UPCOMING_DAYS` 日後以前の未完了を、APIの並びで並べる（期限切れは、締切日が今日以前のため、すべて入る）。0件なら0件の文言 |
| `loadDeadlines({ showLoading = true } = {})` | 関数 | 未完了の課題・タスクの取得（下の順序） |
| `toggleDeadlineCompleted(task, checkbox)` | 関数 | 欄の完了の切り替え（下の順序） |
| `showTaskDetail(apiTask)` | 関数 | 締切のクリック。対象のコピーを控えて、締切の詳細パネルを開く（値は、`show.bs.modal` で入れる） |
| `updateDetailOverdue` | 関数 | 詳細パネルの期限切れの印を、`isTaskOverdue(detailTask, detailOpenedAt)` に合わせる |
| `showDetailError`・`hideDetailError` | 関数 | 詳細パネルのエラーの表示・消去 |
| `prepareTaskDetail` | 関数 | 詳細パネルの `show.bs.modal`（下の順序） |
| `toggleDetailCompleted` | 関数 | 詳細パネルの完了の切り替え（下の順序） |
| `renderFilter` | 関数 | 絞り込みの選択肢を、`FILTER_CATEGORIES` から作る（今までは `EVENT_CATEGORIES`。作り方は同じ） |
| `initCalendar` | 関数（`export`） | FullCalendarの設定（下の変更点）、「再読み込み」（カレンダー・欄）、`calendar-tab` の `shown.bs.tab`、詳細パネルの `show.bs.modal` と、チェックボックスの `change`。最後に `calendar.render()` と `loadDeadlines()` |

FullCalendarの設定の変更点（`main` との違い。ほかの設定は同じ）：
- `initialView`・`headerToolbar.right`・`views` のキー・`navLinkDayClick`・`moreLinkClick` の表示の名前を、定数に置き換えた（値は同じ）
- `customButtons`（新規）：表示と同じ名前の3つのボタン（文言「週」「月」「一覧」、説明「週表示」「月表示」「一覧表示」、押すと `switchView`）。これに合わせて、使わなくなった `buttonText` の `week`・`month`、`viewHint`、一覧表示の `buttonText` を消した（`buttonText` は `{ today: "今日" }` だけ）
- `eventOrder: "start,-duration,allDay,dueDateTime,title"`（新規）
- `allDaySlot: false` を消し、`allDayText: "締切"` を足した（週表示の終日の行を、締切の行にする）
- `events: fetchEvents` を、`eventSources: [{ id: "events", events: fetchEvents }, { id: DEADLINE_SOURCE_ID, events: fetchDeadlines }]` にした
- `eventSourceFailure`：何もしない関数を、`ApiError` でない例外だけを `showLoadError(error)` で表示する関数にした（013-L1。`ApiError` を `api.js` から `import` する）
- `eventClick`：`extendedProps` に `apiTask` があれば `showTaskDetail`、なければ今までどおり `showEventDetail`
- 月表示の `dayMaxEvents: 3` のコメントに「締切を含む」を足した（値は同じ）

`switchView(viewType)`（表示の切り替え）の順序：
1. 一覧表示へ：`deadlinesShown = false`、`refetchDeadlines()`（締切を外す）、`calendar.changeView(viewType)`
2. 週・月の表示へ：`calendar.changeView(viewType)`、`deadlinesShown = true`、`refetchDeadlines()`（締切を戻す）
- 同じ処理の中で続けて行うため、画面に出るのは最後の状態だけ（一覧表示に、締切が一瞬も出ない）。`calendar.batchRendering` は使わない（`docs/architecture.md` の「一覧表示には、締切を出さない」）

`loadDeadlines`（未完了の課題・タスクの取得）の順序：
1. `taskRequestSerial` を増やして控える。`showLoading` が `true` なら、欄の読み込み中を表示する（欄の本体を隠す）
2. `GET /api/tasks?is_completed=false`（`try` で囲むのは、この要求だけ）
3. どちらの場合も、新しい取得を始めていれば（`taskRequestSerial` が違えば）、何もしない
4. 失敗：欄に、取得の失敗（メッセージと「再読み込み」）を表示する（`incompleteTasks` は変えない。カレンダーの締切は、それまでのものが残る）
5. 成功：`incompleteTasks` に入れ、`renderDeadlinePanel()`、`refetchDeadlines()`

取得するのは、ページを開いたとき（`initCalendar` の最後）、カレンダーのモードを開いたとき（`shown.bs.tab`。予定の `refetchEvents()` と一緒に。欄の切り替えのエラーを消す）、欄の「再読み込み」（ここまでは、読み込み中を表示する）、完了の切り替えの成功のあと（`loadDeadlines({ showLoading: false })`）。

`toggleDeadlineCompleted`（欄の完了の切り替え）の順序（課題・タスクモードの `toggleTaskCompleted` と同じ形）：
1. 欄の切り替えのエラーを消し、チェックボックスを押せなくする
2. `PATCH /api/tasks/<id>` に `{ is_completed: <チェックボックスの今の状態> }`（`try` で囲むのは、この要求だけ）
3. 失敗：チェックを元に戻し、押せるようにし、エラーを欄の上部に表示する
4. 成功：`loadDeadlines({ showLoading: false })`（完了にしたものは、欄とカレンダーから消える）

`prepareTaskDetail`（締切の詳細パネルを開くとき）の順序：
1. `detailSerial` を増やす。`detailOpenedAt` に今の日時（`localDateTimeString()`）を入れる
2. 見出し（タイトル）、カテゴリ（`taskCategoryOf` のアイコンと表示名）、締切（`formatJapaneseDateTime`）を入れ、期限切れの印を合わせる（`updateDetailOverdue`）。対象授業とメモの行は、`setDetailRow`（値が `null` なら行を隠す）
3. 「完了」のチェックボックスを、今の完了の状態にし、押せるようにする。エラーを消す

`toggleDetailCompleted`（締切の詳細パネルの完了の切り替え）の順序：
1. 今の `detailSerial` と、対象、チェックボックスの今の状態（`completed`）を控える。エラーを消し、チェックボックスを押せなくする
2. `PATCH /api/tasks/<id>` に `{ is_completed: completed }`（`try` で囲むのは、この要求だけ）
3. 失敗：パネルを開き直していなければ（`detailSerial` が同じなら）、チェックを元に戻し、押せるようにして、チェックボックスにフォーカスを戻し、エラーをパネルの中に表示する。開き直していれば、何もしない
4. 成功：パネルを開き直していなければ、対象の `is_completed` を `completed` にし、期限切れの印を合わせ、チェックボックスを押せるようにして、フォーカスを戻す。パネルは閉じない。開き直していても、`loadDeadlines({ showLoading: false })` で、カレンダーの締切と欄を取得し直す
- フォーカスを戻すのは、押せなくしたときに、フォーカスがパネルの外に移り、Escapeキーでパネルを閉じられなくなるため（017-N2で見つかった挙動。このパネルでは起きないようにする）

注意：
- 締切の詳細パネルは、JavaScriptから開き（`window.bootstrap.Modal.getOrCreateInstance(...).show()`）、閉じるのは利用者のボタンだけ（`hideModal`・`trackModalShowing` は使わない。予定の詳細パネルと同じ）
- 期限切れの判定は、`task_display.js` の `isTaskOverdue`（欄は、作り直すときの日時。詳細パネルは、開いたときの日時）
- カレンダーのモードは、ほかのモードと `CustomEvent` でつながらない（課題・タスクモードでの変更は、カレンダーのモードを開くたびの取得で反映する）
- 予定の取得（`fetchEvents`）と、予定の詳細パネルは変えない

### 2-3. 変わる挙動・変わらない挙動

| 操作 | 変わる・変わらない |
|---|---|
| カレンダー（週表示） | 時間軸の上に「締切」の行が出て、未完了の締切が、●の印とタイトルで並ぶ（同じ日は締切日時の順）。締切のクリックで、締切の詳細パネルが開く |
| カレンダー（月表示） | 締切日に、●の印とタイトル（時間型のブロックより上）。1日3件まで（締切を含む）、4件目以降は「＋N件」 |
| カレンダー（一覧表示） | 変わらない（締切を出さない） |
| カレンダー（絞り込み） | 選択肢が、授業・課題・アルバイト・その他になる。課題・その他を外すと、その締切も出ない |
| カレンダー（表示の切り替えのボタン） | 見た目・文言・説明・押された状態は変わらない（独自のボタンにした） |
| カレンダー（取得のあとの例外） | 画面に、固定のメッセージを表示する（今までは、何も出なかった。013-L1。今のコードでは起きない） |
| 「直近の締切」欄 | カレンダーの右（幅が992px未満では下）に出る。完了の切り替えができる |
| 予定の詳細パネル | 長い文字列が、折り返す。ほかは変わらない |
| 課題・タスクモード | 長い文字列が、課題名・対象授業のセルの中で折り返す（017-L1）。ほかは変わらない（共通処理を `task_display.js` に移しただけ） |
| 授業モード・API・DB | 変わらない |

## JavaScriptの共通の規則
`.github/copilot-instructions.md` の「コーディング方針」のJavaScriptの規則と、`docs/architecture.md` の「JavaScriptの構成（ES modules）」の規則（`innerHTML` などを使わない、`textContent` で表示する、`fetch` は `api.js` だけ、`try` で囲むのは要求だけ、名前つきの引数、モードのファイル同士は `import` しない、1行は80文字以内）。付録の全文は、これらに合っている（「Copilot確認手順」の3・6で確かめる）。

## 変更してよい既存のテスト
なし（Pythonを変えないため、テストは変えない・足さない）。**既存のテスト（787件）が、想定外に失敗した場合**は、原因を調べ、そこで実装を止めて、チャットで報告する。

## 実装手順
1. ブランチ・作業ツリーの確認。設計資料が更新されていることを確認する（「Copilot確認手順」の1の `grep`）。更新されていなければ、何も変更せずに停止して報告する
2. 作業の前の状態を記録する：開発用DBの有無・ハッシュ・件数（「Copilot確認手順」の1。**`sqlite3` は `-readonly` を付ける**）。`python -m pytest -q` が787件、すべて合格すること（合格しなければ、何も変更せずに停止して報告する）
3. **（段階1）** 「全文からファイルを作るスクリプト」を `python - 1` で実行する。`python -m pytest -q` が787件、すべて合格すること。「全文との比較」（「Copilot確認手順」の4）を `python - 1` で実行し、3ファイルとも「一致」
4. **（段階2）** スクリプトを `python - 2` で実行する。`python -m pytest -q` が787件、すべて合格すること。「全文との比較」を `python - 2` で実行し、5ファイルとも「一致」
5. 「Copilot確認手順」の2・3・5・6・7を実施する
6. 結果を報告して、応答を終える（コマンドの出力は、要約せずに、そのまま貼る。サーバーを起動していないこと、ブラウザでの確認をしていないことを明記する）

各段階の終わりに、`python -m pytest -q` の結果（件数・警告）と、全文との比較の結果を控えておく（最終報告に、出力をそのまま貼る）。

## 完了条件
- `python -m pytest -q` が、作業の前と、段階1・段階2の終わりに、**787件**すべて合格する（失敗・エラー・スキップが0件）
- 変更・新規のファイルが、「実装対象ファイル」の5つだけ
- 5ファイルが、このTask MDの全文と1文字も違わない（「Copilot確認手順」の4が、段階1の終わりに3ファイル、段階2の終わりに5ファイルとも「一致」）
- `app/static/js/` のJavaScriptのファイルに、80文字を超える行がない
- 「Copilot確認手順」の5（画面のHTMLの確認）と6（検索と差分）が、期待どおり
- 実施の前後で、開発用DB（`instance/app.db`）のハッシュと、`semesters`・`subjects`・`closures`・`events`・`tasks` の件数が同じ
- 「Komaの確認」が、期待どおり
- レビューで承認される

## Copilot確認手順
**`sqlite3` は、必ず `-readonly` を付けて実行する**（011-L1）。**それぞれのコマンドの出力を、要約せずに、そのまま報告に貼る**（014-L1）。**コマンドは、書いてあるとおりに実行する（書き換えた場合は、報告に書く。016-N1・017-N1）。**

```
# 1. 実施前
git branch --show-current      # feature/018-calendar-deadlines
git status                     # 変更なし
grep -c -F "task_display.js" docs/architecture.md          # 4以上
grep -n -F -e "customButtons" -e "一覧表示には、締切を出さない" docs/architecture.md   # 2件以上（「FullCalendarの使い方」の節）
grep -n -F "### 締切の詳細パネル（課題・タスク）" docs/ui_ux.md   # 1件
grep -c -F "直近の締切" docs/ui_ux.md                        # 10以上
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
        "app/static/js/task_display.js",
        "app/static/js/tasks.js",
        "app/static/js/categories.js",
    ],
    "2": [
        "app/templates/index.html",
        "app/static/js/calendar.js",
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
expected_files = read_full_texts("docs/tasks/018_calendar_deadlines.md")
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
    "calendar-deadline-panel", "calendar-deadline-heading",
    "calendar-deadline-loading", "calendar-deadline-load-error",
    "calendar-deadline-load-error-message", "calendar-deadline-retry-button",
    "calendar-deadline-content", "calendar-deadline-action-error",
    "calendar-deadline-empty", "calendar-deadline-list",
    "task-detail-modal", "task-detail-modal-title", "task-detail-error",
    "task-detail-category-icon", "task-detail-category", "task-detail-due",
    "task-detail-overdue", "task-detail-subject-row", "task-detail-subject",
    "task-detail-notes-row", "task-detail-notes", "task-detail-completed",
]
ORDER = [
    "calendar-pane", "calendar-view", "calendar-deadline-panel",
    "subjects-pane", "tasks-pane", "event-modal", "task-detail-modal",
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
    print("詳細パネルは<main>の外:", html.index("</main>") < positions[-1])
    print("折り返し（text-break）:", html.count("text-break"))
    print("見出し「直近の締切」:", html.count(">直近の締切</h2>"))
    # JavaScriptが getElement("…") で使うidと、calendar.js の「"task-detail-…"」
    # 「"calendar-deadline-…"」の文字列のidが、HTMLにあること。
    missing = []
    get_element = 'getElement[(][ ' + newline + ']*"([^"]+)"'
    for path in sorted(Path("app/static/js").glob("*.js")):
        text = path.read_text(encoding="utf-8")
        for element_id in re.findall(get_element, text):
            if element_id not in ids:
                missing.append(f"{path.name}:{element_id}")
    calendar_text = Path("app/static/js/calendar.js").read_text(encoding="utf-8")
    pattern = '"((?:task-detail|calendar-deadline)-[a-z-]+)"'
    for element_id in re.findall(pattern, calendar_text):
        if element_id not in ids:
            missing.append(f"calendar.js:{element_id}")
    print("JavaScriptのidで、HTMLにないもの:", missing)
    for name in [
        "js/task_display.js", "js/tasks.js", "js/categories.js",
        "js/calendar.js",
    ]:
        response = client.get(f"/static/{name}")
        print(name, response.status_code, response.mimetype)
        response.close()
EOF

# 6. 検索と差分（段階2の終わり）
grep -rn -F -e innerHTML -e outerHTML -e insertAdjacentHTML -e "document.write" -e "eval(" -e localStorage -e sessionStorage -e setTimeout -e "export default" -e "var " -e ".style" -e "confirm(" app/static/js/   # 出力なし
grep -rn -F "fetch(" app/static/js/                                # 2件：api.js の「fetch(url, options)」と、calendar.js の「.refetch()」（FullCalendarの関数で、fetch ではない）
grep -rn -F -e "batchRendering" -e "datesSet" app/static/js/       # 出力なし
grep -rn -F -e "function taskLabel" -e "function isTaskOverdue" -e "function createOverdueBadge" -e "function createTaskTitle" app/static/js/   # 4件：すべて task_display.js
grep -rn -F -e "taskLabel(" -e "isTaskOverdue(" -e "createOverdueBadge(" -e "createTaskTitle(" app/static/js/   # 14件：task_display.js 4（定義）、tasks.js 5、calendar.js 5
grep -rn -F -e "trackModalShowing(" -e "hideModal(" app/static/js/ # 14件：ui.js 2（定義）、semesters.js 2、subjects.js 4、tasks.js 6（Task 017と同じ。calendar.js は使わない）
grep -rn -F "window.bootstrap.Modal" app/static/js/                # 7件：calendar.js 2、ui.js 1、subjects.js 2、tasks.js 2
grep -rn -F -e '"assignment"' -e '"other"' app/static/js/          # 4件：calendar.js 3（FILTER_CATEGORIES の前のコメント1と、FILTER_CATEGORIES の2行）、tasks.js 1（ASSIGNMENT の定義）
grep -n -F "export " app/static/js/task_display.js app/static/js/tasks.js app/static/js/calendar.js app/static/js/categories.js   # 10件：task_display.js 4、tasks.js 1（initTasks）、calendar.js 1（initCalendar）、categories.js 4
grep -rn -F "eventSourceFailure" app/static/js/                    # 2件：calendar.js（fetchDeadlines のコメント1と、設定1）
grep -rn -F "text-break" app/static/js/ app/templates/index.html   # 7件：calendar.js 1、tasks.js 2、index.html 4
grep -n -F -e onclick -e "style=" app/templates/index.html app/templates/base.html   # 出力なし
git diff --numstat app/static/js/tasks.js app/static/js/categories.js app/templates/index.html app/static/js/calendar.js
wc -l app/static/js/task_display.js
git diff --stat -- app/*.py app/routes/ app/models/ migrations/ tests/ requirements.txt pytest.ini run.py app/templates/base.html app/static/css/style.css app/static/js/api.js app/static/js/ui.js app/static/js/dates.js app/static/js/main.js app/static/js/current_semester.js app/static/js/semesters.js app/static/js/subjects.js app/static/js/closures.js   # 出力なし

# 7. 実施後
shasum -a 256 instance/app.db  # 実施前と同じ
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"   # 実施前と同じ
git status                     # 変更：4ファイル。新規：task_display.js
git diff --stat
```

| 確認 | 期待する結果 |
|---|---|
| `python -m pytest -q` | 実施前、段階1・段階2の終わりとも、787件がすべて合格。失敗・エラー・スキップが0件。`migrations/env.py` の `DeprecationWarning` は、出ても構わない（報告する） |
| 1行の長さ（3） | 出力なし |
| 全文との比較（4） | `全文の数：5` と、段階1の終わりは3ファイル、段階2の終わりは5ファイルとも「一致」。「不一致」が出たら、手で直さず、その段階の「全文からファイルを作るスクリプト」をもう一度実行して全文に戻し、2からやり直す（戻したことを報告する）。Task MDの全文のほうを変える必要があると判断した場合は、停止して報告する |
| 画面のHTMLの確認（5） | 「新しいid:」のあとが、`1` が22個の一覧。「重複したid: []」。「並び: True」「詳細パネルは<main>の外: True」「折り返し（text-break）: 4」「見出し「直近の締切」: 1」「JavaScriptのidで、HTMLにないもの: []」。4つのJavaScriptのファイルが `200 text/javascript` |
| 検索と差分（6） | 上のコメントのとおり。`git diff --numstat` は、`449 31 app/static/js/calendar.js`、`2 1 app/static/js/categories.js`、`23 37 app/static/js/tasks.js`、`63 3 app/templates/index.html`（表示の順は、Gitの並びでよい）。`wc -l` は、`51 app/static/js/task_display.js`。件数が違う場合は、その行を報告に書く |
| 開発用DB | 実施の前後で、ハッシュと、5つのテーブルの件数が同じ |
| `git status` | 変更：`app/static/js/calendar.js`、`app/static/js/categories.js`、`app/static/js/tasks.js`、`app/templates/index.html`。新規（`??`）：`app/static/js/task_display.js`。Pythonのファイル・`migrations/`・`tests/`・`docs/`・`.github/`・`requirements.txt`・`run.py`・`instance/`・ほかのJavaScriptのファイル・`base.html`・`style.css` に変更なし |

`.pytest_cache/` や `__pycache__/` が `git status` に表示される場合は、`.gitignore` を変更せず、報告する。**Copilotは、サーバーを起動せず、ブラウザでの確認もしない**（Claude と Koma が行う）。報告に、そのことを明記する。

## Komaの確認
順序：（1）pytest →（2）commit・push とレビューの依頼 →（3）ブラウザでの確認（確認用のサーバー）→（4）開発用DBでの、読み取りだけの確認 →（5）マージ。

### 1. pytest
`python -m pytest -q` を自分で実行し、**787件、すべて合格**することを確かめる。

### 2. push とレビューの依頼
featureブランチを commit・push する（PRを作ってもよい）。新規のファイル（`task_display.js`）も、commitに含める。Copilotの完了報告を共有して、Claudeにレビューを頼む。**pushは、マージではない。レビューの承認の前に、マージしない。** 修正が必要になった場合は、同じブランチでCopilotが直し、もう一度pushしてレビューを受ける。

### 3. ブラウザでの確認（確認用のサーバー）
レビューで「承認可能」になったあとに行う。**ブラウザの操作は、Claudeが、ブラウザのパネルまたはChromeで行う。Komaは、サーバーの起動・停止、確認用のデータの登録、DBのハッシュの確認、後片付けを行う**（roadmap の「進め方の決定の記録」、2026-10-12）。

#### 確認の安全のしくみ
- **開発用DBは使わない。** 確認用のDB（`/tmp/schedule-app-check-018/check.db`）を、migrationで作り、そのDBで起動した確認用のサーバーで確かめる（Task 010〜017と同じ方法）。開発用DBには、何も残らない
- 確認用のデータ（下の「確認用のデータの登録」）は、確認用のDBの場所を指定して、すべてアプリのAPIで登録する。**このスクリプトは、確認用のDBだけに書き込む**
- 確認の途中の、APIの直接の呼び出し（D7の削除、各項目の読み取り）は、確認用のDBの、確認のために登録したデータに限る（roadmap の「進め方の決定の記録」、2026-10-12）
- ブラウザは、BootstrapとFullCalendarを、インターネット（jsDelivr）から読み込む。インターネットにつながった状態で行う
- 確認の前後で、開発用DBのハッシュが同じことを確かめる

#### 確認の日付と時刻
確認用のデータの日付は、**データを登録した日（このMacの「今日」。以下 T）からの相対**で決める（「直近の締切」欄と期限切れは、今日によって変わるため）。下の表の日付の例は、**T が 2026年10月21日（水）の場合**（Claudeが、実際の T に読み替える）。

- **確認は、T の 00:05〜23:50 の間に行い、日付をまたがない**（T の 00:01 の課題が期限切れで、T の 23:57 以降の課題が期限切れでないことを前提にしているため）。日付をまたいだ場合は、後片付けをしてから、準備からやり直す
- 週表示の T−3 の列は、T が水〜土曜日のときだけ、同じ週に入る（日〜火曜日のときは、前の週）。T+7・T+8 は、いつも次の週

#### 準備
1. `python run.py` が起動していれば、Ctrl＋Cで止める（確認用のサーバーも、5001番を使うため）。開発用DBのハッシュを控える
   ```
   shasum -a 256 instance/app.db
   ```
2. 下の「確認用のサーバーの起動」のコマンドで、確認用のサーバーを起動する（このターミナルは、確認の間、開いたままにする）
3. 別のターミナルを開き、リポジトリのルートで、`.venv` を有効にして、下の「確認用のデータの登録」を実行する（1回だけ）
4. Claudeが、ブラウザで `http://127.0.0.1:5001/` を開き、強制再読み込みをする（ブラウザの幅は、1200px以上にする）

#### 確認用のサーバーの起動
ブランチ `feature/018-calendar-deadlines` のまま、リポジトリのルートで、`.venv` を有効にして、次を実行する（行の先頭に空白を入れずにコピーする）。

```
python - <<'EOF'
from pathlib import Path

from flask_migrate import upgrade

from app import create_app

# 確認用のDB（開発用DBとは別のファイル）。止めて起動し直しても、残る。
check_directory = Path("/tmp/schedule-app-check-018")
check_directory.mkdir(exist_ok=True)
database_path = check_directory / "check.db"
app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"})
with app.app_context():
    upgrade(directory="migrations")
print(f"確認用のDB：{database_path}", flush=True)
app.run(host="127.0.0.1", port=5001, debug=False)
EOF
```

期待する出力：初めての起動では、`Running upgrade  -> 0280f6cf8d09, initial tables` と `Running upgrade 0280f6cf8d09 -> 42bd53808fa1, add closures table`、「確認用のDB：/tmp/schedule-app-check-018/check.db」、`Running on http://127.0.0.1:5001`。起動し直したときは、`Running upgrade` の行が出ない。

#### 確認用のデータの登録
確認用のサーバーを起動したあとに、別のターミナルで、1回だけ実行する（行の先頭に空白を入れずにコピーする）。

```
python - <<'EOF'
from datetime import date, timedelta
from pathlib import Path

from app import create_app

# 確認用のDBだけに書き込む（開発用DBは使わない）。DBは、確認用のサーバーが、
# 起動のときにmigrationで作っておいたものを使う。
database_path = Path("/tmp/schedule-app-check-018/check.db")
if not database_path.exists():
    raise SystemExit("確認用のDBがありません。先に、確認用のサーバーを起動してください")
app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"})
client = app.test_client()
newline = chr(10)
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


# 学期・授業・課題・タスクは、すべてAPIで登録する。
semester = send("POST", "/api/semesters", {"name": "2026年度 後期", "start_date": day(-42), "end_date": day(42)}, 201)
subjects = [
    send("POST", "/api/subjects", {"semester_id": semester["id"], "subject_name": "テスト：今日の曜日の授業", "weekday": today.weekday(), "start_time": "13:00", "end_time": "14:30", "room": "3号館201"}, 201),
    send("POST", "/api/subjects", {"semester_id": semester["id"], "subject_name": "Subject_" + "y" * 60, "weekday": (today.weekday() + 2) % 7, "start_time": "09:00", "end_time": "10:00"}, 201),
]
tasks = [
    {"category": "assignment", "subject_id": subjects[0]["id"], "title": "テスト：期限切れの課題", "due_datetime": day(-3) + "T23:59"},
    {"category": "assignment", "subject_id": subjects[0]["id"], "title": "テスト：今日の朝の課題", "due_datetime": day(0) + "T00:01"},
    {"category": "assignment", "subject_id": subjects[1]["id"], "title": "Report_" + "x" * 80, "due_datetime": day(0) + "T23:57"},
    {"category": "assignment", "subject_id": subjects[0]["id"], "title": "テスト：今日のB", "due_datetime": day(0) + "T23:58", "notes": "メモ1行目" + newline + "メモ2行目"},
    {"category": "other", "title": "テスト：今日のA（その他）", "due_datetime": day(0) + "T23:59"},
    {"category": "assignment", "subject_id": subjects[0]["id"], "title": "テスト：7日後", "due_datetime": day(7) + "T23:59"},
    {"category": "assignment", "subject_id": subjects[0]["id"], "title": "テスト：8日後", "due_datetime": day(8) + "T00:00"},
    {"category": "assignment", "subject_id": subjects[0]["id"], "title": "テスト：完了した課題", "due_datetime": day(0) + "T22:00"},
]
created = [send("POST", "/api/tasks", task, 201) for task in tasks]
# 8番目を、完了にする。
send("PATCH", f"/api/tasks/{created[7]['id']}", {"is_completed": True}, 200)
print(f"今日：{today.isoformat()}（{WEEKDAYS[today.weekday()]}）")
print("授業のid：", [subject["id"] for subject in subjects])
print("課題・タスクのid：", [task["id"] for task in created])
print("未完了の件数：", len(client.get("/api/tasks?is_completed=false").get_json()))
for task in created:
    print(task["id"], task["due_datetime"], task["title"][:20])
EOF
```

期待する出力（T が 2026-10-21 の場合）：

```
今日：2026-10-21（水）
授業のid： [1, 2]
課題・タスクのid： [1, 2, 3, 4, 5, 6, 7, 8]
未完了の件数： 7
1 2026-10-18T23:59 テスト：期限切れの課題
2 2026-10-21T00:01 テスト：今日の朝の課題
3 2026-10-21T23:57 Report_xxxxxxxxxxxxx
4 2026-10-21T23:58 テスト：今日のB
5 2026-10-21T23:59 テスト：今日のA（その他）
6 2026-10-28T23:59 テスト：7日後
7 2026-10-29T00:00 テスト：8日後
8 2026-10-21T22:00 テスト：完了した課題
```

1行目の日付が、今日（T）。4行目から下は、課題・タスクのid・締切日時・タイトル（20文字まで）。2回目に実行すると、「中止：POST /api/semesters 400 …」で止まり、何も増えない（そのままでよい）。

以下、idは、この出力のとおり。

| 種類 | id：内容 |
|---|---|
| 学期 | 「2026年度 後期」（T−42〜T+42） |
| 授業 | 1：テスト：今日の曜日の授業（T と同じ曜日、13:00〜14:30、3号館201）、2：`Subject_` と `y` 60個（T の2日後と同じ曜日、09:00〜10:00。長い名前） |
| 課題・タスク | 1：テスト：期限切れの課題（授業1、T−3 23:59）、2：テスト：今日の朝の課題（授業1、T 00:01）、3：`Report_` と `x` 80個（授業2、T 23:57。長いタイトル）、4：テスト：今日のB（授業1、T 23:58、メモ2行）、5：テスト：今日のA（その他）（その他、T 23:59）、6：テスト：7日後（授業1、T+7 23:59）、7：テスト：8日後（授業1、T+8 00:00）、8：テスト：完了した課題（授業1、T 22:00、完了） |

T の締切のタイトルは、締切日時の順（朝の課題 → Report → B → A）と、タイトルの順（A → B → Report → 朝の課題）が違うようにしてある（締切日時の順に並ぶことを確かめるため）。

#### W. 週表示（ページを開いた状態から）

| No | 操作 | 期待する結果 |
|---|---|---|
| W1 | 画面を見る | 上部の絞り込みは、左から「授業」（青の見本）「課題」（オレンジ）「アルバイト」（緑）「その他」（グレー）。週表示で、時間軸の上に、見出し「締切」の行がある。T の列の締切の行に、上から ●（オレンジ）「テスト：今日の朝の課題」、●（オレンジ）「Report_xxx…」（列の幅で切れ、はみ出さない）、●（オレンジ）「テスト：今日のB」、●（グレー）「テスト：今日のA（その他）」（時刻は出ない）。「テスト：完了した課題」は出ない。T の列の13:00〜14:30に、青いブロック「テスト：今日の曜日の授業」。カレンダーの右に、「直近の締切」欄 |
| W2 | コンソールで、`[...document.querySelectorAll(".fc-timegrid .fc-daygrid-day")].map((day) => [day.dataset.date, [...day.querySelectorAll(".fc-event-title")].map((title) => title.textContent.slice(0, 12))]).filter((day) => day[1].length > 0)` と、`[...document.querySelectorAll(".fc-toolbar .fc-button")].map((button) => [button.textContent, button.title, button.getAttribute("aria-pressed")])` を実行する | 1つ目：`["2026-10-21", ["テスト：今日の朝の課題", "Report_xxxxx", "テスト：今日のB", "テスト：今日のA（その他"]]` を含む（T が水〜土曜日なら、その前に `["2026-10-18", ["テスト：期限切れの課題"]]` も）。2つ目：`[["", "前へ", "false"], ["", "次へ", "false"], ["今日", "今日を表示", "false"], ["週", "週表示", "true"], ["月", "月表示", "false"], ["一覧", "一覧表示", "false"]]` |

#### P. 「直近の締切」欄

| No | 操作 | 期待する結果 |
|---|---|---|
| P1 | 欄を見る | 見出し「直近の締切」と、小さく「期限切れと、今日から7日後までの、未完了の課題・タスク」。行は、上から ①「2026年10月18日（日） 23:59」と赤い「期限切れ」、「✅ テスト：期限切れの課題」、「テスト：今日の曜日の授業」 ②「2026年10月21日（水） 00:01」と「期限切れ」、「✅ テスト：今日の朝の課題」、「テスト：今日の曜日の授業」 ③「2026年10月21日（水） 23:57」、「✅ Report_xxx…」（欄の中で折り返す）、「Subject_yyy…」（折り返す） ④「2026年10月21日（水） 23:58」、「✅ テスト：今日のB」、「テスト：今日の曜日の授業」 ⑤「2026年10月21日（水） 23:59」、「⭐ テスト：今日のA（その他）」（対象授業の行はない） ⑥「2026年10月28日（水） 23:59」、「✅ テスト：7日後」、「テスト：今日の曜日の授業」。各行の左に、チェックボックス（チェックなし）。「テスト：8日後」（T+8）と「テスト：完了した課題」は出ない。欄の外に、文字がはみ出さない |
| P2 | コンソールで、`[...document.querySelectorAll("#calendar-deadline-list li")].map((item) => [item.querySelector("input").getAttribute("aria-label"), item.querySelector(".visually-hidden").textContent, item.querySelectorAll(".badge").length])` を実行する | `[["「テスト：期限切れの課題」（締切 2026年10月18日（日） 23:59）の完了", "課題：", 1], ["「テスト：今日の朝の課題」（締切 2026年10月21日（水） 00:01）の完了", "課題：", 1], ["「Report_xxx…（x が80個）」（締切 2026年10月21日（水） 23:57）の完了", "課題：", 0], ["「テスト：今日のB」（締切 2026年10月21日（水） 23:58）の完了", "課題：", 0], ["「テスト：今日のA（その他）」（締切 2026年10月21日（水） 23:59）の完了", "その他：", 0], ["「テスト：7日後」（締切 2026年10月28日（水） 23:59）の完了", "課題：", 0]]` |

#### M. 月表示

| No | 操作 | 期待する結果 |
|---|---|---|
| M1 | 「月」を押す | 「月」のボタンが押された状態。T の日付の中に、上から ●「テスト：今日の朝の課題」、●「Report_…」、●「テスト：今日のB」と「＋2件」（締切が、時間型の青いブロックより上。1日3件まで）。T+7 の日付に、●「テスト：7日後」と、その下に青いブロック「テスト：今日の曜日の授業」。T+8 の日付（同じ月の表示に入る場合）に、●「テスト：8日後」。T−3 の日付（同じ月の表示に入る場合）に、●「テスト：期限切れの課題」。授業の日に、青いブロック（時刻なし） |
| M2 | T の日付の「＋2件」を押す | T を含む週の週表示に移る。「週」のボタンが押された状態。締切の行は、W1と同じ |

#### V. 一覧表示（締切を出さない）

| No | 操作 | 期待する結果 |
|---|---|---|
| V1 | コンソールで、下の「V1のスクリプト」を実行する。そのあと、「一覧」を押す。コンソールで、`window.deadlineRows` と、`[...document.querySelectorAll(".fc-list-day-text")].map((day) => day.textContent)` を実行する | 一覧表示に、授業の行だけが並ぶ（「テスト：今日の曜日の授業」と「Subject_yyy…」。締切は出ない）。1つ目：`0`（一覧表示に、締切の行が一瞬も出ていない）。2つ目：T からの28日間の、授業のある日だけ（T、T+2、T+7、T+9、…）。T+8（2026年10月29日（木））の見出しはない（その日は、締切だけで、授業がないため） |
| V2 | 「次へ」「前へ」の順に押す。そのあと「週」を押し、もう一度「一覧」を押してから、「月」を押す。コンソールで、`window.deadlineRows` を実行する | 一覧表示の間は、締切が出ない。「週」に戻すと、締切の行が W1 と同じになり、「月」では M1 と同じ。結果は `0` |

V1のスクリプト（コンソールに、そのまま貼る。カレンダーの表示が変わるたびに、一覧表示の行のうち、授業（`category-class`）でない行を数える）：

```
window.deadlineRows = 0;
new MutationObserver(() => {
  const rows = [...document.querySelectorAll(".fc-list-event")];
  window.deadlineRows += rows.filter((row) => !row.classList.contains("category-class")).length;
}).observe(document.getElementById("calendar-view"), { childList: true, subtree: true });
```

#### F. 絞り込み（週表示で行う。「今日」を押して、T の週にしておく）

| No | 操作 | 期待する結果 |
|---|---|---|
| F1 | 「課題」のチェックを外す | T の列の締切の行が、●「テスト：今日のA（その他）」だけになる（T−3 の締切も消える）。青いブロックは残る。「直近の締切」欄は変わらない（6行） |
| F2 | 「その他」のチェックも外す | 締切の行が空になる（「締切」の見出しの行は残る）。欄は変わらない |
| F3 | 「課題」と「その他」のチェックを戻す | W1と同じ表示に戻る |

#### D. 締切の詳細パネル

| No | 操作 | 期待する結果 |
|---|---|---|
| D1 | 締切の行の「テスト：今日のB」を押す | パネルが開く。見出し「テスト：今日のB」。上から、カテゴリ「✅ 課題」、締切「2026年10月21日（水） 23:58」（期限切れの印なし）、対象授業「テスト：今日の曜日の授業」、詳細・メモ「メモ1行目」「メモ2行目」（2行）。その下に「完了」のチェックボックス（チェックなし）。ボタンは「閉じる」だけ |
| D2 | 「完了」のチェックボックスを押す。コンソールで、`[document.activeElement.id, document.getElementById("task-detail-completed").disabled]` を実行する | パネルは開いたまま。チェックが入る。締切の行から「テスト：今日のB」が消え、欄が5行になる（④が消える）。結果は `["task-detail-completed", false]` |
| D3 | もう一度「完了」のチェックボックスを押す（チェックを外す） | 締切の行の「テスト：今日のB」が、「Report_…」と「テスト：今日のA（その他）」の間に戻る。欄が6行に戻る |
| D4 | Escapeキーを押す | パネルが閉じる（保存のあとも、Escapeキーで閉じられる。017-N2がこのパネルで起きないこと） |
| D5 | 締切の行の「テスト：今日の朝の課題」を押す。「完了」を押し、もう一度押す。最後に「閉じる」を押す | 開いたとき、締切「2026年10月21日（水） 00:01」の横に赤い「期限切れ」。詳細・メモの行はない。完了にすると「期限切れ」の印が消え、チェックを外すと、また出る。「閉じる」で閉じる |
| D6 | 締切の行の「テスト：今日のA（その他）」を押す。右上の×を押す | カテゴリ「⭐ その他」。対象授業の行と、詳細・メモの行はない。期限切れの印もない。×で閉じる |
| D7 | 締切の行の「Report_…」を押す。コンソールで、`["task-detail-modal-title", "task-detail-subject"].map((id) => { const element = document.getElementById(id); return element.scrollWidth <= element.clientWidth; })` を実行する。「閉じる」を押す | 見出しと対象授業が、パネルの中で折り返す（はみ出さない）。結果は `[true, true]` |

#### P（続き）. 欄の完了の切り替え

| No | 操作 | 期待する結果 |
|---|---|---|
| P3 | 欄の「テスト：期限切れの課題」のチェックボックスを押す | 確認は出ない。欄から、その行が消える（5行）。T−3 の締切が週表示に出ていた場合は、それも消える |
| P4 | 画面下の「課題・タスク」を押す。完了の表の「テスト：期限切れの課題」のチェックを外す。画面下の「カレンダー」を押す | 課題・タスクモードの完了の表に「テスト：期限切れの課題」がある（チェックを外すと、未完了の表に戻る）。カレンダーに戻ると、欄が P1 と同じ6行に戻る |
| P5 | **Komaが、確認用のサーバーを止める（Ctrl＋C）。** Claudeが、欄の「テスト：7日後」のチェックボックスを押す | 欄の上部に、赤い枠で「サーバーに接続できませんでした。時間をおいて、もう一度お試しください」。チェックは外れたまま（元に戻る）で、押せる。行は残る |
| P6 | （サーバーは止めたまま）画面下の「課題・タスク」を押し、もう一度「カレンダー」を押す | 欄に、赤い枠で「サーバーに接続できませんでした。時間をおいて、もう一度お試しください」と「再読み込み」ボタン（行は出ない。P5の赤い枠は消えている）。カレンダーの上にも、同じメッセージと「再読み込み」。カレンダーの締切の行は、それまでのものが残る |
| P7 | **Komaが、「確認用のサーバーの起動」のコマンドで、確認用のサーバーを起動し直す**（ターミナルで↑キーを押すと、前のコマンドを呼び出せる）。Claudeが、欄の「再読み込み」を押し、次に、カレンダーの上の「再読み込み」を押す | 欄が、P1 と同じ6行に戻る。カレンダーの上の赤い枠が消える |

#### D（続き）. 締切の詳細パネルの失敗

| No | 操作 | 期待する結果 |
|---|---|---|
| D8 | コンソールで、`(await fetch("/api/tasks/5", { method: "DELETE" })).status` を実行する（ほかの場所で削除された場合の再現。確認用のデータに限る）。そのあと、締切の行に残っている「テスト：今日のA（その他）」を押し、「完了」のチェックボックスを押す。コンソールで、`document.activeElement.id` を実行する | 1つ目：`204`。パネルの上部に、赤い枠で「課題・タスクが見つかりません」。チェックは外れたまま（元に戻る）で、押せる。パネルは開いたまま。2つ目：`"task-detail-completed"` |
| D9 | Escapeキーでパネルを閉じる。画面下の「課題・タスク」を押し、もう一度「カレンダー」を押す | 締切の行と欄から、「テスト：今日のA（その他）」が消える（欄は5行） |

#### E. 予定の詳細パネル（変わらないこと）

| No | 操作 | 期待する結果 |
|---|---|---|
| E1 | 「一覧」を押し、「Subject_yyy…」の行を押す。コンソールで、`(() => { const title = document.getElementById("event-modal-title"); return title.scrollWidth <= title.clientWidth; })()` を実行する。「閉じる」を押し、「週」を押す | 予定の詳細パネルが開く（カテゴリ「📖 授業」、日付、時間「09:00 〜 10:00」。教室の行はない）。見出しがパネルの中で折り返す。結果は `true` |

#### L. 取得のあとの例外の表示（013-L1）

| No | 操作 | 期待する結果 |
|---|---|---|
| L1 | コンソールで、下の「L1のスクリプト」を実行する（予定APIの応答を、ブラウザの中だけで、形の違う `[null]` に置き換える。サーバーとDBは変わらない）。そのあと、「次へ」を押す | カレンダーの上に、赤い枠で「予期しないエラーが発生しました。ページを再読み込みして、もう一度お試しください」と「再読み込み」。コンソールに、`TypeError`（`Cannot read properties of null`）の記録（`console.error`。013-L1の前は、どちらも出なかった） |
| L2 | ページを強制再読み込みする | 置き換えが消え、W1と同じ表示（欄は5行。「テスト：今日のA（その他）」は D8 で削除した）。赤い枠はない |

L1のスクリプト（コンソールに、そのまま貼る）：

```
const originalFetch = window.fetch;
window.fetch = async (url, options) => {
  if (String(url).startsWith("/api/events")) {
    return new Response("[null]", { status: 200, headers: { "Content-Type": "application/json" } });
  }
  return originalFetch(url, options);
};
```

#### T. 課題・タスクモード（017-L1と、変わらないこと）

| No | 操作 | 期待する結果 |
|---|---|---|
| T1 | 画面下の「課題・タスク」を押す | 未完了の表は、上から「テスト：期限切れの課題」（期限切れ）、「テスト：今日の朝の課題」（期限切れ）、「Report_xxx…」、「テスト：今日のB」（その下にメモ2行）、「テスト：7日後」、「テスト：8日後」の6行。完了の表は「テスト：完了した課題」の1行（チェックあり、期限切れの印なし）。「Report_xxx…」と「Subject_yyy…」が、それぞれのセルの中で折り返し、右の「対象授業」「操作」の列にはみ出さない。アイコン・期限切れの印・「編集」「削除」のボタンは、Task 017と同じ |
| T2 | コンソールで、`[...document.querySelectorAll("#task-incomplete-body tr, #task-completed-body tr")].filter((row) => [...row.children].some((cell) => cell.scrollWidth > cell.clientWidth + 1)).length` と、`[...document.querySelectorAll("#task-incomplete-body tr:first-child input, #task-incomplete-body tr:first-child button")].map((element) => element.getAttribute("aria-label"))` を実行する | 1つ目：`0`（はみ出すセルがない。017-L1の前は、`1`）。2つ目：`["「テスト：期限切れの課題」（締切 2026年10月18日（日） 23:59）の完了", "「テスト：期限切れの課題」（締切 2026年10月18日（日） 23:59）を編集", "「テスト：期限切れの課題」（締切 2026年10月18日（日） 23:59）を削除"]` |
| T3 | 1行目の「削除」を押す。「キャンセル」を押す | 削除の確認のモーダルに、「「テスト：期限切れの課題」（締切 2026年10月18日（日） 23:59）を削除します。」と「削除は取り消せません。」。「キャンセル」で閉じる（削除しない） |
| T4 | ブラウザの表示の幅を760pxにする。T2の1つ目を、もう一度実行する。画面下の「カレンダー」を押し、コンソールで、`document.getElementById("calendar-deadline-panel").getBoundingClientRect().top >= document.getElementById("calendar-view").getBoundingClientRect().bottom - 1` を実行する。幅を元に戻す | 1つ目：`0`。2つ目：`true`（幅が992px未満では、「直近の締切」欄がカレンダーの下に出る） |

#### X. 確認の全体を通して

| No | 確認 | 期待する結果 |
|---|---|---|
| X1 | コンソール | JavaScriptの例外（`Uncaught …`）が出ていない。想定した記録（D8の404の「Failed to load resource」、サーバーを止めている間（P5・P6）の接続の失敗（`net::ERR_CONNECTION_REFUSED`）、L1の `TypeError` の `console.error`）は、除く（010-N1） |

#### 後片付け
1. 確認用のサーバーを止める（Ctrl＋C）
2. 確認用のDBのフォルダを消す
   ```
   rm -r /tmp/schedule-app-check-018
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
| ブラウザで開き、強制再読み込みする | 週表示に「締切」の行（空）。「直近の締切」欄に「直近の締切はありません」。絞り込みは「授業」「課題」「アルバイト」「その他」。コンソールに、JavaScriptの例外がない |
| 最後のハッシュ | 起動の前と同じ |

### 5. マージ
1〜4が期待どおりで、レビューで承認されたら、マージする。このタスクは、DBの構造を変えないため、開発用DBへのmigrationの適用はない。開発用DBのデータも変えないため、バックアップは要らない。

## Git操作
**Git commit / push / ブランチ操作 / マージは行わない**（`git branch --show-current`、`git status`、`git diff` のような読み取りだけのコマンドは除く）。

## 注意
- **停止して報告する条件**（ファイルを変更せず、実装を止め、チャットで「問題点・発生理由・変更した場合の影響・推奨案（必要なら）」を報告する）
  - ブランチの不一致、作業ツリーの想定外の変更
  - 設計資料が更新されていない（実装手順の1）、または、設計資料とこのTask MDの間に、矛盾・不足がある
  - 設計資料にない判断が必要になった（特に、`docs/architecture.md` の「未決定事項」や、`docs/ui_ux.md` の「未決定」に触れる場合）
  - 「全文からファイルを作るスクリプト」の出力が、期待と違う（全文の数・行数・エラー）
  - 「変更しない」と定めたもの（Pythonのファイル、テスト、ほかのJavaScriptのファイル、`base.html`、`style.css` など）を変更しないと実装できない。または、5ファイルの全文を変える必要があると判断した
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
- **最後の報告には、次を含め、コマンドの出力は、要約せずに、そのまま貼る**（014-L1）：変更・新規のファイル、「全文からファイルを作るスクリプト」の出力（段階1・2）、作業の前と各段階の `pytest` の件数と警告（最後の行）、1行の長さの確認の出力、全文との比較の出力（段階1：3ファイル、段階2：5ファイルの「一致」。スクリプトで全文に戻した場合は、そのこと）、画面のHTMLの確認の出力、検索と差分の出力（各コマンドと、その出力）、開発用DBの前後のハッシュ・件数、`git status`・`git diff --stat` の出力、コマンドを書き換えた場合は、その箇所と理由（016-N1・017-N1）、サーバーの起動とブラウザでの確認をしていないこと、気になった点

## 付録：全文
「全文からファイルを作るスクリプト」と「全文との比較」が使う。各ファイルの全文は、「`<!-- 全文: パス -->`」の印の行の直後のコードブロック。**この付録を、手で書き写さない。** 本文の要点・差分と食い違う場合は、作業をせずに停止して報告する。

### 付録A. `app/static/js/task_display.js`

<!-- 全文: app/static/js/task_display.js -->
```javascript
import { taskCategoryOf } from "./categories.js";
import { formatJapaneseDateTime } from "./dates.js";

// 課題・タスクの表示の共通処理。課題・タスクモード（tasks.js）と、
// カレンダーの「直近の締切」欄（calendar.js）で使う（モードのファイル同士は、
// 互いを import しないため、このファイルにまとめる）。APIは扱わない。

// 課題・タスクを表す文字列（例：「レポート第1回」（締切 2026年10月20日（火）
// 23:59））。読み上げの名前（aria-label）と、削除の確認の文に使う。同じ
// タイトルの課題・タスクを、締切で区別できるようにする。
export function taskLabel(task) {
  return (
    `「${task.title}」` +
    `（締切 ${formatJapaneseDateTime(task.due_datetime)}）`
  );
}

// 期限切れかを返す。未完了で、締切日時が now（今の日時。YYYY-MM-DDTHH:MM。
// dates.js の localDateTimeString）より前なら、期限切れ。締切日時と同じ分は、
// まだ期限切れではない。YYYY-MM-DDTHH:MMは桁が固定されているため、文字列の
// 大小で前後を比べられる。
export function isTaskOverdue(task, now) {
  return !task.is_completed && task.due_datetime < now;
}

// 期限切れの印（赤い「期限切れ」）を作る。
export function createOverdueBadge() {
  const badge = document.createElement("span");
  badge.className = "badge text-bg-danger ms-1";
  badge.textContent = "期限切れ";
  return badge;
}

// 課題名の表示（カテゴリのアイコンと、課題名）を作る。アイコンは読み上げず、
// 代わりに、カテゴリの表示名（「課題：」など）を、見えない文字で添える。
export function createTaskTitle(task) {
  const category = taskCategoryOf(task.category);
  const title = document.createElement("div");

  const icon = document.createElement("span");
  icon.className = "me-1";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = category.icon;

  const categoryName = document.createElement("span");
  categoryName.className = "visually-hidden";
  categoryName.textContent = `${category.label}：`;

  title.append(icon, categoryName, task.title);
  return title;
}
```

### 付録B. `app/static/js/tasks.js`

<!-- 全文: app/static/js/tasks.js -->
```javascript
import { apiRequest } from "./api.js";
import { chooseCurrentSemester } from "./current_semester.js";
import {
  formatJapaneseDateTime,
  localDateString,
  localDateTimeString,
} from "./dates.js";
import {
  createOverdueBadge,
  createTaskTitle,
  isTaskOverdue,
  taskLabel,
} from "./task_display.js";
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

// 一覧の1行を作る。now は、期限切れの判定に使う今の日時
// （YYYY-MM-DDTHH:MM）。
function createTaskRow(task, now) {
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
  if (isTaskOverdue(task, now)) {
    dueCell.append(createOverdueBadge());
  }
  row.append(dueCell);

  // 課題名と対象授業のセルは、区切れる場所のない長い文字列（空白のない
  // 長いURLなど）も、折り返す（右の列にはみ出さないため。017-L1）。
  const titleCell = document.createElement("td");
  titleCell.className = "text-break";
  titleCell.append(createTaskTitle(task));
  if (task.notes !== null) {
    const notes = document.createElement("div");
    notes.className = "text-muted small text-pre-wrap";
    notes.textContent = task.notes;
    titleCell.append(notes);
  }
  row.append(titleCell);

  const subjectCell = document.createElement("td");
  subjectCell.className = "text-break";
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
function renderTaskTable(tasks, { bodyId, listId, emptyId, now }) {
  const fragment = document.createDocumentFragment();
  for (const task of tasks) {
    fragment.append(createTaskRow(task, now));
  }
  getElement(bodyId).replaceChildren(fragment);
  setVisible(getElement(emptyId), tasks.length === 0);
  setVisible(getElement(listId), tasks.length > 0);
}

// 一覧を、未完了と完了の2つの表に分けて表示する。APIの並びは、締切日時の
// 早い順。未完了は、そのまま（期限切れが上に来る）。完了は、逆にして、
// 締切日時の新しい順にする。期限切れは、表示するときの日時で判定する
// （完了の表には、期限切れの印は付かない）。
function renderTasks(tasks) {
  const incomplete = tasks.filter((task) => !task.is_completed);
  const completed = tasks.filter((task) => task.is_completed).reverse();
  const now = localDateTimeString();

  renderTaskTable(incomplete, {
    bodyId: "task-incomplete-body",
    listId: "task-incomplete-list",
    emptyId: "task-incomplete-empty",
    now,
  });
  renderTaskTable(completed, {
    bodyId: "task-completed-body",
    listId: "task-completed-list",
    emptyId: "task-completed-empty",
    now,
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

### 付録C. `app/static/js/categories.js`

<!-- 全文: app/static/js/categories.js -->
```javascript
// カテゴリの対応表。DBの保存値（APIの category）から、画面に出す
// 表示名・アイコン・色のclassを引く。複数のモードで使うため、
// このファイルにまとめる（モードのファイル同士は、互いを import しない）。
// 色の値は、style.css の、className と同じ名前のclassに書く
// （JavaScriptでは、色の値を持たない）。

// 予定（Event）のカテゴリ。並びは、app/categories.py の EVENT_CATEGORIES と
// 同じ（カレンダーの絞り込みの選択肢の並びは、calendar.js で決める）。
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

### 付録D. `app/templates/index.html`

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

### 付録E. `app/static/js/calendar.js`

<!-- 全文: app/static/js/calendar.js -->
```javascript
import { ApiError, apiRequest } from "./api.js";
import {
  EVENT_CATEGORIES,
  TASK_CATEGORIES,
  eventCategoryOf,
  taskCategoryOf,
} from "./categories.js";
import {
  formatJapaneseDateTime,
  formatJapaneseDateWithWeekday,
  localDateString,
  localDateTimeString,
} from "./dates.js";
import {
  createOverdueBadge,
  createTaskTitle,
  isTaskOverdue,
  taskLabel,
} from "./task_display.js";
import { errorMessageOf, getElement, setVisible } from "./ui.js";

// 表示の種類（FullCalendarの表示の名前）。
const WEEK_VIEW = "timeGridWeek";
const MONTH_VIEW = "dayGridMonth";
const LIST_VIEW = "listFourWeeks";
// 一覧表示の期間の日数（今日から4週間）。前後への移動も、この日数ずつ。
const LIST_DAYS = 28;
// 「直近の締切」欄に載せる範囲。期限切れと、締切日が今日からこの日数後
// までのもの（来週の同じ曜日の締切まで入る）。欄の説明の文（index.html）の
// 日数と合わせる。
const UPCOMING_DAYS = 7;
// 締切の取得元（FullCalendarの eventSources）のid。
const DEADLINE_SOURCE_ID = "deadlines";
// 絞り込みの選択肢（保存値と、カテゴリの対応表の項目）。並びは、授業・
// 課題・アルバイト・その他。その他は、予定（時間指定あり）と課題・タスク
// （締切のみ）で保存値が同じ（"other"）のため、1つの選択肢で両方を
// 切り替える。
const FILTER_CATEGORIES = [
  ["class", EVENT_CATEGORIES.class],
  ["assignment", TASK_CATEGORIES.assignment],
  ["part_time", EVENT_CATEGORIES.part_time],
  ["other", EVENT_CATEGORIES.other],
];
// 一覧表示の行で、タイトルの横に出す主要項目（カテゴリの保存値 → 予定の項目）。
const LIST_DETAIL_FIELDS = new Map([
  ["class", "room"],
  ["part_time", "employer"],
]);
const LIBRARY_ERROR_MESSAGE =
  "カレンダーの部品を読み込めませんでした。" +
  "ネットワークの接続を確かめて、ページを再読み込みしてください";

let calendar = null;
// 絞り込みで外したカテゴリの保存値。初期状態は、すべてのカテゴリを表示する。
const hiddenCategories = new Set();
// 予定の取得の通し番号。古い取得の結果で、今の表示（エラーの表示）を
// 変えないために使う（古い取得の予定は、FullCalendarが捨てる）。
let requestSerial = 0;
// 未完了の課題・タスク（課題・タスクAPIの一覧。締切日時・idの昇順）。
// カレンダーの締切と、「直近の締切」欄で使う。
let incompleteTasks = [];
// 課題・タスクの取得の通し番号（古い応答で、今の表示を変えないため）。
let taskRequestSerial = 0;
// カレンダーに締切を出すか。一覧表示では出さない（期限型は載せないため）。
let deadlinesShown = true;
// 課題・タスクの詳細パネルの対象（課題・タスクのコピー）と、開いたときの
// 日時（期限切れの判定に使う）。開くたびに増やす通し番号は、閉じて開き
// 直したあとに届いた古い応答で、今の表示を変えないために使う。
let detailTask = null;
let detailOpenedAt = "";
let detailSerial = 0;

function showLoadError(error) {
  getElement("calendar-load-error-message").textContent =
    errorMessageOf(error);
  setVisible(getElement("calendar-load-error"), true);
}

function hideLoadError() {
  setVisible(getElement("calendar-load-error"), false);
}

// FullCalendarの期間（終わりの日を含まない Date）を、予定APIの期間
// （両端を含む YYYY-MM-DD）にする。終わりの日は、その前の日にする。
function toApiRange(start, end) {
  // 日に0を渡すと、前の月の最後の日になる（月をまたいでも正しい）。
  const lastDate = new Date(
    end.getFullYear(),
    end.getMonth(),
    end.getDate() - 1,
  );
  return {
    startDate: localDateString(start),
    endDate: localDateString(lastDate),
  };
}

// 予定APIの予定を、FullCalendarの予定の形にする。日時は、タイムゾーンの
// ない「YYYY-MM-DDTHH:MM」で渡す（ブラウザのローカルの日時として読まれる）。
function toCalendarEvent(apiEvent) {
  const category = eventCategoryOf(apiEvent.category);
  return {
    id: String(apiEvent.id),
    title: apiEvent.title,
    start: `${apiEvent.date}T${apiEvent.start_time}`,
    end: `${apiEvent.date}T${apiEvent.end_time}`,
    classNames: category.className === "" ? [] : [category.className],
    // 詳細パネルと一覧表示で使うため、APIの予定のコピーを持たせる。
    extendedProps: { apiEvent: { ...apiEvent } },
  };
}

// FullCalendarが、表示する期間が変わるたびと、refetchEvents() のたびに
// 呼ぶ。予定APIから期間の予定を取得し、絞り込みで外したカテゴリを除く。
async function fetchEvents(fetchInfo) {
  requestSerial += 1;
  const serial = requestSerial;
  const { startDate, endDate } = toApiRange(fetchInfo.start, fetchInfo.end);
  const query = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
  });

  let apiEvents;
  try {
    apiEvents = await apiRequest("GET", `/api/events?${query}`);
  } catch (error) {
    if (serial === requestSerial) {
      showLoadError(error);
    }
    // FullCalendarに、取得の失敗を伝える。
    throw error;
  }

  if (serial === requestSerial) {
    hideLoadError();
  }
  return apiEvents
    .filter((apiEvent) => !hiddenCategories.has(apiEvent.category))
    .map(toCalendarEvent);
}

// 課題・タスクを、FullCalendarの締切（締切日の終日の予定）にする。週表示の
// 「締切」の行（終日の行）と、月表示の日付の中に、●の印とタイトルで出す。
function toDeadlineEvent(task) {
  const category = taskCategoryOf(task.category);
  const [dueDate] = task.due_datetime.split("T");
  return {
    id: `task-${task.id}`,
    title: task.title,
    start: dueDate,
    allDay: true,
    // ●の印で表示する（時間型の予定は、カレンダー全体の eventDisplay の
    // "block"。色のブロック）。
    display: "list-item",
    classNames: category.className === "" ? [] : [category.className],
    // dueDateTime は、同じ日の締切を、締切日時の順に並べるため（eventOrder）。
    // 詳細パネルで使うため、課題・タスクのコピーを持たせる。
    extendedProps: {
      dueDateTime: task.due_datetime,
      apiTask: { ...task },
    },
  };
}

// 締切の取得元。FullCalendarが、表示する期間が変わるたびと、refetch の
// たびに呼ぶ。課題・タスクは loadDeadlines で取得済みのため、APIは呼ばず、
// すぐに結果を返す（async にせず、successCallback を呼ぶ。待つ間に描画が
// 入らないようにするため）。一覧表示と、絞り込みで外したカテゴリの締切は
// 出さない。
function fetchDeadlines(fetchInfo, successCallback, failureCallback) {
  let deadlineEvents;
  try {
    deadlineEvents = deadlinesShown
      ? incompleteTasks
          .filter((task) => !hiddenCategories.has(task.category))
          .map(toDeadlineEvent)
      : [];
  } catch (error) {
    // 形の変換の例外も、FullCalendarに失敗として伝える（eventSourceFailure）。
    failureCallback(error);
    return;
  }
  successCallback(deadlineEvents);
}

function refetchDeadlines() {
  calendar.getEventSourceById(DEADLINE_SOURCE_ID).refetch();
}

// 表示を切り替える（週・月・一覧のボタン）。一覧表示では、締切を出さない。
// 一覧表示に、締切が一瞬でも出ないように、一覧表示へは、締切を外してから
// 切り替え、週・月の表示へは、切り替えてから締切を戻す（どちらも、同じ
// 処理の中で続けて行うため、画面に出るのは、最後の状態だけ）。
function switchView(viewType) {
  if (viewType === LIST_VIEW) {
    deadlinesShown = false;
    refetchDeadlines();
    calendar.changeView(viewType);
    return;
  }
  calendar.changeView(viewType);
  deadlinesShown = true;
  refetchDeadlines();
}

// 一覧表示の行の、タイトルの欄の中身。アイコン・タイトルと、カテゴリごとの
// 主要項目（授業＝教室、アルバイト＝派遣会社）を、textContent で作る。
function renderListEventContent(arg) {
  const apiEvent = arg.event.extendedProps.apiEvent;
  const category = eventCategoryOf(apiEvent.category);

  const icon = document.createElement("span");
  icon.className = "me-1";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = category.icon;

  const title = document.createElement("span");
  title.textContent = apiEvent.title;

  const nodes = [icon, title];
  const detailField = LIST_DETAIL_FIELDS.get(apiEvent.category);
  if (detailField !== undefined && apiEvent[detailField] !== null) {
    const detail = document.createElement("span");
    detail.className = "ms-2 text-muted small";
    detail.textContent = apiEvent[detailField];
    nodes.push(detail);
  }
  return { domNodes: nodes };
}

// 詳細パネルの1行（教室・派遣会社・対象授業・メモ）。値がなければ、行ごと
// 隠す。
function setDetailRow(rowId, valueId, value) {
  getElement(valueId).textContent = value ?? "";
  setVisible(getElement(rowId), value !== null);
}

// 予定の詳細パネルを開く（読み取りだけ。閉じるのは、利用者のボタンだけ）。
function showEventDetail(apiEvent) {
  const category = eventCategoryOf(apiEvent.category);
  getElement("event-modal-title").textContent = apiEvent.title;
  getElement("event-modal-category-icon").textContent = category.icon;
  getElement("event-modal-category").textContent = category.label;
  getElement("event-modal-date").textContent =
    formatJapaneseDateWithWeekday(apiEvent.date);
  getElement("event-modal-time").textContent =
    `${apiEvent.start_time} 〜 ${apiEvent.end_time}`;
  setDetailRow("event-modal-room-row", "event-modal-room", apiEvent.room);
  setDetailRow(
    "event-modal-employer-row",
    "event-modal-employer",
    apiEvent.employer,
  );
  setDetailRow("event-modal-notes-row", "event-modal-notes", apiEvent.notes);

  const modal = window.bootstrap.Modal.getOrCreateInstance(
    getElement("event-modal"),
  );
  modal.show();
}

function showDeadlineLoading() {
  setVisible(getElement("calendar-deadline-loading"), true);
  setVisible(getElement("calendar-deadline-load-error"), false);
  setVisible(getElement("calendar-deadline-content"), false);
}

function showDeadlineLoadError(error) {
  getElement("calendar-deadline-load-error-message").textContent =
    errorMessageOf(error);
  setVisible(getElement("calendar-deadline-loading"), false);
  setVisible(getElement("calendar-deadline-load-error"), true);
  setVisible(getElement("calendar-deadline-content"), false);
}

function showDeadlineActionError(error) {
  const actionError = getElement("calendar-deadline-action-error");
  actionError.textContent = errorMessageOf(error);
  setVisible(actionError, true);
}

function hideDeadlineActionError() {
  const actionError = getElement("calendar-deadline-action-error");
  actionError.replaceChildren();
  setVisible(actionError, false);
}

// 「直近の締切」欄の1行（完了のチェックボックス、締切と期限切れの印、
// アイコンと課題名、対象授業）。now は、期限切れの判定に使う今の日時。
function createDeadlineItem(task, now) {
  const item = document.createElement("li");
  item.className = "d-flex gap-2 py-2 border-top";

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.id = `calendar-deadline-complete-${task.id}`;
  checkbox.className = "form-check-input flex-shrink-0 mt-1";
  checkbox.setAttribute("aria-label", `${taskLabel(task)}の完了`);
  checkbox.addEventListener("change", () => {
    toggleDeadlineCompleted(task, checkbox);
  });

  // 区切れる場所のない長い文字列も、欄の中で折り返す。
  const body = document.createElement("div");
  body.className = "text-break";

  const due = document.createElement("div");
  due.className = "small";
  due.textContent = formatJapaneseDateTime(task.due_datetime);
  if (isTaskOverdue(task, now)) {
    due.append(createOverdueBadge());
  }
  body.append(due, createTaskTitle(task));

  if (task.subject_name !== null) {
    const subject = document.createElement("div");
    subject.className = "small text-muted";
    subject.textContent = task.subject_name;
    body.append(subject);
  }

  item.append(checkbox, body);
  return item;
}

// 「直近の締切」欄を作り直す。期限切れと、締切日が今日から UPCOMING_DAYS
// 日後までの未完了を、締切日時の順（APIの並び）に並べる。カテゴリの
// 絞り込みの影響を受けない。今日と期限切れは、作り直すときの、ブラウザの
// 日付・時刻で決める。
function renderDeadlinePanel() {
  const now = new Date();
  const lastDate = localDateString(
    new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate() + UPCOMING_DAYS,
    ),
  );
  const nowText = localDateTimeString(now);
  // 期限切れ（締切日時が今より前）は、締切日が今日以前のため、すべて入る。
  const tasks = incompleteTasks.filter(
    (task) => task.due_datetime.split("T")[0] <= lastDate,
  );

  const fragment = document.createDocumentFragment();
  for (const task of tasks) {
    fragment.append(createDeadlineItem(task, nowText));
  }
  getElement("calendar-deadline-list").replaceChildren(fragment);
  setVisible(getElement("calendar-deadline-empty"), tasks.length === 0);
  setVisible(getElement("calendar-deadline-list"), tasks.length > 0);
  setVisible(getElement("calendar-deadline-loading"), false);
  setVisible(getElement("calendar-deadline-load-error"), false);
  setVisible(getElement("calendar-deadline-content"), true);
}

// 未完了の課題・タスクを取得し、「直近の締切」欄と、カレンダーの締切を
// 作り直す。失敗したときは、欄に、エラーと「再読み込み」を出す（カレンダーの
// 締切は、それまでに表示していたものが残る）。
async function loadDeadlines({ showLoading = true } = {}) {
  const currentRequest = ++taskRequestSerial;
  if (showLoading) {
    showDeadlineLoading();
  }

  let tasks;
  try {
    tasks = await apiRequest("GET", "/api/tasks?is_completed=false");
  } catch (error) {
    // 新しい取得を始めていたら、古い取得の結果で、画面を変えない。
    if (currentRequest !== taskRequestSerial) {
      return;
    }
    showDeadlineLoadError(error);
    return;
  }

  if (currentRequest !== taskRequestSerial) {
    return;
  }
  incompleteTasks = tasks;
  renderDeadlinePanel();
  refetchDeadlines();
}

// 「直近の締切」欄の完了の切り替え（チェックボックス）。確認は出さない。
// 成功したら、取得し直す（完了にしたものは、欄とカレンダーから消える）。
// 失敗したら、チェックを元に戻し、エラーを欄の上部に出す。
async function toggleDeadlineCompleted(task, checkbox) {
  hideDeadlineActionError();
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
    showDeadlineActionError(error);
    return;
  }

  await loadDeadlines({ showLoading: false });
}

// 課題・タスクの詳細パネルを開く（カレンダーの締切のクリック）。値は、
// 開くとき（show.bs.modal）に入れる。閉じるのは、利用者のボタンだけ。
function showTaskDetail(apiTask) {
  detailTask = { ...apiTask };
  window.bootstrap.Modal.getOrCreateInstance(
    getElement("task-detail-modal"),
  ).show();
}

// 詳細パネルの期限切れの印を、今の完了の状態に合わせる（判定の日時は、
// 開いたとき）。
function updateDetailOverdue() {
  setVisible(
    getElement("task-detail-overdue"),
    isTaskOverdue(detailTask, detailOpenedAt),
  );
}

function showDetailError(error) {
  const detailError = getElement("task-detail-error");
  detailError.textContent = errorMessageOf(error);
  setVisible(detailError, true);
}

function hideDetailError() {
  const detailError = getElement("task-detail-error");
  detailError.replaceChildren();
  setVisible(detailError, false);
}

// 詳細パネルを開くたびに、対象の値を表示し、エラーを消す。
function prepareTaskDetail() {
  detailSerial += 1;
  detailOpenedAt = localDateTimeString();
  const task = detailTask;
  const category = taskCategoryOf(task.category);

  getElement("task-detail-modal-title").textContent = task.title;
  getElement("task-detail-category-icon").textContent = category.icon;
  getElement("task-detail-category").textContent = category.label;
  getElement("task-detail-due").textContent = formatJapaneseDateTime(
    task.due_datetime,
  );
  updateDetailOverdue();
  setDetailRow(
    "task-detail-subject-row",
    "task-detail-subject",
    task.subject_name,
  );
  setDetailRow("task-detail-notes-row", "task-detail-notes", task.notes);

  const checkbox = getElement("task-detail-completed");
  checkbox.checked = task.is_completed;
  checkbox.disabled = false;
  hideDetailError();
}

// 詳細パネルの完了の切り替え（チェックボックス）。確認は出さない。パネルは
// 開いたまま（チェックを外せば、未完了に戻せる）。保存が終わったら、
// チェックボックスを押せるように戻し、フォーカスを戻す（押せなくしたときに、
// フォーカスがページ本体に移り、Escapeキーでパネルを閉じられなくなるため。
// 017-N2）。カレンダーの締切と「直近の締切」欄は、取得し直す。
async function toggleDetailCompleted() {
  // 応答が届くまでに、パネルを開き直したかを確かめるために控える。
  const startedSerial = detailSerial;
  const task = detailTask;
  const checkbox = getElement("task-detail-completed");
  const completed = checkbox.checked;
  hideDetailError();
  checkbox.disabled = true;

  // try で囲むのは、切り替えの要求だけにする。
  try {
    await apiRequest("PATCH", `/api/tasks/${task.id}`, {
      is_completed: completed,
    });
  } catch (error) {
    // パネルを開き直していたら、今のパネルの表示を変えない。
    if (startedSerial === detailSerial) {
      checkbox.checked = !completed;
      checkbox.disabled = false;
      checkbox.focus();
      showDetailError(error);
    }
    return;
  }

  if (startedSerial === detailSerial) {
    task.is_completed = completed;
    updateDetailOverdue();
    checkbox.disabled = false;
    checkbox.focus();
  }
  await loadDeadlines({ showLoading: false });
}

// 絞り込みの選択肢を、カテゴリの対応表から作る（表示名を1か所で持つため）。
function renderFilter() {
  const fragment = document.createDocumentFragment();

  for (const [code, category] of FILTER_CATEGORIES) {
    const item = document.createElement("div");
    item.className = "form-check form-check-inline me-0";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "form-check-input";
    checkbox.id = `calendar-filter-${code}`;
    checkbox.checked = true;
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        hiddenCategories.delete(code);
      } else {
        hiddenCategories.add(code);
      }
      // fetchEvents・fetchDeadlines が、今の絞り込みで選び直すように、
      // 取得し直す。
      calendar.refetchEvents();
    });

    const label = document.createElement("label");
    label.className = "form-check-label";
    label.htmlFor = checkbox.id;
    const swatch = document.createElement("span");
    swatch.className = `category-swatch ${category.className} me-1`;
    swatch.setAttribute("aria-hidden", "true");
    label.append(swatch, category.label);

    item.append(checkbox, label);
    fragment.append(item);
  }

  getElement("calendar-filter").replaceChildren(fragment);
}

export function initCalendar() {
  // FullCalendarは、base.html の通常のスクリプトで、このファイルより先に
  // 読み込まれる。読み込めなかった場合（ネットワークにつながらないなど）は、
  // ほかのモードを止めないように、例外にせず、メッセージだけを出す
  // （「直近の締切」欄も出さない）。
  if (window.FullCalendar === undefined) {
    getElement("calendar-load-error-message").textContent =
      LIBRARY_ERROR_MESSAGE;
    setVisible(getElement("calendar-retry-button"), false);
    setVisible(getElement("calendar-load-error"), true);
    setVisible(getElement("calendar-content"), false);
    return;
  }

  renderFilter();
  calendar = new window.FullCalendar.Calendar(getElement("calendar-view"), {
    locale: "ja",
    // 日曜始まり
    firstDay: 0,
    initialView: WEEK_VIEW,
    headerToolbar: {
      left: "prev,next today",
      center: "title",
      right: `${WEEK_VIEW},${MONTH_VIEW},${LIST_VIEW}`,
    },
    // 表示の切り替えのボタン。表示と同じ名前の独自のボタンにして、切り替えを
    // switchView に通す（一覧表示では、締切を出さないため）。FullCalendarは、
    // 同じ名前の独自のボタンを、表示のボタンの代わりに置き、今の表示の
    // ボタンを、押された状態（fc-button-active・aria-pressed）にする。
    customButtons: {
      [WEEK_VIEW]: {
        text: "週",
        hint: "週表示",
        click: () => switchView(WEEK_VIEW),
      },
      [MONTH_VIEW]: {
        text: "月",
        hint: "月表示",
        click: () => switchView(MONTH_VIEW),
      },
      [LIST_VIEW]: {
        text: "一覧",
        hint: "一覧表示",
        click: () => switchView(LIST_VIEW),
      },
    },
    // 日本語の文言のファイルは読み込まず、使う文言を、ここで指定する。
    buttonText: { today: "今日" },
    buttonHints: { prev: "前へ", next: "次へ", today: "今日を表示" },
    navLinkHint: "$0を含む週を表示",
    moreLinkText: (count) => `＋${count}件`,
    moreLinkHint: (count) => `ほかに${count}件の予定（週の表示へ）`,
    noEventsText: "表示する予定はありません",
    timeHint: "時間",
    eventHint: "予定",
    eventTimeFormat: { hour: "2-digit", minute: "2-digit", hour12: false },
    // 予定は、色のブロックで表示する（締切は、toDeadlineEvent で、●の印に
    // する）。この設定は、表示ごと（views）には指定できず、週表示と一覧表示の
    // 見た目は変わらない。
    eventDisplay: "block",
    // 同じ日の予定の並び。FullCalendarの既定の並び（開始・長さ・終日）に、
    // 締切日時（締切だけが持つ）を足す。月表示では、締切（終日）が、
    // その日の時間型の予定より上に、締切日時の順に並ぶ。
    eventOrder: "start,-duration,allDay,dueDateTime,title",
    // 週表示：終日の行を、締切の行（「締切」）にする（予定は、すべて時刻を
    // 持つため、終日の行には締切だけが入る）。時間軸は0〜24時の全体にし
    // （範囲の外の予定が消えないように）、8時から見せる。
    allDayText: "締切",
    scrollTime: "08:00:00",
    views: {
      [MONTH_VIEW]: {
        // 時間型の予定は、時刻を出さず、タイトルだけを表示する。
        displayEventTime: false,
        // 1日3件まで（締切を含む）。4件目以降は「＋N件」にまとめる。
        dayMaxEvents: 3,
        // 日付と「＋N件」のクリックで、その日を含む週の週表示へ移る。
        navLinks: true,
        navLinkDayClick: WEEK_VIEW,
        moreLinkClick: WEEK_VIEW,
      },
      [LIST_VIEW]: {
        type: "list",
        // 日数（days）で指定する。週（weeks）で指定すると、日曜日に
        // そろってしまうため。日数なら、表示中の日付（初めは今日）から始まる。
        duration: { days: LIST_DAYS },
        // 日付の見出しに、曜日を付ける（例：2026年10月13日(火)）。
        listDayFormat: {
          year: "numeric",
          month: "long",
          day: "numeric",
          weekday: "short",
        },
        eventContent: renderListEventContent,
      },
    },
    eventSources: [
      { id: "events", events: fetchEvents },
      { id: DEADLINE_SOURCE_ID, events: fetchDeadlines },
    ],
    // 予定の取得の失敗（ApiError）は、fetchEvents が画面に出すため、ここでは
    // 出さない（FullCalendarの既定の、コンソールへの警告も出さない）。取得の
    // あとの処理（絞り込み・形の変換）の例外など、ApiError でない例外は、
    // ここで画面に出す（errorMessageOf が、固定のメッセージにし、詳細を
    // console.error に出す。013-L1）。
    eventSourceFailure: (error) => {
      if (!(error instanceof ApiError)) {
        showLoadError(error);
      }
    },
    loading: (isLoading) => {
      setVisible(getElement("calendar-loading"), isLoading);
    },
    eventClick: (info) => {
      const { apiEvent, apiTask } = info.event.extendedProps;
      if (apiTask !== undefined) {
        showTaskDetail(apiTask);
        return;
      }
      showEventDetail(apiEvent);
    },
  });

  getElement("calendar-retry-button").addEventListener("click", () => {
    calendar.refetchEvents();
  });
  getElement("calendar-deadline-retry-button").addEventListener(
    "click",
    () => {
      loadDeadlines();
    },
  );
  getElement("calendar-tab").addEventListener("shown.bs.tab", () => {
    // ほかのモードでの登録（授業・休講日・課題など）を反映するため、カレンダー
    // のモードを開くたびに、予定と課題・タスクを取得し直す。隠れている間に
    // 画面の幅が変わった場合に備えて、大きさも計算し直す。前の完了の切り替えの
    // エラーは消す。
    calendar.updateSize();
    calendar.refetchEvents();
    hideDeadlineActionError();
    loadDeadlines();
  });
  getElement("task-detail-modal").addEventListener(
    "show.bs.modal",
    prepareTaskDetail,
  );
  getElement("task-detail-completed").addEventListener(
    "change",
    toggleDetailCompleted,
  );
  calendar.render();
  // カレンダーのモードは、ページを開いたときに表示されているため、ここで
  // 課題・タスクを取得する（タブの shown.bs.tab は、最初は起きない）。
  loadDeadlines();
}
```
