"""本番（ホストの uWSGI）が読み込む、このアプリの入口。

uWSGI は、このファイルの application を、WSGI のアプリとして動かす。
設定は、環境変数（と、SCHEDULE_ENV_FILE の設定のファイル）から読む
（app/config.py・app/env_file.py。手順は docs/development/deploy.md）。
ローカルでは使わない（python run.py）。
"""
import os

from app import create_app
from app.config import PRODUCTION, ConfigError
from app.env_file import environment_with_env_file

# 本番の設定（APP_ENV=production）が読めないまま、ローカルの扱い（Secure の
# ない Cookie・HSTS なし・接続元の層なし・リポジトリの中のDB）で起動しない。
# サイトの設定で SCHEDULE_ENV_FILE を付け忘れたときに、すぐ気づけるように、
# アプリを作る前（instance/ にファイルを作る前）に止める
if environment_with_env_file(os.environ).get("APP_ENV") != PRODUCTION:
    raise ConfigError(
        "wsgi.py は本番の入口です。本番の設定（APP_ENV=production）が"
        "ありません。サイトの環境変数 SCHEDULE_ENV_FILE を確かめてください"
        "（docs/development/deploy.md）"
    )

application = create_app()
