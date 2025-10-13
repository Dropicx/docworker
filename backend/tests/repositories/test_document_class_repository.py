"""
Tests for DocumentClassRepository

Tests specialized queries for document class management,
including classification, indicators, examples, and statistics.
"""

import pytest

from app.repositories.document_class_repository import DocumentClassRepository


class TestDocumentClassRepository:
    """Test suite for DocumentClassRepository specialized methods."""

    @pytest.fixture
    def repository(self, db_session):
        """Create DocumentClassRepository instance."""
        return DocumentClassRepository(db_session)

    # ==================== BASIC CRUD TESTS ====================

    def test_create_document_class(self, repository):
        """Test creating a new document class."""
        doc_class = repository.create(
            class_key="ARZTBRIEF",
            display_name="Arztbrief",
            description="Doctor's letter",
            icon="📨",
            is_enabled=True,
            is_system_class=True
        )

        assert doc_class.id is not None
        assert doc_class.class_key == "ARZTBRIEF"
        assert doc_class.display_name == "Arztbrief"
        assert doc_class.is_enabled is True

    def test_get_by_id(self, repository, create_document_class):
        """Test retrieving document class by ID."""
        created_class = create_document_class(class_key="TEST_CLASS")
        retrieved_class = repository.get_by_id(created_class.id)

        assert retrieved_class is not None
        assert retrieved_class.id == created_class.id

    # ==================== QUERY BY CLASS KEY ====================

    def test_get_by_class_key_existing(self, repository, create_document_class):
        """Test retrieving document class by its unique key."""
        create_document_class(class_key="ARZTBRIEF", display_name="Arztbrief")

        doc_class = repository.get_by_class_key("ARZTBRIEF")

        assert doc_class is not None
        assert doc_class.class_key == "ARZTBRIEF"
        assert doc_class.display_name == "Arztbrief"

    def test_get_by_class_key_nonexistent(self, repository):
        """Test retrieving non-existent class key returns None."""
        doc_class = repository.get_by_class_key("NONEXISTENT")
        assert doc_class is None

    # ==================== ENABLED/DISABLED CLASSES ====================

    def test_get_enabled_classes(self, repository, create_document_class):
        """Test retrieving all enabled document classes."""
        create_document_class(class_key="ENABLED_1", is_enabled=True)
        create_document_class(class_key="ENABLED_2", is_enabled=True)
        create_document_class(class_key="DISABLED_1", is_enabled=False)

        enabled_classes = repository.get_enabled_classes()

        assert len(enabled_classes) == 2
        assert all(doc_class.is_enabled for doc_class in enabled_classes)

    def test_get_enabled_classes_ordered_by_display_name(self, repository, create_document_class):
        """Test that enabled classes are ordered by display name."""
        create_document_class(class_key="C", display_name="Charlie", is_enabled=True)
        create_document_class(class_key="A", display_name="Alpha", is_enabled=True)
        create_document_class(class_key="B", display_name="Bravo", is_enabled=True)

        enabled_classes = repository.get_enabled_classes()

        assert len(enabled_classes) == 3
        assert enabled_classes[0].display_name == "Alpha"
        assert enabled_classes[1].display_name == "Bravo"
        assert enabled_classes[2].display_name == "Charlie"

    def test_get_disabled_classes(self, repository, create_document_class):
        """Test retrieving all disabled document classes."""
        create_document_class(class_key="ENABLED_1", is_enabled=True)
        create_document_class(class_key="DISABLED_1", is_enabled=False)
        create_document_class(class_key="DISABLED_2", is_enabled=False)

        disabled_classes = repository.get_disabled_classes()

        assert len(disabled_classes) == 2
        assert all(not doc_class.is_enabled for doc_class in disabled_classes)

    # ==================== SYSTEM VS USER CLASSES ====================

    def test_get_system_classes(self, repository, create_document_class):
        """Test retrieving system document classes."""
        create_document_class(class_key="SYSTEM_1", is_system_class=True)
        create_document_class(class_key="SYSTEM_2", is_system_class=True)
        create_document_class(class_key="USER_1", is_system_class=False)

        system_classes = repository.get_system_classes()

        assert len(system_classes) == 2
        assert all(doc_class.is_system_class for doc_class in system_classes)

    def test_get_user_classes(self, repository, create_document_class):
        """Test retrieving user-created document classes."""
        create_document_class(class_key="SYSTEM_1", is_system_class=True)
        create_document_class(class_key="USER_1", is_system_class=False)
        create_document_class(class_key="USER_2", is_system_class=False)

        user_classes = repository.get_user_classes()

        assert len(user_classes) == 2
        assert all(not doc_class.is_system_class for doc_class in user_classes)

    # ==================== CLASS KEY EXISTENCE CHECK ====================

    def test_class_key_exists_true(self, repository, create_document_class):
        """Test checking if class key exists."""
        create_document_class(class_key="EXISTING_KEY")

        exists = repository.class_key_exists("EXISTING_KEY")

        assert exists is True

    def test_class_key_exists_false(self, repository):
        """Test checking if non-existent class key exists."""
        exists = repository.class_key_exists("NONEXISTENT_KEY")

        assert exists is False

    def test_class_key_exists_with_exclusion(self, repository, create_document_class):
        """Test checking key existence while excluding specific ID."""
        doc_class = create_document_class(class_key="UPDATE_KEY")

        # Should return False when excluding the same ID
        exists = repository.class_key_exists("UPDATE_KEY", exclude_id=doc_class.id)

        assert exists is False

    def test_class_key_exists_with_exclusion_multiple_records(self, repository, create_document_class):
        """Test key existence check with exclusion when duplicates would exist."""
        doc_class1 = create_document_class(class_key="KEY_1")
        create_document_class(class_key="KEY_2")

        # Check if KEY_2 exists, excluding KEY_1's ID
        exists = repository.class_key_exists("KEY_2", exclude_id=doc_class1.id)

        assert exists is True

    # ==================== ENABLE/DISABLE OPERATIONS ====================

    def test_enable_class(self, repository, create_document_class):
        """Test enabling a disabled document class."""
        doc_class = create_document_class(class_key="DISABLE_TEST", is_enabled=False)

        enabled_class = repository.enable_class(doc_class.id)

        assert enabled_class is not None
        assert enabled_class.is_enabled is True

    def test_disable_class(self, repository, create_document_class):
        """Test disabling an enabled document class."""
        doc_class = create_document_class(class_key="ENABLE_TEST", is_enabled=True)

        disabled_class = repository.disable_class(doc_class.id)

        assert disabled_class is not None
        assert disabled_class.is_enabled is False

    def test_enable_nonexistent_class(self, repository):
        """Test enabling non-existent class returns None."""
        result = repository.enable_class(999999)
        assert result is None

    def test_disable_nonexistent_class(self, repository):
        """Test disabling non-existent class returns None."""
        result = repository.disable_class(999999)
        assert result is None

    # ==================== INDICATORS ====================

    def test_get_classes_with_indicators_strong(self, repository, create_document_class):
        """Test retrieving classes with specific strong indicator."""
        create_document_class(
            class_key="CLASS_1",
            strong_indicators=["Arztbrief", "Entlassungsbericht"]
        )
        create_document_class(
            class_key="CLASS_2",
            strong_indicators=["Befund", "Labor"]
        )

        classes = repository.get_classes_with_indicators("Arztbrief")

        assert len(classes) == 1
        assert classes[0].class_key == "CLASS_1"

    def test_get_classes_with_indicators_weak(self, repository, create_document_class):
        """Test retrieving classes with specific weak indicator."""
        create_document_class(
            class_key="CLASS_1",
            weak_indicators=["Patient", "Diagnose"]
        )
        create_document_class(
            class_key="CLASS_2",
            weak_indicators=["Laborwerte"]
        )

        classes = repository.get_classes_with_indicators("Patient")

        assert len(classes) == 1
        assert classes[0].class_key == "CLASS_1"

    def test_get_classes_with_indicators_no_match(self, repository, create_document_class):
        """Test searching for non-existent indicator returns empty list."""
        create_document_class(
            class_key="CLASS_1",
            strong_indicators=["Arztbrief"]
        )

        classes = repository.get_classes_with_indicators("Nonexistent")

        assert classes == []

    def test_add_strong_indicator(self, repository, create_document_class):
        """Test adding a strong indicator to a document class."""
        doc_class = create_document_class(
            class_key="INDICATOR_TEST",
            strong_indicators=["Initial"]
        )

        updated_class = repository.add_strong_indicator(doc_class.id, "NewIndicator")

        assert updated_class is not None
        assert "Initial" in updated_class.strong_indicators
        assert "NewIndicator" in updated_class.strong_indicators

    def test_add_strong_indicator_to_empty_list(self, repository, create_document_class):
        """Test adding strong indicator when list is None."""
        doc_class = create_document_class(
            class_key="EMPTY_INDICATORS",
            strong_indicators=None
        )

        updated_class = repository.add_strong_indicator(doc_class.id, "FirstIndicator")

        assert updated_class is not None
        assert updated_class.strong_indicators == ["FirstIndicator"]

    def test_add_strong_indicator_duplicate(self, repository, create_document_class):
        """Test adding duplicate strong indicator doesn't create duplicates."""
        doc_class = create_document_class(
            class_key="DUP_TEST",
            strong_indicators=["Existing"]
        )

        repository.add_strong_indicator(doc_class.id, "Existing")
        updated_class = repository.get(doc_class.id)

        assert updated_class.strong_indicators.count("Existing") == 1

    def test_add_weak_indicator(self, repository, create_document_class):
        """Test adding a weak indicator to a document class."""
        doc_class = create_document_class(
            class_key="WEAK_TEST",
            weak_indicators=["Initial"]
        )

        updated_class = repository.add_weak_indicator(doc_class.id, "NewWeak")

        assert updated_class is not None
        assert "Initial" in updated_class.weak_indicators
        assert "NewWeak" in updated_class.weak_indicators

    def test_add_weak_indicator_to_empty_list(self, repository, create_document_class):
        """Test adding weak indicator when list is None."""
        doc_class = create_document_class(
            class_key="EMPTY_WEAK",
            weak_indicators=None
        )

        updated_class = repository.add_weak_indicator(doc_class.id, "FirstWeak")

        assert updated_class is not None
        assert updated_class.weak_indicators == ["FirstWeak"]

    # ==================== EXAMPLES ====================

    def test_get_classes_with_examples(self, repository, create_document_class):
        """Test retrieving classes with specific example."""
        create_document_class(
            class_key="CLASS_1",
            examples=["Sehr geehrte", "Mit freundlichen"]
        )
        create_document_class(
            class_key="CLASS_2",
            examples=["Laborwerte", "Blutwerte"]
        )

        classes = repository.get_classes_with_examples("Laborwerte")

        assert len(classes) == 1
        assert classes[0].class_key == "CLASS_2"

    def test_get_classes_with_examples_no_match(self, repository, create_document_class):
        """Test searching for non-existent example returns empty list."""
        create_document_class(
            class_key="CLASS_1",
            examples=["Example1"]
        )

        classes = repository.get_classes_with_examples("Nonexistent")

        assert classes == []

    def test_add_example(self, repository, create_document_class):
        """Test adding an example to a document class."""
        doc_class = create_document_class(
            class_key="EXAMPLE_TEST",
            examples=["Initial example"]
        )

        updated_class = repository.add_example(doc_class.id, "New example")

        assert updated_class is not None
        assert "Initial example" in updated_class.examples
        assert "New example" in updated_class.examples

    def test_add_example_to_empty_list(self, repository, create_document_class):
        """Test adding example when list is None."""
        doc_class = create_document_class(
            class_key="EMPTY_EXAMPLES",
            examples=None
        )

        updated_class = repository.add_example(doc_class.id, "First example")

        assert updated_class is not None
        assert updated_class.examples == ["First example"]

    def test_add_example_duplicate(self, repository, create_document_class):
        """Test adding duplicate example doesn't create duplicates."""
        doc_class = create_document_class(
            class_key="DUP_EXAMPLE",
            examples=["Existing example"]
        )

        repository.add_example(doc_class.id, "Existing example")
        updated_class = repository.get(doc_class.id)

        assert updated_class.examples.count("Existing example") == 1

    def test_add_example_nonexistent_class(self, repository):
        """Test adding example to non-existent class returns None."""
        result = repository.add_example(999999, "Example")
        assert result is None

    def test_remove_example(self, repository, create_document_class):
        """Test removing an example from a document class."""
        doc_class = create_document_class(
            class_key="REMOVE_EXAMPLE",
            examples=["Keep this", "Remove this"]
        )

        updated_class = repository.remove_example(doc_class.id, "Remove this")

        assert updated_class is not None
        assert "Keep this" in updated_class.examples
        assert "Remove this" not in updated_class.examples

    def test_remove_example_nonexistent(self, repository, create_document_class):
        """Test removing non-existent example returns class unchanged."""
        doc_class = create_document_class(
            class_key="REMOVE_TEST",
            examples=["Example1"]
        )

        updated_class = repository.remove_example(doc_class.id, "Nonexistent")

        assert updated_class is not None
        assert updated_class.examples == ["Example1"]

    def test_remove_example_from_empty_list(self, repository, create_document_class):
        """Test removing example when list is None returns None."""
        doc_class = create_document_class(
            class_key="EMPTY_REMOVE",
            examples=None
        )

        result = repository.remove_example(doc_class.id, "Any")

        assert result is None

    def test_remove_example_nonexistent_class(self, repository):
        """Test removing example from non-existent class returns None."""
        result = repository.remove_example(999999, "Example")
        assert result is None

    # ==================== ASSOCIATED STEPS ====================

    def test_has_associated_steps_false(self, repository, create_document_class):
        """Test checking for associated steps when none exist."""
        doc_class = create_document_class(class_key="NO_STEPS")

        has_steps = repository.has_associated_steps(doc_class.id)

        assert has_steps is False

    def test_has_associated_steps_true(
        self,
        repository,
        create_document_class,
        create_pipeline_step,
        sample_llama_model
    ):
        """Test checking for associated steps when they exist."""
        doc_class = create_document_class(class_key="WITH_STEPS")

        # Create a pipeline step associated with this class
        create_pipeline_step(
            name="Test Step",
            document_class_id=doc_class.id,
            selected_model_id=sample_llama_model.id
        )

        has_steps = repository.has_associated_steps(doc_class.id)

        assert has_steps is True

    # ==================== STATISTICS ====================

    def test_get_class_statistics_empty(self, repository):
        """Test getting statistics with no classes."""
        stats = repository.get_class_statistics()

        assert stats["total_classes"] == 0
        assert stats["enabled_classes"] == 0
        assert stats["disabled_classes"] == 0
        assert stats["system_classes"] == 0
        assert stats["user_classes"] == 0

    def test_get_class_statistics_comprehensive(self, repository, create_document_class):
        """Test getting comprehensive statistics."""
        # Create various types of classes
        create_document_class(
            class_key="SYS_ENABLED",
            is_enabled=True,
            is_system_class=True,
            examples=["Example"],
            strong_indicators=["Strong"],
            weak_indicators=["Weak"]
        )
        create_document_class(
            class_key="SYS_DISABLED",
            is_enabled=False,
            is_system_class=True
        )
        create_document_class(
            class_key="USER_ENABLED",
            is_enabled=True,
            is_system_class=False,
            examples=["Example2"]
        )
        create_document_class(
            class_key="USER_DISABLED",
            is_enabled=False,
            is_system_class=False
        )

        stats = repository.get_class_statistics()

        assert stats["total_classes"] == 4
        assert stats["enabled_classes"] == 2
        assert stats["disabled_classes"] == 2
        assert stats["system_classes"] == 2
        assert stats["user_classes"] == 2
        assert stats["classes_with_examples"] == 2
        assert stats["classes_with_strong_indicators"] == 1
        assert stats["classes_with_weak_indicators"] == 1

    # ==================== SEARCH ====================

    def test_search_by_display_name(self, repository, create_document_class):
        """Test searching classes by display name."""
        create_document_class(class_key="KEY1", display_name="Arztbrief")
        create_document_class(class_key="KEY2", display_name="Befundbericht")
        create_document_class(class_key="KEY3", display_name="Arzt Notizen")

        results = repository.search_by_display_name("Arzt")

        assert len(results) == 2
        display_names = [r.display_name for r in results]
        assert "Arztbrief" in display_names
        assert "Arzt Notizen" in display_names

    def test_search_by_display_name_case_insensitive(self, repository, create_document_class):
        """Test that display name search is case-insensitive."""
        create_document_class(class_key="KEY1", display_name="Arztbrief")

        results = repository.search_by_display_name("arzt")

        assert len(results) == 1
        assert results[0].display_name == "Arztbrief"

    def test_search_by_display_name_no_match(self, repository, create_document_class):
        """Test searching for non-existent display name."""
        create_document_class(class_key="KEY1", display_name="Arztbrief")

        results = repository.search_by_display_name("Nonexistent")

        assert results == []

    def test_search_by_description(self, repository, create_document_class):
        """Test searching classes by description."""
        create_document_class(
            class_key="KEY1",
            display_name="Class 1",
            description="Medical letter from doctor"
        )
        create_document_class(
            class_key="KEY2",
            display_name="Class 2",
            description="Laboratory results"
        )

        results = repository.search_by_description("medical")

        assert len(results) == 1
        assert results[0].class_key == "KEY1"

    def test_search_by_description_case_insensitive(self, repository, create_document_class):
        """Test that description search is case-insensitive."""
        create_document_class(
            class_key="KEY1",
            description="Medical Letter"
        )

        results = repository.search_by_description("MEDICAL")

        assert len(results) == 1
        assert results[0].class_key == "KEY1"

    def test_search_by_description_no_match(self, repository, create_document_class):
        """Test searching for non-existent description."""
        create_document_class(
            class_key="KEY1",
            description="Medical letter"
        )

        results = repository.search_by_description("Nonexistent")

        assert results == []

    # ==================== INTEGRATION WITH BASE REPOSITORY ====================

    def test_inherits_base_repository_methods(self, repository, create_document_class):
        """Test that specialized repository inherits base CRUD methods."""
        # Test create (from base)
        doc_class = repository.create(
            class_key="BASE_TEST",
            display_name="Base Test Class",
            is_enabled=True,
            is_system_class=False
        )

        # Test get_by_id (from base)
        retrieved = repository.get_by_id(doc_class.id)
        assert retrieved is not None

        # Test update (from base)
        updated = repository.update(doc_class.id, display_name="Updated Name")
        assert updated.display_name == "Updated Name"

        # Test delete (from base)
        deleted = repository.delete(doc_class.id)
        assert deleted is True

        # Verify deletion
        assert repository.get_by_id(doc_class.id) is None
