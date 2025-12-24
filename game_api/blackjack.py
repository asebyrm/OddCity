import random
from flask import Blueprint, request, jsonify, session
from .database import get_db_connection
from .auth import login_required
from mysql.connector import Error

blackjack_bp = Blueprint('blackjack', __name__)

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
        
        # Deduct bet
        cursor.execute("UPDATE wallets SET balance = balance - %s WHERE wallet_id = %s", (amount, wallet_id))
        cursor.execute("INSERT INTO transactions (wallet_id, amount, tx_type) VALUES (%s, %s, 'BET')", (wallet_id, amount))
        
        conn.commit()
        
        # Initialize Game State
        deck = get_deck()
        random.shuffle(deck)
        
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()] # Second card hidden in frontend
        
        session['bj_game'] = {
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
            return stand_logic(conn, cursor, wallet_id, amount, player_hand, dealer_hand, True)
            
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
        game['status'] = 'finished'
        session['bj_game'] = game
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
    
    return stand_logic(conn, cursor, game['wallet_id'], game['bet_amount'], game['player_hand'], game['dealer_hand'])

def stand_logic(conn, cursor, wallet_id, amount, player_hand, dealer_hand, is_blackjack=False):
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
    
    if is_blackjack:
        # Check if dealer also has blackjack
        if dealer_value == 21 and len(dealer_hand) == 2:
            payout = amount # Push
            result = 'push'
            message = 'Berabere (Push)!'
        else:
            payout = amount * 2.5 # 3:2 payout
            result = 'win'
            message = 'Blackjack! Kazandınız!'
    elif dealer_value > 21:
        payout = amount * 2
        result = 'win'
        message = 'Krupiye Battı! Kazandınız!'
    elif dealer_value > player_value:
        result = 'lose'
        message = 'Krupiye Kazandı.'
    elif dealer_value < player_value:
        payout = amount * 2
        result = 'win'
        message = 'Kazandınız!'
    else:
        payout = amount
        result = 'push'
        message = 'Berabere (Push)!'
        
    if payout > 0:
        cursor.execute("UPDATE wallets SET balance = balance + %s WHERE wallet_id = %s", (payout, wallet_id))
        cursor.execute("INSERT INTO transactions (wallet_id, amount, tx_type) VALUES (%s, %s, 'PAYOUT')", (wallet_id, payout))
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
