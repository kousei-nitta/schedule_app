# schedule_app

大学生活のためのスケジュール帳Webアプリ。授業・課題・アルバイト・その他の予定を、1つの画面で管理する。

大学の授業（PDCAサイクルを回しながらアプリを作る課題）で始め、今は、自分で使いながら開発を続けている。今は、1人で、自分のパソコンで使う形（ログインなし）。

## 機能
- **カレンダー**（週・月・一覧）：授業・アルバイト・その他の予定と、課題の締切を表示する。カテゴリで絞り込める。空き枠から予定を追加し、詳細から編集・削除する
- **授業モード**：学期を登録し、授業を曜日と時刻で登録すると、学期の毎週の授業の予定が、自動でできる。休講日を登録すると、その日の授業の予定を作らない
- **課題・タスクモード**：課題と、締切だけのタスクを登録し、完了を管理する。カレンダーにも「直近の締切」を表示する

## 技術
- Python 3.11、Flask、SQLite（Flask-SQLAlchemy・Flask-Migrate）
- 画面：Jinja2、バニラJavaScript（ES modules）、FullCalendar 6、Bootstrap 5
- テストと検査：pytest、Playwright（E2E）、ruff、ESLint、GitHub Actions

## 起動方法
```sh
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app db upgrade   # DB（instance/app.db）を作る
python run.py                # http://127.0.0.1:5001 を開く
```

- 起動のとき、使っているDBを表示し、`instance/app.db` の、その日のバックアップを `instance/backups/` に自動で作る（新しい30個を残す）
- 手動のバックアップ：`flask --app app backup-db --label before-025`（ラベルは英数字・`-`・`_`）。新しいmigrationを適用する前などに取る（`docs/development/database.md`）

デモ用の架空のデータで試すとき（使うDBは、環境変数 `DATABASE_URL` で切り替える）：
```sh
DATABASE_URL=sqlite:///demo.db flask --app app create-demo-db   # instance/demo.db を作る
DATABASE_URL=sqlite:///demo.db python run.py
```

開発のとき（テストと検査）：
```sh
pip install -r requirements-dev.txt
python -m pytest
ruff check .
npm ci && npm run lint       # Node.js があるときだけ（なくても、CIが検査する）
python -m playwright install chromium   # E2Eテストのブラウザ（初回だけ）
python -m pytest -m e2e      # E2Eテスト（画面の主な流れ）
```

## 開発の進め方
AI（Claude）が設計の案を出し、開発者が承認したあと、Claudeが実装してPRを作る。CI・別のレビュー役（実装の経緯を知らないClaudeの別のエージェント）・開発者が確かめてから、開発者がマージする。

- 資料の索引：`docs/README.md`
- 開発の進め方：`docs/development/workflow.md`
- 決定の記録：`docs/decisions/`
- 計画と進み具合：`docs/roadmap.md`
