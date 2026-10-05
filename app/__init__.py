import os

from flask import Flask

from app.config import Config
from app.extensions import db, migrate


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)

    from app import models

    migrate.init_app(app, db, render_as_batch=True)

    from app.routes.main import main as main_blueprint

    app.register_blueprint(main_blueprint)
    return app
