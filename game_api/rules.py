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