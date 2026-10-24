# タスク008: 学期登録モーダルの不具合（P1）の修正と、Task 007のLowの整理

| 項目 | 内容 |
|---|---|
| Task ID | 008 |
| Task名 | 学期登録モーダルの不具合（P1）の修正と、Task 007のLowの整理 |
| ブランチ | `feature/008-semester-modal-fix`（Komaが作成・切替済みの状態で渡される） |

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに停止して報告する。

## 目的
学期の登録モーダルで、開いた直後（表示のアニメーションの途中）に登録が成功すると、モーダルが閉じず、「登録する」ボタンが「登録中…」のまま無効で残る不具合（P1）を直す。あわせて、Task 007のレビューで持ち越した軽微な指摘（007-L1・007-L2）を直す。次の2段階で、この順に行う。

| 段階 | 内容 | 挙動の変化 | 段階の終わりの `pytest` |
|---|---|---|---|
| 1 | 007-L1（docstring）と007-L2（テストの確認を1行足す） | なし | **273件**（変わらない） |
| 2 | P1の修正（`app/static/js/semesters.js`） | 表示のアニメーションの途中で登録が成功しても、表示が終わってから閉じる。それ以外の操作は変わらない | **273件**（JavaScriptの自動テストはない） |

## 前提（Task 007完了時点の状態）

| 区分 | 内容 |
|---|---|
| すでにある | 学期API（`GET`・`POST /api/semesters`）、授業API（`GET`・`POST /api/subjects`）、学期UI・授業UI、pytest（**273件**。`main` の `2973be9` で確認） |
| 今の挙動（このタスクで直す） | 学期の登録モーダルを開いてすぐに登録し、表示のアニメーション（0.5秒ほど）が終わる前に成功の応答が届くと、モーダルが閉じない。成功の経路ではボタンを元に戻さないため、ボタンも「登録中…」のまま無効になる。学期は登録され、一覧は取得し直される。通常の操作（日付を入力してから登録）では起きにくい |
| 原因 | `semesters.js` の `submitSemester` は、成功すると、すぐに `hide()` を呼ぶ（`main` の269〜270行）。Bootstrap 5.3.8 のモーダルは、開き始めてから表示が終わるまで（`show.bs.modal` から `shown.bs.modal` まで）の `hide()` を、何もせずに無視する |
| 授業のモーダル | 登録に成功しても閉じない仕様（`docs/ui_ux.md` の「授業」の「登録フォーム」）のため、P1は起きない。**変更しない** |
| 設計資料 | このタスクの前に、更新した `docs/architecture.md` が `main` に反映されている。「JavaScriptの構成（ES modules）」の規則に、JavaScriptからモーダルを閉じるときの規則（表示のアニメーションの途中でも閉じられるようにする）があり、「未決定事項」に「モーダルを閉じる処理の共通化」がある |
| DBの構造 | 変えない。**migrationは不要** |
| 開発用DB | `instance/app.db` には、実際の学期・授業が入っている。**このタスクで、書き込まない。** Copilotが行うのは、「Copilot確認手順」の1・6の読み取り（ハッシュ・件数）だけ。**Copilotは、サーバーを起動しない（`python run.py` を実行しない）** |
| JavaScriptの確認 | JavaScriptの自動テストはない（pytestはAPIだけが対象）。Copilotはブラウザを使えないため、JavaScriptの動作は、Komaがブラウザで確かめる（「Komaの確認」）。Copilotは、コードの検索と差分で確かめる |
| 設計資料のほうが先の部分 | 設計資料には、予定（Event）の自動生成、`generated_event_count`、休講日が書かれているが、**このタスクでは実装しない**（後のタスク）。今のコードとテストが、これらを持たないことは、矛盾として扱わない |

## Source of Truth
- `docs/architecture.md`：「JavaScriptの構成（ES modules）」（特に、モーダルの2つの規則：インスタンスは `getOrCreateInstance` で取得する、JavaScriptから閉じるときは表示のアニメーションの途中でも閉じられるようにする）、「未決定事項」の「モーダルを閉じる処理の共通化」、「API共通ルール」の「文字列の項目の検査の順序」（007-L1）、「自動テスト（pytest）」
- `docs/ui_ux.md`：「学期（タブと登録）」の「登録フォーム」と「登録後」
- `docs/tasks/007_api_input_validation.md`：段階2のT7（007-L2の対象のテスト）、段階3（使用できない文字の検査の順序。007-L1）
- `.github/copilot-instructions.md`：進め方、コーディング方針（特にJavaScript）、「テスト」

## 実装対象ファイル

| 区分 | ファイル | 段階 | 内容 |
|---|---|---|---|
| 変更 | `app/api_helpers.py` | 1 | 007-L1：3つの検証関数の**docstringだけ** |
| 変更 | `tests/test_subjects_api.py` | 1 | 007-L2：1行の追加だけ |
| 変更 | `app/static/js/semesters.js` | 2 | P1の修正（J1〜J4） |

上の3ファイル以外は、変更しない。

## 非対象（このタスクでは作らない・変更しない）
- `app/static/js/` のほかのファイル（`ui.js`・`api.js`・`subjects.js`・`main.js`）。**`ui.js` に、モーダルを閉じる共通の関数を作らない**（未決定事項「モーダルを閉じる処理の共通化」。2つ目のモジュールで必要になったときに決める）
- `app/templates/`（HTML）。モーダルの `fade`（アニメーション）を外さない
- `app/api_helpers.py` の処理（docstring以外の行は変えない）、`app/routes/`、`app/models/`、`app/__init__.py`、`app/config.py`、`app/extensions.py`、`run.py`
- `migrations/`（**新しいmigrationを作らない。`flask db` のコマンドを、一切実行しない**）
- `docs/`、`.github/`、`.gitignore`、`pytest.ini`、`requirements.txt`（**ライブラリを追加しない**）、`tests/` のほかのファイル
- 学期の登録モーダルの、P1以外の挙動：送信中・失敗時のボタンの表示、失敗の経路（`catch` の中）、フォームの初期値（`resetForm`）、成功したあとの一覧の取得し直し（`loadSemesters(created.id)`）。成功の経路で、ボタンを「登録する」に戻す処理は足さない（次に開くときに、`resetForm` で戻る。`ui_ux.md` のとおり）
- Task 003で持ち越した項目（003-H）、Task 006のLow（006-L1・L2）、休講日、予定（Event）の自動生成

## 段階1：Task 007のLow（Python。挙動を変えない）

### 1-1. 007-L1：`app/api_helpers.py` の3つの検証関数のdocstring
使用できない文字の検査（Task 007の段階3で入れた）が、docstringに書かれていないため、書き足す。**処理は変えない。** 行番号は、`main`（このタスクを始める時点）のもの。

| 関数 | 今のdocstring（`main` の行） |
|---|---|
| `validate_required_string` | 127行 `"""必須文字列を検査し、値またはエラーメッセージを返す。"""` |
| `validate_optional_string` | 155行 `"""任意文字列を検査して正規化し、値またはエラーを返す。"""` |
| `validate_required_time` | 224行 `"""必須時刻を検査し、Pythonのtimeかエラーメッセージを返す。"""` |

それぞれを、次のとおりにする（1行目は今のまま。1行は79文字以内）：

```python
def validate_required_string(...):
    """必須文字列を検査し、値またはエラーメッセージを返す。

    使用できない文字（孤立サロゲート）を含む場合は、
    UNUSABLE_CHARACTER_MESSAGEを返す。この検査は、引数の指定に関係なく、
    型の検査のあと、前後の空白の除去と長さの検査より前に、常に行う。
    """

def validate_optional_string(...):
    """任意文字列を検査して正規化し、値またはエラーを返す。

    使用できない文字（孤立サロゲート）を含む場合は、
    UNUSABLE_CHARACTER_MESSAGEを返す。この検査は、引数の指定に関係なく、
    型の検査のあと、前後の空白の除去と長さの検査より前に、常に行う。
    """

def validate_required_time(...):
    """必須時刻を検査し、Pythonのtimeかエラーメッセージを返す。

    使用できない文字（孤立サロゲート）を含む場合は、
    UNUSABLE_CHARACTER_MESSAGEを返す。この検査は、型の検査のあと、
    形式の検査より前に、常に行う。
    """
```

（`def` の行の `...` は、省略を表す。引数は変えない）

### 1-2. 007-L2：`tests/test_subjects_api.py` の `test_unsupported_subject_methods_do_not_change_rows`
要求の前の `GET` が失敗しても（例：準備で作った授業が見つからない）、前と後の応答が同じなら合格してしまうため、最初の `GET` が200であることを確かめる。`main` の705行（`before_subject = client.get(...)`）の直後に、次の1行を足す。ほかの行は変えない。

```python
    before_subject = client.get(f"/api/subjects/{subject_id}")
    assert before_subject.status_code == 200
```

段階1の終わりに、`python -m pytest -q` が **273件、すべて合格**すること（件数は変わらない）。79文字を超える行がないこと（「Copilot確認手順」の3）。

## 段階2：P1の修正（`app/static/js/semesters.js`）

### 2-1. 変更内容
行番号は、`main`（このタスクを始める時点）のもの。

| 番号 | 場所 | 変更 |
|---|---|---|
| J1 | 11〜12行（`let semesters`・`let selectedId`）の直後 | 変数 `semesterModalShowing`（初期値 `false`）を足す。「学期の登録モーダルが、表示のアニメーションの途中か」を表す。理由のコメントを付ける |
| J2 | `submitSemester`（250行）の直前 | 関数 `closeSemesterModal()` を足す。表示の途中でなければ、すぐに `hide()` する。表示の途中なら、`shown.bs.modal` のときに `hide()` するリスナーを、`{ once: true }` で付ける |
| J3 | `submitSemester` の成功の経路（269〜270行の2行） | `closeSemesterModal();` の1行に置き換える。次の行の `await loadSemesters(created.id);` は、そのまま |
| J4 | `initSemesters`（278行）の、`show.bs.modal` に `resetForm` を登録している行（282行） | 学期のモーダルに、`show.bs.modal` で `semesterModalShowing` を `true` に、`shown.bs.modal` で `false` にするリスナーを足す。`show.bs.modal` に `resetForm` を登録することは、そのまま残す |

### 2-2. 守ること
- `semesterModalShowing` を変えるのは、J4の2つのリスナー（`show.bs.modal` で `true`、`shown.bs.modal` で `false`）**だけ**。`hide.bs.modal`・`hidden.bs.modal` では変えない（Bootstrapは表示の途中の `hide()` を受け付けないため、閉じ始めるのは、必ず表示が終わったあと＝`false` のときになる）
- `shown.bs.modal` を待つリスナーは、**表示の途中のときだけ**付け、`{ once: true }` にする。表示の途中なら、そのあと必ず `shown.bs.modal` が起きるため、リスナーは1回で外れて残らない。表示が終わっているときに付けると、リスナーが残り、次に開いたときに、すぐに閉じてしまう
- Bootstrapの内部の値（`_isTransitioning`・`_isShown` など、`_` で始まるもの）を使わない（公開されていないため）。`setTimeout` で時間を待つ方式にしない（アニメーションの長さに依存するため）
- モーダルのインスタンスは、これまでどおり `window.bootstrap.Modal.getOrCreateInstance(...)` で取得する
- 名前は、`semesterModalShowing` と `closeSemesterModal` にする（「Copilot確認手順」の検索で使う）
- 書き方は、`.github/copilot-instructions.md` のJavaScriptの規則と、今の `semesters.js` に合わせる（`const`／`let`、セミコロン、空白2つのインデント、二重引用符、`===`、複数行の引数の末尾のカンマ、日本語のコメント）

### 2-3. 書き方の例
同じ意味なら、コメントの文言は多少違ってよい（差分の形で示す。`-` は消す行、`+` は足す行）。

```diff
 let semesters = [];
 let selectedId = null;
+// 学期の登録モーダルが、表示のアニメーションの途中か。Bootstrapは、
+// 表示の途中のhide()を無視するため、閉じるときに確かめる。
+let semesterModalShowing = false;
```

```diff
+function closeSemesterModal() {
+  const modal = getElement("semester-modal");
+  const instance = window.bootstrap.Modal.getOrCreateInstance(modal);
+  if (semesterModalShowing) {
+    // 表示の途中なら、表示が終わったとき（shown.bs.modal）に閉じる。
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
+
 async function submitSemester(event) {
```

```diff
       start_date: startDate,
       end_date: endDate,
     });
-    const modal = getElement("semester-modal");
-    window.bootstrap.Modal.getOrCreateInstance(modal).hide();
+    closeSemesterModal();
     await loadSemesters(created.id);
```

```diff
   getElement("semester-retry-button").addEventListener("click", () => {
     loadSemesters();
   });
-  getElement("semester-modal").addEventListener("show.bs.modal", resetForm);
+  const modal = getElement("semester-modal");
+  modal.addEventListener("show.bs.modal", () => {
+    semesterModalShowing = true;
+  });
+  modal.addEventListener("shown.bs.modal", () => {
+    semesterModalShowing = false;
+  });
+  modal.addEventListener("show.bs.modal", resetForm);
   getElement("semester-form").addEventListener("submit", submitSemester);
```

### 2-4. 変わる挙動・変わらない挙動

| 操作 | 今 | 変更後 |
|---|---|---|
| 開いて、表示のアニメーションの途中で、登録が成功する | 閉じない。ボタンが「登録中…」のまま無効 | 表示が終わると、続けて閉じる |
| 表示が終わってから、登録が成功する（通常の操作） | 閉じる | 同じ |
| 成功のあとの、学期の一覧の取得し直しと、登録した学期の選択 | あり | 同じ（閉じるのを待たずに始まる） |
| 登録が失敗する | 開いたまま。エラーを表示し、ボタンが「登録する」に戻る | 同じ |
| 閉じたあと、もう一度開く | 初期値に戻る | 同じ（開いたまま残り、すぐには閉じない） |
| 「キャンセル」・「×」で閉じる | 閉じる | 同じ |

## 変更してよい既存のテスト

| ファイル | 変更してよいもの | それ以外 |
|---|---|---|
| `tests/test_subjects_api.py` | `test_unsupported_subject_methods_do_not_change_rows` に、1-2の1行を足すことだけ | 変えない |
| ほかの `tests/` のファイル | なし | 変えない |

- 新しいテストは足さない（件数は273のまま）。テストの期待値（状態コード・`code`・メッセージ・件数の確認）は変えない
- このタスクでの「既存のテスト」は、作業の開始時からあるすべてのテスト（1-2で1行足すテストを含む）。**既存のテストが想定外に失敗した場合**は、テストの期待値やほかの仕様を直さない。原因を調べ、そこで実装を止めて、チャットで報告する（「注意」の停止の条件）

## 実装手順
1. ブランチ・作業ツリーの確認。`docs/architecture.md` に「表示のアニメーションの途中でも閉じられるようにする」と、未決定事項「モーダルを閉じる処理の共通化」が書かれていることを確認する。書かれていなければ、何も変更せずに停止して報告する
2. 作業の前の状態を記録する：開発用DBのハッシュと件数（「Copilot確認手順」の1）。`python -m pytest -q` が273件、すべて合格すること（合格しなければ、何も変更せずに停止して報告する）
3. **（段階1）** 1-1・1-2。`python -m pytest -q` が273件、すべて合格すること。79文字を超える行がないこと
4. **（段階2）** J1〜J4。`python -m pytest -q` が273件、すべて合格すること
5. 「Copilot確認手順」を実施する
6. 結果を報告して止まる

## 完了条件
- `python -m pytest -q` が、**273件、すべて合格**する（失敗・エラー・スキップが0件）。件数が273でない場合は、理由を報告する
- 変更したファイルが、「実装対象ファイル」の3つだけ
- `app/api_helpers.py` の差分が、3つのdocstringだけ。`tests/test_subjects_api.py` の差分が、1-2の1行だけ
- `semesters.js` の変更が、J1〜J4と「2-2. 守ること」のとおり（「Copilot確認手順」の4・5）
- `app/`・`tests/`・`run.py` に、79文字を超える行がない（Pythonのファイル）
- 実行の前後で、開発用DB（`instance/app.db`）のハッシュが同じで、`semesters`・`subjects` の件数も同じ
- 「Komaの確認」が、期待どおり（修正前の再現B1・B2と、修正後のA1〜A6）
- レビューで承認される

## Copilot確認手順
```
# 1. 実施前
git branch --show-current      # feature/008-semester-modal-fix
git status                     # 変更なし
shasum -a 256 instance/app.db
sqlite3 instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects;"
python -m pytest -q            # 273 passed

# 2. 各段階の終わり
python -m pytest -q            # 段階1・段階2とも 273 passed

# 3. 1行の長さ（段階1・段階2の終わり。出力がなければ合格）
python - <<'EOF'
from pathlib import Path
paths = [*Path("app").rglob("*.py"), *Path("tests").glob("*.py"), Path("run.py")]
for path in paths:
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, 1):
        if len(line) > 79:
            print(f"{path}:{number}: {len(line)}")
EOF

# 4. 検索（段階2の終わり）
grep -nF "semesterModalShowing" app/static/js/semesters.js   # 4件：宣言、closeSemesterModalのif、trueにする、falseにする
grep -nF "closeSemesterModal" app/static/js/semesters.js     # 2件：定義と、submitSemesterでの呼び出し
grep -nF '"shown.bs.modal"' app/static/js/semesters.js       # 2件：closeSemesterModalの中と、initSemestersの中
grep -nF '"show.bs.modal"' app/static/js/semesters.js        # 2件：どちらもinitSemestersの中（trueにする、resetForm）
grep -nF "once: true" app/static/js/semesters.js             # 1件：closeSemesterModalの中
grep -nF "instance.hide()" app/static/js/semesters.js        # 2件：どちらもcloseSemesterModalの中
grep -nF "getOrCreateInstance" app/static/js/semesters.js    # 1件：closeSemesterModalの中
grep -rnE "_isTransitioning|_isShown|setTimeout" app/static/js/   # 出力なし

# 5. 差分（段階2の終わり）
git diff app/api_helpers.py           # 3つのdocstringだけ
git diff tests/test_subjects_api.py   # 1行の追加だけ
git diff app/static/js/semesters.js   # J1〜J4だけ

# 6. 実施後
shasum -a 256 instance/app.db  # 実施前と同じ
sqlite3 instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects;"   # 実施前と同じ
git status                     # 変更：「実装対象ファイル」の3つだけ。新規ファイルなし
git diff --stat
```

| 確認 | 期待する結果 |
|---|---|
| `python -m pytest -q` | 段階1・段階2とも、273件がすべて合格。失敗・エラー・スキップが0件。`migrations/env.py` の `DeprecationWarning` は、出ても構わない（報告する） |
| 1行の長さ | 出力なし |
| 検索 | 上のコメントのとおり（件数は、2-3の例のとおりに書いた場合。コメントの書き方などで件数が違う場合は、その行を報告に書く） |
| 開発用DB | 実施の前後で、ハッシュ・`semesters`・`subjects` の件数が同じ |
| `git status` | 変更：`app/api_helpers.py`、`tests/test_subjects_api.py`、`app/static/js/semesters.js` のみ。`app/templates/`・`app/static/js/` のほかのファイル・`app/routes/`・`migrations/`・`docs/`・`requirements.txt`・`instance/` に変更なし |

`.pytest_cache/` や `__pycache__/` が `git status` に表示される場合は、`.gitignore` を変更せず、報告する。**ブラウザでの確認は、Copilotは行わない（Komaが行う）。報告に、ブラウザで確認していないことを明記する。**

## Komaの確認
1. `python -m pytest -q` を自分で実行し、**273件、すべて合格**することを確認する
2. ブラウザで、修正前の再現（B）と、修正後の確認（A）を行う（下記）。**開発用DBに書き込まない方法で行う**

### ブラウザ確認の安全のしくみ
学期は、今のアプリでは削除できないため、確認で学期を登録しない。代わりに、確認用のスクリプトを、ブラウザの開発者ツールのコンソールに貼り、学期の登録の要求（`POST /api/semesters`）を、サーバーに送らずに、ブラウザの中で応答を返すようにする（応答の模擬）。

- スクリプトは、ページの中の `fetch`（サーバーへの要求）を差し替える。読み取り（`GET`）だけをサーバーに送る。`POST /api/semesters` は、サーバーに送らず、ブラウザの中で、成功（201）か失敗（400）の応答を返す。ほかの書き込みの要求（`POST`・`PATCH`・`DELETE` など）は、送らずに止める
- 登録の操作は、「登録する」ボタンを手で押さず、スクリプトの関数（`semesterCheck.openAndSubmit()`・`semesterCheck.submitNow()`）で行う。関数は、模擬が設定されていないと、送信せずにエラーで止まる
- 関数が入れる日付は、わざと開始日（2099-07-31）と終了日（2099-04-01）を逆にしてある。万一、模擬が効かずにサーバーへ届いても、400（「終了日は開始日より後にしてください」）で拒否され、DBに書き込まれない
- 成功の模擬の応答は、`id` が 999999（実在しない学期）。画面は、この `id` で学期の一覧を取得し直すが、一覧に無いため、今の選び方で学期が選ばれる。学期のタブは増えない
- 開発者ツールの「ネットワーク」で、`POST` の要求が1つも出ないことを確かめる（模擬した要求は、ネットワークに出ない）
- 終わったら、ページを再読み込みして、模擬を消す。確認の前後で、開発用DBのハッシュが同じことを確かめる

### 準備（B・Aのそれぞれで行う）
1. サーバーを起動する**前**に、開発用DBのハッシュと件数を控える
   ```
   shasum -a 256 instance/app.db
   sqlite3 instance/app.db "SELECT COUNT(*) FROM semesters;"
   ```
2. `python run.py` で起動し、Chromeで `http://127.0.0.1:5001/` を開く。JavaScriptを読み直すため、強制再読み込み（Cmd＋Shift＋R）をする。画面下の「授業」を押す
3. 開発者ツール（Cmd＋Option＋I）を開く。「ネットワーク」の絞り込みの欄に `method:POST` と入れておく（`POST` の要求だけが表示される。確認の間、何も表示されないのが正しい）
4. 「コンソール」に、下の「確認用スクリプト」を貼り付けて、Enterを押す。「模擬を設定しました（解除は、ページの再読み込み）」と表示されればよい（Chromeが貼り付けの警告を出した場合は、案内に従って `allow pasting` と入力してEnterを押してから、もう一度貼り付ける）

### 確認用スクリプト
**確認のためだけのもので、アプリのファイルには入れない。** ページを再読み込みすると、消える。

```javascript
// Task 008の確認用。学期の登録（POST）をサーバーに送らず、ブラウザの中で
// 応答を返す（開発用DBに書き込まない）。ページを再読み込みすると、消える。
(() => {
  if (window.semesterCheck !== undefined) {
    console.log("模擬は、すでに設定されています");
    return;
  }

  const realFetch = window.fetch.bind(window);
  const check = { mode: "success", mockedCount: 0 };

  function jsonResponse(status, body) {
    return new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  }

  function mockFetch(url, options = {}) {
    const method = (options.method ?? "GET").toUpperCase();
    if (method === "GET") {
      // 一覧の取得（読み取り）だけは、サーバーに送る。
      return realFetch(url, options);
    }
    if (method === "POST" && url === "/api/semesters") {
      check.mockedCount += 1;
      if (check.mode === "error") {
        console.log("模擬：POST /api/semesters を送らず、400を返しました");
        return Promise.resolve(
          jsonResponse(400, {
            error: {
              code: "validation_error",
              message: "入力内容に誤りがあります",
              fields: { end_date: "終了日は開始日より後にしてください" },
            },
          }),
        );
      }
      console.log("模擬：POST /api/semesters を送らず、201を返しました");
      return Promise.resolve(
        jsonResponse(201, { id: 999999, ...JSON.parse(options.body) }),
      );
    }
    // ほかの書き込み（POST・PATCH・DELETEなど）は、送らずに止める。
    console.warn(`模擬：${method} ${url} を、送らずに止めました`);
    return Promise.reject(new TypeError("確認中のため、送信しません"));
  }

  function assertMocked() {
    if (window.fetch !== mockFetch) {
      throw new Error("模擬が設定されていないため、送信しません");
    }
  }

  function submitForm() {
    assertMocked();
    // 開始日と終了日を、わざと逆にする。万一、模擬が効かずにサーバーへ
    // 送られても、400で拒否され、開発用DBに書き込まれないようにするため。
    document.getElementById("semester-year").value = "2099";
    document.getElementById("semester-term").value = "前期";
    document.getElementById("semester-start-date").value = "2099-07-31";
    document.getElementById("semester-end-date").value = "2099-04-01";
    document.getElementById("semester-form").requestSubmit();
  }

  // モーダルを開き、表示のアニメーションの途中で、すぐに登録する（P1の操作）。
  check.openAndSubmit = () => {
    const modal = document.getElementById("semester-modal");
    if (modal.classList.contains("show")) {
      throw new Error("モーダルを閉じてから、実行してください");
    }
    assertMocked();
    window.bootstrap.Modal.getOrCreateInstance(modal).show();
    // show()の中でフォームが初期値に戻るため、そのあとに入力して送信する。
    submitForm();
  };

  // 開いてあるモーダルで、登録する（表示が終わってからの、通常の操作）。
  check.submitNow = () => {
    const modal = document.getElementById("semester-modal");
    if (!modal.classList.contains("show")) {
      throw new Error("先に、学期の登録のモーダルを開いてください");
    }
    submitForm();
  };

  window.fetch = mockFetch;
  window.semesterCheck = check;
  console.log("模擬を設定しました（解除は、ページの再読み込み）");
})();
```

モーダルを「開く」操作は、画面に表示されているボタン（「新しい学期を登録する」、バナーの「登録する」、学期が0件のときの「最初の学期を登録する」のどれか）で行う。

### 修正前の再現（B）
**行う時機：ブランチを作った直後、Copilotに渡す前**（コードが `main` と同じ時点）。修正前に、この方法でP1が再現することを確かめておく（再現しない方法では、修正後の確認が意味を持たないため）。

| No | 操作（コンソール） | 期待する結果 |
|---|---|---|
| B1 | `semesterCheck.openAndSubmit()` を実行し、2秒待つ | **モーダルが開いたまま残る。** ボタンは「登録中…」で押せない。コンソールに「模擬：POST /api/semesters を送らず、201を返しました」。ネットワーク（`method:POST`）に何も出ない（P1の再現） |
| B2 | 「キャンセル」で閉じる。ボタンで開き、1秒以上待ってから、`semesterCheck.submitNow()` を実行する | モーダルが閉じる（表示が終わってからの登録なら、今のコードでも閉じる。B1との違いが「開いた直後かどうか」だけであることを確かめる） |

B1でモーダルが閉じた（再現しない）場合は、Copilotに渡す前に、Claudeに伝える。終わったら、「後片付け」を行う。

### 修正後の確認（A）
**行う時機：Copilotの完了報告のあと。** 「準備」を最初からやり直す（強制再読み込みで、新しいJavaScriptを読み込み、スクリプトを貼り直す）。

| No | 操作 | 期待する結果 |
|---|---|---|
| A1 | `semesterCheck.openAndSubmit()` を実行し、2秒待つ | モーダルが開き、表示が終わると、続けて閉じる。コンソールに「…201を返しました」。ネットワーク（`method:POST`）に何も出ない |
| A2 | ボタンで開き、1秒以上待つ | 開いたまま残る（すぐに閉じない）。年度・種別が初期値、開始日・終了日が空欄、ボタンは「登録する」で押せる |
| A3 | そのまま、`semesterCheck.submitNow()` を実行する | モーダルが閉じる（通常の操作） |
| A4 | ボタンで開き、1秒以上待つ。`semesterCheck.mode = "error"` を実行してから、`semesterCheck.submitNow()` を実行する | モーダルは閉じない。終了日の下に「終了日は開始日より後にしてください」。ボタンが「登録する」に戻る。コンソールに「…400を返しました」 |
| A5 | 「キャンセル」で閉じる。`semesterCheck.mode = "success"` を実行してから、`semesterCheck.openAndSubmit()` を、もう一度実行し、2秒待つ | A1と同じく、閉じる（2回目も閉じる） |
| A6 | 確認の全体を通して | コンソールに、赤いエラーが出ていない（スクリプトの関数が、自分で止めたエラーを除く）。学期のタブの数が、確認の前と同じ。`semesterCheck.mockedCount` を実行すると `4`（模擬した登録の回数） |

### 後片付け（B・Aのそれぞれのあと）
1. 強制再読み込み（Cmd＋Shift＋R）をする。コンソールで `typeof semesterCheck` を実行し、`"undefined"` と表示されることを確かめる（模擬が消えた）
2. サーバーを止めてから、開発用DBのハッシュと件数が、「準備」の1と同じことを確かめる
   ```
   shasum -a 256 instance/app.db
   sqlite3 instance/app.db "SELECT COUNT(*) FROM semesters;"
   ```

ハッシュや件数が変わっていた場合は、開発用DBを操作せずに、Claudeに伝える。

## Git操作
**Git commit / push / ブランチ操作 / マージは行わない**（`git branch --show-current`、`git status`、`git diff` のような読み取りだけのコマンドは除く）。

## 注意
- **停止して報告する条件**（ファイルを変更せず、実装を止め、チャットで「問題点・発生理由・変更した場合の影響・推奨案（必要なら）」を報告する）
  - ブランチの不一致、作業ツリーの想定外の変更
  - 設計資料が更新されていない（実装手順の1）、または、設計資料とこのTask MDの間に、矛盾・不足がある
  - 設計資料にない判断が必要になった（特に、`ui.js` に共通の関数を作る必要があると判断した場合。未決定事項「モーダルを閉じる処理の共通化」に当たる）
  - 「変更しない」と定めたもの（HTML、`semesters.js` 以外のJavaScript、`app/routes/`、`migrations/`、`requirements.txt` など）を変更しないと実装できない
  - 作業の前の `python -m pytest` が、273件すべて合格しない
  - 既存のテストが、想定外に失敗した。テストの期待値や、ほかの仕様を直さずに、原因を調べて報告する
  - DBの構造の変更（migration）が必要だと判断した。作らず・適用せずに報告し、承認を待つ
  - 実施の前後で、`instance/app.db` が変わった
- `flask db` コマンドを、一切実行しない。ライブラリを追加しない。サーバーを起動しない（`python run.py` を実行しない）
- 期待する結果と異なる結果が出た場合は、確認を飛ばさず、原因を直してから、すべての確認をやり直す（ただし、既存のテストの想定外の失敗は、上の停止の条件に従う）
- 設計資料に書かれていない仕様は、自分で決めない
- 途中の承認ゲートはない。「Copilot確認手順」を実施したら、結果を報告して止まる
- 最後の報告に、次を含める：変更したファイル、各段階の `pytest` の件数と警告、1行の長さの確認の結果、検索の結果、開発用DBの前後のハッシュと件数、`git status`・`git diff --stat`、ブラウザで確認していないこと、気になった点
