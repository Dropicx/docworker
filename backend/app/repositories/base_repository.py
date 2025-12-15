"""
Base Repository Pattern

Provides generic CRUD operations for database entities.
All specific repositories should inherit from BaseRepository.

Includes EncryptedRepositoryMixin for transparent field-level encryption.
"""

import logging
from typing import Any, Generic, TypeVar

from sqlalchemy import JSON, LargeBinary
from sqlalchemy.orm import Session

from app.core.encryption import encryptor

logger = logging.getLogger(__name__)

# Generic type for database models
ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Base repository providing common CRUD operations.

    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self, db: Session):
                super().__init__(db, User)
    """

    def __init__(self, db: Session, model: type[ModelType]):
        """
        Initialize repository with database session and model class.

        Args:
            db: SQLAlchemy session
            model: SQLAlchemy model class
        """
        self.db = db
        self.model = model

    def get(self, record_id: Any) -> ModelType | None:
        """
        Get entity by primary key (convenience method).

        Alias for get_by_id() for shorter syntax.

        Args:
            record_id: Primary key value

        Returns:
            Entity instance or None if not found
        """
        return self.get_by_id(record_id)

    def get_by_id(self, record_id: Any) -> ModelType | None:
        """Get entity by primary key."""
        try:
            return self.db.query(self.model).filter(self.model.id == record_id).first()
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by id={record_id}: {e}")
            raise

    def get_all(
        self, skip: int = 0, limit: int = 100, filters: dict[str, Any] | None = None
    ) -> list[ModelType]:
        """
        Get all entities with optional filtering and pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of field:value filters
        """
        try:
            query = self.db.query(self.model)

            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        query = query.filter(getattr(self.model, field) == value)

            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting all {self.model.__name__}: {e}")
            raise

    def get_one(self, filters: dict[str, Any]) -> ModelType | None:
        """
        Get single entity by filters.

        Args:
            filters: Dictionary of field:value filters
        """
        try:
            query = self.db.query(self.model)

            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)

            return query.first()
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} with filters {filters}: {e}")
            raise

    def create(self, **kwargs) -> ModelType:
        """
        Create new entity.

        Args:
            **kwargs: Field values for new entity
        """
        try:
            entity = self.model(**kwargs)
            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)

            logger.info("Created {self.model.__name__} with id={entity.id}")
            return entity
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise

    def update(self, record_id: Any, **kwargs) -> ModelType | None:
        """
        Update entity by primary key.

        Args:
            record_id: Primary key value
            **kwargs: Fields to update
        """
        try:
            entity = self.get_by_id(record_id)
            if not entity:
                logger.warning("{self.model.__name__} with id={record_id} not found")
                return None

            for key, value in kwargs.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)

            self.db.commit()
            self.db.refresh(entity)

            logger.info("Updated {self.model.__name__} with id={record_id}")
            return entity
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating {self.model.__name__} id={record_id}: {e}")
            raise

    def delete(self, record_id: Any) -> bool:
        """
        Delete entity by primary key.

        Args:
            record_id: Primary key value

        Returns:
            True if deleted, False if not found
        """
        try:
            entity = self.get_by_id(record_id)
            if not entity:
                logger.warning("{self.model.__name__} with id={record_id} not found")
                return False

            self.db.delete(entity)
            self.db.commit()

            logger.info("Deleted {self.model.__name__} with id={record_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting {self.model.__name__} id={record_id}: {e}")
            raise

    def count(self, filters: dict[str, Any] | None = None) -> int:
        """
        Count entities with optional filtering.

        Args:
            filters: Dictionary of field:value filters
        """
        try:
            query = self.db.query(self.model)

            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        query = query.filter(getattr(self.model, field) == value)

            return query.count()
        except Exception as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            raise

    def exists(self, filters: dict[str, Any]) -> bool:
        """
        Check if entity exists with given filters.

        Args:
            filters: Dictionary of field:value filters
        """
        return self.count(filters) > 0


class EncryptedRepositoryMixin:
    """
    Mixin for repositories that need transparent field-level encryption.

    Usage:
        class UserRepository(BaseRepository[UserDB], EncryptedRepositoryMixin):
            encrypted_fields = ['email', 'full_name']

            def __init__(self, db: Session):
                super().__init__(db, UserDB)

    The mixin automatically encrypts fields on write and decrypts on read.
    Service layer code remains unchanged - encryption is completely transparent.
    """

    # Override this in subclasses to specify which fields to encrypt
    encrypted_fields: list[str] = []

    def _should_encrypt_field(self, field_name: str) -> bool:
        """
        Check if a field should be encrypted.

        Args:
            field_name: Name of the field to check

        Returns:
            True if field should be encrypted, False otherwise
        """
        return field_name in self.encrypted_fields

    def _is_binary_field(self, field_name: str) -> bool:
        """
        Check if a field is a binary field (LargeBinary column type).

        Args:
            field_name: Name of the field to check

        Returns:
            True if field is binary, False otherwise
        """
        if not hasattr(self.model, field_name):
            return False

        column = getattr(self.model, field_name).property.columns[0]
        return isinstance(column.type, LargeBinary)

    def _is_json_field(self, field_name: str) -> bool:
        """
        Check if a field is a JSON field (JSON column type).

        Args:
            field_name: Name of the field to check

        Returns:
            True if field is JSON, False otherwise
        """
        if not hasattr(self.model, field_name):
            return False

        column = getattr(self.model, field_name).property.columns[0]
        return isinstance(column.type, JSON)

    def _is_json_encrypted_field(self, field_name: str) -> bool:
        """
        Check if a field contains encrypted JSON (dict → JSON string → encrypted string).
        
        These fields are stored as Text columns but contain encrypted JSON data that should
        be decrypted to a dict.

        Args:
            field_name: Name of the field to check

        Returns:
            True if field is a JSON-encrypted field (like result_data)
        """
        # Hardcode for now - result_data is the only field that stores encrypted JSON as Text
        return field_name == "result_data"

    def _encrypt_fields(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Encrypt specified fields in a dictionary.

        Handles both text fields (str) and binary fields (bytes) automatically.

        Args:
            data: Dictionary containing fields to encrypt

        Returns:
            New dictionary with encrypted fields
        """
        if not self.encrypted_fields:
            logger.debug(f"No encrypted fields defined for {self.model.__name__}")
            return data
        
        if not encryptor.is_enabled():
            logger.warning(f"⚠️ Encryption is disabled for {self.model.__name__} - fields will be stored in plaintext!")
            return data

        logger.info(f"🔐 Encrypting fields for {self.model.__name__}: {self.encrypted_fields}")
        logger.info(f"   Encryption enabled: {encryptor.is_enabled()}")
        encrypted_data = data.copy()

        for field in self.encrypted_fields:
            if field in encrypted_data and encrypted_data[field] is not None:
                try:
                    if self._is_binary_field(field):
                        logger.debug(f"   Field {field} is binary (LargeBinary)")
                        # Binary field: use binary encryption
                        if isinstance(encrypted_data[field], bytes):
                            original_binary = encrypted_data[field]
                            original_size = len(original_binary)
                            logger.info(f"   📦 Encrypting {field}: {original_size} bytes (type: bytes)")
                            
                            # Show first few bytes of original
                            original_preview = original_binary[:20].hex()
                            logger.debug(f"   Original preview (hex): {original_preview}...")
                            
                            # Encrypt binary → returns base64-encoded string
                            encrypted_str = encryptor.encrypt_binary_field(original_binary)
                            
                            if encrypted_str:
                                logger.debug(f"   Encryption returned string of length: {len(encrypted_str)}")
                                
                                # Verify encryption actually happened
                                try:
                                    original_as_str = original_binary.decode("utf-8", errors="ignore")
                                    if encrypted_str == original_as_str:
                                        logger.error(f"❌ Encryption returned same value as input for {field}!")
                                        raise ValueError(f"Encryption failed - returned plaintext")
                                except UnicodeDecodeError:
                                    # Can't decode as UTF-8, so definitely different
                                    pass
                                
                                # Verify it looks encrypted (should start with Fernet token prefix)
                                preview = encrypted_str[:20]
                                logger.debug(f"   Encrypted preview: {preview}...")
                                if not preview.startswith("gAAAAA"):
                                    logger.warning(f"   ⚠️ Encrypted data doesn't look like Fernet token: {preview}...")
                                else:
                                    logger.debug(f"   ✅ Verified: Encrypted token starts with 'gAAAAA' (Fernet format)")
                                
                                # Convert encrypted string to bytes for LargeBinary column
                                encrypted_bytes = encrypted_str.encode("utf-8")
                                encrypted_size = len(encrypted_bytes)
                                
                                # Store encrypted bytes
                                encrypted_data[field] = encrypted_bytes
                                
                                size_increase = (encrypted_size / original_size * 100) if original_size > 0 else 0
                                logger.info(f"✅ Encrypted binary field: {field} ({original_size} bytes → {encrypted_size} bytes, {size_increase:.1f}% size increase)")
                                
                                # Final verification - check what we're about to store
                                stored_preview = encrypted_bytes[:50].decode("utf-8", errors="ignore")
                                logger.debug(f"   Will store (first 50 chars): {stored_preview}...")
                            else:
                                logger.error(f"❌ Encryption returned None for {field}!")
                                raise ValueError(f"Encryption failed for {field} - returned None")
                        else:
                            # If it's already a string (from database), treat as text
                            encrypted_data[field] = encryptor.encrypt_field(
                                str(encrypted_data[field])
                            )
                            logger.debug(f"Encrypted field (as text): {field}")
                    elif self._is_json_field(field):
                        # JSON field: use JSON encryption (dict/list → JSON string → encrypted string)
                        logger.debug(f"   Field {field} is JSON")
                        if isinstance(encrypted_data[field], dict):
                            original_json = encrypted_data[field]
                            logger.info(f"   📋 Encrypting {field}: JSON dict with {len(original_json)} keys")
                            
                            # Encrypt dict → returns encrypted string
                            encrypted_str = encryptor.encrypt_json_field(original_json)
                            
                            if encrypted_str:
                                encrypted_data[field] = encrypted_str
                                logger.info(f"✅ Encrypted JSON field: {field} ({len(str(original_json))} chars → {len(encrypted_str)} chars)")
                            else:
                                logger.error(f"❌ Encryption returned None for JSON field {field}!")
                                raise ValueError(f"Encryption failed for {field} - returned None")
                        else:
                            logger.warning(f"⚠️ JSON field {field} is not a dict, treating as text")
                            encrypted_data[field] = encryptor.encrypt_field(
                                str(encrypted_data[field])
                            )
                    elif self._is_json_encrypted_field(field):
                        # JSON-encrypted field (result_data): dict → JSON string → encrypted string → store in Text column
                        logger.debug(f"   Field {field} is JSON-encrypted (Text column with encrypted JSON)")
                        if isinstance(encrypted_data[field], dict):
                            original_json = encrypted_data[field]
                            logger.info(f"   📋 Encrypting {field}: JSON dict with {len(original_json)} keys")
                            
                            # Encrypt dict → returns encrypted string
                            encrypted_str = encryptor.encrypt_json_field(original_json)
                            
                            if encrypted_str:
                                encrypted_data[field] = encrypted_str
                                logger.info(f"✅ Encrypted JSON field: {field} ({len(str(original_json))} chars → {len(encrypted_str)} chars)")
                            else:
                                logger.error(f"❌ Encryption returned None for JSON field {field}!")
                                raise ValueError(f"Encryption failed for {field} - returned None")
                        else:
                            logger.warning(f"⚠️ JSON field {field} is not a dict, skipping encryption")
                            # Keep as-is if not a dict
                    else:
                        # Text field: use text encryption
                        original_length = len(str(encrypted_data[field])) if encrypted_data[field] else 0
                        encrypted_data[field] = encryptor.encrypt_field(
                            str(encrypted_data[field])
                        )
                        encrypted_length = len(str(encrypted_data[field])) if encrypted_data[field] else 0
                        logger.info(f"✅ Encrypted text field: {field} (original: {original_length} chars → encrypted: {encrypted_length} chars)")
                except Exception as e:
                    logger.error(f"Failed to encrypt field {field}: {e}")
                    raise

        return encrypted_data

    def _decrypt_entity(self, entity: ModelType | None) -> ModelType | None:
        """
        Decrypt encrypted fields in an entity.

        Handles both text fields (str) and binary fields (bytes) automatically.

        Args:
            entity: Database entity instance

        Returns:
            Entity with decrypted fields (modifies in-place)
        """
        if not entity or not self.encrypted_fields or not encryptor.is_enabled():
            return entity

        for field in self.encrypted_fields:
            if hasattr(entity, field):
                encrypted_value = getattr(entity, field)
                if encrypted_value is not None:
                    try:
                        if self._is_binary_field(field):
                            # Binary field: use binary decryption
                            # First check if it's encrypted or plaintext binary
                            if isinstance(encrypted_value, bytes):
                                # Try to decode as UTF-8 to check if it's encrypted
                                try:
                                    encrypted_value_str = encrypted_value.decode("utf-8")
                                    logger.debug(f"   Decoded {field} as UTF-8: {len(encrypted_value_str)} chars, starts with: {encrypted_value_str[:20]}")
                                    
                                    # Check if it looks like an encrypted Fernet token
                                    # For binary fields encrypted with encrypt_binary_field():
                                    # - The encrypted string is base64-encoded Fernet token
                                    # - It should start with "gAAAAA" (Fernet token base64-encoded)
                                    # - OR "Z0FBQUFB" if there's another layer of base64 encoding
                                    is_enc = False
                                    
                                    # Quick heuristic check first (most common case)
                                    if encrypted_value_str.startswith("gAAAAA"):
                                        is_enc = True
                                        logger.debug(f"   Heuristic check: Looks encrypted (starts with gAAAAA)")
                                    elif encrypted_value_str.startswith("Z0FBQUFB"):
                                        is_enc = True
                                        logger.debug(f"   Heuristic check: Looks encrypted (starts with Z0FBQUFB - double base64)")
                                    else:
                                        # Try the is_encrypted() method (more thorough check)
                                        is_enc = encryptor.is_encrypted(encrypted_value_str)
                                        logger.debug(f"   is_encrypted() returned: {is_enc}")
                                    
                                    if is_enc:
                                        # It's encrypted - decrypt it
                                        logger.info(f"🔓 Decrypting binary field: {field} ({len(encrypted_value)} bytes → will decrypt)")
                                        try:
                                            decrypted_value = encryptor.decrypt_binary_field(encrypted_value_str)
                                            setattr(entity, field, decrypted_value)
                                            logger.info(f"✅ Decrypted binary field: {field} ({len(encrypted_value)} bytes → {len(decrypted_value)} bytes)")
                                            
                                            # Verify it's actually decrypted (should be PDF binary)
                                            if isinstance(decrypted_value, bytes) and decrypted_value[:4] == b'%PDF':
                                                logger.info(f"   ✅ Verified: Decrypted data is PDF (starts with %PDF)")
                                            else:
                                                logger.warning(f"   ⚠️ Decrypted data doesn't look like PDF: {decrypted_value[:20] if isinstance(decrypted_value, bytes) else str(decrypted_value)[:20]}")
                                        except Exception as e:
                                            logger.error(f"   ❌ Failed to decrypt {field}: {e}")
                                            raise
                                    else:
                                        # Not encrypted - return as-is (plaintext binary)
                                        logger.debug(f"Binary field {field} is not encrypted, returning as-is")
                                        # Already set correctly, no need to change
                                except UnicodeDecodeError:
                                    # Can't decode as UTF-8 - it's plaintext binary, not encrypted
                                    logger.debug(f"Binary field {field} is plaintext binary (not encrypted), returning as-is")
                                    # Already set correctly, no need to change
                            else:
                                # It's already a string - try to decrypt
                                if encryptor.is_encrypted(str(encrypted_value)):
                                    decrypted_value = encryptor.decrypt_binary_field(str(encrypted_value))
                                    setattr(entity, field, decrypted_value)
                                    logger.debug(f"Decrypted binary field: {field}")
                                else:
                                    # Not encrypted - convert to bytes if needed
                                    logger.debug(f"Binary field {field} is not encrypted")
                                    # Already set correctly, no need to change
                        elif isinstance(encrypted_value, str) and self._is_json_encrypted_field(field):
                            # JSON-encrypted field (result_data): encrypted string that decrypts to JSON
                            # These are stored in Text columns, not JSON columns
                            logger.debug(f"   Field {field} is JSON-encrypted (Text column with encrypted JSON)")
                            
                            # Heuristic check: Fernet tokens start with 'g' or 'Z0FBQUFB' (base64 'gAAAAA')
                            looks_encrypted = (
                                encrypted_value.startswith('gAAAAA') or  # Direct Fernet token
                                encrypted_value.startswith('Z0FBQUFB') or  # Base64-encoded Fernet token
                                encryptor.is_encrypted(encrypted_value)  # Full validation
                            )
                            
                            if looks_encrypted:
                                logger.info(f"🔓 Decrypting JSON-encrypted field: {field} ({len(encrypted_value)} chars)")
                                try:
                                    decrypted_dict = encryptor.decrypt_json_field(encrypted_value)
                                    setattr(entity, field, decrypted_dict)
                                    logger.info(f"✅ Decrypted JSON field: {field} (dict with {len(decrypted_dict) if decrypted_dict else 0} keys)")
                                except Exception as e:
                                    logger.error(f"Failed to decrypt JSON field {field}: {e}")
                                    # Keep as-is if decryption fails
                            else:
                                # Not encrypted - parse JSON directly
                                logger.debug(f"JSON field {field} is not encrypted, parsing as plaintext JSON")
                                import json
                                try:
                                    decrypted_dict = json.loads(encrypted_value)
                                    setattr(entity, field, decrypted_dict)
                                except json.JSONDecodeError:
                                    logger.warning(f"Failed to parse plaintext JSON for {field}, keeping as-is")
                        else:
                            # Text field: use text decryption
                            # Check if it's encrypted first
                            if encryptor.is_encrypted(str(encrypted_value)):
                                decrypted_value = encryptor.decrypt_field(encrypted_value)
                                setattr(entity, field, decrypted_value)
                                logger.debug(f"Decrypted text field: {field}")
                            else:
                                # Not encrypted - return as-is
                                logger.debug(f"Text field {field} is not encrypted, returning as-is")
                                # Already set correctly, no need to change
                    except Exception as e:
                        logger.error(f"Failed to decrypt field {field}: {e}")
                        # Don't raise - return value as-is (might be plaintext)
                        logger.warning(f"Returning value as-is for {field} (may be plaintext or encrypted)")

        return entity

    def _decrypt_entities(self, entities: list[ModelType]) -> list[ModelType]:
        """
        Decrypt encrypted fields in a list of entities.

        Args:
            entities: List of database entity instances

        Returns:
            List of entities with decrypted fields
        """
        if not entities or not self.encrypted_fields or not encryptor.is_enabled():
            return entities

        for entity in entities:
            self._decrypt_entity(entity)

        return entities

    # Override BaseRepository methods to add encryption/decryption

    def create(self, **kwargs) -> ModelType:
        """
        Create new entity with automatic field encryption.

        Also generates searchable hashes for encrypted fields if the model has
        corresponding *_searchable columns (e.g., email -> email_searchable).

        Args:
            **kwargs: Field values for new entity

        Returns:
            Created entity with decrypted fields
        """
        # Generate searchable hashes for encrypted fields BEFORE encryption
        for field in self.encrypted_fields:
            if field in kwargs and kwargs[field] is not None:
                searchable_field = f"{field}_searchable"
                # Check if model has searchable column
                if hasattr(self.model, searchable_field):
                    # Generate hash from plaintext value
                    kwargs[searchable_field] = encryptor.generate_searchable_hash(kwargs[field])

        # Encrypt fields before creation
        encrypted_kwargs = self._encrypt_fields(kwargs)
        
        # Log what we're about to save
        for field in self.encrypted_fields:
            if field in encrypted_kwargs and encrypted_kwargs[field] is not None:
                if isinstance(encrypted_kwargs[field], bytes):
                    logger.info(f"🔐 About to save encrypted {field}: {len(encrypted_kwargs[field])} bytes")
                    # Check if it looks encrypted
                    try:
                        preview = encrypted_kwargs[field][:50].decode("utf-8")
                        if preview.startswith("gAAAAA"):
                            logger.info(f"   ✅ Verified: Encrypted token format before save")
                        else:
                            logger.warning(f"   ⚠️ Doesn't look encrypted before save: {preview[:20]}...")
                    except UnicodeDecodeError:
                        logger.warning(f"   ⚠️ Cannot decode as UTF-8 before save (might be plaintext binary)")

        # Log what we're passing to super().create()
        logger.info(f"🔐 Calling super().create() with encrypted_kwargs containing:")
        for field in self.encrypted_fields:
            if field in encrypted_kwargs and encrypted_kwargs[field] is not None:
                if isinstance(encrypted_kwargs[field], bytes):
                    logger.info(f"   {field}: {len(encrypted_kwargs[field])} bytes")
                    try:
                        preview = encrypted_kwargs[field][:50].decode("utf-8")
                        logger.info(f"      Preview: {preview[:30]}...")
                    except UnicodeDecodeError:
                        logger.warning(f"      Cannot decode as UTF-8 (might be plaintext binary)")
        
        # Call parent create method
        entity = super().create(**encrypted_kwargs)
        
        # CRITICAL: Flush and commit to ensure data is persisted before any other operations
        self.db.flush()
        self.db.commit()
        
        # Verify what was actually saved to database using raw SQL to bypass ORM
        from sqlalchemy import text
        verify_result = self.db.execute(
            text(f"SELECT LENGTH({self.encrypted_fields[0]}) as len FROM {self.model.__tablename__} WHERE id = :id"),
            {"id": entity.id}
        )
        db_row = verify_result.fetchone()
        if db_row:
            db_length = db_row[0]
            logger.info(f"🔍 Raw SQL verification: {self.encrypted_fields[0]} in DB = {db_length} bytes")
            
            # Check if it matches what we tried to save
            encrypted_value = encrypted_kwargs.get(self.encrypted_fields[0])
            if encrypted_value is None:
                expected_length = 0
            elif isinstance(encrypted_value, bytes):
                expected_length = len(encrypted_value)
            elif isinstance(encrypted_value, str):
                # For text fields, encrypted value is a string, check its length
                expected_length = len(encrypted_value.encode("utf-8"))  # Convert to bytes for comparison
            else:
                expected_length = 0
                
            if db_length == expected_length and expected_length > 0:
                logger.info(f"   ✅ Verified: Database has correct encrypted size ({db_length} bytes)")
            elif expected_length == 0 and db_length == 0:
                logger.info(f"   ✅ Verified: Both expected and database are NULL/empty")
            else:
                logger.warning(f"   ⚠️ Size mismatch: Expected {expected_length} bytes, but database has {db_length} bytes (this may be normal for text fields stored as TEXT vs BYTEA)")
        
        # Also refresh entity to see what ORM thinks is in the database
        self.db.refresh(entity)  # Force reload from database
        for field in self.encrypted_fields:
            if hasattr(entity, field):
                saved_value = getattr(entity, field)
                if saved_value is not None:
                    if isinstance(saved_value, bytes):
                        logger.info(f"🔍 After save, {field} in DB: {len(saved_value)} bytes")
                        try:
                            preview = saved_value[:50].decode("utf-8")
                            if preview.startswith("gAAAAA"):
                                logger.info(f"   ✅ Verified: Encrypted token format in database")
                            else:
                                logger.warning(f"   ⚠️ Doesn't look encrypted in database: {preview[:20]}...")
                        except UnicodeDecodeError:
                            logger.warning(f"   ⚠️ Cannot decode as UTF-8 in database (might be plaintext binary)")

        # Decrypt fields for return (so service layer gets plaintext)
        decrypted_entity = self._decrypt_entity(entity)
        
        # CRITICAL: Expunge the entity after decrypting to prevent SQLAlchemy from
        # tracking the decrypted values and accidentally saving them back to the database.
        # The entity is now detached and won't be auto-saved on session flush/close.
        self.db.expunge(decrypted_entity)
        logger.debug(f"Expunged {self.model.__name__} entity (id={decrypted_entity.id}) after decryption in create()")
        
        return decrypted_entity

    def get_by_id(self, record_id: Any) -> ModelType | None:
        """
        Get entity by primary key with automatic decryption.

        Args:
            record_id: Primary key value

        Returns:
            Entity with decrypted fields or None (detached from session)
        """
        entity = super().get_by_id(record_id)
        decrypted_entity = self._decrypt_entity(entity)
        
        # Expunge to prevent accidental overwrites of decrypted data
        if decrypted_entity:
            self.db.expunge(decrypted_entity)
            logger.debug(f"Expunged {self.model.__name__} entity (id={decrypted_entity.id}) after decryption in get_by_id()")
        
        return decrypted_entity

    def get_all(
        self, skip: int = 0, limit: int = 100, filters: dict[str, Any] | None = None
    ) -> list[ModelType]:
        """
        Get all entities with automatic decryption.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of field:value filters

        Returns:
            List of entities with decrypted fields (detached from session)
        """
        entities = super().get_all(skip, limit, filters)
        decrypted_entities = self._decrypt_entities(entities)
        
        # Expunge all to prevent accidental overwrites of decrypted data
        for entity in decrypted_entities:
            self.db.expunge(entity)
        logger.debug(f"Expunged {len(decrypted_entities)} {self.model.__name__} entities after decryption in get_all()")
        
        return decrypted_entities

    def get_one(self, filters: dict[str, Any]) -> ModelType | None:
        """
        Get single entity with automatic decryption.

        Args:
            filters: Dictionary of field:value filters

        Returns:
            Entity with decrypted fields or None (detached from session)
        """
        entity = super().get_one(filters)
        decrypted_entity = self._decrypt_entity(entity)
        
        # Expunge to prevent accidental overwrites of decrypted data
        if decrypted_entity:
            self.db.expunge(decrypted_entity)
            logger.debug(f"Expunged {self.model.__name__} entity after decryption in get_one()")
        
        return decrypted_entity

    def update(self, record_id: Any, **kwargs) -> ModelType | None:
        """
        Update entity with automatic field encryption.

        Also updates searchable hashes for any encrypted fields being modified.

        IMPORTANT: Only fields in kwargs are updated. Encrypted fields not in kwargs
        are preserved (not overwritten with decrypted values from memory).

        Args:
            record_id: Primary key value
            **kwargs: Fields to update

        Returns:
            Updated entity with decrypted fields or None
        """
        # Generate searchable hashes for encrypted fields being updated
        for field in self.encrypted_fields:
            if field in kwargs and kwargs[field] is not None:
                searchable_field = f"{field}_searchable"
                # Check if model has searchable column
                if hasattr(self.model, searchable_field):
                    # Generate hash from new plaintext value
                    kwargs[searchable_field] = encryptor.generate_searchable_hash(kwargs[field])

        # Encrypt fields before update
        encrypted_kwargs = self._encrypt_fields(kwargs)

        # Use SQLAlchemy's update() statement to update only specified columns
        # This prevents overwriting encrypted fields that are not in kwargs
        from sqlalchemy import update
        from sqlalchemy.inspection import inspect
        
        # Get primary key column name
        mapper = inspect(self.model)
        pk_column = mapper.primary_key[0]
        pk_attr = pk_column.name
        
        # Build update statement - only update fields in encrypted_kwargs
        update_stmt = (
            update(self.model)
            .where(getattr(self.model, pk_attr) == record_id)
            .values(**encrypted_kwargs)
        )
        
        # CRITICAL: Before executing the update, expire any existing entity with this ID
        # from the session to prevent SQLAlchemy from tracking the decrypted file_content
        # and accidentally saving it back when we commit
        existing_entity = self.db.query(self.model).filter(getattr(self.model, pk_attr) == record_id).first()
        if existing_entity:
            # Expunge the entity to remove it from session entirely
            # This prevents SQLAlchemy from tracking any changes to decrypted fields
            self.db.expunge(existing_entity)
            logger.debug(f"Expunged existing {self.model.__name__} entity (id={record_id}) from session before update")

        result = self.db.execute(update_stmt)
        self.db.commit()
        
        if result.rowcount == 0:
            logger.warning(f"{self.model.__name__} with {pk_attr}={record_id} not found")
            return None

        logger.info(f"Updated {self.model.__name__} with {pk_attr}={record_id} (affected rows: {result.rowcount})")

        # CRITICAL: Expire all objects in the session to prevent SQLAlchemy from
        # tracking decrypted entities and accidentally saving them back to the database
        # This ensures that any entity loaded after this update will be fresh from the database
        self.db.expire_all()

        # CRITICAL: Do NOT reload the entity after update!
        # Reloading would decrypt it and add it to the session, risking accidental overwrites.
        # The worker doesn't need the return value, and services can query again if needed.
        logger.debug(f"Update complete for {self.model.__name__} (id={record_id}). Not reloading entity to prevent session tracking.")
        
        return None  # Return None instead of reloaded entity
