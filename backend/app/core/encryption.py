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
            raise EncryptionKeyError(f"ENCRYPTION_KEY is invalid or corrupted: {e}") from e

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
            # Fernet.encrypt() returns base64url-encoded bytes, decode directly
            cipher = self._get_current_cipher()
            encrypted_bytes = cipher.encrypt(plaintext_bytes)

            # Return as string (already base64url-encoded by Fernet)
            return encrypted_bytes.decode("utf-8")

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
            # Fernet tokens are already base64url-encoded - pass directly to decrypt()
            # No need to decode first; Fernet.decrypt() handles the base64 internally
            logger.debug(f"Decrypting field: input {len(ciphertext)} chars")
            token_bytes = ciphertext.encode("utf-8")

            # Try current key first
            cipher = self._get_current_cipher()
            try:
                decrypted_bytes = cipher.decrypt(token_bytes)
                result = decrypted_bytes.decode("utf-8")
                logger.debug(f"Decryption successful: {len(result)} chars")
                return result
            except InvalidToken:
                # If current key fails, try previous key (key rotation support)
                previous_cipher = self._get_previous_cipher()
                if previous_cipher:
                    logger.debug("Current key failed, trying previous key for decryption")
                    decrypted_bytes = previous_cipher.decrypt(token_bytes)
                    return decrypted_bytes.decode("utf-8")
                raise  # No previous key available, re-raise exception

        except InvalidToken as e:
            logger.error(f"Decryption failed - invalid token or wrong key: {e}")
            raise DecryptionError(
                "Failed to decrypt field - invalid token or encryption key mismatch"
            ) from e
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise DecryptionError(f"Failed to decrypt field: {e}") from e

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
        Check if a value appears to be encrypted (has Fernet token format).

        Args:
            value: Value to check

        Returns:
            True if value looks like a Fernet-encrypted token, False otherwise

        Note:
            This is a heuristic check based on Fernet token format.
            encrypt_field returns Fernet tokens directly (base64url-encoded).
        """
        if not value or not isinstance(value, str):
            return False

        try:
            # Fernet tokens are base64url-encoded; decode to check version byte
            decoded = base64.urlsafe_b64decode(value)
            # Fernet tokens start with version byte 0x80
            return len(decoded) > 0 and decoded[0] == 0x80
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

    def encrypt_binary_field(self, binary_data: bytes | None) -> str | None:
        """
        Encrypt a binary field (e.g., file content) by converting to base64 first.

        Binary data is first base64-encoded to a string, then encrypted using Fernet.
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
            # Returns: "gAAAAABk1x2y..." (base64-encoded Fernet token)
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

            # Verify it's actually encrypted
            # Note: Fernet tokens start with "gAAAAA" in base64, which is "Z0FBQUFB" in base64 encoding
            # But the encrypted_string is already base64-encoded, so we check for the base64 representation
            if encrypted_string.startswith("gAAAAA"):
                logger.debug(
                    "   ✅ encrypt_binary_field: Verified Fernet token format (starts with 'gAAAAA')"
                )
            elif encrypted_string.startswith("Z0FBQUFB"):
                logger.debug(
                    "   ✅ encrypt_binary_field: Verified Fernet token format (base64 encoded, starts with 'Z0FBQUFB')"
                )
            else:
                # Decode base64 to check if it's a Fernet token
                try:
                    import base64 as b64

                    decoded = b64.b64decode(encrypted_string)
                    if decoded.startswith(b"gAAAAA"):
                        logger.debug(
                            "   ✅ encrypt_binary_field: Verified Fernet token format (after base64 decode)"
                        )
                    else:
                        logger.warning(
                            f"   ⚠️ encrypt_binary_field: Doesn't look like Fernet token: {encrypted_string[:20]}..."
                        )
                except Exception:
                    logger.warning(
                        f"   ⚠️ encrypt_binary_field: Cannot verify token format: {encrypted_string[:20]}..."
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

        Args:
            encrypted_string: Base64-encoded encrypted value (str or None)

        Returns:
            Decrypted binary data (bytes), or None if input is None

        Raises:
            DecryptionError: If decryption fails

        Example:
            encrypted = "gAAAAABk1x2y..."  # From encrypt_binary_field()
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
        stored in PostgreSQL JSON columns.

        Args:
            json_data: Dictionary or JSON-serializable object to encrypt

        Returns:
            Encrypted string (Fernet token), or None if input is None

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

        Args:
            encrypted_string: Encrypted Fernet token from database

        Returns:
            Decrypted dictionary, or None if input is None

        Example:
            encrypted = job.result_data  # From database
            result_data = encryptor.decrypt_json_field(encrypted)
            original_text = result_data["original_text"]

        Note:
            Handles both encrypted and plaintext JSON (for backward compatibility
            with data that was stored before encryption was enabled).
        """
        if not encrypted_string:
            return None

        if not self.is_enabled():
            logger.warning("Encryption disabled - parsing JSON directly")
            import json

            return json.loads(encrypted_string)

        try:
            import json

            # Check if it's encrypted (Fernet token) or plaintext JSON
            # Use heuristic check: Fernet tokens start with 'gAAAAA' or base64-encoded 'Z0FBQUFB'
            looks_encrypted = (
                encrypted_string.startswith("gAAAAA")  # Direct Fernet token
                or encrypted_string.startswith("Z0FBQUFB")  # Base64-encoded Fernet token
            )
            logger.debug(
                f"Checking if encrypted: first 50 chars: {encrypted_string[:50] if encrypted_string else 'EMPTY'}..."
            )
            logger.info(f"looks_encrypted (heuristic): {looks_encrypted}")

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
