"""
Game Service - Tüm oyun işlemlerini yönetir
"""
import json
from ..database import get_db_connection
from ..rules import get_active_rule_set_id, get_active_rule_value
from ..utils.logger import game_logger
from .wallet_service import WalletService
from mysql.connector import Error


class GameService:
    """
    Oyun işlemleri için base service class
    Tüm oyunlar bu class'ı kullanır
    """
    
    @staticmethod
    def create_game(user_id: int, game_type: str, cursor) -> tuple:
        """
        Yeni game kaydı oluştur
        
        Returns:
            (game_id, rule_set_id)
        """
        rule_set_id = get_active_rule_set_id()
        
        cursor.execute("""
            INSERT INTO games (user_id, rule_set_id, game_type, status)
            VALUES (%s, %s, %s, 'ACTIVE')
        """, (user_id, rule_set_id, game_type))
        
        game_id = cursor.lastrowid
        game_logger.debug(f"Game created: id={game_id}, type={game_type}, user={user_id}")
        
        return game_id, rule_set_id
    
    @staticmethod
    def create_bet(game_id: int, user_id: int, bet_type: str, bet_value: str, stake_amount: float, cursor) -> int:
        """
        Bet kaydı oluştur
        
        Returns:
            bet_id
        """
        cursor.execute("""
            INSERT INTO bets (game_id, user_id, bet_type, bet_value, stake_amount)
            VALUES (%s, %s, %s, %s, %s)
        """, (game_id, user_id, bet_type, bet_value, stake_amount))
        
        bet_id = cursor.lastrowid
        game_logger.debug(f"Bet created: id={bet_id}, game={game_id}, amount={stake_amount}")
        
        return bet_id
    
    @staticmethod
    def create_payout(bet_id: int, win_amount: float, outcome: str, cursor) -> int:
        """
        Payout kaydı oluştur
        
        Args:
            outcome: 'WIN' veya 'LOSS'
        
        Returns:
            payout_id
        """
        cursor.execute("""
            INSERT INTO payouts (bet_id, win_amount, outcome)
            VALUES (%s, %s, %s)
        """, (bet_id, win_amount, outcome))
        
        payout_id = cursor.lastrowid
        game_logger.debug(f"Payout created: id={payout_id}, bet={bet_id}, amount={win_amount}, outcome={outcome}")
        
        return payout_id
    
    @staticmethod
    def complete_game(game_id: int, game_result: dict, cursor):
        """
        Oyunu tamamla ve sonucu kaydet
        """
        result_json = json.dumps(game_result)
        
        cursor.execute("""
            UPDATE games 
            SET game_result = %s, ended_at = NOW(), status = 'COMPLETED'
            WHERE game_id = %s
        """, (result_json, game_id))
        
        game_logger.debug(f"Game completed: id={game_id}")
    
    @staticmethod
    def process_game(user_id: int, game_type: str, bet_amount: float, bet_type: str, 
                     bet_value: str, game_result: dict, is_win: bool, payout_amount: float) -> dict:
        """
        Tüm oyun işlemlerini tek bir transaction'da yap
        
        Args:
            user_id: Kullanıcı ID
            game_type: 'coinflip', 'roulette', 'blackjack'
            bet_amount: Bahis miktarı
            bet_type: Bahis tipi (örn: 'choice', 'number', 'color')
            bet_value: Bahis değeri (örn: 'yazi', '7', 'red')
            game_result: Oyun sonucu dict'i
            is_win: Kazandı mı?
            payout_amount: Kazanç miktarı (kaybettiyse 0)
        
        Returns:
            {
                'success': bool,
                'message': str,
                'game_id': int,
                'new_balance': float,
                ...game_result
            }
        """
        conn = None
        cursor = None
        
        try:
            conn = get_db_connection()
            if not conn:
                return {'success': False, 'message': 'Database error'}
            
            conn.start_transaction()
            cursor = conn.cursor(dictionary=True)
            
            # 1. Bakiye kontrolü
            has_enough, wallet_id, balance = WalletService.check_balance(user_id, bet_amount, cursor)
            
            if not wallet_id:
                conn.rollback()
                return {'success': False, 'message': 'Cüzdan bulunamadı'}
            
            if not has_enough:
                conn.rollback()
                return {
                    'success': False,
                    'message': f'Yetersiz bakiye. Mevcut: {balance:.2f}'
                }
            
            # 2. Game oluştur
            game_id, rule_set_id = GameService.create_game(user_id, game_type, cursor)
            
            # 3. Bahis miktarını düş
            WalletService.debit(wallet_id, bet_amount, cursor)
            
            # 4. Bet oluştur
            bet_id = GameService.create_bet(game_id, user_id, bet_type, str(bet_value), bet_amount, cursor)
            
            # 5. Oyunu tamamla
            GameService.complete_game(game_id, game_result, cursor)
            
            # 6. Payout işle
            if is_win:
                WalletService.credit(wallet_id, payout_amount, cursor)
                GameService.create_payout(bet_id, payout_amount, 'WIN', cursor)
            else:
                GameService.create_payout(bet_id, 0, 'LOSS', cursor)
            
            conn.commit()
            
            # 7. Yeni bakiyeyi al
            new_balance = WalletService.get_balance(wallet_id, cursor)
            
            # Log
            outcome = 'WIN' if is_win else 'LOSS'
            game_logger.info(
                f"Game played: type={game_type}, user={user_id}, bet={bet_amount}, "
                f"outcome={outcome}, payout={payout_amount}, new_balance={new_balance}"
            )
            
            return {
                'success': True,
                'game_id': game_id,
                'new_balance': new_balance,
                **game_result
            }
            
        except Error as e:
            if conn: conn.rollback()
            game_logger.error(f"Game processing error: {e}")
            return {'success': False, 'message': 'Oyun sırasında bir hata oluştu'}
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
    
    @staticmethod
    def get_user_games(user_id: int, game_type: str = None, limit: int = 20, offset: int = 0) -> list:
        """
        Kullanıcının oyun geçmişini getir
        """
        conn = get_db_connection()
        if not conn:
            return []
        
        cursor = conn.cursor(dictionary=True)
        
        try:
            sql = """
                SELECT 
                    g.game_id,
                    g.game_type,
                    g.game_result,
                    g.started_at,
                    g.ended_at,
                    g.status,
                    rs.name as rule_set_name,
                    b.bet_type,
                    b.bet_value,
                    b.stake_amount,
                    p.win_amount,
                    p.outcome
                FROM games g
                LEFT JOIN rule_sets rs ON g.rule_set_id = rs.rule_set_id
                LEFT JOIN bets b ON b.game_id = g.game_id
                LEFT JOIN payouts p ON p.bet_id = b.bet_id
                WHERE g.user_id = %s
            """
            params = [user_id]
            
            if game_type:
                sql += " AND g.game_type = %s"
                params.append(game_type)
            
            sql += " ORDER BY g.started_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cursor.execute(sql, params)
            games = cursor.fetchall()
            
            # JSON parse
            for game in games:
                if game['game_result']:
                    try:
                        game['game_result'] = json.loads(game['game_result'])
                    except:
                        pass
                if game['stake_amount']:
                    game['stake_amount'] = float(game['stake_amount'])
                if game['win_amount']:
                    game['win_amount'] = float(game['win_amount'])
            
            return games
            
        except Error as e:
            game_logger.error(f"Get user games error: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_game_stats(user_id: int = None, game_type: str = None, days: int = 30) -> dict:
        """
        Oyun istatistiklerini getir
        
        Returns:
            {
                'total_games': int,
                'total_bets': float,
                'total_payouts': float,
                'win_count': int,
                'loss_count': int,
                'win_rate': float
            }
        """
        conn = get_db_connection()
        if not conn:
            return {}
        
        cursor = conn.cursor(dictionary=True)
        
        try:
            sql = """
                SELECT 
                    COUNT(DISTINCT g.game_id) as total_games,
                    COALESCE(SUM(b.stake_amount), 0) as total_bets,
                    COALESCE(SUM(p.win_amount), 0) as total_payouts,
                    SUM(CASE WHEN p.outcome = 'WIN' THEN 1 ELSE 0 END) as win_count,
                    SUM(CASE WHEN p.outcome = 'LOSS' THEN 1 ELSE 0 END) as loss_count
                FROM games g
                LEFT JOIN bets b ON b.game_id = g.game_id
                LEFT JOIN payouts p ON p.bet_id = b.bet_id
                WHERE g.status = 'COMPLETED'
                AND g.started_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            """
            params = [days]
            
            if user_id:
                sql += " AND g.user_id = %s"
                params.append(user_id)
            
            if game_type:
                sql += " AND g.game_type = %s"
                params.append(game_type)
            
            cursor.execute(sql, params)
            stats = cursor.fetchone()
            
            if stats:
                win_count = int(stats['win_count'] or 0)
                loss_count = int(stats['loss_count'] or 0)
                total = win_count + loss_count
                
                return {
                    'total_games': int(stats['total_games'] or 0),
                    'total_bets': float(stats['total_bets'] or 0),
                    'total_payouts': float(stats['total_payouts'] or 0),
                    'win_count': win_count,
                    'loss_count': loss_count,
                    'win_rate': round((win_count / total * 100), 2) if total > 0 else 0,
                    'profit': float(stats['total_bets'] or 0) - float(stats['total_payouts'] or 0)
                }
            
            return {
                'total_games': 0,
                'total_bets': 0,
                'total_payouts': 0,
                'win_count': 0,
                'loss_count': 0,
                'win_rate': 0,
                'profit': 0
            }
            
        except Error as e:
            game_logger.error(f"Get game stats error: {e}")
            return {}
        finally:
            cursor.close()
            conn.close()

