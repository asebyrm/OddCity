import os

class Config:
    DB_CONFIG = {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'database': 'game_db'
    }

    SECRET_KEY = os.environ.get('SECRET_KEY', 'bu-hala-gizli-kalsa-iyi-olur-67890')
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = './flask_session_cache'
    SESSION_PERMANENT = True