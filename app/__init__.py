import os
from flask import Flask

from app.db import init_db

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(PROJECT_ROOT, "templates"),
        static_folder=os.path.join(PROJECT_ROOT, "static"),
    )
    app.secret_key = "gift-pool-dev-secret"  # fine for this assessment; not for real production
    init_db()

    from app.routes import bp
    app.register_blueprint(bp)

    return app
