# Task 023 データの保護・DBの切り替え・デモデータ・E2Eの基盤

- 段階：1 地固め（`docs/roadmap.md`）
- 決定の記録：`docs/decisions/0001-development-system-and-plan.md`（以下、ADR 0001）の「自動の確認」「実データでの利用」
- ブランチ：`feature/023-data-protection-and-e2e`
- 設計の承認：Koma、2026-10-25（推奨案A〜Eをすべて承認）

## 目的
実データのDB（KomaのMacの `instance/app.db`）を、手作業に頼らずに守る。実データに触れずに画面を確かめられるようにする（DBの切り替えと、デモ用の架空のデータ）。画面の主な流れを、自動で確かめる（E2E）。

## 範囲
1. DBの切り替え：環境変数 `DATABASE_URL` で、使うDBを変えられるようにする。起動のとき、使っているDBを表示する
2. バックアップ：起動のときの1日1回の自動バックアップ（実データのDBだけ）と、手動のコマンド `flask --app app backup-db`
3. デモ用の架空のデータ：コマンド `flask --app app create-demo-db`
4. E2E：Playwright（pytestから動かす）の基盤と、主な流れの1本。CIに、ジョブ `e2e` を足す
5. `CLAUDE.md` に、ライブラリの版の規則（公開から2週間以上）を足す
6. 資料の更新（下の「決めたこと」の「書いた場所」）と、roadmap（Task 022の完了、Task 023の状態）。持ち越し 022-L6 を直す

## 非対象
- バックアップから戻すコマンド（実データを上書きする操作のため、人が手順で行う）
- クラウドでのバックアップ（クラウドへの公開のタスク。ADR 0002 で Task 026 になった）。SQLite以外のDBのバックアップ
- 起動したまま日をまたいだときの自動バックアップ（次の起動まで作らない。必要なら手動で取る）
- 画面の変更（デモのDBを使っていることを画面に出す、など）
- E2Eで、すべての操作を網羅すること（手動の確認を置き換えない。ADR 0001）
- DBの構造（migrationを作らない）

## 決めたこと
Komaの承認（2026-10-25）。

| 項目 | 決定 | 書いた場所 |
|---|---|---|
| 要求定義の変更（A） | 「初期段階ではバックアップの仕組みは作らない」を、「実データのDBは、起動のときに1日1回、自動でバックアップする。手動でも取れる」に変える | `requirements.md` の「非機能要件」 |
| バックアップの取り方（A） | Python標準の `sqlite3` のオンラインバックアップで、元のDBを読み取り専用で開いてコピーする。コピーのあと、壊れていないこと（`PRAGMA integrity_check`）と、各テーブルの件数が元と同じことを確かめる。途中のファイルは別の名前で作り、確かめてから正式な名前にする | `architecture/overview.md` の「データの保護（バックアップ）」 |
| 置き場所と名前（A） | DBのファイルと同じフォルダの `backups/`（実データのDBなら `instance/backups/`）。自動：`app-YYYYMMDD-auto.db`。手動：`app-YYYYMMDD-HHMMSS-<ラベル>.db`（ラベルの初期値は `manual`。英数字・`-`・`_`）。同じ名前のファイルは上書きしない | 同上 |
| 自動のバックアップ（A） | `python run.py` の起動のとき。対象は実データのDB（`instance/app.db`）だけ。その日の分があれば作らない。自動のものは新しい30個を残し、それより古い自動のものを消す（手動のものは消さない）。失敗したら、警告を表示して、起動を続ける | 同上 |
| 手動のバックアップ（A・C） | `flask --app app backup-db [--label …]`。対象は、使っているDB（SQLiteのファイル）。失敗したら、エラーで終わる。migrationの適用の手順の「バックアップ」を、このコマンドに置き換える | 同上、`development/database.md` |
| 戻し方（A） | コマンドは作らない。手順（サーバーを止める → 今のDBもバックアップする → コピーで戻す）を書く | `development/database.md` |
| DBの切り替え（B） | 環境変数 `DATABASE_URL`（SQLAlchemyの形のURL）。設定がない・空のときは、これまでどおり `sqlite:///app.db`（`instance/app.db`）。`flask --app app db …` にも効く。`run.py` は、起動のとき、使っているDBと、実データのDBかどうかを表示する（URLのパスワードは隠す） | `architecture/overview.md` の「DBの切り替え（環境変数）」 |
| コマンドの形（C） | 手動のバックアップとデモデータは、Flaskのコマンド（`app/cli.py`。`create_app` で登録する） | `architecture/overview.md` |
| デモデータ（C） | `flask --app app create-demo-db [--replace]`。使っているDBに作る。実データのDB（`instance/app.db`）には作らない。SQLiteのファイルだけ。ファイルがあれば止まる（`--replace` で作り直す）。migrationで空のDBを作り、アプリのAPIを（Flaskの `test_client` で）呼んで登録する。中身は、今日を含む学期1つと、架空の授業・休講日・予定・課題。日付は今日からの相対 | `development/database.md` の「デモ用の架空のデータ」 |
| デモデータの守り（レビューの023-L2。Komaの承認、2026-10-26） | 実データのDBのバックアップのフォルダ（`instance/backups/`。下のフォルダを含む）の中にも、デモデータを作らない（`--replace` でも）。フォルダは、パスの文字でなく、フォルダそのもので比べる | `development/database.md` の「デモ用の架空のデータ」、`architecture/overview.md` の「DBの切り替え（環境変数）」 |
| デモデータの作り直し（2026-10-26の精査） | `--replace` は、このコマンドで作ったデモのDB（SQLiteの見出しの `application_id` に印のあるもの）だけを作り直す。途中で失敗したら、作りかけのDBを消す。学期名の前期・後期の区切りは、画面の初期値（`ui_ux.md`）と同じ4〜8月・9〜3月 | `development/database.md` の「デモ用の架空のデータ」 |
| E2Eの印と時計（2026-10-26の精査） | `tests/e2e/` の中のテストには、`conftest.py` が印 `e2e` を自動で付ける。ブラウザの「今」を、テストの「今日」の正午に固定する | `development/testing.md` の「E2Eテスト」 |
| E2Eの置き方（D） | `tests/e2e/`。印 `e2e` を付け、ふだんの `python -m pytest` からは外す（`pytest.ini`）。`python -m pytest -m e2e` で動かす | `development/testing.md` の「E2Eテスト」 |
| E2Eのアプリ（D） | テストごとに、一時ディレクトリのDB（migrationで作った雛形のコピー）で、アプリを別のスレッドで起動する（実データのDBに触れない） | 同上 |
| CDNの代用（D） | 環境変数 `E2E_CDN_FROM_NPM=1` のときだけ、CDN（jsDelivr）への読み込みに、`node_modules` の同じ版のファイルで答える（Claudeの作業環境用。CIはCDNを読む）。ブラウザがSRIを確かめる | 同上 |
| CI（D） | ジョブ `e2e`（Python 3.11）を足す：`pip install -r requirements-dev.txt` → `python -m playwright install --with-deps chromium` → `python -m pytest -m e2e`。マージのあと、Komaが、ルールセットの必須チェックに `e2e` を足す | `.github/workflows/ci.yml`、`development/testing.md` の「CI」 |
| ライブラリ（E） | Python：playwright 1.63.0、pytest-playwright 0.10.0、pyee 13.0.1、greenlet 3.5.6、python-slugify 9.1.3、text-unidecode 1.3。npm：bootstrap 5.3.8、fullcalendar 6.1.21（CDNの代用だけ）。どれも開発のときだけ使う | `requirements-dev.txt`・`package.json`、`architecture/overview.md` の「技術スタック」 |
| 版の規則 | ライブラリ・道具の版は、公開から2週間以上たったものを選ぶ（Komaの承認、2026-10-24） | `CLAUDE.md` |

## 段階（commit）
1. 計画書（この資料）と roadmap
2. DBの切り替え（`app/config.py`・`run.py`）とテスト
3. バックアップ（`app/backup.py`・`app/cli.py`・`run.py`）とテスト
4. デモデータ（`app/demo_data.py`・`app/cli.py`）とテスト
5. E2E（ライブラリ・`pytest.ini`・`tests/e2e/`）とCI
6. 資料（`requirements.md`・`architecture/overview.md`・`development/database.md`・`development/testing.md`・`development/workflow.md`・`architecture/api_endpoints.md` の古い文）、`CLAUDE.md`、`README.md`、`docs/README.md`。`tests/conftest.py` の守りを、`instance/` の中のすべてのファイルに広げる

## 受け入れ条件
- `DATABASE_URL` がない・空のときは、これまでどおり `instance/app.db` を使う。あるときは、その接続先を使う
- `python run.py` の起動で、使っているDBが表示される。実データのDBを使うときは、その日の自動バックアップが `instance/backups/` にでき（その日の分があれば作らない）、30個を超えた古い自動のものが消える（手動のものは残る）
- `flask --app app backup-db` で、手動のバックアップができる。既存のファイルを上書きしない。失敗したときは、正式な名前のファイルが残らない
- バックアップは、壊れていないことと、件数が元と同じことを確かめたものだけが、正式な名前になる
- `flask --app app create-demo-db` は、実データのDB・既存のファイル（`--replace` なし）・SQLite以外では、何も変えずにエラーで終わる。それ以外では、今日を含む学期と、架空のデータを作る
- `python -m pytest`（E2Eを除く）、`python -m pytest -m e2e`、`ruff check .`、`npm run lint` が、すべて通る
- CIの3つのジョブ（`python`・`javascript`・`e2e`）が、このPRで合格する
- テストが、`instance/` の中のファイル（`app.db` とバックアップ）を作らない・変えない・消さない（`tests/conftest.py` が、テストの前後で確かめる）

## テストの観点
- DBの切り替え：設定がない・空・あるときの接続先。表示の文（実データかどうか、パスワードを隠す）
- バックアップ：中身と件数が元と同じ。名前。その日の分があれば作らない。30個を超えた古い自動のものだけが消え、手動のもの・ほかの名前のファイルは残る。既存のファイルを上書きしない。検査に失敗したら、正式な名前のファイルが残らない。元のDBの内容（ハッシュ）が変わらない。SQLiteのファイルでないDB・存在しないDBの扱い。起動のときの処理（実データのDBでなければ作らない、失敗しても例外を外に出さない）
- 手動のコマンド：成功の表示と終了コード、ラベルの検査、失敗のときの終了コード
- デモデータ：実データのDB・既存のファイル・SQLite以外を断り、何も変えない。`--replace`。作ったデータ（学期が今日を含む、授業の予定が休講日を除いてできる、課題の完了・未完了・期限切れ）
- E2E：主な流れ（学期 → 休講日 → 授業 → カレンダー → 課題 → 完了）と、その間にJavaScriptの例外が出ないこと。日付は今日からの相対

## 確認の方法
- Claude：上のコマンドを、作業環境で実行する（E2Eは `E2E_CDN_FROM_NPM=1` で）。`python run.py` の起動と、2つのコマンドも、作業環境の空のDBで動かす。PRの説明に、結果を書く
- CI：3つのジョブが合格する
- 別の目のレビュー：計画書・該当する仕様・PRの差分を渡す。データの保護（実データのDBを変えない・消さない）を重点的に見てもらう
- Koma：PRを読む。マージのあと、ルールセットに `e2e` を足す。Macで `pip install -r requirements-dev.txt` と `npm ci`（E2Eを手元で動かすときだけ `python -m playwright install chromium`）。画面は変わらないが、Macで次を確かめる：起動すると今日の自動バックアップができる、手動のコマンドが動く、デモのDBで起動できる

## 止まる条件
- 実データのDBを変える・消す可能性のある処理が、設計のほかに必要になった
- 既存のテストが、この変更のために失敗し、仕様の変更なしには直せない
- Playwrightの版が、作業環境のChromium・CIで動かない（版を変える場合は、Komaに確かめる）
- CIの設定ファイルを、Claudeがpushできない（そのファイルだけ、Komaにcommitを頼む）
