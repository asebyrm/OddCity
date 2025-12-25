import random
import json
from flask import jsonify, request, Blueprint, session
from .database import get_db_connection
from .auth import login_required
from .rules import get_active_rule_value, get_active_rule_set_id, create_rule_snapshot
from mysql.connector import Error

coinflip_bp = Blueprint('coinflip', __name__)

# Varsayılan payout multiplier (rule system'de kural yoksa kullanılır)
DEFAULT_PAYOUT_MULTIPLIER = 1.95

@coinflip_bp.route('/game/coinflip/play', methods=['POST'])
@login_required
def play_coinflip():
    """Yazı-Tura oyunu"""
    user_id = session.get('user_id')
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

        # Aktif rule set ID'sini al
        rule_set_id = get_active_rule_set_id()
        
        # Game kaydı oluştur
        sql_create_game = """
            INSERT INTO games (user_id, rule_set_id, game_type, status)
            VALUES (%s, %s, 'coinflip', 'ACTIVE')
        """
        cursor.execute(sql_create_game, (user_id, rule_set_id))
        game_id = cursor.lastrowid
        
        # Bakiye düş
        sql_debit = "UPDATE wallets SET balance = balance - %s WHERE wallet_id = %s"
        cursor.execute(sql_debit, (bet_amount, wallet_id))

        # Bet kaydı oluştur
        sql_create_bet = """
            INSERT INTO bets (game_id, user_id, bet_type, bet_value, stake_amount)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql_create_bet, (game_id, user_id, 'choice', choice, bet_amount))
        bet_id = cursor.lastrowid

        game_result = random.choice(['yazi', 'tura'])
        is_win = (choice == game_result)

        new_balance = 0.0

        # Rule snapshot oluştur (oyun oynandığında kullanılan rule değerlerini kaydet)
        create_rule_snapshot(game_id, rule_set_id, 'coinflip')
        
        # Game sonucunu kaydet
        game_result_json = json.dumps({'result': game_result, 'choice': choice, 'is_win': is_win})
        sql_update_game = """
            UPDATE games 
            SET game_result = %s, ended_at = NOW(), status = 'COMPLETED'
            WHERE game_id = %s
        """
        cursor.execute(sql_update_game, (game_result_json, game_id))
        
        if is_win:
            # Database'den payout multiplier'ı al, yoksa varsayılan değeri kullan
            payout_multiplier = get_active_rule_value('coinflip_payout', DEFAULT_PAYOUT_MULTIPLIER)
            payout_amount = bet_amount * payout_multiplier

            # Bakiye ekle
            sql_credit = "UPDATE wallets SET balance = balance + %s WHERE wallet_id = %s"
            cursor.execute(sql_credit, (payout_amount, wallet_id))

            # Payout kaydı oluştur
            sql_create_payout = """
                INSERT INTO payouts (bet_id, win_amount, outcome)
                VALUES (%s, %s, 'WIN')
            """
            cursor.execute(sql_create_payout, (bet_id, payout_amount))

            conn.commit()

            cursor.execute("SELECT balance FROM wallets WHERE wallet_id = %s", (wallet_id,))
            new_balance = cursor.fetchone()['balance']

            return jsonify({
                'message': f'Tebrikler, KAZANDINIZ! ({payout_amount:.2f})',
                'your_choice': choice,
                'result': game_result,
                'is_win': True,
                'payout': payout_amount,
                'new_balance': float(new_balance)
            }), 200

        else:
            # Kayıp durumunda payout kaydı oluştur (win_amount = 0)
            sql_create_payout = """
                INSERT INTO payouts (bet_id, win_amount, outcome)
                VALUES (%s, 0, 'LOSS')
            """
            cursor.execute(sql_create_payout, (bet_id,))
            
            conn.commit()

            cursor.execute("SELECT balance FROM wallets WHERE wallet_id = %s", (wallet_id,))
            new_balance = cursor.fetchone()['balance']

            return jsonify({
                'message': 'Kaybettiniz.',
                'your_choice': choice,
                'result': game_result,
                'is_win': False,
                'payout': 0,
                'new_balance': float(new_balance)
            }), 200

    except Error as e:
        if conn:
            conn.rollback()
        print(f"Coinflip Hatasi: {e}")
        return jsonify({'message': 'Oyun sırasında bir hata oluştu. İşlem geri alındı.'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# Eski endpoint'i koruyalım (geriye dönük uyumluluk için)
@coinflip_bp.route('/game/play', methods=['POST'])
@login_required
def play_game_legacy():
    """Eski endpoint - geriye dönük uyumluluk için"""
    return play_coinflip()

