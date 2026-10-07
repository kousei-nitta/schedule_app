# タスク006: 授業UI（学期UIの整理を含む）

| 項目 | 内容 |
|---|---|
| Task ID | 006 |
| Task名 | 授業UI（学期UIの整理を含む） |
| ブランチ | `feature/006-subjects-ui`（Komaが作成・切替済みの状態で渡される） |

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに停止して報告する。

## 目的
授業モードの学期タブの下に、**選択中の学期の授業の一覧と、授業の登録（連続登録）** を実装し、Task 005の授業API（`GET`・`POST /api/subjects`）を、初めて画面から使えるようにする。次の3段階で行う。

| 段階 | 内容 | 画面の変化 |
|---|---|---|
| 1 | 学期UIの整理（Task 004のレビューのLow-1〜Low-6の修正）、共通処理 `ui.js` の切り出し、選択中の学期を知らせるイベント `semester-selected` の追加 | 既存の学期UIの仕様を維持し、承認済みのLow-1〜Low-6の修正による改善だけが加わる（下の「許される変化」） |
| 2 | 授業の一覧（表）。取得中・失敗・0件の表示 | 授業の一覧が出る |
| 3 | 「授業を追加」ボタンと、登録のモーダル（連続登録） | 授業を登録できる |

## 前提（Task 005完了時点の状態）

| 区分 | 内容 |
|---|---|
| すでにある | 授業API（`GET /api/subjects?semester_id=`、`GET /api/subjects/<id>`、`POST /api/subjects`）、学期API、pytest（**212件**）、`main.js`・`api.js`・`semesters.js`、学期UI（Task 004）。`#semester-detail` の中に、仮の注記「この学期の授業は、まだ登録できません（準備中）」がある |
| まだない | `ui.js`、`subjects.js`、授業の画面、`semester-selected` イベント |
| このタスクでAPIは変更しない | Pythonのファイル、テスト、`requirements.txt`、`migrations/` は、変更しない。それでも、完了の確認で、`python -m pytest` を実行し、**212件が合格したまま**であることを確認する |
| 暫定 | 授業の `POST` は、授業の行だけを作る（Eventの自動生成は、別のタスク）。**このタスクの確認で登録する授業は、テストデータ**として、科目名を「テスト」で始める。Eventの自動生成のタスクの前に、すべての授業を削除する（実際の授業は、そのあとで登録する） |
| 開発用DB | 実際の学期が入っている場合がある。Copilotは、`POST` を実行しない（確認で、データを作らない） |

## Source of Truth
- `docs/ui_ux.md`：「学期（タブと登録）」、「授業」
- `docs/architecture.md`：「JavaScriptの構成（ES modules）」（`ui.js`、規則、「モード間の連携（`CustomEvent`）」、「`api.js` の仕様」）、「授業API」、「エラー」
- `docs/requirements.md`：「学期」、「予定の登録」の授業モード
- `docs/tasks/004_semester_ui_and_js_foundation.md`：学期UIの仕様、DOM構成、エラー処理（段階1で、**既存の仕様を維持する**基準）
- `docs/tasks/005_subjects_api_and_pytest.md`：授業APIの仕様、エラーメッセージの文言
- `.github/copilot-instructions.md`：進め方、コーディング方針（JavaScript）、「テスト」

## 実装対象ファイル

| 区分 | ファイル | 段階 | 内容 |
|---|---|---|---|
| 新規 | `app/static/js/ui.js` | 1 | 表示・フォームの共通処理 |
| 変更 | `app/static/js/semesters.js` | 1 | Low-1〜Low-6の修正、`selectSemester(id)`、イベントの発行、`ui.js` の利用 |
| 新規 | `app/static/js/subjects.js` | 2・3 | 授業の一覧（段階2）、登録フォーム（段階3） |
| 変更 | `app/static/js/main.js` | 2 | `initSubjects()` の追加 |
| 変更 | `app/templates/index.html` | 2・3 | 授業の一覧（段階2）、「授業を追加」ボタンとモーダル（段階3） |

## 非対象（このタスクでは作らない・変更しない）
- Pythonのファイルのすべて（`app/*.py`、`app/routes/`、`app/models/`）、`tests/`、`pytest.ini`、`requirements.txt`、`migrations/`、`run.py`、`instance/` の中のデータ
- `app/static/js/api.js`、`app/templates/base.html`
- `docs/`、`.github/`
- 授業の**編集・削除**（授業一覧の操作列、確認ダイアログ）、Eventの自動生成、課題・カレンダーのUI、`calendar.js`・`tasks.js`
- 独自のCSS（`app/static/css/` を作らない）、`style` 属性、ライブラリの追加、JavaScriptの自動テスト、`dates.js`（日付補助の共通化）
- Task 004のレビューの参考項目（矢印キーでのタブの移動、応答が読めない場合の扱い、`Object.hasOwn` の対応ブラウザ）

## 段階1：学期UIの整理（既存の仕様を維持し、承認済みの修正による改善だけを行う）

**この段階の最重要事項は、既存の学期UIの仕様を維持し、承認済みのLow-1〜Low-6の修正による改善だけを行うこと。** 既存の仕様を壊さない。`index.html` の学期のブロック（ID・クラス・構造・文言）は、変更しない。

**許される変化**（これ以外の変化は、仕様からの逸脱として、扱う）

| 変化 | 根拠 |
|---|---|
| タブをキーボードで選んだとき、フォーカスが、そのタブに残る（以前は失われた） | Low-2 |
| 学期の登録に成功したとき、モーダルが閉じる間、送信ボタンのラベルが「登録中…」のままになる（「登録する」に戻る様子が、見えなくなる） | 送信ボタンの戻し方（`ui.js` の `setSubmitting` への整理に伴う。1-2の7） |
| 想定外の例外（プログラムの誤りなど）が起きたとき、技術的な英語のメッセージではなく、固定の日本語のメッセージが出る | Low-5 |
| 選択中の学期が変わったとき、`semester-selected` イベントが発行される（画面には、見えない） | Low-4 |
| `li` の `role`、モーダルを閉じる呼び出しの変更（画面には、見えない） | Low-3、Low-1 |

### 1-1. `app/static/js/ui.js`（新規）
`semesters.js` にある共通の処理を、移して、次の**6つの関数だけ**を、名前つきで `export` する（`api.js` から `ApiError` を `import` する）。日付の補助や、リソース固有の処理は、持たせない。

| 関数 | 内容 |
|---|---|
| `getElement(id)` | `document.getElementById`（既存の `semesters.js` の実装を、そのまま移す） |
| `setVisible(element, visible)` | Bootstrapの `d-none` の付け外し（既存の実装を、そのまま移す） |
| `errorMessageOf(error)` | `ApiError` なら、`error.message`。それ以外の例外（プログラムの誤りなど）なら、`console.error(error)` に出し、固定の文言「予期しないエラーが発生しました。ページを再読み込みして、もう一度お試しください」を返す（**Low-5**） |
| `clearFormErrors(fieldMap, formErrorId)` | `fieldMap` の各項目について、エラー表示の要素の中身を空にし、入力欄から `is-invalid` を外す。`formErrorId` の要素の中身を空にして、隠す |
| `showApiError(error, fieldMap, formErrorId)` | まず `clearFormErrors` を行う。`error` が `ApiError` で、`code` が `validation_error`、`fields` が `null` でないとき：`fields` のうち `fieldMap` にある項目は、その項目のエラー表示に `textContent` で表示し、入力欄に `is-invalid` を付ける。`fieldMap` にない項目がある場合、または `fields` が空の場合は、フォーム上部に「入力内容に誤りがあります」を表示する。そうでない場合は、フォーム上部に `errorMessageOf(error)` を表示する（Task 004の `showSubmitError` と、**同じ結果**になること） |
| `setSubmitting(button, submitting, labels)` | `button.disabled = submitting`。ラベル（`textContent`）は、`submitting` なら `labels.busy`、そうでなければ `labels.idle` |

`fieldMap` の形：`{ "<APIの項目名>": { inputIds: ["<入力欄のid>", ...], messageId: "<エラー表示のid>" }, ... }`（入力欄がない項目は、`inputIds` を空の配列にする）

`ui.js` の中で、`showApiError` が使う補助の処理（項目のエラーの表示、フォーム上部のメッセージの表示）は、`export` しない非公開の関数にする（Task 004の `setFieldError`・`showFormMessage` に当たる。名前は任意）。`ui.js` の公開関数は、上の6つだけで、`semesters.js` と `subjects.js` は、この6つだけを使う。

### 1-2. `app/static/js/semesters.js` の変更
1. **`selectSemester(id)`（Low-4）**：`id` は、学期のid、または `null`。**`selectedId` への代入は、この関数の中だけで行う**（初期の `let selectedId = null` を除く）。この関数が、次を行う
   1. `selectedId` を更新する（前の値を、控えておく）
   2. タブの選択の表示を、更新する（下の `updateTabSelection`）。本文（名前・期間）を、更新する
   3. 前の値と `id` が違うときだけ、`document.dispatchEvent(new CustomEvent("semester-selected", { detail: { semester } }))` を発行する。`semester` は、`{ id, name, start_date, end_date }` の**コピー**（`id` が `null` なら `null`）。発行は、画面（タブ・本文）が新しい選択を反映した**あと**に行う
2. **タブを作り直さない（Low-2）**：タブのボタンは、一覧を取得したとき（`loadSemesters`）に1回だけ作る。選択が変わったときは、`updateTabSelection()` で、既存のボタンの `active` と `aria-selected`、本文の `aria-labelledby` を付け替える。タブのクリックは、`selectSemester(semester.id)` を呼ぶだけにする
3. **`li` に `role="presentation"`（Low-3）**
4. **モーダルを閉じる処理（Low-1）**：`getInstance(...)` を、`getOrCreateInstance(...)` に変える
5. **`ui.js` の利用（Low-5・Low-6）**：`semesters.js` から、次の関数の定義を削除し、右の置き換え先に替える。`ui.js` から `import` するのは、公開関数の6つ（`getElement`・`setVisible`・`errorMessageOf`・`clearFormErrors`・`showApiError`・`setSubmitting`）だけ。

   | 削除する関数・処理 | 置き換え先 |
   |---|---|
   | `getElement` | `ui.js` の `getElement` |
   | `setVisible` | `ui.js` の `setVisible` |
   | `clearFormErrors()` | `ui.js` の `clearFormErrors(fieldMap, formErrorId)` |
   | `showSubmitError(error)` | `ui.js` の `showApiError(error, fieldMap, formErrorId)` |
   | `setFieldError`・`showFormMessage` | `ui.js` の非公開の補助関数に移る。`semesters.js` からは、使わない |
   | 送信ボタンの `disabled`・`textContent` の直接の書き換え | `ui.js` の `setSubmitting` |
   | `showLoadError` の `error.message` | `errorMessageOf(error)` |

   `fieldMap`（`SEMESTER_FIELDS`）は、`name`（`semester-year`・`semester-term`、`semester-name-error`）、`start_date`（`semester-start-date`、`semester-start-date-error`）、`end_date`（`semester-end-date`、`semester-end-date-error`）。フォーム上部は `semester-form-error`
6. **読みやすさ（Low-6）**：`resetForm` の月の数字の比較に、「`getMonth()` は0始まり（3は4月、7は8月）」というコメントを書く。`loadSemesters` は、`selectSemester(...)` を使う（0件のときは `selectSemester(null)`、1件以上のときは、一覧を表示し、タブを作ってから `selectSemester(選んだid)`。登録後は、登録した学期のid）
7. **送信ボタンの戻し方**：成功したときは、ボタンを元に戻さない（モーダルが閉じる間に、ラベルが「登録する」へ戻るちらつきを避ける）。元に戻すのは、失敗したときと、モーダルを開くたびの初期化（`resetForm`）のとき。`ui.js` の `setSubmitting` を使う
8. 上記以外の仕様（初期選択の規則、バナー、日付の変換、文言、DOMのID、APIの呼び出し）は、**維持する**

### 1-3. Low-1〜Low-6の対応表

| 項目 | 対応 |
|---|---|
| Low-1 `getInstance` | 1-2の4 |
| Low-2 タブ再描画でフォーカスが失われる | 1-2の2 |
| Low-3 `li` の `role="presentation"` | 1-2の3 |
| Low-4 選択状態の集約 | 1-2の1 |
| Low-5 想定外の例外の表示 | 1-1の `errorMessageOf`、1-2の5 |
| Low-6 読みやすさ | 1-2の5・6 |

### 1-4. `main.js`
段階1では、変更しない（`initSubjects` は、段階2で足す）。

## 段階2：授業の一覧

### 2-1. `index.html` の変更
`#semester-detail` の中の、仮の注記 `<p class="text-muted">この学期の授業は、まだ登録できません（準備中）</p>` を、次のブロックに置き換える。**ID・クラス・構造は、このとおり**にする。段階2では、見出し行の「授業を追加」ボタンは、作らない（段階3で足す）。

```html
<div id="subject-section" class="mt-4">
  <div class="d-flex justify-content-between align-items-center mb-2">
    <h3 class="h6 mb-0">授業</h3>
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
        </tr>
      </thead>
      <tbody id="subject-table-body"></tbody>
    </table>
  </div>
</div>
```

### 2-2. `app/static/js/subjects.js`（新規）と `main.js`
- `export function initSubjects()` だけを `export` する。`semesters.js` を `import` しない（`ui.js` と `api.js` だけ）
- `main.js` は、`initSubjects` を `import` し、**`initSubjects()` を、`initSemesters()` より先に呼ぶ**。コメントに、理由（購読する側を、先に呼ぶ規則）を書く
- 状態は、モジュールの中の変数：選択中の学期（`currentSemester`、初期値は `null`）、要求の通し番号（`requestSerial`）
- `initSubjects()` の中で（同期処理）、`document` の `semester-selected` を購読する。受け取ったら、`currentSemester = event.detail.semester`、`requestSerial` を1増やす。`currentSemester` が `null` なら、一覧を空にして終わる。そうでなければ、一覧を取得する
- 「再読み込み」ボタンは、`currentSemester` の一覧を取得し直す
- **一覧の取得**：`apiRequest("GET", `/api/subjects?semester_id=${id}`)`。要求のたびに、`requestSerial` を1増やし、その値を控える。応答が届いたとき、`requestSerial` が控えた値と違えば、**結果を捨てる**（`ui.js` の規則どおり。学期のタブを素早く切り替えたときの、追い越しを防ぐ）。コメントに、理由を書く
- **表示の状態**：取得を始めたとき（その学期の最初の取得）は「読み込み中…」だけ。成功したら、0件なら `#subject-empty`、1件以上なら `#subject-list`。失敗したら、`#subject-load-error` に、`errorMessageOf(error)` と「再読み込み」
- **表の行**（`createElement` で作り、`replaceChildren()` で差し替える。`innerHTML` は使わない）：曜日（`["月", "火", "水", "木", "金", "土", "日"]` の、`weekday` 番目）、時間（`` `${start_time} 〜 ${end_time}` ``）、科目名（`<div>`）と、その下に、詳細・メモ（ある場合だけ。`<div class="text-muted small">`）、教室（`null` なら「—」）
- **メモの改行**：メモを、改行（`\n`、`\r\n`）で行に分け、行ごとの文字（`createTextNode`）を、`<br>` で区切って表示する

## 段階3：授業の登録（連続登録）

### 3-1. `index.html` の変更
1. 見出し行（`#subject-section` の中の、`<h3>` の右）に、次のボタンを足す

```html
<button type="button" id="subject-add-button" class="btn btn-primary btn-sm"
        data-bs-toggle="modal" data-bs-target="#subject-modal">授業を追加</button>
```

2. モーダルを、`{% block content %}` の中の最上位（**`<main>` の外**。学期のモーダルの隣）に、次のとおり置く

```html
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
```

### 3-2. `subjects.js` の追加（登録フォーム）
- **項目の対応表（`fieldMap`）**：`semester_id`（入力欄なし、エラー表示は `subject-semester-error`）、`subject_name`（`subject-name`、`subject-name-error`）、`room`（`subject-room`、`subject-room-error`）、`weekday`（`subject-weekday`、`subject-weekday-error`）、`start_time`（`subject-start-time`、`subject-start-time-error`）、`end_time`（`subject-end-time`、`subject-end-time-error`）、`notes`（`subject-notes`、`subject-notes-error`）。フォーム上部は `subject-form-error`
- **モーダルを開くとき（`show.bs.modal`）**：入力欄を初期値（科目名・教室・メモは空、曜日は `0`、開始 `09:00`、終了 `10:00`）に戻す。エラー表示と、登録済みのメッセージを消す。送信ボタンを元に戻す。`#subject-modal-semester` に、`currentSemester.name` を `textContent` で表示する
- **開いたあと（`shown.bs.modal`）**：科目名の欄に、フォーカスを移す
- **開始時刻を変えたとき（`change`）**：終了時刻が、開始時刻以下になっていたら、終了時刻を、開始時刻の1時間後に合わせる（時刻の文字列 `HH:MM` は、文字列のまま大小を比べられる。コメントに書く）。開始時刻は18:00までなので、1時間後（最大19:00）は、必ず選択肢にある
- **送信（`submit`）**：`event.preventDefault()`。エラー表示と、登録済みのメッセージを消す。`setSubmitting(ボタン, true, { idle: "登録する", busy: "登録中…" })`。`apiRequest("POST", "/api/subjects", body)`。`body` は、`semester_id`（`currentSemester.id`）、`subject_name`、`room`、`weekday`（`Number(...)`）、`start_time`、`end_time`、`notes`（入力欄の値のまま。前後の空白の除去・空文字の `null` 化は、APIが行う）
- **成功したとき**：モーダルは**閉じない**。`#subject-form-success` に、`「${created.subject_name}」を登録しました` を表示する（`textContent`）。入力欄を、初期値に戻す（登録済みのメッセージは、消さない）。科目名の欄に、フォーカスを戻す。送信ボタンを元に戻す。一覧を取得し直す（このときは、「読み込み中…」を出さず、一覧を表示したまま、取得できたら差し替える。失敗したときは、一覧の取得失敗の表示にする）
- **失敗したとき**：`showApiError(error, fieldMap, "subject-form-error")`。入力欄の値は、保持する。送信ボタンを元に戻す
- 入力の検証は、`required`（ブラウザ標準）だけ。`maxlength` などは、付けない（検証は、APIが行う）

### 3-3. DOMのID一覧（段階2・3）
`subject-section`、`subject-add-button`、`subject-loading`、`subject-load-error`、`subject-load-error-message`、`subject-retry-button`、`subject-empty`、`subject-list`、`subject-table-body`、`subject-modal`、`subject-modal-title`、`subject-modal-semester`、`subject-semester-error`、`subject-form`、`subject-form-success`、`subject-form-error`、`subject-name`、`subject-name-error`、`subject-room`、`subject-room-error`、`subject-weekday`、`subject-weekday-error`、`subject-start-time`、`subject-start-time-error`、`subject-end-time`、`subject-end-time-error`、`subject-notes`、`subject-notes-error`、`subject-submit-button`

## JavaScriptの共通の規則
`.github/copilot-instructions.md` の「コーディング方針（JavaScript）」と、`docs/architecture.md` の「JavaScriptの構成（ES modules）」の規則に従う（名前つきの `export`、`innerHTML` などの禁止、`textContent`、`fetch` は `api.js` だけ、日本語のコメント、など）。次の点を、特に守る。
- モードのファイル（`semesters.js`・`subjects.js`）同士は、`import` しない。連携は、`semester-selected` イベントだけ
- コメントに理由を書く箇所：①`selectSemester` にまとめた理由と、イベントを画面の更新のあとに発行する理由、②要求の通し番号で、古い応答を捨てる理由、③開始時刻の文字列を、文字列のまま比べられる理由、④`resetForm` の0始まりの月

## 実装手順
1. ブランチ・作業ツリーの確認。設計資料に、このタスクの前提が書かれていることを確認する。1つでも書かれていなければ、何も変更せずに停止して報告する
   - `docs/architecture.md`：`ui.js` の表の行、「モード間の連携（`CustomEvent`）」と `semester-selected` の表、規則の「`getOrCreateInstance`」「`role="presentation"`」
   - `docs/ui_ux.md`：「授業」の「連続登録」「登録フォーム（モーダル）」「一覧」
2. 作業の前の状態を記録する：`python -m pytest -q`（**212件が合格**。失敗があれば、停止して報告する）、開発用DBのハッシュ（`shasum -a 256 instance/app.db`）、`sqlite3 instance/app.db "SELECT COUNT(*) FROM subjects;"`
3. **段階1**：`ui.js` を作り、`semesters.js` を、変更する。「Copilot確認手順」の段階1の確認を行う
4. **段階2**：`index.html` の授業の一覧のブロック、`subjects.js`（一覧）、`main.js`。段階2の確認を行う
5. **段階3**：「授業を追加」ボタンとモーダル、`subjects.js`（登録フォーム）。段階3の確認を行う
6. 最終の確認を行い、結果を報告して止まる（ブラウザでの確認は、Komaが行う）

## 完了条件
- 「Copilot確認手順」のすべてが、期待どおり
- `python -m pytest` が、**212件、すべて合格**（件数が変わらない。失敗・エラー・スキップが0件）。開発用DBの前後のハッシュと、`subjects` の件数が同じ
- 「Komaのブラウザ確認」のすべてが、期待どおり（特に、段階1の学期UIの回帰）
- レビューで承認される

## Copilot確認手順
ブラウザは使えないので、次を確認する。**`POST` を実行しない。**

### 各段階の終わりに（共通）
```
python -m pytest -q                       # 212 passed（件数が変わらない）
```

### 段階1
| 確認 | 期待する結果 |
|---|---|
| `selectedId` への代入 | `semesters.js` の中で、`selectSemester` の中だけ（初期の `let selectedId = null` を除く） |
| `getInstance(` | 0件。`getOrCreateInstance(` が1件以上 |
| `role` の設定 | `li` に `"presentation"` を設定する行がある |
| イベントの発行 | `new CustomEvent("semester-selected"` が、`selectSemester` の中に1件だけ |
| 重複した定義 | `semesters.js` に、`getElement`・`setVisible`・`clearFormErrors`・`setFieldError`・`showSubmitError`・`showFormMessage` の定義が残っていない |
| `ui.js` の公開関数 | `export` が、`getElement`・`setVisible`・`errorMessageOf`・`clearFormErrors`・`showApiError`・`setSubmitting` の6つだけ。`semesters.js` が `import` するのは、この6つの中だけ |
| `index.html` | **変更なし**（`git diff` に、`index.html` が出ない） |
| 禁止事項（`app/static/js/` を検索） | 「禁止事項の検索」のとおり、すべて0件 |
| `git status` | 新規：`ui.js`。変更：`semesters.js` のみ |

### 段階2
```
BASE=http://127.0.0.1:5001
python run.py                                          # 別のターミナルで、以下を実行
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' $BASE/static/js/ui.js
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' $BASE/static/js/subjects.js
curl -s $BASE/ > /tmp/index.html                       # IDの確認に使う
curl -s -w '\nHTTP %{http_code}\n' "$BASE/api/subjects?semester_id=99999"   # 200、[]
```
| 確認 | 期待する結果 |
|---|---|
| `ui.js`・`subjects.js` | 200。`Content-Type` が JavaScript（HTMLではない） |
| `GET /` のHTML | 次のIDが、それぞれ1回ずつ含まれる：`subject-section`、`subject-loading`、`subject-load-error`、`subject-load-error-message`、`subject-retry-button`、`subject-empty`、`subject-list`、`subject-table-body`。仮の注記「準備中」が、なくなっている。`<script>` は、Bootstrapの1つと `type="module"` の1つだけ |
| `main.js` | `initSubjects()` が、`initSemesters()` より**前**に呼ばれている |
| `subjects.js` | `semesters.js` を `import` していない。`ui.js` から `import` するのは、公開関数の6つの中だけ。`fetch(` がない。`semester-selected` の購読が、`initSubjects` の中にある。`requestSerial`（要求の通し番号）で、古い応答を捨てている |
| `git status` | 新規：`ui.js`、`subjects.js`。変更：`semesters.js`、`main.js`、`index.html` のみ |

### 段階3
| 確認 | 期待する結果 |
|---|---|
| `GET /` のHTML | 「3-3. DOMのID一覧」のIDが、それぞれ1回ずつ含まれる。`subject-modal` が、`<main>` の外にある。`subject-add-button` が、`#subject-section` の中の見出し行にある。`style=`・`onclick=` がない |
| `subjects.js` | 開始時刻の自動調整、送信、成功時にモーダルを閉じない処理（`hide()` を呼ばない）、`showApiError` の利用、`setSubmitting` の利用がある。`maxlength`・`innerHTML` がない |

### 禁止事項の検索（段階の終わりごと）
`app/static/js/` と `app/templates/` の中で、次が**0件**：`innerHTML`、`outerHTML`、`insertAdjacentHTML`、`document.write`、`eval(`、`onclick`、`style=`、`localStorage`、`sessionStorage`、`var `、`export default`、`{{`（JSファイル内）。`fetch(` は、`api.js` の中だけ

### 最終
```
python -m pytest -q                                    # 212 passed
shasum -a 256 instance/app.db                          # 実施前と同じ
sqlite3 instance/app.db "SELECT COUNT(*) FROM subjects;"   # 実施前と同じ
lsof -i :5001                                          # サーバー停止後、出力が空
git status                                             # 新規：ui.js、subjects.js。変更：semesters.js、main.js、index.html のみ
git diff --stat
```
Pythonのファイル、`tests/`、`requirements.txt`、`migrations/`、`docs/`、`api.js`、`base.html` に、変更がないこと。**ブラウザでの確認は、していないと明記して報告する。**

## Komaのブラウザ確認
前提：`python run.py` で起動し、Chromeで開く。JavaScriptを直したあとは、強制再読み込み（Cmd＋Shift＋R）。開発者ツール（F12）のコンソールとネットワークを開いておく。**確認で登録する授業は、科目名を「テスト」で始める。** 段階1の回帰（R）が壊れていたら、授業の確認に進まず、報告する。

### R. 段階1：学期UIの回帰（既存の仕様が維持され、承認済みの修正による改善だけが加わっていること）
| 番号 | 操作 | 期待する結果 |
|---|---|---|
| R1 | ページを開き、「授業」を押す | 学期タブが並び、今日を含む学期が選択される。コンソールにエラーがない |
| R2 | 別のタブをクリックする | 本文（名前・期間）が切り替わる。バナーの表示は変わらない |
| R3 | キーボード：Tabキーでタブに移り、Enter（またはSpace）で選ぶ | 選択が切り替わり、**フォーカスが、そのタブに残る**（以前は失われた）。続けてTabキーで、次の要素へ移れる |
| R4 | 「新しい学期を登録する」→「2099年度 前期」、2099-04-06〜2099-07-20で登録 | モーダルが閉じ、その学期が選択される。バナーが出る（今日が期間外のため）。成功のあいだ、ボタンのラベルが「登録中…」のまま閉じる（「登録する」に戻る様子が見えない） |
| R5 | 同じ名前で、もう一度登録する | 年度・種別の下に、「同じ名前の学期がすでに登録されています」。ボタンが「登録する」に戻る |
| R6 | 終了日を開始日と同じにして登録する | 終了日の下に、「終了日は開始日より後にしてください」 |
| R7 | コンソールに、`document.addEventListener("semester-selected", e => console.log(e.detail))` を貼り付けて実行し、タブをクリックする | `{ semester: { id, name, start_date, end_date } }` が出力される。**同じタブを、もう一度クリックしても、出力されない** |
| R8 | R4と同じ状態で、別の学期を、新しく登録する | 登録した学期のイベントが、出力される |
| R9 | サーバーを止めて、登録を試す | モーダルに、「サーバーに接続できませんでした。時間をおいて、もう一度お試しください」。ボタンが戻る（再起動すると、再度登録できる） |
| R10 | ページを再読み込みする | 今日を含む学期が、選択される |

S1（空状態）は、実際の学期が登録済みの場合は、省略してよい（レビューで、別の方法で確認する）。R4で作った学期の後片付け：`sqlite3 instance/app.db "DELETE FROM semesters WHERE name = '2099年度 前期';"`（実際の学期は、消さない）。

### L. 段階2：授業の一覧
準備：対象の学期のidを確認し（`curl -s $BASE/api/semesters`）、テスト用の授業を3件登録する（`<N>` は、学期のid）。
```
curl -s -X POST $BASE/api/subjects -H 'Content-Type: application/json' -d '{"semester_id": <N>, "subject_name": "テスト：月曜1限", "weekday": 0, "start_time": "09:00", "end_time": "10:00"}'
curl -s -X POST $BASE/api/subjects -H 'Content-Type: application/json' -d '{"semester_id": <N>, "subject_name": "テスト：月曜2限", "weekday": 0, "start_time": "10:00", "end_time": "11:00", "room": "A101", "notes": "持ち物：PC"}'
curl -s -X POST $BASE/api/subjects -H 'Content-Type: application/json' -d '{"semester_id": <N>, "subject_name": "テスト：水曜", "weekday": 2, "start_time": "09:00", "end_time": "10:00", "room": "3号館", "notes": "1行目\n2行目"}'
curl -s -X POST $BASE/api/subjects -H 'Content-Type: application/json' -d '{"semester_id": <N>, "subject_name": "テスト：<b>太字</b>", "weekday": 4, "start_time": "13:00", "end_time": "14:00"}'
```
| 番号 | 操作 | 期待する結果 |
|---|---|---|
| L1 | 再読み込みして、その学期を選ぶ | 表に4行。順序は、月曜1限、月曜2限、水曜、金曜。列は、曜日（月・月・水・金）・時間（`09:00 〜 10:00` など）・科目名・教室 |
| L2 | 表の中身を見る | 月曜1限の教室は「—」。月曜2限は、科目名の下に、小さく「持ち物：PC」。水曜は、メモが**2行**で表示される。4件目は、`<b>太字</b>` が、**そのまま文字として**表示される（太字にならない） |
| L3 | 授業のない別の学期を選ぶ | 「この学期には、まだ授業が登録されていません」 |
| L4 | ネットワークのスロットリング（Slow 3G）を設定し、学期のタブを、素早く、複数回切り替える | 最後に選んだタブの授業が表示される（古い応答で、上書きされない）。取得中は、「読み込み中…」が見える |
| L5 | ネットワークの記録で確認する | タブを切り替えるたびに、`GET /api/subjects?semester_id=<id>` が1回ずつ出る |
| L6 | サーバーを止めて、別のタブを選ぶ | エラーメッセージと「再読み込み」。サーバーを再起動して押すと、一覧が出る |
| L7 | 全体 | コンソールにエラーがない。R1〜R3が、これまでどおり |

### F. 段階3：授業の登録
| 番号 | 操作 | 期待する結果 |
|---|---|---|
| F1 | 見出し「授業」の右の「授業を追加」を押す | モーダルが開く。上部に、「登録先の学期：（選択中のタブの学期名）」。科目名の欄に、フォーカスがある |
| F2 | 初期値を見る | 曜日＝月曜日、開始＝09:00、終了＝10:00。教室・メモは空 |
| F3 | 科目名を空のまま「登録する」 | ブラウザ標準の入力チェックで止まる。ネットワークに `POST` が出ない |
| F4 | 開始時刻を14:00に変える | 終了時刻が、自動で15:00になる。開始を18:00にすると、終了が19:00になる。終了時刻を、開始より前（例：12:00）に手で変えて登録する → 終了時刻の下に、「終了時刻は開始時刻より後にしてください」 |
| F5 | 科目名「テスト：国語」で登録する | **モーダルが閉じない**。「「テスト：国語」を登録しました」が出る。入力欄が初期値に戻り、科目名にフォーカスがある。背後の表に、行が増える。ボタンは「登録する」 |
| F6 | 続けて、3件登録する（科目名を入れて、Enterキーで送信してもよい） | そのたびに、メッセージが、最新の1件に替わる。表に、曜日・時刻の順で、並ぶ |
| F7 | 科目名に前後の空白（例：`  テスト：空白  `）を入れて登録する | 表と、メッセージでは、前後の空白がない |
| F8 | 教室とメモを空で登録する／メモを複数行で登録する | 教室は「—」、メモの行はなし／メモが、改行どおりに表示される |
| F9 | 科目名に、101文字以上を入れて登録する | 科目名の下に、「科目名は100文字以内にしてください」。入力は保持され、モーダルは開いたまま |
| F10 | 「閉じる」、右上の×、背景のクリック、Escキーで、閉じる。もう一度開く | どれでも閉じる。開き直すと、入力・エラー・メッセージが、初期化されている |
| F11 | 別の学期のタブを選び、授業を追加する | 登録先に、その学期名が出る。登録した授業は、その学期の一覧に出て、元の学期には出ない |
| F12 | 過去の学期のタブで、授業を追加する | 追加できる |
| F13 | サーバーを止めて、登録を試す | フォーム上部に、「サーバーに接続できませんでした。時間をおいて、もう一度お試しください」。入力は保持され、ボタンが戻る |
| F14 | 全体 | コンソールにエラーがない。R1〜R3、L1〜L3が、これまでどおり |

確認のあとの後片付け：`sqlite3 instance/app.db "DELETE FROM subjects WHERE subject_name LIKE 'テスト%';"`。**Eventの自動生成のタスクの前に、すべての授業を削除する。**

## Copilotが変更してはいけないもの
上の「非対象」のすべて。特に、Pythonのファイル、`tests/`、`requirements.txt`、`migrations/`、`docs/`、`.github/`、`api.js`、`base.html`、`index.html` の学期のブロック（段階1・2・3を通じて、学期の部分は変更しない。学期のモーダルとタブの構造は、そのまま。例外は、`#semester-detail` の中の仮の注記を、授業のブロックに置き換える段階2の変更だけ）。

## Git操作
**Git commit / push / ブランチ操作 / マージは行わない**（`git branch --show-current`、`git status`、`git diff` のような読み取りだけのコマンドは除く）。

## 注意
- **停止して報告する条件**（ファイルを変更せず、実装を止め、チャットで「問題点・発生理由・変更した場合の影響・推奨案（必要なら）」を報告する）
  - ブランチの不一致、作業ツリーの想定外の変更
  - 設計資料とこのTask MDの間に、矛盾・不足がある
  - 設計資料にない判断が必要になった（特に `docs/architecture.md` の「未決定事項」に触れる場合）
  - 「変更しない」と定めたもの（Pythonのファイル、`tests/`、`api.js` など）を変更しないと実装できない
  - 作業の前の `python -m pytest` が、212件すべて合格しない
  - 授業APIの仕様が、このMDの前提と違う（APIを直さずに、停止する）
- 学期UIの既存の仕様を変える変更は、しない（承認済みのLow-1〜Low-6の修正による変化は、「許される変化」の範囲だけ）。迷ったら、停止して報告する
- 期待する結果と異なる結果が出た場合は、確認を飛ばさず、原因を直してから、すべての確認をやり直す
- 設計資料に書かれていない仕様は、自分で決めない
- 途中の承認ゲートはない。「Copilot確認手順」を実施したら、結果を報告して止まる
- 最後の報告に、次を含める：変更したファイル、各段階の確認結果、`python -m pytest` の件数、開発用DBの前後のハッシュ、`git status`・`git diff --stat`、気になった点（特に、学期UIの挙動に影響しうる変更）
