# CLAUDE.md

スケジュール帳アプリ（Python 3.11・Flask・SQLite。画面は Jinja2・バニラJavaScript・FullCalendar・Bootstrap）で作業するときの規則。
資料の索引は `docs/README.md`、進め方は `docs/development/workflow.md`。`docs/archive/` は過去の資料で、今の仕様ではない。

## コマンド
| 目的 | コマンド |
|---|---|
| 準備 | `python3.11 -m venv .venv`、`source .venv/bin/activate`、`pip install -r requirements-dev.txt`、`npm ci` |
| テスト | `python -m pytest`（1つのファイル：`python -m pytest tests/test_subjects_api.py`） |
| Pythonの検査 | `ruff check .` |
| JavaScriptの検査 | `npm run lint` |
| 起動 | `python run.py`（`http://127.0.0.1:5001`。`instance/app.db` を使う） |

PRを作る前に、テストと2つの検査が、すべて通ることを確かめる（CIも、同じことを確かめる）。

## データを守る（最も重要）
- KomaのMacの `instance/app.db` は、実データ。Claudeは触れない。リンクしたMacのファイルは、Komaに頼まれたときだけ扱う
- テストは、pytestの一時ディレクトリのDBだけを使う。テストで `create_app()` を引数なしで呼ばない（`SQLALCHEMY_DATABASE_URI` を、一時ディレクトリのDBにして渡す）
- DBの構造の変更は、migrationで行う。`db.create_all()` は使わない。migrationは、一時的なDBと比べて生成する。手順は `docs/development/database.md`
- `upgrade()` に削除（drop）・変更（alter）を含むmigrationや、設計資料にない構造の変更は、PRにする前に、Komaに確かめる
- `migrations/` の削除・作り直しをしない。マージしたmigrationファイルを変えない
- リポジトリは公開されている。個人の予定・時間割や、大学の資料そのものを入れない。テストと確認のデータは、架空のものにする

## 仕様と範囲
- 仕様は、`docs/` の設計資料が正本。承認されていない範囲を実装しない。承認済みの仕様を、理由なく変えない
- 未決定事項（`docs/open_questions.md`）を、自分の判断で決めない
- 設計資料の問題（矛盾・抜け・実現が難しい）や、設計資料にない判断が要る場面に当たったら、止まってKomaに伝える：問題点・理由・変えた場合の影響・推奨案
- 小さな問題（書き間違い、明らかな抜け）は、止まらずに、その場で直して進める
- ライブラリの追加は、設計の段階でKomaに確かめる（開発のときだけ使う無料の道具は、方針として認めている）。費用をかけない

## コーディング
- 読んで理解しやすい書き方を優先する（Komaが、自分で読んで理解・修正できることが目的）。凝った書き方をしない
- 名前は、意味が分かるものにする（過度に省略しない）
- コメント・docstringは、日本語で、適度に書く。すぐには分からない判断には、理由を書く
- 共通化は、2つ目の利用者が出た時点で行う（先回りして共通化しない）
- Python：PEP8に沿う。ruff（E・F・W、1行79文字。全角の文字は2文字に数える）を通す。自動整形（ruff format）は使わない
- JavaScript（`app/static/js/`）：ESLintを通す
  - ES modulesで書く。`import` は拡張子つきの相対パス（例：`"./api.js"`）。`export` は名前つきにし、`export default` は使わない
  - `const`／`let` を使い、`var` は使わない。セミコロンを付ける。インデントは空白2つ。文字列は二重引用符。比較は `===`。非同期は `async`／`await`
  - 使わない：`innerHTML`・`outerHTML`・`insertAdjacentHTML`・`document.write`・`eval`、HTMLの `onclick` などの属性、`style` 属性の操作
  - 利用者の入力やAPIの応答の文字を表示するときは、`textContent` を使う
  - `fetch` は `api.js` の中だけで呼ぶ。Jinjaの値をJavaScriptに書かない
- 検査の例外（`# noqa` など）は、理由をコメントに書いて、その行だけに付ける

## テスト
- APIを作る・変えるタスクでは、そのAPIのpytestのテストを、同じタスクで作る。書き方は `docs/development/testing.md` の「自動テスト（pytest）」
- 期待値は、設計資料から決める。テストを通すために、期待値を設計資料に反して変えない
- テスト専用のコード（テスト用のルートなど）を、`app/` に入れない
- 通らないテストを残したまま、PRにしない
- 画面が変わるタスクでは、Komaが、Macで触って確かめる。確認の手順を書くときは、`docs/development/testing.md` の「画面の確認」の知見を使う

## Git・PR
- ブランチは `feature/NNN-説明`（タスクでない資料の変更は `docs/説明`）。1タスク＝1ブランチ＝1PR。段階ごとにcommitする
- commitの作者は「Claude」。commitのメッセージは、日本語で、何をなぜ変えたかを書く
- PRの説明は、日本語で、変更の要点・読む順番・判断の理由・確認の結果を書く
- しないこと：マージ、`main` への直接のpush、force push、リポジトリの設定の変更（すべてKomaが行う）
- 別の目のレビューの手配と、指摘への対応の残し方は、`docs/development/workflow.md` の「レビュー」
