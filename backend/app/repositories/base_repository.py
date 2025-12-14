"""
Base Repository Pattern

Provides generic CRUD operations for database entities.
All specific repositories should inherit from BaseRepository.

Includes EncryptedRepositoryMixin for transparent field-level encryption.
"""

import logging
from typing import Any, Generic, TypeVar

from sqlalchemy import LargeBinary
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
            logger.debug("No encrypted fields defined for this repository")
            return data
        
        if not encryptor.is_enabled():
            logger.warning("Encryption is disabled - fields will be stored in plaintext!")
            return data

        encrypted_data = data.copy()

        for field in self.encrypted_fields:
            if field in encrypted_data and encrypted_data[field] is not None:
                try:
                    if self._is_binary_field(field):
                        # Binary field: use binary encryption
                        if isinstance(encrypted_data[field], bytes):
                            # Encrypt binary → returns base64-encoded string
                            encrypted_str = encryptor.encrypt_binary_field(
                                encrypted_data[field]
                            )
                            # Convert encrypted string to bytes for LargeBinary column
                            encrypted_data[field] = encrypted_str.encode("utf-8") if encrypted_str else None
                            logger.info(f"✅ Encrypted binary field: {field} (original: {len(encrypted_data[field]) if isinstance(data[field], bytes) else 0} bytes → encrypted: {len(encrypted_data[field]) if encrypted_data[field] else 0} bytes)")
                        else:
                            # If it's already a string (from database), treat as text
                            encrypted_data[field] = encryptor.encrypt_field(
                                str(encrypted_data[field])
                            )
                            logger.debug(f"Encrypted field (as text): {field}")
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
                                    # Check if it looks like an encrypted Fernet token
                                    if encryptor.is_encrypted(encrypted_value_str):
                                        # It's encrypted - decrypt it
                                        decrypted_value = encryptor.decrypt_binary_field(encrypted_value_str)
                                        setattr(entity, field, decrypted_value)
                                        logger.debug(f"Decrypted binary field: {field}")
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

        # Call parent create method
        entity = super().create(**encrypted_kwargs)

        # Decrypt fields for return (so service layer gets plaintext)
        return self._decrypt_entity(entity)

    def get_by_id(self, record_id: Any) -> ModelType | None:
        """
        Get entity by primary key with automatic decryption.

        Args:
            record_id: Primary key value

        Returns:
            Entity with decrypted fields or None
        """
        entity = super().get_by_id(record_id)
        return self._decrypt_entity(entity)

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
            List of entities with decrypted fields
        """
        entities = super().get_all(skip, limit, filters)
        return self._decrypt_entities(entities)

    def get_one(self, filters: dict[str, Any]) -> ModelType | None:
        """
        Get single entity with automatic decryption.

        Args:
            filters: Dictionary of field:value filters

        Returns:
            Entity with decrypted fields or None
        """
        entity = super().get_one(filters)
        return self._decrypt_entity(entity)

    def update(self, record_id: Any, **kwargs) -> ModelType | None:
        """
        Update entity with automatic field encryption.

        Also updates searchable hashes for any encrypted fields being modified.

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

        # Call parent update method
        entity = super().update(record_id, **encrypted_kwargs)

        # Decrypt fields for return
        return self._decrypt_entity(entity)
