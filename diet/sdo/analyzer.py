"""
Symptom Analyzer

LLM-powered symptom analysis component that processes user-reported symptoms
and generates health insights with confidence scores.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from diet.models.events import (
    HealthInsight,
    NutritionalDeficiencyInsight,
    SymptomInput,
    SymptomReportedEvent,
)
from diet.utils.config_manager import get_config_manager
from diet.utils.llm_service import execute_llm_step

logger = logging.getLogger(__name__)


class SymptomAnalysisOutput(BaseModel):
    """Output schema for LLM symptom analysis."""
    insights: List[HealthInsight] = Field(default_factory=list)
    deficiencies: List[NutritionalDeficiencyInsight] = Field(default_factory=list)
    severity_score: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0)
    patterns_detected: List[str] = Field(default_factory=list)
    urgency_indicators: List[str] = Field(default_factory=list)
    reasoning: str = Field(default="")


class SymptomAnalyzer:
    """
    LLM-powered symptom analyzer.

    Processes user-reported symptoms and generates:
    - Health insights with confidence scores
    - Potential nutritional deficiency identifications
    - Severity assessments
    - Pattern recognition across symptoms
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.SymptomAnalyzer")
        self._config_manager = None

    @property
    def config_manager(self):
        if self._config_manager is None:
            self._config_manager = get_config_manager()
        return self._config_manager

    async def analyze(
        self,
        event: SymptomReportedEvent,
        historical_symptoms: Optional[List[SymptomInput]] = None,
    ) -> SymptomAnalysisOutput:
        """
        Analyze symptoms and generate health insights.

        Args:
            event: Symptom reported event with user symptoms
            historical_symptoms: Optional historical symptom data for context

        Returns:
            Analysis output with insights and deficiencies
        """
        self.logger.info(f"Analyzing {len(event.symptoms)} symptoms for user {event.user_id}")

        try:
            result = await self._analyze_with_llm(event, historical_symptoms)
            if result:
                self.logger.info(
                    f"Analysis complete: {len(result.insights)} insights, "
                    f"{len(result.deficiencies)} deficiencies"
                )
                return result
        except Exception as e:
            self.logger.error(f"LLM analysis failed: {e}")

        return self._fallback_analysis(event)

    async def _analyze_with_llm(
        self,
        event: SymptomReportedEvent,
        historical_symptoms: Optional[List[SymptomInput]] = None,
    ) -> Optional[SymptomAnalysisOutput]:
        """Perform LLM-based symptom analysis."""
        symptoms_text = self._format_symptoms(event.symptoms)
        context_text = self._format_context(event)
        historical_text = self._format_historical(historical_symptoms) if historical_symptoms else "No historical data"

        prompt_template = self.config_manager.get_prompt_template(
            "sdo", "symptom_analysis"
        )

        if not prompt_template:
            prompt_template = self._get_default_prompt()

        input_variables = {
            "user_id": event.user_id,
            "symptoms": symptoms_text,
            "context": context_text,
            "historical": historical_text,
            "timestamp": event.timestamp.isoformat(),
        }

        parser = PydanticOutputParser(pydantic_object=SymptomAnalysisOutput)

        result = await execute_llm_step(
            state=None,
            step_name="sdo_symptom_analysis",
            prompt_template=prompt_template,
            input_variables=input_variables,
            parser=parser,
            project_name="diet-insight-engine-sdo",
        )

        if result and isinstance(result, SymptomAnalysisOutput):
            return result

        return None

    def _fallback_analysis(
        self,
        event: SymptomReportedEvent,
    ) -> SymptomAnalysisOutput:
        """Generate fallback analysis when LLM is unavailable."""
        self.logger.warning("Using fallback symptom analysis")

        insights = []
        deficiencies = []
        patterns = []
        urgency = []

        severity_sum = sum(s.severity for s in event.symptoms)
        avg_severity = severity_sum / len(event.symptoms) if event.symptoms else 0.5

        symptom_names = [s.name.lower() for s in event.symptoms]

        fatigue_keywords = ["fatigue", "tired", "exhausted", "low energy"]
        if any(kw in " ".join(symptom_names) for kw in fatigue_keywords):
            deficiencies.append(NutritionalDeficiencyInsight(
                nutrient="iron",
                deficiency_likelihood=0.6,
                supporting_symptoms=["fatigue"],
                recommended_intake="18mg daily for women, 8mg for men",
                food_sources=["red meat", "spinach", "lentils", "fortified cereals"],
                priority=2,
            ))
            deficiencies.append(NutritionalDeficiencyInsight(
                nutrient="vitamin_b12",
                deficiency_likelihood=0.5,
                supporting_symptoms=["fatigue", "low energy"],
                recommended_intake="2.4mcg daily",
                food_sources=["eggs", "dairy", "fortified foods", "nutritional yeast"],
                priority=2,
            ))
            patterns.append("fatigue_pattern")

        mood_keywords = ["mood", "anxiety", "stress", "depression", "irritable"]
        if any(kw in " ".join(symptom_names) for kw in mood_keywords):
            deficiencies.append(NutritionalDeficiencyInsight(
                nutrient="magnesium",
                deficiency_likelihood=0.55,
                supporting_symptoms=["mood changes", "stress"],
                recommended_intake="400mg daily",
                food_sources=["dark chocolate", "avocados", "nuts", "leafy greens"],
                priority=2,
            ))
            deficiencies.append(NutritionalDeficiencyInsight(
                nutrient="vitamin_d",
                deficiency_likelihood=0.5,
                supporting_symptoms=["mood", "fatigue"],
                recommended_intake="600-800 IU daily",
                food_sources=["fatty fish", "fortified milk", "egg yolks", "sunlight"],
                priority=2,
            ))
            patterns.append("mood_pattern")

        if avg_severity > 0.7:
            urgency.append("elevated_severity")

        if len(event.symptoms) >= 3:
            patterns.append("multiple_symptoms")

        for symptom in event.symptoms:
            insights.append(HealthInsight(
                category="symptom_noted",
                title=f"Symptom: {symptom.name}",
                description=f"Reported symptom with severity {symptom.severity:.1f}",
                confidence=0.7,
                severity=symptom.severity,
                related_symptoms=[symptom.name],
                suggested_actions=["Monitor symptom progression", "Consider dietary factors"],
            ))

        return SymptomAnalysisOutput(
            insights=insights,
            deficiencies=deficiencies,
            severity_score=avg_severity,
            confidence_score=0.6,
            patterns_detected=patterns,
            urgency_indicators=urgency,
            reasoning="Fallback rule-based analysis due to LLM unavailability",
        )

    def _format_symptoms(self, symptoms: List[SymptomInput]) -> str:
        """Format symptoms for LLM prompt."""
        lines = []
        for i, s in enumerate(symptoms, 1):
            line = f"{i}. {s.name} (severity: {s.severity:.1f})"
            if s.duration_hours:
                line += f", duration: {s.duration_hours}h"
            if s.frequency:
                line += f", frequency: {s.frequency}"
            if s.notes:
                line += f", notes: {s.notes}"
            lines.append(line)
        return "\n".join(lines)

    def _format_context(self, event: SymptomReportedEvent) -> str:
        """Format event context for LLM prompt."""
        parts = []
        if event.recent_foods:
            parts.append(f"Recent foods: {', '.join(event.recent_foods)}")
        if event.sleep_hours is not None:
            parts.append(f"Sleep: {event.sleep_hours} hours")
        if event.stress_level is not None:
            parts.append(f"Stress level: {event.stress_level}/10")
        if event.exercise_minutes is not None:
            parts.append(f"Exercise: {event.exercise_minutes} minutes")
        return " | ".join(parts) if parts else "No additional context"

    def _format_historical(self, symptoms: List[SymptomInput]) -> str:
        """Format historical symptoms for LLM prompt."""
        if not symptoms:
            return "No historical data"
        return f"Previous symptoms ({len(symptoms)} total): " + ", ".join(s.name for s in symptoms[:10])

    def _get_default_prompt(self) -> str:
        """Get default prompt template for symptom analysis."""
        return """You are a health analysis AI assistant. Analyze the following symptoms and provide insights.

User ID: {user_id}
Timestamp: {timestamp}

Reported Symptoms:
{symptoms}

Context:
{context}

Historical Data:
{historical}

Analyze these symptoms and provide:
1. Health insights with confidence scores
2. Potential nutritional deficiencies
3. Overall severity assessment
4. Pattern recognition
5. Any urgency indicators

Respond in JSON format matching the SymptomAnalysisOutput schema.
{format_instructions}"""
