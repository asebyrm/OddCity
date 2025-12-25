import os

class Config:
    DB_CONFIG = {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'database': 'game_db'
    }

    # Secret Key - Production'da mutlaka environment variable olarak set edilmeli
    SECRET_KEY = os.environ.get('SECRET_KEY', 'bu-hala-gizli-kalsa-iyi-olur-67890')
    if SECRET_KEY == 'bu-hala-gizli-kalsa-iyi-olur-67890' and os.environ.get('FLASK_ENV') != 'development':
        import warnings
        warnings.warn("WARNING: Using default SECRET_KEY! Set SECRET_KEY environment variable for production!")
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = './flask_session_cache'
    SESSION_PERMANENT = True