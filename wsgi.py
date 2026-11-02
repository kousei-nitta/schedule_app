"""本番（ホストの uWSGI）が読み込む、このアプリの入口。

uWSGI は、このファイルの application を、WSGI のアプリとして動かす。
設定は、環境変数（と、SCHEDULE_ENV_FILE の設定のファイル）から読む
（app/config.py・app/env_file.py。手順は docs/development/deploy.md）。
ローカルでは使わない（python run.py）。
"""
from app import create_app

application = create_app()
