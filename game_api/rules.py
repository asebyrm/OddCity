from flask import jsonify, request, Blueprint, session
from .database import get_db_connection
from .auth import admin_required
from mysql.connector import Error

rules_bp = Blueprint('rules', __name__)

# Rule type'ları - Oyunlar için kullanılan rule tipleri
RULE_TYPES = {
    'coinflip_payout': 'Coin Flip Payout Multiplier',
    'roulette_number_payout': 'Roulette Number Payout',
    'roulette_color_payout': 'Roulette Color Payout',
    'roulette_parity_payout': 'Roulette Parity Payout',
    'blackjack_payout': 'Blackjack Payout (3:2)',
    'blackjack_normal_payout': 'Blackjack Normal Win Payout'
}

# Rule Set Yönetimi

@rules_bp.route('/admin/rule-sets', methods=['GET'])
@admin_required
def list_rule_sets():
    """Tüm rule set'leri listele"""
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı hatası'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT rs.rule_set_id, rs.name, rs.description, rs.house_edge, 
                   rs.is_active, rs.start_at, rs.end_at,
                   u.email as created_by
            FROM rule_sets rs
            LEFT JOIN users u ON rs.created_by_admin_id = u.user_id
            ORDER BY rs.rule_set_id ASC
        """
        cursor.execute(query)
        rule_sets = cursor.fetchall()
        return jsonify(rule_sets), 200
    except Error as e:
        print(f"Rule sets list error: {e}")
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@rules_bp.route('/admin/rule-sets', methods=['POST'])
@admin_required
def create_rule_set():
    """Yeni rule set oluştur"""
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
        admin_id = session.get('user_id')
        
        sql = "INSERT INTO rule_sets (name, description, house_edge, created_by_admin_id) VALUES (%s, %s, %s, %s)"
        val = (name, description, house_edge, admin_id)

        cursor.execute(sql, val)
        conn.commit()

        return jsonify({'message': 'Kural seti başarıyla oluşturuldu!', 'rule_set_id': cursor.lastrowid}), 201

    except Error as e:
        if e.errno == 1062:
            return jsonify({'message': 'Bu isimde bir kural seti zaten var.'}), 409
        print(f"Rule set hatası: {e}")
        return jsonify({'message': 'Kural seti oluşturulurken bir hata oluştu.'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@rules_bp.route('/admin/rule-sets/<int:rule_set_id>', methods=['GET'])
@admin_required
def get_rule_set(rule_set_id):
    """Rule set detaylarını ve kurallarını getir"""
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı hatası'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Rule set bilgileri
        cursor.execute("""
            SELECT rs.rule_set_id, rs.name, rs.description, rs.house_edge, 
                   rs.is_active, rs.start_at, rs.end_at,
                   u.email as created_by
            FROM rule_sets rs
            LEFT JOIN users u ON rs.created_by_admin_id = u.user_id
            WHERE rs.rule_set_id = %s
        """, (rule_set_id,))
        rule_set = cursor.fetchone()
        
        if not rule_set:
            return jsonify({'message': 'Kural seti bulunamadı'}), 404
        
        # Rule set'in kuralları
        cursor.execute("""
            SELECT rule_id, rule_type, rule_param, priority, is_required
            FROM rules
            WHERE rule_set_id = %s
            ORDER BY priority DESC, rule_id ASC
        """, (rule_set_id,))
        rules = cursor.fetchall()
        
        rule_set['rules'] = rules
        return jsonify(rule_set), 200
    except Error as e:
        print(f"Rule set detail error: {e}")
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@rules_bp.route('/admin/rule-sets/<int:rule_set_id>/activate', methods=['POST'])
@admin_required
def activate_rule_set(rule_set_id):
    """Rule set'i aktif yap (diğerlerini pasif yap)"""
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı hatası'}), 500
    
    cursor = conn.cursor()
    try:
        # Önce tüm rule set'leri pasif yap
        cursor.execute("UPDATE rule_sets SET is_active = FALSE")
        
        # Sonra bu rule set'i aktif yap
        cursor.execute("UPDATE rule_sets SET is_active = TRUE WHERE rule_set_id = %s", (rule_set_id,))
        
        if cursor.rowcount == 0:
            conn.rollback()
            return jsonify({'message': 'Kural seti bulunamadı'}), 404
        
        conn.commit()
        return jsonify({'message': 'Kural seti aktif edildi.'}), 200
    except Error as e:
        conn.rollback()
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@rules_bp.route('/admin/rule-sets/<int:rule_set_id>/deactivate', methods=['POST'])
@admin_required
def deactivate_rule_set(rule_set_id):
    """Rule set'i pasif yap"""
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı hatası'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE rule_sets SET is_active = FALSE WHERE rule_set_id = %s", (rule_set_id,))
        
        if cursor.rowcount == 0:
            return jsonify({'message': 'Kural seti bulunamadı'}), 404
        
        conn.commit()
        return jsonify({'message': 'Kural seti pasif edildi.'}), 200
    except Error as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

# Rule Yönetimi

@rules_bp.route('/admin/rule-sets/<int:rule_set_id>/rules', methods=['POST'])
@admin_required
def add_rule(rule_set_id):
    """Rule set'e yeni kural ekle"""
    data = request.get_json()
    if not data or 'rule_type' not in data or 'rule_param' not in data:
        return jsonify({'message': 'rule_type ve rule_param gereklidir!'}), 400
    
    rule_type = data['rule_type']
    rule_param = data['rule_param']
    priority = data.get('priority', 0)
    is_required = data.get('is_required', True)
    
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı hatası'}), 500
    
    cursor = conn.cursor()
    try:
        # Rule set'in var olduğunu kontrol et
        cursor.execute("SELECT rule_set_id FROM rule_sets WHERE rule_set_id = %s", (rule_set_id,))
        if not cursor.fetchone():
            return jsonify({'message': 'Kural seti bulunamadı'}), 404
        
        # Kuralı ekle
        cursor.execute("""
            INSERT INTO rules (rule_set_id, rule_type, rule_param, priority, is_required)
            VALUES (%s, %s, %s, %s, %s)
        """, (rule_set_id, rule_type, rule_param, priority, is_required))
        
        conn.commit()
        return jsonify({
            'message': 'Kural başarıyla eklendi!',
            'rule_id': cursor.lastrowid
        }), 201
    except Error as e:
        conn.rollback()
        if e.errno == 1062:
            return jsonify({'message': 'Bu rule_type için zaten bir kural var.'}), 409
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@rules_bp.route('/admin/rules/<int:rule_id>', methods=['PUT'])
@admin_required
def update_rule(rule_id):
    """Kuralı güncelle"""
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Güncellenecek veri gereklidir!'}), 400
    
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı hatası'}), 500
    
    cursor = conn.cursor()
    try:
        # Güncellenebilir alanlar
        updates = []
        values = []
        
        if 'rule_param' in data:
            updates.append("rule_param = %s")
            values.append(data['rule_param'])
        
        if 'priority' in data:
            updates.append("priority = %s")
            values.append(data['priority'])
        
        if 'is_required' in data:
            updates.append("is_required = %s")
            values.append(data['is_required'])
        
        if not updates:
            return jsonify({'message': 'Güncellenecek alan belirtilmedi!'}), 400
        
        values.append(rule_id)
        query = f"UPDATE rules SET {', '.join(updates)} WHERE rule_id = %s"
        cursor.execute(query, values)
        
        if cursor.rowcount == 0:
            return jsonify({'message': 'Kural bulunamadı'}), 404
        
        conn.commit()
        return jsonify({'message': 'Kural başarıyla güncellendi!'}), 200
    except Error as e:
        conn.rollback()
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@rules_bp.route('/admin/rules/<int:rule_id>', methods=['DELETE'])
@admin_required
def delete_rule(rule_id):
    """Kuralı sil"""
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı hatası'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM rules WHERE rule_id = %s", (rule_id,))
        
        if cursor.rowcount == 0:
            return jsonify({'message': 'Kural bulunamadı'}), 404
        
        conn.commit()
        return jsonify({'message': 'Kural başarıyla silindi!'}), 200
    except Error as e:
        conn.rollback()
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@rules_bp.route('/admin/rule-types', methods=['GET'])
@admin_required
def get_rule_types():
    """Kullanılabilir rule type'ları listele"""
    return jsonify(RULE_TYPES), 200

@rules_bp.route('/games/<int:game_id>/rules', methods=['GET'])
@admin_required
def get_game_rules_endpoint(game_id):
    """Bir oyunun hangi rule'larla oynandığını getir"""
    from .rules import get_game_rules
    
    rules_data = get_game_rules(game_id)
    
    if not rules_data:
        return jsonify({'message': 'Bu oyun için rule snapshot bulunamadı'}), 404
    
    return jsonify(rules_data), 200

def get_active_rule_set_id():
    """Aktif rule set'in ID'sini döndürür"""
    conn = get_db_connection()
    if not conn: 
        return None
    
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT rule_set_id FROM rule_sets WHERE is_active = TRUE LIMIT 1")
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"Active rule set fetch error: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_active_rule_value(rule_type, default_value):
    """
    Aktif rule set'ten belirli bir rule_type için rule değerini alır.
    
    Args:
        rule_type: Kural tipi (örn: 'coinflip_payout', 'roulette_number_payout')
        default_value: Eğer kural bulunamazsa döndürülecek varsayılan değer
    
    Returns:
        float: Kural değeri veya default_value
    """
    conn = get_db_connection()
    if not conn: 
        return default_value
    
    cursor = conn.cursor()
    try:
        # Aktif rule set'ten rule değerini al (rule_param kolonunu kullan)
        query = """
            SELECT r.rule_param 
            FROM rules r
            JOIN rule_sets rs ON r.rule_set_id = rs.rule_set_id
            WHERE rs.is_active = TRUE AND r.rule_type = %s
            ORDER BY r.priority DESC
            LIMIT 1
        """
        cursor.execute(query, (rule_type,))
        result = cursor.fetchone()
        
        if result and result[0]:
            try:
                return float(result[0])
            except (ValueError, TypeError):
                # Eğer float'a çevrilemezse default değeri döndür
                return default_value
        return default_value
    except Exception as e:
        print(f"Rule fetch error: {e}")
        return default_value
    finally:
        cursor.close()
        conn.close()

def create_rule_snapshot(game_id, rule_set_id, game_type):
    """
    Oyun için rule snapshot oluştur - Oyun oynandığında kullanılan rule değerlerini kaydet
    
    Args:
        game_id: Oyun ID'si
        rule_set_id: Kullanılan rule set ID'si
        game_type: Oyun tipi ('coinflip', 'roulette', 'blackjack')
    """
    conn = get_db_connection()
    if not conn:
        print("Rule snapshot oluşturulamadı: Veritabanı bağlantısı yok")
        return
    
    cursor = conn.cursor()
    try:
        # Oyun tipine göre rule'ları belirle
        rules_to_snapshot = []
        
        if game_type == 'coinflip':
            payout = get_active_rule_value('coinflip_payout', 1.95)
            rules_to_snapshot.append(('coinflip_payout', payout))
        
        elif game_type == 'roulette':
            number_payout = get_active_rule_value('roulette_number_payout', 35)
            color_payout = get_active_rule_value('roulette_color_payout', 1)
            parity_payout = get_active_rule_value('roulette_parity_payout', 1)
            rules_to_snapshot.extend([
                ('roulette_number_payout', number_payout),
                ('roulette_color_payout', color_payout),
                ('roulette_parity_payout', parity_payout)
            ])
        
        elif game_type == 'blackjack':
            blackjack_payout = get_active_rule_value('blackjack_payout', 2.5)
            normal_payout = get_active_rule_value('blackjack_normal_payout', 2.0)
            rules_to_snapshot.extend([
                ('blackjack_payout', blackjack_payout),
                ('blackjack_normal_payout', normal_payout)
            ])
        
        # Snapshot'ları kaydet
        for rule_type, rule_value in rules_to_snapshot:
            cursor.execute("""
                INSERT INTO game_rule_snapshots (game_id, rule_set_id, rule_type, rule_value)
                VALUES (%s, %s, %s, %s)
            """, (game_id, rule_set_id, rule_type, rule_value))
        
        conn.commit()
        
    except Error as e:
        print(f"Rule snapshot oluşturma hatası: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def get_game_rules(game_id):
    """
    Bir oyunun hangi rule'larla oynandığını getir
    
    Returns:
        {
            'rule_set_id': 1,
            'rules': [
                {'rule_type': 'coinflip_payout', 'rule_value': 1.95},
                ...
            ]
        }
    """
    conn = get_db_connection()
    if not conn:
        return None
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Snapshot'ları getir
        cursor.execute("""
            SELECT rule_set_id, rule_type, rule_value
            FROM game_rule_snapshots
            WHERE game_id = %s
            ORDER BY rule_type
        """, (game_id,))
        
        snapshots = cursor.fetchall()
        
        if not snapshots:
            return None
        
        # İlk snapshot'tan rule_set_id'yi al
        rule_set_id = snapshots[0]['rule_set_id']
        
        # Rule'ları formatla
        rules = [
            {
                'rule_type': s['rule_type'],
                'rule_value': float(s['rule_value'])
            }
            for s in snapshots
        ]
        
        return {
            'rule_set_id': rule_set_id,
            'rules': rules
        }
        
    except Error as e:
        print(f"Game rules getirme hatası: {e}")
        return None
    finally:
        cursor.close()
        conn.close()