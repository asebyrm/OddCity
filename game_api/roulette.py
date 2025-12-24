import random
from flask import Blueprint, request, jsonify, session
from .database import get_db_connection
from .auth import login_required
from mysql.connector import Error

roulette_bp = Blueprint('roulette', __name__)

# Roulette Payouts
PAYOUTS = {
    'number': 35,  # Straight up
    'color': 1,    # Red/Black
    'parity': 1    # Odd/Even
}

# European Roulette Numbers (0-36)
# Red numbers: 1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34
RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34}

def get_color(number):
    if number == 0:
        return 'green'
    return 'red' if number in RED_NUMBERS else 'black'

def get_parity(number):
    if number == 0:
        return None
    return 'even' if number % 2 == 0 else 'odd'

@roulette_bp.route('/game/roulette/play', methods=['POST'])
@login_required
def play_roulette():
    user_id = session.get('user_id')
    data = request.get_json()

    if not data or 'amount' not in data or 'bet_type' not in data or 'bet_value' not in data:
        return jsonify({'message': 'Eksik veri! (amount, bet_type, bet_value)'}), 400

    try:
        amount = float(data['amount'])
        bet_type = data['bet_type']
        bet_value = data['bet_value']
    except ValueError:
        return jsonify({'message': 'Geçersiz veri formatı!'}), 400

    if amount <= 0:
        return jsonify({'message': 'Bahis miktarı 0\'dan büyük olmalıdır!'}), 400

    if bet_type not in PAYOUTS:
        return jsonify({'message': 'Geçersiz bahis türü!'}), 400

    # Validate bet_value based on bet_type
    if bet_type == 'number':
        try:
            bet_value = int(bet_value)
            if not (0 <= bet_value <= 36):
                raise ValueError
        except ValueError:
            return jsonify({'message': 'Geçersiz sayı! (0-36 arası olmalı)'}), 400
    elif bet_type == 'color':
        if bet_value not in ['red', 'black']:
            return jsonify({'message': 'Geçersiz renk! (red veya black)'}), 400
    elif bet_type == 'parity':
        if bet_value not in ['odd', 'even']:
            return jsonify({'message': 'Geçersiz tek/çift seçimi! (odd veya even)'}), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'message': 'Veritabanı hatası!'}), 500

        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)

        # Check balance
        cursor.execute("SELECT wallet_id, balance FROM wallets WHERE user_id = %s FOR UPDATE", (user_id,))
        wallet = cursor.fetchone()

        if not wallet:
            conn.rollback()
            return jsonify({'message': 'Cüzdan bulunamadı!'}), 404

        wallet_id = wallet['wallet_id']
        balance = float(wallet['balance'])

        if balance < amount:
            conn.rollback()
            return jsonify({'message': 'Yetersiz bakiye!'}), 400

        # Deduct bet amount
        cursor.execute("UPDATE wallets SET balance = balance - %s WHERE wallet_id = %s", (amount, wallet_id))
        cursor.execute("INSERT INTO transactions (user_id, wallet_id, amount, tx_type) VALUES (%s, %s, %s, 'BET')", (user_id, wallet_id, amount))

        # Play Roulette
        winning_number = random.randint(0, 36)
        winning_color = get_color(winning_number)
        winning_parity = get_parity(winning_number)

        is_win = False
        if bet_type == 'number':
            is_win = (bet_value == winning_number)
        elif bet_type == 'color':
            is_win = (bet_value == winning_color)
        elif bet_type == 'parity':
            is_win = (bet_value == winning_parity)

        payout = 0
        if is_win:
            multiplier = PAYOUTS[bet_type]
            # Original stake + profit
            payout = amount * (1 + multiplier)
            
            cursor.execute("UPDATE wallets SET balance = balance + %s WHERE wallet_id = %s", (payout, wallet_id))
            cursor.execute("INSERT INTO transactions (user_id, wallet_id, amount, tx_type) VALUES (%s, %s, %s, 'PAYOUT')", (user_id, wallet_id, payout))

        conn.commit()

        # Get new balance
        cursor.execute("SELECT balance FROM wallets WHERE wallet_id = %s", (wallet_id,))
        new_balance = float(cursor.fetchone()['balance'])

        return jsonify({
            'message': 'KAZANDINIZ!' if is_win else 'Kaybettiniz.',
            'winning_number': winning_number,
            'winning_color': winning_color,
            'is_win': is_win,
            'payout': payout,
            'new_balance': new_balance
        }), 200

    except Error as e:
        if conn: conn.rollback()
        print(f"Rulet hatası: {e}")
        return jsonify({'message': f'Bir hata oluştu: {e}'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
