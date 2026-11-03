"""アプリの設定。ローカル（Mac）と本番（クラウド）で、何が違うかを決める。

仕様は docs/architecture/security.md の「本番の設定」。
- ローカル：環境変数 APP_ENV がない。`127.0.0.1`・`localhost` だけで動き、
  Cookie の Secure はオフ、実データのDBは instance/app.db
- 本番：APP_ENV=production。下の必須の設定がすべてあり、形が正しいとき
  だけ起動する（足りない・おかしいときは、Web もコマンドも起動しない）

設定は、create_app を呼んだ時点の環境変数から読む
（settings_from_environment）。本番の環境変数は、0600 の設定のファイルに
まとめてもよい（SCHEDULE_ENV_FILE。Web の入口と SSH のコマンドが、同じ
ファイルを読むため。app/env_file.py）。
"""
import re
from collections.abc import Mapping
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from app.secret_key import SecretKeyError, check_secret_key

# リポジトリ（このプロジェクトのフォルダ）。本番のDBは、この外に置く
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 環境変数 DATABASE_URL がないときに使うDB（ローカルだけ）。
# Flask-SQLAlchemyは、SQLiteの相対パスを instance/ からのパスとして扱う
# ため、instance/app.db になる（KomaのMacでは、実データのDB）。
DEFAULT_DATABASE_URI = "sqlite:///app.db"

PRODUCTION = "production"

# ローカルの Cookie の名前。本番は __Host- を付ける（下の production_settings）
LOCAL_AUTH_COOKIE_NAME = "schedule_session"
LOCAL_DEVICE_COOKIE_NAME = "schedule_device"
# __Host- で始まる名前の Cookie は、ブラウザが、Secure・Path=/・Domain なし
# のときだけ受け付ける（ほかのサブドメインから、同じ名前の Cookie を
# 置かれない）
HOST_COOKIE_PREFIX = "__Host-"

# すべての要求の本文の大きさの上限（バイト）。いちばん大きい正しい要求
# （メモ2,000字×3バイトほど）より十分に大きく、大きな本文を読ませて
# メモリーを使わせない大きさ。超えたら413。ログインは、もっと小さい上限
# （app/routes/auth.py）
MAX_CONTENT_LENGTH = 64 * 1024

# 本番の PUBLIC_ORIGIN の形：https:// と、点を含むホストの名前だけ
# （英小文字・数字・-。パス・ポート・末尾の / を付けない）
PUBLIC_ORIGIN_PATTERN = re.compile(
    r"https://"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+"
)
# 接続元のヘッダーの名前の形（英数字と -）。REMOTE_ADDR は、ヘッダーで
# なく、サーバーが渡す接続元そのものを使う、という意味
HEADER_NAME_PATTERN = re.compile(r"[A-Za-z0-9-]{1,64}")
REMOTE_ADDR = "REMOTE_ADDR"


class ConfigError(RuntimeError):
    """設定が足りない・おかしい（起動しない）。理由を日本語の文で持つ。"""


class Config:
    """ローカルと本番で共通の設定と、ローカルの既定値。"""

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # SQLの例外の文に、SQLの引数（予定の名前・メモなど、利用者のデータ）を
    # 入れない（エラーのログから、データが漏れないため）
    SQLALCHEMY_ENGINE_OPTIONS = {"hide_parameters": True}
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH
    # 本番かどうか（APP_ENV=production のときだけ True）
    PRODUCTION = False
    # 本番の、このアプリの Origin（例：https://example.alwaysdata.net）。
    # ローカルでは None（要求の Host から決める）
    PUBLIC_ORIGIN = None
    # 本番で、接続元を読むヘッダー（app/proxy.py）。ローカルでは None
    CLIENT_ADDRESS_HEADER = None
    # 受け付ける Host ヘッダー（ポートは見ない）。ほかの名前の要求は、
    # 400 にする。悪意のあるサイトが、自分の名前を 127.0.0.1 に向け直して
    # （DNSリバインディング）、このアプリのAPIを操作するのを防ぐため。
    # localhost は、テストの test_client の既定の名前でもある。
    # docs/architecture/security.md の「Hostヘッダーの検査」。
    TRUSTED_HOSTS = ["127.0.0.1", "localhost"]
    # ログインの Cookie（app/user_sessions.py）と、端末の印の Cookie
    # （app/trusted_devices.py）。Secure（HTTPSのときだけ送る）は、
    # ローカル（HTTP）ではオフ
    AUTH_COOKIE_NAME = LOCAL_AUTH_COOKIE_NAME
    DEVICE_COOKIE_NAME = LOCAL_DEVICE_COOKIE_NAME
    AUTH_COOKIE_SECURE = False


def database_uri(environment: Mapping[str, str]) -> str:
    """ローカルで使うDBの接続先（SQLAlchemyの形のURL）を返す。

    環境変数 DATABASE_URL があれば、その値を使う（デモのDBなどに切り替える
    ため）。ない・空のときは、実データのDB。前後の空白は取り除く（コピーの
    ときに入りやすく、空白つきの名前のファイルができてしまうため）。
    """
    value = environment.get("DATABASE_URL", "").strip()
    return value or DEFAULT_DATABASE_URI


def public_origin(value: str) -> str:
    """本番の PUBLIC_ORIGIN を確かめて返す。"""
    if not value:
        raise ConfigError(
            "本番（APP_ENV=production）では、PUBLIC_ORIGIN が必要です"
            "（例：https://example.alwaysdata.net）"
        )
    if PUBLIC_ORIGIN_PATTERN.fullmatch(value) is None:
        raise ConfigError(
            "PUBLIC_ORIGIN は、https:// と、ホストの名前だけにしてください"
            "（英小文字。パス・ポート・末尾の / を付けない。"
            "例：https://example.alwaysdata.net）"
        )
    return value


def production_database_uri(value: str) -> str:
    """本番の DATABASE_URL を確かめて返す。

    SQLite のファイルの絶対パスで、リポジトリの外にあること（リポジトリの
    中だと、git の操作（git clean など）で消えうるため。Web から読める
    場所に置かないため）。
    """
    if not value:
        raise ConfigError(
            "本番では、DATABASE_URL が必要です"
            "（例：sqlite:////home/<アカウント>/data/app.db）"
        )
    try:
        url = make_url(value)
    except ArgumentError as error:
        raise ConfigError("DATABASE_URL の形が違います") from error
    if url.get_backend_name() != "sqlite" or url.query:
        raise ConfigError(
            "本番の DATABASE_URL は、SQLite のファイル"
            "（sqlite:////絶対パス）にしてください"
        )
    path_text = url.database or ""
    if path_text in ("", ":memory:") or not Path(path_text).is_absolute():
        raise ConfigError(
            "本番の DATABASE_URL は、絶対パスにしてください"
            "（sqlite:////home/... のように、/ を4つ）"
        )
    if Path(path_text).resolve().is_relative_to(PROJECT_ROOT):
        raise ConfigError(
            "本番のDBは、リポジトリのフォルダの外に置いてください"
        )
    return value


def client_address_header(value: str) -> str:
    """本番の CLIENT_ADDRESS_HEADER を確かめて返す。"""
    if not value:
        raise ConfigError(
            "本番では、CLIENT_ADDRESS_HEADER が必要です（プロキシが必ず"
            "上書きすると、下見で確かめたヘッダーの名前。例：X-Real-IP。"
            "docs/development/deploy.md）"
        )
    if value != REMOTE_ADDR and HEADER_NAME_PATTERN.fullmatch(value) is None:
        raise ConfigError(
            "CLIENT_ADDRESS_HEADER は、ヘッダーの名前（英数字と -）か、"
            "REMOTE_ADDR にしてください"
        )
    return value


def production_settings(environment: Mapping[str, str]) -> dict:
    """本番の設定を、環境変数から決める（おかしければ ConfigError）。"""
    origin = public_origin(environment.get("PUBLIC_ORIGIN", "").strip())
    try:
        secret_key = check_secret_key(
            environment.get("SECRET_KEY", "").strip(), "環境変数"
        )
    except SecretKeyError as error:
        raise ConfigError(
            "本番では、32文字以上の SECRET_KEY が必要です"
            "（instance/ のファイルは使いません）"
        ) from error
    return {
        "PRODUCTION": True,
        "PUBLIC_ORIGIN": origin,
        "TRUSTED_HOSTS": [origin.removeprefix("https://")],
        "AUTH_COOKIE_NAME": HOST_COOKIE_PREFIX + LOCAL_AUTH_COOKIE_NAME,
        "DEVICE_COOKIE_NAME": HOST_COOKIE_PREFIX + LOCAL_DEVICE_COOKIE_NAME,
        "AUTH_COOKIE_SECURE": True,
        "SECRET_KEY": secret_key,
        "SQLALCHEMY_DATABASE_URI": production_database_uri(
            environment.get("DATABASE_URL", "").strip()
        ),
        "CLIENT_ADDRESS_HEADER": client_address_header(
            environment.get("CLIENT_ADDRESS_HEADER", "").strip()
        ),
    }


def settings_from_environment(environment: Mapping[str, str]) -> dict:
    """環境変数から、ローカルか本番かを決め、その設定を返す。

    APP_ENV は、ない（ローカル）か production（本番）だけ。ほかの値は、
    書き間違いのまま、黙ってローカルの扱いにならないよう、起動しない。
    """
    app_env = environment.get("APP_ENV", "").strip()
    if app_env == PRODUCTION:
        return production_settings(environment)
    if app_env:
        raise ConfigError(
            "APP_ENV に指定できるのは production だけです"
            f"（{app_env!r}）"
        )
    if environment.get("PUBLIC_ORIGIN", "").strip():
        raise ConfigError(
            "PUBLIC_ORIGIN があるのに、APP_ENV=production がありません"
        )
    return {"SQLALCHEMY_DATABASE_URI": database_uri(environment)}


# Cookie の Secure をオフにしてよい Host（このMacの中だけ）
LOCAL_HOSTS = {"127.0.0.1", "localhost"}


def check_security_settings(config: Mapping) -> None:
    """Host・Cookie・本番の設定が危ないときは、起動しない（安全な側に倒す）。

    - TRUSTED_HOSTS が空・None：Flask は Host を確かめなくなる（DNS
      リバインディングを防げない）
    - ローカルでない名前があるのに、Cookie の Secure がオフ：ログインの
      Cookie が HTTP でも送られてしまう
    - 本番なのに、本番から決まるはずの値と違う（テストや手で設定を
      上書きしたとき）
    """
    if not config.get("TRUSTED_HOSTS"):
        raise ConfigError(
            "TRUSTED_HOSTS が空です（受け付ける Host の名前を決めてください）"
        )
    hosts = set(config["TRUSTED_HOSTS"])
    if not config["AUTH_COOKIE_SECURE"] and not hosts <= LOCAL_HOSTS:
        raise ConfigError(
            "TRUSTED_HOSTS に、このMacの外の名前があるのに、"
            "AUTH_COOKIE_SECURE がオフです（HTTPSで公開するときは、"
            "オンにしてください）"
        )
    if not config.get("PRODUCTION"):
        return
    origin = config.get("PUBLIC_ORIGIN") or ""
    if (
        PUBLIC_ORIGIN_PATTERN.fullmatch(origin) is None
        or config["TRUSTED_HOSTS"] != [origin.removeprefix("https://")]
        or not config["AUTH_COOKIE_SECURE"]
        or not config["AUTH_COOKIE_NAME"].startswith(HOST_COOKIE_PREFIX)
        or not config["DEVICE_COOKIE_NAME"].startswith(HOST_COOKIE_PREFIX)
        or not config.get("CLIENT_ADDRESS_HEADER")
    ):
        raise ConfigError(
            "本番の設定が、PUBLIC_ORIGIN から決まる値と合いません"
            "（Host・Cookie・接続元のヘッダー）"
        )
