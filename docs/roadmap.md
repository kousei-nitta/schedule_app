# ロードマップ

進行管理の資料：現在地、段階とタスク、未解決の持ち越し。

- 仕様は、設計資料が正本（`docs/README.md`）。この資料は、実装の根拠にしない
- 段階と順序を決めた理由は、`docs/decisions/0001-development-system-and-plan.md` の「今後の計画（段階）」。Task 024（セキュリティの土台）を入れて、番号をずらした理由は、`docs/decisions/0002-security-baseline-before-login.md`。Pythonを3.14にした理由は、`docs/decisions/0003-python-3-14.md`。ログインの方式の理由は、`docs/decisions/0004-login-and-user-data.md`。公開先と、端末の印の理由は、`docs/decisions/0005-public-hosting-and-device-cookie.md`
- 更新の仕方は、`docs/development/workflow.md` の「roadmapの更新」
- Task 001〜021の記録（完了したタスクの一覧、持ち越し、進め方の決定）は、`docs/archive/roadmap_until_task021.md`

## 現在地
最後に更新した時点の状態。最新の状態は、`main` のコミットの履歴（最後のマージ）で確かめる。

| 項目 | 状態 |
|---|---|
| 最後にマージしたもの | Dependabot の #51（Playwright 1.64.0 ほか）と #50（ESLint 10.13.0）（2026-11-02。マージコミット `498ad57`・`fa22620`）。その前は Task 025（PR #49、2026-11-02。マージコミット `0df68d5`） |
| 実装中のタスク | Task 026（クラウドへの公開。このPR） |
| 次に設計するタスク | Task 027〜（見た目と使い心地） |
| 自動の確認 | pytest 1,865件が合格（2件 skip、5件 xfail：受け入れた弱さ。Task 025 の2件と、Task 026 の3件）、E2E 6件が合格、ruff・ESLint が合格（2026-11-08、Task 026。Claude の作業環境の Python 3.14） |
| DBの構造 | 初期migration（`0280f6cf8d09`）、休講日の `closures` テーブル（`42bd53808fa1`）、利用者の表と、データの持ち主（`a750d741785a`。Task 025）。Task 026で、端末の印の `trusted_devices` を足す（このPR。本番のDBは、移行の写しに当てて作る） |
| 実データのDB | 2026-10-24から、KomaがMacの `instance/app.db` で、実データで使っている（Task 023の自動のバックアップと手動のコマンドで守る。`docs/development/database.md`）。Task 026のマージのあと、Komaがクラウド（alwaysdata）へ移す（`docs/development/deploy.md`） |
| 最終更新 | 2026-11-10（Task 026） |

## 段階とタスク
025より後の番号は仮。段階や順序を変える場合は、`docs/decisions/` に残す（2026-10-26に、ADR 0002 で、Task 024を入れて、ログイン以降の番号を1つずつずらした）。

| 段階 | Task | 内容 | 状態 | 設計で決めること・注意 |
|---|---|---|---|---|
| — | 001〜021 | MVP（学期・授業・休講日・予定の自動生成・カレンダー・課題・予定の操作・学期の編集と削除） | 完了（PR #1〜#38） | 一覧は `docs/archive/roadmap_until_task021.md` |
| 1 地固め | 022 | 開発体制の移行：資料の分割（`docs/architecture/`）・索引・`open_questions.md`・`docs/development/`、過去の資料の `docs/archive/` への移動、この資料の作り直し、CI（pytest・ruff・ESLint・migrationのずれ）、`requirements-dev.txt`、`CLAUDE.md`、最低限のREADME、Copilot向けの指示ファイル（`.github/` の中）の削除 | 完了（PR #40） | マージのあと、`main` のルールセットに、ステータスチェック（`python`・`javascript`）の必須を足した（Koma）。Macで `pip install -r requirements-dev.txt` を実行した（Koma） |
| 1 地固め | 023 | データの保護（起動のときの1日1回の自動バックアップと、手動のコマンド）、DBの切り替え（環境変数）、デモ用の架空のデータ、Playwrightの E2E の基盤（主な流れ）とCIへの追加。計画書は `docs/tasks/023_data_protection_and_e2e.md` | 完了（PR #44。追補は PR #45） | `main` のルールセットに、ステータスチェック `e2e` の必須を足した（Koma）。追補：Macで書きかけの記録のテストが失敗した（テストの準備が、MacのSQLiteで書きかけの記録を作れていなかった。アプリの守りは正しい）のを直した。マージの前に、Macで追補のブランチの `python -m pytest` が1211件すべて合格した（大文字・小文字を区別しないファイルシステムだけのテスト2件を含む。Koma、2026-10-27）。Macで、自動と手動のバックアップが正しく動くことを確かめた（Koma）。MacにはNode.jsを入れていないため、`npm ci` は不要とした |
| 1 地固め | 024 | セキュリティの土台（ADR 0002）：Hostヘッダーの検査、深い入れ子のJSON、セキュリティのヘッダー（CSP）、`debug` を指定したときだけに、ESLintの禁止の規則、CI・依存の守り（アクションのSHAでの固定・Dependabot など）、`SECURITY.md`、設計資料 `architecture/security.md`、Python 3.14 への移行（ADR 0003）。DBの構造は変えない。計画書は `docs/tasks/024_security_baseline.md` | 完了（PR #46） | Komaが行ったこと（2026-10-27）：開発の環境の pip・certifi の更新、GitHub の secret scanning・push protection・Dependabot alerts・Dependabot security updates・Private vulnerability reporting の有効化。マージの前に、Macで Python 3.14.10（pyenv）を入れ、`.venv` を作り直し、このブランチの `python -m pytest` が1254件すべて合格（大文字・小文字を区別しないファイルシステムだけのテスト2件を含む）、`python -m pytest -m e2e` が1件合格、デモのDBと実データで、画面・コンソール（CSPのエラーなし）・自動バックアップが想定どおりと確かめた（Koma）。マージのあと、Dependabotが最初のPRを2つ出した。#47（pip の小さな更新4件）は、差分の確認（新たに要る依存なし・公開から17日以上）のあと、マージした（Koma、2026-10-30。Macで `pip install -r requirements-dev.txt` も実行）。#48 は、下の「未解決の持ち越し」 |
| 2 クラウドへ | 025 | ログインと、利用者ごとのデータ（`users` テーブルと、データの利用者のID。まずローカルで）。計画書は `docs/tasks/025_login_and_user_data.md` | 完了（PR #49） | 役割を分けたAIエージェント（脅威の分析・攻撃のテスト・2つの別の目のレビュー）で確かめた（ADR 0004）。マージの前に、Komaが Mac の Chrome と Safari で確かめ、見つかった2件（ログアウトが遅い、Safari で「戻る」・スワイプでログアウトの前の画面が見えた）を、PR #49 の中で直した。マージのあと（2026-11-02、Koma）：実データのDBに、`backup-db --label before-025` → `db upgrade`（`a750d741785a`）→ 適用の後の確認（版・件数・`users`・`user_id`・スキーマの差。問題なし）→ `rename-user` で推測されにくいIDに変更 → `set-password` → 新しいIDでログインし、今までのデータが見えること・ログアウトできることを確かめた |
| 2 クラウドへ | 026 | クラウドへの公開（alwaysdata の Free。本番の設定、接続元、日本時間の「今日」、端末の印、データの移行、バックアップ）と、スマホでの最低限の表示。計画書は `docs/tasks/026_cloud_deployment.md` | 実装中（このPR） | 公開先と端末の印（025-D1）の理由は ADR 0005。役割を分けたAIエージェント（脅威の分析・攻撃のテスト・2つの別の目のレビュー）で確かめる。マージの前に、Komaが下見（架空のデータ）と、iPhone の Safari での確認。マージのあと、Komaが実データを移す（`docs/development/deploy.md`）。候補だった「起動したままのときの自動のバックアップ」は、クラウドでは定期実行の `daily-backup` で毎日作るため、閉じた |
| 3 見た目と使い心地 | 027〜 | デザインの方向を、主な画面の案（2〜3案）で決めてから実装する。アニメーション、スマホの画面、`index.html` の分割 | 未着手 | Apple風の考え方を取り入れる（Appleの素材そのものは使わない）。利用者のメニューの「すべての端末からログアウト」を、間違えて押しにくくするか（確かめの画面など。今の `ui_ux.md` は、確かめを出さない）。2026-11-08・09 の下見で、iPhone で「ログアウト」のつもりで押し、すべての端末の印が消えた（次にログインするまで、締め出しへの守りがなくなる。`architecture/security.md` の「端末の印」） |
| 4 見せる・使ってもらう | — | 画面を載せたREADMEとデモ。他の人に開くかの判断 | 未着手 | 段階2・3が安定してから判断する |
| 候補 | — | 予定の重複の警告 | 未着手 | 段階3のあとの候補 |

- 未決定事項と将来の検討事項は、`docs/open_questions.md`。画面の未決定事項は、実データで使ってから決める
- 使って気づいたことは、GitHubのIssueに書き、重さに応じて、段階の間に小さなタスクとして入れる（`docs/development/workflow.md`）

## 未解決の持ち越し
レビューで見つかり、直さずにマージしたもの（Lowなど）。後続のタスクで直す。

| ID | 内容 | 見つけた時 | 扱う予定 |
|---|---|---|---|
| D-48 | Dependabot の pyee：Playwright 1.64 は、pyee を「15未満」に限る。#48（pyee 14）は、Dependabot が閉じ、#52（pyee 15。CIが失敗する）に置き換わった | 2026-10-27（Dependabot） | 2026-11-02、Koma：#51（Playwright 1.64.0・SQLAlchemy 2.1.5・pluggy 1.7.0・ruff 0.17.1。新たに要る依存がないことを、Python 3.14 で pyee 14 と一緒に入れて確かめた）を rebase のあとマージし、Macで `pip install -r requirements-dev.txt` と `python -m playwright install chromium`。#50（ESLint 10.13.0）もマージ。#52 は閉じた。Task 026 で、`dependabot.yml` に「pyee 15以上を除外」を足した（Playwright が受け付けるようになったら外す）。このPRのマージのあとの月曜日に出る pyee 14 のPRを、CIの合格と差分の確認のあと、マージする |
| 026-L1 | 本番の `pip install` に、`--require-hashes`（配布物のハッシュの固定）がない。版の固定だけでは、乗っ取られたアカウントが、同じ版に新しい配布物を足すと、それが入りうる（別の目のレビュー（守り）の Low。脅威の分析でも挙がった） | 2026-11-02（Task 026） | 後続のタスク。ハッシュを書いた requirements を作る道具（開発のときだけ使う無料の道具）と、Dependabot の更新との合わせ方を、設計で決める |
| 026-L2 | 下見で確かめて決めること。① 決めた（2026-11-10、Koma の承認）：ほかのアカウントは、プロキシを通らずに uWSGI の待ち受けにつなげる（alwaysdata の返事、2026-11-09。アカウントの間のネットワークは分けない）。自分の要求の接続元を偽れるが、ログインIDごとの制限・全体の上限・端末の印は、接続元によらず働くので、今の守りのまま受け入れる（`architecture/security.md` の「接続元」の「残る弱さ」）。残り：ほかのアカウントが、このサイトの待ち受けのアドレスとポートで待ち受けられるか（できるなら、プロキシからの要求（パスワード・Cookie）を受け取れ、アプリでは守れない）と、プロキシに秘密のヘッダーを付けさせられるか（付けられれば、直接の接続を断れる）を、alwaysdata に質問中（2026-11-09）② 決めた（同）：管理画面の「Advanced > Logs」で、ログを残す期間を30日にする（消す定期実行は足さない）。アプリのログ（`uwsgi/`。日ごとに分かれていない1つのファイル）にも効くかは、同じく質問中 | 2026-11-02（Task 026） | 実データの移行（`docs/development/deploy.md` の「3」）の前に、①の待ち受けの答えを確かめる（できる・分からないなら、移行しない）。秘密のヘッダーを付けられるなら、使うかを決める。②が uWSGI のログに効かないなら、扱いを決める。コードや手順書の変更が要れば、このPRか、次のPRで |
| 026-L3 | 本番の Python が 3.14.9（alwaysdata の 3.14 の最新。2026-11-03）で、セキュリティの修正版の 3.14.10 より古い。その間は、pip をハッシュと照らして上げ、本番で本物のパスワードの `set-password`・`create-user` を使わない（`docs/development/deploy.md` の「Python の版」） | 2026-11-03（Task 026。Koma の承認） | alwaysdata が 3.14.10 以上を用意したら、Koma が上げる（手順書の「Python の修正版を上げる」）。上げたら、点検のスクリプトの下限（`MIN_PYTHON`）を 3.14.10 に戻し、手順書の注意を消す |

- Task 021までの持ち越し（010-N1〜021-N1の17件）は、Task 022で閉じた。多くは、Copilotが計画書を書き写して報告する経路に関するもので、開発体制の変更で不要になった。ブラウザ確認で分かったこと（010-N1・018-N2・020-N2・020-N3・021-N1）は、`docs/development/testing.md` の「画面の確認」に、`sqlite3` を `-readonly` で開くこと（011-L1）は、`docs/development/database.md` に残した。記録は `docs/archive/roadmap_until_task021.md`
