"""
Shared Base Schema

This module defines common data structures, enums, and base classes that are
shared between the Diet Insight Engine and Amazon Store Agent modules.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NutrientDeficiency(str, Enum):
    """Common nutrient deficiencies that can be addressed through supplements."""

    # Vitamins
    VITAMIN_D = "vitamin_d"
    VITAMIN_B12 = "vitamin_b12"
    VITAMIN_C = "vitamin_c"
    VITAMIN_A = "vitamin_a"
    VITAMIN_E = "vitamin_e"
    VITAMIN_K = "vitamin_k"
    FOLATE = "folate"
    THIAMINE = "thiamine"
    RIBOFLAVIN = "riboflavin"
    NIACIN = "niacin"
    VITAMIN_B6 = "vitamin_b6"
    BIOTIN = "biotin"
    PANTOTHENIC_ACID = "pantothenic_acid"

    # Minerals
    IRON = "iron"
    CALCIUM = "calcium"
    MAGNESIUM = "magnesium"
    ZINC = "zinc"
    POTASSIUM = "potassium"
    SELENIUM = "selenium"
    IODINE = "iodine"
    CHROMIUM = "chromium"
    COPPER = "copper"
    MANGANESE = "manganese"

    # Essential Fatty Acids
    OMEGA_3 = "omega_3"
    OMEGA_6 = "omega_6"

    # Other Important Nutrients
    FIBER = "fiber"
    PROTEIN = "protein"
    PROBIOTICS = "probiotics"


class SeverityLevel(str, Enum):
    """Severity levels for symptoms and conditions."""

    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


class HealthStatus(str, Enum):
    """General health status indicators."""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    """Confidence level categories."""

    VERY_HIGH = "very_high"  # 0.9-1.0
    HIGH = "high"  # 0.7-0.89
    MEDIUM = "medium"  # 0.5-0.69
    LOW = "low"  # 0.3-0.49
    VERY_LOW = "very_low"  # 0.0-0.29


def confidence_score_to_level(score: float) -> ConfidenceLevel:
    """Convert a numeric confidence score to a confidence level."""
    if score >= 0.9:
        return ConfidenceLevel.VERY_HIGH
    elif score >= 0.7:
        return ConfidenceLevel.HIGH
    elif score >= 0.5:
        return ConfidenceLevel.MEDIUM
    elif score >= 0.3:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.VERY_LOW


class MealType(str, Enum):
    """Types of meals for food tracking."""

    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    BEVERAGE = "beverage"
    OTHER = "other"


class FoodItem(BaseModel):
    """Represents a consumed food item with nutritional information."""

    name: str = Field(..., description="Name of the food item")
    meal_type: Optional[MealType] = Field(None, description="Type of meal")
    calories: Optional[int] = Field(None, description="Calories consumed")
    serving_size: Optional[str] = Field(None, description="Serving size description")
    nutrients: Dict[str, float] = Field(
        default_factory=dict, description="Nutrient content (e.g., 'protein': 20.5)"
    )
    preparation_method: Optional[str] = Field(None, description="How the food was prepared")
    notes: Optional[str] = Field(None, description="Additional notes about the food item")


class PipelineStage(str, Enum):
    """Common pipeline stage identifiers."""

    INPUT_VALIDATION = "input_validation"
    DATA_EXTRACTION = "data_extraction"
    DATA_PROCESSING = "data_processing"
    ANALYSIS = "analysis"
    RECOMMENDATION = "recommendation"
    OUTPUT_GENERATION = "output_generation"


class StepStatus(str, Enum):
    """Status of a pipeline step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    SKIPPED = "skipped"


class IntermediateStep(BaseModel):
    """Represents an intermediate step in a pipeline process."""

    step_name: str = Field(..., description="Name of the step")
    status: StepStatus = Field(default=StepStatus.PENDING, description="Current status of the step")
    start_time: Optional[datetime] = Field(default=None, description="When the step started")
    end_time: Optional[datetime] = Field(default=None, description="When the step completed")
    input_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Input data for the step"
    )
    output_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Output data from the step"
    )
    error: Optional[str] = Field(default=None, description="Error message if step failed")
    duration_seconds: Optional[float] = Field(default=None, description="Step duration in seconds")

    def complete(self, output_data: Optional[Dict[str, Any]] = None):
        """Mark step as completed."""
        self.status = StepStatus.COMPLETED
        self.end_time = datetime.now()
        if output_data:
            self.output_data = output_data
        if self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()

    def fail(self, error: str):
        """Mark step as failed."""
        self.status = StepStatus.ERROR
        self.end_time = datetime.now()
        self.error = error
        if self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()


class PipelineState(BaseModel):
    """Base state for pipeline processes."""

    process_id: Optional[str] = Field(default=None, description="Unique identifier for the process")
    user_id: Optional[str] = Field(default=None, description="User identifier")
    intermediate_steps: List[IntermediateStep] = Field(
        default_factory=list, description="Steps in the pipeline"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Shared context between steps"
    )
    error: Optional[str] = Field(default=None, description="Global error message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def add_step(
        self, step_name: str, input_data: Optional[Dict[str, Any]] = None
    ) -> IntermediateStep:
        """Add a new step to the pipeline."""
        step = IntermediateStep(
            step_name=step_name,
            status=StepStatus.RUNNING,
            start_time=datetime.now(),
            input_data=input_data,
        )
        self.intermediate_steps.append(step)
        return step
