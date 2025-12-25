"""
Input validation functions
"""
import re
from typing import Tuple, Optional


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Email formatını kontrol et
    
    Returns:
        (is_valid, error_message)
    """
    if not email:
        return False, "E-posta adresi gereklidir"
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Geçersiz e-posta formatı"
    
    if len(email) > 200:
        return False, "E-posta adresi çok uzun (max 200 karakter)"
    
    return True, None


def validate_password(password: str) -> Tuple[bool, Optional[str]]:
    """
    Şifre güçlülüğünü kontrol et
    
    Returns:
        (is_valid, error_message)
    """
    if not password:
        return False, "Şifre gereklidir"
    
    if len(password) < 4:
        return False, "Şifre en az 4 karakter olmalıdır"
    
    if len(password) > 100:
        return False, "Şifre çok uzun (max 100 karakter)"
    
    return True, None


def validate_bet_amount(amount, balance: float, min_bet: float = 0.01, max_bet: float = 10000) -> Tuple[bool, Optional[str]]:
    """
    Bahis miktarını kontrol et
    
    Returns:
        (is_valid, error_message)
    """
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return False, "Geçersiz bahis miktarı"
    
    if amount <= 0:
        return False, "Bahis miktarı 0'dan büyük olmalıdır"
    
    if amount < min_bet:
        return False, f"Minimum bahis: {min_bet}"
    
    if amount > max_bet:
        return False, f"Maximum bahis: {max_bet}"
    
    if amount > balance:
        return False, f"Yetersiz bakiye. Mevcut: {balance:.2f}"
    
    return True, None


def validate_choice(choice: str, valid_choices: list) -> Tuple[bool, Optional[str]]:
    """
    Seçimi kontrol et
    
    Returns:
        (is_valid, error_message)
    """
    if not choice:
        return False, "Seçim gereklidir"
    
    choice = str(choice).lower()
    if choice not in valid_choices:
        return False, f"Geçersiz seçim. Geçerli seçenekler: {', '.join(valid_choices)}"
    
    return True, None

