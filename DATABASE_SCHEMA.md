# Database Schema - Tablo İlişkileri (Güncellenmiş)

> Son güncelleme: Index'ler eklendi, tablo ilişkileri optimize edildi

## 📊 ER Diagram (Entity Relationship)

```
┌─────────────┐
│   users     │
│─────────────│
│ user_id (PK)│
│ email       │
│ password    │
│ is_admin    │
└──────┬──────┘
       │
       │ 1:N
       │
       ├─────────────────────────────────────┐
       │                                     │
       │                                     │
┌──────▼──────┐                    ┌─────────▼─────────┐
│  wallets    │                    │   rule_sets       │
│─────────────│                    │──────────────────│
│ wallet_id   │                    │ rule_set_id (PK) │
│ user_id (FK)│                    │ name              │
│ balance     │                    │ house_edge        │
│ currency    │                    │ is_active         │
└──────┬──────┘                    │ created_by (FK)  │
       │                           └───────┬───────────┘
       │                                   │
       │ 1:N                               │ 1:N
       │                                   │
       │                                   │
┌──────▼──────────┐              ┌────────▼────────┐
│ transactions    │              │     rules       │
│─────────────────│              │─────────────────│
│ tx_id (PK)      │              │ rule_id (PK)     │
│ user_id (FK)    │              │ rule_set_id (FK) │
│ wallet_id (FK)  │              │ rule_type        │
│ tx_type         │              │ rule_param       │
│ amount          │              │ priority         │
└─────────────────┘              └──────────────────┘
       │
       │ (DEPOSIT/WITHDRAW only)
       │
       │
┌──────▼──────┐
│   games     │
│─────────────│
│ game_id (PK)│
│ user_id (FK)│──────────┐
│ rule_set_id (FK)───────┤
│ game_type             │
│ game_result           │
│ status                │
│ started_at            │
│ ended_at              │
└──────┬────────────────┘
       │
       │ 1:N
       │
       │
┌──────▼──────────┐
│     bets        │
│─────────────────│
│ bet_id (PK)     │
│ game_id (FK)    │
│ user_id (FK)    │
│ bet_type        │
│ bet_value       │
│ stake_amount    │
└──────┬──────────┘
       │
       │ 1:1
       │
       │
┌──────▼──────────┐
│    payouts      │
│─────────────────│
│ payout_id (PK)  │
│ bet_id (FK)     │
│ win_amount      │
│ outcome         │
└─────────────────┘

┌──────────────────────┐
│ game_rule_snapshots  │
│──────────────────────│
│ snapshot_id (PK)     │
│ game_id (FK)         │
│ rule_set_id (FK)     │
│ rule_type            │
│ rule_value           │
└──────────────────────┘
```

---

## 🔗 İlişki Detayları

### 1. **users** → **wallets** (1:N)
- Bir kullanıcının bir cüzdanı var
- `wallets.user_id` → `users.user_id`

### 2. **users** → **rule_sets** (1:N)
- Admin kullanıcılar rule set oluşturabilir
- `rule_sets.created_by_admin_id` → `users.user_id`

### 3. **rule_sets** → **rules** (1:N)
- Bir rule set'te birden fazla rule olabilir
- `rules.rule_set_id` → `rule_sets.rule_set_id`

### 4. **users** → **games** (1:N)
- Bir kullanıcı birden fazla oyun oynayabilir
- `games.user_id` → `users.user_id`

### 5. **rule_sets** → **games** (1:N)
- Bir rule set birden fazla oyunda kullanılabilir
- `games.rule_set_id` → `rule_sets.rule_set_id`

### 6. **games** → **bets** (1:N)
- Bir oyunda birden fazla bahis olabilir (şu an 1:1 ama gelecekte çoklu bahis için)
- `bets.game_id` → `games.game_id`

### 7. **users** → **bets** (1:N)
- Bir kullanıcı birden fazla bahis yapabilir
- `bets.user_id` → `users.user_id`

### 8. **bets** → **payouts** (1:1)
- Her bahis için bir payout kaydı var (kazanç veya kayıp)
- `payouts.bet_id` → `bets.bet_id` (UNIQUE)

### 9. **users** → **transactions** (1:N)
- Bir kullanıcının birden fazla transaction'ı olabilir
- `transactions.user_id` → `users.user_id`

### 10. **wallets** → **transactions** (1:N)
- Bir cüzdanın birden fazla transaction'ı olabilir
- `transactions.wallet_id` → `wallets.wallet_id`

### 11. **games** → **game_rule_snapshots** (1:N)
- Bir oyun için birden fazla rule snapshot olabilir (her rule type için bir snapshot)
- `game_rule_snapshots.game_id` → `games.game_id`

### 12. **rule_sets** → **game_rule_snapshots** (1:N)
- Bir rule set birden fazla snapshot'ta kullanılabilir
- `game_rule_snapshots.rule_set_id` → `rule_sets.rule_set_id`

---

## 📋 Veri Akışı Örnekleri

### Örnek 1: Coin Flip Oyunu

```
1. User oyun oynar
   └─> games tablosuna kayıt (game_id=1, user_id=5, rule_set_id=1, game_type='coinflip')

2. Bahis yapılır
   └─> bets tablosuna kayıt (bet_id=1, game_id=1, user_id=5, bet_type='choice', bet_value='yazi', stake_amount=10)

3. Rule snapshot oluşturulur
   └─> game_rule_snapshots tablosuna kayıt (game_id=1, rule_set_id=1, rule_type='coinflip_payout', rule_value=1.95)

4. Oyun sonucu
   └─> games.game_result güncellenir
   └─> Eğer kazanç varsa:
       └─> payouts tablosuna kayıt (bet_id=1, win_amount=19.5, outcome='WIN')
```

### Örnek 2: Rule Set Değişikliği

```
1. Admin rule set değiştirir
   └─> rule_sets.is_active = FALSE (eski)
   └─> rule_sets.is_active = TRUE (yeni)

2. Yeni oyun oynanır
   └─> games.rule_set_id = 2 (yeni rule set)
   └─> game_rule_snapshots.rule_set_id = 2 (yeni rule set ile snapshot)

3. Eski oyunlar
   └─> games.rule_set_id = 1 (eski rule set)
   └─> game_rule_snapshots.rule_set_id = 1 (eski rule set ile snapshot)
   └─> Eski oyunların rule değerleri korunur!
```

---

## 🎯 Ana Tablolar ve Amaçları

### **users**
- Kullanıcı bilgileri
- Admin yetkisi kontrolü

### **wallets**
- Kullanıcı bakiyeleri
- Para yatırma/çekme işlemleri

### **rule_sets**
- Oyun kuralları setleri
- Admin tarafından yönetilir
- Sadece bir tanesi aktif olabilir

### **rules**
- Rule set içindeki kurallar
- Payout multiplier'ları
- Oyun tipine göre farklı rule'lar

### **games**
- Oynanan oyunlar
- Hangi rule set ile oynandığı
- Oyun sonuçları

### **bets**
- Yapılan bahisler
- Hangi oyuna ait
- Bahis detayları (bet_type, bet_value)

### **payouts**
- Kazanç/kayıp kayıtları
- Her bahis için bir payout
- Win amount ve outcome

### **transactions**
- Para yatırma/çekme işlemleri
- Sadece DEPOSIT ve WITHDRAW
- BET ve PAYOUT burada değil (bets ve payouts tablolarında)

### **game_rule_snapshots**
- Oyun oynandığında kullanılan rule değerleri
- Rule değişse bile eski değerler korunur
- Audit trail için

---

## 🔍 Sorgu Örnekleri

### Bir oyunun tüm bilgilerini getir:
```sql
SELECT 
    g.game_id,
    g.game_type,
    g.game_result,
    g.started_at,
    u.email as player_email,
    rs.name as rule_set_name,
    b.bet_type,
    b.bet_value,
    b.stake_amount,
    p.win_amount,
    p.outcome
FROM games g
JOIN users u ON g.user_id = u.user_id
JOIN rule_sets rs ON g.rule_set_id = rs.rule_set_id
JOIN bets b ON b.game_id = g.game_id
JOIN payouts p ON p.bet_id = b.bet_id
WHERE g.game_id = 1;
```

### Bir oyunun hangi rule'larla oynandığını getir:
```sql
SELECT 
    grs.rule_type,
    grs.rule_value,
    rs.name as rule_set_name
FROM game_rule_snapshots grs
JOIN rule_sets rs ON grs.rule_set_id = rs.rule_set_id
WHERE grs.game_id = 1;
```

### Bir rule set'in kaç oyunda kullanıldığını getir:
```sql
SELECT 
    rs.name,
    COUNT(g.game_id) as game_count
FROM rule_sets rs
LEFT JOIN games g ON g.rule_set_id = rs.rule_set_id
GROUP BY rs.rule_set_id;
```

---

## ⚠️ Önemli Notlar

1. **Aynı anda sadece bir rule set aktif olabilir**
   - `rule_sets.is_active = TRUE` olan sadece bir tane olmalı

2. **Transaction'lar sadece DEPOSIT ve WITHDRAW için**
   - BET ve PAYOUT işlemleri `bets` ve `payouts` tablolarında

3. **Rule snapshot'lar immutable**
   - Rule değişse bile eski oyunların snapshot'ları değişmez

4. **Her bahis için bir payout kaydı var**
   - Kazanç varsa `outcome='WIN'`, yoksa `outcome='LOSS'`
   - `win_amount` kazanç miktarı (kayıp ise 0)

5. **Foreign key constraints**
   - Tüm ilişkiler foreign key ile korunuyor
   - Silme işlemlerinde dikkatli olunmalı

