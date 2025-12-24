from flask import Blueprint, jsonify, request
from .database import get_db_connection
from .auth import admin_required
from mysql.connector import Error

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/users', methods=['GET'])
@admin_required
def list_users():
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı hatası'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT u.user_id, u.email, u.status, u.is_admin, u.created_at, w.balance, w.currency
            FROM users u
            LEFT JOIN wallets w ON u.user_id = w.user_id
            ORDER BY u.created_at DESC
        """
        cursor.execute(query)
        users = cursor.fetchall()
        return jsonify(users)
    except Error as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/admin/user/<int:user_id>/ban', methods=['POST'])
@admin_required
def ban_user(user_id):
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı hatası'}), 500
    
    cursor = conn.cursor()
    try:
        # Prevent banning self or other admins (optional, but good practice)
        cursor.execute("SELECT is_admin FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if user and user[0]:
             return jsonify({'message': 'Adminler yasaklanamaz!'}), 400

        cursor.execute("UPDATE users SET status = 'BANNED' WHERE user_id = %s", (user_id,))
        conn.commit()
        return jsonify({'message': 'Kullanıcı yasaklandı.'})
    except Error as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/admin/user/<int:user_id>/unban', methods=['POST'])
@admin_required
def unban_user(user_id):
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı hatası'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET status = 'ACTIVE' WHERE user_id = %s", (user_id,))
        conn.commit()
        return jsonify({'message': 'Kullanıcı yasağı kaldırıldı.'})
    except Error as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/admin/user/<int:user_id>/history', methods=['GET'])
@admin_required
def user_history(user_id):
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı hatası'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Get wallet id first
        cursor.execute("SELECT wallet_id FROM wallets WHERE user_id = %s", (user_id,))
        wallet = cursor.fetchone()
        if not wallet:
            return jsonify({'message': 'Cüzdan bulunamadı'}), 404
            
        wallet_id = wallet['wallet_id']
        
        # Get transactions
        query = """
            SELECT tx_id as transaction_id, amount, tx_type, created_at
            FROM transactions
            WHERE wallet_id = %s
            ORDER BY created_at DESC
            LIMIT 50
        """
        cursor.execute(query, (wallet_id,))
        history = cursor.fetchall()
        return jsonify(history)
    except Error as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()
