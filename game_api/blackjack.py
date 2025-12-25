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


def save_game_state(cursor, game_id, deck, player_hand, dealer_hand, bet_amount, wallet_id):
    """Oyun durumunu veritabanına kaydet"""
    game_state = json.dumps({
        'deck': deck,
        'player_hand': player_hand,
        'dealer_hand': dealer_hand,
        'bet_amount': bet_amount,
        'wallet_id': wallet_id
    })
    cursor.execute("UPDATE games SET game_state = %s WHERE game_id = %s", (game_state, game_id))


def load_game_state(game_row):
    """Veritabanından oyun durumunu yükle"""
    if not game_row or not game_row.get('game_state'):
        return None
    
    try:
        state = json.loads(game_row['game_state']) if isinstance(game_row['game_state'], str) else game_row['game_state']
        return {
            'game_id': game_row['game_id'],
            'bet_id': game_row.get('bet_id'),
            'deck': state['deck'],
            'player_hand': state['player_hand'],
            'dealer_hand': state['dealer_hand'],
            'bet_amount': state['bet_amount'],
            'wallet_id': state['wallet_id'],
            'status': 'playing'
        }
    except (json.JSONDecodeError, KeyError):
        return None


def get_active_blackjack_game(cursor, user_id):
    """Kullanıcının aktif blackjack oyununu getir"""
    cursor.execute("""
        SELECT g.*, b.bet_id 
        FROM games g
        LEFT JOIN bets b ON g.game_id = b.game_id
        WHERE g.user_id = %s AND g.game_type = 'blackjack' AND g.status = 'ACTIVE'
        ORDER BY g.started_at DESC
        LIMIT 1
    """, (user_id,))
    return cursor.fetchone()


@blackjack_bp.route('/game/blackjack/active', methods=['GET'])
@login_required
def check_active_game():
    """Aktif blackjack oyunu var mı kontrol et"""
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabani hatasi'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        game_row = get_active_blackjack_game(cursor, user_id)
        
        if game_row:
            game_state = load_game_state(game_row)
            if game_state:
                player_value = calculate_hand_value(game_state['player_hand'])
                return jsonify({
                    'has_active_game': True,
                    'game_id': game_row['game_id'],
                    'bet_amount': game_state['bet_amount'],
                    'player_hand': game_state['player_hand'],
                    'dealer_card': game_state['dealer_hand'][0],
                    'player_value': player_value,
                    'started_at': game_row['started_at'].isoformat() if game_row['started_at'] else None
                })
        
        return jsonify({'has_active_game': False})
        
    finally:
        cursor.close()
        conn.close()


@blackjack_bp.route('/game/blackjack/resume', methods=['POST'])
@login_required
def resume_game():
    """Aktif oyunu devam ettir"""
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabani hatasi'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        game_row = get_active_blackjack_game(cursor, user_id)
        
        if not game_row:
            return jsonify({'message': 'Aktif oyun bulunamadi!'}), 404
        
        game_state = load_game_state(game_row)
        if not game_state:
            return jsonify({'message': 'Oyun durumu yuklenemedi!'}), 500
        
        # Session'a yükle
        game_state['bet_id'] = game_row['bet_id']
        session['bj_game'] = game_state
        
        player_value = calculate_hand_value(game_state['player_hand'])
        
        # Bakiye bilgisini al
        cursor.execute("SELECT balance FROM wallets WHERE wallet_id = %s", (game_state['wallet_id'],))
        wallet = cursor.fetchone()
        
        return jsonify({
            'message': 'Oyun devam ediyor',
            'player_hand': game_state['player_hand'],
            'dealer_card': game_state['dealer_hand'][0],
            'player_value': player_value,
            'status': 'playing',
            'new_balance': float(wallet['balance']) if wallet else 0
        })
        
    finally:
        cursor.close()
        conn.close()


@blackjack_bp.route('/game/blackjack/start', methods=['POST'])
@login_required
def start_game():
    user_id = session.get('user_id')
    data = request.get_json()
    
    if not data or 'amount' not in data:
        return jsonify({'message': 'Bahis miktari gereklidir!'}), 400
        
    try:
        amount = float(data['amount'])
        if amount <= 0: raise ValueError
    except ValueError:
        return jsonify({'message': 'Gecersiz bahis miktari!'}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({'message': 'Veritabani hatasi!'}), 500
        
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)
        
        # Aktif oyun kontrolü
        active_game = get_active_blackjack_game(cursor, user_id)
        if active_game:
            conn.rollback()
            return jsonify({
                'message': 'Zaten aktif bir oyununuz var!',
                'has_active_game': True,
                'game_id': active_game['game_id']
            }), 400
        
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
        
        # Initialize Game State
        deck = get_deck()
        random.shuffle(deck)
        
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]
        
        # Oyun durumunu veritabanına kaydet
        save_game_state(cursor, game_id, deck, player_hand, dealer_hand, amount, wallet_id)
        
        conn.commit()
        
        # Session'a da kaydet (performans için)
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
            return handle_game_end(game_id, bet_id, wallet_id, amount, player_hand, dealer_hand, True)
            
        return jsonify({
            'player_hand': player_hand,
            'dealer_card': dealer_hand[0],
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
    user_id = session.get('user_id')
    game = session.get('bj_game')
    
    # Session'da oyun yoksa veritabanından yükle
    if not game or game.get('status') != 'playing':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        game_row = get_active_blackjack_game(cursor, user_id)
        
        if game_row:
            game = load_game_state(game_row)
            if game:
                game['bet_id'] = game_row['bet_id']
                session['bj_game'] = game
        
        cursor.close()
        conn.close()
    
    if not game or game.get('status') != 'playing':
        return jsonify({'message': 'Aktif oyun yok!'}), 400
        
    deck = game['deck']
    player_hand = game['player_hand']
    
    # Deal card
    card = deck.pop()
    player_hand.append(card)
    
    player_value = calculate_hand_value(player_hand)
    
    # Oyun durumunu güncelle
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    save_game_state(cursor, game['game_id'], deck, player_hand, game['dealer_hand'], game['bet_amount'], game['wallet_id'])
    conn.commit()
    
    if player_value > 21:
        # Bust durumunda oyunu bitir
        game_id = game['game_id']
        bet_id = game['bet_id']
        
        # Rule snapshot oluştur
        create_rule_snapshot(game_id, get_active_rule_set_id(), 'blackjack')
        
        # Game sonucunu kaydet
        game_result_json = json.dumps({
            'player_hand': player_hand,
            'dealer_hand': game['dealer_hand'],
            'player_value': player_value,
            'result': 'bust',
            'payout': 0
        })
        cursor.execute("""
            UPDATE games 
            SET game_result = %s, game_state = NULL, ended_at = NOW(), status = 'COMPLETED'
            WHERE game_id = %s
        """, (game_result_json, game_id))
        
        # Payout kaydı oluştur (LOSS)
        cursor.execute("""
            INSERT INTO payouts (bet_id, win_amount, outcome)
            VALUES (%s, 0, 'LOSS')
        """, (bet_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        session.pop('bj_game', None)
        return jsonify({
            'player_hand': player_hand,
            'player_value': player_value,
            'dealer_hand': game['dealer_hand'],
            'dealer_value': calculate_hand_value(game['dealer_hand']),
            'status': 'bust',
            'message': 'Bust! Kaybettiniz.'
        })
    
    # Session'ı güncelle
    session['bj_game'] = game
    cursor.close()
    conn.close()
    
    return jsonify({
        'player_hand': player_hand,
        'player_value': player_value,
        'dealer_hand': game['dealer_hand'],
        'dealer_value': '?',
        'status': 'playing'
    })


@blackjack_bp.route('/game/blackjack/stand', methods=['POST'])
@login_required
def stand():
    user_id = session.get('user_id')
    game = session.get('bj_game')
    
    # Session'da oyun yoksa veritabanından yükle
    if not game or game.get('status') != 'playing':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        game_row = get_active_blackjack_game(cursor, user_id)
        
        if game_row:
            game = load_game_state(game_row)
            if game:
                game['bet_id'] = game_row['bet_id']
                session['bj_game'] = game
        
        cursor.close()
        conn.close()
    
    if not game or game.get('status') != 'playing':
        return jsonify({'message': 'Aktif oyun yok!'}), 400
    
    return handle_game_end(
        game['game_id'], 
        game['bet_id'], 
        game['wallet_id'], 
        game['bet_amount'], 
        game['player_hand'], 
        game['dealer_hand'],
        False
    )


def handle_game_end(game_id, bet_id, wallet_id, amount, player_hand, dealer_hand, is_blackjack=False):
    """Oyun bitişini işle"""
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        conn.start_transaction()
        
        deck = session.get('bj_game', {}).get('deck', get_deck())
        
        # Dealer draws
        while calculate_hand_value(dealer_hand) < 17:
            if deck:
                dealer_hand.append(deck.pop())
            else:
                break
        
        player_value = calculate_hand_value(player_hand)
        dealer_value = calculate_hand_value(dealer_hand)
        
        # Determine winner
        payout = 0
        result = ''
        message = ''
        
        if is_blackjack and player_value == 21 and len(player_hand) == 2:
            # Player has blackjack
            if dealer_value == 21 and len(dealer_hand) == 2:
                result = 'push'
                payout = amount
                message = 'Her iki taraf da Blackjack! Push.'
            else:
                result = 'blackjack'
                payout_multiplier = get_active_rule_value('blackjack_payout', DEFAULT_BLACKJACK_PAYOUT)
                payout = amount * payout_multiplier
                message = f'BLACKJACK! Kazandiniz! (+{payout:.2f})'
        elif dealer_value > 21:
            result = 'win'
            payout_multiplier = get_active_rule_value('blackjack_normal_payout', DEFAULT_NORMAL_PAYOUT)
            payout = amount * payout_multiplier
            message = f'Krupiye batti! Kazandiniz! (+{payout:.2f})'
        elif player_value > dealer_value:
            result = 'win'
            payout_multiplier = get_active_rule_value('blackjack_normal_payout', DEFAULT_NORMAL_PAYOUT)
            payout = amount * payout_multiplier
            message = f'Kazandiniz! (+{payout:.2f})'
        elif player_value < dealer_value:
            result = 'lose'
            payout = 0
            message = 'Kaybettiniz.'
        else:
            result = 'push'
            payout = amount
            message = 'Berabere! Bahis iade edildi.'
        
        # Rule snapshot
        create_rule_snapshot(game_id, get_active_rule_set_id(), 'blackjack')
        
        # Update balance if won
        if payout > 0:
            cursor.execute(
                "UPDATE wallets SET balance = balance + %s WHERE wallet_id = %s",
                (payout, wallet_id)
            )
        
        # Save game result
        game_result_json = json.dumps({
            'player_hand': player_hand,
            'dealer_hand': dealer_hand,
            'player_value': player_value,
            'dealer_value': dealer_value,
            'result': result,
            'payout': payout
        })
        
        cursor.execute("""
            UPDATE games 
            SET game_result = %s, game_state = NULL, ended_at = NOW(), status = 'COMPLETED'
            WHERE game_id = %s
        """, (game_result_json, game_id))
        
        # Create payout record
        outcome = 'WIN' if result in ['win', 'blackjack'] else 'LOSS'
        cursor.execute("""
            INSERT INTO payouts (bet_id, win_amount, outcome)
            VALUES (%s, %s, %s)
        """, (bet_id, payout, outcome))
        
        conn.commit()
        
        # Get new balance
        cursor.execute("SELECT balance FROM wallets WHERE wallet_id = %s", (wallet_id,))
        new_balance = float(cursor.fetchone()['balance'])
        
        # Clear session
        session.pop('bj_game', None)
        
        return jsonify({
            'player_hand': player_hand,
            'dealer_hand': dealer_hand,
            'player_value': player_value,
            'dealer_value': dealer_value,
            'result': result,
            'status': 'finished',
            'message': message,
            'payout': payout,
            'new_balance': new_balance
        })
        
    except Error as e:
        conn.rollback()
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()
