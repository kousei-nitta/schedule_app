# タスク001: アプリ基盤・DBモデル・初期マイグレーション

ブランチ：`feature/001-app-foundation`（Komaが作成・切替済みの状態で渡される。作業開始前に `git branch --show-current` で確認し、`main` だった場合は作業せずKomaに報告する）

## ゴール
Flaskアプリケーションの基盤（アプリケーションファクトリ）を作り、Flask-SQLAlchemy・Flask-Migrate・SQLiteを接続する。
`Semester`・`Subject`・`Event`・`Task` の4つのモデルを定義し、初期migrationを作成・適用して、SQLiteに4つのテーブルができた状態にする。外部キーの関係は **Semester → Subject → Event / Task**。

画面もAPIもまだ作らない。このタスクの完成形は「アプリがデータベースを扱える土台」まで。

## このタスクで使うコマンドの意味
`flask db init` は **テーブルを作るコマンドではない**。migrationを管理するための作業フォルダ `migrations/` を作るだけで、データベースには変更を加えない。テーブルが作られるのは `flask db upgrade` のときである。
詳しくは `docs/architecture.md` の「Flask-Migrateの操作の意味」を参照。

| 順番 | コマンド | このタスクでの役割 |
|---|---|---|
| 1 | `flask --app app db init` | `migrations/` を作る（テーブルはまだできない） |
| 2 | `flask --app app db migrate -m "initial tables"` | 4モデルから、テーブルを作るmigrationファイルを自動生成する（テーブルはまだできない） |
| 3 | （確認ポイント）生成されたファイルを確認し、Komaの承認を待つ | |
| 4 | `flask --app app db upgrade` | migrationをDBに適用する。**ここで初めてテーブルができる** |

## やること

### 1. ライブラリのインストール
- `.venv` が有効であることを確認する
- `Flask-SQLAlchemy` と `Flask-Migrate` をインストールする（Komaが採用を承認済み）
- `pip freeze > requirements.txt` で `requirements.txt` を作成する

### 2. アプリ基盤の作成（`docs/architecture.md` のディレクトリ構成に従う）
- `app/extensions.py`：`db` と `migrate` を定義する。`db` には、`docs/architecture.md` の「制約の命名規則」にある `NAMING_CONVENTION` を設定した `MetaData` を渡す
- `app/config.py`：設定クラスを定義する。DBはSQLiteで、ファイルは `instance/app.db`
- `app/__init__.py`：`create_app()`（アプリケーションファクトリ）を定義し、次を行う
  - 設定の読み込み
  - `db.init_app(app)`
  - `migrate.init_app(app, db, render_as_batch=True)`（SQLiteで後からカラムを変更できるようにするため。理由は `docs/architecture.md` を参照）
  - Migrateがモデルを認識できるよう、モデルを読み込む

### 3. モデルの定義（`app/models/`）
`app/models/__init__.py`、`semester.py`、`subject.py`、`event.py`、`task.py` を作る。

テーブル名、カラム、型、NULL可否、初期値、外部キー、`relationship` は、**`docs/architecture.md` の「データ設計」のとおり**に実装する（この資料には表を重複して書かない）。特に次の点を守る。

- モデルは `Semester`・`Subject`・`Event`・`Task` の4つ。テーブル名は `semesters`・`subjects`・`events`・`tasks`
- `Subject` は `semester_id`（`semesters.id` への外部キー、NULL不可）を持つ。**`term_start_date`・`term_end_date` は存在しない**（学期の期間は `Semester` が持つ）
- `Event` には `is_generated`（Boolean、NULL不可、初期値 `False`）がある
- `Subject.weekday` は整数で、0=月曜〜6=日曜
- `relationship` は `back_populates` で双方向にし、`cascade` や `ondelete` は指定しない
- インデックス・unique制約・check制約は定義しない

### 4. 初期migrationの作成と適用
1. `flask --app app db init`
2. `flask --app app db migrate -m "initial tables"`
3. **【確認ポイント】** 生成された `migrations/versions/` のファイルを読み、チャットで次を報告して、Komaの承認を待つ（承認前に `upgrade` を実行しない）
   - 作成されるテーブルとカラム（名前・型・NULL可否）。`docs/architecture.md` のデータ設計との差異の有無
   - 外部キーが **Semester → Subject → Event / Task** の関係で生成されていること
     - `subjects.semester_id` → `semesters.id`
     - `events.subject_id` → `subjects.id`
     - `tasks.subject_id` → `subjects.id`
   - 主キー・外部キーのすべてに名前が付いていること。名前が `docs/architecture.md` の「制約の命名規則」に書かれた名前と一致すること
   - index・unique・check制約が含まれていないこと
   - `create_table` 以外の操作（drop・alterなど）が含まれていないこと
   - 期待と異なる点があっても、migrationファイルを手で書き換えず、そのまま報告する
4. 承認後、`flask --app app db upgrade`

## やらないこと（このタスクの範囲外）
- ルーティング（Blueprintを含む）、`app/routes/`
- HTML、Jinjaテンプレート、`app/templates/`
- JavaScript、FullCalendar、Bootstrap、CSS、`app/static/`
- UIに関するすべて
- `run.py` の作成と、開発サーバーの起動（ルーティングを作るタスクで扱う）
- サンプルデータ・初期データの投入（「完了の確認方法」で行う確認用の一時データを除く）
- 入力値のバリデーション、カテゴリ値の制限
- 授業の登録に伴う、毎週分のEventの自動生成
- 削除時の連動（`cascade`、`ondelete`）の設定
- テスト（`tests/`）
- `db.create_all()` の使用
- `.gitignore`・`.vscode`・Git設定の変更
- Git commit / push
- 設計資料（`docs/requirements.md`・`architecture.md`・`ui_ux.md`）の変更

## 参照
- `docs/architecture.md`：技術スタック、データ設計、制約の命名規則、DBスキーマ変更の方式、ディレクトリ構成、未決定事項
- `.github/copilot-instructions.md`：進め方と、設計上の問題を見つけたときの手順

## 完了の確認方法
1. `flask --app app db upgrade` がエラーなく完了し、`instance/app.db` ができている
2. `flask --app app db current` で、適用済みのmigrationが表示される
3. `sqlite3 instance/app.db ".tables"` で `semesters`・`subjects`・`events`・`tasks`・`alembic_version` が表示される
4. `sqlite3 instance/app.db ".schema"` で、次を確認する
   - `subjects` に `semester_id` があり、`term_start_date`・`term_end_date` がない
   - `events` に `is_generated` がある
   - 外部キーの関係と制約の名前が、確認ポイントで報告した内容と一致している
5. `flask --app app shell` で、`Semester` → `Subject` → `Event`・`Task` の順に1件ずつ追加し、`relationship`（`subject.semester`・`subject.events`・`subject.tasks`・`event.subject`）で参照できる。確認後、**Event・Task → Subject → Semester の順に削除**し、空の状態に戻す（`cascade` を指定していないため、この順にする）
6. `git status` で、`migrations/`・`app/`・`requirements.txt` が新規ファイルとして表示され、`instance/app.db` が表示されない（Git管理対象外であることの確認）
7. 変更したファイルが、このタスクの「やること」の範囲内だけである

## 注意
- `flask --app app ...` が動かない場合や、このタスクの内容が設計資料と矛盾する場合は、実装せず `.github/copilot-instructions.md` の手順で報告する
- 型や制約について、`docs/architecture.md` で決まっていないことは自分で決めず、Komaに確認する。特に「未決定事項」に書かれた項目は、このタスクでは扱わない
