# タスク015: 授業の編集・削除の画面

| 項目 | 内容 |
|---|---|
| Task ID | 015 |
| Task名 | 授業の編集・削除の画面（授業一覧の「編集」「削除」、編集のモーダル、削除の確認のモーダル、モーダルを閉じる処理の共通化、010-N2） |
| ブランチ | `feature/015-subject-edit-delete-ui`（Komaが作成・切替済みの状態で渡される） |

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに停止して報告する。

**このタスクには、承認ゲートはない（DBの構造を変えないため、migrationを作らない）。** 段階1・2を順に進め、「Copilot確認手順」を実施したら、結果を報告して応答を終える。途中で止まるのは、「注意」の停止の条件に当たったときだけ。**止まるときは、報告を書いて応答を終える。質問の機能（選択肢を出して回答を待つ機能）は使わない**（`.github/copilot-instructions.md` の「止まる場面の応答」）。

**ファイルは、手で書き写さない。** 5つのファイルの全文は、このTask MDの付録にある。各段階の始めに、「全文からファイルを作るスクリプト」を実行して作る（013-N1）。付録の全文は、スクリプトが読む。付録を読んで書き写す必要はない（本文の要点・差分・確認の手順を読む）。

**報告には、コマンドの出力を、要約せずに、そのまま貼る**（014-L1。Task 014の完了報告が要約だけで、求めた値（スクリプトの出力、件数、検索と差分の出力、開発用DBのハッシュ・件数、`git status`）がなかったため）。「注意」の最後の報告の項目を参照。

## 目的
授業モードの授業一覧から、授業全体の編集と削除ができるようにする（Task 014で作ったAPI、`PATCH`・`DELETE /api/subjects/<id>` と、1件取得の件数 `event_count`・`task_count` を使う）。設計資料（`docs/ui_ux.md` の「授業」の「一覧」「編集」「削除」「編集・削除の共通」、`docs/architecture.md` の「JavaScriptの構成（ES modules）」のモーダルの規則と `ui.js`）の仕様を、そのまま実装する。あわせて、JavaScriptからモーダルを閉じる処理を `ui.js` に共通化し（2026-10-14に決定。それまでの未決定事項「モーダルを閉じる処理の共通化」）、持ち越しの010-N2（休講日の「削除」ボタンの `aria-label`）を直す。**Python・API・DBの構造は変えない**（pytestは569件のまま）。

次の2段階で、この順に行う。

| 段階 | 内容 | 挙動の変化 | 段階の終わりの `pytest` |
|---|---|---|---|
| 1 | モーダルを閉じる処理の共通化と010-N2：`ui.js`（`trackModalShowing`・`hideModal` を足す）、`semesters.js`（自前の処理を、共通の関数に置き換える）、`closures.js`（「削除」ボタンの `aria-label`） | 学期の登録モーダルの動きは変わらない（表示の途中で登録が成功しても閉じる）。休講日の「削除」ボタンに `aria-label` が付く | **569件**（Pythonを変えない） |
| 2 | 授業の編集・削除の画面：`index.html`（一覧の「操作」の列、編集のモーダル、削除の確認のモーダル）、`subjects.js`（編集・削除） | 授業一覧に「編集」「削除」が出て、編集・削除ができる | **569件** |

## 前提（Task 014完了時点の状態）

| 区分 | 内容 |
|---|---|
| すでにある | 学期・授業・休講日のAPIと画面、予定API、カレンダー表示（Task 013）、授業の編集・削除のAPI（`PATCH`・`DELETE /api/subjects/<id>`）と、1件取得の件数（Task 014）。pytest（**569件**。`main` の `b13e99f` で確認） |
| まだない | 授業の編集・削除の画面、`ui.js` の `trackModalShowing`・`hideModal`（今は、`semesters.js` が自前で、表示の途中かを記録して閉じている） |
| DBの構造 | 変えない（初期migration `0280f6cf8d09` と、休講日の `42bd53808fa1`）。**migrationは不要** |
| 開発用DB | `instance/app.db` は、Komaの実際の開発用DB（すべてのテーブルが0件。2026-10-14、Task 014の確認のあとにKomaが確認）。**Copilotは、書き込まない。サーバーを起動しない（`python run.py` を実行しない）**。読むのは、「Copilot確認手順」のハッシュと件数だけ。**`sqlite3` は、必ず `-readonly` を付けて実行する**（011-L1） |
| 設計資料 | このタスクの前に、更新した設計資料が `main` に反映されている。`docs/architecture.md` の「JavaScriptの構成（ES modules）」に、`trackModalShowing`・`hideModal` の規則があり、未決定事項の表から「モーダルを閉じる処理の共通化」の行が外れている。`docs/ui_ux.md` の「授業」に、「**編集**（モーダル）」「**削除**（確認のモーダル）」がある |
| 確認 | JavaScriptの自動テストはない。画面の動きは、Komaの確認（確認用のサーバーでのブラウザ確認。ブラウザの操作はClaude）で確かめる。Copilotは、ブラウザでの確認をしない |

## Source of Truth
- `docs/ui_ux.md`：「授業モード」の「休講日」（「削除」ボタンの名前）、「授業」（「一覧」「編集」「削除」「編集・削除の共通」）
- `docs/architecture.md`：「JavaScriptの構成（ES modules）」（`ui.js`・`subjects.js` の役割、規則。特に、モーダルの規則、モーダルの中で始める要求の規則、`try` で囲む範囲、`textContent`、DOMの `id`）、「授業API」（1件取得の件数、`PATCH`・`DELETE`）、「授業全体の編集による作り直し」、「`api.js` の仕様」
- `docs/requirements.md`：「予定の編集・削除」
- `.github/copilot-instructions.md`：進め方、「止まる場面の応答」、コーディング方針（JavaScript）

## 実装対象ファイル

| 区分 | ファイル | 段階 | 内容 | 全文 |
|---|---|---|---|---|
| 変更 | `app/static/js/ui.js` | 1 | `trackModalShowing`・`hideModal` を足す | 付録A |
| 変更 | `app/static/js/semesters.js` | 1 | 自前のモーダルを閉じる処理（`semesterModalShowing`・`closeSemesterModal`）を、`ui.js` の共通の関数に置き換える | 付録B |
| 変更 | `app/static/js/closures.js` | 1 | 「削除」ボタンに `aria-label` を付ける（010-N2） | 付録C |
| 変更 | `app/templates/index.html` | 2 | 授業一覧の「操作」の列の見出し、編集のモーダル、削除の確認のモーダル | 付録D |
| 変更 | `app/static/js/subjects.js` | 2 | 一覧の「編集」「削除」ボタン、編集、削除の確認と削除 | 付録E |

上の5ファイル以外は、変更しない（`__pycache__/` などの、`.gitignore` の対象は除く）。**5ファイルとも、このTask MDの付録に全文がある。「全文からファイルを作るスクリプト」で作り、手で書き写さない。書き込んだあとに、手で直さない。** 全文を変える必要があると判断した場合は、変えずに停止して報告する。

## 非対象（このタスクでは作らない・変更しない）
- Pythonのファイル（`app/` の `.py`、`run.py`）、`tests/`（**テストは変えない・足さない**）、`migrations/`（**`flask db` のコマンドを、一切実行しない**）、`requirements.txt`（**ライブラリを追加しない**）、`pytest.ini`
- `app/templates/base.html`、`app/static/css/style.css`、`app/static/js/` の上の4つ以外のファイル（`api.js`・`dates.js`・`categories.js`・`calendar.js`・`main.js`）
- `index.html` の、授業一覧の見出しの行と、新しい2つのモーダル以外の部分（授業の登録モーダル、学期の登録モーダル、予定の詳細パネル、カレンダー、休講日の欄など）
- `docs/`、`.github/`、`.gitignore`
- 作らないもの：カレンダーからの予定の操作（詳細パネルは、確認だけのまま）、学期の変更・削除、授業の学期の付け替え、課題・タスクの画面、編集・削除のあとのメッセージ（一覧の表示の変化で分かるため、出さない）
- 持ち越しの003-H・013-L1（このタスクでは扱わない。013-L1は、`calendar.js` を変えるタスクで扱う）
- 開発用DB（`instance/app.db`）への書き込み、サーバーの起動（`python run.py` も、「Komaの確認」の確認用のサーバーも、起動しない）、ブラウザでの確認

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
        "app/static/js/ui.js",
        "app/static/js/semesters.js",
        "app/static/js/closures.js",
    ],
    "2": ["app/templates/index.html", "app/static/js/subjects.js"],
}

stage = sys.argv[1]
# このTask MDの「<!-- 全文: パス -->」の直後のコードブロックを、
# そのファイルの全文として取り出す。
fence = "`" * 3
task_text = Path("docs/tasks/015_subject_edit_delete_ui.md").read_text(
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
| 1（`python - 1`） | `全文の数：5`、`app/static/js/ui.js：書き込み（132行）`、`app/static/js/semesters.js：書き込み（282行）`、`app/static/js/closures.js：書き込み（234行）` |
| 2（`python - 2`） | `全文の数：5`、`app/templates/index.html：書き込み（403行）`、`app/static/js/subjects.js：書き込み（577行）` |

- 出力が上と違う場合（全文の数・行数・エラー）は、ほかの作業をせずに停止して報告する
- 段階の終わりの「全文との比較」（「Copilot確認手順」の4）で「不一致」が出た場合は、手で直さず、その段階のスクリプトをもう一度実行して、全文に戻す。戻したことと、違っていた理由（分かれば）を、報告に書く（013-N1）

## 段階1：モーダルを閉じる処理の共通化と010-N2（挙動は変わらない）

### 1-1. `app/static/js/ui.js`（全文：付録A）
要点：
- `trackModalShowing(modal)`：モーダル（要素）が、表示のアニメーションの途中（`show.bs.modal` から `shown.bs.modal` まで）かを、`ui.js` の中の集合（`showingModals`。`Set`）に記録する。JavaScriptから閉じるモーダルごとに、初期化で1回だけ呼ぶ
- `hideModal(modal)`：モーダルを閉じる。表示の途中なら、`shown.bs.modal` を待ってから閉じる（Bootstrapは、表示の途中の `hide()` を、何もせずに無視するため）。処理は、今の `semesters.js` の `closeSemesterModal` と同じ
- Bootstrapの内部の値（`_isTransitioning`・`_isShown` など）を使わない。時間を待つ方式（`setTimeout`）にしない
- 既存の6つの関数は変えない

`main` からの差分（確認用）：

```diff
--- a/app/static/js/ui.js
+++ b/app/static/js/ui.js
@@ -93,3 +93,40 @@ export function setSubmitting(button, submitting, labels) {
   button.disabled = submitting;
   button.textContent = submitting ? labels.busy : labels.idle;
 }
+
+// 表示のアニメーションの途中（show.bs.modal から shown.bs.modal まで）の
+// モーダルの要素。Bootstrapは、表示の途中の hide() を、何もせずに無視する
+// ため、閉じるとき（hideModal）に確かめる。Bootstrapの内部の値は使わず、
+// イベントで記録する。
+const showingModals = new Set();
+
+// modal（モーダルの要素）が、表示のアニメーションの途中かを記録する。
+// JavaScriptから閉じる（hideModal を使う）モーダルごとに、初期化のときに
+// 1回だけ呼ぶ。
+export function trackModalShowing(modal) {
+  modal.addEventListener("show.bs.modal", () => {
+    showingModals.add(modal);
+  });
+  modal.addEventListener("shown.bs.modal", () => {
+    showingModals.delete(modal);
+  });
+}
+
+// modal（モーダルの要素）を閉じる。表示のアニメーションの途中なら、表示が
+// 終わったとき（shown.bs.modal）に閉じる。trackModalShowing を呼んでおいた
+// モーダルにだけ使う。
+export function hideModal(modal) {
+  const instance = window.bootstrap.Modal.getOrCreateInstance(modal);
+
+  if (showingModals.has(modal)) {
+    modal.addEventListener(
+      "shown.bs.modal",
+      () => {
+        instance.hide();
+      },
+      { once: true },
+    );
+    return;
+  }
+  instance.hide();
+}
```

### 1-2. `app/static/js/semesters.js`（全文：付録B）
要点：変数 `semesterModalShowing` と関数 `closeSemesterModal` を消し、`ui.js` の `trackModalShowing`（初期化）と `hideModal`（登録の成功のあと）に置き換える。学期の登録の動き（表示の途中で登録が成功しても、表示が終わってから閉じる。P1、Task 008）は変わらない。

`main` からの差分（確認用）：

```diff
--- a/app/static/js/semesters.js
+++ b/app/static/js/semesters.js
@@ -4,16 +4,15 @@ import {
   clearFormErrors,
   errorMessageOf,
   getElement,
+  hideModal,
   setSubmitting,
   setVisible,
   showApiError,
+  trackModalShowing,
 } from "./ui.js";
 
 let semesters = [];
 let selectedId = null;
-// 学期の登録モーダルが、表示のアニメーションの途中か。Bootstrapは、
-// 表示の途中のhide()を無視するため、閉じるときに確かめる。
-let semesterModalShowing = false;
 
 const SEMESTER_FIELDS = {
   name: {
@@ -214,24 +213,6 @@ function showContent() {
   renderBanner();
 }
 
-function closeSemesterModal() {
-  const modal = getElement("semester-modal");
-  const instance = window.bootstrap.Modal.getOrCreateInstance(modal);
-
-  if (semesterModalShowing) {
-    // 表示の途中なら、表示が終わったとき（shown.bs.modal）に閉じる。
-    modal.addEventListener(
-      "shown.bs.modal",
-      () => {
-        instance.hide();
-      },
-      { once: true },
-    );
-    return;
-  }
-  instance.hide();
-}
-
 async function loadSemesters(preferredId = null) {
   showLoading();
   try {
@@ -283,7 +264,8 @@ async function submitSemester(event) {
     return;
   }
 
-  closeSemesterModal();
+  // 表示のアニメーションの途中でも、表示が終わってから閉じる（ui.js）。
+  hideModal(getElement("semester-modal"));
   await loadSemesters(created.id);
 }
 
@@ -292,12 +274,8 @@ export function initSemesters() {
     loadSemesters();
   });
   const modal = getElement("semester-modal");
-  modal.addEventListener("show.bs.modal", () => {
-    semesterModalShowing = true;
-  });
-  modal.addEventListener("shown.bs.modal", () => {
-    semesterModalShowing = false;
-  });
+  // 登録に成功したら、JavaScriptから閉じるため、表示の途中かを記録する。
+  trackModalShowing(modal);
   modal.addEventListener("show.bs.modal", resetForm);
   getElement("semester-form").addEventListener("submit", submitSemester);
   loadSemesters();
```

### 1-3. `app/static/js/closures.js`（全文：付録C）
要点：休講日の「削除」ボタンに、「2026年5月15日（金）の休講日を削除」の形の `aria-label` を付ける（010-N2。読み上げで、どの休講日のボタンかを区別できるようにする）。表示する日付の文字列を変数 `dateLabel` にして、表示と `aria-label` で使う。

`main` からの差分（確認用）：

```diff
--- a/app/static/js/closures.js
+++ b/app/static/js/closures.js
@@ -90,9 +90,10 @@ function renderClosures(closures) {
     item.className =
       "list-group-item d-flex justify-content-between align-items-center";
 
+    const dateLabel = formatJapaneseDateWithWeekday(closure.date);
     const text = document.createElement("div");
     const dateText = document.createElement("span");
-    dateText.textContent = formatJapaneseDateWithWeekday(closure.date);
+    dateText.textContent = dateLabel;
     text.append(dateText);
     if (closure.name !== null) {
       const name = document.createElement("span");
@@ -107,6 +108,8 @@ function renderClosures(closures) {
     deleteButton.id = `closure-delete-${closure.id}`;
     deleteButton.className = "btn btn-outline-danger btn-sm text-nowrap ms-2";
     deleteButton.textContent = CLOSURE_DELETE_LABELS.idle;
+    // 読み上げで、どの休講日の「削除」ボタンかを区別できるようにする。
+    deleteButton.setAttribute("aria-label", `${dateLabel}の休講日を削除`);
     deleteButton.addEventListener("click", () => {
       deleteClosure(closure.id, deleteButton);
     });
```

## 段階2：授業の編集・削除の画面

### 2-1. `app/templates/index.html`（全文：付録D）
要点：
- 授業一覧の表の見出しに、「操作」の列（`<th scope="col" class="text-end">操作</th>`）を足す。行の「編集」「削除」ボタンは、`subjects.js` が作る
- 授業の登録モーダル（`subject-modal`）のあと、予定の詳細パネル（`event-modal`）の前に、2つのモーダルを足す（どちらも `<main>` の外。`fade` を付ける。開くのは `subjects.js` から）
  - 編集のモーダル（`subject-edit-modal`）：見出し「授業を編集」、学期名と「学期は変更できません。…」、フォームの上部のエラー、科目名・教室・曜日・開始時刻・終了時刻・詳細／メモ（項目・選択肢・`required` は、登録フォームと同じ。`id` は `subject-edit-…`）、注意書き（`subject-edit-notice`。「保存する」の上）、「キャンセル」「保存する」
  - 削除の確認のモーダル（`subject-delete-modal`）：見出し「授業を削除」、対象の授業（`subject-delete-target`）、件数の取得中の表示（`subject-delete-loading`）、件数（`subject-delete-counts`。最初は隠す）、エラー（`subject-delete-error`。最初は隠す）、「削除は取り消せません。」、「キャンセル」（`subject-delete-cancel-button`）「削除する」（`subject-delete-submit-button`。最初は `disabled`）
- 文言は、`docs/ui_ux.md` の「授業」の「編集」「削除」のとおり

`main` からの差分のうち、見出しの行（確認用。モーダルの全文は付録D）：

```diff
--- a/app/templates/index.html
+++ b/app/templates/index.html
@@ -93,6 +93,7 @@
                     <th scope="col">時間</th>
                     <th scope="col">科目名</th>
                     <th scope="col">教室</th>
+                    <th scope="col" class="text-end">操作</th>
                   </tr>
                 </thead>
                 <tbody id="subject-table-body"></tbody>
```

足すDOMの `id`（27個）：

| モーダル | `id` |
|---|---|
| 編集 | `subject-edit-modal`、`subject-edit-modal-title`、`subject-edit-form`、`subject-edit-modal-semester`、`subject-edit-form-error`、`subject-edit-name`・`subject-edit-name-error`、`subject-edit-room`・`subject-edit-room-error`、`subject-edit-weekday`・`subject-edit-weekday-error`、`subject-edit-start-time`・`subject-edit-start-time-error`、`subject-edit-end-time`・`subject-edit-end-time-error`、`subject-edit-notes`・`subject-edit-notes-error`、`subject-edit-notice`、`subject-edit-submit-button` |
| 削除の確認 | `subject-delete-modal`、`subject-delete-modal-title`、`subject-delete-target`、`subject-delete-loading`、`subject-delete-counts`、`subject-delete-error`、`subject-delete-cancel-button`、`subject-delete-submit-button` |

行のボタンの `id` は、`subject-edit-<授業のid>`・`subject-delete-<授業のid>`（`subjects.js` が作る。休講日の `closure-delete-<id>` と同じ形）。

### 2-2. `app/static/js/subjects.js`（全文：付録E）
ファイルの構成（上から順に）：

| 名前 | 種類 | 内容 |
|---|---|---|
| `currentSemester`・`requestSerial` | 変数 | 変えない |
| `editingSubject`・`deletingSubject` | 変数（新規） | 編集・削除の対象の授業（一覧の行の値のコピー）。モーダルを開くときに入れる |
| `editSerial`・`deleteSerial` | 変数（新規） | 編集・削除のモーダルを開くたびに増やす通し番号（モーダルの中で始める要求の規則） |
| `WEEKDAYS`・`SUBJECT_FIELDS`・`SUBJECT_SUBMIT_LABELS` | 定数 | 変えない |
| `SUBJECT_EDIT_FIELDS`・`SUBJECT_EDIT_FORM_ERROR_ID`・`SUBJECT_EDIT_SUBMIT_LABELS`・`SUBJECT_DELETE_SUBMIT_LABELS` | 定数（新規） | 編集フォームの項目（`semester_id` はない）、エラーの表示先、ボタンの文言（「保存する」「保存中…」、「削除する」「削除中…」） |
| `subjectLabel` | 関数（新規） | 授業を表す文字列「「科目名」（月 09:00 〜 10:00）」。`aria-label` と、削除の確認の文言で使う |
| `resetSubjectForm` | 関数 | 変えない |
| `adjustEndTime(startSelect, endSelect)` | 関数（変更） | 対象のプルダウンを引数で受け取る（登録・編集で共通）。1時間後の時刻が選択肢にないときは、変えない（登録のフォームでは起きないため、登録の動きは変わらない） |
| `removeAddedTimeOptions`・`selectTime` | 関数（新規） | 編集で、今の時刻がプルダウンの選択肢にない場合に、時刻の順の位置に選択肢を足して選ぶ（足した選択肢には `data-added-time` を付け、次に開くときに取り除く） |
| `clearSubjectList`・`showSubjectLoading`・`showSubjectError`・`appendNotes` | 関数 | 変えない |
| `renderSubjects` | 関数（変更） | 行の最後に、操作のセル（右寄せ）と、「編集」「削除」ボタンを足す（`aria-label` は「「科目名」（月 09:00 〜 10:00）を編集」「…を削除」） |
| `loadSubjects`・`subjectCreatedMessage`・`submitSubject` | 関数 | 変えない |
| `openEditModal` | 関数（新規） | 「編集」ボタン。対象を控えて、編集のモーダルを開く |
| `fillEditForm` | 関数（新規） | 編集のモーダルの `show.bs.modal`。`editSerial` を増やし、今の値を入れ、エラーを消し、ボタンを戻す |
| `submitSubjectEdit` | 関数（新規） | 編集の保存（下の順序） |
| `openDeleteModal` | 関数（新規） | 「削除」ボタン。対象を控えて、削除の確認のモーダルを開く |
| `showDeleteError`・`hideDeleteError` | 関数（新規） | 削除の確認のモーダルの中のエラーの表示・消去 |
| `prepareDeleteModal` | 関数（新規） | 削除の確認のモーダルの `show.bs.modal`。件数の取得（下の順序） |
| `submitSubjectDelete` | 関数（新規） | 削除（下の順序） |
| `initSubjects` | 関数（変更） | 登録の開始時刻の `change` を、`adjustEndTime` の新しい引数に合わせる。編集・削除のモーダルに、`trackModalShowing` と、イベント（`show.bs.modal`・`shown.bs.modal`・`submit`・`click`・`change`）を付ける |

`submitSubjectEdit`（編集の保存）の順序：
1. 既定の送信を止める。今の `editSerial` と、対象の授業の `id` を控える。エラーの表示を消し、「保存する」を「保存中…」（無効）にする
2. `PATCH /api/subjects/<id>` に、6つの項目をすべて送る（`try` で囲むのは、この要求だけ）
3. 失敗：モーダルを開き直していれば（`editSerial` が違えば）、何もしない。そうでなければ、エラーを表示し（`showApiError`）、ボタンを戻す（モーダルは開いたまま）
4. 成功：モーダルを開き直していなければ、`hideModal` で閉じる。一覧を取得し直す（`loadSubjects({ showLoading: false })`）

`prepareDeleteModal`（件数の取得）の順序：
1. `deleteSerial` を増やして控える。対象の授業の文字列を表示し、件数とエラーを隠し、「予定と課題の件数を確認しています…」を表示し、「削除する」を押せなくする
2. `GET /api/subjects/<id>`（`try` で囲むのは、この要求だけ）
3. どちらの場合も、モーダルを開き直していれば（`deleteSerial` が違えば）、何もしない
4. 失敗：取得中の表示を隠し、エラーをモーダルの中に表示する。「削除する」は押せないまま
5. 成功：取得中の表示を隠し、「この授業の予定N件（今日より前の分を含む）と、課題M件も、まとめて削除されます。」を表示し、「削除する」を押せるようにする

`submitSubjectDelete`（削除）の順序：
1. 今の `deleteSerial` と、対象の授業の `id` を控える。エラーを消し、「削除する」を「削除中…」（無効）にする
2. `DELETE /api/subjects/<id>`（`try` で囲むのは、この要求だけ）
3. 失敗：モーダルを開き直していれば、何もしない。そうでなければ、エラーをモーダルの中に表示し、ボタンを戻す
4. 成功：モーダルを開き直していなければ、`hideModal` で閉じる。一覧を取得し直す

注意：
- 編集・削除のモーダルは、JavaScriptから開く（`window.bootstrap.Modal.getOrCreateInstance(...).show()`）。値は、`show.bs.modal` で入れる（登録のモーダルを開くたびに初期値に戻すのと同じ形）
- 削除の確認に、ブラウザ標準の `confirm` を使わない
- 編集・削除のあとに、メッセージを出さない（`docs/ui_ux.md`）

### 2-3. 変わる挙動・変わらない挙動

| 操作 | 変わる・変わらない |
|---|---|
| 授業一覧 | 「操作」の列と、各行の「編集」「削除」ボタンが出る。ほかの列・並び・読み込み中・取得の失敗・0件の表示は変わらない |
| 授業の登録（連続登録） | 変わらない（モーダルは閉じない。開始時刻を変えると、終了時刻が1時間後に合う） |
| 学期の登録 | 変わらない（登録に成功したら閉じる。表示の途中で成功しても、表示が終わってから閉じる） |
| 休講日の欄 | 「削除」ボタンに `aria-label` が付く。見た目と動きは変わらない |
| カレンダー | 変わらない（予定の詳細パネルは、確認だけのまま） |
| API・DB | 変わらない |

## JavaScriptの共通の規則
`.github/copilot-instructions.md` の「コーディング方針」のJavaScriptの規則と、`docs/architecture.md` の「JavaScriptの構成（ES modules）」の規則（`innerHTML` などを使わない、`textContent` で表示する、`fetch` は `api.js` だけ、`try` で囲むのは要求だけ、名前つきの引数、1行は80文字以内）。付録の全文は、これらに合っている（「Copilot確認手順」の3・6で確かめる）。

## 変更してよい既存のテスト
なし（Pythonを変えないため、テストは変えない・足さない）。**既存のテスト（569件）が、想定外に失敗した場合**は、原因を調べ、そこで実装を止めて、チャットで報告する。

## 実装手順
1. ブランチ・作業ツリーの確認。設計資料が更新されていることを確認する（「Copilot確認手順」の1の `grep`）。更新されていなければ、何も変更せずに停止して報告する
2. 作業の前の状態を記録する：開発用DBの有無・ハッシュ・件数（「Copilot確認手順」の1。**`sqlite3` は `-readonly` を付ける**）。`python -m pytest -q` が569件、すべて合格すること（合格しなければ、何も変更せずに停止して報告する）
3. **（段階1）** 「全文からファイルを作るスクリプト」を `python - 1` で実行する。`python -m pytest -q` が569件、すべて合格すること。「全文との比較」（「Copilot確認手順」の4）を `python - 1` で実行し、3ファイルとも「一致」
4. **（段階2）** スクリプトを `python - 2` で実行する。`python -m pytest -q` が569件、すべて合格すること。「全文との比較」を `python - 2` で実行し、5ファイルとも「一致」
5. 「Copilot確認手順」の2・3・5・6・7を実施する
6. 結果を報告して、応答を終える（コマンドの出力は、要約せずに、そのまま貼る。サーバーを起動していないこと、ブラウザでの確認をしていないことを明記する）

各段階の終わりに、`python -m pytest -q` の結果（件数・警告）と、全文との比較の結果を控えておく（最終報告に、出力をそのまま貼る）。

## 完了条件
- `python -m pytest -q` が、作業の前と、段階1・段階2の終わりに、**569件**すべて合格する（失敗・エラー・スキップが0件）
- 変更したファイルが、「実装対象ファイル」の5つだけ
- 5ファイルが、このTask MDの全文と1文字も違わない（「Copilot確認手順」の4が、段階1の終わりに3ファイル、段階2の終わりに5ファイルとも「一致」）
- `app/static/js/` のJavaScriptのファイルに、80文字を超える行がない
- 「Copilot確認手順」の5（画面のHTMLの確認）と6（検索と差分）が、期待どおり
- 実施の前後で、開発用DB（`instance/app.db`）のハッシュと、`semesters`・`subjects`・`closures`・`events`・`tasks` の件数が同じ
- 「Komaの確認」が、期待どおり
- レビューで承認される

## Copilot確認手順
**`sqlite3` は、必ず `-readonly` を付けて実行する**（011-L1）。**それぞれのコマンドの出力を、要約せずに、そのまま報告に貼る**（014-L1）。

```
# 1. 実施前
git branch --show-current      # feature/015-subject-edit-delete-ui
git status                     # 変更なし
grep -n "trackModalShowing\|hideModal" docs/architecture.md        # 数件
grep -n "| モーダルを閉じる処理の共通化" docs/architecture.md       # 出力なし（未決定事項の表から外れている）
grep -n "\*\*編集\*\*（モーダル）\|\*\*削除\*\*（確認のモーダル）" docs/ui_ux.md   # 2件
grep -n "の休講日を削除" docs/ui_ux.md                              # 1件
grep -n "止まる場面の応答" .github/copilot-instructions.md         # 数件
ls -l instance/app.db          # 存在すること（なければ、何も変更せずに停止して報告する）
shasum -a 256 instance/app.db
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"
python -m pytest -q            # 569 passed

# 2. 各段階の終わり
python -m pytest -q            # 段階1・段階2とも 569 passed

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
import re
import sys
from pathlib import Path

# 段階ごとのファイル（「全文からファイルを作るスクリプト」と同じ）。
STAGE_FILES = {
    "1": [
        "app/static/js/ui.js",
        "app/static/js/semesters.js",
        "app/static/js/closures.js",
    ],
    "2": ["app/templates/index.html", "app/static/js/subjects.js"],
}

stage = sys.argv[1]
# このTask MDの「<!-- 全文: パス -->」の直後のコードブロックを、
# そのファイルの期待する全文として取り出し、今のファイルと比べる。
fence = "`" * 3
task_text = Path("docs/tasks/015_subject_edit_delete_ui.md").read_text(
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

# 5. 画面のHTMLの確認（段階2の終わり。DBを使わない。開発用DBは開かない）
python - <<'EOF'
import re
import tempfile
from pathlib import Path

from app import create_app

EXPECTED_IDS = [
    "subject-edit-modal", "subject-edit-modal-title", "subject-edit-form",
    "subject-edit-modal-semester", "subject-edit-form-error",
    "subject-edit-name", "subject-edit-name-error", "subject-edit-room",
    "subject-edit-room-error", "subject-edit-weekday",
    "subject-edit-weekday-error", "subject-edit-start-time",
    "subject-edit-start-time-error", "subject-edit-end-time",
    "subject-edit-end-time-error", "subject-edit-notes",
    "subject-edit-notes-error", "subject-edit-notice",
    "subject-edit-submit-button", "subject-delete-modal",
    "subject-delete-modal-title", "subject-delete-target",
    "subject-delete-loading", "subject-delete-counts", "subject-delete-error",
    "subject-delete-cancel-button", "subject-delete-submit-button",
]
ORDER = [
    "subject-table-body", "semester-modal", "subject-modal",
    "subject-edit-modal", "subject-delete-modal", "event-modal",
]

with tempfile.TemporaryDirectory() as work_directory:
    database_path = Path(work_directory) / "check.db"
    app = create_app(
        {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"}
    )
    client = app.test_client()
    html = client.get("/").get_data(as_text=True)
    ids = re.findall(r'\bid="([^"]+)"', html)
    print("新しいid:", [ids.count(i) for i in EXPECTED_IDS])
    print("重複したid:", sorted({i for i in ids if ids.count(i) > 1}))
    positions = [html.index(f'id="{i}"') for i in ORDER]
    print("並び:", positions == sorted(positions))
    print("モーダルは<main>の外:", html.index("</main>") < positions[1])
    print("操作の列:", html.count('<th scope="col" class="text-end">操作</th>'))
    # JavaScriptが getElement("…") で使うidが、HTMLにあること。
    missing = []
    for path in sorted(Path("app/static/js").glob("*.js")):
        text = path.read_text(encoding="utf-8")
        for element_id in re.findall(r'getElement\(\s*"([^"]+)"', text):
            if element_id not in ids:
                missing.append(f"{path.name}:{element_id}")
    print("JavaScriptのidで、HTMLにないもの:", missing)
    for name in [
        "js/ui.js", "js/semesters.js", "js/closures.js", "js/subjects.js"
    ]:
        response = client.get(f"/static/{name}")
        print(name, response.status_code, response.mimetype)
        response.close()
EOF

# 6. 検索と差分（段階2の終わり）
grep -rnE "innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(|localStorage|sessionStorage|setTimeout|export default|\bvar |\.style\b|confirm\(" app/static/js/   # 出力なし
grep -rn "fetch(" app/static/js/                                   # api.js の中の1件だけ
grep -rn "_isTransitioning\|_isShown\|semesterModalShowing\|closeSemesterModal" app/static/js/   # 出力なし
grep -rn "trackModalShowing(\|hideModal(" app/static/js/           # 8件：ui.js 2（定義）、semesters.js 2、subjects.js 4
grep -rn "window.bootstrap.Modal" app/static/js/                   # 4件：calendar.js 1、ui.js 1、subjects.js 2（編集・削除のモーダルを開く）
grep -n "^export" app/static/js/ui.js                              # 8件（6つの関数と、trackModalShowing・hideModal）
grep -nE "onclick|style=" app/templates/index.html app/templates/base.html   # 出力なし
git diff --numstat app/static/js/ui.js app/static/js/semesters.js app/static/js/closures.js app/templates/index.html app/static/js/subjects.js
git diff --stat -- app/*.py app/routes/ app/models/ migrations/ tests/ requirements.txt pytest.ini run.py app/templates/base.html app/static/css/ app/static/js/api.js app/static/js/dates.js app/static/js/categories.js app/static/js/calendar.js app/static/js/main.js   # 出力なし

# 7. 実施後
shasum -a 256 instance/app.db  # 実施前と同じ
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"   # 実施前と同じ
git status                     # 変更：「実装対象ファイル」の5つ。新規：なし
git diff --stat
```

| 確認 | 期待する結果 |
|---|---|
| `python -m pytest -q` | 実施前、段階1・段階2の終わりとも、569件がすべて合格。失敗・エラー・スキップが0件。`migrations/env.py` の `DeprecationWarning` は、出ても構わない（報告する） |
| 1行の長さ（3） | 出力なし |
| 全文との比較（4） | `全文の数：5` と、段階1の終わりは3ファイル、段階2の終わりは5ファイルとも「一致」。「不一致」が出たら、手で直さず、その段階の「全文からファイルを作るスクリプト」をもう一度実行して全文に戻し、2からやり直す（戻したことを報告する）。Task MDの全文のほうを変える必要があると判断した場合は、停止して報告する |
| 画面のHTMLの確認（5） | 「新しいid:」のあとが、`1` が27個の一覧。「重複したid: []」。「並び: True」「モーダルは<main>の外: True」「操作の列: 1」「JavaScriptのidで、HTMLにないもの: []」。4つのファイルが、`200 text/javascript` |
| 検索と差分（6） | 上のコメントのとおり。`git diff --numstat` は、`37 0 app/static/js/ui.js`、`6 28 app/static/js/semesters.js`、`4 1 app/static/js/closures.js`、`110 0 app/templates/index.html`、`326 11 app/static/js/subjects.js`（表示の順は、Gitの並びでよい）。件数が違う場合は、その行を報告に書く |
| 開発用DB | 実施の前後で、ハッシュと、5つのテーブルの件数が同じ |
| `git status` | 変更：`app/static/js/ui.js`、`app/static/js/semesters.js`、`app/static/js/closures.js`、`app/static/js/subjects.js`、`app/templates/index.html`。新規：なし。Pythonのファイル・`migrations/`・`tests/`・`docs/`・`.github/`・`requirements.txt`・`run.py`・`instance/`・ほかのJavaScriptのファイル・`base.html`・`style.css` に変更なし |

`.pytest_cache/` や `__pycache__/` が `git status` に表示される場合は、`.gitignore` を変更せず、報告する。**Copilotは、サーバーを起動せず、ブラウザでの確認もしない**（Claude と Koma が行う）。報告に、そのことを明記する。

## Komaの確認
順序：（1）pytest →（2）commit・push とレビューの依頼 →（3）ブラウザでの確認（確認用のサーバー）→（4）開発用DBでの、読み取りだけの確認 →（5）マージ。

### 1. pytest
`python -m pytest -q` を自分で実行し、**569件、すべて合格**することを確かめる。

### 2. push とレビューの依頼
featureブランチを commit・push する（PRを作ってもよい）。Copilotの完了報告を共有して、Claudeにレビューを頼む。**pushは、マージではない。レビューの承認の前に、マージしない。** 修正が必要になった場合は、同じブランチでCopilotが直し、もう一度pushしてレビューを受ける。

### 3. ブラウザでの確認（確認用のサーバー）
レビューで「承認可能」になったあとに行う。**ブラウザの操作は、Claudeが、ブラウザのパネルまたはChromeで行う。Komaは、サーバーの起動・停止、確認用のデータの登録、DBのハッシュの確認、後片付けを行う**（roadmap の「進め方の決定の記録」、2026-10-12）。

#### 確認の安全のしくみ
- **開発用DBは使わない。** 確認用のDB（`/tmp/schedule-app-check-015/check.db`）を、migrationで作り、そのDBで起動した確認用のサーバーで確かめる（Task 010〜014と同じ方法）。開発用DBには、何も残らない
- 確認用のデータ（下の「確認用のデータの登録」）は、確認用のDBの場所を指定して登録する。学期・休講日・授業は、アプリのAPIで登録する（授業の予定は、APIが作る）。単発の予定（補講）と課題は、まだAPIで作れないため、確認用のDBに直接入れる。**このスクリプトは、確認用のDBだけに書き込む**
- 確認の途中の、APIの直接の呼び出し（D3の削除、E5などの読み取り）は、確認用のDBの、確認のために登録したデータに限る（roadmap の「進め方の決定の記録」、2026-10-12）
- ブラウザは、BootstrapとFullCalendarを、インターネット（jsDelivr）から読み込む。インターネットにつながった状態で行う
- 確認の前後で、開発用DBのハッシュが同じことを確かめる

#### 確認の日付
期待する結果は、確認の日（サーバーとブラウザの「今日」）が **2026-10-14〜2027-01-18** の間にあることを前提にしている（確認用の学期「2026年度 後期」（2026-09-21〜2027-01-29）が今日を含み、今日以降に月曜日の授業の予定があるため。「2026年度 前期」（〜2026-07-31）は、今日より前に終わっている）。この範囲の外の日に行う場合は、行う前にClaudeに伝える。件数の例は、2026-10-15（木）に確認した場合。

#### 準備
1. `python run.py` が起動していれば、Ctrl＋Cで止める（確認用のサーバーも、5001番を使うため）。開発用DBのハッシュを控える
   ```
   shasum -a 256 instance/app.db
   ```
2. 下の「確認用のサーバーの起動」のコマンドで、確認用のサーバーを起動する（このターミナルは、確認の間、開いたままにする）
3. 別のターミナルを開き、リポジトリのルートで、`.venv` を有効にして、下の「確認用のデータの登録」を実行する（1回だけ）
4. Claudeが、ブラウザで `http://127.0.0.1:5001/` を開き、強制再読み込みをする

#### 確認用のサーバーの起動
ブランチ `feature/015-subject-edit-delete-ui` のまま、リポジトリのルートで、`.venv` を有効にして、次を実行する（行の先頭に空白を入れずにコピーする）。

```
python - <<'EOF'
from pathlib import Path

from flask_migrate import upgrade

from app import create_app

# 確認用のDB（開発用DBとは別のファイル）。止めて起動し直しても、残る。
check_directory = Path("/tmp/schedule-app-check-015")
check_directory.mkdir(exist_ok=True)
database_path = check_directory / "check.db"
app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"})
with app.app_context():
    upgrade(directory="migrations")
print(f"確認用のDB：{database_path}", flush=True)
app.run(host="127.0.0.1", port=5001, debug=False)
EOF
```

期待する出力：初めての起動では、`Running upgrade  -> 0280f6cf8d09, initial tables` と `Running upgrade 0280f6cf8d09 -> 42bd53808fa1, add closures table`、「確認用のDB：/tmp/schedule-app-check-015/check.db」、`Running on http://127.0.0.1:5001`。起動し直したときは、`Running upgrade` の行が出ない。

#### 確認用のデータの登録
確認用のサーバーを起動したあとに、別のターミナルで、1回だけ実行する（行の先頭に空白を入れずにコピーする）。

```
python - <<'EOF'
from datetime import date, datetime, time
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models.event import Event
from app.models.task import Task

# 確認用のDBだけに書き込む（開発用DBは使わない）。DBは、確認用のサーバーが、
# 起動のときにmigrationで作っておいたものを使う。
database_path = Path("/tmp/schedule-app-check-015/check.db")
if not database_path.exists():
    raise SystemExit("確認用のDBがありません。先に、確認用のサーバーを起動してください")
app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"})
client = app.test_client()


def post(url, body):
    response = client.post(url, json=body)
    if response.status_code != 201:
        raise SystemExit(f"中止：{url} {response.status_code} {response.get_json()}")
    return response.get_json()


# 学期・休講日・授業は、APIで登録する（授業の予定は、APIが作る）。
autumn = post("/api/semesters", {"name": "2026年度 後期", "start_date": "2026-09-21", "end_date": "2027-01-29"})
spring = post("/api/semesters", {"name": "2026年度 前期", "start_date": "2026-04-06", "end_date": "2026-07-31"})
post("/api/closures", {"semester_id": autumn["id"], "date": "2026-11-23", "name": "勤労感謝の日"})
subjects = [
    (autumn, {"subject_name": "テスト：月曜1限", "weekday": 0, "start_time": "09:00", "end_time": "10:00", "room": "3号館201", "notes": "持ち物：教科書"}),
    (autumn, {"subject_name": "テスト：水曜2限", "weekday": 2, "start_time": "10:40", "end_time": "12:10", "notes": "APIで登録\n2行目"}),
    (autumn, {"subject_name": "テスト：週2回", "weekday": 1, "start_time": "13:00", "end_time": "14:00"}),
    (autumn, {"subject_name": "テスト：週2回", "weekday": 3, "start_time": "13:00", "end_time": "14:00"}),
    (spring, {"subject_name": "テスト：前期の授業", "weekday": 4, "start_time": "09:00", "end_time": "10:00"}),
]
created = [post("/api/subjects", {"semester_id": semester["id"], **subject}) for semester, subject in subjects]
print("授業のid：", [subject["id"] for subject in created])
print("授業の予定の件数：", [subject["generated_event_count"] for subject in created])

# 単発の予定（補講）と課題は、まだAPIで作れないため、確認用のDBに直接入れる。
with app.app_context():
    db.session.add(Event(subject_id=created[0]["id"], category="class", date=date(2026, 12, 5), start_time=time(13, 0), end_time=time(14, 0), title="テスト：月曜1限（補講）", room="3号館201", is_generated=False))
    db.session.add(Task(subject_id=created[0]["id"], category="assignment", title="テスト：レポート", due_datetime=datetime(2026, 11, 30, 23, 59), is_completed=False))
    db.session.commit()
print("「テスト：月曜1限」の件数：", client.get(f"/api/subjects/{created[0]['id']}").get_json())
EOF
```

期待する出力：`授業のid： [1, 2, 3, 4, 5]`、`授業の予定の件数： [18, 19, 19, 19, 17]`（月曜日は、休講日の11/23を除く。前期の金曜日は17日）、「テスト：月曜1限」の件数の行に `'event_count': 19`（自動生成18件＋補講1件）と `'task_count': 1`。2回目に実行すると、「中止：/api/semesters 400 …」で止まり、何も増えない（そのままでよい）。

以下、授業のidは、この出力のとおり（1：テスト：月曜1限、2：テスト：水曜2限、3：テスト：週2回（火）、4：テスト：週2回（木）、5：テスト：前期の授業）。

#### S. 授業一覧（ページを開いた状態から）

| No | 操作 | 期待する結果 |
|---|---|---|
| S1 | 画面下の「授業」を押す。学期「2026年度 後期」が選ばれていることを確かめる | 授業の表の見出しが、「曜日」「時間」「科目名」「教室」「操作」（「操作」は右寄せ）。行は、月「09:00 〜 10:00」「テスト：月曜1限」（その下に小さく「持ち物：教科書」）「3号館201」、火「13:00 〜 14:00」「テスト：週2回」「—」、水「10:40 〜 12:10」「テスト：水曜2限」（メモ2行）「—」、木「13:00 〜 14:00」「テスト：週2回」「—」。各行の右端に、「編集」（グレーの枠）と「削除」（赤の枠）のボタン |
| S2 | コンソールで、`[...document.querySelectorAll("#subject-table-body button")].map((b) => b.getAttribute("aria-label"))` と、`document.querySelector("#closure-list button").getAttribute("aria-label")` を実行する | 1つ目：`["「テスト：月曜1限」（月 09:00 〜 10:00）を編集", "「テスト：月曜1限」（月 09:00 〜 10:00）を削除", "「テスト：週2回」（火 13:00 〜 14:00）を編集", "「テスト：週2回」（火 13:00 〜 14:00）を削除", "「テスト：水曜2限」（水 10:40 〜 12:10）を編集", "「テスト：水曜2限」（水 10:40 〜 12:10）を削除", "「テスト：週2回」（木 13:00 〜 14:00）を編集", "「テスト：週2回」（木 13:00 〜 14:00）を削除"]`（同じ科目名の授業も、曜日で区別できる）。2つ目：`"2026年11月23日（月）の休講日を削除"`（010-N2） |

#### E. 編集

| No | 操作 | 期待する結果 |
|---|---|---|
| E1 | 「テスト：月曜1限」の行の「編集」を押す | モーダル「授業を編集」が開く。上部に「学期：**2026年度 後期**」と、小さく「学期は変更できません。誤った場合は、授業を削除して、正しい学期に登録し直してください。」。科目名「テスト：月曜1限」、教室「3号館201」、曜日「月曜日」、開始時刻「09:00」、終了時刻「10:00」、詳細・メモ「持ち物：教科書」。「保存する」の上に、黄色の枠の注意書き「保存すると、今日以降（今日を含む）のこの授業の予定が、新しい内容で作り直されます。カレンダーで個別に変更・削除した日も、元に戻ります。今日より前の予定と、カレンダーから追加した単発の授業（補講など）は、変わりません。」。ボタンは「キャンセル」と「保存する」。科目名の欄にカーソルがある |
| E2 | 開始時刻を「15:00」にする。そのあと「キャンセル」を押し、もう一度「テスト：月曜1限」の「編集」を押す | 開始時刻を変えると、終了時刻が「16:00」になる。開き直すと、開始時刻「09:00」、終了時刻「10:00」に戻っている（保存していない） |
| E3 | 科目名を、空白2つ（「  」）にして、「保存する」を押す | 科目名の欄が赤い枠になり、その下に「科目名は必須です」。モーダルは開いたまま。ボタンは「保存する」に戻り、押せる |
| E4 | 科目名を「テスト：月曜2限」、開始時刻を「11:00」、終了時刻を「12:00」にして、「保存する」を押す | モーダルが閉じる。一覧の月曜日の行が、「11:00 〜 12:00」「テスト：月曜2限」「3号館201」になる（メッセージは出ない）。行の並びは変わらない |
| E5 | コンソールで、下の「E5のスクリプト」を実行する | `today` が確認の日。`今日より前` と `今日以降` の件数の合計が18。`今日より前の値` が `["テスト：月曜1限 09:00-10:00 3号館201"]`、`今日以降の値` が `["テスト：月曜2限 11:00-12:00 3号館201"]`（今日以降だけが、新しい値で作り直された）。`単発` が `["テスト：月曜1限（補講） 13:00-14:00 3号館201"]`（変わらない）。`件数` が `{event_count: 19, task_count: 1}`。例：2026-10-15（木）なら、`今日より前: 4`、`今日以降: 14` |
| E6 | 画面下の「カレンダー」を押し、「一覧」を押す。そのあと、画面下の「授業」を押す | 今日からの28日間の一覧で、月曜日の行が「11:00 - 12:00」「📖 テスト：月曜2限」「3号館201」（編集が反映されている。11/23の月曜日は、休講日のため行がない）。2026-12-05が期間に入る場合は、その日に「13:00 - 14:00」「📖 テスト：月曜1限（補講）」 |
| E7 | 「テスト：水曜2限」の「編集」を押す。コンソールで、`[...document.getElementById("subject-edit-start-time").options].map((o) => o.value)` と、`[...document.getElementById("subject-edit-end-time").options].map((o) => o.value)` を実行する | 開始時刻が「10:40」、終了時刻が「12:10」を選んだ状態（空欄にならない）。詳細・メモが2行（「APIで登録」と「2行目」）。1つ目：`["09:00", "10:00", "10:40", "11:00", …, "18:00"]`（11個。10:40が、10:00と11:00の間）。2つ目：`["10:00", "11:00", "12:00", "12:10", "13:00", …, "19:00"]`（11個） |
| E8 | 何も変えずに「保存する」を押す。コンソールで、`await (await fetch("/api/subjects/2")).json()` を実行する | モーダルが閉じる。一覧の水曜日の行は「10:40 〜 12:10」のまま。応答の `start_time` が `"10:40"`、`end_time` が `"12:10"`、`notes` が `"APIで登録\n2行目"`、`room` が `null`（変わらない） |
| E9 | 火曜日の「テスト：週2回」の「編集」を押し、コンソールで、E7の1つ目を実行する。そのあと「キャンセル」を押す | 開始時刻「13:00」、終了時刻「14:00」。1つ目：`["09:00", "10:00", …, "18:00"]`（10個。E7で足した10:40は、なくなっている） |
| E10 | コンソールで、`document.getElementById("subject-edit-3").click(); document.getElementById("subject-edit-form").requestSubmit();` を実行し、2秒待つ。そのあと、`document.querySelectorAll(".modal-backdrop").length` を実行する | モーダルが開き、閉じる（開き始めてすぐ、表示の途中で保存が成功しても、表示が終わってから閉じる。`hideModal`）。2つ目の結果が `0`（背景の暗い幕が残っていない）。画面を操作できる |
| E11 | 学期のタブ「2026年度 前期」を押す。「テスト：前期の授業」の「編集」を押す。教室を「テスト教室」にして、「保存する」を押す。コンソールで、`(await (await fetch("/api/events?start_date=2026-04-06&end_date=2026-07-31")).json()).map((e) => e.room)` と、`(await (await fetch("/api/subjects/5")).json()).room` を実行する | E11で開いたモーダルの学期は「2026年度 前期」。保存するとモーダルが閉じ、一覧の教室が「テスト教室」になる。1つ目：`null` が17個（今日が学期の後のため、予定は作り直されない）。2つ目：`"テスト教室"`。最後に、学期のタブ「2026年度 後期」を押す |

E5のスクリプト（コンソールに、そのまま貼る）：

```
const { localDateString } = await import("/static/js/dates.js");
const today = localDateString();
const events = await (await fetch("/api/events?start_date=2026-09-21&end_date=2027-01-29")).json();
const mine = events.filter((e) => e.subject_id === 1);
const kinds = (list) => [...new Set(list.map((e) => `${e.title} ${e.start_time}-${e.end_time} ${e.room}`))];
const generated = mine.filter((e) => e.is_generated);
const before = generated.filter((e) => e.date < today);
const after = generated.filter((e) => e.date >= today);
const subject = await (await fetch("/api/subjects/1")).json();
({ today, 今日より前: before.length, 今日より前の値: kinds(before), 今日以降: after.length, 今日以降の値: kinds(after), 単発: kinds(mine.filter((e) => !e.is_generated)), 件数: { event_count: subject.event_count, task_count: subject.task_count } });
```

#### D. 削除（学期「2026年度 後期」で）

| No | 操作 | 期待する結果 |
|---|---|---|
| D1 | 「テスト：月曜2限」の行の「削除」を押す。コンソールで、`document.activeElement.id` を実行する | モーダル「授業を削除」が開く。上から、「「テスト：月曜2限」（月 11:00 〜 12:00）を削除します。」、「この授業の予定19件（今日より前の分を含む）と、課題1件も、まとめて削除されます。」、赤い字で「削除は取り消せません。」。ボタンは「キャンセル」と「削除する」（赤。押せる）。「予定と課題の件数を確認しています…」は、消えている。コンソールの結果は `"subject-delete-cancel-button"`（最初のフォーカスは「キャンセル」） |
| D2 | 「キャンセル」を押す | モーダルが閉じる。一覧は変わらない（「テスト：月曜2限」の行が残る） |
| D3 | コンソールで、`(await fetch("/api/subjects/4", { method: "DELETE" })).status` を実行する（ほかの場所で削除された場合の再現。確認用のデータに限る）。そのあと、一覧に残っている木曜日の「テスト：週2回」の行の「削除」を押す | 1つ目：`204`。モーダルが開き、対象「「テスト：週2回」（木 13:00 〜 14:00）を削除します。」の下に、赤い枠で「授業が見つかりません」。件数と「予定と課題の件数を確認しています…」は出ていない。「削除する」は押せない（薄い表示）。「キャンセル」で閉じる |
| D4 | 「テスト：月曜2限」の「削除」を押し、件数が出てから「削除する」を押す。コンソールで、`(await fetch("/api/subjects/1")).status` と、`(await (await fetch("/api/events?start_date=2026-09-21&end_date=2027-01-29")).json()).filter((e) => e.subject_id === 1).length` を実行する | ボタンが「削除中…」になり、モーダルが閉じる。一覧が、火「テスト：週2回」と、水「テスト：水曜2限」の2行になる（D3で削除した木曜日の行も、取得し直しで消える）。1つ目：`404`。2つ目：`0`（自動生成の予定と、補講の予定の両方が消えた） |
| D5 | コンソールで、下の「D5のスクリプト」を実行し、2秒待つ。そのあと、`document.querySelectorAll(".modal-backdrop").length` を実行する | 削除の確認のモーダルが開き、件数が出た直後に「削除する」が押され、モーダルが閉じる（表示の途中で削除が成功しても、閉じる）。2つ目の結果が `0`。一覧は、火「テスト：週2回」の1行 |
| D6 | 火曜日の「テスト：週2回」の「削除」を押し、「この授業の予定19件（今日より前の分を含む）と、課題0件も、まとめて削除されます。」が出るのを待つ。**Komaが、確認用のサーバーを止める（Ctrl＋C）。** Claudeが、「削除する」を押す | モーダルの中に、赤い枠で「サーバーに接続できませんでした。時間をおいて、もう一度お試しください」。ボタンは「削除する」に戻り、押せる。モーダルは開いたまま |
| D7 | **Komaが、「確認用のサーバーの起動」のコマンドで、確認用のサーバーを起動し直す**（ターミナルで↑キーを押すと、前のコマンドを呼び出せる。`Running upgrade` の行は出ない）。Claudeが、「キャンセル」を押す | モーダルが閉じる。一覧に、火「テスト：週2回」の行が残っている（削除されていない） |

D5のスクリプト（コンソールに、そのまま貼る）：

```
document.getElementById("subject-delete-2").click();
const button = document.getElementById("subject-delete-submit-button");
await new Promise((resolve) => {
  const timer = setInterval(() => {
    if (!button.disabled) {
      clearInterval(timer);
      button.click();
      resolve();
    }
  }, 5);
});
```

#### R. 学期の登録（`semesters.js` を共通の関数に置き換えたことの確認）

| No | 操作 | 期待する結果 |
|---|---|---|
| R1 | 「新しい学期を登録する」を押す。年度「2027」、種別「前期」、開始日 2027-04-05、終了日 2027-07-30 にして、「登録する」を押す | モーダルが閉じる。タブ「2027年度 前期」ができて、選ばれる。授業の欄は「この学期には、まだ授業が登録されていません」 |
| R2 | コンソールで、下の「R2のスクリプト」を実行し、2秒待つ。そのあと、`document.querySelectorAll(".modal-backdrop").length` を実行する（P1の操作。Task 008では模擬した要求で確かめたが、ここでは、確認用のDBに実際に登録する） | モーダルが開き、閉じる（開き始めてすぐ、表示の途中で登録が成功しても、表示が終わってから閉じる）。タブ「2027年度 後期」ができて、選ばれる。2つ目の結果が `0` |

R2のスクリプト（コンソールに、そのまま貼る）：

```
document.getElementById("semester-open-button").click();
document.getElementById("semester-year").value = "2027";
document.getElementById("semester-term").value = "後期";
document.getElementById("semester-start-date").value = "2027-09-20";
document.getElementById("semester-end-date").value = "2028-01-28";
document.getElementById("semester-form").requestSubmit();
```

#### C. 授業の登録（変わらないことの確認。R2の「2027年度 後期」で）

| No | 操作 | 期待する結果 |
|---|---|---|
| C1 | 「授業を追加」を押す。科目名「テスト：登録」、開始時刻「18:00」にして、「登録する」を押す | 開始時刻を変えると、終了時刻が「19:00」になる。登録すると、モーダルは閉じず、緑の枠で「「テスト：登録」を登録しました（予定19件を作成）」。入力欄は初期値に戻る |
| C2 | 「閉じる」を押す | 一覧に、月「18:00 〜 19:00」「テスト：登録」「—」の行と、その「編集」「削除」ボタン |

#### X. 確認の全体を通して

| No | 確認 | 期待する結果 |
|---|---|---|
| X1 | コンソール | JavaScriptの例外（`Uncaught …`）が出ていない。想定した400・404の応答（E3・D3）の「Failed to load resource」と、サーバーを止めている間（D6）の接続の失敗の記録（`net::ERR_CONNECTION_REFUSED`）は、除く（010-N1） |

#### 後片付け
1. 確認用のサーバーを止める（Ctrl＋C）
2. 確認用のDBのフォルダを消す
   ```
   rm -r /tmp/schedule-app-check-015
   ```
3. 開発用DBのハッシュが、準備の1と同じことを確かめる
   ```
   shasum -a 256 instance/app.db
   ```

ハッシュが変わっていた場合は、開発用DBを操作せずに、Claudeに伝える。

### 4. 開発用DBでの、読み取りだけの確認
3が期待どおりなら、開発用DBで起動して、画面が開くことだけを確かめる（登録・編集・削除はしない）。

```
shasum -a 256 instance/app.db          # 控える
python run.py                          # 開発用DBで起動
# ブラウザでの確認のあと、サーバーを Ctrl+C で止めてから
shasum -a 256 instance/app.db          # 起動の前と同じ
```

| 確認 | 期待 |
|---|---|
| ブラウザで開き、強制再読み込みして、画面下の「授業」を押す | 学期が0件のため、「学期がまだ登録されていません。最初の学期を登録してください」と「最初の学期を登録する」ボタン（学期・授業を登録していた場合は、その一覧と、各行の「編集」「削除」ボタン。**押さない**）。コンソールに、JavaScriptの例外がない |
| 最後のハッシュ | 起動の前と同じ |

### 5. マージ
1〜4が期待どおりで、レビューで承認されたら、マージする。このタスクは、DBの構造を変えないため、開発用DBへのmigrationの適用はない。開発用DBのデータも変えないため、バックアップは要らない。

マージのあとは、開発用DBのサーバー（`python run.py`）の授業モードで、授業の編集・削除ができる。削除は取り消せない（確認のモーダルで、削除される予定・課題の件数を確かめてから削除する）。

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
  - 作業の前の `python -m pytest` が、569件すべて合格しない
  - **既存のテスト**（569件）**が、想定外に失敗した**。テストの期待値や、ほかの仕様を直さずに、原因を調べて報告する
  - APIの変更や、DBの構造の変更（migration）が必要だと判断した
  - 実施の前後で、`instance/app.db` が変わった
- **止まるときは、報告を書いて、その応答を終える。質問の機能は使わない。** 再開するのは、Komaの新しいメッセージが、判断や再開を明確に示したときだけ（無回答や「続けて」だけの返事は、再開の指示ではない）。`.github/copilot-instructions.md` の「止まる場面の応答」
- **開発用DBを `sqlite3` で開くときは、必ず `-readonly` を付ける**（SELECTだけでも、付けずに開かない。011-L1）。`flask db` のコマンドを、一切実行しない。ライブラリを追加しない。サーバーを起動しない（`python run.py` も、「Komaの確認」の確認用のサーバーも）。「確認用のデータの登録」のスクリプトも、実行しない（Komaが行う）。ブラウザでの確認もしない
- 期待する結果と異なる結果が出た場合は、確認を飛ばさず、原因を直してから、すべての確認をやり直す（ただし、既存のテストの想定外の失敗は、上の停止の条件に従う。全文との「不一致」は、手で直さず、スクリプトで全文に戻す）
- 設計資料に書かれていない仕様は、自分で決めない
- **最後の報告には、次を含め、コマンドの出力は、要約せずに、そのまま貼る**（014-L1）：変更したファイル、「全文からファイルを作るスクリプト」の出力（段階1・2）、作業の前と各段階の `pytest` の件数と警告（最後の行）、1行の長さの確認の出力、全文との比較の出力（段階1：3ファイル、段階2：5ファイルの「一致」。スクリプトで全文に戻した場合は、そのこと）、画面のHTMLの確認の出力、検索と差分の出力（各コマンドと、その出力）、開発用DBの前後のハッシュ・件数、`git status`・`git diff --stat` の出力、サーバーの起動とブラウザでの確認をしていないこと、気になった点

## 付録：全文
「全文からファイルを作るスクリプト」と「全文との比較」が使う。各ファイルの全文は、「`<!-- 全文: パス -->`」の印の直後のコードブロック。**この付録を、手で書き写さない。** 本文の要点・差分と食い違う場合は、作業をせずに停止して報告する。

### 付録A. `app/static/js/ui.js`

<!-- 全文: app/static/js/ui.js -->
```javascript
import { ApiError } from "./api.js";

// 複数のモードで使う、表示とフォームの共通処理。
// fieldMap は { 項目名: { inputIds: [入力欄のid], messageId: エラー表示のid } }
// の形（項目名は、APIの fields の項目名と同じ）。

// idの要素を返す。見つからない場合は、idの書き間違いに気づけるように、
// idを含むエラーを投げる（null を返すと、あとで分かりにくい例外になるため）。
export function getElement(id) {
  const element = document.getElementById(id);
  if (element === null) {
    throw new Error(`要素が見つかりません：${id}`);
  }
  return element;
}

// visible が true なら表示し、false なら隠す（Bootstrapの d-none）。
export function setVisible(element, visible) {
  element.classList.toggle("d-none", !visible);
}

// 画面に出すエラーメッセージを返す。ApiError でない例外は、
// 固定のメッセージにし、詳細を console.error に出す。
export function errorMessageOf(error) {
  if (error instanceof ApiError) {
    return error.message;
  }

  console.error(error);
  return "予期しないエラーが発生しました。ページを再読み込みして、もう一度お試しください";
}

function setFieldError(field, message) {
  getElement(field.messageId).textContent = message;
  for (const inputId of field.inputIds) {
    getElement(inputId).classList.add("is-invalid");
  }
}

function showFormMessage(formErrorId, message) {
  const formError = getElement(formErrorId);
  formError.textContent = message;
  setVisible(formError, true);
}

// fieldMap の項目のエラー表示と、フォームの上部のエラー（formErrorId）を消す。
export function clearFormErrors(fieldMap, formErrorId) {
  for (const field of Object.values(fieldMap)) {
    getElement(field.messageId).replaceChildren();
    for (const inputId of field.inputIds) {
      getElement(inputId).classList.remove("is-invalid");
    }
  }

  const formError = getElement(formErrorId);
  formError.replaceChildren();
  setVisible(formError, false);
}

// API のエラーを表示する。fields の項目は、fieldMap の項目の下に出し、
// それ以外は、フォームの上部（formErrorId）に出す。
export function showApiError(error, fieldMap, formErrorId) {
  clearFormErrors(fieldMap, formErrorId);

  if (
    error instanceof ApiError &&
    error.code === "validation_error" &&
    error.fields !== null
  ) {
    let hasUnexpectedField = Object.keys(error.fields).length === 0;
    for (const [fieldName, message] of Object.entries(error.fields)) {
      const field = Object.prototype.hasOwnProperty.call(fieldMap, fieldName)
        ? fieldMap[fieldName]
        : undefined;
      if (field === undefined) {
        hasUnexpectedField = true;
      } else {
        setFieldError(field, message);
      }
    }

    if (hasUnexpectedField) {
      showFormMessage(formErrorId, "入力内容に誤りがあります");
    }
    return;
  }

  showFormMessage(formErrorId, errorMessageOf(error));
}

// 送信中の表示。labels は { idle: 通常の文字, busy: 送信中の文字 } の形。
export function setSubmitting(button, submitting, labels) {
  button.disabled = submitting;
  button.textContent = submitting ? labels.busy : labels.idle;
}

// 表示のアニメーションの途中（show.bs.modal から shown.bs.modal まで）の
// モーダルの要素。Bootstrapは、表示の途中の hide() を、何もせずに無視する
// ため、閉じるとき（hideModal）に確かめる。Bootstrapの内部の値は使わず、
// イベントで記録する。
const showingModals = new Set();

// modal（モーダルの要素）が、表示のアニメーションの途中かを記録する。
// JavaScriptから閉じる（hideModal を使う）モーダルごとに、初期化のときに
// 1回だけ呼ぶ。
export function trackModalShowing(modal) {
  modal.addEventListener("show.bs.modal", () => {
    showingModals.add(modal);
  });
  modal.addEventListener("shown.bs.modal", () => {
    showingModals.delete(modal);
  });
}

// modal（モーダルの要素）を閉じる。表示のアニメーションの途中なら、表示が
// 終わったとき（shown.bs.modal）に閉じる。trackModalShowing を呼んでおいた
// モーダルにだけ使う。
export function hideModal(modal) {
  const instance = window.bootstrap.Modal.getOrCreateInstance(modal);

  if (showingModals.has(modal)) {
    modal.addEventListener(
      "shown.bs.modal",
      () => {
        instance.hide();
      },
      { once: true },
    );
    return;
  }
  instance.hide();
}
```

### 付録B. `app/static/js/semesters.js`

<!-- 全文: app/static/js/semesters.js -->
```javascript
import { apiRequest } from "./api.js";
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

function chooseInitialSemester(items, today) {
  // YYYY-MM-DDは桁が固定されているため、文字列の大小が日付の前後と一致する。
  const current = items.find(
    (semester) => semester.start_date <= today && today <= semester.end_date,
  );
  if (current !== undefined) {
    return current;
  }

  let next = null;
  for (const semester of items) {
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
  for (const semester of items) {
    if (
      mostRecent === null ||
      semester.end_date > mostRecent.end_date
    ) {
      mostRecent = semester;
    }
  }
  return mostRecent;
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
      preferred ?? chooseInitialSemester(semesters, localDateString());
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

### 付録C. `app/static/js/closures.js`

<!-- 全文: app/static/js/closures.js -->
```javascript
import { apiRequest } from "./api.js";
import { formatJapaneseDateWithWeekday } from "./dates.js";
import {
  clearFormErrors,
  errorMessageOf,
  getElement,
  setSubmitting,
  setVisible,
  showApiError,
} from "./ui.js";

let currentSemester = null;
// 一覧の取得の通し番号。古い応答で、今の一覧を上書きしないために使う。
let requestSerial = 0;
// 学期の選択の通し番号。追加・削除の途中で、学期が変わったかを確かめる。
// 一覧の取得し直しでは選択は変わらないため、requestSerialとは別に持つ。
let selectionSerial = 0;

const CLOSURE_FIELDS = {
  semester_id: {
    inputIds: [],
    messageId: "closure-semester-error",
  },
  date: {
    inputIds: ["closure-date"],
    messageId: "closure-date-error",
  },
  name: {
    inputIds: ["closure-name"],
    messageId: "closure-name-error",
  },
};
// 欄の上部のエラー表示。追加の、項目に結びつかないエラーと、削除のエラーを出す。
const CLOSURE_FORM_ERROR_ID = "closure-form-error";
const CLOSURE_SUBMIT_LABELS = {
  idle: "追加する",
  busy: "追加中…",
};
const CLOSURE_DELETE_LABELS = {
  idle: "削除",
  busy: "削除中…",
};

function clearClosureErrors() {
  clearFormErrors(CLOSURE_FIELDS, CLOSURE_FORM_ERROR_ID);
}

function resetClosureForm() {
  getElement("closure-form").reset();
  getElement("closure-date").value = "";
  getElement("closure-name").value = "";
  clearClosureErrors();
  setSubmitting(
    getElement("closure-submit-button"),
    false,
    CLOSURE_SUBMIT_LABELS,
  );
}

function clearClosureList() {
  getElement("closure-list").replaceChildren();
  setVisible(getElement("closure-loading"), false);
  setVisible(getElement("closure-load-error"), false);
  setVisible(getElement("closure-empty"), false);
  setVisible(getElement("closure-list"), false);
}

function showClosureLoading() {
  setVisible(getElement("closure-loading"), true);
  setVisible(getElement("closure-load-error"), false);
  setVisible(getElement("closure-empty"), false);
  setVisible(getElement("closure-list"), false);
}

function showClosureLoadError(error) {
  getElement("closure-load-error-message").textContent =
    errorMessageOf(error);
  setVisible(getElement("closure-loading"), false);
  setVisible(getElement("closure-load-error"), true);
  setVisible(getElement("closure-empty"), false);
  setVisible(getElement("closure-list"), false);
}

function renderClosures(closures) {
  const list = getElement("closure-list");
  const fragment = document.createDocumentFragment();

  for (const closure of closures) {
    const item = document.createElement("li");
    item.className =
      "list-group-item d-flex justify-content-between align-items-center";

    const dateLabel = formatJapaneseDateWithWeekday(closure.date);
    const text = document.createElement("div");
    const dateText = document.createElement("span");
    dateText.textContent = dateLabel;
    text.append(dateText);
    if (closure.name !== null) {
      const name = document.createElement("span");
      name.className = "ms-2 text-muted";
      name.textContent = closure.name;
      text.append(name);
    }
    item.append(text);

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.id = `closure-delete-${closure.id}`;
    deleteButton.className = "btn btn-outline-danger btn-sm text-nowrap ms-2";
    deleteButton.textContent = CLOSURE_DELETE_LABELS.idle;
    // 読み上げで、どの休講日の「削除」ボタンかを区別できるようにする。
    deleteButton.setAttribute("aria-label", `${dateLabel}の休講日を削除`);
    deleteButton.addEventListener("click", () => {
      deleteClosure(closure.id, deleteButton);
    });
    item.append(deleteButton);

    fragment.append(item);
  }

  list.replaceChildren(fragment);
  setVisible(getElement("closure-loading"), false);
  setVisible(getElement("closure-load-error"), false);
  setVisible(getElement("closure-empty"), closures.length === 0);
  setVisible(list, closures.length > 0);
}

async function loadClosures({ showLoading = true } = {}) {
  if (currentSemester === null) {
    clearClosureList();
    return;
  }

  const semesterId = currentSemester.id;
  const currentRequest = ++requestSerial;
  if (showLoading) {
    showClosureLoading();
  }

  try {
    const closures = await apiRequest(
      "GET",
      `/api/closures?semester_id=${semesterId}`,
    );
    // タブ切替後に古い応答が届いても、現在の休講日の一覧を上書きしない。
    if (currentRequest !== requestSerial) {
      return;
    }
    renderClosures(closures);
  } catch (error) {
    if (currentRequest !== requestSerial) {
      return;
    }
    showClosureLoadError(error);
  }
}

async function submitClosure(event) {
  event.preventDefault();
  // 追加の途中で学期が変わったら、結果を今の画面に出さないために控える。
  const startedSelection = selectionSerial;
  clearClosureErrors();

  const submitButton = getElement("closure-submit-button");
  setSubmitting(submitButton, true, CLOSURE_SUBMIT_LABELS);

  // try で囲むのは、追加の要求だけにする（成功後の処理の例外を、
  // 「追加の失敗」として表示しないため）。
  try {
    await apiRequest("POST", "/api/closures", {
      semester_id: currentSemester.id,
      date: getElement("closure-date").value,
      name: getElement("closure-name").value,
    });
  } catch (error) {
    if (startedSelection !== selectionSerial) {
      return;
    }
    showApiError(error, CLOSURE_FIELDS, CLOSURE_FORM_ERROR_ID);
    setSubmitting(submitButton, false, CLOSURE_SUBMIT_LABELS);
    return;
  }

  if (startedSelection !== selectionSerial) {
    return;
  }
  resetClosureForm();
  getElement("closure-date").focus();
  await loadClosures({ showLoading: false });
}

async function deleteClosure(closureId, button) {
  // 削除の途中で学期が変わったら、結果を今の画面に出さないために控える。
  const startedSelection = selectionSerial;
  clearClosureErrors();
  setSubmitting(button, true, CLOSURE_DELETE_LABELS);

  // try で囲むのは、削除の要求だけにする（追加と同じ理由）。
  try {
    await apiRequest("DELETE", `/api/closures/${closureId}`);
  } catch (error) {
    if (startedSelection !== selectionSerial) {
      return;
    }
    showApiError(error, CLOSURE_FIELDS, CLOSURE_FORM_ERROR_ID);
    setSubmitting(button, false, CLOSURE_DELETE_LABELS);
    return;
  }

  if (startedSelection !== selectionSerial) {
    return;
  }
  await loadClosures({ showLoading: false });
}

export function initClosures() {
  document.addEventListener("semester-selected", (event) => {
    currentSemester = event.detail.semester;
    selectionSerial += 1;
    requestSerial += 1;
    // ほかの学期への入力や、ほかの学期で出たエラーを残さない。
    resetClosureForm();
    if (currentSemester === null) {
      clearClosureList();
      return;
    }
    loadClosures();
  });

  getElement("closure-retry-button").addEventListener("click", () => {
    loadClosures();
  });
  getElement("closure-form").addEventListener("submit", submitClosure);
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
      <p>課題・タスク（準備中）</p>
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
          <button type="submit" id="subject-edit-submit-button" class="btn btn-primary">保存する</button>
        </div>
      </form>
    </div>
  </div>
</div>

<div class="modal fade" id="subject-delete-modal" tabindex="-1" aria-labelledby="subject-delete-modal-title" aria-hidden="true">
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
        <p class="text-danger mb-0">削除は取り消せません。</p>
      </div>
      <div class="modal-footer">
        <button type="button" id="subject-delete-cancel-button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
        <button type="button" id="subject-delete-submit-button" class="btn btn-danger" disabled>削除する</button>
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

### 付録E. `app/static/js/subjects.js`

<!-- 全文: app/static/js/subjects.js -->
```javascript
import { apiRequest } from "./api.js";
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

let currentSemester = null;
let requestSerial = 0;
// 編集・削除の対象の授業（一覧の行の値のコピー）。モーダルを開くときに入れる。
let editingSubject = null;
let deletingSubject = null;
// 編集・削除のモーダルを開くたびに増やす通し番号。閉じて開き直したあとに
// 届いた古い応答で、今のモーダルの表示を変えないために使う。
let editSerial = 0;
let deleteSerial = 0;

const WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"];
const SUBJECT_FIELDS = {
  semester_id: {
    inputIds: [],
    messageId: "subject-semester-error",
  },
  subject_name: {
    inputIds: ["subject-name"],
    messageId: "subject-name-error",
  },
  room: {
    inputIds: ["subject-room"],
    messageId: "subject-room-error",
  },
  weekday: {
    inputIds: ["subject-weekday"],
    messageId: "subject-weekday-error",
  },
  start_time: {
    inputIds: ["subject-start-time"],
    messageId: "subject-start-time-error",
  },
  end_time: {
    inputIds: ["subject-end-time"],
    messageId: "subject-end-time-error",
  },
  notes: {
    inputIds: ["subject-notes"],
    messageId: "subject-notes-error",
  },
};
const SUBJECT_SUBMIT_LABELS = {
  idle: "登録する",
  busy: "登録中…",
};
// 編集フォームの項目。学期（semester_id）は、編集では送らない。
const SUBJECT_EDIT_FIELDS = {
  subject_name: {
    inputIds: ["subject-edit-name"],
    messageId: "subject-edit-name-error",
  },
  room: {
    inputIds: ["subject-edit-room"],
    messageId: "subject-edit-room-error",
  },
  weekday: {
    inputIds: ["subject-edit-weekday"],
    messageId: "subject-edit-weekday-error",
  },
  start_time: {
    inputIds: ["subject-edit-start-time"],
    messageId: "subject-edit-start-time-error",
  },
  end_time: {
    inputIds: ["subject-edit-end-time"],
    messageId: "subject-edit-end-time-error",
  },
  notes: {
    inputIds: ["subject-edit-notes"],
    messageId: "subject-edit-notes-error",
  },
};
const SUBJECT_EDIT_FORM_ERROR_ID = "subject-edit-form-error";
const SUBJECT_EDIT_SUBMIT_LABELS = {
  idle: "保存する",
  busy: "保存中…",
};
const SUBJECT_DELETE_SUBMIT_LABELS = {
  idle: "削除する",
  busy: "削除中…",
};

// 授業を表す文字列（例：「プログラミング基礎」（月 09:00 〜 10:00））。
// 同じ科目名の授業（週2回の授業など）を区別できるように、曜日と時刻を含める。
function subjectLabel(subject) {
  return (
    `「${subject.subject_name}」` +
    `（${WEEKDAYS[subject.weekday]} ` +
    `${subject.start_time} 〜 ${subject.end_time}）`
  );
}

function resetSubjectForm({ clearSuccess = true } = {}) {
  getElement("subject-form").reset();
  getElement("subject-name").value = "";
  getElement("subject-room").value = "";
  getElement("subject-weekday").value = "0";
  getElement("subject-start-time").value = "09:00";
  getElement("subject-end-time").value = "10:00";
  getElement("subject-notes").value = "";
  getElement("subject-modal-semester").textContent = currentSemester.name;
  clearFormErrors(SUBJECT_FIELDS, "subject-form-error");
  if (clearSuccess) {
    const success = getElement("subject-form-success");
    success.replaceChildren();
    setVisible(success, false);
  }
  setSubmitting(
    getElement("subject-submit-button"),
    false,
    SUBJECT_SUBMIT_LABELS,
  );
}

// 開始時刻を変えて、終了時刻が開始時刻以下になったときは、終了時刻を、
// 開始時刻の1時間後に合わせる（登録・編集のフォームで使う）。
function adjustEndTime(startSelect, endSelect) {
  // HH:MMは桁が固定されているため、文字列の大小で時刻を比較できる。
  if (endSelect.value > startSelect.value) {
    return;
  }
  const nextHour = String(Number(startSelect.value.slice(0, 2)) + 1).padStart(
    2,
    "0",
  );
  const nextTime = `${nextHour}:00`;
  // 1時間後の時刻が選択肢にない場合（編集で、選択肢に足した時刻を選んだ
  // 場合など）は、変えない（APIの入力チェックで、誤りが表示される）。
  const hasNextTime = Array.from(endSelect.options).some(
    (option) => option.value === nextTime,
  );
  if (hasNextTime) {
    endSelect.value = nextTime;
  }
}

// 編集フォームで、時刻のプルダウンに足した選択肢を取り除く。
function removeAddedTimeOptions(select) {
  for (const option of select.querySelectorAll("option[data-added-time]")) {
    option.remove();
  }
}

// 時刻のプルダウンで、time を選ぶ。選択肢にない時刻（APIで登録した授業の、
// 9〜19時・1時間刻み以外の時刻など）は、時刻の順の位置に選択肢を足して
// から選ぶ（足さないと、空欄になり、必須のエラーになるため）。
function selectTime(select, time) {
  const options = Array.from(select.options);
  if (!options.some((option) => option.value === time)) {
    const option = document.createElement("option");
    option.value = time;
    option.textContent = time;
    option.dataset.addedTime = "true";
    const nextOption = options.find((item) => item.value > time);
    select.insertBefore(option, nextOption ?? null);
  }
  select.value = time;
}

function clearSubjectList() {
  getElement("subject-table-body").replaceChildren();
  setVisible(getElement("subject-loading"), false);
  setVisible(getElement("subject-load-error"), false);
  setVisible(getElement("subject-empty"), false);
  setVisible(getElement("subject-list"), false);
}

function showSubjectLoading() {
  setVisible(getElement("subject-loading"), true);
  setVisible(getElement("subject-load-error"), false);
  setVisible(getElement("subject-empty"), false);
  setVisible(getElement("subject-list"), false);
}

function showSubjectError(error) {
  getElement("subject-load-error-message").textContent =
    errorMessageOf(error);
  setVisible(getElement("subject-loading"), false);
  setVisible(getElement("subject-load-error"), true);
  setVisible(getElement("subject-empty"), false);
  setVisible(getElement("subject-list"), false);
}

function appendNotes(cell, notes) {
  const memo = document.createElement("div");
  memo.className = "text-muted small";
  const lines = notes.split(/\r?\n/);

  lines.forEach((line, index) => {
    if (index > 0) {
      memo.append(document.createElement("br"));
    }
    memo.append(document.createTextNode(line));
  });

  cell.append(memo);
}

function renderSubjects(subjects) {
  const tableBody = getElement("subject-table-body");
  const fragment = document.createDocumentFragment();

  for (const subject of subjects) {
    const row = document.createElement("tr");

    const weekday = document.createElement("td");
    weekday.textContent = WEEKDAYS[subject.weekday];
    row.append(weekday);

    const time = document.createElement("td");
    time.textContent = `${subject.start_time} 〜 ${subject.end_time}`;
    row.append(time);

    const name = document.createElement("td");
    const subjectName = document.createElement("div");
    subjectName.textContent = subject.subject_name;
    name.append(subjectName);
    if (subject.notes !== null) {
      appendNotes(name, subject.notes);
    }
    row.append(name);

    const room = document.createElement("td");
    room.textContent = subject.room ?? "—";
    row.append(room);

    // 読み上げで、どの授業のボタンかを区別できるように、aria-label に
    // 授業を表す文字列を入れる。
    const label = subjectLabel(subject);
    const actions = document.createElement("td");
    actions.className = "text-end text-nowrap";

    const editButton = document.createElement("button");
    editButton.type = "button";
    editButton.id = `subject-edit-${subject.id}`;
    editButton.className = "btn btn-outline-secondary btn-sm";
    editButton.textContent = "編集";
    editButton.setAttribute("aria-label", `${label}を編集`);
    editButton.addEventListener("click", () => {
      openEditModal(subject);
    });
    actions.append(editButton);

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.id = `subject-delete-${subject.id}`;
    deleteButton.className = "btn btn-outline-danger btn-sm ms-1";
    deleteButton.textContent = "削除";
    deleteButton.setAttribute("aria-label", `${label}を削除`);
    deleteButton.addEventListener("click", () => {
      openDeleteModal(subject);
    });
    actions.append(deleteButton);

    row.append(actions);
    fragment.append(row);
  }

  tableBody.replaceChildren(fragment);
  setVisible(getElement("subject-loading"), false);
  setVisible(getElement("subject-load-error"), false);
  setVisible(getElement("subject-empty"), subjects.length === 0);
  setVisible(getElement("subject-list"), subjects.length > 0);
}

async function loadSubjects({ showLoading = true } = {}) {
  if (currentSemester === null) {
    clearSubjectList();
    return;
  }

  const semesterId = currentSemester.id;
  const currentRequest = ++requestSerial;
  if (showLoading) {
    showSubjectLoading();
  }

  try {
    const subjects = await apiRequest(
      "GET",
      `/api/subjects?semester_id=${semesterId}`,
    );
    // タブ切替後に古い応答が届いても、現在の授業一覧を上書きしない。
    if (currentRequest !== requestSerial) {
      return;
    }
    renderSubjects(subjects);
  } catch (error) {
    if (currentRequest !== requestSerial) {
      return;
    }
    showSubjectError(error);
  }
}

// 登録済みのメッセージ。作成された予定の件数によって、文言を変える。
function subjectCreatedMessage(created) {
  const registered = `「${created.subject_name}」を登録しました`;
  if (created.generated_event_count === 0) {
    return (
      `${registered}（学期の期間内に、この曜日の授業日がないため、` +
      "予定は作成されませんでした）"
    );
  }
  return `${registered}（予定${created.generated_event_count}件を作成）`;
}

async function submitSubject(event) {
  event.preventDefault();
  clearFormErrors(SUBJECT_FIELDS, "subject-form-error");
  const success = getElement("subject-form-success");
  success.replaceChildren();
  setVisible(success, false);

  const submitButton = getElement("subject-submit-button");
  setSubmitting(submitButton, true, SUBJECT_SUBMIT_LABELS);

  // try で囲むのは、登録の要求だけにする。登録の成功後の処理で例外が
  // 起きた場合に、「登録の失敗」として表示しないため。
  let created;
  try {
    created = await apiRequest("POST", "/api/subjects", {
      semester_id: currentSemester.id,
      subject_name: getElement("subject-name").value,
      room: getElement("subject-room").value,
      weekday: Number(getElement("subject-weekday").value),
      start_time: getElement("subject-start-time").value,
      end_time: getElement("subject-end-time").value,
      notes: getElement("subject-notes").value,
    });
  } catch (error) {
    showApiError(error, SUBJECT_FIELDS, "subject-form-error");
    setSubmitting(submitButton, false, SUBJECT_SUBMIT_LABELS);
    return;
  }

  success.textContent = subjectCreatedMessage(created);
  setVisible(success, true);
  resetSubjectForm({ clearSuccess: false });
  getElement("subject-name").focus();
  await loadSubjects({ showLoading: false });
}

// 一覧の「編集」ボタン。対象の授業を控えて、編集のモーダルを開く
// （入力欄は、モーダルを開くとき（show.bs.modal）に入れる）。
function openEditModal(subject) {
  editingSubject = { ...subject };
  window.bootstrap.Modal.getOrCreateInstance(
    getElement("subject-edit-modal"),
  ).show();
}

// 編集のモーダルを開くたびに、対象の授業の今の値を入力欄に入れ、
// エラーの表示を消す。
function fillEditForm() {
  editSerial += 1;
  const subject = editingSubject;
  const startSelect = getElement("subject-edit-start-time");
  const endSelect = getElement("subject-edit-end-time");

  getElement("subject-edit-form").reset();
  removeAddedTimeOptions(startSelect);
  removeAddedTimeOptions(endSelect);
  getElement("subject-edit-modal-semester").textContent =
    currentSemester.name;
  getElement("subject-edit-name").value = subject.subject_name;
  getElement("subject-edit-room").value = subject.room ?? "";
  getElement("subject-edit-weekday").value = String(subject.weekday);
  selectTime(startSelect, subject.start_time);
  selectTime(endSelect, subject.end_time);
  getElement("subject-edit-notes").value = subject.notes ?? "";
  clearFormErrors(SUBJECT_EDIT_FIELDS, SUBJECT_EDIT_FORM_ERROR_ID);
  setSubmitting(
    getElement("subject-edit-submit-button"),
    false,
    SUBJECT_EDIT_SUBMIT_LABELS,
  );
}

async function submitSubjectEdit(event) {
  event.preventDefault();
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = editSerial;
  const subjectId = editingSubject.id;
  clearFormErrors(SUBJECT_EDIT_FIELDS, SUBJECT_EDIT_FORM_ERROR_ID);

  const submitButton = getElement("subject-edit-submit-button");
  setSubmitting(submitButton, true, SUBJECT_EDIT_SUBMIT_LABELS);

  // try で囲むのは、編集の要求だけにする（登録と同じ理由）。
  // すべての項目を送る（変えていない項目も、今の値のまま送る）。
  try {
    await apiRequest("PATCH", `/api/subjects/${subjectId}`, {
      subject_name: getElement("subject-edit-name").value,
      room: getElement("subject-edit-room").value,
      weekday: Number(getElement("subject-edit-weekday").value),
      start_time: getElement("subject-edit-start-time").value,
      end_time: getElement("subject-edit-end-time").value,
      notes: getElement("subject-edit-notes").value,
    });
  } catch (error) {
    if (startedSerial !== editSerial) {
      return;
    }
    showApiError(error, SUBJECT_EDIT_FIELDS, SUBJECT_EDIT_FORM_ERROR_ID);
    setSubmitting(submitButton, false, SUBJECT_EDIT_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === editSerial) {
    hideModal(getElement("subject-edit-modal"));
  }
  await loadSubjects({ showLoading: false });
}

// 一覧の「削除」ボタン。対象の授業を控えて、削除の確認のモーダルを開く
// （件数は、モーダルを開くとき（show.bs.modal）に取得する）。
function openDeleteModal(subject) {
  deletingSubject = { ...subject };
  window.bootstrap.Modal.getOrCreateInstance(
    getElement("subject-delete-modal"),
  ).show();
}

function showDeleteError(error) {
  const deleteError = getElement("subject-delete-error");
  deleteError.textContent = errorMessageOf(error);
  setVisible(deleteError, true);
}

function hideDeleteError() {
  const deleteError = getElement("subject-delete-error");
  deleteError.replaceChildren();
  setVisible(deleteError, false);
}

// 削除の確認のモーダルを開くたびに、対象の授業を表示し、削除される予定と
// 課題の件数を、授業の1件取得（event_count・task_count）で取得する。
// 件数が表示されるまで、「削除する」ボタンは押せない。
async function prepareDeleteModal() {
  const currentSerial = ++deleteSerial;
  const subject = deletingSubject;
  const loading = getElement("subject-delete-loading");
  const counts = getElement("subject-delete-counts");
  const submitButton = getElement("subject-delete-submit-button");

  getElement("subject-delete-target").textContent =
    `${subjectLabel(subject)}を削除します。`;
  counts.replaceChildren();
  setVisible(counts, false);
  setVisible(loading, true);
  hideDeleteError();
  submitButton.textContent = SUBJECT_DELETE_SUBMIT_LABELS.idle;
  submitButton.disabled = true;

  let detail;
  try {
    detail = await apiRequest("GET", `/api/subjects/${subject.id}`);
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
  counts.textContent =
    `この授業の予定${detail.event_count}件（今日より前の分を含む）と、` +
    `課題${detail.task_count}件も、まとめて削除されます。`;
  setVisible(counts, true);
  submitButton.disabled = false;
}

async function submitSubjectDelete() {
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = deleteSerial;
  const subjectId = deletingSubject.id;
  hideDeleteError();

  const submitButton = getElement("subject-delete-submit-button");
  setSubmitting(submitButton, true, SUBJECT_DELETE_SUBMIT_LABELS);

  // try で囲むのは、削除の要求だけにする（登録と同じ理由）。
  try {
    await apiRequest("DELETE", `/api/subjects/${subjectId}`);
  } catch (error) {
    if (startedSerial !== deleteSerial) {
      return;
    }
    showDeleteError(error);
    setSubmitting(submitButton, false, SUBJECT_DELETE_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === deleteSerial) {
    hideModal(getElement("subject-delete-modal"));
  }
  await loadSubjects({ showLoading: false });
}

export function initSubjects() {
  document.addEventListener("semester-selected", (event) => {
    currentSemester = event.detail.semester;
    requestSerial += 1;
    if (currentSemester === null) {
      clearSubjectList();
      return;
    }
    loadSubjects();
  });

  getElement("subject-retry-button").addEventListener("click", () => {
    loadSubjects();
  });
  getElement("subject-modal").addEventListener("show.bs.modal", () => {
    resetSubjectForm();
  });
  getElement("subject-modal").addEventListener("shown.bs.modal", () => {
    getElement("subject-name").focus();
  });
  getElement("subject-start-time").addEventListener("change", () => {
    adjustEndTime(
      getElement("subject-start-time"),
      getElement("subject-end-time"),
    );
  });
  getElement("subject-form").addEventListener("submit", submitSubject);

  // 編集・削除のモーダルは、成功したら、JavaScriptから閉じるため、
  // 表示の途中かを記録する（ui.js の hideModal）。
  const editModal = getElement("subject-edit-modal");
  trackModalShowing(editModal);
  editModal.addEventListener("show.bs.modal", fillEditForm);
  editModal.addEventListener("shown.bs.modal", () => {
    getElement("subject-edit-name").focus();
  });
  getElement("subject-edit-start-time").addEventListener("change", () => {
    adjustEndTime(
      getElement("subject-edit-start-time"),
      getElement("subject-edit-end-time"),
    );
  });
  getElement("subject-edit-form").addEventListener("submit", submitSubjectEdit);

  const deleteModal = getElement("subject-delete-modal");
  trackModalShowing(deleteModal);
  deleteModal.addEventListener("show.bs.modal", prepareDeleteModal);
  // 取り消せない操作のため、最初のフォーカスは「キャンセル」に置く。
  deleteModal.addEventListener("shown.bs.modal", () => {
    getElement("subject-delete-cancel-button").focus();
  });
  getElement("subject-delete-submit-button").addEventListener(
    "click",
    submitSubjectDelete,
  );
}
```
