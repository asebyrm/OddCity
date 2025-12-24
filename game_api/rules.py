from flask import jsonify, request, Blueprint, session
from .database import get_db_connection
from .auth import admin_required
from mysql.connector import Error

rules_bp = Blueprint('rules', __name__)

@rules_bp.route('/rule-sets', methods=['POST'])
@admin_required
def create_rule_set():
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
        # created_by_admin_id zorunlu, session'dan alıyoruz (admin_required zaten kontrol etti)
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
        return jsonify({'message': f'Bir hata oluştu: {e}'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def get_active_rule_value(rule_type, default_value):
    conn = get_db_connection()
    if not conn: return default_value
    
    cursor = conn.cursor()
    try:
        # Get active rule set's rule
        query = """
            SELECT r.rule_value 
            FROM rules r
            JOIN rule_sets rs ON r.rule_set_id = rs.rule_set_id
            WHERE rs.is_active = TRUE AND r.rule_type = %s
            ORDER BY r.priority DESC
            LIMIT 1
        """
        cursor.execute(query, (rule_type,))
        result = cursor.fetchone()
        
        if result and result[0]:
            return float(result[0])
        return default_value
    except Exception as e:
        print(f"Rule fetch error: {e}")
        return default_value
    finally:
        cursor.close()
        conn.close()