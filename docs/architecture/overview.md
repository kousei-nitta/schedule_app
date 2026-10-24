# 技術の概要（技術スタック・ディレクトリ構成）

> 仕様の正本。変更は、Komaの承認を得てから、PRで行う（`docs/development/workflow.md`）。

## 技術スタック
| 項目 | 採用 | 備考 |
|---|---|---|
| 言語 | Python 3.11 | プロジェクト専用の仮想環境 `.venv` を使用 |
| バックエンド | Flask | |
| DB | SQLite | 単一ユーザー・ローカル1ファイル。同時アクセスの考慮は不要 |
| ORM | Flask-SQLAlchemy | |
| DBスキーマ変更 | Flask-Migrate（内部でAlembicを使用） | モデルの変更をmigrationファイルとして記録し、既存データを保ったままテーブルを更新する。方式の詳細は「DBスキーマ変更の方式」を参照 |
| テンプレート | Jinja2（Flask標準） | |
| フロントエンドJS | バニラJavaScript（ES modules） | `fetch` でFlaskのAPIを呼ぶ。構成と規則は「JavaScriptの構成」、APIの規則は「API共通ルール」を参照 |
| カレンダー描画 | FullCalendar 6.1.21 | MIT・無料の標準のバンドル（週／月／一覧表示）だけを使う。リソース／タイムライン表示などの有料機能は使わない。CDN（jsDelivr）から、バージョンを固定して読み込む（「FullCalendarの読み込み」を参照） |
| CSS（UI部品） | Bootstrap 5.3.8 | CDN（jsDelivr）から、バージョンを固定して読み込む（「Bootstrapの読み込み」を参照）。タブ（モード切り替え）、モーダル（詳細パネル）、バッジ（カテゴリ表示）などに利用 |
| 認証 | なし | ログイン機能は実装しない |
| 自動テスト | pytest | APIのテストに使う。配置・DB・実行方法は「自動テスト（pytest）」を参照 |
| 起動 | `run.py` | 開発用サーバーを `127.0.0.1:5001`（`debug=True`）で起動する。5001番を使うのは、macOSではAirPlayレシーバーが5000番を使うことがあるため |

制約：費用をかけない（大学の授業の一環のため）。

### Bootstrapの読み込み（確定）
- **CDN（jsDelivr）から読み込み、バージョンを固定する。** 固定するバージョンは **5.3.8**（2026年10月時点の最新の安定版）。`latest` など、バージョンを固定しないURLは使わない。
- 読み込むのは2つ。CSS（`bootstrap.min.css`）を `<head>` 内に、JavaScript（`bootstrap.bundle.min.js`。Popperを含む）を `</body>` の直前に置く。
- 改ざんの検出用に `integrity`（ハッシュ値）と `crossorigin="anonymous"` を付ける。
- バージョンを変えるときは、この資料、Task MD、タグの `integrity` を、そろえて更新する（開発者の承認を得る）。`integrity` の値は、公式サイトの掲載値を使う。

```html
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB" crossorigin="anonymous">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js" integrity="sha384-FKyoEForCGlyvwx9Hj09JcYn3nv7wiPVlz7YYwJrWVcXK/BmnVDxM+D2scQbITxI" crossorigin="anonymous"></script>
```

### FullCalendarの読み込み（確定）
- **CDN（jsDelivr）から読み込み、バージョンを固定する。** 固定するバージョンは **6.1.21**（v6系の最終版。2026年6月）。`latest` など、バージョンを固定しないURLは使わない。
- v7（2026年6月に公開）は使わない。CSSが本体に含まれず、テーマのファイルを別に読み込む必要があること、npmの公開パッケージに圧縮した版がないこと、ボタンの文言（`buttonText`）など多くの設定の名前が変わったことから、v6のほうが、このアプリの用途（読み込むファイルが少なく、設定の書き方が広く知られている）に合うため。v7へ移るときは、別のタスクとして設計する。
- 読み込むのは、標準のバンドル `index.global.min.js` の1つだけ（週・月・一覧などの表示と、操作の部品を含む。有料の機能は含まない）。CSSも、このファイルに含まれる（FullCalendarが、ページに自動で入れる）。`base.html` の `</body>` の直前、Bootstrapの `<script>` のあと、`{% block scripts %}` の前に置く（通常のスクリプトのため、`type="module"` の `main.js` より先に実行され、`window.FullCalendar` として使える）。
- 日本語の文言のファイル（`locales/ja`）は読み込まない。日付の表示は `locale: "ja"` で日本語になり、ボタンなどの文言は、`calendar.js` の設定で指定する（「＋N件」など、このアプリの文言に合わせるため。読み込むファイルを1つにするため）。
- 改ざんの検出用に `integrity`（ハッシュ値）と `crossorigin="anonymous"` を付ける。FullCalendarの公式サイトには `integrity` の値が掲載されていないため、npmの公開パッケージ（`fullcalendar@6.1.21`）の `index.global.min.js` から計算したSHA-384を使う。その値が、jsDelivrの掲載値（`data.jsdelivr.com` のファイル一覧のハッシュ）と一致することを確かめた（2026-10-13）。
- バージョンを変えるときは、この資料、Task MD、タグの `integrity` を、そろえて更新する（開発者の承認を得る）。`integrity` の値は、上と同じ方法で求め、jsDelivrの掲載値と照らす。
- Bootstrapは、`<a>` の文字を、青い下線つきにする。FullCalendarは、日付の見出しなどに `<a>` を使うため、`style.css` で、FullCalendarの中の `<a>` を、FullCalendarの本来の見た目（通常の文字）に戻す。

```html
<script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.21/index.global.min.js" integrity="sha384-WDvnzcla8X1CQM97EnYyl4OoTCvmMFp5lBiVNO3IjVdvLMOUjwt+iuYb/Mru5A9v" crossorigin="anonymous"></script>
```

- 独自のスタイル（`app/static/css/style.css`）は、`base.html` の `<head>` で、BootstrapのCSSのあとに読み込む（Bootstrapの指定を、上書きできるようにするため）。

## ディレクトリ構成
以下は目標の構成。`.git/`・`.venv/`・`.vscode/` は作成済みで、変更しない。

```
schedule_app/
├── app/
│   ├── __init__.py          # Flaskアプリの作成（`create_app(test_config=None)`）
│   ├── config.py            # SQLiteのパスなどの設定
│   ├── extensions.py        # db = SQLAlchemy(命名規則つきのMetaData)、migrate = Migrate() など
│   ├── api_helpers.py       # API共通処理（エラー応答、エラーハンドラー、JSON本文の受け取り（PATCHの空の本文の検査 read_patch_object を含む）、一覧のクエリのIDの読み取り read_id_query、項目の検査（使用できない文字の検査、真偽値、決まった値から選ぶ文字列を含む）、日付・時刻・日時の変換と検証、IDの上限 MAX_ID、メッセージの定数 UNUSABLE_CHARACTER_MESSAGE・EMPTY_PATCH_MESSAGE）。DBの操作は行わない
│   ├── categories.py        # カテゴリの保存値の定数と、APIで受け付ける値の一覧（EVENT_CATEGORIES・TASK_CATEGORIES）。定数だけを持つ
│   ├── class_events.py      # 授業のEventの生成（日付の計算 class_event_dates、1日分のEventの作成 build_class_event、学期全体のEventの作成 build_class_events、作り直しのEventの作成 build_class_events_from。カテゴリは categories.py の EVENT_CATEGORY_CLASS を使う）。セッションの操作・commitは行わない
│   ├── models/
│   │   ├── __init__.py      # 各モデルの読み込み
│   │   ├── semester.py      # 学期
│   │   ├── subject.py       # 授業
│   │   ├── event.py         # 時間型の予定
│   │   ├── task.py          # 課題・タスク（期限型）
│   │   └── closure.py       # 学期の休講日
│   ├── routes/
│   │   ├── __init__.py      # routesをパッケージにする（空のファイル）
│   │   ├── main.py          # トップページ（カレンダー・授業・課題の3モードを含む1画面）
│   │   ├── semesters.py     # 学期のAPI（一覧・取得・登録・編集・削除と、期間の変更の、予定・休講日への反映）
│   │   ├── subjects.py      # 授業モードのAPI（登録・編集・削除・一覧）
│   │   ├── closures.py      # 休講日のAPI（一覧・登録・削除と、予定の同期）
│   │   ├── events.py        # 予定（Event）のAPI（期間を指定した一覧・1件取得・派遣会社の候補と、単発の予定の登録・編集・削除）
│   │   └── tasks.py         # 課題・タスクのAPI（一覧（完了の状態の絞り込み）・1件取得・登録・編集（完了の切り替えを含む）・削除）
│   ├── templates/
│   │   ├── base.html        # 共通の骨組み。Bootstrap・FullCalendar・style.css の読み込みと、JavaScript用の scripts ブロック
│   │   └── index.html
│   └── static/
│       ├── css/style.css    # カテゴリの色・独自スタイル
│       └── js/
│           ├── main.js      # 入口（各モードの初期化）
│           ├── api.js       # fetchの共通処理
│           ├── ui.js        # 表示の切り替え・フォームのエラー表示・モーダルを閉じる処理などの共通処理
│           ├── dates.js     # 日付の補助処理（今日の日付・今の日時の文字列、日付・日時の表示形式）
│           ├── categories.js # カテゴリの対応表（保存値 → 表示名・アイコン・色のclass。予定と課題・タスク）
│           ├── current_semester.js # 今の学期を選ぶ規則（授業モードの初期選択と、今の学期の授業から選ぶ欄）
│           ├── subject_options.js # 今の学期の授業から選ぶ欄の共通処理（授業の取得、説明の文、選択肢。課題の対象授業と、単発の授業）
│           ├── task_display.js # 課題・タスクの表示の共通処理（表す文字列、期限切れの判定と印、アイコンと課題名）
│           ├── semesters.js # 授業モードの学期タブ・登録フォーム・編集フォーム・削除の確認
│           ├── calendar.js  # カレンダーモード（FullCalendarの設定、予定の取得・絞り込み、締切の表示、直近の締切欄、空き枠のクリック、予定と締切の詳細パネル）
│           ├── event_forms.js # カレンダーモードの中の部品（予定の追加（その他（締切のみ）を含む）・編集・削除の確認のモーダル。calendar.js だけが import する）
│           ├── subjects.js  # 授業モードの一覧・登録・編集・削除の確認
│           ├── closures.js  # 授業モードの休講日の一覧・追加・削除
│           └── tasks.js     # 課題・タスクモードの一覧・完了の切り替え・追加・編集・削除の確認
├── migrations/              # Flask-Migrateのmigration環境（`flask db init` で生成）。Git管理対象
│   └── versions/            # migrationファイル（自動生成後にレビューする）。Git管理対象
├── instance/                # Git管理対象外（.gitignore）
│   ├── app.db               # SQLiteファイル（開発用DB）
│   └── backups/             # 開発用DBのバックアップ（migrationの適用の前など。「migrationの作成と適用」）
├── docs/                    # 資料（何がどこにあるかは docs/README.md）
├── .github/workflows/ci.yml # CI（GitHub Actions。docs/development/testing.md の「CI」）
├── node_modules/            # npmのパッケージ（Git管理対象外。npm ci で作る）
├── tests/                   # pytestのテスト（「自動テスト（pytest）」を参照）
│   ├── conftest.py          # 共通のfixture（テスト用DB・アプリ・クライアント・開発用DBの保護）
│   ├── test_setup.py        # テスト基盤そのものの確認（migrationで作られるテーブル・列・制約の確認と、モデルとmigrationのずれの確認を含む）
│   ├── test_api_helpers.py  # api_helpers.py の共通関数の単体テスト
│   ├── test_class_events.py # class_events.py の単体テスト（日付の計算、Eventの値）
│   ├── test_<リソース名>_api.py  # APIのテスト（リソースごと）
│   ├── test_subjects_update_delete_api.py  # 授業の編集・削除と、1件取得の件数のAPIのテスト（授業のテストが大きくなるため、分けた）
│   ├── test_events_create_update_delete_api.py  # 予定の登録・編集・削除のAPIのテスト（予定の一覧・1件取得・派遣会社の候補は test_events_api.py）
│   └── test_semesters_update_delete_api.py  # 学期の編集・削除（期間の変更の、予定・休講日への反映を含む）と、1件取得の件数のAPIのテスト（学期の登録・一覧と、405の Allow などのAPI共通の確認は test_semesters_api.py）
├── pytest.ini               # pytestの設定
├── ruff.toml                # ruff（Pythonの検査）の設定
├── eslint.config.js         # ESLint（JavaScriptの検査）の設定
├── package.json             # ESLintとその版（package-lock.json も同じ）。開発のときだけ使う
├── package-lock.json
├── requirements.txt
├── requirements-dev.txt     # 開発のときだけ使うもの（pytest・ruff）。requirements.txt も読み込む
├── .ignore                  # 検索から外すフォルダ（docs/archive/）
├── CLAUDE.md                # 実装の規則（Claudeが作業の始めに読む）
├── README.md                # リポジトリの表紙（概要・機能・技術・起動方法・開発体制）
└── run.py                   # 起動スクリプト（127.0.0.1:5001）
```

注意：
- 授業のモデル名は、Pythonの予約語 `class` と紛らわしいため `Subject` とする。`class` という語は、Eventのカテゴリの保存値（文字列 `"class"`）と、その定数名 `EVENT_CATEGORY_CLASS`、モジュール名 `class_events.py` とその関数名（`class_event_dates`・`build_class_event`・`build_class_events`）にだけ使う。これは「授業のEvent」を表す名前で、Pythonのクラス名・変数名として授業そのものを `class` と呼ぶわけではない（授業は、クラス名 `Subject`、変数名 `subject`）。
- 画面はカレンダー／授業／課題・タスクの3モードを1ページ（`index.html`）に持たせ、Bootstrapのタブ機能と、必要なJavaScriptで表示を切り替える。
- ログインがないため、認証関連のファイルは作らない。
