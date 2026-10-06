# タスク005: 授業APIとpytest基盤

| 項目 | 内容 |
|---|---|
| Task ID | 005 |
| Task名 | 授業APIとpytest基盤 |
| ブランチ | `feature/005-subjects-api-and-pytest`（Komaが作成・切替済みの状態で渡される） |

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに停止して報告する。

## 目的
次の3つを、この順に実装する。
1. **pytest基盤**：自動テストの土台を作る。テストは、開発用のDB（`instance/app.db`）を**絶対に使わず**、一時ディレクトリのテスト用DBだけを使う。
2. **学期APIの回帰テスト**：Task 003で作った学期APIの挙動を、テストで固定する（学期APIのコードは変更しない）。
3. **授業API**：`GET /api/subjects`、`GET /api/subjects/<id>`、`POST /api/subjects`と、そのテスト。

## 前提（Task 004完了時点の状態）

| 区分 | 内容 |
|---|---|
| すでにある | 学期API、`api_helpers.py`（エラー応答・エラーハンドラー・`read_json_object`・`validate_allowed_fields`・`validate_required_string`・`parse_date`・`format_date`・`MAX_ID`）、`Subject`・`Event`・`Task`のモデルとテーブル（migration適用済み）、学期UI、`create_app()`（引数なし） |
| まだない | `tests/`、`pytest.ini`、pytest（ライブラリ）、`routes/subjects.py`、時刻の変換、整数の検証、任意の文字列の検証 |
| 決定済み | pytestの導入（このタスクで、Komaが承認済み。`requirements.txt` への追加を含む）。`docs/architecture.md` の「自動テスト（pytest）」「授業API」「API共通ルール」 |
| このタスクの暫定 | 授業の `POST` は、**授業の行だけ**を作る（Eventの自動生成は、別のタスクで実装する）。授業の編集・削除（`PATCH`・`DELETE`）も、このタスクでは提供しない |
| 開発用DB | `instance/app.db` には、実際に登録した学期が入っている場合がある。**このタスクで、読み書きしない**（テストも、`curl` の確認も） |

## Source of Truth
- `docs/architecture.md`：「API共通ルール」（特に「リクエストとレスポンス（JSON）」「日付・時刻・日時」「エラー」「404の使い分け」「API共通処理の補助モジュール」）、「授業API」、「自動テスト（pytest）」、「データ設計」のSubject、「DBスキーマ変更の方式」
- `docs/requirements.md`：「学期」「予定の登録」の授業モード
- `docs/tasks/003_api_foundation_and_semesters_api.md`：学期APIの仕様と、エラーメッセージの文言（回帰テストの期待値）
- `.github/copilot-instructions.md`：進め方、「テスト」

## 実装対象ファイル

| 区分 | ファイル | 内容 |
|---|---|---|
| 新規 | `pytest.ini` | pytestの設定 |
| 新規 | `tests/conftest.py` | テスト用DB・アプリ・クライアントのfixture、開発用DBの保護 |
| 新規 | `tests/test_setup.py` | テスト基盤の確認 |
| 新規 | `tests/test_api_helpers.py` | `api_helpers.py` の共通関数の単体テスト |
| 新規 | `tests/test_semesters_api.py` | 学期APIの回帰テスト |
| 新規 | `tests/test_subjects_api.py` | 授業APIのテスト |
| 新規 | `app/routes/subjects.py` | 授業API |
| 変更 | `app/__init__.py` | `create_app(test_config=None)` への変更、授業のBlueprintの登録 |
| 変更 | `app/api_helpers.py` | 共通関数の追加・拡張（後述） |
| 変更 | `requirements.txt` | pytestの追加 |

`tests/__init__.py` は作らない。

## 非対象（このタスクでは作らない・変更しない）
- `app/routes/semesters.py`、`app/routes/main.py`（**学期APIのコードは変更しない**。回帰テストで、現在の挙動を固定する）
- `app/models/`、`app/config.py`、`app/extensions.py`、`run.py`
- `migrations/`（**新しいmigrationは作らない。`flask db migrate`・`flask db upgrade`・`flask db downgrade` などの `flask db` コマンドを、一切実行しない。** テストの中で、Pythonの関数 `flask_migrate.upgrade()` を、テスト用DBに対してだけ呼ぶ）
- `app/templates/`、`app/static/`（画面・JavaScript）
- `docs/`、`.github/`、`.gitignore`
- 授業の `PATCH`・`DELETE`、Eventの自動生成、`/api/events`、`/api/tasks`
- JavaScriptのテスト
- **Task 004のLow-1〜Low-6（`semesters.js` などのJavaScript）は、このタスクでは修正しない**（授業UIのタスクで扱う）
- Task 003で持ち越した項目（405の `Allow` ヘッダー、`assert` の整理、`Semester.query` と `db.session` の書き方の統一、学期APIの日付検証コードの共通化）

## pytest基盤の実装

### 1. `create_app(test_config=None)`（`app/__init__.py`）
- 引数 `test_config`（辞書または `None`）を足す。`None` のときは、これまでどおり（`Config` を使い、`instance/` を作る）
- `test_config` が渡されたとき：
  1. `SQLALCHEMY_DATABASE_URI` が `test_config` に含まれていなければ、`ValueError` を送出する（開発用DBを、うっかり使わないため）。メッセージは日本語
  2. `Config` の読み込みのあと、**`db.init_app(app)` の前に**、`app.config.update(test_config)` で設定を上書きする
  3. `instance/` ディレクトリの作成（`os.makedirs`）は、行わない
- 授業のBlueprint（`app.routes.subjects` の `subjects_bp`）を、学期のBlueprintのあとに登録する
- それ以外の処理は、変更しない。`run.py` は、変更なしで動くこと

### 2. `pytest.ini`
```
[pytest]
testpaths = tests
pythonpath = .
```

### 3. `requirements.txt`
- `pip install pytest` を実行する（Komaの承認済み）
- ファイルの既存の書式（`==` でバージョンを固定、並び順）に合わせて、`pytest` と、そのインストールで増えたライブラリを追加する。`pip freeze` の差分で、増えたものを確認する
- 既存の行は、変更しない

### 4. `tests/conftest.py`
次のfixtureを定義する（この構成で、動作確認済み）。

| fixture | スコープ | 役割 |
|---|---|---|
| `protect_dev_db` | session、`autouse` | テストの前後で、`instance/app.db` の内容のハッシュ（SHA-256）が同じことを確認する。ファイルがなければ、なかったことを確認する。違えば、`AssertionError` |
| `template_db` | session | `tmp_path_factory` の一時ディレクトリに、雛形のDBを作る。`create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": ...})` でアプリを作り、`app_context` の中で `flask_migrate.upgrade(directory=<リポジトリの migrations/ の絶対パス>)` を呼び、最後に `db.engine.dispose()` する |
| `app` | function | `template_db` を、テストごとの `tmp_path` へコピーし、そのDBでアプリを作る。作る前に、DBのパスが、pytestの一時ディレクトリの中にあり、`instance/app.db` と別であることを確認する（違えば、`AssertionError`）。テストのあとに、`db.session.remove()` と `db.engine.dispose()` を行う |
| `client` | function | `app.test_client()` |

要点：
- DBのURIは、`f"sqlite:///{絶対パス}"`（絶対パスなので、スラッシュが合計4本になる）
- 各テストは、新しいコピーのDBを使う（リセットは、コピーに替わることで行う）。テストのあとに、DBを消す処理は書かない（pytestが一時ディレクトリを管理する）
- リポジトリのルート（`PROJECT_ROOT`）は、`Path(__file__).resolve().parents[1]` で求める
- 開発用DBのパスは、`PROJECT_ROOT / "instance" / "app.db"`
- テストのコードで、`create_app()` を引数なしで呼ばない
- テストにデータを入れるときは、`with app.app_context():` の中で、ORM（`db.session.add`・`commit`）を使う（テストの準備は、APIを通さない）。繰り返し使うデータの作成は、fixtureや補助関数にしてよい

### 5. `tests/test_setup.py`（基盤の確認）
| テスト | 期待 |
|---|---|
| テスト用DBの隔離 | `app.config["SQLALCHEMY_DATABASE_URI"]` が、`instance/app.db` を指さず、pytestの一時ディレクトリの中を指す |
| migrationの適用 | `semesters`・`subjects`・`events`・`tasks`・`alembic_version` のテーブルがある |
| 書き込みの隔離（1つのテスト。実行順に依存しない） | `app` のDBファイルが、**このテスト専用の `tmp_path` の直下**にあり、雛形（`template_db`）とは別のファイルである。学期を1件作って `commit` した（件数が1になる）あとで、雛形のハッシュ（SHA-256）が、作る前と同じである。テストの書き込みが雛形に及ばないので、次のテストは、雛形のコピー（空のDB）から始まる。DBのパスは、`app.config["SQLALCHEMY_DATABASE_URI"]` から、先頭の `sqlite:///` を取り除いて求める。`fixture` が、雛形をそのまま使う、またはDBを共有する、という誤りを、このテストが検出する（理由を、コメントに書く） |
| `ValueError` | `create_app({"TESTING": True})` が、`ValueError` になる |
| クライアント | `client.get("/")` が、200で、`text/html` |

### 6. 実行方法
リポジトリのルートで、`.venv` を有効にして、`python -m pytest`。1つのファイル：`python -m pytest tests/test_subjects_api.py`。

### 7. 注意
- `migrations/env.py` の `get_engine()` に関する `DeprecationWarning` が出る場合がある。`migrations/` は変更しない。警告は、完了報告に記載する
- テストの実行で、`.pytest_cache/` などが、追跡対象（`git status` に表示）になる場合は、`.gitignore` を変更せず、報告する

## `api_helpers.py` の追加・拡張
**DBの操作を持たせない**（`db` を `import` しない）。次の関数の挙動は、下の表のとおり。**すでにある関数の挙動は、引数を指定しない限り、変えない**（学期APIの挙動が変わらないこと。回帰テストで確認する）。

| 関数 | 内容 |
|---|---|
| `validate_required_string`（拡張） | 既存の引数のあとに、キーワード専用の引数 `max_length=None`、`length_message=None`、`strip=False` を足す。指定しなければ、これまでと同じ挙動。`strip=True`：前後の空白（全角を含む。`str.strip()`）を取り除いてから、検査する。取り除いた結果が空なら、`required_message`。`max_length`：取り除いたあとの文字数が、`max_length` を超えたら、`length_message`。`max_length` を指定するときは、`length_message` も必須（ない場合は `ValueError`）。返す値は、`(値, エラーメッセージ)`（取り除いたあとの値） |
| `validate_optional_string`（新設） | `(payload, field, type_message, *, max_length=None, length_message=None)`。キーがない、または `None` なら `(None, None)`。文字列でなければ `(None, type_message)`。前後の空白を取り除き、空なら `(None, None)`。長さの上限を超えたら `(None, length_message)`。それ以外は `(値, None)` |
| `validate_required_integer`（新設） | `(payload, field, required_message, type_message, *, min_value=None, max_value=None, range_message=None)`。キーがない、`None`、`""` は `required_message`。**真偽値は不可**。`int` 以外（小数・文字列・配列など）は `type_message`。範囲外は `range_message`（指定がなければ `type_message`）。それ以外は `(整数, None)` |
| `parse_time`（新設） | `(value)`。文字列で、`[0-9]{2}:[0-9]{2}` に**全体一致**し、時が0〜23、分が0〜59なら、`datetime.time`。それ以外は `None`。`24:00`・`9:00`・`09:00:00`・`0900`・全角・前後の空白・末尾の改行は、`None` |
| `format_time`（新設） | `(value)`。`time` を `"HH:MM"` の文字列にする |
| `validate_required_time`（新設） | `(payload, field, required_message, format_message)`。キーがない、`None`、`""` は `required_message`。`parse_time` が `None` なら `format_message`。それ以外は `(time, None)` |

## 学期API回帰テスト（`tests/test_semesters_api.py`）
Task 003のMDの仕様と、メッセージの文言を、期待値にする。**学期APIのコード（`routes/semesters.py`）は変更しない。** テストが落ちた場合は、次のとおり。
- テストの期待値が、Task 003の仕様と食い違っているなら、テストを直す
- テストがTask 003の仕様どおりで、コードが仕様と違うなら、**コードは直さず、停止して報告する**

テスト項目（`pytest.mark.parametrize` を使ってよい）：

| 区分 | 項目 |
|---|---|
| 一覧・取得 | 空の一覧は `[]`（200、JSON）。作成は201で、`id`・`name`・`start_date`・`end_date` の4項目。一覧の並びは、開始日の新しい順で、同じ開始日なら、idの新しい順。1件取得は、作成時の応答と一致 |
| 検証（400、`validation_error`） | 同名の重複。形式違反（`前期`、全角数字、末尾の改行、先頭の空白）。51文字。空のオブジェクト（3項目の必須）。型違い。日付の形式（`20990406`・`2099/04/06`・`2099-4-6`・`2099-02-30`・末尾の改行）。終了日が開始日と同じ、または前。未知の項目と `id`。本文がオブジェクトでない5種（配列・文字列・数値・`true`・`null`。`fields` なし） |
| JSON・Content-Type（400、`invalid_json`） | 壊れたJSON。`text/plain`。`Content-Type` なし。`charset` つきの `application/json` は成功 |
| 404 | 存在しない学期（`99999`、`0`、`MAX_ID`）は「学期が見つかりません」。`MAX_ID + 1`、20桁の数、`abc`、`-1`、末尾のスラッシュ、`/api/unknown`、`/api` は「URLが見つかりません」 |
| 405 | `DELETE`・`PATCH`（`/api/semesters/1`）、`PUT`（`/api/semesters`）、`POST`（`/api/semesters/1`）。いずれも `method_not_allowed` |
| 通常ページ | `/` は200のHTML。存在しないページは404のHTML。`POST /` は405のHTML。`Access-Control-` で始まるヘッダーが、`GET` と `OPTIONS` の応答にない |
| 500 | `/api` の中で例外が起きたら、500のJSON（`server_error`）。通常ページで例外が起きたら、HTML。テスト専用のルートを、テストの中で足し、`PROPAGATE_EXCEPTIONS` を `False` にする |
| 失敗時の副作用 | 400になった `POST` の前後で、学期の件数が変わらない |

## 授業API仕様（`app/routes/subjects.py`）

| 操作 | 内容 |
|---|---|
| `GET /api/subjects` | 200。配列。並びは `weekday`・`start_time`・`id` の昇順。クエリ `semester_id`（任意）で絞り込む |
| `GET /api/subjects/<id>` | 200。存在しなければ404（`not_found`、「授業が見つかりません」） |
| `POST /api/subjects` | 201。作成した授業を返す。**授業の行だけを作る**（Event・Taskは作らない） |
| `PATCH`・`DELETE`（ほか未定義のメソッド） | 提供しない（405） |

レスポンスは、8項目（`id`・`semester_id`・`subject_name`・`room`・`weekday`・`start_time`・`end_time`・`notes`）を、常にすべて含む。`room`・`notes` は、値がなければ `null`。`start_time`・`end_time` は `"HH:MM"`。

```json
{"id": 1, "semester_id": 1, "subject_name": "プログラミング基礎", "room": "3号館201", "weekday": 0, "start_time": "09:00", "end_time": "10:00", "notes": null}
```

実装の規則：
- Blueprint名は `subjects_bp`（`url_prefix="/api/subjects"`）。関数名は `get_subjects`・`get_subject`・`create_subject`
- IDを受け取るURLの規則は、`f"/<int(max={MAX_ID}):subject_id>"`（`MAX_ID` は `api_helpers` から `import`）
- 授業が存在しない場合は、`abort(404)` ではなく、route の中で `api_error_response("not_found", "授業が見つかりません")` を返す
- DBの操作は、この `route` の中で、`db.session` を使って行う。取得は `db.session.get(Subject, id)`、一覧は `db.session.scalars(db.select(Subject)...)`。`Subject.query` は使わない
- `subject_to_dict`（モデルをJSONにする関数）は、この `route` の中に置く。`format_time` を使う
- 型の絞り込みのためだけの `assert` は、使わない
- 授業の登録のときに、学期が存在するかの確認（`db.session.get(Semester, semester_id)`）は、`semester_id` が整数で、1〜`MAX_ID` の範囲内のときだけ行う
- 日本語のコメントで、次の2か所に理由を書く：①`semester_id` の範囲を、DBに問い合わせる前に確認する理由（範囲外の数をDBに渡すと、`OverflowError` になるため）、②クエリの数字の桁数を確認する理由（Pythonは、非常に長い数字の文字列を `int()` に渡すと、`ValueError` になるため）

## 入力検証

### `POST /api/subjects`
誤りのある項目は、**すべて** `fields` に入れる（項目名がキー）。1つの項目に複数の誤りがあるときは、下の順で、最初に見つかった1つだけを、その項目のメッセージにする。

| 項目 | 検査（この順） | message |
|---|---|---|
| `semester_id` | ①必須（キーがない、`null`、`""`） | 学期IDは必須です |
| | ②整数（真偽値・小数・文字列・配列・オブジェクトは不可） | 学期IDは整数で指定してください |
| | ③1〜`MAX_ID`。範囲外は、DBに問い合わせない | 指定された学期が存在しません |
| | ④その学期が存在する | 指定された学期が存在しません |
| `subject_name` | ①必須（キーがない、`null`、前後の空白を取り除いて空） | 科目名は必須です |
| | ②文字列 | 科目名は文字列で指定してください |
| | ③前後の空白を取り除いたあとの文字数が100以下 | 科目名は100文字以内にしてください |
| `room` | 任意。①文字列（`null` は可） | 教室は文字列で指定してください |
| | ②取り除いたあとの文字数が100以下。空なら `null` | 教室は100文字以内にしてください |
| `weekday` | ①必須（キーがない、`null`、`""`） | 曜日は必須です |
| | ②整数（真偽値・小数・文字列は不可）で、0〜6 | 曜日は0（月曜）〜6（日曜）の整数で指定してください |
| `start_time` | ①必須 | 開始時刻は必須です |
| | ②`HH:MM`（`00:00`〜`23:59`）。文字列でない値も、この誤り | 開始時刻は「HH:MM」の形式（00:00〜23:59）で指定してください |
| `end_time` | ①必須 | 終了時刻は必須です |
| | ②`HH:MM`（`00:00`〜`23:59`） | 終了時刻は「HH:MM」の形式（00:00〜23:59）で指定してください |
| | ③`start_time`・`end_time` が、どちらも正しい時刻のときだけ：`end_time` が `start_time` より後（同じ時刻も不可） | 終了時刻は開始時刻より後にしてください |
| `notes` | 任意。文字列（`null` は可）。取り除いて空なら `null`。長さの上限なし | 詳細・メモは文字列で指定してください |
| 未知の項目、`id` | その項目名で、`fields` に入れる | この項目は指定できません |

- 全体のmessage：「入力内容に誤りがあります」
- 9〜19時・1時間刻みは、**検証しない**（`07:30`〜`21:45` も受け付ける。UIだけの制約）
- 同じ科目名・同じ時間の授業の重複は、検証しない（2件目も201）
- 本文がオブジェクトでない、JSONが読めない、`Content-Type` が違う場合は、Task 003のとおり（`read_json_object` を使う）

### `GET /api/subjects` のクエリ `semester_id`

| 値 | 結果 |
|---|---|
| 指定なし | すべての授業 |
| 半角数字だけ（`[0-9]+` に全体一致）で、先頭の0を取り除いた値が、1〜`MAX_ID` | その学期の授業。学期が存在しなければ、`[]` |
| 半角数字だけで、先頭の0を取り除いた値が、空（0）、または `MAX_ID` を超える（取り除いたあとが19桁を超える数字は、`int()` に渡さず、範囲外として扱う） | `[]`（200） |
| 数字だけでない（空文字・`abc`・`-1`・`1.5`・全角数字・前後の空白など） | 400、`validation_error`、`fields.semester_id`＝「学期IDは整数で指定してください」 |
| 複数回の指定（`?semester_id=1&semester_id=2`） | 400、`validation_error`、`fields.semester_id`＝「学期IDは1つだけ指定してください」 |
| 先頭に0がある数字（`001`、`0000000000000000000001`） | 先頭の0を取り除いて、整数として扱う（どちらも `1`） |
| 未知のクエリ（`?foo=bar`） | 無視する |

400のときの全体のmessageは、「入力内容に誤りがあります」。

## エラー処理

| 状況 | ステータス | code | message |
|---|---|---|---|
| 入力の誤り（上記すべて） | 400 | `validation_error` | 入力内容に誤りがあります（`fields` つき）。本文がオブジェクトでない場合は、Task 003のとおり（`fields` なし） |
| JSONが読めない、`Content-Type` が違う | 400 | `invalid_json` | Task 003のとおり |
| 存在しない授業のID（形式は正しく、上限以内） | 404 | `not_found` | 授業が見つかりません |
| URLが存在しない、IDの形式が不正、IDが `MAX_ID` を超える | 404 | `not_found` | URLが見つかりません（共通のエラーハンドラー） |
| 未定義のメソッド（`PATCH`・`DELETE`・`PUT`） | 405 | `method_not_allowed` | このURLでは、そのメソッドは使えません |
| 他のデータとの競合（409） | 使わない | | |
| 予期しない例外 | 500 | `server_error` | Task 003のとおり |

## APIテストケース

### `tests/test_api_helpers.py`（単体テスト。DBを使わない）
| 対象 | ケース |
|---|---|
| `parse_time` | 正しい：`00:00`・`09:00`・`23:59`。`None` になる：`24:00`・`09:60`・`9:00`・`09:0`・`0900`・`09:00:00`・` 09:00`・`09:00 `・`09:00\n`・`０９：００`・`ab:cd`・`""`・`900`（整数）・`None` |
| `format_time` | `time(9, 0)` → `"09:00"`、`time(23, 59)` → `"23:59"` |
| `validate_required_time` | 必須（キーがない・`None`・`""`）、形式の誤り、正しい値 |
| `validate_required_string` | 既存の挙動が変わらない（`strip` なしで、前後の空白をそのまま保つ。`"  "` は、空ではない）。`strip=True`（取り除く、空白だけなら必須）。`max_length`（100字ちょうどは可、101字は不可。取り除いたあとで数える）。`max_length` だけを指定すると `ValueError` |
| `validate_optional_string` | キーなし・`None`・`""`・`"  "`・`"　"`（全角） → `None`。非文字列 → 型エラー。上限 |
| `validate_required_integer` | 整数・`0`・負の数は可。`True`・`False`・`1.0`・`"1"`・`[1]`・`{}` は型エラー。`None`・`""`・キーなしは必須。範囲の境界（最小・最大の両端と、その外側）。`range_message` を指定しないと `type_message` |

### `tests/test_subjects_api.py`
基本の本文：`{"semester_id": <作成した学期のid>, "subject_name": "プログラミング基礎", "weekday": 0, "start_time": "09:00", "end_time": "10:00"}`。各テストが、必要な学期を、自分で作る。

| 区分 | ケース（期待） |
|---|---|
| 登録（201） | 全項目（応答の8項目が、入力と一致。DBの行も一致）。必須だけ（`room`・`notes` が `null`）。前後の空白（全角空白を含む）が取り除かれる。`room`・`notes` が `""`・空白だけ・`null` → `null`。科目名100字・教室100字・メモ10000字。時刻の境界（`00:00`〜`23:59`）。曜日の `0` と `6`。9〜19時の外（`07:30`〜`21:45`）。同じ内容の2件目も201（別のid）。登録後に、`events`・`tasks` の件数が0のまま |
| 必須・型（400） | `{}`（5項目の必須）。`semester_id`：`null`・`""`・`"1"`・`true`・`false`・`1.5`・`[1]`・`{}`。`subject_name`：`""`・`"   "`・`"　"`・`null`・`123`・`true`・`[]`。`weekday`：`null`・`""`・`"1"`・`true`・`1.0`・`[0]`。`start_time`・`end_time`：`null`・`""`・`900`・`true` |
| `semester_id`（400） | `0`・`-1`・`MAX_ID + 1`・`10**30`・存在しない `99999`・`MAX_ID`（範囲内で存在しない）→ すべて「指定された学期が存在しません」。`MAX_ID` 付近の値で、500にならない |
| 範囲・長さ（400） | `weekday`：`-1`・`7`・`100`。`subject_name`：101字。取り除く前は101字だが、取り除くと100字 → 成功。`room`：101字 |
| 時刻（400） | `9:00`・`09:0`・`0900`・`09:00:00`・`24:00`・`09:60`・`ab:cd`・` 09:00`・`09:00 `・`09:00\n`・`０９：００` |
| 時刻の前後（400） | `end_time` が `start_time` と同じ、または前 → `end_time` のエラー。`start_time` が不正なときは、前後の検査を行わない（`end_time` に、前後のエラーがつかない） |
| 未知の項目（400） | `color`、`id`、`events` → 「この項目は指定できません」 |
| 複数の誤り（400） | 存在しない `semester_id`、範囲外の `weekday`、前後が逆の時刻を、同時に → 3項目すべてが `fields` に入る |
| 本文（400） | オブジェクトでない5種（`fields` なし）、壊れたJSON（`invalid_json`）、`text/plain`・`Content-Type` なし（`invalid_json`）、`charset` つきは成功 |
| 失敗時の副作用 | 400になった `POST` の前後で、授業の件数が変わらない |
| 一覧 | 空は `[]`。並び：曜日→開始時刻→id（曜日・時刻・idがばらばらの6件で確認。同じ曜日・時刻は、idの昇順）。`?semester_id=` で絞り込める（別の学期の授業が混ざらない）。指定なしは、全学期の授業 |
| 一覧のクエリ | 存在しない学期・`0`・`MAX_ID + 1`・20桁・5000桁の数字 → 200、`[]`。`abc`・空文字・`-1`・`1.5`・`１`（全角）・` 1`・`1 ` → 400（`fields.semester_id`）。複数指定 → 400。`001`・`0000000000000000000001`（22桁） → 学期1の授業。0だけの数字（`000`）→ `[]`。`?foo=bar` は無視 |
| 1件取得 | 200（`POST` の応答と一致）。存在しないID（`99999`・`0`・`MAX_ID`）→ 404「授業が見つかりません」。`MAX_ID + 1`・20桁・`abc`・`-1`・末尾のスラッシュ → 404「URLが見つかりません」 |
| 405 | `PATCH`・`DELETE`（`/api/subjects/<id>`）、`PUT`・`PATCH`・`DELETE`（`/api/subjects`）、`POST`（`/api/subjects/<id>`） → 405（`method_not_allowed`）。授業が、変更・削除されていない |

件数の目安は、授業APIのテストで、50〜80件程度（`parametrize` の展開後）。上の区分とケースが、すべてテストになっていること。

## 実装手順
1. ブランチ・作業ツリーの確認。`docs/architecture.md` に、「自動テスト（pytest）」「授業API」が書かれていることを確認する。書かれていなければ、何も変更せずに停止して報告する
2. 作業の前の状態を記録する（後の確認のため）：開発用DBのハッシュ（`shasum -a 256 instance/app.db`）と、`sqlite3 instance/app.db "SELECT COUNT(*) FROM subjects;"`
3. **（段階1）基盤**：`pip install pytest`、`requirements.txt`、`pytest.ini`、`create_app(test_config=None)`、`tests/conftest.py`、`tests/test_setup.py`。`python -m pytest` が、全件合格すること
4. **（段階2）学期APIの回帰テスト**：`tests/test_semesters_api.py`。`python -m pytest` が、全件合格すること
5. **（段階3）授業API**：`api_helpers.py` の追加・拡張と `tests/test_api_helpers.py`（合格を確認）→ `routes/subjects.py` と授業のBlueprintの登録 → `tests/test_subjects_api.py`。`python -m pytest` が、全件合格すること
6. 「Copilot確認手順」を実施する
7. 結果を報告して止まる

各段階の終わりに、`python -m pytest` の結果（件数）を、控えておく（最終報告に書く）。

## 完了条件
- `python -m pytest` が、全件合格する（失敗・エラー・スキップが0件）
- 上の「APIテストケース」の区分が、すべて、テストとして存在する
- 実行の前後で、開発用DB（`instance/app.db`）のハッシュが同じで、`subjects` の件数も同じ
- 学期のAPIの挙動が、変わっていない（回帰テストが合格）
- Komaの確認（下記）が、期待どおり
- レビューで承認される

## Copilot確認手順
```
# 1. 実施前（手順2で記録済みの値を使う）
shasum -a 256 instance/app.db
sqlite3 instance/app.db "SELECT COUNT(*) FROM subjects;"

# 2. テスト
python -m pytest -q            # 全件合格。件数・警告を記録する

# 3. 実施後
shasum -a 256 instance/app.db  # 実施前と同じ
sqlite3 instance/app.db "SELECT COUNT(*) FROM subjects;"   # 実施前と同じ

# 4. 起動中のサーバーの、読み取りだけの確認（POSTは実行しない）
python run.py                  # 別のターミナルで、以下を実行
BASE=http://127.0.0.1:5001
curl -s -w '\nHTTP %{http_code}\n' $BASE/api/subjects
curl -s -w '\nHTTP %{http_code}\n' $BASE/api/subjects/99999
curl -s -w '\nHTTP %{http_code}\n' $BASE/api/subjects/99999999999999999999
curl -s -w '\nHTTP %{http_code}\n' "$BASE/api/subjects?semester_id=abc"
curl -s -w '\nHTTP %{http_code}\n' "$BASE/api/subjects?semester_id=99999"
curl -s -w '\nHTTP %{http_code}\n' -X PATCH $BASE/api/subjects/1
curl -s -w '\nHTTP %{http_code}\n' -X DELETE $BASE/api/subjects/1
curl -s -w '\nHTTP %{http_code}\n' $BASE/api/semesters
curl -s -o /dev/null -w 'HTTP %{http_code} %{content_type}\n' $BASE/
```

| 確認 | 期待する結果 |
|---|---|
| `python -m pytest -q` | 全件合格。失敗・エラー・スキップが0件。`migrations/env.py` の `DeprecationWarning` は、出ても構わない（報告する） |
| 開発用DB | 実施の前後で、ハッシュ・`subjects` の件数が同じ |
| `GET /api/subjects` | 200、`[]` |
| `GET /api/subjects/99999` | 404、`not_found`、「授業が見つかりません」 |
| `GET /api/subjects/99999999999999999999` | 404、`not_found`、「URLが見つかりません」 |
| `?semester_id=abc` | 400、`validation_error`、`fields.semester_id`＝「学期IDは整数で指定してください」 |
| `?semester_id=99999` | 200、`[]` |
| `PATCH`・`DELETE` | 405、`method_not_allowed`、JSON |
| `GET /api/semesters` | 200（既存の学期の一覧。変更なし） |
| `GET /` | 200、`text/html` |
| サーバー停止後 | `lsof -i :5001` の出力が空 |
| `git status` | 新規：`pytest.ini`、`tests/`（`conftest.py`・`test_setup.py`・`test_api_helpers.py`・`test_semesters_api.py`・`test_subjects_api.py`）、`app/routes/subjects.py`。変更：`app/__init__.py`、`app/api_helpers.py`、`requirements.txt` のみ。`app/routes/semesters.py`・`app/models/`・`app/templates/`・`app/static/`・`migrations/`・`docs/`・`run.py`・`instance/` に変更なし |
| `git diff` | `app/__init__.py` は、`create_app` の引数と設定、Blueprintの登録だけ。`api_helpers.py` は、既存の関数の挙動を変えていない（`validate_required_string` の既存の引数の扱い） |

`.pytest_cache/` や `__pycache__/` が `git status` に表示される場合は、`.gitignore` を変更せず、報告する。**ブラウザでの確認は、このタスクにはない。**

## Komaの確認
1. `python -m pytest` を、自分で実行して、全件合格することを確認する
2. 開発用DBに、授業を1件登録し、確認して、消す（実際の学期のIDを使う）
```
python run.py          # 起動
curl -s $BASE/api/semesters          # 既存の学期の id を確認する
curl -s -X POST $BASE/api/subjects -H 'Content-Type: application/json' \
  -d '{"semester_id": <学期のid>, "subject_name": "テスト授業", "weekday": 0, "start_time": "09:00", "end_time": "10:00"}'
curl -s "$BASE/api/subjects?semester_id=<学期のid>"
sqlite3 instance/app.db "DELETE FROM subjects WHERE subject_name = 'テスト授業';"
```
期待：201で、8項目（`room`・`notes` は `null`）。一覧に、1件だけ出る。最後の `DELETE` で、`subjects` が0件に戻る。

## Git操作
**Git commit / push / ブランチ操作 / マージは行わない**（`git branch --show-current`、`git status`、`git diff` のような読み取りだけのコマンドは除く）。

## 注意
- **停止して報告する条件**（ファイルを変更せず、実装を止め、チャットで「問題点・発生理由・変更した場合の影響・推奨案（必要なら）」を報告する）
  - ブランチの不一致、作業ツリーの想定外の変更
  - 設計資料とこのTask MDの間に、矛盾・不足がある
  - 設計資料にない判断が必要になった（特に `docs/architecture.md` の「未決定事項」に触れる場合。Eventの `category` の保存値、Event自動生成の詳細、選択中の学期の共有方法など）
  - 「変更しない」と定めたもの（学期APIのコード、`migrations/`、`.gitignore` など）を変更しないと実装できない
  - 学期APIの回帰テストが、Task 003の仕様と食い違い、コードを直さないと合格しない
  - テストの実行の前後で、`instance/app.db` が変わった
  - テスト用DBを、`upgrade` で作れない（`migrations/` の問題）
- `flask db` コマンドを、一切実行しない
- 期待する結果と異なる結果が出た場合は、確認を飛ばさず、原因を直してから、すべての確認をやり直す
- 設計資料に書かれていない仕様は、自分で決めない
- 途中の承認ゲートはない。「Copilot確認手順」を実施したら、結果を報告して止まる
- 最後の報告に、次を含める：変更したファイル、各段階の `pytest` の件数、授業APIのテスト件数、警告の有無、開発用DBの前後のハッシュ、`git status`・`git diff --stat`
