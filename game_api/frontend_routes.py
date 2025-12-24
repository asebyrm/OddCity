import os
from flask import Blueprint, send_from_directory

# Frontend klasörünün mutlak yolunu bul
# Bu dosya: game_api/frontend_routes.py
# Frontend: game_api/../frontend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

frontend_bp = Blueprint('frontend', __name__, static_folder=FRONTEND_DIR, static_url_path='')

@frontend_bp.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@frontend_bp.route('/<path:path>')
def serve_static(path):
    return send_from_directory(FRONTEND_DIR, path)

# Admin Frontend Serving
ADMIN_FRONTEND_DIR = os.path.join(BASE_DIR, 'admin_frontend')

admin_fe_bp = Blueprint('admin_fe', __name__, static_folder=ADMIN_FRONTEND_DIR, static_url_path='/admin')

@admin_fe_bp.route('/admin/')
def admin_index():
    return send_from_directory(ADMIN_FRONTEND_DIR, 'index.html')

@admin_fe_bp.route('/admin/<path:path>')
def serve_admin_static(path):
    return send_from_directory(ADMIN_FRONTEND_DIR, path)
