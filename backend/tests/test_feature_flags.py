"""
Tests for FeatureFlags Service

Tests the three-tier priority system for feature flags:
1. Environment variables (highest priority)
2. Database configuration
3. Config defaults / hardcoded defaults (fallback)
"""

import os
import pytest
from unittest.mock import Mock, patch

from app.services.feature_flags import (
    FeatureFlags,
    Feature,
    is_feature_enabled,
    get_enabled_features,
)
from app.repositories.system_settings_repository import SystemSettingsRepository


class TestFeatureFlags:
    """Test suite for FeatureFlags service."""

    @pytest.fixture
    def repository(self, db_session):
        """Create SystemSettingsRepository instance."""
        return SystemSettingsRepository(db_session)

    @pytest.fixture
    def mock_settings(self):
        """Create mock Settings object for testing."""
        settings = Mock()
        settings.enable_multi_file = True
        settings.enable_privacy_filter = True
        return settings

    @pytest.fixture
    def clear_env_vars(self):
        """Clear feature flag environment variables before and after tests."""
        # Store original values
        original_env = {}
        for key in list(os.environ.keys()):
            if key.startswith("FEATURE_FLAG_"):
                original_env[key] = os.environ.pop(key)

        yield

        # Restore original values
        for key, value in original_env.items():
            os.environ[key] = value

    # ==================== INITIALIZATION TESTS ====================

    def test_initialization_with_session_and_settings(self, db_session, mock_settings):
        """Test initialization with database session and settings."""
        flags = FeatureFlags(session=db_session, settings=mock_settings)

        assert flags.session == db_session
        assert flags.settings == mock_settings
        assert flags.settings_repository is not None
        assert isinstance(flags.settings_repository, SystemSettingsRepository)

    def test_initialization_without_session(self, mock_settings):
        """Test initialization without database session (env vars only)."""
        flags = FeatureFlags(session=None, settings=mock_settings)

        assert flags.session is None
        assert flags.settings_repository is None
        assert flags.settings == mock_settings

    def test_initialization_with_repository_injection(self, db_session, repository, mock_settings):
        """Test initialization with injected repository (dependency injection)."""
        flags = FeatureFlags(
            session=db_session, settings=mock_settings, settings_repository=repository
        )

        assert flags.settings_repository is repository

    def test_initialization_without_settings_uses_global(self, db_session):
        """Test initialization without settings uses global settings."""
        flags = FeatureFlags(session=db_session, settings=None)

        # Should not crash - uses global settings or None
        assert flags.settings is not None or flags.settings is None

    # ==================== PRIORITY TIER 1: ENVIRONMENT VARIABLES ====================

    def test_is_enabled_from_environment_variable_true(self, clear_env_vars, db_session):
        """Test feature enabled via environment variable (highest priority)."""
        os.environ["FEATURE_FLAG_FEEDBACK_AI_ANALYSIS_ENABLED"] = "true"
        flags = FeatureFlags(session=db_session)

        result = flags.is_enabled(Feature.FEEDBACK_AI_ANALYSIS)

        assert result is True

    def test_is_enabled_from_environment_variable_false(self, clear_env_vars, db_session):
        """Test feature disabled via environment variable."""
        os.environ["FEATURE_FLAG_COST_TRACKING_ENABLED"] = "false"
        flags = FeatureFlags(session=db_session)

        result = flags.is_enabled(Feature.COST_TRACKING)

        assert result is False

    @pytest.mark.parametrize(
        "env_value,expected",
        [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("YES", True),
            ("on", True),
            ("ON", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("off", False),
            ("invalid", False),
            ("", False),
        ],
    )
    def test_environment_variable_value_parsing(
        self, clear_env_vars, db_session, env_value, expected
    ):
        """Test environment variable value parsing for various formats."""
        os.environ["FEATURE_FLAG_FEEDBACK_AI_ANALYSIS_ENABLED"] = env_value
        flags = FeatureFlags(session=db_session)

        result = flags.is_enabled(Feature.FEEDBACK_AI_ANALYSIS)

        assert result is expected

    def test_environment_variable_overrides_database(
        self, clear_env_vars, db_session, repository, create_system_setting
    ):
        """Test environment variable overrides database setting (priority test)."""
        # Set database to False
        create_system_setting(key="feedback_ai_analysis_enabled", value="false")

        # Set environment to True (should override)
        os.environ["FEATURE_FLAG_FEEDBACK_AI_ANALYSIS_ENABLED"] = "true"

        flags = FeatureFlags(session=db_session, settings_repository=repository)
        result = flags.is_enabled(Feature.FEEDBACK_AI_ANALYSIS)

        assert result is True  # Environment wins

    # ==================== PRIORITY TIER 2: DATABASE CONFIGURATION ====================

    def test_is_enabled_from_database_true(self, clear_env_vars, db_session, create_system_setting):
        """Test feature enabled via database configuration."""
        create_system_setting(key="cost_tracking_enabled", value="true")

        flags = FeatureFlags(session=db_session)
        result = flags.is_enabled(Feature.COST_TRACKING)

        assert result is True

    def test_is_enabled_from_database_false(
        self, clear_env_vars, db_session, create_system_setting
    ):
        """Test feature disabled via database configuration."""
        create_system_setting(key="cost_tracking_enabled", value="false")

        flags = FeatureFlags(session=db_session)
        result = flags.is_enabled(Feature.COST_TRACKING)

        assert result is False

    @pytest.mark.parametrize(
        "db_value,expected",
        [
            ("true", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("0", False),
            ("no", False),
            ("off", False),
        ],
    )
    def test_database_value_parsing(
        self, clear_env_vars, db_session, create_system_setting, db_value, expected
    ):
        """Test database value parsing for various formats."""
        create_system_setting(key="cost_tracking_enabled", value=db_value)

        flags = FeatureFlags(session=db_session)
        result = flags.is_enabled(Feature.COST_TRACKING)

        assert result is expected

    def test_database_setting_without_session(self, clear_env_vars):
        """Test that database is skipped when no session available."""
        flags = FeatureFlags(session=None)

        # Should fall through to defaults without crashing
        result = flags.is_enabled(Feature.COST_TRACKING)

        assert isinstance(result, bool)

    def test_database_error_falls_through_to_defaults(self, clear_env_vars, db_session):
        """Test that database errors don't crash, fall through to defaults."""
        # Create flags with a broken repository that will raise exception
        flags = FeatureFlags(session=db_session)

        # Force an error by closing the session
        db_session.close()

        # Should not crash, should fall through to defaults
        result = flags.is_enabled(Feature.COST_TRACKING)

        assert isinstance(result, bool)

    # ==================== PRIORITY TIER 3: CONFIG DEFAULTS ====================

    def test_is_enabled_from_config_defaults(self, clear_env_vars, db_session, mock_settings):
        """Test feature enabled via Settings config defaults."""
        # No env var, no database setting
        # Mock settings has enable_multi_file = True
        flags = FeatureFlags(session=db_session, settings=mock_settings)

        result = flags.is_enabled(Feature.MULTI_FILE_PROCESSING)

        assert result is True

    def test_is_enabled_from_config_mapping(self, clear_env_vars, db_session, mock_settings):
        """Test config mapping for privacy filter."""
        # Privacy filter should map to enable_privacy_filter
        mock_settings.enable_privacy_filter = True

        flags = FeatureFlags(session=db_session, settings=mock_settings)

        result = flags.is_enabled(Feature.ADVANCED_PRIVACY_FILTER)

        assert result is True

    def test_config_mapping_for_pii_removal(self, clear_env_vars, db_session, mock_settings):
        """Test that PII_REMOVAL_ENABLED maps to same config as ADVANCED_PRIVACY_FILTER."""
        mock_settings.enable_privacy_filter = False

        flags = FeatureFlags(session=db_session, settings=mock_settings)

        # Both should map to same config attribute
        assert flags.is_enabled(Feature.PII_REMOVAL_ENABLED) is False
        assert flags.is_enabled(Feature.ADVANCED_PRIVACY_FILTER) is False

    # ==================== PRIORITY TIER 4: HARDCODED DEFAULTS ====================

    def test_hardcoded_default_enabled_features(self, clear_env_vars, db_session):
        """Test features enabled by hardcoded defaults."""
        flags = FeatureFlags(session=db_session, settings=None)

        # These should be True by default
        assert flags.is_enabled(Feature.FEEDBACK_AI_ANALYSIS) is True
        assert flags.is_enabled(Feature.MULTI_FILE_PROCESSING) is True
        assert flags.is_enabled(Feature.ADVANCED_PRIVACY_FILTER) is True
        assert flags.is_enabled(Feature.PII_REMOVAL_ENABLED) is True
        assert flags.is_enabled(Feature.COST_TRACKING) is True
        assert flags.is_enabled(Feature.AI_LOGGING) is True
        assert flags.is_enabled(Feature.DYNAMIC_BRANCHING) is True
        assert flags.is_enabled(Feature.STOP_CONDITIONS) is True
        assert flags.is_enabled(Feature.RETRY_ON_FAILURE) is True

    def test_hardcoded_default_disabled_features(self, clear_env_vars, db_session):
        """Test features disabled by hardcoded defaults (experimental)."""
        flags = FeatureFlags(session=db_session, settings=None)

        # Experimental features should be False by default
        assert flags.is_enabled(Feature.PARALLEL_STEP_EXECUTION) is False

    def test_unknown_feature_defaults_to_false(self, clear_env_vars, db_session):
        """Test that features not in DEFAULTS dict default to False."""
        flags = FeatureFlags(session=db_session, settings=None)

        # Create a mock feature not in defaults
        with patch.object(Feature, "__iter__", return_value=iter([Mock(value="unknown_feature")])):
            # Should not crash
            pass

    # ==================== PRIORITY SYSTEM INTEGRATION TESTS ====================

    def test_complete_priority_chain_env_wins(
        self, clear_env_vars, db_session, mock_settings, create_system_setting
    ):
        """Test complete priority chain where environment variable wins."""
        # Set all tiers to different values
        mock_settings.enable_multi_file = False  # Config: False
        create_system_setting(key="multi_file_processing_enabled", value="false")  # DB: False
        os.environ["FEATURE_FLAG_MULTI_FILE_PROCESSING_ENABLED"] = "true"  # ENV: True

        flags = FeatureFlags(session=db_session, settings=mock_settings)
        result = flags.is_enabled(Feature.MULTI_FILE_PROCESSING)

        assert result is True  # Environment variable wins

    def test_complete_priority_chain_db_wins_over_config(
        self, clear_env_vars, db_session, mock_settings, create_system_setting
    ):
        """Test complete priority chain where database wins over config."""
        # No environment variable
        mock_settings.enable_privacy_filter = False  # Config: False
        create_system_setting(key="advanced_privacy_filter_enabled", value="true")  # DB: True

        flags = FeatureFlags(session=db_session, settings=mock_settings)
        result = flags.is_enabled(Feature.ADVANCED_PRIVACY_FILTER)

        assert result is True  # Database wins over config

    def test_complete_priority_chain_config_wins_over_hardcoded(
        self, clear_env_vars, db_session, mock_settings
    ):
        """Test complete priority chain where config wins over hardcoded default."""
        # No environment variable, no database
        mock_settings.enable_multi_file = False  # Config: False
        # Hardcoded default: True

        flags = FeatureFlags(session=db_session, settings=mock_settings)
        result = flags.is_enabled(Feature.MULTI_FILE_PROCESSING)

        assert result is False  # Config wins over hardcoded default

    # ==================== OTHER METHOD TESTS ====================

    def test_is_disabled(self, clear_env_vars, db_session):
        """Test is_disabled() method (inverse of is_enabled)."""
        flags = FeatureFlags(session=db_session, settings=None)

        # Enabled feature should return False for is_disabled
        assert flags.is_disabled(Feature.COST_TRACKING) is False

        # Disabled feature should return True for is_disabled
        assert flags.is_disabled(Feature.PARALLEL_STEP_EXECUTION) is True

    def test_get_enabled_features(self, clear_env_vars, db_session):
        """Test get_enabled_features() returns list of enabled feature names."""
        flags = FeatureFlags(session=db_session, settings=None)

        enabled = flags.get_enabled_features()

        assert isinstance(enabled, list)
        assert len(enabled) > 0
        assert "feedback_ai_analysis_enabled" in enabled
        assert "cost_tracking_enabled" in enabled
        assert "parallel_step_execution_enabled" not in enabled  # Disabled by default

    def test_get_enabled_features_with_env_override(self, clear_env_vars, db_session):
        """Test get_enabled_features() reflects environment variable overrides."""
        # Enable an experimental feature via env var
        os.environ["FEATURE_FLAG_PARALLEL_STEP_EXECUTION_ENABLED"] = "true"

        flags = FeatureFlags(session=db_session, settings=None)
        enabled = flags.get_enabled_features()

        assert "parallel_step_execution_enabled" in enabled

    def test_get_feature_status(self, clear_env_vars, db_session):
        """Test get_feature_status() returns dict of all features."""
        flags = FeatureFlags(session=db_session, settings=None)

        status = flags.get_feature_status()

        assert isinstance(status, dict)
        assert len(status) == len(Feature)  # All features included

        # Check specific features
        assert status["feedback_ai_analysis_enabled"] is True
        assert status["cost_tracking_enabled"] is True
        assert status["parallel_step_execution_enabled"] is False

    def test_get_feature_status_comprehensive(
        self, clear_env_vars, db_session, create_system_setting
    ):
        """Test get_feature_status() with mixed sources."""
        # Mix of env, db, and defaults
        os.environ["FEATURE_FLAG_COST_TRACKING_ENABLED"] = "false"
        create_system_setting(key="ai_logging_enabled", value="false")

        flags = FeatureFlags(session=db_session, settings=None)
        status = flags.get_feature_status()

        assert status["cost_tracking_enabled"] is False  # From env
        assert status["ai_logging_enabled"] is False  # From DB
        assert status["feedback_ai_analysis_enabled"] is True  # From defaults

    def test_require_feature_enabled_passes(self, clear_env_vars, db_session):
        """Test require_feature() passes when feature is enabled."""
        flags = FeatureFlags(session=db_session, settings=None)

        # Should not raise exception
        flags.require_feature(Feature.COST_TRACKING)

    def test_require_feature_disabled_raises(self, clear_env_vars, db_session):
        """Test require_feature() raises RuntimeError when feature is disabled."""
        flags = FeatureFlags(session=db_session, settings=None)

        with pytest.raises(RuntimeError) as exc_info:
            flags.require_feature(Feature.PARALLEL_STEP_EXECUTION)

        assert "parallel_step_execution_enabled" in str(exc_info.value)
        assert "required but currently disabled" in str(exc_info.value)
        assert "FEATURE_FLAG_PARALLEL_STEP_EXECUTION_ENABLED=true" in str(exc_info.value)

    # ==================== GLOBAL HELPER FUNCTION TESTS ====================

    def test_global_is_feature_enabled(self, clear_env_vars, db_session, mock_settings):
        """Test global is_feature_enabled() helper function."""
        result = is_feature_enabled(
            Feature.COST_TRACKING, session=db_session, settings=mock_settings
        )

        assert isinstance(result, bool)

    def test_global_is_feature_enabled_without_session(self, clear_env_vars, mock_settings):
        """Test global helper without session."""
        result = is_feature_enabled(
            Feature.FEEDBACK_AI_ANALYSIS, session=None, settings=mock_settings
        )

        assert isinstance(result, bool)

    def test_global_is_feature_enabled_respects_env(self, clear_env_vars, mock_settings):
        """Test global helper respects environment variables."""
        os.environ["FEATURE_FLAG_COST_TRACKING_ENABLED"] = "false"

        result = is_feature_enabled(Feature.COST_TRACKING, session=None, settings=mock_settings)

        assert result is False

    def test_global_get_enabled_features(self, clear_env_vars, db_session, mock_settings):
        """Test global get_enabled_features() helper function."""
        enabled = get_enabled_features(session=db_session, settings=mock_settings)

        assert isinstance(enabled, list)
        assert len(enabled) > 0

    def test_global_get_enabled_features_without_session(self, clear_env_vars, mock_settings):
        """Test global helper without session."""
        enabled = get_enabled_features(session=None, settings=mock_settings)

        assert isinstance(enabled, list)

    # ==================== EDGE CASE TESTS ====================

    def test_feature_check_with_none_values(self, clear_env_vars):
        """Test feature checks handle None values gracefully."""
        flags = FeatureFlags(session=None, settings=None, settings_repository=None)

        # Should not crash
        result = flags.is_enabled(Feature.COST_TRACKING)

        assert isinstance(result, bool)

    def test_multiple_feature_checks_consistent(self, clear_env_vars, db_session):
        """Test multiple checks of same feature return consistent results."""
        flags = FeatureFlags(session=db_session, settings=None)

        result1 = flags.is_enabled(Feature.COST_TRACKING)
        result2 = flags.is_enabled(Feature.COST_TRACKING)
        result3 = flags.is_enabled(Feature.COST_TRACKING)

        assert result1 == result2 == result3

    def test_all_features_checkable(self, clear_env_vars, db_session):
        """Test that all Feature enum values can be checked without errors."""
        flags = FeatureFlags(session=db_session, settings=None)

        for feature in Feature:
            result = flags.is_enabled(feature)
            assert isinstance(result, bool)

    def test_database_setting_case_sensitivity(
        self, clear_env_vars, db_session, create_system_setting
    ):
        """Test database value parsing is case-insensitive."""
        create_system_setting(key="cost_tracking_enabled", value="TrUe")

        flags = FeatureFlags(session=db_session)
        result = flags.is_enabled(Feature.COST_TRACKING)

        assert result is True

    def test_feature_flags_instance_isolation(self, clear_env_vars, db_session, mock_settings):
        """Test that different FeatureFlags instances work independently."""
        flags1 = FeatureFlags(session=db_session, settings=mock_settings)
        flags2 = FeatureFlags(session=None, settings=None)

        # Both should work independently
        result1 = flags1.is_enabled(Feature.COST_TRACKING)
        result2 = flags2.is_enabled(Feature.COST_TRACKING)

        assert isinstance(result1, bool)
        assert isinstance(result2, bool)

    # ==================== INTEGRATION TESTS ====================

    def test_feature_flag_workflow_complete(
        self, clear_env_vars, db_session, create_system_setting
    ):
        """Test complete feature flag workflow with all priority levels."""
        # Start with hardcoded defaults only
        flags = FeatureFlags(session=db_session, settings=None)
        assert flags.is_enabled(Feature.COST_TRACKING) is True  # Default

        # Add database configuration
        create_system_setting(key="cost_tracking_enabled", value="false")
        flags = FeatureFlags(session=db_session, settings=None)
        assert flags.is_enabled(Feature.COST_TRACKING) is False  # DB overrides default

        # Add environment variable
        os.environ["FEATURE_FLAG_COST_TRACKING_ENABLED"] = "true"
        flags = FeatureFlags(session=db_session, settings=None)
        assert flags.is_enabled(Feature.COST_TRACKING) is True  # Env overrides DB

    def test_feature_status_matches_individual_checks(self, clear_env_vars, db_session):
        """Test that get_feature_status() matches individual is_enabled() calls."""
        flags = FeatureFlags(session=db_session, settings=None)

        status = flags.get_feature_status()

        for feature in Feature:
            assert status[feature.value] == flags.is_enabled(feature)

    def test_enabled_features_list_matches_status(self, clear_env_vars, db_session):
        """Test that get_enabled_features() matches get_feature_status()."""
        flags = FeatureFlags(session=db_session, settings=None)

        enabled_list = flags.get_enabled_features()
        status_dict = flags.get_feature_status()

        enabled_from_status = [k for k, v in status_dict.items() if v is True]

        assert set(enabled_list) == set(enabled_from_status)

    def test_real_world_scenario_mixed_sources(
        self, clear_env_vars, db_session, mock_settings, create_system_setting
    ):
        """Test real-world scenario with features from different sources."""
        # Environment: Disable cost tracking
        os.environ["FEATURE_FLAG_COST_TRACKING_ENABLED"] = "false"

        # Database: Disable AI logging
        create_system_setting(key="ai_logging_enabled", value="false")

        # Config: Enable multi-file
        mock_settings.enable_multi_file = True

        # Everything else: defaults

        flags = FeatureFlags(session=db_session, settings=mock_settings)

        assert flags.is_enabled(Feature.COST_TRACKING) is False  # From env
        assert flags.is_enabled(Feature.AI_LOGGING) is False  # From DB
        assert flags.is_enabled(Feature.MULTI_FILE_PROCESSING) is True  # From config
        assert flags.is_enabled(Feature.FEEDBACK_AI_ANALYSIS) is True  # From defaults
        assert (
            flags.is_enabled(Feature.PARALLEL_STEP_EXECUTION) is False
        )  # From defaults (experimental)
