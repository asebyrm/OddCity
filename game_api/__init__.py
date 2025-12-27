from flask import Flask, jsonify
from flask_session import Session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flasgger import Swagger

from .config import Config

# Global limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(
        app,
        supports_credentials=True,
        origins=["file://", "http://localhost:*", "http://127.0.0.1:*"]
    )

    # ======================
    # Session
    # ======================
    Session(app)

    # ======================
    # Swagger (Flasgger)
    # ======================
    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "Casino Game API",
            "description": "Session-based authentication + CSRF protected API",
            "version": "1.0.0"
        },
        "securityDefinitions": {
            "sessionAuth": {
                "type": "apiKey",
                "in": "cookie",
                "name": "session"
            }
        }
    }

    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/apidocs/",
    }

    Swagger(app, template=swagger_template, config=swagger_config)

    # ======================
    # Rate Limiter
    # ======================
    limiter.init_app(app)

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            'message': 'Çok fazla istek gönderdiniz. Lütfen biraz bekleyin.',
            'error': 'rate_limit_exceeded',
            'retry_after': e.description
        }), 429

    # ======================
    # Blueprints
    # ======================
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

    # ======================
    # DB Init
    # ======================
    from .database import init_db
    init_db()

    # ======================
    # Frontend Routes
    # ======================
    from .frontend_routes import frontend_bp, admin_fe_bp
    app.register_blueprint(admin_fe_bp)
    app.register_blueprint(frontend_bp)

    return app
