import random
import json
from flask import Blueprint, request, jsonify, session
from .database import get_db_connection
from .auth import login_required
from .rules import get_active_rule_value, get_active_rule_set_id, create_rule_snapshot
from mysql.connector import Error

blackjack_bp = Blueprint('blackjack', __name__)

# Varsayılan Blackjack payouts (rule system'de kural yoksa kullanılır)
DEFAULT_BLACKJACK_PAYOUT = 2.5  # 3:2 payout
DEFAULT_NORMAL_PAYOUT = 2.0     # Normal win

# Card values
SUITS = ['H', 'D', 'C', 'S'] # Hearts, Diamonds, Clubs, Spades
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

def get_deck():
    return [{'suit': s, 'rank': r} for s in SUITS for r in RANKS]

def calculate_hand_value(hand):
    value = 0
    aces = 0
    for card in hand:
        rank = card['rank']
        if rank in ['J', 'Q', 'K']:
            value += 10
        elif rank == 'A':
            aces += 1
            value += 11
        else:
            value += int(rank)
    
    while value > 21 and aces:
        value -= 10
        aces -= 1
    
    return value

@blackjack_bp.route('/game/blackjack/start', methods=['POST'])
@login_required
def start_game():
    user_id = session.get('user_id')
    data = request.get_json()
    
    if not data or 'amount' not in data:
        return jsonify({'message': 'Bahis miktarı gereklidir!'}), 400
        
    try:
        amount = float(data['amount'])
        if amount <= 0: raise ValueError
    except ValueError:
        return jsonify({'message': 'Geçersiz bahis miktarı!'}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({'message': 'Veritabanı hatası!'}), 500
        
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)
        
        # Check balance
        cursor.execute("SELECT wallet_id, balance FROM wallets WHERE user_id = %s FOR UPDATE", (user_id,))
        wallet = cursor.fetchone()
        
        if not wallet or float(wallet['balance']) < amount:
            conn.rollback()
            return jsonify({'message': 'Yetersiz bakiye!'}), 400
            
        wallet_id = wallet['wallet_id']
        
        # Aktif rule set ID'sini al
        rule_set_id = get_active_rule_set_id()
        
        # Game kaydı oluştur
        sql_create_game = """
            INSERT INTO games (user_id, rule_set_id, game_type, status)
            VALUES (%s, %s, 'blackjack', 'ACTIVE')
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
        cursor.execute(sql_create_bet, (game_id, user_id, 'blackjack', str(amount), amount))
        bet_id = cursor.lastrowid
        
        conn.commit()
        
        # Initialize Game State
        deck = get_deck()
        random.shuffle(deck)
        
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()] # Second card hidden in frontend
        
        session['bj_game'] = {
            'game_id': game_id,
            'bet_id': bet_id,
            'deck': deck,
            'player_hand': player_hand,
            'dealer_hand': dealer_hand,
            'bet_amount': amount,
            'wallet_id': wallet_id,
            'status': 'playing'
        }
        
        player_value = calculate_hand_value(player_hand)
        
        # Check for immediate Blackjack
        if player_value == 21:
            return stand_logic(conn, cursor, game_id, bet_id, wallet_id, amount, player_hand, dealer_hand, True)
            
        return jsonify({
            'player_hand': player_hand,
            'dealer_card': dealer_hand[0], # Show only first card
            'player_value': player_value,
            'status': 'playing',
            'new_balance': float(wallet['balance']) - amount
        })

    except Error as e:
        if conn: conn.rollback()
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@blackjack_bp.route('/game/blackjack/hit', methods=['POST'])
@login_required
def hit():
    game = session.get('bj_game')
    if not game or game['status'] != 'playing':
        return jsonify({'message': 'Aktif oyun yok!'}), 400
        
    deck = game['deck']
    player_hand = game['player_hand']
    
    # Deal card
    card = deck.pop()
    player_hand.append(card)
    
    player_value = calculate_hand_value(player_hand)
    
    if player_value > 21:
        # Bust durumunda oyunu bitir
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        game_id = game['game_id']
        bet_id = game['bet_id']
        
        # Rule snapshot oluştur (oyun oynandığında kullanılan rule değerlerini kaydet)
        create_rule_snapshot(game_id, get_active_rule_set_id(), 'blackjack')
        
        # Game sonucunu kaydet
        game_result_json = json.dumps({
            'player_hand': player_hand,
            'player_value': player_value,
            'result': 'bust',
            'payout': 0
        })
        sql_update_game = """
            UPDATE games 
            SET game_result = %s, ended_at = NOW(), status = 'COMPLETED'
            WHERE game_id = %s
        """
        cursor.execute(sql_update_game, (game_result_json, game_id))
        
        # Payout kaydı oluştur (LOSS)
        sql_create_payout = """
            INSERT INTO payouts (bet_id, win_amount, outcome)
            VALUES (%s, 0, 'LOSS')
        """
        cursor.execute(sql_create_payout, (bet_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        game['status'] = 'finished'
        session.pop('bj_game', None)
        return jsonify({
            'player_hand': player_hand,
            'player_value': player_value,
            'status': 'bust',
            'message': 'Bust! Kaybettiniz.'
        })
        
    session['bj_game'] = game
    return jsonify({
        'player_hand': player_hand,
        'player_value': player_value,
        'status': 'playing'
    })

@blackjack_bp.route('/game/blackjack/stand', methods=['POST'])
@login_required
def stand():
    game = session.get('bj_game')
    if not game or game['status'] != 'playing':
        return jsonify({'message': 'Aktif oyun yok!'}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    return stand_logic(conn, cursor, game['game_id'], game['bet_id'], game['wallet_id'], game['bet_amount'], game['player_hand'], game['dealer_hand'])

def stand_logic(conn, cursor, game_id, bet_id, wallet_id, amount, player_hand, dealer_hand, is_blackjack=False):
    user_id = session.get('user_id')
    deck = session['bj_game']['deck']
    dealer_value = calculate_hand_value(dealer_hand)
    
    # Dealer plays
    while dealer_value < 17:
        card = deck.pop()
        dealer_hand.append(card)
        dealer_value = calculate_hand_value(dealer_hand)
        
    player_value = calculate_hand_value(player_hand)
    
    payout = 0
    result = 'lose'
    message = 'Kaybettiniz.'
    
    # Database'den payout multiplier'ları al
    blackjack_multiplier = get_active_rule_value('blackjack_payout', DEFAULT_BLACKJACK_PAYOUT)
    normal_multiplier = get_active_rule_value('blackjack_normal_payout', DEFAULT_NORMAL_PAYOUT)
    
    if is_blackjack:
        # Check if dealer also has blackjack
        if dealer_value == 21 and len(dealer_hand) == 2:
            payout = amount # Push
            result = 'push'
            message = 'Berabere (Push)!'
        else:
            payout = amount * blackjack_multiplier
            result = 'win'
            message = 'Blackjack! Kazandınız!'
    elif dealer_value > 21:
        payout = amount * normal_multiplier
        result = 'win'
        message = 'Krupiye Battı! Kazandınız!'
    elif dealer_value > player_value:
        result = 'lose'
        message = 'Krupiye Kazandı.'
    elif dealer_value < player_value:
        payout = amount * normal_multiplier
        result = 'win'
        message = 'Kazandınız!'
    else:
        payout = amount
        result = 'push'
        message = 'Berabere (Push)!'
        
    # Rule snapshot oluştur (oyun oynandığında kullanılan rule değerlerini kaydet)
    create_rule_snapshot(game_id, get_active_rule_set_id(), 'blackjack')
    
    # Game sonucunu kaydet
    game_result_json = json.dumps({
        'player_hand': player_hand,
        'dealer_hand': dealer_hand,
        'player_value': player_value,
        'dealer_value': dealer_value,
        'result': result,
        'payout': payout
    })
    sql_update_game = """
        UPDATE games 
        SET game_result = %s, ended_at = NOW(), status = 'COMPLETED'
        WHERE game_id = %s
    """
    cursor.execute(sql_update_game, (game_result_json, game_id))
    
    # Payout kaydı oluştur
    # PUSH durumunda outcome = 'LOSS' ama win_amount = payout (stake geri verilir)
    outcome = 'WIN' if result == 'win' else 'LOSS'
    sql_create_payout = """
        INSERT INTO payouts (bet_id, win_amount, outcome)
        VALUES (%s, %s, %s)
    """
    cursor.execute(sql_create_payout, (bet_id, payout, outcome))
    
    if payout > 0:
        cursor.execute("UPDATE wallets SET balance = balance + %s WHERE wallet_id = %s", (payout, wallet_id))
    
    conn.commit()
    
    cursor.execute("SELECT balance FROM wallets WHERE wallet_id = %s", (wallet_id,))
    new_balance = float(cursor.fetchone()['balance'])
    
    session.pop('bj_game', None)
    cursor.close()
    conn.close()
    
    return jsonify({
        'player_hand': player_hand,
        'dealer_hand': dealer_hand,
        'player_value': player_value,
        'dealer_value': dealer_value,
        'status': 'finished',
        'result': result,
        'message': message,
        'payout': payout,
        'new_balance': new_balance
    })
