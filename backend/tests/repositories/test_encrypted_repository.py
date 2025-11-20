"""
Integration tests for encrypted repository pattern.

Tests transparent field-level encryption in repositories with actual database operations.
Verifies that:
- Data is encrypted when written to database
- Data is decrypted when read from database
- Service layer code receives plaintext values
- Database stores ciphertext values
"""

import base64

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.encryption import encryptor
from app.database.auth_models import UserDB, UserRole, UserStatus, Base as AuthBase
from app.database.unified_models import SystemSettingsDB, Base as UnifiedBase
from app.repositories.system_settings_repository import SystemSettingsRepository
from app.repositories.user_repository import UserRepository


# Test database fixtures
@pytest.fixture(scope="function")
def test_engine():
    """Create in-memory SQLite engine for testing"""
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Create all tables
    AuthBase.metadata.create_all(engine)
    UnifiedBase.metadata.create_all(engine)

    yield engine

    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_engine):
    """Create a new database session for each test"""
    TestSessionLocal = sessionmaker(bind=test_engine)
    session = TestSessionLocal()

    try:
        yield session
    finally:
        session.close()


class TestSystemSettingsRepositoryEncryption:
    """Test SystemSettingsRepository encryption functionality"""

    def test_create_encrypted_setting(self, test_db_session: Session):
        """Test creating a setting with encryption enabled"""
        repo = SystemSettingsRepository(test_db_session)

        # Create encrypted setting
        setting = repo.set_value(
            key="api_secret",
            value="my_secret_api_key_12345",
            description="API secret key",
            is_encrypted=True,
        )

        # Service layer receives plaintext
        assert setting.value == "my_secret_api_key_12345"
        assert setting.is_encrypted is True

        # Verify database stores encrypted value
        raw_result = test_db_session.execute(
            text("SELECT value FROM system_settings WHERE key = :key"), {"key": "api_secret"}
        ).fetchone()

        stored_value = raw_result[0]

        # Database should have ciphertext
        assert stored_value != "my_secret_api_key_12345"
        assert len(stored_value) > len("my_secret_api_key_12345")
        # Stored value should be base64-encoded (our outer encoding)
        try:
            base64.b64decode(stored_value.encode("ascii"))
            is_valid_base64 = True
        except Exception:
            is_valid_base64 = False
        assert is_valid_base64

    def test_retrieve_encrypted_setting(self, test_db_session: Session):
        """Test retrieving an encrypted setting returns plaintext"""
        repo = SystemSettingsRepository(test_db_session)

        # Create encrypted setting
        repo.set_value("db_password", "super_secure_password", is_encrypted=True)

        # Retrieve setting
        retrieved = repo.get_by_key("db_password")

        # Should receive decrypted value
        assert retrieved.value == "super_secure_password"
        assert retrieved.is_encrypted is True

    def test_create_plaintext_setting(self, test_db_session: Session):
        """Test creating a setting without encryption"""
        repo = SystemSettingsRepository(test_db_session)

        # Create plaintext setting
        setting = repo.set_value(
            key="feature_flag", value="enabled", description="Feature flag", is_encrypted=False
        )

        # Service layer receives plaintext
        assert setting.value == "enabled"
        assert setting.is_encrypted is False

        # Verify database stores plaintext
        raw_result = test_db_session.execute(
            text("SELECT value FROM system_settings WHERE key = 'feature_flag'")
        ).fetchone()

        assert raw_result[0] == "enabled"

    def test_update_encrypted_setting(self, test_db_session: Session):
        """Test updating an encrypted setting"""
        repo = SystemSettingsRepository(test_db_session)

        # Create encrypted setting
        repo.set_value("token", "old_token_value", is_encrypted=True)

        # Update with new value
        updated = repo.set_value("token", "new_token_value", is_encrypted=True)

        # Should receive new decrypted value
        assert updated.value == "new_token_value"

        # Retrieve to verify persistence
        retrieved = repo.get_by_key("token")
        assert retrieved.value == "new_token_value"

    def test_mixed_encrypted_and_plaintext_settings(self, test_db_session: Session):
        """Test repository handles both encrypted and plaintext settings"""
        repo = SystemSettingsRepository(test_db_session)

        # Create mixed settings
        repo.set_value("public_key", "public_value", is_encrypted=False)
        repo.set_value("private_key", "private_value", is_encrypted=True)
        repo.set_value("feature_enabled", "true", is_encrypted=False)

        # Retrieve all
        public = repo.get_by_key("public_key")
        private = repo.get_by_key("private_key")
        feature = repo.get_by_key("feature_enabled")

        # All should return correct plaintext values
        assert public.value == "public_value"
        assert private.value == "private_value"
        assert feature.value == "true"

        # Verify encryption flags
        assert public.is_encrypted is False
        assert private.is_encrypted is True
        assert feature.is_encrypted is False

    def test_get_value_helper_with_encrypted_setting(self, test_db_session: Session):
        """Test get_value helper method with encrypted setting"""
        repo = SystemSettingsRepository(test_db_session)

        # Create encrypted setting
        repo.set_value("encrypted_value", "secret_content", is_encrypted=True)

        # Use helper method
        value = repo.get_value("encrypted_value")

        # Should return decrypted value
        assert value == "secret_content"

    def test_encryption_with_special_characters(self, test_db_session: Session):
        """Test encryption with special characters and Unicode"""
        repo = SystemSettingsRepository(test_db_session)

        special_value = "Müller's Secret: !@#$%^&*()_+{}|:<>? 中文"

        # Create encrypted setting with special chars
        setting = repo.set_value("special", special_value, is_encrypted=True)

        # Should handle special characters correctly
        assert setting.value == special_value

        # Retrieve and verify
        retrieved = repo.get_by_key("special")
        assert retrieved.value == special_value


class TestUserRepositoryEncryption:
    """Test UserRepository encryption functionality"""

    def test_create_user_with_encrypted_fields(self, test_db_session: Session):
        """Test creating a user encrypts email and full_name"""
        repo = UserRepository(test_db_session)

        # Create user (service layer code)
        user = repo.create_user(
            email="patient@hospital.de",
            full_name="Max Müller",
            password_hash="hashed_password_123",
            role=UserRole.USER,
        )

        # Service layer receives plaintext
        assert user.email == "patient@hospital.de"
        assert user.full_name == "Max Müller"

        # Verify database stores encrypted values
        # Close current session and create a new one to get raw database values
        test_db_session.close()
        from sqlalchemy.orm import sessionmaker

        TestSessionLocal = sessionmaker(bind=test_db_session.bind)
        fresh_session = TestSessionLocal()

        try:
            # Query raw database values without going through repository decryption
            db_user_raw = fresh_session.query(UserDB).filter(UserDB.id == user.id).first()
            stored_email = db_user_raw.email
            stored_full_name = db_user_raw.full_name

            # Database should have ciphertext (different from plaintext)
            assert (
                stored_email != "patient@hospital.de"
            ), f"Email not encrypted! Got: {stored_email}"
            assert (
                stored_full_name != "Max Müller"
            ), f"Full name not encrypted! Got: {stored_full_name}"
            # Values should be base64-encoded
            try:
                base64.b64decode(stored_email.encode("ascii"))
                base64.b64decode(stored_full_name.encode("ascii"))
                is_valid_base64 = True
            except Exception:
                is_valid_base64 = False
            assert (
                is_valid_base64
            ), f"Values not base64 encoded: email={stored_email}, name={stored_full_name}"
        finally:
            fresh_session.close()

    def test_retrieve_user_decrypts_fields(self, test_db_session: Session):
        """Test retrieving a user decrypts encrypted fields"""
        repo = UserRepository(test_db_session)

        # Create user
        created_user = repo.create_user(
            email="doctor@clinic.com",
            full_name="Dr. Schmidt",
            password_hash="hashed_password",
            role=UserRole.ADMIN,
        )

        # Retrieve user by ID
        retrieved_user = repo.get_by_id(created_user.id)

        # Should receive decrypted values
        assert retrieved_user.email == "doctor@clinic.com"
        assert retrieved_user.full_name == "Dr. Schmidt"
        assert retrieved_user.role == UserRole.ADMIN

    def test_update_user_encrypted_fields(self, test_db_session: Session):
        """Test updating user encrypted fields"""
        repo = UserRepository(test_db_session)

        # Create user
        user = repo.create_user(
            email="old@email.com", full_name="Old Name", password_hash="hash", role=UserRole.USER
        )

        # Update encrypted fields
        updated = repo.update(user.id, email="new@email.com", full_name="New Name")

        # Should receive new decrypted values
        assert updated.email == "new@email.com"
        assert updated.full_name == "New Name"

        # Verify database updated with new encrypted values
        # Use fresh session to get raw database values
        test_db_session.close()
        from sqlalchemy.orm import sessionmaker

        TestSessionLocal = sessionmaker(bind=test_db_session.bind)
        fresh_session = TestSessionLocal()

        try:
            # Query raw database values
            db_user_raw = fresh_session.query(UserDB).filter(UserDB.id == user.id).first()
            stored_email = db_user_raw.email
            stored_full_name = db_user_raw.full_name

            # Values should be encrypted (different from plaintext)
            assert stored_email != "new@email.com", f"Email not encrypted! Got: {stored_email}"
            assert (
                stored_full_name != "New Name"
            ), f"Full name not encrypted! Got: {stored_full_name}"
        finally:
            fresh_session.close()

    def test_get_all_users_decrypts_batch(self, test_db_session: Session):
        """Test retrieving all users decrypts all encrypted fields"""
        repo = UserRepository(test_db_session)

        # Create multiple users
        users_data = [
            ("user1@example.com", "User One"),
            ("user2@example.com", "User Two"),
            ("user3@example.com", "User Three"),
        ]

        for email, full_name in users_data:
            repo.create_user(
                email=email, full_name=full_name, password_hash="hash", role=UserRole.USER
            )

        # Retrieve all users
        all_users = repo.get_all()

        # All should have decrypted values
        assert len(all_users) == 3

        for user in all_users:
            assert "@example.com" in user.email
            assert user.email in [e for e, _ in users_data]
            assert user.full_name in [n for _, n in users_data]

    def test_password_hash_not_encrypted(self, test_db_session: Session):
        """Test that password_hash is NOT encrypted (already hashed)"""
        repo = UserRepository(test_db_session)

        password_hash = "bcrypt_hashed_password_value"

        # Create user
        user = repo.create_user(
            email="test@test.com",
            full_name="Test User",
            password_hash=password_hash,
            role=UserRole.USER,
        )

        # password_hash should not be encrypted (not in encrypted_fields)
        assert user.password_hash == password_hash

        # Verify database stores the hash as-is (not encrypted) - use ORM query
        test_db_session.expire_all()  # Force reload from DB
        stored_password_hash = (
            test_db_session.query(UserDB.password_hash).filter(UserDB.id == user.id).scalar()
        )

        assert stored_password_hash == password_hash

    def test_encryption_with_german_characters(self, test_db_session: Session):
        """Test encryption handles German umlauts correctly"""
        repo = UserRepository(test_db_session)

        # Create user with German name
        user = repo.create_user(
            email="müller@klinik.de",
            full_name="Dr. Müller-Schäfer",
            password_hash="hash",
            role=UserRole.USER,
        )

        # Should handle umlauts correctly
        assert user.email == "müller@klinik.de"
        assert user.full_name == "Dr. Müller-Schäfer"

        # Retrieve and verify
        retrieved = repo.get_by_id(user.id)
        assert retrieved.email == "müller@klinik.de"
        assert retrieved.full_name == "Dr. Müller-Schäfer"


class TestEncryptedRepositoryMixinBehavior:
    """Test EncryptedRepositoryMixin edge cases and behavior"""

    def test_mixin_handles_non_encrypted_fields(self, test_db_session: Session):
        """Test that mixin doesn't interfere with non-encrypted fields"""
        repo = UserRepository(test_db_session)

        # Create user - password_hash should not be encrypted
        user = repo.create(
            email="test@test.com",
            full_name="Test User",
            password_hash="bcrypt_hash_12345",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
            is_active=True,
            is_verified=True,
        )

        # password_hash should remain as-is (not encrypted)
        assert user.password_hash == "bcrypt_hash_12345"

        # Verify database stores password_hash as plaintext - use ORM query
        test_db_session.expire_all()  # Force reload from DB
        stored_password_hash = (
            test_db_session.query(UserDB.password_hash).filter(UserDB.id == user.id).scalar()
        )

        assert stored_password_hash == "bcrypt_hash_12345"

    def test_empty_string_handling(self, test_db_session: Session):
        """Test that encrypting empty strings returns None (can't encrypt nothing)"""
        from app.core.encryption import encryptor

        # Empty strings can't be encrypted - returns None
        result = encryptor.encrypt_field("")
        assert result is None

        # Whitespace-only strings also return None
        result = encryptor.encrypt_field("   ")
        assert result is None

        # None values return None
        result = encryptor.encrypt_field(None)
        assert result is None

    def test_get_one_with_filters_decrypts(self, test_db_session: Session):
        """Test get_one method decrypts fields"""
        repo = UserRepository(test_db_session)

        # Create user
        created = repo.create_user(
            email="filter@test.com",
            full_name="Filter Test",
            password_hash="hash",
            role=UserRole.USER,
        )

        # Use get_one with filters
        found = repo.get_one({"role": UserRole.USER})

        # Should return decrypted values
        assert found is not None
        assert found.email == "filter@test.com"
        assert found.full_name == "Filter Test"


class TestEncryptionPerformance:
    """Performance tests for encrypted operations"""

    def test_batch_create_performance(self, test_db_session: Session):
        """Test performance of batch user creation"""
        repo = UserRepository(test_db_session)

        import time

        # Create 50 users
        start = time.time()
        for i in range(50):
            repo.create_user(
                email=f"user{i}@test.com",
                full_name=f"User {i}",
                password_hash="hash",
                role=UserRole.USER,
            )
        elapsed = time.time() - start

        # Should complete in reasonable time (<5s for 50 users)
        assert elapsed < 5.0, f"Batch creation took {elapsed:.2f}s (target: <5s)"

    def test_batch_retrieve_performance(self, test_db_session: Session):
        """Test performance of batch retrieval with decryption"""
        repo = UserRepository(test_db_session)

        # Create 50 users
        for i in range(50):
            repo.create_user(
                email=f"user{i}@test.com",
                full_name=f"User {i}",
                password_hash="hash",
                role=UserRole.USER,
            )

        import time

        # Retrieve all users
        start = time.time()
        all_users = repo.get_all(limit=100)
        elapsed = time.time() - start

        # Should retrieve and decrypt quickly (<1s)
        assert elapsed < 1.0, f"Batch retrieval took {elapsed:.2f}s (target: <1s)"
        assert len(all_users) == 50


class TestEncryptionDisabledMode:
    """Test behavior when encryption is disabled"""

    def test_encryption_disabled_stores_plaintext(self, test_db_session: Session, monkeypatch):
        """Test that disabling encryption stores plaintext"""
        # Disable encryption
        monkeypatch.setenv("ENCRYPTION_ENABLED", "false")

        # Force reload of encryptor to pick up new env var
        from importlib import reload
        from app.core import encryption

        reload(encryption)

        repo = UserRepository(test_db_session)

        # Create user
        user = repo.create_user(
            email="plaintext@test.com",
            full_name="Plaintext User",
            password_hash="hash",
            role=UserRole.USER,
        )

        # Verify database stores plaintext - use ORM query
        test_db_session.expire_all()  # Force reload from DB
        stored_email = test_db_session.query(UserDB.email).filter(UserDB.id == user.id).scalar()
        stored_full_name = (
            test_db_session.query(UserDB.full_name).filter(UserDB.id == user.id).scalar()
        )

        # Should be plaintext (encryption disabled)
        assert stored_email == "plaintext@test.com"
        assert stored_full_name == "Plaintext User"
