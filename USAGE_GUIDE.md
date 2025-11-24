# OddCity Coin Flip Game - Kullanım Rehberi

## 🎯 Genel Bakış

OddCity, animasyonlu coin flip oyunu sunan bir web uygulamasıdır. Kullanıcılar sanal para ile bahis oynayabilir, cüzdan işlemleri yapabilir ve gerçek zamanlı coin flip animasyonlarını izleyebilirler.

## 🚀 Kurulum ve Çalıştırma

### Gereksinimler
- Python 3.7+
- MySQL/MariaDB
- Modern web browser (Chrome, Firefox, Safari)

### Adım 1: Repository'yi İndir
```bash
git clone https://github.com/asebyrm/OddCity.git
cd OddCity
```

### Adım 2: Python Bağımlılıklarını Yükle
```bash
pip install flask flask-session flask-cors mysql-connector-python werkzeug
```

### Adım 3: Veritabanı Kurulumu
1. MySQL/MariaDB'yi başlat
2. `game_db` isimli veritabanını oluştur
3. Gerekli tabloları oluştur (users, wallets, transactions, rule_sets)

### Adım 4: Konfigürasyon
`game_api/config.py` dosyasında veritabanı ayarlarını kontrol edin:
```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',  # Kendi şifrenizi girin
    'database': 'game_db',
    'port': 8889  # Kendi port'unuzu girin
}
```

### Adım 5: Uygulamayı Çalıştır

**Backend Server (Port 3001):**
```bash
python run.py
```

**Frontend Server (Port 8080):**
```bash
cd frontend
python -m http.server 8080
```

### Adım 6: Tarayıcıda Aç
Tarayıcınızda şu adrese gidin: `http://localhost:8080`

---

## 🎮 Kullanım Kılavuzu

### 1. Hesap Oluşturma
1. Ana sayfada **"Kayıt Ol"** butonuna tıklayın
2. E-posta ve şifrenizi girin
3. **"Kayıt Ol"** butonuna tıklayın
4. Başarılı kayıt sonrası otomatik olarak cüzdan oluşturulur

### 2. Giriş Yapma
1. **"Giriş Yap"** butonuna tıklayın
2. E-posta ve şifrenizi girin
3. **"Giriş Yap"** butonuna tıklayın

### 3. Cüzdan İşlemleri

#### Para Yatırma
1. **"💰 Para Yatır"** butonuna tıklayın
2. Yatırmak istediğiniz miktarı girin
3. **"Onayla"** butonuna tıklayın

#### Para Çekme
1. **"💸 Para Çek"** butonuna tıklayın
2. Çekmek istediğiniz miktarı girin (bakiyenizden fazla olamaz)
3. **"Onayla"** butonuna tıklayın

### 4. Coin Flip Oyunu Oynama

#### Oyun Adımları
1. **Bahis Miktarını Ayarlayın:**
   - Slider ile veya doğrudan rakam girerek bahis miktarını belirleyin
   - Minimum: 1 VIRTUAL, Maksimum: Mevcut bakiyeniz

2. **Tahmininizi Yapın:**
   - **🪙 YAZI** veya **🌟 TURA** butonlarından birini seçin
   - Seçilen buton mavi renkte vurgulanır

3. **Oyunu Başlatın:**
   - **🎮 OYNA!** butonuna tıklayın
   - Coin 3 saniye boyunca animasyonlu şekilde döner

4. **Sonucu Görün:**
   - Kazanırsanız: **🎉 KAZANDIN!** mesajı ve 1.95x kazanç
   - Kaybederseniz: **😔 KAYBETTİN!** mesajı
   - Bakiyeniz otomatik güncellenir

### 5. Oyun Geçmişi
- **Son Oyunlar** bölümünde son 10 oyununuzun sonuçlarını görebilirsiniz
- **🪙** simgesi YAZI sonucunu, **🌟** simgesi TURA sonucunu gösterir
- Yeşil renkli ikonlar kazandığınız, kırmızı renkli ikonlar kaybettiğiniz oyunları temsil eder

---

## 🎯 Oyun Kuralları

### Kazanç Oranı
- **Doğru tahmin:** Bahis × 1.95 = Kazanç
- **Yanlış tahmin:** Bahis kaybedilir

### Bahis Limitleri
- **Minimum bahis:** 1.00 VIRTUAL
- **Maksimum bahis:** Mevcut bakiyeniz
- **Yetersiz bakiye durumunda oyun oynanamaz**

### İşlem Güvenliği
- Tüm işlemler atomik transaction'larla korunur
- Race condition'lara karşı database kilitleme kullanılır
- Session tabanlı güvenli kimlik doğrulama

---

## 🎨 Görsel Özellikler

### Animasyonlar
- **3D Coin Flip:** Gerçekçi physics ile coin dönüşü
- **Hover Efektleri:** Butonlarda ve coin üzerinde etkileşimli animasyonlar
- **Loading States:** İşlem sırasında spinner animasyonları
- **Result Animations:** Kazanç durumunda pulse efekti

### Responsive Tasarım
- Desktop, tablet ve mobil uyumlu
- Modern gradient arkaplanlar
- Glassmorphism efektleri
- Smooth geçişler ve hover efektleri

---

## 🔧 Teknik Özellikler

### Frontend
- **HTML5:** Semantic markup
- **CSS3:** Flexbox, Grid, 3D Transforms, Animations
- **JavaScript:** ES6+, Async/Await, Fetch API
- **Responsive:** Mobile-first approach

### Backend
- **Flask:** Python web framework
- **Flask-Session:** Dosya tabanlı session yönetimi
- **Flask-CORS:** Cross-origin resource sharing
- **MySQL:** İlişkisel veritabanı
- **Werkzeug:** Password hashing

### API Endpoints
- `POST /register` - Kullanıcı kaydı
- `POST /login` - Kullanıcı girişi
- `POST /logout` - Kullanıcı çıkışı
- `GET /wallets/me` - Cüzdan bilgileri
- `POST /wallets/me/deposit` - Para yatırma
- `POST /wallets/me/withdraw` - Para çekme
- `POST /game/play` - Oyun oynama
- `POST /rule-sets` - Kural seti oluşturma (Admin)

---

## ⚠️ Önemli Notlar

### Port Ayarları
- **Backend:** http://localhost:3001
- **Frontend:** http://localhost:8080
- **macOS kullanıcıları:** Port 5000 AirPlay Receiver tarafından kullanıldığı için 3001 kullanıyoruz

### Güvenlik
- Şifreler hash'lenerek saklanır
- Session bilgileri sunucu tarafında tutulur
- CORS koruması aktif
- SQL Injection koruması (parameterized queries)

### Performans
- Optimized CSS animations
- Efficient DOM manipulation
- Minimal API calls
- Background transaction processing

---

## 🐛 Sorun Giderme

### Bağlantı Hatası
- Backend'in çalıştığından emin olun (`python run.py`)
- Frontend'in çalıştığından emin olun (`python -m http.server 8080`)
- Port'ların (3001, 8080) boş olduğunu kontrol edin

### Veritabanı Hatası
- MySQL/MariaDB'nin çalıştığından emin olun
- `game_api/config.py` ayarlarını kontrol edin
- Veritabanı ve tabloların oluşturulduğunu onaylayın

### Session Hatası
- Tarayıcı cache'ini temizleyin
- Cookies'leri etkinleştirin
- `flask_session_cache` klasörünü silin (otomatik oluşacak)

---

## 📞 Destek

Herhangi bir sorun yaşarsanız:
1. Browser Console'da hata mesajlarını kontrol edin (F12)
2. Backend loglarını kontrol edin
3. API dokümantasyonu için `API_Examples.md` dosyasına bakın

---

## 🎉 Keyifli Oyunlar!

OddCity Coin Flip oyununun tadını çıkarın! 🪙✨