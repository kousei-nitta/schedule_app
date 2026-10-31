# セキュリティ

> 仕様の正本。変更は、Komaの承認を得てから、PRで行う（`docs/development/workflow.md`）。

守るもの、想定する攻撃、今の対策、ローカルと公開の違い、公開の前の点検。対策を入れた経緯は、`docs/decisions/0002-security-baseline-before-login.md`（ADR 0002）と Task 024の計画書、ログインと認可は `docs/decisions/0004-login-and-user-data.md`（ADR 0004）と Task 025の計画書。

考え方：インターネットに公開すると、あらゆる面から攻撃され、どこかから情報が漏れうると考える。攻撃させない守りを重ね、破られても漏れる情報が少ない作りにする（Koma、2026-10-30）。

## 守るもの
| 守るもの | 内容 |
|---|---|
| 実データのDB | KomaのMacの `instance/app.db`（公開のあとは、クラウドのDB）。個人の予定・時間割・課題。読まれない・変えられない・消えないように守る（消えたときの備えは、`architecture/overview.md` の「データの保護（バックアップ）」） |
| 利用者ごとのデータ | 利用者は、自分のデータだけを扱える。他人のデータは、読めない・変えられない・あることも分からない（下の「認可」） |
| ログインの情報 | パスワード（DBには scrypt のハッシュだけ）、ログイン中の端末の記録（トークンのSHA-256だけ）、ログインの失敗の記録（IDと接続元のHMACだけ）、`SECRET_KEY`。DBが漏れても、パスワード・ログイン・打ち込まれたID・接続元が分からないようにする |
| 開発の環境 | KomaのMacと、そこで動く Python・ライブラリ。乗っ取られた依存や、通信の途中の偽物から守る |
| リポジトリ | 公開のリポジトリ（`kousei-nitta/schedule_app`）。秘密・個人のデータを入れない。CIと依存の設定を、外から悪用されないようにする |

## 想定する攻撃（今の形：ローカル）
今は、Macの `127.0.0.1:5001` で使う（Task 025から、ログインが要る）。外から直接は届かないが、同じMacのブラウザで開いた**ほかのサイト**を経由する攻撃と、**依存の供給網**の攻撃を想定する。

| 攻撃 | 内容 | 対策 |
|---|---|---|
| DNSリバインディング | 悪意のあるサイトが、自分の名前を `127.0.0.1` に向け直し、このアプリのAPIを、同じサイトとして読み書きする | Hostヘッダーの検査 |
| CSRF（別のサイトからの書き込み） | 悪意のあるサイトのフォームやスクリプトが、このアプリのAPIに書き込みを送る。ログイン・ログアウトをさせる | 下の「ほかのサイトからの要求（CSRF）」：`Sec-Fetch-Site`・`Origin` の検査、Cookie の `SameSite=Strict`、JSONの本文と `Content-Type: application/json` だけを受け付ける（フォームの送信は400）、CORSを許さない（`architecture/api.md`） |
| XSS（入力がスクリプトとして動く） | 予定の名前などに入れた文字が、画面でHTMLとして解釈される | 文字は `textContent` で入れる。HTMLとして解釈される書き方をESLintで禁止。CSPで、インラインのスクリプトを止める |
| クリックジャッキング | ほかのサイトの枠（iframe）の中に表示し、ボタンを押させる | `X-Frame-Options: DENY`、CSPの `frame-ancestors 'none'` |
| 壊れた入力での停止 | 入れ子が深すぎるJSONで、サーバーの中のエラー（500）になる | 400（`invalid_json`）にする |
| デバッガーの悪用 | デバッグモードのエラー画面から、サーバーの中でコードを実行する | デバッグモードは、指定したときだけ |
| 依存の乗っ取り | 乗っ取られて公開された版のライブラリ・アクションが、インストールやCIで動く | 版の固定、公開から2週間待つ規則、Dependabotの待ち時間、npmのスクリプトを動かさない、アクションのSHAでの固定、CDNの `integrity`（SRI） |
| 通信の途中の偽物 | `pip install` などの通信に、偽物を渡す | pip・certifi・Python を、侵害された証明書に対応した版にする（「開発の環境」） |

## 想定する攻撃（ログイン。公開を見据えて）
ログインは、公開してインターネットのだれからでも届くことを前提に作る（Task 025）。

| 攻撃 | 内容 | 対策 |
|---|---|---|
| パスワードの推測 | 総当たり・よく使われるパスワード・ほかのサイトから漏れたパスワード（同じものを使っている場合）を試す | 15文字以上、漏えいしたパスワードを断る（「パスワード」）。試行の制限（「ログインの試行の制限」） |
| 分散した総当たり | 多くの接続元から、1つのIDを試す | ログインIDごとの制限（接続元によらない） |
| IDの有無の推測 | 応答の文・状態コード・時間の違いから、ログインIDがあるかを知る | IDがなくても、同じ文・同じ状態コード・同じ計算（ダミーのハッシュ）。制限も、IDの有無によらず同じ |
| なりすまし | ログインのCookieを盗む・推測する・偽造する・固定する | 32バイトの乱数、`HttpOnly`、ログインのたびに新しいトークン、DBにはSHA-256だけ、期限（14日・30日）、ログアウトですぐ無効（「ログインの状態（セッション）」） |
| 他人のデータの読み書き | URLのID・本文で参照するID・一覧・件数・候補・重複の検査・一括の処理から、他人のデータに触れる・知る | 既定で拒否と、すべての問い合わせを持ち主で絞る（「認可」）。網羅的なテスト |
| 締め出しの悪用 | わざと失敗を続けて、本人をログインできなくする | ログイン中の端末は、そのまま使える。推測されにくいログインIDにする（`rename-user`）。制限を解くコマンド（`unlock-login`） |
| 資源の枯渇 | ログインの前に、重い計算（scrypt）を、同時にたくさんさせる。大きな本文を読ませる | 断るかを先に判断（計算しない）、決まりに合わない入力は計算しない、同時の確かめは2つまで（空かなければ503）、ログインの本文は16KiBまで（超えたら、読まずに413）、失敗の記録に索引（行を増やされても遅くならない） |
| 消したデータの残り | DBのファイルやバックアップが漏れたときに、消したはずの行（メモなど）が、ファイルの空き領域から読まれる | SQLite の `secure_delete` をオン（下の「入力」） |
| DB・ログからの漏れ | DB・バックアップ・ログが漏れる | パスワードはハッシュ、トークンはSHA-256、失敗の記録はHMAC。ログに、パスワード・トークン・打ち込まれたIDを出さない |
| キャッシュからの漏れ | 共用のPCで、ログアウトのあとに「戻る」で見える。途中の機器に残る | `Cache-Control: no-store`、ログアウトで `Clear-Site-Data` |

## 対策

### Hostヘッダーの検査
- `app/config.py` の `TRUSTED_HOSTS = ["127.0.0.1", "localhost"]`（Flaskの設定）。要求の `Host` の名前（ポートは見ない）が、どちらかと同じときだけ受け付ける
- ほかの名前の要求は、400。`/api` では、JSONのエラー（`bad_request`「リクエストを受け付けられません」。`architecture/api.md` の「エラー」）。画面（`/` など）は、Flaskの標準のHTMLのまま
- `localhost` は、テストの `test_client` の既定の名前でもある。公開のとき（Task 026）は、本番の名前を、設定で決める

### セキュリティのヘッダー
`app/security.py` が、すべての応答（画面・API・静的ファイル・エラー）に付ける。

| ヘッダー | 値 | 理由 |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | 宣言した種類（`Content-Type`）と違うものとして、ブラウザに読ませない |
| `X-Frame-Options` | `DENY` | ほかのサイトの枠の中に表示させない（古いブラウザのため。CSPの `frame-ancestors` と同じ） |
| `Referrer-Policy` | `same-origin` | ほかのサイト（CDNを含む）へ、URLを送らない。`no-referrer` にしないのは、フォームの送信（ログインの画面など）の `Origin` ヘッダーが `null` になり、Task 025の `Origin` の検査に使えなくなるため（`fetch` の送信は、`no-referrer` でも `Origin` を送る） |
| `Content-Security-Policy` | 下の表 | ページが読み込んでよいもの・実行してよいものを、ブラウザに伝える |
| `Cross-Origin-Opener-Policy` | `same-origin` | ほかのサイトの窓と、このアプリの窓を切り離す（ほかのサイトから、この窓を操作・観察させない） |
| `Cross-Origin-Resource-Policy` | `same-origin` | このアプリの応答を、ほかのサイトのページに読み込ませない（`<script src>`・`<img src>` などを含む） |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), payment=(), usb=()` | 使わないブラウザの機能を、使えなくする |
| `X-Robots-Tag` | `noindex, nofollow` | 公開したとき、検索エンジンに載せない |
| `Cache-Control` | `no-store`（静的ファイルのほか） | 個人のデータを含む応答（画面・API・ログインの画面）を、ブラウザや途中の機器に保存させない |

**CSP（Content-Security-Policy）**

| 種類 | 許すもの | 理由 |
|---|---|---|
| `default-src` | `'self'` | 下で決めていない種類は、自分のサイトからだけ |
| `script-src` | `'self'`、CDNの `bootstrap.bundle.min.js`・`index.global.min.js`（URLまで指定） | 自分のファイル（`main.js` など）と、決まった2つのファイルだけ。jsDelivrの、ほかのファイルは読ませない |
| `style-src` | `'self'`、CDNの `bootstrap.min.css`（URLまで指定）、`'nonce-…'` | `style.css`、BootstrapのCSS、FullCalendarが差し込む `<style>` |
| `img-src` | `'self'`、`data:` | BootstrapのCSSは、選択欄の矢印などに `data:` の画像を使う |
| `font-src` | `'self'`、`data:` | FullCalendarのCSSは、ボタンのアイコンに `data:` のフォントを使う |
| `connect-src` | `'self'` | `fetch` は、自分のAPIだけ |
| `object-src`・`base-uri` | `'none'` | 使わない |
| `form-action` | `'self'` | フォームの送り先は、自分だけ（画面のフォームは、JavaScriptで送る） |
| `frame-ancestors` | `'none'` | ほかのサイトの枠の中に表示させない |

- `'unsafe-inline'`（インラインのスクリプト・スタイル）と `'unsafe-eval'`（文字列からのコードの実行）は、使わない。弱めないと画面が動かない場合は、止まってKomaに確かめる
- ログインの画面（`/login`）は、`script-src 'none'`（スクリプトを1つも許さない）。テンプレートも、スクリプトを読み込まない（`base.html` の `library_scripts` を空にする）。パスワードを入れる画面では、外部のスクリプトも含めて、何も動かさない
- **nonce**：要求ごとに作る使い捨ての値（`secrets.token_urlsafe(16)`）。FullCalendarは、自分のCSSを `<style>` として差し込むとき、`nonce` の付いた `<script>` から値を読んで付ける。そのため、`base.html` の FullCalendar の `<script>` に `nonce="{{ csp_nonce }}"` を付ける。CSPは、その値の `<style>` だけを許す
- CDNのファイルの版を変えるときは、`base.html` と同時に、`app/security.py` のURLも変える（`tests/test_security.py` が、`base.html` のCDNのURLが、すべてCSPで許されていることを確かめる。`architecture/overview.md` の「Bootstrapの読み込み」「FullCalendarの読み込み」）
- テンプレートには、インラインの `<script>`（`src` のないもの）・`<style>`・`style` 属性・`onclick` などの属性を書かない（CSPで止まる。`tests/test_security.py` が確かめる）
- E2Eテストは、画面の主な流れで、CSPの違反（ブラウザが止めた読み込み・実行）がないことを確かめる（`development/testing.md` の「E2Eテスト」）

### 入力
- JSONの本文の扱い・CORSを許さないことは、`architecture/api.md` の「リクエストとレスポンス（JSON）」「URLとメソッド」
- 入れ子が深すぎるJSON（Pythonの `json` が `RecursionError` にするもの）は、400（`invalid_json`）
- 画面での文字の表示は `textContent`。`innerHTML` などは使わない（`CLAUDE.md`。ESLintが確かめる。下の「依存とCI」）
- DBは、SQLAlchemy（ORM）だけで読み書きする（SQLの文字列を、入力から組み立てない）
- 消したデータを、DBのファイルに残さない：SQLite につなぐたびに `PRAGMA secure_delete = ON`（`app/extensions.py`）。消した行の中身を、0で上書きする。これより前に消した行の空き領域と、前のバックアップには、残っていることがある（クラウドへ移すとき（Task 026）は、行だけを写すため、持ち込まれない）

### ログイン
画面は `docs/ui_ux.md` の「ログイン」、処理は `app/auth.py`・`app/routes/auth.py`・`app/login_limits.py`・`app/user_sessions.py`・`app/passwords.py`。表は `architecture/data_model.md` の「User」「UserSession」「LoginFailure」。

**既定で拒否**（`app/auth.py`）
- ログインしなくても使えるのは、ログインの画面（`/login`）と静的ファイル（`/static/…`）だけ（routeの名前 `auth.login`・`static` で決める。パスの前方一致で決めない）。ほかは、新しく足したものも含めて、ログインが要る
- ログインしていなければ、画面はログインの画面へ（303）、`/api` は401（`unauthorized`「ログインしてください」。`architecture/api.md` の「エラー」）。存在しないURLも同じ（ログインの前に、どんなURLがあるかを知らせない）。`OPTIONS`・`HEAD` も同じ
- 信頼しない Host の要求は、ログインの確かめより先に、400 のまま（「Hostヘッダーの検査」）
- テスト・デモのために、ログインを外す設定や分岐は作らない（テストとデモは、本物のログイン中の端末の行を作って使う）

**パスワード**（`app/passwords.py`）
- 長さ：NFKC（全角の英数字を半角にする、など）で正規化してから数えて、15〜128文字（NIST SP 800-63B-4。パスワードだけでログインする場合は15文字以上）。文字の種類の決まり（大文字・記号を必ず含む、など）は設けない。空白も使える
- 断るもの：ログインIDを含む（大文字・小文字を区別しない）、同じ文字の繰り返しだけ、使われている文字の種類が5つ未満（`abababab…` など）、連続した文字だけ（`123…`・`abc…`・`987…`。空白は除いて見る）、制御文字、漏えいしたパスワード。漏えいの確認のほかは、手元で確かめる（漏えいの確認を省いたときも断る）
- 漏えいの確認：Have I Been Pwned の Pwned Passwords（無料）。パスワードのSHA-1の先頭5文字だけを送り、同じ先頭のハッシュの一覧を受け取って、手元で照らす（k-匿名性。サービスは、どのパスワードかを知れない）。`Add-Padding` で、応答の大きさからも推測させない（件数0の詰め物は数えない）。つながらないときは失敗にし、コマンドの `--skip-breach-check` でだけ省ける
- ハッシュ：Werkzeug の scrypt（N=2^15・r=8・p=3。OWASPの推奨の1つ。1回に32MiBのメモリー）。パスワードそのものは保存しない
- 設定するのは、コマンドだけ（下の「利用者の管理」）。画面では、パスワードの設定・変更を受け付けない。コマンドは、表示しない入力で2回受け取る（引数・環境変数では受け取らない。履歴に残さないため）

**ログインの処理の順序**（`POST /login`。ログインを試すのは `POST` だけ。`GET`・`HEAD` は画面を返すだけ）
1. ほかのサイトからの要求なら、断る（403。下の「ほかのサイトからの要求（CSRF）」）。本文が16KiBより大きければ、読まずに413
2. 試行の制限で断っていれば、429（「約N分後に、もう一度お試しください」。60分以上は「約N時間後」）。パスワードは確かめない
3. 受け付けるなら、先に失敗として記録する（同時の試行で、数え漏れないため）
4. 決まりに合わないID（ありえないID）と、512文字より長いパスワード（正規化の前）は、計算せずに失敗にする
5. パスワードを確かめる。同時に確かめるのは2つまで（scrypt で、メモリーを使い切らせないため）。5秒待っても空かなければ、503（「混み合っています」。記録を取り消す）。IDがない・パスワードのない利用者でも、ダミーのハッシュで、同じ計算をする
6. 失敗：401「ログインIDかパスワードが違います」（IDの有無で、文・状態コードを変えない）。成功：その接続元からの、そのIDの失敗の記録を消し、この端末の前のログインがあれば消し、新しいトークンでログインする。トップ（`/`）へ303（`?next=` などの、移り先の指定は受け付けない）

**ログインの試行の制限**（`app/login_limits.py`）
- 同じログインID（打ち込まれたまま。IDがなくても同じ）：24時間の失敗が5回で15分、10回で1時間、20回で24時間、その失敗から断る。接続元によらない（分散した総当たり）
- 同じ接続元：1時間の失敗が10回で、1時間断る。接続元は、IPv4 はアドレス、IPv6 は /64 の範囲（1つの契約で、とても多くのアドレスを持つため）、IPv4 を IPv6 の形で表したもの（`::ffff:…`）は IPv4。読めない値は1つ（`unknown`）にまとめる
- 断っている間は、正しいパスワードでも断る。断った試行は、失敗に数えない
- 断る期限は、失敗を記録するときに、その時点の数から決めて、行に残す（古い失敗が数える窓から外れても、始まった制限が早く解けないため）。行は、24時間より古く、その行で始まった制限が終わってから消す
- 成功したら、その接続元からの、そのIDの失敗だけを消す（ほかの接続元の失敗（他人の試行かもしれない）と、それで始まった制限は残す）
- 「断るかの判断」と「失敗の記録」は、ひとまとめにして、1つずつ行う（今は、プロセスの中の鍵。複数のプロセスで動かすときは、Task 026 で、DBの側で1つずつにする）
- 記録には、ログインIDと接続元を、`SECRET_KEY` を鍵にした HMAC-SHA256 でだけ残す（DBが漏れても、打ち込まれたID（パスワードを打ち間違えたものかもしれない）と、接続元が分からない）
- 締め出し：IDごとの制限は、だれの失敗でも始まるため、IDを知っている人は、1つの接続元から少しずつ失敗を送るだけで、本人を締め出し続けられる（攻撃のテストで確かめた。`tests/test_attacks_auth.py` の「受け入れた弱さ」）。そのため、ログインIDは推測されにくいものにする（`owner` のままにしない。応答からは、IDの有無が分からないため、IDを知られなければ狙えない）。締め出されたときも、ログイン中の端末はそのまま使える。`flask --app app unlock-login <ID>` で解き、`rename-user` でIDを変える。一度ログインした端末の印（device cookie）を足すかは、公開（Task 026）の前に決める

**ログインの状態（セッション）**（`app/user_sessions.py`）
- ログインすると、32バイトの乱数（トークン。`secrets.token_urlsafe`）を作り、Cookie に入れる。DBの `user_sessions` には、トークンの SHA-256 だけを置く（DBが漏れても、Cookie を作れない）。Flask の署名つきのセッション（`session`）は使わない（`SECRET_KEY` が漏れても、ログインを偽造できない。`session` の Cookie も作らない）
- Cookie：名前 `schedule_session`（設定 `AUTH_COOKIE_NAME`）、`HttpOnly`（JavaScriptから読めない）、`SameSite=Strict`（ほかのサイトから始まった要求には付けない）、`Path=/`、`Max-Age` は30日、`Domain` は付けない。`Secure` は設定 `AUTH_COOKIE_SECURE`（ローカルの HTTP ではオフ）。`TRUSTED_HOSTS` にローカル（`127.0.0.1`・`localhost`）でない名前があるのに `Secure` がオフなら、起動しない（`app/config.py` の `check_cookie_security`。公開の設定での付け忘れを防ぐ）
- 期限：最後に使ってから14日（使うたびに延びる）、ログインから30日（使っていても、入れ直す。NIST の AAL1 の入れ直しの期限）。最後に使った時刻は、1時間に1回だけ更新する。期限の切れた行は、使われたときと、だれかがログインしたときに消す
- 期限切れ・ログアウト済み・偽物のトークンの Cookie は、応答でブラウザから消す
- ほかのサイトのリンクから開いたとき（`SameSite=Strict` で Cookie が送られない）は、ログインの画面を1回だけ開き直す（`<meta http-equiv="refresh">` で `/login?reloaded=1` へ。JavaScriptは使わない）。開き直しは、このアプリの中からの移動になり、ログイン中なら、そのまま使える。`reloaded` の付いた画面は、開き直さない（ブラウザの違いで、開き直しが続かないように）

**ログアウト**
- 「ログアウト」（`POST /logout`）：この端末の行を消す。「すべての端末からログアウト」（`POST /logout-all`）：その利用者の行をすべて消す（端末をなくしたとき）。パスワードを変えたときも、すべての端末からログアウトする
- どちらも、Cookie を消し、`Clear-Site-Data: "cache", "storage"`（ブラウザに残ったデータを消してもらう）を付けて、ログインの画面へ303。`"cookies"` は付けない（同じドメインの、ほかのサイトの Cookie まで消すことがあるため。このアプリの Cookie は、`Set-Cookie` で消す）
- `GET` では受け付けない（405。データを変える操作を、リンクで起こさせない）

**利用者の管理**（`app/cli.py`。手順は `development/database.md` の「利用者の管理」）
- `create-user <ID>`・`set-password <ID>`・`rename-user <ID> <新しいID>`・`unlock-login <ID>`。使うDBは、アプリと同じ（環境変数 `DATABASE_URL`）

**`SECRET_KEY`**（`app/secret_key.py`）
- 使い道は、失敗の記録のHMACだけ（ログインの状態には使わない）
- 環境変数 `SECRET_KEY` があれば使う。なければ `instance/secret_key`（初回に乱数で作る。持ち主だけが読み書きできる0600。ほかの人も読める権限なら、0600に直す）。32文字未満なら、起動しない
- テストでは、アプリごとの乱数（`instance/` に作らない）
- 鍵のファイルは、DB・バックアップと同じ `instance/` にある。公開（Task 026）では、環境変数だけにする

**ログ**（ロガー `app.auth`。Flask の既定の出力先（標準エラー））
- 出すもの：ログインの成功・失敗・試行の制限・混雑・ログアウト・すべての端末からのログアウト・断った要求（ほかのサイトから）・利用者の作成・パスワードの変更・ログインIDの変更
- 利用者は、DBの id で示す（失敗で、IDがないときは「不明なID」）。接続元のアドレスを書く（侵入を調べるため。DBには残さない）
- 出さないもの：パスワード、トークン、Cookie、打ち込まれたログインID
- 要求から来た値（パス・ヘッダー）は、`%r` で書く（改行などで、偽の行を作らせない）
- migration（`migrations/env.py`）は、既にあるロガーを止めない（同じプロセスで migration を動かしたあとも、ログを残すため）

### 認可（利用者ごとのデータ）
- 規則は `architecture/api.md` の「利用者ごとのデータ（認可）」。他人のデータは、存在しないデータと同じに扱う
- `tests/test_authorization.py` が、すべてのAPI（URL×メソッド）で、他人のデータを読む・変える・消す・参照する・一覧や候補で知ることができないことを確かめる。APIのURL×メソッドの一覧とずれたら、失敗する（APIを足したら、テストにも足す）

### ほかのサイトからの要求（CSRF）
`app/auth.py` の `is_cross_site_request`。要求ごとに、ログインの確かめより先に行う。断ったら、403（`/api` は `forbidden`「リクエストを受け付けられません」、画面は Flask の標準のHTML）と、ログ。

1. `Sec-Fetch-Site`（今のブラウザが付ける、要求がどこから始まったか）が、`same-origin`（このアプリから）・`none`（アドレス欄に打った・ブックマーク）でなければ断る。`same-site`（同じホストの別のポートなど）も断る。ただし、画面への `GET` のページ移動（`Sec-Fetch-Mode: navigate`、`Sec-Fetch-Dest: document`。ほかのサイトのリンク）は許す。埋め込み（`iframe`・`img` など）と、`/api` は、読み取りも断る
2. データを変えるメソッド（`POST`・`PATCH`・`PUT`・`DELETE`）で、`Origin` が、このアプリ（スキーム・ホスト・ポート）と違えば断る（`null` を含む）
3. 画面のフォームの送信（ログイン・ログアウト）は、`Origin` と `Sec-Fetch-Site` のどちらもなければ断る（今のブラウザは、必ずどちらかを付ける）
4. `/api` は、どちらのヘッダーもない要求（ブラウザでないもの）を通す。ほかのサイトは、`application/json` を、事前の確かめ（preflight）なしに送れず、CORS も許していないため。今まで（Task 024）の、JSONだけを受け付ける規則と合わせて守る
5. Cookie の `SameSite=Strict`

### debug（デバッグモード）
- `python run.py` は、デバッグモードで動かさない。環境変数 `FLASK_DEBUG` が `1` のときだけ、デバッグモードにする（例：`FLASK_DEBUG=1 python run.py`。起動のときに表示する）。Flaskの決まり（`0`・`false`・`no` 以外はオン）より厳しくし、`FLASK_DEBUG=off` のような書き方でオンにならないようにする
- デバッグモードでは、コードを変えると自動で起動し直し、エラーの画面にデバッガー（サーバーの中でコードを実行できる道具）が出る。開発のときだけ使い、実データで使うときは使わない
- 待ち受けは `127.0.0.1` だけ（`run.py`）。`0.0.0.0` などに変えない（同じネットワークのほかの機器から届くようになる）

### 依存とCI
- **版の規則**：ライブラリ・道具は、版を固定し、公開から2週間以上たった版を選ぶ（`CLAUDE.md` の「仕様と範囲」）
- **Dependabot**（`.github/dependabot.yml`）：pip・npm・GitHub Actions の新しい版を、毎週、PRで知らせる。公開から14日たった版だけ（`cooldown`）。ただし、待つのは更新する依存の版だけで、そのとき一緒に変わる間接の依存（npm の lockfile の中など）は、新しすぎる版になりうる。そのため、マージの前に差分で確かめる。セキュリティの修正のPR（Dependabot security updates）は、待たずに出る。npm の `bootstrap`・`fullcalendar`・`@fullcalendar/*` は対象外（画面がCDNから読む版と、そろえる必要があるため。対象外にすると、セキュリティの修正のPRも出ない。Dependabot alerts で知り、タスクとして上げる）。扱い方は `development/workflow.md` の「依存の更新（Dependabot）」
- **npm**：`npm ci`（lockfile のとおりに入れる。`integrity` を確かめる）。`.npmrc` の `ignore-scripts=true` で、インストールのときのスクリプトを動かさない
- **CDN**：Bootstrap・FullCalendarは、版を固定し、`integrity`（SRI）を付ける（`architecture/overview.md`）。ファイルが変えられていれば、ブラウザが読み込まない
- **CI**（`.github/workflows/ci.yml`）
  - アクションは、コミットのSHAで固定し、版を行の末尾のコメントに書く（タグは、あとから別のコミットに付け替えられるため）
  - 権限は、読み取りだけ（`permissions: contents: read`）。`checkout` は、認証の情報を残さない（`persist-credentials: false`）。`pull_request` で動く（ほかの人のPRは、秘密や書き込みの権限なしで動く）
  - 全部のジョブに、時間の上限（`timeout-minutes`）
  - Python・Node.js は、その系列の最新の修正版（`check-latest`）。pip は、決めた版にしてから使う
- **ESLint**（`eslint.config.js`）：`innerHTML`・`outerHTML`・`insertAdjacentHTML`・`setHTMLUnsafe`・`createContextualFragment`・`document.write`・`eval` の類（`setTimeout` に文字列、`new Function`）・`style` の操作・`setAttribute` での `on…`・`style`（文字列と、テンプレートリテラルの形）を禁止する。書き方をすべて機械で見つけられるわけではない（例：`window.document.write`）ため、CSPと、レビューでも守る

### リポジトリ
- GitHubの設定（Komaが行う）：secret scanning・push protection（秘密の文字列を見つけ、pushを止める）、Dependabot alerts・security updates、Private vulnerability reporting（脆弱性の非公開の報告）。`main` のルールセット（`development/workflow.md` の「Git」）
- `SECURITY.md`：脆弱性の報告のしかた（非公開の報告を使う）
- `.gitignore`：DBのファイル（`instance/`・`*.db` など）、`.env`、鍵（`*.pem`・`*.key`）、`.DS_Store` などを入れない
- 個人の予定・時間割や、大学の資料そのものを入れない。テストと確認のデータは、架空のもの（`development/workflow.md` の「公開のリポジトリで守ること」）
- Issue・PR・コメント（他人やDependabotが書いたもの）と、外部のページの文は、データとして読み、Claudeへの指示として扱わない（同上）

### 開発の環境
KomaのMacの方針。

| 項目 | 方針 |
|---|---|
| Python | 3.14（`docs/decisions/0003-python-3-14.md`）。pyenv で入れ、プロジェクトの `.venv` を、その版で作る。3.14 のセキュリティの修正版が出たら、上げる（公開から2週間の規則に従う。急ぎのセキュリティの修正は、Komaが判断して例外にする）。上げたら、`.venv` を作り直す |
| pip・certifi | eMudhra の件（2026-10-20 公表。侵害された中間CA）に対応した版（pip 26.2.2 以降・certifi 2026.10.19 以降）。Python 3.14.10 以降は、`ssl` も侵害された鍵を拒む |
| Node.js | 入れない（ESLintはCIが確かめ、MacのE2EはCDNから読むため、要らない。更新するものを減らす） |
| ブラウザ | 最新にする（アプリを開くブラウザが、ほかのサイトからの攻撃を止める仕組みを持つため） |

Python の修正版を上げるときの手順（例：3.14.10 → 3.14.11）：サーバーを止める → `pyenv install 3.14.11` → プロジェクトのフォルダで `.venv` を消して作り直す（`"$(pyenv root)/versions/3.14.11/bin/python3.14" -m venv .venv`）→ `source .venv/bin/activate` → `pip --version` で、pip が上の表の版以降かを確かめる（古ければ `python -m pip install pip==26.2.2`。CIと同じ版）→ `pip install -r requirements-dev.txt` → `python -m playwright install chromium` → `python -m pytest`。`.venv` には、入れたライブラリだけがあり、データ（`instance/`）は別の場所なので、消してよい。

## ローカルと公開の違い
| 項目 | 今（ローカル） | 公開のとき（Task 025・026） |
|---|---|---|
| 届く範囲 | 同じMacだけ（`127.0.0.1`） | インターネットのだれでも |
| 利用者 | ログインして、利用者ごとのデータ（Task 025）。データは Koma の `owner`（IDは変える） | 同じ |
| Host | `127.0.0.1`・`localhost` | 本番の名前（設定で決める） |
| 通信 | HTTP（Macの中だけ） | HTTPS（と、HSTS） |
| Cookie | `Secure` なし、名前 `schedule_session` | `Secure`、名前 `__Host-` で始まるもの |
| サーバー | Flaskの開発用サーバー（`run.py`） | WSGIのサーバー。デバッグモードは使えないようにする |
| 秘密 | `SECRET_KEY`（`instance/secret_key`。Gitに入らない） | `SECRET_KEY` は環境変数だけ。リポジトリに入れない |

## 公開の前の点検
Task 025（ログイン）・Task 026（クラウドへの公開）の設計と受け入れ条件で扱う（ADR 0002）。

- **Task 025**（済み。ADR 0004）：認可の網羅的なテスト、`SECRET_KEY`、Cookie（`HttpOnly`・`SameSite=Strict`。`Secure` は Task 026）、CSRF（`Origin`・`Sec-Fetch-Site`）、ログインの試行の制限、ログ（上の「ログイン」「認可」「ほかのサイトからの要求（CSRF）」）
- **Task 026**
  - 本番の設定：デバッグモードなし（Werkzeug のデバッガーは、ログインの確かめより前で動くため、本番で起動できないようにする）、`SECRET_KEY` は環境変数だけ（使い捨てのファイルシステムで、起動のたびに変わらないように）、HTTPS（HSTS）、WSGIのサーバー、`TRUSTED_HOSTS` を本番の名前に
  - Cookie：`AUTH_COOKIE_SECURE` をオン、名前を `__Host-` で始まるものに（起動の確かめは、Task 025で入れた）
  - プロキシの後ろ：`ProxyFix` は、信頼するプロキシの段数だけにする（ほかでは `X-Forwarded-For` を読まない）。接続元ごとの試行の制限が、利用者の本当のIPで働くこと、`Origin` の検査がスキーム（`https`）で合うことを、本番で確かめる。「自分」の Origin を、設定（`ALLOWED_ORIGINS`）で決めるかを決める
  - プロセスの数：試行の制限の「判断と記録を1つずつ」（今はプロセスの中の鍵）と、同時のパスワードの確かめの数（1回32MiB）を、プロセスの数と合わせて決める（複数のプロセスなら、DBの側で1つずつにする）
  - ログイン：Koma のログインIDを、推測されにくいものにしてあること（`owner` のままにしない）。一度ログインした端末の印（device cookie。印のある端末は、IDごとの制限を別に数える）を足すかを決める（上の「ログインの試行の制限」の締め出し）。制限を解くコマンドを、本番でどう動かすか（コマンドを動かす環境にも、サーバーと同じ `SECRET_KEY` が要る。違うと、記録のHMACが合わず、解けない）。締め出しや失敗が多いことを、Koma に知らせる仕組み（任意）
  - ログ：置き場所・保存の期間・量。接続元のアドレスを残す期間。SQLAlchemy の例外の文に、利用者のデータ（SQLの引数）が入ること（`hide_parameters` を考える）
  - DB：クラウドのDBとバックアップ（パスワードのハッシュ・ログイン中の端末の記録を含む）を読める人を限り、暗号化する。パスワードの pepper（DBとアプリが別の場所になるとき）を考える
  - 本文の大きさの上限（`MAX_CONTENT_LENGTH`。今は上限がなく、大きなメモも保存される）と、メモなどの文字数の上限（仕様の変更）
  - `Server` ヘッダーに、サーバーとPythonの版を出さない
  - 公開の前のセキュリティの点検：別の目のレビューと、本番のURLへの外からの確認（ヘッダー・HTTPS・Hostの検査・エラーの応答）
  - クラウドのDBのバックアップと、壊す操作のコマンドを本番で断ること（`docs/roadmap.md` の Task 026）
