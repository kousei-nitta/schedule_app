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
| ログ | `~/admin/logs/`（alwaysdata が書く） | `uwsgi/`：アプリのログ（ログインの成功・失敗など）、`http/`：アクセスの記録。残す期間は30日（「Advanced > Logs」。`uwsgi/` を含む） |

## 1. アカウントの準備（初めの1回）
1. alwaysdata で、Free のアカウントを作る（カードは不要）。アカウント名は、URL（`<アカウント名>.alwaysdata.net`）になるため、GitHub の ID・本名・大学から推測できない名前にする
2. 管理画面のパスワードは、ほかで使っていない長いものにする。登録したメールアドレス（アカウントの復旧の経路）のパスワードも、別の長いものにする
3. 管理画面の2段階認証（TOTP）を有効にする（「Profile」の2段階認証）
4. SSH：「Remote access > SSH」で、SSH を使えるようにする。Mac で鍵を作り（`ssh-keygen -t ed25519`。パスフレーズを付ける）、公開鍵（`~/.ssh/id_ed25519.pub`）を、サーバーの `~/.ssh/authorized_keys` に入れる。鍵で入れることを確かめたら、SSH のパスワードでのログインを切れるなら切る
5. 「Environment > Python」で、既定の Python を 3.14 にする。SSH で `python --version` が 3.14.9 以上であること（3.14.10 以上が望ましい。alwaysdata が 3.14.10 以上を用意するまでは、3.14.9 で進める。下の「Python の版」）
6. 管理画面には、最初の1年は120日に1回、そのあとは6か月に1回、ログインする（しないと、サイトが止まる。カレンダーに予定を入れておく）

## 作業中にする・戻す（サイトを止める代わり）
alwaysdata の管理画面には、サイトを止める機能がない（公式の資料「Disabling a Website」）。そこで、作業の間は、どの要求にも「ただいま作業中です」と 503 を返すだけの道具（`scripts/maintenance_wsgi.py`。標準のライブラリだけ。要求の中身は読まない）を、サイトの入口にする。
- **作業中にする**：管理画面の Web > Sites で、サイトの編集のボタンを押し、Application path を `/home/<アカウント名>/schedule_app/scripts/maintenance_wsgi.py` に変えて、いちばん下の Submit を押す（保存すると、サイトは自動で再起動し、アプリは DB を開かなくなる）。ブラウザで開いて、「ただいま作業中です」と出ることを確かめる
- **戻す**：同じ画面で、Application path を `/home/<アカウント名>/schedule_app/wsgi.py` に戻して、Submit を押す
- ほかの欄（Working directory・Python version・uWSGI additional settings・Environment variables・Virtualenv directory）は、変えない

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
   curl -4 https://api.ipify.org     # この Mac の公開の IPv4 のアドレス
   curl -6 https://api64.ipify.org   # この Mac の公開の IPv6 のアドレス（ない・つながらないなら、IPv4 だけでよい）
   python3.14 scripts/check_public.py --probe https://<アカウント名>.alwaysdata.net
   ```
   尋ねられたら、上の2つのアドレスを、空白で区切って入れる（Mac が両方を持つと、要求ごとに、どちらで届くかが変わるため）
   - スクリプトは、偽の接続元を、ふつうの名前（`X-Real-IP`）と下線の名前（`X_Real_IP`）で、別々に送る。ふつうの名前の偽の値が上書きされ（値が1つで、この Mac のアドレス）、下線の名前の偽の値が、捨てられるか、本物の値と混ざる（`192.0.2.20, <Mac のアドレス>` のような形。アプリが400で断るので安全）ヘッダーを、「候補」として出す。`REMOTE_ADDR` が、この Mac のアドレスのままで、ヘッダーの写しでなければ、それも候補になる（いちばんよい）。alwaysdata では、`REMOTE_ADDR` は `X-Real-IP` の写しで（2026-11-08 の下見）、「X-Real-IP の写し」と出るので、`X-Real-IP` を使う。候補の最初のものを `CLIENT_ADDRESS_HEADER` にする。候補が「なし」なら、止まって相談する
   - ✗ があれば（Python が 3.14.9 より古い、ワーカーが1つでない、ホームのファイルシステムがネットワーク上（`nfs` など）、`X-Forwarded-Proto` を偽れる）、止まって相談する
   - 「REMOTE_ADDR」の行も、Claude に伝える（Mac のアドレスは、IPv4 も IPv6 も `<MAC>` に。内部のアドレス（`fd00::…` など）なら、そのまま）
   - 「IPv4 で届いた」「IPv6 で届いた」と出たら、その種類の Mac のアドレスを入れていない。上の `curl` の、その種類の結果を足して、入れ直す
   - 最後の行の「uWSGI の待ち受け」を、Claude に伝える（共有のサーバーの、ほかの利用者が、プロキシを通らずにアプリへ直接つなげるかを判断する）。伝えるときは、アカウント名を `<アカウント名>` に、Mac のアドレスを伏せる
4. 下見の道具が動いているうちに（ブラウザでサイトを開いた直後に）、SSH で、自分のサイトの uWSGI に、プロキシを通らずに直接つないでみる。`<待ち受け>` は、3 の「uWSGI の待ち受け」の値（例：`[fd00::7:eaac]:8100`）。ほかのアドレスには、つながない（ほかの利用者のサイトかもしれない）
   ```sh
   ss -ltnH | grep ':8100'       # 自分の待ち受けが、この SSH から見えるか
   python - '<待ち受け>' <<'EOF'
   import json, socket, sys
   host, port = sys.argv[1].rsplit(":", 1)
   request = b"GET / HTTP/1.0\r\nHost: test\r\nX-Real-IP: 192.0.2.77\r\n\r\n"
   proxy_line = b"PROXY TCP4 192.0.2.88 192.0.2.99 40000 8100\r\n"
   for title, first in [("1 直接", b""), ("2 PROXYの行", proxy_line)]:
       try:
           with socket.create_connection((host.strip("[]"), int(port)), timeout=10) as conn:
               conn.sendall(first + request)
               data = b"".join(iter(lambda: conn.recv(65536), b""))
       except OSError as error:
           print(title, "つなげない：", error)
           continue
       head, _, body = data.partition(b"\r\n\r\n")
       print(title, head.split(b"\r\n")[0].decode(errors="replace") or "応答なし")
       if body.startswith(b"{"):
           seen = json.loads(body)
           print("   REMOTE_ADDR:", seen["REMOTE_ADDR"], "/ X-Real-IP:", seen["headers"].get("HTTP_X_REAL_IP"))
   EOF
   ```
   - 「つなげない」（Connection refused など）でも、ほかのアカウントからつなげないとは言えない。alwaysdata の返事（2026-11-09）では、アカウントの間のネットワークは分けていない（ほかのアカウントは、直接つなげる。`architecture/security.md` の「接続元」の「残る弱さ」）。2026-11-08 の下見では、サイトを開いた直後（下見の道具が動いているはずの間）も、自分の SSH からは、自分の待ち受けが `ss` に出ず、つなげなかった（SSH とサイトが、別のサーバーで動いているためと考えられる。推測）
   - 「1 直接」が 200 なら、プロキシを通らずにつなげる（`X-Real-IP` の偽の値 `192.0.2.77` が届くので、接続元を偽れる。`architecture/security.md` の「接続元」の「残る弱さ」）
   - 結果を Claude に伝える（サーバーの中のアドレスは、伏せなくてよい。アカウント名は伏せる）
5. すぐに、サイトの Application path を `/home/<アカウント名>/schedule_app/scripts/maintenance_wsgi.py` に変えて保存する（下見の道具を、公開したままにしない。下の「作業中にする・戻す」）

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
4. 管理画面のサイトの設定（Application path は、まだ作業中の道具のまま。手順6で変える）。変えたら、Submit を押す（作業中の道具のまま、再起動する）
   - Environment に `SCHEDULE_ENV_FILE=/home/<アカウント名>/.config/schedule_app/production.env`（値は、パスだけ）
   - Virtualenv directory：`/home/<アカウント名>/schedule_app/.venv`
5. SSH で、設定と、空のDBを作る（下見の DB。架空のデータだけを入れる）
   ```sh
   cd ~/schedule_app && . .venv/bin/activate
   flask --app app show-settings        # 1行目が「環境：本番」であること。DB・権限（700）も。SECRET_KEY は長さだけ出る
   flask --app app db upgrade           # 空のDBを作る
   flask --app app create-user <下見用のID>   # 架空の利用者（demo は使えない）
   ```
   - 本番のアプリのコマンドは、どれも、最初に「環境：本番」と、使うDBを出す（`flask db` は出さない）。「環境：ローカル」と出たら、設定を読めていない。その先へ進まない（`flask db upgrade` などが、リポジトリの中に別のDBを作ってしまう）。手順3を確かめる
6. 管理画面で、Application path を `/home/<アカウント名>/schedule_app/wsgi.py` に変えて、Submit を押す（保存すると、サイトは自動で再起動する）。DB を作ってから、アプリを開く（先に開くと、表のないDBで、要求がエラーになる）。ブラウザで開き、ログインの画面が出ることを確かめる。開けないときは、`~/admin/logs/uwsgi/` の新しいログを見る（起動しない理由が、日本語で出る）

### 2-3. 点検する
点検の間のログアウトは、利用者のメニューの「ログアウト」を使う。すぐ下の「すべての端末からログアウト」は、すべての端末の印を消すため、手順4の確かめにならない（2026-11-08・09 の下見では、これを押したため、印が0個になり、印の確かめでログインできなかった）。

1. Mac で
   ```sh
   python3.14 scripts/check_public.py https://<アカウント名>.alwaysdata.net
   python3.14 scripts/check_public.py --login https://<アカウント名>.alwaysdata.net   # 下見用のID・パスワード
   ```
   すべて ✓ であること。✗ があれば、表示を Claude に伝える（URL は伏せる）。ほかの名前の Host には、alwaysdata のプロキシが 404 で答え、アプリには届かない（下見で確かめた。点検は、どちらが答えたかを表示する）。`--login` は、動かすたびに、本番に端末の印を1つ増やす（利用者ごとに10個まで。古いものから消える）。何度も動かしたあとは、iPhone・Mac でログインし直す（印を付け直す）
2. iPhone の Safari で
   - ログインして（この iPhone に、端末の印が付く）、架空のデータで、学期・授業・予定・課題を登録し、3つのモードを見る（横にはみ出さない、カレンダーが一覧で始まる、課題の表が読める）。開くまでの時間・操作の速さが、実用になるか
   - ほかのサイトのリンクから開く（メモのアプリにURLを書いて、タップする）：ログインの画面が1回だけ開き直され、ログイン中なら、そのまま使える
   - 「ログアウト」でログアウトし、「戻る」のボタンと、左の端からのスワイプで戻る：ログイン中の画面（スワイプのときの画面の写しを含む）が見えない
   - モバイルの回線でも、主な画面が実用の速さか見る
3. Mac の Chrome・Safari でも、ログインと主な画面を開き、「ログアウト」でログアウトする
4. 端末の印を確かめる（2・3 のあと。この順番で。ログインIDごとの制限で試すので、iPhone と Mac は、同じ接続元でなくてよい）
   1. iPhone の Safari のふつうのタブで、ログインし、「ログアウト」する（印は残る）
   2. Mac の Safari のプライベートウインドウ（「ファイル」→「新規プライベートウインドウ」。印がない）で、下見のIDと、わざと違うパスワードを、「ログインの失敗が続いたため、しばらくログインできません。…」が出るまで送る（24時間の中の、このIDの失敗が5回になると、次の送信から出る。IDは正確に打つ。ふつうのウインドウで送ると、印のある道で扱われ、IDの失敗に数えられない）
   3. 2 の最後の失敗から15分のうちに（IDごとの制限が解ける前に）、iPhone のふつうのタブ（印がある）で、下見のIDと正しいパスワードで、ログインできる（印のある道は、IDごと・接続元ごとの制限を受けない）
   4. 続けて、iPhone のプライベートのタブ（印がない）で、下見のIDと正しいパスワードを送ると、2 と同じ「しばらくログインできません」になる（断っている間は、正しくても断る）。ここでログインできてしまったら、2 のIDの打ち間違いか、15分を過ぎた。1 からやり直す
   5. SSH で、ログを見る：`grep -h "ログインしました" ~/admin/logs/uwsgi/*.log | tail -n 3`。最後の行（4 の3 のログイン）が「印のある端末」であること
   6. iPhone のふつうのタブで、「ログアウト」する
5. 最後に、Mac で、接続元の偽装を点検する（Mac と、同じ接続元の端末が、1時間ログインできなくなる。印のある端末は使える）。この接続元からの、最後のログインの失敗（4 の2 など）から、1時間あけて動かす（あけないと、11回目より前に断られ、✗ になる）。ふつうの名前で偽った11回（10回目までが 401、11回目が 429）と、下線の名前で偽った3回（どれも 400 か 429）を、別々に送る
   ```sh
   python3.14 scripts/check_public.py --rate-limit https://<アカウント名>.alwaysdata.net
   ```
   表示が残らなかったときは、Claude に相談する（ログで確かめられる。2026-11-09 の下見では、1回目の表示が残らず、ログで確かめた：存在しないIDの「ログインに失敗しました」が10行、そのあとに「ログインを断りました（試行の制限…）」が1行で、どれも、ほかのログインと同じ接続元（偽った、毎回違うアドレスではない）。下線の名前の3回は、1時間の中で動かした2回目で、400・400・400）
6. SSH で：`ls -la ~/schedule_data ~/.config/schedule_app`（DBとフォルダが、自分だけの権限。`backups` は、まだなくてよい）、`ps aux | grep -c uwsgi`（ほかの利用者のプロセスが見えるか）
7. 管理画面の「Advanced > Logs」で、ログを残す期間を30日にする（下の「7. ログ」）
8. 下見の DB は、まだ消さない（消すのは、移行の手順で、作業中にしたあと）

### Python の版
- 本番の Python は、alwaysdata が用意する 3.14 の修正版から選ぶ（サイト（uWSGI）は、alwaysdata の Python で動く）。2026-11-03 の時点では 3.14.9 で、セキュリティの修正版の 3.14.10（2026-10-25）は、まだない。3.14.10 以上が用意されるまで、3.14.9 で進める（Koma の承認、2026-11-03。ADR 0005 の「影響」。roadmap の 026-L3）
- 3.14.10 の3つのセキュリティの修正のうち、本番に関係するのは、eMudhra の件（`ssl` が、侵害された中間CAの鍵を拒む）だけ（`tarfile`・`http.cookiejar` は使わない。利用者からの HTTPS は、alwaysdata のプロキシが受ける）。本番の Python から外へつなぐのは、次の2つ
  - pip を上げる1回目：上の、ハッシュと照らす手順で守る（pip 26.2.2 は、この件に対応済み。そのあとのライブラリの取得も守られる）
  - `set-password`・`create-user` の、漏えいしたパスワードの確認：3.14.10 以上に上げるまで、本番で、本物のパスワードの `set-password`・`create-user` を使わない（通信を乗っ取られると、パスワードのハッシュの先頭5文字が漏れうる）。本物のパスワードは、Mac で決めたものを、移行の写しで運ぶ。下見の架空のパスワードは、使ってよい。端末をなくしたなど、急ぎでやむをえないときは、使ってよい（漏れうるのは、先頭5文字だけ）
- alwaysdata の更新履歴（`https://changelog.alwaysdata.com/`）を、ときどき見る。3.14.10 以上が出たら、上げる（下の「4. 更新」の「Python の修正版を上げる」）

## 3. 実データの移行（PR のマージのあと、1回だけ）
始める前に：ほかのアカウントが、このサイトの待ち受けのアドレスとポートで待ち受けられないこと（alwaysdata の返事、2026-11-10：待ち受けられない。uWSGI が止まっている・再起動の間も。`architecture/security.md` の「接続元」）。2026-11-12 の移行は、この返事を得てから行った。できる・分からないなら、移行しない（Claude と相談する。できるなら、プロキシからの要求（パスワード・Cookie）を、ほかのアカウントが受け取れ、アプリでは守れない。公開先を移すときも、移す先で同じことを確かめる）。

1. Mac：サーバー（`run.py`）を止め、`main` に切り替えて新しくする（`git switch main && git pull`）
2. Mac：手動のバックアップと、移行の写しを作る。写しは、リポジトリの外の、同期しないフォルダに作る（iCloud Drive の「デスクトップと書類」・Dropbox などの中に置かない。写しには、実データの全部と、パスワードのハッシュが入るため）
   ```sh
   flask --app app backup-db --label before-transfer
   mkdir -m 700 ~/schedule-transfer
   flask --app app make-transfer-copy ~/schedule-transfer/app.db
   ```
   写しには、ログイン中の端末・ログインの失敗・端末の印と、消した行の残りが入らない。ログインIDが `owner` のままの利用者や、デモの利用者（`demo`）がいれば止まる
3. 本番：管理画面で、作業中にする（上の「作業中にする・戻す」）
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
8. 管理画面で、Application path を戻す（上の「作業中にする・戻す」）。Mac と iPhone で、今までのID・パスワードでログインし、今までのデータが見えることを確かめる（このログインで、それぞれの端末に印が付く）
9. Mac で `python3.14 scripts/check_public.py https://...` と `--login`（そのあと、iPhone・Mac でログインし直す必要はない。印は10個まで持てる）
10. 毎日のバックアップを作る（下の「バックアップ」の定期実行）。まず、サーバーの時刻（SSH で `date`）の5分ほどあとに予定して、動くかを試す（alwaysdata のヘルプには、すぐに1回動かす方法が書かれていない）。その時刻の5分ほどあとに（予定より少し遅れて動く。2026-11-12 は約1分40秒）、`ls -la ~/schedule_data/backups` に、その日（日本の日付）の `app-YYYYMMDD-auto.db`（600）ができたことと、定期実行の記録（`ls -lt ~/admin/logs/jobs/2026/` のいちばん新しいファイル。年ごとのフォルダ）が `exit code: 0` で終わったことを確かめる。動いたら、時刻を 03:17 に直す（同じ日にもう一度動いても、「今日の分は、作成済みです」と出るだけ）
11. Mac：送った写しを消す（`rm -r ~/schedule-transfer`）。Mac の `instance/app.db` は、移行の前の記録として残すが、もう使わない（`run.py` で起動して書き込むと、本番とずれる）

## 4. 更新（PR をマージしたあと）
1. GitHub で、マージのコミット（`main` の最新）を確かめる
2. 管理画面で、作業中にする（古いコードのまま、ライブラリやDBが入れ替わらないように。上の「作業中にする・戻す」）
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
4. 管理画面で、Application path を戻す。Mac で `python3.14 scripts/check_public.py https://...`
5. 戻すとき：`git checkout <前のコミット>` で再起動する。DB を戻すなら、下の「バックアップから戻す」

### Python の修正版を上げる（alwaysdata が新しい 3.14.x を用意したとき）
1. 管理画面の「Environment > Python」と、サイトの「Python version」で、新しい版を選べるかを見る（選べる版は、alwaysdata が決める）
2. 管理画面で、作業中にする
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
4. 管理画面で、サイトの Python の版を合わせ、Application path を戻す。Mac で `python3.14 scripts/check_public.py https://...`（`--probe` は、下見の道具を置いたときだけ）
5. 3.14.10 以上になったら、Claude に伝える（roadmap の 026-L3 を閉じ、上の「Python の版」の注意を消す）

## 5. バックアップ
- 毎日：管理画面の「Advanced > Scheduled tasks」で、毎日1回の定期実行を作る
  ```sh
  cd $HOME/schedule_app && SCHEDULE_ENV_FILE=$HOME/.config/schedule_app/production.env .venv/bin/flask --app app daily-backup
  ```
  - 種類：コマンド。Environment は変えない
  - Frequency：「Every day at 03:17」（サーバーの時刻＝パリの時刻）。定期実行は、SSH の `date` と同じ時計（2026-11 は CET＝UTC+1）で動く（2026-11-12 に試して確かめた）
  - 03:17 にする理由：日本の昼（冬は11:17、夏は10:17）で、日付の境目にかからない。夏時間の切り替えで、飛んだり2回あったりする2時台にも当たらない
  - 「Error report email addresses」：自分のメールアドレス。終了コードが0でないときに、報告のメールが届く（定期実行そのものが動かなかったときは届かない）
  - 動き：その日（日本時間）の分を作り、新しい30個を残す（本番のアプリは、作るファイルを、持ち主だけが読める権限にする）。その日の分があれば、「今日の分は、作成済みです」と出るだけ。失敗すると、終了コード1で終わる。定期実行の記録（`~/admin/logs/jobs/2026/`）には、開始・終了・終了コードだけが残り、コマンドの出力は入らない（2026-11-12 に確かめた）。理由（日本語の文）は、SSH で同じコマンドを動かすと見られる（報告のメールに出力が入るかは、まだ見ていない）
  - ほかに、alwaysdata が3日分のバックアップを持つ
- 毎週：Mac に取り寄せる（Mac の故障・本番のアカウントの停止に備える。iCloud Drive などの同期するフォルダには置かない）
  ```sh
  mkdir -p -m 700 ~/schedule-backups
  rsync -av --chmod=F600 <アカウント名>@ssh-<アカウント名>.alwaysdata.net:schedule_data/backups/ ~/schedule-backups/
  ```
  バックアップには、パスワードのハッシュ・ログイン中の端末の記録（SHA-256）も入る。Mac は FileVault（ディスクの暗号化）をオンにしておく
- `daily-backup` は、終わりに、バックアップのフォルダの合計の大きさを出す。1GB の上限に近づいていないかを、ときどき見る
- バックアップから戻す：作業中にし、`flask --app app backup-db --label before-restore` のあと、戻すファイルを `~/schedule_data/app.db` に写し（`-journal` などが残っていないこと）、`flask --app app backup-db --label after-restore` が成功してから、Application path を戻す（考え方は `development/database.md` の「バックアップから戻す」と同じ）

## 6. 利用者の管理（本番）
- SSH で、`cd ~/schedule_app && . .venv/bin/activate` のあと、`flask --app app <コマンド>`（`development/database.md` の「利用者の管理」）。アプリのコマンドは、どれも、最初に「環境：本番」と、使うDBを出す（`flask db` は出さないため、その前に `show-settings` などで確かめる）。「ローカル」と出たら、`SCHEDULE_ENV_FILE` を読めていない（止めて、`~/.profile` を確かめる）
- 締め出されたとき（端末の印のない新しい端末で、ログインの失敗が続いたため断られる）：`flask --app app unlock-login <ID>`。続くなら、`rename-user` で、推測されにくいIDに変える
- 端末をなくしたとき：別の端末でログインして「すべての端末からログアウト」（ログイン中の端末と、端末の印が、すべて消える）。ログインできなければ、SSH で `set-password`（同じく、すべて消える）
- ふだんは「ログアウト」を使う。「すべての端末からログアウト」は、端末をなくしたとき・知らない端末があるとき（`docs/ui_ux.md` の「利用者のメニュー」）だけ（すべての端末の印が消え、それぞれの端末で次にログインするまで、締め出しへの守り（印のある道）がなくなる）
- 本番では、`create-demo-db`、ID の `demo`、`flask run`・`run.py`（開発用のサーバー）は使えない（断られる）。`flask db` は、`upgrade`・`current`・`history -i` だけ（`downgrade`・`stamp`・`migrate`・`check` などは断られる。migration は Mac で作る）

## 7. ログ
- アプリのログ（`~/admin/logs/uwsgi/`）：ログインの成功・失敗・制限・端末の印の無効化・断った要求（ほかのサイトから）。パスワード・トークン・打ち込まれたIDは出ない。接続元のアドレスは出る
- アクセスの記録（`~/admin/logs/http/`）：alwaysdata が書く（接続元・パス・ブラウザの名前）
- 残す期間：30日。管理画面の「Advanced > Logs」で決める（alwaysdata の資料「Admin Directory Overview」：期間を過ぎたログを消す。アプリのログ（`uwsgi/`）を含む `admin/logs` のすべてに効く。alwaysdata の返事、2026-11-10）。消す定期実行は足さない。`uwsgi/` は日ごとに分かれていない1つのファイルなので、2026-12-20 以降に一度、`grep -h -m 1 '^\[20' ~/admin/logs/uwsgi/*.log` で、いちばん古いアプリのログの日付を見る（日付のある行だけを見るため。アプリのログは、下見の 2026-11-08 からあるので、それが35日をこえてから、余裕を見て、2026-12-20 以降に見る。消す処理の遅れを見込み、35日ほどより前の行が残っていれば、Claude に相談する）
- ログインの記録を見る：`grep -h "in auth" ~/admin/logs/uwsgi/*.log | tail -n 40`（接続元のアドレスが出るので、Claude に伝えるときは伏せる）
- ときどき、「端末の印を、続けての失敗で無効にしました」「全体の上限」がないかを見る（印が盗まれた・多くの接続元から試されている兆し）
