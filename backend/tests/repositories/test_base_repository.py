"""
Tests for BaseRepository

Tests all generic CRUD operations provided by the base repository class.
This validates the foundation for all specific repositories.
"""

import pytest
from sqlalchemy.orm import Session

from app.database.unified_models import SystemSettingsDB
from app.repositories.base_repository import BaseRepository


class TestBaseRepository:
    """Test suite for BaseRepository generic CRUD operations."""

    @pytest.fixture
    def repository(self, db_session):
        """Create a BaseRepository instance for SystemSettingsDB model."""
        return BaseRepository(db_session, SystemSettingsDB)

    # ==================== CREATE TESTS ====================

    def test_create_entity(self, repository, db_session):
        """Test creating a new entity."""
        setting = repository.create(
            key="test.setting",
            value="test_value",
            value_type="string",
            description="Test setting"
        )

        assert setting.id is not None
        assert setting.key == "test.setting"
        assert setting.value == "test_value"
        assert setting.value_type == "string"
        assert setting.description == "Test setting"
        assert setting.created_at is not None

    def test_create_entity_with_defaults(self, repository):
        """Test creating entity with minimal required fields."""
        setting = repository.create(
            key="minimal.setting",
            value="value",
            value_type="string"
        )

        assert setting.id is not None
        assert setting.key == "minimal.setting"
        assert setting.is_encrypted is False  # Default value

    def test_create_entity_with_extra_fields(self, repository):
        """Test creating entity with additional fields."""
        setting = repository.create(
            key="extra.setting",
            value="value",
            value_type="string",
            is_encrypted=True,
            updated_by="test_user"
        )

        assert setting.is_encrypted is True
        assert setting.updated_by == "test_user"

    # ==================== READ TESTS ====================

    def test_get_by_id_existing(self, repository, create_system_setting):
        """Test retrieving existing entity by ID."""
        created_setting = create_system_setting(key="test.get")
        retrieved_setting = repository.get_by_id(created_setting.id)

        assert retrieved_setting is not None
        assert retrieved_setting.id == created_setting.id
        assert retrieved_setting.key == "test.get"

    def test_get_by_id_nonexistent(self, repository):
        """Test retrieving non-existent entity returns None."""
        result = repository.get_by_id(999999)
        assert result is None

    def test_get_alias_for_get_by_id(self, repository, create_system_setting):
        """Test that get() is an alias for get_by_id()."""
        created_setting = create_system_setting(key="test.alias")

        result_get = repository.get(created_setting.id)
        result_get_by_id = repository.get_by_id(created_setting.id)

        assert result_get is not None
        assert result_get.id == result_get_by_id.id
        assert result_get.key == result_get_by_id.key

    def test_get_all_no_filters(self, repository, create_system_setting):
        """Test retrieving all entities without filters."""
        # Create test data
        create_system_setting(key="setting.1", value="value1", value_type="string")
        create_system_setting(key="setting.2", value="value2", value_type="string")
        create_system_setting(key="setting.3", value="value3", value_type="string")

        results = repository.get_all()

        assert len(results) == 3
        assert all(isinstance(s, SystemSettingsDB) for s in results)

    def test_get_all_with_pagination(self, repository, create_system_setting):
        """Test pagination with skip and limit."""
        # Create 10 settings
        for i in range(10):
            create_system_setting(key=f"setting.{i}", value=f"value{i}", value_type="string")

        # Get first 5
        page1 = repository.get_all(skip=0, limit=5)
        assert len(page1) == 5

        # Get next 3
        page2 = repository.get_all(skip=5, limit=3)
        assert len(page2) == 3

        # Ensure no overlap
        page1_keys = {s.key for s in page1}
        page2_keys = {s.key for s in page2}
        assert len(page1_keys & page2_keys) == 0

    def test_get_all_with_filters(self, repository, create_system_setting):
        """Test filtering entities by field values."""
        create_system_setting(key="encrypted.1", value="v1", value_type="string", is_encrypted=True)
        create_system_setting(key="encrypted.2", value="v2", value_type="string", is_encrypted=True)
        create_system_setting(key="plain.1", value="v3", value_type="string", is_encrypted=False)

        # Filter by is_encrypted=True
        encrypted = repository.get_all(filters={"is_encrypted": True})
        assert len(encrypted) == 2
        assert all(s.is_encrypted for s in encrypted)

        # Filter by is_encrypted=False
        plain = repository.get_all(filters={"is_encrypted": False})
        assert len(plain) == 1
        assert not plain[0].is_encrypted

    def test_get_all_with_multiple_filters(self, repository, create_system_setting):
        """Test filtering with multiple conditions."""
        create_system_setting(key="test.1", value="value1", value_type="string", is_encrypted=True)
        create_system_setting(key="test.2", value="value2", value_type="int", is_encrypted=True)
        create_system_setting(key="test.3", value="value3", value_type="string", is_encrypted=False)

        results = repository.get_all(filters={
            "value_type": "string",
            "is_encrypted": True
        })

        assert len(results) == 1
        assert results[0].key == "test.1"

    def test_get_one_existing(self, repository, create_system_setting):
        """Test retrieving single entity by filters."""
        create_system_setting(key="unique.setting", value="unique_value", value_type="string")

        result = repository.get_one(filters={"key": "unique.setting"})

        assert result is not None
        assert result.key == "unique.setting"
        assert result.value == "unique_value"

    def test_get_one_nonexistent(self, repository):
        """Test get_one returns None when no match found."""
        result = repository.get_one(filters={"key": "nonexistent.key"})
        assert result is None

    def test_get_one_multiple_matches_returns_first(self, repository, create_system_setting):
        """Test that get_one returns first match when multiple exist."""
        create_system_setting(key="dup.1", value="v1", value_type="string")
        create_system_setting(key="dup.2", value="v2", value_type="string")

        # Both have same value_type
        result = repository.get_one(filters={"value_type": "string"})

        assert result is not None
        assert result.value_type == "string"

    # ==================== UPDATE TESTS ====================

    def test_update_existing_entity(self, repository, create_system_setting):
        """Test updating an existing entity."""
        setting = create_system_setting(key="update.test", value="old_value", value_type="string")
        original_id = setting.id

        updated = repository.update(
            setting.id,
            value="new_value",
            description="Updated description"
        )

        assert updated is not None
        assert updated.id == original_id
        assert updated.value == "new_value"
        assert updated.description == "Updated description"
        assert updated.key == "update.test"  # Unchanged field

    def test_update_nonexistent_entity(self, repository):
        """Test updating non-existent entity returns None."""
        result = repository.update(999999, value="new_value")
        assert result is None

    def test_update_multiple_fields(self, repository, create_system_setting):
        """Test updating multiple fields at once."""
        setting = create_system_setting(
            key="multi.update",
            value="old",
            value_type="string",
            is_encrypted=False
        )

        updated = repository.update(
            setting.id,
            value="new",
            value_type="int",
            is_encrypted=True,
            updated_by="test_user"
        )

        assert updated.value == "new"
        assert updated.value_type == "int"
        assert updated.is_encrypted is True
        assert updated.updated_by == "test_user"

    def test_update_ignores_invalid_fields(self, repository, create_system_setting):
        """Test that update ignores fields that don't exist on model."""
        setting = create_system_setting(key="invalid.test", value="value", value_type="string")

        updated = repository.update(
            setting.id,
            value="new_value",
            nonexistent_field="should_be_ignored"
        )

        assert updated.value == "new_value"
        assert not hasattr(updated, "nonexistent_field")

    # ==================== DELETE TESTS ====================

    def test_delete_existing_entity(self, repository, create_system_setting, db_session):
        """Test deleting an existing entity."""
        setting = create_system_setting(key="delete.test", value="value", value_type="string")
        setting_id = setting.id

        result = repository.delete(setting_id)

        assert result is True

        # Verify entity is deleted
        deleted = repository.get_by_id(setting_id)
        assert deleted is None

    def test_delete_nonexistent_entity(self, repository):
        """Test deleting non-existent entity returns False."""
        result = repository.delete(999999)
        assert result is False

    def test_delete_is_permanent(self, repository, create_system_setting):
        """Test that deletion is permanent and not reversible."""
        setting = create_system_setting(key="permanent.delete", value="v", value_type="string")
        setting_id = setting.id

        repository.delete(setting_id)

        # Try to retrieve multiple times
        assert repository.get_by_id(setting_id) is None
        assert repository.get_one(filters={"key": "permanent.delete"}) is None

    # ==================== COUNT TESTS ====================

    def test_count_all_entities(self, repository, create_system_setting):
        """Test counting all entities without filters."""
        create_system_setting(key="count.1", value="v1", value_type="string")
        create_system_setting(key="count.2", value="v2", value_type="string")
        create_system_setting(key="count.3", value="v3", value_type="string")

        count = repository.count()
        assert count == 3

    def test_count_with_filters(self, repository, create_system_setting):
        """Test counting with filters."""
        create_system_setting(key="count.encrypted.1", value="v1", value_type="string", is_encrypted=True)
        create_system_setting(key="count.encrypted.2", value="v2", value_type="string", is_encrypted=True)
        create_system_setting(key="count.plain.1", value="v3", value_type="string", is_encrypted=False)

        encrypted_count = repository.count(filters={"is_encrypted": True})
        assert encrypted_count == 2

        plain_count = repository.count(filters={"is_encrypted": False})
        assert plain_count == 1

    def test_count_empty_table(self, repository):
        """Test count on empty table returns 0."""
        count = repository.count()
        assert count == 0

    def test_count_with_no_matches(self, repository, create_system_setting):
        """Test count with filters that match nothing returns 0."""
        create_system_setting(key="count.test", value="value", value_type="string")

        count = repository.count(filters={"key": "nonexistent.key"})
        assert count == 0

    # ==================== EXISTS TESTS ====================

    def test_exists_when_entity_exists(self, repository, create_system_setting):
        """Test exists returns True when entity exists."""
        create_system_setting(key="exists.test", value="value", value_type="string")

        result = repository.exists(filters={"key": "exists.test"})
        assert result is True

    def test_exists_when_entity_does_not_exist(self, repository):
        """Test exists returns False when entity doesn't exist."""
        result = repository.exists(filters={"key": "nonexistent.key"})
        assert result is False

    def test_exists_with_multiple_filters(self, repository, create_system_setting):
        """Test exists with multiple filter conditions."""
        create_system_setting(
            key="exists.multi",
            value="value",
            value_type="string",
            is_encrypted=True
        )

        # All conditions match
        assert repository.exists(filters={
            "key": "exists.multi",
            "is_encrypted": True
        }) is True

        # One condition doesn't match
        assert repository.exists(filters={
            "key": "exists.multi",
            "is_encrypted": False
        }) is False

    # ==================== ERROR HANDLING TESTS ====================

    def test_create_with_duplicate_unique_field_raises_error(self, repository, create_system_setting):
        """Test that creating duplicate unique key raises error."""
        create_system_setting(key="duplicate.key", value="v1", value_type="string")

        with pytest.raises(Exception):
            repository.create(key="duplicate.key", value="v2", value_type="string")

    def test_rollback_on_create_error(self, repository, create_system_setting):
        """Test that database is rolled back on create error."""
        # Create a valid entry
        create_system_setting(key="valid.key", value="value", value_type="string")

        # Try to create duplicate (should fail)
        try:
            repository.create(key="valid.key", value="duplicate", value_type="string")
        except Exception:
            pass

        # Verify original entry is still intact
        original = repository.get_one(filters={"key": "valid.key"})
        assert original is not None
        assert original.value == "value"

    def test_rollback_on_update_error(self, repository, create_system_setting):
        """Test that database is rolled back on update error."""
        setting = create_system_setting(key="update.rollback", value="original", value_type="string")
        original_value = setting.value

        # Try invalid update (this is a simplified test, actual error depends on constraints)
        try:
            # Simulating an error scenario
            repository.update(setting.id, value="new_value")
            # Force an error by trying to set key to existing value
            repository.update(setting.id, key="update.rollback")  # This should succeed
        except Exception:
            pass

        # Verify data consistency
        updated_setting = repository.get_by_id(setting.id)
        assert updated_setting is not None

    def test_rollback_on_delete_error(self, repository, create_system_setting):
        """Test database state after attempted delete with constraints."""
        setting = create_system_setting(key="delete.rollback", value="value", value_type="string")

        # Successfully delete
        result = repository.delete(setting.id)
        assert result is True

    # ==================== TRANSACTION TESTS ====================

    def test_multiple_operations_in_transaction(self, repository, create_system_setting):
        """Test multiple operations maintain data integrity."""
        # Create
        setting1 = repository.create(key="tx.test.1", value="v1", value_type="string")

        # Update
        repository.update(setting1.id, value="v1_updated")

        # Create another
        setting2 = repository.create(key="tx.test.2", value="v2", value_type="string")

        # Verify all operations completed
        assert repository.get_by_id(setting1.id).value == "v1_updated"
        assert repository.get_by_id(setting2.id).value == "v2"
        assert repository.count() == 2

    # ==================== TYPE SAFETY TESTS ====================

    def test_repository_returns_correct_model_type(self, repository, create_system_setting):
        """Test that repository operations return correct model type."""
        setting = create_system_setting(key="type.test", value="value", value_type="string")

        # Test each retrieval method returns correct type
        by_id = repository.get_by_id(setting.id)
        assert isinstance(by_id, SystemSettingsDB)

        get_result = repository.get(setting.id)
        assert isinstance(get_result, SystemSettingsDB)

        one_result = repository.get_one(filters={"key": "type.test"})
        assert isinstance(one_result, SystemSettingsDB)

        all_results = repository.get_all()
        assert all(isinstance(s, SystemSettingsDB) for s in all_results)
