# テストと確認

自動テスト（pytest）、検査の道具、CI、E2Eテスト、画面の確認。コマンドの一覧は、リポジトリ直下の `CLAUDE.md`。

## 自動テスト（pytest）
**pytest** を採用する。APIの入力検証は項目が多く、`curl` での確認は手間がかかり、見落としも起きやすいため。

### 対象と方針
- 対象は、PythonのAPI（Flaskの `test_client` で呼ぶ）と、PythonのAPI以外の処理（バックアップ・デモデータ・コマンドなど）。JavaScriptの単体テストは、導入しない（画面は、E2Eテストの主な流れと、ブラウザでの確認で確かめる。下の「E2Eテスト」）
- APIを実装するタスクでは、そのAPIのテストを、同じタスクで作る。完了の条件に、テストの合格を含める
- `curl` での確認は、補助として、実際に起動したサーバーの読み取りの確認に使う
- テストの期待値は、設計資料から決める。テストを通すために、期待値を設計資料に反して変えない

### 配置と実行
- テストは `tests/` に置く。ファイル名は `test_*.py`。共通の準備は `tests/conftest.py`
- 設定は、リポジトリ直下の `pytest.ini`（テストの場所、`import app` のための `pythonpath`、印 `e2e` の宣言と、E2Eテストをふだんの実行から外す `addopts`）
- 実行：リポジトリのルートで、`.venv` を有効にして、`python -m pytest`。1つのファイルだけ：`python -m pytest tests/test_subjects_api.py`
- `pytest` は、`requirements-dev.txt` に、バージョンを固定して書く（依存するライブラリも、ファイルの形式に合わせる。`requirements.txt` には、アプリを動かすものだけを書く）

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
4. セッション全体で、`instance/app.db` の内容（ハッシュ）と、`instance/` の有無と、その中のすべてのファイル・フォルダ（バックアップなど）が、テストの前後で、作られず・変わらず・消えていないことを確認する（違えば、失敗させる）。テストの間に、アプリを使った・起動した（その日のバックアップができる）・`backup-db` を実行した場合も、この確認で失敗する（テストの不具合ではない）。テストの間は、アプリを使わない
5. バックアップは、DBのファイルと同じフォルダの `backups/` にできるため、テストのバックアップは、一時ディレクトリの中にだけできる。実データのDBかどうか（`instance/app.db` か）の判定を確かめるテストは、`instance/` を一時ディレクトリにした空のFlaskアプリ（`Flask(__name__, instance_path=…)`）で行う（`tests/test_database_files.py`・`tests/test_backup.py`・`tests/test_demo_data.py`）

### テストの書き方
- APIは、`app.test_client()` で呼ぶ。JSONの本文は `client.post(url, json=...)`。JSONでない本文や、`Content-Type` の違いは、`data=` と `content_type=` で指定する
- 500の確認は、テストの中で、テスト専用のルートを `app.add_url_rule` で足し、`PROPAGATE_EXCEPTIONS` を `False` にして行う。テスト専用のコードを、`app/` に入れない
- 既存のrouteの途中で例外が起きた場合の確認（例：Eventの生成中の例外で、授業も保存されないこと）は、pytestの `monkeypatch` で、routeが呼ぶ関数を、例外を投げる関数に置き換えて行う。置き換える場所は、routeのモジュールが参照している名前（`from ... import` で取り込んだ名前なら、routeのモジュール側）。500のJSONを確かめるため、このときも `PROPAGATE_EXCEPTIONS` を `False` にする。保存されていないことは、例外のあとで、DBの行数を数えて確かめる
- DBを使わない関数（`class_events.py` の日付の計算など）は、アプリやDBを作らずに、関数を直接呼んで確認する
- 予定（Event）を作る・消すAPIのテストでは、レスポンスだけでなく、DBのEventの行を数えて確かめる。少なくとも、次を確かめる
  - 授業の登録：`generated_event_count` と、その授業の自動生成のEventの行数が一致する。休講日の日付には、行がない
  - 休講日の追加・削除（「休講日の変更と予定の同期」の規則）：その日付の、その学期の授業の自動生成のEventの行数（追加後は0、削除後は、その曜日の授業の数）。単発のEvent（`is_generated=False`）と、ほかの学期の授業のEventは変わらない。休講日の削除では、その日の曜日の授業に、同じ日付の単発のEventがあっても、自動生成のEventが1件作られる。曜日が違う授業は、同じ日付に単発のEventがあっても、Eventは作られない
  - 同じ授業・同じ日付の自動生成のEventが、2件以上ない（「休講日の変更と予定の同期」の規則）
  - 授業全体の編集（「授業全体の編集による作り直し」）：今日より前の予定が変わらない。今日（を含む）以降の自動生成の予定が、授業の新しい値で、規則どおりの日にある（休講日を除く）。個別に変更・削除した今日以降の予定が、設定どおりに戻る。単発の予定と、ほかの授業の予定が変わらない。今日が学期の前・後の場合
  - 授業の削除：その授業の予定（自動生成・単発）と課題の行が0件になる。`subject_id` が `NULL` の予定・課題が増えていない。ほかの授業の予定・課題と、授業に結びつかない予定・課題が変わらない
  - 学期の期間の変更（「学期の期間の変更と予定の同期」）：新しい期間の外の自動生成の予定と休講日がなくなる。新しく期間に入った日に、規則どおりの予定ができる（授業の今の値で）。両方の期間に入る日の予定（個別の変更・削除を含む）、単発の予定、授業に結びつかない予定・課題、ほかの学期は変わらない。同じ授業・同じ日付の自動生成の予定が2件以上ない。途中で例外が起きたら、どれも保存されない
  - 学期の削除：授業がある学期は409で、何も変わらない。授業がない学期は、学期と、その休講日の行が0件になる（`semester_id` が `NULL` の休講日が増えていない）。ほかの学期の行は変わらない
  - 予定の登録・編集・削除（予定API）：その予定の行だけが、作られる・変わる・消える。ほかの予定（自動生成の予定を含む）は変わらない。登録した予定は `is_generated=False`、編集した自動生成の予定は `is_generated=True` のまま。カレンダーから操作した予定と、休講日の追加・授業全体の編集・授業の削除との関係（「カレンダーからの授業の予定の操作」）
- 「今日」に依存する処理のテストでは、routeが「今日」を求める関数（`routes/subjects.py` の `current_date`）を、`monkeypatch` で置き換えて、日付を固定する（実行した日によって、結果が変わらないようにするため）。置き換える場所は、routeのモジュールの名前
- migrationでテーブルを追加・変更したタスクでは、`tests/test_setup.py` で、そのテーブルの列（名前・型・NULL可否）と制約の名前が、「データ設計」と「制約の命名規則」のとおりであることを確かめる（テスト用DBはmigrationで作るため、migrationの内容の確認になる）
- 各テストは独立させる（実行順に依存しない）。1つのテストで確認することは、1つにする

## 検査の道具
道具は、開発のときだけ使う（`requirements-dev.txt`・`package.json`）。版は固定する（版の選び方は、`CLAUDE.md` の「仕様と範囲」）。

| 確認 | 道具と設定 | 実行 |
|---|---|---|
| Pythonの書き方 | ruff。`ruff.toml`：PEP8の主な規則（E・F・W）、1行79文字（全角の文字は2文字に数える）。`migrations/versions/` は対象から外す（自動生成で、確かめてマージしたファイルのため）。`docs/archive/` も、`.ignore` に従って外れる | `ruff check .` |
| JavaScriptの書き方 | ESLint。`eslint.config.js`：推奨の規則（定義していない変数など）に、`no-var`・`prefer-const`・`eqeqeq`・`max-len`（80文字）・`quotes`（二重引用符）を足す。中に `"` を含む文字列だけ、単引用符を許す（`avoidEscape`）。対象は `app/static/js/` | `npm run lint` |
| モデルとmigrationのずれ | pytestのテスト（`tests/test_setup.py` の `test_models_and_migrations_have_no_differences`）。migrationで作った一時的なDBと、モデルを比べる（`flask db check` と同じ確認）。ずれがあると、差の内容を出して失敗する | `python -m pytest` |

- ESLintを手元で動かすには、Node.js が要る（`npm ci` → `npm run lint`）。KomaのMacには入れていない（CIのジョブ `javascript` が、PRごとに確かめるため）。入れるかは、Task 024（開発の環境の方針）で決める
- 検査の例外は、理由をコメントに書いて、その行だけに付ける。今の例外：`app/__init__.py` の `from app import models  # noqa: F401`（モデルの登録のための読み込みで、名前は使わない）
- コードの自動整形（ruff format）は使わない（変更と関係のない差分が大きくなるため。ADR 0001）
- `flask db check` は、ふだん直接は実行しない（Macでは、実データのDBと比べることになるため）。pytestで確かめる

## CI
- `.github/workflows/ci.yml`（GitHub Actions）。PRと、`main` へのpushのときに動く
- ジョブ `python`（Python 3.11）：`pip install -r requirements-dev.txt` → `ruff check .` → `python -m pytest`
- ジョブ `javascript`（Node.js 22）：`npm ci` → `npm run lint`
- ジョブ `e2e`（Python 3.11。15分で打ち切る）：`pip install -r requirements-dev.txt` → `python -m playwright install --with-deps chromium` → `python -m pytest -m e2e`（Bootstrap・FullCalendarは、CDNから読む）
- 通らないPRは、マージしない。`main` のルールセットで、3つのジョブの合格を必須にする（設定はKoma）

## E2Eテスト
画面を、ブラウザ（Chromium）で、利用者と同じように操作して確かめる。道具は Playwright（pytest-playwright。pytestから動かす）。手動の確認を、すべて置き換えるものではない（ADR 0001 の「自動の確認」）。

### 対象
- 主な流れ（`tests/e2e/test_main_flow.py`）：学期の登録 → 休講日の追加 → 授業の登録（休講日を除いて予定ができる）→ カレンダーの週表示（休講日に授業の予定がなく、次の週にはある）→ 課題の登録（「直近の締切」欄に出る）→ 完了（完了の一覧に移り、「直近の締切」欄から消える）。流れの全体で、JavaScriptの例外が起きていないこと
- E2Eテストは、主な流れと、新しい画面の重要な操作に絞る。細かな入力の検査は、APIのテスト（pytest）で確かめる

### 配置と実行
- `tests/e2e/` に置く。この中のテストには、`tests/e2e/conftest.py` が、印 `e2e` を自動で付ける（付け忘れると、ブラウザのない環境（CIのジョブ `python`）で失敗するため）。`pytest.ini` の設定で、印 `e2e` のテストは、ふだんの `python -m pytest` からは外れる（ブラウザの準備が要り、時間もかかるため）
- 実行：`python -m pytest -m e2e`。ファイルを指定するときも、`-m e2e` を付ける（例：`python -m pytest -m e2e tests/e2e/test_main_flow.py`。付けないと、外されて何も動かない）。初めて動かす前と、Playwright の版を上げたときに、ブラウザを入れる：`python -m playwright install chromium`
- 操作を目で見るとき：`python -m pytest -m e2e --headed --slowmo 500`（ブラウザの画面を出し、1つの操作ごとに0.5秒待つ）
- Claudeの作業環境：`E2E_CDN_FROM_NPM=1 python -m pytest -m e2e`。CDN（jsDelivr）に届かないため、この環境変数があるときだけ、CDNへの読み込みに、`node_modules` の同じ版のファイル（`npm ci` で入る）で答える（`tests/e2e/conftest.py`）。ブラウザが `integrity`（SRI）を確かめるので、違うファイルなら読み込まれない。CIとKomaのMacでは、付けない（CDNから読む）

### 仕組み（`tests/e2e/conftest.py`）
- テストごとに、migrationで作った雛形のDB（`tests/conftest.py` の `template_db`）を一時ディレクトリにコピーし、そのDBで、アプリを別のスレッドで起動する（空いているポート）。実データのDBに触れない（「開発用DB（`instance/app.db`）を触らない仕組み」も、そのまま効く）
- アプリは、ふだんと同じく、サーバーの中の例外を外へ出さない設定（`PROPAGATE_EXCEPTIONS` を `False`）で動かす（APIの500を、JSONで返すため）
- ページで起きたJavaScriptの例外を、fixture `page_errors` に集める。テストの最後に、空であることを確かめる

### 書き方
- 日付は、今日からの相対で決める（下の「画面の確認」）。週表示は日曜始まり。ブラウザの「今」は、`page.clock.set_fixed_time` で、テストの「今日」の正午に固定する（テストの途中で日付をまたいでも、Pythonとブラウザの「今日」がずれないように）
- 「ないこと」を確かめる前に、同じ画面で「あること」を確かめて、読み込みが終わったことを確かめる（読み込みの前に「ない」と判定されて、確認が空振りになるのを防ぐ）。例：主な流れでは、同じ週の木曜日の授業の予定が出てから、休講日の水曜日に授業の予定がないことを確かめる
- 要素は、`id` か、読み上げの名前（`get_by_role` の `name`）で探す。見た目のための class には、なるべく頼らない（FullCalendarの日付の列など、ほかに手がかりがない場合を除く）

## 画面の確認
画面が変わるタスクでは、Komaが、Macで触って確かめる。Claudeがブラウザで確かめるときも含めて、次の知見を使う（Task 008〜021で分かったこと）。

- データ：デモのDB（`database.md` の「デモ用の架空のデータ」）か、確認用の架空のデータで確かめる。実データのDBで確かめるときは、データを変える操作の前に、Komaがバックアップを取る（`database.md` の「実データのDBの扱い」）
- 日付：確認用のデータは、確認する日からの相対の日付で作り、日付をまたがずに確かめる（「直近の締切」欄や期限切れの表示は、今日によって変わるため）
- 取得：FullCalendarは、取得済みの範囲を取得し直さない（`lazyFetching`）。取得を確かめる手順には、取得を起こす操作（取得済みの範囲の外へ移る、絞り込みやモードを切り替える）を書く
- 再読み込みは、ページを開き直して行う。スクリーンショットは古いことがあるため、表示は、DOMで確かめる
- 空き枠を押す手順は、それより前の手順で作った予定と重ならない枠にする
- 週をまたぐかどうかが曜日で変わる手順は、「次へ」「前へ」で移る形にするか、曜日による違いを書く
- コンソールは、「JavaScriptの例外（`Uncaught …`）が出ていない」ことで確かめる。想定した400・404の応答は、Chromeが「Failed to load resource」として記録するため、除いて考える
- `grep -r` などの結果の並びは、環境によって違うことがある。件数で確かめ、並びは期待しない
