import mysql.connector
from mysql.connector import Error
from flask import Flask, request, jsonify, session  # <<< 'session' eklendi
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps  # Decorator'lar için hala lazım
import random

# --- YENİ İÇE AKTARMA VE AYARLAR ---
from flask_session import Session  # Yeni kütüphane

# --- 1. Başlangıç Yapılandırması ---
app = Flask(__name__)

# --- OTURUM (SESSION) AYARLARI ---
# Gizli anahtar hala lazım (Cookie'leri imzalamak için)
app.config['SECRET_KEY'] = 'bu-hala-gizli-kalsa-iyi-olur-67890'
# Session'ları nerede tutacağız? 'filesystem' (dosya sistemi) en basitidir.
app.config['SESSION_TYPE'] = 'filesystem'
# Session verilerini saklamak için 'flask_session' adında bir klasör oluşacak
app.config['SESSION_FILE_DIR'] = './flask_session_cache'
# Kalıcı oturum (tarayıcıyı kapatınca silinmesin - Postman için fark etmez)
app.config['SESSION_PERMANENT'] = True
Session(app)  # <<< Flask-Session'ı başlat
# ------------------------------------

# Veritabanı bilgilerin (değişiklik yok)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'game_db',
    'port': 8889
}


# Veritabanı bağlantı yardımcısı (değişiklik yok)
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Veritabanı bağlantı hatası: {e}")
        return None


# --- 2. YETKİLENDİRME DECORATOR'LARI (GÜNCELLENDİ) ---

# Bu fonksiyon, bir kullanıcının giriş yapıp yapmadığını kontrol eder
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 'session' içinde 'user_id' var mı diye bak
        if 'user_id' not in session:
            return jsonify({'message': 'Bu işlemi yapmak için giriş yapmalısınız.'}), 401
        # Varsa, yola devam et
        return f(*args, **kwargs)

    return decorated_function


# Bu fonksiyon, kullanıcının 'admin' olmasını şart koşar
def admin_required(f):
    @wraps(f)
    @login_required  # Önce giriş yapmış mı diye bak
    def decorated_function(*args, **kwargs):
        # 'session' içinde 'is_admin' True mu diye bak
        if not session.get('is_admin'):
            return jsonify({'message': 'Bu işlemi yapmak için admin yetkisi gerekli!'}), 403
        return f(*args, **kwargs)

    return decorated_function


# --- 3. Kullanıcı Yönetimi API Endpoint'leri ---

# /register (Değişiklik yok)
@app.route('/register', methods=['POST'])
def register_user():
    # ... (Bu fonksiyonun içi kütüphane projesindekiyle aynı, DEĞİŞİKLİK YOK) ...
    # ... (Kopyala-yapıştır yapabilirsin) ...
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'message': 'E-posta ve şifre gereklidir!'}), 400
    email = data['email']
    password = data['password']
    hashed_password = generate_password_hash(password)
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({'message': 'Veritabanı sunucu hatası!'}), 500
        cursor = conn.cursor()
        sql_insert_user = "INSERT INTO users (email, password_hash) VALUES (%s, %s)"
        user_val = (email, hashed_password)
        cursor.execute(sql_insert_user, user_val)
        new_user_id = cursor.lastrowid
        sql_insert_wallet = "INSERT INTO wallets (user_id) VALUES (%s)"
        cursor.execute(sql_insert_wallet, (new_user_id,))
        conn.commit()
        return jsonify({'message': 'Kullanıcı ve cüzdanı başarıyla oluşturuldu!', 'user_id': new_user_id}), 201
    except Error as e:
        if e.errno == 1062: return jsonify({'message': 'Bu e-posta adresi zaten kullanılıyor.'}), 409
        print(f"Kayıt hatası: {e}")
        return jsonify({'message': f'Bir hata oluştu: {e}'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# /login (GÜNCELLENDİ: ARTIK TOKEN YERİNE SESSION OLUŞTURUYOR)
@app.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'message': 'E-posta ve şifre gereklidir!'}), 400
    email = data['email']
    password = data['password']
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({'message': 'Veritabanı sunucu hatası!'}), 500
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT id, email, password_hash, is_admin FROM users WHERE email = %s"
        cursor.execute(sql, (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password_hash'], password):

            # --- SESSION OLUŞTURMA BAŞLANGIÇ ---
            # Sunucu bu bilgiyi hatırlar ve bir cookie'ye bağlar
            session['user_id'] = user['id']
            session['email'] = user['email']
            session['is_admin'] = user['is_admin']
            # --- SESSION OLUŞTURMA BİTİŞ ---

            # Token göndermeye gerek yok!
            return jsonify({
                'message': 'Giriş başarılı! Sunucu sizi hatırlayacak.'
            }), 200
        else:
            return jsonify({'message': 'Geçersiz e-posta veya şifre!'}), 401
    except Error as e:
        print(f"Giriş hatası: {e}")
        return jsonify({'message': f'Bir hata oluştu: {e}'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ÇIKIŞ YAP (SESSION'I TEMİZLE)
@app.route('/logout', methods=['POST'])
@login_required  # Çıkış yapmak için giriş yapmış olman lazım
def logout_user():
    session.clear()  # Sunucudaki hafızayı temizle
    return jsonify({'message': 'Başarıyla çıkış yapıldı.'}), 200


# --- 4. Admin API Endpoint'leri (GÜNCELLENDİ) ---

# YENİ KURAL SETİ OLUŞTUR (SADECE ADMIN)
@app.route('/rule-sets', methods=['POST'])
@admin_required  # Bu decorator artık session'ı kontrol ediyor
def create_rule_set():
    # 'current_user' parametresine gerek kalmadı,
    # çünkü kim olduğumuzu 'session'dan biliyoruz

    admin_email = session.get('email')
    print(f"Bu işlemi yapan admin: {admin_email}")

    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'message': 'Kural seti adı (name) gereklidir!'}), 400

    name = data['name']
    description = data.get('description')
    house_edge = data.get('house_edge', 5.0)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({'message': 'Veritabanı sunucu hatası!'}), 500

        cursor = conn.cursor()
        sql = "INSERT INTO rule_sets (name, description, house_edge) VALUES (%s, %s, %s)"
        val = (name, description, house_edge)

        cursor.execute(sql, val)
        conn.commit()

        return jsonify({'message': 'Kural seti başarıyla oluşturuldu!', 'rule_set_id': cursor.lastrowid}), 201

    except Error as e:
        if e.errno == 1062:
            return jsonify({'message': 'Bu isimde bir kural seti zaten var.'}), 409
        print(f"Rule set hatası: {e}")
        return jsonify({'message': f'Bir hata oluştu: {e}'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/wallets/me', methods=['GET'])
@login_required  # Sadece giriş yapmış kullanıcılar
def get_my_wallet():
    # Session'dan kimin giriş yaptığını al
    user_id = session.get('user_id')

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'message': 'Veritabanı sunucu hatası!'}), 500

        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT u.email, w.balance, w.currency, w.updated_at 
            FROM wallets w
            JOIN users u ON w.user_id = u.id
            WHERE w.user_id = %s
        """
        cursor.execute(sql, (user_id,))
        wallet_info = cursor.fetchone()

        if not wallet_info:
            return jsonify({'message': 'Cüzdan bulunamadı!'}), 404

        # 'balance' (Decimal) tipini JSON'a uygun float'a çevir
        wallet_info['balance'] = float(wallet_info['balance'])

        return jsonify({'wallet': wallet_info}), 200

    except Error as e:
        print(f"Cüzdan getirme hatası: {e}")
        return jsonify({'message': f'Bir hata oluştu: {e}'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# KENDİ CÜZDANINA PARA YATIR (DEPOSIT)
@app.route('/wallets/me/deposit', methods=['POST'])
@login_required  # Sadece giriş yapmış kullanıcılar
def deposit_to_wallet():
    # Session'dan kimin giriş yaptığını al
    user_id = session.get('user_id')
    user_email = session.get('email')

    # 2. Gönderilen JSON verisini al ve doğrula
    data = request.get_json()
    if not data or 'amount' not in data:
        return jsonify({'message': 'Yatırılacak miktar (amount) gereklidir!'}), 400

    try:
        # Gelen miktarı sayıya çevirmeyi dene
        amount = float(data['amount'])
    except ValueError:
        return jsonify({'message': 'Miktar (amount) geçerli bir sayı olmalıdır!'}), 400

    if amount <= 0:
        return jsonify({'message': 'Miktar (amount) sıfırdan büyük olmalıdır!'}), 400

    # 3. Veritabanı İşlemleri (ATOMİK TRANSACTION)
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'message': 'Veritabanı sunucu hatası!'}), 500

        # --- ATOMİK İŞLEM BAŞLANGICI ---
        # Değişiklikleri otomatik kaydetmeyi kapat
        conn.start_transaction()

        cursor = conn.cursor(dictionary=True)

        # ADIM A: Cüzdan bakiyesini GÜNCELLE
        # (NOT: 'balance = balance + %s' kullanımı, race condition'ları önler)
        sql_update_wallet = "UPDATE wallets SET balance = balance + %s WHERE user_id = %s"
        cursor.execute(sql_update_wallet, (amount, user_id))

        # ADIM B: Güncel cüzdan bilgilerini (özellikle cüzdan ID'si) al
        sql_get_wallet = "SELECT id, balance FROM wallets WHERE user_id = %s"
        cursor.execute(sql_get_wallet, (user_id,))
        wallet = cursor.fetchone()

        if not wallet:
            # Bu olmamalı (çünkü register'da cüzdan açtık), ama olursa diye...
            conn.rollback()  # İşlemi geri al
            return jsonify({'message': 'Kullanıcıya ait cüzdan bulunamadı!'}), 404

        wallet_id = wallet['id']
        new_balance = wallet['balance']

        # ADIM C: İşlemi 'transactions' tablosuna kaydet

        # DOĞRUSU: 'deposit' için de %s kullan
        sql_log_tx = "INSERT INTO transactions (wallet_id, amount, transaction_type) VALUES (%s, %s, %s)"

        # Artık 3 parametre, 3 tane %s ile tam eşleşiyor
        cursor.execute(sql_log_tx, (wallet_id, amount, 'deposit'))

        # Her iki (UPDATE ve INSERT) işlem de başarılıysa, değişiklikleri onayla
        conn.commit()
        # --- ATOMİK İŞLEM BİTİŞİ ---

        return jsonify({
            'message': f'Başarılı! {amount} VIRTUAL cüzdanınıza eklendi.',
            'user': user_email,
            'new_balance': float(new_balance)  # Decimal'i float'a çevir
        }), 200

    except Error as e:
        # Bir hata olursa (ADIM A, B veya C'de), tüm işlemleri geri al
        if conn:
            conn.rollback()
        print(f"Deposit hatası: {e}")
        return jsonify({'message': f'Bir hata oluştu: {e}'}), 500
    finally:
        # Bağlantıyı her zaman kapat
        if cursor: cursor.close()
        if conn: conn.close()


# Kendi Cüzdanından Para Çek (Withdraw)
@app.route('/wallets/me/withdraw', methods=['POST'])
@login_required  # Sadece giriş yapmış kullanıcılar
def withdraw_from_wallet():
    user_id = session.get('user_id')
    user_email = session.get('email')

    data = request.get_json()
    if not data or 'amount' not in data:
        return jsonify({'message': 'Çeklecek miktar (amount) gereklidir!'}), 400

    try:
        amount = float(data['amount'])
    except ValueError:
        return jsonify({'message': 'Miktar (amount) geçerli bir sayı olmalıdır!'}), 400

    if amount <= 0:
        return jsonify({'message': 'Miktar (amount) sıfırdan büyük olmalıdır!'}), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'message': 'Veritabanı sunucu hatası!'}), 500

        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)

        # <<< HATA 3 BURADAYDI (ve HATA 4) >>>
        # Bakiye kontrolü için satırı kilitliyoruz (FOR UPDATE)
        sql_get_balance = "SELECT balance FROM wallets WHERE user_id = %s FOR UPDATE"
        cursor.execute(sql_get_balance, (user_id,))
        result = cursor.fetchone()

        if not result:
            conn.rollback()
            return jsonify({'message': 'Cüzdan bulunamadı!'}), 404

        # result[0] yerine result['balance'] kullan
        balance = float(result['balance'])

        # <<< HATA 2 BURADAYDI (ve HATA 4) >>>
        # <= yerine < kullan
        if balance < amount:
            conn.rollback()  # <<< İşlemi geri almayı unutma!
            return jsonify({
                'message': 'Yetersiz bakiye!',
                'current_balance': balance,
                'withdraw_amount': amount
            }), 400  # 400 Bad Request veya 403 Forbidden daha uygun

        # ADIM A: Cüzdan bakiyesini GÜNCELLE (Düşür)
        sql_update_wallet = "UPDATE wallets SET balance = balance - %s WHERE user_id = %s"
        cursor.execute(sql_update_wallet, (amount, user_id))

        # ADIM B: Güncel cüzdan bilgilerini al (ID lazım)
        sql_get_wallet = "SELECT id, balance FROM wallets WHERE user_id = %s"
        cursor.execute(sql_get_wallet, (user_id,))
        wallet = cursor.fetchone()

        # (Bu kontrole aslında gerek kalmadı çünkü başta yaptık, ama kalsın)
        if not wallet:
            conn.rollback()
            return jsonify({'message': 'Kullanıcıya ait cüzdan bulunamadı!'}), 404

        wallet_id = wallet['id']
        new_balance = wallet['balance']

        # ADIM C: İşlemi 'transactions' tablosuna kaydet
        sql_log_tx = "INSERT INTO transactions (wallet_id, amount, transaction_type) VALUES (%s, %s, %s)"

        # <<< HATA 1 BURADAYDI >>>
        # 'deposit' yerine 'withdraw' (veya ne tanımladıysan)
        # NOT: Para çektiğimiz için amount'u - (eksi) olarak da kaydedebilirsin,
        # ama 'transaction_type' ile ayırmak daha sağlıklıdır.
        cursor.execute(sql_log_tx, (wallet_id, amount, 'withdraw'))

        conn.commit()

        return jsonify({
            'message': f'Başarılı! {amount} VIRTUAL cüzdanınızdan çekildi.',
            'user': user_email,
            'new_balance': float(new_balance)
        }), 200

    except Error as e:
        if conn:
            conn.rollback()

        # <<< HATA 5 (Bonus) >>>
        print(f"Para Çekme hatası: {e}")
        return jsonify({'message': f'Bir hata oluştu: {e}'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# --- 6. Oyun Oynama API'si (YENİ BÖLÜM) ---

@app.route('/game/play', methods=['POST'])
@login_required  # Oynamak için giriş yapmak ZORUNLU
def play_game():
    # 1. Gelen isteği al ve doğrula
    user_id = session.get('user_id')
    user_email = session.get('email')
    data = request.get_json()

    # Gerekli bilgiler geldi mi?
    if not data or 'amount' not in data or 'choice' not in data:
        return jsonify({'message': 'Bahis (amount) ve seçim (choice) gereklidir!'}), 400

    try:
        bet_amount = float(data['amount'])
        choice = str(data['choice']).lower()  # "YAZI" veya "Tura" -> "yazi", "tura"
    except ValueError:
        return jsonify({'message': 'Bahis (amount) geçerli bir sayı olmalıdır!'}), 400

    # Mantık kontrolleri
    if bet_amount <= 0:
        return jsonify({'message': 'Bahis sıfırdan büyük olmalıdır!'}), 400

    if choice not in ['yazi', 'tura']:
        return jsonify({'message': 'Seçim (choice) "yazi" veya "tura" olmalıdır!'}), 400

    # --- OYUN KURALI (Şimdilik hard-code) ---
    # Kullanıcının istediği 1.95x kazanç oranı
    PAYOUT_MULTIPLIER = 1.95

    conn = None
    cursor = None

    try:
        # 2. ATOMİK İŞLEM BAŞLAT
        conn = get_db_connection()
        if conn is None:
            return jsonify({'message': 'Veritabanı sunucu hatası!'}), 500

        conn.start_transaction()  # Buradan itibaren her şey YA HEP YA HİÇ
        cursor = conn.cursor(dictionary=True)

        # 3. BAKİYEYİ KONTROL ET VE CÜZDANI KİLİTLE (Race Condition Önlemi)
        # "FOR UPDATE" sorgusu, bu işlem bitene kadar başka bir işlemin
        # bu satırı (cüzdanı) değiştirmesini engeller.
        sql_get_wallet = "SELECT id, balance FROM wallets WHERE user_id = %s FOR UPDATE"
        cursor.execute(sql_get_wallet, (user_id,))
        wallet = cursor.fetchone()

        if not wallet:
            conn.rollback()  # İşlemi geri al
            return jsonify({'message': 'Cüzdan bulunamadı!'}), 404

        wallet_id = wallet['id']
        current_balance = float(wallet['balance'])  # DB'den gelen Decimal'i float'a çevir

        # Bakiye yetersiz mi?
        if current_balance < bet_amount:
            conn.rollback()  # İşlemi geri al
            return jsonify({
                'message': 'Yetersiz bakiye!',
                'current_balance': current_balance,
                'bet_amount': bet_amount
            }), 403  # 403 Forbidden (Yasak)

        # 4. BAHİSİ CÜZDANDAN DÜŞ (DEBIT)
        sql_debit = "UPDATE wallets SET balance = balance - %s WHERE id = %s"
        cursor.execute(sql_debit, (bet_amount, wallet_id))

        # 5. BAHİS İŞLEMİNİ KAYDET (transactions)
        sql_log_bet = "INSERT INTO transactions (wallet_id, amount, transaction_type) VALUES (%s, %s, 'bet')"
        cursor.execute(sql_log_bet, (wallet_id, bet_amount))

        # 6. ZURNAYI ÇAL: OYUNU OYNA (Simülasyon)
        game_result = random.choice(['yazi', 'tura'])
        is_win = (choice == game_result)

        new_balance = 0.0

        # 7. SONUCU İŞLE
        if is_win:
            # --- KAZANDI ---
            payout_amount = bet_amount * PAYOUT_MULTIPLIER

            # 7a. KAZANCİ CÜZDANA EKLE (CREDIT)
            sql_credit = "UPDATE wallets SET balance = balance + %s WHERE id = %s"
            cursor.execute(sql_credit, (payout_amount, wallet_id))

            # 7b. KAZANÇ İŞLEMİNİ KAYDET (transactions)
            sql_log_payout = "INSERT INTO transactions (wallet_id, amount, transaction_type) VALUES (%s, %s, 'payout')"
            cursor.execute(sql_log_payout, (wallet_id, payout_amount))

            # 8. İŞLEMİ ONAYLA (COMMIT)
            conn.commit()

            # 9. KULLANICIYA DÖN (Güncel bakiye ile)
            cursor.execute("SELECT balance FROM wallets WHERE id = %s", (wallet_id,))
            new_balance = cursor.fetchone()['balance']

            return jsonify({
                'message': f'Tebrikler, KAZANDINIZ! ({payout_amount:.2f})',
                'your_choice': choice,
                'result': game_result,
                'new_balance': float(new_balance)
            }), 200

        else:
            # --- KAYBETTİ ---
            # Para zaten (Adım 4'te) düşüldü. Ekstra bir şey yapmaya gerek yok.

            # 8. İŞLEMİ ONAYLA (COMMIT)
            # (Sadece bahsin düşüldüğü haliyle onaylanır)
            conn.commit()

            # 9. KULLANICIYA DÖN
            cursor.execute("SELECT balance FROM wallets WHERE id = %s", (wallet_id,))
            new_balance = cursor.fetchone()['balance']

            return jsonify({
                'message': 'Kaybettiniz.',
                'your_choice': choice,
                'result': game_result,
                'new_balance': float(new_balance)
            }), 200

    except Error as e:
        # 10. HATA OLURSA HER ŞEYİ GERİ AL (ROLLBACK)
        # (örn: UPDATE'lerden biri patlarsa)
        if conn:
            conn.rollback()
        print(f"Bahis Oynama Hatası: {e}")
        return jsonify({'message': f'Kritik bir hata oluştu, işlem geri alındı: {e}'}), 500
    finally:
        # Bağlantıyı her zaman kapat
        if cursor: cursor.close()
        if conn: conn.close()

# --- 5. Sunucuyu Başlatma ---
if __name__ == '__main__':
    app.run(debug=True)