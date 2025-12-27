from flask import jsonify, request, Blueprint, session
from .database import get_db_connection
from .auth import admin_required
from .utils.csrf import csrf_required
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
    """
    List all rule sets (Admin only)

    ---
    tags:
      - Admin Rules
    summary: List rule sets
    description: Returns all rule sets with their details.
    security:
      - session: []
      - admin: []
    responses:
      200:
        description: Rule sets retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              rule_set_id:
                type: integer
                example: 1
              name:
                type: string
                example: Default Rules
              description:
                type: string
              house_edge:
                type: number
                example: 5.0
              is_active:
                type: boolean
              start_at:
                type: string
                format: date-time
              end_at:
                type: string
                format: date-time
              created_by:
                type: string
                example: admin@example.com
      401:
        description: Not authenticated
      403:
        description: Admin access required
    """
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
@csrf_required
def create_rule_set():
    """
    Create a new rule set (Admin only)

    ---
    tags:
      - Admin Rules
    summary: Create rule set
    description: |
      Creates a new rule set for game configurations.
      New rule sets are created as inactive by default.
      Requires CSRF token.
    security:
      - session: []
      - admin: []
      - csrf: []
    consumes:
      - application/json
    parameters:
      - in: header
        name: X-CSRF-Token
        type: string
        required: true
        description: CSRF token
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - name
          properties:
            name:
              type: string
              example: High Stakes Rules
            description:
              type: string
              example: Rules for high roller games
            house_edge:
              type: number
              default: 5.0
              example: 3.5
            csrf_token:
              type: string
    responses:
      201:
        description: Rule set created successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Rule set created successfully!
            rule_set_id:
              type: integer
              example: 2
      400:
        description: Missing name
      401:
        description: Not authenticated
      403:
        description: Admin access required or invalid CSRF token
      409:
        description: Rule set name already exists
    """
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
        
        sql = "INSERT INTO rule_sets (name, description, house_edge, created_by_admin_id, is_active) VALUES (%s, %s, %s, %s, FALSE)"
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
    """
    Get rule set details (Admin only)

    ---
    tags:
      - Admin Rules
    summary: Get rule set details
    description: Returns a rule set with all its rules.
    security:
      - session: []
      - admin: []
    parameters:
      - in: path
        name: rule_set_id
        type: integer
        required: true
        description: Rule set ID
    responses:
      200:
        description: Rule set retrieved successfully
        schema:
          type: object
          properties:
            rule_set_id:
              type: integer
            name:
              type: string
            description:
              type: string
            house_edge:
              type: number
            is_active:
              type: boolean
            start_at:
              type: string
              format: date-time
            end_at:
              type: string
              format: date-time
            created_by:
              type: string
            rules:
              type: array
              items:
                type: object
                properties:
                  rule_id:
                    type: integer
                  rule_type:
                    type: string
                  rule_param:
                    type: string
      401:
        description: Not authenticated
      403:
        description: Admin access required
      404:
        description: Rule set not found
    """
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
            SELECT rule_id, rule_type, rule_param
            FROM rules
            WHERE rule_set_id = %s
            ORDER BY rule_id ASC
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
@csrf_required
def activate_rule_set(rule_set_id):
    """
    Activate a rule set (Admin only)

    ---
    tags:
      - Admin Rules
    summary: Activate rule set
    description: |
      Activates a rule set and deactivates all others.
      Only one rule set can be active at a time.
      Requires CSRF token.
    security:
      - session: []
      - admin: []
      - csrf: []
    consumes:
      - application/json
    parameters:
      - in: path
        name: rule_set_id
        type: integer
        required: true
        description: Rule set ID to activate
      - in: header
        name: X-CSRF-Token
        type: string
        required: true
        description: CSRF token
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            csrf_token:
              type: string
    responses:
      200:
        description: Rule set activated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Rule set activated.
      401:
        description: Not authenticated
      403:
        description: Admin access required or invalid CSRF token
      404:
        description: Rule set not found
    """
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
@csrf_required
def deactivate_rule_set(rule_set_id):
    """
    Deactivate a rule set (Admin only)

    ---
    tags:
      - Admin Rules
    summary: Deactivate rule set
    description: |
      Deactivates a rule set.
      Requires CSRF token.
    security:
      - session: []
      - admin: []
      - csrf: []
    consumes:
      - application/json
    parameters:
      - in: path
        name: rule_set_id
        type: integer
        required: true
        description: Rule set ID to deactivate
      - in: header
        name: X-CSRF-Token
        type: string
        required: true
        description: CSRF token
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            csrf_token:
              type: string
    responses:
      200:
        description: Rule set deactivated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Rule set deactivated.
      401:
        description: Not authenticated
      403:
        description: Admin access required or invalid CSRF token
      404:
        description: Rule set not found
    """
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


@rules_bp.route('/admin/rule-sets/<int:rule_set_id>', methods=['DELETE'])
@admin_required
@csrf_required
def delete_rule_set(rule_set_id):
    """
    Delete a rule set (Admin only)

    ---
    tags:
      - Admin Rules
    summary: Delete rule set
    description: |
      Deletes a rule set permanently.
      Only rule sets with no games played can be deleted.
      Active rule sets cannot be deleted.
      Requires CSRF token.
    security:
      - session: []
      - admin: []
      - csrf: []
    parameters:
      - in: path
        name: rule_set_id
        type: integer
        required: true
        description: Rule set ID to delete
      - in: header
        name: X-CSRF-Token
        type: string
        required: true
        description: CSRF token
    responses:
      200:
        description: Rule set deleted successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Rule set "Test Rules" deleted successfully!
            deleted_rules:
              type: integer
              example: 5
      400:
        description: Cannot delete active rule set or rule set has games
        schema:
          type: object
          properties:
            message:
              type: string
            game_count:
              type: integer
      401:
        description: Not authenticated
      403:
        description: Admin access required or invalid CSRF token
      404:
        description: Rule set not found
    """
    conn = get_db_connection()
    if not conn: 
        return jsonify({'message': 'Veritabanı hatası'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Rule set var mı kontrol et
        cursor.execute("SELECT rule_set_id, name, is_active FROM rule_sets WHERE rule_set_id = %s", (rule_set_id,))
        rule_set = cursor.fetchone()
        
        if not rule_set:
            return jsonify({'message': 'Kural seti bulunamadı'}), 404
        
        # Aktif rule set silinmeye çalışılıyor mu?
        if rule_set['is_active']:
            return jsonify({'message': 'Aktif kural seti silinemez! Önce başka bir kural setini aktif edin.'}), 400
        
        # Bu rule set ile oyun oynanmış mı kontrol et
        cursor.execute("SELECT COUNT(*) as game_count FROM games WHERE rule_set_id = %s", (rule_set_id,))
        game_count = cursor.fetchone()['game_count']
        
        if game_count > 0:
            return jsonify({
                'message': f'Bu kural seti ile {game_count} oyun oynanmış. Oyun geçmişi olan kural setleri silinemez!',
                'game_count': game_count
            }), 400
        
        # Önce bu rule set'e ait kuralları sil
        cursor.execute("DELETE FROM rules WHERE rule_set_id = %s", (rule_set_id,))
        deleted_rules = cursor.rowcount
        
        # Sonra rule set'i sil
        cursor.execute("DELETE FROM rule_sets WHERE rule_set_id = %s", (rule_set_id,))
        
        conn.commit()
        
        return jsonify({
            'message': f'Kural seti "{rule_set["name"]}" başarıyla silindi!',
            'deleted_rules': deleted_rules
        }), 200
        
    except Error as e:
        conn.rollback()
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()


# Rule Yönetimi

@rules_bp.route('/admin/rule-sets/<int:rule_set_id>/rules', methods=['POST'])
@admin_required
@csrf_required
def add_rule(rule_set_id):
    """
    Add a rule to a rule set (Admin only)

    ---
    tags:
      - Admin Rules
    summary: Add rule to rule set
    description: |
      Adds a new rule to an existing rule set.
      Each rule_type can only exist once per rule set.
      Requires CSRF token.
    security:
      - session: []
      - admin: []
      - csrf: []
    consumes:
      - application/json
    parameters:
      - in: path
        name: rule_set_id
        type: integer
        required: true
        description: Rule set ID
      - in: header
        name: X-CSRF-Token
        type: string
        required: true
        description: CSRF token
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - rule_type
            - rule_param
          properties:
            rule_type:
              type: string
              enum: [coinflip_payout, roulette_number_payout, roulette_color_payout, roulette_parity_payout, blackjack_payout, blackjack_normal_payout]
              example: coinflip_payout
            rule_param:
              type: string
              example: "1.95"
              description: Rule value (as string)
            csrf_token:
              type: string
    responses:
      201:
        description: Rule created successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Rule added successfully!
            rule_id:
              type: integer
              example: 10
      400:
        description: Missing required fields
      401:
        description: Not authenticated
      403:
        description: Admin access required or invalid CSRF token
      404:
        description: Rule set not found
      409:
        description: Rule type already exists in this rule set
    """
    data = request.get_json()
    if not data or 'rule_type' not in data or 'rule_param' not in data:
        return jsonify({'message': 'rule_type ve rule_param gereklidir!'}), 400
    
    rule_type = data['rule_type']
    rule_param = data['rule_param']
    
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
            INSERT INTO rules (rule_set_id, rule_type, rule_param)
            VALUES (%s, %s, %s)
        """, (rule_set_id, rule_type, rule_param))
        
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
@csrf_required
def update_rule(rule_id):
    """
    Update a rule (Admin only)

    ---
    tags:
      - Admin Rules
    summary: Update rule
    description: |
      Updates an existing rule's parameter value.
      Requires CSRF token.
    security:
      - session: []
      - admin: []
      - csrf: []
    consumes:
      - application/json
    parameters:
      - in: path
        name: rule_id
        type: integer
        required: true
        description: Rule ID
      - in: header
        name: X-CSRF-Token
        type: string
        required: true
        description: CSRF token
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - rule_param
          properties:
            rule_param:
              type: string
              example: "2.0"
              description: New rule value
            csrf_token:
              type: string
    responses:
      200:
        description: Rule updated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Rule updated successfully!
      400:
        description: No update data provided
      401:
        description: Not authenticated
      403:
        description: Admin access required or invalid CSRF token
      404:
        description: Rule not found
    """
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
@csrf_required
def delete_rule(rule_id):
    """
    Delete a rule (Admin only)

    ---
    tags:
      - Admin Rules
    summary: Delete rule
    description: |
      Deletes a rule from a rule set.
      Requires CSRF token.
    security:
      - session: []
      - admin: []
      - csrf: []
    parameters:
      - in: path
        name: rule_id
        type: integer
        required: true
        description: Rule ID to delete
      - in: header
        name: X-CSRF-Token
        type: string
        required: true
        description: CSRF token
    responses:
      200:
        description: Rule deleted successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Rule deleted successfully!
      401:
        description: Not authenticated
      403:
        description: Admin access required or invalid CSRF token
      404:
        description: Rule not found
    """
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
    """
    Get available rule types (Admin only)

    ---
    tags:
      - Admin Rules
    summary: Get rule types
    description: Returns a list of all available rule types that can be used in rule sets.
    security:
      - session: []
      - admin: []
    responses:
      200:
        description: Rule types retrieved successfully
        schema:
          type: object
          properties:
            coinflip_payout:
              type: string
              example: Coin Flip Payout Multiplier
            roulette_number_payout:
              type: string
              example: Roulette Number Payout
            roulette_color_payout:
              type: string
              example: Roulette Color Payout
            roulette_parity_payout:
              type: string
              example: Roulette Parity Payout
            blackjack_payout:
              type: string
              example: "Blackjack Payout (3:2)"
            blackjack_normal_payout:
              type: string
              example: Blackjack Normal Win Payout
      401:
        description: Not authenticated
      403:
        description: Admin access required
    """
    return jsonify(RULE_TYPES), 200

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
    