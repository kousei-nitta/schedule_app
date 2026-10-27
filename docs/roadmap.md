# ロードマップ

進行管理の資料：現在地、段階とタスク、未解決の持ち越し。

- 仕様は、設計資料が正本（`docs/README.md`）。この資料は、実装の根拠にしない
- 段階と順序を決めた理由は、`docs/decisions/0001-development-system-and-plan.md` の「今後の計画（段階）」。Task 024（セキュリティの土台）を入れて、番号をずらした理由は、`docs/decisions/0002-security-baseline-before-login.md`。Pythonを3.14にした理由は、`docs/decisions/0003-python-3-14.md`
- 更新の仕方は、`docs/development/workflow.md` の「roadmapの更新」
- Task 001〜021の記録（完了したタスクの一覧、持ち越し、進め方の決定）は、`docs/archive/roadmap_until_task021.md`

## 現在地
最後に更新した時点の状態。最新の状態は、`main` のコミットの履歴（最後のマージ）で確かめる。

| 項目 | 状態 |
|---|---|
| 最後にマージしたもの | Task 023の追補（PR #45、2026-10-27。マージコミット `e901acb`） |
| 実装中のタスク | Task 024（セキュリティの土台。このPR） |
| 次に設計するタスク | Task 025（ログインと、利用者ごとのデータ） |
| 自動の確認 | pytest 1252件（E2Eを除く。ほかに、大文字・小文字を区別しないファイルシステム（KomaのMac）でだけ動く2件）、E2E 1件（主な流れ。CSPの違反がないことを含む）、ruff・ESLint・モデルとmigrationのずれ：指摘なし（Task 024のブランチ。Python 3.14。CIの3つのジョブで確かめる） |
| DBの構造 | 初期migration（`0280f6cf8d09`）と、休講日の `closures` テーブル（`42bd53808fa1`）。Task 010〜024では変えていない |
| 実データのDB | 2026-10-24から、KomaがMacの `instance/app.db` で、実データで使っている。起動のときの自動のバックアップと、手動のコマンドで守る（Task 023。`docs/development/database.md` の「実データのDBの扱い」） |
| 最終更新 | 2026-10-27（Task 024） |

## 段階とタスク
025より後の番号は仮。段階や順序を変える場合は、`docs/decisions/` に残す（2026-10-26に、ADR 0002 で、Task 024を入れて、ログイン以降の番号を1つずつずらした）。

| 段階 | Task | 内容 | 状態 | 設計で決めること・注意 |
|---|---|---|---|---|
| — | 001〜021 | MVP（学期・授業・休講日・予定の自動生成・カレンダー・課題・予定の操作・学期の編集と削除） | 完了（PR #1〜#38） | 一覧は `docs/archive/roadmap_until_task021.md` |
| 1 地固め | 022 | 開発体制の移行：資料の分割（`docs/architecture/`）・索引・`open_questions.md`・`docs/development/`、過去の資料の `docs/archive/` への移動、この資料の作り直し、CI（pytest・ruff・ESLint・migrationのずれ）、`requirements-dev.txt`、`CLAUDE.md`、最低限のREADME、Copilot向けの指示ファイル（`.github/` の中）の削除 | 完了（PR #40） | マージのあと、`main` のルールセットに、ステータスチェック（`python`・`javascript`）の必須を足した（Koma）。Macで `pip install -r requirements-dev.txt` を実行した（Koma） |
| 1 地固め | 023 | データの保護（起動のときの1日1回の自動バックアップと、手動のコマンド）、DBの切り替え（環境変数）、デモ用の架空のデータ、Playwrightの E2E の基盤（主な流れ）とCIへの追加。計画書は `docs/tasks/023_data_protection_and_e2e.md` | 完了（PR #44。追補は PR #45） | `main` のルールセットに、ステータスチェック `e2e` の必須を足した（Koma）。追補：Macで書きかけの記録のテストが失敗した（テストの準備が、MacのSQLiteで書きかけの記録を作れていなかった。アプリの守りは正しい）のを直した。マージの前に、Macで追補のブランチの `python -m pytest` が1211件すべて合格した（大文字・小文字を区別しないファイルシステムだけのテスト2件を含む。Koma、2026-10-27）。Macで、自動と手動のバックアップが正しく動くことを確かめた（Koma）。MacにはNode.jsを入れていないため、`npm ci` は不要とした |
| 1 地固め | 024 | セキュリティの土台（ADR 0002）：Hostヘッダーの検査、深い入れ子のJSON、セキュリティのヘッダー（CSP）、`debug` を指定したときだけに、ESLintの禁止の規則、CI・依存の守り（アクションのSHAでの固定・Dependabot など）、`SECURITY.md`、設計資料 `architecture/security.md`、Python 3.14 への移行（ADR 0003）。DBの構造は変えない。計画書は `docs/tasks/024_security_baseline.md` | 実装中（このPR） | Komaが行ったこと（2026-10-27）：開発の環境の pip・certifi の更新、GitHub の secret scanning・push protection・Dependabot alerts・Dependabot security updates・Private vulnerability reporting の有効化。マージの前に、Macで Python 3.14.10（pyenv）を入れ、`.venv` を作り直して確かめる（Koma）。Playwright 1.64.1 は、Dependabotが、2026-11-05以降にPRを出す |
| 2 クラウドへ | 025 | ログインと、利用者ごとのデータ（`users` テーブルと、データの利用者のID。まずローカルで） | 未着手 | 実データのDBの構造を変える（Komaがバックアップを取ってから適用）。ログインの仕組みを、別の目のレビューで重点的に確かめる。認可（他人のデータに触れない）の網羅的なテスト、`SECRET_KEY`、Cookie、CSRF、試行の制限（ADR 0002）。デモデータの作成とE2Eに、ログインの手順を足す（デモデータは `test_client` を1つのアプリのコンテキストの中で呼ぶため、`g` と `db.session` が要求の間で共有されることに注意） |
| 2 クラウドへ | 026 | クラウドへの公開（ホストとDB、本番の設定、日本時間の「今日」、データの移行、バックアップ）と、スマホでの最低限の表示 | 未着手 | ホストとDBは、設計のときに改めて調べて決める（候補と条件は、ADR 0001）。受け入れ条件に、公開の前のセキュリティの点検を入れる（ADR 0002。点検の一覧は `architecture/security.md` の「公開の前の点検」）。ホストは、Python 3.14 を使えるものにする（ADR 0003）。実データのDBの決め方（今はパス `instance/app.db`。本番では設定で決め、壊す操作のコマンドを断る）、`postgres://` の形のURL（SQLAlchemy 2 は受け付けない）、`Config` が読み込みの時点で環境変数を読むこと（`create_app` の時点で読む形に）、クラウドのDBのバックアップ（自動のバックアップは `run.py` の中だけ。定期実行で `backup-db`、または `pg_dump`）、`date.today()` を1か所にまとめて日本時間に（CIのE2Eに `TZ`）、読み取り専用のファイルシステムでの `instance/` の作成 |
| 3 見た目と使い心地 | 027〜 | デザインの方向を、主な画面の案（2〜3案）で決めてから実装する。アニメーション、スマホの画面、`index.html` の分割 | 未着手 | Apple風の考え方を取り入れる（Appleの素材そのものは使わない） |
| 4 見せる・使ってもらう | — | 画面を載せたREADMEとデモ。他の人に開くかの判断 | 未着手 | 段階2・3が安定してから判断する |
| 候補 | — | 予定の重複の警告 | 未着手 | 段階3のあとの候補 |
| 候補 | — | 起動したままのときの自動のバックアップ（起動したまま日をまたぐと、次の起動まで作られない。最新のバックアップが古いときの警告、日が変わって最初の操作で作る、など） | 未着手 | Task 023のレビュー。Task 026（クラウド）で、バックアップの仕組みが変わるため、それまでに必要かを判断する |

- 未決定事項と将来の検討事項は、`docs/open_questions.md`。画面の未決定事項は、実データで使ってから決める
- 使って気づいたことは、GitHubのIssueに書き、重さに応じて、段階の間に小さなタスクとして入れる（`docs/development/workflow.md`）

## 未解決の持ち越し
レビューで見つかり、直さずにマージしたもの（Lowなど）。後続のタスクで直す。

| ID | 内容 | 見つけた時 | 扱う予定 |
|---|---|---|---|
| — | （なし） | — | — |

- Task 021までの持ち越し（010-N1〜021-N1の17件）は、Task 022で閉じた。多くは、Copilotが計画書を書き写して報告する経路に関するもので、開発体制の変更で不要になった。ブラウザ確認で分かったこと（010-N1・018-N2・020-N2・020-N3・021-N1）は、`docs/development/testing.md` の「画面の確認」に、`sqlite3` を `-readonly` で開くこと（011-L1）は、`docs/development/database.md` に残した。記録は `docs/archive/roadmap_until_task021.md`
