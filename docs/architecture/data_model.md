# データ設計

> 仕様の正本。変更は、Komaの承認を得てから、PRで行う（`docs/development/workflow.md`）。

データのテーブルは5つ（Semester・Subject・Event・Task・Closure）。関係は **Semester → Subject → Event / Task** と、**Semester → Closure**。Closure（休講日）は、初期migrationには含まれない（休講日を実装するときに、新しいmigrationで追加する）。

ログインのテーブルは3つ（User・UserSession・LoginFailure。Task 025）。5つのデータのテーブルは、すべて `user_id` で、どれかの利用者（User）のものになる（下の「データの持ち主」）。

## 共通の約束
- 型は SQLAlchemy の型で書く。`String(n)` の n は最大文字数。
- 日付・時刻（Date／Time／DateTime）は、タイムゾーン情報なし（naive）のローカル時刻として扱う。タイムゾーンの変換はしない。
  - 例外：ログインのテーブル（User・UserSession・LoginFailure）の日時は、UTC（タイムゾーンなしで保存）。期限を、サーバーのタイムゾーンや、Macとクラウドの違いに左右されずに決めるため。処理は `app/clock.py` の `utc_now` の1か所で求める
- 主キー `id` は整数の自動採番。
- 初期値（`default`）は SQLAlchemy 側（Python側）で指定する。DB側の `server_default` は、現時点のモデルでは使わない（データが入ったテーブルにNOT NULLのカラムを後から追加する場合は、そのときのmigrationで別途検討する）。
- 現時点のモデルには、インデックス・check制約を定義しない。unique制約は、ログインのテーブルの2つ（`users.username`・`user_sessions.token_digest`。取り違えると、他人としてログインしうるため、DBでも守る）だけにする（制約の命名規則は「制約の命名規則」を参照）。
- SQLiteは、既定では外部キー制約を強制しない（`PRAGMA foreign_keys` を有効にしていない）。`user_id` の外部キーも、DBでは強制されないため、守りとして当てにしない（持ち主は、routeで確かめる。「データの持ち主」）。
- 削除時の連動は、ORMの `cascade` やDB側の `ondelete` を使わず、routeで、子の行を明示的に削除してから、親の行を削除する（1回のcommit。2026-10-13に決定）。SQLiteは既定では外部キー制約を強制しない（`PRAGMA foreign_keys`）ため、親の行だけを削除すると、子の行が残る（ORMで親の行を `session.delete` すると、`relationship` を通して、子の行の外部キーが `NULL` に書き換えられて残る）。routeに書くのは、何を削除するかを、routeのコードから読めるようにするため（休講日の追加で、その日の予定を削除する処理と同じ書き方）。DBの構造は変えない（migrationは不要）。現時点で、子の行を持つ親の削除は、授業の削除（予定・課題。「授業API」）と、学期の削除（休講日。授業がある学期は削除できない。「学期API」。2026-10-20）
- `category` には、コード値（英小文字と `_` だけの固定の文字列）を保存する。値は、Event・Taskの表のとおり。画面に出す表示名・色・アイコンは、画面側の対応表（`app/static/js/categories.js`。色の値は `app/static/css/style.css`。「JavaScriptの構成」）で持ち、DBには持たない。
- `category` の保存値と、APIで受け付ける値（許可値）の一覧は、`app/categories.py` だけで持つ（2026-10-15に決定。下の「カテゴリの保存値の置き場所」）。APIで `category` を受け付けるときは、許可値と完全に一致する文字列だけを受け付け、それ以外は400にする（「API共通ルール」の「決まった値から選ぶ文字列」）。Event・Taskの両方に、同じ規則を使う

### カテゴリの保存値の置き場所：`app/categories.py`
- 配置：`app/` 直下（`api_helpers.py`・`class_events.py` と同じ階層）。定数だけを持つ（関数・DBの操作・Flaskの処理を持たない）
- 定数

  | 定数 | 値 |
  |---|---|
  | `EVENT_CATEGORY_CLASS`・`EVENT_CATEGORY_PART_TIME`・`EVENT_CATEGORY_OTHER` | `"class"`・`"part_time"`・`"other"`（予定（Event）の保存値） |
  | `EVENT_CATEGORIES` | 上の3つのタプル（予定のAPIで `category` を受け付けるときの許可値。並びは、画面の `categories.js` の `EVENT_CATEGORIES` と同じ） |
  | `TASK_CATEGORY_ASSIGNMENT`・`TASK_CATEGORY_OTHER` | `"assignment"`・`"other"`（課題・タスク（Task）の保存値） |
  | `TASK_CATEGORIES` | 上の2つのタプル（課題・タスクのAPIで `category` を受け付けるときの許可値） |

- Pythonのコードで、カテゴリの保存値の文字列（`"class"` など）を直接書かず、この定数を使う（テストの期待値は除く）。授業のEventの自動生成（`app/class_events.py`）も、`EVENT_CATEGORY_CLASS` を、ここから `import` して使う
- 予定のAPIは、登録（`POST /api/events`）で `category` を受け付け、許可値に `EVENT_CATEGORIES` を使う（2026-10-19。「予定API」）
- 画面側の対応表（`categories.js`）は、表示名・色・アイコンのための別の対応表で、このファイルとは独立に持つ（PythonとJavaScriptで、定数を共有する仕組みは作らない。保存値を変えることはないため）

## データの持ち主（`user_id`。Task 025）
- 5つのデータのテーブル（semesters・subjects・closures・events・tasks）は、どれも `user_id`（Integer、外部キー → `users.id`、NULL不可）を持つ。下の各テーブルの表では、省いて書く
- 子の行は、作るときに、親の `user_id` を写す（授業・休講日は学期から、授業の予定は授業から。単発の予定と課題・タスクは、ログインした利用者。授業の予定（単発）と課題の授業は、自分のものと確かめてある）
- APIは、ログインした利用者の行だけを扱う（`architecture/api.md` の「利用者ごとのデータ（認可）」）
- 既存のデータ（Task 025より前）は、migration（`a750d741785a`）で、利用者 `owner`（パスワードなし）のものになる。データのないDBでは、利用者を作らない
- `relationship` は足さない（利用者から、すべてのデータを辿る必要がなく、問い合わせを、routeの文で明示するため）

## User（利用者）　テーブル名：`users`
ログインする人。データの持ち主。作る・変えるのは、コマンドだけ（`architecture/security.md` の「利用者の管理」）。

| フィールド | 型 | NULL | 内容 |
|---|---|---|---|
| id | Integer（主キー） | 不可 | |
| username | String(32) | 不可 | ログインID。半角英小文字・数字・`_`・`-`、3〜32文字。一意（`uq_users_username`） |
| password_hash | String(255) | 可 | パスワードのハッシュ（scrypt。Werkzeug の形）。NULLの利用者は、ログインできない（パスワードを決める前の `owner`） |
| created_at | DateTime | 不可 | 作った日時（UTC） |

## UserSession（ログイン中の端末）　テーブル名：`user_sessions`
1回のログインにつき1行。ログアウト・期限切れで消す（`architecture/security.md` の「ログインの状態（セッション）」）。

| フィールド | 型 | NULL | 内容 |
|---|---|---|---|
| id | Integer（主キー） | 不可 | |
| user_id | Integer、外部キー → `users.id` | 不可 | ログインした利用者 |
| token_digest | String(64) | 不可 | Cookie のトークンの SHA-256（16進数）。トークンそのものは保存しない。一意（`uq_user_sessions_token_digest`） |
| created_at | DateTime | 不可 | ログインした日時（UTC）。30日で切れる |
| last_used_at | DateTime | 不可 | 最後に使った日時（UTC。1時間に1回だけ更新）。14日で切れる |

## LoginFailure（ログインの失敗）　テーブル名：`login_failures`
試行の制限に使う記録（`architecture/security.md` の「ログインの試行の制限」）。利用者とは結びつけない（IDがないときも記録するため）。

| フィールド | 型 | NULL | 内容 |
|---|---|---|---|
| id | Integer（主キー） | 不可 | |
| login_id_digest | String(64) | 不可 | 打ち込まれたログインIDの HMAC-SHA256（鍵は `SECRET_KEY`）。IDそのものは保存しない |
| client_digest | String(64) | 不可 | 接続元（IPv4、または IPv6 の /64）の HMAC-SHA256。アドレスそのものは保存しない |
| failed_at | DateTime | 不可 | 失敗した日時（UTC） |
| login_id_locked_until | DateTime | 不可 | この失敗で始まった、ログインIDごとの制限の期限（UTC）。断らないときは `failed_at` と同じ |
| client_locked_until | DateTime | 不可 | この失敗で始まった、接続元ごとの制限の期限（UTC）。断らないときは `failed_at` と同じ |

- 行は、24時間より古く、その行で始まった制限が終わってから消す

## Semester（学期）　テーブル名：`semesters`
学期を表す。UIの学期タブ、「新しい学期の登録」、学期ごとの期間管理に対応する。

| フィールド | 型 | NULL | 内容 |
|---|---|---|---|
| id | Integer（主キー） | 不可 | |
| name | String(50) | 不可 | 学期名。形式は「2026年度 前期」（「学期API」を参照）。DBには文字列だけを保存し、年度・種別の別カラムは持たない |
| start_date | Date | 不可 | 学期の開始日 |
| end_date | Date | 不可 | 学期の終了日 |

- 名前と期間は、編集で変えられる（「学期API」の `PATCH`。2026-10-20）。期間を変えると、授業の予定と休講日に反映する（「学期の期間の変更と予定の同期」）
- 授業がある学期は、削除できない。授業がない学期を削除すると、その学期の休講日も削除される（「学期API」の削除）

## Subject（授業）　テーブル名：`subjects`
授業モードで登録する「パターン」そのもの。必ず1つの学期に所属する。

| フィールド | 型 | NULL | 内容 |
|---|---|---|---|
| id | Integer（主キー） | 不可 | |
| semester_id | Integer、外部キー → `semesters.id` | 不可 | 所属する学期。登録のあとで変えられない（「授業API」） |
| subject_name | String(100) | 不可 | 科目名 |
| room | String(100) | 可 | 教室 |
| weekday | Integer | 不可 | 曜日。**0=月曜〜6=日曜**（Pythonの `date.weekday()` と同じ）。JavaScript・FullCalendarの曜日は0=日曜なので、受け渡しの際は変換が必要 |
| start_time | Time | 不可 | 開始時刻 |
| end_time | Time | 不可 | 終了時刻 |
| notes | Text | 可 | 詳細／メモ |

## Event（予定／時間型）　テーブル名：`events`
授業の毎週分・アルバイト・その他（時間指定あり）の実際の1件1件。

| フィールド | 型 | NULL | 内容 |
|---|---|---|---|
| id | Integer（主キー） | 不可 | |
| subject_id | Integer、外部キー → `subjects.id` | 可 | 授業由来のEvent（自動生成・単発の授業とも）のみ値が入る。アルバイト／その他はNULL |
| category | String(20) | 不可 | `class`（授業）／`part_time`（アルバイト）／`other`（その他） |
| date | Date | 不可 | 日付 |
| start_time | Time | 不可 | 開始時刻 |
| end_time | Time | 不可 | 終了時刻 |
| title | String(200) | 不可 | タイトル |
| room | String(100) | 可 | 教室（主に授業用） |
| employer | String(100) | 可 | 派遣会社（主にアルバイト用） |
| notes | Text | 可 | 詳細／メモ |
| is_generated | Boolean | 不可 | 初期値 `False`。授業の学期一括登録で自動生成したEventは `True`（休講日の削除と、学期の期間の変更で作る授業のEventも `True`）。カレンダーから追加した単発の授業（補講など）、アルバイト、その他は `False` |

- 教室（`room`）は授業の予定だけ、派遣会社（`employer`）はアルバイトの予定だけが持つ（予定APIで、ほかのカテゴリには指定できない。「予定API」）
- **日付をまたぐ予定**（例：22:00〜翌2:00のアルバイト）は、1件の予定では表さない。1件の予定の終了時刻は、開始時刻より後（同じ日の中）にする。日付をまたぐときは、日付ごとに2件に分けて登録する（22:00〜23:59 と、翌日の 00:00〜02:00）。2026-10-19に決定（それまでの未決定事項「日付をまたぐアルバイト」）。理由：日付をまたぐアルバイトは、ほとんどないため（開発者の利用状況）。1件で表す方式（終了が開始より前なら翌日に終わるとみなす方式、終了日の列を足す方式）は、週・月の表示の境目の扱いや、DBの構造の変更が要り、変更が大きいため採らない

## Task（課題・タスク／期限型）　テーブル名：`tasks`
課題と、その他（締切のみ）の実際の1件1件。

| フィールド | 型 | NULL | 内容 |
|---|---|---|---|
| id | Integer（主キー） | 不可 | |
| subject_id | Integer、外部キー → `subjects.id` | 可 | 対象授業。課題（`assignment`）は必ず値が入る。その他（`other`）はNULL（「課題・タスクAPI」） |
| category | String(20) | 不可 | `assignment`（課題）／`other`（その他） |
| title | String(200) | 不可 | 課題名／タイトル |
| due_datetime | DateTime | 不可 | 締切日時。分までを保存する（秒は0。APIの日時の形式が、秒を持たないため） |
| notes | Text | 可 | 詳細／メモ |
| is_completed | Boolean | 不可 | 初期値 `False`（未完了） |

状態は「未完了」「完了」の2つのみ（中間状態は設けない）。

- 課題の対象授業は、編集で変えられる（課題には、授業の予定のような、授業から作るデータがないため）。カテゴリは、変えられない（要求定義のとおり）
- 授業を削除すると、その授業の課題も削除される（「授業API」の削除）。その他（`subject_id` がNULL）は、授業の削除で変わらない

## Closure（休講日）　テーブル名：`closures`
学期の中で、授業が行われない日（休講日）の1件1件。大学の学年暦などで確認した日を、学期ごとに手動で登録する（各学期で数日程度を想定）。登録した休講日には、その学期に所属するすべての授業の予定を作らない（「繰り返し予定の扱い」）。

| フィールド | 型 | NULL | 内容 |
|---|---|---|---|
| id | Integer（主キー） | 不可 | |
| semester_id | Integer、外部キー → `semesters.id` | 不可 | 所属する学期 |
| date | Date | 不可 | 休講日の日付。学期の期間内（`start_date`〜`end_date`、両端を含む）。同じ学期の中で、同じ日付は1件まで |
| name | String(100) | 可 | 休講日の名前（例：「開学記念日」）。表示用 |

- 同じ学期で同じ日付を登録できないことは、学期名の重複と同じく、APIで検査する。DBの一意制約は、「共通の約束」（制約を定義しない）に合わせて付けない
- 学期の期間を変えて、新しい期間の外になった休講日は、削除される（「学期の期間の変更と予定の同期」。2026-10-20）。学期を削除すると、その学期の休講日も削除される
- 休講日は、その日の授業すべてを対象にする（午前だけの休講など、時間帯の指定は扱わない。必要なら、その日の予定を個別に削除する）

## 関係
- Semester 1 — n Subject（Subjectは必ず1つのSemesterに所属）
- Subject 1 — 0..n Event（授業由来のEvent）
- Subject 1 — 0..n Task（対象授業としての参照）
- Semester 1 — 0..n Closure（休講日）
- User 1 — 0..n 各データ（Semester・Subject・Closure・Event・Task。`user_id`）、User 1 — 0..n UserSession
- ORMの `relationship`（`back_populates` で双方向）：`Semester.subjects` ↔ `Subject.semester`、`Subject.events` ↔ `Event.subject`、`Subject.tasks` ↔ `Task.subject`、`Semester.closures` ↔ `Closure.semester`。`cascade` は指定しない（削除の連動は、「共通の約束」のとおり、routeで明示的に行う）。

## 制約の命名規則（naming convention）
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
- index・check：現時点では作らない。unique：ログインのテーブルの2つだけ（下の Task 025 の migration）
- 休講日のテーブル（「Closure（休講日）」）を加えるmigrationで作られる名前（そのmigrationの確認に使う）：主キー `pk_closures`、外部キー `fk_closures_semester_id_semesters`
- 利用者とデータの持ち主を加えるmigration（`a750d741785a`。Task 025）で作られる名前：主キー `pk_users`・`pk_user_sessions`・`pk_login_failures`、外部キー `fk_user_sessions_user_id_users`・`fk_semesters_user_id_users`・`fk_subjects_user_id_users`・`fk_closures_user_id_users`・`fk_events_user_id_users`・`fk_tasks_user_id_users`、unique `uq_users_username`・`uq_user_sessions_token_digest`

注意：checkを定義する場合は、`ck` の規則が `constraint_name` を使うため、制約に明示的な名前が必要になる。`Boolean` などの型にcheck制約を自動で作らせない（`create_constraint` は既定のまま使わない）。
