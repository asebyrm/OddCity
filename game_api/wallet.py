from flask import jsonify, request, Blueprint, session
from .database import get_db_connection
from .auth import login_required
from .utils.csrf import csrf_required
from mysql.connector import Error

wallet_bp = Blueprint('wallet', __name__)

# Rate limiter
def get_limiter():
    from . import limiter
    return limiter

@wallet_bp.route('/wallets/me', methods=['GET'])
@login_required
def get_my_wallet():
    """
    Get current user's wallet information

    ---
    tags:
      - Wallet
    summary: Get wallet balance
    description: Returns the authenticated user's wallet details including balance and currency.
    security:
      - session: []
    responses:
      200:
        description: Wallet information retrieved successfully
        schema:
          type: object
          properties:
            wallet:
              type: object
              properties:
                email:
                  type: string
                  example: user@example.com
                balance:
                  type: number
                  format: float
                  example: 500.00
                currency:
                  type: string
                  example: VRT
                updated_at:
                  type: string
                  format: date-time
      401:
        description: Not authenticated
      404:
        description: Wallet not found
    """
    user_id = session.get('user_id')

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'message': 'Database server error!'}), 500

        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT u.email, w.balance, w.currency, w.updated_at
            FROM wallets w
            JOIN users u ON w.user_id = u.user_id
            WHERE w.user_id = %s
        """
        cursor.execute(sql, (user_id,))
        wallet_info = cursor.fetchone()

        if not wallet_info:
            return jsonify({'message': 'Wallet not found!'}), 404

        wallet_info['balance'] = float(wallet_info['balance'])

        return jsonify({'wallet': wallet_info}), 200

    except Error as e:
        print(f"Wallet fetch error: {e}")
        return jsonify({'message': 'An error occurred while fetching wallet details.'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@wallet_bp.route('/wallets/me/deposit', methods=['POST'])
@get_limiter().limit("20 per hour")  # 20 deposits per hour
@login_required
@csrf_required
def deposit_to_wallet():
    """
    Deposit virtual currency to wallet

    ---
    tags:
      - Wallet
    summary: Deposit funds
    description: |
      Adds virtual currency to the authenticated user's wallet.
      Requires CSRF token for security.
    security:
      - session: []
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
            - amount
          properties:
            amount:
              type: number
              format: float
              minimum: 0.01
              example: 100.00
            csrf_token:
              type: string
              description: Alternative way to provide CSRF token
    responses:
      200:
        description: Deposit successful
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Success! 100.0 VIRTUAL added to your wallet."
            user:
              type: string
              example: user@example.com
            new_balance:
              type: number
              example: 600.00
      400:
        description: Invalid amount
      401:
        description: Not authenticated
      403:
        description: Invalid CSRF token
      404:
        description: Wallet not found
    """
    user_id = session.get('user_id')
    user_email = session.get('email')

    data = request.get_json()
    if not data or 'amount' not in data:
        return jsonify({'message': 'Amount is required!'}), 400

    try:
        amount = float(data['amount'])
    except ValueError:
        return jsonify({'message': 'Amount must be a valid number!'}), 400

    if amount <= 0:
        return jsonify({'message': 'Amount must be greater than zero!'}), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'message': 'Database server error!'}), 500

        conn.start_transaction()

        cursor = conn.cursor(dictionary=True)

        # SECURITY: Prevent race condition with Row lock
        sql_get_wallet = "SELECT wallet_id, balance FROM wallets WHERE user_id = %s FOR UPDATE"
        cursor.execute(sql_get_wallet, (user_id,))
        wallet = cursor.fetchone()

        if not wallet:
            conn.rollback()
            return jsonify({'message': 'User wallet not found!'}), 404

        wallet_id = wallet['wallet_id']

        # Update balance
        sql_update_wallet = "UPDATE wallets SET balance = balance + %s WHERE wallet_id = %s"
        cursor.execute(sql_update_wallet, (amount, wallet_id))

        # Calculate new balance
        new_balance = float(wallet['balance']) + amount

        # Transaction log
        sql_log_tx = "INSERT INTO transactions (user_id, wallet_id, amount, tx_type) VALUES (%s, %s, %s, 'DEPOSIT')"
        cursor.execute(sql_log_tx, (user_id, wallet_id, amount))

        conn.commit()

        return jsonify({
            'message': f'Success! {amount} VIRTUAL added to your wallet.',
            'user': user_email,
            'new_balance': float(new_balance)
        }), 200

    except Error as e:
        if conn:
            conn.rollback()
        print(f"Deposit error: {e}")
        return jsonify({'message': 'An error occurred during deposit.'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@wallet_bp.route('/wallets/me/withdraw', methods=['POST'])
@get_limiter().limit("10 per hour")  # 10 withdrawals per hour
@login_required
@csrf_required
def withdraw_from_wallet():
    """
    Withdraw virtual currency from wallet

    ---
    tags:
      - Wallet
    summary: Withdraw funds
    description: |
      Withdraws virtual currency from the authenticated user's wallet.
      Requires sufficient balance and CSRF token.
    security:
      - session: []
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
            - amount
          properties:
            amount:
              type: number
              format: float
              minimum: 0.01
              example: 50.00
            csrf_token:
              type: string
              description: Alternative way to provide CSRF token
    responses:
      200:
        description: Withdrawal successful
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Success! 50.0 VIRTUAL withdrawn from your wallet."
            user:
              type: string
              example: user@example.com
            new_balance:
              type: number
              example: 450.00
      400:
        description: Invalid amount or insufficient balance
        schema:
          type: object
          properties:
            message:
              type: string
              example: Insufficient balance!
            current_balance:
              type: number
              example: 100.00
            withdraw_amount:
              type: number
              example: 500.00
      401:
        description: Not authenticated
      403:
        description: Invalid CSRF token
      404:
        description: Wallet not found
    """
    user_id = session.get('user_id')
    user_email = session.get('email')

    data = request.get_json()
    if not data or 'amount' not in data:
        return jsonify({'message': 'Withdrawal amount is required!'}), 400

    try:
        amount = float(data['amount'])
    except ValueError:
        return jsonify({'message': 'Amount must be a valid number!'}), 400

    if amount <= 0:
        return jsonify({'message': 'Amount must be greater than zero!'}), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'message': 'Database server error!'}), 500

        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)

        sql_get_balance = "SELECT balance FROM wallets WHERE user_id = %s FOR UPDATE"
        cursor.execute(sql_get_balance, (user_id,))
        result = cursor.fetchone()

        if not result:
            conn.rollback()
            return jsonify({'message': 'Wallet not found!'}), 404

        balance = float(result['balance'])

        if balance < amount:
            conn.rollback()
            return jsonify({
                'message': 'Insufficient balance!',
                'current_balance': balance,
                'withdraw_amount': amount
            }), 400

        # Get wallet_id (already got it with SELECT FOR UPDATE)
        cursor.execute("SELECT wallet_id FROM wallets WHERE user_id = %s", (user_id,))
        wallet = cursor.fetchone()
        wallet_id = wallet['wallet_id']

        # Update balance
        sql_update_wallet = "UPDATE wallets SET balance = balance - %s WHERE wallet_id = %s"
        cursor.execute(sql_update_wallet, (amount, wallet_id))

        # Calculate new balance
        new_balance = balance - amount

        # Transaction log
        sql_log_tx = "INSERT INTO transactions (user_id, wallet_id, amount, tx_type) VALUES (%s, %s, %s, 'WITHDRAW')"
        cursor.execute(sql_log_tx, (user_id, wallet_id, amount))

        conn.commit()

        return jsonify({
            'message': f'Success! {amount} VIRTUAL withdrawn from your wallet.',
            'user': user_email,
            'new_balance': float(new_balance)
        }), 200

    except Error as e:
        if conn:
            conn.rollback()
        print(f"Withdrawal error: {e}")
        return jsonify({'message': 'An error occurred during withdrawal.'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()