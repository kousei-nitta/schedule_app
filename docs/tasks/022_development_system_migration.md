# Task 022 開発体制の移行

- 段階：1 地固め（`docs/roadmap.md`）
- 決定の記録：`docs/decisions/0001-development-system-and-plan.md`（以下、ADR 0001）
- ブランチ：`feature/022-development-system-migration`
- 設計の承認：Koma、2026-10-25（推奨案1〜4をすべて承認）

## 目的
ADR 0001 の開発体制（Claudeが実装してPRを作り、CI・別の目のレビュー・Komaが確かめる）で、次のタスクから進められるようにする。資料を新しい構成に移し、自動の確認（CI）を入れる。**アプリの動きは変えない。**

## 範囲
1. 過去の資料の移動：Task 001〜021の計画書（Task MD）と、Task 021までのroadmapを `docs/archive/` へ移す（削除しない）。`.ignore` で、`docs/archive/` を検索から外す
2. `docs/architecture.md` の分割：ADR 0001 の「資料の構成」のとおり、`docs/architecture/` の6つの資料と、`docs/development/` に分ける。まず文を変えずに分け、文が失われていないことをスクリプトで確かめる
3. 分割の例外（ADR 0001 に書いたもの）の書き直しと、`docs/archive/` への移動
4. 新しい資料：`docs/README.md`（索引）、`docs/open_questions.md`、`docs/development/` の3つ（`workflow.md`・`testing.md`・`database.md`）
5. 曜日の読み替えの記述の整理：未決定事項から「将来の検討事項」へ移す（方式の案は残す）。`requirements.md`・`ui_ux.md`・`architecture/class_events.md` の該当する文を合わせて直す
6. 検査の道具：`requirements-dev.txt`、ruff（`ruff.toml`）、ESLint（`eslint.config.js`・`package.json`・`package-lock.json`）、モデルとmigrationのずれのテスト。ruffの指摘（10件）の修正。`migrations/env.py` の警告の修正
7. CI：`.github/workflows/ci.yml`
8. `CLAUDE.md`、最低限の `README.md`、`.github/copilot-instructions.md` の削除
9. `docs/roadmap.md` の作り直し（現在地・段階とタスク・未解決の持ち越しだけ）。Task 021までの持ち越し（010-N1〜021-N1）を閉じる

## 非対象
- アプリのコードの動き（Python・JavaScript・HTML・CSS）。変えるのは、ruffの指摘に合わせた長い行の折り返し（コメントと、テストのデータの行。構文木は変わらない）と、例外の印（`# noqa`）だけ
- DBの構造（migrationを作らない）
- 分割した資料の、経緯の削除などの中身の整理（その節を変えるタスクで、少しずつ行う。ADR 0001）
- コードの自動整形（ruff format）。E2Eテスト（Task 023）
- `main` のルールセットの変更（Koma）

## 決めたこと
ADR 0001 に書いたことのほか、設計で次を決めた（Komaの承認、2026-10-25）。

| 項目 | 決定 | 書いた場所 |
|---|---|---|
| ADR 0001 の構成図にない節の置き場所（推奨案1） | 「DBスキーマ変更の方式」「Flask-Migrateの操作の意味」「migrationの作成と適用」「開発中の注意」→ `development/database.md`。「制約の命名規則」→ `architecture/data_model.md`。「自動テスト（pytest）」→ `development/testing.md` | `docs/README.md` の索引 |
| 分割したあとの参照（推奨案2） | 節の名前だけの参照（「予定API」を参照、など）は、そのまま残し、`docs/README.md` に「節 → 資料」の一覧を置く。ファイル名を含む参照（`architecture.md` の「…」）は、ファイル名だけを新しい資料に書き換える | `docs/README.md` |
| migrationのずれの確認（推奨案3） | pytestのテストの中で、migrationで作った一時的なDBとモデルを比べる（`flask db check` と同じ確認）。CIは、pytestで確かめる | `development/testing.md` |
| pytestの置き場所（推奨案4） | `requirements.txt` はアプリを動かすものだけにし、pytest（と依存するもの）とruffは `requirements-dev.txt` に置く | `development/testing.md`、`CLAUDE.md` |
| ruffの対象 | 規則はE・F・W、1行79文字。`migrations/versions/` は外す（自動生成で、承認済みのファイルのため） | `ruff.toml`、`development/testing.md` |
| ESLintの規則 | 推奨の規則に、`no-var`・`prefer-const`・`eqeqeq`・`max-len`（80）・`quotes`（二重引用符）を足す。中に `"` を含む文字列だけ単引用符を許す（`avoidEscape`）。対象は `app/static/js/` | `eslint.config.js`、`development/testing.md` |
| 道具の版 | ruff 0.16.10、ESLint 10.12.0・`@eslint/js` 10.0.1・`globals` 17.13.0（公開から2週間以上たった版） | `requirements-dev.txt`・`package.json` |
| CI | PRと、`main` へのpushのときに動く。ジョブは `python`（Python 3.11：ruff・pytest）と `javascript`（Node.js 22：ESLint） | `.github/workflows/ci.yml`、`development/testing.md` |
| 「開発用DB」の呼び方 | 移した文の中の「開発用DB」は変えない。新しい資料では「実データのDB」と書き、`development/database.md` で、同じものを指すと説明する | `development/database.md` |
| 古いroadmapの「進め方の決定の記録」 | 今も有効なもの（Lowはマージを止めない、タスクを細かく分けすぎない、2つ目の利用者が出た時点で共通化する、ブラウザ確認の知見、`sqlite3 -readonly`）を `development/` と `CLAUDE.md` に移す。Copilot向けのもの（全文の付録、書き写し、報告の形、承認ゲートのSHA-256など）は、`docs/archive/` に残すだけにする | `development/`、`CLAUDE.md` |

## 分割の対応（`docs/architecture.md` → 新しい資料）
| 元の節 | 移す先 |
|---|---|
| 技術スタック（Bootstrap・FullCalendarの読み込みを含む）、ディレクトリ構成 | `architecture/overview.md` |
| データ設計（共通の約束〜関係）、制約の命名規則 | `architecture/data_model.md` |
| 繰り返し予定の扱い（その下の節）、授業のEventの生成処理 | `architecture/class_events.md` |
| API共通ルール（`api_helpers.py` を含む） | `architecture/api.md` |
| 学期API・授業API・休講日API・予定API・課題・タスクAPI | `architecture/api_endpoints.md` |
| JavaScriptの構成・FullCalendarの使い方・モード間の連携・`api.js` の仕様 | `architecture/frontend.md` |
| DBスキーマ変更の方式・Flask-Migrateの操作の意味・migrationの作成と適用・開発中の注意 | `development/database.md` |
| 自動テスト（pytest） | `development/testing.md` |
| 未決定事項 | `open_questions.md`（書き直す） |
| 開発の役割分担とGit運用 | `development/workflow.md`（書き直す） |
| 予定の自動生成より前に登録した授業（と、それに関する未決定事項） | `docs/archive/`（済んだ移行の手順） |

- 各資料の先頭に、題名と注意を足す（元の `##` の節が資料の全体になる `data_model.md`・`api.md`・`frontend.md` は、その節の見出しを題名にする）。見出しは、各資料の中で一番上の節が `##` になるように、階層だけを上げる（文は変えない）
- 分割で変える文は、例外（ADR 0001）と、次の機械的な変更だけ：ファイル名を含む参照の書き換え、移した先で意味が変わる自分の資料への参照（「このファイルの」「下記」）、体制の変更で事実と違うようになる文（ディレクトリ構成の `copilot-instructions.md`・作成済みの一覧、pytestの置き場所）、曜日の読み替え
- 「編集・削除の仕様」の段落は、移す節（予定の自動生成より前に登録した授業）の中に続けて書かれていたため、見出し「編集・削除の仕様」を足して、その段落を残す（ほかの節が「編集・削除の仕様」として参照している）

## 段階（commit）
1. 計画書（この資料）
2. 過去の資料の移動と `.ignore`
3. `architecture.md` の分割（文を変えない。参照のファイル名の書き換えを含む）
4. 例外の書き直しと、新しい資料（`open_questions.md`・`development/`・`docs/README.md`）、曜日の読み替え
5. 検査の道具と、指摘の修正
6. CI
7. `CLAUDE.md`・`README.md`、`.github/copilot-instructions.md` の削除
8. `docs/roadmap.md` の作り直し

## 受け入れ条件
- `docs/architecture.md` がなくなり、ADR 0001 の構成図の資料がそろっている
- 確認のスクリプト（`docs/archive/task022/check_architecture_split.py`）が「問題なし」で終わる：元の `architecture.md`（`396e8b5`）の、空でない行が、例外を除いて、決めた移す先の資料に、同じ順で、同じ文のまま入っている。足した行と、書き直した節の差分が、一覧で出る
- `docs/archive/` の過去の資料は、移す前と同じ内容（gitの名前の変更として扱われる）
- `docs/` の中で、`architecture.md`・`copilot-instructions.md` を指す参照が、`docs/archive/` と `docs/decisions/`（決定の記録）と、この計画書のほかに残っていない
- `ruff check .`・`npm run lint`・`python -m pytest` がすべて通る。pytestは1120件（今の1119件と、ずれのテスト1件）。`migrations/env.py` の `get_engine` の警告が出ない
- ずれのテストが、モデルを変えたときに失敗する（一時的にモデルに列を足して確かめ、元に戻す）
- CIの2つのジョブが、このPRで合格する
- `CLAUDE.md` に、コマンド・コーディング・テスト・DBとGitの禁止事項・PRの書き方がある。`.github/copilot-instructions.md` の規則のうち、今も有効なものが、`CLAUDE.md` か `development/` に入っている

## テストの観点
- 既存のテスト（1119件）が、変えずにそのまま通る（長い行の折り返しだけを変える）
- ずれのテスト：最新のmigrationを適用した一時的なDBと、モデルの間に差がない。差があるときは、差の内容がわかる失敗になる
- 開発用DB（`instance/app.db`）を、テストが読み書きしない（今の `conftest.py` の仕組みのまま）

## 確認の方法
- Claude：上のコマンドと、確認のスクリプトを、作業環境で実行する。PRの説明に、結果を書く
- CI：PRで、2つのジョブが合格する
- 別の目のレビュー：計画書・ADR 0001・PRの差分を渡す。確認のスクリプトも実行してもらう
- Koma：PRを読む（読む順番はPRの説明）。画面は変わらないため、Macでの動作確認は要らない。Macでは、一度だけ `pip install -r requirements-dev.txt` を実行する（pytestを `requirements-dev.txt` に移すため）

## 止まる条件
- 分割で、文を変えないと成り立たない箇所が、上の機械的な変更のほかに見つかった（Komaに確認する）
- 既存のテストが、長い行の折り返し以外の理由で失敗した
- CIの設定ファイルを、Claudeがpushできない（そのファイルだけ、Komaにcommitを頼む）
- 仕様の変更が要る判断に当たった
