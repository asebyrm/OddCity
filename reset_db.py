from game_api.database import get_db_connection, init_db

def reset_db():
    conn = get_db_connection()
    if conn is None:
        print("Veritabanına bağlanılamadı.")
        return

    cursor = conn.cursor()
    
    # Sırayla tabloları sil (Foreign Key kısıtlamaları yüzünden sıra önemli)
    tables_to_drop = [
        'logs', 'game_rule_snapshots', 'transactions', 'payouts', 'bets', 'games', 'rules', 'rule_sets', 'wallets', 'users'
    ]

    try:
        # Foreign key kontrolünü geçici olarak kapat
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        for table in tables_to_drop:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"Tablo silindi: {table}")
            
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
        print("Tüm tablolar başarıyla silindi.")
        
        # Yeniden oluştur
        print("Tablolar yeniden oluşturuluyor...")
        init_db()
        
    except Exception as e:
        print(f"Hata oluştu: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    reset_db()
