from flask import jsonify, request, Blueprint, session
from .database import get_db_connection
from .auth import login_required
from mysql.connector import Error

wallet_bp = Blueprint('wallet', __name__)

@wallet_bp.route('/wallets/me', methods=['GET'])
@login_required
def get_my_wallet():
    user_id = session.get('user_id')

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'message': 'Veritabanı sunucu hatası!'}), 500

        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT u.email, w.balance, w.currency, w.updated_at
            FROM wallets w
            JOIN users u ON w.user_id = u.user_id
            WHERE w.user_id = %s
        """
        cursor.execute(sql, (user_id,))
        wallet_info = cursor.fetchone()

        if not wallet_info:
            return jsonify({'message': 'Cüzdan bulunamadı!'}), 404

        wallet_info['balance'] = float(wallet_info['balance'])

        return jsonify({'wallet': wallet_info}), 200

    except Error as e:
        print(f"Cüzdan getirme hatası: {e}")
        return jsonify({'message': f'Bir hata oluştu: {e}'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@wallet_bp.route('/wallets/me/deposit', methods=['POST'])
@login_required
def deposit_to_wallet():
    user_id = session.get('user_id')
    user_email = session.get('email')

    data = request.get_json()
    if not data or 'amount' not in data:
        return jsonify({'message': 'Yatırılacak miktar (amount) gereklidir!'}), 400

    try:
        amount = float(data['amount'])
    except ValueError:
        return jsonify({'message': 'Miktar (amount) geçerli bir sayı olmalıdır!'}), 400

    if amount <= 0:
        return jsonify({'message': 'Miktar (amount) sıfırdan büyük olmalıdır!'}), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'message': 'Veritabanı sunucu hatası!'}), 500

        conn.start_transaction()

        cursor = conn.cursor(dictionary=True)

        sql_update_wallet = "UPDATE wallets SET balance = balance + %s WHERE user_id = %s"
        cursor.execute(sql_update_wallet, (amount, user_id))

        sql_get_wallet = "SELECT wallet_id, balance FROM wallets WHERE user_id = %s"
        cursor.execute(sql_get_wallet, (user_id,))
        wallet = cursor.fetchone()

        if not wallet:
            conn.rollback()
            return jsonify({'message': 'Kullanıcıya ait cüzdan bulunamadı!'}), 404

        wallet_id = wallet['wallet_id']
        new_balance = wallet['balance']

        sql_log_tx = "INSERT INTO transactions (wallet_id, amount, tx_type) VALUES (%s, %s, %s)"
        cursor.execute(sql_log_tx, (wallet_id, amount, 'DEPOSIT'))

        conn.commit()

        return jsonify({
            'message': f'Başarılı! {amount} VIRTUAL cüzdanınıza eklendi.',
            'user': user_email,
            'new_balance': float(new_balance)
        }), 200

    except Error as e:
        if conn:
            conn.rollback()
        print(f"Deposit hatası: {e}")
        return jsonify({'message': f'Bir hata oluştu: {e}'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@wallet_bp.route('/wallets/me/withdraw', methods=['POST'])
@login_required
def withdraw_from_wallet():
    user_id = session.get('user_id')
    user_email = session.get('email')

    data = request.get_json()
    if not data or 'amount' not in data:
        return jsonify({'message': 'Çeklecek miktar (amount) gereklidir!'}), 400

    try:
        amount = float(data['amount'])
    except ValueError:
        return jsonify({'message': 'Miktar (amount) geçerli bir sayı olmalıdır!'}), 400

    if amount <= 0:
        return jsonify({'message': 'Miktar (amount) sıfırdan büyük olmalıdır!'}), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'message': 'Veritabanı sunucu hatası!'}), 500

        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)

        sql_get_balance = "SELECT balance FROM wallets WHERE user_id = %s FOR UPDATE"
        cursor.execute(sql_get_balance, (user_id,))
        result = cursor.fetchone()

        if not result:
            conn.rollback()
            return jsonify({'message': 'Cüzdan bulunamadı!'}), 404

        balance = float(result['balance'])

        if balance < amount:
            conn.rollback()
            return jsonify({
                'message': 'Yetersiz bakiye!',
                'current_balance': balance,
                'withdraw_amount': amount
            }), 400

        sql_update_wallet = "UPDATE wallets SET balance = balance - %s WHERE user_id = %s"
        cursor.execute(sql_update_wallet, (amount, user_id))

        sql_get_wallet = "SELECT wallet_id, balance FROM wallets WHERE user_id = %s"
        cursor.execute(sql_get_wallet, (user_id,))
        wallet = cursor.fetchone()

        if not wallet:
            conn.rollback()
            return jsonify({'message': 'Kullanıcıya ait cüzdan bulunamadı!'}), 404

        wallet_id = wallet['wallet_id']
        new_balance = wallet['balance']

        sql_log_tx = "INSERT INTO transactions (wallet_id, amount, tx_type) VALUES (%s, %s, %s)"
        cursor.execute(sql_log_tx, (wallet_id, amount, 'WITHDRAW'))

        conn.commit()

        return jsonify({
            'message': f'Başarılı! {amount} VIRTUAL cüzdanınızdan çekildi.',
            'user': user_email,
            'new_balance': float(new_balance)
        }), 200

    except Error as e:
        if conn:
            conn.rollback()
        print(f"Para Çekme hatası: {e}")
        return jsonify({'message': f'Bir hata oluştu: {e}'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()