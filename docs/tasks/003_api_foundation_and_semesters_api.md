# タスク003: API共通基盤と学期API

ブランチ：`feature/003-api-foundation`（Komaが作成・切替済みの状態で渡される）

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに停止して報告する。

## 目的
JSONを返すAPIの共通の土台（エラーの形式、JSON本文の受け取り、日付の検査など）を作り、その最初の利用として、学期のAPI（一覧・1件取得・作成）を作る。

画面はまだ作らない。確認は、`curl` でAPIを直接呼んで行う。このタスクで決めた共通の土台が、これ以降の授業・Event・TaskのAPIのすべてで使われる。

## このタスクで出てくる言葉
- **API**：画面のJavaScriptや `curl` が、JSONのやり取りをするためのURL。HTMLではなくJSONを返す。
- **エラーハンドラー**：404などのエラーが起きたときに呼ばれ、返す内容を作る関数。このタスクでは、`/api` 以下のエラーだけをJSONにする。
- **curl**：ターミナルからHTTPリクエストを送るコマンド。ブラウザを使わずに、APIの応答を確かめられる。

## 作成・変更するファイル

| 区分 | ファイル | 内容 |
|---|---|---|
| 新規 | `app/api_helpers.py` | API共通処理 |
| 新規 | `app/routes/semesters.py` | 学期のAPI（検証とJSON変換を含む） |
| 変更 | `app/__init__.py` | エラーハンドラーの登録と、学期のBlueprintの登録 |

次のファイルは、変更しない：`app/models/`、`app/config.py`、`app/extensions.py`、`app/routes/main.py`、`app/templates/`、`run.py`、`requirements.txt`、`migrations/`。

## やること

### 1. 守るAPI共通ルール（`docs/architecture.md` の「API共通ルール」が正本）
このタスクに関係する規則を、次に書く。食い違いに気づいた場合は、停止して報告する（「注意」を参照）。

- **URLとメソッド**：`/api/<複数形>`、`/api/<複数形>/<int:id>`。末尾に `/` を付けたURLは使わない（`/api/semesters/` は404）。使うメソッドは GET・POST・PATCH・DELETE（PUTは使わない）。まだ決まっていない操作（学期のPATCH・DELETE）は提供せず、405を返す
- **成功時**：一覧・1件取得は200、作成は201（作成したオブジェクトを返す）
- **Content-Type**：JSON本文を持つ **`POST` と `PATCH` だけ** が、`Content-Type: application/json`（`charset` 付きも可）を必須とする。`GET` と `DELETE` には要求せず、本文も読まない
- **本文はJSONのオブジェクト**でなければならない
  - JSONとして読めない、または `Content-Type` が違う場合は、400（`invalid_json`）
  - JSONとして読めても、オブジェクトでない場合（配列・文字列・数値・`true`/`false`・`null`）は、400（`validation_error`）。この場合、`fields` は付けない
- **JSONの形**：項目名は `snake_case` でDBのカラム名と同じ。包み（`{"data": ...}` など）を使わず、リソースをそのまま返す。一覧は配列。レスポンスには全項目を常に含める
- **リクエストで受け付ける項目**：リソースごとに定めた項目だけ。`id` などの読み取り専用の項目や、未知の項目が含まれていたら、400（`validation_error`）
- **日付**：`YYYY-MM-DD` を **厳密に** 検査する（0埋めあり、別の書式は受け付けない）。実在しない日付（`2026-02-30` など）は、400（`validation_error`）
- **CORS**：他のオリジンからのアクセスを許可する設定は行わない
- **エラーをJSONにする範囲**：URLのパスが `/api` または `/api/` で始まるリクエストのエラーだけ。**通常のHTMLページのエラー（`/` や `/api` 以外の存在しないURLなど）は、変更せず、Flaskの標準のHTMLのままにする**。判定はパスだけで行う
- **共通処理の置き場所**：共通処理は `app/api_helpers.py`、リソース固有の検証とJSON変換は `routes/semesters.py`。**モデル（`app/models/`）にAPI用の処理は持たせない**

### 2. `app/api_helpers.py`
`docs/architecture.md` の「API共通処理の補助モジュール」の責務のうち、**このタスクで使うものだけ** を作る。

- **エラーのJSONレスポンスを作る**：形式は「エラーの形式」のとおり。`code` とステータスの対応も、そのとおり
- **エラーハンドラーの登録**：`register_api_error_handlers(app)` という関数にまとめ、`create_app()` から呼ぶ
  - 対象は、404（`not_found`）、405（`method_not_allowed`）、500（`server_error`）の3つ。400と409は、このタスクではハンドラーを作らない（400は各routeが自分でJSONを返す。409は予約で、このタスクでは使わない）。ほかのHTTPエラー（413など、設計資料に定めのないもの）は、このタスクでは扱わない
  - どのハンドラーも、パスが `/api` または `/api/` で始まるときだけJSONを返す。それ以外のパスでは、受け取った例外をそのまま返し、Flask標準のHTMLにする
  - 500のハンドラーは、500（`InternalServerError`）に対して登録する。`Exception` 全体には登録しない（`debug=True` のときにデバッガ画面が出るのは、仕様どおり）
- **JSON本文の受け取り**：
  - `request.mimetype` が `application/json` でなければ、400（`invalid_json`）。`Content-Type` が違う場合にFlaskが自動で返す415にはしない
  - JSONとして読めなければ、400（`invalid_json`）
  - 読めても、オブジェクト（辞書）でなければ、400（`validation_error`、`fields` なし）
  - **`invalid_json` と、JSONの `null`（`validation_error`）を区別すること。** `request.get_json(silent=True)` は、どちらの場合も `None` を返すので、そのままでは区別できない
- **項目の共通検査**：未知の項目や `id` の拒否（`fields` に、その項目名で入れる）、必須の検査、文字列の型の検査
- **日付の変換**：`YYYY-MM-DD` の文字列を、Pythonの日付に変換する関数と、日付を文字列にする関数。形式の検査（半角数字、0埋め、全体一致）を先に行い、そのあとで実在する日付かを確かめる。**Python 3.11の `date.fromisoformat` は `20260921` のような別の書式も受け付けるため、形式の検査を別に行う**

**このタスクでは作らない**（使うタスクで追加する）：時刻・日時の変換、`PATCH` の「項目が1つもない」の検査、任意項目の空文字の `null` 化。

### 3. `app/routes/semesters.py`
- Blueprintを作る（名前は `semesters`、変数名は `semesters_bp`、`url_prefix` は `/api/semesters`）
- 次の3つのエンドポイントを作る（仕様は「学期APIの仕様」）
  - `GET /api/semesters`、`GET /api/semesters/<int:id>`、`POST /api/semesters`
- 学期の入力検証と、学期をJSONにする変換（`id`・`name`・`start_date`・`end_date` の辞書にする）を、このファイルの中に置く
- DBの操作は、Flask-SQLAlchemyの標準的な書き方で行う。`Semester` モデルは変更しない

### 4. `app/__init__.py`
- `create_app()` の中で、`register_api_error_handlers(app)` を呼ぶ
- 学期のBlueprintを登録する
- **既存の処理（`db.init_app`、モデルの読み込み、`migrate.init_app`、`main` のBlueprintの登録）は、変更しない**

### コメントの書き方
`.github/copilot-instructions.md` のとおり、日本語のコメントを入れる。特に次の4か所には、理由を書く。
- `invalid_json` と `null` を区別する処理（`silent=True` の注意）
- 学期名の正規表現を「全体一致」で検査している理由（前後の改行などを許さないため）
- 日付の形式検査を `fromisoformat` とは別に行う理由
- エラーハンドラーが `/api` 以下だけに働く理由

## 学期APIの仕様

| 操作 | 内容 | 成功時 |
|---|---|---|
| `GET /api/semesters` | 開始日の新しい順（開始日が同じなら、idの新しい順）の配列。0件なら `[]` | 200 |
| `GET /api/semesters/<int:id>` | 存在しなければ404（`not_found`） | 200 |
| `POST /api/semesters` | 本文は `name`・`start_date`・`end_date`（すべて必須） | 201（作成した学期） |
| `PATCH`・`DELETE` | 提供しない | 405（`method_not_allowed`） |

レスポンスの例（日本語は、Flask標準の設定により、`\uXXXX` の形で出力される。これは正しい動作で、変更しない）：

```json
{"id": 1, "name": "2026年度 後期", "start_date": "2026-09-21", "end_date": "2026-12-27"}
```

### 入力検証（`POST`）
1つでも満たさなければ、400（`validation_error`）。`fields` に、**誤りのあるすべての項目** を入れる。1つの項目に複数の誤りがある場合は、下の順で最初に見つかった1つだけを、その項目のメッセージにする。

| 項目 | 検査（この順） |
|---|---|
| `name` | ①必須（キーがない、`null`、`""`） ②文字列である ③50字以内 ④形式が正しい（下の「`name` の形式」のとおり） ⑤同じ `name` が登録済みでない（完全一致で比較） |
| `start_date`・`end_date` | ①必須（キーがない、`null`、`""`） ②文字列で、`YYYY-MM-DD` の形式かつ実在する日付 |
| `end_date`（関係） | `start_date` と `end_date` がどちらも正しい日付のときだけ検査する。`end_date` が `start_date` より後でなければ、`end_date` のエラー（同じ日も不可） |
| そのほか | `id` を含む、定められていない項目は、その項目名で `fields` に入れる |

**`name` の形式**：`[0-9]{4}年度 (前期|後期)` に**全体一致**すること。半角数字4桁、「年度」、半角スペース1つ、「前期」か「後期」で、前後に余分な文字・空白・改行を許さない。Pythonの正規表現の `\d` は全角数字も通すので、`[0-9]` を使う。

検査しないこと：名前の年度と期間の整合性、ほかの学期との期間の重なり。

### メッセージの文言（確認しやすいよう、このとおりにする）

| 場面 | `message` または `fields` の値 |
|---|---|
| `validation_error` 全体の `message` | `入力内容に誤りがあります` |
| 本文がオブジェクトでない（`message`） | `リクエストの本文は、JSONのオブジェクトにしてください` |
| `invalid_json`（`message`） | `リクエストの本文がJSONとして読めません。Content-Typeを application/json にして、JSONで送ってください` |
| `name` が必須 | `学期名は必須です` |
| `name` が文字列でない | `学期名は文字列で指定してください` |
| `name` が50字を超える | `学期名は50文字以内にしてください` |
| `name` の形式が違う | `学期名は「2026年度 前期」の形式で指定してください` |
| `name` が重複 | `同じ名前の学期がすでに登録されています` |
| `start_date` が必須／形式が違う | `開始日は必須です`／`開始日は実在する日付を「YYYY-MM-DD」の形式で指定してください` |
| `end_date` が必須／形式が違う | `終了日は必須です`／`終了日は実在する日付を「YYYY-MM-DD」の形式で指定してください` |
| `end_date` が `start_date` 以前 | `終了日は開始日より後にしてください` |
| 定められていない項目 | `この項目は指定できません` |
| 404（`/api/semesters/<id>` の学期がない） | `学期が見つかりません` |
| 404（それ以外の `/api` 以下のURL） | `URLが見つかりません` |
| 405 | `このURLでは、そのメソッドは使えません` |
| 500 | `サーバーでエラーが発生しました` |

### エラーの形式（`docs/architecture.md` の「エラー」のとおり）

```json
{"error": {"code": "validation_error",
           "message": "入力内容に誤りがあります",
           "fields": {"end_date": "終了日は開始日より後にしてください"}}}
```

`fields` は、`validation_error` で、項目ごとの誤りがあるときだけ付ける（本文がオブジェクトでない場合は付けない）。

| 状況 | ステータス | `code` |
|---|---|---|
| JSONが読めない、`Content-Type` が違う | 400 | `invalid_json` |
| 入力の誤り（本文がオブジェクトでない・必須漏れ・形式・型・範囲・重複・未知の項目） | 400 | `validation_error` |
| 存在しないIDやURL | 404 | `not_found` |
| 許可されていないメソッド | 405 | `method_not_allowed` |
| サーバー内部のエラー | 500 | `server_error` |

## やらないこと（このタスクの範囲外）
- 学期のUI、`main.js`・`api.js`・`semesters.js`などのJavaScript（`app/static/` を作らない）
- `base.html` の `scripts` ブロックの追加、`app/templates/` の変更
- Bootstrapの追加・変更、独自CSS、ブラウザの画面に関するすべて
- 授業・Event・TaskのAPI
- 学期の `PATCH`・`DELETE`（405のまま）
- 時刻・日時の変換、`PATCH` の空の検査、任意項目の空文字の `null` 化（使うタスクで追加する）
- 学期の期間の重なりの検査、名前の年度と期間の整合性の検査
- `Semester` モデルの変更、モデルへのAPI用処理（`to_dict()` など）の追加
- DBの構造を変える操作の一切。migrationの作成・適用、`migrations/` の変更。`flask db ...` は実行しない
- `pytest` などのテストの導入、`tests/`
- `pip install`、`requirements.txt` の変更（`flask-cors` などの新しいライブラリも使わない）
- CORSの設定
- `.gitignore`・`.vscode`・Git設定の変更
- Git commit / push / ブランチ操作 / マージ（`git branch --show-current`、`git status` のような読み取りだけのコマンドは除く）
- 設計資料（`docs/requirements.md`・`architecture.md`・`ui_ux.md`）と `.github/copilot-instructions.md` の変更

## 参照
- `docs/architecture.md`：「API共通ルール」の全節（URLとメソッド、リクエストとレスポンス、日付・時刻・日時、エラー、エラーをJSONにする範囲、補助モジュール、学期API）、「データ設計」の `Semester`、「未決定事項」、「ディレクトリ構成」
- `docs/requirements.md`：「学期」
- `docs/ui_ux.md`：「学期（タブと登録）」（エラーの `fields` の項目名 `name`・`start_date`・`end_date` が、画面の入力欄に対応する）
- `.github/copilot-instructions.md`：進め方と、設計上の問題を見つけたときの手順

## 完了の確認方法（Copilotが行う）

### 準備
1. `sqlite3 instance/app.db "SELECT COUNT(*) FROM semesters;"` が **`0`** であることを確認する。**0でなければ、何も変更せずに停止して報告する**（既存のデータには触れない）
2. `.venv` が有効な状態で、`python run.py` を起動する（5001番がすでに使われている場合は、変更せずに報告する）
3. 別のターミナルで、次を設定する

```
BASE=http://127.0.0.1:5001
J='Content-Type: application/json'
```

以降の `curl` は、`-s -w '\nHTTP %{http_code}\n'` を付けて、本文のあとにステータスを表示する。

### A. 正常系
```
# A1 空の一覧（ヘッダーも確認する）
curl -s -i $BASE/api/semesters

# A2〜A5 作成（A4はA3と期間が重なる。A5はA4と開始日が同じ）
curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -H "$J" -d '{"name":"2099年度 前期","start_date":"2099-04-06","end_date":"2099-07-20"}'
curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -H "$J" -d '{"name":"2099年度 後期","start_date":"2099-09-21","end_date":"2099-12-27"}'
curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -H "$J" -d '{"name":"2100年度 前期","start_date":"2099-12-01","end_date":"2100-03-31"}'
curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -H "$J" -d '{"name":"2100年度 後期","start_date":"2099-12-01","end_date":"2100-03-31"}'

# A6 一覧、A7 1件（A2のidを使う）
curl -s -w '\nHTTP %{http_code}\n' $BASE/api/semesters
curl -s -w '\nHTTP %{http_code}\n' $BASE/api/semesters/<A2のid>
```

| 番号 | 期待する結果 |
|---|---|
| A1 | 200、`Content-Type: application/json`、本文は `[]` |
| A2〜A5 | いずれも **201**。本文は `id`（整数）・`name`・`start_date`・`end_date` の4項目だけ。A4（期間が重なる）も201 |
| A6 | 200。4件が、**`2100年度 後期` → `2100年度 前期` → `2099年度 後期` → `2099年度 前期`** の順（開始日の新しい順。開始日が同じA4とA5は、idの新しいA5が先） |
| A7 | 200。A2の応答と同じ内容 |

### B. エラー系
```
# B1 同じ名前
curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -H "$J" -d '{"name":"2099年度 前期","start_date":"2099-04-06","end_date":"2099-07-20"}'
# B2 形式が違う名前、B3 全角数字、B4 末尾に改行
curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -H "$J" -d '{"name":"前期","start_date":"2102-04-06","end_date":"2102-07-20"}'
curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -H "$J" -d '{"name":"２１０２年度 前期","start_date":"2102-04-06","end_date":"2102-07-20"}'
curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -H "$J" -d '{"name":"2102年度 前期\n","start_date":"2102-04-06","end_date":"2102-07-20"}'
# B5 51文字
python3 -c 'import json;print(json.dumps({"name":"あ"*51,"start_date":"2102-04-06","end_date":"2102-07-20"}))' | curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -H "$J" -d @-
# B6 空のオブジェクト、B7 型が違う
curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -H "$J" -d '{}'
curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -H "$J" -d '{"name":123,"start_date":20990406,"end_date":null}'
# B8 日付の形式（4通り）
for d in "20990406" "2099/04/06" "2099-4-6" "2099-02-30"; do curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -H "$J" -d "{\"name\":\"2102年度 前期\",\"start_date\":\"$d\",\"end_date\":\"2102-07-20\"}"; done
# B9 終了日が開始日と同じ／前
curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -H "$J" -d '{"name":"2102年度 前期","start_date":"2102-04-06","end_date":"2102-04-06"}'
curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -H "$J" -d '{"name":"2102年度 前期","start_date":"2102-04-06","end_date":"2102-04-05"}'
# B10 定められていない項目、id
curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -H "$J" -d '{"name":"2102年度 前期","start_date":"2102-04-06","end_date":"2102-07-20","color":"red"}'
curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -H "$J" -d '{"id":5,"name":"2102年度 前期","start_date":"2102-04-06","end_date":"2102-07-20"}'
# B11 本文がオブジェクトでない（5通り）
for b in '[]' 'null' '"abc"' '123' 'true'; do curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -H "$J" -d "$b"; done
# B12 JSONとして読めない
curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -H "$J" -d '{"name":'
# B13 Content-Typeが違う／ない（curl -d の既定は、フォーム形式）
curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -H 'Content-Type: text/plain' -d '{"name":"2102年度 前期","start_date":"2102-04-06","end_date":"2102-07-20"}'
curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters -d '{"name":"2102年度 前期","start_date":"2102-04-06","end_date":"2102-07-20"}'
# B14 存在しないID・URL
for u in /api/semesters/99999 /api/semesters/abc /api/unknown /api/semesters/ /api; do curl -s -w '\nHTTP %{http_code}\n' $BASE$u; done
# B15 提供しないメソッド（DELETEとPATCHには、Content-Typeを付けなくてよい）
curl -s -w '\nHTTP %{http_code}\n' -X DELETE $BASE/api/semesters/1
curl -s -w '\nHTTP %{http_code}\n' -X PATCH $BASE/api/semesters/1
curl -s -w '\nHTTP %{http_code}\n' -X PUT $BASE/api/semesters
curl -s -w '\nHTTP %{http_code}\n' -X POST $BASE/api/semesters/1 -H "$J" -d '{}'
```

| 番号 | 期待する結果（いずれも、本文は「エラーの形式」のJSON） |
|---|---|
| B1 | 400 `validation_error`。`fields` は `name` だけ（同名） |
| B2〜B4 | 400 `validation_error`。`fields` は `name` だけ（形式）。**B4が201になった場合は、全体一致になっていない** |
| B5 | 400 `validation_error`。`fields` は `name` だけ（50字） |
| B6 | 400 `validation_error`。`fields` に `name`・`start_date`・`end_date`（すべて必須） |
| B7 | 400 `validation_error`。`name`（文字列でない）、`start_date`（形式）、`end_date`（必須）の3つ |
| B8 | 4通りとも、400 `validation_error`。`fields` は `start_date` だけ。**`20990406` が201になった場合は、形式の検査が足りない** |
| B9 | どちらも400 `validation_error`。`fields` は `end_date` だけ |
| B10 | どちらも400 `validation_error`。`fields` は `color`、`id` だけ（`この項目は指定できません`） |
| B11 | 5通りとも、400 `validation_error`。**`fields` は付かない**。`null` が `invalid_json` になっていない |
| B12 | 400 `invalid_json` |
| B13 | どちらも400 `invalid_json`（415にならない） |
| B14 | 5つとも、404 `not_found`（JSON）。`/api/semesters/99999` のメッセージは `学期が見つかりません`、それ以外は `URLが見つかりません` |
| B15 | 4つとも、405 `method_not_allowed`（JSON）。**`DELETE` と `PATCH` が400にならない**（`Content-Type` を要求されていない） |

### C. 通常のページと、CORS
```
# C1 トップページ、C2 存在しないページ、C3 トップページへのPOST
curl -s -i $BASE/
curl -s -i $BASE/no-such-page
curl -s -i -X POST $BASE/
# C4 CORS（Originを付けたGETと、事前確認のOPTIONS）
curl -s -i -H "Origin: http://example.com" $BASE/api/semesters
curl -s -i -X OPTIONS $BASE/api/semesters -H "Origin: http://example.com" -H "Access-Control-Request-Method: POST"
```

| 番号 | 期待する結果 |
|---|---|
| C1 | 200、`Content-Type: text/html`。「カレンダー」「授業」「課題・タスク」を含む（Task 002のまま） |
| C2 | 404、**`Content-Type: text/html`**（JSONではない） |
| C3 | 405、**`Content-Type: text/html`**（JSONではない） |
| C4 | どちらの応答にも、`Access-Control-` で始まるヘッダーがない |

### D. 後片付けと範囲の確認
1. `curl -s $BASE/api/semesters` で、A2〜A5の4件だけがあり、**エラー系（B）で追加されたデータがない**ことを確認する
2. サーバーを停止し、`lsof -i :5001` の出力が空であることを確認する
3. 確認用のデータだけを削除し、0件に戻す（`sqlite3` の `DELETE` を使う。ほかのデータには触れない）

```
sqlite3 instance/app.db "DELETE FROM semesters WHERE name LIKE '2099年度%' OR name LIKE '2100年度%' OR name LIKE '2102年度%';"
sqlite3 instance/app.db "SELECT COUNT(*) FROM semesters;"     # 0 になること
```

4. `git status` で、次のとおりになっている
   - 新規：`app/api_helpers.py`、`app/routes/semesters.py`
   - 変更：`app/__init__.py` のみ
   - `app/models/`、`app/templates/`、`app/static/`、`run.py`、`requirements.txt`、`migrations/`、`instance/` に変更がない
5. 変更したファイルが、このタスクの「やること」の範囲内だけである

## 確認ポイント（Komaが行う）
Copilotの報告を受けたあと、Komaが `python run.py` で起動して確認する。

- Chromeで `http://127.0.0.1:5001/api/semesters` を開くと、`[]` が表示される
- Chromeで `http://127.0.0.1:5001/` を開くと、Task 002と同じ3つのモードの画面が表示される
- `http://127.0.0.1:5001/api/unknown` はJSONのエラー、`http://127.0.0.1:5001/no-such-page` はFlask標準のHTMLの404が表示される
- ターミナルで、`curl -s -X POST http://127.0.0.1:5001/api/semesters -H 'Content-Type: application/json' -d '{}'` が400の `validation_error`、`curl -s -X DELETE http://127.0.0.1:5001/api/semesters/1` が405の `method_not_allowed` を返す
- （任意）学期を1件作成して一覧に出ることを確認し、作成した場合は、後片付けと同じ `DELETE` で削除する

## 注意
- **停止して報告する条件**（ファイルを変更せず、実装を止め、チャットで「問題点・発生理由・変更した場合の影響・推奨案（必要なら）」を報告する）
  - Task MDに書かれたブランチ名と、実際のブランチが異なる
  - 作業開始前の `git status` に、想定外の変更がある
  - 設計資料（`docs/architecture.md`・`requirements.md`・`ui_ux.md`）とこのTask MDの間に、矛盾・不足がある
  - 設計資料にない判断が必要になった。特に、`docs/architecture.md` の「未決定事項」に書かれた項目に触れる場合
  - モデル、`requirements.txt`、migrationなど、「変更しない」と定めたものを変更しないと実装できない
  - 確認前の `semesters` が0件でない、または5001番がすでに使われている
- 上の表の「期待する結果」と異なる応答が出た場合は、確認を飛ばさず、原因を直してから、すべての確認をやり直す
- 設計資料に書かれていない仕様は、自分で決めない
- このタスクに、途中の承認ゲートはない。完了の確認方法を実施したら、結果を報告して止まる（Komaの確認は、そのあとに行う）
