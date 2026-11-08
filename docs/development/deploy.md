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
5. 「Environment > Python」で、既定の Python を 3.14 にする。SSH で `python --version` が 3.14.9 以上であること（3.14.10 以上が望ましい。alwaysdata が 3.14.10 以上を用意するまでは、3.14.9 で進める。下の「Python の版」）
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
3. Mac で（リポジトリのフォルダで。`.venv` はなくてよい。`python3.14` で動かす：Mac に最初から入っている `python3` は古く、動かない）
   ```sh
   curl https://api64.ipify.org      # この Mac の公開のアドレス（次で尋ねられる。IPv4 と IPv6 のどちらか）
   python3.14 scripts/check_public.py --probe https://<アカウント名>.alwaysdata.net
   ```
   - スクリプトは、偽の接続元を、ふつうの名前（`X-Real-IP`）と下線の名前（`X_Real_IP`）で、別々に送る。ふつうの名前の偽の値が上書きされ（値が1つで、この Mac のアドレス）、下線の名前の偽の値が、捨てられるか、本物の値と混ざる（`192.0.2.20, <Mac のアドレス>` のような形。アプリが400で断るので安全）ヘッダーを、「候補」として出す。`REMOTE_ADDR` が、この Mac のアドレスなら、それも候補になる（いちばんよい）。候補の最初のものを `CLIENT_ADDRESS_HEADER` にする。候補が「なし」なら、止まって相談する
   - ✗ があれば（Python が 3.14.9 より古い、ワーカーが1つでない、ホームのファイルシステムがネットワーク上（`nfs` など）、`X-Forwarded-Proto` を偽れる）、止まって相談する
   - 「REMOTE_ADDR」の行も、Claude に伝える（Mac のアドレスと同じなら `<MAC>` に。内部のアドレス（`fd00::…` など）なら、そのまま）
   - 「この Mac のアドレスと違う」と出たら、IPv4 と IPv6 の違いかもしれない。表示された値と同じ種類のアドレス（IPv4：`curl -4 https://api.ipify.org`、IPv6：`curl -6 https://api64.ipify.org`）で、入れ直す
   - 最後の行の「uWSGI の待ち受け」を、Claude に伝える（共有のサーバーの、ほかの利用者が、プロキシを通らずにアプリへ直接つなげるかを判断する）。伝えるときは、アカウント名を `<アカウント名>` に、Mac のアドレスを伏せる
4. すぐに、サイトの Application path を `/home/<アカウント名>/schedule_app/wsgi.py` に変える（下見の道具を、公開したままにしない）

### 2-2. アプリを置く
1. SSH で、Python のライブラリを入れる（`--only-binary :all:`：配布物の中のスクリプトを、入れるときに動かさない）
   ```sh
   cd ~/schedule_app
   python -m venv .venv
   . .venv/bin/activate
   python -m pip install --only-binary :all: --require-hashes -r <(echo "pip==26.2.2 --hash=sha256:fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70")
   pip --version                  # pip 26.2.2
   pip install --only-binary :all: -r requirements.txt
   ```
   pip を上げる行は、PyPI が公開している pip 26.2.2 のファイルのハッシュ（SHA-256）と照らして入れる。3.14.9 に付いてくる古い pip は、eMudhra の件（侵害された中間CAの鍵）に対応していないため、通信を乗っ取られて偽の pip を入れられないように（下の「Python の版」）。「THESE PACKAGES DO NOT MATCH THE HASHES」と出たら、止まって相談する
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
3. SSH のコマンドが、同じ設定を読むように、`~/.profile` の最後に足す
   ```sh
   export SCHEDULE_ENV_FILE="$HOME/.config/schedule_app/production.env"
   ```
   SSH で入り直し、`echo $SCHEDULE_ENV_FILE` で、パスが出ることを確かめる。出なければ、`~/.bash_profile` があるかを見る（あると、bash は `~/.profile` を読まない）。あれば、同じ行を、そちらに足す
4. 管理画面のサイトの設定
   - Environment に `SCHEDULE_ENV_FILE=/home/<アカウント名>/.config/schedule_app/production.env`（値は、パスだけ）
   - Virtualenv directory：`/home/<アカウント名>/schedule_app/.venv`
   - Application path：`/home/<アカウント名>/schedule_app/wsgi.py`
5. SSH で、設定と、空のDBを作る（下見の DB。架空のデータだけを入れる）
   ```sh
   cd ~/schedule_app && . .venv/bin/activate
   flask --app app show-settings        # 1行目が「環境：本番」であること。DB・権限（700）も。SECRET_KEY は長さだけ出る
   flask --app app db upgrade           # 空のDBを作る
   flask --app app create-user <下見用のID>   # 架空の利用者（demo は使えない）
   ```
   - 本番のアプリのコマンドは、どれも、最初に「環境：本番」と、使うDBを出す（`flask db` は出さない）。「環境：ローカル」と出たら、設定を読めていない。その先へ進まない（`flask db upgrade` などが、リポジトリの中に別のDBを作ってしまう）。手順3を確かめる
6. 管理画面で、サイトを再起動する。ブラウザで開き、ログインの画面が出ることを確かめる。開けないときは、`~/admin/logs/uwsgi/` の新しいログを見る（起動しない理由が、日本語で出る）

### 2-3. 点検する
1. Mac で
   ```sh
   python3.14 scripts/check_public.py https://<アカウント名>.alwaysdata.net
   python3.14 scripts/check_public.py --login https://<アカウント名>.alwaysdata.net   # 下見用のID・パスワード
   ```
   すべて ✓ であること。✗ があれば、表示を Claude に伝える（URL は伏せる）。`--login` は、動かすたびに、本番に端末の印を1つ増やす（利用者ごとに10個まで。古いものから消える）。何度も動かしたあとは、iPhone・Mac でログインし直す（印を付け直す）
2. iPhone の Safari で（まず、Mac と同じ Wi-Fi で。iCloud プライベートリレーを使っていれば、その Wi-Fi の「IPアドレスを非公開」を、点検の間だけ切る。切らないと、iPhone の接続元が Mac と違い、手順3の確かめにならない）
   - ログインして（この iPhone に、端末の印が付く）、架空のデータで、学期・授業・予定・課題を登録し、3つのモードを見る（横にはみ出さない、カレンダーが一覧で始まる、課題の表が読める）。開くまでの時間・操作の速さが、実用になるか
   - ほかのサイトのリンクから開く（メモのアプリにURLを書いて、タップする）：ログインの画面が1回だけ開き直され、ログイン中なら、そのまま使える
   - 利用者のメニューからログアウトし、「戻る」のボタンと、左の端からのスワイプで戻る：ログイン中の画面（スワイプのときの画面の写しを含む）が見えない
3. 端末の印を確かめる（2 のあと。この順番で）
   1. Mac で、接続元の偽装を点検する（Mac と、同じ Wi-Fi の iPhone の接続元が、1時間ログインできなくなる）。ふつうの名前で偽った11回（11回目が 429）と、下線の名前で偽った3回（どれも 400 か 429）を、別々に送る
      ```sh
      python3.14 scripts/check_public.py --rate-limit https://<アカウント名>.alwaysdata.net
      ```
   2. 同じ Wi-Fi の iPhone（印のある Safari）で、ログインできる（印のある道は、接続元ごとの制限を受けない）
   3. 同じ Wi-Fi の iPhone の、プライベートのタブ（印がない）では、「ログインの失敗が続いたため、しばらくログインできません。…」になる
   4. モバイルの回線の iPhone でも、主な画面が実用の速さか見る
4. Mac の Chrome・Safari でも、ログインと主な画面を開く（Mac の接続元の制限が解けた1時間あと。または、テザリングなどで別の接続元から）
5. SSH で：`ls -la ~/schedule_data ~/.config/schedule_app`（DBとフォルダが、自分だけの権限。`backups` は、まだなくてよい）、`ls -la ~/admin/logs/*/ | head`（ログが日ごとに分かれ、古いものが消えるかを見て、Claude に伝える）、`ps aux | grep -c uwsgi`（ほかの利用者のプロセスが見えるか）
6. 下見の DB は、まだ消さない（消すのは、移行の手順で、サイトを止めたあと）

### Python の版
- 本番の Python は、alwaysdata が用意する 3.14 の修正版から選ぶ（サイト（uWSGI）は、alwaysdata の Python で動く）。2026-11-03 の時点では 3.14.9 で、セキュリティの修正版の 3.14.10（2026-10-25）は、まだない。3.14.10 以上が用意されるまで、3.14.9 で進める（Koma の承認、2026-11-03。ADR 0005 の「影響」。roadmap の 026-L3）
- 3.14.10 の3つのセキュリティの修正のうち、本番に関係するのは、eMudhra の件（`ssl` が、侵害された中間CAの鍵を拒む）だけ（`tarfile`・`http.cookiejar` は使わない。利用者からの HTTPS は、alwaysdata のプロキシが受ける）。本番の Python から外へつなぐのは、次の2つ
  - pip を上げる1回目：上の、ハッシュと照らす手順で守る（pip 26.2.2 は、この件に対応済み。そのあとのライブラリの取得も守られる）
  - `set-password`・`create-user` の、漏えいしたパスワードの確認：3.14.10 以上に上げるまで、本番で、本物のパスワードの `set-password`・`create-user` を使わない（通信を乗っ取られると、パスワードのハッシュの先頭5文字が漏れうる）。本物のパスワードは、Mac で決めたものを、移行の写しで運ぶ。下見の架空のパスワードは、使ってよい。端末をなくしたなど、急ぎでやむをえないときは、使ってよい（漏れうるのは、先頭5文字だけ）
- alwaysdata の更新履歴（`https://changelog.alwaysdata.com/`）を、ときどき見る。3.14.10 以上が出たら、上げる（下の「4. 更新」の「Python の修正版を上げる」）

## 3. 実データの移行（PR のマージのあと、1回だけ）
1. Mac：サーバー（`run.py`）を止め、`main` に切り替えて新しくする（`git switch main && git pull`）
2. Mac：手動のバックアップと、移行の写しを作る。写しは、リポジトリの外の、同期しないフォルダに作る（iCloud Drive の「デスクトップと書類」・Dropbox などの中に置かない。写しには、実データの全部と、パスワードのハッシュが入るため）
   ```sh
   flask --app app backup-db --label before-transfer
   mkdir -m 700 ~/schedule-transfer
   flask --app app make-transfer-copy ~/schedule-transfer/app.db
   ```
   写しには、ログイン中の端末・ログインの失敗・端末の印と、消した行の残りが入らない。ログインIDが `owner` のままの利用者や、デモの利用者（`demo`）がいれば止まる
3. 本番：管理画面で、サイトを止める（Disable）
4. 本番（SSH）：コードを、マージのコミットにそろえ、下見の DB を消す
   ```sh
   cd ~/schedule_app && . .venv/bin/activate
   flask --app app show-settings   # 1行目が「環境：本番」
   git switch main                 # 下見のブランチから
   git pull --ff-only
   git log -1 --format=%H          # GitHub の main の最新（マージのコミット）と同じこと
   git status --short              # 何も出ないこと（予定外のファイルがない）
   pip install --only-binary :all: -r requirements.txt
   ls -la ~/schedule_data          # app.db のほかに、app.db-journal・-wal・-shm がないこと
   rm ~/schedule_data/app.db
   rm -rf ~/schedule_data/backups  # 下見のバックアップ（なくてもよい）
   ```
   `-journal` などがあれば、消さずに止まり、Claude に相談する
5. Mac から送る：`scp ~/schedule-transfer/app.db <アカウント名>@ssh-<アカウント名>.alwaysdata.net:schedule_data/app.db`
6. 本番（SSH）
   ```sh
   cd ~/schedule_app && . .venv/bin/activate
   chmod 600 ~/schedule_data/app.db
   flask --app app backup-db --label uploaded   # 1行目が「環境：本番」。壊れていないことと件数を確かめる
   flask --app app db upgrade                   # Task 026 の migration（端末の印の表）を当てる
   flask --app app db current                   # 最新の版（head）
   ```
7. iPhone・Mac のパスワードの管理（Safari の自動入力・「パスワード」のアプリ）から、下見のIDとパスワードを消す（このあとのログインの前に。下見と本番は同じサイトの名前のため、自動入力で下見のIDを送ると、本物の端末の印の失敗に数えられ、5回で印が消える）
8. 管理画面で、サイトを動かす（Enable）。Mac と iPhone で、今までのID・パスワードでログインし、今までのデータが見えることを確かめる（このログインで、それぞれの端末に印が付く）
9. Mac で `python3.14 scripts/check_public.py https://...` と `--login`（そのあと、iPhone・Mac でログインし直す必要はない。印は10個まで持てる）
10. 毎日のバックアップを作る（下の「バックアップ」の定期実行）。管理画面から1回動かし、`ls -la ~/schedule_data/backups` に、その日の `app-YYYYMMDD-auto.db`（600）ができたことを確かめる
11. Mac：送った写しを消す（`rm -r ~/schedule-transfer`）。Mac の `instance/app.db` は、移行の前の記録として残すが、もう使わない（`run.py` で起動して書き込むと、本番とずれる）

## 4. 更新（PR をマージしたあと）
1. GitHub で、マージのコミット（`main` の最新）を確かめる
2. 管理画面で、サイトを止める（Disable。古いコードのまま、ライブラリやDBが入れ替わらないように）
3. 本番（SSH）
   ```sh
   cd ~/schedule_app && . .venv/bin/activate
   flask --app app show-settings   # 1行目が「環境：本番」
   git pull --ff-only
   git log -1 --format=%H          # 1 と同じこと
   git status --short              # 何も出ないこと
   pip install --only-binary :all: -r requirements.txt
   flask --app app backup-db --label before-<タスクの番号>
   flask --app app db upgrade
   ```
4. 管理画面で、サイトを動かす（Enable）。Mac で `python3.14 scripts/check_public.py https://...`
5. 戻すとき：`git checkout <前のコミット>` で再起動する。DB を戻すなら、下の「バックアップから戻す」

### Python の修正版を上げる（alwaysdata が新しい 3.14.x を用意したとき）
1. 管理画面の「Environment > Python」と、サイトの「Python version」で、新しい版を選べるかを見る（選べる版は、alwaysdata が決める）
2. 管理画面で、サイトを止める（Disable）
3. 本番（SSH）：`.venv` を作り直す（`.venv` には、入れたライブラリだけがある。DB と設定のファイルは別の場所なので、消してよい）
   ```sh
   cd ~/schedule_app
   python --version                # 新しい版（3.14.10 以上）
   rm -rf .venv
   python -m venv .venv
   . .venv/bin/activate
   python -m pip install --only-binary :all: --require-hashes -r <(echo "pip==26.2.2 --hash=sha256:fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70")
   pip install --only-binary :all: -r requirements.txt
   flask --app app show-settings   # 1行目が「環境：本番」。Python の版
   ```
4. 管理画面で、サイトの Python の版を合わせ、サイトを動かす（Enable）。Mac で `python3.14 scripts/check_public.py https://...`（`--probe` は、下見の道具を置いたときだけ）
5. 3.14.10 以上になったら、Claude に伝える（roadmap の 026-L3 を閉じ、上の「Python の版」の注意を消す）

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
- SSH で、`cd ~/schedule_app && . .venv/bin/activate` のあと、`flask --app app <コマンド>`（`development/database.md` の「利用者の管理」）。アプリのコマンドは、どれも、最初に「環境：本番」と、使うDBを出す（`flask db` は出さないため、その前に `show-settings` などで確かめる）。「ローカル」と出たら、`SCHEDULE_ENV_FILE` を読めていない（止めて、`~/.profile` を確かめる）
- 締め出されたとき（端末の印のない新しい端末で、ログインの失敗が続いたため断られる）：`flask --app app unlock-login <ID>`。続くなら、`rename-user` で、推測されにくいIDに変える
- 端末をなくしたとき：別の端末でログインして「すべての端末からログアウト」（ログイン中の端末と、端末の印が、すべて消える）。ログインできなければ、SSH で `set-password`（同じく、すべて消える）
- 本番では、`create-demo-db`、ID の `demo`、`flask run`・`run.py`（開発用のサーバー）は使えない（断られる）。`flask db` は、`upgrade`・`current`・`history -i` だけ（`downgrade`・`stamp`・`migrate`・`check` などは断られる。migration は Mac で作る）

## 7. ログ
- アプリのログ（`~/admin/logs/uwsgi/`）：ログインの成功・失敗・制限・端末の印の無効化・断った要求（ほかのサイトから）。パスワード・トークン・打ち込まれたIDは出ない。接続元のアドレスは出る
- アクセスの記録（`~/admin/logs/http/`）：alwaysdata が書く（接続元・パス・ブラウザの名前）
- 残す期間：下見で、alwaysdata が古いログを消すかを確かめ、消さないなら、30日より古いログを消す定期実行を足す（Claude と決める）
- ときどき、「端末の印を、続けての失敗で無効にしました」「全体の上限」がないかを見る（印が盗まれた・多くの接続元から試されている兆し）
