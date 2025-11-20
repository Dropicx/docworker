"""
Tests for SystemSettingsRepository

Tests all specialized system settings operations including typed getters/setters,
bulk operations, import/export, and search functionality.
"""

import pytest
from sqlalchemy.orm import Session

from app.database.unified_models import SystemSettingsDB
from app.repositories.system_settings_repository import SystemSettingsRepository


class TestSystemSettingsRepository:
    """Test suite for SystemSettingsRepository specialized methods."""

    @pytest.fixture
    def repository(self, db_session):
        """Create SystemSettingsRepository instance."""
        return SystemSettingsRepository(db_session)

    # ==================== GET BY KEY TESTS ====================

    def test_get_by_key_existing(self, repository, create_system_setting):
        """Test retrieving setting by key."""
        create_system_setting(key="test.setting", value="test_value", value_type="string")

        setting = repository.get_by_key("test.setting")

        assert setting is not None
        assert setting.key == "test.setting"
        assert setting.value == "test_value"

    def test_get_by_key_nonexistent(self, repository):
        """Test get_by_key returns None for non-existent key."""
        result = repository.get_by_key("nonexistent.key")
        assert result is None

    def test_get_by_key_case_sensitive(self, repository, create_system_setting):
        """Test that key matching is case-sensitive."""
        create_system_setting(key="Test.Setting", value="value", value_type="string")

        assert repository.get_by_key("Test.Setting") is not None
        assert repository.get_by_key("test.setting") is None

    # ==================== GET VALUE TESTS ====================

    def test_get_value_existing(self, repository, create_system_setting):
        """Test getting value from existing setting."""
        create_system_setting(key="test.key", value="test_value", value_type="string")

        value = repository.get_value("test.key")
        assert value == "test_value"

    def test_get_value_nonexistent_returns_none(self, repository):
        """Test get_value returns None for non-existent key."""
        value = repository.get_value("nonexistent.key")
        assert value is None

    def test_get_value_with_default(self, repository):
        """Test get_value returns default when key doesn't exist."""
        value = repository.get_value("nonexistent.key", default="default_value")
        assert value == "default_value"

    def test_get_value_ignores_default_when_key_exists(self, repository, create_system_setting):
        """Test that default is ignored when key exists."""
        create_system_setting(key="existing.key", value="actual_value", value_type="string")

        value = repository.get_value("existing.key", default="default_value")
        assert value == "actual_value"

    # ==================== GET BOOL VALUE TESTS ====================

    def test_get_bool_value_true_variants(self, repository, create_system_setting):
        """Test that various true values are recognized."""
        true_values = ["true", "True", "TRUE", "1", "yes", "Yes", "on", "ON"]

        for idx, val in enumerate(true_values):
            create_system_setting(key=f"bool.{idx}", value=val, value_type="string")
            assert repository.get_bool_value(f"bool.{idx}") is True

    def test_get_bool_value_false_variants(self, repository, create_system_setting):
        """Test that non-true values are recognized as false."""
        false_values = ["false", "False", "0", "no", "off", "anything_else"]

        for idx, val in enumerate(false_values):
            create_system_setting(key=f"bool.{idx}", value=val, value_type="string")
            assert repository.get_bool_value(f"bool.{idx}") is False

    def test_get_bool_value_nonexistent_returns_default(self, repository):
        """Test get_bool_value returns default for non-existent key."""
        assert repository.get_bool_value("nonexistent.key", default=False) is False
        assert repository.get_bool_value("nonexistent.key", default=True) is True

    def test_get_bool_value_default_false_when_not_specified(self, repository):
        """Test that default is False when not specified."""
        value = repository.get_bool_value("nonexistent.key")
        assert value is False

    # ==================== GET INT VALUE TESTS ====================

    def test_get_int_value_valid_integer(self, repository, create_system_setting):
        """Test getting valid integer values."""
        create_system_setting(key="int.positive", value="42", value_type="string")
        create_system_setting(key="int.negative", value="-10", value_type="string")
        create_system_setting(key="int.zero", value="0", value_type="string")

        assert repository.get_int_value("int.positive") == 42
        assert repository.get_int_value("int.negative") == -10
        assert repository.get_int_value("int.zero") == 0

    def test_get_int_value_invalid_returns_default(self, repository, create_system_setting):
        """Test that invalid integers return default."""
        create_system_setting(key="int.invalid", value="not_a_number", value_type="string")

        value = repository.get_int_value("int.invalid", default=99)
        assert value == 99

    def test_get_int_value_float_string_returns_default(self, repository, create_system_setting):
        """Test that float strings can't be converted to int."""
        create_system_setting(key="int.float", value="3.14", value_type="string")

        value = repository.get_int_value("int.float", default=0)
        assert value == 0

    def test_get_int_value_nonexistent_returns_default(self, repository):
        """Test get_int_value returns default for non-existent key."""
        value = repository.get_int_value("nonexistent.key", default=100)
        assert value == 100

    def test_get_int_value_default_zero_when_not_specified(self, repository):
        """Test that default is 0 when not specified."""
        value = repository.get_int_value("nonexistent.key")
        assert value == 0

    # ==================== GET FLOAT VALUE TESTS ====================

    def test_get_float_value_valid_float(self, repository, create_system_setting):
        """Test getting valid float values."""
        create_system_setting(key="float.pi", value="3.14159", value_type="string")
        create_system_setting(key="float.negative", value="-2.5", value_type="string")
        create_system_setting(key="float.zero", value="0.0", value_type="string")

        assert repository.get_float_value("float.pi") == 3.14159
        assert repository.get_float_value("float.negative") == -2.5
        assert repository.get_float_value("float.zero") == 0.0

    def test_get_float_value_integer_string_converts(self, repository, create_system_setting):
        """Test that integer strings can be converted to float."""
        create_system_setting(key="float.int", value="42", value_type="string")

        value = repository.get_float_value("float.int")
        assert value == 42.0
        assert isinstance(value, float)

    def test_get_float_value_invalid_returns_default(self, repository, create_system_setting):
        """Test that invalid floats return default."""
        create_system_setting(key="float.invalid", value="not_a_number", value_type="string")

        value = repository.get_float_value("float.invalid", default=99.9)
        assert value == 99.9

    def test_get_float_value_nonexistent_returns_default(self, repository):
        """Test get_float_value returns default for non-existent key."""
        value = repository.get_float_value("nonexistent.key", default=1.5)
        assert value == 1.5

    def test_get_float_value_default_zero_when_not_specified(self, repository):
        """Test that default is 0.0 when not specified."""
        value = repository.get_float_value("nonexistent.key")
        assert value == 0.0

    # ==================== SET VALUE TESTS ====================

    def test_set_value_creates_new_setting(self, repository):
        """Test that set_value creates a new setting if it doesn't exist."""
        setting = repository.set_value("new.key", "new_value", "Description")

        assert setting is not None
        assert setting.key == "new.key"
        assert setting.value == "new_value"
        assert setting.description == "Description"

    def test_set_value_updates_existing_setting(self, repository, create_system_setting):
        """Test that set_value updates an existing setting."""
        original = create_system_setting(
            key="existing.key",
            value="old_value",
            value_type="string",
            description="Old description",
        )

        updated = repository.set_value("existing.key", "new_value", "New description")

        assert updated.id == original.id
        assert updated.value == "new_value"
        assert updated.description == "New description"

    def test_set_value_without_description(self, repository):
        """Test set_value without description parameter."""
        setting = repository.set_value("key.no.desc", "value")

        assert setting.key == "key.no.desc"
        assert setting.value == "value"
        assert setting.description == ""

    def test_set_value_update_preserves_description_if_not_provided(
        self, repository, create_system_setting
    ):
        """Test that updating without description preserves original description."""
        original = create_system_setting(
            key="preserve.desc",
            value="old_value",
            value_type="string",
            description="Original description",
        )

        updated = repository.set_value("preserve.desc", "new_value")

        assert updated.description == "Original description"

    # ==================== SET BOOL VALUE TESTS ====================

    def test_set_bool_value_true(self, repository):
        """Test setting boolean true value."""
        setting = repository.set_bool_value("bool.true", True, "Boolean setting")

        assert setting.value == "true"
        assert repository.get_bool_value("bool.true") is True

    def test_set_bool_value_false(self, repository):
        """Test setting boolean false value."""
        setting = repository.set_bool_value("bool.false", False, "Boolean setting")

        assert setting.value == "false"
        assert repository.get_bool_value("bool.false") is False

    def test_set_bool_value_updates_existing(self, repository, create_system_setting):
        """Test updating an existing boolean setting."""
        create_system_setting(key="bool.toggle", value="false", value_type="string")

        repository.set_bool_value("bool.toggle", True)

        assert repository.get_bool_value("bool.toggle") is True

    # ==================== SET INT VALUE TESTS ====================

    def test_set_int_value_positive(self, repository):
        """Test setting positive integer value."""
        setting = repository.set_int_value("int.positive", 42, "Integer setting")

        assert setting.value == "42"
        assert repository.get_int_value("int.positive") == 42

    def test_set_int_value_negative(self, repository):
        """Test setting negative integer value."""
        setting = repository.set_int_value("int.negative", -10)

        assert setting.value == "-10"
        assert repository.get_int_value("int.negative") == -10

    def test_set_int_value_zero(self, repository):
        """Test setting zero integer value."""
        setting = repository.set_int_value("int.zero", 0)

        assert setting.value == "0"
        assert repository.get_int_value("int.zero") == 0

    # ==================== SET FLOAT VALUE TESTS ====================

    def test_set_float_value_decimal(self, repository):
        """Test setting decimal float value."""
        setting = repository.set_float_value("float.pi", 3.14159, "Pi value")

        assert setting.value == "3.14159"
        assert repository.get_float_value("float.pi") == 3.14159

    def test_set_float_value_negative(self, repository):
        """Test setting negative float value."""
        setting = repository.set_float_value("float.negative", -2.5)

        assert setting.value == "-2.5"
        assert repository.get_float_value("float.negative") == -2.5

    # ==================== KEY EXISTS TESTS ====================

    def test_key_exists_true(self, repository, create_system_setting):
        """Test key_exists returns True for existing key."""
        create_system_setting(key="existing.key", value="value", value_type="string")

        assert repository.key_exists("existing.key") is True

    def test_key_exists_false(self, repository):
        """Test key_exists returns False for non-existent key."""
        assert repository.key_exists("nonexistent.key") is False

    def test_key_exists_case_sensitive(self, repository, create_system_setting):
        """Test that key_exists is case-sensitive."""
        create_system_setting(key="CaseSensitive", value="value", value_type="string")

        assert repository.key_exists("CaseSensitive") is True
        assert repository.key_exists("casesensitive") is False

    # ==================== GET ALL SETTINGS TESTS ====================

    def test_get_all_settings_returns_dict(self, repository, create_system_setting):
        """Test get_all_settings returns key-value dictionary."""
        create_system_setting(key="key1", value="value1", value_type="string")
        create_system_setting(key="key2", value="value2", value_type="string")
        create_system_setting(key="key3", value="value3", value_type="string")

        settings = repository.get_all_settings()

        assert isinstance(settings, dict)
        assert len(settings) == 3
        assert settings["key1"] == "value1"
        assert settings["key2"] == "value2"
        assert settings["key3"] == "value3"

    def test_get_all_settings_empty_database(self, repository):
        """Test get_all_settings returns empty dict when no settings."""
        settings = repository.get_all_settings()

        assert isinstance(settings, dict)
        assert len(settings) == 0

    # ==================== GET SETTINGS BY PREFIX TESTS ====================

    def test_get_settings_by_prefix(self, repository, create_system_setting):
        """Test filtering settings by key prefix."""
        create_system_setting(key="enable_feature_a", value="true", value_type="string")
        create_system_setting(key="enable_feature_b", value="false", value_type="string")
        create_system_setting(key="disable_feature_c", value="true", value_type="string")
        create_system_setting(key="other_setting", value="value", value_type="string")

        enable_settings = repository.get_settings_by_prefix("enable_")

        assert len(enable_settings) == 2
        assert all(s.key.startswith("enable_") for s in enable_settings)

    def test_get_settings_by_prefix_no_matches(self, repository, create_system_setting):
        """Test get_settings_by_prefix returns empty list when no matches."""
        create_system_setting(key="some.key", value="value", value_type="string")

        results = repository.get_settings_by_prefix("nonexistent_")

        assert len(results) == 0

    def test_get_settings_by_prefix_empty_prefix(self, repository, create_system_setting):
        """Test that empty prefix returns all settings."""
        create_system_setting(key="key1", value="v1", value_type="string")
        create_system_setting(key="key2", value="v2", value_type="string")

        results = repository.get_settings_by_prefix("")

        assert len(results) == 2

    # ==================== GET FEATURE FLAGS TESTS ====================

    def test_get_feature_flags(self, repository, create_system_setting):
        """Test getting all feature flags."""
        create_system_setting(key="enable_feature_a", value="true", value_type="string")
        create_system_setting(key="enable_feature_b", value="false", value_type="string")
        create_system_setting(key="enable_feature_c", value="1", value_type="string")
        create_system_setting(key="other_setting", value="true", value_type="string")

        flags = repository.get_feature_flags()

        assert isinstance(flags, dict)
        assert len(flags) == 3
        assert flags["enable_feature_a"] is True
        assert flags["enable_feature_b"] is False
        assert flags["enable_feature_c"] is True
        assert "other_setting" not in flags

    def test_get_feature_flags_empty(self, repository):
        """Test get_feature_flags returns empty dict when no flags."""
        flags = repository.get_feature_flags()

        assert isinstance(flags, dict)
        assert len(flags) == 0

    # ==================== DELETE BY KEY TESTS ====================

    def test_delete_by_key_existing(self, repository, create_system_setting):
        """Test deleting existing setting by key."""
        create_system_setting(key="to.delete", value="value", value_type="string")

        result = repository.delete_by_key("to.delete")

        assert result is True
        assert repository.get_by_key("to.delete") is None

    def test_delete_by_key_nonexistent(self, repository):
        """Test deleting non-existent key returns False."""
        result = repository.delete_by_key("nonexistent.key")
        assert result is False

    def test_delete_by_key_is_permanent(self, repository, create_system_setting):
        """Test that deletion by key is permanent."""
        create_system_setting(key="permanent.delete", value="value", value_type="string")

        repository.delete_by_key("permanent.delete")

        assert repository.get_by_key("permanent.delete") is None
        assert repository.key_exists("permanent.delete") is False

    # ==================== BULK UPDATE TESTS ====================

    def test_bulk_update_creates_new_settings(self, repository):
        """Test bulk_update creates new settings."""
        settings = {"key1": "value1", "key2": "value2", "key3": "value3"}

        count = repository.bulk_update(settings)

        assert count == 3
        assert repository.get_value("key1") == "value1"
        assert repository.get_value("key2") == "value2"
        assert repository.get_value("key3") == "value3"

    def test_bulk_update_updates_existing_settings(self, repository, create_system_setting):
        """Test bulk_update updates existing settings."""
        create_system_setting(key="existing1", value="old1", value_type="string")
        create_system_setting(key="existing2", value="old2", value_type="string")

        settings = {"existing1": "new1", "existing2": "new2"}

        count = repository.bulk_update(settings)

        assert count == 2
        assert repository.get_value("existing1") == "new1"
        assert repository.get_value("existing2") == "new2"

    def test_bulk_update_mixed_create_and_update(self, repository, create_system_setting):
        """Test bulk_update with mix of new and existing keys."""
        create_system_setting(key="existing", value="old", value_type="string")

        settings = {"existing": "updated", "new_key": "new_value"}

        count = repository.bulk_update(settings)

        assert count == 2
        assert repository.get_value("existing") == "updated"
        assert repository.get_value("new_key") == "new_value"

    def test_bulk_update_empty_dict(self, repository):
        """Test bulk_update with empty dictionary."""
        count = repository.bulk_update({})
        assert count == 0

    # ==================== EXPORT SETTINGS TESTS ====================

    def test_get_settings_for_export(self, repository, create_system_setting):
        """Test exporting settings with metadata."""
        create_system_setting(
            key="export.test", value="test_value", value_type="string", description="Test setting"
        )

        export = repository.get_settings_for_export()

        assert isinstance(export, dict)
        assert "export.test" in export
        assert export["export.test"]["value"] == "test_value"
        assert export["export.test"]["description"] == "Test setting"
        assert "created_at" in export["export.test"]
        assert "last_modified" in export["export.test"]

    def test_get_settings_for_export_multiple_settings(self, repository, create_system_setting):
        """Test exporting multiple settings."""
        create_system_setting(key="key1", value="value1", value_type="string", description="Desc 1")
        create_system_setting(key="key2", value="value2", value_type="string", description="Desc 2")

        export = repository.get_settings_for_export()

        assert len(export) == 2
        assert "key1" in export
        assert "key2" in export

    def test_get_settings_for_export_empty_database(self, repository):
        """Test exporting from empty database."""
        export = repository.get_settings_for_export()

        assert isinstance(export, dict)
        assert len(export) == 0

    # ==================== IMPORT SETTINGS TESTS ====================

    def test_import_settings_new_keys(self, repository):
        """Test importing new settings."""
        settings = {"import.key1": "value1", "import.key2": "value2"}

        stats = repository.import_settings(settings)

        assert stats["imported"] == 2
        assert stats["skipped"] == 0
        assert stats["updated"] == 0
        assert repository.get_value("import.key1") == "value1"
        assert repository.get_value("import.key2") == "value2"

    def test_import_settings_skip_existing_by_default(self, repository, create_system_setting):
        """Test that existing settings are skipped by default."""
        create_system_setting(key="existing.key", value="original", value_type="string")

        settings = {"existing.key": "new_value", "new.key": "value"}

        stats = repository.import_settings(settings, overwrite=False)

        assert stats["imported"] == 1
        assert stats["skipped"] == 1
        assert stats["updated"] == 0
        assert repository.get_value("existing.key") == "original"  # Not updated
        assert repository.get_value("new.key") == "value"  # Created

    def test_import_settings_overwrite_existing(self, repository, create_system_setting):
        """Test importing with overwrite=True updates existing settings."""
        create_system_setting(key="existing.key", value="original", value_type="string")

        settings = {"existing.key": "new_value", "new.key": "value"}

        stats = repository.import_settings(settings, overwrite=True)

        assert stats["imported"] == 1
        assert stats["skipped"] == 0
        assert stats["updated"] == 1
        assert repository.get_value("existing.key") == "new_value"  # Updated
        assert repository.get_value("new.key") == "value"  # Created

    def test_import_settings_empty_dict(self, repository):
        """Test importing empty dictionary."""
        stats = repository.import_settings({})

        assert stats["imported"] == 0
        assert stats["skipped"] == 0
        assert stats["updated"] == 0

    # ==================== SEARCH SETTINGS TESTS ====================

    def test_search_settings_by_key(self, repository, create_system_setting):
        """Test searching settings by key."""
        create_system_setting(
            key="enable_feature_a", value="v1", value_type="string", description="Feature A"
        )
        create_system_setting(
            key="enable_feature_b", value="v2", value_type="string", description="Feature B"
        )
        create_system_setting(
            key="other_setting", value="v3", value_type="string", description="Other"
        )

        results = repository.search_settings("enable")

        assert len(results) == 2
        assert all("enable" in r.key for r in results)

    def test_search_settings_by_description(self, repository, create_system_setting):
        """Test searching settings by description."""
        create_system_setting(
            key="key1", value="v1", value_type="string", description="Database configuration"
        )
        create_system_setting(
            key="key2", value="v2", value_type="string", description="Database timeout"
        )
        create_system_setting(
            key="key3", value="v3", value_type="string", description="API settings"
        )

        results = repository.search_settings("database")

        assert len(results) == 2
        assert all("database" in r.description.lower() for r in results)

    def test_search_settings_case_insensitive(self, repository, create_system_setting):
        """Test that search is case-insensitive."""
        create_system_setting(
            key="EnableFeature", value="v", value_type="string", description="Test"
        )

        results_lower = repository.search_settings("enable")
        results_upper = repository.search_settings("ENABLE")
        results_mixed = repository.search_settings("EnAbLe")

        assert len(results_lower) == 1
        assert len(results_upper) == 1
        assert len(results_mixed) == 1

    def test_search_settings_no_matches(self, repository, create_system_setting):
        """Test search returns empty list when no matches."""
        create_system_setting(
            key="some.key", value="value", value_type="string", description="Description"
        )

        results = repository.search_settings("nonexistent")

        assert len(results) == 0

    def test_search_settings_matches_key_or_description(self, repository, create_system_setting):
        """Test search matches either key or description."""
        create_system_setting(
            key="search_in_key", value="v1", value_type="string", description="Other text"
        )
        create_system_setting(
            key="other_key", value="v2", value_type="string", description="search in description"
        )

        results = repository.search_settings("search")

        assert len(results) == 2

    # ==================== STATISTICS TESTS ====================

    def test_get_settings_statistics_comprehensive(self, repository, create_system_setting):
        """Test getting comprehensive statistics."""
        # Feature flags
        create_system_setting(key="enable_feature_a", value="true", value_type="string")
        create_system_setting(key="enable_feature_b", value="false", value_type="string")

        # Boolean settings
        create_system_setting(key="bool_setting", value="yes", value_type="string")

        # Numeric settings
        create_system_setting(key="numeric_setting", value="42", value_type="string")

        # Regular settings
        create_system_setting(key="regular_setting", value="some_text", value_type="string")

        stats = repository.get_settings_statistics()

        assert stats["total_settings"] == 5
        assert stats["feature_flags"] == 2
        assert stats["enabled_features"] == 1
        assert stats["boolean_settings"] >= 2  # enable_feature_a, enable_feature_b, bool_setting
        assert stats["numeric_settings"] == 1

    def test_get_settings_statistics_empty_database(self, repository):
        """Test statistics on empty database."""
        stats = repository.get_settings_statistics()

        assert stats["total_settings"] == 0
        assert stats["feature_flags"] == 0
        assert stats["enabled_features"] == 0
        assert stats["boolean_settings"] == 0
        assert stats["numeric_settings"] == 0

    def test_get_settings_statistics_counts_enabled_features_correctly(
        self, repository, create_system_setting
    ):
        """Test that enabled features are counted correctly."""
        create_system_setting(key="enable_feature_1", value="true", value_type="string")
        create_system_setting(key="enable_feature_2", value="1", value_type="string")
        create_system_setting(key="enable_feature_3", value="false", value_type="string")
        create_system_setting(key="enable_feature_4", value="0", value_type="string")

        stats = repository.get_settings_statistics()

        assert stats["feature_flags"] == 4
        assert stats["enabled_features"] == 2  # true and 1

    # ==================== INTEGRATION TESTS ====================

    def test_round_trip_string_value(self, repository):
        """Test setting and getting string value."""
        repository.set_value("test.string", "test_value")
        value = repository.get_value("test.string")

        assert value == "test_value"

    def test_round_trip_bool_value(self, repository):
        """Test setting and getting boolean value."""
        repository.set_bool_value("test.bool", True)
        value = repository.get_bool_value("test.bool")

        assert value is True

    def test_round_trip_int_value(self, repository):
        """Test setting and getting integer value."""
        repository.set_int_value("test.int", 42)
        value = repository.get_int_value("test.int")

        assert value == 42

    def test_round_trip_float_value(self, repository):
        """Test setting and getting float value."""
        repository.set_float_value("test.float", 3.14)
        value = repository.get_float_value("test.float")

        assert value == 3.14

    def test_multiple_operations_maintain_consistency(self, repository):
        """Test that multiple operations maintain data consistency."""
        # Create
        repository.set_value("test.key", "value1")
        assert repository.get_value("test.key") == "value1"

        # Update
        repository.set_value("test.key", "value2")
        assert repository.get_value("test.key") == "value2"

        # Check existence
        assert repository.key_exists("test.key") is True

        # Delete
        repository.delete_by_key("test.key")
        assert repository.key_exists("test.key") is False
        assert repository.get_value("test.key") is None

    def test_export_and_import_round_trip(self, repository, create_system_setting):
        """Test exporting and re-importing settings."""
        # Create original settings
        create_system_setting(key="key1", value="value1", value_type="string", description="Desc 1")
        create_system_setting(key="key2", value="value2", value_type="string", description="Desc 2")

        # Export
        exported = repository.get_all_settings()

        # Clear database (using delete_by_key)
        repository.delete_by_key("key1")
        repository.delete_by_key("key2")

        # Re-import
        stats = repository.import_settings(exported)

        assert stats["imported"] == 2
        assert repository.get_value("key1") == "value1"
        assert repository.get_value("key2") == "value2"

    # ==================== ERROR HANDLING TESTS ====================

    def test_set_value_handles_none_description_gracefully(self, repository):
        """Test that None description is handled correctly."""
        setting = repository.set_value("test.key", "value", description=None)

        assert setting.description == ""

    def test_bulk_update_handles_various_value_types(self, repository):
        """Test bulk_update with various string values."""
        settings = {
            "string_key": "string_value",
            "number_key": "123",
            "bool_key": "true",
            "empty_key": "",
        }

        count = repository.bulk_update(settings)

        assert count == 4
        assert repository.get_value("string_key") == "string_value"
        assert repository.get_value("number_key") == "123"
        assert repository.get_value("bool_key") == "true"
        assert repository.get_value("empty_key") == ""
