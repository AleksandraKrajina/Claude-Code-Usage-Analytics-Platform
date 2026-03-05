"""SQLAlchemy ORM models for Claude Code usage analytics."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Float, Integer, String, Index
from sqlalchemy.sql import func

from backend.database import Base


class TelemetryEvent(Base):
    """
    Stores parsed Claude Code telemetry events.
    
    Maps to the structure from generate_fake_data.py output,
    supporting api_request, tool_decision, tool_result, user_prompt, api_error events.
    """

    __tablename__ = "telemetry_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    session_id = Column(String(36), nullable=False, index=True)
    role = Column(String(64), nullable=True, index=True)  # user.practice: Backend Eng, etc.
    project_type = Column(String(64), nullable=True, index=True)  # same as practice
    event_type = Column(String(64), nullable=False, index=True)  # body: claude_code.api_request, etc.
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    model = Column(String(128), nullable=True)  # for api_request events
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cache_read_tokens = Column(Integer, default=0)
    cache_creation_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    duration_ms = Column(Integer, nullable=True)
    tool_name = Column(String(64), nullable=True)  # for tool_decision, tool_result
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_telemetry_timestamp_event", "timestamp", "event_type"),
        Index("ix_telemetry_user_timestamp", "user_id", "timestamp"),
    )

    @property
    def token_count(self) -> int:
        """Total tokens (input + output + cache_read + cache_creation)."""
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_creation_tokens
        )

    def __repr__(self) -> str:
        return f"<TelemetryEvent {self.event_type} user={self.user_id} ts={self.timestamp}>"


class Employee(Base):
    """
    Employee directory from generate_fake_data.py employees.csv.
    
    Links user emails to practice, level, and location.
    """

    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=True)
    practice = Column(String(64), nullable=True, index=True)
    level = Column(String(16), nullable=True)
    location = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Employee {self.email} {self.practice}>"
