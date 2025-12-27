import random
import json
from flask import Blueprint, request, jsonify, session
from .database import get_db_connection
from .auth import login_required
from .rules import get_active_rule_value, get_active_rule_set_id
from .utils.csrf import csrf_required
from mysql.connector import Error

roulette_bp = Blueprint('roulette', __name__)

# Rate limiter
def get_limiter():
    from . import limiter
    return limiter

# Varsayılan Roulette Payouts (rule system'de kural yoksa kullanılır)
DEFAULT_PAYOUTS = {
    'number': 35,  # Straight up
    'color': 1,    # Red/Black
    'parity': 1    # Odd/Even
}

# European Roulette Numbers (0-36)
# Red numbers: 1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36
RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

def get_color(number):
    if number == 0:
        return 'green'
    return 'red' if number in RED_NUMBERS else 'black'

def get_parity(number):
    if number == 0:
        return None
    return 'even' if number % 2 == 0 else 'odd'

@roulette_bp.route('/game/roulette/play', methods=['POST'])
@get_limiter().limit("60 per minute")  # Dakikada 60 oyun
@login_required
@csrf_required
def play_roulette():
    """
    Play a roulette game

    ---
    tags:
      - Games
    summary: Play Roulette
    description: |
      Places a bet on European roulette (numbers 0-36).
      Bet types: number (straight up), color (red/black), parity (odd/even).
      Payouts are based on active rule set.
    security:
      - session: []
      - csrf: []
    consumes:
      - application/json
    parameters:
      - in: header
        name: X-CSRF-Token
        type: string
        required: true
        description: CSRF token
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - amount
            - bet_type
            - bet_value
          properties:
            amount:
              type: number
              format: float
              minimum: 0.01
              example: 10.00
              description: Bet amount
            bet_type:
              type: string
              enum: [number, color, parity]
              example: color
              description: Type of bet
            bet_value:
              type: string
              example: red
              description: |
                Bet value based on bet_type:
                - number: 0-36
                - color: red, black
                - parity: odd, even
            csrf_token:
              type: string
              description: Alternative way to provide CSRF token
    responses:
      200:
        description: Game completed
        schema:
          type: object
          properties:
            message:
              type: string
              example: "YOU WON!"
            winning_number:
              type: integer
              example: 7
            winning_color:
              type: string
              example: red
            is_win:
              type: boolean
              example: true
            payout:
              type: number
              example: 20.00
            new_balance:
              type: number
              example: 520.00
      400:
        description: Invalid bet type, value, or insufficient balance
      401:
        description: Not authenticated
      403:
        description: Invalid CSRF token
      404:
        description: Wallet not found
    """
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

    if bet_type not in DEFAULT_PAYOUTS:
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

        # Aktif rule set ID'sini al
        rule_set_id = get_active_rule_set_id()
        
        # Game kaydı oluştur
        sql_create_game = """
            INSERT INTO games (user_id, rule_set_id, game_type, status)
            VALUES (%s, %s, 'roulette', 'ACTIVE')
        """
        cursor.execute(sql_create_game, (user_id, rule_set_id))
        game_id = cursor.lastrowid

        # Bakiye düş
        cursor.execute("UPDATE wallets SET balance = balance - %s WHERE wallet_id = %s", (amount, wallet_id))
        
        # Bet kaydı oluştur
        sql_create_bet = """
            INSERT INTO bets (game_id, user_id, bet_type, bet_value, stake_amount)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql_create_bet, (game_id, user_id, bet_type, str(bet_value), amount))
        bet_id = cursor.lastrowid

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
        
        # Game sonucunu kaydet
        game_result_json = json.dumps({
            'winning_number': winning_number,
            'winning_color': winning_color,
            'winning_parity': winning_parity,
            'bet_type': bet_type,
            'bet_value': str(bet_value),
            'is_win': is_win
        })
        sql_update_game = """
            UPDATE games 
            SET game_result = %s, ended_at = NOW(), status = 'COMPLETED'
            WHERE game_id = %s
        """
        cursor.execute(sql_update_game, (game_result_json, game_id))
        
        payout = 0
        if is_win:
            # Database'den payout multiplier'ı al
            rule_key = f'roulette_{bet_type}_payout'
            multiplier = get_active_rule_value(rule_key, DEFAULT_PAYOUTS[bet_type])
            # Original stake + profit
            payout = amount * (1 + multiplier)
            
            # Bakiye ekle
            cursor.execute("UPDATE wallets SET balance = balance + %s WHERE wallet_id = %s", (payout, wallet_id))
            
            # Payout kaydı oluştur
            sql_create_payout = """
                INSERT INTO payouts (bet_id, win_amount, outcome)
                VALUES (%s, %s, 'WIN')
            """
            cursor.execute(sql_create_payout, (bet_id, payout))
        else:
            # Kayıp durumunda payout kaydı oluştur
            sql_create_payout = """
                INSERT INTO payouts (bet_id, win_amount, outcome)
                VALUES (%s, 0, 'LOSS')
            """
            cursor.execute(sql_create_payout, (bet_id,))

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
