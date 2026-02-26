"""
Diet Recommender

Generates personalized dietary and supplement recommendations
based on symptom analysis and identified deficiencies.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from diet.health_store_agent import HealthStoreFactory
from diet.models.events import NutritionalDeficiencyInsight, Recommendation
from diet.models.health_units import (
    ProductSearchQuery,
    ProductSearchResult,
    StandardizedHealthUnit,
)
from diet.models.store import StoreType
from diet.sdo.analyzer import SymptomAnalysisOutput

logger = logging.getLogger(__name__)


class DietaryRecommendation(BaseModel):
    """A dietary recommendation with food suggestions."""
    recommendation_id: str = Field(default_factory=lambda: str(uuid4()))
    nutrient: str = Field(..., description="Target nutrient")
    priority: int = Field(default=1, ge=1, le=5)
    food_suggestions: List[str] = Field(default_factory=list)
    meal_ideas: List[str] = Field(default_factory=list)
    daily_target: Optional[str] = Field(default=None)
    reasoning: str = Field(default="")


class SupplementRecommendation(BaseModel):
    """A supplement recommendation with product suggestions."""
    recommendation_id: str = Field(default_factory=lambda: str(uuid4()))
    nutrient: str = Field(..., description="Target nutrient")
    priority: int = Field(default=1, ge=1, le=5)
    dosage_suggestion: Optional[str] = Field(default=None)
    timing_suggestion: Optional[str] = Field(default=None)
    products: List[StandardizedHealthUnit] = Field(default_factory=list)
    reasoning: str = Field(default="")


class RecommendationResult(BaseModel):
    """Combined recommendation results."""
    dietary_recommendations: List[DietaryRecommendation] = Field(default_factory=list)
    supplement_recommendations: List[SupplementRecommendation] = Field(default_factory=list)
    lifestyle_recommendations: List[Recommendation] = Field(default_factory=list)
    priority_actions: List[str] = Field(default_factory=list)
    overall_guidance: str = Field(default="")


class DietRecommender:
    """
    Generates diet and supplement recommendations.

    Features:
    - Nutrient-specific food recommendations
    - Supplement product matching via Health Store Agent
    - Lifestyle suggestions
    - Priority action identification
    """

    NUTRIENT_FOODS = {
        "iron": {
            "foods": ["red meat", "spinach", "lentils", "fortified cereals", "oysters", "dark chocolate"],
            "meals": ["Spinach salad with lemon dressing", "Lentil soup", "Beef stir-fry"],
            "target": "18mg daily for women, 8mg for men",
        },
        "vitamin_d": {
            "foods": ["fatty fish (salmon, mackerel)", "fortified milk", "egg yolks", "mushrooms"],
            "meals": ["Grilled salmon with vegetables", "Mushroom omelette", "Fortified smoothie"],
            "target": "600-800 IU daily",
        },
        "vitamin_b12": {
            "foods": ["eggs", "dairy products", "fortified nutritional yeast", "fortified cereals"],
            "meals": ["Scrambled eggs with cheese", "Greek yogurt parfait", "B12-fortified smoothie"],
            "target": "2.4mcg daily",
        },
        "magnesium": {
            "foods": ["dark chocolate", "avocados", "nuts", "leafy greens", "legumes", "seeds"],
            "meals": ["Avocado toast with pumpkin seeds", "Almond butter smoothie", "Quinoa salad"],
            "target": "400-420mg daily for men, 310-320mg for women",
        },
        "zinc": {
            "foods": ["oysters", "beef", "pumpkin seeds", "chickpeas", "cashews"],
            "meals": ["Beef and vegetable stew", "Hummus with vegetables", "Pumpkin seed trail mix"],
            "target": "11mg daily for men, 8mg for women",
        },
        "omega_3": {
            "foods": ["fatty fish", "walnuts", "flaxseeds", "chia seeds", "fish oil"],
            "meals": ["Baked salmon", "Walnut-crusted fish", "Chia pudding"],
            "target": "250-500mg EPA+DHA daily",
        },
        "calcium": {
            "foods": ["dairy products", "fortified plant milk", "sardines", "leafy greens", "tofu"],
            "meals": ["Greek yogurt with fruit", "Calcium-fortified smoothie", "Sardine salad"],
            "target": "1000-1200mg daily",
        },
        "folate": {
            "foods": ["leafy greens", "legumes", "citrus fruits", "fortified grains", "asparagus"],
            "meals": ["Spinach and lentil salad", "Citrus fruit bowl", "Asparagus stir-fry"],
            "target": "400mcg daily",
        },
    }

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.DietRecommender")
        self._store_factory = HealthStoreFactory()

    async def generate_recommendations(
        self,
        analysis: SymptomAnalysisOutput,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> RecommendationResult:
        """
        Generate comprehensive recommendations based on analysis.

        Args:
            analysis: Symptom analysis output
            user_preferences: Optional user dietary preferences

        Returns:
            Recommendation results
        """
        self.logger.info(f"Generating recommendations for {len(analysis.deficiencies)} deficiencies")

        sorted_deficiencies = sorted(
            analysis.deficiencies,
            key=lambda d: (d.priority, d.deficiency_likelihood),
            reverse=True
        )

        dietary_recs = []
        supplement_recs = []
        lifestyle_recs = []
        priority_actions = []

        for deficiency in sorted_deficiencies[:5]:
            dietary_rec = self._generate_dietary_recommendation(deficiency)
            dietary_recs.append(dietary_rec)

            supplement_rec = await self._generate_supplement_recommendation(
                deficiency, user_preferences
            )
            supplement_recs.append(supplement_rec)

            if deficiency.priority >= 3 or deficiency.deficiency_likelihood >= 0.7:
                priority_actions.append(
                    f"Address {deficiency.nutrient} deficiency: {dietary_rec.food_suggestions[0] if dietary_rec.food_suggestions else 'consult healthcare provider'}"
                )

        lifestyle_recs = self._generate_lifestyle_recommendations(analysis)

        overall_guidance = self._generate_overall_guidance(
            analysis, dietary_recs, supplement_recs
        )

        return RecommendationResult(
            dietary_recommendations=dietary_recs,
            supplement_recommendations=supplement_recs,
            lifestyle_recommendations=lifestyle_recs,
            priority_actions=priority_actions,
            overall_guidance=overall_guidance,
        )

    def _generate_dietary_recommendation(
        self,
        deficiency: NutritionalDeficiencyInsight,
    ) -> DietaryRecommendation:
        """Generate dietary recommendation for a deficiency."""
        nutrient = deficiency.nutrient.lower()
        nutrient_data = self.NUTRIENT_FOODS.get(nutrient, {})

        foods = nutrient_data.get("foods", deficiency.food_sources or [])
        meals = nutrient_data.get("meals", [])
        target = nutrient_data.get("target", deficiency.recommended_intake)

        return DietaryRecommendation(
            nutrient=deficiency.nutrient,
            priority=deficiency.priority,
            food_suggestions=foods[:6],
            meal_ideas=meals[:3],
            daily_target=target,
            reasoning=f"Based on {deficiency.deficiency_likelihood:.0%} likelihood of {deficiency.nutrient} deficiency",
        )

    async def _generate_supplement_recommendation(
        self,
        deficiency: NutritionalDeficiencyInsight,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> SupplementRecommendation:
        """Generate supplement recommendation with product search."""
        products = []

        try:
            adapter = self._store_factory.create(StoreType.SHOP)
            await adapter.initialize()

            query = ProductSearchQuery(
                query_text=deficiency.nutrient,
                deficiencies=[deficiency.nutrient],
                symptoms=deficiency.supporting_symptoms,
                limit=3,
            )

            if user_preferences:
                dietary_reqs = user_preferences.get("dietary_requirements", [])
                if dietary_reqs:
                    query.dietary_requirements = dietary_reqs

            raw_products = await adapter.search_products(query)
            products = [adapter.normalize_product(p) for p in raw_products]

        except Exception as e:
            self.logger.warning(f"Product search failed: {e}")

        dosage_map = {
            "vitamin_d": "1000-5000 IU daily with food",
            "iron": "18-25mg daily with vitamin C",
            "vitamin_b12": "500-1000mcg daily",
            "magnesium": "200-400mg daily before bed",
            "zinc": "15-30mg daily with food",
            "omega_3": "1000-2000mg EPA+DHA daily",
            "calcium": "500-600mg twice daily",
            "folate": "400-800mcg daily",
        }

        timing_map = {
            "vitamin_d": "With breakfast or largest meal",
            "iron": "On empty stomach or with vitamin C",
            "vitamin_b12": "Morning, any time",
            "magnesium": "Evening, 1-2 hours before bed",
            "zinc": "With food to avoid nausea",
            "omega_3": "With meals containing fat",
            "calcium": "Spread throughout day, not with iron",
            "folate": "Morning with food",
        }

        nutrient_key = deficiency.nutrient.lower()

        return SupplementRecommendation(
            nutrient=deficiency.nutrient,
            priority=deficiency.priority,
            dosage_suggestion=dosage_map.get(nutrient_key),
            timing_suggestion=timing_map.get(nutrient_key),
            products=products,
            reasoning=f"Supplement recommended due to {deficiency.deficiency_likelihood:.0%} likelihood and supporting symptoms: {', '.join(deficiency.supporting_symptoms[:3])}",
        )

    def _generate_lifestyle_recommendations(
        self,
        analysis: SymptomAnalysisOutput,
    ) -> List[Recommendation]:
        """Generate lifestyle recommendations based on analysis."""
        recs = []

        if "fatigue_pattern" in analysis.patterns_detected:
            recs.append(Recommendation(
                type="lifestyle",
                title="Sleep Optimization",
                description="Aim for 7-9 hours of quality sleep. Consider a consistent sleep schedule and limiting screen time before bed.",
                priority=2,
                evidence_basis="symptom_pattern",
            ))

        if "mood_pattern" in analysis.patterns_detected:
            recs.append(Recommendation(
                type="lifestyle",
                title="Stress Management",
                description="Practice stress-reduction techniques such as meditation, deep breathing, or regular exercise.",
                priority=2,
                evidence_basis="symptom_pattern",
            ))

        if "digestive" in " ".join(analysis.patterns_detected).lower():
            recs.append(Recommendation(
                type="lifestyle",
                title="Digestive Health",
                description="Consider eating smaller, more frequent meals. Stay hydrated and include fiber-rich foods.",
                priority=2,
                evidence_basis="symptom_pattern",
            ))

        if analysis.severity_score >= 0.6:
            recs.append(Recommendation(
                type="lifestyle",
                title="Healthcare Consultation",
                description="Given the severity of symptoms, consider consulting with a healthcare provider for personalized guidance.",
                priority=1,
                evidence_basis="severity_assessment",
            ))

        return recs

    def _generate_overall_guidance(
        self,
        analysis: SymptomAnalysisOutput,
        dietary_recs: List[DietaryRecommendation],
        supplement_recs: List[SupplementRecommendation],
    ) -> str:
        """Generate overall guidance summary."""
        parts = []

        if analysis.deficiencies:
            top_nutrients = [d.nutrient for d in analysis.deficiencies[:3]]
            parts.append(f"Focus on increasing intake of: {', '.join(top_nutrients)}.")

        if dietary_recs:
            parts.append(f"Dietary changes recommended for {len(dietary_recs)} nutrients.")

        if supplement_recs:
            high_priority = [s for s in supplement_recs if s.priority >= 3]
            if high_priority:
                parts.append(f"Consider supplements for: {', '.join(s.nutrient for s in high_priority)}.")

        if analysis.severity_score >= 0.7:
            parts.append("Due to symptom severity, consider consulting a healthcare provider.")

        return " ".join(parts) if parts else "Continue monitoring symptoms and maintain a balanced diet."
