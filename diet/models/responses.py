"""
Typed Response Models for the Diet Insight Engine API

Provides strongly-typed Pydantic models for API endpoint responses,
replacing generic Dict[str, Any] with structured sub-models.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class HealthInsight(BaseModel):
    """A single health insight from symptom analysis."""

    category: str = ""
    description: str = ""
    severity: float = 0.0
    confidence: float = 0.0
    title: Optional[str] = None
    related_symptoms: List[str] = []
    suggested_actions: List[str] = []


class NutritionalDeficiencyInsight(BaseModel):
    """Insight about a potential nutritional deficiency."""

    nutrient: str = ""
    deficiency_likelihood: float = 0.0
    supporting_symptoms: List[str] = []
    recommended_intake: Optional[str] = None
    food_sources: List[str] = []
    priority: int = 1


class SymptomAnalysisResponse(BaseModel):
    """Typed response for symptom analysis results."""

    insights: List[HealthInsight] = []
    deficiencies: List[NutritionalDeficiencyInsight] = []
    patterns_detected: int = 0
    severity_score: float = 0.0
    confidence_score: float = 0.0


class RecommendationResponse(BaseModel):
    """Typed response for dietary recommendations."""

    dietary_recommendations: List[dict] = []
    supplement_recommendations: List[dict] = []
    lifestyle_recommendations: List[dict] = []
    priority_actions: List[str] = []
    overall_guidance: str = ""


class ProductResult(BaseModel):
    """Typed result for a product search hit."""

    id: str = ""
    name: str = ""
    brand: Optional[str] = None
    category: Optional[str] = None
    price: Optional[dict] = None
    quality_score: float = 0.0
