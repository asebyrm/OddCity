import os
from datetime import timedelta

class Config:
    DB_CONFIG = {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'database': 'game_db'
    }

    # Environment
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    IS_PRODUCTION = FLASK_ENV == 'production'

    # Secret Key
    # Production'da mutlaka environment variable olarak set edilmeli
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        if IS_PRODUCTION:
            raise RuntimeError("SECRET_KEY must be set in production!")
        else:
            # Development için varsayılan key (sadece geliştirme amaçlı)
            SECRET_KEY = 'dev-secret-key-do-not-use-in-production'
            import warnings
            warnings.warn("Using default SECRET_KEY - set SECRET_KEY env var for production!")

    # Session Configuration
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = os.path.join(os.path.dirname(__file__), 'flask_session_cache')
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)  # 2 saat oturum süresi

    # Cookie Security
    SESSION_COOKIE_HTTPONLY = True   # JavaScript'in cookie'ye erişimini engeller (XSS koruması)
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF koruması
    SESSION_COOKIE_SECURE = IS_PRODUCTION  # Production'da True (HTTPS gerektirir)