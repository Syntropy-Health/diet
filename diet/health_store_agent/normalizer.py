"""
Product Normalizer for Health Store Agent

Transforms raw product data from various stores into standardized health units
suitable for vector storage and semantic search.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from diet.models.health_units import (
    AvailabilityStatus,
    DietaryTag,
    HealthCategory,
    MoneyAmount,
    NutrientValue,
    RawProduct,
    ServingSize,
    StandardizedHealthUnit,
    StoreType,
)

logger = logging.getLogger(__name__)


class ProductNormalizer:
    """
    Normalizes raw product data into StandardizedHealthUnit format.

    This class handles the transformation of store-specific product data
    into a unified format for vector storage and semantic search.
    """

    CATEGORY_KEYWORDS = {
        HealthCategory.VITAMIN: ["vitamin", "vitamins", "multivitamin"],
        HealthCategory.MINERAL: ["mineral", "minerals", "calcium", "magnesium", "zinc", "iron"],
        HealthCategory.SUPPLEMENT: ["supplement", "supplements", "dietary supplement"],
        HealthCategory.HERBAL: ["herbal", "herb", "herbs", "botanical", "plant extract"],
        HealthCategory.PROTEIN: ["protein", "whey", "casein", "plant protein"],
        HealthCategory.PROBIOTIC: ["probiotic", "probiotics", "lactobacillus", "bifidobacterium"],
        HealthCategory.OMEGA: ["omega", "fish oil", "dha", "epa", "fatty acid"],
        HealthCategory.AMINO_ACID: ["amino", "bcaa", "glutamine", "creatine"],
        HealthCategory.SUPERFOOD: ["superfood", "spirulina", "chlorella", "greens"],
        HealthCategory.MEAL_REPLACEMENT: ["meal replacement", "shake", "nutrition shake"],
        HealthCategory.SPORTS_NUTRITION: ["sports", "pre-workout", "post-workout", "energy"],
        HealthCategory.WELLNESS: ["wellness", "immune", "sleep", "stress", "mood"],
    }

    DIETARY_TAG_KEYWORDS = {
        DietaryTag.VEGAN: ["vegan", "plant-based", "plant based"],
        DietaryTag.VEGETARIAN: ["vegetarian"],
        DietaryTag.GLUTEN_FREE: ["gluten-free", "gluten free", "no gluten"],
        DietaryTag.DAIRY_FREE: ["dairy-free", "dairy free", "no dairy", "lactose-free"],
        DietaryTag.SOY_FREE: ["soy-free", "soy free", "no soy"],
        DietaryTag.NUT_FREE: ["nut-free", "nut free", "no nuts"],
        DietaryTag.ORGANIC: ["organic", "usda organic"],
        DietaryTag.NON_GMO: ["non-gmo", "non gmo", "no gmo"],
        DietaryTag.KOSHER: ["kosher"],
        DietaryTag.HALAL: ["halal"],
        DietaryTag.KETO: ["keto", "ketogenic"],
        DietaryTag.PALEO: ["paleo"],
        DietaryTag.SUGAR_FREE: ["sugar-free", "sugar free", "no sugar", "zero sugar"],
    }

    SYMPTOM_KEYWORDS = {
        "fatigue": ["fatigue", "tired", "tiredness", "energy", "exhaustion"],
        "headache": ["headache", "migraine", "head pain"],
        "joint_pain": ["joint", "arthritis", "joint pain", "mobility"],
        "digestive": ["digestive", "digestion", "gut", "bloating", "ibs"],
        "sleep": ["sleep", "insomnia", "restless", "melatonin"],
        "stress": ["stress", "anxiety", "calm", "relaxation"],
        "immune": ["immune", "immunity", "cold", "flu", "defense"],
        "skin": ["skin", "acne", "complexion", "collagen"],
        "hair": ["hair", "hair growth", "hair loss", "biotin"],
        "mood": ["mood", "depression", "serotonin", "st. john"],
        "cognitive": ["brain", "memory", "focus", "cognitive", "concentration"],
        "inflammation": ["inflammation", "anti-inflammatory", "turmeric", "curcumin"],
    }

    DEFICIENCY_KEYWORDS = {
        "vitamin_d": ["vitamin d", "d3", "cholecalciferol"],
        "vitamin_b12": ["vitamin b12", "b12", "cobalamin", "methylcobalamin"],
        "iron": ["iron", "ferrous", "ferritin"],
        "magnesium": ["magnesium", "mag"],
        "zinc": ["zinc"],
        "calcium": ["calcium"],
        "omega_3": ["omega-3", "omega 3", "dha", "epa", "fish oil"],
        "vitamin_c": ["vitamin c", "ascorbic acid"],
        "folate": ["folate", "folic acid", "b9"],
        "potassium": ["potassium"],
        "iodine": ["iodine", "kelp"],
        "selenium": ["selenium"],
    }

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.ProductNormalizer")

    def normalize(
        self,
        raw_product: RawProduct,
        generate_embedding: bool = False,
    ) -> StandardizedHealthUnit:
        """
        Normalize a raw product to a standardized health unit.

        Args:
            raw_product: Raw product data from store
            generate_embedding: Whether to generate vector embedding

        Returns:
            Standardized health unit
        """
        raw_data = raw_product.raw_data

        name = raw_product.name or raw_data.get("name", "Unknown Product")
        description = raw_product.description or raw_data.get("description", "")

        searchable_text = f"{name} {description}".lower()

        category = self._extract_category(searchable_text, raw_data)
        dietary_tags = self._extract_dietary_tags(searchable_text, raw_data)
        target_symptoms = self._extract_target_symptoms(searchable_text)
        target_deficiencies = self._extract_target_deficiencies(searchable_text)
        nutrients = self._extract_nutrients(raw_data)
        serving_size = self._extract_serving_size(raw_data)
        price = self._extract_price(raw_product)
        availability = self._extract_availability(raw_data)

        quality_score = self._calculate_quality_score(
            raw_product, nutrients, dietary_tags, target_symptoms
        )

        unit = StandardizedHealthUnit(
            source_store=raw_product.source_store,
            source_product_id=raw_product.source_product_id,
            name=name,
            description=description[:2000] if description else "",
            brand=raw_data.get("brand"),
            category=category,
            subcategory=raw_data.get("subcategory"),
            nutrients=nutrients,
            serving_size=serving_size,
            ingredients=raw_data.get("ingredients", []),
            health_claims=raw_data.get("health_claims", []),
            target_symptoms=target_symptoms,
            target_deficiencies=target_deficiencies,
            allergens=raw_data.get("allergens", []),
            dietary_tags=dietary_tags,
            price=price,
            availability=availability,
            product_url=raw_product.product_url,
            affiliate_link=raw_data.get("affiliate_link"),
            image_url=raw_product.image_url,
            quality_score=quality_score,
        )

        return unit

    def _extract_category(
        self,
        searchable_text: str,
        raw_data: Dict[str, Any],
    ) -> HealthCategory:
        """Extract health category from product text."""
        raw_category = raw_data.get("category", "").lower()
        combined_text = f"{searchable_text} {raw_category}"

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in combined_text:
                    return category

        return HealthCategory.OTHER

    def _extract_dietary_tags(
        self,
        searchable_text: str,
        raw_data: Dict[str, Any],
    ) -> List[DietaryTag]:
        """Extract dietary tags from product text."""
        tags = []

        raw_tags = raw_data.get("dietary_tags", [])
        if isinstance(raw_tags, list):
            for tag in raw_tags:
                try:
                    tags.append(DietaryTag(tag))
                except ValueError:
                    pass

        for tag, keywords in self.DIETARY_TAG_KEYWORDS.items():
            if tag not in tags:
                for keyword in keywords:
                    if keyword in searchable_text:
                        tags.append(tag)
                        break

        return tags

    def _extract_target_symptoms(self, searchable_text: str) -> List[str]:
        """Extract target symptoms from product text."""
        symptoms = []

        for symptom, keywords in self.SYMPTOM_KEYWORDS.items():
            for keyword in keywords:
                if keyword in searchable_text:
                    symptoms.append(symptom)
                    break

        return symptoms

    def _extract_target_deficiencies(self, searchable_text: str) -> List[str]:
        """Extract target nutritional deficiencies from product text."""
        deficiencies = []

        for deficiency, keywords in self.DEFICIENCY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in searchable_text:
                    deficiencies.append(deficiency)
                    break

        return deficiencies

    def _extract_nutrients(
        self,
        raw_data: Dict[str, Any],
    ) -> Dict[str, NutrientValue]:
        """Extract nutrient values from raw data."""
        nutrients = {}

        raw_nutrients = raw_data.get("nutrients", {})
        if not raw_nutrients:
            raw_nutrients = raw_data.get("nutrition_facts", {})

        if isinstance(raw_nutrients, dict):
            for name, value in raw_nutrients.items():
                if isinstance(value, dict):
                    nutrients[name] = NutrientValue(
                        amount=value.get("amount", 0),
                        unit=value.get("unit", "mg"),
                        daily_value_percent=value.get("daily_value_percent"),
                    )
                elif isinstance(value, (int, float)):
                    nutrients[name] = NutrientValue(
                        amount=float(value),
                        unit="mg",
                    )

        return nutrients

    def _extract_serving_size(
        self,
        raw_data: Dict[str, Any],
    ) -> Optional[ServingSize]:
        """Extract serving size information from raw data."""
        serving = raw_data.get("serving_size")

        if isinstance(serving, dict):
            return ServingSize(
                amount=serving.get("amount", 1),
                unit=serving.get("unit", "serving"),
                servings_per_container=serving.get("servings_per_container"),
                description=serving.get("description"),
            )
        elif isinstance(serving, str):
            match = re.match(r"(\d+(?:\.\d+)?)\s*(\w+)", serving)
            if match:
                return ServingSize(
                    amount=float(match.group(1)),
                    unit=match.group(2),
                    description=serving,
                )

        return None

    def _extract_price(
        self,
        raw_product: RawProduct,
    ) -> Optional[MoneyAmount]:
        """Extract price information."""
        if raw_product.price is not None:
            return MoneyAmount(
                amount=raw_product.price,
                currency=raw_product.currency or "USD",
            )
        return None

    def _extract_availability(
        self,
        raw_data: Dict[str, Any],
    ) -> AvailabilityStatus:
        """Extract availability status from raw data."""
        availability = raw_data.get("availability", "").lower()
        in_stock = raw_data.get("in_stock")

        if in_stock is True or "in stock" in availability:
            return AvailabilityStatus.IN_STOCK
        elif in_stock is False or "out of stock" in availability:
            return AvailabilityStatus.OUT_OF_STOCK
        elif "low" in availability:
            return AvailabilityStatus.LOW_STOCK
        elif "preorder" in availability or "pre-order" in availability:
            return AvailabilityStatus.PREORDER
        elif "discontinued" in availability:
            return AvailabilityStatus.DISCONTINUED

        return AvailabilityStatus.UNKNOWN

    def _calculate_quality_score(
        self,
        raw_product: RawProduct,
        nutrients: Dict[str, NutrientValue],
        dietary_tags: List[DietaryTag],
        target_symptoms: List[str],
    ) -> float:
        """Calculate data quality score for the product."""
        score = 0.0

        if raw_product.name:
            score += 0.15

        if raw_product.description and len(raw_product.description) > 50:
            score += 0.15

        if raw_product.price is not None:
            score += 0.1

        if raw_product.image_url:
            score += 0.1

        if nutrients:
            score += min(len(nutrients) * 0.05, 0.2)

        if dietary_tags:
            score += min(len(dietary_tags) * 0.03, 0.15)

        if target_symptoms:
            score += min(len(target_symptoms) * 0.03, 0.15)

        return min(score, 1.0)


_normalizer_instance: Optional[ProductNormalizer] = None


def get_product_normalizer() -> ProductNormalizer:
    """Get or create the global normalizer instance."""
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = ProductNormalizer()
    return _normalizer_instance
