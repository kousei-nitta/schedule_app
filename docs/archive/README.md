# 過去の資料（アーカイブ）

開発の経緯として残している資料。**今の仕様・進め方ではない。** 今の資料は `docs/README.md` から探す。

- 内容は、移したときのまま変えていない（中のパスや手順は、当時のもの）
- 検索の結果に古いコードの写しが混ざらないよう、リポジトリ直下の `.ignore` で、このフォルダを検索から外している（ripgrepなど、`.ignore` に従う道具の場合）

| 資料 | 内容 |
|---|---|
| `tasks/` | Task 001〜021の計画書（Task MD）。Task 014以降は、GitHub Copilot Agentに渡すための、コードの全文の付録を含む |
| `roadmap_until_task021.md` | Task 021と、仕様検討フェーズ（PR #39）までのroadmap。完了したタスクの一覧、持ち越し（010-N1〜021-N1）、進め方の決定の記録（2026-10-24まで） |
| `migration_before_class_event_generation.md` | 済んだ移行の手順：予定の自動生成より前に登録した授業の扱い（Task 011で実施。元は `docs/architecture.md`） |
| `task022/check_architecture_split.py` | Task 022で、`docs/architecture.md` を分割したときに、文が失われていないことを確かめたスクリプト |

体制を変えた理由は、`docs/decisions/0001-development-system-and-plan.md`。
