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
| フロントエンドJS | バニラJavaScript | fetch APIでFlaskの小さなAPIエンドポイント（JSONを返す）を呼ぶ |
| カレンダー描画 | FullCalendar | MIT・無料範囲の週／月／一覧表示のみ使用。リソース／タイムライン表示などの有料機能は使わない |
| CSS（UI部品） | Bootstrap 5.3.8 | CDN（jsDelivr）から、バージョンを固定して読み込む（「Bootstrapの読み込み」を参照）。タブ（モード切り替え）、モーダル（詳細パネル）、バッジ（カテゴリ表示）などに利用 |
| 認証 | なし | ログイン機能は実装しない |
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
現時点で決まっていない事項の一覧。**実装側（Copilot）は、これらを自分の判断で決めない。** 該当する実装に入る前に、開発者（Koma）が決定し、このファイルを更新する。いずれもTask 001の実装には影響しない。

| 項目 | 内容 | 決めるタイミング |
|---|---|---|
| categoryの保存値 | `Event.category`・`Task.category` に保存する値（日本語の文字列そのままか、コード値か）。入力値の制限（バリデーション）の方式も含む | 登録・表示を実装するタスクの前 |
| 日付をまたぐアルバイト | 例：22:00〜翌2:00。Eventは日付1つ＋開始／終了時刻のため、終了が開始より前の入力を許すか、日をまたぐ予定をどう表すか | アルバイトの登録を実装するタスクの前 |
| 授業削除時のEvent・Task削除方式 | 「授業を削除したら、紐づくEvent・Taskもまとめて削除する」という挙動は決定済み。未決定なのは**実装方式**（ORMの `cascade`、削除処理を明示的に書く、DB側の `ondelete` など）。注意点：SQLiteは既定では外部キー制約を強制しない（`PRAGMA foreign_keys`）。`relationship` に `cascade` を指定せず親を削除すると、子の外部キーがNULLになって残る場合がある | 削除を実装するタスクの前 |
| 学期期間の初期値の決定方法 | 学期を作るとき、「今日の日付に近い学期」の期間を初期値として出す。その値の出どころ（固定の値か、入力済みの学期から推測するか、など） | 授業モードを実装するタスクの前 |
| 学期名の決め方 | `Semester.name` を開発者が入力するのか、「前期／後期」から選ぶのか、期間から自動で付けるのか | 授業モードを実装するタスクの前 |
| 学期の変更・削除時の扱い | 学期の期間を修正したときのEventの作り直し、学期を削除したときの授業・Event・Taskの扱い、授業の所属学期の付け替え | 授業モードの編集・削除を実装するタスクの前 |
| 一覧表示の「今日以降」の範囲 | FullCalendarのリスト表示は期間を指定する方式のため、期間の上限（例：今日から3か月）が必要 | カレンダー表示を実装するタスクの前 |
| FullCalendarの読み込み方法 | CDNから読み込むか、ファイルを `app/static/` に置くか（Bootstrapは、CDN方式で確定済み） | カレンダー表示を実装するタスクの前 |

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
| name | String(50) | 不可 | 学期名（例：前期） |
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

## ディレクトリ構成
以下は目標の構成。`.git/`・`.gitignore`・`.venv/`・`.vscode/`・`README.md` は作成済みで、変更しない。

```
schedule_app/
├── app/
│   ├── __init__.py          # Flaskアプリの作成
│   ├── config.py            # SQLiteのパスなどの設定
│   ├── extensions.py        # db = SQLAlchemy(命名規則つきのMetaData)、migrate = Migrate() など
│   ├── models/
│   │   ├── __init__.py      # 各モデルの読み込み
│   │   ├── semester.py      # 学期
│   │   ├── subject.py       # 授業
│   │   ├── event.py         # 時間型の予定
│   │   └── task.py          # 課題・タスク（期限型）
│   ├── routes/
│   │   ├── __init__.py      # routesをパッケージにする（空のファイル）
│   │   ├── main.py          # トップページ（カレンダー・授業・課題の3モードを含む1画面）
│   │   ├── subjects.py      # 授業モードのAPI（登録・編集・削除・一覧）
│   │   ├── events.py        # カレンダーからの予定のAPI（登録・編集・削除）
│   │   └── tasks.py         # 課題・タスクのAPI（登録・編集・削除・完了切替）
│   ├── templates/
│   │   ├── base.html
│   │   └── index.html
│   └── static/
│       ├── css/style.css    # カテゴリの色・独自スタイル
│       └── js/
│           ├── calendar.js  # FullCalendarの設定、期限型の表示、直近の締切欄
│           ├── subjects.js  # 授業モードの一覧・登録フォーム
│           └── tasks.js     # 課題モードの一覧・完了切替
├── migrations/              # Flask-Migrateのmigration環境（`flask db init` で生成）。Git管理対象
│   └── versions/            # migrationファイル（自動生成後にレビューする）。Git管理対象
├── instance/app.db          # SQLiteファイル。Git管理対象外
├── docs/                    # 設計資料（正本）とタスク資料
├── .github/copilot-instructions.md
├── tests/                   # 実装後、必要に応じて追加
├── requirements.txt
├── README.md                # 作成済み
└── run.py                   # 起動スクリプト（127.0.0.1:5001）
```

注意：
- 授業のモデル名は、Pythonの予約語 `class` と紛らわしいため `Subject` とする。
- 画面はカレンダー／授業／課題・タスクの3モードを1ページ（`index.html`）に持たせ、Bootstrapのタブ機能（Bootstrap JavaScript）で表示を切り替える。
- ログインがないため、認証関連のファイルは作らない。

## 開発の役割分担とGit運用
- Claude：要求定義・設計・技術判断・実装方針・実装結果のレビュー
- GitHub Copilot Agent mode：実装担当
- Koma：最終判断・コード確認・テスト結果確認・Git管理
- Git：`main` は常に動く状態を保つ。タスクごとに `feature/タスク番号-説明` ブランチを切り、Komaが確認・テストしてから `main` へマージする（1タスク＝1ブランチ＝1マージ）。ブランチの作成・切替、commit、push、マージはすべてKomaが行い、Copilot Agentは行わない。
