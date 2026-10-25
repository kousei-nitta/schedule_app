# タスク013: カレンダー表示（読み取りのみ）

| 項目 | 内容 |
|---|---|
| Task ID | 013 |
| Task名 | カレンダー表示（週・月・一覧、カテゴリの絞り込み、予定の詳細パネル。読み取りのみ） |
| ブランチ | `feature/013-calendar-view`（Komaが作成・切替済みの状態で渡される） |

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに停止して報告する。

**このタスクには、承認ゲートはない（DBの構造を変えないため、migrationを作らない）。** 段階1・2を順に進め、「Copilot確認手順」を実施したら、結果を報告して応答を終える。途中で止まるのは、「注意」の停止の条件に当たったときだけ。**止まるときは、報告を書いて応答を終える。質問の機能（選択肢を出して回答を待つ機能）は使わない**（`.github/copilot-instructions.md` の「止まる場面の応答」）。

## 目的
カレンダーモードに、予定（Event）の週・月・一覧の表示を作る。カレンダーの描画には、FullCalendar 6.1.21（2026-10-13に、Komaが追加を承認）を、CDNから読み込む。あわせて、カテゴリの絞り込み、カテゴリの色とアイコン、予定の詳細パネル（確認だけ）を作る。予定は、予定API（`GET /api/events`。Task 012）から取得する。設計資料（`docs/architecture.md` の「FullCalendarの読み込み（確定）」「FullCalendarの使い方（`calendar.js`）」、`docs/ui_ux.md` の「カレンダーモード」「色・アイコン」）の仕様を、そのまま実装する。**Python・API・DBは変えない。**

次の2段階で、この順に行う。

| 段階 | 内容 | 挙動の変化 | 段階の終わりの `pytest` |
|---|---|---|---|
| 1 | 読み込みと土台：`base.html`（FullCalendarと `style.css` の読み込み）、`style.css`、`categories.js` | 見た目は変わらない（FullCalendarは読み込まれるが、まだ使わない。`categories.js` は、まだどこからも使わない） | **478件**（Pythonを変えないため、件数は変わらない） |
| 2 | カレンダー：`index.html`（カレンダーの欄と、予定の詳細パネル）、`calendar.js`、`main.js` | カレンダーモードに、カレンダーが出る | **478件** |

## 前提（Task 012完了時点の状態）

| 区分 | 内容 |
|---|---|
| すでにある | 学期・授業・休講日のAPIと画面、予定API（`GET /api/events`（`start_date`・`end_date` は必須で、両端を含む）と `GET /api/events/<id>`）、pytest（**478件**。`main` の `502ebf1` で確認） |
| まだない | `app/static/css/`（フォルダごと）、`app/static/js/calendar.js`・`categories.js`。カレンダーモードは「カレンダー（準備中）」の1行だけ |
| DBの構造・API | 変えない（初期migration `0280f6cf8d09` と、休講日の `42bd53808fa1`）。**migrationは不要**。予定API（Task 012）を、そのまま使う |
| ライブラリ | FullCalendar 6.1.21 を、`base.html` の `<script>`（CDN）で読み込む（Komaが2026-10-13に承認）。**npm・pipなどで、何もインストール・ダウンロードしない。`requirements.txt` は変えない。FullCalendarのファイルを、リポジトリに置かない** |
| 開発用DB | `instance/app.db` は、Komaの実際の開発用DB（すべてのテーブルが0件。2026-10-13、Task 012の確認のあとにKomaが確認）。**Copilotは、書き込まない。サーバーを起動しない（`python run.py` を実行しない）**。読むのは、「Copilot確認手順」のハッシュと件数だけ。**`sqlite3` は、必ず `-readonly` を付けて実行する**（011-L1） |
| 設計資料 | このタスクの前に、更新した設計資料が `main` に反映されている。`docs/architecture.md` に「FullCalendarの読み込み（確定）」と「FullCalendarの使い方（`calendar.js`）」の節があり、「JavaScriptの構成」の表に `categories.js` の行がある。未決定事項から、「FullCalendarの読み込み方法」「一覧表示の「今日以降」の範囲」「カテゴリの対応表の置き場所」が外れている。`docs/ui_ux.md` の「色・アイコン」に、色とアイコンの値の表がある |
| JavaScriptの確認 | JavaScriptの自動テストはない。Copilotはブラウザを使えないため、画面の動作は、確認用のサーバーとブラウザで確かめる（「Komaの確認」）。Copilotは、全文との比較、画面のHTMLの確認、検索で確かめる |

## Source of Truth
- `docs/architecture.md`：「技術スタック」、「Bootstrapの読み込み（確定）」、「FullCalendarの読み込み（確定）」、「データ設計」の「共通の約束」（`category`）、「予定API（`/api/events`）」、「JavaScriptの構成（ES modules）」（表、規則、「FullCalendarの使い方（`calendar.js`）」）
- `docs/ui_ux.md`：「カレンダーモード」（表示単位・週表示・月表示・一覧表示・共通・予定の確認・編集・削除）、「色・アイコン」、「未決定」
- `docs/tasks/012_events_list_api.md`：予定APIの応答の形
- `.github/copilot-instructions.md`：進め方、「止まる場面の応答」、コーディング方針（JavaScript）、「テスト」

## 実装対象ファイル

| 区分 | ファイル | 段階 | 内容 |
|---|---|---|---|
| 変更 | `app/templates/base.html` | 1 | `style.css` の `<link>` と、FullCalendarの `<script>` の2行を足す |
| 新規 | `app/static/css/style.css` | 1 | カテゴリの色、FullCalendarの中のリンクの見た目、色の見本、改行の表示 |
| 新規 | `app/static/js/categories.js` | 1 | カテゴリの対応表（`EVENT_CATEGORIES`・`eventCategoryOf`） |
| 変更 | `app/templates/index.html` | 2 | カレンダーモードの中身（「カレンダー（準備中）」を置き換える）と、予定の詳細パネル（モーダル）を足す |
| 新規 | `app/static/js/calendar.js` | 2 | カレンダーモード（`initCalendar`） |
| 変更 | `app/static/js/main.js` | 2 | `initCalendar` の `import` と、最後の呼び出し |

上の6ファイル以外は、変更しない（`__pycache__/` などの、`.gitignore` の対象は除く）。**6ファイルとも、このTask MDに全文を書いている。全文のとおりに作る（コメント・空行・順序・絵文字を含め、書き方を変えない）。** 変える必要があると判断した場合は、変えずに停止して報告する。

## 非対象（このタスクでは作らない・変更しない）
- Pythonのファイル（`app/` の `.py`、`app/routes/`、`app/models/`）、`migrations/`（**新しいmigrationを作らない。`flask db` のコマンドを、一切実行しない**）、`requirements.txt`（**ライブラリを追加しない。npmも使わない**）、`pytest.ini`、`run.py`、`tests/`（テストを足さない・変えない）
- `app/static/js/` の、`main.js` 以外の既存のファイル（`api.js`・`ui.js`・`dates.js`・`semesters.js`・`subjects.js`・`closures.js`）
- `index.html` の、カレンダーモードの中身と、新しい予定の詳細パネル以外の部分（授業モード・課題・タスクモード・下の切り替えのボタン・学期と授業のモーダル）
- `docs/`、`.github/`、`.gitignore`
- 作らないもの：予定の登録・編集・削除（空き枠のクリック、詳細パネルの編集・削除のボタン）、週表示の「締切」の行・月表示の期限型の印・「直近の締切」欄（課題・タスクを実装するタスク）、課題・タスク（Task）のカテゴリの対応表と色、カレンダーへの休講日の表示（`docs/ui_ux.md` の未決定）、`tasks.js`
- 使わないもの：FullCalendar 7、FullCalendarの日本語の文言のファイル（`locales/ja`）、アイコンのライブラリ（Bootstrap Iconsなど）、FullCalendarの有料の機能
- 持ち越しの003-H・010-N2（このタスクでは扱わない）
- 開発用DB（`instance/app.db`）への書き込み、サーバーの起動（`python run.py` も、「Komaの確認」の確認用のサーバーも、起動しない）

## 段階1：読み込みと土台（見た目は変わらない）

### 1-1. `app/templates/base.html`
`<head>` の、BootstrapのCSSの次の行に、`style.css` の `<link>` を足す。`</body>` の前の、Bootstrapの `<script>` の次の行に、FullCalendarの `<script>` を足す（2行の追加だけ）。

要点：
- FullCalendarのURLのバージョン（`6.1.21`）と `integrity` は、`docs/architecture.md` の「FullCalendarの読み込み（確定）」の値と、1文字も違わないこと（違うと、ブラウザが読み込みを拒否し、カレンダーが出ない）
- FullCalendarの `<script>` は、`type="module"` を付けない、通常のスクリプト。`{% block scripts %}`（`main.js`）より前に置く（`main.js` が実行される前に、`window.FullCalendar` ができているようにするため）
- `style.css` は、BootstrapのCSSのあとに読み込む（Bootstrapの指定を、上書きできるようにするため）

<!-- 全文: app/templates/base.html -->
```html
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>スケジュール帳</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB" crossorigin="anonymous">
  <link href="{{ url_for('static', filename='css/style.css') }}" rel="stylesheet">
</head>
<body>
  {% block content %}{% endblock %}
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js" integrity="sha384-FKyoEForCGlyvwx9Hj09JcYn3nv7wiPVlz7YYwJrWVcXK/BmnVDxM+D2scQbITxI" crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.21/index.global.min.js" integrity="sha384-WDvnzcla8X1CQM97EnYyl4OoTCvmMFp5lBiVNO3IjVdvLMOUjwt+iuYb/Mru5A9v" crossorigin="anonymous"></script>
  {% block scripts %}{% endblock %}
</body>
</html>
```

### 1-2. `app/static/css/style.css`（新規。フォルダ `app/static/css/` も、新しく作る）
要点：
- 色の値は、`docs/ui_ux.md` の「色・アイコン」の表のとおり。課題（`assignment`）の色は、このタスクでは書かない（課題・タスクの画面を作るタスクで足す）
- FullCalendarは、予定の色を、CSSの変数（`--fc-event-bg-color` など）で受け取る。カテゴリのclass（`categories.js` の `className` と同じ名前）に、変数を設定する
- `.fc a`：Bootstrapの、リンクの見た目（青い下線）を、FullCalendarの中では戻す（`docs/architecture.md` の「FullCalendarの読み込み（確定）」）

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
```

### 1-3. `app/static/js/categories.js`（新規）
要点：
- 公開するのは、`EVENT_CATEGORIES` と `eventCategoryOf` の2つ（名前つきの `export`）。`import` はない。DOMとAPIは扱わない
- アイコンは、絵文字の文字（📖・💼・⭐）。ファイルは、UTF-8で保存する（絵文字を、ほかの文字や `\u` の書き方に変えない）
- 色の値（`#` から始まる値）は書かない（色は `style.css`）

<!-- 全文: app/static/js/categories.js -->
```javascript
// カテゴリの対応表。DBの保存値（APIの category）から、画面に出す
// 表示名・アイコン・色のclassを引く。複数のモードで使うため、
// このファイルにまとめる（モードのファイル同士は、互いを import しない）。
// 色の値は、style.css の、className と同じ名前のclassに書く
// （JavaScriptでは、色の値を持たない）。

// 予定（Event）のカテゴリ。並びは、カレンダーの絞り込みの選択肢の並び。
// 課題・タスク（Task）のカテゴリは、課題・タスクの画面を作るタスクで足す。
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

// 予定のカテゴリの保存値に対応する項目を返す。対応表にない値は、
// DBに入らない想定だが、画面が止まらないように、保存値をそのまま
// 表示名にし、アイコンと色のclassを付けない。
export function eventCategoryOf(category) {
  if (Object.prototype.hasOwnProperty.call(EVENT_CATEGORIES, category)) {
    return EVENT_CATEGORIES[category];
  }
  return { label: category, icon: "", className: "" };
}
```

## 段階2：カレンダー

### 2-1. `app/templates/index.html`
変更は、次の2か所だけ。ほかの行は変えない（全文との比較で確かめる）。
- カレンダーモード（`calendar-pane`）の中の `<p>カレンダー（準備中）</p>` を、取得の失敗の表示（`calendar-load-error`）と、カレンダーの欄（`calendar-content`：絞り込み・「読み込み中…」・カレンダーの描画先 `calendar-view`）に置き換える
- ファイルの最後のモーダル（`subject-modal`）のあと、`{% endblock %}` の前に、予定の詳細パネル（`event-modal`）を足す。値がない項目（教室・派遣会社・詳細・メモ）は、行（`event-modal-room-row` など）ごと隠せるようにする

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

### 2-2. `app/static/js/calendar.js`（新規）
要点（`docs/architecture.md` の「FullCalendarの使い方（`calendar.js`）」と、`docs/ui_ux.md` の「カレンダーモード」）：
- `initCalendar()`：`window.FullCalendar` がなければ、例外にせず、カレンダーの欄を隠して、`LIBRARY_ERROR_MESSAGE` を出す（「再読み込み」のボタンは隠す）。あれば、絞り込みの選択肢を作り、FullCalendarを作って表示する。「再読み込み」のボタンと、カレンダーのモードを開いたとき（`calendar-tab` の `shown.bs.tab`）に、予定を取得し直す
- FullCalendarの設定：日曜始まり、初期表示は週（`timeGridWeek`）、ボタンは「前へ・次へ・今日」と「週・月・一覧」。文言は日本語（`locale: "ja"` と、文言の設定。日本語の文言のファイルは読み込まない）。予定は色のブロック（`eventDisplay: "block"`。表示ごとには指定できないため、全体に指定する）。週表示は終日の行を出さず、0〜24時の全体を、8時から見せる
- 月表示（`views.dayGridMonth`）：時刻を出さない。1日3件まで、4件目以降は「＋N件」。日付と「＋N件」のクリックで、その日を含む週の週表示へ移る
- 一覧表示（`views.listFourWeeks`）：28日間（`LIST_DAYS`）。日数（`days`）で指定する（週で指定すると、日曜日にそろうため）。日付の見出しに曜日を付ける。行の中身は `renderListEventContent`（アイコン・タイトル・主要項目）
- 予定の取得（`fetchEvents`）：FullCalendarが渡す期間を `toApiRange` で予定APIの期間（両端を含む `YYYY-MM-DD`。終わりは、その前の日）にして、`apiRequest` で取得する。`try` で囲むのは、要求だけ。失敗したら、最新の取得のときだけ、エラーを表示し、例外を投げる（FullCalendarに失敗を伝える）。成功したら、最新の取得のときだけ、エラーの表示を消し、絞り込みで外したカテゴリの予定を除いて返す。FullCalendarの既定の、コンソールへの警告は出さない（`eventSourceFailure`）
- 予定の形（`toCalendarEvent`）：日時は `YYYY-MM-DDTHH:MM`（タイムゾーンなし）。カテゴリのclassを付ける（色は付けない）。APIの予定のコピーを `extendedProps.apiEvent` に持たせる
- 詳細パネル（`showEventDetail`）：`textContent` で値を入れ、値のない行を隠して、モーダルを開く。閉じる処理は書かない（閉じるのは、利用者のボタンだけ）
- 絞り込み（`renderFilter`）：`EVENT_CATEGORIES` から、チェックボックス（色の見本つき）を作る。変えたら、外したカテゴリを `hiddenCategories` に控え、予定を取得し直す（`refetchEvents`）

<!-- 全文: app/static/js/calendar.js -->
```javascript
import { apiRequest } from "./api.js";
import { EVENT_CATEGORIES, eventCategoryOf } from "./categories.js";
import { formatJapaneseDateWithWeekday, localDateString } from "./dates.js";
import { errorMessageOf, getElement, setVisible } from "./ui.js";

// 一覧表示の期間の日数（今日から4週間）。前後への移動も、この日数ずつ。
const LIST_DAYS = 28;
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

// 詳細パネルの1行（教室・派遣会社・メモ）。値がなければ、行ごと隠す。
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

// 絞り込みの選択肢を、カテゴリの対応表から作る（表示名を1か所で持つため）。
function renderFilter() {
  const fragment = document.createDocumentFragment();

  for (const [code, category] of Object.entries(EVENT_CATEGORIES)) {
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
      // fetchEvents が、今の絞り込みで予定を選び直すように、取得し直す。
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
  // ほかのモードを止めないように、例外にせず、メッセージだけを出す。
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
    initialView: "timeGridWeek",
    headerToolbar: {
      left: "prev,next today",
      center: "title",
      right: "timeGridWeek,dayGridMonth,listFourWeeks",
    },
    // 日本語の文言のファイルは読み込まず、使う文言を、ここで指定する。
    buttonText: { today: "今日", week: "週", month: "月" },
    buttonHints: { prev: "前へ", next: "次へ", today: "今日を表示" },
    viewHint: "$0表示",
    navLinkHint: "$0を含む週を表示",
    moreLinkText: (count) => `＋${count}件`,
    moreLinkHint: (count) => `ほかに${count}件の予定（週の表示へ）`,
    noEventsText: "表示する予定はありません",
    timeHint: "時間",
    eventHint: "予定",
    eventTimeFormat: { hour: "2-digit", minute: "2-digit", hour12: false },
    // 予定は、色のブロックで表示する。月表示の既定の●の印は、期限型の
    // 締切に使うため。この設定は、表示ごと（views）には指定できず、
    // 週表示と一覧表示の見た目は変わらない。
    eventDisplay: "block",
    // 週表示：終日の行は出さない（予定は、すべて時刻を持つ）。時間軸は
    // 0〜24時の全体にし（範囲の外の予定が消えないように）、8時から見せる。
    allDaySlot: false,
    scrollTime: "08:00:00",
    views: {
      dayGridMonth: {
        // 時間型の予定は、時刻を出さず、タイトルだけを表示する。
        displayEventTime: false,
        // 1日3件まで。4件目以降は「＋N件」にまとめる。
        dayMaxEvents: 3,
        // 日付と「＋N件」のクリックで、その日を含む週の週表示へ移る。
        navLinks: true,
        navLinkDayClick: "timeGridWeek",
        moreLinkClick: "timeGridWeek",
      },
      listFourWeeks: {
        type: "list",
        // 日数（days）で指定する。週（weeks）で指定すると、日曜日に
        // そろってしまうため。日数なら、表示中の日付（初めは今日）から始まる。
        duration: { days: LIST_DAYS },
        buttonText: "一覧",
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
    events: fetchEvents,
    // 取得の失敗は、fetchEvents が画面に出す。FullCalendarの既定の、
    // コンソールへの警告は出さない。
    eventSourceFailure: () => {},
    loading: (isLoading) => {
      setVisible(getElement("calendar-loading"), isLoading);
    },
    eventClick: (info) => {
      showEventDetail(info.event.extendedProps.apiEvent);
    },
  });

  getElement("calendar-retry-button").addEventListener("click", () => {
    calendar.refetchEvents();
  });
  getElement("calendar-tab").addEventListener("shown.bs.tab", () => {
    // ほかのモードでの登録（授業・休講日など）を反映するため、カレンダーの
    // モードを開くたびに、予定を取得し直す。隠れている間に画面の幅が
    // 変わった場合に備えて、大きさも計算し直す。
    calendar.updateSize();
    calendar.refetchEvents();
  });
  calendar.render();
}
```

### 2-3. `app/static/js/main.js`
`initCalendar` の `import`（1行目）と、最後の呼び出し（コメント2行と、呼び出しの1行）を足す。既存の3つの呼び出しの順序は変えない。

<!-- 全文: app/static/js/main.js -->
```javascript
import { initCalendar } from "./calendar.js";
import { initClosures } from "./closures.js";
import { initSemesters } from "./semesters.js";
import { initSubjects } from "./subjects.js";

// 今後のモードの初期化も、ここに足す。
// semester-selectedを購読する側を、イベントを発行する側より先に初期化する。
initSubjects();
initClosures();
initSemesters();
// カレンダーは、ほかのモードとイベントでつながらない。予期しない例外で、
// ほかのモードの初期化が止まらないように、最後に初期化する。
initCalendar();
```

### 2-4. DOMの `id` の一覧（段階2で足すもの）
`calendar-load-error`、`calendar-load-error-message`、`calendar-retry-button`、`calendar-content`、`calendar-filter-label`、`calendar-filter`、`calendar-loading`、`calendar-view`、`event-modal`、`event-modal-title`、`event-modal-category-icon`、`event-modal-category`、`event-modal-date`、`event-modal-time`、`event-modal-room-row`、`event-modal-room`、`event-modal-employer-row`、`event-modal-employer`、`event-modal-notes-row`、`event-modal-notes`（20個。ページの中で、それぞれ1回だけ）。ほかに、絞り込みのチェックボックスの `calendar-filter-class`・`calendar-filter-part_time`・`calendar-filter-other` を、`calendar.js` が作る。

### 2-5. 変わる挙動・変わらない挙動

| 場面 | 変更後 |
|---|---|
| ページを開いたとき | カレンダーモード（初期表示）に、今日を含む週の週表示が出る（以前は「カレンダー（準備中）」） |
| 授業モード（学期・休講日・授業の一覧と登録） | 変わらない |
| 課題・タスクモード | 変わらない（「課題・タスク（準備中）」） |
| API・DB | 変わらない（予定APIを読むだけ） |
| FullCalendarだけを読み込めなかったとき | カレンダーの欄に、ページの再読み込みを促すメッセージが出る。授業モードは使える |

## JavaScriptの共通の規則
`.github/copilot-instructions.md` の「コーディング方針（JavaScript）」と、`docs/architecture.md` の「JavaScriptの構成（ES modules）」の規則に従う（名前つきの `export`、`innerHTML` などの禁止、`textContent`、`fetch` は `api.js` の中だけ、日本語のコメント、など）。次の点を、特に守る。
- FullCalendarに、URLで予定を取得させない（`events` に関数を渡し、`apiRequest` を使う）
- HTMLの文字列を作らない（FullCalendarの `eventContent` で、`html` を返さない）。表示する文字は、`textContent`（または、`append` に文字列を渡す）
- 色をJavaScriptで指定しない（FullCalendarの `backgroundColor`・`eventColor` などの色の設定と、`style` の操作を使わない）
- JavaScriptの1行は、80文字以内
- 理由のコメントは、全文のとおりに書く

## 変更してよい既存のテスト
なし（既存のテストのファイルは、すべて変えない。新しいテストも足さない。件数は478のまま）。

- `tests/test_setup.py` の `test_client_can_get_homepage` が、`base.html` と `index.html` を表示する。このタスクの変更で、失敗しないこと
- このタスクでの「既存のテスト」は、作業の開始時からあるすべてのテスト（478件）。**既存のテストが、想定外に失敗した場合**は、テストの期待値や、ほかの仕様を直さない。原因を調べ、そこで実装を止めて、チャットで報告する

## 実装手順
1. ブランチ・作業ツリーの確認。設計資料が更新されていることを確認する（「Copilot確認手順」の1の `grep`）。更新されていなければ、何も変更せずに停止して報告する
2. 作業の前の状態を記録する：開発用DBの有無・ハッシュ・件数（「Copilot確認手順」の1。**`sqlite3` は `-readonly` を付ける**）。`python -m pytest -q` が478件、すべて合格すること（合格しなければ、何も変更せずに停止して報告する）
3. **（段階1）** `base.html`（1-1）→ `style.css`（1-2）→ `categories.js`（1-3）を、全文のとおりに作る。`python -m pytest -q` が478件、すべて合格すること
4. **（段階2）** `index.html`（2-1）→ `calendar.js`（2-2）→ `main.js`（2-3）を、全文のとおりに作る。`python -m pytest -q` が478件、すべて合格すること
5. 「Copilot確認手順」の2〜6を実施する
6. 結果を報告して、応答を終える（サーバーを起動していないこと、ブラウザで確認していないことを明記する）

各段階の終わりに、`python -m pytest -q` の結果（件数・警告）を控えておく（最終報告に書く）。

## 完了条件
- `python -m pytest -q` が、作業の前と、段階1・2の終わりに、**478件、すべて合格**する（失敗・エラー・スキップが0件）
- 変更したファイルが、「実装対象ファイル」の6つだけ
- 6ファイルが、このTask MDの全文と1文字も違わない（「Copilot確認手順」の4が、6ファイルとも「一致」）
- `app/static/js/` のファイルに、80文字を超える行がない
- 画面のHTMLの確認（「Copilot確認手順」の5）で、2-4の20個の `id` が、それぞれ1回だけ含まれ、並び・読み込みの順序・`integrity` が期待どおり。新しいファイルが、200で返る
- 実施の前後で、開発用DB（`instance/app.db`）のハッシュと、`semesters`・`subjects`・`closures`・`events`・`tasks` の件数が同じ
- 「Komaの確認」が、期待どおり
- レビューで承認される

## Copilot確認手順
**`sqlite3` は、必ず `-readonly` を付けて実行する**（付けずに開くと、読むだけでも、開発用DBを書き込み可能な状態で開くことになる。011-L1）。

```
# 1. 実施前
git branch --show-current      # feature/013-calendar-view
git status                     # 変更なし
grep -n "### FullCalendarの読み込み（確定）" docs/architecture.md     # 1件
grep -n "### FullCalendarの使い方" docs/architecture.md             # 1件
grep -n "FullCalendarの読み込み方法\|対応表の置き場所" docs/architecture.md   # 出力なし（未決定事項から外れている）
grep -n "categories.js" docs/architecture.md docs/ui_ux.md           # 数件
grep -n "止まる場面の応答" .github/copilot-instructions.md           # 数件
ls -l instance/app.db          # 存在すること（なければ、何も変更せずに停止して報告する）
shasum -a 256 instance/app.db
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"
python -m pytest -q            # 478 passed

# 2. 各段階の終わり
python -m pytest -q            # 段階1・段階2とも 478 passed

# 3. 1行の長さ（出力がなければ合格）
python - <<'EOF'
from pathlib import Path
for path in sorted(Path("app/static/js").glob("*.js")):
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, 1):
        if len(line) > 80:
            print(f"{path}:{number}: {len(line)}")
EOF

# 4. 6ファイルが、このTask MDの全文と同じこと（011-N1）
python - <<'EOF'
import difflib
import re
from pathlib import Path

# このTask MDの「<!-- 全文: パス -->」の直後のコードブロックを、
# そのファイルの期待する全文として取り出し、今のファイルと比べる。
fence = "`" * 3
task_text = Path("docs/tasks/013_calendar_view.md").read_text(
    encoding="utf-8"
)
pattern = re.compile(
    "<!-- 全文: (\\S+) -->\n" + fence + "[a-z]+\n(.*?)" + fence + "\n",
    re.S,
)
expected_files = dict(pattern.findall(task_text))
print(f"全文の数：{len(expected_files)}")
for file_name, expected in expected_files.items():
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

# 5. 画面のHTMLの確認（DBを使わない。開発用DBは開かない）
python - <<'EOF'
import re
import tempfile
from pathlib import Path

from app import create_app

EXPECTED_IDS = [
    "calendar-load-error", "calendar-load-error-message",
    "calendar-retry-button", "calendar-content", "calendar-filter-label",
    "calendar-filter", "calendar-loading", "calendar-view", "event-modal",
    "event-modal-title", "event-modal-category-icon", "event-modal-category",
    "event-modal-date", "event-modal-time", "event-modal-room-row",
    "event-modal-room", "event-modal-employer-row", "event-modal-employer",
    "event-modal-notes-row", "event-modal-notes",
]
ORDER = [
    "calendar-pane", "calendar-load-error", "calendar-content",
    "calendar-filter", "calendar-view", "subjects-pane", "subject-modal",
    "event-modal",
]
SCRIPTS = [
    "bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js",
    "fullcalendar@6.1.21/index.global.min.js",
    "js/main.js",
]
FULLCALENDAR_INTEGRITY = (
    "sha384-WDvnzcla8X1CQM97EnYyl4OoTCvmMFp5lBiVNO3IjVdvLMOUjwt+iuYb/Mru5A9v"
)

with tempfile.TemporaryDirectory() as work_directory:
    database_path = Path(work_directory) / "check.db"
    app = create_app(
        {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"}
    )
    client = app.test_client()
    html = client.get("/").get_data(as_text=True)
    ids = re.findall(r'\bid="([^"]+)"', html)
    for expected in EXPECTED_IDS:
        print(expected, ids.count(expected))
    print("重複したid:", sorted({i for i in ids if ids.count(i) > 1}))
    positions = [html.index(f'id="{i}"') for i in ORDER]
    print("並び:", positions == sorted(positions))
    script_positions = [html.index(s) for s in SCRIPTS]
    print("スクリプトの順序:", script_positions == sorted(script_positions))
    css_positions = [
        html.index("bootstrap.min.css"),
        html.index("css/style.css"),
        html.index("</head>"),
    ]
    print("CSSの順序:", css_positions == sorted(css_positions))
    print("integrity:", html.count(FULLCALENDAR_INTEGRITY))
    print("準備中:", "カレンダー（準備中）" in html)
    for name in [
        "js/calendar.js", "js/categories.js", "js/main.js", "css/style.css"
    ]:
        response = client.get(f"/static/{name}")
        print(name, response.status_code, response.mimetype)
        response.close()
EOF

# 6. 検索と差分
grep -rnE "innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(|localStorage|sessionStorage|setTimeout|export default|\bvar |\.style\b" app/static/js/   # 出力なし
grep -rn "fetch(" app/static/js/                                   # api.js の中の1件だけ
grep -rn "{{" app/static/js/                                       # 出力なし
grep -nE "html:|backgroundColor|borderColor|textColor|eventColor" app/static/js/calendar.js   # 出力なし
grep -rnE "#[0-9a-fA-F]{6}" app/static/js/                          # 出力なし（色の値は、style.css だけ）
grep -n "^export" app/static/js/calendar.js app/static/js/categories.js   # 3件：initCalendar、EVENT_CATEGORIES、eventCategoryOf
grep -n "^import" app/static/js/calendar.js                         # 4件：api.js・categories.js・dates.js・ui.js
grep -n "semesters.js\|subjects.js\|closures.js" app/static/js/calendar.js app/static/js/categories.js   # 出力なし
grep -n "initCalendar" app/static/js/main.js                        # 2件：1行目の import と、最後の呼び出し
grep -nE "onclick|style=" app/templates/index.html app/templates/base.html   # 出力なし
git diff --numstat app/templates/base.html                          # 2	0	app/templates/base.html
git diff --stat -- app/*.py app/routes/ app/models/ migrations/ tests/ requirements.txt pytest.ini run.py app/static/js/api.js app/static/js/ui.js app/static/js/dates.js app/static/js/semesters.js app/static/js/subjects.js app/static/js/closures.js   # 出力なし

# 7. 実施後
shasum -a 256 instance/app.db  # 実施前と同じ
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures; SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM tasks;"   # 実施前と同じ
git status                     # 変更：「実装対象ファイル」の3つ。新規：3つ（app/static/css/ を含む）
git diff --stat
```

| 確認 | 期待する結果 |
|---|---|
| `python -m pytest -q` | 実施前、段階1・段階2の終わりとも、478件がすべて合格。失敗・エラー・スキップが0件。`migrations/env.py` の `DeprecationWarning` は、出ても構わない（報告する） |
| 1行の長さ（3） | 出力なし |
| 全文との比較（4） | `全文の数：6` と、6ファイルとも「一致」。「不一致」が出たら、表示された差分を、Task MDの全文に合わせて直し、2からやり直す（Task MDの全文のほうを変える必要があると判断した場合は、停止して報告する） |
| 画面のHTMLの確認（5） | 20個の `id` が、それぞれ `1`。「重複したid: []」。「並び: True」「スクリプトの順序: True」「CSSの順序: True」「integrity: 1」「準備中: False」。4つのファイルが、`200 text/javascript`（`.js`）と `200 text/css`（`.css`） |
| 検索と差分（6） | 上のコメントのとおり（件数が違う場合は、その行を報告に書く） |
| 開発用DB | 実施の前後で、ハッシュと、5つのテーブルの件数が同じ |
| `git status` | 変更：`app/templates/base.html`、`app/templates/index.html`、`app/static/js/main.js`。新規：`app/static/css/`（`style.css`）、`app/static/js/calendar.js`、`app/static/js/categories.js`。Pythonのファイル・`migrations/`・`tests/`・`docs/`・`.github/`・`requirements.txt`・`run.py`・`instance/`・ほかのJavaScriptのファイルに変更なし |

`.pytest_cache/` や `__pycache__/` が `git status` に表示される場合は、`.gitignore` を変更せず、報告する。**Copilotは、サーバーを起動せず、ブラウザでの確認もしない**（Claude と Koma が行う）。報告に、そのことを明記する。

## Komaの確認
順序：（1）pytest →（2）commit・push とレビューの依頼 →（3）ブラウザでの確認（確認用のサーバー）→（4）開発用DBでの、読み取りだけの確認 →（5）マージ。

### 1. pytest
`python -m pytest -q` を自分で実行し、**478件、すべて合格**することを確かめる。

### 2. push とレビューの依頼
featureブランチを commit・push する（PRを作ってもよい）。Copilotの完了報告を共有して、Claudeにレビューを頼む。**pushは、マージではない。レビューの承認の前に、マージしない。** 修正が必要になった場合は、同じブランチでCopilotが直し、もう一度pushしてレビューを受ける。

### 3. ブラウザでの確認（確認用のサーバー）
レビューで「承認可能」になったあとに行う。**ブラウザの操作は、Claudeが、ブラウザのパネルまたはChromeで行う。Komaは、サーバーの起動・停止、確認用のデータの登録、DBのハッシュの確認、後片付けを行う**（roadmap の「進め方の決定の記録」、2026-10-12）。

#### 確認の安全のしくみ
- **開発用DBは使わない。** 確認用のDB（`/tmp/schedule-app-check-013/check.db`）を、migrationで作り、そのDBで起動した確認用のサーバーで確かめる（Task 010〜012と同じ方法）。開発用DBには、何も残らない
- 確認用のデータ（下の「確認用のデータの登録」）は、確認用のDBの場所を指定して登録する。学期・休講日・授業は、アプリのAPIで登録する（授業の予定は、APIが作る）。アルバイト・その他の予定は、まだAPIで作れないため、確認用のDBに直接入れる。**このスクリプトは、確認用のDBだけに書き込む**（開発用DBと、動いているサーバーの種類に関係なく、DBの場所をファイルの名前で指定するため）
- ブラウザは、BootstrapとFullCalendarを、インターネット（jsDelivr）から読み込む。インターネットにつながった状態で行う
- 確認の前後で、開発用DBのハッシュが同じことを確かめる

#### 確認の日付
期待する結果は、確認の日が **2026-10-13〜2026-12-26** の間にあることを前提にしている（確認用の学期「2026年度 後期」（2026-09-21〜2027-01-31）が、今日を含み、今日を含む週に、授業の予定があるため）。この範囲の外の日に行う場合は、行う前にClaudeに伝える。

#### 準備
1. `python run.py` が起動していれば、Ctrl＋Cで止める（確認用のサーバーも、5001番を使うため）。開発用DBのハッシュを控える
   ```
   shasum -a 256 instance/app.db
   ```
2. 下の「確認用のサーバーの起動」のコマンドで、確認用のサーバーを起動する（このターミナルは、確認の間、開いたままにする）
3. 別のターミナルを開き、リポジトリのルートで、`.venv` を有効にして、下の「確認用のデータの登録」を実行する（1回だけ）
4. Claudeが、ブラウザで `http://127.0.0.1:5001/` を開き、強制再読み込みをする

#### 確認用のサーバーの起動
ブランチ `feature/013-calendar-view` のまま、リポジトリのルートで、`.venv` を有効にして、次を実行する（行の先頭に空白を入れずにコピーする）。

```
python - <<'EOF'
from pathlib import Path

from flask_migrate import upgrade

from app import create_app

# 確認用のDB（開発用DBとは別のファイル）。止めて起動し直しても、残る。
check_directory = Path("/tmp/schedule-app-check-013")
check_directory.mkdir(exist_ok=True)
database_path = check_directory / "check.db"
app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"})
with app.app_context():
    upgrade(directory="migrations")
print(f"確認用のDB：{database_path}", flush=True)
app.run(host="127.0.0.1", port=5001, debug=False)
EOF
```

期待する出力：初めての起動では、`Running upgrade  -> 0280f6cf8d09, initial tables` と `Running upgrade 0280f6cf8d09 -> 42bd53808fa1, add closures table`、「確認用のDB：/tmp/schedule-app-check-013/check.db」、`Running on http://127.0.0.1:5001`。起動し直したときは、`Running upgrade` の行が出ない。

#### 確認用のデータの登録
確認用のサーバーを起動したあとに、別のターミナルで、1回だけ実行する（行の先頭に空白を入れずにコピーする）。

```
python - <<'EOF'
from datetime import date, time
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models.event import Event

# 確認用のDBだけに書き込む（開発用DBは使わない）。DBは、確認用のサーバーが、
# 起動のときにmigrationで作っておいたものを使う。
database_path = Path("/tmp/schedule-app-check-013/check.db")
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
semester = post("/api/semesters", {"name": "2026年度 後期", "start_date": "2026-09-21", "end_date": "2027-01-31"})
post("/api/closures", {"semester_id": semester["id"], "date": "2026-11-03", "name": "文化の日"})
subjects = [
    {"subject_name": "テスト：月曜1限", "weekday": 0, "start_time": "09:00", "end_time": "10:00", "room": "3号館201", "notes": "持ち物：教科書\n小テストあり"},
    {"subject_name": "テスト：火曜2限", "weekday": 1, "start_time": "10:00", "end_time": "11:00"},
    {"subject_name": "テスト：水曜3限", "weekday": 2, "start_time": "13:00", "end_time": "14:00", "room": "5号館101"},
]
counts = [post("/api/subjects", {"semester_id": semester["id"], **subject})["generated_event_count"] for subject in subjects]
print("授業の予定の件数：", counts)

# アルバイト・その他の予定は、まだAPIで作れないため、確認用のDBに直接入れる。
rows = [
    ("part_time", date(2026, 11, 18), time(17, 0), time(21, 0), "テスト：品出し", "テスト派遣", "集合：店舗の裏口\n18時に休憩"),
    ("part_time", date(2026, 11, 18), time(22, 0), time(23, 30), "テスト：夜の棚卸し", None, None),
    ("other", date(2026, 11, 19), time(18, 0), time(19, 0), "テスト：買い物", None, None),
    ("other", date(2026, 11, 20), time(12, 0), time(13, 0), "<b>太字</b>", None, None),
    ("other", date(2026, 11, 21), time(9, 0), time(10, 0), "テスト：予定A", None, None),
    ("other", date(2026, 11, 21), time(11, 0), time(12, 0), "テスト：予定B", None, None),
    ("part_time", date(2026, 11, 21), time(13, 0), time(14, 0), "テスト：予定C", "テスト派遣", None),
    ("other", date(2026, 11, 21), time(15, 0), time(16, 0), "テスト：予定D", None, None),
]
with app.app_context():
    for category, day, start, end, title, employer, notes in rows:
        db.session.add(Event(category=category, date=day, start_time=start, end_time=end, title=title, employer=employer, notes=notes, is_generated=False))
    db.session.commit()
    total = db.session.scalar(db.select(db.func.count()).select_from(Event))
    print("予定の合計：", total)
EOF
```

期待する出力：`授業の予定の件数： [19, 18, 19]`（火曜日は、休講日の11/3を除く）と、`予定の合計： 64`（授業56件＋直接入れた8件）。2回目に実行すると、「中止：/api/semesters 400 …同じ名前の学期がすでに登録されています…」で止まり、何も増えない（そのままでよい）。

#### W. 週表示（ページを開いた状態から）

| No | 操作 | 期待する結果 |
|---|---|---|
| W1 | ページを開いたまま、画面を見る | カレンダーモードが選ばれている。上から、「表示するカテゴリ」と、チェックの入った「■授業」（青）・「■アルバイト」（緑）・「■その他」（グレー）、その下に、左から「＜」「＞」「今日」のボタン、表示中の期間（例：「2026年10月11日 – 17日」）、右に「週」（選択中）「月」「一覧」のボタン。今日を含む週（日曜〜土曜）の週表示。見出しは「10/11(日)」の形で、黒い文字（青い下線つきでない）。終日の行はない。月曜・火曜・水曜に、青いブロックの授業の予定（「09:00 - 10:00」「テスト：月曜1限」、「10:00 - 11:00」「テスト：火曜2限」、「13:00 - 14:00」「テスト：水曜3限」）。ブロックには、時間とタイトルだけ（教室は出ない）。時間軸は、8時が上端の位置で表示されている。今日の列は、薄い黄色（今日を含む週が11/1〜11/7の週の場合は、火曜日が休講日（11/3）のため、火曜日の予定はない） |
| W2 | コンソールで、`[...document.querySelectorAll(".fc-toolbar button")].map(b => b.title)` と、`[...document.querySelectorAll(".fc-timegrid-slot-label[data-time]")].map(e => e.dataset.time).filter((t, i, a) => [0, a.length - 1].includes(i))` を実行する | 1つ目：`["前へ", "次へ", "今日を表示", "週表示", "月表示", "一覧表示"]`（ボタンにマウスを重ねたときの説明）。2つ目：`["00:00:00", "23:30:00"]`（時間軸は0〜24時の全体） |
| W3 | 「＞」を2回押す。そのあと「今日」を押す | 2週先の週に移る（「今日」のボタンが押せる状態になる）。「今日」で、今日を含む週に戻る（「今日」のボタンは、押せない薄い表示になる） |

#### M. 月表示

| No | 操作 | 期待する結果 |
|---|---|---|
| M1 | 「月」を押す | 今日を含む月の月表示（例：「2026年10月」）。曜日の見出しは「日」〜「土」（黒い文字）。授業の予定は、時刻のない、青いブロックとタイトル（例：「テスト：月曜1限」）。●の印は付かない |
| M2 | 表示が「2026年11月」になるまで「＞」を押す（12月に確認する場合は「＜」） | 2日：「テスト：月曜1限」。3日：予定なし（休講日）。4日：「テスト：水曜3限」。18日：「テスト：水曜3限」（青）、「テスト：品出し」「テスト：夜の棚卸し」（緑）の3件（「＋N件」はない）。19日：「テスト：買い物」（グレー）。20日：`<b>太字</b>`（グレー。太字にならず、そのままの文字）。21日：「テスト：予定A」「テスト：予定B」（グレー）、「テスト：予定C」（緑）、その下に「＋1件」 |
| M3 | 21日の「＋1件」にマウスを重ねてから、押す | 説明（`title`）「ほかに1件の予定（週の表示へ）」が出る。押すと、週表示（「週」が選択中）の「2026年11月15日 – 21日」に移る。21日（土）に、「テスト：予定A」（09:00）・「テスト：予定B」（11:00）・「テスト：予定C」（13:00。緑）・「テスト：予定D」（15:00）の4件 |
| M4 | 「月」を押す。「18日」の日付にマウスを重ねてから、押す | 月表示は「2026年11月」のまま（見ている日付を保つ）。説明（`title`）「2026年11月18日を含む週を表示」が出る。押すと、週表示の「2026年11月15日 – 21日」に移る |
| M5 | そのまま、18日（水）の列を見る（時間軸を下までスクロールする） | 「13:00 - 14:00」「テスト：水曜3限」（青）、「17:00 - 21:00」「テスト：品出し」（緑）、22時の位置に「22:00 - 23:30」「テスト：夜の棚卸し」（緑） |

#### D. 予定の詳細パネル（M5の週表示から）

| No | 操作 | 期待する結果 |
|---|---|---|
| D1 | 18日の「テスト：品出し」を押す | 詳細パネルが開く。見出し「テスト：品出し」。カテゴリ「💼 アルバイト」、日付「2026年11月18日（水）」、時間「17:00 〜 21:00」、派遣会社「テスト派遣」、詳細・メモは2行（「集合：店舗の裏口」と「18時に休憩」）。教室の行はない。下のボタンは「閉じる」だけ（編集・削除のボタンはない）。「閉じる」で閉じる |
| D2 | 16日（月）の「テスト：月曜1限」を押す | カテゴリ「📖 授業」、日付「2026年11月16日（月）」、時間「09:00 〜 10:00」、教室「3号館201」、詳細・メモは2行（「持ち物：教科書」と「小テストあり」）。派遣会社の行はない。右上の「×」で閉じる |
| D3 | 20日（金）の `<b>太字</b>` を押す | 見出しに、`<b>太字</b>` が、そのまま文字として出る（太字にならない）。カテゴリ「⭐ その他」、日付「2026年11月20日（金）」、時間「12:00 〜 13:00」。教室・派遣会社・詳細・メモの行はない。Escキーで閉じる |
| D4 | コンソールで、`document.querySelector('td.fc-timegrid-col[data-date="2026-11-19"] .fc-timegrid-event').focus()` を実行してから、Enterキーを押す | 「テスト：買い物」の詳細パネルが開く（キーボードでも開ける）。Escキーで閉じる |

#### L. 一覧表示（D4のあと、週表示「2026年11月15日 – 21日」から）

| No | 操作 | 期待する結果 |
|---|---|---|
| L1 | 「一覧」を押す | 期間「2026年11月15日 – 12月12日」（週の表示で日付をクリックして移ったあとのため、その週の最初の日から28日間）。日付の見出し（例：「2026年11月16日(月)」）ごとに、行が並ぶ。予定のない日（15日・22日など）は出ない。16日：「09:00 - 10:00」、青い●、「📖 テスト：月曜1限」と、薄い字で「3号館201」。17日：「📖 テスト：火曜2限」（教室なし）。18日：「📖 テスト：水曜3限」「5号館101」、緑の●「💼 テスト：品出し」「テスト派遣」、緑の●「💼 テスト：夜の棚卸し」（派遣会社なし）。19日：グレーの●「⭐ テスト：買い物」。20日：「⭐ <b>太字</b>」（そのままの文字）。21日：「⭐ テスト：予定A」「⭐ テスト：予定B」「💼 テスト：予定C」「テスト派遣」「⭐ テスト：予定D」 |
| L2 | 「＞」を押す | 期間「2026年12月13日 – 2027年1月9日」（28日ずつ進む） |
| L3 | 「今日」を押す | 期間が、今日から27日後まで（例：今日が10/13なら「2026年10月13日 – 11月9日」）。最初の見出しは、今日以降で、最初に予定のある日 |
| L4 | 「表示するカテゴリ」の右の、色の見本を見る | 青・緑・グレーが、W1〜L3の予定の色と同じ |

#### F. カテゴリの絞り込み

| No | 操作 | 期待する結果 |
|---|---|---|
| F1 | 「月」を押す。「＞」または「＜」で、表示を「2026年12月」にしてから、「＜」で「2026年11月」に戻す（月の最初の日を、見ている日付にするため）。「授業」のチェックを外す | 青い予定が消える。2日・4日は空。18日：「テスト：品出し」「テスト：夜の棚卸し」。21日：「テスト：予定A」「テスト：予定B」「テスト：予定C」と「＋1件」（変わらない） |
| F2 | 「アルバイト」のチェックも外す | 18日は空。21日：「テスト：予定A」「テスト：予定B」「テスト：予定D」（「＋1件」はない） |
| F3 | 「一覧」を押す | 期間「2026年11月1日 – 28日」（月の表示で前後に移動したあとのため、その月の最初の日から）。その他の予定だけ：19日「⭐ テスト：買い物」、20日「⭐ <b>太字</b>」、21日「⭐ テスト：予定A」「⭐ テスト：予定B」「⭐ テスト：予定D」 |
| F4 | 「その他」のチェックも外す | 「表示する予定はありません」 |
| F5 | 3つのチェックを、すべて入れ直す | 2日「📖 テスト：月曜1限」から、すべての予定が出る（4日「📖 テスト：水曜3限」もある） |

#### R. 取得し直しと、取得の失敗（F5の一覧表示「2026年11月1日 – 28日」から）

| No | 操作 | 期待する結果 |
|---|---|---|
| R1 | 画面下の「授業」を押す。「2026年度 後期」が選ばれていることを確かめ、休講日の欄で、日付 2026-11-04、名前「確認」を追加する。画面下の「カレンダー」を押す | 一覧表示（「2026年11月1日 – 28日」）のまま、4日の行（「テスト：水曜3限」）が消えている（カレンダーのモードを開いたときに、予定を取得し直したため） |
| R2 | 「授業」を押し、休講日の「2026年11月4日（水） 確認」の行の「削除」を押す。「カレンダー」を押す | 4日の「📖 テスト：水曜3限」の行が、また出る |
| R3 | Komaが、確認用のサーバーを止める（Ctrl＋C）。Claudeが、「＞」を押す | 期間「2026年11月29日 – 12月26日」。カレンダーの上に、赤い枠で「サーバーに接続できませんでした。時間をおいて、もう一度お試しください」と「再読み込み」ボタン。一覧は「表示する予定はありません」 |
| R4 | Komaが、「確認用のサーバーの起動」のコマンドで、確認用のサーバーを起動し直す（ターミナルで↑キーを押すと、前のコマンドを呼び出せる。`Running upgrade` の行は出ない）。Claudeが、「再読み込み」を押す | 赤い枠が消え、30日（月）「📖 テスト：月曜1限」からの行が出る |
| R5 | コンソールで、`window.FullCalendar = undefined; const m = await import("/static/js/calendar.js?r5"); m.initCalendar();` を実行する（FullCalendarを読み込めなかった場合の再現。確認のためだけのもので、アプリのファイルには入れない） | カレンダーと絞り込みが消え、赤い枠で「カレンダーの部品を読み込めませんでした。ネットワークの接続を確かめて、ページを再読み込みしてください」。「再読み込み」ボタンは出ない |
| R6 | ページを再読み込みする。画面下の「授業」を押す | 再読み込みで、W1と同じ週表示に戻る（赤い枠はない）。授業モードは、これまでどおり（学期「2026年度 後期」、休講日「2026年11月3日（火） 文化の日」、授業3件） |

#### E. 確認の全体を通して

| No | 確認 | 期待する結果 |
|---|---|---|
| E1 | コンソール | JavaScriptの例外（`Uncaught …`）が出ていない。サーバーを止めている間（R3）の、接続の失敗の記録（`net::ERR_CONNECTION_REFUSED`）は、除く（010-N1） |

#### 後片付け
1. 確認用のサーバーを止める（Ctrl＋C）
2. 確認用のDBのフォルダを消す
   ```
   rm -r /tmp/schedule-app-check-013
   ```
3. 開発用DBのハッシュが、準備の1と同じことを確かめる
   ```
   shasum -a 256 instance/app.db
   ```

ハッシュが変わっていた場合は、開発用DBを操作せずに、Claudeに伝える。

### 4. 開発用DBでの、読み取りだけの確認
3が期待どおりなら、開発用DBで起動して、カレンダーが開くことだけを確かめる（登録・削除はしない）。

```
shasum -a 256 instance/app.db          # 控える
python run.py                          # 開発用DBで起動（別のターミナルで、次を実行）
curl -s -w '\nHTTP %{http_code}\n' "http://127.0.0.1:5001/api/events?start_date=2026-10-01&end_date=2026-12-31"
# 画面の確認のあと、サーバーを Ctrl+C で止めてから
shasum -a 256 instance/app.db          # 起動の前と同じ
```

| 確認 | 期待 |
|---|---|
| ブラウザで開き、強制再読み込みする | 今日を含む週の週表示。予定はない（開発用DBの予定は0件）。赤い枠は出ない。「一覧」を押すと「表示する予定はありません」。コンソールに、JavaScriptの例外がない（学期・授業を登録していた場合は、その予定が表示される） |
| `curl` | `[]`、HTTP 200（授業を登録していた場合は、その予定の一覧） |
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
  - 「変更しない」と定めたもの（Pythonのファイル、テスト、ほかのJavaScriptのファイル、`index.html` のカレンダーと詳細パネル以外の部分など）を変更しないと実装できない。または、6ファイルの全文を変える必要があると判断した
  - ライブラリのインストール・ダウンロードや、FullCalendarの別の版・別のファイル（日本語の文言のファイルなど）が必要だと判断した
  - 開発用DB（`instance/app.db`）がない
  - 作業の前の `python -m pytest` が、478件すべて合格しない
  - **既存のテスト**（作業の開始時からある478件）**が、想定外に失敗した**。テストの期待値や、ほかの仕様を直さずに、原因を調べて報告する
  - APIの変更や、DBの構造の変更（migration）が必要だと判断した
  - 実施の前後で、`instance/app.db` が変わった
- **止まるときは、報告を書いて、その応答を終える。質問の機能は使わない。** 再開するのは、Komaの新しいメッセージが、判断や再開を明確に示したときだけ（無回答や「続けて」だけの返事は、再開の指示ではない）。`.github/copilot-instructions.md` の「止まる場面の応答」
- **開発用DBを `sqlite3` で開くときは、必ず `-readonly` を付ける**（SELECTだけでも、付けずに開かない。011-L1）。`flask db` のコマンドを、一切実行しない。ライブラリを追加しない。サーバーを起動しない（`python run.py` も、「Komaの確認」の確認用のサーバーも）。「確認用のデータの登録」のスクリプトも、実行しない（Komaが行う）
- 期待する結果と異なる結果が出た場合は、確認を飛ばさず、原因を直してから、すべての確認をやり直す（ただし、既存のテストの想定外の失敗は、上の停止の条件に従う）
- 設計資料に書かれていない仕様は、自分で決めない
- 最後の報告に、次を含める：変更したファイル、作業の前と各段階の `pytest` の件数と警告、1行の長さの確認の結果、全文との比較の結果（6ファイルの「一致」）、画面のHTMLの確認の出力、検索と差分の結果、開発用DBの前後のハッシュ・件数、`git status`・`git diff --stat`、サーバーの起動とブラウザでの確認をしていないこと、気になった点
