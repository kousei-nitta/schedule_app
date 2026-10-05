# タスク002: 画面の土台（起動・トップページ・Bootstrap・3モード切り替え）

ブランチ：`feature/002-ui-foundation`（Komaが作成・切替済みの状態で渡される）

**作業を始める前に、必ず `git branch --show-current` で現在のブランチを確認する。このタスクに書かれたブランチ名と異なる場合は、ファイルを一切変更せず、実装を停止して、現在のブランチ名をチャットで報告する。** あわせて `git status` で作業ツリーを確認し、想定外の変更がある場合も、変更せずに報告する。

## ゴール
アプリを起動し、ブラウザで `http://127.0.0.1:5001` を開くと、画面の下部に3つのボタン（カレンダー／授業／課題・タスク）が表示され、ボタンで3つの空の表示領域を切り替えられる状態にする。

このタスクの完成形は「画面の土台」まで。各モードの中身（カレンダー、授業の登録、課題の一覧など）は、後続のタスクで作る。

## このタスクで出てくる言葉
- **Blueprint**：Flaskで、URLと処理（route）をまとめて管理するための仕組み。このタスクでは、トップページ用のBlueprintを1つ作る。
- **テンプレートの継承**：`base.html` に全ページ共通の骨組みを書き、`index.html` が `{% extends "base.html" %}` でそれを引き継いで、中身だけを書く方式（Jinja2の機能）。
- **CDN**：Bootstrapのファイルを、インターネット上の配布場所から読み込む方式。このプロジェクトではバージョンを固定して使う。

## やること

### 1. 起動スクリプト `run.py`（プロジェクトのルート）
- `create_app()` でアプリを作成し、開発サーバーを起動する（`python run.py` で起動できること）
- ホストは `127.0.0.1`（自分のPCからのみ接続できる）、ポートは **5001**、`debug=True`（開発用）
- 5001番を使う理由：macOSでは、AirPlayレシーバーが5000番を使うことがあるため。

### 2. トップページ用のroute
- `app/routes/__init__.py`（空のファイル。`routes` をパッケージにするために必要）
- `app/routes/main.py`：Blueprint（名前は `main`）を作り、`/` にアクセスしたら `index.html` を表示する
- `app/__init__.py`（既存）：`create_app()` の中でBlueprintを登録する。**既存の処理（`db.init_app`、`migrate.init_app`、モデルの読み込みなど）は変更しない**

### 3. テンプレート（`app/templates/`）
**`base.html`**
- HTML5の骨組み。`<html lang="ja">`、文字コード、viewport、`<title>`（スケジュール帳）
- Bootstrapを、下に示すタグのとおりに読み込む（CSSは `<head>` 内、JSは `</body>` の直前）
- 各ページの中身を入れる `{% block content %}`

**`index.html`**
- `base.html` を継承する
- 画面下部に固定した、3つの切り替えボタン：「カレンダー」「授業」「課題・タスク」（この順）
- 3つの表示領域（カレンダー用・授業用・課題・タスク用）。最初に表示されるのは「カレンダー」
- 各領域には、どのモードか分かる短い仮の文言（例：「カレンダー（準備中）」）だけを入れる
- 切り替えは、**Bootstrapのタブ機能（`data-bs-toggle="pill"` など）だけ**で実現する。独自のJavaScriptは書かない
- 下部に固定したボタンが、表示領域の内容に重ならないようにする（Bootstrapのクラスで余白を取る）

**Bootstrapの読み込み（このタグをそのまま使う。バージョンは5.3.8で固定）**

```html
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB" crossorigin="anonymous">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js" integrity="sha384-FKyoEForCGlyvwx9Hj09JcYn3nv7wiPVlz7YYwJrWVcXK/BmnVDxM+D2scQbITxI" crossorigin="anonymous"></script>
```

これらは `docs/architecture.md` の「Bootstrapの読み込み」に書かれた、5.3.8用のタグと同じもの。URLやバージョン、`integrity` の値を、自分の判断で変更・省略しない。

## やらないこと（このタスクの範囲外）
- FullCalendarの導入、およびBootstrap以外の外部ライブラリ・CDNの読み込み（Bootstrap Icons、jQueryなど）
- API（JSONを返すエンドポイント）
- DB操作（読み書き）、`app/models/` の変更
- **migrationに関する操作の一切**（`flask db init`・`migrate`・`upgrade`・`downgrade`・`current` など。今回は該当しないため行わない）。`migrations/` と `instance/app.db` は変更しない
- 各モードの中身（カレンダー描画、フォーム、一覧、詳細パネルなど）
- 独自のJavaScript（`.js` ファイル、`<script>` 内の自作コード）
- 独自のCSS（`style.css`、`<style>`）、色・アイコン。Bootstrapのクラスだけを使う
- `app/static/` の作成
- ライブラリの追加（`pip install`）と `requirements.txt` の変更
- テスト（`tests/`）
- `.gitignore`・`.vscode`・Git設定の変更
- Git commit / push / ブランチ操作 / マージ（`git branch --show-current`、`git status` のような読み取りだけのコマンドは除く）
- 設計資料（`docs/requirements.md`・`architecture.md`・`ui_ux.md`）と `.github/copilot-instructions.md` の変更

## 参照
- `docs/ui_ux.md`：「画面構成」（3モードと、アプリ下部の切り替えボタン群）
- `docs/architecture.md`：技術スタック（Bootstrap、起動）、Bootstrapの読み込み、ディレクトリ構成
- `.github/copilot-instructions.md`：進め方と、設計上の問題を見つけたときの手順

## 完了の確認方法（Copilotが行う）
1. `.venv` が有効な状態で、`python run.py` でエラーなく起動できる（5001番がすでに使われている場合は、変更せずに報告する）
2. 起動中に `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5001/` を実行し、`200` が返る
3. `curl -s http://127.0.0.1:5001/` の出力に、次がすべて含まれている
   - 「カレンダー」「授業」「課題・タスク」の3つのラベル
   - `lang="ja"`
   - 上に示したBootstrapのCSSとJSのタグ（バージョン5.3.8）
   - 3つの表示領域
4. サーバーを停止する。5001番を使うプロセスが残っていないことを確認する（`lsof -i :5001` の出力が空）
5. `git status` で、次のとおりになっている
   - 新規：`run.py`、`app/routes/`、`app/templates/`
   - 変更：`app/__init__.py` のみ
   - `migrations/`、`app/models/`、`requirements.txt`、`instance/` に変更がない
6. 変更したファイルが、このタスクの「やること」の範囲内だけである

## 確認ポイント（Komaがブラウザで行う）
Copilotの報告を受けたあと、Komaが `python run.py` で起動し、Chromeで `http://127.0.0.1:5001` を開いて確認する。

- 画面の下部に、「カレンダー」「授業」「課題・タスク」の3つのボタンが表示される
- 最初は「カレンダー」が選択されていて、カレンダー用の仮の文言が表示される
- 各ボタンを押すと、対応する領域に切り替わり、ほかの2つは表示されない
- 下部のボタンが、領域の文言に重なっていない
- 開発者ツール（F12）のコンソールに、エラー（特に `integrity` に関するもの）が出ていない

## 注意
- Bootstrapのタグが読み込めない（404やintegrityエラーなど）場合は、自分で直さずに、エラー内容を報告する
- **設計上の問題や未決定事項に遭遇した場合**：`.github/copilot-instructions.md` の「設計上の問題を見つけたとき」の手順に従う。ファイルを変更せず、実装を停止し、チャットで「問題点・発生理由・変更した場合の影響・推奨案（必要なら）」を報告する
- このタスクで決まっていないことは、自分で決めない。特に `docs/architecture.md` の「未決定事項」に書かれた項目は、このタスクでは扱わない
- 途中の承認ゲートはない。完了の確認方法を実施したら、結果を報告して止まる（ブラウザでの確認はKomaが行う）
