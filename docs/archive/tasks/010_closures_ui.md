# タスク010: 休講日の画面（一覧・追加・削除）と、日付補助の共通化

| 項目 | 内容 |
|---|---|
| Task ID | 010 |
| Task名 | 休講日の画面（一覧・追加・削除）と、日付補助の共通化 |
| ブランチ | `feature/010-closures-ui`（Komaが作成・切替済みの状態で渡される） |

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに停止して報告する。

**このタスクには、承認ゲートはない。** 段階1〜3を順に進め、「Copilot確認手順」を実施したら、結果を報告して応答を終える。途中で止まるのは、「注意」の停止の条件に当たったときだけ。**止まるときは、報告を書いて応答を終える。質問の機能（選択肢を出して回答を待つ機能）は使わない**（`.github/copilot-instructions.md` の「止まる場面の応答」）。

## 目的
授業モードの、選択中の学期の本文（名前・期間）の下に、「休講日」の欄（一覧・追加・削除）を作り、Task 009の休講日API（`GET /api/closures`・`POST /api/closures`・`DELETE /api/closures/<id>`）を、初めて画面から使えるようにする。あわせて、日付の補助処理を、新しい `app/static/js/dates.js` に共通化し（休講日の日付の表示が、2つ目の利用者になるため）、Task 009のレビューで持ち越した009-L1を直す。

次の3段階で、この順に行う。

| 段階 | 内容 | 挙動の変化 | 段階の終わりの `pytest` |
|---|---|---|---|
| 1 | 009-L1（テストの確認を1行足す） | なし | **394件**（変わらない） |
| 2 | 日付補助の共通化（`dates.js` の新設と、`semesters.js` からの移動） | なし（学期UIの挙動は変えない） | **394件** |
| 3 | 休講日の欄（`index.html`・`closures.js`・`main.js`） | 休講日の欄が出る | **394件**（JavaScriptの自動テストはない） |

## 前提（Task 009完了時点の状態）

| 区分 | 内容 |
|---|---|
| すでにある | 学期API・授業API・休講日API（`GET /api/closures?semester_id=`・`POST /api/closures`・`DELETE /api/closures/<id>`。予定の同期は、まだない）、学期UI・授業UI（`main.js`・`api.js`・`ui.js`・`semesters.js`・`subjects.js`）、pytest（**394件**。`main` の `06eeb2c` で確認） |
| まだない | 休講日の画面、`closures.js`、`dates.js` |
| DBの構造 | 変えない（初期migration `0280f6cf8d09` と、休講日の `42bd53808fa1`）。**migrationは不要** |
| 開発用DB | `instance/app.db` は、Komaの実際の開発用DB（`closures` テーブルは適用済み。学期は0件。2026-10-11にKomaが確認）。**Copilotは、書き込まない。サーバーを起動しない（`python run.py` を実行しない）**。読むのは、「Copilot確認手順」のハッシュと件数だけ |
| 設計資料 | このタスクの前に、更新した設計資料が `main` に反映されている。`docs/architecture.md` の「JavaScriptの構成（ES modules）」に、`dates.js` の行と、日付の補助処理の規則、選択に依存する画面での登録・削除の規則がある（未決定事項「日付補助の共通化」は、なくなっている）。`docs/ui_ux.md` の「休講日」に、欄の中の並び、学期を切り替えたときの扱い、「追加・削除の共通」がある。`.github/copilot-instructions.md` に「止まる場面の応答」がある |
| JavaScriptの確認 | JavaScriptの自動テストはない（pytestは、APIだけが対象）。Copilotはブラウザを使えないため、画面の動作は、Komaが、確認用のサーバーとブラウザで確かめる（「Komaの確認」）。Copilotは、テンプレートの出力（Flaskのテスト用のクライアント）と、コードの検索・差分で確かめる |
| 設計資料のほうが先の部分 | 休講日の追加・削除による予定（Event）の同期、予定の自動生成、`generated_event_count` は、Task 011で入れる。休講日の画面は、予定を扱わない（休講日の行だけを扱う）。予定が変わらないことは、矛盾として扱わない |

## Source of Truth
- `docs/ui_ux.md`：「授業モード」の「学期（タブと登録）」と「休講日」
- `docs/architecture.md`：「JavaScriptの構成（ES modules）」（`ui.js`・`dates.js`・`closures.js` の行、規則、「モード間の連携（`CustomEvent`）」、「`api.js` の仕様」）、「休講日API」、「API共通ルール」の「エラー」
- `docs/tasks/006_subjects_ui.md`：授業の一覧と登録フォームの作り（休講日の欄は、これに合わせる）
- `docs/tasks/009_closures_api.md`：休講日APIのエラーメッセージの文言、M1（009-L1の対象のテスト）
- `.github/copilot-instructions.md`：進め方、「止まる場面の応答」、コーディング方針（特にJavaScript）、「テスト」

## 実装対象ファイル

| 区分 | ファイル | 段階 | 内容 |
|---|---|---|---|
| 変更 | `tests/test_closures_api.py` | 1 | 009-L1：1行の追加だけ |
| 新規 | `app/static/js/dates.js` | 2 | 日付の補助処理（3つの関数） |
| 変更 | `app/static/js/semesters.js` | 2 | 日付の補助処理の2つの関数を `dates.js` へ移し、`import` に替える（D1〜D3だけ） |
| 新規 | `app/static/js/closures.js` | 3 | 休講日の欄（一覧・追加・削除） |
| 変更 | `app/templates/index.html` | 3 | 休講日の欄のHTML（1か所に足すだけ） |
| 変更 | `app/static/js/main.js` | 3 | `initClosures()` の追加 |

上の6ファイル以外は、変更しない（`__pycache__/` などの、`.gitignore` の対象は除く）。

## 非対象（このタスクでは作らない・変更しない）
- Pythonのファイルのすべて（`app/*.py`、`app/routes/`、`app/models/`、`run.py`）。**APIは変えない**
- `tests/` の、段階1の1行以外。新しいテストは足さない（件数は394のまま）
- `migrations/`（**新しいmigrationを作らない。`flask db` のコマンドを、一切実行しない**）、`requirements.txt`（**ライブラリを追加しない**）、`pytest.ini`
- `app/static/js/api.js`・`ui.js`・`subjects.js`。**`ui.js` に、新しい共通の関数を作らない**（公開する関数は6つのまま）。`subjects.js` の授業の曜日の表（`WEEKDAYS`）は、`dates.js` に移さない（授業の `weekday` は0=月曜の並びで、`dates.js` の曜日の表示（0=日曜）とは並びが違うため。`docs/architecture.md` の規則）
- `app/templates/base.html`。`index.html` の、休講日の欄以外の部分（学期・授業のブロック、モーダル）
- `docs/`、`.github/`、`.gitignore`
- 学期UIの挙動の変更（段階2は、関数を移すだけ）。`semesters.js` の、D1〜D3以外の行
- 予定（Event）の画面・同期、カレンダー（Task 011以降）
- `docs/ui_ux.md` の「未決定」のうち、曜日ごとの授業日数の表示、連続した日のまとめての登録、カレンダーへの休講日の表示
- 独自のCSS（`app/static/css/` を作らない）、`style` 属性、JavaScriptの自動テスト
- 開発用DB（`instance/app.db`）への書き込み、サーバーの起動（`python run.py` も、「Komaの確認」の確認用のサーバーも、起動しない）
- Task 003の持ち越しの残り（003-H）、Task 006のLow（006-L1・L2）

## 段階1：009-L1（テスト。挙動を変えない）
`tests/test_closures_api.py` の `test_unsupported_closure_methods_do_not_change_rows`（`main` の587〜599行目）で、593行目 `before = client.get("/api/closures")` の次の行に、`assert before.status_code == 200` を足す（Task 008の007-L2と同じ形。要求の前の一覧の取得が、成功していることを確かめる）。ほかの行は変えない。

```python
    url = url.format(closure_id=closure_id)
    before = client.get("/api/closures")
    assert before.status_code == 200

    response = getattr(client, method)(url)
```

段階1の終わりに、`python -m pytest -q` が **394件、すべて合格**すること（件数は変わらない）。

## 段階2：日付補助の共通化（学期UIの挙動を変えない）
行番号は、`main`（このタスクを始める時点、`06eeb2c`）のもの。

### 2-1. `app/static/js/dates.js`（新規）
次のとおりに書く（動作を確かめたコード）。

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
```

- 公開する関数は、この3つだけ。`WEEKDAY_LABELS` は `export` しない
- `localDateString` と `formatJapaneseDate` は、`semesters.js` の今のコード（38〜44行目・80〜83行目）を、コメントも含めて、そのまま移したもの（処理を変えない）
- DOMとAPI（`fetch`・`api.js`）を扱わない。ほかのファイルを `import` しない
- 表示の例：`formatJapaneseDate("2026-09-21")` は「2026年9月21日」、`formatJapaneseDateWithWeekday("2026-05-15")` は「2026年5月15日（金）」

### 2-2. `app/static/js/semesters.js`

| 番号 | 場所（`main` の行） | 変更 |
|---|---|---|
| D1 | 1行目 `import { apiRequest } from "./api.js";` の次 | `import { formatJapaneseDate, localDateString } from "./dates.js";` を足す（`import` の並びは、ファイル名の順：`api.js`・`dates.js`・`ui.js`） |
| D2 | 38〜44行目（`function localDateString`）と、その次の空行（45行目） | 消す（`dates.js` へ移した） |
| D3 | 80〜83行目（`function formatJapaneseDate`）と、その次の空行（84行目） | 消す（`dates.js` へ移した） |

- ほかの行は変えない。`localDateString()`（153行目・262行目）と `formatJapaneseDate(...)`（168〜169行目）の呼び出しは、名前が同じなので、そのまま動く
- `resetForm` の年度・種別の初期値（`new Date()` を使う部分）は、学期に固有の処理なので、`semesters.js` に残す（`docs/architecture.md` の規則）

段階2の終わりに、`python -m pytest -q` が **394件、すべて合格**すること。

## 段階3：休講日の欄

### 3-1. `app/templates/index.html`
36行目 `<p id="semester-detail-period" class="text-muted"></p>` と、37行目 `<div id="subject-section" class="mt-4">` の間に、次のブロックを入れる。**ID・クラス・構造・文言は、このとおり**にする。インデントは、前後の行に合わせる（`<div id="closure-section"` の行は、空白10文字）。

```html
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
```

- 欄の中の並びは、`docs/ui_ux.md` のとおり（上から、見出し、欄の上部のエラーの表示、一覧、追加の入力欄）
- `#closure-semester-error` は、`semester_id` のエラー（入力欄のない項目）を出す場所、`#closure-form-error` は、欄の上部のエラー（追加の、項目に結びつかないエラーと、削除のエラー）を出す場所
- 入力の検証は、日付の `required`（ブラウザ標準）だけ。`min`・`max`・`maxlength` は付けない（`docs/ui_ux.md`。検証は、APIが行う）。`form` に `novalidate` を付けない
- 欄は `#semester-content` の中にあるため、学期が0件のとき（空状態）と、学期の一覧の取得に失敗したときは、表示されない（`semesters.js` が、`#semester-content` を隠す）。`closures.js` は、欄そのものの表示・非表示を切り替えない

### 3-2. `app/static/js/closures.js`（新規）
動き（`docs/ui_ux.md` の「休講日」と、`docs/architecture.md` の「JavaScriptの構成」の規則による）：

| 場面 | 動き |
|---|---|
| `semester-selected` を受け取ったとき | 選択中の学期を替え、学期の選択の通し番号と、一覧の取得の通し番号を1増やす。追加の入力欄を空に戻し、エラーの表示を消し、「追加する」ボタンを元に戻す。学期が `null` なら、一覧を空にして終わる。そうでなければ、「読み込み中…」を出して、一覧を取得する |
| 一覧の取得 | `GET /api/closures?semester_id=<id>`。要求のたびに、一覧の取得の通し番号を1増やして控え、応答が届いたときに違えば、結果を捨てる。成功：0件なら「休講日は登録されていません」、1件以上なら一覧。失敗：エラーメッセージと「再読み込み」 |
| 一覧の行 | 日付（`formatJapaneseDateWithWeekday`）、名前（`null` でなければ）、「削除」ボタン。`createElement` で作り、`replaceChildren()` で差し替える。並びは、APIの応答の順（日付の昇順） |
| 追加（`submit`） | 学期の選択の通し番号を控える。エラーの表示を消す。「追加する」を無効にして「追加中…」。`POST /api/closures`（本文は `semester_id`・`date`・`name`。値は、入力欄の値のまま。前後の空白の除去などは、APIが行う） |
| 追加の成功 | 選択が変わっていなければ：入力欄を空に戻し、ボタンを元に戻し、日付の入力欄にフォーカスを移し、一覧を取得し直す（「読み込み中…」は出さない） |
| 追加の失敗 | 選択が変わっていなければ：`showApiError` でエラーを表示し（項目のエラーは入力欄の下、それ以外は欄の上部）、ボタンを元に戻す。入力欄の値は残す |
| 削除（行の「削除」） | 学期の選択の通し番号を控える。エラーの表示を消す。その行の「削除」を無効にして「削除中…」。`DELETE /api/closures/<id>` |
| 削除の成功 | 選択が変わっていなければ：一覧を取得し直す（「読み込み中…」は出さない） |
| 削除の失敗 | 選択が変わっていなければ：欄の上部にエラーを表示し、その行の「削除」を元に戻す。一覧は、取得し直さない |
| 追加・削除の途中で学期が変わったとき | 応答が届いても、画面（入力欄・メッセージ・ボタン・一覧）を変えない（新しい学期の画面は、`semester-selected` のときに作り直しているため） |
| 「再読み込み」 | 「読み込み中…」を出して、一覧を取得し直す |

項目の対応表（`showApiError` と `clearFormErrors` に渡す。欄の上部のエラーの表示は `closure-form-error`）：

| 項目 | 入力欄 | エラーの表示 |
|---|---|---|
| `semester_id` | なし | `closure-semester-error` |
| `date` | `closure-date` | `closure-date-error` |
| `name` | `closure-name` | `closure-name-error` |

次のとおりに書く（動作を確かめたコード）。

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

    const text = document.createElement("div");
    const dateText = document.createElement("span");
    dateText.textContent = formatJapaneseDateWithWeekday(closure.date);
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

async function loadClosures(showLoading = true) {
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

  try {
    await apiRequest("POST", "/api/closures", {
      semester_id: currentSemester.id,
      date: getElement("closure-date").value,
      name: getElement("closure-name").value,
    });
    if (startedSelection !== selectionSerial) {
      return;
    }
    resetClosureForm();
    getElement("closure-date").focus();
    await loadClosures(false);
  } catch (error) {
    if (startedSelection !== selectionSerial) {
      return;
    }
    showApiError(error, CLOSURE_FIELDS, CLOSURE_FORM_ERROR_ID);
    setSubmitting(submitButton, false, CLOSURE_SUBMIT_LABELS);
  }
}

async function deleteClosure(closureId, button) {
  // 削除の途中で学期が変わったら、結果を今の画面に出さないために控える。
  const startedSelection = selectionSerial;
  clearClosureErrors();
  setSubmitting(button, true, CLOSURE_DELETE_LABELS);

  try {
    await apiRequest("DELETE", `/api/closures/${closureId}`);
    if (startedSelection !== selectionSerial) {
      return;
    }
    await loadClosures(false);
  } catch (error) {
    if (startedSelection !== selectionSerial) {
      return;
    }
    showApiError(error, CLOSURE_FIELDS, CLOSURE_FORM_ERROR_ID);
    setSubmitting(button, false, CLOSURE_DELETE_LABELS);
  }
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

- `export` は、`initClosures` だけ。`semesters.js`・`subjects.js` を `import` しない（モード間の連携は、`semester-selected` だけ）
- `ui.js` から `import` するのは、公開されている6つの関数の中だけ
- 行の「削除」ボタンの `id` は、`closure-delete-<休講日のid>`（`docs/architecture.md` のDOMの `id` の規則。タブの `semester-tab-<id>` と同じ形）

### 3-3. `app/static/js/main.js`
次のとおりにする（`initClosures` の `import` と呼び出しを足すだけ。`semester-selected` を購読する側を、発行する側（`initSemesters()`）より先に呼ぶ規則のとおり）。

```javascript
import { initClosures } from "./closures.js";
import { initSemesters } from "./semesters.js";
import { initSubjects } from "./subjects.js";

// 今後のモードの初期化も、ここに足す。
// semester-selectedを購読する側を、イベントを発行する側より先に初期化する。
initSubjects();
initClosures();
initSemesters();
```

### 3-4. DOMの `id` の一覧（段階3で足すもの）
`closure-section`、`closure-semester-error`、`closure-form-error`、`closure-loading`、`closure-load-error`、`closure-load-error-message`、`closure-retry-button`、`closure-empty`、`closure-list`、`closure-form`、`closure-date`、`closure-date-error`、`closure-name`、`closure-name-error`、`closure-submit-button`（15個。ページの中で、それぞれ1回だけ）。ほかに、行ごとに `closure-delete-<id>` を、`closures.js` が作る。

### 3-5. 変わる挙動・変わらない挙動

| 場面 | 変更後 |
|---|---|
| 授業モード（学期が1件以上） | 学期の本文の下、授業の上に、休講日の欄が出る |
| 学期が0件（空状態）・学期の一覧の取得の失敗 | 変わらない（休講日の欄は出ない） |
| 学期の期間の表示、バナー、初期の選択、学期の登録 | 変わらない（段階2は、関数を移すだけ） |
| 授業の一覧・登録 | 変わらない |
| 休講日の追加・削除と、予定（Event） | 予定は変わらない（同期は、Task 011でAPIに入れる。画面は、予定を扱わない） |

## JavaScriptの共通の規則
`.github/copilot-instructions.md` の「コーディング方針（JavaScript）」と、`docs/architecture.md` の「JavaScriptの構成（ES modules）」の規則に従う（名前つきの `export`、`innerHTML` などの禁止、`textContent`、`fetch` は `api.js` の中だけ、日本語のコメント、など）。次の点を、特に守る。
- 日付の補助処理は、`dates.js` に置く。`closures.js` に、日付を「年月日」に変える処理を書かない
- 日付の文字列から `Date` を作るときに、`new Date("YYYY-MM-DD")` を使わない
- JavaScriptの1行は、80文字以内（今のファイルに合わせる）
- 理由のコメントは、上のコードの例のとおりに書く（`toISOString()` を使わない理由、`new Date("YYYY-MM-DD")` を使わない理由、曜日の並びの違い、2つの通し番号の役割、古い応答を捨てる理由、学期の切り替えで入力欄を空に戻す理由）

## 変更してよい既存のテスト

| ファイル | 変更してよいもの | それ以外 |
|---|---|---|
| `tests/test_closures_api.py` | `test_unsupported_closure_methods_do_not_change_rows` に、段階1の1行を足すことだけ | 変えない |
| ほかの `tests/` のファイル | なし | 変えない |

- 新しいテストは足さない（件数は394のまま）。テストの期待値は変えない
- このタスクでの「既存のテスト」は、作業の開始時からあるすべてのテスト（段階1で1行足すテストを含む）。**既存のテストが想定外に失敗した場合**は、テストの期待値や、ほかの仕様を直さない。原因を調べ、そこで実装を止めて、チャットで報告する

## 実装手順
1. ブランチ・作業ツリーの確認。設計資料が更新されていることを確認する（「Copilot確認手順」の1の `grep`）。更新されていなければ、何も変更せずに停止して報告する
2. 作業の前の状態を記録する：開発用DBの有無・ハッシュ・件数（「Copilot確認手順」の1）。`python -m pytest -q` が394件、すべて合格すること（合格しなければ、何も変更せずに停止して報告する）
3. **（段階1）** `tests/test_closures_api.py` の1行。`python -m pytest -q` が394件、すべて合格すること。1行の長さの確認（「Copilot確認手順」の3）
4. **（段階2）** `dates.js`（2-1）→ `semesters.js`（2-2）。`python -m pytest -q` が394件、すべて合格すること。「Copilot確認手順」の4
5. **（段階3）** `index.html`（3-1）→ `closures.js`（3-2）→ `main.js`（3-3）。`python -m pytest -q` が394件、すべて合格すること。「Copilot確認手順」の3・5・6
6. 「Copilot確認手順」の7を実施する
7. 結果を報告して、応答を終える（ブラウザでの確認は、していないと明記する）

各段階の終わりに、`python -m pytest -q` の結果（件数・警告）を控えておく（最終報告に書く）。

## 完了条件
- `python -m pytest -q` が、段階1・2・3の終わりに、**394件、すべて合格**する（失敗・エラー・スキップが0件）
- 変更したファイルが、「実装対象ファイル」の6つだけ
- `tests/test_closures_api.py` の差分が、段階1の1行だけ。`semesters.js` の差分が、D1〜D3だけ
- `dates.js`・`closures.js`・`main.js`・`index.html` が、2-1・3-1〜3-3のとおり
- 画面のHTMLの確認（「Copilot確認手順」の5）で、3-4の `id` が、それぞれ1回だけ含まれ、並びが期待どおり
- `app/`・`tests/`・`run.py` のPythonのファイルに、79文字を超える行がなく、`app/static/js/` のファイルに、80文字を超える行がない
- 実施の前後で、開発用DB（`instance/app.db`）のハッシュと、`semesters`・`subjects`・`closures` の件数が同じ
- 「Komaの確認」が、期待どおり
- レビューで承認される

## Copilot確認手順
```
# 1. 実施前
git branch --show-current      # feature/010-closures-ui
git status                     # 変更なし
grep -n "dates.js" docs/architecture.md                          # 数件（JavaScriptの構成の表・規則・ディレクトリ構成）
grep -n "日付補助の共通化" docs/architecture.md docs/ui_ux.md      # 出力なし（未決定事項から外れている）
grep -n "追加・削除の共通" docs/ui_ux.md                          # 1件
grep -n "止まる場面の応答" .github/copilot-instructions.md        # 数件
ls -l instance/app.db          # 存在すること（なければ、何も変更せずに停止して報告する）
shasum -a 256 instance/app.db
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures;"
python -m pytest -q            # 394 passed

# 2. 各段階の終わり
python -m pytest -q            # 段階1・段階2・段階3とも 394 passed

# 3. 1行の長さ（段階1・段階3の終わり。出力がなければ合格。migrations/ は対象外）
python - <<'EOF'
from pathlib import Path
paths = [*Path("app").rglob("*.py"), *Path("tests").glob("*.py"), Path("run.py")]
for path in paths:
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, 1):
        if len(line) > 79:
            print(f"{path}:{number}: {len(line)}")
for path in sorted(Path("app/static/js").glob("*.js")):
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, 1):
        if len(line) > 80:
            print(f"{path}:{number}: {len(line)}")
EOF

# 4. 検索（段階2の終わり）
grep -n "^export function" app/static/js/dates.js      # 3件：localDateString・formatJapaneseDate・formatJapaneseDateWithWeekday
grep -n "^import" app/static/js/dates.js                # 出力なし
grep -n "function localDateString\|function formatJapaneseDate" app/static/js/semesters.js   # 出力なし
grep -n 'from "./dates.js"' app/static/js/semesters.js  # 1件（2行目）
grep -rnE '^[^/]*new Date\(' app/static/js/              # 3件（コメントの行は除く）：semesters.js の resetForm の new Date()、dates.js の localDateString の new Date() と、new Date(year, month - 1, day)
git diff app/static/js/semesters.js                     # D1〜D3だけ（1行の追加と、2つの関数の削除）

# 5. 画面のHTMLの確認（段階3の終わり。DBを使わない。開発用DBは開かない）
python - <<'EOF'
import re
import tempfile
from pathlib import Path

from app import create_app

EXPECTED_IDS = [
    "closure-section", "closure-semester-error", "closure-form-error",
    "closure-loading", "closure-load-error", "closure-load-error-message",
    "closure-retry-button", "closure-empty", "closure-list",
    "closure-form", "closure-date", "closure-date-error", "closure-name",
    "closure-name-error", "closure-submit-button",
]
ORDER = [
    "semester-detail-period", "closure-section", "closure-form-error",
    "closure-list", "closure-form", "subject-section",
]

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
    for name in ["dates.js", "closures.js", "semesters.js", "main.js"]:
        response = client.get(f"/static/js/{name}")
        print(name, response.status_code, response.mimetype)
        response.close()
EOF

# 6. 検索（段階3の終わり）
grep -n "^export" app/static/js/closures.js              # 1件：initClosures
grep -n "^import" app/static/js/closures.js              # 3件：api.js・dates.js・ui.js（ui.js は、複数行の import の1行目）
grep -n "semesters.js\|subjects.js" app/static/js/closures.js   # 出力なし
grep -n "initClosures" app/static/js/main.js             # 2件：import と、initSubjects() と initSemesters() の間の呼び出し
grep -n "selectionSerial" app/static/js/closures.js      # 8件：宣言、追加の控え・確認2つ、削除の控え・確認2つ、semester-selected での増加
grep -rnE "innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(|localStorage|sessionStorage|setTimeout|export default|\bvar " app/static/js/   # 出力なし
grep -rn "fetch(" app/static/js/                         # api.js の中の1件だけ
grep -rn "{{" app/static/js/                             # 出力なし
grep -nE "onclick|style=" app/templates/index.html       # 出力なし
git diff app/templates/index.html                        # 3-1のブロックの追加だけ（ほかの行は変わらない）

# 7. 実施後
shasum -a 256 instance/app.db  # 実施前と同じ
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects; SELECT COUNT(*) FROM closures;"   # 実施前と同じ
git status                     # 変更：「実装対象ファイル」の6つだけ
git diff --stat
```

| 確認 | 期待する結果 |
|---|---|
| `python -m pytest -q` | 実施前、段階1・段階2・段階3の終わりとも、394件がすべて合格。失敗・エラー・スキップが0件。`migrations/env.py` の `DeprecationWarning` は、出ても構わない（報告する） |
| 1行の長さ | 出力なし |
| 検索 | 上のコメントのとおり（件数が違う場合は、その行を報告に書く） |
| 画面のHTMLの確認 | 15個の `id` が、それぞれ `1`。「重複したid: []」。「並び: True」。4つのJavaScriptのファイルが `200 text/javascript` |
| 開発用DB | 実施の前後で、ハッシュと、`semesters`・`subjects`・`closures` の件数が同じ |
| `git status` | 変更：`tests/test_closures_api.py`、`app/static/js/semesters.js`、`app/static/js/main.js`、`app/templates/index.html`。新規：`app/static/js/dates.js`、`app/static/js/closures.js`。Pythonの `app/` のファイル・`migrations/`・`docs/`・`.github/`・`requirements.txt`・`run.py`・`instance/`・`api.js`・`ui.js`・`subjects.js`・`base.html` に変更なし |

`.pytest_cache/` や `__pycache__/` が `git status` に表示される場合は、`.gitignore` を変更せず、報告する。**Copilotは、サーバーを起動せず、ブラウザでの確認もしない**（Komaが行う）。報告に、ブラウザで確認していないことを明記する。

## Komaの確認
順序：（1）pytest →（2）commit・push とレビューの依頼 →（3）ブラウザでの確認（確認用のサーバー）→（4）開発用DBでの、読み取りだけの確認 →（5）マージ。

### 1. pytest
`python -m pytest -q` を自分で実行し、**394件、すべて合格**することを確かめる。

### 2. push とレビューの依頼
featureブランチを commit・push する（PRを作ってもよい）。Copilotの完了報告を共有して、Claudeにレビューを頼む。**pushは、マージではない。レビューの承認の前に、マージしない。** 修正が必要になった場合は、同じブランチでCopilotが直し、もう一度pushしてレビューを受ける。

### 3. ブラウザでの確認（確認用のサーバー）
レビューで「承認可能」になったあとに行う（修正が必要になった場合は、修正のあとに行う）。ブラウザの操作は、Claude in Chromeで行ってもよい（その場合も、サーバーの起動・停止など、ターミナルの操作は、Komaが行う）。

#### 確認の安全のしくみ
- **開発用DBは使わない。** 確認用のDB（`/tmp/schedule-app-check-010/check.db`）を、migrationで作り、そのDBで起動した確認用のサーバーで確かめる。学期・休講日・授業は、確認用のDBに登録する（開発用DBには、何も残らない。学期は、アプリから削除できないため）
- 確認用のサーバーは、`create_app` に確認用のDBの場所を渡して起動する（Task 009のmigrationの生成と同じ方法）。`instance/` は使われず、開発用DBは開かれない
- 確認用のDBは、サーバーを止めて起動し直しても残る（C16〜C18で使う）。終わったら、フォルダごと消す
- 確認の前後で、開発用DBのハッシュが同じことを確かめる

#### 確認の日付
期待する結果は、確認の日が **2026-09-21〜2027-01-31** の間にあることを前提にしている（R3で登録する「2026年度 後期」が、今日を含む）。この範囲の外の日に行う場合は、R2〜R4の、バナーと初期の選択の期待が変わるため、行う前にClaudeに伝える。

#### 準備
1. `python run.py` が起動していれば、Ctrl＋Cで止める（確認用のサーバーも、5001番を使うため）。開発用DBのハッシュを控える
   ```
   shasum -a 256 instance/app.db
   ```
2. 下の「確認用のサーバーの起動」のコマンドで、確認用のサーバーを起動する（このターミナルは、確認の間、開いたままにする）
3. Chromeで `http://127.0.0.1:5001/` を開き、強制再読み込み（Cmd＋Shift＋R）をして、画面下の「授業」を押す。開発者ツール（Cmd＋Option＋I）の「コンソール」を開いておく
4. 別のターミナルを開き、リポジトリのルートで、`BASE=http://127.0.0.1:5001` を実行しておく（C15で使う）

#### 確認用のサーバーの起動
ブランチ `feature/010-closures-ui` のまま、リポジトリのルートで、`.venv` を有効にして、次を実行する（行の先頭に空白を入れずにコピーする。空白が入ると、Pythonがエラーになり、最後の `EOF` でも終わらない）。

```
python - <<'EOF'
from pathlib import Path

from flask_migrate import upgrade

from app import create_app

# 確認用のDB（開発用DBとは別のファイル）。止めて起動し直しても、残る。
check_directory = Path("/tmp/schedule-app-check-010")
check_directory.mkdir(exist_ok=True)
database_path = check_directory / "check.db"
app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"})
with app.app_context():
    upgrade(directory="migrations")
print(f"確認用のDB：{database_path}", flush=True)
app.run(host="127.0.0.1", port=5001, debug=False)
EOF
```

期待する出力：初めての起動では、`Running upgrade  -> 0280f6cf8d09, initial tables` と `Running upgrade 0280f6cf8d09 -> 42bd53808fa1, add closures table`、「確認用のDB：/tmp/schedule-app-check-010/check.db」、`Running on http://127.0.0.1:5001`。起動し直したときは、`Running upgrade` の行が出ない（データが残っている）。`debug=False` のため、コードを直しても、自動では再起動しない（止めて、起動し直す）。

#### R. 学期UIの回帰（段階2で、日付の関数を移したため）

| No | 操作 | 期待する結果 |
|---|---|---|
| R1 | 「授業」を開いたまま、画面を見る | 「学期がまだ登録されていません。最初の学期を登録してください」と「最初の学期を登録する」ボタンだけ。休講日の欄は出ない。コンソールに、赤いエラーがない |
| R2 | 「最初の学期を登録する」を押し、年度2026・種別「前期」（初期値は「後期」なので、変える）、開始日2026-04-06、終了日2026-07-31で登録する | モーダルが閉じ、「2026年度 前期」が選ばれる。期間が「2026年4月6日 〜 2026年7月31日」。バナー「新しい学期を登録しますか」が出る（今日が、どの学期にも含まれないため）。期間の下、「授業」の上に、休講日の欄が出て、「休講日は登録されていません」 |
| R3 | 「新しい学期を登録する」を押し、年度2026・種別「後期」、開始日2026-09-21、終了日2027-01-31で登録する | モーダルが閉じ、「2026年度 後期」が選ばれ、タブの左に並ぶ。期間が「2026年9月21日 〜 2027年1月31日」。バナーが消える |
| R4 | ページを再読み込みする | 「2026年度 後期」が選ばれている（今日を含む学期）。バナーは出ない |
| R5 | タブを「前期」「後期」と切り替える | 期間の表示が、それぞれの学期のものに切り替わる。最後に「後期」を選んでおく |

#### C. 休講日の欄（「2026年度 後期」を選んだ状態から）

| No | 操作 | 期待する結果 |
|---|---|---|
| C1 | 休講日の欄を見る | 上から、見出し「休講日」、「休講日は登録されていません」、「日付」（空）と「名前（任意）」（薄い字で「例：開学記念日」）の入力欄、「追加する」ボタン。その下に、見出し「授業」 |
| C2 | 日付 2026-11-03、名前「文化の日」で「追加する」を押す | 確認のダイアログは出ない。一覧に、「2026年11月3日（火）」と「文化の日」（少し離して、薄い字）と、右端に「削除」ボタンの行が出る。入力欄が空に戻り、日付の欄にフォーカスがある |
| C3 | 日付 2026-10-21 だけで追加する。続けて、日付 2027-01-04、名前「　冬季休業 」（前後に空白）で追加する | 日付の昇順に、「2026年10月21日（水）」（名前なし）、「2026年11月3日（火） 文化の日」、「2027年1月4日（月） 冬季休業」（前後の空白なし） |
| C4 | 日付 2026-09-21（開始日）、2027-01-31（終了日）、2026-10-17（土曜日）を、それぞれ追加する | どれも追加できる。曜日は、それぞれ「（月）」「（日）」「（土）」。一覧は日付の順 |
| C5 | 日付を空のまま、「追加する」を押す | ブラウザ標準の入力チェックで止まる（要求は送られない。一覧は変わらない） |
| C6 | 日付 2026-09-20（期間の前の日）で追加する。続けて、2027-02-01（期間の後の日）で追加する | どちらも、日付の欄の下に「休講日は、学期の期間内の日付にしてください」。日付の欄が赤枠になる。入力した値は残る。ボタンは「追加する」に戻る |
| C7 | 日付 2026-11-03（登録済み）で追加する | 日付の欄の下に、「同じ日付の休講日がすでに登録されています」 |
| C8 | 日付を 2026-12-25 にし、名前の欄に101文字を入れて、追加する（コンソールで `document.getElementById("closure-name").value = "あ".repeat(101)` を実行してから、「追加する」を押してもよい） | 名前の欄の下に、「名前は100文字以内にしてください」。C7の日付のエラーは消えている |
| C9 | そのまま、名前を「冬休み」に直して、追加する | 追加でき、エラーの表示が消える |
| C10 | 日付 2026-11-23、名前 `<b>太字</b>` で追加する | 一覧に、`<b>太字</b>` が、そのまま文字として出る（太字にならない） |
| C11 | 「2026年10月21日（水）」の行の「削除」を押す | 確認のダイアログは出ず、その行だけが消える |
| C12 | 日付 2026-08-01、名前「入力中」で追加し、期間のエラーを出す。そのまま、「2026年度 前期」のタブを押す | 前期の休講日の欄（「休講日は登録されていません」）に切り替わる。入力欄が空になり、エラーの表示が消えている |
| C13 | 前期で、日付 2026-04-29、名前「昭和の日」で追加する。続けて、日付 2026-11-03 で追加する | 4/29は、「2026年4月29日（水） 昭和の日」として追加される。11/3は、「休講日は、学期の期間内の日付にしてください」（学期ごとに検査される） |
| C14 | 「後期」のタブに戻る | 後期の休講日だけが出る（4/29は出ない） |
| C15 | 別のターミナルで、後期の「2026-09-21」の休講日を、APIで削除する（下のコマンド）。そのあと、画面の「2026年9月21日（月）」の行の「削除」を押す | 欄の上部に、「休講日が見つかりません」。その行の「削除」ボタンが、押せる状態に戻る（一覧は取得し直さないため、行は残る）。「前期」→「後期」とタブを切り替えると、その行は消えている |
| C16 | 確認用のサーバーを止める（サーバーのターミナルで Ctrl＋C）。日付 2026-12-01 で「追加する」を押す。続けて、どれかの行の「削除」を押す | どちらも、欄の上部に、「サーバーに接続できませんでした。時間をおいて、もう一度お試しください」。ボタンは「追加する」・「削除」に戻る。追加の入力欄の値（2026-12-01）は残る |
| C17 | サーバーを止めたまま、「前期」のタブを押す | 休講日の欄に、エラーメッセージと「再読み込み」ボタン（授業の欄も、同じような表示になる） |
| C18 | 「確認用のサーバーの起動」のコマンドで、確認用のサーバーを起動し直す（ターミナルで↑キーを押すと、前のコマンドを呼び出せる。`Running upgrade` の行は出ない）。休講日の欄の「再読み込み」を押す | 前期の休講日（「2026年4月29日（水） 昭和の日」）が出る |
| C19 | 確認の全体を通して | コンソールに、赤いエラーが出ていない。ただし、C16・C17でサーバーを止めている間の、接続の失敗の表示（`net::ERR_CONNECTION_REFUSED`）は除く |

C15のコマンド（後期の学期の `id` は、R2・R3の順に登録していれば `2`）：

```
curl -s "$BASE/api/closures?semester_id=2" | python -m json.tool --no-ensure-ascii   # 2026-09-21 の行の id を控える
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X DELETE $BASE/api/closures/<控えたid>   # HTTP 204
```

#### D. 送信中の表示と、途中の学期の切り替え（遅延の確認）
休講日のAPIへの要求を、ブラウザの中で2秒遅らせて、送信中の表示と、追加・削除の途中で学期を切り替えたときの動きを確かめる。下の「遅延のスクリプト」を、コンソールに貼り付けて、Enterを押す。「遅延を設定しました（解除は、ページの再読み込み）」と表示されればよい（Chromeが貼り付けの警告を出した場合は、案内に従って `allow pasting` と入力してEnterを押してから、もう一度貼り付ける）。**確認のためだけのもので、アプリのファイルには入れない。**

```javascript
// Task 010の確認用。休講日のAPIへの要求を、送る前に2秒待たせる（内容は変えない）。
// ページを再読み込みすると、消える。
(() => {
  if (window.closureDelay !== undefined) {
    console.log("遅延は、すでに設定されています");
    return;
  }
  const realFetch = window.fetch.bind(window);
  window.fetch = async (url, options) => {
    if (String(url).startsWith("/api/closures")) {
      await new Promise((resolve) => {
        setTimeout(resolve, 2000);
      });
    }
    return realFetch(url, options);
  };
  window.closureDelay = true;
  console.log("遅延を設定しました（解除は、ページの再読み込み）");
})();
```

| No | 操作（「2026年度 後期」を選んだ状態から） | 期待する結果 |
|---|---|---|
| D1 | 日付 2026-12-10 で「追加する」を押す | 約2秒、ボタンが「追加中…」で押せない。そのあと、ボタンが「追加する」に戻り、入力欄が空になる。さらに約2秒後（一覧の取得も遅れるため）に、一覧に「2026年12月10日（木）」が出る |
| D2 | その行の「削除」を押す | その行のボタンが「削除中…」で押せなくなる。約4秒後（削除と、一覧の取得が、それぞれ2秒遅れるため）に、行が消える |
| D3 | 日付 2026-12-11、名前「途中」で「追加する」を押し、2秒以内に「前期」のタブを押す | すぐに前期の欄に切り替わる（「読み込み中…」のあと、前期の一覧）。入力欄は空で、ボタンは「追加する」。2秒たっても、前期の画面に、メッセージ・エラー・入力欄の変化が出ない |
| D4 | 「後期」のタブに戻る | 「読み込み中…」のあと、一覧に「2026年12月11日（金） 途中」がある（追加は、サーバーでは行われている） |
| D5 | ページを再読み込みする | 遅延が消える（コンソールで `typeof closureDelay` を実行すると `"undefined"`） |

#### S. 授業の回帰

| No | 操作 | 期待する結果 |
|---|---|---|
| S1 | 「後期」で「授業を追加」を押し、科目名「テスト：月曜1限」で登録して、モーダルを閉じる | これまでどおり、授業の一覧に出る。休講日の欄は変わらない |

#### 後片付け
1. 確認用のサーバーを止める（Ctrl＋C）
2. 確認用のDBのフォルダを消す
   ```
   rm -r /tmp/schedule-app-check-010
   ```
3. 開発用DBのハッシュが、準備の1と同じことを確かめる
   ```
   shasum -a 256 instance/app.db
   ```

ハッシュが変わっていた場合は、開発用DBを操作せずに、Claudeに伝える。

### 4. 開発用DBでの、読み取りだけの確認
3が期待どおりなら、開発用DBで起動して、画面が開くことだけを確かめる（追加・削除はしない）。

```
shasum -a 256 instance/app.db          # 控える
python run.py                          # 開発用DBで起動（別のターミナルで、次を実行）
curl -s -w '\nHTTP %{http_code}\n' http://127.0.0.1:5001/api/closures
# 画面の確認のあと、サーバーを Ctrl+C で止めてから
shasum -a 256 instance/app.db          # 起動の前と同じ
```

| 確認 | 期待 |
|---|---|
| Chromeで開き、強制再読み込みして、「授業」を押す | 学期が0件のため、空状態（「学期がまだ登録されていません…」）だけ。休講日の欄は出ない。コンソールに、赤いエラーがない（学期を登録していた場合は、休講日の欄が出て、その学期の休講日が表示される） |
| `curl` | `[]`、HTTP 200（休講日を登録していた場合は、その一覧） |
| 最後のハッシュ | 起動の前と同じ |

### 5. マージ
1〜4が期待どおりで、レビューで承認されたら、マージする。このタスクは、DBの構造を変えないため、開発用DBへの適用はない。

## Git操作
**Git commit / push / ブランチ操作 / マージは行わない**（`git branch --show-current`、`git status`、`git diff` のような読み取りだけのコマンドは除く）。

## 注意
- **停止して報告する条件**（ファイルを変更せず、実装を止め、チャットで「問題点・発生理由・変更した場合の影響・推奨案（必要なら）」を報告する）
  - ブランチの不一致、作業ツリーの想定外の変更
  - 設計資料が更新されていない（実装手順の1）、または、設計資料とこのTask MDの間に、矛盾・不足がある
  - 設計資料にない判断が必要になった（特に、`docs/architecture.md` の「未決定事項」や、`docs/ui_ux.md` の「未決定」に触れる場合）
  - 「変更しない」と定めたもの（Pythonのファイル、`api.js`・`ui.js`・`subjects.js`、`base.html`、`index.html` の休講日の欄以外の部分など）を変更しないと実装できない。または、2-1・3-1〜3-3のコードを変える必要があると判断した
  - 開発用DB（`instance/app.db`）がない
  - 作業の前の `python -m pytest` が、394件すべて合格しない
  - **既存のテスト**（作業の開始時からあるテスト）**が、想定外に失敗した**。テストの期待値や、ほかの仕様を直さずに、原因を調べて報告する
  - APIの変更や、DBの構造の変更（migration）が必要だと判断した
  - 実施の前後で、`instance/app.db` が変わった
- **止まるときは、報告を書いて、その応答を終える。質問の機能は使わない。** 再開するのは、Komaの新しいメッセージが、判断や再開を明確に示したときだけ（無回答や「続けて」だけの返事は、再開の指示ではない）。`.github/copilot-instructions.md` の「止まる場面の応答」
- `flask db` のコマンドを、一切実行しない。ライブラリを追加しない。サーバーを起動しない（`python run.py` も、「Komaの確認」の確認用のサーバーも）
- 期待する結果と異なる結果が出た場合は、確認を飛ばさず、原因を直してから、すべての確認をやり直す（ただし、既存のテストの想定外の失敗は、上の停止の条件に従う）
- 設計資料に書かれていない仕様は、自分で決めない
- 最後の報告に、次を含める：変更したファイル、各段階の `pytest` の件数と警告、1行の長さの確認の結果、検索の結果、画面のHTMLの確認の出力、開発用DBの前後のハッシュ・件数、`git status`・`git diff --stat`、ブラウザで確認していないこと、気になった点
