# Rule System Mimari Önerisi

## 🎯 Amaç
Admin'in oyun payout'larını değiştirebilmesi ve her oyunun hangi rule set ile oynandığını takip edebilmesi.

---

## 📊 Mevcut Sistem (İyi Çalışıyor)

### Avantajlar:
- ✅ `games.rule_set_id` ile oyun-rule ilişkisi var
- ✅ Aktif rule set sistemi çalışıyor
- ✅ Her oyun oynandığında aktif rule_set_id kaydediliyor

### Eksikler:
- ⚠️ Rule değişikliği sonrası eski oyunların hangi rule ile oynandığı net değil
- ⚠️ Rule snapshot yok (rule değiştiğinde eski değerler kaybolur)
- ⚠️ Rule versioning yok

---

## 🏗️ Baştan Kurarken Önerilen Mimari

### 1. **Rule Snapshot Sistemi**

Her oyun oynandığında, kullanılan rule değerlerini snapshot olarak kaydet:

```sql
CREATE TABLE game_rule_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    game_id INTEGER NOT NULL,
    rule_set_id INTEGER NOT NULL,
    rule_type VARCHAR(50) NOT NULL,
    rule_value DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (rule_set_id) REFERENCES rule_sets(rule_set_id)
);
```

**Avantaj:**
- Rule değişse bile, oyun oynandığındaki rule değeri korunur
- Audit trail: Hangi rule ile ne kadar kazanç verildiği net

**Kullanım:**
```python
# Oyun oynanırken
rule_value = get_active_rule_value('coinflip_payout', 1.95)
payout = bet_amount * rule_value

# Snapshot kaydet
save_rule_snapshot(game_id, rule_set_id, 'coinflip_payout', rule_value)
```

---

### 2. **Rule Engine Pattern**

Tüm rule işlemlerini tek bir yerde topla:

```python
# services/rule_engine.py
class RuleEngine:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 60  # 60 saniye cache
    
    def get_rule_value(self, rule_type, default_value, rule_set_id=None):
        """
        Rule değerini getir
        
        Args:
            rule_type: 'coinflip_payout', 'roulette_number_payout', etc.
            default_value: Rule yoksa kullanılacak varsayılan değer
            rule_set_id: Belirli bir rule set kullan (None ise aktif olanı kullan)
        """
        # Cache kontrolü
        cache_key = f"{rule_set_id or 'active'}:{rule_type}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Database'den al
        if rule_set_id:
            value = self._get_rule_from_set(rule_set_id, rule_type)
        else:
            value = self._get_active_rule(rule_type)
        
        value = value or default_value
        
        # Cache'e ekle
        self.cache[cache_key] = value
        return value
    
    def get_all_rules_for_game(self, game_type, rule_set_id=None):
        """
        Bir oyun türü için tüm rule'ları getir
        
        Örnek: coinflip için coinflip_payout
        Örnek: roulette için number_payout, color_payout, parity_payout
        """
        rules = {}
        
        if game_type == 'coinflip':
            rules['payout'] = self.get_rule_value('coinflip_payout', 1.95, rule_set_id)
        
        elif game_type == 'roulette':
            rules['number_payout'] = self.get_rule_value('roulette_number_payout', 35, rule_set_id)
            rules['color_payout'] = self.get_rule_value('roulette_color_payout', 1, rule_set_id)
            rules['parity_payout'] = self.get_rule_value('roulette_parity_payout', 1, rule_set_id)
        
        elif game_type == 'blackjack':
            rules['blackjack_payout'] = self.get_rule_value('blackjack_payout', 2.5, rule_set_id)
            rules['normal_payout'] = self.get_rule_value('blackjack_normal_payout', 2.0, rule_set_id)
        
        return rules
    
    def create_snapshot(self, game_id, rule_set_id, game_type):
        """
        Oyun için rule snapshot oluştur
        """
        rules = self.get_all_rules_for_game(game_type, rule_set_id)
        
        for rule_type, rule_value in rules.items():
            # game_rule_snapshots tablosuna kaydet
            save_snapshot(game_id, rule_set_id, rule_type, rule_value)
    
    def clear_cache(self):
        """Cache'i temizle (rule değişikliğinden sonra)"""
        self.cache.clear()
```

---

### 3. **Game Service Pattern**

Her oyun için service class'ı:

```python
# services/coinflip_service.py
class CoinFlipService:
    def __init__(self, rule_engine, game_repo, bet_repo, payout_repo):
        self.rule_engine = rule_engine
        self.game_repo = game_repo
        self.bet_repo = bet_repo
        self.payout_repo = payout_repo
    
    def play(self, user_id, bet_amount, choice):
        """
        Coin flip oyununu oyna
        """
        # 1. Aktif rule set'i al
        rule_set_id = get_active_rule_set_id()
        
        # 2. Rule değerini al
        payout_multiplier = self.rule_engine.get_rule_value(
            'coinflip_payout', 
            1.95, 
            rule_set_id
        )
        
        # 3. Oyunu oyna
        game_result = random.choice(['yazi', 'tura'])
        is_win = (choice == game_result)
        
        # 4. Game kaydı oluştur
        game = self.game_repo.create({
            'user_id': user_id,
            'rule_set_id': rule_set_id,
            'game_type': 'coinflip',
            'status': 'ACTIVE'
        })
        
        # 5. Bet kaydı oluştur
        bet = self.bet_repo.create({
            'game_id': game.id,
            'user_id': user_id,
            'bet_type': 'choice',
            'bet_value': choice,
            'stake_amount': bet_amount
        })
        
        # 6. Rule snapshot oluştur
        self.rule_engine.create_snapshot(game.id, rule_set_id, 'coinflip')
        
        # 7. Payout hesapla ve kaydet
        payout_amount = 0
        if is_win:
            payout_amount = bet_amount * payout_multiplier
            # Bakiye ekle
            # Payout kaydı oluştur
        
        # 8. Game'i tamamla
        self.game_repo.update(game.id, {
            'game_result': json.dumps({
                'result': game_result,
                'choice': choice,
                'is_win': is_win,
                'payout_multiplier': payout_multiplier,
                'payout_amount': payout_amount
            }),
            'status': 'COMPLETED',
            'ended_at': datetime.now()
        })
        
        return {
            'game_id': game.id,
            'result': game_result,
            'is_win': is_win,
            'payout': payout_amount,
            'rule_set_id': rule_set_id,
            'payout_multiplier': payout_multiplier
        }
```

---

### 4. **Rule Versioning (Opsiyonel - İleri Seviye)**

Rule değişikliklerini versiyonla:

```sql
CREATE TABLE rule_versions (
    version_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    rule_id INTEGER NOT NULL,
    rule_param VARCHAR(100) NOT NULL,
    version_number INTEGER NOT NULL,
    changed_by_admin_id INTEGER NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rule_id) REFERENCES rules(rule_id),
    FOREIGN KEY (changed_by_admin_id) REFERENCES users(user_id)
);
```

**Avantaj:**
- Rule değişiklik geçmişi
- Geri alma (rollback) imkanı
- Audit trail

---

### 5. **Unified Game Interface**

Tüm oyunlar için ortak interface:

```python
# services/base_game_service.py
class BaseGameService:
    def __init__(self, rule_engine, game_type):
        self.rule_engine = rule_engine
        self.game_type = game_type
    
    def play(self, user_id, bet_data):
        """
        Tüm oyunlar için ortak play metodu
        
        bet_data: Oyun tipine göre değişir
        - coinflip: {'amount': 10, 'choice': 'yazi'}
        - roulette: {'amount': 10, 'bet_type': 'number', 'bet_value': 7}
        - blackjack: {'amount': 10}
        """
        # 1. Rule set al
        rule_set_id = get_active_rule_set_id()
        
        # 2. Rule'ları al
        rules = self.rule_engine.get_all_rules_for_game(self.game_type, rule_set_id)
        
        # 3. Oyunu oyna (her oyun kendi logic'ini implement eder)
        result = self._play_game(bet_data, rules)
        
        # 4. Game kaydı oluştur
        game = self._create_game_record(user_id, rule_set_id, result)
        
        # 5. Bet kaydı oluştur
        bet = self._create_bet_record(game.id, user_id, bet_data)
        
        # 6. Rule snapshot oluştur
        self.rule_engine.create_snapshot(game.id, rule_set_id, self.game_type)
        
        # 7. Payout işle
        self._process_payout(game.id, bet.id, result, rules)
        
        return result
    
    def _play_game(self, bet_data, rules):
        """Her oyun kendi logic'ini implement eder"""
        raise NotImplementedError
    
    def _create_game_record(self, user_id, rule_set_id, result):
        """Game kaydı oluştur"""
        pass
    
    def _create_bet_record(self, game_id, user_id, bet_data):
        """Bet kaydı oluştur"""
        pass
    
    def _process_payout(self, game_id, bet_id, result, rules):
        """Payout işle"""
        pass

# services/coinflip_service.py
class CoinFlipService(BaseGameService):
    def __init__(self, rule_engine):
        super().__init__(rule_engine, 'coinflip')
    
    def _play_game(self, bet_data, rules):
        """Coin flip logic"""
        choice = bet_data['choice']
        game_result = random.choice(['yazi', 'tura'])
        is_win = (choice == game_result)
        
        payout = 0
        if is_win:
            payout = bet_data['amount'] * rules['payout']
        
        return {
            'result': game_result,
            'choice': choice,
            'is_win': is_win,
            'payout': payout
        }
```

---

## 📋 Özet: Baştan Kurarken Yapılacaklar

### 1. **Database Schema**
- ✅ `games.rule_set_id` (mevcut)
- ➕ `game_rule_snapshots` (yeni - rule snapshot için)
- ➕ `rule_versions` (opsiyonel - versioning için)

### 2. **Rule Engine**
- ✅ `get_active_rule_value()` (mevcut)
- ➕ `get_all_rules_for_game()` (yeni - tüm rule'ları getir)
- ➕ `create_snapshot()` (yeni - snapshot oluştur)
- ➕ Cache mekanizması (performans için)

### 3. **Service Layer**
- ➕ `BaseGameService` (ortak interface)
- ➕ `CoinFlipService`, `RouletteService`, `BlackjackService` (her oyun için)

### 4. **Repository Pattern**
- ➕ `GameRepository`, `BetRepository`, `PayoutRepository` (database işlemleri)

### 5. **API Endpoints**
- ✅ Mevcut endpoint'ler
- ➕ `GET /games/:id/rules` (oyunun hangi rule'larla oynandığını göster)
- ➕ `GET /admin/rule-sets/:id/usage` (rule set'in kaç oyunda kullanıldığını göster)

---

## 🎯 Avantajlar

1. **Scalability**: Yeni oyun eklemek kolay (BaseGameService'den inherit et)
2. **Audit Trail**: Her oyunun hangi rule ile oynandığı net
3. **Rule Snapshot**: Rule değişse bile eski oyunların rule değerleri korunur
4. **Maintainability**: Kod tekrarı azalır
5. **Testability**: Her katman ayrı test edilebilir

---

## 🔄 Mevcut Sistemden Geçiş

Mevcut sistem zaten iyi çalışıyor. İyileştirmeler:

1. **Rule Snapshot ekle** (en önemli)
2. **Rule Engine pattern** (code organization)
3. **Service layer** (business logic separation)

Bu iyileştirmeler yapılırsa, sistem daha maintainable ve scalable olur.

