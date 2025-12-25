# OddCity Proje Analizi

## 📋 Genel Bakış

**OddCity**, Flask tabanlı bir kumarhane oyun platformudur. Coin Flip, Rulet ve Blackjack oyunları içerir. Kullanıcılar sanal para ile bahis yapabilir, cüzdan işlemleri gerçekleştirebilir.

---

## 🏗️ Mimari Yapı

### Teknoloji Stack

**Backend:**
- Flask (Python web framework)
- MySQL/MariaDB (Veritabanı)
- Flask-Session (Session yönetimi - filesystem)
- Flask-CORS (Cross-Origin Resource Sharing)
- Werkzeug (Password hashing)

**Frontend:**
- Vanilla JavaScript (ES6+ (ES6+))
- HTML5
- CSS3 (Modern animasyonlar ve 3D transforms)

**Port Yapılandırması:**
- Backend: **Port 3001** (`run.py`)
- Frontend: Backend tarafından servis ediliyor (`frontend_routes.py`)

---

## 📁 Proje Yapısı

```
OddCity/
├── game_api/              # Backend API modülleri
│   ├── __init__.py        # Flask app factory
│   ├── config.py          # Konfigürasyon
│   ├── database.py        # DB bağlantı ve tablo oluşturma
│   ├── auth.py            # Kimlik doğrulama
│   ├── wallet.py          # Cüzdan işlemleri
│   ├── game_logic.py      # Coin flip oyunu
│   ├── roulette.py        # Rulet oyunu
│   ├── blackjack.py       # Blackjack oyunu
│   ├── admin.py           # Admin panel API
│   ├── rules.py           # Kural yönetimi
│   └── frontend_routes.py # Frontend dosyalarını servis etme
├── frontend/              # Kullanıcı frontend
│   ├── index.html
│   ├── script.js
│   └── style.css
├── admin_frontend/        # Admin panel frontend
│   ├── index.html
│   ├── script.js
│   └── style.css
├── run.py                 # Uygulama başlatma
└── reset_db.py            # Veritabanı sıfırlama
```

---

## 🎮 Oyunlar

### 1. Coin Flip (Yazı Tura)
- **Endpoint:** `POST /game/play`
- **Payout:** 1.95x (5% house edge)
- **Seçenekler:** yazi, tura

### 2. Roulette (Rulet)
- **Endpoint:** `POST /game/roulette/play`
- **Bahis Türleri:**
  - Number (0-36): 35x payout
  - Color (red/black): 2x payout
  - Parity (odd/even): 2x payout
- **Avrupa Ruleti:** 0-36 (37 sayı)

### 3. Blackjack
- **Endpoints:**
  - `POST /game/blackjack/start` - Oyun başlat
  - `POST /game/blackjack/hit` - Kart çek
  - `POST /game/blackjack/stand` - Dur
- **Özellikler:**
  - Blackjack: 2.5x payout (3:2)
  - Normal kazanç: 2x payout
  - Dealer <17'de kart çeker
  - Ace değeri otomatik hesaplanır

---

## 🗄️ Veritabanı Şeması

### Aktif Kullanılan Tablolar

1. **users** - Kullanıcı bilgileri
   - `user_id`, `email`, `password_hash`, `status`, `is_admin`

2. **wallets** - Cüzdan bilgileri
   - `wallet_id`, `user_id`, `balance`, `currency`

3. **transactions** - İşlem geçmişi
   - `tx_id`, `user_id`, `wallet_id`, `tx_type`, `amount`, `currency`
   - `tx_type`: DEPOSIT, BET, PAYOUT, WITHDRAW

4. **rule_sets** - Kural setleri (Admin)
   - `rule_set_id`, `name`, `description`, `house_edge`, `is_active`

5. **rules** - Kurallar (Admin)
   - `rule_id`, `rule_set_id`, `rule_type`, `rule_param`, `priority`

### Kullanılmayan Tablolar (Altyapı Mevcut)

6. **games** - Oyun kayıtları (oluşturulmuş ama kullanılmıyor)
7. **bets** - Bahis kayıtları (oluşturulmuş ama kullanılmıyor)
8. **payouts** - Ödeme kayıtları (oluşturulmuş ama kullanılmıyor)
9. **logs** - Log kayıtları (oluşturulmuş ama kullanılmıyor)

---

## 🔌 API Endpoints

### Kimlik Doğrulama
- `POST /register` - Kullanıcı kaydı
- `POST /login` - Giriş (session oluşturur)
- `POST /logout` - Çıkış

### Cüzdan İşlemleri
- `GET /wallets/me` - Cüzdan bilgileri
- `POST /wallets/me/deposit` - Para yatırma
- `POST /wallets/me/withdraw` - Para çekme

### Oyunlar
- `POST /game/play` - Coin flip
- `POST /game/roulette/play` - Rulet
- `POST /game/blackjack/start` - Blackjack başlat
- `POST /game/blackjack/hit` - Blackjack kart çek
- `POST /game/blackjack/stand` - Blackjack dur

### Admin (Admin yetkisi gerekli)
- `GET /admin/users` - Tüm kullanıcıları listele
- `POST /admin/user/<id>/ban` - Kullanıcı yasakla
- `POST /admin/user/<id>/unban` - Kullanıcı yasağını kaldır
- `GET /admin/user/<id>/history` - Kullanıcı işlem geçmişi

### Kural Yönetimi (Admin)
- `POST /rule-sets` - Kural seti oluştur

### Frontend Servis
- `GET /` - Ana sayfa (frontend/index.html)
- `GET /admin/` - Admin panel (admin_frontend/index.html)

---

## 🔒 Güvenlik Analizi

### ✅ İyi Yönler

1. **Password Hashing**
   - Werkzeug'un `generate_password_hash` ve `check_password_hash` kullanılıyor
   - Passwords asla plain text saklanmıyor

2. **SQL Injection Koruması**
   - Tüm sorgular parameterized queries kullanıyor
   - String concatenation yok

3. **Transaction Safety**
   - Wallet işlemleri transaction içinde
   - `FOR UPDATE` lock kullanılıyor (race condition koruması)
   - Hata durumunda rollback

4. **Session Yönetimi**
   - Server-side session (Flask-Session)
   - Session-based authentication
   - Protected routes (`@login_required`, `@admin_required`)

5. **Input Validation**
   - Amount validation (positive numbers)
   - Choice validation (enum checks)
   - Bet type validation

### ⚠️ Güvenlik Endişeleri

1. **CORS Yapılandırması**
   - Çok geniş: `origins=["file://", "http://localhost:*", "http://127.0.0.1:*"]`
   - Production'da kısıtlanmalı

2. **Secret Key**
   - Hardcoded fallback: `'bu-hala-gizli-kalsa-iyi-olur-67890'`
   - Environment variable kullanılmalı

3. **Session Storage**
   - Filesystem-based (scalability sorunu)
   - Session expiration yok
   - Session dosyaları proje dizininde

4. **Rate Limiting Yok**
   - Brute force saldırılarına açık
   - API abuse koruması yok

5. **Error Messages**
   - Bazı hatalarda database detayları gösteriliyor
   - Kullanıcıya fazla bilgi veriliyor

6. **CSRF Koruması Yok**
   - Session-based auth var ama CSRF token yok

---

## 💻 Kod Kalitesi

### ✅ Güçlü Yönler

1. **Temiz Mimari**
   - Blueprint pattern kullanımı
   - Modüler yapı
   - Separation of concerns

2. **Error Handling**
   - Try-catch blokları
   - Transaction rollback
   - Proper cleanup (cursor/connection closing)

3. **Code Organization**
   - Her modül kendi sorumluluğunda
   - Helper functions (get_color, calculate_hand_value)
   - Decorator pattern (auth)

4. **Database Design**
   - İyi tasarlanmış şema
   - Foreign key constraints
   - Proper data types

### ⚠️ İyileştirme Alanları

1. **Hardcoded Values**
   - `PAYOUT_MULTIPLIER = 1.95` (game_logic.py)
   - `PAYOUTS` dictionary (roulette.py)
   - Rule system var ama kullanılmıyor

2. **Database Connection**
   - Her request'te yeni connection
   - Connection pooling yok
   - Flask-SQLAlchemy kullanılabilir

3. **Code Duplication**
   - Wallet balance check tekrarlanıyor
   - Transaction logging benzer kodlar
   - Error handling patterns tekrar ediyor

4. **Unused Infrastructure**
   - `games`, `bets`, `payouts`, `logs` tabloları oluşturulmuş ama kullanılmıyor
   - Rule system altyapısı var ama oyunlarda kullanılmıyor

5. **Frontend API URL**
   - `this.apiUrl = ''` - Boş string
   - Backend'den servis edildiği için relative path kullanılabilir

6. **Blackjack Session State**
   - Oyun durumu Flask session'da saklanıyor
   - Session expire olursa oyun kaybolur
   - Database'de persist edilmeli

---

## 🐛 Potansiyel Sorunlar

### Kritik

1. **Blackjack Session Dependency**
   - Oyun durumu session'da
   - Server restart'ta kaybolur
   - Session expire olursa oyun kaybolur

2. **Race Conditions (Kısmen Çözülmüş)**
   - `FOR UPDATE` kullanılıyor ama her yerde değil
   - Concurrent requests sorun yaratabilir

3. **Balance Consistency**
   - Balance birden fazla yerde güncelleniyor
   - Transaction başarısız olursa tutarsızlık olabilir

### Orta Öncelik

1. **Game State Persistence Yok**
   - Blackjack oyunları database'de saklanmıyor
   - Recovery mekanizması yok

2. **Transaction Logging**
   - Transactions loglanıyor ama games/bets ile linklenmiyor
   - `reference_type` ve `reference_id` kullanılmıyor

3. **Bet Limits Yok**
   - Kullanıcı tüm bakiyesini bahis yapabilir
   - Min/max bet kontrolü yok

### Düşük Öncelik

1. **Performance**
   - Database index'leri belirtilmemiş
   - Query optimization yok
   - N+1 query potansiyeli (admin endpoints)

2. **Scalability**
   - Filesystem sessions scale olmaz
   - Load balancing desteği yok
   - Single database connection per request

---

## 📊 İstatistikler

- **Backend Dosyaları:** 10 Python modülü
- **Frontend Dosyaları:** 3 dosya (HTML, CSS, JS)
- **Veritabanı Tabloları:** 9 tablo (4 aktif, 5 kullanılmıyor)
- **API Endpoints:** ~15 endpoint
- **Oyunlar:** 3 tam implementasyon
- **Tahmini Kod Satırı:** ~2000+

---

## 💡 Öneriler

### Hemen Yapılabilir

1. **Frontend API URL Düzeltmesi**
   ```javascript
   // script.js'de
   this.apiUrl = window.location.origin; // Backend'den servis edildiği için
   ```

2. **Secret Key Environment Variable**
   ```python
   # config.py'de
   SECRET_KEY = os.environ.get('SECRET_KEY')
   if not SECRET_KEY:
       raise ValueError("SECRET_KEY environment variable must be set!")
   ```

3. **Error Message İyileştirme**
   - Database hatalarını kullanıcıya gösterme
   - Generic error messages

### Kısa Vadede

1. **Rule System Entegrasyonu**
   - Oyunlarda hardcoded değerler yerine rule system kullan
   - Admin panel'den oyun ayarları yapılabilir

2. **Game State Persistence**
   - Blackjack oyunlarını database'de sakla
   - Oyun recovery mekanizması

3. **Connection Pooling**
   - SQLAlchemy veya connection pooler kullan
   - Performance iyileştirmesi

4. **Bet Limits**
   - Oyun bazında min/max bet
   - Configurable limits

### Uzun Vadede

1. **Testing**
   - Unit tests (game logic)
   - Integration tests (API)
   - Frontend tests

2. **Monitoring & Logging**
   - Logging system implementasyonu
   - Analytics
   - Error tracking

3. **Performance Optimization**
   - Database indexes
   - Query optimization
   - Caching layer

4. **Security Hardening**
   - CSRF protection
   - Rate limiting
   - Input sanitization
   - Security headers

---

## 🎯 Sonuç

**OddCity** iyi yapılandırılmış bir proje. Temel güvenlik önlemleri alınmış, kod organizasyonu temiz. Ancak production'a geçmeden önce:

1. ✅ Güvenlik iyileştirmeleri (CORS, secret key, rate limiting)
2. ✅ Game state persistence
3. ✅ Rule system entegrasyonu
4. ✅ Error handling iyileştirmeleri
5. ✅ Performance optimizasyonları

yapılmalı.

**Genel Değerlendirme:** ⭐⭐⭐⭐ (4/5)
- Temiz kod yapısı
- İyi güvenlik temelleri
- Bazı iyileştirmeler gerekli

---

*Analiz Tarihi: 2024*

