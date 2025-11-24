# game_api/__init__.py

from flask import Flask
from flask_session import Session
from .config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Flask-Session'ı başlat
    Session(app)

    # --- Blueprint'leri Kaydet (Modül Kaydı) ---

    # Auth (Kayıt, Giriş, Çıkış)
    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    # Cüzdan İşlemleri
    from .wallet import wallet_bp
    app.register_blueprint(wallet_bp)

    # Admin Kuralları
    from .rules import rules_bp
    app.register_blueprint(rules_bp)

    # Oyun Mantığı
    from .game_logic import game_bp
    app.register_blueprint(game_bp)

    return app