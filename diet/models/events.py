"""
Event Models for the Symptom-Diet Optimizer (SDO)

This module defines event schemas for the event-driven architecture,
enabling asynchronous symptom processing and real-time notifications.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events in the SDO system."""
    SYMPTOM_REPORTED = "symptom_reported"
    INSIGHT_GENERATED = "insight_generated"
    ALERT_TRIGGERED = "alert_triggered"
    PRODUCT_QUERY = "product_query"
    PRODUCT_MATCHED = "product_matched"
    RECOMMENDATION_GENERATED = "recommendation_generated"


class EventStatus(str, Enum):
    """Status of event processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class BaseEvent(BaseModel):
    """Base class for all events in the SDO system."""
    event_id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    event_type: EventType = Field(..., description="Type of event")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event creation time")
    user_id: str = Field(..., description="User identifier")
    correlation_id: Optional[UUID] = Field(default=None, description="ID to correlate related events")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional event metadata")

    class Config:
        use_enum_values = True


class SymptomInput(BaseModel):
    """Input model for a single symptom report."""
    name: str = Field(..., description="Symptom name or description")
    severity: float = Field(default=0.5, ge=0.0, le=1.0, description="Severity score 0-1")
    duration_hours: Optional[float] = Field(default=None, description="Duration in hours")
    frequency: Optional[str] = Field(default=None, description="Frequency description")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    body_location: Optional[str] = Field(default=None, description="Body location if applicable")


class SymptomReportedEvent(BaseEvent):
    """Event emitted when a user reports symptoms."""
    event_type: EventType = Field(default=EventType.SYMPTOM_REPORTED)
    symptoms: List[SymptomInput] = Field(..., description="List of reported symptoms")
    context: Dict[str, Any] = Field(default_factory=dict, description="Contextual information")
    source: str = Field(default="user_input", description="Source of symptom report")

    # Optional health context
    recent_foods: Optional[List[str]] = Field(default=None, description="Recently consumed foods")
    sleep_hours: Optional[float] = Field(default=None, description="Recent sleep hours")
    stress_level: Optional[int] = Field(default=None, ge=1, le=10, description="Stress level 1-10")
    exercise_minutes: Optional[int] = Field(default=None, description="Recent exercise minutes")


class HealthInsight(BaseModel):
    """A single health insight derived from symptom analysis."""
    insight_id: UUID = Field(default_factory=uuid4)
    category: str = Field(..., description="Insight category")
    title: str = Field(..., description="Short insight title")
    description: str = Field(..., description="Detailed insight description")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    severity: float = Field(default=0.5, ge=0.0, le=1.0, description="Severity indicator")
    related_symptoms: List[str] = Field(default_factory=list, description="Related symptom names")
    suggested_actions: List[str] = Field(default_factory=list, description="Suggested actions")


class NutritionalDeficiencyInsight(BaseModel):
    """Insight about a potential nutritional deficiency."""
    nutrient: str = Field(..., description="Nutrient name")
    deficiency_likelihood: float = Field(..., ge=0.0, le=1.0, description="Likelihood score")
    supporting_symptoms: List[str] = Field(default_factory=list, description="Supporting symptoms")
    recommended_intake: Optional[str] = Field(default=None, description="Recommended daily intake")
    food_sources: List[str] = Field(default_factory=list, description="Food sources")
    priority: int = Field(default=1, ge=1, le=5, description="Priority level 1-5")


class InsightGeneratedEvent(BaseEvent):
    """Event emitted when insights are generated from symptom analysis."""
    event_type: EventType = Field(default=EventType.INSIGHT_GENERATED)
    source_event_id: UUID = Field(..., description="ID of triggering symptom event")
    insights: List[HealthInsight] = Field(default_factory=list, description="Generated insights")
    deficiencies: List[NutritionalDeficiencyInsight] = Field(
        default_factory=list, description="Identified deficiencies"
    )
    analysis_confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Overall confidence")
    patterns_detected: List[str] = Field(default_factory=list, description="Detected patterns")


class ProductQuery(BaseModel):
    """Query model for product search."""
    query_id: UUID = Field(default_factory=uuid4)
    search_terms: List[str] = Field(..., description="Search terms")
    category_filter: Optional[str] = Field(default=None, description="Category filter")
    nutrient_requirements: Dict[str, float] = Field(
        default_factory=dict, description="Required nutrients"
    )
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results")
    price_range: Optional[tuple] = Field(default=None, description="Price range (min, max)")


class ProductQueryEvent(BaseEvent):
    """Event emitted when product recommendations are needed."""
    event_type: EventType = Field(default=EventType.PRODUCT_QUERY)
    source_event_id: UUID = Field(..., description="ID of triggering insight event")
    query: ProductQuery = Field(..., description="Product query details")
    target_deficiencies: List[str] = Field(default_factory=list, description="Deficiencies to address")


class ProductMatchedEvent(BaseEvent):
    """Event emitted when products are matched to a query."""
    event_type: EventType = Field(default=EventType.PRODUCT_MATCHED)
    source_event_id: UUID = Field(..., description="ID of triggering query event")
    matched_products: List[Dict[str, Any]] = Field(
        default_factory=list, description="Matched product data"
    )
    match_scores: Dict[str, float] = Field(
        default_factory=dict, description="Match scores by product ID"
    )


class Recommendation(BaseModel):
    """A single actionable recommendation."""
    recommendation_id: UUID = Field(default_factory=uuid4)
    type: str = Field(..., description="Type: dietary, supplement, lifestyle")
    title: str = Field(..., description="Short title")
    description: str = Field(..., description="Detailed description")
    priority: int = Field(default=1, ge=1, le=5, description="Priority 1-5")
    evidence_basis: str = Field(default="symptom_analysis", description="Evidence basis")
    product_ids: List[str] = Field(default_factory=list, description="Related product IDs")


class RecommendationGeneratedEvent(BaseEvent):
    """Event emitted when recommendations are generated."""
    event_type: EventType = Field(default=EventType.RECOMMENDATION_GENERATED)
    source_event_id: UUID = Field(..., description="ID of triggering event")
    recommendations: List[Recommendation] = Field(
        default_factory=list, description="Generated recommendations"
    )
