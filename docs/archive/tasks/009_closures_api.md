# タスク009: 休講日のデータとAPI（モデル・migration・一覧・登録・削除）

| 項目 | 内容 |
|---|---|
| Task ID | 009 |
| Task名 | 休講日のデータとAPI（モデル・migration・一覧・登録・削除） |
| ブランチ | `feature/009-closures-api`（Komaが作成・切替済みの状態で渡される） |

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに停止して報告する。

**このタスクには、承認ゲートが1か所ある（段階2の終わり）。** migrationを生成したら、「2-4. 承認ゲートの報告」をチャットで報告して止まり、Komaの承認を待つ。承認まで、`python -m pytest` を含め、何も実行しない。ほかの段階では、止まらずに進める。

## 目的
休講日（Closure）のモデルと、`closures` テーブルを作るmigrationを加え、休講日API（`GET /api/closures`・`POST /api/closures`・`DELETE /api/closures/<id>`）を実装する。あわせて、休講日APIが2つ目の利用者になる次の2つの処理を、先に `app/api_helpers.py` へ共通化し、学期API・授業APIの同じ処理を置き換える。
- 必須の日付の検証 `validate_required_date`（Task 003で持ち越した「学期APIの日付の検証の共通化」）
- 一覧の絞り込みのクエリ `semester_id` の読み取り `read_id_query`

**休講日と予定（Event）の同期は、このタスクでは入れない（Task 011で入れる）。** 休講日の登録・削除は、休講日の行だけを扱う（`docs/architecture.md` の「休講日の変更と予定の同期」の「最終的な仕様と、実装の途中の段階」の、休講日APIが先の場合）。

次の3段階で、この順に行う。

| 段階 | 内容 | APIの挙動の変化 | 段階の終わりの `pytest` |
|---|---|---|---|
| 1 | 共通化（`validate_required_date`・`read_id_query`）と、学期API・授業APIの置き換え、単体テスト | なし | **306件**（273＋33） |
| 2 | Closureのモデルと、migrationの生成。**生成したら、承認ゲートで止まる** | なし | モデルを変えたあと、migrationを生成する前に**306件**。生成のあとは、承認まで実行しない |
| 3 | （承認のあと）`closures` テーブルの確認のテストと、休講日API・そのテスト | 休講日APIが加わる | **394件**（306＋1＋87） |

## 前提（Task 008完了時点の状態）

| 区分 | 内容 |
|---|---|
| すでにある | 学期API（`GET`・`POST /api/semesters`）、授業API（`GET`・`POST /api/subjects`）、`app/api_helpers.py` の検証関数（`validate_required_string`・`validate_optional_string`・`validate_required_integer`・`validate_required_time`・`parse_date`・`format_date` など）、pytest（**273件**。`main` の `31310aa` で確認）、学期UI・授業UI |
| DBの構造 | 初期migration（`0280f6cf8d09`）だけ。`closures` テーブルはない。**このタスクで、migrationを1つ加える**（`closures` の作成だけ） |
| 設計資料 | このタスクの前に、更新した設計資料が `main` に反映されている。`docs/architecture.md` に「migrationの作成と適用」の節と、「API共通処理の補助モジュール」の `read_id_query`・`validate_required_date` がある。`.github/copilot-instructions.md` の「DBスキーマとmigration」に、承認ゲートの規則がある |
| 開発用DB | `instance/app.db` は、Komaの実際の開発用DB。**Copilotは、書き込まない。開発用DBに対して `flask db` のコマンドを実行しない。`run.py` も起動しない**（開発用DBには、まだ `closures` テーブルがなく、休講日APIは開発用DBでは動かないため。休講日APIの動作は、pytestで確かめる）。読むのは、「Copilot確認手順」のハッシュ・件数・テーブルの一覧だけ。開発用DBへのmigrationの適用は、Komaが、レビューの承認のあとに行う（「Komaの確認」） |
| 設計資料のほうが先の部分 | 設計資料には、休講日と予定の同期、予定（Event）の自動生成、`generated_event_count`、`app/class_events.py`、休講日の画面（`closures.js`）が書かれているが、**このタスクでは実装しない**（Task 010・011）。授業の登録で予定が作られないこと、休講日の登録・削除で予定が変わらないことは、矛盾として扱わない |
| 文言 | 休講日APIのエラーメッセージは、このMDの表のとおり（設計資料が定める「休講日は、学期の期間内の日付にしてください」「同じ日付の休講日がすでに登録されています」「休講日が見つかりません」と、授業APIと同じ `semester_id` の文言を含む）。学期API・授業APIの既存の文言は変えない |

## Source of Truth
- `docs/architecture.md`：「データ設計」の「Closure（休講日）」と「関係」、「休講日の変更と予定の同期」（特に「最終的な仕様と、実装の途中の段階」）、「DBスキーマ変更の方式」（特に「制約の命名規則」と「migrationの作成と適用」）、「API共通ルール」（「URLとメソッド」「リクエストとレスポンス（JSON）」「日付・時刻・日時」「エラー」「404の使い分け」）、「API共通処理の補助モジュール：`app/api_helpers.py`」、「休講日API」、「自動テスト（pytest）」
- `docs/tasks/003_api_foundation_and_semesters_api.md`：学期APIの仕様と、エラーメッセージの文言
- `docs/tasks/005_subjects_api_and_pytest.md`：授業APIの仕様と、エラーメッセージの文言
- `.github/copilot-instructions.md`：進め方、コーディング方針、「DBスキーマとmigration」、「テスト」

## 実装対象ファイル

| 区分 | ファイル | 段階 | 内容 |
|---|---|---|---|
| 変更 | `app/api_helpers.py` | 1 | `read_id_query`・`validate_required_date` を足す |
| 変更 | `app/routes/semesters.py` | 1 | 開始日・終了日の検証を、`validate_required_date` に置き換える |
| 変更 | `app/routes/subjects.py` | 1 | 一覧のクエリの読み取りを、`read_id_query` に置き換える |
| 変更 | `tests/test_api_helpers.py` | 1 | 2つの関数の単体テストを足す（33件） |
| 新規 | `app/models/closure.py` | 2 | Closureのモデル |
| 変更 | `app/models/__init__.py` | 2 | Closureの読み込み |
| 変更 | `app/models/semester.py` | 2 | `closures` の関係（`relationship`）を足す |
| 新規 | `migrations/versions/<revision>_add_closures_table.py` | 2 | 生成したmigration（**手で書かない・直さない**。`<revision>` は、生成のときに決まる英数字） |
| 新規 | `app/routes/closures.py` | 3 | 休講日API |
| 変更 | `app/__init__.py` | 3 | 休講日APIのBlueprintの登録 |
| 変更 | `tests/test_setup.py` | 3 | `closures` テーブルの確認（既存のテスト1件の変更と、1件の追加） |
| 新規 | `tests/test_closures_api.py` | 3 | 休講日APIのテスト（87件） |

上の12ファイル以外は、変更しない（`__pycache__/` などの、`.gitignore` の対象は除く）。

## 非対象（このタスクでは作らない・変更しない）
- 休講日と予定（Event）の同期、予定の自動生成、`generated_event_count`、`app/class_events.py`（Task 011）。**`routes/closures.py` は、予定（Event）を読まない・作らない・消さない**
- 休講日の画面（`app/templates/`・`app/static/`。`closures.js` を含む。Task 010）
- Task 003の持ち越しの残り（405の応答の `Allow` ヘッダー、`assert` の整理、`Semester.query` と `db.session.get` の書き方の統一）。`routes/semesters.py` の `assert` と `Semester.query` は、段階1で置き換える日付の部分を除いて、変えない
- 休講日の1件取得（`GET /api/closures/<id>`）と変更（`PATCH`）。設計資料のとおり、提供しない（405）
- 学期・授業の変更・削除、学期の削除時の休講日の扱い（未決定事項「学期の変更・削除時の扱い」）
- `routes/subjects.py` の `create_subject`（`semester_id` の検証を含む。変えない）
- `app/config.py`、`app/extensions.py`、`app/models/` のほかのモデル（`event.py`・`subject.py`・`task.py`）、`run.py`、`migrations/` の既存のファイル（`env.py`・`alembic.ini`・`script.py.mako`・`0280f6cf8d09_initial_tables.py` など）
- `docs/`、`.github/`、`.gitignore`、`pytest.ini`、`requirements.txt`（**ライブラリを追加しない**）、`tests/conftest.py`、`tests/test_semesters_api.py`、`tests/test_subjects_api.py`
- 開発用DB（`instance/app.db`）への書き込み、開発用DBに対する `flask db` のコマンド、`run.py` の起動

## 段階1：共通化（APIの挙動を変えない）
行番号は、`main`（このタスクを始める時点、`31310aa`）のもの。

### 1-1. `app/api_helpers.py`
**DBの操作を持たせない**（`db` を `import` しない）。既存の関数は変えない。

| 追加 | 置き場所 | 内容 |
|---|---|---|
| `read_id_query(name, multiple_message, format_message)` | `read_json_object`（83〜102行目）の直後 | 一覧の絞り込みのクエリ `name` から、IDを読み取る。戻り値は「指定の有無（`bool`）、ID（`int` か `None`）、エラーメッセージ（`str` か `None`）」の組 |
| `validate_required_date(payload, field, required_message, format_message)` | ファイルの最後（`format_date` の後） | 必須の日付を検査する。戻り値は「日付（`date` か `None`）、エラーメッセージ（`str` か `None`）」の組 |

`read_id_query` の戻り値（判定の順序は、今の `routes/subjects.py` の `get_subjects` と同じ）：

| 要求のクエリ（`request.args.getlist(name)`） | 戻り値 |
|---|---|
| 指定がない | `(False, None, None)` |
| 2回以上の指定 | `(True, None, multiple_message)` |
| 値が `[0-9]+` に全体一致しない（空文字・符号・小数・全角の数字・前後の空白など） | `(True, None, format_message)` |
| 数字だけだが、先頭の0を取り除くと空（`0`・`000`）、または `MAX_ID` より大きい | `(True, None, None)`（該当なし。呼び出し側は、空の一覧を返す） |
| それ以外 | `(True, ID, None)`（先頭の0は取り除く。例：`001` → `1`） |

- `MAX_ID` より大きいかは、`int()` に変換する前に、先頭の0を取り除いた文字列の桁数と値で判定する（今の `routes/subjects.py` の67〜74行目と同じ）。理由のコメント（`OverflowError`・`ValueError`）も移す
- DBを読まない（学期が存在するかは、確かめない）。日本語のdocstringに、上の表の5つの場合を書く

`validate_required_date` の検査の順序（`validate_required_time` と同じ形。最初に見つかった誤りを返す）：

| 順 | 条件 | 戻り値 |
|---|---|---|
| ① | キーがない・`None`・`""` | `(None, required_message)` |
| ② | 文字列でない | `(None, format_message)`（`validate_required_time` と同じく、型の誤りも形式のメッセージ） |
| ③ | 使用できない文字を含む（`contains_unusable_character`） | `(None, UNUSABLE_CHARACTER_MESSAGE)` |
| ④ | `parse_date(value)` が `None`（形式の誤り・実在しない日付） | `(None, format_message)` |
| ⑤ | それ以外 | `(日付, None)` |

- docstringに、②と、③の検査を「型の検査のあと、形式の検査より前に、常に行う」ことを書く（`validate_required_time` のdocstringと同じ内容）

書き方の例（同じ意味なら、文言は多少違ってよい。1行は79文字以内）：

```python
def read_id_query(
    name: str,
    multiple_message: str,
    format_message: str,
) -> tuple[bool, int | None, str | None]:
    """一覧の絞り込みのクエリで指定されたIDを読み取る。

    戻り値は、（指定の有無、ID、エラーメッセージ）の組。
    - 指定がない：(False, None, None)
    - 2回以上の指定：(True, None, multiple_message)
    - 数字だけでない（空文字・符号・小数・全角の数字・空白など）：
      (True, None, format_message)
    - 数字だけだが、1〜MAX_IDの外（0、MAX_IDより大きい数）：
      (True, None, None)。該当するデータがないため、呼び出し側は、
      DBに問い合わせずに、空の一覧を返す
    - それ以外：(True, ID, None)
    DBは読まない（IDのデータが存在するかは、確かめない）。
    """
    values = request.args.getlist(name)
    if not values:
        return False, None, None
    if len(values) > 1:
        return True, None, multiple_message

    text = values[0]
    if re.fullmatch(r"[0-9]+", text) is None:
        return True, None, format_message

    # MAX_IDより大きい数をDBに渡すとOverflowErrorになり、非常に長い
    # 数字の文字列をint()に渡すとValueErrorになるため、int()の前に、
    # 先頭の0を取り除いた桁数と値で、MAX_IDと比べる。
    normalized_text = text.lstrip("0")
    maximum_text = str(MAX_ID)
    if normalized_text == "" or len(normalized_text) > len(maximum_text):
        return True, None, None
    if (
        len(normalized_text) == len(maximum_text)
        and normalized_text > maximum_text
    ):
        return True, None, None
    return True, int(normalized_text), None


def validate_required_date(
    payload: dict[str, Any],
    field: str,
    required_message: str,
    format_message: str,
) -> tuple[date | None, str | None]:
    """必須の日付を検査し、Pythonのdateかエラーメッセージを返す。

    文字列でない値は、時刻と同じく、format_messageを返す。
    使用できない文字（孤立サロゲート）を含む場合は、
    UNUSABLE_CHARACTER_MESSAGEを返す。この検査は、型の検査のあと、
    形式の検査より前に、常に行う。
    """
    value = payload.get(field)
    if field not in payload or value is None or value == "":
        return None, required_message
    if not isinstance(value, str):
        return None, format_message
    if contains_unusable_character(value):
        return None, UNUSABLE_CHARACTER_MESSAGE

    parsed_value = parse_date(value)
    if parsed_value is None:
        return None, format_message
    return parsed_value, None
```

### 1-2. `app/routes/semesters.py`
- 81〜113行目（`start_date`・`end_date` の検証）を、`validate_required_date` を使う形に置き換える（下の例）。**メッセージの文言は変えない**
- 使わなくなる `import` を消す：2行目 `from datetime import date`、11行目 `parse_date`。`validate_required_date` を、`app.api_helpers` の `import` に足す（アルファベット順）
- 置き換える部分の中の `assert`（91・108行目）は、置き換えに伴って、なくなる。**それ以外の `assert`（59・72・136〜138行目）と、`Semester.query`（39・78行目）は、変えない**（Task 003の持ち越しの残り）
- 終了日と開始日の前後の確認（115〜120行目）は、変えない

書き方の例（81〜113行目を、次に置き換える）：

```python
    start_date_value, start_date_error = validate_required_date(
        payload,
        "start_date",
        "開始日は必須です",
        "開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください",
    )
    if start_date_error is not None:
        fields["start_date"] = start_date_error

    end_date_value, end_date_error = validate_required_date(
        payload,
        "end_date",
        "終了日は必須です",
        "終了日は実在する日付を「YYYY-MM-DD」の形式で指定してください",
    )
    if end_date_error is not None:
        fields["end_date"] = end_date_error
```

### 1-3. `app/routes/subjects.py`
- `get_subjects`（43〜84行目）のうち、クエリの読み取り（45〜76行目）を、`read_id_query` を使う形に置き換える（下の例）。メッセージの文言は変えない。並び（78〜84行目）は変えない
- 使わなくなる `import` を消す：1行目 `import re`、4行目の `request`。`read_id_query` を、`app.api_helpers` の `import` に足す（アルファベット順）
- `create_subject` は変えない

書き方の例（45〜76行目を、次に置き換える）：

```python
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
```

### 1-4. `tests/test_api_helpers.py`（単体テスト。DBを使わない。33件）
ファイルの最後に、次のテストを足す。既存のテストは変えない。`import` に、`date`（`from datetime import date, time`）、`Flask`（`from flask import Flask`）、`MAX_ID`・`read_id_query`・`validate_required_date` を足す。

| 番号 | テスト | 入力 | 期待 | 件数 |
|---|---|---|---|---|
| H1 | `test_validate_required_date_converts_value` | `"2026-04-01"`→`date(2026, 4, 1)`、`"2028-02-29"`→`date(2028, 2, 29)` | `(日付, None)` | 2 |
| H2 | `test_validate_required_date_reports_required` | `payload` を `{}`・`{"value": None}`・`{"value": ""}` | `(None, "必須")` | 3 |
| H3 | `test_validate_required_date_reports_non_string_as_format_error` | `20260401`・`True` | `(None, "形式")` | 2 |
| H4 | `test_validate_required_date_reports_format_error` | `"2026-4-1"`・`"2026/04/01"`・`"20260401"`・`"2026-02-30"`・`" 2026-04-01"`・`"2026-04-01 "`・`"２０２６-04-01"` | `(None, "形式")` | 7 |
| H5 | `test_validate_required_date_rejects_unusable_characters` | `"\ud800"`・`"2026-04-01\udc00"` | `(None, UNUSABLE_CHARACTER_MESSAGE)` | 2 |
| H6 | `test_read_id_query_without_value_is_not_specified` | クエリ `{}`・`{"foo": "bar"}` | `(False, None, None)` | 2 |
| H7 | `test_read_id_query_rejects_repeated_values` | クエリ `{"semester_id": ["1", "2"]}` | `(True, None, "複数")` | 1 |
| H8 | `test_read_id_query_rejects_non_digit_text` | `semester_id` が `""`・`"abc"`・`"-1"`・`"1.5"`・`"１"`・`" 1"`・`"1 "` | `(True, None, "形式")` | 7 |
| H9 | `test_read_id_query_out_of_range_matches_nothing` | `semester_id` が `"0"`・`"000"`・`str(MAX_ID + 1)`・`"9" * 5000` | `(True, None, None)` | 4 |
| H10 | `test_read_id_query_returns_id` | `"1"`→`1`、`"001"`→`1`、`str(MAX_ID)`→`MAX_ID` | `(True, ID, None)` | 3 |

- H1〜H5は、`validate_required_date({"value": 値}, "value", "必須", "形式")` を呼ぶ（H2は、`payload` をそのまま渡す）
- H6〜H10は、DBを使わない最小のFlaskアプリの、要求の中の状態で `read_id_query("semester_id", "複数", "形式")` を呼ぶ（下の補助関数の例）。「クエリ」は、`query_string` に渡す辞書（H8〜H10は `{"semester_id": 値}`）。`app` のfixtureは使わない（DBを作らないため）
- 孤立サロゲートは、ソースファイルに直接書かず、Pythonのエスケープ（`"\ud800"`）で書く
- パラメータが複数あるテストは、`pytest.mark.parametrize` で書く（件数は、表のとおりになる）

補助関数の例：

```python
def read_semester_id_query(query_string):
    # read_id_queryは、要求のクエリを読むため、DBを使わない最小の
    # Flaskアプリで、要求の中の状態を作って呼ぶ。
    request_app = Flask(__name__)
    with request_app.test_request_context(query_string=query_string):
        return read_id_query("semester_id", "複数", "形式")
```

段階1の終わりに、`python -m pytest -q` が **306件、すべて合格**すること。既存の273件は、期待値を変えずに合格すること（学期API・授業APIの挙動が変わっていないことの確認になる）。

## 段階2：Closureのモデルとmigrationの生成（最後に承認ゲート）

### 2-1. モデル
`docs/architecture.md` の「Closure（休講日）」と「関係」のとおり。`cascade` は指定しない。

```python
# app/models/closure.py（新規）
from app.extensions import db


class Closure(db.Model):
    __tablename__ = "closures"

    id = db.Column(db.Integer, primary_key=True)
    semester_id = db.Column(
        db.Integer, db.ForeignKey("semesters.id"), nullable=False
    )
    date = db.Column(db.Date, nullable=False)
    name = db.Column(db.String(100), nullable=True)

    semester = db.relationship("Semester", back_populates="closures")
```

- `app/models/semester.py`：12行目（`subjects = ...`）の次に、`closures = db.relationship("Closure", back_populates="semester")` を足す。ほかは変えない
- `app/models/__init__.py`：先頭に `from app.models.closure import Closure` を足し（`import` はアルファベット順）、`__all__` を `["Semester", "Subject", "Event", "Task", "Closure"]` にする

モデルを変えたら、**migrationを生成する前に**、`python -m pytest -q` が **306件、すべて合格**することを確かめる（まだmigrationがないため、テスト用DBに `closures` テーブルはないが、既存のテストは使わない）。

### 2-2. migrationの生成（一時的なDBと比べる）
リポジトリのルートで、`.venv` を有効にして、次を**1回だけ**実行する。既存のmigrationを適用した一時的なDB（一時ディレクトリの中。終わると消える）と、モデルを比べて、migrationファイルを生成する。**開発用DB（`instance/app.db`）は使わない**（`create_app` に一時的なDBのURIを渡すため）。スクリプトの中の `upgrade` は、一時的なDBに、既存のmigration（`0280f6cf8d09`）を適用するだけ。

```
python - <<'EOF'
import tempfile
from pathlib import Path

from flask_migrate import migrate, upgrade

from app import create_app
from app.extensions import db

with tempfile.TemporaryDirectory() as work_directory:
    database_path = Path(work_directory) / "migrate.db"
    app = create_app(
        {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}"}
    )
    with app.app_context():
        upgrade(directory="migrations")
        migrate(directory="migrations", message="add closures table")
        db.engine.dispose()
EOF
```

期待する出力（`INFO` の行のうち、主なもの。`<revision>` は、生成のときに決まる英数字）：

```
INFO  [alembic.runtime.migration] Running upgrade  -> 0280f6cf8d09, initial tables
INFO  [alembic.autogenerate.compare.tables] Detected added table 'closures'
Generating .../migrations/versions/<revision>_add_closures_table.py ...  done
```

- エラーになった場合、`Detected added table 'closures'` 以外の変更（`Detected removed ...`・`Detected type change ...` など）が出た場合、ファイルが生成されなかった場合（`No changes in schema detected.`）、2つ以上のファイルが生成された場合は、**ファイルを直さず、消さず、もう一度実行せずに**、止まって報告する
- 開発用DBに対して、`flask db migrate`・`flask db upgrade` などを実行しない（`.github/copilot-instructions.md` の「DBスキーマとmigration」）

### 2-3. 生成したファイルの確認（DBを使わない）
生成したファイルを読んで、次を確かめる。**ファイルは手で直さない**（自動生成のコメント `# ### commands auto generated by Alembic - please adjust! ###` も、そのまま残す。migrationファイルは、1行の長さの確認の対象外）。

| 確認 | 期待 |
|---|---|
| `migrations/versions/` に増えたファイル | `<revision>_add_closures_table.py` の1つだけ（`.py` のファイルは、既存の `0280f6cf8d09_initial_tables.py` と合わせて2つ） |
| `down_revision` | `'0280f6cf8d09'` |
| `upgrade()` | `op.create_table('closures', ...)` の1つだけ。列：`id`（`sa.Integer()`、`nullable=False`）、`semester_id`（`sa.Integer()`、`nullable=False`）、`date`（`sa.Date()`、`nullable=False`）、`name`（`sa.String(length=100)`、`nullable=True`）。制約：`sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], name=op.f('fk_closures_semester_id_semesters'))`、`sa.PrimaryKeyConstraint('id', name=op.f('pk_closures'))` |
| `upgrade()` のほかの操作 | ない。既存のテーブル（`semesters`・`subjects`・`events`・`tasks`）への操作（`drop_table`・`alter_column`・`batch_alter_table`・`create_index` など）がない |
| `downgrade()` | `op.drop_table('closures')` の1つだけ |
| `git status` | 変更：段階1の4ファイルと、`app/models/__init__.py`・`app/models/semester.py`。新規：`app/models/closure.py` と、生成したmigrationファイル |

期待と違う場合は、ファイルを直さず、消さずに、止まって報告する。

### 2-4. 承認ゲートの報告（ここで止まる）
次をチャットで報告して、**止まる**。Komaの承認の回答があるまで、`python -m pytest` を含め、何も実行しない（`pytest` は、テスト用の一時的なDBに、生成したmigrationを適用するため）。

1. 2-2のスクリプトの出力（全文）
2. 生成したファイル名、`revision`、`down_revision`
3. 生成したファイルの全文（`upgrade()` と `downgrade()` を含む。`cat` で表示したもの）
4. 作成・変更するテーブルと列の表（列の名前・型・NULL可否）と、制約の名前（主キー・外部キー）
5. 既存のテーブルへの変更の有無
6. `docs/architecture.md` の「Closure（休講日）」と「制約の命名規則」との差異の有無
7. 2-3の確認の結果
8. 生成したファイルのハッシュ（`shasum -a 256 migrations/versions/<revision>_add_closures_table.py`。承認のあとに変わっていないことを、最後に確かめるため）
9. 段階1の終わりと、2-1のあとの `python -m pytest -q` の結果（どちらも306件）
10. `git status`

### 2-5. Komaの確認（承認ゲート）
Copilotの報告を読み、次を確かめる。迷う点があれば、報告をClaudeに貼って相談する。

| 確認 | 期待 |
|---|---|
| ファイル | 1つだけで、名前が `<revision>_add_closures_table.py` |
| `down_revision` | `'0280f6cf8d09'`（初期migrationの次） |
| `upgrade()` | `op.create_table('closures', ...)` だけ。列は4つ（`id`・`semester_id`・`date`・`name`）で、型とNULL可否が、`docs/architecture.md` の「Closure（休講日）」のとおり。制約の名前が `pk_closures` と `fk_closures_semester_id_semesters` |
| 既存のテーブル | `upgrade()` に、既存のテーブルへの操作がない |
| `downgrade()` | `op.drop_table('closures')` だけ |

承認する場合は、「再開のプロンプト」（Task MDとは別に、Claudeが用意したもの）を、ファイル名を埋めてCopilotに送る。承認しない場合は、理由を伝え、何も実行せずに次の指示を待つように、Copilotに送る（生成したファイルの扱いは、Claudeと相談して決める）。

## 段階3：休講日APIとテスト（承認のあと）
最初に、`python -m pytest -q` が **306件、すべて合格**することを確かめる（ここで初めて、テスト用DBに、承認したmigrationが適用される）。合格しなければ、止まって報告する。**承認したmigrationファイルは、変更しない。**

### 3-1. `app/routes/closures.py`（新規）
- Blueprintは `closures_bp`（名前 `"closures"`、`url_prefix="/api/closures"`）。モデルをJSONにする関数 `closure_to_dict(closure)` は、`id`・`semester_id`・`date`（`format_date` で `YYYY-MM-DD`）・`name`（なければ `None`）の4項目を返す
- routeは、次の3つだけ。ほかのメソッドのrouteを書かない（`GET /api/closures/<id>`・`PATCH`・`PUT`・コレクションへの `DELETE` などは、Flaskと共通のエラーハンドラーが、405（`method_not_allowed`）を返す）

| route | 関数 | 内容 |
|---|---|---|
| `GET ""` | `get_closures` | 一覧。クエリ `semester_id` は `read_id_query`（メッセージは、授業の一覧と同じ「学期IDは1つだけ指定してください」「学期IDは整数で指定してください」）。エラーなら400（`validation_error`、`fields.semester_id`）。範囲外なら、DBに問い合わせずに `[]`。並びは、`date`・`id` の昇順 |
| `POST ""` | `create_closure` | 登録。下の表の検査。成功は201で、作成した休講日 |
| `DELETE f"/<int(max={MAX_ID}):closure_id>"` | `delete_closure` | 削除。`db.session.get` で取得し、なければ404（`not_found`、「休講日が見つかりません」）。あれば削除・`commit` し、204（本文なし。`return "", 204`） |

- 書き方は、`routes/subjects.py` に合わせる（`db.select`・`db.session.scalars`・`db.session.get`。`Closure.query` は使わない。型を絞るための `assert` を書かない）
- 予定（Event）は、読まない・作らない・消さない（同期は Task 011）

`POST` の本文の検査（誤りのある項目は、すべて `fields` に入れて、400（`validation_error`、「入力内容に誤りがあります」）。1つの項目の中では、表の順に検査し、最初に見つかった誤りを、その項目のエラーにする）：

| 項目 | 検査の順序 | メッセージ |
|---|---|---|
| `semester_id` | 必須（なし・`null`・`""`）→ 整数（真偽値・小数・文字列は不可。`validate_required_integer`）→ 範囲（1〜`MAX_ID`。範囲外は、DBに問い合わせない）→ 学期が存在する | 「学期IDは必須です」→「学期IDは整数で指定してください」→「指定された学期が存在しません」（範囲外と、存在しないとき） |
| `date` | `validate_required_date`（必須 → 文字列 → 使用できない文字 → 形式・実在）→ **`semester_id` に誤りがないときだけ**：学期の期間内（`start_date`〜`end_date`、両端を含む）→ 同じ学期に、同じ日付の休講日がない | 「日付は必須です」→「日付は実在する日付を「YYYY-MM-DD」の形式で指定してください」（文字列でないときも）→ `UNUSABLE_CHARACTER_MESSAGE` →「休講日は、学期の期間内の日付にしてください」→「同じ日付の休講日がすでに登録されています」 |
| `name` | 任意。`validate_optional_string`（`max_length=100`）：文字列 → 使用できない文字 → 前後の空白（全角を含む）を取り除き、空なら `null` → 100字以内 | 「名前は文字列で指定してください」→ `UNUSABLE_CHARACTER_MESSAGE` →「名前は100文字以内にしてください」 |
| ほかの項目（`id` を含む） | `validate_allowed_fields(payload, {"semester_id", "date", "name"})` | 「この項目は指定できません」 |

- `semester_id` の検査は、`routes/subjects.py` の `create_subject` と同じ書き方にする（範囲の確認の直前に、理由のコメント「範囲外のIDをDBに渡すと、SQLiteでOverflowErrorになるため先に確認する。」を書く）
- 存在を確かめた学期（`Semester`）を、`date` の期間の検査に使う（学期をDBから読み直さない）
- 期間と重複の検査は、`semester_id` と `date` の両方に誤りがないときだけ行う（設計資料の「休講日API」）。理由のコメントを書く
- 重複の検査は、`semester_id` と `date` が同じ休講日の行があるかで行う（DBの一意制約はない。設計資料のとおり）
- 曜日による制限はしない（土日の日付も登録できる）
- 成功したら、`Closure` を作り、`db.session.add`・`db.session.commit` をして、201で `closure_to_dict` を返す

書き方の例（`create_closure` の、`semester_id` と `date` の部分）：

```python
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

    closure_date, date_error = validate_required_date(
        payload,
        "date",
        "日付は必須です",
        "日付は実在する日付を「YYYY-MM-DD」の形式で指定してください",
    )
    if date_error is not None:
        fields["date"] = date_error
    elif semester is not None:
        # 学期の期間と重複の検査は、semester_idとdateの両方に
        # 誤りがないときだけ行う。
        if not semester.start_date <= closure_date <= semester.end_date:
            fields["date"] = "休講日は、学期の期間内の日付にしてください"
        else:
            duplicate = db.session.scalars(
                db.select(Closure).where(
                    Closure.semester_id == semester.id,
                    Closure.date == closure_date,
                )
            ).first()
            if duplicate is not None:
                fields["date"] = "同じ日付の休講日がすでに登録されています"
```

### 3-2. `app/__init__.py`
授業APIのBlueprintの登録（45〜47行目）の次、`return app` の前に、休講日APIのBlueprintの登録を足す。ほかは変えない。

```python
    from app.routes.subjects import subjects_bp

    app.register_blueprint(subjects_bp)

    from app.routes.closures import closures_bp

    app.register_blueprint(closures_bp)
    return app
```

### 3-3. `tests/test_setup.py`（2件。うち1件は既存のテストの変更）
- `test_migrations_create_all_expected_tables`（25〜35行目）：期待するテーブルの集合に、`"closures"` を足す（この1か所だけを変える）
- `test_closures_table_matches_design` を足す（`docs/architecture.md` の「自動テスト（pytest）」の「テストの書き方」の、migrationでテーブルを追加したタスクの確認）。テスト用DB（migrationで作る）の `closures` テーブルについて、次を確かめる（`inspect` は `import` 済み）

| 確かめること | 期待 |
|---|---|
| 列（名前：(型の文字列, NULL可否)） | `{"id": ("INTEGER", False), "semester_id": ("INTEGER", False), "date": ("DATE", False), "name": ("VARCHAR(100)", True)}` |
| 主キー（`get_pk_constraint`） | `{"constrained_columns": ["id"], "name": "pk_closures"}` |
| 外部キー（`get_foreign_keys` の、名前・列・参照先のテーブル・参照先の列） | `[("fk_closures_semester_id_semesters", ["semester_id"], "semesters", ["id"])]` |

書き方の例：

```python
def test_closures_table_matches_design(app):
    with app.app_context():
        inspector = inspect(db.engine)
        columns = {
            column["name"]: (str(column["type"]), column["nullable"])
            for column in inspector.get_columns("closures")
        }
        primary_key = inspector.get_pk_constraint("closures")
        foreign_keys = [
            (
                foreign_key["name"],
                foreign_key["constrained_columns"],
                foreign_key["referred_table"],
                foreign_key["referred_columns"],
            )
            for foreign_key in inspector.get_foreign_keys("closures")
        ]

    assert columns == {
        "id": ("INTEGER", False),
        "semester_id": ("INTEGER", False),
        "date": ("DATE", False),
        "name": ("VARCHAR(100)", True),
    }
    assert primary_key == {
        "constrained_columns": ["id"],
        "name": "pk_closures",
    }
    assert foreign_keys == [
        (
            "fk_closures_semester_id_semesters",
            ["semester_id"],
            "semesters",
            ["id"],
        )
    ]
```

### 3-4. `tests/test_closures_api.py`（新規。87件）
補助関数と定数（`tests/test_subjects_api.py` と同じ考え方。テストの準備のデータは、APIを通さず、ORMで作ってよい）：

| 補助 | 内容 |
|---|---|
| `make_semester(app, name="2026年度 前期")` | ORMで学期（2026-04-01〜2026-07-31）を作り、idを返す |
| `make_closure(app, semester_id, closure_date, name=None)` | ORMで休講日を作り、idを返す（`closure_date` は `date`） |
| `make_friday_subject(app, semester_id)` | ORMで金曜（`weekday=4`）の授業を作り、idを返す |
| `closure_payload(default_semester_id, **overrides)` | `{"semester_id": default_semester_id, "date": "2026-05-15"}` に、`overrides` を重ねた辞書。**最初の引数の名前を `semester_id` にしない**（`semester_id` を上書きするテストで、`closure_payload(semester_id, **{"semester_id": None})` の引数が重なり、`TypeError` になるため。`tests/test_subjects_api.py` の `subject_payload` と同じ） |
| `assert_validation_error(response, fields)` | 400で、本文が `{"error": {"code": "validation_error", "message": "入力内容に誤りがあります", "fields": fields}}` と一致する |
| `closure_count(app)`・`event_count(app)` | 休講日・予定の行数 |
| 定数 `DATE_FORMAT_MESSAGE` | 「日付は実在する日付を「YYYY-MM-DD」の形式で指定してください」 |

テストのデータの日付：2026-05-15 は金曜日、2026-05-16 は土曜日。

登録（`POST`）の成功：

| 番号 | テスト | 入力 | 期待 | 件数 |
|---|---|---|---|---|
| P1 | `test_closure_creation_returns_all_fields_and_matches_database` | `name` が `"　開学記念日 "` | 201。本文が `{"id": 整数, "semester_id": 学期のid, "date": "2026-05-15", "name": "開学記念日"}`。DBの行も同じ値（`date` は `date(2026, 5, 15)`、`name` は前後の空白を取り除いたもの） | 1 |
| P2 | `test_closure_name_is_optional_and_empty_becomes_null` | `name` が、なし・`None`・`""`・`"  "`・`"　"` | 201。`name` は `null`（DBも `None`） | 5 |
| P3 | `test_closure_dates_on_boundaries_and_weekends_are_accepted` | `date` が `"2026-04-01"`（開始日）・`"2026-07-31"`（終了日）・`"2026-05-16"`（土曜日） | 201。`date` が入力と同じ | 3 |
| P4 | `test_closure_name_up_to_100_characters_is_accepted` | `name` が `"名" * 100`・`"😀" * 100` | 201。`name` が入力と同じ | 2 |
| P5 | `test_same_date_in_another_semester_is_accepted` | 学期を2つ作り（名前「2026年度 前期」「2026年度 後期」。期間は同じ）、1つ目に5/15の休講日（ORM）。2つ目に5/15を登録 | 201。休講日が2件 | 1 |

登録（`POST`）の誤り：

| 番号 | テスト | 入力 | 期待 | 件数 |
|---|---|---|---|---|
| V1 | `test_empty_closure_payload_reports_required_fields` | `{}` | `{"semester_id": "学期IDは必須です", "date": "日付は必須です"}` | 1 |
| V2 | `test_closure_fields_validate_missing_types_and_length` | 正しい本文の1項目だけを替える：`semester_id` が `None`・`""`（必須）、`"1"`・`True`・`1.5`（整数）。`date` が `None`・`""`（必須）、`20260515`・`True`（形式）。`name` が `123`・`True`（文字列）、`"名" * 101`（100文字） | その項目のエラーだけ（メッセージは3-1の表） | 12 |
| V3 | `test_invalid_or_missing_semester_references_are_validation_errors` | 学期を1件作ったうえで、`semester_id` が `0`・`-1`・`MAX_ID + 1`・`10**30`・`99999`・`MAX_ID` | `{"semester_id": "指定された学期が存在しません"}` | 6 |
| V4 | `test_malformed_closure_dates_are_rejected` | `date` が `"2026-5-15"`・`"2026/05/15"`・`"20260515"`・`"2026-02-30"`・`" 2026-05-15"`・`"2026-05-15 "`・`"2026-05-15\n"`・`"２０２６-05-15"` | `{"date": DATE_FORMAT_MESSAGE}` | 8 |
| V5 | `test_closure_date_outside_semester_is_rejected` | `date` が `"2026-03-31"`・`"2026-08-01"` | `{"date": "休講日は、学期の期間内の日付にしてください"}` | 2 |
| V6 | `test_duplicate_closure_date_in_same_semester_is_rejected` | 5/15の休講日（ORM）がある学期に、5/15（`name` は `"別の名前"`）を登録 | `{"date": "同じ日付の休講日がすでに登録されています"}`。休講日は1件のまま | 1 |
| V7 | `test_semester_error_skips_period_and_duplicate_checks` | `semester_id` が `99999`（存在しない）、`date` が `"2026-12-31"`（期間の外） | `{"semester_id": "指定された学期が存在しません"}` だけ（`date` のエラーはない） | 1 |
| V8 | `test_unknown_closure_fields_are_rejected` | 正しい本文に、`id`・`color`・`weekday` のどれか1つ（値は `"unexpected"`）を足す | `{その項目: "この項目は指定できません"}` | 3 |
| V9 | `test_multiple_closure_validation_errors_are_returned_together` | `{"semester_id": "1", "date": "2026/05/15", "name": 123, "id": 1}` | `semester_id`（整数）・`date`（形式）・`name`（文字列）・`id`（指定できません）の4つ | 1 |
| V10 | `test_unusable_characters_in_closure_fields_are_rejected` | `date` が `"\ud800"`・`"2026-05-15\udc00"`、`name` が `"\ud800"`・`"  \udfff  "` | `{その項目: UNUSABLE_CHARACTER_MESSAGE}`。休講日は0件のまま | 4 |
| V11 | `test_non_object_closure_payload_has_no_fields` | `[]`・`"abc"`・`123`・`True`・`null`（`null` は、`data="null"`・`content_type="application/json"` で送る） | 400。本文が `{"error": {"code": "validation_error", "message": "リクエストの本文は、JSONのオブジェクトにしてください"}}`（`fields` はない） | 5 |
| V12 | `test_invalid_json_or_content_type_is_rejected` | `('{"date":', "application/json")`・`('{"date":"2026-05-15"}', "text/plain")`・`('{"date":"2026-05-15"}', None)` を、`data` と `content_type` で送る | 400。本文が `{"error": {"code": "invalid_json", "message": INVALID_JSON_MESSAGE}}` | 3 |

一覧（`GET`）：

| 番号 | テスト | 入力 | 期待 | 件数 |
|---|---|---|---|---|
| G1 | `test_empty_closure_list_returns_empty_array` | 休講日なし | 200、`[]` | 1 |
| G2 | `test_closure_list_orders_by_date_and_id_and_filters_semester` | 学期A（「2026年度 前期」）・B（「2026年度 後期」）。ORMで、この順に作る：A 6/1、B 5/15（名前「後期の休講日」）、A 5/15、A 4/29（名前「昭和の日」） | 全件：A 4/29・B 5/15・A 5/15・A 6/1 の順（idで確かめる。同じ日付は、idの昇順）。`?semester_id=<A>`：A 4/29・A 5/15・A 6/1。`?semester_id=<B>`：B 5/15の1件（4項目すべてを確かめる） | 1 |
| G3 | `test_invalid_semester_id_query_is_validation_error` | `?semester_id=`・`?semester_id=abc`・`?semester_id=1.5` | `{"semester_id": "学期IDは整数で指定してください"}` | 3 |
| G4 | `test_repeated_semester_id_query_is_validation_error` | `?semester_id=1&semester_id=2` | `{"semester_id": "学期IDは1つだけ指定してください"}` | 1 |
| G5 | `test_out_of_range_or_missing_semester_query_returns_empty` | 休講日を1件作ったうえで、`?semester_id=` が `0`・`str(MAX_ID + 1)`・`99999` | 200、`[]` | 3 |
| G6 | `test_leading_zero_semester_query_and_unknown_query` | 休講日を1件作ったうえで、`?semester_id=00<学期のid>` と `?foo=bar` | どちらも、その1件 | 1 |

削除（`DELETE`）：

| 番号 | テスト | 入力 | 期待 | 件数 |
|---|---|---|---|---|
| D1 | `test_closure_deletion_returns_204_and_removes_only_that_row` | 5/15と6/1の休講日を作り、5/15を削除 | 204、本文が空（`response.data == b""`）。休講日は1件で、一覧は6/1だけ | 1 |
| D2 | `test_deleted_closure_date_can_be_registered_again` | 5/15の休講日を作り、削除してから、5/15を登録 | 削除は204、登録は201 | 1 |
| D3 | `test_closure_delete_not_found_and_invalid_urls` | `/api/closures/99999`・`/api/closures/0`・`/api/closures/<MAX_ID>` →「休講日が見つかりません」。`/api/closures/<MAX_ID + 1>`・`/api/closures/abc`・`/api/closures/-1`・`/api/closures/` →「URLが見つかりません」 | 404。本文が `{"error": {"code": "not_found", "message": メッセージ}}` | 7 |

提供しないメソッド：

| 番号 | テスト | 入力 | 期待 | 件数 |
|---|---|---|---|---|
| M1 | `test_unsupported_closure_methods_do_not_change_rows` | 休講日を1件作り、`GET`・`PATCH`・`PUT`・`POST` を `/api/closures/<その休講日のid>` に、`PUT`・`PATCH`・`DELETE` を `/api/closures` に送る | 405、`code` が `method_not_allowed`。要求の前と後で、一覧（`GET /api/closures`）の応答が同じ | 7 |

予定（Event）を同期しないこと（**同期を入れる前の段階の期待値**。Task 011で、`docs/architecture.md` の「休講日の変更と予定の同期」の最終的な仕様の期待値に直す。テストの中に、その旨のコメントを書く）：

| 番号 | テスト | 入力 | 期待 | 件数 |
|---|---|---|---|---|
| E1 | `test_closure_creation_does_not_change_events_before_sync` | 金曜の授業と、その授業の5/15の予定を2件（`is_generated` が `True` のものと `False` のもの。`category="class"`）をORMで作り、5/15の休講日を登録 | 201。予定は2件のまま | 1 |
| E2 | `test_closure_deletion_does_not_create_events_before_sync` | 金曜の授業と、5/15の休講日をORMで作り（予定はない）、休講日を削除 | 204。予定は0件のまま | 1 |

- 件数の合計：登録の成功12・誤り47、一覧10、削除9、提供しないメソッド7、予定2の、87件
- 孤立サロゲートは、Pythonのエスケープ（`"\ud800"`）で書く。期待するメッセージは、`UNUSABLE_CHARACTER_MESSAGE`・`INVALID_JSON_MESSAGE` を `import` して使う
- パラメータが複数あるテストは、`pytest.mark.parametrize` で書く（件数は、表のとおりになる）

段階3の終わりに、`python -m pytest -q` が **394件、すべて合格**すること。

## 変更してよい既存のテスト

| ファイル | 変更してよいもの | それ以外 |
|---|---|---|
| `tests/test_api_helpers.py` | `import` の追加。H1〜H10と、補助関数の追加 | 既存のテストは変えない |
| `tests/test_setup.py` | `test_migrations_create_all_expected_tables` の集合に `"closures"` を足すこと。`test_closures_table_matches_design` の追加 | ほかは変えない |
| `tests/test_semesters_api.py`・`tests/test_subjects_api.py`・`tests/conftest.py` | 変えない | 段階1の共通化の前後で、期待値を変えずに合格すること |

- このタスクでの「既存のテスト」は、作業の開始時からあるテストのこと（`test_migrations_create_all_expected_tables` は、上の1か所の変更のあとも、既存のテストとして扱う）。**既存のテストが想定外に失敗した場合**は、テストの期待値やほかの仕様を直さない。原因を調べ、そこで実装を止めて、チャットで報告する
- このタスクで追加したテストが失敗した場合は、表の期待値を変えずに、実装やテストの書き間違いを直す。表の期待値そのものが、設計資料と食い違うと判断した場合は、直さずに停止して報告する

## 実装手順
1. ブランチ・作業ツリーの確認。設計資料が更新されていることを確認する（「Copilot確認手順」の1の `grep`）。更新されていなければ、何も変更せずに停止して報告する
2. 作業の前の状態を記録する：開発用DBの有無・ハッシュ・件数（「Copilot確認手順」の1）。`python -m pytest -q` が273件、すべて合格すること（合格しなければ、何も変更せずに停止して報告する）
3. **（段階1）** `api_helpers.py` の2つの関数 → `tests/test_api_helpers.py` のH1〜H10（合格を確認）→ `routes/semesters.py` → `routes/subjects.py`。`python -m pytest -q` が306件、すべて合格すること。1行の長さの確認（「Copilot確認手順」の3）
4. **（段階2）** モデルの3ファイル（2-1）。`python -m pytest -q` が306件、すべて合格すること
5. **（段階2）** 2-2のスクリプトを1回だけ実行 → 2-3の確認 → 2-4の報告 → **止まる**（承認まで、何も実行しない）
6. **（段階3。承認のあと）** `python -m pytest -q` が306件、すべて合格すること
7. **（段階3）** `tests/test_setup.py`（307件になる）→ `routes/closures.py`・`app/__init__.py` → `tests/test_closures_api.py`。`python -m pytest -q` が394件、すべて合格すること
8. 「Copilot確認手順」を実施する
9. 結果を報告して止まる

各段階の終わりに、`python -m pytest -q` の結果（件数・警告）を控えておく（最終報告に書く）。

## 完了条件
- `python -m pytest -q` が、**394件、すべて合格**する（失敗・エラー・スキップが0件）。件数が394でない場合は、どのテストが違うか、理由を報告する
- 段階1の終わりに306件、2-1のあとに306件、段階3の最初に306件が、すべて合格していた
- 承認ゲート（2-4）で報告して止まり、Komaの承認のあとで、段階3を始めた
- migrationファイルが1つ加わり（`migrations/versions/` の `.py` は2つ）、そのハッシュが、承認ゲートの報告と同じ（承認のあと、変えていない）
- 1-4・3-3・3-4の表のテストが、すべて、表の名前で存在する
- `app/`・`tests/`・`run.py` に、79文字を超える行がない（migrationファイルは対象外）
- 実行の前後で、開発用DB（`instance/app.db`）のハッシュが同じで、`semesters`・`subjects` の件数も同じ。開発用DBに `closures` テーブルがない（Copilotは適用していない）
- 変更したファイルが、「実装対象ファイル」の12だけ
- 「Komaの確認」が、期待どおり
- レビューで承認される

## Copilot確認手順
```
# 1. 実施前
git branch --show-current      # feature/009-closures-api
git status                     # 変更なし
grep -n "migrationの作成と適用" docs/architecture.md                       # 見出しを含む数件
grep -n "read_id_query\|validate_required_date" docs/architecture.md      # 数件
grep -n "承認ゲート" .github/copilot-instructions.md                       # 数件
ls -l instance/app.db          # 存在すること（なければ、何も変更せずに停止して報告する）
shasum -a 256 instance/app.db
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects;"
python -m pytest -q            # 273 passed

# 2. 各段階の終わり
python -m pytest -q            # 段階1：306 passed、2-1のあと：306 passed、段階3の最初：306 passed、段階3の終わり：394 passed

# 3. 1行の長さ（段階1・段階3の終わり。出力がなければ合格。migrations/ は対象外）
python - <<'EOF'
from pathlib import Path
paths = [*Path("app").rglob("*.py"), *Path("tests").glob("*.py"), Path("run.py")]
for path in paths:
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, 1):
        if len(line) > 79:
            print(f"{path}:{number}: {len(line)}")
EOF

# 4. 承認ゲートの確認（段階2。生成のあと。DBを使わない）
ls migrations/versions/*.py                                     # 2つ
grep -n "revision\|op\." migrations/versions/*_add_closures_table.py
cat migrations/versions/*_add_closures_table.py
shasum -a 256 migrations/versions/*_add_closures_table.py
git status

# 5. 検索（段階3の終わり）
grep -n "^def read_id_query\|^def validate_required_date" app/api_helpers.py   # 2件
grep -n "^from\|^import\|db\." app/api_helpers.py              # db を import していない、db. を使っていない
grep -n "parse_date\|from datetime" app/routes/semesters.py    # 出力なし
grep -n "request\|^import re" app/routes/subjects.py           # 出力なし
grep -n "read_id_query\|validate_required_date" app/routes/*.py   # closures.py に両方、semesters.py に validate_required_date、subjects.py に read_id_query
grep -n "\.query\|assert" app/routes/closures.py               # 出力なし
grep -n "Event" app/routes/closures.py                         # 出力なし（コメントで予定に触れる場合は、その行だけ）
grep -rn --include="*.py" "db.create_all" app tests            # 出力なし
ls migrations/versions/*.py                                     # 2つ
shasum -a 256 migrations/versions/*_add_closures_table.py      # 承認ゲートの報告と同じ

# 6. 実施後
shasum -a 256 instance/app.db  # 実施前と同じ
sqlite3 -readonly instance/app.db "SELECT COUNT(*) FROM semesters; SELECT COUNT(*) FROM subjects;"   # 実施前と同じ
sqlite3 -readonly instance/app.db ".tables"   # closures がない（開発用DBには、まだ適用していない）
git status                     # 変更：「実装対象ファイル」の12だけ
git diff --stat
```

| 確認 | 期待する結果 |
|---|---|
| `python -m pytest -q` | 実施前：273件、段階1：306件、2-1のあと：306件、段階3の最初：306件、段階3の終わり：394件が、すべて合格。失敗・エラー・スキップが0件。`migrations/env.py` の `DeprecationWarning` は、出ても構わない（報告する） |
| 1行の長さ | 出力なし |
| 承認ゲートの確認 | 2-3の表のとおり |
| 検索 | 上のコメントのとおり |
| 開発用DB | 実施の前後で、ハッシュ・`semesters`・`subjects` の件数が同じ。`.tables` に `closures` がない |
| `git status` | 変更：`app/api_helpers.py`、`app/routes/semesters.py`、`app/routes/subjects.py`、`app/models/__init__.py`、`app/models/semester.py`、`app/__init__.py`、`tests/test_api_helpers.py`、`tests/test_setup.py`。新規：`app/models/closure.py`、`app/routes/closures.py`、`migrations/versions/<revision>_add_closures_table.py`、`tests/test_closures_api.py`。`docs/`・`.github/`・`app/templates/`・`app/static/`・`requirements.txt`・`run.py`・`instance/` に変更なし |
| `git diff` | `app/routes/semesters.py` は、1-2の `import` と日付の検証の置き換えだけ。`app/routes/subjects.py` は、1-3の `import` とクエリの読み取りの置き換えだけ。`app/__init__.py` は、Blueprintの登録の追加だけ。`app/models/semester.py` は、1行の追加だけ |

`.pytest_cache/` や `__pycache__/` が `git status` に表示される場合は、`.gitignore` を変更せず、報告する。**このタスクでは、Copilotは `run.py` を起動せず、ブラウザでの確認もない**（画面を変えないため）。

## Komaの確認
順序：（1）pytest →（2）commit・push とレビューの依頼 →（3）レビューの承認のあと、開発用DBへの適用 →（4）適用のあとの確認 →（5）マージ。**開発用DBへの適用は、レビューの承認のあと、マージの前に行う。**

### 1. pytest
`python -m pytest -q` を自分で実行し、**394件、すべて合格**することを確かめる。

### 2. push とレビューの依頼
featureブランチを commit・push する（PRを作ってもよい）。Copilotの完了報告を共有して、Claudeにレビューを頼む。**pushは、マージではない。レビューの承認の前に、マージしない。** 修正が必要になった場合は、同じブランチでCopilotが直し、もう一度pushしてレビューを受ける。

### 3. 開発用DBへの適用（レビューの承認のあと）
`docs/architecture.md` の「migrationの作成と適用」の手順。ブランチは `feature/009-closures-api` のまま、リポジトリのルートで、`.venv` を有効にして行う。今の開発用DBは、学期・授業とも0件（2026-10-11にKomaが確認）だが、手順のとおりに行う。

```
# 0. サーバー（run.py）が起動していれば、Ctrl+C で止める
git branch --show-current                # feature/009-closures-api

# 1. 適用の前の版
flask --app app db current               # INFO の行のあとに 0280f6cf8d09（(head) は付かない）

# 2. バックアップ（日付は、実行した日になる）
mkdir -p instance/backups
cp -p instance/app.db instance/backups/app-$(date +%Y%m%d)-before-009.db
ls -l instance/backups/
shasum -a 256 instance/app.db instance/backups/app-*-before-009.db   # 2つのハッシュが同じ
git status --short                       # instance/ のファイルは表示されない（Gitの対象外）

# 3. 適用の前の記録
sqlite3 -readonly instance/app.db ".schema" > instance/backups/schema-before-009.sql
sqlite3 -readonly instance/app.db "SELECT 'semesters', COUNT(*) FROM semesters UNION ALL SELECT 'subjects', COUNT(*) FROM subjects UNION ALL SELECT 'events', COUNT(*) FROM events UNION ALL SELECT 'tasks', COUNT(*) FROM tasks;"

# 4. 適用
flask --app app db upgrade               # Running upgrade 0280f6cf8d09 -> <revision>, add closures table

# 5. 適用の後の確認
flask --app app db current               # <revision> (head)
sqlite3 -readonly instance/app.db ".schema closures"
sqlite3 -readonly instance/app.db ".schema" > instance/backups/schema-after-009.sql
diff instance/backups/schema-before-009.sql instance/backups/schema-after-009.sql
sqlite3 -readonly instance/app.db "SELECT 'semesters', COUNT(*) FROM semesters UNION ALL SELECT 'subjects', COUNT(*) FROM subjects UNION ALL SELECT 'events', COUNT(*) FROM events UNION ALL SELECT 'tasks', COUNT(*) FROM tasks UNION ALL SELECT 'closures', COUNT(*) FROM closures;"
shasum -a 256 instance/app.db            # 控えておく（4の確認のあとに比べる）
```

| 確認 | 期待 |
|---|---|
| 2のハッシュ | `instance/app.db` とバックアップが同じ |
| 4の出力 | `Running upgrade 0280f6cf8d09 -> <revision>, add closures table`（`<revision>` は、承認したmigrationのもの） |
| 5の `current` | `<revision> (head)` |
| 5の `.schema closures` | 下のとおり |
| 5の `diff` | `closures` の `CREATE TABLE` の8行だけが、`>` 付きで表示される（既存のテーブルの行は、表示されない） |
| 5の件数 | `semesters`・`subjects`・`events`・`tasks` が、3と同じ。`closures` は0 |

`.schema closures` の期待：

```
CREATE TABLE closures (
	id INTEGER NOT NULL, 
	semester_id INTEGER NOT NULL, 
	date DATE NOT NULL, 
	name VARCHAR(100), 
	CONSTRAINT pk_closures PRIMARY KEY (id), 
	CONSTRAINT fk_closures_semester_id_semesters FOREIGN KEY(semester_id) REFERENCES semesters (id)
);
```

### 4. 適用のあとの確認（書き込みにならない要求だけ）
開発用DBには学期がないため、休講日の登録・削除が成功する確認はしない（その動きは、pytestで確かめている）。休講日の画面は、Task 010で作る。

```
python run.py          # 起動（別のターミナルで、以下を実行）
BASE=http://127.0.0.1:5001
curl -s -w '\nHTTP %{http_code}\n' $BASE/api/closures
curl -s "$BASE/api/closures?semester_id=abc" | python -m json.tool --no-ensure-ascii
curl -s -X POST $BASE/api/closures -H 'Content-Type: application/json' \
  -d '{"semester_id": 99999, "date": "2026-05-15"}' \
  | python -m json.tool --no-ensure-ascii
curl -s -X DELETE $BASE/api/closures/99999 | python -m json.tool --no-ensure-ascii
curl -s $BASE/api/closures/1 | python -m json.tool --no-ensure-ascii
curl -s -o /dev/null -w 'HTTP %{http_code}\n' $BASE/api/semesters
curl -s -o /dev/null -w 'HTTP %{http_code}\n' $BASE/api/subjects
curl -s -o /dev/null -w 'HTTP %{http_code} %{content_type}\n' $BASE/
# サーバーを Ctrl+C で止めてから
shasum -a 256 instance/app.db          # 3の5で控えたハッシュと同じ
```

| 要求 | 期待 |
|---|---|
| `GET /api/closures` | `[]`、HTTP 200 |
| `?semester_id=abc` | `validation_error`、`fields.semester_id` が「学期IDは整数で指定してください」 |
| `POST`（存在しない学期） | `validation_error`、`fields.semester_id` が「指定された学期が存在しません」（検証で失敗するため、データは作られない） |
| `DELETE /api/closures/99999` | `not_found`、「休講日が見つかりません」 |
| `GET /api/closures/1` | `method_not_allowed`（405） |
| 学期・授業の一覧、トップページ | 200（トップページは `text/html`） |
| 最後のハッシュ | 適用の後（3の5）と同じ（確認の要求で、開発用DBは変わらない） |

### 戻し方（必要なときだけ）
適用でエラーが出た、`diff` や件数が期待と違う、適用のあとでmigrationを作り直すことになった、などの場合に行う。サーバーを止めてから、2で作ったバックアップを、元の名前に戻す（`<日付>` は、2で作ったファイルの日付）。戻したら、Claudeに状況を伝える。

```
cp -p instance/backups/app-<日付>-before-009.db instance/app.db
flask --app app db current               # 0280f6cf8d09
```

### 5. マージ
3・4が期待どおりなら、マージする。マージのあと、`main` に切り替えて取得し、`flask --app app db current` が `<revision> (head)` であることを確かめる（開発用DBは、すでに適用済み）。

**ブラウザでの確認は、このタスクにはない**（画面を変えないため。roadmapの「進め方の決定の記録」）。

## Git操作
**Git commit / push / ブランチ操作 / マージは行わない**（`git branch --show-current`、`git status`、`git diff` のような読み取りだけのコマンドは除く）。

## 注意
- **停止して報告する条件**（ファイルを変更せず、実装を止め、チャットで「問題点・発生理由・変更した場合の影響・推奨案（必要なら）」を報告する）
  - ブランチの不一致、作業ツリーの想定外の変更
  - 設計資料が更新されていない（実装手順の1）、または、設計資料とこのTask MDの間に、矛盾・不足がある
  - 設計資料にない判断が必要になった（特に `docs/architecture.md` の「未決定事項」に触れる場合）
  - 「変更しない」と定めたもの（`tests/test_subjects_api.py`、`requirements.txt`、既存のmigration、画面のファイルなど）を変更しないと実装できない
  - 開発用DB（`instance/app.db`）がない
  - 作業の前の `python -m pytest` が、273件すべて合格しない
  - **既存のテスト**（作業の開始時からあるテスト）**が、想定外に失敗した**。テストの期待値や、ほかの仕様を直さずに、原因を調べて報告する
  - migrationの生成（2-2）で、エラー・想定外の変更・生成なし・2つ以上の生成のどれかが起きた、または、生成したファイルが2-3の期待と違う。ファイルを直さず、消さず、もう一度実行せずに報告する
  - 承認したmigrationファイルを変更する必要が出た
  - テストの実行の前後で、`instance/app.db` が変わった
- **承認ゲート（2-4）は、停止の条件ではなく、手順の一部**。報告して止まり、承認のあとで段階3に進む。ほかの段階では止まらずに進める
- 開発用DBに対して、`flask db` のコマンドを、一切実行しない。`run.py` を起動しない。ライブラリを追加しない
- 期待する結果と異なる結果が出た場合は、確認を飛ばさず、原因を直してから、すべての確認をやり直す（ただし、既存のテストの想定外の失敗と、migrationの生成の問題は、上の停止の条件に従う）
- 設計資料に書かれていない仕様は、自分で決めない
- 最後の報告に、次を含める：変更したファイル、各段階の `pytest` の件数と警告、1行の長さの確認の結果、検索の結果、migrationファイルのハッシュ（承認ゲートの報告と、最後の確認）、開発用DBの前後のハッシュ・件数・`.tables`、`git status`・`git diff --stat`、気になった点
