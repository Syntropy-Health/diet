"""
Tests for the Symptom-Diet Optimizer (SDO) Engine

Tests cover:
- Symptom analysis (with fallback when LLM unavailable)
- Pattern correlation
- Recommendation generation
- Alert classification
- Full pipeline processing
"""

import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from diet.models.alerts import AlertLevel
from diet.models.events import SymptomInput, SymptomReportedEvent
from diet.sdo.alert_classifier import SDOAlertClassifier
from diet.sdo.analyzer import SymptomAnalysisOutput, SymptomAnalyzer
from diet.sdo.correlator import CorrelationResult, PatternCorrelator
from diet.sdo.engine import SDOEngine, get_sdo_engine
from diet.sdo.recommender import DietRecommender


class TestSymptomAnalyzer:
    """Tests for the SymptomAnalyzer component."""

    @pytest.fixture
    def analyzer(self):
        return SymptomAnalyzer()

    @pytest.fixture
    def sample_event(self):
        return SymptomReportedEvent(
            user_id="test_user_001",
            symptoms=[
                SymptomInput(name="fatigue", severity=0.7, duration_hours=48),
                SymptomInput(name="headache", severity=0.5),
                SymptomInput(name="mood changes", severity=0.6),
            ],
            recent_foods=["coffee", "sandwich", "salad"],
            sleep_hours=5.5,
            stress_level=7,
        )

    @pytest.mark.asyncio
    async def test_fallback_analysis(self, analyzer, sample_event):
        """Test that fallback analysis works when LLM is unavailable."""
        result = await analyzer.analyze(sample_event)

        assert isinstance(result, SymptomAnalysisOutput)
        assert len(result.insights) > 0
        assert result.severity_score > 0
        assert result.confidence_score > 0

    @pytest.mark.asyncio
    async def test_fatigue_detection(self, analyzer):
        """Test detection of fatigue-related deficiencies."""
        event = SymptomReportedEvent(
            user_id="test_user_002",
            symptoms=[
                SymptomInput(name="extreme fatigue", severity=0.8),
                SymptomInput(name="tiredness", severity=0.7),
            ],
        )

        result = await analyzer.analyze(event)

        deficiency_nutrients = [d.nutrient for d in result.deficiencies]
        assert "iron" in deficiency_nutrients or "vitamin_b12" in deficiency_nutrients

    @pytest.mark.asyncio
    async def test_mood_pattern_detection(self, analyzer):
        """Test detection of mood-related patterns."""
        event = SymptomReportedEvent(
            user_id="test_user_003",
            symptoms=[
                SymptomInput(name="anxiety", severity=0.6),
                SymptomInput(name="stress", severity=0.7),
                SymptomInput(name="irritability", severity=0.5),
            ],
        )

        result = await analyzer.analyze(event)

        assert "mood_pattern" in result.patterns_detected
        deficiency_nutrients = [d.nutrient for d in result.deficiencies]
        assert "magnesium" in deficiency_nutrients or "vitamin_d" in deficiency_nutrients


class TestPatternCorrelator:
    """Tests for the PatternCorrelator component."""

    @pytest.fixture
    def correlator(self):
        return PatternCorrelator()

    @pytest.fixture
    def sample_events(self):
        base_time = datetime.utcnow()
        events = []
        for i in range(5):
            events.append(SymptomReportedEvent(
                user_id="test_user_pattern",
                timestamp=base_time - timedelta(days=i),
                symptoms=[
                    SymptomInput(name="headache", severity=0.5 + i * 0.05),
                    SymptomInput(name="fatigue", severity=0.4 + i * 0.03),
                ],
            ))
        return events

    def test_co_occurrence_detection(self, correlator):
        """Test detection of co-occurring symptoms."""
        event = SymptomReportedEvent(
            user_id="test_user_cooc",
            symptoms=[
                SymptomInput(name="headache", severity=0.6),
                SymptomInput(name="nausea", severity=0.5),
                SymptomInput(name="fatigue", severity=0.7),
            ],
        )

        result = correlator.correlate(event)

        assert isinstance(result, CorrelationResult)
        assert len(result.co_occurrences) > 0

    def test_recurring_symptom_tracking(self, correlator, sample_events):
        """Test tracking of recurring symptoms across events."""
        for event in sample_events:
            correlator.correlate(event)

        final_result = correlator.correlate(sample_events[-1])

        assert len(final_result.recurring_symptoms) > 0
        assert "headache" in final_result.recurring_symptoms

    def test_severity_trend_analysis(self, correlator, sample_events):
        """Test analysis of severity trends."""
        for event in sample_events:
            correlator.correlate(event)

        final_result = correlator.correlate(sample_events[0])

        assert len(final_result.severity_trends) > 0

    def test_history_clearing(self, correlator, sample_events):
        """Test that history can be cleared."""
        for event in sample_events:
            correlator.correlate(event)

        correlator.clear_history("test_user_pattern")

        result = correlator.correlate(sample_events[0])
        assert len(result.recurring_symptoms) == 0


class TestDietRecommender:
    """Tests for the DietRecommender component."""

    @pytest.fixture
    def recommender(self):
        return DietRecommender()

    @pytest.fixture
    def sample_analysis(self):
        from diet.models.events import NutritionalDeficiencyInsight

        return SymptomAnalysisOutput(
            insights=[],
            deficiencies=[
                NutritionalDeficiencyInsight(
                    nutrient="iron",
                    deficiency_likelihood=0.7,
                    supporting_symptoms=["fatigue", "weakness"],
                    priority=3,
                ),
                NutritionalDeficiencyInsight(
                    nutrient="vitamin_d",
                    deficiency_likelihood=0.6,
                    supporting_symptoms=["fatigue", "mood"],
                    priority=2,
                ),
            ],
            severity_score=0.6,
            confidence_score=0.75,
            patterns_detected=["fatigue_pattern"],
        )

    @pytest.mark.asyncio
    async def test_dietary_recommendations(self, recommender, sample_analysis):
        """Test generation of dietary recommendations."""
        result = await recommender.generate_recommendations(sample_analysis)

        assert len(result.dietary_recommendations) > 0

        iron_rec = next((r for r in result.dietary_recommendations if r.nutrient == "iron"), None)
        assert iron_rec is not None
        assert len(iron_rec.food_suggestions) > 0

    @pytest.mark.asyncio
    async def test_supplement_recommendations(self, recommender, sample_analysis):
        """Test generation of supplement recommendations."""
        result = await recommender.generate_recommendations(sample_analysis)

        assert len(result.supplement_recommendations) > 0

        for supp in result.supplement_recommendations:
            assert supp.nutrient in ["iron", "vitamin_d"]

    @pytest.mark.asyncio
    async def test_lifestyle_recommendations(self, recommender, sample_analysis):
        """Test generation of lifestyle recommendations."""
        result = await recommender.generate_recommendations(sample_analysis)

        assert len(result.lifestyle_recommendations) > 0

    @pytest.mark.asyncio
    async def test_priority_actions(self, recommender, sample_analysis):
        """Test identification of priority actions."""
        result = await recommender.generate_recommendations(sample_analysis)

        assert len(result.priority_actions) > 0


class TestSDOAlertClassifier:
    """Tests for the SDOAlertClassifier component."""

    @pytest.fixture
    def classifier(self):
        return SDOAlertClassifier()

    def test_high_severity_alert(self, classifier):
        """Test that high severity triggers ALERT level."""
        analysis = SymptomAnalysisOutput(
            insights=[],
            deficiencies=[],
            severity_score=0.85,
            confidence_score=0.8,
            urgency_indicators=["severe", "persistent"],
        )

        result = classifier.classify(analysis)

        assert result.alert_level == AlertLevel.ALERT
        assert result.should_notify

    def test_moderate_severity_suggestion(self, classifier):
        """Test that moderate severity triggers SUGGESTION level."""
        analysis = SymptomAnalysisOutput(
            insights=[],
            deficiencies=[],
            severity_score=0.5,
            confidence_score=0.7,
        )

        result = classifier.classify(analysis)

        assert result.alert_level == AlertLevel.SUGGESTION

    def test_low_severity_tips(self, classifier):
        """Test that low severity triggers TIPS level."""
        analysis = SymptomAnalysisOutput(
            insights=[],
            deficiencies=[],
            severity_score=0.2,
            confidence_score=0.6,
        )

        result = classifier.classify(analysis)

        assert result.alert_level == AlertLevel.TIPS

    def test_notification_creation(self, classifier):
        """Test notification creation from classification."""
        analysis = SymptomAnalysisOutput(
            insights=[],
            deficiencies=[],
            severity_score=0.6,
            confidence_score=0.75,
        )

        classification = classifier.classify(analysis)
        notification = classifier.create_notification(
            "test_user", classification, analysis
        )

        assert notification.user_id == "test_user"
        assert notification.alert_level == classification.alert_level
        assert notification.title
        assert notification.message


class TestSDOEngine:
    """Tests for the complete SDO Engine."""

    @pytest.fixture
    def engine(self):
        return SDOEngine()

    @pytest.fixture
    def sample_event(self):
        return SymptomReportedEvent(
            user_id="test_engine_user",
            symptoms=[
                SymptomInput(name="fatigue", severity=0.7),
                SymptomInput(name="headache", severity=0.5),
            ],
            sleep_hours=6,
            stress_level=6,
        )

    @pytest.mark.asyncio
    async def test_engine_initialization(self, engine):
        """Test engine initialization."""
        await engine.initialize()
        assert engine._initialized
        await engine.shutdown()
        assert not engine._initialized

    @pytest.mark.asyncio
    async def test_full_pipeline_processing(self, engine, sample_event):
        """Test complete pipeline processing."""
        await engine.initialize()

        result = await engine.process_symptoms(sample_event)

        assert result.success
        assert result.analysis is not None
        assert result.correlation is not None
        assert result.recommendations is not None
        assert result.classification is not None
        assert result.notification is not None
        assert result.processing_time_ms > 0

        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_event_creation(self, engine, sample_event):
        """Test event creation from processing result."""
        await engine.initialize()

        result = await engine.process_symptoms(sample_event)

        insight_event = engine.create_insight_event(sample_event, result)
        assert insight_event is not None
        assert insight_event.user_id == sample_event.user_id

        alert_event = engine.create_alert_event(sample_event, result)
        assert alert_event is not None
        assert alert_event.notification is not None

        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_batch_processing(self, engine):
        """Test batch processing of multiple events."""
        events = [
            SymptomReportedEvent(
                user_id=f"batch_user_{i}",
                symptoms=[SymptomInput(name="fatigue", severity=0.5 + i * 0.1)],
            )
            for i in range(3)
        ]

        await engine.initialize()

        results = await engine.process_batch(events)

        assert len(results) == 3
        assert all(r.success for r in results)

        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_user_history_tracking(self, engine, sample_event):
        """Test user history is tracked correctly."""
        await engine.initialize()

        await engine.process_symptoms(sample_event)
        await engine.process_symptoms(sample_event)

        history = engine.get_user_history(sample_event.user_id)
        assert len(history) == 2

        engine.clear_user_history(sample_event.user_id)
        history = engine.get_user_history(sample_event.user_id)
        assert len(history) == 0

        await engine.shutdown()


def test_global_engine_singleton():
    """Test that get_sdo_engine returns a singleton."""
    engine1 = get_sdo_engine()
    engine2 = get_sdo_engine()
    assert engine1 is engine2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
