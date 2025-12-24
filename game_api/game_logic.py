import random
from flask import jsonify, request, Blueprint, session
from .database import get_db_connection
from .auth import login_required
from mysql.connector import Error

game_bp = Blueprint('game', __name__)

PAYOUT_MULTIPLIER = 1.95

@game_bp.route('/game/play', methods=['POST'])
@login_required
def play_game():
    user_id = session.get('user_id')
    user_email = session.get('email')
    data = request.get_json()

    if not data or 'amount' not in data or 'choice' not in data:
        return jsonify({'message': 'Bahis (amount) ve seçim (choice) gereklidir!'}), 400

    try:
        bet_amount = float(data['amount'])
        choice = str(data['choice']).lower()
    except ValueError:
        return jsonify({'message': 'Bahis (amount) geçerli bir sayı olmalıdır!'}), 400

    if bet_amount <= 0:
        return jsonify({'message': 'Bahis sıfırdan büyük olmalıdır!'}), 400

    if choice not in ['yazi', 'tura']:
        return jsonify({'message': 'Seçim (choice) "yazi" veya "tura" olmalıdır!'}), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'message': 'Veritabanı sunucu hatası!'}), 500

        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)

        sql_get_wallet = "SELECT wallet_id, balance FROM wallets WHERE user_id = %s FOR UPDATE"
        cursor.execute(sql_get_wallet, (user_id,))
        wallet = cursor.fetchone()

        if not wallet:
            conn.rollback()
            return jsonify({'message': 'Cüzdan bulunamadı!'}), 404

        wallet_id = wallet['wallet_id']
        current_balance = float(wallet['balance'])

        if current_balance < bet_amount:
            conn.rollback()
            return jsonify({
                'message': 'Yetersiz bakiye!',
                'current_balance': current_balance,
                'bet_amount': bet_amount
            }), 403

        sql_debit = "UPDATE wallets SET balance = balance - %s WHERE wallet_id = %s"
        cursor.execute(sql_debit, (bet_amount, wallet_id))

        sql_log_bet = "INSERT INTO transactions (user_id, wallet_id, amount, tx_type) VALUES (%s, %s, %s, 'BET')"
        cursor.execute(sql_log_bet, (user_id, wallet_id, bet_amount))

        game_result = random.choice(['yazi', 'tura'])
        is_win = (choice == game_result)

        new_balance = 0.0

        if is_win:
            payout_amount = bet_amount * PAYOUT_MULTIPLIER

            sql_credit = "UPDATE wallets SET balance = balance + %s WHERE wallet_id = %s"
            cursor.execute(sql_credit, (payout_amount, wallet_id))

            sql_log_payout = "INSERT INTO transactions (user_id, wallet_id, amount, tx_type) VALUES (%s, %s, %s, 'PAYOUT')"
            cursor.execute(sql_log_payout, (user_id, wallet_id, payout_amount))

            conn.commit()

            cursor.execute("SELECT balance FROM wallets WHERE wallet_id = %s", (wallet_id,))
            new_balance = cursor.fetchone()['balance']

            return jsonify({
                'message': f'Tebrikler, KAZANDINIZ! ({payout_amount:.2f})',
                'your_choice': choice,
                'result': game_result,
                'new_balance': float(new_balance)
            }), 200

        else:
            conn.commit()

            cursor.execute("SELECT balance FROM wallets WHERE wallet_id = %s", (wallet_id,))
            new_balance = cursor.fetchone()['balance']

            return jsonify({
                'message': 'Kaybettiniz.',
                'your_choice': choice,
                'result': game_result,
                'new_balance': float(new_balance)
            }), 200

    except Error as e:
        if conn:
            conn.rollback()
        print(f"Bahis Oynama Hatası: {e}")
        return jsonify({'message': f'Kritik bir hata oluştu, işlem geri alındı: {e}'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()