# 開発の進め方

## 開発の役割分担とGit運用
- Claude：要求定義・設計・技術判断・実装方針・実装結果のレビュー
- GitHub Copilot Agent mode：実装担当
- Koma：最終判断・コード確認・テスト結果確認・Git管理
- Git：`main` は常に動く状態を保つ。タスクごとに `feature/タスク番号-説明` ブランチを切り、Komaが確認・テストしてから `main` へマージする（1タスク＝1ブランチ＝1マージ）。ブランチの作成・切替、commit、push、マージはすべてKomaが行い、Copilot Agentは行わない。
