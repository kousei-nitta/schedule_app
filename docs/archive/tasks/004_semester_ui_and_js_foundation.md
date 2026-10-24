# タスク004: 学期UIとJavaScript基盤

| 項目 | 内容 |
|---|---|
| Task ID | 004 |
| Task名 | 学期UIとJavaScript基盤 |
| ブランチ | `feature/004-semester-ui`（Komaが作成・切替済みの状態で渡される） |

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに停止して報告する。

## 目的
授業モードに、**学期の一覧（タブ）と登録（モーダル）** を実装し、Task 003で作った学期API（`GET`・`POST /api/semesters`）を、初めて画面から使えるようにする。

あわせて、これ以降のすべての画面で使う **JavaScriptの共通基盤**（ES modulesの構成、入口の `main.js`、API通信の共通処理 `api.js`）を作る。

## 前提（Task 003完了時点の状態）

| 区分 | 内容 |
|---|---|
| すでにある | 学期API（`GET /api/semesters`、`POST /api/semesters`）、`/api` 以下のJSONエラー、`base.html`（Bootstrap 5.3.8のCSSと `bootstrap.bundle.min.js`）、`index.html`（3モードの切り替え。授業モードの領域 `subjects-pane` には、仮の文言「授業（準備中）」だけがある）、`run.py`（`127.0.0.1:5001`） |
| まだない | `app/static/`、JavaScriptのファイル、`base.html` の `scripts` ブロック、学期の画面 |
| DBの状態 | `semesters` は0件のはず（このタスクでCopilotはデータを作らない） |

## Source of Truth
次の設計資料を正本とし、食い違いに気づいた場合は、停止して報告する（「注意」を参照）。
- `docs/ui_ux.md`：「授業モード」の「学期（タブと登録）」
- `docs/architecture.md`：「JavaScriptの構成（ES modules）」（「`api.js` の仕様」を含む）、「API共通ルール」、「学期API」
- `docs/requirements.md`：「学期」
- `docs/tasks/003_api_foundation_and_semesters_api.md`：学期APIの仕様とエラー形式
- `.github/copilot-instructions.md`：進め方、コーディング方針（JavaScriptの方針を含む）

## 実装対象ファイル

| 区分 | ファイル | 内容 |
|---|---|---|
| 新規 | `app/static/js/main.js` | 入口。各モードの初期化を呼ぶ |
| 新規 | `app/static/js/api.js` | `fetch` の共通処理と `ApiError` |
| 新規 | `app/static/js/semesters.js` | 授業モードの学期タブ・登録フォーム |
| 変更 | `app/templates/base.html` | `{% block scripts %}` を追加する（それ以外は変更しない） |
| 変更 | `app/templates/index.html` | 授業モードの領域に学期のDOMを作る。モーダルを置く。`main.js` を読み込む |

## 非対象（このタスクでは作らない・変更しない）
- Pythonのファイルのすべて（`app/*.py`、`app/routes/`、`app/models/`）。**APIは変更しない**
- `run.py`、`requirements.txt`、`migrations/`、`instance/`
- `docs/`、`.github/`
- `subjects.js`・`calendar.js`・`tasks.js`、授業の一覧・「授業を追加」ボタン、カレンダー、課題・タスクのUI、FullCalendar
- 学期の編集・削除の操作
- 独自のCSS（`app/static/css/` を作らない）、`style` 属性、色・アイコン。Bootstrapのクラスだけを使う
- テスト（`pytest`・JavaScriptのテスト）、`npm`・ライブラリの追加（Bootstrap以外の外部ファイルを読み込まない）

## 画面仕様

### 授業モードの状態

| 状態 | いつ | 表示するもの |
|---|---|---|
| 読み込み中 | ページを開いた直後〜一覧の取得が終わるまで | 「読み込み中…」だけ |
| 取得失敗 | 一覧の取得（`GET /api/semesters`）が失敗したとき | エラーメッセージと「再読み込み」ボタン。押すと、取得をやり直す |
| 空状態 | 学期が0件 | 説明文「学期がまだ登録されていません。最初の学期を登録してください」と、「最初の学期を登録する」ボタン。タブ・バナー・「新しい学期を登録する」ボタン・本文は出さない |
| 通常 | 学期が1件以上 | 下記のとおり |

「通常」の表示：
- 上部に、学期タブと、「新しい学期を登録する」ボタン
- 今日がどの学期にも含まれないときだけ、バナー（下の「バナー」を参照）
- 本文に、選択中の学期の名前・期間・仮の注記

### タブ
- 学期の一覧は、APIが返した順（開始日の新しい順、同じ開始日ならidの新しい順）のまま、左から並べる。**JavaScriptで並べ替えない**
- ラベルは、学期の `name`。過去の学期も、特別な印を付けず、同じ見た目にする。選択中のタブは、Bootstrapの `active` で示す
- 数が増えたら、横にスクロールできるようにする（`flex-nowrap` と `overflow-x-auto` を使う）
- タブをクリックすると、選択中の学期が切り替わり、本文が変わる。バナーの表示・非表示は変わらない

### 本文（選択中の学期）
- 名前（見出し）
- 期間：「2026年9月21日 〜 2026年12月27日」の形（月・日の先頭のゼロを付けない）。`"YYYY-MM-DD"` の文字列を `-` で分けて作る（`Date` オブジェクトを使わない）
- 注記：「この学期の授業は、まだ登録できません（準備中）」

### 初期選択
一覧の取得後（最初の読み込みと、「再読み込み」のあと）に、次の順で選ぶ。「今日」はブラウザの日付で、`YYYY-MM-DD` の文字列にして、文字列のまま比較する（ISOの日付は、文字列の大小が日付の前後と一致する）。
1. 今日を含む学期（開始日 ≦ 今日 ≦ 終了日。両端を含む）。複数あれば、タブの並びで左にあるもの（一覧の並びで先にあるもの）
2. なければ、今日より後に始まる学期のうち、開始日が最も早いもの。同じ開始日が複数あれば、タブの並びで左にあるもの（一覧の並びで先にあるもの）
3. なければ、終了日が最も新しいもの。同じ終了日が複数あれば、タブの並びで左にあるもの（一覧の並びで先にあるもの）
4. 学期が1件もなければ、空状態

**今日の日付は、ブラウザのローカルの日付を `getFullYear()`・`getMonth()`・`getDate()` から作る。`toISOString()` は使わない**（UTCに変換されて、日本時間の午前中に前日になるため）。

### バナー
- 学期が1件以上あり、今日がどの学期（1.の条件）にも含まれないときだけ表示する
- 文言は「新しい学期を登録しますか」。同じ行に、「登録する」ボタンを置く。押すと、登録のモーダルを開く
- 学期が0件のときは出さない

### 登録のモーダル（Bootstrapのモーダル）

| 項目 | 入力 | 必須 | 初期値（モーダルを開くたびに設定する） |
|---|---|---|---|
| 年度 | 数値（`type="number"`） | `required` | 今日の年度。4〜12月は今年、1〜3月は前年 |
| 種別 | 選択（前期／後期） | `required` | 今日が4〜8月なら「前期」、9〜3月なら「後期」 |
| 開始日 | 日付（`type="date"`） | `required` | 空欄 |
| 終了日 | 日付（`type="date"`） | `required` | 空欄 |

- 学期名は、年度と種別から `"{年度}年度 {種別}"`（「年度」と種別の間は、半角スペース1つ）に組み立てる（例：`2026年度 後期`）。名前の入力欄は作らない
- ボタンは「キャンセル」と「登録する」。モーダルを開くたびに、入力値を初期値に戻し、エラー表示を消す
- 空の項目は、ブラウザ標準の入力チェック（`required`）で止める。それ以外の入力チェックは、JavaScriptでは行わない（検証は、APIが行う）
- 送信中は、「登録する」ボタンを無効にし、ラベルを「登録中…」にする。失敗したら、元に戻す

### 登録に成功したとき
1. モーダルを閉じる
2. `GET /api/semesters` で一覧を取得し直す
3. 登録した学期（`POST` の応答の `id`）を、選択状態にする（初期選択の規則は使わない）
4. タブ・バナー・本文を、更新する

### エラーの表示
「エラー処理」の表のとおり。

### 文言（このとおりにする）

| 場面 | 文言 |
|---|---|
| 読み込み中 | 読み込み中… |
| 空状態の説明 | 学期がまだ登録されていません。最初の学期を登録してください |
| 空状態のボタン | 最初の学期を登録する |
| 通常のボタン、モーダルのタイトル | 新しい学期を登録する |
| バナー、バナーのボタン | 新しい学期を登録しますか、登録する |
| 本文の注記 | この学期の授業は、まだ登録できません（準備中） |
| 取得失敗のボタン | 再読み込み |
| モーダルのラベル | 年度、種別、開始日、終了日（種別の選択肢は、前期、後期） |
| モーダルのボタン | キャンセル、登録する（送信中は、登録中…） |
| モーダルを閉じるボタンの `aria-label` | 閉じる |

## DOM構成（`index.html`）
授業モードの領域（`id="subjects-pane"` の `<section>`）の中の仮の文言を、次の構造に置き換える。**ID・クラス・構造は、このとおりにする**（`semesters.js` が、これらのIDを使う）。動的に作るのは、タブ（`#semester-tabs` の中）だけで、ほかはHTMLに書いておき、JavaScriptは、表示・非表示（`d-none`）と、文字（`textContent`）だけを変える。

```html
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
    <p class="text-muted">この学期の授業は、まだ登録できません（準備中）</p>
  </div>
</div>
```

**モーダルは、`<main>` や `.tab-content` の外（`{% block content %}` の中の最上位）に置く**（`.tab-pane` の `fade` やスタックの影響を避けるため）。

```html
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
```

`index.html` の末尾（`{% endblock %}` のあと）に、次のブロックを書く。これが、ページに書く **唯一のJavaScriptの読み込み** である。

```html
{% block scripts %}
<script type="module" src="{{ url_for('static', filename='js/main.js') }}"></script>
{% endblock %}
```

`base.html` では、Bootstrapの `<script>`（`bootstrap.bundle.min.js`）の **あと**、`</body>` の前に、`{% block scripts %}{% endblock %}` を追加する。

## JavaScript仕様

### 共通の規則
- すべてES modules。`import` の相手は、拡張子つきの相対パス（例：`"./api.js"`）。`export` は名前つき（`export default` は使わない）
- 禁止：`innerHTML`・`outerHTML`・`insertAdjacentHTML`・`document.write`・`eval`、HTMLの `onclick` などの属性、`var`、`style` 属性の操作、`localStorage` など
- ユーザーの入力や、APIが返した文字を表示するときは、`textContent` を使う。要素の中身を空にするときは `replaceChildren()` を使う
- `fetch` は `api.js` の中だけで呼ぶ。画面のコードは、`apiRequest` を使う
- Jinjaの値をJavaScriptの中に書かない。データは、APIから取る
- 書き方：`const`／`let`、セミコロンあり、インデントは空白2つ、文字列は二重引用符、`===`、`async`／`await`
- コメントは日本語で、次の4か所に理由を書く：①`Content-Type` を本文があるときだけ付ける理由（`api.js`）、②今日の日付を `toISOString()` で作らない理由、③日付を文字列のまま比較できる理由、④モーダルを開くたびに初期化する理由（`semesters.js`）

### モジュールの構成と呼び出し関係

```
index.html ──<script type="module">──▶ main.js ──import──▶ semesters.js ──import──▶ api.js
                                                   │
Bootstrap（base.html の通常の <script>。window.bootstrap） ◀── semesters.js が、モーダルを閉じるときに使う
```

- `base.html` のBootstrapの `<script>` は、通常のスクリプトとして、先に読み込まれる。`type="module"` のスクリプトは、ページの解析が終わってから実行されるため、`main.js` が動くときには、`window.bootstrap` が使える
- 今後のモード（授業・カレンダー・課題）は、それぞれ `initXxx()` を `export` し、`main.js` が呼ぶ（このタスクでは、`initSemesters()` だけ）

### `main.js`
- `initSemesters` を `semesters.js` から `import` し、呼ぶだけにする（ほかの処理を書かない）
- コメントに、「今後のモードの初期化も、ここに足す」と書く

### `api.js`
- `export class ApiError extends Error`：次のプロパティを持つ
  - `status`（HTTPのステータス。応答がなければ `0`）、`code`（文字列）、`message`（画面に出せる日本語）、`fields`（オブジェクトまたは `null`）
- `export async function apiRequest(method, url, body)`：
  - `body` が `undefined` でないときだけ、`Content-Type: application/json` を付け、`JSON.stringify(body)` を送る（`GET` には付けない）
  - 成功（2xx）：ステータスが204なら `null`、それ以外は、JSONを解析した値を返す
  - 失敗：応答の本文が `{"error": {"code", "message", "fields"?}}` の形なら、その値で `ApiError` を作って投げる
  - 通信できない（`fetch` が例外）：`status: 0`、`code: "network_error"`、`message: "サーバーに接続できませんでした。時間をおいて、もう一度お試しください"` の `ApiError` を投げる
  - 応答がJSONとして読めない、または形が違う：`code: "invalid_response"`、`message: "サーバーから想定外の応答がありました。時間をおいて、もう一度お試しください"` の `ApiError`（`status` は実際の値）を投げる
- 上記以外の機能（再試行、キャッシュ、ログなど）は、作らない

### `semesters.js`
- `export function initSemesters()` だけを `export` する。それ以外は、モジュールの中の関数にする
- 状態は、モジュールの中の変数2つだけ：一覧（`semesters`）と、選択中のid（`selectedId`）
- 次の役割の関数に分ける（名前は任意）
  - 取得と表示の切り替え：`GET /api/semesters` を呼び、状態（読み込み中／取得失敗／空／通常）に合わせて、各ブロックの `d-none` を切り替える
  - 初期選択の関数：上の「初期選択」の規則（一覧と今日の文字列を受け取り、選ぶ学期、またはなしを返す）
  - 描画：タブ（`createElement` で作り、`replaceChildren()` で差し替える）、バナー、本文
  - 日付の補助：今日の文字列、年度・種別の初期値、名前の組み立て、`YYYY-MM-DD` から日本語の表記
  - フォーム：モーダルを開く直前（`show.bs.modal` のイベント）に、入力値の初期化とエラー表示の消去を行う。送信の処理（`submit` のイベント）
  - エラー表示：「エラー処理」の表のとおり
- モーダルを閉じるときは、`window.bootstrap.Modal.getInstance(要素).hide()` を使う（開くときは、HTMLの `data-bs-toggle="modal"` に任せる）
- イベントの登録は、`initSemesters()` の中で1回だけ行う

## API利用仕様

| 場面 | 呼び出し | 備考 |
|---|---|---|
| ページを開いたとき、「再読み込み」、登録成功後 | `apiRequest("GET", "/api/semesters")` | 応答は、学期の配列（開始日の新しい順）。そのまま使う |
| 登録 | `apiRequest("POST", "/api/semesters", { name, start_date, end_date })` | `name` は組み立てた文字列。日付は、入力欄の値（`YYYY-MM-DD`）をそのまま送る。応答の `id` で、登録した学期を選ぶ |

- `GET /api/semesters/<id>`、`PATCH`、`DELETE` は、このタスクでは使わない
- ページを開いた時点で、1回だけ取得する（授業モードのタブを開いたときではない）

## エラー処理

| 場面 | 条件 | 表示 |
|---|---|---|
| 登録 | `validation_error` で `fields` がある | `fields.name` は、`#semester-name-error`（年度・種別の入力欄の下）。`fields.start_date` は `#semester-start-date-error`。`fields.end_date` は `#semester-end-date-error`。該当する入力欄には、`is-invalid` を付ける（`name` のときは、年度と種別の両方）。モーダルは閉じない |
| 登録 | 上記以外の `fields` の項目（想定外） | `#semester-form-error` に、「入力内容に誤りがあります」 |
| 登録 | それ以外すべて（`invalid_json`、`fields` のない `validation_error`、`not_found`、`method_not_allowed`、`server_error`、`network_error`、`invalid_response`） | `#semester-form-error` に、`ApiError` の `message` をそのまま表示する。モーダルは閉じない |
| 一覧の取得 | 失敗したすべて | 取得失敗の表示（`#semester-load-error-message` に、`message`）と、「再読み込み」 |

- 登録のエラー表示は、送信のたびに、いったん全部消してから、表示し直す
- 未対応の `code` でも、`message` を表示する（`code` で処理を分けるのは、`validation_error` の `fields` だけ）
- 登録に成功したあとの一覧の取得に失敗した場合は、「取得失敗」の表示にする（登録自体は成功している）

## 実装手順
1. ブランチと作業ツリーの確認（上記）。設計資料に、このタスクの前提が書かれていることを確認する。1つでも書かれていなければ、何も変更せずに停止して報告する（ブランチに、最新の設計資料が入っていない可能性がある）
   - `docs/ui_ux.md` の「学期（タブと登録）」に、「**読み込み中・取得失敗**」の小節と、空状態の「『最初の学期を登録する』ボタンだけを表示する」、登録フォームの「送信中は、『登録する』ボタンを無効にして、『登録中…』と表示する」
   - `docs/architecture.md` の「JavaScriptの構成（ES modules）」に、「### `api.js` の仕様」の小節（`network_error`・`invalid_response` を含む）と、規則の「`initXxx()`」「DOMの `id`」「モーダルはBootstrapのものを使う」
   - `.github/copilot-instructions.md` の「コーディング方針」に、「JavaScript（`app/static/js/`）：」の箇条書き
2. `base.html` に、`scripts` ブロックを追加する
3. `index.html` に、DOM構成のとおり、学期のブロックとモーダルを作り、`scripts` ブロックを書く
4. `api.js` を作る
5. `semesters.js` を作る
6. `main.js` を作る
7. `python run.py` を起動し、「動作確認手順（Copilot）」を実施する
8. 結果を報告して止まる（ブラウザでの確認は、Komaが行う）

## 完了条件
- 「動作確認手順（Copilot）」のすべてが、期待どおり
- 「動作確認手順（Koma）」のすべてが、期待どおり
- レビューで承認される

## 動作確認手順（Copilotが行う）
ブラウザは使えないので、次を確認する。**`semesters` にデータを作らない**（`POST` を実行しない）。

```
BASE=http://127.0.0.1:5001
sqlite3 instance/app.db "SELECT COUNT(*) FROM semesters;"        # 0 のまま（実施前後で同じ）
python run.py                                                      # 起動（別ターミナルで以下を実行）
curl -s -i $BASE/static/js/main.js | head -5                       # 200、Content-Type が text/javascript 系
curl -s -i $BASE/static/js/api.js | head -5                        # 200
curl -s -i $BASE/static/js/semesters.js | head -5                  # 200
curl -s $BASE/ | grep -c 'type="module"'                           # 1
curl -s $BASE/ | grep -n -E 'bootstrap.bundle|js/main.js'          # bootstrap.bundle の行が、main.js の行より前にある
curl -s -w '\nHTTP %{http_code}\n' $BASE/api/semesters             # 200、[]（API が変わっていないこと）
```

| 確認 | 期待する結果 |
|---|---|
| 3つのJSファイル | 200。`Content-Type` が JavaScript（`text/javascript` など。HTMLではない） |
| `GET /` のHTML | 次のIDがすべて1回ずつ含まれる：`semester-loading`、`semester-load-error`、`semester-load-error-message`、`semester-retry-button`、`semester-empty`、`semester-empty-open-button`、`semester-content`、`semester-banner`、`semester-banner-open-button`、`semester-tabs`、`semester-open-button`、`semester-detail`、`semester-detail-name`、`semester-detail-period`、`semester-modal`、`semester-form`、`semester-form-error`、`semester-year`、`semester-term`、`semester-name-error`、`semester-start-date`、`semester-start-date-error`、`semester-end-date`、`semester-end-date-error`、`semester-submit-button` |
| `GET /` のHTMLの構造 | モーダル（`semester-modal`）が、`<main>` の外にある。`<script>` は、Bootstrapの1つと、`type="module"` の1つだけ。`style=` や `onclick=` がない。3モードのラベル（カレンダー・授業・課題・タスク）が、そのまま残っている |
| 禁止事項（`app/static/js/` と `app/templates/` を検索） | `innerHTML`・`outerHTML`・`insertAdjacentHTML`・`document.write`・`eval(`・`localStorage`・`var `・`{{` のJSファイル内の出現が、すべて0件。`fetch(` は `api.js` の中だけ |
| 構文 | 3つのJSファイルが、エディタ（Pylanceなど）の診断で、構文エラーなし。`import` の相手のファイル名が、実在する |
| `git status` | modified：`app/templates/base.html`、`app/templates/index.html`。新規：`app/static/js/main.js`、`api.js`、`semesters.js` だけ。Pythonのファイル、`docs/`、`requirements.txt`、`migrations/`、`instance/` に変更なし |
| `git diff --stat`（変更の2ファイル） | `base.html` は数行、`index.html` は100行前後の追加が目安。大きく超える場合は、理由を報告する |

サーバーを停止し、`lsof -i :5001` が空であることを確認する。**ブラウザでの確認は、していないと明記して報告する。**

## 動作確認手順（Komaがブラウザで行う）
前提：`semesters` が0件。`python run.py` で起動し、Chromeで `http://127.0.0.1:5001` を開く。JavaScriptを直したあとは、強制再読み込み（Cmd＋Shift＋R）をする。開発者ツール（F12）のコンソールとネットワークを開いておく。

| 番号 | 操作 | 期待する結果 |
|---|---|---|
| S1 | ページを開き、「授業」を押す | 空状態（説明文と「最初の学期を登録する」）。タブ・バナー・「新しい学期を登録する」ボタンがない。コンソールにエラーがない。ネットワークに、`GET /api/semesters`（200）が1回ある |
| S2 | 「最初の学期を登録する」を押す | モーダルが開く。年度＝今日の年度（4〜12月は今年、1〜3月は前年）、種別＝今日が4〜8月なら前期、9〜3月なら後期。開始日・終了日は空 |
| S3 | 開始日を空のまま「登録する」を押す | ブラウザ標準の入力チェックで止まる。ネットワークに `POST` が出ない |
| S4 | 終了日を開始日と同じ日にして、「登録する」を押す | 終了日の入力欄の下に、「終了日は開始日より後にしてください」。モーダルは閉じない。ボタンは「登録する」に戻り、押せる |
| S5 | 「2026年度 前期」、開始日 2026-04-06、終了日 2026-07-20 で登録する | モーダルが閉じる。タブ「2026年度 前期」が現れて選択状態。本文に、名前と「2026年4月6日 〜 2026年7月20日」と注記。今日が期間外なら、バナー「新しい学期を登録しますか」が出る |
| S6 | 再度、同じ「2026年度 前期」で登録する | 年度・種別の入力欄の下に、「同じ名前の学期がすでに登録されています」。モーダルは閉じない |
| S7 | バナーの「登録する」を押し、「2026年度 後期」、2026-09-21〜2026-12-27 で登録する | モーダルが開く（入力値は初期値に戻っている）。登録後、タブが「2026年度 後期」「2026年度 前期」の順（左が新しい）。今日がこの期間に含まれていれば、バナーが消える |
| S8 | ページを再読み込みする | 今日を含む学期（後期）が選択されている。「前期」のタブを押すと、本文が前期に変わる。再読み込みすると、また後期に戻る |
| S9 | サーバーを止めて、「新しい学期を登録する」から登録を試す | モーダルに、「サーバーに接続できませんでした。時間をおいて、もう一度お試しください」。ボタンは元に戻る。サーバーを再起動すると、再度登録できる |
| S10 | 全体 | コンソールにエラーがない。ほかの2つのモード（カレンダー・課題・タスク）の表示と切り替えが、これまでどおり |

今日がS5・S7の期間と合わない場合は、「今日を含む」「含まない」の期待結果を読み替える。確認で作ったデータを消すときは、次のようにする（実際に使う学期は、消さない）。

```
sqlite3 instance/app.db "DELETE FROM semesters WHERE name IN ('2026年度 前期','2026年度 後期');"
```

## Copilotが変更してはいけないもの
上の「非対象」のすべて。特に、Pythonのファイル（APIを含む）、`docs/`、`.github/`、`requirements.txt`、`migrations/`、`instance/` の中のデータ、`base.html` の `scripts` ブロック以外の部分。

## Git操作
**Git commit / push / ブランチ操作 / マージは行わない**（`git branch --show-current`、`git status`、`git diff` のような読み取りだけのコマンドは除く）。

## 注意
- **停止して報告する条件**（ファイルを変更せず、実装を止め、チャットで「問題点・発生理由・変更した場合の影響・推奨案（必要なら）」を報告する）
  - ブランチの不一致、作業ツリーの想定外の変更
  - 設計資料とこのTask MDの間に、矛盾・不足がある
  - 設計資料にない判断が必要になった（特に `docs/architecture.md` の「未決定事項」に触れる場合）
  - 「変更しない」と定めたもの（Pythonのファイルなど）を変更しないと実装できない
  - `semesters` が0件でない（確認前）、5001番が使用中
- 期待する結果と異なる結果が出た場合は、確認を飛ばさず、原因を直してから、すべての確認をやり直す
- 設計資料に書かれていない仕様は、自分で決めない
- 途中の承認ゲートはない。「動作確認手順（Copilot）」を実施したら、結果を報告して止まる（Komaのブラウザ確認は、そのあと）
