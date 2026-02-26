"""
Error Models for the Diet Insight Engine API

RFC 7807 Problem Details for HTTP APIs, providing a standardized
format for error responses across all endpoints.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details for HTTP APIs."""

    type: str = Field(description="URI reference identifying the problem type")
    title: str = Field(description="Short human-readable summary")
    status: int = Field(description="HTTP status code")
    detail: str = Field(
        description="Human-readable explanation specific to this occurrence"
    )
    correlation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    instance: Optional[str] = Field(
        default=None, description="URI reference for the specific occurrence"
    )
