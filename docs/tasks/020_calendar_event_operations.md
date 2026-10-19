# タスク020: カレンダーからの予定の操作

| 項目 | 内容 |
|---|---|
| Task ID | 020 |
| Task名 | カレンダーからの予定の操作の画面（空き枠のクリックで開く追加フォーム（単発の授業・アルバイト・その他（時間指定あり／締切のみ））、予定の詳細パネルの編集・削除、締切の詳細パネルの編集・削除）と、今の学期の授業から選ぶ欄の共通化（`subject_options.js`）、017-N2 |
| ブランチ | `feature/020-calendar-event-operations`（Komaが作成・切替済みの状態で渡される） |

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに停止して報告する。

**このタスクには、承認ゲートはない（DBの構造を変えないため、migrationを作らない）。** 段階1・2を順に進め、「Copilot確認手順」を実施したら、結果を報告して応答を終える。途中で止まるのは、「注意」の停止の条件に当たったときだけ。**止まるときは、報告を書いて応答を終える。質問の機能（選択肢を出して回答を待つ機能）は使わない**（`.github/copilot-instructions.md` の「止まる場面の応答」）。

**ファイルは、手で書き写さない。** 8つのファイルの全文は、このTask MDの付録にある。各段階の始めに、「全文からファイルを作るスクリプト」を実行して作る（013-N1）。付録の全文は、スクリプトが読む。付録を読んで書き写す必要はない（本文の要点・差分・確認の手順を読む）。

**報告には、コマンドの出力を、要約せずに、そのまま貼る**（014-L1）。「全文からファイルを作るスクリプト」の出力と、「Copilot確認手順」の1（実施前）の出力も、文章にまとめずに、そのまま貼る（019-N1）。「Copilot確認手順」の1・2・6は、各コマンドの前に、`echo` で見出しを出すように書いてある。**見出しの行も含めて、出力をそのまま貼る**（018-N1・019-N1）。「注意」の最後の報告の項目を参照。

**このTask MDのスクリプトとコマンドには、バックスラッシュ（`\`）の書き方を使っていない**（016-N1。改行は、スクリプトの中で `newline = chr(10)` として表す。`grep` は、`-F`（文字どおりに探す）と `-e`（探す文字列を1つずつ指定）で書く）。**コマンドは、書いてあるとおりに実行する。`grep` の `-e` を足す・減らすことも含め、書き換えた場合は、どこをどう書き換えたかを、報告に書く**（017-N1）。

## 目的
カレンダーモードから、予定の追加・編集・削除と、締切（課題・タスク）の編集・削除をできるようにする（Task 019の予定APIと、Task 016の課題・タスクAPIを使う）。設計資料（`docs/ui_ux.md` の「カレンダーモード」の「予定の追加」「予定の確認・編集・削除」「締切の詳細パネル（課題・タスク）」、`docs/architecture.md` の「JavaScriptの構成（ES modules）」「FullCalendarの使い方（`calendar.js`）」「モード間の連携（`CustomEvent`）」）の仕様を、そのまま実装する。2026-10-19に決めた次のことを含む。

- 空き枠のクリックで、追加フォームを開く（週表示の時間軸は日付と時刻、週表示の「締切」の行は「その他」の「締切のみ」、月表示の日付の枠は日付だけ）。カテゴリの初期値はアルバイト。時刻は自由入力。単発の授業の選択肢は、今の学期の授業。アルバイトの登録のあとは、カレンダーの上に、「同じ内容で別の日も登録」のボタンつきの知らせを出す
- 予定の追加・編集・削除のモーダルは、カレンダーモードの中の部品の新しいファイル `event_forms.js` に置く（`calendar.js` だけが `import` する）
- 締切の詳細パネルの「編集」「削除」は、課題・タスクモードの編集・削除のモーダルを、`CustomEvent`（`task-edit-requested`・`task-delete-requested`・`task-changed`）で使う（同じ画面を2つ作らない）
- 今の学期の授業から選ぶ欄の処理（授業の取得、欄の下の説明、選択肢の作成）を、`tasks.js` から新しい `subject_options.js` に移す（単発の授業の選択肢が、2つ目の利用者になるため）
- 017-N2（送信がエラーになったあと、Escapeキーでモーダルを閉じられない）を、`ui.js` の `setSubmitting` だけで直す（送信を始めるときに、フォーカスをモーダルに移し、終わったらボタンに戻す）
- 休講日を追加するときの確認のダイアログは、出さない（`ui_ux.md` の「未決定」を閉じた。画面は変えない）

**Python・API・DBの構造は変えない**（pytestは1021件のまま）。

| 段階 | 内容 | 挙動の変化 | 段階の終わりの `pytest` |
|---|---|---|---|
| 1 | 共通の部品と課題・タスクモード：`ui.js`（017-N2）、`subject_options.js`（新規。今の学期の授業から選ぶ欄の共通処理）、`current_semester.js`（コメントだけ）、`tasks.js`（授業の取得などを `subject_options.js` から使う。カレンダーからの依頼を購読し、編集・削除の結果を知らせる） | 送信がエラーになったあとも、Escapeキーでモーダルを閉じられる（017-N2。すべてのモーダル）。課題・タスクモードの見た目と動きは、ほかは同じ | **1021件**（Pythonを変えない） |
| 2 | カレンダー：`index.html`（追加・編集・削除のモーダル、詳細パネルの「編集」「削除」、アルバイトの知らせ、派遣会社の候補）、`event_forms.js`（新規。予定の追加・編集・削除のモーダル）、`calendar.js`（空き枠のクリック、詳細パネルの「編集」「削除」、`task-changed` の購読）、`main.js`（コメントだけ） | カレンダーから、予定の追加・編集・削除と、締切の編集・削除ができる | **1021件** |

（「全文からファイルを作るスクリプト」は、1つのファイルを1つの段階でだけ書き込む。`calendar.js`・`index.html`・`event_forms.js` は、追加・編集・削除のすべてに関わるため、段階を、共通の部品（段階1）と、カレンダー（段階2）の2つにした）

## 前提（Task 019完了時点の状態）

| 区分 | 内容 |
|---|---|
| すでにある | 学期・授業・休講日のAPIと画面、授業の編集・削除（Task 014・015）、予定API（一覧・1件取得・登録・編集・削除・派遣会社の候補。Task 012・019）、カレンダー表示（Task 013・018。予定の詳細パネルは読み取りだけ。締切の詳細パネルは、完了の切り替えだけ）、課題・タスクのAPIと画面（Task 016・017）。pytest（**1021件**。`main` の `effdf96` で確認） |
| まだない | 予定の追加フォーム、予定の編集・削除のモーダル、詳細パネルの「編集」「削除」、`subject_options.js`、`event_forms.js`。017-N2（送信がエラーになったあと、Escapeキーでモーダルを閉じられない）は、今も起きる |
| DBの構造 | 変えない（初期migration `0280f6cf8d09` と、休講日の `42bd53808fa1`）。**migrationは不要** |
| 開発用DB | `instance/app.db` は、Komaの実際の開発用DB（すべてのテーブルが0件。2026-10-19、Task 019の確認のあとにKomaが確認）。**Copilotは、書き込まない。サーバーを起動しない（`python run.py` を実行しない）**。読むのは、「Copilot確認手順」のハッシュと件数だけ。**`sqlite3` は、必ず `-readonly` を付けて実行する**（011-L1） |
| 設計資料 | このタスクの前に、更新した設計資料が `main` に反映されている。`docs/ui_ux.md` の「カレンダーモード」の「予定の追加」が詳しくなり、「予定の確認・編集・削除」に「編集（モーダル。2026-10-19に決定）」「削除（確認のモーダル。2026-10-19に決定）」の小節があり、「締切の詳細パネル（課題・タスク）」に「編集」「削除」のボタンがある。「未決定」から、休講日の確認のダイアログの項目が外れている。`docs/architecture.md` の「JavaScriptの構成（ES modules）」に、`subject_options.js`・`event_forms.js` の行と、モードの中の部品の規則、`setSubmitting` のフォーカスの規則があり、「FullCalendarの使い方（`calendar.js`）」に「空き枠のクリック」、「モード間の連携」に `task-edit-requested`・`task-delete-requested`・`task-changed` がある |
| 確認 | JavaScriptの自動テストはない。画面の動きは、Komaの確認（確認用のサーバーでのブラウザ確認。ブラウザの操作はClaude）で確かめる。Copilotは、ブラウザでの確認をしない |

## Source of Truth
- `docs/ui_ux.md`：「カレンダーモード」（「予定の追加」、「予定の確認・編集・削除」とその小節「編集」「削除」「追加・編集・削除の共通」、「締切の詳細パネル（課題・タスク）」、「共通」）、「授業モード」の「休講日」の「追加」（確認のダイアログを出さない）、「課題・タスクモード」（「一覧」のその他の追加の入口、「編集」「削除」、「追加・編集・削除の共通」）、「色・アイコン」
- `docs/architecture.md`：「JavaScriptの構成（ES modules）」（`ui.js`・`current_semester.js`・`subject_options.js`・`calendar.js`・`event_forms.js`・`tasks.js` の役割、規則。特に、モードの中の部品の規則、モーダルの規則、モーダルの中で始める要求の規則、`setSubmitting` のフォーカスの規則、`try` で囲む範囲、`textContent`、DOMの `id`、名前つきの引数）、「FullCalendarの使い方（`calendar.js`）」（「詳細パネル」「空き枠のクリック」）、「モード間の連携（`CustomEvent`）」、「予定API」（登録・編集・削除の項目、派遣会社の候補）、「課題・タスクAPI」（その他（締切のみ）の登録）、「カレンダーからの授業の予定の操作」、「`api.js` の仕様」
- `docs/requirements.md`：「予定の登録」、「予定の編集・削除」
- `.github/copilot-instructions.md`：進め方、「止まる場面の応答」、コーディング方針（JavaScript）

## 実装対象ファイル

| 区分 | ファイル | 段階 | 内容 | 全文 |
|---|---|---|---|---|
| 変更 | `app/static/js/ui.js` | 1 | `setSubmitting` のフォーカスの扱い（017-N2）。ほかの関数は変えない | 付録A |
| 新規 | `app/static/js/subject_options.js` | 1 | 今の学期の授業から選ぶ欄の共通処理（`fetchCurrentSubjects`・`currentSubjectsNote`・`renderSubjectOptions`・`SUBJECTS_LOADING_NOTE`）。`tasks.js` から移した | 付録B |
| 変更 | `app/static/js/current_semester.js` | 1 | 先頭のコメントだけ（使う場所に `subject_options.js` を書く） | 付録C |
| 変更 | `app/static/js/tasks.js` | 1 | 授業の取得・説明・選択肢を `subject_options.js` から使う。`task-edit-requested`・`task-delete-requested` を購読し、編集・削除に成功したら `task-changed` を発行する | 付録D |
| 変更 | `app/templates/index.html` | 2 | アルバイトの知らせ、予定・締切の詳細パネルの「削除」「編集」、追加・編集・削除のモーダル、派遣会社の候補（`datalist`） | 付録E |
| 新規 | `app/static/js/event_forms.js` | 2 | 予定の追加（その他（締切のみ）を含む）・編集・削除の確認のモーダルと、アルバイトの知らせ | 付録F |
| 変更 | `app/static/js/calendar.js` | 2 | 空き枠のクリック（`dateClick`）、詳細パネルの「編集」「削除」、`event_forms.js` の初期化、`task-changed` の購読 | 付録G |
| 変更 | `app/static/js/main.js` | 2 | コメントだけ（課題・タスクとカレンダーが、イベントでつながること） | 付録H |

上の8ファイル以外は、変更しない（`__pycache__/` などの、`.gitignore` の対象は除く）。**8ファイルとも、このTask MDの付録に全文がある。「全文からファイルを作るスクリプト」で作り、手で書き写さない。書き込んだあとに、手で直さない。** 全文を変える必要があると判断した場合は、変えずに停止して報告する。

## 非対象（このタスクでは作らない・変更しない）
- Pythonのファイル（`app/` の `.py`、`run.py`）、`tests/`（**テストは変えない・足さない**）、`migrations/`（**`flask db` のコマンドを、一切実行しない**）、`requirements.txt`（**ライブラリを追加しない**）、`pytest.ini`
- `app/templates/base.html`、`app/static/css/style.css`、`app/static/js/` の上の7つ以外のファイル（`api.js`・`dates.js`・`categories.js`・`task_display.js`・`semesters.js`・`subjects.js`・`closures.js`）。017-N2は、`ui.js` の `setSubmitting` だけで直す（各モードのファイルは変えない）
- `index.html` の、上の「内容」に書いた部分以外（授業モード・課題・タスクモードの部分、既存のモーダルの中身）
- `docs/`、`.github/`、`.gitignore`
- 作らないもの：キーボードや一覧表示から予定を追加するための入口（「予定を追加」のボタンなど）、範囲を選んで追加する操作（FullCalendarの `selectable`）、休講日を追加するときの確認のダイアログ（出さないと決めた）、カレンダーへの休講日の表示、複数日のアルバイトの一括登録、日付をまたぐ予定を1件で表す仕組み、学期の変更・削除
- 持ち越しの003-H（Task 021で扱う）
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
        "app/static/js/ui.js",
        "app/static/js/subject_options.js",
        "app/static/js/current_semester.js",
        "app/static/js/tasks.js",
    ],
    "2": [
        "app/templates/index.html",
        "app/static/js/event_forms.js",
        "app/static/js/calendar.js",
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
full_texts = read_full_texts("docs/tasks/020_calendar_event_operations.md")
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
| 1（`python - 1`） | `全文の数：8`、`app/static/js/ui.js：書き込み（160行）`、`app/static/js/subject_options.js：書き込み（66行）`、`app/static/js/current_semester.js：書き込み（43行）`、`app/static/js/tasks.js：書き込み（610行）` |
| 2（`python - 2`） | `全文の数：8`、`app/templates/index.html：書き込み（821行）`、`app/static/js/event_forms.js：書き込み（755行）`、`app/static/js/calendar.js：書き込み（814行）`、`app/static/js/main.js：書き込み（19行）` |

- 出力が上と違う場合（全文の数・行数・エラー）は、ほかの作業をせずに停止して報告する
- 段階の終わりの「全文との比較」（「Copilot確認手順」の4）で「不一致」が出た場合は、手で直さず、その段階のスクリプトをもう一度実行して、全文に戻す。戻したことと、違っていた理由（分かれば）を、報告に書く（013-N1）
- **スクリプトの出力は、報告に、そのまま貼る**（019-N1）

## 段階1：共通の部品と課題・タスクモード

### 1-1. `app/static/js/ui.js`（全文：付録A）
`setSubmitting(button, submitting, labels)` に、フォーカスの扱いを足す（017-N2。`docs/architecture.md` の「JavaScriptの構成」の、`setSubmitting` の規則）。引数・名前・ほかの関数は変えない（各モードのファイルは、変えずに、この直しの効果を受ける）。

- 原因：送信中にボタンを押せなくする（`disabled`）と、そのボタンにあったフォーカスが、ページ本体（`document.body`）に移る。Bootstrapのモーダルは、モーダルの中で押されたEscapeキーで閉じるため、フォーカスがページ本体にあると、Escapeキーで閉じられない（「キャンセル」・×では閉じられる）
- 送信を始めるとき（`submitting` が `true`）：ボタンにフォーカスがあれば、そのボタンを覚えておく（`WeakSet`）。押せなくしたあと、覚えたボタンがモーダルの中（`button.closest(".modal")`）なら、フォーカスをモーダルの要素に移す（モーダルの要素は `tabindex="-1"` のため、フォーカスを受けられる）
- 送信が終わったとき（`submitting` が `false`）：覚えたボタンなら、覚えを消し、フォーカスがモーダルの要素かページ本体にあれば、ボタンに戻す。フォーカスがほかの欄にあれば（成功のあとに、授業の連続登録が科目名の欄へ移した、など）、変えない
- モーダルの外のボタン（休講日の「追加する」「削除」）も、失敗のあとに、フォーカスがボタンに戻る（送信中は、今までどおり、ページ本体）
- Enterキーで送信した場合（フォーカスが入力欄にある）は、ボタンにフォーカスがないため、何もしない（フォーカスは入力欄のまま）

`main` からの差分（確認用）：

```diff
--- a/app/static/js/ui.js
+++ b/app/static/js/ui.js
@@ -88,10 +88,38 @@ export function showApiError(error, fieldMap, formErrorId) {
   showFormMessage(formErrorId, errorMessageOf(error));
 }
 
+// 送信を始めたときに、フォーカスがあったボタン（送信が終わったら、
+// フォーカスを戻す）。
+const focusReturnButtons = new WeakSet();
+
 // 送信中の表示。labels は { idle: 通常の文字, busy: 送信中の文字 } の形。
+// 押せなくしたボタンからは、フォーカスがページ本体に移り、モーダルを
+// Escapeキーで閉じられなくなる（017-N2）。そのため、送信を始めるときに、
+// ボタンにフォーカスがあれば覚えておき、ボタンがモーダルの中なら、
+// フォーカスをモーダル（の要素）に移す。送信が終わって、ボタンを押せる
+// ように戻すときに、フォーカスがモーダルかページ本体にあれば、ボタンに
+// 戻す（ほかの欄に移していれば、そのまま）。
 export function setSubmitting(button, submitting, labels) {
+  const modal = button.closest(".modal");
+  if (submitting && document.activeElement === button) {
+    focusReturnButtons.add(button);
+  }
   button.disabled = submitting;
   button.textContent = submitting ? labels.busy : labels.idle;
+
+  if (submitting) {
+    if (focusReturnButtons.has(button) && modal !== null) {
+      modal.focus();
+    }
+    return;
+  }
+  if (!focusReturnButtons.delete(button)) {
+    return;
+  }
+  const active = document.activeElement;
+  if (active === document.body || active === modal) {
+    button.focus();
+  }
 }
 
 // 表示のアニメーションの途中（show.bs.modal から shown.bs.modal まで）の
```

### 1-2. `app/static/js/subject_options.js`（新規。全文：付録B）
今の学期の授業から選ぶ欄（プルダウン）の共通処理。課題の対象授業（`tasks.js`）と、カレンダーから追加する単発の授業（`event_forms.js`）で使う（モードのファイル同士は、互いを `import` しないため。`docs/architecture.md` の「JavaScriptの構成」の `subject_options.js` の行）。中身は、`tasks.js` の今の処理と同じ（名前だけ変えた）。

| 公開するもの | 内容 | `tasks.js` の今の名前 |
|---|---|---|
| `SUBJECTS_LOADING_NOTE` | 定数「授業を読み込み中…」 | `SUBJECT_LOADING_NOTE` |
| `fetchCurrentSubjects()` | 今の学期（`current_semester.js` の `chooseCurrentSemester`。「今日」は `dates.js` の `localDateString()`）と、その学期の授業の一覧を取得し、`{ semester, subjects }` を返す。学期が0件なら `{ semester: null, subjects: [] }` | `fetchCurrentSubjects` |
| `currentSubjectsNote(semester, subjects)` | 欄の下の説明の文（学期がない／授業がない／「2026年度 後期の授業から選びます」） | `subjectNoteOf` |
| `renderSubjectOptions(select, subjects, extraSubject = null)` | プルダウンの選択肢を作る。先頭は「選択してください」（値は空）。`extraSubject` があれば、先頭の次に足す（課題の編集で、今の対象授業が今の学期にないとき） | `renderSubjectOptions`（`extraSubject` を省略できるようにした） |

「選択してください」の文字は、このファイルの中の定数（`SUBJECT_PLACEHOLDER`。公開しない）。

### 1-3. `app/static/js/current_semester.js`（全文：付録C）
要点：先頭のコメントだけを変える（使う場所を、「課題の対象授業の選択肢」から、「今の学期の授業から選ぶ欄（`subject_options.js`。課題の対象授業と、単発の授業）」にする）。関数は変えない。DOMとAPIは、今までどおり扱わない。

`main` からの差分（確認用）：

```diff
--- a/app/static/js/current_semester.js
+++ b/app/static/js/current_semester.js
@@ -1,5 +1,6 @@
 // 今の学期を選ぶ規則。複数のモードで使うため、このファイルにまとめる
-// （授業モードの学期の初期選択と、課題の対象授業の選択肢）。
+// （授業モードの学期の初期選択と、今の学期の授業から選ぶ欄
+// （subject_options.js。課題の対象授業と、単発の授業））。
 // DOMとAPIは扱わない。
 
 // semesters は、学期のAPIの一覧の並び（開始日の新しい順。タブの並び）の
```

### 1-4. `app/static/js/tasks.js`（全文：付録D）
要点：
- `renderSubjectOptions`・`fetchCurrentSubjects`・`subjectNoteOf` と、定数 `SUBJECT_PLACEHOLDER`・`SUBJECT_LOADING_NOTE` を消し、`subject_options.js` から `import` する（`subjectNoteOf` は `currentSubjectsNote`、`SUBJECT_LOADING_NOTE` は `SUBJECTS_LOADING_NOTE`）。使わなくなった `current_semester.js` の `import` と、`dates.js` の `localDateString` の `import` を消す。呼び出しは、引数も含めて、今と同じ（`renderSubjectOptions(select, [], null)` など）
- `notifyTaskChanged()`（新規）：`document` に `CustomEvent("task-changed")` を発行する（`detail` はない）。課題・タスクの編集（`submitTaskEdit`）と削除（`submitTaskDelete`）に成功したときに、モーダルを閉じたあと、一覧を取得し直す前に呼ぶ（モーダルを開き直していても呼ぶ。データは変わっているため）。カレンダーが、締切と「直近の締切」欄を取得し直す
- `initTasks` で、`task-edit-requested` と `task-delete-requested` を購読する。届いたら、`event.detail.task`（課題・タスクのコピー）で、今の `openEditModal`・`openDeleteModal` を呼ぶ（一覧の「編集」「削除」と同じ関数。カレンダーの締切の詳細パネルの「編集」「削除」から開く）
- 追加と完了の切り替えでは、`task-changed` を発行しない（`docs/architecture.md` の「モード間の連携」）
- 一覧の表示、完了の切り替え、追加・編集・削除の動きは変わらない

`main` からの差分（確認用）：

```diff
--- a/app/static/js/tasks.js
+++ b/app/static/js/tasks.js
@@ -1,10 +1,11 @@
 import { apiRequest } from "./api.js";
-import { chooseCurrentSemester } from "./current_semester.js";
+import { formatJapaneseDateTime, localDateTimeString } from "./dates.js";
 import {
-  formatJapaneseDateTime,
-  localDateString,
-  localDateTimeString,
-} from "./dates.js";
+  SUBJECTS_LOADING_NOTE,
+  currentSubjectsNote,
+  fetchCurrentSubjects,
+  renderSubjectOptions,
+} from "./subject_options.js";
 import {
   createOverdueBadge,
   createTaskTitle,
@@ -27,8 +28,6 @@ import {
 const ASSIGNMENT = "assignment";
 // 締切時刻の初期値（課題は、23:59の締切が多いため）。
 const DEFAULT_DUE_TIME = "23:59";
-const SUBJECT_PLACEHOLDER = "選択してください";
-const SUBJECT_LOADING_NOTE = "授業を読み込み中…";
 
 const TASK_FIELDS = {
   title: {
@@ -282,55 +281,11 @@ async function toggleTaskCompleted(task, checkbox) {
   await loadTasks({ showLoading: false });
 }
 
-// 対象授業のプルダウンの選択肢を作る。先頭は「選択してください」（値は空）。
-// extraSubject は、今の学期の授業の一覧にない、課題の今の対象授業（編集の
-// とき。{ id, subject_name }）。ないときは null。
-function renderSubjectOptions(select, subjects, extraSubject) {
-  const placeholder = document.createElement("option");
-  placeholder.value = "";
-  placeholder.textContent = SUBJECT_PLACEHOLDER;
-  const options = [placeholder];
-  const items =
-    extraSubject === null ? subjects : [extraSubject, ...subjects];
-  for (const subject of items) {
-    const option = document.createElement("option");
-    option.value = String(subject.id);
-    option.textContent = subject.subject_name;
-    options.push(option);
-  }
-  select.replaceChildren(...options);
-}
-
-// 今の学期（授業モードで最初に選ばれる学期と同じ規則。current_semester.js）
-// と、その学期の授業の一覧を取得する。学期が0件なら、semester は null。
-async function fetchCurrentSubjects() {
-  const semesters = await apiRequest("GET", "/api/semesters");
-  const semester = chooseCurrentSemester(semesters, localDateString());
-  if (semester === null) {
-    return { semester: null, subjects: [] };
-  }
-  const subjects = await apiRequest(
-    "GET",
-    `/api/subjects?semester_id=${semester.id}`,
-  );
-  return { semester, subjects };
-}
-
-// 対象授業の欄の下に出す説明。
-function subjectNoteOf(semester, subjects) {
-  if (semester === null) {
-    return (
-      "学期が登録されていません。" +
-      "授業モードで、学期と授業を登録してください"
-    );
-  }
-  if (subjects.length === 0) {
-    return (
-      `${semester.name}には、授業が登録されていません。` +
-      "授業モードで、授業を登録してください"
-    );
-  }
-  return `${semester.name}の授業から選びます`;
+// 課題・タスクを編集・削除したことを、ほかのモード（カレンダーの締切と
+// 「直近の締切」欄）に知らせる（モードのファイル同士は、互いを import
+// しないため、CustomEvent でつなぐ）。
+function notifyTaskChanged() {
+  document.dispatchEvent(new CustomEvent("task-changed"));
 }
 
 // 追加のモーダルを開くたびに、入力欄を初期値に戻し、今の学期の授業を
@@ -354,7 +309,7 @@ async function prepareAddModal() {
   // 授業を取得するまでは、「選択してください」だけ（必須のため、
   // ブラウザの入力チェックで、登録は止まる）。
   renderSubjectOptions(select, [], null);
-  note.textContent = SUBJECT_LOADING_NOTE;
+  note.textContent = SUBJECTS_LOADING_NOTE;
 
   let result;
   try {
@@ -373,7 +328,7 @@ async function prepareAddModal() {
     return;
   }
   renderSubjectOptions(select, result.subjects, null);
-  note.textContent = subjectNoteOf(result.semester, result.subjects);
+  note.textContent = currentSubjectsNote(result.semester, result.subjects);
 }
 
 async function submitTask(event) {
@@ -411,7 +366,8 @@ async function submitTask(event) {
   await loadTasks({ showLoading: false });
 }
 
-// 一覧の「編集」ボタン。対象を控えて、編集のモーダルを開く（入力欄は、
+// 一覧の「編集」ボタンと、カレンダーの締切の詳細パネルの「編集」
+// （task-edit-requested）。対象を控えて、編集のモーダルを開く（入力欄は、
 // モーダルを開くとき（show.bs.modal）に入れる）。
 function openEditModal(task) {
   editingTask = { ...task };
@@ -467,7 +423,7 @@ async function prepareEditModal() {
   };
   renderSubjectOptions(select, [], currentSubject);
   select.value = String(task.subject_id);
-  note.textContent = SUBJECT_LOADING_NOTE;
+  note.textContent = SUBJECTS_LOADING_NOTE;
 
   let result;
   try {
@@ -495,7 +451,7 @@ async function prepareEditModal() {
     inCurrentSemester ? null : currentSubject,
   );
   select.value = String(task.subject_id);
-  note.textContent = subjectNoteOf(result.semester, result.subjects);
+  note.textContent = currentSubjectsNote(result.semester, result.subjects);
 }
 
 async function submitTaskEdit(event) {
@@ -535,10 +491,12 @@ async function submitTaskEdit(event) {
   if (startedSerial === editSerial) {
     hideModal(getElement("task-edit-modal"));
   }
+  notifyTaskChanged();
   await loadTasks({ showLoading: false });
 }
 
-// 一覧の「削除」ボタン。対象を控えて、削除の確認のモーダルを開く。
+// 一覧の「削除」ボタンと、カレンダーの締切の詳細パネルの「削除」
+// （task-delete-requested）。対象を控えて、削除の確認のモーダルを開く。
 function openDeleteModal(task) {
   deletingTask = { ...task };
   window.bootstrap.Modal.getOrCreateInstance(
@@ -596,6 +554,7 @@ async function submitTaskDelete() {
   if (startedSerial === deleteSerial) {
     hideModal(getElement("task-delete-modal"));
   }
+  notifyTaskChanged();
   await loadTasks({ showLoading: false });
 }
 
@@ -610,6 +569,14 @@ export function initTasks() {
   getElement("task-retry-button").addEventListener("click", () => {
     loadTasks();
   });
+  // カレンダーの締切の詳細パネルの「編集」「削除」で、このモードの編集・
+  // 削除のモーダルを開く（detail.task は、課題・タスクのコピー）。
+  document.addEventListener("task-edit-requested", (event) => {
+    openEditModal(event.detail.task);
+  });
+  document.addEventListener("task-delete-requested", (event) => {
+    openDeleteModal(event.detail.task);
+  });
 
   // 追加・編集・削除のモーダルは、成功したら、JavaScriptから閉じるため、
   // 表示の途中かを記録する（ui.js の hideModal）。
```

## 段階2：カレンダー

### 2-1. `app/templates/index.html`（全文：付録E）
要点（足すだけ。既存の部分の中身は変えない）：
- カレンダーモードの絞り込みの行の下（2つの列の上）に、アルバイトを登録したことの知らせ（`event-added-notice`。`alert alert-success`、`role="status"`。最初は隠す）：メッセージ（`event-added-notice-message`）、「同じ内容で別の日も登録」ボタン（`event-repeat-button`）、閉じるボタン（`event-added-notice-close-button`。×、`aria-label="閉じる"`）
- 予定の詳細パネル（`event-modal`）の下のボタンを、「削除」（`event-modal-delete-button`。`btn-outline-danger`、`me-auto` で左）、「編集」（`event-modal-edit-button`）、「閉じる」（今までのもの）にする。締切の詳細パネル（`task-detail-modal`）も同じ（`task-detail-delete-button`・`task-detail-edit-button`）。「削除」「編集」には `data-bs-dismiss` を付けない（JavaScriptで閉じる）
- 締切の詳細パネルのあとに、3つのモーダルと `datalist` を足す（`<main>` の外。`fade`）
  - 予定の追加（`event-add-modal`。フォーム `event-add-form`）：見出し「予定を追加」、フォームの上部のエラー、カテゴリ（`fieldset` と `legend`「カテゴリ」。ボタンの形のラジオボタン（`btn-check`）3つ：`name="event-add-category"`、値 `class`・`part_time`・`other`、ラベル「授業（補講など）」「アルバイト」「その他」）、その他の種類（`fieldset` `event-add-other-type-row`、`legend`「その他の種類」。ラジオボタン2つ：`name="event-add-other-type"`、値 `timed`「時間指定あり」・`deadline`「締切のみ」）、授業の欄（`event-add-subject-row`：プルダウン、説明、エラー）、タイトルの欄（`event-add-title-row`：ラベル `event-add-title-label` の文字は JavaScript が入れる）、派遣会社の欄（`event-add-employer-row`：`list="event-employer-options"`、`autocomplete="off"`）、日付の欄（`event-add-date-row`）、時刻の欄（`event-add-time-row`：開始時刻・終了時刻。`type="time"`）、締切の欄（`event-add-due-row`：締切日・締切時刻と、まとめたエラー）、教室の欄（`event-add-room-row`）、詳細・メモ。ボタンは「キャンセル」（`data-bs-dismiss`）と「登録する」（`event-add-submit-button`、`type="submit"`）
  - 予定の編集（`event-edit-modal`。フォーム `event-edit-form`）：見出し「予定を編集」、フォームの上部のエラー、カテゴリの表示（アイコン `event-edit-category-icon`・表示名 `event-edit-category`）、授業の表示（`event-edit-subject-row`・`event-edit-subject`）、タイトル・派遣会社・日付の欄（追加と同じ形）、変えられない日付の表示（`event-edit-fixed-date-row`：日付 `event-edit-fixed-date` と、自動生成の予定の注意書き）、開始時刻・終了時刻、教室、詳細・メモ。ボタンは「キャンセル」と「保存する」（`event-edit-submit-button`）
  - 予定の削除（`event-delete-modal`）：見出し「予定を削除」、対象（`event-delete-target`）、自動生成の予定の注意（`event-delete-generated-note`。最初は隠す。文字は JavaScript が入れる）、エラー（`event-delete-error`）、「削除は取り消せません。」（`event-delete-warning`）。モーダルと「削除する」ボタン（`event-delete-submit-button`）の `aria-describedby` は、`event-delete-target event-delete-generated-note event-delete-warning`。「キャンセル」（`event-delete-cancel-button`）
  - 派遣会社の候補（`<datalist id="event-employer-options">`。中の `option` は JavaScript が作る。追加と編集の派遣会社の欄で共有する）
- 授業・課題のモーダルと同じく、エラーの表示の `id` は `<項目>-error`。項目の欄の `id` は `<モーダル>-<項目>-row`（JavaScriptが、カテゴリによって表示・非表示を切り替える）

足すDOMの `id`（86個）：

| 場所 | `id` |
|---|---|
| アルバイトの知らせ（4個） | `event-added-notice`、`event-added-notice-message`、`event-repeat-button`、`event-added-notice-close-button` |
| 詳細パネルのボタン（4個） | `event-modal-delete-button`、`event-modal-edit-button`、`task-detail-delete-button`、`task-detail-edit-button` |
| 予定の追加（39個） | `event-add-modal`、`event-add-modal-title`、`event-add-form`、`event-add-form-error`、`event-add-category-class`、`event-add-category-part-time`、`event-add-category-other`、`event-add-other-type-row`、`event-add-other-type-timed`、`event-add-other-type-deadline`、`event-add-subject-row`、`event-add-subject`、`event-add-subject-note`、`event-add-subject-error`、`event-add-title-row`、`event-add-title-label`、`event-add-title`、`event-add-title-error`、`event-add-employer-row`、`event-add-employer`、`event-add-employer-error`、`event-add-date-row`、`event-add-date`、`event-add-date-error`、`event-add-time-row`、`event-add-start-time`、`event-add-start-time-error`、`event-add-end-time`、`event-add-end-time-error`、`event-add-due-row`、`event-add-due-date`、`event-add-due-time`、`event-add-due-error`、`event-add-room-row`、`event-add-room`、`event-add-room-error`、`event-add-notes`、`event-add-notes-error`、`event-add-submit-button` |
| 予定の編集（30個） | `event-edit-modal`、`event-edit-modal-title`、`event-edit-form`、`event-edit-form-error`、`event-edit-category-icon`、`event-edit-category`、`event-edit-subject-row`、`event-edit-subject`、`event-edit-title-row`、`event-edit-title-label`、`event-edit-title`、`event-edit-title-error`、`event-edit-employer-row`、`event-edit-employer`、`event-edit-employer-error`、`event-edit-date-row`、`event-edit-date`、`event-edit-date-error`、`event-edit-fixed-date-row`、`event-edit-fixed-date`、`event-edit-start-time`、`event-edit-start-time-error`、`event-edit-end-time`、`event-edit-end-time-error`、`event-edit-room-row`、`event-edit-room`、`event-edit-room-error`、`event-edit-notes`、`event-edit-notes-error`、`event-edit-submit-button` |
| 予定の削除（8個） | `event-delete-modal`、`event-delete-modal-title`、`event-delete-target`、`event-delete-generated-note`、`event-delete-error`、`event-delete-warning`、`event-delete-cancel-button`、`event-delete-submit-button` |
| 派遣会社の候補（1個） | `event-employer-options` |

### 2-2. `app/static/js/event_forms.js`（新規。全文：付録F）
カレンダーモードの中の部品（`docs/architecture.md` の「JavaScriptの構成」の `event_forms.js` の行と、モードの中の部品の規則）。予定の追加（その他（締切のみ）を含む）・編集・削除の確認のモーダルと、アルバイトを登録したことの知らせを扱う。**`calendar.js` だけが `import` する。** ほかのモードのファイル（`tasks.js` など）は `import` しない。

ファイルの構成（上から順に）：

| 名前 | 種類 | 内容 |
|---|---|---|
| `CLASS`・`PART_TIME`・`OTHER` | 定数 | 予定のカテゴリの保存値 `"class"`・`"part_time"`・`"other"`（締切のみは、課題・タスクのその他として登録する。保存値は、予定のその他と同じ `"other"`） |
| `DEFAULT_CATEGORY` | 定数 | 追加フォームのカテゴリの初期値（`PART_TIME`） |
| `CATEGORY_RADIO_IDS` | 定数 | カテゴリの保存値 → ラジオボタンの `id` |
| `DEFAULT_START_TIME`・`DEFAULT_END_TIME`・`DEFAULT_DUE_TIME`・`LAST_TIME` | 定数 | `"09:00"`・`"10:00"`（時刻のないクリックの初期値）、`"23:59"`（締切時刻の初期値）、`"23:59"`（1日の最後の時刻。終了時刻を1時間後に合わせるときの上限） |
| `ADD_FIELDS`・`EDIT_FIELDS` | 定数 | APIの `fields` の項目 → 入力欄とエラーの表示の `id`（`ui.js` の `showApiError`・`clearFormErrors` の形）。追加は、`subject_id`・`title`・`employer`・`date`・`start_time`・`end_time`・`due_datetime`（締切日・締切時刻の2つの欄）・`room`・`notes`。編集は、`title`・`employer`・`date`・`start_time`・`end_time`・`room`・`notes` |
| `ADD_FORM_ERROR_ID`・`ADD_SUBMIT_LABELS`・`EDIT_FORM_ERROR_ID`・`EDIT_SUBMIT_LABELS`・`DELETE_SUBMIT_LABELS`・`GENERATED_DELETE_NOTE` | 定数 | フォームの上部のエラーの `id`、ボタンの文字（「登録する」「登録中…」、「保存する」「保存中…」、「削除する」「削除中…」）、削除の確認の注意の文 |
| `notifyEventsChanged`・`notifyTasksChanged` | 変数 | 登録・編集・削除ができたときに呼ぶ関数（`initEventForms` で受け取る） |
| `addValues`・`addFocusId`・`editFocusId`・`addSubjects`・`lastPartTimeEvent`・`editingEvent`・`deletingEvent` | 変数 | 追加フォームを開くときに入れる値、最初にフォーカスを置く欄、追加フォームの授業の選択肢（教室の初期値に使う）、最後に登録したアルバイト（「同じ内容で別の日も登録」）、編集・削除の対象（予定のコピー） |
| `addSerial`・`editSerial`・`deleteSerial`・`employerSerial` | 変数 | モーダルを開くたびに増やす通し番号（古い応答で、今のモーダルの表示を変えないため）と、派遣会社の候補の取得の通し番号 |
| `eventLabel(apiEvent)` | 関数 | 予定を表す文字列「「タイトル」（2026年10月24日（土） 17:00 〜 21:00）」（日付は `formatJapaneseDateWithWeekday`）。知らせと削除の確認の文に使う |
| `oneHourLater(time)` | 関数 | 時刻（`HH:MM`）の1時間後。23時台は `LAST_TIME` |
| `adjustEndTime(startInputId, endInputId)` | 関数 | 開始時刻が空でなく、終了時刻が開始時刻以下なら、終了時刻を `oneHourLater(開始時刻)` にする（文字列の大小で比べる） |
| `setFieldRowVisible(rowId, inputIds, visible)` | 関数 | 欄を表示・非表示にし、中の入力欄を、表示するときだけ使えるようにする（隠した入力欄は `disabled`。隠した欄の入力チェック（必須）で、送信が止まらないため） |
| `showModal(modalId)` | 関数 | モーダルを、`window.bootstrap.Modal.getOrCreateInstance(...).show()` で開く |
| `loadEmployerOptions()` | 関数 | 派遣会社の候補（`GET /api/events/employers`）で、`datalist` の `option` を作り直す。失敗しても、何も表示しない（`ApiError` でない例外だけ、`console.error`）。古い応答は捨てる |
| `selectedAddCategory()`・`isDeadlineOnly()` | 関数 | 追加フォームで選んでいるカテゴリ（保存値）と、その他の「締切のみ」か |
| `applyAddCategory()` | 関数 | 追加フォームの欄を、選んでいるカテゴリに合わせる（下の表）。入力した値は変えない。タイトルの欄の名前は、アルバイトは「仕事内容」、ほかは「タイトル」 |
| `openEventAddModal({ date, time = null, deadlineOnly = false })` | 関数（`export`） | 追加フォームを開く（下の「追加フォームを開くときの値」）。`calendar.js` の空き枠のクリックから呼ぶ |
| `openRepeatAddModal()` | 関数 | 「同じ内容で別の日も登録」。`lastPartTimeEvent` の日付以外を入れて、追加フォームを開く |
| `showAddedNotice(createdEvent)`・`hideAddedNotice()` | 関数 | アルバイトを登録したことの知らせの表示（「`eventLabel` を登録しました。」。`lastPartTimeEvent` に控える）・消去 |
| `loadAddSubjects(currentSerial)` | 関数 | 追加フォームの授業の選択肢を、`fetchCurrentSubjects` で作る（下の順序） |
| `fillRoomFromSubject()` | 関数 | 授業の選択が変わったら、その授業の教室（なければ空）を、教室の欄に入れる |
| `prepareAddModal()` | 関数 | 追加のモーダルの `show.bs.modal`（下の順序） |
| `addRequestOf()` | 関数 | 追加フォームの値から、登録の要求（URLと本文）を作る（下の表） |
| `submitEventAdd(event)` | 関数 | 追加フォームの送信（下の順序） |
| `hasFixedDate(apiEvent)` | 関数 | 日付を変えられない予定か（`apiEvent.is_generated`。自動生成の予定は、授業の予定だけ） |
| `openEventEditModal(apiEvent)` | 関数（`export`） | 対象のコピーを控えて、編集のモーダルを開く（値は、`show.bs.modal` で入れる） |
| `prepareEditModal()` | 関数 | 編集のモーダルの `show.bs.modal`（下の順序） |
| `editRequestBodyOf(target)` | 関数 | 編集の本文（下の表） |
| `submitEventEdit(event)` | 関数 | 編集のフォームの送信（追加と同じ形。`PATCH /api/events/<id>`。成功したら、開き直していなければ閉じ、`notifyEventsChanged()`） |
| `openEventDeleteModal(apiEvent)` | 関数（`export`） | 対象のコピーを控えて、削除の確認のモーダルを開く |
| `showDeleteError`・`hideDeleteError` | 関数 | 削除の確認のモーダルのエラーの表示・消去 |
| `prepareDeleteModal()` | 関数 | 削除の確認のモーダルの `show.bs.modal`：`deleteSerial` を増やす。対象（「`eventLabel` を削除します。」）を入れる。自動生成の予定なら、注意（`GENERATED_DELETE_NOTE`）を入れて表示し、そうでなければ、注意の文字を空にして隠す（空にするのは、隠しても、`aria-describedby` で読み上げられるため）。エラーを消し、ボタンを戻す |
| `submitEventDelete()` | 関数 | 削除（`DELETE /api/events/<id>`。授業・課題の削除と同じ形。成功したら、開き直していなければ閉じ、`notifyEventsChanged()`） |
| `initEventForms({ onEventsChanged, onTasksChanged })` | 関数（`export`） | 初期化（下の一覧） |

追加フォームの欄（`applyAddCategory`。○は表示。隠した欄の入力欄は `disabled`）：

| 欄 | 授業 | アルバイト | その他（時間指定あり） | その他（締切のみ） |
|---|---|---|---|---|
| その他の種類（`event-add-other-type-row`） | | | ○ | ○ |
| 授業（`event-add-subject-row`） | ○ | | | |
| タイトル（`event-add-title-row`） | | ○（「仕事内容」） | ○ | ○ |
| 派遣会社（`event-add-employer-row`） | | ○ | | |
| 日付（`event-add-date-row`） | ○ | ○ | ○ | |
| 時刻（`event-add-time-row`） | ○ | ○ | ○ | |
| 締切（`event-add-due-row`） | | | | ○ |
| 教室（`event-add-room-row`） | ○ | | | |

追加フォームを開くときの値（`addValues`）：

| 開き方 | カテゴリ | 日付 | 開始・終了時刻 | 締切日・締切時刻 | 仕事内容・タイトル、派遣会社、メモ | 最初のフォーカス |
|---|---|---|---|---|---|---|
| `openEventAddModal({ date, time })`（週表示の時間軸） | アルバイト（時間指定あり） | `date` | `time` と `oneHourLater(time)` | `date` と `time` | 空 | 仕事内容の欄 |
| `openEventAddModal({ date })`（月表示の日付の枠） | アルバイト（時間指定あり） | `date` | `09:00`・`10:00` | `date` と `23:59` | 空 | 仕事内容の欄 |
| `openEventAddModal({ date, deadlineOnly: true })`（週表示の「締切」の行） | その他（締切のみ） | `date` | `09:00`・`10:00` | `date` と `23:59` | 空 | タイトルの欄 |
| `openRepeatAddModal()`（「同じ内容で別の日も登録」） | アルバイト（時間指定あり） | 空 | 最後に登録したアルバイトの時刻 | 空と `23:59` | 最後に登録したアルバイトの値（`null` は空） | 日付の欄 |

（最初のフォーカスは、カテゴリが授業なら授業の欄、ほかはタイトル（仕事内容）の欄。「同じ内容で別の日も登録」だけは、日付の欄。教室は、どの開き方でも空）

`prepareAddModal`（追加のモーダルを開くとき）の順序：
1. `addSerial` を増やして控える。アルバイトの知らせを消す（`hideAddedNotice`）
2. フォームを `reset()` し、`addValues` のカテゴリのラジオボタン、その他の種類（`deadlineOnly` なら「締切のみ」、そうでなければ「時間指定あり」）を選び、各欄に値を入れる（教室は空）
3. エラーを消し（`clearFormErrors`）、「登録する」ボタンを戻す（`setSubmitting(…, false, …)`）。`applyAddCategory()` で欄を合わせ、最初のフォーカスの欄（`addFocusId`）を決める
4. `loadAddSubjects(控えた通し番号)` と `loadEmployerOptions()` を呼ぶ（待たない）

`loadAddSubjects(currentSerial)` の順序：
1. `addSubjects` を空にし、選択肢を「選択してください」だけにする（`renderSubjectOptions(select, [])`）。欄の下に `SUBJECTS_LOADING_NOTE`
2. `fetchCurrentSubjects()`（`try` で囲むのは、この要求だけ）
3. どちらの場合も、モーダルを開き直していれば（`currentSerial` が `addSerial` と違えば）、何もしない
4. 失敗：欄の下に、エラーメッセージ（`errorMessageOf`）を出す（選択肢は「選択してください」だけ。授業の予定は、ブラウザの入力チェックで止まる。ほかのカテゴリは登録できる）
5. 成功：`addSubjects` に入れ、選択肢を作り、欄の下に `currentSubjectsNote`

登録の要求（`addRequestOf`）：

| カテゴリ | URL | 本文 |
|---|---|---|
| 授業 | `/api/events` | `category`（`"class"`）、`date`、`start_time`、`end_time`、`notes`、`subject_id`（数値）、`room`（`title` は送らない。授業の科目名になる） |
| アルバイト | `/api/events` | `category`（`"part_time"`）、`date`、`start_time`、`end_time`、`notes`、`title`、`employer` |
| その他（時間指定あり） | `/api/events` | `category`（`"other"`）、`date`、`start_time`、`end_time`、`notes`、`title` |
| その他（締切のみ） | `/api/tasks` | `category`（`"other"`）、`title`、`due_datetime`（締切日と締切時刻を `T` でつなぐ）、`notes` |

`submitEventAdd`（追加フォームの送信）の順序：
1. `preventDefault()`。今の `addSerial` と、締切のみかを控え、`addRequestOf()` で要求を作る。エラーを消し、「登録する」ボタンを押せなくする（「登録中…」）
2. `POST`（`try` で囲むのは、この要求だけ）
3. 失敗：モーダルを開き直していなければ、エラーを表示し（`showApiError(error, ADD_FIELDS, ADD_FORM_ERROR_ID)`。項目のエラーは欄の下、それ以外はフォームの上部）、ボタンを戻す（モーダルは開いたまま）。開き直していれば、何もしない
4. 成功：モーダルを開き直していなければ、閉じる（`hideModal`）。締切のみでなく、作った予定のカテゴリがアルバイトなら、知らせを出す（`showAddedNotice`）
5. 締切のみなら `notifyTasksChanged()`、そうでなければ `notifyEventsChanged()`（開き直していても呼ぶ。データは変わっているため）

`prepareEditModal`（編集のモーダルを開くとき）の順序：
1. `editSerial` を増やす。フォームを `reset()` する
2. カテゴリ（`eventCategoryOf` のアイコンと表示名）と、授業の表示（予定のタイトル）を入れる
3. 欄を合わせる：授業の表示（`event-edit-subject-row`）は授業だけ。タイトルの欄は授業以外（名前は、アルバイトは「仕事内容」、その他は「タイトル」）。派遣会社の欄はアルバイトだけ。日付の欄は、自動生成の予定以外。変えられない日付の表示（`event-edit-fixed-date-row`）は、自動生成の予定だけ。教室の欄は授業だけ（隠した入力欄は `disabled`）
4. 今の値を入れる（`null` は空。変えられない日付は、`formatJapaneseDateWithWeekday`）。エラーを消し、「保存する」ボタンを戻す。最初のフォーカスは、授業は開始時刻の欄、ほかはタイトル（仕事内容）の欄
5. アルバイトなら、`loadEmployerOptions()` を呼ぶ（待たない）

編集の本文（`editRequestBodyOf`。変えられる項目を、すべて送る）：

| 予定 | 本文 |
|---|---|
| 授業（自動生成） | `start_time`、`end_time`、`notes`、`room`（`date` は送らない） |
| 授業（単発） | `start_time`、`end_time`、`notes`、`date`、`room` |
| アルバイト | `start_time`、`end_time`、`notes`、`date`、`title`、`employer` |
| その他 | `start_time`、`end_time`、`notes`、`date`、`title` |

`initEventForms({ onEventsChanged, onTasksChanged })` で行うこと：
- 受け取った2つの関数を、`notifyEventsChanged`・`notifyTasksChanged` に入れる
- 3つのモーダルに `trackModalShowing`（成功したら、JavaScriptから閉じるため）。`show.bs.modal` に `prepareAddModal`・`prepareEditModal`・`prepareDeleteModal`。`shown.bs.modal` で、最初のフォーカスの欄（削除の確認は「キャンセル」）にフォーカスを置く
- 追加フォームの5つのラジオボタンの `change` に `applyAddCategory`、授業のプルダウンの `change` に `fillRoomFromSubject`、開始時刻の `change` に `adjustEndTime`（追加・編集とも）、フォームの `submit` に `submitEventAdd`・`submitEventEdit`、「削除する」の `click` に `submitEventDelete`
- 知らせの「同じ内容で別の日も登録」の `click` に `openRepeatAddModal`、×の `click` に `hideAddedNotice`。カレンダーのモードを開き直したとき（`calendar-tab` の `shown.bs.tab`）も `hideAddedNotice`

### 2-3. `app/static/js/calendar.js`（全文：付録G）
要点（`main` との違い。ほかは同じ）：
- `import`：`event_forms.js` から `initEventForms`・`openEventAddModal`・`openEventDeleteModal`・`openEventEditModal`。`ui.js` から `hideModal`・`trackModalShowing` を足す
- 変数：`detailEvent`（予定の詳細パネルの対象のコピー。`showEventDetail` で控える）、`afterDetailHidden`（詳細パネルを閉じたあとに行う操作。ないときは `null`）
- `closeDetailThen(modalId, action)`（新規）：`afterDetailHidden` に `action` を控え、詳細パネルを `hideModal` で閉じる（表示の途中なら、表示が終わってから閉じる）
- `runAfterDetailHidden()`（新規）：詳細パネルの `hidden.bs.modal` で呼ぶ。控えた操作を取り出して消し、あれば行う（Bootstrapでは、2つのモーダルを重ねて開けないため、閉じ終わってから、次のモーダルを開く）
- `requestTaskAction(eventName, task)`（新規）：`document` に `CustomEvent(eventName, { detail: { task: 課題・タスクのコピー } })` を発行する（`task-edit-requested`・`task-delete-requested`）
- `handleDateClick(info)`（新規。FullCalendarの `dateClick`）：`localDateTimeString(info.date)` を `T` で分けて、日付と時刻にする。`info.allDay` が `false`（週表示の時間軸）なら `openEventAddModal({ date, time })`。`true` で、表示が週表示（`WEEK_VIEW`）なら（「締切」の行）`openEventAddModal({ date, deadlineOnly: true })`。それ以外（月表示の日付の枠）は `openEventAddModal({ date })`
- FullCalendarの設定に `dateClick: handleDateClick` を足す（`selectable` は使わない）。`dateClick` は、予定・締切・月表示の日付の数字・「＋N件」のクリックでは起きない（FullCalendarの仕様。今の `eventClick`・`navLinkDayClick`・`moreLinkClick` は変わらない）。一覧表示では起きない
- `new FullCalendar.Calendar(...)` のあとに、`initEventForms({ onEventsChanged, onTasksChanged })` を呼ぶ。`onEventsChanged` は `calendar.refetchEvents()`、`onTasksChanged` は `loadDeadlines({ showLoading: false })`
- `initCalendar` の最後のほうに：2つの詳細パネル（`event-modal`・`task-detail-modal`）に `trackModalShowing`、`show.bs.modal` で `afterDetailHidden = null`、`hidden.bs.modal` で `runAfterDetailHidden`。4つのボタンの `click`：予定の「編集」「削除」は `closeDetailThen("event-modal", …)` で `openEventEditModal`・`openEventDeleteModal`（対象は、押したときの `detailEvent`）、締切の「編集」「削除」は `closeDetailThen("task-detail-modal", …)` で `requestTaskAction("task-edit-requested", …)`・`requestTaskAction("task-delete-requested", …)`（対象は、押したときの `detailTask`）。`document` の `task-changed` で `loadDeadlines({ showLoading: false })`
- コメント：`showEventDetail`・`showTaskDetail` の前のコメントを、「閉じるのは、利用者のボタンだけ」から、「「編集」「削除」は、パネルを閉じてから…」にした
- 予定・締切の取得、絞り込み、「直近の締切」欄、締切の詳細パネルの完了の切り替え、表示の切り替えは変えない
- `initCalendar` の始めの、FullCalendarを読み込めなかったときの処理は変えない（そのときは、`initEventForms` も、ボタンの登録も行わない。追加フォームを開く手段がないため）

`main` からの差分（確認用）：

```diff
--- a/app/static/js/calendar.js
+++ b/app/static/js/calendar.js
@@ -11,13 +11,25 @@ import {
   localDateString,
   localDateTimeString,
 } from "./dates.js";
+import {
+  initEventForms,
+  openEventAddModal,
+  openEventDeleteModal,
+  openEventEditModal,
+} from "./event_forms.js";
 import {
   createOverdueBadge,
   createTaskTitle,
   isTaskOverdue,
   taskLabel,
 } from "./task_display.js";
-import { errorMessageOf, getElement, setVisible } from "./ui.js";
+import {
+  errorMessageOf,
+  getElement,
+  hideModal,
+  setVisible,
+  trackModalShowing,
+} from "./ui.js";
 
 // 表示の種類（FullCalendarの表示の名前）。
 const WEEK_VIEW = "timeGridWeek";
@@ -69,6 +81,11 @@ let deadlinesShown = true;
 let detailTask = null;
 let detailOpenedAt = "";
 let detailSerial = 0;
+// 予定の詳細パネルの対象（予定のコピー）。
+let detailEvent = null;
+// 詳細パネル（予定・締切）を閉じたあとに行う操作（「編集」「削除」で
+// 控える）。ないときは null。
+let afterDetailHidden = null;
 
 function showLoadError(error) {
   getElement("calendar-load-error-message").textContent =
@@ -236,8 +253,10 @@ function setDetailRow(rowId, valueId, value) {
   setVisible(getElement(rowId), value !== null);
 }
 
-// 予定の詳細パネルを開く（読み取りだけ。閉じるのは、利用者のボタンだけ）。
+// 予定の詳細パネルを開く。「編集」「削除」は、パネルを閉じてから、
+// 編集・削除の確認のモーダルを開く（event_forms.js）。
 function showEventDetail(apiEvent) {
+  detailEvent = { ...apiEvent };
   const category = eventCategoryOf(apiEvent.category);
   getElement("event-modal-title").textContent = apiEvent.title;
   getElement("event-modal-category-icon").textContent = category.icon;
@@ -408,7 +427,8 @@ async function toggleDeadlineCompleted(task, checkbox) {
 }
 
 // 課題・タスクの詳細パネルを開く（カレンダーの締切のクリック）。値は、
-// 開くとき（show.bs.modal）に入れる。閉じるのは、利用者のボタンだけ。
+// 開くとき（show.bs.modal）に入れる。「編集」「削除」は、パネルを閉じて
+// から、課題・タスクモードの編集・削除の確認のモーダルを開く。
 function showTaskDetail(apiTask) {
   detailTask = { ...apiTask };
   window.bootstrap.Modal.getOrCreateInstance(
@@ -503,6 +523,50 @@ async function toggleDetailCompleted() {
   await loadDeadlines({ showLoading: false });
 }
 
+// 詳細パネル（予定・締切。modalId）を閉じ、閉じ終わってから
+// （hidden.bs.modal）、action を行う（Bootstrapでは、2つのモーダルを
+// 重ねて開けないため）。表示の途中なら、表示が終わってから閉じる
+// （ui.js の hideModal）。
+function closeDetailThen(modalId, action) {
+  afterDetailHidden = action;
+  hideModal(getElement(modalId));
+}
+
+// 詳細パネルが閉じたとき（hidden.bs.modal）に、控えた操作を行う。
+function runAfterDetailHidden() {
+  const action = afterDetailHidden;
+  afterDetailHidden = null;
+  if (action !== null) {
+    action();
+  }
+}
+
+// 課題・タスクモードに、編集・削除のモーダルを開くように頼む（eventName は
+// task-edit-requested か task-delete-requested。モードのファイル同士は、
+// 互いを import しないため、CustomEvent でつなぐ）。
+function requestTaskAction(eventName, task) {
+  document.dispatchEvent(
+    new CustomEvent(eventName, { detail: { task: { ...task } } }),
+  );
+}
+
+// 空き枠のクリック（FullCalendarの dateClick）。追加フォームを、クリック
+// した日時を入れて開く。週表示の時間軸は、日付と、30分の枠の始まりの
+// 時刻。週表示の「締切」の行（終日の行）は、その他の「締切のみ」。月表示の
+// 日付の枠は、日付だけ（時刻は、初期値）。一覧表示では、起きない。
+function handleDateClick(info) {
+  const [date, time] = localDateTimeString(info.date).split("T");
+  if (!info.allDay) {
+    openEventAddModal({ date, time });
+    return;
+  }
+  if (info.view.type === WEEK_VIEW) {
+    openEventAddModal({ date, deadlineOnly: true });
+    return;
+  }
+  openEventAddModal({ date });
+}
+
 // 絞り込みの選択肢を、カテゴリの対応表から作る（表示名を1か所で持つため）。
 function renderFilter() {
   const fragment = document.createDocumentFragment();
@@ -662,6 +726,20 @@ export function initCalendar() {
       }
       showEventDetail(apiEvent);
     },
+    // 空き枠のクリック。予定・締切・月表示の日付の数字・「＋N件」の
+    // クリックでは、起きない（FullCalendarの仕様）。
+    dateClick: handleDateClick,
+  });
+  // 予定の追加・編集・削除のモーダル（event_forms.js）。登録・編集・削除が
+  // できたら、予定（その他（締切のみ）は、締切と「直近の締切」欄）を
+  // 取得し直す。
+  initEventForms({
+    onEventsChanged: () => {
+      calendar.refetchEvents();
+    },
+    onTasksChanged: () => {
+      loadDeadlines({ showLoading: false });
+    },
   });
 
   getElement("calendar-retry-button").addEventListener("click", () => {
@@ -691,6 +769,44 @@ export function initCalendar() {
     "change",
     toggleDetailCompleted,
   );
+
+  // 詳細パネル（予定・締切）は、「編集」「削除」で、JavaScriptから閉じる
+  // ため、表示の途中かを記録する（ui.js の hideModal）。開くときは、前に
+  // 控えた操作を消す。閉じたら、控えた操作を行う。
+  for (const modalId of ["event-modal", "task-detail-modal"]) {
+    const modal = getElement(modalId);
+    trackModalShowing(modal);
+    modal.addEventListener("show.bs.modal", () => {
+      afterDetailHidden = null;
+    });
+    modal.addEventListener("hidden.bs.modal", runAfterDetailHidden);
+  }
+  getElement("event-modal-edit-button").addEventListener("click", () => {
+    const target = detailEvent;
+    closeDetailThen("event-modal", () => openEventEditModal(target));
+  });
+  getElement("event-modal-delete-button").addEventListener("click", () => {
+    const target = detailEvent;
+    closeDetailThen("event-modal", () => openEventDeleteModal(target));
+  });
+  getElement("task-detail-edit-button").addEventListener("click", () => {
+    const target = detailTask;
+    closeDetailThen("task-detail-modal", () => {
+      requestTaskAction("task-edit-requested", target);
+    });
+  });
+  getElement("task-detail-delete-button").addEventListener("click", () => {
+    const target = detailTask;
+    closeDetailThen("task-detail-modal", () => {
+      requestTaskAction("task-delete-requested", target);
+    });
+  });
+  // 課題・タスクモードで、課題・タスクを編集・削除したら（カレンダーの
+  // 締切の詳細パネルから開いた場合を含む）、締切と「直近の締切」欄を
+  // 取得し直す。
+  document.addEventListener("task-changed", () => {
+    loadDeadlines({ showLoading: false });
+  });
   calendar.render();
   // カレンダーのモードは、ページを開いたときに表示されているため、ここで
   // 課題・タスクを取得する（タブの shown.bs.tab は、最初は起きない）。
```

### 2-4. `app/static/js/main.js`（全文：付録H）
要点：コメントだけを変える（課題・タスクとカレンダーは、イベントでつながる。どちらのイベントも、利用者の操作のあとに発行するため、初期化の順序によらない）。初期化の順序は変えない。

`main` からの差分（確認用）：

```diff
--- a/app/static/js/main.js
+++ b/app/static/js/main.js
@@ -9,8 +9,11 @@ import { initTasks } from "./tasks.js";
 initSubjects();
 initClosures();
 initSemesters();
-// 課題・タスクは、ほかのモードとイベントでつながらない。
+// 課題・タスクとカレンダーは、カレンダーの締切の詳細パネルの「編集」
+// 「削除」（task-edit-requested・task-delete-requested）と、編集・削除の
+// 結果（task-changed）で、イベントでつながる。どちらも、利用者の操作の
+// あとに発行するため、初期化の順序によらない。
 initTasks();
-// カレンダーは、ほかのモードとイベントでつながらない。予期しない例外で、
-// ほかのモードの初期化が止まらないように、最後に初期化する。
+// カレンダーは、予期しない例外で、ほかのモードの初期化が止まらないように、
+// 最後に初期化する。
 initCalendar();
```

### 2-5. 変わる挙動・変わらない挙動

| 操作 | 変わる・変わらない |
|---|---|
| カレンダー（週表示の時間軸の空き枠・「締切」の行、月表示の日付の枠のクリック） | 追加フォームが開く（今までは、何も起きなかった） |
| カレンダー（予定・締切のクリック、月表示の日付の数字・「＋N件」、一覧表示） | 変わらない（詳細パネル、週表示への移動） |
| 予定の詳細パネル | 下に「削除」「編集」が足される |
| 締切の詳細パネル | 下に「削除」「編集」が足される。完了の切り替えは変わらない |
| 課題・タスクモード | 見た目と動きは変わらない（共通処理を `subject_options.js` に移しただけ）。編集・削除のモーダルが、カレンダーからも開く。編集・削除のあと、カレンダーの締切と「直近の締切」欄も取得し直す |
| すべてのモーダル（学期の登録、授業の登録・編集・削除、課題・タスクの追加・編集・削除、予定の追加・編集・削除） | 送信がエラーになったあとも、Escapeキーで閉じられる（017-N2）。送信中は、フォーカスがモーダルにある |
| 休講日の「追加する」「削除」 | 失敗のあとに、フォーカスがボタンに戻る（今までは、ページ本体）。ほかは変わらない |
| 授業モード・API・DB | 変わらない |

## JavaScriptの共通の規則
`.github/copilot-instructions.md` の「コーディング方針」のJavaScriptの規則と、`docs/architecture.md` の「JavaScriptの構成（ES modules）」の規則（`innerHTML` などを使わない、`textContent` で表示する、`fetch` は `api.js` だけ、`try` で囲むのは要求だけ、名前つきの引数、モードのファイル同士は `import` しない（モードの中の部品は、そのモードのファイルだけが `import` する）、1行は80文字以内）。付録の全文は、これらに合っている（「Copilot確認手順」の3・6で確かめる）。

## 変更してよい既存のテスト
なし（Pythonを変えないため、テストは変えない・足さない）。**既存のテスト（1021件）が、想定外に失敗した場合**は、原因を調べ、そこで実装を止めて、チャットで報告する。

## 実装手順
1. ブランチ・作業ツリーの確認。設計資料が更新されていることを確認する（「Copilot確認手順」の1の `grep`）。更新されていなければ、何も変更せずに停止して報告する
2. 作業の前の状態を記録する：開発用DBの有無・ハッシュ・件数（「Copilot確認手順」の1。**`sqlite3` は `-readonly` を付ける**）。`python -m pytest -q` が1021件、すべて合格すること（合格しなければ、何も変更せずに停止して報告する）。**1の出力は、見出しの行も含めて、報告に、そのまま貼るために控える**（019-N1）
3. **（段階1）** 「全文からファイルを作るスクリプト」を `python - 1` で実行する（出力を控える）。「Copilot確認手順」の2を実施し、`python -m pytest -q` が1021件、すべて合格すること。「全文との比較」（「Copilot確認手順」の4）を `python - 1` で実行し、4ファイルとも「一致」
4. **（段階2）** スクリプトを `python - 2` で実行する（出力を控える）。「Copilot確認手順」の2を実施し、`python -m pytest -q` が1021件、すべて合格すること。「全文との比較」を `python - 2` で実行し、8ファイルとも「一致」
5. 「Copilot確認手順」の3・5・6・7を実施する
6. 結果を報告して、応答を終える（コマンドの出力は、要約せずに、そのまま貼る。サーバーを起動していないこと、ブラウザでの確認をしていないことを明記する）

## 完了条件
- `python -m pytest -q` が、作業の前と、段階1・段階2の終わりに、**1021件**すべて合格する（失敗・エラー・スキップが0件）
- 変更・新規のファイルが、「実装対象ファイル」の8つだけ
- 8ファイルが、このTask MDの全文と1文字も違わない（「Copilot確認手順」の4が、段階1の終わりに4ファイル、段階2の終わりに8ファイルとも「一致」）
- `app/static/js/` のJavaScriptのファイルに、80文字を超える行がない
- 「Copilot確認手順」の5（画面のHTMLの確認）と6（検索と差分）が、期待どおり
- 実施の前後で、開発用DB（`instance/app.db`）のハッシュと、`semesters`・`subjects`・`closures`・`events`・`tasks` の件数が同じ
- 「Komaの確認」が、期待どおり
- レビューで承認される

## Copilot確認手順
**`sqlite3` は、必ず `-readonly` を付けて実行する**（011-L1）。**それぞれのコマンドの出力を、要約せずに、`echo` の見出しの行も含めて、そのまま報告に貼る**（014-L1・018-N1・019-N1）。**コマンドは、書いてあるとおりに実行する（書き換えた場合は、報告に書く。016-N1・017-N1）。**

```
# 1. 実施前（出力は、見出しの行も含めて、そのまま報告に貼る。019-N1）
echo "== 1-1 ブランチ（feature/020-calendar-event-operations）"
git branch --show-current
echo "== 1-2 作業ツリー（変更なし）"
git status
echo "== 1-3 設計資料：予定の編集・削除の小節（2件）"
grep -n -F -e "#### 編集（モーダル。2026-10-19に決定）" -e "#### 削除（確認のモーダル。2026-10-19に決定）" docs/ui_ux.md
echo "== 1-4 設計資料：休講日の確認のダイアログの未決定（出力なし。未決定から外れている）"
grep -n -F "休講日を追加するときに、確認のダイアログを出すか" docs/ui_ux.md
echo "== 1-5 設計資料：event_forms.js・subject_options.js（それぞれ4以上）"
grep -c -F "event_forms.js" docs/architecture.md
grep -c -F "subject_options.js" docs/architecture.md
echo "== 1-6 設計資料：モード間の連携のイベント（3件以上）"
grep -n -F -e '| `task-edit-requested`' -e '| `task-changed`' -e '**空き枠のクリック**' docs/architecture.md
echo "== 1-7 止まる場面の応答（数件）"
grep -n -F "止まる場面の応答" .github/copilot-instructions.md
echo "== 1-8 開発用DB（存在すること。なければ、何も変更せずに停止して報告する）"
ls -l instance/app.db
shasum -a 256 instance/app.db
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"
echo "== 1-9 pytest（1021 passed）"
python -m pytest -q

# 2. 各段階の終わり（段階1・段階2とも）
echo "== 2-1 pytest（1021 passed）"
python -m pytest -q

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
        "app/static/js/ui.js",
        "app/static/js/subject_options.js",
        "app/static/js/current_semester.js",
        "app/static/js/tasks.js",
    ],
    "2": [
        "app/templates/index.html",
        "app/static/js/event_forms.js",
        "app/static/js/calendar.js",
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
expected_files = read_full_texts("docs/tasks/020_calendar_event_operations.md")
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
    "event-added-notice", "event-added-notice-message", "event-repeat-button",
    "event-added-notice-close-button",
    "event-modal-delete-button", "event-modal-edit-button",
    "task-detail-delete-button", "task-detail-edit-button",
    "event-add-modal", "event-add-modal-title", "event-add-form",
    "event-add-form-error", "event-add-category-class",
    "event-add-category-part-time", "event-add-category-other",
    "event-add-other-type-row", "event-add-other-type-timed",
    "event-add-other-type-deadline", "event-add-subject-row",
    "event-add-subject", "event-add-subject-note", "event-add-subject-error",
    "event-add-title-row", "event-add-title-label", "event-add-title",
    "event-add-title-error", "event-add-employer-row", "event-add-employer",
    "event-add-employer-error", "event-add-date-row", "event-add-date",
    "event-add-date-error", "event-add-time-row", "event-add-start-time",
    "event-add-start-time-error", "event-add-end-time",
    "event-add-end-time-error", "event-add-due-row", "event-add-due-date",
    "event-add-due-time", "event-add-due-error", "event-add-room-row",
    "event-add-room", "event-add-room-error", "event-add-notes",
    "event-add-notes-error", "event-add-submit-button",
    "event-edit-modal", "event-edit-modal-title", "event-edit-form",
    "event-edit-form-error", "event-edit-category-icon",
    "event-edit-category", "event-edit-subject-row", "event-edit-subject",
    "event-edit-title-row", "event-edit-title-label", "event-edit-title",
    "event-edit-title-error", "event-edit-employer-row",
    "event-edit-employer", "event-edit-employer-error", "event-edit-date-row",
    "event-edit-date", "event-edit-date-error", "event-edit-fixed-date-row",
    "event-edit-fixed-date", "event-edit-start-time",
    "event-edit-start-time-error", "event-edit-end-time",
    "event-edit-end-time-error", "event-edit-room-row", "event-edit-room",
    "event-edit-room-error", "event-edit-notes", "event-edit-notes-error",
    "event-edit-submit-button",
    "event-delete-modal", "event-delete-modal-title", "event-delete-target",
    "event-delete-generated-note", "event-delete-error",
    "event-delete-warning", "event-delete-cancel-button",
    "event-delete-submit-button", "event-employer-options",
]
ORDER = [
    "calendar-pane", "event-added-notice", "calendar-view", "subjects-pane",
    "tasks-pane", "event-modal", "task-detail-modal", "event-add-modal",
    "event-edit-modal", "event-delete-modal", "event-employer-options",
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
    print("派遣会社の欄の list:", html.count('list="event-employer-options"'))
    print("カテゴリの選択肢の値:", re.findall('name="event-add-category" id="[^"]+" value="([^"]+)"', html))
    print("その他の種類の値:", re.findall('name="event-add-other-type" id="[^"]+" value="([^"]+)"', html))
    # JavaScriptが getElement("…") で使うidと、event_forms.js・calendar.js の
    # 「"event-…"」「"task-detail-…"」の文字列のidが、HTMLにあること。
    missing = []
    get_element = 'getElement[(][ ' + newline + ']*"([^"]+)"'
    for path in sorted(Path("app/static/js").glob("*.js")):
        text = path.read_text(encoding="utf-8")
        for element_id in re.findall(get_element, text):
            if element_id not in ids:
                missing.append(f"{path.name}:{element_id}")
    pattern = '"((?:event|task-detail)-[a-z-]+)"'
    for name in ["event_forms.js", "calendar.js"]:
        text = Path("app/static/js", name).read_text(encoding="utf-8")
        for element_id in re.findall(pattern, text):
            if element_id not in ids:
                missing.append(f"{name}:{element_id}")
    print("JavaScriptのidで、HTMLにないもの:", missing)
    for name in [
        "js/ui.js", "js/subject_options.js", "js/current_semester.js",
        "js/tasks.js", "js/event_forms.js", "js/calendar.js", "js/main.js",
    ]:
        response = client.get(f"/static/{name}")
        print(name, response.status_code, response.mimetype)
        response.close()
EOF

# 6. 検索と差分（段階2の終わり。各コマンドの前の echo の見出しも、出力として貼る。018-N1）
echo "== 6-1 使わない書き方（出力なし）"
grep -rn -F -e innerHTML -e outerHTML -e insertAdjacentHTML -e "document.write" -e "eval(" -e localStorage -e sessionStorage -e setTimeout -e "export default" -e "var " -e ".style" -e "confirm(" app/static/js/
echo "== 6-2 fetch を呼ぶ場所（1件：api.js）"
grep -rn -F " fetch(" app/static/js/
echo "== 6-3 event_forms.js を import するファイル（1件：calendar.js だけ）"
grep -rn -F 'from "./event_forms.js"' app/static/js/
echo "== 6-4 モードのファイルを import するファイル（5件：すべて main.js）"
grep -rn -F -e 'from "./calendar.js"' -e 'from "./tasks.js"' -e 'from "./subjects.js"' -e 'from "./semesters.js"' -e 'from "./closures.js"' app/static/js/
echo "== 6-5 subject_options.js・current_semester.js を import するファイル（4件：subject_options.js（current_semester.js）・event_forms.js・semesters.js（current_semester.js）・tasks.js）"
grep -rn -F -e 'from "./subject_options.js"' -e 'from "./current_semester.js"' app/static/js/
echo "== 6-6 CustomEvent の名前（11件：calendar.js 4（コメント1、発行2、購読1）、tasks.js 5（発行1、コメント2、購読2）、main.js 2（コメント））"
grep -rn -F -e "task-edit-requested" -e "task-delete-requested" -e "task-changed" app/static/js/
echo "== 6-7 trackModalShowing・hideModal（22件：calendar.js 2、ui.js 2（定義）、event_forms.js 6、semesters.js 2、subjects.js 4、tasks.js 6）"
grep -rn -F -e "trackModalShowing(" -e "hideModal(" app/static/js/
echo "== 6-8 window.bootstrap.Modal（8件：calendar.js 2、ui.js 1、event_forms.js 1、subjects.js 2、tasks.js 2）"
grep -rn -F "window.bootstrap.Modal" app/static/js/
echo "== 6-9 カテゴリの保存値の文字列（12件：calendar.js 7（Task 018と同じ）、event_forms.js 4（コメント1と、定数3）、tasks.js 1）"
grep -rn -F -e '"class"' -e '"part_time"' -e '"assignment"' -e '"other"' app/static/js/
echo "== 6-10 export（19件：ui.js 8、subject_options.js 4、current_semester.js 1、tasks.js 1、event_forms.js 4、calendar.js 1、main.js 0）"
grep -n -F "export " app/static/js/ui.js app/static/js/subject_options.js app/static/js/current_semester.js app/static/js/tasks.js app/static/js/event_forms.js app/static/js/calendar.js app/static/js/main.js
echo "== 6-11 空き枠のクリック（2件：calendar.js のコメント1と、設定1。selectable は使わない）"
grep -rn -F -e "dateClick" -e "selectable" app/static/js/
echo "== 6-12 setSubmitting のフォーカス（2件：ui.js の modal.focus() と button.focus()）"
grep -n -F ".focus()" app/static/js/ui.js
echo "== 6-13 HTMLの onclick・style 属性（出力なし）"
grep -n -F -e onclick -e "style=" app/templates/index.html app/templates/base.html
echo "== 6-14 変更したファイルの行数（6行：119 3 calendar.js、2 1 current_semester.js、6 3 main.js、29 62 tasks.js、28 0 ui.js、197 0 index.html）"
git diff --numstat app/static/js/ui.js app/static/js/current_semester.js app/static/js/tasks.js app/templates/index.html app/static/js/calendar.js app/static/js/main.js
echo "== 6-15 新しいファイルの行数（66 subject_options.js、755 event_forms.js）"
wc -l app/static/js/subject_options.js app/static/js/event_forms.js
echo "== 6-16 変えないファイル（出力なし）"
git diff --stat -- app/*.py app/routes/ app/models/ migrations/ tests/ requirements.txt pytest.ini run.py app/templates/base.html app/static/css/style.css app/static/js/api.js app/static/js/dates.js app/static/js/categories.js app/static/js/task_display.js app/static/js/semesters.js app/static/js/subjects.js app/static/js/closures.js

# 7. 実施後
echo "== 7-1 開発用DB（実施前と同じ）"
shasum -a 256 instance/app.db
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"
echo "== 7-2 git status（変更：6ファイル。新規：subject_options.js・event_forms.js）"
git status
echo "== 7-3 git diff --stat"
git diff --stat
```

| 確認 | 期待する結果 |
|---|---|
| 実施前（1） | 各見出しの括弧の中のとおり。1-5は、2つとも4以上 |
| `python -m pytest -q` | 実施前、段階1・段階2の終わりとも、1021件がすべて合格。失敗・エラー・スキップが0件。`migrations/env.py` の `DeprecationWarning` は、出ても構わない（報告する） |
| 1行の長さ（3） | 出力なし |
| 全文との比較（4） | `全文の数：8` と、段階1の終わりは4ファイル、段階2の終わりは8ファイルとも「一致」。「不一致」が出たら、手で直さず、その段階の「全文からファイルを作るスクリプト」をもう一度実行して全文に戻し、2からやり直す（戻したことを報告する）。Task MDの全文のほうを変える必要があると判断した場合は、停止して報告する |
| 画面のHTMLの確認（5） | 「新しいidの数: 86」「新しいidで、1つでないもの: []」「重複したid: []」「並び: True」「モーダルは<main>の外: True」「派遣会社の欄の list: 2」「カテゴリの選択肢の値: ['class', 'part_time', 'other']」「その他の種類の値: ['timed', 'deadline']」「JavaScriptのidで、HTMLにないもの: []」。7つのJavaScriptのファイルが `200 text/javascript` |
| 検索と差分（6） | 各見出しの括弧の中のとおり（件数が違う場合は、その見出しと出力を報告に書く） |
| 開発用DB | 実施の前後で、ハッシュと、5つのテーブルの件数が同じ |
| `git status` | 変更：`app/static/js/calendar.js`、`app/static/js/current_semester.js`、`app/static/js/main.js`、`app/static/js/tasks.js`、`app/static/js/ui.js`、`app/templates/index.html`。新規（`??`）：`app/static/js/event_forms.js`、`app/static/js/subject_options.js`。Pythonのファイル・`migrations/`・`tests/`・`docs/`・`.github/`・`requirements.txt`・`run.py`・`instance/`・ほかのJavaScriptのファイル・`base.html`・`style.css` に変更なし |

`.pytest_cache/` や `__pycache__/` が `git status` に表示される場合は、`.gitignore` を変更せず、報告する。**Copilotは、サーバーを起動せず、ブラウザでの確認もしない**（Claude と Koma が行う）。報告に、そのことを明記する。

## Komaの確認
順序：（1）pytest →（2）commit・push とレビューの依頼 →（3）ブラウザでの確認（確認用のサーバー）→（4）開発用DBでの、読み取りだけの確認 →（5）マージ。

### 1. pytest
`python -m pytest -q` を自分で実行し、**1021件、すべて合格**することを確かめる。

### 2. push とレビューの依頼
featureブランチを commit・push する（PRを作ってもよい）。新規のファイル（`subject_options.js`・`event_forms.js`）も、commitに含める。Copilotの完了報告を共有して、Claudeにレビューを頼む。**pushは、マージではない。レビューの承認の前に、マージしない。** 修正が必要になった場合は、同じブランチでCopilotが直し、もう一度pushしてレビューを受ける。

### 3. ブラウザでの確認（確認用のサーバー）
レビューで「承認可能」になったあとに行う。**ブラウザの操作は、Claudeが、ブラウザのパネルまたはChromeで行う。Komaは、サーバーの起動・停止、確認用のデータの登録、DBのハッシュの確認、後片付けを行う**（roadmap の「進め方の決定の記録」、2026-10-12）。

#### 確認の安全のしくみ
- **開発用DBは使わない。** 確認用のDB（`/tmp/schedule-app-check-020/check.db`）を、migrationで作り、そのDBで起動した確認用のサーバーで確かめる（Task 010〜018と同じ方法）。開発用DBには、何も残らない
- 確認用のデータ（下の「確認用のデータの登録」）は、確認用のDBの場所を指定して、すべてアプリのAPIで登録する。**このスクリプトは、確認用のDBだけに書き込む**
- 確認の途中の、APIの直接の呼び出し（E6の削除、各項目の読み取り）は、確認用のDBの、確認のために登録したデータに限る（roadmap の「進め方の決定の記録」、2026-10-12）
- ブラウザは、BootstrapとFullCalendarを、インターネット（jsDelivr）から読み込む。インターネットにつながった状態で行う
- 確認の前後で、開発用DBのハッシュが同じことを確かめる

#### 確認の日付と、確認の書き方
- 確認用のデータの日付は、**データを登録した日（このMacの「今日」。以下 T）からの相対**で決める。下の表の日付の例は、**T が 2026年10月21日（水）の場合**（Claudeが、実際の T に読み替える）。確認は、日付をまたがずに行う（日付をまたいだ場合は、後片付けをしてから、準備からやり直す）
- 週表示は、日曜始まり。T+1〜T+3 が、T の週に入らない場合（T が木〜土曜日のとき）は、その日を操作する前に「次へ」を押し、終わったら「前へ」で T の週に戻る
- 予定・締切の表示は、DOMで確かめる（スクリーンショットは、古いことがある。018-N2）。カレンダーに、ほかの場所の変更を反映させるときは、画面下の「課題・タスク」を押してから「カレンダー」を押す（カレンダーのモードを開くたびに、取得し直す。018-N2）
- 「押す」は、マウスで押す（JavaScriptの `click()` を使わない。017-N2の確認は、押したボタンにフォーカスがあることが前提のため）。入力欄への入力は、キーボードで入力するか、下の「確認用の関数」の `setValue` を使う（時刻・日付の欄は、`setValue` を使ってよい）
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
ブランチ `feature/020-calendar-event-operations` のまま、リポジトリのルートで、`.venv` を有効にして、次を実行する（行の先頭に空白を入れずにコピーする）。

```
python - <<'EOF'
from pathlib import Path

from flask_migrate import upgrade

from app import create_app

# 確認用のDB（開発用DBとは別のファイル）。止めて起動し直しても、残る。
check_directory = Path("/tmp/schedule-app-check-020")
check_directory.mkdir(exist_ok=True)
database_path = check_directory / "check.db"
app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"})
with app.app_context():
    upgrade(directory="migrations")
print(f"確認用のDB：{database_path}", flush=True)
app.run(host="127.0.0.1", port=5001, debug=False)
EOF
```

期待する出力：初めての起動では、`Running upgrade  -> 0280f6cf8d09, initial tables` と `Running upgrade 0280f6cf8d09 -> 42bd53808fa1, add closures table`、「確認用のDB：/tmp/schedule-app-check-020/check.db」、`Running on http://127.0.0.1:5001`。起動し直したときは、`Running upgrade` の行が出ない。

#### 確認用のデータの登録
確認用のサーバーを起動したあとに、別のターミナルで、1回だけ実行する（行の先頭に空白を入れずにコピーする）。

```
python - <<'EOF'
from datetime import date, timedelta
from pathlib import Path

from app import create_app

# 確認用のDBだけに書き込む（開発用DBは使わない）。DBは、確認用のサーバーが、
# 起動のときにmigrationで作っておいたものを使う。
database_path = Path("/tmp/schedule-app-check-020/check.db")
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


def class_event_id(subject_id, offset):
    events = client.get(f"/api/events?start_date={day(offset)}&end_date={day(offset)}").get_json()
    return [event["id"] for event in events if event["subject_id"] == subject_id]


# 学期・授業・予定・課題・タスクは、すべてAPIで登録する。
semester = send("POST", "/api/semesters", {"name": "2026年度 後期", "start_date": day(-42), "end_date": day(42)}, 201)
subjects = [
    send("POST", "/api/subjects", {"semester_id": semester["id"], "subject_name": "テスト：今日の曜日の授業", "weekday": today.weekday(), "start_time": "13:00", "end_time": "14:30", "room": "3号館201"}, 201),
    send("POST", "/api/subjects", {"semester_id": semester["id"], "subject_name": "テスト：教室のない授業", "weekday": (today.weekday() + 2) % 7, "start_time": "09:00", "end_time": "10:00"}, 201),
]
events = [
    send("POST", "/api/events", {"category": "part_time", "date": day(-7), "start_time": "17:00", "end_time": "21:00", "title": "テスト：前の週のアルバイト", "employer": "テスト派遣A"}, 201),
    send("POST", "/api/events", {"category": "part_time", "date": day(-6), "start_time": "10:00", "end_time": "15:00", "title": "テスト：前の週のアルバイト2", "employer": "テスト派遣B"}, 201),
    send("POST", "/api/events", {"category": "other", "date": day(1), "start_time": "10:00", "end_time": "11:00", "title": "テスト：歯医者", "notes": "メモ1行目" + newline + "メモ2行目"}, 201),
]
tasks = [
    send("POST", "/api/tasks", {"category": "assignment", "subject_id": subjects[0]["id"], "title": "テスト：レポート", "due_datetime": day(1) + "T23:59"}, 201),
    send("POST", "/api/tasks", {"category": "other", "title": "テスト：申込み締切", "due_datetime": day(3) + "T12:00"}, 201),
]
print(f"今日：{today.isoformat()}（{WEEKDAYS[today.weekday()]}）")
print("授業のid：", [subject["id"] for subject in subjects])
print("授業の予定の件数：", [subject["generated_event_count"] for subject in subjects])
print("今日と7日後の授業1の予定のid：", class_event_id(1, 0), class_event_id(1, 7))
print("単発の予定のid：", [event["id"] for event in events])
print("課題・タスクのid：", [task["id"] for task in tasks])
print("派遣会社の候補：", client.get("/api/events/employers").get_json())
EOF
```

期待する出力（T が 2026-10-21 の場合）：

```
今日：2026-10-21（水）
授業のid： [1, 2]
授業の予定の件数： [13, 12]
今日と7日後の授業1の予定のid： [7] [8]
単発の予定のid： [26, 27, 28]
課題・タスクのid： [1, 2]
派遣会社の候補： ['テスト派遣B', 'テスト派遣A']
```

1行目の日付が、今日（T）。2回目に実行すると、「中止：POST /api/semesters 400 …」で止まり、何も増えない（そのままでよい）。

以下、idは、この出力のとおり。確認の中で登録する予定のidは、29（A2）、30（A4）、31（B4）、32（C2）、課題・タスクのidは、3（D2）になる。

| 種類 | id：内容 |
|---|---|
| 学期 | 「2026年度 後期」（T−42〜T+42） |
| 授業 | 1：テスト：今日の曜日の授業（T と同じ曜日、13:00〜14:30、3号館201。自動生成の予定13件。T の予定は 7、T+7 の予定は 8）、2：テスト：教室のない授業（T+2 と同じ曜日、09:00〜10:00、教室なし。自動生成の予定12件） |
| 単発の予定 | 26：テスト：前の週のアルバイト（T−7、17:00〜21:00、テスト派遣A）、27：テスト：前の週のアルバイト2（T−6、10:00〜15:00、テスト派遣B）、28：テスト：歯医者（その他、T+1、10:00〜11:00、メモ2行） |
| 課題・タスク | 1：テスト：レポート（課題、授業1、T+1 23:59）、2：テスト：申込み締切（その他、T+3 12:00） |

#### 確認用の関数
コンソールに、そのまま貼る（ページを開き直したら、もう一度貼る）。`setValue(id, value)` は、入力欄に値を入れ、入力したときと同じイベントを起こす。`addFormState()`・`editFormState()` は、追加・編集のモーダルの、今の状態を返す（`rows` は表示している欄、`values` は欄の値、`focus` はフォーカスのある要素の `id`、`employers` は派遣会社の候補）。

```
window.setValue = (id, value) => { const input = document.getElementById(id); input.value = value; input.dispatchEvent(new Event("input", { bubbles: true })); input.dispatchEvent(new Event("change", { bubbles: true })); };
window.addFormState = () => { const value = (id) => document.getElementById(`event-add-${id}`).value; return { category: [...document.querySelectorAll('input[name="event-add-category"]')].find((radio) => radio.checked).value, otherType: document.getElementById("event-add-other-type-deadline").checked ? "deadline" : "timed", rows: [...document.querySelectorAll('#event-add-modal [id$="-row"]')].filter((row) => !row.classList.contains("d-none")).map((row) => row.id.slice(10, -4)), values: ["subject", "title", "employer", "date", "start-time", "end-time", "due-date", "due-time", "room", "notes"].map(value), focus: document.activeElement.id, employers: [...document.querySelectorAll("#event-employer-options option")].map((option) => option.value) }; };
window.editFormState = () => { const value = (id) => document.getElementById(`event-edit-${id}`).value; return { category: document.getElementById("event-edit-category").textContent, rows: [...document.querySelectorAll('#event-edit-modal [id$="-row"]')].filter((row) => !row.classList.contains("d-none")).map((row) => row.id.slice(11, -4)), subject: document.getElementById("event-edit-subject").textContent, fixedDate: document.getElementById("event-edit-fixed-date").textContent, values: ["title", "employer", "date", "start-time", "end-time", "room", "notes"].map(value), focus: document.activeElement.id }; };
```

`addFormState()` の `values` の並びは、授業・タイトル（仕事内容）・派遣会社・日付・開始時刻・終了時刻・締切日・締切時刻・教室・メモ。`editFormState()` の `values` の並びは、タイトル（仕事内容）・派遣会社・日付・開始時刻・終了時刻・教室・メモ。

#### A. 追加フォーム（週表示の時間軸。アルバイト）

| No | 操作 | 期待する結果 |
|---|---|---|
| A1 | 週表示で、T の列の 17:00 の空き枠を押す。コンソールで `addFormState()` を実行する | モーダル「予定を追加」が開く。カテゴリは、ボタンの形の「授業（補講など）」「アルバイト」「その他」で、「アルバイト」が選ばれている。欄は、上から「仕事内容」「派遣会社（任意）」「日付」「開始時刻」「終了時刻」「詳細・メモ（任意）」。結果は `{ category: "part_time", otherType: "timed", rows: ["title", "employer", "date", "time"], values: ["", "", "", "2026-10-21", "17:00", "18:00", "2026-10-21", "17:00", "", ""], focus: "event-add-title", employers: ["テスト派遣B", "テスト派遣A"] }` |
| A2 | 派遣会社の欄を押し、↓キーを押す（候補を見る）。仕事内容に「テスト：倉庫の仕分け」、派遣会社に「テスト派遣C」を入力し、終了時刻を 21:00 にして、「登録する」を押す | 派遣会社の欄で、候補「テスト派遣B」「テスト派遣A」が出る（この順）。登録すると、モーダルが閉じ、T の列の 17:00〜21:00 に、緑のブロック「テスト：倉庫の仕分け」。カレンダーの上（絞り込みの下）に、緑の枠で「「テスト：倉庫の仕分け」（2026年10月21日（水） 17:00 〜 21:00）を登録しました。」と、「同じ内容で別の日も登録」ボタン、× |
| A3 | 「同じ内容で別の日も登録」を押す。`addFormState()` を実行する | 知らせが消え、追加フォームが開く。結果は `{ category: "part_time", otherType: "timed", rows: ["title", "employer", "date", "time"], values: ["", "テスト：倉庫の仕分け", "テスト派遣C", "", "17:00", "21:00", "", "23:59", "", ""], focus: "event-add-date", employers: ["テスト派遣C", "テスト派遣B", "テスト派遣A"] }`（日付だけが空。派遣会社の候補は、新しく使った順） |
| A4 | 日付に T+1（2026-10-22）を入れて、「登録する」を押す | モーダルが閉じ、T+1 の列の 17:00〜21:00 に、緑のブロック「テスト：倉庫の仕分け」。知らせが「「テスト：倉庫の仕分け」（2026年10月22日（木） 17:00 〜 21:00）を登録しました。」になる |
| A5 | 知らせの × を押す | 知らせが消える |

#### B. 開始時刻の自動調整と、入力エラーのあとのEscapeキー（017-N2）

| No | 操作 | 期待する結果 |
|---|---|---|
| B1 | T の列の 10:00 の空き枠を押す。「その他」を押す。タイトルに「テスト：面談」を入れる。`setValue("event-add-start-time", "11:30")` を実行する。`addFormState()` を実行する | 「その他」を押すと、カテゴリの下に「その他の種類」（「時間指定あり」が選ばれている、「締切のみ」）が出て、欄の名前が「タイトル」になる（派遣会社の欄は消える）。結果の `category` は `"other"`、`otherType` は `"timed"`、`rows` は `["other-type", "title", "date", "time"]`、`values` は `["", "テスト：面談", "", "2026-10-21", "11:30", "12:30", "2026-10-21", "10:00", "", ""]`（終了時刻が、開始時刻の1時間後に合う） |
| B2 | `setValue("event-add-end-time", "11:00")` を実行する。「登録する」を押す。`[document.activeElement.id, document.getElementById("event-add-submit-button").disabled]` を実行する | 終了時刻の欄の下に、赤い字で「終了時刻は開始時刻より後にしてください」。モーダルは開いたまま。結果は `["event-add-submit-button", false]`（017-N2の前は、フォーカスがページ本体だった） |
| B3 | Escapeキーを押す | モーダルが閉じる（017-N2。エラーのあとも、Escapeキーで閉じられる） |
| B4 | T の列の 10:00 の空き枠を、もう一度押す。`addFormState()` を実行する。「その他」を押し、タイトルに「テスト：面談」を入れて、「登録する」を押す | 1つ目：カテゴリは「アルバイト」に戻り、入力は消えている（`values` は `["", "", "", "2026-10-21", "10:00", "11:00", "2026-10-21", "10:00", "", ""]`）。登録すると、T の列の 10:00〜11:00 に、グレーのブロック「テスト：面談」。知らせは出ない |

#### C. 授業（補講など）

| No | 操作 | 期待する結果 |
|---|---|---|
| C1 | T の列の 15:00 の空き枠を押す。「授業（補講など）」を押す。`addFormState()` を実行する | 欄は、上から「授業」（プルダウン。選択肢は「選択してください」「テスト：今日の曜日の授業」「テスト：教室のない授業」。下に「2026年度 後期の授業から選びます」）、「日付」、「開始時刻」「終了時刻」、「教室（任意）」、「詳細・メモ（任意）」。結果の `rows` は `["subject", "date", "time", "room"]`、`values` は `["", "", "", "2026-10-21", "15:00", "16:00", "2026-10-21", "15:00", "", ""]` |
| C2 | 授業で「テスト：今日の曜日の授業」を選ぶ。次に「テスト：教室のない授業」を選ぶ。もう一度「テスト：今日の曜日の授業」を選ぶ。詳細・メモに「補講」を入れて、「登録する」を押す。コンソールで `(await fetch("/api/events/32")).json()` を実行する | 教室の欄が、「3号館201」→ 空 →「3号館201」と変わる。登録すると、モーダルが閉じ、T の列の 15:00〜16:00 に、青いブロック「テスト：今日の曜日の授業」（13:00〜14:30 の授業と別に並ぶ）。知らせは出ない。結果は、`category: "class"`、`subject_id: 1`、`title: "テスト：今日の曜日の授業"`、`date: "2026-10-21"`、`start_time: "15:00"`、`end_time: "16:00"`、`room: "3号館201"`、`notes: "補講"`、`is_generated: false` |

#### D. その他（締切のみ）

| No | 操作 | 期待する結果 |
|---|---|---|
| D1 | 週表示の「締切」の行の、T の列の空いている所を押す。`addFormState()` を実行する | 追加フォームが、「その他」と「締切のみ」を選んだ状態で開く。欄は「タイトル」「締切日」「締切時刻」「詳細・メモ（任意）」。結果の `category` は `"other"`、`otherType` は `"deadline"`、`rows` は `["other-type", "title", "due"]`、`values` の締切日・締切時刻は `"2026-10-21"`・`"23:59"`、`focus` は `"event-add-title"` |
| D2 | 「時間指定あり」を押す（日付・開始時刻・終了時刻の欄に変わる。日付は T、09:00〜10:00）。「締切のみ」を押す。タイトルに「テスト：書類の提出」を入れて、「登録する」を押す | モーダルが閉じる。「締切」の行の T の列に、グレーの●「テスト：書類の提出」。「直近の締切」欄の先頭に、「2026年10月21日（水） 23:59」「⭐ テスト：書類の提出」（対象授業の行はない）。知らせは出ない |
| D3 | 画面下の「課題・タスク」を押す。画面下の「カレンダー」を押す | 課題・タスクモードの未完了の表の先頭に、「2026年10月21日（水） 23:59」「⭐ テスト：書類の提出」、対象授業「—」。カレンダーに戻る |

#### M. 月表示と一覧表示

| No | 操作 | 期待する結果 |
|---|---|---|
| M1 | 「月」を押す。T+4（2026年10月25日（日））の日付の枠の、日付の数字と予定のない所を押す。`addFormState()` を実行する | 追加フォームが開く。結果の `category` は `"part_time"`、`rows` は `["title", "employer", "date", "time"]`、`values` は `["", "", "", "2026-10-25", "09:00", "10:00", "2026-10-25", "23:59", "", ""]` |
| M2 | 仕事内容に「テスト：飲み会」を入れる。「その他」を押し、「締切のみ」を押す。`addFormState()` を実行する。「キャンセル」を押す | 欄の名前が「タイトル」になり、「テスト：飲み会」は残る。結果の `rows` は `["other-type", "title", "due"]`、`values` は `["", "テスト：飲み会", "", "2026-10-25", "09:00", "10:00", "2026-10-25", "23:59", "", ""]`。「キャンセル」で閉じる（登録しない） |
| M3 | T+4 の日付の数字を押す。「今日」を押す | T+4 を含む週の週表示に移る（追加フォームは開かない。「週」のボタンが押された状態）。「今日」で T の週に戻る |
| M4 | 「一覧」を押す。日付の見出しの行を押す。`document.querySelectorAll(".modal.show").length` を実行する。「週」を押す | 何も開かない（結果は `0`）。「週」で週表示に戻る |

#### E. 予定の編集

| No | 操作 | 期待する結果 |
|---|---|---|
| E1 | T の列の 13:00〜14:30 の青いブロック（自動生成の授業）を押す | 予定の詳細パネルが開く。下に、左から「削除」（赤い枠）、右に「編集」「閉じる」 |
| E2 | 「編集」を押す。`editFormState()` を実行する | 詳細パネルが閉じ、モーダル「予定を編集」が開く。「カテゴリ：📖 授業」。授業「テスト：今日の曜日の授業」、日付「2026年10月21日（水）」（入力欄でない）と、その下に小さく、日付を変えられないこと・別の日に移す方法・授業全体の編集で作り直されることの注意書き。結果は `{ category: "授業", rows: ["subject", "fixed-date", "room"], subject: "テスト：今日の曜日の授業", fixedDate: "2026年10月21日（水）", values: ["", "", "2026-10-21", "13:00", "14:30", "3号館201", ""], focus: "event-edit-start-time" }` |
| E3 | 教室を「テスト：5号館101」にし、`setValue("event-edit-end-time", "15:00")` を実行して、「保存する」を押す。コンソールで `(await fetch("/api/events/7")).json()` を実行する | モーダルが閉じ、ブロックが 13:00〜15:00 になる。結果は、`date: "2026-10-21"`、`start_time: "13:00"`、`end_time: "15:00"`、`room: "テスト：5号館101"`、`is_generated: true`（自動生成のまま） |
| E4 | T の列の 15:00〜16:00 の青いブロック（C2の補講）を押し、「編集」を押す。`editFormState()` を実行する。日付を T+1（2026-10-22）にして、「保存する」を押す | 結果は `{ category: "授業", rows: ["subject", "date", "room"], subject: "テスト：今日の曜日の授業", fixedDate: …, values: ["", "", "2026-10-21", "15:00", "16:00", "3号館201", "補講"], focus: "event-edit-start-time" }`（日付は入力欄で、注意書きはない。`fixedDate` の値は使わない）。保存すると、補講のブロックが T+1 の列の 15:00〜16:00 に移る |
| E5 | T の列の「テスト：倉庫の仕分け」（17:00〜21:00）を押し、「編集」を押す。`editFormState()` と、`[...document.querySelectorAll("#event-employer-options option")].map((option) => option.value)` を実行する。派遣会社を空にして、「保存する」を押す。同じブロックを押す | 1つ目の結果の `category` は `"アルバイト"`、`rows` は `["title", "employer", "date"]`、`values` は `["テスト：倉庫の仕分け", "テスト派遣C", "2026-10-21", "17:00", "21:00", "", ""]`、`focus` は `"event-edit-title"`（欄の名前は「仕事内容」）。2つ目は `["テスト派遣C", "テスト派遣B", "テスト派遣A"]`。保存のあと、詳細パネルに、派遣会社の行がない。「閉じる」で閉じる |
| E6 | T+1 の列の「テスト：歯医者」を押し、「編集」を押す。`editFormState()` を実行する。コンソールで `(await fetch("/api/events/28", { method: "DELETE" })).status` を実行する（ほかの場所で削除された場合の再現。確認用のデータに限る）。「保存する」を押す。`document.activeElement.id` を実行する。Escapeキーを押す。画面下の「課題・タスク」を押し、「カレンダー」を押す | 1つ目の結果の `category` は `"その他"`、`rows` は `["title", "date"]`、`values` は `["テスト：歯医者", "", "2026-10-22", "10:00", "11:00", "", "メモ1行目" と改行と "メモ2行目"]`。2つ目は `204`。保存すると、フォームの上部に、赤い枠で「予定が見つかりません」（モーダルは開いたまま）。3つ目は `"event-edit-submit-button"`。Escapeキーで閉じる。カレンダーに戻ると、「テスト：歯医者」が消えている |

#### R. 予定の削除

| No | 操作 | 期待する結果 |
|---|---|---|
| R1 | 「次へ」を押す。T+7 の列の 13:00〜14:30 の青いブロックを押し、「削除」を押す。`document.activeElement.id` を実行する | 詳細パネルが閉じ、モーダル「予定を削除」が開く。上から、「「テスト：今日の曜日の授業」（2026年10月28日（水） 13:00 〜 14:30）を削除します。」、「授業の登録で作られた予定です。授業全体を編集すると、今日以降の分は、作り直されます。」、赤い字の「削除は取り消せません。」。結果は `"event-delete-cancel-button"` |
| R2 | 「削除する」を押す。コンソールで `(await fetch("/api/events/8")).status` を実行する | モーダルが閉じ、T+7 の 13:00〜14:30 のブロックが消える。結果は `404` |
| R3 | 「前へ」を押す。T+1 の列の「テスト：倉庫の仕分け」（A4）を押し、「削除」を押す。`[document.getElementById("event-delete-generated-note").textContent, document.getElementById("event-delete-generated-note").classList.contains("d-none")]` を実行する。「キャンセル」を押す。`document.querySelectorAll(".modal.show").length` を実行する | 「「テスト：倉庫の仕分け」（2026年10月22日（木） 17:00 〜 21:00）を削除します。」と「削除は取り消せません。」（注意の行はない）。1つ目の結果は `["", true]`。「キャンセル」で閉じ、詳細パネルにも戻らない（2つ目の結果は `0`）。ブロックは残る |

#### K. 締切の詳細パネルの編集・削除

| No | 操作 | 期待する結果 |
|---|---|---|
| K1 | 「締切」の行の T+1 の列の「テスト：レポート」を押す。下のボタンを見る。「編集」を押す | 締切の詳細パネルの下に、「削除」（左）、「編集」「閉じる」（右）。「編集」で、パネルが閉じ、課題・タスクモードと同じモーダル「課題を編集」が開く（カレンダーのモードのまま）。課題名「テスト：レポート」、対象授業「テスト：今日の曜日の授業」（下に「2026年度 後期の授業から選びます」）、締切日 2026-10-22、締切時刻 23:59 |
| K2 | 締切日を T+2（2026-10-23）にして、「保存する」を押す | モーダルが閉じる。カレンダーのモードのまま、「締切」の行の「テスト：レポート」が、T+1 の列から T+2 の列に移る。「直近の締切」欄の「テスト：レポート」の締切が「2026年10月23日（金） 23:59」になる（課題・タスクモードを開かなくても、反映される） |
| K3 | 「締切」の行の T+3 の列の「テスト：申込み締切」を押し、「削除」を押す。`document.activeElement.id` を実行する。「削除する」を押す | モーダル「課題・タスクを削除」に、「「テスト：申込み締切」（締切 2026年10月24日（土） 12:00）を削除します。」と「削除は取り消せません。」。結果は `"task-delete-cancel-button"`。削除すると、「締切」の行と「直近の締切」欄から、「テスト：申込み締切」が消える |
| K4 | 「締切」の行の T の列の「テスト：書類の提出」を押し、「編集」を押す。「キャンセル」を押す | 見出しが「その他（締切のみ）を編集」のモーダルが開く（対象授業の欄はない）。「キャンセル」で閉じ、詳細パネルにも戻らない |
| K5 | 「テスト：書類の提出」を押し、右上の × を押す。`document.querySelectorAll(".modal.show").length` を実行する | 詳細パネルが閉じ、ほかのモーダルは開かない（結果は `0`） |

#### N. ほかのモーダルの017-N2と、休講日の追加

| No | 操作 | 期待する結果 |
|---|---|---|
| N1 | 画面下の「課題・タスク」を押す。「課題を追加」を押す。課題名に空白3つ（`   `）を入れ、対象授業で「テスト：今日の曜日の授業」を選び、締切日に T+5（2026-10-26）を入れて、「登録する」を押す。`document.activeElement.id` を実行する。Escapeキーを押す | 課題名の欄の下に「タイトルは必須です」。結果は `"task-submit-button"`。Escapeキーで閉じる（017-N2） |
| N2 | 画面下の「授業」を押す。「テスト：教室のない授業」の「編集」を押す。`setValue("subject-edit-name", "x".repeat(101))` を実行し、「保存する」を押す。`document.activeElement.id` を実行する。Escapeキーを押す | 科目名の欄の下に「科目名は100文字以内にしてください」。結果は `"subject-edit-submit-button"`。Escapeキーで閉じる（017-N2） |
| N3 | 休講日の日付に、T+60（2026-12-20）を入れて、「追加する」を押す。`document.activeElement.id` を実行する | 日付の欄の下に「休講日は、学期の期間内の日付にしてください」。結果は `"closure-submit-button"`（失敗のあとに、フォーカスがボタンに戻る） |

#### S. サーバーに接続できないとき

| No | 操作 | 期待する結果 |
|---|---|---|
| S1 | 画面下の「カレンダー」を押す。**Komaが、確認用のサーバーを止める（Ctrl＋C）。** Claudeが、T の列の 19:00 の空き枠を押す。「授業（補講など）」を押す | 追加フォームが開く。授業の欄の下に「サーバーに接続できませんでした。時間をおいて、もう一度お試しください」（選択肢は「選択してください」だけ）。派遣会社の候補の取得の失敗は、表示されない |
| S2 | 「アルバイト」を押す。仕事内容に「テスト：停止中」を入れて、「登録する」を押す。`document.activeElement.id` を実行する。Escapeキーを押す | フォームの上部に、赤い枠で「サーバーに接続できませんでした。時間をおいて、もう一度お試しください」。「登録する」ボタンが押せる状態に戻る。結果は `"event-add-submit-button"`。Escapeキーで閉じる |
| S3 | **Komaが、「確認用のサーバーの起動」のコマンドで、確認用のサーバーを起動し直す**（ターミナルで↑キーを押すと、前のコマンドを呼び出せる）。Claudeが、画面下の「課題・タスク」を押し、「カレンダー」を押す | 赤い枠のメッセージがない。「テスト：停止中」は、どこにもない（登録されていない） |

#### X. 確認の全体を通して

| No | 確認 | 期待する結果 |
|---|---|---|
| X1 | コンソール | JavaScriptの例外（`Uncaught …`）が出ていない。想定した記録（B2・N1・N2・N3の400、E6の保存とR2の確認の404の「Failed to load resource」、サーバーを止めている間（S1・S2）の接続の失敗（`net::ERR_CONNECTION_REFUSED`））は、除く（010-N1） |

#### 後片付け
1. 確認用のサーバーを止める（Ctrl＋C）
2. 確認用のDBのフォルダを消す
   ```
   rm -r /tmp/schedule-app-check-020
   ```
3. 開発用DBのハッシュが、準備の1と同じことを確かめる
   ```
   shasum -a 256 instance/app.db
   ```

ハッシュが変わっていた場合は、開発用DBを操作せずに、Claudeに伝える。

### 4. 開発用DBでの、読み取りだけの確認
3が期待どおりなら、開発用DBで起動して、画面が開くことだけを確かめる（**登録・編集・削除・完了の切り替えはしない**）。

```
shasum -a 256 instance/app.db          # 控える
python run.py                          # 開発用DBで起動
# ブラウザでの確認のあと、サーバーを Ctrl+C で止めてから
shasum -a 256 instance/app.db          # 起動の前と同じ
```

| 確認 | 期待 |
|---|---|
| ブラウザで開き、ページを開き直す。週表示の時間軸の空き枠を押す。「授業（補講など）」を押す。「キャンセル」を押す | 追加フォームが開く。授業の欄の下に「学期が登録されていません。授業モードで、学期と授業を登録してください」（開発用DBに学期がないため）。「キャンセル」で閉じる（登録しない）。コンソールに、JavaScriptの例外がない |
| 最後のハッシュ | 起動の前と同じ |

### 5. マージ
1〜4が期待どおりで、レビューで承認されたら、マージする。このタスクは、DBの構造を変えないため、開発用DBへのmigrationの適用はない。開発用DBのデータも変えないため、バックアップは要らない。

マージのあとは、カレンダーから、予定の追加・編集・削除と、締切の編集・削除ができる。開発用DBで登録・編集・削除をすると、データが変わる（削除は、元に戻せない）。

## Git操作
**Git commit / push / ブランチ操作 / マージは行わない**（`git branch --show-current`、`git status`、`git diff` のような読み取りだけのコマンドは除く）。

## 注意
- **停止して報告する条件**（ファイルを変更せず、実装を止め、チャットで「問題点・発生理由・変更した場合の影響・推奨案（必要なら）」を報告する）
  - ブランチの不一致、作業ツリーの想定外の変更
  - 設計資料が更新されていない（実装手順の1）、または、設計資料とこのTask MDの間に、矛盾・不足がある
  - 設計資料にない判断が必要になった（特に、`docs/architecture.md` の「未決定事項」や、`docs/ui_ux.md` の「未決定」に触れる場合）
  - 「全文からファイルを作るスクリプト」の出力が、期待と違う（全文の数・行数・エラー）
  - 「変更しない」と定めたもの（Pythonのファイル、テスト、ほかのJavaScriptのファイル、`base.html`、`style.css` など）を変更しないと実装できない。または、8ファイルの全文を変える必要があると判断した
  - ライブラリのインストール・ダウンロードが必要だと判断した
  - 開発用DB（`instance/app.db`）がない
  - 作業の前の `python -m pytest` が、1021件すべて合格しない
  - **既存のテスト**（1021件）**が、想定外に失敗した**。テストの期待値や、ほかの仕様を直さずに、原因を調べて報告する
  - APIの変更や、DBの構造の変更（migration）が必要だと判断した
  - 実施の前後で、`instance/app.db` が変わった
- **止まるときは、報告を書いて、その応答を終える。質問の機能は使わない。** 再開するのは、Komaの新しいメッセージが、判断や再開を明確に示したときだけ（無回答や「続けて」だけの返事は、再開の指示ではない）。`.github/copilot-instructions.md` の「止まる場面の応答」
- **開発用DBを `sqlite3` で開くときは、必ず `-readonly` を付ける**（SELECTだけでも、付けずに開かない。011-L1）。`flask db` のコマンドを、一切実行しない。ライブラリを追加しない。サーバーを起動しない（`python run.py` も、「Komaの確認」の確認用のサーバーも）。「確認用のデータの登録」のスクリプトも、実行しない（Komaが行う）。ブラウザでの確認もしない
- 期待する結果と異なる結果が出た場合は、確認を飛ばさず、原因を直してから、すべての確認をやり直す（ただし、既存のテストの想定外の失敗は、上の停止の条件に従う。全文との「不一致」は、手で直さず、スクリプトで全文に戻す）
- 設計資料に書かれていない仕様は、自分で決めない
- 作業と関係のない操作（自分の過去のセッションの検索など）は、行わない（019-N2）
- **最後の報告には、次を含め、コマンドの出力は、要約せずに、そのまま貼る**（014-L1・019-N1）：変更・新規のファイル、**「Copilot確認手順」の1（実施前）の出力（`echo` の見出しの行と、ブランチ・`git status`・設計資料の `grep`・開発用DBのハッシュ・件数・`pytest` の最後の行を含む）**、**「全文からファイルを作るスクリプト」の出力（段階1・2）**、各段階の終わりの `pytest` の出力（`echo` の見出しと最後の行）、1行の長さの確認の出力、全文との比較の出力（段階1：4ファイル、段階2：8ファイルの「一致」。スクリプトで全文に戻した場合は、そのこと）、画面のHTMLの確認の出力、検索と差分の出力（`echo` の見出しの行も含めて、そのまま。018-N1）、実施後の開発用DBのハッシュ・件数、`git status`・`git diff --stat` の出力、コマンドを書き換えたかどうか（書き換えていなければ「書き換えなし」）、サーバーの起動とブラウザでの確認をしていないこと、気になった点

## 付録：全文
「全文からファイルを作るスクリプト」と「全文との比較」が使う。各ファイルの全文は、「`<!-- 全文: パス -->`」の印の行の直後のコードブロック。**この付録を、手で書き写さない。** 本文の要点・差分と食い違う場合は、作業をせずに停止して報告する。

### 付録A. `app/static/js/ui.js`

<!-- 全文: app/static/js/ui.js -->
```
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

// 送信を始めたときに、フォーカスがあったボタン（送信が終わったら、
// フォーカスを戻す）。
const focusReturnButtons = new WeakSet();

// 送信中の表示。labels は { idle: 通常の文字, busy: 送信中の文字 } の形。
// 押せなくしたボタンからは、フォーカスがページ本体に移り、モーダルを
// Escapeキーで閉じられなくなる（017-N2）。そのため、送信を始めるときに、
// ボタンにフォーカスがあれば覚えておき、ボタンがモーダルの中なら、
// フォーカスをモーダル（の要素）に移す。送信が終わって、ボタンを押せる
// ように戻すときに、フォーカスがモーダルかページ本体にあれば、ボタンに
// 戻す（ほかの欄に移していれば、そのまま）。
export function setSubmitting(button, submitting, labels) {
  const modal = button.closest(".modal");
  if (submitting && document.activeElement === button) {
    focusReturnButtons.add(button);
  }
  button.disabled = submitting;
  button.textContent = submitting ? labels.busy : labels.idle;

  if (submitting) {
    if (focusReturnButtons.has(button) && modal !== null) {
      modal.focus();
    }
    return;
  }
  if (!focusReturnButtons.delete(button)) {
    return;
  }
  const active = document.activeElement;
  if (active === document.body || active === modal) {
    button.focus();
  }
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

### 付録B. `app/static/js/subject_options.js`

<!-- 全文: app/static/js/subject_options.js -->
```
import { apiRequest } from "./api.js";
import { chooseCurrentSemester } from "./current_semester.js";
import { localDateString } from "./dates.js";

// 今の学期の授業から選ぶ欄（プルダウン）の共通処理。課題の対象授業
// （tasks.js）と、カレンダーから追加する単発の授業（event_forms.js）で使う
// （モードのファイル同士は、互いを import しないため、このファイルに
// まとめる）。

// 授業を取得している間に、欄の下に出す説明。
export const SUBJECTS_LOADING_NOTE = "授業を読み込み中…";
const SUBJECT_PLACEHOLDER = "選択してください";

// 今の学期（授業モードで最初に選ばれる学期と同じ規則。current_semester.js）
// と、その学期の授業の一覧（授業の一覧APIの並び。曜日・開始時刻の順）を
// 取得する。学期が0件なら、semester は null、subjects は空の配列。
export async function fetchCurrentSubjects() {
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

// 授業の欄の下に出す説明。semester・subjects は、fetchCurrentSubjects の
// 結果。
export function currentSubjectsNote(semester, subjects) {
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

// 授業のプルダウン（select）の選択肢を作る。先頭は「選択してください」
// （値は空）。extraSubject は、subjects にない授業（課題の編集で、今の
// 対象授業が、今の学期の授業にないとき。{ id, subject_name }）で、先頭の
// 次に足す。ないときは null。
export function renderSubjectOptions(select, subjects, extraSubject = null) {
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
```

### 付録C. `app/static/js/current_semester.js`

<!-- 全文: app/static/js/current_semester.js -->
```
// 今の学期を選ぶ規則。複数のモードで使うため、このファイルにまとめる
// （授業モードの学期の初期選択と、今の学期の授業から選ぶ欄
// （subject_options.js。課題の対象授業と、単発の授業））。
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

### 付録D. `app/static/js/tasks.js`

<!-- 全文: app/static/js/tasks.js -->
```
import { apiRequest } from "./api.js";
import { formatJapaneseDateTime, localDateTimeString } from "./dates.js";
import {
  SUBJECTS_LOADING_NOTE,
  currentSubjectsNote,
  fetchCurrentSubjects,
  renderSubjectOptions,
} from "./subject_options.js";
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

// 課題・タスクを編集・削除したことを、ほかのモード（カレンダーの締切と
// 「直近の締切」欄）に知らせる（モードのファイル同士は、互いを import
// しないため、CustomEvent でつなぐ）。
function notifyTaskChanged() {
  document.dispatchEvent(new CustomEvent("task-changed"));
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
  note.textContent = SUBJECTS_LOADING_NOTE;

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
  note.textContent = currentSubjectsNote(result.semester, result.subjects);
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

// 一覧の「編集」ボタンと、カレンダーの締切の詳細パネルの「編集」
// （task-edit-requested）。対象を控えて、編集のモーダルを開く（入力欄は、
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
  note.textContent = SUBJECTS_LOADING_NOTE;

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
  note.textContent = currentSubjectsNote(result.semester, result.subjects);
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
  notifyTaskChanged();
  await loadTasks({ showLoading: false });
}

// 一覧の「削除」ボタンと、カレンダーの締切の詳細パネルの「削除」
// （task-delete-requested）。対象を控えて、削除の確認のモーダルを開く。
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
  notifyTaskChanged();
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
  // カレンダーの締切の詳細パネルの「編集」「削除」で、このモードの編集・
  // 削除のモーダルを開く（detail.task は、課題・タスクのコピー）。
  document.addEventListener("task-edit-requested", (event) => {
    openEditModal(event.detail.task);
  });
  document.addEventListener("task-delete-requested", (event) => {
    openDeleteModal(event.detail.task);
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

### 付録E. `app/templates/index.html`

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

### 付録F. `app/static/js/event_forms.js`

<!-- 全文: app/static/js/event_forms.js -->
```
import { ApiError, apiRequest } from "./api.js";
import { eventCategoryOf } from "./categories.js";
import { formatJapaneseDateWithWeekday } from "./dates.js";
import {
  SUBJECTS_LOADING_NOTE,
  currentSubjectsNote,
  fetchCurrentSubjects,
  renderSubjectOptions,
} from "./subject_options.js";
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

// カレンダーモードの中の部品：予定の追加（その他（締切のみ）を含む）・
// 編集・削除の確認のモーダル。calendar.js だけが import する（calendar.js
// が大きくなりすぎないように、分けた）。登録・編集・削除ができたら、
// initEventForms で受け取った関数で、カレンダーに取得し直させる。

// 予定のカテゴリの保存値（categories.js の EVENT_CATEGORIES のキー）。
// その他（締切のみ）は、課題・タスクのその他として登録する（保存値は、
// 予定のその他と同じ "other"）。
const CLASS = "class";
const PART_TIME = "part_time";
const OTHER = "other";
// 追加フォームのカテゴリの初期値（カレンダーから追加する予定で、最も多い
// と考えられるため。授業の予定は、授業の登録で作られる）。
const DEFAULT_CATEGORY = PART_TIME;
// 追加フォームのカテゴリのラジオボタンの id（保存値 → id）。
const CATEGORY_RADIO_IDS = {
  [CLASS]: "event-add-category-class",
  [PART_TIME]: "event-add-category-part-time",
  [OTHER]: "event-add-category-other",
};
// 時刻のないクリック（月表示の日付）の、開始・終了時刻の初期値と、
// 締切時刻の初期値（課題と同じ）。
const DEFAULT_START_TIME = "09:00";
const DEFAULT_END_TIME = "10:00";
const DEFAULT_DUE_TIME = "23:59";
// 1日の最後の時刻。日付をまたぐ予定は、1件では登録できないため、終了時刻を
// 1時間後に合わせるときも、これより後にしない。
const LAST_TIME = "23:59";

const ADD_FIELDS = {
  subject_id: {
    inputIds: ["event-add-subject"],
    messageId: "event-add-subject-error",
  },
  title: {
    inputIds: ["event-add-title"],
    messageId: "event-add-title-error",
  },
  employer: {
    inputIds: ["event-add-employer"],
    messageId: "event-add-employer-error",
  },
  date: {
    inputIds: ["event-add-date"],
    messageId: "event-add-date-error",
  },
  start_time: {
    inputIds: ["event-add-start-time"],
    messageId: "event-add-start-time-error",
  },
  end_time: {
    inputIds: ["event-add-end-time"],
    messageId: "event-add-end-time-error",
  },
  due_datetime: {
    inputIds: ["event-add-due-date", "event-add-due-time"],
    messageId: "event-add-due-error",
  },
  room: {
    inputIds: ["event-add-room"],
    messageId: "event-add-room-error",
  },
  notes: {
    inputIds: ["event-add-notes"],
    messageId: "event-add-notes-error",
  },
};
const ADD_FORM_ERROR_ID = "event-add-form-error";
const ADD_SUBMIT_LABELS = {
  idle: "登録する",
  busy: "登録中…",
};
const EDIT_FIELDS = {
  title: {
    inputIds: ["event-edit-title"],
    messageId: "event-edit-title-error",
  },
  employer: {
    inputIds: ["event-edit-employer"],
    messageId: "event-edit-employer-error",
  },
  date: {
    inputIds: ["event-edit-date"],
    messageId: "event-edit-date-error",
  },
  start_time: {
    inputIds: ["event-edit-start-time"],
    messageId: "event-edit-start-time-error",
  },
  end_time: {
    inputIds: ["event-edit-end-time"],
    messageId: "event-edit-end-time-error",
  },
  room: {
    inputIds: ["event-edit-room"],
    messageId: "event-edit-room-error",
  },
  notes: {
    inputIds: ["event-edit-notes"],
    messageId: "event-edit-notes-error",
  },
};
const EDIT_FORM_ERROR_ID = "event-edit-form-error";
const EDIT_SUBMIT_LABELS = {
  idle: "保存する",
  busy: "保存中…",
};
const DELETE_SUBMIT_LABELS = {
  idle: "削除する",
  busy: "削除中…",
};
const GENERATED_DELETE_NOTE =
  "授業の登録で作られた予定です。" +
  "授業全体を編集すると、今日以降の分は、作り直されます。";

// 登録・編集・削除ができたときに呼ぶ関数（initEventForms で受け取る）。
let notifyEventsChanged = () => {};
let notifyTasksChanged = () => {};
// 追加フォームを開くときに入れる値（openEventAddModal と「同じ内容で別の
// 日も登録」で控える）。入れるのは、モーダルを開くとき（show.bs.modal）。
let addValues = null;
// 追加・編集のフォームで、最初にフォーカスを置く欄の id。
let addFocusId = "";
let editFocusId = "";
// 追加フォームの授業の選択肢（今の学期の授業。教室の初期値に使う）。
let addSubjects = [];
// 最後に登録したアルバイト（「同じ内容で別の日も登録」で使う）。
let lastPartTimeEvent = null;
// 編集・削除の対象（予定のコピー）。
let editingEvent = null;
let deletingEvent = null;
// 追加・編集・削除のモーダルを開くたびに増やす通し番号。閉じて開き直した
// あとに届いた古い応答で、今のモーダルの表示を変えないために使う。
let addSerial = 0;
let editSerial = 0;
let deleteSerial = 0;
// 派遣会社の候補の取得の通し番号（古い応答で、候補を上書きしないため）。
let employerSerial = 0;

// 予定を表す文字列（例：「倉庫の仕分け」（2026年10月24日（土） 17:00 〜
// 21:00））。登録の知らせと、削除の確認の文に使う。
function eventLabel(apiEvent) {
  return (
    `「${apiEvent.title}」` +
    `（${formatJapaneseDateWithWeekday(apiEvent.date)} ` +
    `${apiEvent.start_time} 〜 ${apiEvent.end_time}）`
  );
}

// 時刻（HH:MM）の1時間後。23時台は、日付をまたがないように LAST_TIME。
function oneHourLater(time) {
  const [hours, minutes] = time.split(":").map(Number);
  if (hours >= 23) {
    return LAST_TIME;
  }
  return (
    `${String(hours + 1).padStart(2, "0")}:` +
    `${String(minutes).padStart(2, "0")}`
  );
}

// 開始時刻を変えて、終了時刻が開始時刻以下になったときは、終了時刻を、
// 開始時刻の1時間後に合わせる（授業の登録と同じ。追加・編集のフォームで
// 使う）。HH:MMは桁が固定されているため、文字列の大小で時刻を比べられる。
function adjustEndTime(startInputId, endInputId) {
  const startInput = getElement(startInputId);
  const endInput = getElement(endInputId);
  if (startInput.value === "" || endInput.value > startInput.value) {
    return;
  }
  endInput.value = oneHourLater(startInput.value);
}

// 欄（rowId）を表示・非表示にし、中の入力欄を、表示するときだけ使える
// ようにする（隠した欄の入力チェック（必須）で、送信が止まらないように、
// 隠した入力欄は無効にする）。
function setFieldRowVisible(rowId, inputIds, visible) {
  setVisible(getElement(rowId), visible);
  for (const inputId of inputIds) {
    getElement(inputId).disabled = !visible;
  }
}

// モーダル（modalId）を、JavaScriptから開く。
function showModal(modalId) {
  window.bootstrap.Modal.getOrCreateInstance(getElement(modalId)).show();
}

// 派遣会社の入力候補（datalist）を、予定APIの派遣会社の候補（新しく
// 使った順）で作り直す。候補は入力の補助のため、取得に失敗しても、何も
// 表示しない（候補なしで入力できる。それまでの候補は残る）。
async function loadEmployerOptions() {
  const currentRequest = ++employerSerial;
  let employers;
  try {
    employers = await apiRequest("GET", "/api/events/employers");
  } catch (error) {
    // ApiError でない例外（プログラムの誤りなど）は、console.error に出す。
    if (!(error instanceof ApiError)) {
      console.error(error);
    }
    return;
  }

  if (currentRequest !== employerSerial) {
    return;
  }
  const options = employers.map((employer) => {
    const option = document.createElement("option");
    option.value = employer;
    return option;
  });
  getElement("event-employer-options").replaceChildren(...options);
}

// 追加フォームで選んでいるカテゴリ（保存値）。
function selectedAddCategory() {
  for (const [category, radioId] of Object.entries(CATEGORY_RADIO_IDS)) {
    if (getElement(radioId).checked) {
      return category;
    }
  }
  return DEFAULT_CATEGORY;
}

// 追加フォームが、その他の「締切のみ」か。
function isDeadlineOnly() {
  return (
    selectedAddCategory() === OTHER &&
    getElement("event-add-other-type-deadline").checked
  );
}

// 追加フォームの欄を、選んでいるカテゴリに合わせる（入力した値は残す）。
function applyAddCategory() {
  const category = selectedAddCategory();
  const timed = !isDeadlineOnly();
  setVisible(getElement("event-add-other-type-row"), category === OTHER);
  setFieldRowVisible(
    "event-add-subject-row",
    ["event-add-subject"],
    category === CLASS,
  );
  setFieldRowVisible(
    "event-add-title-row",
    ["event-add-title"],
    category !== CLASS,
  );
  setFieldRowVisible(
    "event-add-employer-row",
    ["event-add-employer"],
    category === PART_TIME,
  );
  setFieldRowVisible("event-add-date-row", ["event-add-date"], timed);
  setFieldRowVisible(
    "event-add-time-row",
    ["event-add-start-time", "event-add-end-time"],
    timed,
  );
  setFieldRowVisible(
    "event-add-due-row",
    ["event-add-due-date", "event-add-due-time"],
    !timed,
  );
  setFieldRowVisible(
    "event-add-room-row",
    ["event-add-room"],
    category === CLASS,
  );
  getElement("event-add-title-label").textContent =
    category === PART_TIME ? "仕事内容" : "タイトル";
}

// 追加フォームを開く（カレンダーの空き枠のクリック）。date は
// 「YYYY-MM-DD」。time は、クリックした時刻（「HH:MM」。時刻のない
// クリックは null）。deadlineOnly が true なら、その他の「締切のみ」を
// 選んだ状態で開く（週表示の「締切」の行のクリック）。
export function openEventAddModal({ date, time = null, deadlineOnly = false }) {
  addValues = {
    category: deadlineOnly ? OTHER : DEFAULT_CATEGORY,
    deadlineOnly,
    date,
    startTime: time ?? DEFAULT_START_TIME,
    endTime: time === null ? DEFAULT_END_TIME : oneHourLater(time),
    dueDate: date,
    dueTime: time ?? DEFAULT_DUE_TIME,
    title: "",
    employer: "",
    notes: "",
    // 最初のフォーカスは、カテゴリで決める（null）。
    focusId: null,
  };
  showModal("event-add-modal");
}

// 「同じ内容で別の日も登録」。最後に登録したアルバイトの、日付以外を
// 入れた追加フォームを開く（日付は空。最初のフォーカスは、日付の欄）。
function openRepeatAddModal() {
  const source = lastPartTimeEvent;
  addValues = {
    category: PART_TIME,
    deadlineOnly: false,
    date: "",
    startTime: source.start_time,
    endTime: source.end_time,
    dueDate: "",
    dueTime: DEFAULT_DUE_TIME,
    title: source.title,
    employer: source.employer ?? "",
    notes: source.notes ?? "",
    focusId: "event-add-date",
  };
  showModal("event-add-modal");
}

// カレンダーの上の、アルバイトを登録したことの知らせ（「同じ内容で別の日も
// 登録」のボタンつき）。
function showAddedNotice(createdEvent) {
  lastPartTimeEvent = { ...createdEvent };
  getElement("event-added-notice-message").textContent =
    `${eventLabel(createdEvent)}を登録しました。`;
  setVisible(getElement("event-added-notice"), true);
}

function hideAddedNotice() {
  setVisible(getElement("event-added-notice"), false);
}

// 追加フォームの授業の選択肢（今の学期の授業）を取得する。currentSerial
// は、取得を始めたときの追加のモーダルの通し番号。
async function loadAddSubjects(currentSerial) {
  const select = getElement("event-add-subject");
  const note = getElement("event-add-subject-note");
  addSubjects = [];
  // 授業を取得するまでは、「選択してください」だけ（必須のため、ブラウザの
  // 入力チェックで、授業の登録は止まる）。
  renderSubjectOptions(select, []);
  note.textContent = SUBJECTS_LOADING_NOTE;

  let result;
  try {
    result = await fetchCurrentSubjects();
  } catch (error) {
    // モーダルを開き直していたら、今のモーダルの表示を変えない。
    if (currentSerial !== addSerial) {
      return;
    }
    // 授業の欄の下に出す（ほかのカテゴリは、登録できる）。
    note.textContent = errorMessageOf(error);
    return;
  }

  if (currentSerial !== addSerial) {
    return;
  }
  addSubjects = result.subjects;
  renderSubjectOptions(select, result.subjects);
  note.textContent = currentSubjectsNote(result.semester, result.subjects);
}

// 授業を選んだら、その授業の教室を、教室の欄に入れる（選び直すたびに
// 入れ直す。教室のない授業と、「選択してください」は、空にする）。
function fillRoomFromSubject() {
  const subjectId = Number(getElement("event-add-subject").value);
  const subject = addSubjects.find((item) => item.id === subjectId);
  getElement("event-add-room").value = subject?.room ?? "";
}

// 追加のモーダルを開くたびに、入力欄に、控えた値を入れ、エラーの表示と、
// アルバイトを登録したことの知らせを消す。授業の選択肢と、派遣会社の
// 候補を取得する。
function prepareAddModal() {
  const currentSerial = ++addSerial;
  const values = addValues;

  hideAddedNotice();
  getElement("event-add-form").reset();
  getElement(CATEGORY_RADIO_IDS[values.category]).checked = true;
  getElement(
    values.deadlineOnly
      ? "event-add-other-type-deadline"
      : "event-add-other-type-timed",
  ).checked = true;
  getElement("event-add-title").value = values.title;
  getElement("event-add-employer").value = values.employer;
  getElement("event-add-date").value = values.date;
  getElement("event-add-start-time").value = values.startTime;
  getElement("event-add-end-time").value = values.endTime;
  getElement("event-add-due-date").value = values.dueDate;
  getElement("event-add-due-time").value = values.dueTime;
  getElement("event-add-room").value = "";
  getElement("event-add-notes").value = values.notes;
  clearFormErrors(ADD_FIELDS, ADD_FORM_ERROR_ID);
  setSubmitting(
    getElement("event-add-submit-button"),
    false,
    ADD_SUBMIT_LABELS,
  );
  applyAddCategory();
  if (values.focusId !== null) {
    addFocusId = values.focusId;
  } else {
    addFocusId =
      values.category === CLASS ? "event-add-subject" : "event-add-title";
  }

  loadAddSubjects(currentSerial);
  loadEmployerOptions();
}

// 追加フォームの値から、登録の要求（URLと本文）を作る。
function addRequestOf() {
  const category = selectedAddCategory();
  const notes = getElement("event-add-notes").value;
  if (isDeadlineOnly()) {
    // 締切のみは、課題・タスクのAPIで、その他として登録する。
    const dueDate = getElement("event-add-due-date").value;
    const dueTime = getElement("event-add-due-time").value;
    return {
      url: "/api/tasks",
      body: {
        category: OTHER,
        title: getElement("event-add-title").value,
        due_datetime: `${dueDate}T${dueTime}`,
        notes,
      },
    };
  }

  const body = {
    category,
    date: getElement("event-add-date").value,
    start_time: getElement("event-add-start-time").value,
    end_time: getElement("event-add-end-time").value,
    notes,
  };
  if (category === CLASS) {
    // 授業の予定のタイトルは、送らない（授業の科目名になる）。
    body.subject_id = Number(getElement("event-add-subject").value);
    body.room = getElement("event-add-room").value;
  } else {
    body.title = getElement("event-add-title").value;
  }
  if (category === PART_TIME) {
    body.employer = getElement("event-add-employer").value;
  }
  return { url: "/api/events", body };
}

async function submitEventAdd(event) {
  event.preventDefault();
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = addSerial;
  const deadlineOnly = isDeadlineOnly();
  const { url, body } = addRequestOf();
  clearFormErrors(ADD_FIELDS, ADD_FORM_ERROR_ID);

  const submitButton = getElement("event-add-submit-button");
  setSubmitting(submitButton, true, ADD_SUBMIT_LABELS);

  // try で囲むのは、登録の要求だけにする（成功後の処理の例外を、
  // 「登録の失敗」として表示しないため）。
  let created;
  try {
    created = await apiRequest("POST", url, body);
  } catch (error) {
    if (startedSerial !== addSerial) {
      return;
    }
    showApiError(error, ADD_FIELDS, ADD_FORM_ERROR_ID);
    setSubmitting(submitButton, false, ADD_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === addSerial) {
    hideModal(getElement("event-add-modal"));
    if (!deadlineOnly && created.category === PART_TIME) {
      showAddedNotice(created);
    }
  }
  if (deadlineOnly) {
    notifyTasksChanged();
    return;
  }
  notifyEventsChanged();
}

// 日付を変えられない予定か（自動生成の授業の予定。「カレンダーからの
// 授業の予定の操作」）。自動生成の予定は、授業の予定だけ。
function hasFixedDate(apiEvent) {
  return apiEvent.is_generated;
}

// 編集のモーダルを開く（予定の詳細パネルの「編集」）。入力欄は、モーダルを
// 開くとき（show.bs.modal）に入れる。
export function openEventEditModal(apiEvent) {
  editingEvent = { ...apiEvent };
  showModal("event-edit-modal");
}

// 編集のモーダルを開くたびに、対象の今の値を入力欄に入れ、エラーの表示を
// 消す。カテゴリと、授業の予定の授業は、表示だけ（変えられない）。
function prepareEditModal() {
  editSerial += 1;
  const target = editingEvent;
  const category = eventCategoryOf(target.category);
  const isClass = target.category === CLASS;
  const fixedDate = hasFixedDate(target);

  getElement("event-edit-form").reset();
  getElement("event-edit-category-icon").textContent = category.icon;
  getElement("event-edit-category").textContent = category.label;
  // 授業の予定のタイトルは、追加・作成したときの授業の科目名の控え。
  getElement("event-edit-subject").textContent = target.title;
  setVisible(getElement("event-edit-subject-row"), isClass);
  setFieldRowVisible("event-edit-title-row", ["event-edit-title"], !isClass);
  getElement("event-edit-title-label").textContent =
    target.category === PART_TIME ? "仕事内容" : "タイトル";
  setFieldRowVisible(
    "event-edit-employer-row",
    ["event-edit-employer"],
    target.category === PART_TIME,
  );
  setFieldRowVisible("event-edit-date-row", ["event-edit-date"], !fixedDate);
  setVisible(getElement("event-edit-fixed-date-row"), fixedDate);
  setFieldRowVisible("event-edit-room-row", ["event-edit-room"], isClass);

  getElement("event-edit-title").value = isClass ? "" : target.title;
  getElement("event-edit-employer").value = target.employer ?? "";
  getElement("event-edit-date").value = target.date;
  getElement("event-edit-fixed-date").textContent =
    formatJapaneseDateWithWeekday(target.date);
  getElement("event-edit-start-time").value = target.start_time;
  getElement("event-edit-end-time").value = target.end_time;
  getElement("event-edit-room").value = target.room ?? "";
  getElement("event-edit-notes").value = target.notes ?? "";
  clearFormErrors(EDIT_FIELDS, EDIT_FORM_ERROR_ID);
  setSubmitting(
    getElement("event-edit-submit-button"),
    false,
    EDIT_SUBMIT_LABELS,
  );
  editFocusId = isClass ? "event-edit-start-time" : "event-edit-title";

  if (target.category === PART_TIME) {
    loadEmployerOptions();
  }
}

// 編集の本文。変えられる項目を、すべて送る（変えていない項目も、今の値の
// まま送る）。変えられない項目（カテゴリ・授業・授業の予定のタイトル・
// 自動生成の予定の日付）は、送らない。
function editRequestBodyOf(target) {
  const body = {
    start_time: getElement("event-edit-start-time").value,
    end_time: getElement("event-edit-end-time").value,
    notes: getElement("event-edit-notes").value,
  };
  if (!hasFixedDate(target)) {
    body.date = getElement("event-edit-date").value;
  }
  if (target.category === CLASS) {
    body.room = getElement("event-edit-room").value;
  } else {
    body.title = getElement("event-edit-title").value;
  }
  if (target.category === PART_TIME) {
    body.employer = getElement("event-edit-employer").value;
  }
  return body;
}

async function submitEventEdit(event) {
  event.preventDefault();
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = editSerial;
  const target = editingEvent;
  const body = editRequestBodyOf(target);
  clearFormErrors(EDIT_FIELDS, EDIT_FORM_ERROR_ID);

  const submitButton = getElement("event-edit-submit-button");
  setSubmitting(submitButton, true, EDIT_SUBMIT_LABELS);

  // try で囲むのは、編集の要求だけにする（登録と同じ理由）。
  try {
    await apiRequest("PATCH", `/api/events/${target.id}`, body);
  } catch (error) {
    if (startedSerial !== editSerial) {
      return;
    }
    showApiError(error, EDIT_FIELDS, EDIT_FORM_ERROR_ID);
    setSubmitting(submitButton, false, EDIT_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === editSerial) {
    hideModal(getElement("event-edit-modal"));
  }
  notifyEventsChanged();
}

// 削除の確認のモーダルを開く（予定の詳細パネルの「削除」）。
export function openEventDeleteModal(apiEvent) {
  deletingEvent = { ...apiEvent };
  showModal("event-delete-modal");
}

function showDeleteError(error) {
  const deleteError = getElement("event-delete-error");
  deleteError.textContent = errorMessageOf(error);
  setVisible(deleteError, true);
}

function hideDeleteError() {
  const deleteError = getElement("event-delete-error");
  deleteError.replaceChildren();
  setVisible(deleteError, false);
}

// 削除の確認のモーダルを開くたびに、対象を表示し、エラーを消す。自動生成の
// 授業の予定には、作り直されることの注意を添える（それ以外は、注意の
// 文字を空にする。読み上げの説明（aria-describedby）に入らないように）。
function prepareDeleteModal() {
  deleteSerial += 1;
  const generated = deletingEvent.is_generated;
  getElement("event-delete-target").textContent =
    `${eventLabel(deletingEvent)}を削除します。`;
  const note = getElement("event-delete-generated-note");
  note.textContent = generated ? GENERATED_DELETE_NOTE : "";
  setVisible(note, generated);
  hideDeleteError();
  setSubmitting(
    getElement("event-delete-submit-button"),
    false,
    DELETE_SUBMIT_LABELS,
  );
}

async function submitEventDelete() {
  // 応答が届くまでに、モーダルを開き直したかを確かめるために控える。
  const startedSerial = deleteSerial;
  const eventId = deletingEvent.id;
  hideDeleteError();

  const submitButton = getElement("event-delete-submit-button");
  setSubmitting(submitButton, true, DELETE_SUBMIT_LABELS);

  // try で囲むのは、削除の要求だけにする（登録と同じ理由）。
  try {
    await apiRequest("DELETE", `/api/events/${eventId}`);
  } catch (error) {
    if (startedSerial !== deleteSerial) {
      return;
    }
    showDeleteError(error);
    setSubmitting(submitButton, false, DELETE_SUBMIT_LABELS);
    return;
  }

  // モーダルを開き直していたら、今のモーダルは閉じない。
  if (startedSerial === deleteSerial) {
    hideModal(getElement("event-delete-modal"));
  }
  notifyEventsChanged();
}

// 初期化。onEventsChanged は、予定を登録・編集・削除できたときに、
// onTasksChanged は、その他（締切のみ）を登録できたときに呼ぶ関数
// （カレンダーの予定・締切を取得し直す）。
export function initEventForms({ onEventsChanged, onTasksChanged }) {
  notifyEventsChanged = onEventsChanged;
  notifyTasksChanged = onTasksChanged;

  // 追加・編集・削除のモーダルは、成功したら、JavaScriptから閉じるため、
  // 表示の途中かを記録する（ui.js の hideModal）。
  const addModal = getElement("event-add-modal");
  trackModalShowing(addModal);
  addModal.addEventListener("show.bs.modal", prepareAddModal);
  addModal.addEventListener("shown.bs.modal", () => {
    getElement(addFocusId).focus();
  });
  const addRadioIds = [
    ...Object.values(CATEGORY_RADIO_IDS),
    "event-add-other-type-timed",
    "event-add-other-type-deadline",
  ];
  for (const radioId of addRadioIds) {
    getElement(radioId).addEventListener("change", applyAddCategory);
  }
  getElement("event-add-subject").addEventListener(
    "change",
    fillRoomFromSubject,
  );
  getElement("event-add-start-time").addEventListener("change", () => {
    adjustEndTime("event-add-start-time", "event-add-end-time");
  });
  getElement("event-add-form").addEventListener("submit", submitEventAdd);

  // アルバイトを登録したことの知らせ。カレンダーのモードを開き直したときも
  // 消す。
  getElement("event-repeat-button").addEventListener(
    "click",
    openRepeatAddModal,
  );
  getElement("event-added-notice-close-button").addEventListener(
    "click",
    hideAddedNotice,
  );
  getElement("calendar-tab").addEventListener("shown.bs.tab", hideAddedNotice);

  const editModal = getElement("event-edit-modal");
  trackModalShowing(editModal);
  editModal.addEventListener("show.bs.modal", prepareEditModal);
  editModal.addEventListener("shown.bs.modal", () => {
    getElement(editFocusId).focus();
  });
  getElement("event-edit-start-time").addEventListener("change", () => {
    adjustEndTime("event-edit-start-time", "event-edit-end-time");
  });
  getElement("event-edit-form").addEventListener("submit", submitEventEdit);

  const deleteModal = getElement("event-delete-modal");
  trackModalShowing(deleteModal);
  deleteModal.addEventListener("show.bs.modal", prepareDeleteModal);
  // 取り消せない操作のため、最初のフォーカスは「キャンセル」に置く。
  deleteModal.addEventListener("shown.bs.modal", () => {
    getElement("event-delete-cancel-button").focus();
  });
  getElement("event-delete-submit-button").addEventListener(
    "click",
    submitEventDelete,
  );
}
```

### 付録G. `app/static/js/calendar.js`

<!-- 全文: app/static/js/calendar.js -->
```
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
  initEventForms,
  openEventAddModal,
  openEventDeleteModal,
  openEventEditModal,
} from "./event_forms.js";
import {
  createOverdueBadge,
  createTaskTitle,
  isTaskOverdue,
  taskLabel,
} from "./task_display.js";
import {
  errorMessageOf,
  getElement,
  hideModal,
  setVisible,
  trackModalShowing,
} from "./ui.js";

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
// 予定の詳細パネルの対象（予定のコピー）。
let detailEvent = null;
// 詳細パネル（予定・締切）を閉じたあとに行う操作（「編集」「削除」で
// 控える）。ないときは null。
let afterDetailHidden = null;

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

// 予定の詳細パネルを開く。「編集」「削除」は、パネルを閉じてから、
// 編集・削除の確認のモーダルを開く（event_forms.js）。
function showEventDetail(apiEvent) {
  detailEvent = { ...apiEvent };
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
// 開くとき（show.bs.modal）に入れる。「編集」「削除」は、パネルを閉じて
// から、課題・タスクモードの編集・削除の確認のモーダルを開く。
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

// 詳細パネル（予定・締切。modalId）を閉じ、閉じ終わってから
// （hidden.bs.modal）、action を行う（Bootstrapでは、2つのモーダルを
// 重ねて開けないため）。表示の途中なら、表示が終わってから閉じる
// （ui.js の hideModal）。
function closeDetailThen(modalId, action) {
  afterDetailHidden = action;
  hideModal(getElement(modalId));
}

// 詳細パネルが閉じたとき（hidden.bs.modal）に、控えた操作を行う。
function runAfterDetailHidden() {
  const action = afterDetailHidden;
  afterDetailHidden = null;
  if (action !== null) {
    action();
  }
}

// 課題・タスクモードに、編集・削除のモーダルを開くように頼む（eventName は
// task-edit-requested か task-delete-requested。モードのファイル同士は、
// 互いを import しないため、CustomEvent でつなぐ）。
function requestTaskAction(eventName, task) {
  document.dispatchEvent(
    new CustomEvent(eventName, { detail: { task: { ...task } } }),
  );
}

// 空き枠のクリック（FullCalendarの dateClick）。追加フォームを、クリック
// した日時を入れて開く。週表示の時間軸は、日付と、30分の枠の始まりの
// 時刻。週表示の「締切」の行（終日の行）は、その他の「締切のみ」。月表示の
// 日付の枠は、日付だけ（時刻は、初期値）。一覧表示では、起きない。
function handleDateClick(info) {
  const [date, time] = localDateTimeString(info.date).split("T");
  if (!info.allDay) {
    openEventAddModal({ date, time });
    return;
  }
  if (info.view.type === WEEK_VIEW) {
    openEventAddModal({ date, deadlineOnly: true });
    return;
  }
  openEventAddModal({ date });
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
    // 空き枠のクリック。予定・締切・月表示の日付の数字・「＋N件」の
    // クリックでは、起きない（FullCalendarの仕様）。
    dateClick: handleDateClick,
  });
  // 予定の追加・編集・削除のモーダル（event_forms.js）。登録・編集・削除が
  // できたら、予定（その他（締切のみ）は、締切と「直近の締切」欄）を
  // 取得し直す。
  initEventForms({
    onEventsChanged: () => {
      calendar.refetchEvents();
    },
    onTasksChanged: () => {
      loadDeadlines({ showLoading: false });
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

  // 詳細パネル（予定・締切）は、「編集」「削除」で、JavaScriptから閉じる
  // ため、表示の途中かを記録する（ui.js の hideModal）。開くときは、前に
  // 控えた操作を消す。閉じたら、控えた操作を行う。
  for (const modalId of ["event-modal", "task-detail-modal"]) {
    const modal = getElement(modalId);
    trackModalShowing(modal);
    modal.addEventListener("show.bs.modal", () => {
      afterDetailHidden = null;
    });
    modal.addEventListener("hidden.bs.modal", runAfterDetailHidden);
  }
  getElement("event-modal-edit-button").addEventListener("click", () => {
    const target = detailEvent;
    closeDetailThen("event-modal", () => openEventEditModal(target));
  });
  getElement("event-modal-delete-button").addEventListener("click", () => {
    const target = detailEvent;
    closeDetailThen("event-modal", () => openEventDeleteModal(target));
  });
  getElement("task-detail-edit-button").addEventListener("click", () => {
    const target = detailTask;
    closeDetailThen("task-detail-modal", () => {
      requestTaskAction("task-edit-requested", target);
    });
  });
  getElement("task-detail-delete-button").addEventListener("click", () => {
    const target = detailTask;
    closeDetailThen("task-detail-modal", () => {
      requestTaskAction("task-delete-requested", target);
    });
  });
  // 課題・タスクモードで、課題・タスクを編集・削除したら（カレンダーの
  // 締切の詳細パネルから開いた場合を含む）、締切と「直近の締切」欄を
  // 取得し直す。
  document.addEventListener("task-changed", () => {
    loadDeadlines({ showLoading: false });
  });
  calendar.render();
  // カレンダーのモードは、ページを開いたときに表示されているため、ここで
  // 課題・タスクを取得する（タブの shown.bs.tab は、最初は起きない）。
  loadDeadlines();
}
```

### 付録H. `app/static/js/main.js`

<!-- 全文: app/static/js/main.js -->
```
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
// 課題・タスクとカレンダーは、カレンダーの締切の詳細パネルの「編集」
// 「削除」（task-edit-requested・task-delete-requested）と、編集・削除の
// 結果（task-changed）で、イベントでつながる。どちらも、利用者の操作の
// あとに発行するため、初期化の順序によらない。
initTasks();
// カレンダーは、予期しない例外で、ほかのモードの初期化が止まらないように、
// 最後に初期化する。
initCalendar();
```
