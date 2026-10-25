# 資料の索引

何がどこにあるか。作業を始めるときは、ここから、作業に関係する資料を読む。実装の規則は、リポジトリ直下の `CLAUDE.md`。

## 資料の一覧
| 資料 | 内容 |
|---|---|
| `requirements.md` | 要求（目的・MVPの範囲・カテゴリ・機能要件・非機能要件） |
| `ui_ux.md` | 画面と操作の仕様（3つのモード、色・アイコン） |
| `architecture/overview.md` | 技術スタック、Bootstrap・FullCalendarの読み込み、DBの切り替え（環境変数）、データの保護（バックアップ）、ディレクトリ構成 |
| `architecture/data_model.md` | データ設計（テーブルと列、共通の約束、関係、制約の命名規則） |
| `architecture/class_events.md` | 授業の予定の自動生成と、休講日・学期の期間・授業の編集・カレンダーからの操作との関係 |
| `architecture/api.md` | API共通ルール（URL・JSON・日付・エラー）、`app/api_helpers.py` |
| `architecture/api_endpoints.md` | 各API（学期・授業・休講日・予定・課題・タスク） |
| `architecture/frontend.md` | JavaScriptの構成、FullCalendarの使い方、モード間の連携、`api.js` |
| `open_questions.md` | 未決定事項と、将来の検討事項 |
| `development/workflow.md` | 体制、タスクの流れ、レビュー、計画書、Git、資料の書き方、roadmapの更新 |
| `development/testing.md` | pytest、検査の道具（ruff・ESLint・migrationのずれ）、CI、E2E（Playwright）、画面の確認 |
| `development/database.md` | migrationの作成と適用、実データのDBの扱い（バックアップ・戻し方）、デモ用の架空のデータ |
| `decisions/` | 重要な決定の記録（ADR）。`0001`：開発体制と今後の計画 |
| `roadmap.md` | 現在地、段階とタスク、未解決の持ち越し |
| `tasks/` | 計画書（Task 022から） |
| `archive/` | 過去の資料（Task 001〜021の計画書、Task 021までのroadmap、済んだ移行の手順）。今の仕様ではない。検索から外している |

## 作業の種類ごとに読むもの
| 作業 | 読むもの |
|---|---|
| どの作業でも | `CLAUDE.md`、`roadmap.md`、そのタスクの計画書、`development/workflow.md` |
| APIを作る・変える | `architecture/api.md`、`architecture/api_endpoints.md` の該当するAPI、`architecture/data_model.md`、`development/testing.md` の「自動テスト（pytest）」 |
| DBの構造を変える | `architecture/data_model.md`、`development/database.md` |
| 授業の予定の作成・同期に関わる | `architecture/class_events.md` |
| 画面を作る・変える | `ui_ux.md` の該当する節、`architecture/frontend.md`、`development/testing.md` の「E2Eテスト」「画面の確認」 |
| ライブラリ・検査の道具・CIを変える | `architecture/overview.md`、`development/testing.md` |
| バックアップ・DBの切り替え・デモデータを変える | `architecture/overview.md` の「DBの切り替え（環境変数）」「データの保護（バックアップ）」、`development/database.md` |
| 仕様を決める | `open_questions.md`、`decisions/`、`requirements.md` |

## 節の名前から資料を探す
資料の中の「…」は、ほかの節の名前（例：「予定API」を参照）。次の表で、どの資料にあるかを探す。節の中の小見出し（太字）は、その節の資料の中で探す。

| 資料 | 節 |
|---|---|
| `architecture/overview.md` | 技術スタック、Bootstrapの読み込み、FullCalendarの読み込み、DBの切り替え（環境変数）、データの保護（バックアップ）、ディレクトリ構成 |
| `architecture/data_model.md` | データ設計、共通の約束、カテゴリの保存値の置き場所、Semester（学期）、Subject（授業）、Event（予定）、Task（課題・タスク）、Closure（休講日）、関係、制約の命名規則 |
| `architecture/class_events.md` | 繰り返し予定の扱い（生成の規則、各Eventの値）、休講日の変更と予定の同期、学期の期間の変更と予定の同期、同じ授業・同じ日付に単発の予定がある場合、編集・削除の仕様、授業全体の編集による作り直し、カレンダーからの授業の予定の操作、授業のEventの生成処理 |
| `architecture/api.md` | API共通ルール、URLとメソッド、リクエストとレスポンス（JSON）、日付・時刻・日時、エラー、404の使い分け、エラーをJSONにする範囲、API共通処理の補助モジュール |
| `architecture/api_endpoints.md` | 学期API、授業API、休講日API、予定API、課題・タスクAPI |
| `architecture/frontend.md` | JavaScriptの構成、FullCalendarの使い方、モード間の連携、`api.js` の仕様 |
| `development/database.md` | DBスキーマ変更の方式、Flask-Migrateの操作の意味、migrationの作成と適用、実データのDBの扱い、バックアップから戻す、開発中の注意、デモ用の架空のデータ |
| `development/testing.md` | 自動テスト（pytest）（対象と方針、配置と実行、アプリの生成、テスト用DB、開発用DBを触らない仕組み、テストの書き方）、検査の道具、CI、E2Eテスト（対象、配置と実行、仕組み、書き方）、画面の確認 |
