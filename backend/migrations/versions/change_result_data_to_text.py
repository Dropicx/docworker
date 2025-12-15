"""Change result_data from JSON to Text for encrypted storage

Revision ID: change_result_data_to_text
Revises: encrypt_existing_document_content
Create Date: 2025-12-15 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'change_result_data_to_text'
down_revision: Union[str, None] = 'encrypt_existing_document_content'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Change result_data column from JSON to Text type.
    
    This is necessary because we now store encrypted JSON strings in this column,
    not actual JSON objects. PostgreSQL JSON type automatically deserializes strings,
    which breaks our encryption flow.
    """
    # Use USING clause to convert JSON to Text
    # This will convert any existing JSON data to its string representation
    op.execute(
        """
        ALTER TABLE pipeline_jobs 
        ALTER COLUMN result_data TYPE TEXT 
        USING result_data::text
        """
    )


def downgrade() -> None:
    """
    Revert result_data column from Text back to JSON type.
    """
    # Convert Text back to JSON (this may fail if data is encrypted)
    op.execute(
        """
        ALTER TABLE pipeline_jobs 
        ALTER COLUMN result_data TYPE JSON 
        USING result_data::json
        """
    )

