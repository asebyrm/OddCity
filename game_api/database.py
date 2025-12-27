import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash
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
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by_admin_id) REFERENCES users(user_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS rules (
            rule_id INTEGER PRIMARY KEY AUTO_INCREMENT,
            rule_set_id INTEGER NOT NULL,
            rule_type VARCHAR(50) NOT NULL,
            rule_param VARCHAR(100),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rule_set_id) REFERENCES rule_sets(rule_set_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS games (
            game_id INTEGER PRIMARY KEY AUTO_INCREMENT,
            user_id INTEGER NOT NULL,
            rule_set_id INTEGER,
            game_type VARCHAR(20) NOT NULL CHECK (game_type IN ('coinflip', 'roulette', 'blackjack')),
            game_state JSON,
            game_result TEXT,
            started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','COMPLETED','ABANDONED')),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (rule_set_id) REFERENCES rule_sets(rule_set_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS bets (
            bet_id INTEGER PRIMARY KEY AUTO_INCREMENT,
            game_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            bet_type VARCHAR(50),
            bet_value VARCHAR(100),
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
            FOREIGN KEY (bet_id) REFERENCES bets(bet_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS transactions (
            tx_id INTEGER PRIMARY KEY AUTO_INCREMENT,
            user_id INTEGER NOT NULL,
            wallet_id INTEGER NOT NULL,
            tx_type VARCHAR(20) NOT NULL CHECK (tx_type IN ('DEPOSIT','WITHDRAW')),
            amount DECIMAL(12,2) NOT NULL,
            currency CHAR(3) NOT NULL DEFAULT 'VRT',
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
    
    # Index'ler - Performans için
    indexes = [
        # Games tablosu index'leri
        "CREATE INDEX IF NOT EXISTS idx_games_user_id ON games(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_games_rule_set_id ON games(rule_set_id)",
        "CREATE INDEX IF NOT EXISTS idx_games_game_type ON games(game_type)",
        "CREATE INDEX IF NOT EXISTS idx_games_started_at ON games(started_at)",
        "CREATE INDEX IF NOT EXISTS idx_games_status ON games(status)",
        
        # Bets tablosu index'leri
        "CREATE INDEX IF NOT EXISTS idx_bets_game_id ON bets(game_id)",
        "CREATE INDEX IF NOT EXISTS idx_bets_user_id ON bets(user_id)",
        
        # Payouts tablosu index'leri
        "CREATE INDEX IF NOT EXISTS idx_payouts_outcome ON payouts(outcome)",
        
        # Rules tablosu index'leri
        "CREATE INDEX IF NOT EXISTS idx_rules_rule_set_id ON rules(rule_set_id)",
        "CREATE INDEX IF NOT EXISTS idx_rules_rule_type ON rules(rule_type)",
        
        # Rule sets tablosu index'leri
        "CREATE INDEX IF NOT EXISTS idx_rule_sets_is_active ON rule_sets(is_active)",
        
        
        # Transactions tablosu index'leri
        "CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at)",
        
        # Users tablosu index'leri
        "CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)",
        "CREATE INDEX IF NOT EXISTS idx_users_is_admin ON users(is_admin)"
    ]

    try:
        for table_sql in tables:
            cursor.execute(table_sql)
        conn.commit()
        print("Veritabanı tabloları başarıyla kontrol edildi/oluşturuldu.")
        
        # Index'leri oluştur
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except Error:
                pass  # Index zaten varsa hata vermesini engelle
        conn.commit()
        print("Index'ler oluşturuldu.")
        
        # Default admin kullanıcısını oluştur
        admin_id = create_default_admin(conn, cursor)
        
        # Default rule set ve kurallarını oluştur
        if admin_id:
            create_default_rules(conn, cursor, admin_id)
        
    except Error as e:
        print(f"Tablo oluşturma hatası: {e}")
    finally:
        cursor.close()
        conn.close()

def create_default_admin(conn, cursor):
    """Default admin kullanıcısını oluştur"""
    try:
        # Admin kullanıcısı var mı kontrol et
        cursor.execute("SELECT user_id FROM users WHERE email = 'admin@example.com'")
        existing_admin = cursor.fetchone()
        
        if existing_admin:
            admin_id = existing_admin[0]
            # Admin yetkisini garanti et
            cursor.execute("UPDATE users SET is_admin = TRUE WHERE user_id = %s", (admin_id,))
            print(f"Default admin kullanıcısı zaten mevcut (user_id: {admin_id})")
            return admin_id
        
        # Admin kullanıcısı oluştur
        admin_email = 'admin@example.com'
        admin_password = 'admin'
        hashed_password = generate_password_hash(admin_password)
        
        cursor.execute("""
            INSERT INTO users (email, password_hash, is_admin, status)
            VALUES (%s, %s, TRUE, 'ACTIVE')
        """, (admin_email, hashed_password))
        
        admin_id = cursor.lastrowid
        
        # Admin için wallet oluştur
        cursor.execute("INSERT INTO wallets (user_id) VALUES (%s)", (admin_id,))
        
        conn.commit()
        print(f"\n[OK] Default admin kullanıcisi olusturuldu:")
        print(f"   Email: {admin_email}")
        print(f"   Sifre: {admin_password}")
        print(f"   User ID: {admin_id}")
        
        return admin_id
        
    except Error as e:
        print(f"Default admin oluşturma hatası: {e}")
        conn.rollback()
        return None

def create_default_rules(conn, cursor, admin_id):
    """Default, Hard ve Easy rule set'lerini oluştur"""
    
    # 3 farklı rule set tanımı
    rule_sets = [
        {
            'name': 'Default Rules',
            'description': 'Varsayılan oyun kuralları - Dengeli payout oranları',
            'house_edge': 5.0,
            'is_active': True,  # Sadece bu aktif
            'rules': [
                ('coinflip_payout', '1.95'),      # %2.5 ev avantajı
                ('roulette_number_payout', '35'), # 35:1 (tek sayı)
                ('roulette_color_payout', '1'),   # 1:1 (kırmızı/siyah)
                ('roulette_parity_payout', '1'),  # 1:1 (tek/çift)
                ('blackjack_payout', '2.5'),      # Blackjack 3:2
                ('blackjack_normal_payout', '2.0') # Normal kazanç 1:1
            ]
        },
        {
            'name': 'Hard Mode',
            'description': 'Zor mod - Düşük payout oranları (Ev avantajı yüksek)',
            'house_edge': 8.0,
            'is_active': False,
            'rules': [
                ('coinflip_payout', '1.92'),      # %4 ev avantajı
                ('roulette_number_payout', '34'), # 34:1 (düşük)
                ('roulette_color_payout', '0.95'),# 0.95:1 (düşük)
                ('roulette_parity_payout', '0.95'),# 0.95:1 (düşük)
                ('blackjack_payout', '2.2'),      # Blackjack 6:5
                ('blackjack_normal_payout', '1.9') # Normal kazanç düşük
            ]
        },
        {
            'name': 'Easy Mode',
            'description': 'Kolay mod - Yüksek payout oranları (Oyuncu avantajlı)',
            'house_edge': 2.0,
            'is_active': False,
            'rules': [
                ('coinflip_payout', '1.98'),      # %1 ev avantajı
                ('roulette_number_payout', '36'), # 36:1 (yüksek)
                ('roulette_color_payout', '1.05'),# 1.05:1 (yüksek)
                ('roulette_parity_payout', '1.05'),# 1.05:1 (yüksek)
                ('blackjack_payout', '2.5'),      # Blackjack 3:2
                ('blackjack_normal_payout', '2.1') # Normal kazanç yüksek
            ]
        }
    ]
    
    try:
        created_count = 0
        
        for rule_set in rule_sets:
            # Rule set var mı kontrol et
            cursor.execute("SELECT rule_set_id FROM rule_sets WHERE name = %s", (rule_set['name'],))
            existing = cursor.fetchone()
            
            if existing:
                print(f"   {rule_set['name']} zaten mevcut.")
                continue
            
            # Rule set oluştur
            cursor.execute("""
                INSERT INTO rule_sets (name, description, house_edge, created_by_admin_id, is_active)
                VALUES (%s, %s, %s, %s, %s)
            """, (rule_set['name'], rule_set['description'], rule_set['house_edge'], 
                  admin_id, rule_set['is_active']))
            
            rule_set_id = cursor.lastrowid
            
            # Kuralları ekle
            for rule_type, rule_param in rule_set['rules']:
                cursor.execute("""
                    INSERT INTO rules (rule_set_id, rule_type, rule_param)
                    VALUES (%s, %s, %s)
                """, (rule_set_id, rule_type, rule_param))
            
            created_count += 1
            status = "AKTIF" if rule_set['is_active'] else "PASIF"
            print(f"\n[OK] {rule_set['name']} olusturuldu (ID: {rule_set_id}) [{status}]")
            print(f"   Ev avantaji: {rule_set['house_edge']}%")
            print("   Kurallar:")
            for rule_type, rule_param in rule_set['rules']:
                print(f"   - {rule_type}: {rule_param}")
        
        if created_count > 0:
            conn.commit()
            print(f"\n[OK] Toplam {created_count} rule set olusturuldu.")
            print("   Default Rules AKTIF durumda.")
            print("   Admin panelden diger rule set'leri aktif edebilirsiniz.")
        
    except Error as e:
        print(f"Rule set oluşturma hatası: {e}")
        conn.rollback()