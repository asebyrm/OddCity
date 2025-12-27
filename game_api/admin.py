from flask import Blueprint, jsonify, request
from .database import get_db_connection
from .auth import admin_required
from .services.game_service import GameService
from .utils.logger import admin_logger
from .utils.csrf import csrf_required
from mysql.connector import Error

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/users', methods=['GET'])
@admin_required
def list_users():
    """
    List all users (Admin only)

    ---
    tags:
      - Admin
    summary: List all users
    description: Returns a list of all users with their wallet balances.
    security:
      - session: []
      - admin: []
    responses:
      200:
        description: Users retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              user_id:
                type: integer
              email:
                type: string
              status:
                type: string
                enum: [ACTIVE, BANNED]
              is_admin:
                type: boolean
              created_at:
                type: string
                format: date-time
              balance:
                type: number
              currency:
                type: string
      401:
        description: Not authenticated
      403:
        description: Admin access required
    """
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Database error'}), 500
    
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
        return jsonify({'message': f'Error: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/admin/user/<int:user_id>/ban', methods=['POST'])
@admin_required
@csrf_required
def ban_user(user_id):
    """
    Ban a user (Admin only)

    ---
    tags:
      - Admin
    summary: Ban user
    description: |
      Bans a user account, preventing login.
      Admin users cannot be banned.
      Requires CSRF token.
    security:
      - session: []
      - admin: []
      - csrf: []
    consumes:
      - application/json
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: User ID to ban
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
              description: Alternative way to provide CSRF token
    responses:
      200:
        description: User banned successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: User banned.
      400:
        description: Cannot ban admin users
      401:
        description: Not authenticated
      403:
        description: Admin access required or invalid CSRF token
    """
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Database error'}), 500
    
    cursor = conn.cursor()
    try:
        # Prevent banning self or other admins (optional, but good practice)
        cursor.execute("SELECT is_admin FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if user and user[0]:
             return jsonify({'message': 'Admins cannot be banned!'}), 400

        cursor.execute("UPDATE users SET status = 'BANNED' WHERE user_id = %s", (user_id,))
        conn.commit()
        return jsonify({'message': 'User banned.'})
    except Error as e:
        return jsonify({'message': f'Error: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/admin/user/<int:user_id>/unban', methods=['POST'])
@admin_required
@csrf_required
def unban_user(user_id):
    """
    Unban a user (Admin only)

    ---
    tags:
      - Admin
    summary: Unban user
    description: |
      Removes ban from a user account, allowing login again.
      Requires CSRF token.
    security:
      - session: []
      - admin: []
      - csrf: []
    consumes:
      - application/json
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: User ID to unban
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
        description: User unbanned successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: User ban removed.
      401:
        description: Not authenticated
      403:
        description: Admin access required or invalid CSRF token
    """
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Database error'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET status = 'ACTIVE' WHERE user_id = %s", (user_id,))
        conn.commit()
        return jsonify({'message': 'User ban removed.'})
    except Error as e:
        return jsonify({'message': f'Error: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/admin/user/<int:user_id>/history', methods=['GET'])
@admin_required
def user_history(user_id):
    """
    Get user transaction history (Admin only)

    ---
    tags:
      - Admin
    summary: Get user transaction history
    description: Returns the last 50 transactions for a specific user.
    security:
      - session: []
      - admin: []
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: User ID to get history for
    responses:
      200:
        description: Transaction history retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              transaction_id:
                type: integer
              amount:
                type: number
              tx_type:
                type: string
                enum: [DEPOSIT, WITHDRAW]
              created_at:
                type: string
                format: date-time
      401:
        description: Not authenticated
      403:
        description: Admin access required
      404:
        description: User wallet not found
    """
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Database error'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Get wallet id first
        cursor.execute("SELECT wallet_id FROM wallets WHERE user_id = %s", (user_id,))
        wallet = cursor.fetchone()
        if not wallet:
            return jsonify({'message': 'Wallet not found'}), 404
            
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
        return jsonify({'message': f'Error: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

# ============= DASHBOARD APIs =============

@admin_bp.route('/admin/dashboard/stats', methods=['GET'])
@admin_required
def dashboard_stats():
    """
    Get dashboard statistics (Admin only)

    ---
    tags:
      - Admin Dashboard
    summary: Get dashboard statistics
    description: |
      Returns comprehensive statistics for the admin dashboard including
      game stats, user counts, wallet totals, and transaction summaries.
    security:
      - session: []
      - admin: []
    parameters:
      - in: query
        name: days
        type: integer
        default: 30
        description: Number of days to include in statistics
    responses:
      200:
        description: Statistics retrieved successfully
        schema:
          type: object
          properties:
            period_days:
              type: integer
              example: 30
            games:
              type: object
              properties:
                total:
                  type: integer
                unique_players:
                  type: integer
                total_bets:
                  type: number
                total_payouts:
                  type: number
                house_profit:
                  type: number
                win_rate:
                  type: number
                by_type:
                  type: array
                  items:
                    type: object
            users:
              type: object
              properties:
                total:
                  type: integer
                active:
                  type: integer
                banned:
                  type: integer
                admins:
                  type: integer
            wallets:
              type: object
              properties:
                total_balance:
                  type: number
            transactions:
              type: array
              items:
                type: object
            rule_sets:
              type: array
              items:
                type: object
      401:
        description: Not authenticated
      403:
        description: Admin access required
    """
    days = request.args.get('days', 30, type=int)
    
    conn = get_db_connection()
    if not conn: 
        return jsonify({'message': 'Database error'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # General game statistics
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT g.game_id) as total_games,
                COUNT(DISTINCT g.user_id) as unique_players,
                COALESCE(SUM(b.stake_amount), 0) as total_bets,
                COALESCE(SUM(p.win_amount), 0) as total_payouts,
                SUM(CASE WHEN p.outcome = 'WIN' THEN 1 ELSE 0 END) as total_wins,
                SUM(CASE WHEN p.outcome = 'LOSS' THEN 1 ELSE 0 END) as total_losses
            FROM games g
            LEFT JOIN bets b ON b.game_id = g.game_id
            LEFT JOIN payouts p ON p.bet_id = b.bet_id
            WHERE g.status = 'COMPLETED'
            AND g.started_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (days,))
        game_stats = cursor.fetchone()
        
        # Distribution by game type
        cursor.execute("""
            SELECT 
                game_type,
                COUNT(*) as count,
                COALESCE(SUM(b.stake_amount), 0) as total_bets
            FROM games g
            LEFT JOIN bets b ON b.game_id = g.game_id
            WHERE g.status = 'COMPLETED'
            AND g.started_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY game_type
        """, (days,))
        game_type_stats_raw = cursor.fetchall()
        
        # Format and ensure all game types are present
        game_types_map = {}
        for gt in game_type_stats_raw:
            game_types_map[gt['game_type']] = {
                'game_type': gt['game_type'],
                'count': int(gt['count'] or 0),
                'total_bets': float(gt['total_bets'] or 0)
            }
        
        # Ensure all three game types are represented
        for game_type in ['coinflip', 'roulette', 'blackjack']:
            if game_type not in game_types_map:
                game_types_map[game_type] = {
                    'game_type': game_type,
                    'count': 0,
                    'total_bets': 0
                }
        
        game_type_stats = list(game_types_map.values())
        
        # User statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_users,
                SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) as active_users,
                SUM(CASE WHEN status = 'BANNED' THEN 1 ELSE 0 END) as banned_users,
                SUM(CASE WHEN is_admin = TRUE THEN 1 ELSE 0 END) as admin_users
            FROM users
        """)
        user_stats = cursor.fetchone()
        
        # Total balance
        cursor.execute("SELECT COALESCE(SUM(balance), 0) as total_balance FROM wallets")
        wallet_stats = cursor.fetchone()
        
        # Transaction statistics
        cursor.execute("""
            SELECT 
                tx_type,
                COUNT(*) as count,
                COALESCE(SUM(amount), 0) as total_amount
            FROM transactions
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY tx_type
        """, (days,))
        tx_stats_raw = cursor.fetchall()
        
        # Ensure we always have DEPOSIT and WITHDRAW entries
        tx_stats = []
        deposit_found = False
        withdraw_found = False
        for tx in tx_stats_raw:
            tx_stats.append({
                'tx_type': tx['tx_type'],
                'count': int(tx['count'] or 0),
                'total_amount': float(tx['total_amount'] or 0)
            })
            if tx['tx_type'] == 'DEPOSIT':
                deposit_found = True
            if tx['tx_type'] == 'WITHDRAW':
                withdraw_found = True
        
        if not deposit_found:
            tx_stats.append({'tx_type': 'DEPOSIT', 'count': 0, 'total_amount': 0})
        if not withdraw_found:
            tx_stats.append({'tx_type': 'WITHDRAW', 'count': 0, 'total_amount': 0})
        
        # Rule set statistics
        cursor.execute("""
            SELECT 
                rs.rule_set_id,
                rs.name,
                rs.is_active,
                COUNT(g.game_id) as game_count
            FROM rule_sets rs
            LEFT JOIN games g ON g.rule_set_id = rs.rule_set_id
            GROUP BY rs.rule_set_id
        """)
        rule_stats = cursor.fetchall()
        
        # Calculations
        total_bets = float(game_stats['total_bets'] or 0)
        total_payouts = float(game_stats['total_payouts'] or 0)
        house_profit = total_bets - total_payouts
        
        total_games = game_stats['total_games'] or 0
        total_wins = game_stats['total_wins'] or 0
        win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
        
        admin_logger.info(f"Dashboard stats fetched for last {days} days")
        
        return jsonify({
            'period_days': days,
            'games': {
                'total': total_games,
                'unique_players': game_stats['unique_players'] or 0,
                'total_bets': total_bets,
                'total_payouts': total_payouts,
                'house_profit': house_profit,
                'win_rate': round(win_rate, 2),
                'by_type': game_type_stats
            },
            'users': {
                'total': user_stats['total_users'] or 0,
                'active': user_stats['active_users'] or 0,
                'banned': user_stats['banned_users'] or 0,
                'admins': user_stats['admin_users'] or 0
            },
            'wallets': {
                'total_balance': float(wallet_stats['total_balance'] or 0)
            },
            'transactions': tx_stats,
            'rule_sets': rule_stats
        })
        
    except Error as e:
        admin_logger.error(f"Dashboard stats error: {e}")
        return jsonify({'message': f'Error: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/admin/dashboard/recent-games', methods=['GET'])
@admin_required
def recent_games():
    """
    Get recent games (Admin only)

    ---
    tags:
      - Admin Dashboard
    summary: Get recent games
    description: Returns the most recently completed games.
    security:
      - session: []
      - admin: []
    parameters:
      - in: query
        name: limit
        type: integer
        default: 20
        description: Maximum number of games to return
      - in: query
        name: game_type
        type: string
        enum: [coinflip, roulette, blackjack]
        description: Filter by game type
    responses:
      200:
        description: Recent games retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              game_id:
                type: integer
              game_type:
                type: string
              game_result:
                type: object
              started_at:
                type: string
                format: date-time
              ended_at:
                type: string
                format: date-time
              player_email:
                type: string
              rule_set_name:
                type: string
              stake_amount:
                type: number
              win_amount:
                type: number
              outcome:
                type: string
                enum: [WIN, LOSS]
      401:
        description: Not authenticated
      403:
        description: Admin access required
    """
    limit = request.args.get('limit', 20, type=int)
    game_type = request.args.get('game_type')
    
    conn = get_db_connection()
    if not conn: 
        return jsonify({'message': 'Database error'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT 
                g.game_id,
                g.game_type,
                g.game_result,
                g.started_at,
                g.ended_at,
                u.email as player_email,
                rs.name as rule_set_name,
                b.stake_amount,
                p.win_amount,
                p.outcome
            FROM games g
            JOIN users u ON g.user_id = u.user_id
            LEFT JOIN rule_sets rs ON g.rule_set_id = rs.rule_set_id
            LEFT JOIN bets b ON b.game_id = g.game_id
            LEFT JOIN payouts p ON p.bet_id = b.bet_id
            WHERE g.status = 'COMPLETED'
        """
        params = []
        
        if game_type:
            sql += " AND g.game_type = %s"
            params.append(game_type)
        
        sql += " ORDER BY g.started_at DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(sql, params)
        games = cursor.fetchall()
        
        # Format amounts
        for game in games:
            if game['stake_amount']:
                game['stake_amount'] = float(game['stake_amount'])
            if game['win_amount']:
                game['win_amount'] = float(game['win_amount'])
        
        return jsonify(games)
        
    except Error as e:
        return jsonify({'message': f'Error: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/admin/dashboard/top-players', methods=['GET'])
@admin_required
def top_players():
    """
    Get top players (Admin only)

    ---
    tags:
      - Admin Dashboard
    summary: Get top players
    description: |
      Returns rankings of players by activity and winnings.
      Includes most active, top winners, and top losers.
    security:
      - session: []
      - admin: []
    parameters:
      - in: query
        name: days
        type: integer
        default: 30
        description: Number of days to include
      - in: query
        name: limit
        type: integer
        default: 10
        description: Maximum players per category
    responses:
      200:
        description: Top players retrieved successfully
        schema:
          type: object
          properties:
            period_days:
              type: integer
            most_active:
              type: array
              items:
                type: object
                properties:
                  user_id:
                    type: integer
                  email:
                    type: string
                  game_count:
                    type: integer
                  total_bets:
                    type: number
            top_winners:
              type: array
              items:
                type: object
                properties:
                  user_id:
                    type: integer
                  email:
                    type: string
                  net_profit:
                    type: number
            top_losers:
              type: array
              items:
                type: object
                properties:
                  user_id:
                    type: integer
                  email:
                    type: string
                  net_loss:
                    type: number
      401:
        description: Not authenticated
      403:
        description: Admin access required
    """
    days = request.args.get('days', 30, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    conn = get_db_connection()
    if not conn: 
        return jsonify({'message': 'Database error'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Most active
        cursor.execute("""
            SELECT 
                u.user_id,
                u.email,
                COUNT(g.game_id) as game_count,
                COALESCE(SUM(b.stake_amount), 0) as total_bets,
                COALESCE(SUM(p.win_amount), 0) as total_payouts
            FROM users u
            JOIN games g ON g.user_id = u.user_id
            LEFT JOIN bets b ON b.game_id = g.game_id
            LEFT JOIN payouts p ON p.bet_id = b.bet_id
            WHERE g.started_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY u.user_id
            ORDER BY game_count DESC
            LIMIT %s
        """, (days, limit))
        most_active = cursor.fetchall()
        
        # Top winners
        cursor.execute("""
            SELECT 
                u.user_id,
                u.email,
                COALESCE(SUM(p.win_amount), 0) as total_winnings,
                COALESCE(SUM(b.stake_amount), 0) as total_bets,
                (COALESCE(SUM(p.win_amount), 0) - COALESCE(SUM(b.stake_amount), 0)) as net_profit
            FROM users u
            JOIN games g ON g.user_id = u.user_id
            LEFT JOIN bets b ON b.game_id = g.game_id
            LEFT JOIN payouts p ON p.bet_id = b.bet_id
            WHERE g.started_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY u.user_id
            ORDER BY net_profit DESC
            LIMIT %s
        """, (days, limit))
        top_winners = cursor.fetchall()
        
        # Top losers
        cursor.execute("""
            SELECT 
                u.user_id,
                u.email,
                COALESCE(SUM(b.stake_amount), 0) as total_bets,
                COALESCE(SUM(p.win_amount), 0) as total_winnings,
                (COALESCE(SUM(b.stake_amount), 0) - COALESCE(SUM(p.win_amount), 0)) as net_loss
            FROM users u
            JOIN games g ON g.user_id = u.user_id
            LEFT JOIN bets b ON b.game_id = g.game_id
            LEFT JOIN payouts p ON p.bet_id = b.bet_id
            WHERE g.started_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY u.user_id
            ORDER BY net_loss DESC
            LIMIT %s
        """, (days, limit))
        top_losers = cursor.fetchall()
        
        # Format amounts
        for player in most_active + top_winners + top_losers:
            for key in ['total_bets', 'total_payouts', 'total_winnings', 'net_profit', 'net_loss']:
                if key in player and player[key]:
                    player[key] = float(player[key])
        
        return jsonify({
            'period_days': days,
            'most_active': most_active,
            'top_winners': top_winners,
            'top_losers': top_losers
        })
        
    except Error as e:
        return jsonify({'message': f'Error: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/admin/user/<int:user_id>/games', methods=['GET'])
@admin_required
def user_games(user_id):
    """
    Get a user's game history (Admin only)

    ---
    tags:
      - Admin
    summary: Get user's game history
    description: Returns a paginated list of games for a specific user.
    security:
      - session: []
      - admin: []
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: User ID to get games for
      - in: query
        name: limit
        type: integer
        default: 50
        description: Maximum number of games to return
      - in: query
        name: offset
        type: integer
        default: 0
        description: Number of games to skip
      - in: query
        name: game_type
        type: string
        enum: [coinflip, roulette, blackjack]
        description: Filter by game type
    responses:
      200:
        description: Games retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              game_id:
                type: integer
              game_type:
                type: string
              game_result:
                type: object
              started_at:
                type: string
                format: date-time
              stake_amount:
                type: number
              win_amount:
                type: number
              outcome:
                type: string
      401:
        description: Not authenticated
      403:
        description: Admin access required
    """
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    game_type = request.args.get('game_type')
    
    games = GameService.get_user_games(user_id, game_type, limit, offset)
    return jsonify(games)
