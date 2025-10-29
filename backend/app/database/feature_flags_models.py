"""
Database models for feature flags and dynamic configuration.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class FeatureFlag(Base):
    """
    Feature flag for runtime feature toggles.

    Allows enabling/disabling features without deployment.
    Supports gradual rollout with rollout_percentage.
    """

    __tablename__ = "feature_flags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    enabled = Column(Boolean, default=False, nullable=False)
    description = Column(Text)
    rollout_percentage = Column(Integer, default=0, nullable=False)  # 0-100
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self):
        return f"<FeatureFlag(name='{self.name}', enabled={self.enabled}, rollout={self.rollout_percentage}%)>"


class Configuration(Base):
    """
    Dynamic configuration stored in database.

    Allows updating configuration without redeployment.
    Supports JSONB for complex configuration values.
    """

    __tablename__ = "configuration"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)  # Use JSONB in PostgreSQL
    description = Column(Text)
    is_secret = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_by = Column(String(100))

    def __repr__(self):
        value_display = "***SECRET***" if self.is_secret else str(self.value)[:50]
        return f"<Configuration(key='{self.key}', value='{value_display}')>"
