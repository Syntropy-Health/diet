"""
Diet Insight Engine - Models Package

Core data models for the event-driven diet insight system.

Modules:
- events: Event schemas for SDO (Symptom-Diet Optimizer)
- alerts: Alert levels and notification models
- health_units: Standardized health product schemas for HSA
- store: Store configuration and integration schemas
- shared: Base models and enums
"""

# Import from alerts module
from .alerts import (
    AlertClassificationInput,
    AlertClassificationResult,
    AlertClassifier,
    AlertLevel,
    AlertNotification,
    AlertTriggeredEvent,
    NotificationChannel,
    UserNotificationPreferences,
)

# Import from events module
from .events import (
    BaseEvent,
    EventStatus,
    EventType,
    HealthInsight,
    InsightGeneratedEvent,
    NutritionalDeficiencyInsight,
    ProductMatchedEvent,
    ProductQuery,
    ProductQueryEvent,
    Recommendation,
    RecommendationGeneratedEvent,
    SymptomInput,
    SymptomReportedEvent,
)

# Import from health_units module
from .health_units import (
    AvailabilityStatus,
    DietaryTag,
    HealthCategory,
    MoneyAmount,
    NutrientValue,
    ProductSearchQuery,
    ProductSearchResult,
    RawProduct,
    ServingSize,
    StandardizedHealthUnit,
)

# Import from shared module
from .shared import FoodItem, IntermediateStep, PipelineState, SeverityLevel, StepStatus

# Import from store module
from .store import (
    StoreConfig,
    StoreInfo,
    StoreItemEvent,
    StoreSearchRequest,
    StoreSearchResponse,
    StoreStatus,
    StoreType,
)

__all__ = [
    # Event models
    "BaseEvent",
    "EventStatus",
    "EventType",
    "HealthInsight",
    "InsightGeneratedEvent",
    "NutritionalDeficiencyInsight",
    "ProductMatchedEvent",
    "ProductQuery",
    "ProductQueryEvent",
    "Recommendation",
    "RecommendationGeneratedEvent",
    "SymptomInput",
    "SymptomReportedEvent",
    # Alert models
    "AlertClassificationInput",
    "AlertClassificationResult",
    "AlertClassifier",
    "AlertLevel",
    "AlertNotification",
    "AlertTriggeredEvent",
    "NotificationChannel",
    "UserNotificationPreferences",
    # Health unit models
    "AvailabilityStatus",
    "DietaryTag",
    "HealthCategory",
    "MoneyAmount",
    "NutrientValue",
    "ProductSearchQuery",
    "ProductSearchResult",
    "RawProduct",
    "ServingSize",
    "StandardizedHealthUnit",
    # Store models
    "StoreConfig",
    "StoreInfo",
    "StoreItemEvent",
    "StoreSearchRequest",
    "StoreSearchResponse",
    "StoreStatus",
    "StoreType",
    # Shared models
    "FoodItem",
    "IntermediateStep",
    "PipelineState",
    "SeverityLevel",
    "StepStatus",
]
