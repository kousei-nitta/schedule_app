import os
from collections.abc import Mapping

# 環境変数 DATABASE_URL がないときに使うDB。Flask-SQLAlchemyは、SQLiteの
# 相対パスを instance/ からのパスとして扱うため、instance/app.db になる
# （KomaのMacでは、実データのDB）。
DEFAULT_DATABASE_URI = "sqlite:///app.db"


def database_uri(environment: Mapping[str, str] = os.environ) -> str:
    """使うDBの接続先（SQLAlchemyの形のURL）を返す。

    環境変数 DATABASE_URL があれば、その値を使う（デモのDBや、将来の
    クラウドのDBに切り替えるため）。ない・空のときは、実データのDB。
    前後の空白は取り除く（コピーのときに入りやすく、空白つきの名前の
    ファイルができてしまうため）。テストで環境変数を差し替えられるように、
    引数で受け取れるようにする。
    """
    value = environment.get("DATABASE_URL", "").strip()
    return value or DEFAULT_DATABASE_URI


class Config:
    # アプリを起動したとき（create_app を引数なしで呼んだとき）の設定。
    # 環境変数は、このモジュールを読み込んだ時点の値を使う。
    SQLALCHEMY_DATABASE_URI = database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 受け付ける Host ヘッダー（ポートは見ない）。ほかの名前の要求は、
    # 400 にする。悪意のあるサイトが、自分の名前を 127.0.0.1 に向け直して
    # （DNSリバインディング）、このアプリのAPIを操作するのを防ぐため。
    # localhost は、テストの test_client の既定の名前でもある。
    # docs/architecture/security.md の「Hostヘッダーの検査」。
    TRUSTED_HOSTS = ["127.0.0.1", "localhost"]
    # ログインの Cookie（app/user_sessions.py）。Secure（HTTPSのときだけ
    # 送る）は、ローカル（HTTP）ではオフにする。公開のとき（Task 026）に、
    # オンにし、名前を __Host- で始まるものにする
    # （docs/architecture/security.md の「公開の前の点検」）。
    AUTH_COOKIE_NAME = "schedule_session"
    AUTH_COOKIE_SECURE = False


# Cookie の Secure をオフにしてよい Host（このMacの中だけ）
LOCAL_HOSTS = {"127.0.0.1", "localhost"}


def check_cookie_security(config: Mapping) -> None:
    """ローカルでないのに、Cookie の Secure がオフなら、起動しない。

    公開のとき（Task 026）に、TRUSTED_HOSTS だけを本番の名前にして、
    Secure を付け忘れると、ログインの Cookie が HTTP でも送られてしまう。
    その設定の誤りで、起動しないようにする（安全な側に倒す）。
    """
    hosts = set(config["TRUSTED_HOSTS"])
    if not config["AUTH_COOKIE_SECURE"] and not hosts <= LOCAL_HOSTS:
        raise RuntimeError(
            "TRUSTED_HOSTS に、このMacの外の名前があるのに、"
            "AUTH_COOKIE_SECURE がオフです（HTTPSで公開するときは、"
            "オンにしてください）"
        )
