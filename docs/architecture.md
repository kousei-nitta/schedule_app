# アーキテクチャ・技術選定

> このファイルは設計上の正本です。変更が必要な場合は `.github/copilot-instructions.md` の変更手順に従い、開発者（Koma）の承認を得てから更新します。

## 技術スタック
| 項目 | 採用 | 備考 |
|---|---|---|
| 言語 | Python 3.11 | プロジェクト専用の仮想環境 `.venv` を使用 |
| バックエンド | Flask | |
| DB | SQLite | 単一ユーザー・ローカル1ファイル。同時アクセスの考慮は不要 |
| ORM | Flask-SQLAlchemy | |
| DBスキーマ変更 | Flask-Migrate（内部でAlembicを使用） | モデルの変更をmigrationファイルとして記録し、既存データを保ったままテーブルを更新する。方式の詳細は「DBスキーマ変更の方式」を参照 |
| テンプレート | Jinja2（Flask標準） | |
| フロントエンドJS | バニラJavaScript（ES modules） | `fetch` でFlaskのAPIを呼ぶ。構成と規則は「JavaScriptの構成」、APIの規則は「API共通ルール」を参照 |
| カレンダー描画 | FullCalendar | MIT・無料範囲の週／月／一覧表示のみ使用。リソース／タイムライン表示などの有料機能は使わない |
| CSS（UI部品） | Bootstrap 5.3.8 | CDN（jsDelivr）から、バージョンを固定して読み込む（「Bootstrapの読み込み」を参照）。タブ（モード切り替え）、モーダル（詳細パネル）、バッジ（カテゴリ表示）などに利用 |
| 認証 | なし | ログイン機能は実装しない |
| 自動テスト | pytest | APIのテストに使う。配置・DB・実行方法は「自動テスト（pytest）」を参照 |
| 起動 | `run.py` | 開発用サーバーを `127.0.0.1:5001`（`debug=True`）で起動する。5001番を使うのは、macOSではAirPlayレシーバーが5000番を使うことがあるため |

制約：費用をかけない（大学の授業の一環のため）。

### Bootstrapの読み込み（確定）
- **CDN（jsDelivr）から読み込み、バージョンを固定する。** 固定するバージョンは **5.3.8**（2026年10月時点の最新の安定版）。`latest` など、バージョンを固定しないURLは使わない。
- 読み込むのは2つ。CSS（`bootstrap.min.css`）を `<head>` 内に、JavaScript（`bootstrap.bundle.min.js`。Popperを含む）を `</body>` の直前に置く。
- 改ざんの検出用に `integrity`（ハッシュ値）と `crossorigin="anonymous"` を付ける。
- バージョンを変えるときは、この資料、Task MD、タグの `integrity` を、そろえて更新する（開発者の承認を得る）。`integrity` の値は、公式サイトの掲載値を使う。

```html
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB" crossorigin="anonymous">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js" integrity="sha384-FKyoEForCGlyvwx9Hj09JcYn3nv7wiPVlz7YYwJrWVcXK/BmnVDxM+D2scQbITxI" crossorigin="anonymous"></script>
```

## 未決定事項
現時点で決まっていない事項の一覧。**実装側（Copilot）は、これらを自分の判断で決めない。** 該当する実装に入る前に、開発者（Koma）が決定し、このファイルを更新する。決めるタイミングは、各項目に書いたとおり。

| 項目 | 内容 | 決めるタイミング |
|---|---|---|
| categoryの保存値 | `Event.category`・`Task.category` に保存する値（日本語の文字列そのままか、コード値か）。入力値の制限（バリデーション）の方式も含む | 登録・表示を実装するタスクの前 |
| 日付をまたぐアルバイト | 例：22:00〜翌2:00。Eventは日付1つ＋開始／終了時刻のため、終了が開始より前の入力を許すか、日をまたぐ予定をどう表すか | アルバイトの登録を実装するタスクの前 |
| 授業削除時のEvent・Task削除方式 | 「授業を削除したら、紐づくEvent・Taskもまとめて削除する」という挙動は決定済み。未決定なのは**実装方式**（ORMの `cascade`、削除処理を明示的に書く、DB側の `ondelete` など）。注意点：SQLiteは既定では外部キー制約を強制しない（`PRAGMA foreign_keys`）。`relationship` に `cascade` を指定せず親を削除すると、子の外部キーがNULLになって残る場合がある | 削除を実装するタスクの前 |
| 学期の変更・削除時の扱い | 学期の期間を修正したときのEventの作り直し、学期を削除したときの授業・Event・Taskの扱い、授業の所属学期の付け替え | 授業モードの編集・削除を実装するタスクの前 |
| 一覧表示の「今日以降」の範囲 | FullCalendarのリスト表示は期間を指定する方式のため、期間の上限（例：今日から3か月）が必要 | カレンダー表示を実装するタスクの前 |
| FullCalendarの読み込み方法 | CDNから読み込むか、ファイルを `app/static/` に置くか（Bootstrapは、CDN方式で確定済み） | カレンダー表示を実装するタスクの前 |
| 選択中の学期の共有方法 | 授業など他のモジュールが、授業モードで選択中の学期を知る方法（例：`semesters.js` が `CustomEvent` を発行する、関数を `export` する） | 授業の一覧・登録フォームを実装するタスクの前 |
| フォーム・エラー表示・日付補助の共通化 | 2つ目のフォームを作るときに、エラー表示や日付の補助処理を、共通のファイル（例：`ui.js`・`dates.js`）へ切り出すか | 2つ目のフォームを実装するタスクの前 |

## データ設計
テーブルは4つ（Semester・Subject・Event・Task）。関係は **Semester → Subject → Event / Task**。

### 共通の約束
- 型は SQLAlchemy の型で書く。`String(n)` の n は最大文字数。
- 日付・時刻（Date／Time／DateTime）は、タイムゾーン情報なし（naive）のローカル時刻として扱う。タイムゾーンの変換はしない。
- 主キー `id` は整数の自動採番。
- 初期値（`default`）は SQLAlchemy 側（Python側）で指定する。DB側の `server_default` は、現時点のモデルでは使わない（データが入ったテーブルにNOT NULLのカラムを後から追加する場合は、そのときのmigrationで別途検討する）。
- 現時点のモデルには、インデックス・unique制約・check制約を定義しない（制約の命名規則だけは先に定める。「制約の命名規則」を参照）。
- 削除時の連動（`cascade`・`ondelete`）は、未決定事項のため指定しない。

### Semester（学期）　テーブル名：`semesters`
学期を表す。UIの学期タブ、「新しい学期の登録」、学期ごとの期間管理に対応する。

| フィールド | 型 | NULL | 内容 |
|---|---|---|---|
| id | Integer（主キー） | 不可 | |
| name | String(50) | 不可 | 学期名。形式は「2026年度 前期」（「学期API」を参照）。DBには文字列だけを保存し、年度・種別の別カラムは持たない |
| start_date | Date | 不可 | 学期の開始日 |
| end_date | Date | 不可 | 学期の終了日 |

### Subject（授業）　テーブル名：`subjects`
授業モードで登録する「パターン」そのもの。必ず1つの学期に所属する。

| フィールド | 型 | NULL | 内容 |
|---|---|---|---|
| id | Integer（主キー） | 不可 | |
| semester_id | Integer、外部キー → `semesters.id` | 不可 | 所属する学期 |
| subject_name | String(100) | 不可 | 科目名 |
| room | String(100) | 可 | 教室 |
| weekday | Integer | 不可 | 曜日。**0=月曜〜6=日曜**（Pythonの `date.weekday()` と同じ）。JavaScript・FullCalendarの曜日は0=日曜なので、受け渡しの際は変換が必要 |
| start_time | Time | 不可 | 開始時刻 |
| end_time | Time | 不可 | 終了時刻 |
| notes | Text | 可 | 詳細／メモ |

### Event（予定／時間型）　テーブル名：`events`
授業の毎週分・アルバイト・その他（時間指定あり）の実際の1件1件。

| フィールド | 型 | NULL | 内容 |
|---|---|---|---|
| id | Integer（主キー） | 不可 | |
| subject_id | Integer、外部キー → `subjects.id` | 可 | 授業由来のEvent（自動生成・単発の授業とも）のみ値が入る。アルバイト／その他はNULL |
| category | String(20) | 不可 | 授業／アルバイト／その他（保存値は未決定事項） |
| date | Date | 不可 | 日付 |
| start_time | Time | 不可 | 開始時刻 |
| end_time | Time | 不可 | 終了時刻 |
| title | String(200) | 不可 | タイトル |
| room | String(100) | 可 | 教室（主に授業用） |
| employer | String(100) | 可 | 派遣会社（主にアルバイト用） |
| notes | Text | 可 | 詳細／メモ |
| is_generated | Boolean | 不可 | 初期値 `False`。授業の学期一括登録で自動生成したEventは `True`。カレンダーから追加した単発の授業（補講など）、アルバイト、その他は `False` |

### Task（課題・タスク／期限型）　テーブル名：`tasks`
課題と、その他（締切のみ）の実際の1件1件。

| フィールド | 型 | NULL | 内容 |
|---|---|---|---|
| id | Integer（主キー） | 不可 | |
| subject_id | Integer、外部キー → `subjects.id` | 可 | 対象授業がある場合のみ値が入る。その他はNULL |
| category | String(20) | 不可 | 課題／その他（保存値は未決定事項） |
| title | String(200) | 不可 | 課題名／タイトル |
| due_datetime | DateTime | 不可 | 締切日時 |
| notes | Text | 可 | 詳細／メモ |
| is_completed | Boolean | 不可 | 初期値 `False`（未完了） |

状態は「未完了」「完了」の2つのみ（中間状態は設けない）。

### 関係
- Semester 1 — n Subject（Subjectは必ず1つのSemesterに所属）
- Subject 1 — 0..n Event（授業由来のEvent）
- Subject 1 — 0..n Task（対象授業としての参照）
- ORMの `relationship`（`back_populates` で双方向）：`Semester.subjects` ↔ `Subject.semester`、`Subject.events` ↔ `Event.subject`、`Subject.tasks` ↔ `Task.subject`。`cascade` は指定しない。

### 繰り返し予定の扱い
授業を登録すると、所属する学期の期間（`start_date`〜`end_date`）内で `weekday` に一致する日の予定を、**Eventへ実際の行としてまとめて書き込む**（`is_generated=True`）。
パターンだけ持たせて表示時に計算する方式は採らない。

編集・削除の仕様は、次の操作に対応する。
- 授業全体の編集 → `subject_id` が一致し、**`is_generated=True`** で、日付が今日以降のEventを、設定どおりに作り直す。カレンダーからその日だけ編集した自動生成のEventも `is_generated=True` のままなので、この作り直しで設定どおりに戻る。個別に削除した日も戻る。**`is_generated=False` のEvent（カレンダーから追加した単発の授業など）は対象外で、そのまま残る。**
- 特定の日だけの編集（カレンダーから） → その1行だけ更新する。`is_generated` は変えない。
- カレンダーから単発の授業（補講など）を追加 → 授業一覧から選んだ授業の `subject_id` を持つ `is_generated=False` のEventとして追加する。
- 授業の削除 → `subject_id` が一致するEvent・Taskを、`is_generated` の値によらず、過去分を含めてまとめて削除する（実装方式は未決定事項）。

規模の目安：1学期13週 × 授業10科目程度（数百行）。

## DBスキーマ変更の方式（確定）
**Flask-Migrate** を採用する。

採用理由：PDCAで機能を追加していく過程で、データモデルやDBスキーマを変更する可能性がある。そのとき、入力済みの授業・課題・アルバイトのデータを失わずにテーブルを更新できるようにするため。また、migration（スキーマ変更の履歴管理）というWebアプリ開発の概念を学ぶ目的もある。

ルール：
- テーブルの作成・変更は、必ずmigrationを通して行う。`db.create_all()` は使わない（migrationの履歴とDBの実際の状態が食い違い、migrationが失敗しやすくなるため）。
- カラムの追加・変更などのスキーマ変更は、このファイルの「データ設計」の承認なしに行わない。
- 自動生成されたmigrationファイルはレビュー対象。内容を確認し、Komaの承認を得てから適用する。
- `migrations/` はGit管理対象。`instance/app.db` はGit管理対象外。
- 制約には一貫した命名規則を付ける（下記「制約の命名規則」）。
- 自動テスト用のDBも、`db.create_all()` ではなく、migration（`upgrade`）で作る（「自動テスト（pytest）」を参照）。
- SQLiteはカラムの変更・削除などの `ALTER TABLE` に制約があるため、Alembicのbatchモード（`render_as_batch=True`）を明示的に有効にする。

### 制約の命名規則（naming convention）
SQLAlchemyの `MetaData` にnaming conventionを設定し、主キー・外部キー・unique・index・checkの名前を、一貫した規則で自動的に付ける。

理由：SQLiteは `ALTER TABLE` に制約があり、カラムの変更などはbatchモード（テーブルを作り直す方式）で行う。このとき名前のない制約は、後から追加・削除する対象にしにくい（外部キーの追加・削除で「制約に名前が必要」というエラーになりやすい）。初期migrationの前に定めるのは、後から入れても、すでにできた名前なしの制約には名前が付かないため。

規則（仕様）：

```python
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```

設定場所：`app/extensions.py` で `db = SQLAlchemy(metadata=MetaData(naming_convention=NAMING_CONVENTION))` とする。

現在のモデルで作られる名前（初期migrationの確認に使う）：
- 主キー：`pk_semesters`、`pk_subjects`、`pk_events`、`pk_tasks`
- 外部キー：`fk_subjects_semester_id_semesters`、`fk_events_subject_id_subjects`、`fk_tasks_subject_id_subjects`
- index・unique・check：現時点では作らない

注意：checkを定義する場合は、`ck` の規則が `constraint_name` を使うため、制約に明示的な名前が必要になる。`Boolean` などの型にcheck制約を自動で作らせない（`create_constraint` は既定のまま使わない）。

### Flask-Migrateの操作の意味
アプリのコードは `app/` パッケージで、`flask --app app db ...` の形で実行する。

| コマンド | 何をするか | 使うタイミング |
|---|---|---|
| `flask db init` | migrationの作業フォルダ `migrations/` を作る。**テーブルは作らない。** データベースにも変更を加えない | プロジェクトで1回だけ |
| `flask db migrate -m "説明"` | モデルの定義と現在のDBを比べ、差分を埋めるmigrationファイルを `migrations/versions/` に自動生成する。テーブルやデータは変更されない。自動生成なので内容の確認が必要 | モデルを変更したとき |
| `flask db upgrade` | migrationファイルをDBに適用する。**ここで初めてテーブルが作られる／変更される** | migrateの内容を確認したあと |
| `flask db downgrade` | 直近のmigrationの適用を1つ取り消す | 戻したいとき（通常は使わない） |
| `flask db current` | DBに今どのmigrationまで適用されているかを表示する | 状態の確認 |

流れは「モデルを変更 → `migrate`（ファイル生成） → 内容を確認 → `upgrade`（DBに適用）」。

## API共通ルール
画面のJavaScriptからFlaskを呼ぶAPIの共通ルール。今後のすべてのリソース（学期・授業・Event・Task）に適用する。

### URLとメソッド

| 操作 | メソッド | URL | 成功時 |
|---|---|---|---|
| 一覧 | GET | `/api/<複数形>` | 200（配列） |
| 1件取得 | GET | `/api/<複数形>/<int:id>` | 200（オブジェクト） |
| 作成 | POST | `/api/<複数形>` | 201（作成したオブジェクト） |
| 一部の項目を更新 | PATCH | `/api/<複数形>/<int:id>` | 200（更新後のオブジェクト） |
| 削除 | DELETE | `/api/<複数形>/<int:id>` | 204（本文なし） |

- リソース名は小文字の複数形（`semesters`・`subjects`・`events`・`tasks`）。動詞はURLに入れない（例：課題の完了は `PATCH /api/tasks/<id>` で `{"is_completed": true}` を送る）
- 末尾に `/` を付けたURLは使わない（`/api/semesters/` は404）
- 絞り込みはクエリで指定する（例：`/api/subjects?semester_id=1`）
  - クエリの値が不正な場合（整数であるべき値が整数でない、など）は、400（`validation_error`）。`fields` にクエリ名を入れる
  - リソースごとに定めていない未知のクエリは、無視する
- 更新はPATCHだけを使い、PUTは使わない
- まだ決まっていない操作（例：学期のPATCH・DELETE）は、提供しない（405を返す）
- 他のオリジンからのアクセスを許可する設定（CORS）は行わない
- IDを受け取るURLは、`<int(max=MAX_ID):id>` の形で、IDの上限を指定する（上の表の `<int:id>` は、この上限つきの形を指す）
  - 上限は、SQLiteのINTEGERの最大値 **`9223372036854775807`**。`app/api_helpers.py` の `MAX_ID` に定義する。これを超える数をDBに渡すとエラーになるため
  - `MAX_ID` は、ルールの文字列を作るときに、数値として埋め込む（例：`f"/<int(max={MAX_ID}):semester_id>"`）
  - 上限を超える値は、URLに一致しないものとして、404（`not_found`）になる（「404の使い分け」を参照）

### リクエストとレスポンス（JSON）
- **Content-Type**：JSON本文を持つ `POST` と `PATCH` だけが、`Content-Type: application/json`（`charset` 付きも可）を必須とする。違う場合は400（`invalid_json`）。`GET` と `DELETE` には要求せず、本文も読まない
- `POST`・`PATCH` の本文は、JSONの**オブジェクト**でなければならない
  - JSONとして読めない場合は、400（`invalid_json`）
  - JSONとして読めても、オブジェクトでない場合（配列・文字列・数値・`true`/`false`・`null`）は、400（`validation_error`）
  - `PATCH` で項目が1つもない場合（`{}`）も、400（`validation_error`）
- 項目名は `snake_case` で、DBのカラム名と同じ
- 包み（`{"data": ...}` など）は使わず、リソースをそのまま返す。一覧は配列
- レスポンスには、そのリソースの全項目を常に含める（値がなければ `null`）
- リクエストで受け付けるのは、リソースごとに定めた項目だけ。`id` などの読み取り専用の項目や、未知の項目が含まれていたら、400（`validation_error`）
- 任意項目の空文字 `""` は、`null` として扱う。必須項目の空文字は、必須のエラー
- 値の型が違う場合（文字列の項目に数値、など）も、400（`validation_error`）
- **文字列**
  - 自由入力の文字列（科目名・教室・メモ・タイトルなど）は、前後の空白（全角を含む）を取り除いてから、検査・保存する。必須項目は、取り除いた結果が空なら、必須のエラー。任意項目は、空なら `null`
  - 形式を厳密に検査する項目（学期名・日付・時刻）は、取り除かず、そのまま検査する（前後の空白は、形式の誤り）
  - 長さの上限は、取り除いたあとの文字数で数える。上限は、DBの `String(n)` に合わせる
- **整数**：JSONの整数だけを受け付ける。真偽値（`true`／`false`）・小数・文字列は、型の誤り
- **ほかのリソースのIDを参照する項目**（例：`semester_id`）：整数で、1〜`MAX_ID`。範囲外の場合と、該当するデータがない場合は、どちらも、その項目の誤りとして、400（`validation_error`）にする（404にしない。404は、URLの先のデータがない場合）。DBへの問い合わせは、範囲内のときだけ行う
- 一覧の並びは、リソースごとに定める

### 日付・時刻・日時

| 種類 | 形式 | 例 |
|---|---|---|
| 日付 | `YYYY-MM-DD` | `2026-09-21` |
| 時刻 | `HH:MM`（24時間、秒なし） | `09:00` |
| 日時 | `YYYY-MM-DDTHH:MM`（タイムゾーンなし） | `2026-10-12T23:59` |
| 曜日 | 整数。0=月曜〜6=日曜（DBと同じ） | `0` |

- 形式は厳密に検査する（0埋めあり。別の書式は受け付けない）。実在しない日付（`2026-02-30` など）は、400（`validation_error`）。Python 3.11の `fromisoformat` は他の書式も受け付けるため、形式の検査は別に行う
- 時刻は、`00:00`〜`23:59` の実在する時刻だけを受け付ける。`24:00`・`9:00`・`09:00:00`・`0900`・全角の数字などは、400（`validation_error`）。Pythonの `time.fromisoformat` は他の書式も受け付けるため、日付と同じく、形式の検査を先に別に行う
- 時刻に、業務上の制限（授業のプルダウンの9〜19時・1時間刻みなど）を、APIでは設けない。そのような制限は、画面（UI）の側で行う
- 曜日の変換（JavaScriptやFullCalendarは0=日曜）は、画面側のJavaScriptで行う

### エラー
形式：

```json
{"error": {"code": "validation_error",
           "message": "入力内容に誤りがあります",
           "fields": {"end_date": "終了日は開始日より後にしてください"}}}
```

`code` は英語の固定値、`message` は画面に出せる日本語。`fields` は `validation_error` のときに、項目ごとの誤りがあれば付き、項目名とメッセージの組になる。本文がオブジェクトでない場合のように、特定の項目に結びつかない誤りでは付けない。

| 状況 | ステータス | code |
|---|---|---|
| JSONが読めない、`Content-Type` が違う | 400 | `invalid_json` |
| 入力の誤り（本文がオブジェクトでない・必須漏れ・形式・型・範囲・重複・未知の項目） | 400 | `validation_error` |
| 存在しないIDやURL | 404 | `not_found` |
| 許可されていないメソッド | 405 | `method_not_allowed` |
| 他のデータとの関係で実行できない操作 | 409 | `conflict`（予約。必要になったとき使う） |
| サーバー内部のエラー | 500 | `server_error` |

### 404の使い分け
- **URL自体が存在しない、IDの形式が不正（`abc` など）、IDが上限（`MAX_ID`）を超える**場合：共通のエラーハンドラーが、「URLが見つかりません」を返す
- **URLは正しいが、対象のデータが存在しない**場合（形式が正しく、上限以内のID）：各リソースのrouteが、そのリソースのメッセージで `not_found` を返す（例：学期なら「学期が見つかりません」）
- 共通のエラーハンドラーは、特定のリソースの情報を持たない

### エラーをJSONにする範囲
- JSONで返すのは、**URLのパスが `/api` または `/api/` で始まるリクエストのエラーだけ**（404・405・400・409・500を含む）。判定はパスだけで行う
- **通常のHTMLページのエラーは、変更しない。** `/` や、`/api` 以外の存在しないURLなどは、Flaskの標準のHTMLのままにする
- **想定内のエラー**（400・404・405・409）は、`debug=True` でも、常にJSONで返す
- **予期しない例外**（コードの不具合など）は、`debug=False`（通常の動作）では、500のJSONで返す
- **開発中の注意**：`run.py` は `debug=True` で起動するため、予期しない例外が起きると、500のJSONではなく、Flaskのデバッガ画面（HTML）が表示されることがある。これは開発用の動作で、APIのエラー仕様（JSON）を変えるものではない。500のJSON化は仕様として定めるが、開発中の確認の必須項目にはしない

### API共通処理の補助モジュール：`app/api_helpers.py`
- 配置：`app/` 直下（`extensions.py`・`config.py` と同じ階層）。各routeから使う共通部品で、routeではない
- 責務：
  - エラーのJSONレスポンス（上記の形式とステータス）を作る
  - `/api` 以下のエラーをJSONにするエラーハンドラーの登録（`create_app()` から呼ぶ）
  - JSON本文の受け取り（`Content-Type` の検査、オブジェクトであることの検査）
  - 項目の共通検査（未知の項目や `id` の拒否、必須・型、空文字の `null` 化）
  - 日付・時刻・日時の文字列と、Pythonの値との相互変換（厳密な形式の検査を含む）
  - IDの上限の定数 `MAX_ID` を定義する
  - 文字列・整数の項目単位の検証（必須／任意、最大長、前後の空白の除去、整数の範囲。真偽値は整数として扱わない）
  - 時刻の変換と検証（`parse_time`・`format_time`・必須の時刻の項目単位の検証）
- 項目単位の検証関数は、`(値, エラーメッセージ)` の組を返す（正常なら、エラーメッセージは `None`）。メッセージの文言は、呼び出し側（route）が渡す
- 共通関数の追加・拡張で、すでにあるAPIの挙動を変えない。挙動が変わる処理（前後の空白の除去など）は、引数で指定したときだけ行う
- **DBの操作は行わない。** このモジュールが扱うのは、API共通の処理とIDの上限の定数だけ。データの取得・保存は、各route（`routes/<名前>.py`）が担当する
- リソース固有の検証（例：学期名の形式）と、モデルをJSONにする変換は、各リソースのroute（`routes/<名前>.py`）に置く。モデルにAPI用の処理は持たせない

### 学期API（`/api/semesters`）

| 操作 | 提供 | 内容 |
|---|---|---|
| `GET /api/semesters` | 提供する | 開始日の新しい順（開始日が同じなら、idの新しい順）の配列 |
| `GET /api/semesters/<id>` | 提供する | 存在しなければ404 |
| `POST /api/semesters` | 提供する | 201。本文は `name`・`start_date`・`end_date`（すべて必須） |
| `PATCH`・`DELETE` | 提供しない（405） | 「学期の変更・削除時の扱い」が決まるまで |

レスポンスの例：

```json
{"id": 1, "name": "2026年度 後期", "start_date": "2026-09-21", "end_date": "2026-12-27"}
```

`POST` の検証（1つでも満たさなければ、400（`validation_error`）。`fields` は項目名で返す）：
- `name`：文字列。空でない。50字以内。**`[0-9]{4}年度 (前期|後期)` に全体一致**する（半角数字4桁、「年度」、半角スペース1つ、「前期」か「後期」。前後に余分な文字・空白・改行を許さない）。同じ `name` がすでにある場合は不可（完全一致で比較）
- `start_date`・`end_date`：文字列。`YYYY-MM-DD` の実在する日付
- `end_date` は `start_date` より後。違反した場合は `end_date` のエラーにする
- 名前の年度と期間の整合性、ほかの学期との期間の重なりは、検証しない

### 授業API（`/api/subjects`）

| 操作 | 提供 | 内容 |
|---|---|---|
| `GET /api/subjects` | 提供する | 配列。並びは、`weekday`・`start_time`・`id` の昇順。クエリ `semester_id` で絞り込める（任意） |
| `GET /api/subjects/<id>` | 提供する | 存在しなければ404（「授業が見つかりません」） |
| `POST /api/subjects` | 提供する | 201。授業の行だけを作る |
| `PATCH`・`DELETE` | 提供しない（405） | 授業の編集・削除は、Eventの自動生成と合わせて実装する |

- 現時点の `POST` は、授業の行だけを作る。授業の登録時のEventの自動生成は、別途実装する（詳細は、実装の前に決める）
- 授業は、同じ科目名・同じ時間のものも登録できる（週2回の授業は、同じ科目名で2回登録するため）。重複の検知はしない

レスポンスの例：

```json
{"id": 1, "semester_id": 1, "subject_name": "プログラミング基礎", "room": "3号館201", "weekday": 0, "start_time": "09:00", "end_time": "10:00", "notes": null}
```

項目：`id`・`semester_id`・`subject_name`・`room`・`weekday`・`start_time`・`end_time`・`notes`（`room`・`notes` は、値がなければ `null`）。

`POST` の本文は、`semester_id`・`subject_name`・`weekday`・`start_time`・`end_time`（必須）と、`room`・`notes`（任意）。検証（1つでも満たさなければ、400（`validation_error`）。誤りのある項目は、すべて `fields` に項目名で入れる）：
- `semester_id`：必須。整数（真偽値は不可）。1〜`MAX_ID`。その学期が存在すること。範囲外・存在しない場合は、`semester_id` のエラー（404にしない）
- `subject_name`：必須。文字列。前後の空白を取り除いて、1〜100字
- `room`：任意。文字列。前後の空白を取り除いて、100字以内。空なら `null`
- `weekday`：必須。整数（真偽値・小数は不可）。0〜6（0=月曜〜6=日曜）
- `start_time`・`end_time`：必須。`HH:MM`（`00:00`〜`23:59`）。9〜19時・1時間刻みは、強制しない
- `end_time` は `start_time` より後（同じ時刻も不可）。違反した場合は `end_time` のエラー
- `notes`：任意。文字列。前後の空白を取り除いて、空なら `null`。長さの上限は設けない
- `id` を含む、定められていない項目は、その項目名で `fields` に入れる

`GET /api/subjects` のクエリ `semester_id`（任意）：
- 指定がなければ、すべての授業を返す
- 整数でない値（空文字・符号・小数・全角の数字を含む）は、400（`validation_error`、`fields.semester_id`）。複数回の指定も、400
- 整数でも、範囲（1〜`MAX_ID`）の外の値や、存在しない学期のIDは、404にせず、空の配列を返す（絞り込みの結果が0件、という扱い）

## JavaScriptの構成（ES modules）
- すべて `app/static/js/` に置き、`<script type="module">` で読み込む
- 入口は `main.js` の1つだけ。`base.html` に `{% block scripts %}` を用意し、`index.html` で、その中に次の1行を書く。他のファイルは `main.js` から `import` するので、ファイルを足してもHTMLの変更は不要
  `<script type="module" src="{{ url_for('static', filename='js/main.js') }}"></script>`

| ファイル | 役割 |
|---|---|
| `main.js` | 入口。各モードの初期化を呼ぶ |
| `api.js` | `fetch` の共通処理。JSONの送受信を行い、`204` のときは `null` を返す。エラーは `ApiError`（`status`・`code`・`message`・`fields`）として投げる。画面のコードは、APIを呼ぶときに必ずこれを使い、`fetch` を直接呼ばない。仕様は、下の「`api.js` の仕様」 |
| `semesters.js` | 授業モードの学期タブ、学期の登録フォーム |
| `subjects.js` | 授業モードの授業の一覧・登録フォーム |
| `calendar.js` | FullCalendarの設定、期限型の表示、直近の締切欄 |
| `tasks.js` | 課題モードの一覧・完了切替 |

必要になったタスクで、1つずつ作る。

規則：
- 1リソース＝ `routes/<名前>.py` と `static/js/<名前>.js` を対応させる
- HTMLの中に、自作のJavaScriptを書かない
- Jinjaの値をJavaScriptに直接埋め込まない。データはAPIから取得する
- ユーザーの入力を画面に表示するときは、`textContent` を使い、`innerHTML` に直接入れない
- 各モードのファイルは、`initXxx()`（例：`initSemesters()`）を `export` し、`main.js` が呼ぶ。`export` は名前つきにし、`export default` は使わない
- 画面の骨組み（ボタン・モーダル・表示領域）のHTMLは、`index.html`（または、そこから `{% include %}` する部分テンプレート）に書く。JavaScriptが行うのは、表示・非表示の切り替え（Bootstrapの `d-none`）と、文字（`textContent`）の変更。動的に作るのは、件数によって増える部分（一覧のタブや行など）だけで、`createElement` で作り、`replaceChildren()` で差し替える
- DOMの `id` は、`<リソース名の単数形>-<部分>` の形にする（例：`semester-tabs`、`semester-form`）。入力欄のエラー表示の `id` は、`<項目>-error`（例：`semester-start-date-error`）
- モーダルはBootstrapのものを使う。決まった操作で開くときは、HTMLの `data-bs-toggle="modal"` を使ってよい。値を設定して開くときなどは、JavaScriptから `window.bootstrap.Modal` で開く。閉じるときも、`window.bootstrap.Modal` を使う。`base.html` のBootstrapの `<script>` は通常のスクリプトで、先に読み込まれ、`type="module"` のスクリプトは、ページの解析後に実行されるため、`window.bootstrap` を使える。モーダルのHTMLは、`<main>` や `.tab-pane` の外（ページの最上位）に置く
- 日付の補助処理（今日の日付の文字列など）は、必要としたモジュールの中に置く。2つ目のモジュールで必要になったときに、共通のファイルに切り出す。今日の日付は、ブラウザのローカルの日付から作り（`toISOString()` は使わない）、`YYYY-MM-DD` の文字列のまま比較する
- 画面のエラー表示：`ApiError` の `fields` があるときは、該当する項目の下に表示する。それ以外のエラーは、`message` を、フォームの上部や画面に表示する

### `api.js` の仕様
- `export class ApiError extends Error`：`status`（HTTPのステータス。応答がないときは `0`）、`code`（文字列）、`message`（画面に出せる日本語）、`fields`（オブジェクトまたは `null`）を持つ
- `export async function apiRequest(method, url, body)`
  - `body` が `undefined` でないときだけ、`Content-Type: application/json` を付けて、`JSON.stringify(body)` を送る（`GET`・`DELETE` には付けない。サーバーも、これらには要求しない）
  - 成功（2xx）：`204` なら `null`、それ以外は、JSONを解析した値を返す
  - 失敗：応答の `{"error": {"code", "message", "fields"}}` から `ApiError` を作って投げる
  - サーバーに接続できない場合（`fetch` が例外）：`status: 0`、`code: "network_error"`、`message: "サーバーに接続できませんでした。時間をおいて、もう一度お試しください"` の `ApiError` を投げる
  - 応答がJSONとして読めない、または `{"error": {...}}` の形でない場合：`code: "invalid_response"`、`message: "サーバーから想定外の応答がありました。時間をおいて、もう一度お試しください"` の `ApiError` を投げる（`status` は、実際の値）
- `network_error` と `invalid_response` は、サーバーが返すコードではなく、`api.js` が作る（「エラー」の表には含めない）
- 再試行・キャッシュ・ログは持たない

## 自動テスト（pytest）
**pytest** を採用する。APIの入力検証は項目が多く、`curl` での確認は手間がかかり、見落としも起きやすいため。

### 対象と方針
- 対象は、PythonのAPI（Flaskの `test_client` で呼ぶ）。JavaScriptの自動テストは、導入しない（画面は、ブラウザでの確認で行う）
- APIを実装するタスクでは、そのAPIのテストを、同じタスクで作る。完了の条件に、テストの合格を含める
- `curl` での確認は、補助として、実際に起動したサーバーの読み取りの確認に使う
- テストの期待値は、設計資料から決める。テストを通すために、期待値を設計資料に反して変えない

### 配置と実行
- テストは `tests/` に置く。ファイル名は `test_*.py`。共通の準備は `tests/conftest.py`
- 設定は、リポジトリ直下の `pytest.ini`（テストの場所と、`import app` のための `pythonpath`）
- 実行：リポジトリのルートで、`.venv` を有効にして、`python -m pytest`。1つのファイルだけ：`python -m pytest tests/test_subjects_api.py`
- `pytest` は、`requirements.txt` に、バージョンを固定して追加する（依存するライブラリも、ファイルの形式に合わせる）

### アプリの生成（テスト用の設定）
- `create_app(test_config=None)`。`test_config` がなければ、これまでどおり `Config` を使う
- `test_config`（辞書）を渡すと、`Config` の読み込みのあと、`db.init_app(app)` の**前**に、その内容で設定を上書きする
- `test_config` を渡す場合は、`SQLALCHEMY_DATABASE_URI` の指定を必須とする。ない場合は、`ValueError`（開発用DBを、うっかり使わないため）。このとき、`instance/` ディレクトリの作成も行わない

### テスト用DB
- 場所：pytestが用意する一時ディレクトリ（`tmp_path_factory`・`tmp_path`）の中だけ。リポジトリの中や、`instance/` には作らない
- 作り方：**本番と同じmigration（`upgrade`）**。セッションの最初に1回だけ、一時ディレクトリに「雛形のDB」を作り、`flask_migrate.upgrade()`（`directory` は、リポジトリの `migrations/` の絶対パス）で、最新の状態にする。これで、migrationの経路も、毎回確認される
- 各テストの前に、雛形のDBを、テストごとの一時ファイルへコピーして使う（テスト間でデータが混ざらない。リセットは、新しいコピーに替わることで行う）
- テストの中のデータは、各テストが自分で作る（ORMで直接作るか、APIで作る）

### 開発用DB（`instance/app.db`）を触らない仕組み
1. テストは、`create_app({...})` に、一時ディレクトリのDBのURIを渡してアプリを作る。`create_app()` を、引数なしで呼ばない
2. `test_config` に `SQLALCHEMY_DATABASE_URI` がなければ、`create_app` が `ValueError` にする
3. `conftest.py` のfixtureが、DBのパスが、pytestの一時ディレクトリの中であることを確認する（外なら、テストを失敗させる）
4. セッション全体で、`instance/app.db` の内容（ハッシュ）が、テストの前後で変わっていないことを確認する（変わっていれば、失敗させる）

### テストの書き方
- APIは、`app.test_client()` で呼ぶ。JSONの本文は `client.post(url, json=...)`。JSONでない本文や、`Content-Type` の違いは、`data=` と `content_type=` で指定する
- 500の確認は、テストの中で、テスト専用のルートを `app.add_url_rule` で足し、`PROPAGATE_EXCEPTIONS` を `False` にして行う。テスト専用のコードを、`app/` に入れない
- 各テストは独立させる（実行順に依存しない）。1つのテストで確認することは、1つにする

## ディレクトリ構成
以下は目標の構成。`.git/`・`.gitignore`・`.venv/`・`.vscode/`・`README.md` は作成済みで、変更しない。

```
schedule_app/
├── app/
│   ├── __init__.py          # Flaskアプリの作成（`create_app(test_config=None)`）
│   ├── config.py            # SQLiteのパスなどの設定
│   ├── extensions.py        # db = SQLAlchemy(命名規則つきのMetaData)、migrate = Migrate() など
│   ├── api_helpers.py       # API共通処理（エラー応答、エラーハンドラー、JSON本文の受け取り、項目の検査、日付の変換、IDの上限 MAX_ID）。DBの操作は行わない
│   ├── models/
│   │   ├── __init__.py      # 各モデルの読み込み
│   │   ├── semester.py      # 学期
│   │   ├── subject.py       # 授業
│   │   ├── event.py         # 時間型の予定
│   │   └── task.py          # 課題・タスク（期限型）
│   ├── routes/
│   │   ├── __init__.py      # routesをパッケージにする（空のファイル）
│   │   ├── main.py          # トップページ（カレンダー・授業・課題の3モードを含む1画面）
│   │   ├── semesters.py     # 学期のAPI（一覧・取得・登録）
│   │   ├── subjects.py      # 授業モードのAPI（登録・編集・削除・一覧）
│   │   ├── events.py        # カレンダーからの予定のAPI（登録・編集・削除）
│   │   └── tasks.py         # 課題・タスクのAPI（登録・編集・削除・完了切替）
│   ├── templates/
│   │   ├── base.html        # 共通の骨組み。Bootstrapの読み込みと、JavaScript用の scripts ブロック
│   │   └── index.html
│   └── static/
│       ├── css/style.css    # カテゴリの色・独自スタイル
│       └── js/
│           ├── main.js      # 入口（各モードの初期化）
│           ├── api.js       # fetchの共通処理
│           ├── semesters.js # 授業モードの学期タブ・登録フォーム
│           ├── calendar.js  # FullCalendarの設定、期限型の表示、直近の締切欄
│           ├── subjects.js  # 授業モードの一覧・登録フォーム
│           └── tasks.js     # 課題モードの一覧・完了切替
├── migrations/              # Flask-Migrateのmigration環境（`flask db init` で生成）。Git管理対象
│   └── versions/            # migrationファイル（自動生成後にレビューする）。Git管理対象
├── instance/app.db          # SQLiteファイル。Git管理対象外
├── docs/                    # 設計資料（正本）とタスク資料
├── .github/copilot-instructions.md
├── tests/                   # pytestのテスト（「自動テスト（pytest）」を参照）
│   ├── conftest.py          # 共通のfixture（テスト用DB・アプリ・クライアント・開発用DBの保護）
│   ├── test_setup.py        # テスト基盤そのものの確認
│   ├── test_api_helpers.py  # api_helpers.py の共通関数の単体テスト
│   └── test_<リソース名>_api.py  # APIのテスト（リソースごと）
├── pytest.ini               # pytestの設定
├── requirements.txt
├── README.md                # 作成済み
└── run.py                   # 起動スクリプト（127.0.0.1:5001）
```

注意：
- 授業のモデル名は、Pythonの予約語 `class` と紛らわしいため `Subject` とする。
- 画面はカレンダー／授業／課題・タスクの3モードを1ページ（`index.html`）に持たせ、Bootstrapのタブ機能と、必要なJavaScriptで表示を切り替える。
- ログインがないため、認証関連のファイルは作らない。

## 開発の役割分担とGit運用
- Claude：要求定義・設計・技術判断・実装方針・実装結果のレビュー
- GitHub Copilot Agent mode：実装担当
- Koma：最終判断・コード確認・テスト結果確認・Git管理
- Git：`main` は常に動く状態を保つ。タスクごとに `feature/タスク番号-説明` ブランチを切り、Komaが確認・テストしてから `main` へマージする（1タスク＝1ブランチ＝1マージ）。ブランチの作成・切替、commit、push、マージはすべてKomaが行い、Copilot Agentは行わない。
