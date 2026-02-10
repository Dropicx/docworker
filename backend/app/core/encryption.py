"""
Field-Level Encryption Service

Provides transparent encryption/decryption for sensitive database fields
using AES-256-GCM (Galois/Counter Mode) from the cryptography library.

GDPR "Stand der Technik" (State of the Art) compliant:
- AES-256-GCM provides authenticated encryption with 256-bit security
- 96-bit nonces ensure uniqueness for each encryption
- 128-bit authentication tags prevent tampering

SECURITY CRITICAL:
- Encryption keys must be stored securely (Railway env vars, password manager, backup)
- Never log or expose encryption keys
- Supports key rotation with dual-key decryption
- Backward compatible with legacy Fernet tokens during migration

Token Format:
- AES-256-GCM: version(1) + timestamp(8) + nonce(12) + ciphertext + tag(16)
- Version byte 0xAE distinguishes from Fernet's 0x80

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
import struct
import time
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

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


# Version byte for AES-256-GCM tokens (distinguishes from Fernet's 0x80)
AES256GCM_VERSION = 0xAE

# Nonce size for AES-256-GCM (96 bits = 12 bytes, NIST recommended)
AES256GCM_NONCE_SIZE = 12

# Timestamp size (8 bytes for 64-bit timestamp)
AES256GCM_TIMESTAMP_SIZE = 8


class FieldEncryptor:
    """
    Field-level encryption service using AES-256-GCM authenticated encryption.

    Features:
    - AES-256-GCM encryption with 256-bit security (GDPR "Stand der Technik")
    - Authenticated encryption prevents tampering (128-bit auth tag)
    - Automatic key rotation support (dual-key decryption)
    - Backward compatibility with legacy Fernet tokens during migration
    - Batch encryption/decryption operations
    - UTF-8 safe encoding/decoding
    - Performance optimized with key caching

    Environment Variables:
    - ENCRYPTION_KEY: Primary encryption key (base64-encoded, 32 bytes for AES-256)
    - ENCRYPTION_KEY_PREVIOUS: Previous key for rotation (optional)
    - ENCRYPTION_KEY_FERNET_LEGACY: Legacy Fernet key for migration (optional)
    - ENCRYPTION_ENABLED: Enable/disable encryption (default: true)

    Token Format (AES-256-GCM):
    - Byte 0: Version (0xAE)
    - Bytes 1-8: Timestamp (64-bit, big-endian)
    - Bytes 9-20: Nonce (96-bit)
    - Remaining: Ciphertext + Authentication Tag (16 bytes at end)
    """

    def __init__(self):
        """Initialize the encryption service with environment-based configuration"""
        self._aesgcm_cache: AESGCM | None = None
        self._aesgcm_previous_cache: AESGCM | None = None
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate that encryption configuration is properly set up"""
        if not self.is_enabled():
            logger.warning("Encryption is disabled via ENCRYPTION_ENABLED=false")
            return

        try:
            self._get_aesgcm_cipher()
        except Exception as e:
            raise EncryptionKeyError(
                f"Encryption configuration invalid: {e}. "
                "Ensure ENCRYPTION_KEY is set with a valid 256-bit key (44 chars base64)."
            ) from e

    @staticmethod
    def is_enabled() -> bool:
        """Check if encryption is enabled via environment variable"""
        return os.getenv("ENCRYPTION_ENABLED", "true").lower() == "true"

    def _get_aesgcm_cipher(self) -> AESGCM:
        """
        Get the current (primary) AES-256-GCM cipher.

        Cached for performance - only loads once per application lifecycle.

        Returns:
            AESGCM cipher instance for encryption/decryption

        Raises:
            EncryptionKeyError: If ENCRYPTION_KEY is missing or invalid
        """
        if self._aesgcm_cache is not None:
            return self._aesgcm_cache

        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise EncryptionKeyError(
                "ENCRYPTION_KEY environment variable is not set. "
                "Generate a key with: python -c 'import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())'"
            )

        try:
            key_bytes = base64.urlsafe_b64decode(key.encode())
            if len(key_bytes) != 32:
                raise EncryptionKeyError(
                    f"ENCRYPTION_KEY must be 32 bytes (256 bits), got {len(key_bytes)} bytes. "
                    "Generate a new key with: python -c 'import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())'"
                )
            self._aesgcm_cache = AESGCM(key_bytes)
            return self._aesgcm_cache
        except Exception as e:
            if isinstance(e, EncryptionKeyError):
                raise
            raise EncryptionKeyError(f"ENCRYPTION_KEY is invalid or corrupted: {e}") from e

    def _get_aesgcm_previous_cipher(self) -> AESGCM | None:
        """
        Get the previous AES-256-GCM cipher for key rotation.

        During key rotation, this allows decrypting data encrypted with the old key
        while new data is encrypted with the current key.

        Returns:
            AESGCM cipher instance if previous key exists, None otherwise
        """
        if self._aesgcm_previous_cache is not None:
            return self._aesgcm_previous_cache

        key = os.getenv("ENCRYPTION_KEY_PREVIOUS")
        if not key:
            return None

        try:
            key_bytes = base64.urlsafe_b64decode(key.encode())
            if len(key_bytes) != 32:
                logger.error(f"ENCRYPTION_KEY_PREVIOUS must be 32 bytes, got {len(key_bytes)}")
                return None
            self._aesgcm_previous_cache = AESGCM(key_bytes)
            return self._aesgcm_previous_cache
        except Exception as e:
            logger.error(f"ENCRYPTION_KEY_PREVIOUS is invalid: {e}")
            return None

    def _get_fernet_legacy_cipher(self) -> Fernet | None:
        """
        Get the legacy Fernet cipher for migration from AES-128-CBC.

        This is used during migration to decrypt old Fernet-encrypted data.
        Set ENCRYPTION_KEY_FERNET_LEGACY to your old Fernet key during migration.

        Returns:
            Fernet cipher instance if legacy key exists, None otherwise
        """
        key = os.getenv("ENCRYPTION_KEY_FERNET_LEGACY")
        if not key:
            return None

        try:
            return Fernet(key.encode())
        except Exception as e:
            logger.error(f"ENCRYPTION_KEY_FERNET_LEGACY is invalid: {e}")
            return None

    def _get_current_cipher(self) -> Fernet:
        """
        Get the current Fernet cipher (deprecated, for backward compatibility only).

        DEPRECATED: Use _get_aesgcm_cipher() for new encryption.
        This method is kept for backward compatibility during migration.

        Returns:
            Fernet cipher instance for decryption of legacy tokens
        """
        legacy = self._get_fernet_legacy_cipher()
        if legacy:
            return legacy

        # Fallback: try to use ENCRYPTION_KEY as Fernet key (for legacy setups)
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise EncryptionKeyError("No Fernet key available for legacy decryption")

        try:
            return Fernet(key.encode())
        except Exception as e:
            raise EncryptionKeyError(f"Cannot create Fernet cipher from ENCRYPTION_KEY: {e}") from e

    def _get_previous_cipher(self) -> Fernet | None:
        """
        Get the previous Fernet cipher for legacy key rotation.

        DEPRECATED: For legacy Fernet token decryption during migration.

        Returns:
            Fernet cipher instance if previous key exists, None otherwise
        """
        key = os.getenv("ENCRYPTION_KEY_PREVIOUS")
        if not key:
            return None

        try:
            return Fernet(key.encode())
        except Exception as e:
            logger.error(f"ENCRYPTION_KEY_PREVIOUS is invalid as Fernet key: {e}")
            return None

    def _encrypt_aes256gcm(self, plaintext_bytes: bytes) -> bytes:
        """
        Encrypt data using AES-256-GCM.

        Token format:
        - Byte 0: Version (0xAE)
        - Bytes 1-8: Timestamp (64-bit, big-endian)
        - Bytes 9-20: Nonce (96-bit)
        - Remaining: Ciphertext + Authentication Tag (16 bytes)

        Args:
            plaintext_bytes: Data to encrypt

        Returns:
            Encrypted token as bytes
        """
        cipher = self._get_aesgcm_cipher()

        # Generate random nonce (96 bits = 12 bytes, NIST recommended)
        nonce = os.urandom(AES256GCM_NONCE_SIZE)

        # Current timestamp (for audit/debugging, not used for security)
        timestamp = struct.pack(">Q", int(time.time()))

        # Encrypt with authentication
        ciphertext = cipher.encrypt(nonce, plaintext_bytes, None)

        # Build token: version + timestamp + nonce + ciphertext
        token = bytes([AES256GCM_VERSION]) + timestamp + nonce + ciphertext

        return token

    def _decrypt_aes256gcm(self, token: bytes) -> bytes:
        """
        Decrypt data encrypted with AES-256-GCM.

        Args:
            token: Encrypted token bytes

        Returns:
            Decrypted plaintext bytes

        Raises:
            DecryptionError: If decryption fails
        """
        min_length = 1 + AES256GCM_TIMESTAMP_SIZE + AES256GCM_NONCE_SIZE + 16  # version + timestamp + nonce + tag
        if len(token) < min_length:
            raise DecryptionError(f"Token too short: {len(token)} bytes (minimum {min_length})")

        # Parse token
        version = token[0]
        if version != AES256GCM_VERSION:
            raise DecryptionError(f"Invalid token version: 0x{version:02X} (expected 0x{AES256GCM_VERSION:02X})")

        # Extract components
        timestamp_end = 1 + AES256GCM_TIMESTAMP_SIZE
        nonce_end = timestamp_end + AES256GCM_NONCE_SIZE

        # timestamp = struct.unpack(">Q", token[1:timestamp_end])[0]  # Available for debugging
        nonce = token[timestamp_end:nonce_end]
        ciphertext = token[nonce_end:]

        # Try current key first
        cipher = self._get_aesgcm_cipher()
        try:
            return cipher.decrypt(nonce, ciphertext, None)
        except Exception as current_error:
            # Try previous key for rotation support
            previous_cipher = self._get_aesgcm_previous_cipher()
            if previous_cipher:
                try:
                    logger.debug("Current key failed, trying previous key for decryption")
                    return previous_cipher.decrypt(nonce, ciphertext, None)
                except Exception:
                    pass  # Fall through to raise original error

            raise DecryptionError(
                f"Failed to decrypt AES-256-GCM token: {current_error}"
            ) from current_error

    def _is_fernet_token(self, token_bytes: bytes) -> bool:
        """
        Check if token bytes appear to be a Fernet token.

        Fernet tokens start with version byte 0x80.

        Args:
            token_bytes: Raw token bytes (after base64 decoding)

        Returns:
            True if this looks like a Fernet token
        """
        return len(token_bytes) > 0 and token_bytes[0] == 0x80

    def _is_aes256gcm_token(self, token_bytes: bytes) -> bool:
        """
        Check if token bytes appear to be an AES-256-GCM token.

        AES-256-GCM tokens start with version byte 0xAE.

        Args:
            token_bytes: Raw token bytes (after base64 decoding)

        Returns:
            True if this looks like an AES-256-GCM token
        """
        return len(token_bytes) > 0 and token_bytes[0] == AES256GCM_VERSION

    def encrypt_field(self, plaintext: str | None) -> str | None:
        """
        Encrypt a single field value using AES-256-GCM.

        Args:
            plaintext: The value to encrypt (str or None)

        Returns:
            Base64-encoded encrypted value, or None if input is None/empty

        Raises:
            EncryptionError: If encryption fails

        Example:
            encrypted = encryptor.encrypt_field("patient@example.com")
            # Returns: "rgAAAA..." (AES-256-GCM token, starts with 0xAE base64-encoded)
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

            # Encrypt with AES-256-GCM
            encrypted_bytes = self._encrypt_aes256gcm(plaintext_bytes)

            # Base64url-encode for safe storage
            return base64.urlsafe_b64encode(encrypted_bytes).decode("utf-8")

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt field: {e}") from e

    def decrypt_field(self, ciphertext: str | None) -> str | None:
        """
        Decrypt a single field value with automatic format detection and key rotation.

        Supports both:
        - AES-256-GCM tokens (version byte 0xAE) - current format
        - Fernet tokens (version byte 0x80) - legacy format for migration

        Args:
            ciphertext: Base64-encoded encrypted value (str or None)

        Returns:
            Decrypted plaintext value, or None if input is None

        Raises:
            DecryptionError: If decryption fails with all available keys

        Example:
            decrypted = encryptor.decrypt_field("rgAAAA...")  # AES-256-GCM
            decrypted = encryptor.decrypt_field("gAAAAABk1x2y...")  # Legacy Fernet
            # Returns: "patient@example.com"
        """
        if not self.is_enabled():
            logger.debug("Encryption disabled, returning ciphertext as-is")
            return ciphertext

        # Handle None and empty strings
        if ciphertext is None or (isinstance(ciphertext, str) and not ciphertext.strip()):
            return None

        try:
            logger.debug(f"Decrypting field: input {len(ciphertext)} chars")

            # Decode base64 to check version byte
            try:
                token_bytes = base64.urlsafe_b64decode(ciphertext.encode("utf-8"))
            except Exception:
                # If base64 decode fails, might be direct Fernet token (they handle their own base64)
                token_bytes = ciphertext.encode("utf-8")

            # Detect token format and decrypt accordingly
            if len(token_bytes) > 0:
                if self._is_aes256gcm_token(token_bytes):
                    # AES-256-GCM token
                    decrypted_bytes = self._decrypt_aes256gcm(token_bytes)
                    result = decrypted_bytes.decode("utf-8")
                    logger.debug(f"AES-256-GCM decryption successful: {len(result)} chars")
                    return result

                elif self._is_fernet_token(token_bytes):
                    # Legacy Fernet token - use Fernet decryption
                    logger.debug("Detected legacy Fernet token, using Fernet decryption")
                    return self._decrypt_fernet_legacy(ciphertext)

            # If we couldn't detect format, try Fernet first (original behavior)
            # This handles cases where the token is still base64-encoded Fernet
            return self._decrypt_fernet_legacy(ciphertext)

        except DecryptionError:
            raise
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise DecryptionError(f"Failed to decrypt field: {e}") from e

    def _decrypt_fernet_legacy(self, ciphertext: str) -> str:
        """
        Decrypt a legacy Fernet token.

        Used for backward compatibility during migration from AES-128-CBC.

        Args:
            ciphertext: Fernet token string

        Returns:
            Decrypted plaintext

        Raises:
            DecryptionError: If decryption fails
        """
        token_bytes = ciphertext.encode("utf-8")

        # Try legacy Fernet key first (ENCRYPTION_KEY_FERNET_LEGACY)
        legacy_cipher = self._get_fernet_legacy_cipher()
        if legacy_cipher:
            try:
                decrypted_bytes = legacy_cipher.decrypt(token_bytes)
                logger.debug("Legacy Fernet decryption successful with ENCRYPTION_KEY_FERNET_LEGACY")
                return decrypted_bytes.decode("utf-8")
            except InvalidToken:
                pass  # Try other keys

        # Try current key as Fernet (for backward compatibility)
        try:
            cipher = self._get_current_cipher()
            decrypted_bytes = cipher.decrypt(token_bytes)
            logger.debug("Fernet decryption successful with current key")
            return decrypted_bytes.decode("utf-8")
        except InvalidToken:
            # Try previous key (key rotation support)
            previous_cipher = self._get_previous_cipher()
            if previous_cipher:
                try:
                    logger.debug("Current key failed, trying previous key for Fernet decryption")
                    decrypted_bytes = previous_cipher.decrypt(token_bytes)
                    return decrypted_bytes.decode("utf-8")
                except InvalidToken:
                    pass

        raise DecryptionError(
            "Failed to decrypt field - invalid token or encryption key mismatch"
        )

    def encrypt_dict_fields(self, data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
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

    def decrypt_dict_fields(self, data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
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
        Check if a value appears to be encrypted.

        Detects both:
        - AES-256-GCM tokens (version byte 0xAE)
        - Legacy Fernet tokens (version byte 0x80)

        Args:
            value: Value to check

        Returns:
            True if value looks like an encrypted token, False otherwise

        Note:
            This is a heuristic check based on token version bytes.
        """
        if not value or not isinstance(value, str):
            return False

        try:
            # Tokens are base64url-encoded; decode to check version byte
            decoded = base64.urlsafe_b64decode(value)
            if len(decoded) == 0:
                return False

            # Check for AES-256-GCM (0xAE) or Fernet (0x80) version bytes
            return decoded[0] == AES256GCM_VERSION or decoded[0] == 0x80
        except Exception:
            return False

    def is_legacy_fernet(self, value: str | None) -> bool:
        """
        Check if a value is encrypted with legacy Fernet (AES-128-CBC).

        Useful for identifying records that need migration to AES-256-GCM.

        Args:
            value: Value to check

        Returns:
            True if value looks like a Fernet token (version byte 0x80)
        """
        if not value or not isinstance(value, str):
            return False

        try:
            decoded = base64.urlsafe_b64decode(value)
            return len(decoded) > 0 and decoded[0] == 0x80
        except Exception:
            return False

    def is_aes256gcm(self, value: str | None) -> bool:
        """
        Check if a value is encrypted with AES-256-GCM.

        Args:
            value: Value to check

        Returns:
            True if value looks like an AES-256-GCM token (version byte 0xAE)
        """
        if not value or not isinstance(value, str):
            return False

        try:
            decoded = base64.urlsafe_b64decode(value)
            return len(decoded) > 0 and decoded[0] == AES256GCM_VERSION
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

        # Re-encrypt with current key (AES-256-GCM)
        return self.encrypt_field(decrypted)

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new AES-256-GCM encryption key.

        Returns:
            Base64url-encoded 256-bit key (44 characters)

        Example:
            key = FieldEncryptor.generate_key()
            # Returns: "kB4xY2z..." (44-character base64url string)
            # Set this as ENCRYPTION_KEY environment variable
        """
        key_bytes = os.urandom(32)  # 256 bits
        return base64.urlsafe_b64encode(key_bytes).decode("utf-8")

    def encrypt_binary_field(self, binary_data: bytes | None) -> str | None:
        """
        Encrypt a binary field (e.g., file content) by converting to base64 first.

        Binary data is first base64-encoded to a string, then encrypted using AES-256-GCM.
        This allows storing encrypted binary data as text in the database.

        Args:
            binary_data: Binary data to encrypt (bytes or None)

        Returns:
            Base64-encoded encrypted value as string, or None if input is None

        Raises:
            EncryptionError: If encryption fails

        Example:
            with open("document.pdf", "rb") as f:
                file_content = f.read()
            encrypted = encryptor.encrypt_binary_field(file_content)
            # Returns: "rgAAAA..." (base64-encoded AES-256-GCM token)
        """
        if not self.is_enabled():
            logger.warning(
                "⚠️ Encryption disabled in encrypt_binary_field, returning base64-encoded binary (NOT ENCRYPTED)"
            )
            if binary_data is None:
                return None
            return base64.b64encode(binary_data).decode("ascii")

        # Handle None
        if binary_data is None:
            return None

        try:
            binary_size = len(binary_data)
            logger.debug(f"   encrypt_binary_field: Input {binary_size} bytes")

            # Step 1: Convert binary to base64 string
            base64_string = base64.b64encode(binary_data).decode("ascii")
            base64_size = len(base64_string)
            logger.debug(f"   encrypt_binary_field: Base64 encoded to {base64_size} chars")

            # Step 2: Encrypt the base64 string (treat as text)
            encrypted_string = self.encrypt_field(base64_string)

            if encrypted_string:
                encrypted_size = len(encrypted_string)
                logger.debug(f"   encrypt_binary_field: Encrypted to {encrypted_size} chars")

                # Verify it's actually encrypted (AES-256-GCM tokens start with 0xAE)
                if self.is_aes256gcm(encrypted_string):
                    logger.debug(
                        "   ✅ encrypt_binary_field: Verified AES-256-GCM token format"
                    )
                else:
                    logger.warning(
                        f"   ⚠️ encrypt_binary_field: Unexpected token format: {encrypted_string[:20]}..."
                    )

            return encrypted_string

        except Exception as e:
            logger.error(f"Binary encryption failed: {e}")
            import traceback

            logger.error(traceback.format_exc())
            raise EncryptionError(f"Failed to encrypt binary field: {e}") from e

    def decrypt_binary_field(self, encrypted_string: str | None) -> bytes | None:
        """
        Decrypt a binary field by decrypting then base64-decoding.

        Supports both AES-256-GCM and legacy Fernet tokens.

        Args:
            encrypted_string: Base64-encoded encrypted value (str or None)

        Returns:
            Decrypted binary data (bytes), or None if input is None

        Raises:
            DecryptionError: If decryption fails

        Example:
            encrypted = "rgAAAA..."  # From encrypt_binary_field()
            binary_data = encryptor.decrypt_binary_field(encrypted)
            # Returns: b'%PDF-1.4...' (original binary data)
        """
        if not self.is_enabled():
            logger.debug("Encryption disabled, returning base64-decoded binary")
            if encrypted_string is None:
                return None
            try:
                return base64.b64decode(encrypted_string.encode("ascii"))
            except Exception:
                # If it's not base64, return as-is (backward compatibility)
                return encrypted_string.encode("utf-8") if encrypted_string else None

        # Handle None
        if encrypted_string is None:
            return None

        try:
            # Step 1: Decrypt the encrypted string (returns base64 string)
            base64_string = self.decrypt_field(encrypted_string)

            if base64_string is None:
                return None

            # Step 2: Decode base64 string back to binary
            return base64.b64decode(base64_string.encode("ascii"))

        except Exception as e:
            logger.error(f"Binary decryption failed: {e}")
            raise DecryptionError(f"Failed to decrypt binary field: {e}") from e

    def encrypt_json_field(self, json_data: dict | None) -> str | None:
        """
        Encrypt a JSON/dict field by serializing to JSON string first.

        This allows encrypting complex data structures (dicts, lists) that are
        stored in PostgreSQL JSON columns using AES-256-GCM.

        Args:
            json_data: Dictionary or JSON-serializable object to encrypt

        Returns:
            Encrypted string (AES-256-GCM token), or None if input is None

        Example:
            result_data = {"original_text": "...", "translated_text": "..."}
            encrypted = encryptor.encrypt_json_field(result_data)
            # Store encrypted string in database JSON column

        Note:
            The JSON serialization is done before encryption, so the encrypted
            value is a string, not a JSON object. The database column should
            store this as TEXT or VARCHAR, not JSON type.
        """
        if not json_data:
            logger.debug("No JSON data to encrypt (None or empty)")
            return None

        if not self.is_enabled():
            logger.warning("Encryption disabled - returning JSON as string")
            import json

            return json.dumps(json_data)

        try:
            import json

            # Step 1: Serialize dict to JSON string
            json_string = json.dumps(json_data, ensure_ascii=False)
            logger.debug(f"Serialized JSON to {len(json_string)} chars")

            # Step 2: Encrypt the JSON string
            encrypted_string = self.encrypt_field(json_string)
            logger.debug(
                f"Encrypted JSON field: {len(json_string)} chars → {len(encrypted_string) if encrypted_string else 0} chars"
            )

            return encrypted_string

        except Exception as e:
            logger.error(f"JSON encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt JSON field: {e}") from e

    def decrypt_json_field(self, encrypted_string: str | None) -> dict | None:
        """
        Decrypt a JSON field back to dict.

        Supports both AES-256-GCM and legacy Fernet tokens.

        Args:
            encrypted_string: Encrypted token from database

        Returns:
            Decrypted dictionary, or None if input is None

        Example:
            encrypted = job.result_data  # From database
            result_data = encryptor.decrypt_json_field(encrypted)
            original_text = result_data["original_text"]

        Note:
            Handles encrypted (AES-256-GCM or Fernet) and plaintext JSON
            (for backward compatibility with data stored before encryption).
        """
        if not encrypted_string:
            return None

        if not self.is_enabled():
            logger.warning("Encryption disabled - parsing JSON directly")
            import json

            return json.loads(encrypted_string)

        try:
            import json

            # Check if it's encrypted (AES-256-GCM or Fernet) or plaintext JSON
            looks_encrypted = self.is_encrypted(encrypted_string)
            logger.debug(
                f"Checking if encrypted: first 50 chars: {encrypted_string[:50] if encrypted_string else 'EMPTY'}..."
            )
            logger.debug(f"looks_encrypted: {looks_encrypted}")

            if looks_encrypted:
                # Step 1: Decrypt to JSON string
                json_string = self.decrypt_field(encrypted_string)

                if json_string is None:
                    logger.error("decrypt_field returned None")
                    return None

                logger.info(
                    f"Decrypted JSON field: {len(encrypted_string)} chars → {len(json_string)} chars"
                )

                # Debug: Log first 100 chars of decrypted string
                if json_string:
                    logger.debug(f"Decrypted content preview: {json_string[:100]}...")
                else:
                    logger.error("decrypt_field returned empty string!")

                # Step 2: Parse JSON string to dict
                return json.loads(json_string)

            # Plaintext JSON (backward compatibility) - is_encrypted returned False
            logger.warning(
                f"is_encrypted=False, treating as plaintext JSON. First 50 chars: {encrypted_string[:50]}..."
            )
            return json.loads(encrypted_string)

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            raise DecryptionError(f"Failed to parse JSON after decryption: {e}") from e
        except Exception as e:
            logger.error(f"JSON decryption failed: {e}")
            raise DecryptionError(f"Failed to decrypt JSON field: {e}") from e

    @staticmethod
    def generate_searchable_hash(value: str | None) -> str | None:
        """
        Generate SHA-256 hash for searchable encrypted field lookups.

        This allows searching encrypted fields by comparing hashes instead of
        decrypting every record. The hash is deterministic (same input = same hash).

        Args:
            value: Plaintext value to hash

        Returns:
            Hex string of SHA-256 hash (64 characters), or None if input is None

        Example:
            # Generate hash for email lookup
            email_hash = encryptor.generate_searchable_hash("user@example.com")
            # Query: WHERE email_searchable = :hash

        Security Note:
            - SHA-256 is one-way (can't reverse to get original value)
            - Same input always produces same hash (enables search)
            - Different from encryption (can't decrypt a hash)
        """
        if not value:
            return None

        import hashlib

        return hashlib.sha256(value.encode("utf-8")).hexdigest()


# Global singleton instance
encryptor = FieldEncryptor()
