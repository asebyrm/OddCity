import random
import json
from flask import Blueprint, request, jsonify, session
from .database import get_db_connection
from .auth import login_required
from .rules import get_active_rule_value, get_active_rule_set_id
from .utils.csrf import csrf_required
from mysql.connector import Error

blackjack_bp = Blueprint('blackjack', __name__)

# Rate limiter
def get_limiter():
    from . import limiter
    return limiter

# Default Blackjack payouts (used if no rule in rule system)
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
    """Save game state to database"""
    game_state = json.dumps({
        'deck': deck,
        'player_hand': player_hand,
        'dealer_hand': dealer_hand,
        'bet_amount': bet_amount,
        'wallet_id': wallet_id
    })
    cursor.execute("UPDATE games SET game_state = %s WHERE game_id = %s", (game_state, game_id))


def load_game_state(game_row):
    """Load game state from database"""
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
    """
    Check for active blackjack game

    ---
    tags:
      - Games
    summary: Check active blackjack game
    description: Checks if the user has an active (unfinished) blackjack game.
    security:
      - session: []
    responses:
      200:
        description: Active game status
        schema:
          type: object
          properties:
            has_active_game:
              type: boolean
              example: true
            game_id:
              type: integer
              example: 123
            bet_amount:
              type: number
              example: 50.00
            player_hand:
              type: array
              items:
                type: object
                properties:
                  suit:
                    type: string
                    example: H
                  rank:
                    type: string
                    example: K
            dealer_card:
              type: object
              properties:
                suit:
                  type: string
                  example: S
                rank:
                  type: string
                  example: A
            player_value:
              type: integer
              example: 18
            started_at:
              type: string
              format: date-time
      401:
        description: Not authenticated
    """
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Database error'}), 500
    
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
@csrf_required
def resume_game():
    """
    Resume an active blackjack game

    ---
    tags:
      - Games
    summary: Resume blackjack game
    description: |
      Resumes an interrupted blackjack game.
      Loads the game state from the database.
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
        required: false
        schema:
          type: object
          properties:
            csrf_token:
              type: string
    responses:
      200:
        description: Game resumed successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Game continues
            player_hand:
              type: array
              items:
                type: object
            dealer_card:
              type: object
            player_value:
              type: integer
              example: 18
            status:
              type: string
              example: playing
            new_balance:
              type: number
              example: 450.00
      401:
        description: Not authenticated
      403:
        description: Invalid CSRF token
      404:
        description: No active game found
    """
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Database error'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        game_row = get_active_blackjack_game(cursor, user_id)
        
        if not game_row:
            return jsonify({'message': 'No active game found!'}), 404
        
        game_state = load_game_state(game_row)
        if not game_state:
            # Orphaned game - clean it up and tell user to start new game
            cursor.execute("""
                UPDATE games SET status = 'CANCELLED', ended_at = NOW() 
                WHERE game_id = %s
            """, (game_row['game_id'],))
            conn.commit()
            return jsonify({
                'message': 'Game state corrupted. Game cancelled. Please start a new game.',
                'has_active_game': False
            }), 404
        
        # Load into session
        game_state['bet_id'] = game_row['bet_id']
        session['bj_game'] = game_state
        
        player_value = calculate_hand_value(game_state['player_hand'])
        
        # Get balance info
        cursor.execute("SELECT balance FROM wallets WHERE wallet_id = %s", (game_state['wallet_id'],))
        wallet = cursor.fetchone()
        
        return jsonify({
            'message': 'Game continues',
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
@get_limiter().limit("30 per minute")  # 30 new games per minute
@login_required
@csrf_required
def start_game():
    """
    Start a new blackjack game

    ---
    tags:
      - Games
    summary: Start blackjack game
    description: |
      Starts a new blackjack game with the specified bet amount.
      Player receives 2 cards, dealer receives 1 visible card.
      Cannot start if there's already an active game.
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
          properties:
            amount:
              type: number
              format: float
              minimum: 0.01
              example: 50.00
              description: Bet amount
            csrf_token:
              type: string
              description: Alternative way to provide CSRF token
    responses:
      200:
        description: Game started successfully
        schema:
          type: object
          properties:
            player_hand:
              type: array
              items:
                type: object
                properties:
                  suit:
                    type: string
                  rank:
                    type: string
            dealer_card:
              type: object
              properties:
                suit:
                  type: string
                rank:
                  type: string
            player_value:
              type: integer
              example: 15
            status:
              type: string
              example: playing
            new_balance:
              type: number
              example: 450.00
      400:
        description: Invalid amount, insufficient balance, or active game exists
      401:
        description: Not authenticated
      403:
        description: Invalid CSRF token
    """
    user_id = session.get('user_id')
    data = request.get_json()
    
    if not data or 'amount' not in data:
        return jsonify({'message': 'Bet amount is required!'}), 400
        
    try:
        amount = float(data['amount'])
        if amount <= 0: raise ValueError
    except ValueError:
        return jsonify({'message': 'Invalid bet amount!'}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({'message': 'Database error!'}), 500
        
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)
        
        active_game = get_active_blackjack_game(cursor, user_id)
        if active_game:
            # Check if game state is valid, if not clean it up
            game_state = load_game_state(active_game)
            if game_state is None:
                # Orphaned game - clean it up
                cursor.execute("""
                    UPDATE games SET status = 'CANCELLED', ended_at = NOW() 
                    WHERE game_id = %s
                """, (active_game['game_id'],))
                # Continue to create new game
            else:
                conn.rollback()
                return jsonify({
                    'message': 'You already have an active game!',
                    'has_active_game': True,
                    'game_id': active_game['game_id']
                }), 400
        
        # Check balance
        cursor.execute("SELECT wallet_id, balance FROM wallets WHERE user_id = %s FOR UPDATE", (user_id,))
        wallet = cursor.fetchone()
        
        if not wallet or float(wallet['balance']) < amount:
            conn.rollback()
            return jsonify({'message': 'Insufficient balance!'}), 400
            
        wallet_id = wallet['wallet_id']
        
        # Get active rule set ID
        rule_set_id = get_active_rule_set_id()
        
        # Create game record
        sql_create_game = """
            INSERT INTO games (user_id, rule_set_id, game_type, status)
            VALUES (%s, %s, 'blackjack', 'ACTIVE')
        """
        cursor.execute(sql_create_game, (user_id, rule_set_id))
        game_id = cursor.lastrowid
        
        # Deduct balance
        cursor.execute("UPDATE wallets SET balance = balance - %s WHERE wallet_id = %s", (amount, wallet_id))
        
        # Create bet record
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
        # SECURITY: Deal only 1 card to Dealer, draw second card when game ends
        # This prevents hidden card leakage in API response
        dealer_hand = [deck.pop()]
        
        # Save game state to database
        save_game_state(cursor, game_id, deck, player_hand, dealer_hand, amount, wallet_id)
        
        conn.commit()
        
        # Save to session (for performance)
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
        return jsonify({'message': f'Error: {e}'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@blackjack_bp.route('/game/blackjack/hit', methods=['POST'])
@login_required
@csrf_required
def hit():
    """
    Draw a card in blackjack (Hit)

    ---
    tags:
      - Games
    summary: Blackjack Hit
    description: |
      Draws an additional card for the player.
      If player exceeds 21 (bust), the game ends with a loss.
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
        required: false
        schema:
          type: object
          properties:
            csrf_token:
              type: string
    responses:
      200:
        description: Card drawn
        schema:
          type: object
          properties:
            player_hand:
              type: array
              items:
                type: object
            player_value:
              type: integer
              example: 18
            dealer_card:
              type: object
            dealer_value:
              type: string
              example: "?"
            status:
              type: string
              enum: [playing, bust]
              example: playing
            message:
              type: string
              description: Present when game ends (bust)
      400:
        description: No active game
      401:
        description: Not authenticated
      403:
        description: Invalid CSRF token
    """
    user_id = session.get('user_id')
    game = session.get('bj_game')
    
    # Load from database if game not in session
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
        return jsonify({'message': 'No active game!'}), 400
        
    deck = game['deck']
    player_hand = game['player_hand']
    
    # Deal card
    card = deck.pop()
    player_hand.append(card)
    
    player_value = calculate_hand_value(player_hand)
    
    # Update game state
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    save_game_state(cursor, game['game_id'], deck, player_hand, game['dealer_hand'], game['bet_amount'], game['wallet_id'])
    conn.commit()
    
    if player_value > 21:
        # End game on Bust
        game_id = game['game_id']
        bet_id = game['bet_id']
        
        # SECURITY: Start transaction
        conn.start_transaction()
        
        # Draw dealer's second card now (player busted, game over)
        dealer_hand = game['dealer_hand']
        while len(dealer_hand) < 2:
            dealer_hand.append(deck.pop())
        
        dealer_value = calculate_hand_value(dealer_hand)
        
        # Save game result
        game_result_json = json.dumps({
            'player_hand': player_hand,
            'dealer_hand': dealer_hand,
            'player_value': player_value,
            'dealer_value': dealer_value,
            'result': 'bust',
            'payout': 0
        })
        cursor.execute("""
            UPDATE games 
            SET game_result = %s, game_state = NULL, ended_at = NOW(), status = 'COMPLETED'
            WHERE game_id = %s
        """, (game_result_json, game_id))
        
        # Create payout record (LOSS)
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
            'dealer_hand': dealer_hand,
            'dealer_value': dealer_value,
            'status': 'bust',
            'message': 'Bust! You lost.'
        })
    
    # Update session
    session['bj_game'] = game
    cursor.close()
    conn.close()
    
    # SECURITY: Send only dealer's open card, no hidden card (not drawn yet)
    return jsonify({
        'player_hand': player_hand,
        'player_value': player_value,
        'dealer_card': game['dealer_hand'][0],  # Sadece açık kart
        'dealer_value': '?',
        'status': 'playing'
    })


@blackjack_bp.route('/game/blackjack/stand', methods=['POST'])
@login_required
@csrf_required
def stand():
    """
    Stand in blackjack (end turn)

    ---
    tags:
      - Games
    summary: Blackjack Stand
    description: |
      Player stands with current hand. Dealer draws cards until reaching 17 or higher.
      Game result is determined based on final hand values.
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
        required: false
        schema:
          type: object
          properties:
            csrf_token:
              type: string
    responses:
      200:
        description: Game finished
        schema:
          type: object
          properties:
            player_hand:
              type: array
              items:
                type: object
            dealer_hand:
              type: array
              items:
                type: object
            player_value:
              type: integer
              example: 19
            dealer_value:
              type: integer
              example: 17
            result:
              type: string
              enum: [win, lose, push, blackjack]
              example: win
            status:
              type: string
              example: finished
            message:
              type: string
              example: "You won! (+100.00)"
            payout:
              type: number
              example: 100.00
            new_balance:
              type: number
              example: 550.00
      400:
        description: No active game
      401:
        description: Not authenticated
      403:
        description: Invalid CSRF token
    """
    user_id = session.get('user_id')
    game = session.get('bj_game')
    
    # Load from database if game not in session
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
        return jsonify({'message': 'No active game!'}), 400
    
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
    """Handle game end"""
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        conn.start_transaction()
        
        # SECURITY: Prevent race condition with Row lock (for payout)
        cursor.execute("SELECT balance FROM wallets WHERE wallet_id = %s FOR UPDATE", (wallet_id,))
        wallet_row = cursor.fetchone()
        if not wallet_row:
            conn.rollback()
            return jsonify({'message': 'Wallet not found!'}), 404
        
        deck = session.get('bj_game', {}).get('deck', get_deck())
        
        # SECURITY: Draw dealer's second card now (game over)
        # Dealer initially only had 1 card
        while len(dealer_hand) < 2:
            if deck:
                dealer_hand.append(deck.pop())
            else:
                break
        
        # Dealer continues to draw until 17
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
                message = 'Both sides Blackjack! Push.'
            else:
                result = 'blackjack'
                payout_multiplier = get_active_rule_value('blackjack_payout', DEFAULT_BLACKJACK_PAYOUT)
                payout = amount * payout_multiplier
                message = f'BLACKJACK! You won! (+{payout:.2f})'
        elif dealer_value > 21:
            result = 'win'
            payout_multiplier = get_active_rule_value('blackjack_normal_payout', DEFAULT_NORMAL_PAYOUT)
            payout = amount * payout_multiplier
            message = f'Dealer busted! You won! (+{payout:.2f})'
        elif player_value > dealer_value:
            result = 'win'
            payout_multiplier = get_active_rule_value('blackjack_normal_payout', DEFAULT_NORMAL_PAYOUT)
            payout = amount * payout_multiplier
            message = f'You won! (+{payout:.2f})'
        elif player_value < dealer_value:
            result = 'lose'
            payout = 0
            message = 'You lost.'
        else:
            result = 'push'
            payout = amount
            message = 'Push! Bet returned.'
        
        # Update balance if won (wallet is already locked with FOR UPDATE)
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
        return jsonify({'message': f'Error: {e}'}), 500
    finally:
        cursor.close()
        conn.close()
