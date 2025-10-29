"""
Field-Level Encryption Service

Provides transparent encryption/decryption for sensitive database fields
using Fernet (AES-128-CBC + HMAC-SHA256) from the cryptography library.

SECURITY CRITICAL:
- Encryption keys must be stored securely (Railway env vars, password manager, backup)
- Never log or expose encryption keys
- Supports key rotation with dual-key decryption
- All encrypted values are base64-encoded Fernet tokens

Usage:
    from app.core.encryption import encryptor

    # Encrypt single field
    encrypted = encryptor.encrypt_field("sensitive_data")

    # Decrypt single field
    decrypted = encryptor.decrypt_field(encrypted)

    # Batch operations
    encrypted_dict = encryptor.encrypt_dict_fields(
        {"email": "user@example.com", "name": "John"},
        ["email", "name"]
    )
"""

import base64
import logging
import os
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Base exception for encryption-related errors"""

    pass


class EncryptionKeyError(EncryptionError):
    """Raised when encryption key is missing or invalid"""

    pass


class DecryptionError(EncryptionError):
    """Raised when decryption fails"""

    pass


class FieldEncryptor:
    """
    Field-level encryption service using Fernet symmetric encryption.

    Features:
    - AES-128-CBC encryption with HMAC-SHA256 authentication
    - Automatic key rotation support (dual-key decryption)
    - Batch encryption/decryption operations
    - UTF-8 safe encoding/decoding
    - Performance optimized with key caching

    Environment Variables:
    - ENCRYPTION_KEY: Primary encryption key (base64-encoded Fernet key)
    - ENCRYPTION_KEY_PREVIOUS: Previous key for rotation (optional)
    - ENCRYPTION_ENABLED: Enable/disable encryption (default: true)
    """

    def __init__(self):
        """Initialize the encryption service with environment-based configuration"""
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate that encryption configuration is properly set up"""
        if not self.is_enabled():
            logger.warning("Encryption is disabled via ENCRYPTION_ENABLED=false")
            return

        try:
            self._get_current_cipher()
        except Exception as e:
            raise EncryptionKeyError(
                f"Encryption configuration invalid: {e}. "
                "Ensure ENCRYPTION_KEY is set with a valid Fernet key."
            ) from e

    @staticmethod
    def is_enabled() -> bool:
        """Check if encryption is enabled via environment variable"""
        return os.getenv("ENCRYPTION_ENABLED", "true").lower() == "true"

    @lru_cache(maxsize=1)
    def _get_current_cipher(self) -> Fernet:
        """
        Get the current (primary) encryption cipher.

        Cached for performance - only loads once per application lifecycle.

        Returns:
            Fernet cipher instance for encryption/decryption

        Raises:
            EncryptionKeyError: If ENCRYPTION_KEY is missing or invalid
        """
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise EncryptionKeyError(
                "ENCRYPTION_KEY environment variable is not set. "
                "Generate a key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )

        try:
            return Fernet(key.encode())
        except Exception as e:
            raise EncryptionKeyError(
                f"ENCRYPTION_KEY is invalid or corrupted: {e}"
            ) from e

    @lru_cache(maxsize=1)
    def _get_previous_cipher(self) -> Fernet | None:
        """
        Get the previous encryption cipher for key rotation.

        During key rotation, this allows decrypting data encrypted with the old key
        while new data is encrypted with the current key.

        Returns:
            Fernet cipher instance if previous key exists, None otherwise
        """
        key = os.getenv("ENCRYPTION_KEY_PREVIOUS")
        if not key:
            return None

        try:
            return Fernet(key.encode())
        except Exception as e:
            logger.error(f"ENCRYPTION_KEY_PREVIOUS is invalid: {e}")
            return None

    def encrypt_field(self, plaintext: str | None) -> str | None:
        """
        Encrypt a single field value.

        Args:
            plaintext: The value to encrypt (str or None)

        Returns:
            Base64-encoded encrypted value, or None if input is None/empty

        Raises:
            EncryptionError: If encryption fails

        Example:
            encrypted = encryptor.encrypt_field("patient@example.com")
            # Returns: "gAAAAABk1x2y..." (Fernet token)
        """
        if not self.is_enabled():
            logger.debug("Encryption disabled, returning plaintext")
            return plaintext

        # Handle None and empty strings
        if plaintext is None or (isinstance(plaintext, str) and not plaintext.strip()):
            return None

        try:
            # Convert to string and encode to UTF-8 bytes
            plaintext_str = str(plaintext)
            plaintext_bytes = plaintext_str.encode("utf-8")

            # Encrypt with current cipher
            cipher = self._get_current_cipher()
            encrypted_bytes = cipher.encrypt(plaintext_bytes)

            # Return as base64-encoded string for database storage
            return base64.b64encode(encrypted_bytes).decode("ascii")

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt field: {e}") from e

    def decrypt_field(self, ciphertext: str | None) -> str | None:
        """
        Decrypt a single field value with automatic key rotation support.

        Args:
            ciphertext: Base64-encoded encrypted value (str or None)

        Returns:
            Decrypted plaintext value, or None if input is None

        Raises:
            DecryptionError: If decryption fails with both current and previous keys

        Example:
            decrypted = encryptor.decrypt_field("gAAAAABk1x2y...")
            # Returns: "patient@example.com"
        """
        if not self.is_enabled():
            logger.debug("Encryption disabled, returning ciphertext as-is")
            return ciphertext

        # Handle None and empty strings
        if ciphertext is None or (isinstance(ciphertext, str) and not ciphertext.strip()):
            return None

        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(ciphertext.encode("ascii"))

            # Try current key first
            cipher = self._get_current_cipher()
            try:
                decrypted_bytes = cipher.decrypt(encrypted_bytes)
                return decrypted_bytes.decode("utf-8")
            except InvalidToken:
                # If current key fails, try previous key (key rotation support)
                previous_cipher = self._get_previous_cipher()
                if previous_cipher:
                    logger.debug("Current key failed, trying previous key for decryption")
                    decrypted_bytes = previous_cipher.decrypt(encrypted_bytes)
                    return decrypted_bytes.decode("utf-8")
                else:
                    raise  # No previous key available, re-raise exception

        except InvalidToken as e:
            logger.error(f"Decryption failed - invalid token or wrong key: {e}")
            raise DecryptionError(
                "Failed to decrypt field - invalid token or encryption key mismatch"
            ) from e
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise DecryptionError(f"Failed to decrypt field: {e}") from e

    def encrypt_dict_fields(
        self, data: dict[str, Any], fields: list[str]
    ) -> dict[str, Any]:
        """
        Encrypt multiple fields in a dictionary.

        Args:
            data: Dictionary containing fields to encrypt
            fields: List of field names to encrypt

        Returns:
            New dictionary with specified fields encrypted (original unchanged)

        Example:
            data = {"email": "user@example.com", "name": "John", "age": 30}
            encrypted = encryptor.encrypt_dict_fields(data, ["email", "name"])
            # Returns: {"email": "gAAAAA...", "name": "gAAAAA...", "age": 30}
        """
        if not self.is_enabled():
            return data

        encrypted_data = data.copy()

        for field in fields:
            if field in encrypted_data:
                original_value = encrypted_data[field]
                encrypted_data[field] = self.encrypt_field(original_value)

        return encrypted_data

    def decrypt_dict_fields(
        self, data: dict[str, Any], fields: list[str]
    ) -> dict[str, Any]:
        """
        Decrypt multiple fields in a dictionary.

        Args:
            data: Dictionary containing encrypted fields
            fields: List of field names to decrypt

        Returns:
            New dictionary with specified fields decrypted (original unchanged)

        Example:
            data = {"email": "gAAAAA...", "name": "gAAAAA...", "age": 30}
            decrypted = encryptor.decrypt_dict_fields(data, ["email", "name"])
            # Returns: {"email": "user@example.com", "name": "John", "age": 30}
        """
        if not self.is_enabled():
            return data

        decrypted_data = data.copy()

        for field in fields:
            if field in decrypted_data:
                encrypted_value = decrypted_data[field]
                decrypted_data[field] = self.decrypt_field(encrypted_value)

        return decrypted_data

    def encrypt_batch(self, values: list[str | None]) -> list[str | None]:
        """
        Encrypt a batch of values efficiently.

        Args:
            values: List of plaintext values to encrypt

        Returns:
            List of encrypted values (same order as input)

        Example:
            values = ["email1@example.com", "email2@example.com", None]
            encrypted = encryptor.encrypt_batch(values)
            # Returns: ["gAAAAA...", "gAAAAA...", None]
        """
        if not self.is_enabled():
            return values

        return [self.encrypt_field(value) for value in values]

    def decrypt_batch(self, values: list[str | None]) -> list[str | None]:
        """
        Decrypt a batch of values efficiently.

        Args:
            values: List of encrypted values to decrypt

        Returns:
            List of decrypted values (same order as input)

        Example:
            values = ["gAAAAA...", "gAAAAA...", None]
            decrypted = encryptor.decrypt_batch(values)
            # Returns: ["email1@example.com", "email2@example.com", None]
        """
        if not self.is_enabled():
            return values

        return [self.decrypt_field(value) for value in values]

    def is_encrypted(self, value: str | None) -> bool:
        """
        Check if a value appears to be encrypted (has Fernet token format).

        Args:
            value: Value to check

        Returns:
            True if value looks like a Fernet-encrypted token, False otherwise

        Note:
            This is a heuristic check based on Fernet token format.
            Since we double-encode (Fernet + base64), we need to decode twice.
        """
        if not value or not isinstance(value, str):
            return False

        # Our encrypt_field method base64-encodes the Fernet token
        # So we need to decode twice to check the Fernet version byte
        try:
            # First decode: our base64 encoding
            outer_decoded = base64.b64decode(value.encode("ascii"))
            # Second decode: Fernet's base64 encoding
            inner_decoded = base64.b64decode(outer_decoded)
            # Fernet tokens start with version byte 0x80
            return len(inner_decoded) > 0 and inner_decoded[0] == 0x80
        except Exception:
            return False

    def rotate_key(self, old_encrypted: str) -> str:
        """
        Re-encrypt a value with the current key (for key rotation).

        Args:
            old_encrypted: Value encrypted with previous key

        Returns:
            Value re-encrypted with current key

        Example:
            # During key rotation, re-encrypt all data
            old_value = get_from_db()  # Encrypted with old key
            new_value = encryptor.rotate_key(old_value)
            save_to_db(new_value)  # Now encrypted with new key
        """
        # Decrypt with previous key (falls back automatically)
        decrypted = self.decrypt_field(old_encrypted)

        # Re-encrypt with current key
        return self.encrypt_field(decrypted)


# Global singleton instance
encryptor = FieldEncryptor()
