import os
import secrets
from typing import Any

from flask import Flask

from app.api_helpers import register_api_error_handlers
from app.auth import register_auth
from app.config import (
    Config,
    check_security_settings,
    settings_from_environment,
)
from app.env_file import environment_with_env_file
from app.extensions import db, migrate
from app.production import prepare_production
from app.proxy import PublicProxyMiddleware
from app.secret_key import load_secret_key
from app.security import register_security_headers


def create_app(test_config: dict[str, Any] | None = None):
    """アプリを作る。

    test_config がないとき（ふだんの起動・コマンド）は、この時点の環境変数
    （と、本番の設定のファイル）から、ローカルか本番かを決める
    （app/config.py）。テストは、test_config で設定を渡す。
    """
    if (
        test_config is not None
        and "SQLALCHEMY_DATABASE_URI" not in test_config
    ):
        raise ValueError(
            "テスト設定にはSQLALCHEMY_DATABASE_URIが必要です"
        )

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config is None:
        environment = environment_with_env_file(os.environ)
        app.config.update(settings_from_environment(environment))
        if not app.config["PRODUCTION"]:
            os.makedirs(app.instance_path, exist_ok=True)
            # 秘密の鍵：環境変数 SECRET_KEY、なければ instance/secret_key
            # （app/secret_key.py）。本番は、環境変数だけ（上で読んだ）
            app.config["SECRET_KEY"] = load_secret_key(
                app.instance_path, environment
            )
    else:
        # テストでは、instance/ に鍵のファイルを作らない（指定がなければ、
        # アプリごとの乱数）
        app.config["SECRET_KEY"] = secrets.token_hex(32)
        app.config.update(test_config)

    # Host・Cookie・本番の設定が危なければ、起動しない
    check_security_settings(app.config)
    if app.config["PRODUCTION"]:
        prepare_production(app)
        # プロキシの後ろで、接続元とスキームを決める（app/proxy.py）
        app.wsgi_app = PublicProxyMiddleware(
            app.wsgi_app, app.config["CLIENT_ADDRESS_HEADER"]
        )

    db.init_app(app)

    # モデルをSQLAlchemyに登録するための読み込み。migrationがテーブルを
    # 見つけるために必要なので、名前は使わなくても削除しない。
    from app import models  # noqa: F401

    migrate.init_app(app, db, render_as_batch=True)

    from app.routes.main import main as main_blueprint

    app.register_blueprint(main_blueprint)

    register_api_error_handlers(app)

    # すべての応答に、セキュリティのヘッダー（CSPを含む）を付ける
    register_security_headers(app)

    # ほかのサイトからの要求の拒否と、ログインの確かめ（既定で拒否）。
    # ログインの画面と静的ファイルのほかは、ログインが要る（app/auth.py）
    register_auth(app)

    from app.routes.auth import auth_bp

    app.register_blueprint(auth_bp)

    from app.routes.semesters import semesters_bp

    app.register_blueprint(semesters_bp)

    from app.routes.subjects import subjects_bp

    app.register_blueprint(subjects_bp)

    from app.routes.closures import closures_bp

    app.register_blueprint(closures_bp)

    from app.routes.events import events_bp

    app.register_blueprint(events_bp)

    from app.routes.tasks import tasks_bp

    app.register_blueprint(tasks_bp)

    # 自作のコマンド（flask --app app backup-db など）
    from app.cli import register_commands

    register_commands(app)
    return app
