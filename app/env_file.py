"""本番の設定のファイル（環境変数を、1つのファイルにまとめたもの）を読む。

本番では、サイト（uWSGI。WSGI の入口 wsgi.py）と、SSH で動かすコマンド
（flask --app app ...）が、同じ設定を使う必要がある。片方だけに設定が
あると、たとえば unlock-login が別の鍵で照らし合わせて、制限が解けない。
そこで、設定を1つのファイルにまとめ、そのパスを環境変数 SCHEDULE_ENV_FILE
で渡す（サイトの設定と、SSH の ~/.profile の両方に、パスだけを書く）。

ファイルの形（1行に1つ。# で始まる行と空の行は読み飛ばす）：
    APP_ENV=production
    PUBLIC_ORIGIN=https://example.alwaysdata.net
    ...
- 持ち主だけが読み書きできる（0600）、自分のファイルでなければ読まない
  （秘密の鍵を含むため）
- 書ける名前は、下の ALLOWED_NAMES だけ（書き間違いに気づくため）
- 同じ名前が、環境変数にもあれば、読まない（どちらが使われるか、
  分からなくなるため）
エラーの文に、ファイルの中身（秘密の鍵など）を入れない。
"""
import os
import stat
from collections.abc import Mapping
from pathlib import Path

from app.config import ConfigError

ENV_FILE_VARIABLE = "SCHEDULE_ENV_FILE"
ALLOWED_NAMES = {
    "APP_ENV",
    "PUBLIC_ORIGIN",
    "SECRET_KEY",
    "DATABASE_URL",
    "CLIENT_ADDRESS_HEADER",
}


def read_env_file(path: Path) -> dict[str, str]:
    """設定のファイルを読み、名前と値の組を返す。"""
    try:
        file_stat = path.stat()
    except OSError as error:
        raise ConfigError(f"設定のファイルが読めません：{path}") from error
    if not stat.S_ISREG(file_stat.st_mode):
        raise ConfigError(
            f"設定のファイルが、ふつうのファイルでありません：{path}"
        )
    if file_stat.st_uid != os.getuid():
        raise ConfigError(
            f"設定のファイルの持ち主が、自分ではありません：{path}"
        )
    if stat.S_IMODE(file_stat.st_mode) & 0o077:
        raise ConfigError(
            f"設定のファイルを、持ち主だけが読める権限にしてください"
            f"（chmod 600 {path}）"
        )

    values: dict[str, str] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, start=1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        name, separator, value = text.partition("=")
        name = name.strip()
        if not separator or name not in ALLOWED_NAMES:
            # 値（秘密かもしれない）は、エラーの文に入れない
            raise ConfigError(
                f"設定のファイルの {line_number} 行目が読めません"
                f"（書ける名前：{'・'.join(sorted(ALLOWED_NAMES))}）"
            )
        if name in values:
            raise ConfigError(
                f"設定のファイルに、{name} が2回あります"
            )
        values[name] = value.strip()
    return values


def environment_with_env_file(
    environment: Mapping[str, str],
) -> dict[str, str]:
    """環境変数に、設定のファイル（あれば）の値を足したものを返す。"""
    merged = dict(environment)
    path_text = environment.get(ENV_FILE_VARIABLE, "").strip()
    if not path_text:
        return merged
    for name, value in read_env_file(Path(path_text)).items():
        if environment.get(name, "").strip():
            raise ConfigError(
                f"{name} が、環境変数と設定のファイルの両方にあります"
                "（どちらか1つにしてください）"
            )
        merged[name] = value
    return merged
