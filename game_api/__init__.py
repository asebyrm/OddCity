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

    from .coinflip import coinflip_bp
    app.register_blueprint(coinflip_bp)

    from .roulette import roulette_bp
    app.register_blueprint(roulette_bp)

    from .blackjack import blackjack_bp
    app.register_blueprint(blackjack_bp)

    from .admin import admin_bp
    app.register_blueprint(admin_bp)

    from .database import init_db
    init_db()

    from .frontend_routes import frontend_bp, admin_fe_bp
    app.register_blueprint(admin_fe_bp)
    app.register_blueprint(frontend_bp)

    return app
