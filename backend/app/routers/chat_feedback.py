"""
Chat Feedback Router

Provides endpoints for chat message like/dislike feedback.
Allows users to provide feedback on assistant responses.
"""

import hashlib
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.chat_feedback_models import ChatMessageFeedbackDB
from app.database.connection import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat/feedback", tags=["chat-feedback"])


# ==================== REQUEST/RESPONSE MODELS ====================


class FeedbackRequest(BaseModel):
    """Request model for submitting chat message feedback."""

    message_id: str = Field(..., description="ID of the message being rated")
    conversation_id: str | None = Field(None, description="Conversation ID")
    feedback: str = Field(..., pattern="^(like|dislike)$", description="Feedback type: 'like' or 'dislike'")
    reason: str | None = Field(None, max_length=500, description="Optional reason (typically for dislikes)")


class FeedbackResponse(BaseModel):
    """Response model for feedback operations."""

    message_id: str
    feedback: str | None
    reason: str | None = None
    submitted_at: str | None = None


class FeedbackDeleteResponse(BaseModel):
    """Response model for feedback deletion."""

    message_id: str
    deleted: bool


# ==================== HELPER FUNCTIONS ====================


def hash_session_token(token: str | None) -> str | None:
    """Hash session token for privacy-preserving storage."""
    if not token:
        return None
    return hashlib.sha256(token.encode()).hexdigest()


# ==================== ENDPOINTS ====================


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    x_chat_session: str | None = Header(None, alias="X-Chat-Session"),
    db: Session = Depends(get_session),
):
    """
    Submit like/dislike feedback for a chat message.

    - Creates new feedback if none exists
    - Updates existing feedback if found (toggle behavior)
    - One feedback per message per session (enforced by unique constraint)
    """
    try:
        session_hash = hash_session_token(x_chat_session)

        # Check for existing feedback
        existing = (
            db.query(ChatMessageFeedbackDB)
            .filter(
                ChatMessageFeedbackDB.message_id == request.message_id,
                ChatMessageFeedbackDB.session_token_hash == session_hash,
            )
            .first()
        )

        if existing:
            # Update existing feedback
            existing.feedback = request.feedback
            existing.reason = request.reason
            existing.conversation_id = request.conversation_id
            db.commit()
            db.refresh(existing)

            return FeedbackResponse(
                message_id=existing.message_id,
                feedback=existing.feedback,
                reason=existing.reason,
                submitted_at=existing.submitted_at.isoformat() if existing.submitted_at else None,
            )

        # Create new feedback
        feedback = ChatMessageFeedbackDB(
            message_id=request.message_id,
            conversation_id=request.conversation_id,
            feedback=request.feedback,
            reason=request.reason,
            session_token_hash=session_hash,
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)

        logger.info(f"Chat feedback submitted: message_id={request.message_id}, feedback={request.feedback}")

        return FeedbackResponse(
            message_id=feedback.message_id,
            feedback=feedback.feedback,
            reason=feedback.reason,
            submitted_at=feedback.submitted_at.isoformat() if feedback.submitted_at else None,
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feedback already exists for this message",
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting chat feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback",
        ) from e


@router.get("/{message_id}", response_model=FeedbackResponse)
async def get_feedback(
    message_id: str,
    x_chat_session: str | None = Header(None, alias="X-Chat-Session"),
    db: Session = Depends(get_session),
):
    """
    Get feedback for a specific message from the current session.

    Returns the user's feedback if it exists, otherwise returns null feedback.
    """
    try:
        session_hash = hash_session_token(x_chat_session)

        feedback = (
            db.query(ChatMessageFeedbackDB)
            .filter(
                ChatMessageFeedbackDB.message_id == message_id,
                ChatMessageFeedbackDB.session_token_hash == session_hash,
            )
            .first()
        )

        if not feedback:
            return FeedbackResponse(
                message_id=message_id,
                feedback=None,
            )

        return FeedbackResponse(
            message_id=feedback.message_id,
            feedback=feedback.feedback,
            reason=feedback.reason,
            submitted_at=feedback.submitted_at.isoformat() if feedback.submitted_at else None,
        )

    except Exception as e:
        logger.error(f"Error getting chat feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get feedback",
        ) from e


@router.delete("/{message_id}", response_model=FeedbackDeleteResponse)
async def delete_feedback(
    message_id: str,
    x_chat_session: str | None = Header(None, alias="X-Chat-Session"),
    db: Session = Depends(get_session),
):
    """
    Remove feedback for a message.

    Only the user who submitted the feedback can remove it (enforced by session).
    """
    try:
        session_hash = hash_session_token(x_chat_session)

        result = (
            db.query(ChatMessageFeedbackDB)
            .filter(
                ChatMessageFeedbackDB.message_id == message_id,
                ChatMessageFeedbackDB.session_token_hash == session_hash,
            )
            .delete()
        )
        db.commit()

        deleted = result > 0

        if deleted:
            logger.info(f"Chat feedback deleted: message_id={message_id}")

        return FeedbackDeleteResponse(
            message_id=message_id,
            deleted=deleted,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting chat feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete feedback",
        ) from e
