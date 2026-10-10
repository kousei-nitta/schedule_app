import os
from typing import Any

from flask import Flask

from app.api_helpers import register_api_error_handlers
from app.config import Config
from app.extensions import db, migrate


def create_app(test_config: dict[str, Any] | None = None):
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
        os.makedirs(app.instance_path, exist_ok=True)
    else:
        app.config.update(test_config)

    db.init_app(app)

    # モデルをSQLAlchemyに登録するための読み込み。migrationがテーブルを
    # 見つけるために必要なので、名前は使わなくても削除しない。
    from app import models

    migrate.init_app(app, db, render_as_batch=True)

    from app.routes.main import main as main_blueprint

    app.register_blueprint(main_blueprint)

    register_api_error_handlers(app)

    from app.routes.semesters import semesters_bp

    app.register_blueprint(semesters_bp)

    from app.routes.subjects import subjects_bp

    app.register_blueprint(subjects_bp)
    return app
