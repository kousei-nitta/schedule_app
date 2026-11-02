# 本番（クラウド）の手順

alwaysdata の Free での、本番の準備・下見・デプロイ・実データの移行・バックアップ・利用者の管理。作業は、すべて Koma が行う（Claude は本番に触れない。ADR 0005）。本番の設定の仕様は `architecture/security.md` の「本番の設定」、公開先を決めた理由は `docs/decisions/0005-public-hosting-and-device-cookie.md`。

- 本番のURL（`https://<アカウント名>.alwaysdata.net`）・アカウント名・ログインID・設定のファイルの中身は、リポジトリ・Issue・PRに書かない。Claude とのチャットにも、`SECRET_KEY` とパスワードは貼らない
- 下の `<アカウント名>` は、自分のアカウント名に置き換える。コマンドの `$` は打たない
- alwaysdata の画面の名前は、2026-11 時点のもの。変わっていたら、近いものを探す

## 本番の形
| もの | 場所（本番のサーバー） | 内容 |
|---|---|---|
| コード | `~/schedule_app` | 公開のリポジトリの写し（`git clone`。GitHub に書き込める鍵・トークンは置かない） |
| Python のライブラリ | `~/schedule_app/.venv` | `requirements.txt` のとおり |
| DB とバックアップ | `~/schedule_data/`（700） | `app.db`（600）、`backups/`（毎日の30個と、手動のもの） |
| 設定のファイル | `~/.config/schedule_app/production.env`（600） | `APP_ENV`・`PUBLIC_ORIGIN`・`SECRET_KEY`・`DATABASE_URL`・`CLIENT_ADDRESS_HEADER`（`app/env_file.py`） |
| サイト | alwaysdata の「Web > Sites」 | 種類は Python WSGI（uWSGI）。入口は `wsgi.py`。ワーカーは1つ |
| 毎日のバックアップ | alwaysdata の「Advanced > Scheduled tasks」 | `flask --app app daily-backup` |
| ログ | `~/admin/logs/`（alwaysdata が書く） | `uwsgi/`：アプリのログ（ログインの成功・失敗など）、`http/`：アクセスの記録 |

## 1. アカウントの準備（初めの1回）
1. alwaysdata で、Free のアカウントを作る（カードは不要）。アカウント名は、URL（`<アカウント名>.alwaysdata.net`）になるため、GitHub の ID・本名・大学から推測できない名前にする
2. 管理画面のパスワードは、ほかで使っていない長いものにする。登録したメールアドレス（アカウントの復旧の経路）のパスワードも、別の長いものにする
3. 管理画面の2段階認証（TOTP）を有効にする（「Profile」の2段階認証）
4. SSH：「Remote access > SSH」で、SSH を使えるようにする。Mac で鍵を作り（`ssh-keygen -t ed25519`。パスフレーズを付ける）、公開鍵（`~/.ssh/id_ed25519.pub`）を、サーバーの `~/.ssh/authorized_keys` に入れる。鍵で入れることを確かめたら、SSH のパスワードでのログインを切れるなら切る
5. 「Environment > Python」で、既定の Python を 3.14 にする。SSH で `python --version` が 3.14.10 以上であること（`architecture/security.md` の「開発の環境」の版の理由と同じ）
6. 管理画面には、最初の1年は120日に1回、そのあとは6か月に1回、ログインする（しないと、サイトが止まる。カレンダーに予定を入れておく）

## 2. 下見（実データを入れる前。架空のデータで）
資料では分からない前提を、確かめる。どれかが合わなければ、止まって Claude に相談する（ADR 0005）。

### 2-1. プロキシとサーバーを調べる
1. SSH で入り、コードを置く
   ```sh
   git clone https://github.com/kousei-nitta/schedule_app.git ~/schedule_app
   cd ~/schedule_app
   git checkout feature/026-cloud-deployment   # PR のマージの前の下見のとき
   ```
2. 管理画面の「Web > Sites」で、サイトを作る（すでにあれば、変える）
   - Addresses：`<アカウント名>.alwaysdata.net`
   - Type：Python WSGI
   - Application path：`/home/<アカウント名>/schedule_app/scripts/echo_headers_wsgi.py`（下見の道具。受け取ったヘッダーを返すだけ）
   - Working directory：`/home/<アカウント名>/schedule_app`
   - Python version：3.14
   - Advanced の「uWSGI additional settings」：
     ```
     processes = 1
     threads = 4
     lazy-apps = true
     ```
   - SSL：「Force HTTPS」をオン。HSTS は、alwaysdata の設定ではオンにしない（アプリが付ける）。WAF と HTTP のキャッシュは、オンにしない（キャッシュが `no-store` を守るか、WAF がパスワードを記録するかが、分からないため）
3. Mac で（リポジトリのフォルダで。`.venv` はなくてよい）
   ```sh
   python3 scripts/check_public.py --probe https://<アカウント名>.alwaysdata.net
   ```
   - 「上書きされる」ヘッダーのうち、値が1つのアドレスで、Mac の公開のアドレス（例：`curl https://api.ipify.org`）と同じものを、`CLIENT_ADDRESS_HEADER` にする（ふつうは `X-Real-IP`）。候補が「なし」なら、止まって相談する
   - ✗ があれば（Python が 3.14 でない、ワーカーが1つでない、ホームのファイルシステムがネットワーク上（`nfs` など）、`X-Forwarded-Proto` が付かない）、止まって相談する
4. すぐに、サイトの Application path を `/home/<アカウント名>/schedule_app/wsgi.py` に変える（下見の道具を、公開したままにしない）

### 2-2. アプリを置く
1. SSH で、Python のライブラリを入れる（`--only-binary :all:`：配布物の中のスクリプトを、入れるときに動かさない）
   ```sh
   cd ~/schedule_app
   python -m venv .venv
   . .venv/bin/activate
   python -m pip install pip==26.2.2
   pip install --only-binary :all: -r requirements.txt
   ```
2. DB のフォルダと、設定のファイルを作る。`SECRET_KEY` は、画面に出さずに、ファイルの中で作る（コマンドの履歴に残さない）
   ```sh
   mkdir -m 700 ~/schedule_data
   mkdir -p -m 700 ~/.config/schedule_app
   umask 077
   python - <<'EOF'
   import pathlib, secrets
   home = pathlib.Path.home()
   name = home.name
   path = home / ".config/schedule_app/production.env"
   path.write_text(
       "APP_ENV=production\n"
       f"PUBLIC_ORIGIN=https://{name}.alwaysdata.net\n"
       f"SECRET_KEY={secrets.token_hex(32)}\n"
       f"DATABASE_URL=sqlite:///{home}/schedule_data/app.db\n"
       "CLIENT_ADDRESS_HEADER=X-Real-IP\n"
   )
   path.chmod(0o600)
   EOF
   ```
   - `CLIENT_ADDRESS_HEADER` は、2-1 で決めたものにする（`X-Real-IP` でなければ、ファイルを直す）
   - ホームのフォルダの名前がアカウント名でないときは、`PUBLIC_ORIGIN` を直す
   - このファイルは、本番の秘密の鍵を含む。Git に入れない・Mac に写さない・チャットに貼らない
3. SSH のコマンドが、同じ設定を読むように、`~/.profile` の最後に足す（入り直すと有効）
   ```sh
   export SCHEDULE_ENV_FILE="$HOME/.config/schedule_app/production.env"
   ```
4. 管理画面のサイトの設定
   - Environment に `SCHEDULE_ENV_FILE=/home/<アカウント名>/.config/schedule_app/production.env`（値は、パスだけ）
   - Virtualenv directory：`/home/<アカウント名>/schedule_app/.venv`
   - Application path：`/home/<アカウント名>/schedule_app/wsgi.py`
5. SSH で、設定と、空のDBを作る（下見の DB。架空のデータだけを入れる）
   ```sh
   cd ~/schedule_app && . .venv/bin/activate
   flask --app app show-settings        # 本番・DB・権限（700）を確かめる。SECRET_KEY は長さだけ出る
   flask --app app db upgrade           # 空のDBを作る
   flask --app app create-user <下見用のID>   # 架空の利用者（demo は使えない）
   ```
6. 管理画面で、サイトを再起動する。ブラウザで開き、ログインの画面が出ることを確かめる。開けないときは、`~/admin/logs/uwsgi/` の新しいログを見る（起動しない理由が、日本語で出る）

### 2-3. 点検する
1. Mac で
   ```sh
   python3 scripts/check_public.py https://<アカウント名>.alwaysdata.net
   python3 scripts/check_public.py --login https://<アカウント名>.alwaysdata.net        # 下見用のID・パスワード
   python3 scripts/check_public.py --rate-limit https://<アカウント名>.alwaysdata.net   # Mac の接続元が1時間制限される
   ```
   すべて ✓ であること。✗ があれば、表示を Claude に伝える（URL は伏せる）
2. iPhone の Safari で（モバイルの回線と Wi-Fi の両方）
   - ログインして、架空のデータで、学期・授業・予定・課題を登録し、3つのモードを見る（横にはみ出さない、カレンダーが一覧で始まる、課題の表が読める）。開くまでの時間・操作の速さが、実用になるか
   - ほかのサイトのリンクから開く（メモのアプリにURLを書いて、タップする）：ログインの画面が1回だけ開き直され、ログイン中なら、そのまま使える
   - 利用者のメニューからログアウトし、「戻る」のボタンと、左の端からのスワイプで戻る：ログイン中の画面（スワイプのときの画面の写しを含む）が見えない
   - 端末の印：ログアウトしてもう一度ログインできる。Mac で `--rate-limit` の点検をしたあとも、iPhone（モバイルの回線）からログインできる
3. Mac の Chrome・Safari でも、ログインと主な画面を開く
4. SSH で：`ls -la ~/schedule_data ~/schedule_data/backups ~/.config/schedule_app`（DBとフォルダが、自分だけの権限）、`ls -la ~/admin/logs/*/ | head`（ログが日ごとに分かれ、古いものが消えるかを見て、Claude に伝える）、`ps aux | grep -c uwsgi`（ほかの利用者のプロセスが見えるか）
5. 下見が終わったら、架空のDBを消す：`rm ~/schedule_data/app.db ~/schedule_data/backups/*`（設定のファイルは残す）

## 3. 実データの移行（PR のマージのあと、1回だけ）
1. Mac：サーバー（`run.py`）を止め、`main` に切り替えて新しくする（`git switch main && git pull`）
2. Mac：手動のバックアップと、移行の写しを作る（写しは、リポジトリの外に）
   ```sh
   flask --app app backup-db --label before-transfer
   flask --app app make-transfer-copy ~/Desktop/schedule-transfer.db
   ```
   写しには、ログイン中の端末・ログインの失敗・端末の印と、消した行の残りが入らない。ログインIDが `owner` のままなら止まる
3. 本番：管理画面で、サイトを止める（Disable）
4. Mac から送る：`scp ~/Desktop/schedule-transfer.db <アカウント名>@ssh-<アカウント名>.alwaysdata.net:schedule_data/app.db`
5. 本番（SSH）
   ```sh
   cd ~/schedule_app && . .venv/bin/activate
   chmod 600 ~/schedule_data/app.db
   flask --app app backup-db --label uploaded   # 壊れていないことと件数を確かめる
   flask --app app db upgrade                   # Task 026 の migration（端末の印の表）を当てる
   flask --app app db current                   # 最新の版（head）
   ```
6. 管理画面で、サイトを動かす（Enable）。Mac と iPhone で、今までのID・パスワードでログインし、今までのデータが見えることを確かめる（このログインで、それぞれの端末に印が付く）
7. Mac で `python3 scripts/check_public.py https://...` と `--login`
8. Mac：送った写しを消す（`rm ~/Desktop/schedule-transfer.db`）。Mac の `instance/app.db` は、移行の前の記録として残すが、もう使わない（`run.py` で起動して書き込むと、本番とずれる）

## 4. 更新（PR をマージしたあと）
1. GitHub で、マージのコミット（`main` の最新）を確かめる
2. 本番（SSH）
   ```sh
   cd ~/schedule_app && . .venv/bin/activate
   git switch main          # 下見のブランチのままなら
   git pull --ff-only
   git log -1 --format=%H   # 1 と同じこと
   pip install --only-binary :all: -r requirements.txt
   flask --app app backup-db --label before-<タスクの番号>
   flask --app app db upgrade
   ```
3. 管理画面で、サイトを再起動する。Mac で `python3 scripts/check_public.py https://...`
4. 戻すとき：`git checkout <前のコミット>` で再起動する。DB を戻すなら、下の「バックアップから戻す」

## 5. バックアップ
- 毎日：管理画面の「Advanced > Scheduled tasks」で、毎日1回の定期実行を作る。時刻は、サーバーの3時17分ごろ（パリの時刻。日本の昼で、夏時間でも日本の日付がずれない）
  ```sh
  cd $HOME/schedule_app && SCHEDULE_ENV_FILE=$HOME/.config/schedule_app/production.env .venv/bin/flask --app app daily-backup
  ```
  その日（日本時間）の分を作り、新しい30個を残す（本番のアプリは、作るファイルを、持ち主だけが読める権限にする）。失敗すると、定期実行の記録に、終了コード1と理由が残る。ほかに、alwaysdata が3日分のバックアップを持つ
- 毎週：Mac に取り寄せる（Mac の故障・本番のアカウントの停止に備える。iCloud Drive などの同期するフォルダには置かない）
  ```sh
  mkdir -p -m 700 ~/schedule-backups
  rsync -av --chmod=F600 <アカウント名>@ssh-<アカウント名>.alwaysdata.net:schedule_data/backups/ ~/schedule-backups/
  ```
  バックアップには、パスワードのハッシュ・ログイン中の端末の記録（SHA-256）も入る。Mac は FileVault（ディスクの暗号化）をオンにしておく
- `daily-backup` は、終わりに、バックアップのフォルダの合計の大きさを出す。1GB の上限に近づいていないかを、ときどき見る
- バックアップから戻す：サイトを止め、`flask --app app backup-db --label before-restore` のあと、戻すファイルを `~/schedule_data/app.db` に写し（`-journal` などが残っていないこと）、`flask --app app backup-db --label after-restore` が成功してから、サイトを動かす（考え方は `development/database.md` の「バックアップから戻す」と同じ）

## 6. 利用者の管理（本番）
- SSH で、`cd ~/schedule_app && . .venv/bin/activate` のあと、`flask --app app <コマンド>`（`development/database.md` の「利用者の管理」）。どのコマンドも、最初に「環境：本番」と、使うDBを出す。「ローカル」と出たら、`SCHEDULE_ENV_FILE` を読めていない（止めて、`~/.profile` を確かめる）
- 締め出されたとき（端末の印のない新しい端末で、ログインの失敗が続いたため断られる）：`flask --app app unlock-login <ID>`。続くなら、`rename-user` で、推測されにくいIDに変える
- 端末をなくしたとき：別の端末でログインして「すべての端末からログアウト」（ログイン中の端末と、端末の印が、すべて消える）。ログインできなければ、SSH で `set-password`（同じく、すべて消える）
- 本番では、`create-demo-db`・`flask db downgrade`・`flask db stamp`、ID の `demo` は使えない（断られる）

## 7. ログ
- アプリのログ（`~/admin/logs/uwsgi/`）：ログインの成功・失敗・制限・端末の印の無効化・断った要求（ほかのサイトから）。パスワード・トークン・打ち込まれたIDは出ない。接続元のアドレスは出る
- アクセスの記録（`~/admin/logs/http/`）：alwaysdata が書く（接続元・パス・ブラウザの名前）
- 残す期間：下見で、alwaysdata が古いログを消すかを確かめ、消さないなら、30日より古いログを消す定期実行を足す（Claude と決める）
- ときどき、「端末の印を、続けての失敗で無効にしました」「全体の上限」がないかを見る（印が盗まれた・多くの接続元から試されている兆し）
