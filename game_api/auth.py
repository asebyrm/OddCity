from functools import wraps
from flask import jsonify, request, session, Blueprint
from werkzeug.security import generate_password_hash, check_password_hash
from .database import get_db_connection
from mysql.connector import Error

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'message': 'Bu işlemi yapmak için giriş yapmalısınız.'}), 401
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'message': 'Bu işlemi yapmak için admin yetkisi gerekli!'}), 403
        return f(*args, **kwargs)

    return decorated_function


@auth_bp.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'message': 'E-posta ve şifre gereklidir!'}), 400
    email = data['email']
    password = data['password']
    hashed_password = generate_password_hash(password)
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({'message': 'Veritabanı sunucu hatası!'}), 500
        cursor = conn.cursor()
        sql_insert_user = "INSERT INTO users (email, password_hash) VALUES (%s, %s)"
        user_val = (email, hashed_password)
        cursor.execute(sql_insert_user, user_val)
        new_user_id = cursor.lastrowid
        sql_insert_wallet = "INSERT INTO wallets (user_id) VALUES (%s)"
        cursor.execute(sql_insert_wallet, (new_user_id,))
        conn.commit()
        return jsonify({'message': 'Kullanıcı ve cüzdanı başarıyla oluşturuldu!', 'user_id': new_user_id}), 201
    except Error as e:
        if e.errno == 1062: return jsonify({'message': 'Bu e-posta adresi zaten kullanılıyor.'}), 409
        print(f"Kayıt hatası: {e}")
        return jsonify({'message': f'Bir hata oluştu: {e}'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@auth_bp.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'message': 'E-posta ve şifre gereklidir!'}), 400
    email = data['email']
    password = data['password']
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({'message': 'Veritabanı sunucu hatası!'}), 500
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT user_id, email, password_hash, is_admin, status FROM users WHERE email = %s"
        cursor.execute(sql, (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            if user['status'] == 'BANNED':
                return jsonify({'message': 'Hesabınız yasaklanmıştır.'}), 403

            session['user_id'] = user['user_id']
            session['email'] = user['email']
            session['is_admin'] = user['is_admin']
            return jsonify({
                'message': 'Giriş başarılı! Sunucu sizi hatırlayacak.',
                'is_admin': bool(user['is_admin'])
            }), 200
        else:
            return jsonify({'message': 'Geçersiz e-posta veya şifre!'}), 401
    except Error as e:
        print(f"Giriş hatası: {e}")
        return jsonify({'message': f'Bir hata oluştu: {e}'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout_user():
    session.clear()
    return jsonify({'message': 'Başarıyla çıkış yapıldı.'}), 200
