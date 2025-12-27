"""
CSRF (Cross-Site Request Forgery) Protection Module
Provides token-based CSRF protection for sensitive endpoints.
"""
import secrets
import hmac
import hashlib
from functools import wraps
from flask import session, request, jsonify
from datetime import datetime, timedelta


# CSRF Token settings
CSRF_TOKEN_LENGTH = 32
CSRF_TOKEN_EXPIRY_HOURS = 24
CSRF_HEADER_NAME = 'X-CSRF-Token'
CSRF_SESSION_KEY = '_csrf_token'
CSRF_TIMESTAMP_KEY = '_csrf_timestamp'


def generate_csrf_token():
    """
    Generates a new CSRF token and stores it in the session.
    Returns the token for client use.
    """
    token = secrets.token_hex(CSRF_TOKEN_LENGTH)
    session[CSRF_SESSION_KEY] = token
    session[CSRF_TIMESTAMP_KEY] = datetime.utcnow().isoformat()
    return token


def get_csrf_token():
    """
    Gets the current CSRF token from session.
    If no token exists or it's expired, generates a new one.
    """
    token = session.get(CSRF_SESSION_KEY)
    timestamp_str = session.get(CSRF_TIMESTAMP_KEY)
    
    # Check if token exists and is not expired
    if token and timestamp_str:
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            if datetime.utcnow() - timestamp < timedelta(hours=CSRF_TOKEN_EXPIRY_HOURS):
                return token
        except (ValueError, TypeError):
            pass
    
    # Generate new token if missing or expired
    return generate_csrf_token()


def validate_csrf_token(token):
    """
    Validates the provided CSRF token against the session token.
    Uses constant-time comparison to prevent timing attacks.
    """
    session_token = session.get(CSRF_SESSION_KEY)
    
    if not session_token or not token:
        return False
    
    # Constant-time comparison
    return hmac.compare_digest(session_token, token)


def csrf_required(f):
    """
    Decorator to require CSRF token validation for a route.
    
    The token can be provided via:
    1. X-CSRF-Token header (preferred)
    2. csrf_token field in JSON body
    
    Usage:
        @app.route('/sensitive-action', methods=['POST'])
        @login_required
        @csrf_required
        def sensitive_action():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from header first, then from JSON body
        token = request.headers.get(CSRF_HEADER_NAME)
        
        if not token:
            data = request.get_json(silent=True)
            if data:
                token = data.get('csrf_token')
        
        if not token:
            return jsonify({
                'message': 'CSRF token eksik! Güvenlik hatası.',
                'error': 'csrf_token_missing'
            }), 403
        
        if not validate_csrf_token(token):
            return jsonify({
                'message': 'Geçersiz CSRF token! Sayfa yenilenebilir.',
                'error': 'csrf_token_invalid'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def csrf_exempt(f):
    """
    Decorator to mark a route as exempt from CSRF protection.
    Useful for public APIs or webhook endpoints.
    """
    f._csrf_exempt = True
    return f

