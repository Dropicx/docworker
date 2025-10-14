"""
AI Log Interaction Repository

Handles database operations for AI interaction logs and cost tracking.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.database.unified_models import AILogInteractionDB
from app.repositories.base_repository import BaseRepository


class AILogInteractionRepository(BaseRepository[AILogInteractionDB]):
    """
    Repository for AI Log Interaction operations.

    Provides specialized queries for AI interaction logs, cost analytics,
    and usage statistics beyond basic CRUD operations.
    """

    def __init__(self, db: Session):
        """
        Initialize AI log interaction repository.

        Args:
            db: Database session
        """
        super().__init__(db, AILogInteractionDB)

    def get_by_processing_id(self, processing_id: str) -> list[AILogInteractionDB]:
        """
        Get all AI logs for a specific processing ID, ordered by creation time.

        Args:
            processing_id: Processing ID to filter by

        Returns:
            List of AI interaction logs for the processing, ordered chronologically
        """
        return (
            self.db.query(self.model)
            .filter_by(processing_id=processing_id)
            .order_by(self.model.created_at)
            .all()
        )

    def get_by_date_range(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> list[AILogInteractionDB]:
        """
        Get AI logs within a date range.

        Args:
            start_date: Start date (inclusive), None for no lower bound
            end_date: End date (inclusive), None for no upper bound

        Returns:
            List of AI interaction logs within the date range
        """
        query = self.db.query(self.model)

        if start_date:
            query = query.filter(self.model.created_at >= start_date)
        if end_date:
            query = query.filter(self.model.created_at <= end_date)

        return query.all()

    def get_filtered(
        self,
        processing_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        document_type: str | None = None,
    ) -> list[AILogInteractionDB]:
        """
        Get AI logs with multiple filters.

        Args:
            processing_id: Optional processing ID filter
            start_date: Optional start date filter (inclusive)
            end_date: Optional end date filter (inclusive)
            document_type: Optional document type filter

        Returns:
            List of filtered AI interaction logs
        """
        query = self.db.query(self.model)

        if processing_id:
            query = query.filter(self.model.processing_id == processing_id)
        if start_date:
            query = query.filter(self.model.created_at >= start_date)
        if end_date:
            query = query.filter(self.model.created_at <= end_date)
        if document_type:
            query = query.filter(self.model.document_type == document_type)

        return query.all()

    def get_by_step_name(self, step_name: str) -> list[AILogInteractionDB]:
        """
        Get all AI logs for a specific pipeline step.

        Args:
            step_name: Pipeline step name

        Returns:
            List of AI interaction logs for the step
        """
        return self.db.query(self.model).filter_by(step_name=step_name).all()

    def get_by_model(self, model_name: str) -> list[AILogInteractionDB]:
        """
        Get all AI logs for a specific model.

        Args:
            model_name: Model name to filter by

        Returns:
            List of AI interaction logs for the model
        """
        return self.db.query(self.model).filter_by(model_name=model_name).all()

    def get_by_document_type(self, document_type: str) -> list[AILogInteractionDB]:
        """
        Get all AI logs for a specific document type.

        Args:
            document_type: Document type to filter by

        Returns:
            List of AI interaction logs for the document type
        """
        return self.db.query(self.model).filter_by(document_type=document_type).all()

    def get_total_cost(
        self,
        processing_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> float:
        """
        Calculate total cost for filtered logs.

        Args:
            processing_id: Optional processing ID filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Total cost in USD
        """
        logs = self.get_filtered(processing_id, start_date, end_date)
        return sum(log.total_cost_usd or 0 for log in logs)

    def get_total_tokens(
        self,
        processing_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """
        Calculate total tokens for filtered logs.

        Args:
            processing_id: Optional processing ID filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Total token count
        """
        logs = self.get_filtered(processing_id, start_date, end_date)
        return sum(log.total_tokens or 0 for log in logs)

    def count_calls(
        self,
        processing_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """
        Count API calls for filtered logs.

        Args:
            processing_id: Optional processing ID filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Count of AI API calls
        """
        logs = self.get_filtered(processing_id, start_date, end_date)
        return len(logs)

    def delete_old_logs(self, older_than: datetime) -> int:
        """
        Delete logs older than specified date.

        Args:
            older_than: Delete logs older than this timestamp

        Returns:
            Number of deleted records
        """
        try:
            deleted = self.db.query(self.model).filter(self.model.created_at < older_than).delete()
            self.db.commit()
            return deleted
        except Exception:
            self.db.rollback()
            return 0
