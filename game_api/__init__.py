from flask import Flask
from flask_session import Session
from flask_cors import CORS
from .config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, supports_credentials=True, origins=["file://", "http://localhost:*", "http://127.0.0.1:*"])

    Session(app)

    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    from .wallet import wallet_bp
    app.register_blueprint(wallet_bp)

    from .rules import rules_bp
    app.register_blueprint(rules_bp)

    from .game_logic import game_bp
    app.register_blueprint(game_bp)

    return app