"""
SDO Engine - Symptom-Diet Optimizer Core Engine

The main orchestrator that coordinates symptom analysis, pattern correlation,
recommendation generation, and alert classification.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from diet.models.alerts import (
    AlertClassificationResult,
    AlertNotification,
    AlertTriggeredEvent,
)
from diet.models.events import (
    EventType,
    InsightGeneratedEvent,
    SymptomInput,
    SymptomReportedEvent,
)
from diet.sdo.alert_classifier import SDOAlertClassifier
from diet.sdo.analyzer import SymptomAnalysisOutput, SymptomAnalyzer
from diet.sdo.correlator import CorrelationResult, PatternCorrelator
from diet.sdo.recommender import DietRecommender, RecommendationResult

logger = logging.getLogger(__name__)


class SDOProcessingResult(BaseModel):
    """Complete result of SDO processing."""
    process_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = Field(...)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    analysis: Optional[SymptomAnalysisOutput] = None
    correlation: Optional[CorrelationResult] = None
    recommendations: Optional[RecommendationResult] = None
    classification: Optional[AlertClassificationResult] = None
    notification: Optional[AlertNotification] = None

    processing_time_ms: float = Field(default=0.0)
    success: bool = Field(default=True)
    error: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class SDOEngine:
    """
    Symptom-Diet Optimizer Engine.

    Orchestrates the complete symptom processing pipeline:
    1. Symptom Analysis (LLM-powered)
    2. Pattern Correlation
    3. Recommendation Generation
    4. Alert Classification
    5. Notification Creation

    Usage:
        engine = SDOEngine()
        await engine.initialize()
        result = await engine.process_symptoms(event)
        await engine.shutdown()
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.SDOEngine")
        self._analyzer = SymptomAnalyzer()
        self._correlator = PatternCorrelator()
        self._recommender = DietRecommender()
        self._classifier = SDOAlertClassifier()
        self._initialized = False
        self._user_history: Dict[str, List[SymptomReportedEvent]] = {}

    async def initialize(self) -> None:
        """Initialize the SDO engine and its components."""
        if self._initialized:
            return

        self.logger.info("Initializing SDO Engine")
        self._initialized = True
        self.logger.info("SDO Engine initialized")

    async def shutdown(self) -> None:
        """Shutdown the SDO engine and clean up resources."""
        self.logger.info("Shutting down SDO Engine")
        self._correlator.clear_history()
        self._user_history.clear()
        self._initialized = False
        self.logger.info("SDO Engine shutdown complete")

    async def process_symptoms(
        self,
        event: SymptomReportedEvent,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> SDOProcessingResult:
        """
        Process a symptom reported event through the full pipeline.

        Args:
            event: Symptom reported event
            user_preferences: Optional user preferences

        Returns:
            Complete processing result
        """
        start_time = datetime.utcnow()

        result = SDOProcessingResult(
            user_id=event.user_id,
        )

        try:
            if not self._initialized:
                await self.initialize()

            self._store_event(event)
            historical = self._get_historical_symptoms(event.user_id)

            self.logger.info(f"Processing {len(event.symptoms)} symptoms for user {event.user_id}")

            analysis = await self._analyzer.analyze(event, historical)
            result.analysis = analysis

            historical_events = self._user_history.get(event.user_id, [])
            correlation = self._correlator.correlate(event, historical_events[:-1] if len(historical_events) > 1 else None)
            result.correlation = correlation

            recommendations = await self._recommender.generate_recommendations(
                analysis, user_preferences
            )
            result.recommendations = recommendations

            classification = self._classifier.classify(analysis, correlation, recommendations)
            result.classification = classification

            notification = self._classifier.create_notification(
                event.user_id, classification, analysis, recommendations
            )
            result.notification = notification

            result.success = True

        except Exception as e:
            self.logger.error(f"SDO processing failed: {e}", exc_info=True)
            result.success = False
            result.error = str(e)

        end_time = datetime.utcnow()
        result.processing_time_ms = (end_time - start_time).total_seconds() * 1000

        self.logger.info(
            f"SDO processing complete for user {event.user_id}: "
            f"success={result.success}, time={result.processing_time_ms:.1f}ms"
        )

        return result

    async def process_batch(
        self,
        events: List[SymptomReportedEvent],
        user_preferences: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[SDOProcessingResult]:
        """
        Process multiple symptom events in batch.

        Args:
            events: List of symptom events
            user_preferences: Optional dict of user_id -> preferences

        Returns:
            List of processing results
        """
        self.logger.info(f"Processing batch of {len(events)} events")

        tasks = []
        for event in events:
            prefs = user_preferences.get(event.user_id) if user_preferences else None
            tasks.append(self.process_symptoms(event, prefs))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(SDOProcessingResult(
                    user_id=events[i].user_id,
                    success=False,
                    error=str(result),
                ))
            else:
                processed_results.append(result)

        success_count = sum(1 for r in processed_results if r.success)
        self.logger.info(f"Batch processing complete: {success_count}/{len(events)} successful")

        return processed_results

    def create_insight_event(
        self,
        source_event: SymptomReportedEvent,
        result: SDOProcessingResult,
    ) -> Optional[InsightGeneratedEvent]:
        """Create an InsightGeneratedEvent from processing result."""
        if not result.success or not result.analysis:
            return None

        return InsightGeneratedEvent(
            user_id=source_event.user_id,
            source_event_id=source_event.event_id,
            correlation_id=source_event.correlation_id or source_event.event_id,
            insights=result.analysis.insights,
            deficiencies=result.analysis.deficiencies,
            analysis_confidence=result.analysis.confidence_score,
            patterns_detected=result.analysis.patterns_detected,
        )

    def create_alert_event(
        self,
        source_event: SymptomReportedEvent,
        result: SDOProcessingResult,
    ) -> Optional[AlertTriggeredEvent]:
        """Create an AlertTriggeredEvent from processing result."""
        if not result.success or not result.notification or not result.classification:
            return None

        return AlertTriggeredEvent(
            user_id=source_event.user_id,
            source_event_id=source_event.event_id,
            correlation_id=source_event.correlation_id or source_event.event_id,
            notification=result.notification,
            classification=result.classification,
        )

    def _store_event(self, event: SymptomReportedEvent) -> None:
        """Store event in user history."""
        if event.user_id not in self._user_history:
            self._user_history[event.user_id] = []

        self._user_history[event.user_id].append(event)

        self._user_history[event.user_id] = self._user_history[event.user_id][-50:]

    def _get_historical_symptoms(
        self,
        user_id: str,
        limit: int = 20,
    ) -> List[SymptomInput]:
        """Get historical symptoms for a user."""
        events = self._user_history.get(user_id, [])

        symptoms = []
        for event in reversed(events[:-1]):
            symptoms.extend(event.symptoms)
            if len(symptoms) >= limit:
                break

        return symptoms[:limit]

    def get_user_history(self, user_id: str) -> List[SymptomReportedEvent]:
        """Get event history for a user."""
        return self._user_history.get(user_id, []).copy()

    def clear_user_history(self, user_id: str) -> None:
        """Clear event history for a user."""
        if user_id in self._user_history:
            del self._user_history[user_id]
        self._correlator.clear_history(user_id)


_engine_instance: Optional[SDOEngine] = None


def get_sdo_engine() -> SDOEngine:
    """Get or create the global SDO engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = SDOEngine()
    return _engine_instance
