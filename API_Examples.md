# Game API - Örnek İstekler Rehberi

## Giriş
Bu belge, Game API'nin tüm endpoint'leri için örnek HTTP istekleri içerir. API, coin flip oyunu için kullanıcı yönetimi, cüzdan işlemleri ve oyun fonksiyonlarını sağlar.

**Base URL:** `http://localhost:5000`

---

## 1. Kullanıcı Kayıt ve Giriş İşlemleri

### 1.1 Kullanıcı Kaydı
**Endpoint:** `POST /register`

**Açıklama:** Yeni kullanıcı kaydı yapar ve otomatik olarak cüzdan oluşturur.

**İstek Örneği:**
```http
POST http://localhost:5000/register
Content-Type: application/json

{
  "email": "kullanici@example.com",
  "password": "güvenli123"
}
```

**Başarılı Yanıt (201):**
```json
{
  "message": "Kullanıcı ve cüzdanı başarıyla oluşturuldu!",
  "user_id": 1
}
```

**Hata Yanıtları:**
- **400:** E-posta ve şifre gereklidir!
- **409:** Bu e-posta adresi zaten kullanılıyor.

---

### 1.2 Kullanıcı Girişi
**Endpoint:** `POST /login`

**Açıklama:** Kullanıcı girişi yapar ve session oluşturur.

**İstek Örneği:**
```http
POST http://localhost:5000/login
Content-Type: application/json

{
  "email": "kullanici@example.com",
  "password": "güvenli123"
}
```

**Başarılı Yanıt (200):**
```json
{
  "message": "Giriş başarılı! Sunucu sizi hatırlayacak."
}
```

**Hata Yanıtları:**
- **400:** E-posta ve şifre gereklidir!
- **401:** Geçersiz e-posta veya şifre!

---

### 1.3 Kullanıcı Çıkışı
**Endpoint:** `POST /logout`

**Açıklama:** Kullanıcı oturumunu sonlandırır.

**İstek Örneği:**
```http
POST http://localhost:5000/logout
```

**Başarılı Yanıt (200):**
```json
{
  "message": "Başarıyla çıkış yapıldı."
}
```

**Hata Yanıtları:**
- **401:** Bu işlemi yapmak için giriş yapmalısınız.

---

## 2. Cüzdan İşlemleri

### 2.1 Cüzdan Bilgilerini Görüntüleme
**Endpoint:** `GET /wallets/me`

**Açıklama:** Giriş yapmış kullanıcının cüzdan bilgilerini getirir.

**İstek Örneği:**
```http
GET http://localhost:5000/wallets/me
```

**Başarılı Yanıt (200):**
```json
{
  "wallet": {
    "email": "kullanici@example.com",
    "balance": 1000.0,
    "currency": "VIRTUAL",
    "updated_at": "2023-11-24T10:30:00"
  }
}
```

**Hata Yanıtları:**
- **401:** Bu işlemi yapmak için giriş yapmalısınız.
- **404:** Cüzdan bulunamadı!

---

### 2.2 Cüzdana Para Yatırma
**Endpoint:** `POST /wallets/me/deposit`

**Açıklama:** Kullanıcının cüzdanına para yatırır.

**İstek Örneği:**
```http
POST http://localhost:5000/wallets/me/deposit
Content-Type: application/json

{
  "amount": 500.0
}
```

**Başarılı Yanıt (200):**
```json
{
  "message": "Başarılı! 500.0 VIRTUAL cüzdanınıza eklendi.",
  "user": "kullanici@example.com",
  "new_balance": 1500.0
}
```

**Hata Yanıtları:**
- **400:** Yatırılacak miktar (amount) gereklidir!
- **400:** Miktar (amount) sıfırdan büyük olmalıdır!
- **401:** Bu işlemi yapmak için giriş yapmalısınız.

---

### 2.3 Cüzdanından Para Çekme
**Endpoint:** `POST /wallets/me/withdraw`

**Açıklama:** Kullanıcının cüzdanından para çeker.

**İstek Örneği:**
```http
POST http://localhost:5000/wallets/me/withdraw
Content-Type: application/json

{
  "amount": 200.0
}
```

**Başarılı Yanıt (200):**
```json
{
  "message": "Başarılı! 200.0 VIRTUAL cüzdanınızdan çekildi.",
  "user": "kullanici@example.com",
  "new_balance": 1300.0
}
```

**Hata Yanıtları:**
- **400:** Çeklecek miktar (amount) gereklidir!
- **400:** Yetersiz bakiye!
- **401:** Bu işlemi yapmak için giriş yapmalısınız.

---

## 3. Oyun İşlemleri

### 3.1 Coin Flip Oyunu Oynama
**Endpoint:** `POST /game/play`

**Açıklama:** Coin flip oyunu oynar. Kazanç oranı 1.95x'tir.

**İstek Örneği:**
```http
POST http://localhost:5000/game/play
Content-Type: application/json

{
  "amount": 100.0,
  "choice": "yazi"
}
```

**Kazanma Durumu (200):**
```json
{
  "message": "Tebrikler, KAZANDINIZ! (195.00)",
  "your_choice": "yazi",
  "result": "yazi",
  "new_balance": 1395.0
}
```

**Kaybetme Durumu (200):**
```json
{
  "message": "Kaybettiniz.",
  "your_choice": "yazi",
  "result": "tura",
  "new_balance": 1200.0
}
```

**Hata Yanıtları:**
- **400:** Bahis (amount) ve seçim (choice) gereklidir!
- **400:** Seçim (choice) "yazi" veya "tura" olmalıdır!
- **401:** Bu işlemi yapmak için giriş yapmalısınız.
- **403:** Yetersiz bakiye!

**Geçerli Seçimler:**
- `"yazi"` - Yazı tarafı
- `"tura"` - Tura tarafı

---

## 4. Admin İşlemleri

### 4.1 Kural Seti Oluşturma
**Endpoint:** `POST /rule-sets`

**Açıklama:** Yeni oyun kuralları seti oluşturur. (Sadece admin kullanıcılar)

**İstek Örneği:**
```http
POST http://localhost:5000/rule-sets
Content-Type: application/json

{
  "name": "Yüksek Kazanç Kuralları",
  "description": "Daha yüksek kazanç oranları ile oyun",
  "house_edge": 3.0
}
```

**Başarılı Yanıt (201):**
```json
{
  "message": "Kural seti başarıyla oluşturuldu!",
  "rule_set_id": 1
}
```

**Hata Yanıtları:**
- **400:** Kural seti adı (name) gereklidir!
- **401:** Bu işlemi yapmak için giriş yapmalısınız.
- **403:** Bu işlemi yapmak için admin yetkisi gerekli!
- **409:** Bu isimde bir kural seti zaten var.

---

## 5. Örnek İstek Senaryoları

### Senaryo 1: Yeni Kullanıcı Kaydı ve İlk Oyun

1. **Kayıt ol:**
```http
POST /register
{
  "email": "yenioyuncu@example.com",
  "password": "şifre123"
}
```

2. **Giriş yap:**
```http
POST /login
{
  "email": "yenioyuncu@example.com",
  "password": "şifre123"
}
```

3. **Cüzdana para yatır:**
```http
POST /wallets/me/deposit
{
  "amount": 1000.0
}
```

4. **Oyun oyna:**
```http
POST /game/play
{
  "amount": 50.0,
  "choice": "tura"
}
```

### Senaryo 2: Mevcut Kullanıcı Cüzdan Kontrolü

1. **Giriş yap:**
```http
POST /login
{
  "email": "mevcutoyuncu@example.com",
  "password": "eski_şifre"
}
```

2. **Bakiye kontrolü:**
```http
GET /wallets/me
```

3. **Gerekirse para yatır:**
```http
POST /wallets/me/deposit
{
  "amount": 250.0
}
```

---

## 6. Önemli Notlar

### Session Yönetimi
- API, session tabanlı kimlik doğrulama kullanır
- Giriş yaptıktan sonra tüm istekler otomatik olarak kimlik doğrulanır
- Session bilgileri sunucuda dosya sistemi olarak saklanır

### Hata Kodları
- **400:** Bad Request - Geçersiz istek verisi
- **401:** Unauthorized - Giriş gerekli
- **403:** Forbidden - Yetkisiz işlem
- **404:** Not Found - Kaynak bulunamadı
- **409:** Conflict - Çakışma (örn: email zaten var)
- **500:** Internal Server Error - Sunucu hatası

### Para Birimi
- Tüm tutarlar "VIRTUAL" para birimi cinsindendir
- Ondalık sayılar kabul edilir (örn: 150.50)

### Transaction Logları
- Tüm para işlemleri otomatik olarak loglanır
- İşlem tipleri: 'deposit', 'withdraw', 'bet', 'payout'

### Güvenlik
- Şifreler hash'lenerek saklanır
- Database işlemleri atomic transaction'larla korunur
- Race condition'lara karşı FOR UPDATE kullanılır

---

Bu belgede yer alan tüm örnekler gerçek API endpoint'leri ile test edilebilir. Postman, cURL veya benzeri HTTP istemcileri kullanarak bu istekleri gönderebilirsiniz.