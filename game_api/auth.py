from functools import wraps
from flask import jsonify, request, session, Blueprint
from werkzeug.security import generate_password_hash, check_password_hash
from .database import get_db_connection
from .utils.logger import auth_logger
from .utils.csrf import get_csrf_token, csrf_required
from mysql.connector import Error

auth_bp = Blueprint('auth', __name__)

# Rate limiter import (lazy import to prevent circular import)
def get_limiter():
    from . import limiter
    return limiter


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'message': 'You must log in to perform this action.'}), 401
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'message': 'Admin privileges are required for this action!'}), 403
        return f(*args, **kwargs)

    return decorated_function


@auth_bp.route('/register', methods=['POST'])
@get_limiter().limit("5 per hour")  # 5 registrations per hour (spam protection)
def register_user():
    """
    Register a new user account

    ---
    tags:
      - Authentication
    summary: User registration
    description: |
      Creates a new user account with email and password.
      A wallet is automatically created for the new user.
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              format: email
              example: newuser@example.com
            password:
              type: string
              format: password
              example: securePassword123
    responses:
      201:
        description: User created successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: User and wallet created successfully!
            user_id:
              type: integer
              example: 5
      400:
        description: Invalid email or password format
      409:
        description: Email already exists
      500:
        description: Server error
    """
    from .utils.validators import validate_email, validate_password
    
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'message': 'Email and password are required!'}), 400
    
    email = data['email']
    password = data['password']
    
    # Validation
    is_valid, error = validate_email(email)
    if not is_valid:
        return jsonify({'message': error}), 400
    
    is_valid, error = validate_password(password)
    if not is_valid:
        return jsonify({'message': error}), 400
    
    hashed_password = generate_password_hash(password)
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({'message': 'Database server error!'}), 500
        cursor = conn.cursor()
        sql_insert_user = "INSERT INTO users (email, password_hash) VALUES (%s, %s)"
        user_val = (email, hashed_password)
        cursor.execute(sql_insert_user, user_val)
        new_user_id = cursor.lastrowid
        sql_insert_wallet = "INSERT INTO wallets (user_id) VALUES (%s)"
        cursor.execute(sql_insert_wallet, (new_user_id,))
        conn.commit()
        return jsonify({'message': 'User and wallet created successfully!', 'user_id': new_user_id}), 201
    except Error as e:
        if e.errno == 1062: return jsonify({'message': 'This email address is already in use.'}), 409
        print(f"Registration error: {e}")
        return jsonify({'message': 'An error occurred during registration. Please try again.'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@auth_bp.route('/login', methods=['POST'])
@get_limiter().limit("10 per minute")  # 10 attempts per minute (brute force protection)
def login_user():
    """
    User login endpoint (Session-based authentication)

    ---
    tags:
      - Authentication
    summary: User login
    description: |
      Authenticates a user using email and password.
      On success, a server-side session is created and stored securely.
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              format: email
              example: user@example.com
            password:
              type: string
              format: password
              example: strongPassword123
    responses:
      200:
        description: Login successful. Session created.
      401:
        description: Invalid email or password.
      400:
        description: Missing or invalid request body.
    """
    
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'message': 'Email and password are required!'}), 400
    email = data['email']
    password = data['password']
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({'message': 'Database server error!'}), 500
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT user_id, email, password_hash, is_admin, status FROM users WHERE email = %s"
        cursor.execute(sql, (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            if user['status'] == 'BANNED':
                return jsonify({'message': 'Your account has been banned.'}), 403

            session['user_id'] = user['user_id']
            session['email'] = user['email']
            session['is_admin'] = user['is_admin']
            
            # Get user balance
            cursor.execute("SELECT balance FROM wallets WHERE user_id = %s", (user['user_id'],))
            wallet = cursor.fetchone()
            balance = float(wallet['balance']) if wallet else 0.0
            
            # Check for active blackjack game
            cursor.execute("""
                SELECT game_id, game_state, started_at 
                FROM games 
                WHERE user_id = %s AND game_type = 'blackjack' AND status = 'ACTIVE'
                ORDER BY started_at DESC LIMIT 1
            """, (user['user_id'],))
            active_game = cursor.fetchone()
            
            response_data = {
                'message': 'Login successful!',
                'email': user['email'],
                'is_admin': bool(user['is_admin']),
                'balance': balance
            }
            
            if active_game and active_game.get('game_state'):
                response_data['has_active_game'] = True
                response_data['active_game'] = {
                    'game_id': active_game['game_id'],
                    'game_type': 'blackjack',
                    'started_at': active_game['started_at'].isoformat() if active_game['started_at'] else None
                }
            
            # Login log record
            ip_address = request.remote_addr
            cursor.execute(
                "INSERT INTO logs (user_id, action_type, ip_address) VALUES (%s, 'LOGIN', %s)",
                (user['user_id'], ip_address)
            )
            conn.commit()
            
            return jsonify(response_data), 200
        else:
            return jsonify({'message': 'Invalid email or password!'}), 401
    except Error as e:
        print(f"Login error: {e}")
        return jsonify({'message': 'An error occurred during login. Please try again.'}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@auth_bp.route('/logout', methods=['POST'])
@login_required
@csrf_required
def logout_user():
    """
    User logout endpoint

    ---
    tags:
      - Authentication
    summary: User logout
    description: |
      Ends the current user session and logs the action.
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
        description: CSRF token obtained from /csrf-token endpoint
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            csrf_token:
              type: string
              description: Alternative way to provide CSRF token
    responses:
      200:
        description: Logout successful
        schema:
          type: object
          properties:
            message:
              type: string
              example: Successfully logged out.
      401:
        description: Not authenticated
      403:
        description: Invalid or missing CSRF token
    """
    user_id = session.get('user_id')
    
    # Logout log record
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            ip_address = request.remote_addr
            cursor.execute(
                "INSERT INTO logs (user_id, action_type, ip_address) VALUES (%s, 'LOGOUT', %s)",
                (user_id, ip_address)
            )
            conn.commit()
            cursor.close()
            conn.close()
    except Error:
        pass  # Log error is not critical
    
    session.clear()
    return jsonify({'message': 'Logged out successfully.'}), 200


@auth_bp.route('/csrf-token', methods=['GET'])
@login_required
def get_csrf_token_endpoint():
    """
    Get CSRF token for secure operations

    ---
    tags:
      - Authentication
    summary: Get CSRF token
    description: |
      Returns a CSRF token required for all state-changing operations
      (POST, PUT, DELETE). Token is valid for 24 hours.
      Include this token in the X-CSRF-Token header or in request body as csrf_token.
    security:
      - session: []
    responses:
      200:
        description: CSRF token returned successfully
        schema:
          type: object
          properties:
            csrf_token:
              type: string
              example: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
      401:
        description: Not authenticated
    """
    token = get_csrf_token()
    return jsonify({'csrf_token': token})


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """
    Get current user information

    ---
    tags:
      - User
    summary: Get current user profile
    description: Returns the authenticated user's profile information including wallet balance.
    security:
      - session: []
    responses:
      200:
        description: User information retrieved successfully
        schema:
          type: object
          properties:
            user_id:
              type: integer
              example: 1
            email:
              type: string
              example: user@example.com
            status:
              type: string
              enum: [ACTIVE, BANNED]
              example: ACTIVE
            is_admin:
              type: boolean
              example: false
            created_at:
              type: string
              format: date-time
            balance:
              type: number
              format: float
              example: 500.00
      401:
        description: Not authenticated
      404:
        description: User not found
    """
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Database error'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT u.user_id, u.email, u.status, u.is_admin, u.created_at, w.balance
            FROM users u
            LEFT JOIN wallets w ON u.user_id = w.user_id
            WHERE u.user_id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        if user['balance']:
            user['balance'] = float(user['balance'])
        
        return jsonify(user)
        
    except Error as e:
        return jsonify({'message': f'Error: {e}'}), 500
    finally:
        cursor.close()
        conn.close()


@auth_bp.route('/me/games', methods=['GET'])
@login_required
def get_my_games():
    """
    Get current user's game history

    ---
    tags:
      - User
    summary: Get user's game history
    description: Returns a paginated list of games played by the authenticated user.
    security:
      - session: []
    parameters:
      - in: query
        name: limit
        type: integer
        default: 20
        description: Maximum number of games to return
      - in: query
        name: offset
        type: integer
        default: 0
        description: Number of games to skip for pagination
      - in: query
        name: game_type
        type: string
        enum: [coinflip, roulette, blackjack]
        description: Filter by game type
    responses:
      200:
        description: Game history retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              game_id:
                type: integer
              game_type:
                type: string
              game_result:
                type: object
              started_at:
                type: string
                format: date-time
              stake_amount:
                type: number
              win_amount:
                type: number
              outcome:
                type: string
                enum: [WIN, LOSS]
      401:
        description: Not authenticated
    """
    from .services.game_service import GameService
    
    user_id = session.get('user_id')
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    game_type = request.args.get('game_type')
    
    games = GameService.get_user_games(user_id, game_type, limit, offset)
    return jsonify(games)


@auth_bp.route('/me/stats', methods=['GET'])
@login_required
def get_my_stats():
    """
    Get current user's game statistics

    ---
    tags:
      - User
    summary: Get user's game statistics
    description: Returns aggregated statistics for the authenticated user's games.
    security:
      - session: []
    parameters:
      - in: query
        name: days
        type: integer
        default: 30
        description: Number of days to include in statistics
      - in: query
        name: game_type
        type: string
        enum: [coinflip, roulette, blackjack]
        description: Filter by game type
    responses:
      200:
        description: Statistics retrieved successfully
        schema:
          type: object
          properties:
            total_games:
              type: integer
              example: 50
            total_bets:
              type: number
              example: 500.00
            total_payouts:
              type: number
              example: 480.00
            win_count:
              type: integer
              example: 25
            loss_count:
              type: integer
              example: 25
            win_rate:
              type: number
              example: 50.00
            profit:
              type: number
              example: 20.00
      401:
        description: Not authenticated
    """
    from .services.game_service import GameService
    
    user_id = session.get('user_id')
    days = request.args.get('days', 30, type=int)
    game_type = request.args.get('game_type')
    
    stats = GameService.get_game_stats(user_id, game_type, days)
    return jsonify(stats)


@auth_bp.route('/me/password', methods=['PUT'])
@login_required
@csrf_required
def change_password():
    """
    Change user password

    ---
    tags:
      - User
    summary: Change password
    description: |
      Updates the authenticated user's password.
      Requires current password verification and CSRF token.
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
            - current_password
            - new_password
          properties:
            current_password:
              type: string
              format: password
              example: oldPassword123
            new_password:
              type: string
              format: password
              example: newSecurePassword456
            csrf_token:
              type: string
              description: Alternative way to provide CSRF token
    responses:
      200:
        description: Password changed successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Password changed successfully!
      400:
        description: Invalid new password format
      401:
        description: Current password incorrect or not authenticated
      403:
        description: Invalid CSRF token
    """
    from .utils.validators import validate_password
    
    user_id = session.get('user_id')
    data = request.get_json()
    
    if not data or 'current_password' not in data or 'new_password' not in data:
        return jsonify({'message': 'Current password and new password are required!'}), 400
    
    current_password = data['current_password']
    new_password = data['new_password']
    
    # New password validation
    is_valid, error = validate_password(new_password)
    if not is_valid:
        return jsonify({'message': error}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Database error'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Check current password
        cursor.execute("SELECT password_hash FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user or not check_password_hash(user['password_hash'], current_password):
            return jsonify({'message': 'Incorrect current password!'}), 401
        
        # Hash new password and update
        new_hash = generate_password_hash(new_password)
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE user_id = %s",
            (new_hash, user_id)
        )
        conn.commit()
        
        return jsonify({'message': 'Password changed successfully!'})
        
    except Error as e:
        conn.rollback()
        return jsonify({'message': f'Error: {e}'}), 500
    finally:
        cursor.close()
        conn.close()
