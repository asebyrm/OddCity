# Rule System Kullanım Kılavuzu

## 📋 Genel Bakış

Rule System, oyunların payout multiplier'larını database'den yönetmenizi sağlar. Admin'ler rule set'leri oluşturup, kuralları ekleyerek oyunların kazanç oranlarını kontrol edebilir.

---

## 🎮 Desteklenen Rule Type'lar

| Rule Type | Açıklama | Varsayılan Değer |
|-----------|----------|------------------|
| `coinflip_payout` | Coin Flip payout multiplier | 1.95 |
| `roulette_number_payout` | Rulet sayı bahsi payout | 35 |
| `roulette_color_payout` | Rulet renk bahsi payout | 1 |
| `roulette_parity_payout` | Rulet tek/çift bahsi payout | 1 |
| `blackjack_payout` | Blackjack payout (3:2) | 2.5 |
| `blackjack_normal_payout` | Blackjack normal kazanç payout | 2.0 |

---

## 🔧 API Endpoints

### Rule Set Yönetimi

#### 1. Tüm Rule Set'leri Listele
**GET** `/admin/rule-sets`
```json
Response: [
  {
    "rule_set_id": 1,
    "name": "Default Rules",
    "description": "Varsayılan oyun kuralları",
    "house_edge": 5.0,
    "is_active": true,
    "created_at": "...",
    "created_by": "admin@example.com"
  }
]
```

#### 2. Rule Set Oluştur
**POST** `/admin/rule-sets`
```json
{
  "name": "Yeni Kural Seti",
  "description": "Açıklama (opsiyonel)",
  "house_edge": 5.0
}
```

#### 3. Rule Set Detayları
**GET** `/admin/rule-sets/<rule_set_id>`
```json
Response: {
  "rule_set_id": 1,
  "name": "Default Rules",
  "rules": [
    {
      "rule_id": 1,
      "rule_type": "coinflip_payout",
      "rule_param": "1.95",
      "priority": 0
    }
  ]
}
```

#### 4. Rule Set'i Aktif Yap
**POST** `/admin/rule-sets/<rule_set_id>/activate`
- Bu rule set'i aktif yapar ve diğer tüm rule set'leri pasif yapar
- Aynı anda sadece bir rule set aktif olabilir

#### 5. Rule Set'i Pasif Yap
**POST** `/admin/rule-sets/<rule_set_id>/deactivate`

### Rule Yönetimi

#### 6. Rule Ekle
**POST** `/admin/rule-sets/<rule_set_id>/rules`
```json
{
  "rule_type": "coinflip_payout",
  "rule_param": "2.0",
  "priority": 0,
  "is_required": true
}
```

#### 7. Rule Güncelle
**PUT** `/admin/rules/<rule_id>`
```json
{
  "rule_param": "1.98",
  "priority": 1
}
```

#### 8. Rule Sil
**DELETE** `/admin/rules/<rule_id>`

#### 9. Rule Type'ları Listele
**GET** `/admin/rule-types`
```json
Response: {
  "coinflip_payout": "Coin Flip Payout Multiplier",
  "roulette_number_payout": "Roulette Number Payout",
  ...
}
```

---

## 📝 Kullanım Örnekleri

### Örnek 1: Yeni Rule Set Oluştur ve Kuralları Ekle

```bash
# 1. Rule set oluştur
POST /admin/rule-sets
{
  "name": "Yüksek Kazanç",
  "description": "Daha yüksek payout oranları",
  "house_edge": 3.0
}
# Response: {"rule_set_id": 2, ...}

# 2. Coin flip payout'u 2.0 yap
POST /admin/rule-sets/2/rules
{
  "rule_type": "coinflip_payout",
  "rule_param": "2.0",
  "priority": 0
}

# 3. Rulet sayı payout'unu 40 yap
POST /admin/rule-sets/2/rules
{
  "rule_type": "roulette_number_payout",
  "rule_param": "40",
  "priority": 0
}

# 4. Rule set'i aktif yap
POST /admin/rule-sets/2/activate
```

### Örnek 2: Mevcut Rule'u Güncelle

```bash
# Coin flip payout'u 1.98'e düşür
PUT /admin/rules/1
{
  "rule_param": "1.98"
}
```

### Örnek 3: Rule Set Değiştirme

```bash
# Eski rule set'i pasif yap
POST /admin/rule-sets/1/deactivate

# Yeni rule set'i aktif yap
POST /admin/rule-sets/2/activate
```

---

## ⚙️ Nasıl Çalışır?

1. **Aktif Rule Set**: `is_active = TRUE` olan rule set kullanılır
2. **Rule Priority**: Aynı rule_type için birden fazla kural varsa, en yüksek priority'ye sahip olan kullanılır
3. **Default Values**: Eğer aktif rule set'te bir rule_type için kural yoksa, kod içindeki varsayılan değer kullanılır
4. **Real-time**: Rule değişiklikleri hemen etkili olur (cache yok)

---

## 🎯 Oyun Bazında Kullanım

### Coin Flip
- **Rule Type**: `coinflip_payout`
- **Değer**: Payout multiplier (örn: 1.95 = %195 kazanç)
- **Hesaplama**: `payout = bet_amount * multiplier`

### Roulette
- **Rule Types**:
  - `roulette_number_payout`: Sayı bahsi (0-36)
  - `roulette_color_payout`: Renk bahsi (red/black)
  - `roulette_parity_payout`: Tek/çift bahsi
- **Değer**: Payout multiplier (örn: 35 = 35x kazanç)
- **Hesaplama**: `payout = bet_amount * (1 + multiplier)`

### Blackjack
- **Rule Types**:
  - `blackjack_payout`: Blackjack kazanç (3:2)
  - `blackjack_normal_payout`: Normal kazanç
- **Değer**: Payout multiplier
- **Hesaplama**: `payout = bet_amount * multiplier`

---

## ⚠️ Önemli Notlar

1. **Aynı Anda Sadece Bir Rule Set Aktif**: Bir rule set'i aktif yaptığınızda diğerleri otomatik pasif olur
2. **Rule Type Tekrarı**: Aynı rule_set_id içinde aynı rule_type'dan sadece bir tane olmalı
3. **Priority**: Yüksek priority önceliklidir
4. **Rule Param Format**: Sayısal değerler string olarak saklanır ama float'a çevrilir
5. **Default Fallback**: Rule yoksa kod içindeki varsayılan değer kullanılır

---

## 🔍 Test Etme

### 1. Rule Set Oluştur
```bash
curl -X POST http://localhost:3001/admin/rule-sets \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Rules", "house_edge": 5.0}' \
  --cookie "session=..."
```

### 2. Rule Ekle
```bash
curl -X POST http://localhost:3001/admin/rule-sets/1/rules \
  -H "Content-Type: application/json" \
  -d '{"rule_type": "coinflip_payout", "rule_param": "2.0"}' \
  --cookie "session=..."
```

### 3. Aktif Yap
```bash
curl -X POST http://localhost:3001/admin/rule-sets/1/activate \
  --cookie "session=..."
```

### 4. Oyunu Test Et
- Coin flip oynayın
- Payout'un 2.0x olduğunu kontrol edin

---

## 📊 Örnek Senaryolar

### Senaryo 1: House Edge'i Artırma
1. Yeni rule set oluştur
2. Tüm payout'ları düşür (örn: coinflip_payout = 1.90)
3. Rule set'i aktif yap
4. House edge artar, kazanç azalır

### Senaryo 2: Promosyon
1. Yeni rule set oluştur ("Hafta Sonu Promosyonu")
2. Payout'ları yükselt (örn: coinflip_payout = 2.0)
3. Rule set'i aktif yap
4. Hafta sonu sonunda eski rule set'e geri dön

### Senaryo 3: Oyun Bazında Ayarlama
1. Sadece rulet payout'larını değiştir
2. Diğer oyunlar varsayılan değerlerle çalışmaya devam eder

---

*Son Güncelleme: 2024*

