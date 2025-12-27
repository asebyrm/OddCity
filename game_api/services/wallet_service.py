"""
Wallet Service - Tüm wallet işlemlerini yönetir
"""
from ..database import get_db_connection
from ..utils.logger import game_logger
from mysql.connector import Error


class WalletService:
    """
    Wallet işlemleri için service class
    """
    
    @staticmethod
    def get_wallet(user_id: int, cursor=None, for_update: bool = False):
        """
        Kullanıcının wallet bilgilerini getir
        
        Args:
            user_id: Kullanıcı ID
            cursor: Varsa mevcut cursor'ı kullan
            for_update: Transaction için kilitlensin mi?
        
        Returns:
            dict: {'wallet_id': int, 'balance': float} veya None
        """
        own_cursor = cursor is None
        conn = None
        
        try:
            if own_cursor:
                conn = get_db_connection()
                if not conn:
                    return None
                cursor = conn.cursor(dictionary=True)
            
            sql = "SELECT wallet_id, balance FROM wallets WHERE user_id = %s"
            if for_update:
                sql += " FOR UPDATE"
            
            cursor.execute(sql, (user_id,))
            wallet = cursor.fetchone()
            
            if wallet:
                wallet['balance'] = float(wallet['balance'])
            
            return wallet
            
        except Error as e:
            game_logger.error(f"Wallet fetch error: {e}")
            return None
        finally:
            if own_cursor:
                if cursor: cursor.close()
                if conn: conn.close()
    
    @staticmethod
    def check_balance(user_id: int, amount: float, cursor=None) -> tuple:
        """
        Bakiye kontrolü yap
        
        Returns:
            (has_enough, wallet_id, current_balance)
        """
        wallet = WalletService.get_wallet(user_id, cursor, for_update=True)
        
        if not wallet:
            return False, None, 0
        
        has_enough = wallet['balance'] >= amount
        return has_enough, wallet['wallet_id'], wallet['balance']
    
    @staticmethod
    def debit(wallet_id: int, amount: float, cursor) -> bool:
        """
        Wallet'tan para düş
        
        Args:
            wallet_id: Wallet ID
            amount: Düşülecek miktar
            cursor: Database cursor (transaction içinde olmalı)
        
        Returns:
            bool: Başarılı mı?
        """
        try:
            cursor.execute(
                "UPDATE wallets SET balance = balance - %s WHERE wallet_id = %s",
                (amount, wallet_id)
            )
            game_logger.debug(f"Wallet {wallet_id} debited: {amount}")
            return True
        except Error as e:
            game_logger.error(f"Wallet debit error: {e}")
            return False
    
    @staticmethod
    def credit(wallet_id: int, amount: float, cursor) -> bool:
        """
        Wallet'a para ekle
        
        Args:
            wallet_id: Wallet ID
            amount: Eklenecek miktar
            cursor: Database cursor (transaction içinde olmalı)
        
        Returns:
            bool: Başarılı mı?
        """
        try:
            cursor.execute(
                "UPDATE wallets SET balance = balance + %s WHERE wallet_id = %s",
                (amount, wallet_id)
            )
            game_logger.debug(f"Wallet {wallet_id} credited: {amount}")
            return True
        except Error as e:
            game_logger.error(f"Wallet credit error: {e}")
            return False
    
    @staticmethod
    def get_balance(wallet_id: int, cursor) -> float:
        """
        Güncel bakiyeyi getir
        """
        try:
            cursor.execute(
                "SELECT balance FROM wallets WHERE wallet_id = %s",
                (wallet_id,)
            )
            result = cursor.fetchone()
            return float(result['balance']) if result else 0.0
        except Error as e:
            game_logger.error(f"Balance fetch error: {e}")
            return 0.0
    
    @staticmethod
    def deposit(user_id: int, amount: float) -> dict:
        """
        Para yatırma işlemi
        
        Returns:
            {'success': bool, 'message': str, 'new_balance': float}
        """
        conn = None
        cursor = None
        
        try:
            conn = get_db_connection()
            if not conn:
                return {'success': False, 'message': 'Database error'}
            
            conn.start_transaction()
            cursor = conn.cursor(dictionary=True)
            
            # GÜVENLİK: Row lock ile race condition önle
            wallet = WalletService.get_wallet(user_id, cursor, for_update=True)
            if not wallet:
                conn.rollback()
                return {'success': False, 'message': 'Cüzdan bulunamadı'}
            
            wallet_id = wallet['wallet_id']
            old_balance = wallet['balance']
            
            # Para ekle
            WalletService.credit(wallet_id, amount, cursor)
            
            # Transaction kaydı
            cursor.execute("""
                INSERT INTO transactions (user_id, wallet_id, amount, tx_type)
                VALUES (%s, %s, %s, 'DEPOSIT')
            """, (user_id, wallet_id, amount))
            
            conn.commit()
            
            new_balance = WalletService.get_balance(wallet_id, cursor)
            
            game_logger.info(f"Deposit: user={user_id}, amount={amount}, new_balance={new_balance}")
            
            return {
                'success': True,
                'message': f'{amount} VIRTUAL yatırıldı',
                'new_balance': new_balance
            }
            
        except Error as e:
            if conn: conn.rollback()
            game_logger.error(f"Deposit error: {e}")
            return {'success': False, 'message': 'İşlem hatası'}
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
    
    @staticmethod
    def withdraw(user_id: int, amount: float) -> dict:
        """
        Para çekme işlemi
        
        Returns:
            {'success': bool, 'message': str, 'new_balance': float}
        """
        conn = None
        cursor = None
        
        try:
            conn = get_db_connection()
            if not conn:
                return {'success': False, 'message': 'Database error'}
            
            conn.start_transaction()
            cursor = conn.cursor(dictionary=True)
            
            has_enough, wallet_id, balance = WalletService.check_balance(user_id, amount, cursor)
            
            if not wallet_id:
                conn.rollback()
                return {'success': False, 'message': 'Cüzdan bulunamadı'}
            
            if not has_enough:
                conn.rollback()
                return {
                    'success': False,
                    'message': f'Yetersiz bakiye. Mevcut: {balance:.2f}'
                }
            
            # Para düş
            WalletService.debit(wallet_id, amount, cursor)
            
            # Transaction kaydı
            cursor.execute("""
                INSERT INTO transactions (user_id, wallet_id, amount, tx_type)
                VALUES (%s, %s, %s, 'WITHDRAW')
            """, (user_id, wallet_id, amount))
            
            conn.commit()
            
            new_balance = WalletService.get_balance(wallet_id, cursor)
            
            game_logger.info(f"Withdraw: user={user_id}, amount={amount}, new_balance={new_balance}")
            
            return {
                'success': True,
                'message': f'{amount} VIRTUAL çekildi',
                'new_balance': new_balance
            }
            
        except Error as e:
            if conn: conn.rollback()
            game_logger.error(f"Withdraw error: {e}")
            return {'success': False, 'message': 'İşlem hatası'}
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

