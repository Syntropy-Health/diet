"""
Pattern Correlator

Correlates symptoms across time to identify patterns and trends
in user health data.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from diet.models.events import SymptomInput, SymptomReportedEvent

logger = logging.getLogger(__name__)


class SymptomPattern(BaseModel):
    """Represents a detected symptom pattern."""
    pattern_id: str = Field(..., description="Unique pattern identifier")
    pattern_type: str = Field(..., description="Type of pattern")
    symptoms_involved: List[str] = Field(default_factory=list)
    frequency: int = Field(default=1, description="Number of occurrences")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    description: str = Field(default="")
    severity_trend: str = Field(default="stable")  # improving, stable, worsening


class CorrelationResult(BaseModel):
    """Result of pattern correlation analysis."""
    patterns: List[SymptomPattern] = Field(default_factory=list)
    co_occurrences: Dict[str, List[str]] = Field(default_factory=dict)
    severity_trends: Dict[str, str] = Field(default_factory=dict)
    recurring_symptoms: List[str] = Field(default_factory=list)
    risk_indicators: List[str] = Field(default_factory=list)
    overall_trend: str = Field(default="stable")


class PatternCorrelator:
    """
    Correlates symptoms to identify patterns and trends.

    Features:
    - Co-occurrence analysis
    - Temporal pattern detection
    - Severity trend tracking
    - Risk indicator identification
    """

    PATTERN_TYPES = {
        "co_occurrence": "Symptoms that frequently appear together",
        "temporal": "Symptoms with time-based patterns",
        "cyclical": "Symptoms that recur periodically",
        "progressive": "Symptoms showing progression over time",
        "cluster": "Groups of related symptoms",
    }

    RISK_SYMPTOM_COMBINATIONS = [
        (["fatigue", "weight_loss", "appetite_loss"], "metabolic_concern"),
        (["headache", "vision_changes", "nausea"], "neurological_concern"),
        (["chest_pain", "shortness_of_breath", "fatigue"], "cardiovascular_concern"),
        (["joint_pain", "fatigue", "skin_rash"], "autoimmune_concern"),
        (["digestive_issues", "fatigue", "skin_problems"], "nutrient_absorption_concern"),
    ]

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.PatternCorrelator")
        self._symptom_history: Dict[str, List[Tuple[datetime, SymptomInput]]] = defaultdict(list)

    def correlate(
        self,
        current_event: SymptomReportedEvent,
        historical_events: Optional[List[SymptomReportedEvent]] = None,
    ) -> CorrelationResult:
        """
        Analyze symptoms for patterns and correlations.

        Args:
            current_event: Current symptom event
            historical_events: Optional list of historical events

        Returns:
            Correlation analysis results
        """
        self.logger.info(f"Correlating symptoms for user {current_event.user_id}")

        self._update_history(current_event.user_id, current_event)
        if historical_events:
            for event in historical_events:
                self._update_history(event.user_id, event)

        patterns = []

        co_occurrences = self._find_co_occurrences(current_event)
        if co_occurrences:
            for main_symptom, related in co_occurrences.items():
                patterns.append(SymptomPattern(
                    pattern_id=f"co_{main_symptom}_{current_event.timestamp.strftime('%Y%m%d')}",
                    pattern_type="co_occurrence",
                    symptoms_involved=[main_symptom] + related,
                    confidence=0.7,
                    description=f"{main_symptom} frequently co-occurs with {', '.join(related)}",
                ))

        recurring = self._find_recurring_symptoms(current_event.user_id)
        for symptom_name, count in recurring.items():
            if count >= 3:
                patterns.append(SymptomPattern(
                    pattern_id=f"recurring_{symptom_name}",
                    pattern_type="cyclical",
                    symptoms_involved=[symptom_name],
                    frequency=count,
                    confidence=min(0.5 + (count * 0.1), 0.95),
                    description=f"{symptom_name} has occurred {count} times",
                ))

        severity_trends = self._analyze_severity_trends(current_event.user_id)

        risk_indicators = self._check_risk_indicators(current_event)

        overall_trend = self._determine_overall_trend(severity_trends)

        return CorrelationResult(
            patterns=patterns,
            co_occurrences=co_occurrences,
            severity_trends=severity_trends,
            recurring_symptoms=list(recurring.keys()),
            risk_indicators=risk_indicators,
            overall_trend=overall_trend,
        )

    def _update_history(
        self,
        user_id: str,
        event: SymptomReportedEvent,
    ) -> None:
        """Update symptom history for a user."""
        for symptom in event.symptoms:
            key = f"{user_id}:{symptom.name.lower()}"
            self._symptom_history[key].append((event.timestamp, symptom))

            self._symptom_history[key] = [
                (ts, s) for ts, s in self._symptom_history[key]
                if ts > datetime.utcnow() - timedelta(days=90)
            ][-50:]

    def _find_co_occurrences(
        self,
        event: SymptomReportedEvent,
    ) -> Dict[str, List[str]]:
        """Find symptoms that frequently occur together."""
        co_occurrences = {}
        symptom_names = [s.name.lower() for s in event.symptoms]

        if len(symptom_names) >= 2:
            for i, main in enumerate(symptom_names):
                related = [s for j, s in enumerate(symptom_names) if i != j]
                if related:
                    co_occurrences[main] = related

        return co_occurrences

    def _find_recurring_symptoms(
        self,
        user_id: str,
    ) -> Dict[str, int]:
        """Find symptoms that recur for a user."""
        recurring = defaultdict(int)

        for key, history in self._symptom_history.items():
            if key.startswith(f"{user_id}:"):
                symptom_name = key.split(":", 1)[1]
                recurring[symptom_name] = len(history)

        return {k: v for k, v in recurring.items() if v >= 2}

    def _analyze_severity_trends(
        self,
        user_id: str,
    ) -> Dict[str, str]:
        """Analyze severity trends for user symptoms."""
        trends = {}

        for key, history in self._symptom_history.items():
            if key.startswith(f"{user_id}:") and len(history) >= 2:
                symptom_name = key.split(":", 1)[1]

                sorted_history = sorted(history, key=lambda x: x[0])

                recent = sorted_history[-3:]
                older = sorted_history[:-3] if len(sorted_history) > 3 else []

                recent_avg = sum(s.severity for _, s in recent) / len(recent)

                if older:
                    older_avg = sum(s.severity for _, s in older) / len(older)
                    diff = recent_avg - older_avg

                    if diff > 0.15:
                        trends[symptom_name] = "worsening"
                    elif diff < -0.15:
                        trends[symptom_name] = "improving"
                    else:
                        trends[symptom_name] = "stable"
                else:
                    trends[symptom_name] = "stable"

        return trends

    def _check_risk_indicators(
        self,
        event: SymptomReportedEvent,
    ) -> List[str]:
        """Check for risk indicator symptom combinations."""
        risk_indicators = []
        symptom_names = {s.name.lower() for s in event.symptoms}

        for risk_symptoms, risk_name in self.RISK_SYMPTOM_COMBINATIONS:
            matches = sum(1 for rs in risk_symptoms if any(rs in sn for sn in symptom_names))
            if matches >= 2:
                risk_indicators.append(risk_name)

        high_severity = [s for s in event.symptoms if s.severity >= 0.8]
        if high_severity:
            risk_indicators.append("high_severity_symptom")

        if len(event.symptoms) >= 5:
            risk_indicators.append("symptom_cluster")

        return risk_indicators

    def _determine_overall_trend(
        self,
        severity_trends: Dict[str, str],
    ) -> str:
        """Determine overall health trend from individual trends."""
        if not severity_trends:
            return "stable"

        worsening = sum(1 for t in severity_trends.values() if t == "worsening")
        improving = sum(1 for t in severity_trends.values() if t == "improving")
        total = len(severity_trends)

        if worsening > total * 0.5:
            return "worsening"
        elif improving > total * 0.5:
            return "improving"
        else:
            return "stable"

    def clear_history(self, user_id: Optional[str] = None) -> None:
        """Clear symptom history, optionally for a specific user."""
        if user_id:
            keys_to_remove = [k for k in self._symptom_history if k.startswith(f"{user_id}:")]
            for key in keys_to_remove:
                del self._symptom_history[key]
        else:
            self._symptom_history.clear()
