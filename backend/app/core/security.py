"""
Security Core Module

This module provides cryptographic utilities for password hashing, JWT token management,
and API key generation. All functions use industry-standard algorithms and best practices
for security.

Features:
- Password hashing with bcrypt (cost factor 12)
- JWT token creation and validation (HS256)
- API key generation and verification (HMAC-SHA256)
- Constant-time comparison to prevent timing attacks
- Password strength validation
"""

import hashlib
import hmac
import secrets
import string
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.exc import InvalidTokenError

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=settings.bcrypt_rounds)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with configurable cost factor.
    
    Note: bcrypt has a 72 byte limit for passwords.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password string
        
    Raises:
        ValueError: If password is too weak
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    # Validate password strength
    validate_password_strength(password)
    
    # Truncate password to 72 bytes if it's too long (bcrypt limitation)
    # Encode to bytes, truncate, then decode back to string
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
        password = password_bytes.decode('utf-8', errors='ignore')
    
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash using constant-time comparison.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored password hash
        
    Returns:
        True if password matches, False otherwise
    """
    if not plain_password or not hashed_password:
        return False
    
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except InvalidTokenError:
        return False


def validate_password_strength(password: str) -> None:
    """
    Validate password strength requirements.
    
    Args:
        password: Password to validate
        
    Raises:
        ValueError: If password doesn't meet strength requirements
    """
    if len(password) < settings.password_min_length:
        raise ValueError(f"Password must be at least {settings.password_min_length} characters long")
    
    # Check for at least one lowercase letter
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain at least one lowercase letter")
    
    # Check for at least one uppercase letter
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter")
    
    # Check for at least one digit
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one digit")
    
    # Check for at least one special character
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        raise ValueError("Password must contain at least one special character")


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with configurable expiration.
    
    Args:
        data: Payload data to encode in token
        expires_delta: Token expiration time (defaults to configured value)
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    to_encode.update({"exp": expire, "type": "access"})
    
    return jwt.encode(
        to_encode, 
        settings.jwt_secret_key.get_secret_value(), 
        algorithm=settings.jwt_algorithm
    )


def create_refresh_token(user_id: str) -> str:
    """
    Create a JWT refresh token with longer expiration.
    
    Args:
        user_id: User ID to encode in token
        
    Returns:
        Encoded JWT refresh token string
    """
    expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    
    to_encode = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh"
    }
    
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm
    )


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string to decode
        
    Returns:
        Decoded token payload
        
    Raises:
        JWTError: If token is invalid, expired, or malformed
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        raise JWTError(f"Token validation failed: {str(e)}")


def verify_token(token: str, expected_type: str = "access") -> Dict[str, Any]:
    """
    Verify a JWT token and check its type.
    
    Args:
        token: JWT token string to verify
        expected_type: Expected token type ("access" or "refresh")
        
    Returns:
        Decoded token payload if valid
        
    Raises:
        JWTError: If token is invalid, expired, or wrong type
    """
    payload = decode_token(token)
    
    if payload.get("type") != expected_type:
        raise JWTError(f"Invalid token type. Expected: {expected_type}")
    
    return payload


def generate_api_key() -> Tuple[str, str]:
    """
    Generate a cryptographically secure API key and its hash.
    
    Returns:
        Tuple of (plain_key, key_hash) for secure storage
    """
    # Generate random key using cryptographically secure random
    alphabet = string.ascii_letters + string.digits
    plain_key = ''.join(secrets.choice(alphabet) for _ in range(settings.api_key_length))
    
    # Create HMAC hash for secure storage
    key_hash = hash_api_key(plain_key)
    
    return plain_key, key_hash


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using HMAC-SHA256 for secure storage.
    
    Args:
        api_key: Plain API key to hash
        
    Returns:
        HMAC-SHA256 hash of the API key
    """
    return hmac.new(
        settings.jwt_secret_key.get_secret_value().encode(),
        api_key.encode(),
        hashlib.sha256
    ).hexdigest()


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """
    Verify an API key against its stored hash using constant-time comparison.
    
    Args:
        api_key: Plain API key to verify
        stored_hash: Stored hash of the API key
        
    Returns:
        True if API key matches, False otherwise
    """
    if not api_key or not stored_hash:
        return False
    
    expected_hash = hash_api_key(api_key)
    return hmac.compare_digest(expected_hash, stored_hash)


def generate_password(length: int = 16) -> str:
    """
    Generate a cryptographically secure random password.
    
    Args:
        length: Length of password to generate
        
    Returns:
        Random password string
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_secret_key() -> str:
    """
    Generate a cryptographically secure secret key for JWT signing.
    
    Returns:
        Random secret key string (hex encoded)
    """
    return secrets.token_hex(32)


def is_token_expired(token: str) -> bool:
    """
    Check if a JWT token is expired without raising an exception.
    
    Args:
        token: JWT token to check
        
    Returns:
        True if token is expired, False otherwise
    """
    try:
        payload = decode_token(token)
        exp = payload.get("exp")
        if exp is None:
            return True
        
        return datetime.utcnow() > datetime.fromtimestamp(exp)
    except JWTError:
        return True


def extract_user_id_from_token(token: str) -> Optional[str]:
    """
    Extract user ID from a JWT token without full validation.
    
    Args:
        token: JWT token to extract from
        
    Returns:
        User ID if token is valid, None otherwise
    """
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except JWTError:
        return None


def create_password_reset_token(user_id: str) -> str:
    """
    Create a password reset token with short expiration.
    
    Args:
        user_id: User ID to create token for
        
    Returns:
        Password reset token string
    """
    expire = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiration for security
    
    to_encode = {
        "sub": user_id,
        "exp": expire,
        "type": "password_reset"
    }
    
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm
    )


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify a password reset token and return user ID.
    
    Args:
        token: Password reset token to verify
        
    Returns:
        User ID if token is valid, None otherwise
    """
    try:
        payload = verify_token(token, "password_reset")
        return payload.get("sub")
    except JWTError:
        return None
