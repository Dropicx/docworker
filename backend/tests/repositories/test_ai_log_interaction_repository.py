"""
Tests for AILogInteractionRepository

Tests specialized queries for AI interaction logs, cost tracking,
and usage analytics beyond basic CRUD operations.
"""

import pytest
from datetime import datetime, timezone, timedelta

from app.repositories.ai_log_interaction_repository import AILogInteractionRepository


class TestAILogInteractionRepository:
    """Test suite for AILogInteractionRepository specialized methods."""

    @pytest.fixture
    def repository(self, db_session):
        """Create AILogInteractionRepository instance."""
        return AILogInteractionRepository(db_session)

    # ==================== BASIC CRUD TESTS ====================

    def test_create_log_interaction(self, repository):
        """Test creating a new AI log interaction."""
        log = repository.create(
            processing_id="proc-123",
            step_name="translation",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            input_cost_usd=0.001,
            output_cost_usd=0.002,
            total_cost_usd=0.003,
            model_provider="OVH",
            model_name="Meta-Llama-3_3-70B-Instruct",
            document_type="ARZTBRIEF",
        )

        assert log.id is not None
        assert log.processing_id == "proc-123"
        assert log.total_tokens == 150
        assert log.total_cost_usd == 0.003

    def test_get_by_id(self, repository, create_ai_log_interaction):
        """Test retrieving log by ID."""
        created_log = create_ai_log_interaction(processing_id="test-proc")
        retrieved_log = repository.get_by_id(created_log.id)

        assert retrieved_log is not None
        assert retrieved_log.id == created_log.id
        assert retrieved_log.processing_id == "test-proc"

    # ==================== QUERY BY PROCESSING ID ====================

    def test_get_by_processing_id_single(self, repository, create_ai_log_interaction):
        """Test retrieving logs for a specific processing ID."""
        create_ai_log_interaction(processing_id="proc-123", step_name="step1", total_cost_usd=0.005)

        logs = repository.get_by_processing_id("proc-123")

        assert len(logs) == 1
        assert logs[0].processing_id == "proc-123"

    def test_get_by_processing_id_multiple_steps(self, repository, create_ai_log_interaction):
        """Test retrieving multiple steps for same processing ID."""
        # Create logs for different steps in same processing
        create_ai_log_interaction(
            processing_id="proc-multi", step_name="extraction", total_cost_usd=0.001
        )
        create_ai_log_interaction(
            processing_id="proc-multi", step_name="translation", total_cost_usd=0.002
        )
        create_ai_log_interaction(
            processing_id="proc-multi", step_name="validation", total_cost_usd=0.003
        )

        logs = repository.get_by_processing_id("proc-multi")

        assert len(logs) == 3
        assert all(log.processing_id == "proc-multi" for log in logs)
        step_names = [log.step_name for log in logs]
        assert "extraction" in step_names
        assert "translation" in step_names
        assert "validation" in step_names

    def test_get_by_processing_id_chronological_order(self, repository, create_ai_log_interaction):
        """Test that logs are returned in chronological order (created_at)."""
        # Create logs with slight time differences
        log1 = create_ai_log_interaction(processing_id="proc-order", step_name="step1")
        log2 = create_ai_log_interaction(processing_id="proc-order", step_name="step2")
        log3 = create_ai_log_interaction(processing_id="proc-order", step_name="step3")

        logs = repository.get_by_processing_id("proc-order")

        assert len(logs) == 3
        # Verify chronological order by created_at
        assert logs[0].created_at <= logs[1].created_at <= logs[2].created_at

    def test_get_by_processing_id_nonexistent(self, repository):
        """Test querying non-existent processing ID returns empty list."""
        logs = repository.get_by_processing_id("nonexistent-proc")
        assert logs == []

    # ==================== QUERY BY DATE RANGE ====================

    def test_get_by_date_range_both_bounds(self, repository, create_ai_log_interaction):
        """Test retrieving logs within a specific date range."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        # Create log that should be included
        log_in_range = create_ai_log_interaction(processing_id="in-range")

        logs = repository.get_by_date_range(start_date=yesterday, end_date=tomorrow)

        assert len(logs) >= 1
        assert any(log.processing_id == "in-range" for log in logs)

    def test_get_by_date_range_start_only(self, repository, create_ai_log_interaction):
        """Test querying with only start date (no upper bound)."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        create_ai_log_interaction(processing_id="recent")

        logs = repository.get_by_date_range(start_date=yesterday)

        assert len(logs) >= 1

    def test_get_by_date_range_end_only(self, repository, create_ai_log_interaction):
        """Test querying with only end date (no lower bound)."""
        now = datetime.now(timezone.utc)
        tomorrow = now + timedelta(days=1)

        create_ai_log_interaction(processing_id="old")

        logs = repository.get_by_date_range(end_date=tomorrow)

        assert len(logs) >= 1

    def test_get_by_date_range_no_bounds(self, repository, create_ai_log_interaction):
        """Test querying with no date bounds returns all logs."""
        create_ai_log_interaction(processing_id="log1")
        create_ai_log_interaction(processing_id="log2")

        logs = repository.get_by_date_range()

        assert len(logs) >= 2

    # ==================== FILTERED QUERIES ====================

    def test_get_filtered_by_processing_id(self, repository, create_ai_log_interaction):
        """Test filtered query by processing ID."""
        create_ai_log_interaction(processing_id="filter-proc-1")
        create_ai_log_interaction(processing_id="filter-proc-2")

        logs = repository.get_filtered(processing_id="filter-proc-1")

        assert len(logs) == 1
        assert logs[0].processing_id == "filter-proc-1"

    def test_get_filtered_by_document_type(self, repository, create_ai_log_interaction):
        """Test filtered query by document type."""
        create_ai_log_interaction(processing_id="proc1", document_type="ARZTBRIEF")
        create_ai_log_interaction(processing_id="proc2", document_type="BEFUNDBERICHT")
        create_ai_log_interaction(processing_id="proc3", document_type="ARZTBRIEF")

        logs = repository.get_filtered(document_type="ARZTBRIEF")

        assert len(logs) == 2
        assert all(log.document_type == "ARZTBRIEF" for log in logs)

    def test_get_filtered_multiple_criteria(self, repository, create_ai_log_interaction):
        """Test filtered query with multiple criteria."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        create_ai_log_interaction(processing_id="multi-filter", document_type="ARZTBRIEF")
        create_ai_log_interaction(processing_id="other-proc", document_type="ARZTBRIEF")

        logs = repository.get_filtered(
            processing_id="multi-filter",
            start_date=yesterday,
            end_date=tomorrow,
            document_type="ARZTBRIEF",
        )

        assert len(logs) == 1
        assert logs[0].processing_id == "multi-filter"
        assert logs[0].document_type == "ARZTBRIEF"

    def test_get_filtered_no_matches(self, repository, create_ai_log_interaction):
        """Test filtered query with no matches returns empty list."""
        create_ai_log_interaction(processing_id="proc1", document_type="ARZTBRIEF")

        logs = repository.get_filtered(document_type="NONEXISTENT_TYPE")

        assert logs == []

    # ==================== QUERY BY STEP NAME ====================

    def test_get_by_step_name(self, repository, create_ai_log_interaction):
        """Test retrieving logs by pipeline step name."""
        create_ai_log_interaction(processing_id="proc1", step_name="translation")
        create_ai_log_interaction(processing_id="proc2", step_name="translation")
        create_ai_log_interaction(processing_id="proc3", step_name="validation")

        logs = repository.get_by_step_name("translation")

        assert len(logs) == 2
        assert all(log.step_name == "translation" for log in logs)

    def test_get_by_step_name_nonexistent(self, repository):
        """Test querying non-existent step name returns empty list."""
        logs = repository.get_by_step_name("nonexistent_step")
        assert logs == []

    # ==================== QUERY BY MODEL ====================

    def test_get_by_model(self, repository, create_ai_log_interaction):
        """Test retrieving logs by model name."""
        create_ai_log_interaction(processing_id="proc1", model_name="Meta-Llama-3_3-70B-Instruct")
        create_ai_log_interaction(processing_id="proc2", model_name="Meta-Llama-3_3-70B-Instruct")
        create_ai_log_interaction(processing_id="proc3", model_name="Mistral-Nemo-Instruct-2407")

        logs = repository.get_by_model("Meta-Llama-3_3-70B-Instruct")

        assert len(logs) == 2
        assert all(log.model_name == "Meta-Llama-3_3-70B-Instruct" for log in logs)

    # ==================== QUERY BY DOCUMENT TYPE ====================

    def test_get_by_document_type(self, repository, create_ai_log_interaction):
        """Test retrieving logs by document type."""
        create_ai_log_interaction(processing_id="proc1", document_type="ARZTBRIEF")
        create_ai_log_interaction(processing_id="proc2", document_type="ARZTBRIEF")
        create_ai_log_interaction(processing_id="proc3", document_type="LABORWERTE")

        logs = repository.get_by_document_type("ARZTBRIEF")

        assert len(logs) == 2
        assert all(log.document_type == "ARZTBRIEF" for log in logs)

    # ==================== COST ANALYTICS ====================

    def test_get_total_cost_single_processing(self, repository, create_ai_log_interaction):
        """Test calculating total cost for a single processing."""
        create_ai_log_interaction(
            processing_id="cost-proc", step_name="step1", total_cost_usd=0.001
        )
        create_ai_log_interaction(
            processing_id="cost-proc", step_name="step2", total_cost_usd=0.002
        )
        create_ai_log_interaction(
            processing_id="cost-proc", step_name="step3", total_cost_usd=0.003
        )

        total_cost = repository.get_total_cost(processing_id="cost-proc")

        assert total_cost == 0.006

    def test_get_total_cost_all_logs(self, repository, create_ai_log_interaction):
        """Test calculating total cost across all logs."""
        create_ai_log_interaction(processing_id="proc1", total_cost_usd=0.005)
        create_ai_log_interaction(processing_id="proc2", total_cost_usd=0.010)
        create_ai_log_interaction(processing_id="proc3", total_cost_usd=0.015)

        total_cost = repository.get_total_cost()

        assert total_cost == 0.030

    def test_get_total_cost_with_date_range(self, repository, create_ai_log_interaction):
        """Test calculating cost within date range."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        create_ai_log_interaction(processing_id="recent", total_cost_usd=0.020)

        total_cost = repository.get_total_cost(start_date=yesterday, end_date=tomorrow)

        assert total_cost >= 0.020

    def test_get_total_cost_no_logs(self, repository):
        """Test total cost with no logs returns 0."""
        total_cost = repository.get_total_cost(processing_id="nonexistent")
        assert total_cost == 0.0

    def test_get_total_cost_handles_none_values(self, repository, create_ai_log_interaction):
        """Test that None cost values are treated as 0."""
        create_ai_log_interaction(processing_id="none-cost", total_cost_usd=None)
        create_ai_log_interaction(processing_id="none-cost", total_cost_usd=0.005)

        total_cost = repository.get_total_cost(processing_id="none-cost")

        assert total_cost == 0.005

    # ==================== TOKEN ANALYTICS ====================

    def test_get_total_tokens_single_processing(self, repository, create_ai_log_interaction):
        """Test calculating total tokens for a processing."""
        create_ai_log_interaction(processing_id="token-proc", step_name="step1", total_tokens=100)
        create_ai_log_interaction(processing_id="token-proc", step_name="step2", total_tokens=200)

        total_tokens = repository.get_total_tokens(processing_id="token-proc")

        assert total_tokens == 300

    def test_get_total_tokens_all_logs(self, repository, create_ai_log_interaction):
        """Test calculating total tokens across all logs."""
        create_ai_log_interaction(processing_id="proc1", total_tokens=500)
        create_ai_log_interaction(processing_id="proc2", total_tokens=1000)

        total_tokens = repository.get_total_tokens()

        assert total_tokens == 1500

    def test_get_total_tokens_handles_none_values(self, repository, create_ai_log_interaction):
        """Test that None token values are treated as 0."""
        create_ai_log_interaction(processing_id="none-tokens", total_tokens=None)
        create_ai_log_interaction(processing_id="none-tokens", total_tokens=250)

        total_tokens = repository.get_total_tokens(processing_id="none-tokens")

        assert total_tokens == 250

    # ==================== CALL COUNT ANALYTICS ====================

    def test_count_calls_for_processing(self, repository, create_ai_log_interaction):
        """Test counting API calls for a processing."""
        create_ai_log_interaction(processing_id="call-count", step_name="step1")
        create_ai_log_interaction(processing_id="call-count", step_name="step2")
        create_ai_log_interaction(processing_id="call-count", step_name="step3")

        count = repository.count_calls(processing_id="call-count")

        assert count == 3

    def test_count_calls_all_logs(self, repository, create_ai_log_interaction):
        """Test counting all API calls."""
        create_ai_log_interaction(processing_id="proc1")
        create_ai_log_interaction(processing_id="proc2")
        create_ai_log_interaction(processing_id="proc3")

        count = repository.count_calls()

        assert count == 3

    def test_count_calls_with_date_range(self, repository, create_ai_log_interaction):
        """Test counting calls within date range."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        create_ai_log_interaction(processing_id="recent-call")

        count = repository.count_calls(start_date=yesterday, end_date=tomorrow)

        assert count >= 1

    # ==================== DELETE OLD LOGS ====================

    def test_delete_old_logs(self, repository, create_ai_log_interaction, db_session):
        """Test deleting logs older than specified date."""
        # Note: In real tests with real timestamps, you'd need to manipulate created_at
        # For now, test the method exists and returns integer
        now = datetime.now(timezone.utc)
        cutoff_date = now + timedelta(days=1)  # Future date, should delete nothing

        deleted_count = repository.delete_old_logs(older_than=cutoff_date)

        # Should return an integer (count of deleted records)
        assert isinstance(deleted_count, int)
        assert deleted_count >= 0

    def test_delete_old_logs_preserves_recent(self, repository, create_ai_log_interaction):
        """Test that recent logs are not deleted."""
        recent_log = create_ai_log_interaction(processing_id="recent-log")

        # Delete logs older than yesterday (recent log should be preserved)
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        repository.delete_old_logs(older_than=yesterday)

        # Verify recent log still exists
        retrieved = repository.get_by_id(recent_log.id)
        assert retrieved is not None

    # ==================== COMBINED ANALYTICS ====================

    def test_cost_and_token_analytics_combined(self, repository, create_ai_log_interaction):
        """Test calculating both cost and tokens for same processing."""
        create_ai_log_interaction(
            processing_id="analytics-proc",
            step_name="step1",
            total_tokens=100,
            total_cost_usd=0.005,
        )
        create_ai_log_interaction(
            processing_id="analytics-proc",
            step_name="step2",
            total_tokens=200,
            total_cost_usd=0.010,
        )

        total_tokens = repository.get_total_tokens(processing_id="analytics-proc")
        total_cost = repository.get_total_cost(processing_id="analytics-proc")
        call_count = repository.count_calls(processing_id="analytics-proc")

        assert total_tokens == 300
        assert total_cost == 0.015
        assert call_count == 2

    def test_analytics_by_model_performance(self, repository, create_ai_log_interaction):
        """Test analyzing performance by model."""
        # Model A
        create_ai_log_interaction(model_name="ModelA", total_cost_usd=0.010, total_tokens=500)
        create_ai_log_interaction(model_name="ModelA", total_cost_usd=0.012, total_tokens=600)

        # Model B
        create_ai_log_interaction(model_name="ModelB", total_cost_usd=0.005, total_tokens=300)

        model_a_logs = repository.get_by_model("ModelA")
        model_b_logs = repository.get_by_model("ModelB")

        assert len(model_a_logs) == 2
        assert len(model_b_logs) == 1

        # Calculate average cost per token for each model
        model_a_total_cost = sum(log.total_cost_usd for log in model_a_logs)
        model_a_total_tokens = sum(log.total_tokens for log in model_a_logs)

        assert model_a_total_cost == 0.022
        assert model_a_total_tokens == 1100

    # ==================== INTEGRATION WITH BASE REPOSITORY ====================

    def test_inherits_base_repository_methods(self, repository, create_ai_log_interaction):
        """Test that specialized repository inherits base CRUD methods."""
        # Test create (from base)
        log = repository.create(
            processing_id="inherit-test", step_name="test_step", total_tokens=100
        )

        # Test get_by_id (from base)
        retrieved = repository.get_by_id(log.id)
        assert retrieved is not None

        # Test update (from base)
        updated = repository.update(log.id, total_tokens=200)
        assert updated.total_tokens == 200

        # Test delete (from base)
        deleted = repository.delete(log.id)
        assert deleted is True

        # Verify deletion
        assert repository.get_by_id(log.id) is None
