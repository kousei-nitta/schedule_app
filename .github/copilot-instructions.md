# Copilot Instructions — スケジュール帳アプリ

## プロジェクト概要
大学生向けのスケジュール帳Webアプリ（授業・課題・アルバイト・その他の予定を一元管理）。
Python 3.11 + Flask + SQLite + Flask-SQLAlchemy + Flask-Migrate（採用済み）。ログインなし・単一ユーザー・ローカル動作。
カレンダー描画はFullCalendar（無料範囲のみ）、スタイルはBootstrapを使う。費用をかけない。

詳細は次の設計資料を参照すること。実装前に、タスクが関係する部分を必ず読む。
- `docs/requirements.md`（要求定義）
- `docs/architecture.md`（技術選定・データ設計・ディレクトリ構成）
- `docs/ui_ux.md`（画面・操作の仕様）

## 開発体制
- Claude：要求定義・設計・技術判断・実装方針・実装結果のレビュー
- GitHub Copilot Agent mode（あなた）：実装担当
- Koma（開発者）：最終判断・コード確認・テスト結果確認・Git管理

## 設計資料の扱い（最重要）
- `docs/requirements.md`・`docs/architecture.md`・`docs/ui_ux.md` は設計上の **正本**。**あなたが内容を変更してはならない。**
- タスク（`docs/tasks/` 配下）に書かれた範囲だけを実装する。範囲外の機能を先回りして実装しない。
- データモデル・技術選定・決定済みのUI/UXの挙動を、タスクの指示なしに変更しない。
- 設計資料に書かれていない「未決定事項」は、あなたの判断で決めない。

## 設計上の問題を見つけたとき
次のいずれかに当てはまる場合は、下記の手順に従う。
- 設計資料の内容に問題がある（矛盾・抜け・実現困難など）
- タスクの指示が設計資料と矛盾している
- 設計資料にない判断が必要になった（未決定事項に当たった）

手順：
1. **ファイルを変更しない**
2. **実装を停止する**
3. **Copilotのチャット上で、次の4点を報告する**
   - 問題点
   - 発生理由
   - 変更した場合の影響
   - 推奨案（必要な場合）
4. Komaの判断を待つ。回答があるまで実装を再開しない

設計を変更する場合の順序は次のとおりで、設計資料の更新はKomaの承認後にKomaまたはClaudeが行う。

既存設計 → 問題点 → 変更案 → Komaの承認 → 設計資料の更新 → 実装

## DBスキーマとmigration
Flask-Migrateは採用済みの技術として扱う。詳細は `docs/architecture.md` の「DBスキーマ変更の方式」を参照。

- DBスキーマ（テーブル・カラムの追加や変更など）は、設計資料（`docs/architecture.md` のデータ設計）の承認なしに変更しない
- テーブルの作成・変更はmigrationを通して行う。`db.create_all()` は使わない
- migrationファイル（`migrations/versions/` 配下）もレビュー対象。**自動生成されたmigrationを、確認なしに採用（適用）しない**
- `flask db migrate` でmigrationを生成したら、`flask db upgrade` を実行する前に、次をチャットで報告してKomaの承認を待つ
  - 作成・変更されるテーブルとカラム（名前・型・NULL可否）、外部キー
  - `docs/architecture.md` のデータ設計との差異の有無
  - `upgrade()` の中に、削除（drop）や変更（alter）を含む操作がないか（`downgrade()` の巻き戻し用の処理は対象外）
- 設計資料にない変更や、`upgrade()` の中に削除・変更を含む操作がmigrationに含まれていた場合は、適用せず「設計上の問題を見つけたとき」の手順に従う
- `instance/app.db` や `migrations/` の削除・作り直しは、Komaの確認なしに行わない

## すでに完了している環境構築（やり直さない・変更しない）
次は作成・設定済み。再実行や提案をしない。
- Gitリポジトリの初期化、GitHubリモートの接続
- `.gitignore`（Python用）
- `.venv`（プロジェクト専用の仮想環境）とFlaskのインストール
- `.vscode`の設定（Python Interpreterは`.venv`）
- Copilot拡張とAgent modeの利用環境

`.gitignore`・`.vscode`・Git設定は、必要性をKomaに確認せずに変更・削除しない。

## コーディング方針
- PEP8に沿う
- 変数名・関数名は意味が分かる名前にする（過度な省略をしない）
- 複雑な処理や、すぐには分からない判断にはコメントを入れる。コメント・docstringは日本語で書く
- 凝った書き方より、読んで理解しやすい書き方を優先する（開発者が自分で読んで理解・修正できることが要件）
- 新しいライブラリを追加する場合は、事前にKomaに確認する（費用がかかるものは追加しない）
- JavaScript（`app/static/js/`）：
  - ES modulesで書く。`import` は拡張子つきの相対パス（例：`"./api.js"`）。`export` は名前つきにし、`export default` は使わない
  - `const`／`let` を使い、`var` は使わない。セミコロンを付ける。インデントは空白2つ。文字列は二重引用符。比較は `===`。非同期は `async`／`await`
  - 使わない：`innerHTML`・`outerHTML`・`insertAdjacentHTML`・`document.write`・`eval`、HTMLの `onclick` などの属性、`style` 属性の操作
  - ユーザーの入力やAPIの応答の文字を表示するときは、`textContent` を使う
  - `fetch` は `api.js` の中だけで呼ぶ。Jinjaの値をJavaScriptに書かない
  - コメントは、Pythonと同じく、日本語で書く

## テスト
詳細は `docs/architecture.md` の「自動テスト（pytest）」を参照。

- APIを実装するタスクでは、そのAPIのpytestのテストを作成する（範囲は、タスクのMDに書かれたとおり）
- **テストが通ること（`python -m pytest`）を確認してから、完了を報告する。** 通らないテストを残したまま報告しない。原因が設計資料やタスクにある場合は、「設計上の問題を見つけたとき」の手順に従う
- テスト用DBの扱いは、`docs/architecture.md` に従う。**テストが、開発用のDB（`instance/app.db`）を読み書きしてはならない。** テストの実行の前後で、`instance/app.db` が変わっていないことを確認する。変わっていた場合は、直さずに、停止して報告する
- `create_app` をテストで呼ぶときは、`SQLALCHEMY_DATABASE_URI` を、一時ディレクトリのDBにして必ず指定する
- テストを通すために、期待値を設計資料に反して書き換えない。テスト専用のコード（テスト用のルートなど）を、`app/` に入れない

## 作業の進め方
1. 指定された `docs/tasks/` のタスクファイルを読む
2. 関係する設計資料を読む
3. タスクの「やること」の範囲だけを実装する
4. タスクの「完了の確認方法」に沿って動作を確認する（テストがあるタスクでは、`python -m pytest` の結果を含む）
5. 実装内容をチャットで簡潔に報告する（変更したファイルと、確認結果）

## Git
- **Git commit / push は行わない。** ブランチの作成・切替、commit、push、マージはすべてKomaが行う
- 作業はKomaが用意したタスクごとのブランチ（`feature/タスク番号-説明`）の上で行われる前提
- `git status` や `git diff` のような、読み取りだけのGitコマンドは使ってよい
- `.gitignore` は変更しない。`instance/app.db` や `.pytest_cache/` などが追跡対象になっている場合は、変更せずKomaに報告する
