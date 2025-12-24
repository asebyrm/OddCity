import mysql.connector
from mysql.connector import Error
from .config import Config

def get_db_connection():
    try:
        conn = mysql.connector.connect(**Config.DB_CONFIG)
        return conn
    except Error as e:
        print(f"Veritabanı bağlantı hatası: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if conn is None:
        print("Veritabanı bağlantısı kurulamadığı için tablolar oluşturulamadı.")
        return

    cursor = conn.cursor()
    
    tables = [
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTO_INCREMENT,
            email VARCHAR(200) NOT NULL UNIQUE,
            password_hash VARCHAR(200) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','BANNED')),
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS wallets (
            wallet_id INTEGER PRIMARY KEY AUTO_INCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            balance DECIMAL(12,2) NOT NULL DEFAULT 0,
            currency CHAR(3) NOT NULL DEFAULT 'VRT',
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS rule_sets (
            rule_set_id INTEGER PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            house_edge DECIMAL(5,2) NOT NULL DEFAULT 5.00,
            start_at TIMESTAMP,
            end_at TIMESTAMP,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_by_admin_id INTEGER NOT NULL,
            FOREIGN KEY (created_by_admin_id) REFERENCES users(user_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS rules (
            rule_id INTEGER PRIMARY KEY AUTO_INCREMENT,
            rule_set_id INTEGER NOT NULL,
            rule_type VARCHAR(50) NOT NULL,
            rule_param VARCHAR(100),
            priority INTEGER NOT NULL DEFAULT 0,
            is_required BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rule_set_id) REFERENCES rule_sets(rule_set_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS games (
            game_id INTEGER PRIMARY KEY AUTO_INCREMENT,
            user_id INTEGER NOT NULL,
            rule_set_id INTEGER,
            started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','COMPLETED')),
            dice_count INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (rule_set_id) REFERENCES rule_sets(rule_set_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS bets (
            bet_id INTEGER PRIMARY KEY AUTO_INCREMENT,
            game_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            stake_amount DECIMAL(10,2) NOT NULL,
            placed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games(game_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS payouts (
            payout_id INTEGER PRIMARY KEY AUTO_INCREMENT,
            bet_id INTEGER NOT NULL UNIQUE,
            win_amount DECIMAL(10,2) NOT NULL,
            outcome VARCHAR(10) NOT NULL CHECK (outcome IN ('WIN','LOSS')),
            paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            payout_tx_id INTEGER,
            FOREIGN KEY (bet_id) REFERENCES bets(bet_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS transactions (
            tx_id INTEGER PRIMARY KEY AUTO_INCREMENT,
            user_id INTEGER NOT NULL,
            wallet_id INTEGER NOT NULL,
            tx_type VARCHAR(20) NOT NULL CHECK (tx_type IN ('DEPOSIT','BET','PAYOUT','WITHDRAW')),
            amount DECIMAL(12,2) NOT NULL,
            currency CHAR(3) NOT NULL DEFAULT 'VRT',
            reference_type VARCHAR(30),
            reference_id INTEGER,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (wallet_id) REFERENCES wallets(wallet_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS logs (
            log_id INTEGER PRIMARY KEY AUTO_INCREMENT,
            user_id INTEGER NOT NULL,
            action_type VARCHAR(50) NOT NULL,
            ip_address VARCHAR(45),
            user_agent TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            meta_data TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        """
    ]

    try:
        for table_sql in tables:
            cursor.execute(table_sql)
        conn.commit()
        print("Veritabanı tabloları başarıyla kontrol edildi/oluşturuldu.")
    except Error as e:
        print(f"Tablo oluşturma hatası: {e}")
    finally:
        cursor.close()
        conn.close()