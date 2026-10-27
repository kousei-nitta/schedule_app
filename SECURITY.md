# セキュリティの問題の報告（Security Policy）

## 対象
- このリポジトリの `main` ブランチ（最新の版だけを直します）
- このアプリは、今は、開発者が自分のパソコン（`127.0.0.1`）でだけ使う形です。公開しているサーバーはありません
- 守りの考え方と対策は、`docs/architecture/security.md` にあります

## 報告のしかた
脆弱性（セキュリティの問題）を見つけたときは、**公開のIssueやPRに書かず**、GitHubの非公開の報告を使ってください。

1. このリポジトリの「Security」タブを開く
2. 「Report a vulnerability」から、内容を書いて送る

書いてほしいこと：問題の内容、再現の手順、考えられる影響。

## 返事について
- 個人（学生）が、自分で使うために作っているアプリです。返事と修正は、できる範囲で行います（期限の約束はできません）
- 報奨金（バグバウンティ）はありません
- 届いた内容は、確かめてから、修正と一緒に、公開してよい範囲で記録します

---

## English
- **Scope:** the `main` branch only. The app currently runs only on the developer's own machine (`127.0.0.1`); there is no public server.
- **How to report:** please do **not** open a public issue or pull request. Use GitHub's private vulnerability reporting instead: open the **Security** tab of this repository and choose **Report a vulnerability**. Include the problem, steps to reproduce, and the possible impact.
- **Response:** this is a personal student project. Reports are handled on a best-effort basis, with no guaranteed timeline and no bug bounty.
