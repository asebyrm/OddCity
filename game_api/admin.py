from flask import Blueprint, jsonify, request
from .database import get_db_connection
from .auth import admin_required
from .services.game_service import GameService
from .utils.logger import admin_logger
from mysql.connector import Error

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/users', methods=['GET'])
@admin_required
def list_users():
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı hatası'}), 500
    
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
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/admin/user/<int:user_id>/ban', methods=['POST'])
@admin_required
def ban_user(user_id):
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı hatası'}), 500
    
    cursor = conn.cursor()
    try:
        # Prevent banning self or other admins (optional, but good practice)
        cursor.execute("SELECT is_admin FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if user and user[0]:
             return jsonify({'message': 'Adminler yasaklanamaz!'}), 400

        cursor.execute("UPDATE users SET status = 'BANNED' WHERE user_id = %s", (user_id,))
        conn.commit()
        return jsonify({'message': 'Kullanıcı yasaklandı.'})
    except Error as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/admin/user/<int:user_id>/unban', methods=['POST'])
@admin_required
def unban_user(user_id):
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı hatası'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET status = 'ACTIVE' WHERE user_id = %s", (user_id,))
        conn.commit()
        return jsonify({'message': 'Kullanıcı yasağı kaldırıldı.'})
    except Error as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/admin/user/<int:user_id>/history', methods=['GET'])
@admin_required
def user_history(user_id):
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı hatası'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Get wallet id first
        cursor.execute("SELECT wallet_id FROM wallets WHERE user_id = %s", (user_id,))
        wallet = cursor.fetchone()
        if not wallet:
            return jsonify({'message': 'Cüzdan bulunamadı'}), 404
            
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
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

# ============= DASHBOARD APIs =============

@admin_bp.route('/admin/dashboard/stats', methods=['GET'])
@admin_required
def dashboard_stats():
    """
    Admin dashboard için genel istatistikler
    """
    days = request.args.get('days', 30, type=int)
    
    conn = get_db_connection()
    if not conn: 
        return jsonify({'message': 'Veritabanı hatası'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Genel oyun istatistikleri
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
        
        # Oyun tipine göre dağılım
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
        game_type_stats = cursor.fetchall()
        
        # Kullanıcı istatistikleri
        cursor.execute("""
            SELECT 
                COUNT(*) as total_users,
                SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) as active_users,
                SUM(CASE WHEN status = 'BANNED' THEN 1 ELSE 0 END) as banned_users,
                SUM(CASE WHEN is_admin = TRUE THEN 1 ELSE 0 END) as admin_users
            FROM users
        """)
        user_stats = cursor.fetchone()
        
        # Toplam bakiye
        cursor.execute("SELECT COALESCE(SUM(balance), 0) as total_balance FROM wallets")
        wallet_stats = cursor.fetchone()
        
        # Transaction istatistikleri
        cursor.execute("""
            SELECT 
                tx_type,
                COUNT(*) as count,
                COALESCE(SUM(amount), 0) as total_amount
            FROM transactions
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY tx_type
        """, (days,))
        tx_stats = cursor.fetchall()
        
        # Rule set istatistikleri
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
        
        # Hesaplamalar
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
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/admin/dashboard/recent-games', methods=['GET'])
@admin_required
def recent_games():
    """
    Son oynanan oyunlar
    """
    limit = request.args.get('limit', 20, type=int)
    game_type = request.args.get('game_type')
    
    conn = get_db_connection()
    if not conn: 
        return jsonify({'message': 'Veritabanı hatası'}), 500
    
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
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/admin/dashboard/top-players', methods=['GET'])
@admin_required
def top_players():
    """
    En çok oynayan ve en çok kazanan oyuncular
    """
    days = request.args.get('days', 30, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    conn = get_db_connection()
    if not conn: 
        return jsonify({'message': 'Veritabanı hatası'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # En çok oynayan
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
        
        # En çok kazanan
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
        
        # En çok kaybeden
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
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/admin/user/<int:user_id>/games', methods=['GET'])
@admin_required
def user_games(user_id):
    """
    Belirli bir kullanıcının oyun geçmişi
    """
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    game_type = request.args.get('game_type')
    
    games = GameService.get_user_games(user_id, game_type, limit, offset)
    return jsonify(games)
