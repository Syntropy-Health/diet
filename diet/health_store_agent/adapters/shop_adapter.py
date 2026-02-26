"""
Shop Store Adapter - Proof of Concept

This adapter integrates with Syntropy's Shop store as the primary PoC
for the Health Store Agent ingress layer.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from diet.health_store_agent.base_adapter import AbstractStoreAdapter
from diet.health_store_agent.factory import HealthStoreFactory, StoreConfig
from diet.health_store_agent.normalizer import get_product_normalizer
from diet.models.health_units import (
    AvailabilityStatus,
    HealthCategory,
    MoneyAmount,
    NutrientValue,
    ProductSearchQuery,
    RawProduct,
    ServingSize,
    StandardizedHealthUnit,
)
from diet.models.store import StoreType

logger = logging.getLogger(__name__)


@HealthStoreFactory.register(StoreType.SHOP)
class ShopStoreAdapter(AbstractStoreAdapter):
    """
    Adapter for Syntropy's Shop store.

    This is the primary PoC implementation that demonstrates:
    - Product search via Shop API/database
    - Product normalization to StandardizedHealthUnit
    - Integration with the HSA factory pattern
    """

    def __init__(self, config: Optional[StoreConfig] = None):
        self.config = config or StoreConfig()
        self.logger = logging.getLogger(f"{__name__}.ShopStoreAdapter")
        self._initialized = False
        self._normalizer = get_product_normalizer()
        self._mock_products: List[Dict[str, Any]] = []

    @property
    def store_type(self) -> StoreType:
        return StoreType.SHOP

    @property
    def store_name(self) -> str:
        return "Syntropy Shop"

    async def initialize(self) -> None:
        """Initialize the Shop adapter with mock data for PoC."""
        if self._initialized:
            return

        self.logger.info("Initializing Shop Store Adapter")

        self._mock_products = self._load_mock_products()
        self._initialized = True
        self.logger.info(f"Loaded {len(self._mock_products)} mock products")

    async def shutdown(self) -> None:
        """Clean up adapter resources."""
        self.logger.info("Shutting down Shop Store Adapter")
        self._mock_products.clear()
        self._initialized = False

    async def search_products(
        self,
        query: ProductSearchQuery,
    ) -> List[RawProduct]:
        """
        Search for products in the Shop store.

        Args:
            query: Search query with filters

        Returns:
            List of raw products matching the query
        """
        if not self._initialized:
            await self.initialize()

        self.logger.debug(f"Searching Shop for: {query.query_text}")

        results = []
        search_text = (query.query_text or "").lower()

        for product in self._mock_products:
            score = self._calculate_match_score(product, query)
            if score > 0.3:
                raw_product = RawProduct(
                    source_store=StoreType.SHOP,
                    source_product_id=str(product["id"]),
                    raw_data=product,
                    name=product.get("name"),
                    description=product.get("description"),
                    price=product.get("price"),
                    currency="USD",
                    image_url=product.get("image_url"),
                    product_url=product.get("product_url"),
                )
                results.append((score, raw_product))

        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:query.limit]]

    async def get_product_details(
        self,
        product_id: str,
    ) -> Optional[RawProduct]:
        """
        Get detailed product information.

        Args:
            product_id: Shop product ID

        Returns:
            Raw product data or None
        """
        if not self._initialized:
            await self.initialize()

        for product in self._mock_products:
            if str(product["id"]) == product_id:
                return RawProduct(
                    source_store=StoreType.SHOP,
                    source_product_id=product_id,
                    raw_data=product,
                    name=product.get("name"),
                    description=product.get("description"),
                    price=product.get("price"),
                    currency="USD",
                    image_url=product.get("image_url"),
                    product_url=product.get("product_url"),
                )
        return None

    def normalize_product(
        self,
        raw_product: RawProduct,
    ) -> StandardizedHealthUnit:
        """
        Normalize a raw Shop product to a standardized health unit.

        Args:
            raw_product: Raw product from Shop

        Returns:
            Standardized health unit
        """
        return self._normalizer.normalize(raw_product)

    def _calculate_match_score(
        self,
        product: Dict[str, Any],
        query: ProductSearchQuery,
    ) -> float:
        """Calculate relevance score for a product against query."""
        score = 0.0

        product_text = f"{product.get('name', '')} {product.get('description', '')}".lower()

        if query.query_text:
            search_terms = query.query_text.lower().split()
            matches = sum(1 for term in search_terms if term in product_text)
            if search_terms:
                score += 0.4 * (matches / len(search_terms))

        product_symptoms = product.get("target_symptoms", [])
        if query.symptoms:
            symptom_matches = sum(1 for s in query.symptoms if s.lower() in [ps.lower() for ps in product_symptoms])
            if symptom_matches > 0:
                score += 0.4 * (symptom_matches / len(query.symptoms))

        product_deficiencies = product.get("target_deficiencies", [])
        if query.deficiencies:
            def_matches = sum(1 for d in query.deficiencies if d.lower() in [pd.lower() for pd in product_deficiencies])
            if def_matches > 0:
                score += 0.4 * (def_matches / len(query.deficiencies))

        if not query.query_text and not query.symptoms and not query.deficiencies:
            score = 0.5

        return min(score, 1.0)

    def _load_mock_products(self) -> List[Dict[str, Any]]:
        """Load mock product data for PoC demonstration."""
        return [
            {
                "id": "shop-001",
                "name": "Vitamin D3 5000 IU",
                "description": "High-potency Vitamin D3 for immune support and bone health. Supports calcium absorption and mood regulation.",
                "brand": "Syntropy Essentials",
                "category": "vitamin",
                "price": 19.99,
                "image_url": "https://shop.syntropy.health/images/vitamin-d3.jpg",
                "product_url": "https://shop.syntropy.health/products/vitamin-d3-5000",
                "in_stock": True,
                "nutrients": {
                    "vitamin_d": {"amount": 5000, "unit": "IU", "daily_value_percent": 625}
                },
                "serving_size": {"amount": 1, "unit": "softgel", "servings_per_container": 120},
                "ingredients": ["Vitamin D3 (Cholecalciferol)", "Olive Oil", "Softgel Capsule"],
                "health_claims": ["Immune support", "Bone health", "Mood support"],
                "target_symptoms": ["fatigue", "mood", "immune"],
                "target_deficiencies": ["vitamin_d"],
                "dietary_tags": ["gluten_free", "non_gmo"],
            },
            {
                "id": "shop-002",
                "name": "Magnesium Glycinate 400mg",
                "description": "Highly absorbable magnesium glycinate for relaxation, sleep support, and muscle recovery.",
                "brand": "Syntropy Essentials",
                "category": "mineral",
                "price": 24.99,
                "image_url": "https://shop.syntropy.health/images/magnesium.jpg",
                "product_url": "https://shop.syntropy.health/products/magnesium-glycinate",
                "in_stock": True,
                "nutrients": {
                    "magnesium": {"amount": 400, "unit": "mg", "daily_value_percent": 95}
                },
                "serving_size": {"amount": 2, "unit": "capsules", "servings_per_container": 60},
                "ingredients": ["Magnesium Glycinate", "Vegetable Cellulose Capsule"],
                "health_claims": ["Sleep support", "Muscle relaxation", "Stress relief"],
                "target_symptoms": ["sleep", "stress", "joint_pain"],
                "target_deficiencies": ["magnesium"],
                "dietary_tags": ["vegan", "gluten_free"],
            },
            {
                "id": "shop-003",
                "name": "Omega-3 Fish Oil 1000mg",
                "description": "Ultra-pure fish oil with EPA and DHA for brain health, heart health, and inflammation support.",
                "brand": "Syntropy Essentials",
                "category": "omega",
                "price": 29.99,
                "image_url": "https://shop.syntropy.health/images/omega3.jpg",
                "product_url": "https://shop.syntropy.health/products/omega-3-fish-oil",
                "in_stock": True,
                "nutrients": {
                    "epa": {"amount": 360, "unit": "mg"},
                    "dha": {"amount": 240, "unit": "mg"}
                },
                "serving_size": {"amount": 1, "unit": "softgel", "servings_per_container": 90},
                "ingredients": ["Fish Oil Concentrate", "Gelatin", "Glycerin", "Vitamin E"],
                "health_claims": ["Brain health", "Heart health", "Anti-inflammatory"],
                "target_symptoms": ["cognitive", "inflammation", "joint_pain"],
                "target_deficiencies": ["omega_3"],
                "dietary_tags": ["gluten_free"],
            },
            {
                "id": "shop-004",
                "name": "B-Complex with Methylfolate",
                "description": "Complete B-vitamin complex with active methylfolate and methylcobalamin for energy and mood support.",
                "brand": "Syntropy Essentials",
                "category": "vitamin",
                "price": 22.99,
                "image_url": "https://shop.syntropy.health/images/b-complex.jpg",
                "product_url": "https://shop.syntropy.health/products/b-complex",
                "in_stock": True,
                "nutrients": {
                    "vitamin_b12": {"amount": 1000, "unit": "mcg", "daily_value_percent": 41667},
                    "folate": {"amount": 800, "unit": "mcg", "daily_value_percent": 200},
                    "vitamin_b6": {"amount": 25, "unit": "mg", "daily_value_percent": 1471}
                },
                "serving_size": {"amount": 1, "unit": "capsule", "servings_per_container": 60},
                "ingredients": ["Methylcobalamin", "Methylfolate", "Pyridoxal-5-Phosphate"],
                "health_claims": ["Energy support", "Mood balance", "Nervous system health"],
                "target_symptoms": ["fatigue", "mood", "cognitive"],
                "target_deficiencies": ["vitamin_b12", "folate"],
                "dietary_tags": ["vegan", "gluten_free", "non_gmo"],
            },
            {
                "id": "shop-005",
                "name": "Iron Bisglycinate 25mg",
                "description": "Gentle, highly absorbable iron for energy and blood health without digestive upset.",
                "brand": "Syntropy Essentials",
                "category": "mineral",
                "price": 16.99,
                "image_url": "https://shop.syntropy.health/images/iron.jpg",
                "product_url": "https://shop.syntropy.health/products/iron-bisglycinate",
                "in_stock": True,
                "nutrients": {
                    "iron": {"amount": 25, "unit": "mg", "daily_value_percent": 139}
                },
                "serving_size": {"amount": 1, "unit": "capsule", "servings_per_container": 90},
                "ingredients": ["Iron Bisglycinate", "Vitamin C", "Vegetable Capsule"],
                "health_claims": ["Energy support", "Blood health", "Oxygen transport"],
                "target_symptoms": ["fatigue", "cognitive"],
                "target_deficiencies": ["iron"],
                "dietary_tags": ["vegan", "gluten_free"],
            },
            {
                "id": "shop-006",
                "name": "Probiotic 50 Billion CFU",
                "description": "Multi-strain probiotic for digestive health, immune support, and gut microbiome balance.",
                "brand": "Syntropy Essentials",
                "category": "probiotic",
                "price": 34.99,
                "image_url": "https://shop.syntropy.health/images/probiotic.jpg",
                "product_url": "https://shop.syntropy.health/products/probiotic-50b",
                "in_stock": True,
                "nutrients": {},
                "serving_size": {"amount": 1, "unit": "capsule", "servings_per_container": 30},
                "ingredients": ["Lactobacillus acidophilus", "Bifidobacterium lactis", "Prebiotic Fiber"],
                "health_claims": ["Digestive health", "Immune support", "Gut balance"],
                "target_symptoms": ["digestive", "immune"],
                "target_deficiencies": [],
                "dietary_tags": ["vegan", "gluten_free", "dairy_free"],
            },
            {
                "id": "shop-007",
                "name": "Ashwagandha KSM-66",
                "description": "Premium ashwagandha root extract for stress relief, energy, and cognitive performance.",
                "brand": "Syntropy Essentials",
                "category": "herbal",
                "price": 27.99,
                "image_url": "https://shop.syntropy.health/images/ashwagandha.jpg",
                "product_url": "https://shop.syntropy.health/products/ashwagandha-ksm66",
                "in_stock": True,
                "nutrients": {},
                "serving_size": {"amount": 1, "unit": "capsule", "servings_per_container": 60},
                "ingredients": ["Ashwagandha Root Extract (KSM-66)", "Vegetable Capsule"],
                "health_claims": ["Stress relief", "Energy support", "Cognitive enhancement"],
                "target_symptoms": ["stress", "fatigue", "cognitive", "mood"],
                "target_deficiencies": [],
                "dietary_tags": ["vegan", "organic", "non_gmo"],
            },
            {
                "id": "shop-008",
                "name": "Zinc Picolinate 30mg",
                "description": "Highly bioavailable zinc picolinate for immune function, skin health, and hormone balance.",
                "brand": "Syntropy Essentials",
                "category": "mineral",
                "price": 14.99,
                "image_url": "https://shop.syntropy.health/images/zinc.jpg",
                "product_url": "https://shop.syntropy.health/products/zinc-picolinate",
                "in_stock": True,
                "nutrients": {
                    "zinc": {"amount": 30, "unit": "mg", "daily_value_percent": 273}
                },
                "serving_size": {"amount": 1, "unit": "capsule", "servings_per_container": 120},
                "ingredients": ["Zinc Picolinate", "Vegetable Capsule"],
                "health_claims": ["Immune support", "Skin health", "Hormone balance"],
                "target_symptoms": ["immune", "skin"],
                "target_deficiencies": ["zinc"],
                "dietary_tags": ["vegan", "gluten_free"],
            },
        ]
