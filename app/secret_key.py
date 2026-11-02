"""秘密の鍵（SECRET_KEY）を決める。

使い道：ログインの失敗の記録で、ログインIDと接続元を、鍵つきのハッシュ
（HMAC）にする（app/login_limits.py）。鍵がないと、DBが漏れたときに、
総当たりで元の値が分かってしまう（IPv4のアドレスは約43億通りしかない）。
ログインの状態（Cookie）は、この鍵を使わない（app/user_sessions.py）。

決め方（docs/architecture/security.md の「SECRET_KEY」）：
1. 環境変数 SECRET_KEY があれば、それを使う（クラウドでは、これにする）
2. なければ、instance/secret_key のファイル。なければ、乱数で作る
   （持ち主だけが読み書きできる 0600）。Gitには入らない（instance/）
どちらも、32文字未満なら、起動しない（推測されやすい鍵を使わないため）。
"""
import os
import secrets
import stat
from collections.abc import Mapping
from pathlib import Path

MIN_SECRET_KEY_LENGTH = 32
SECRET_KEY_FILE_NAME = "secret_key"


class SecretKeyError(Exception):
    """秘密の鍵を決められない（短い・読めない）。"""


def check_secret_key(value: str, source: str) -> str:
    """鍵が十分に長いかを確かめて、そのまま返す。"""
    if len(value) < MIN_SECRET_KEY_LENGTH:
        raise SecretKeyError(
            f"{source} の SECRET_KEY が短すぎます"
            f"（{MIN_SECRET_KEY_LENGTH}文字以上にしてください。例："
            "python -c 'import secrets; print(secrets.token_hex(32))'）"
        )
    return value


def create_secret_key_file(path: Path) -> None:
    """乱数の鍵のファイルを、持ち主だけが読み書きできる権限で作る。

    O_EXCL：同じ名前のファイルがあれば、作らずに失敗する（ほかの処理が
    同時に作った鍵を、上書きしないため）。
    """
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        file.write(secrets.token_hex(32))


def load_secret_key(
    instance_path: str,
    environment: Mapping[str, str] = os.environ,
) -> str:
    """環境変数か、instance/secret_key から、秘密の鍵を読む。"""
    value = environment.get("SECRET_KEY", "").strip()
    if value:
        return check_secret_key(value, "環境変数")

    path = Path(instance_path) / SECRET_KEY_FILE_NAME
    try:
        create_secret_key_file(path)
    except FileExistsError:
        # すでにある（2回目からの起動）。下で読む
        pass
    # ほかの人も読める権限なら、持ち主だけにする（コピーで権限が
    # 変わった場合など）
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        path.chmod(0o600)
    value = path.read_text(encoding="utf-8").strip()
    return check_secret_key(value, str(path))
