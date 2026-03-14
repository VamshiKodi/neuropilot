import os

from flask import Flask

from routes.api import api_bp
from routes.pages import pages_bp


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(32)

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=False,
    )