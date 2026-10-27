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
