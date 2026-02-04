"""
Database model for chat message feedback.
Stores like/dislike feedback for assistant messages in the chatbot.
"""

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from .models import Base


class ChatMessageFeedbackDB(Base):
    """Database model for chat message feedback (like/dislike)."""

    __tablename__ = "chat_message_feedback"

    id = Column(Integer, primary_key=True, index=True)

    # Message identification
    message_id = Column(String(255), nullable=False, index=True)
    conversation_id = Column(String(255), nullable=True, index=True)

    # Feedback: 'like' or 'dislike'
    feedback = Column(String(10), nullable=False)

    # Optional reason (typically for dislikes)
    reason = Column(Text, nullable=True)

    # Timestamps
    submitted_at = Column(DateTime, default=func.now(), nullable=False)

    # Session tracking for duplicate prevention (hashed for privacy)
    session_token_hash = Column(String(64), nullable=True, index=True)

    # Unique constraint: one feedback per message per session
    __table_args__ = (
        UniqueConstraint("message_id", "session_token_hash", name="uq_message_session_feedback"),
    )

    def __repr__(self) -> str:
        return f"<ChatMessageFeedback(id={self.id}, message_id={self.message_id}, feedback={self.feedback})>"
