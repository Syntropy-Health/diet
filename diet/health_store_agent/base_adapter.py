"""
Abstract Base Adapter for Health Store Integration

This module defines the abstract interface that all store adapters must implement,
enabling pluggable integration of different health/wellness stores.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from diet.models.health_units import (
    HealthCategory,
    ProductSearchQuery,
    RawProduct,
    StandardizedHealthUnit,
)
from diet.models.store import StoreType


class AbstractStoreAdapter(ABC):
    """
    Abstract base class for health store adapters.

    All store integrations (Shop, Amazon, iHerb, etc.) must implement this interface
    to provide a consistent API for product search and normalization.
    """

    @property
    @abstractmethod
    def store_type(self) -> StoreType:
        """Return the store type this adapter handles."""
        pass

    @property
    @abstractmethod
    def store_name(self) -> str:
        """Return a human-readable store name."""
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the adapter with any required setup.

        This may include:
        - API authentication
        - Connection pooling
        - Cache initialization
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Clean up adapter resources.

        This should:
        - Close connections
        - Flush caches
        - Release resources
        """
        pass

    @abstractmethod
    async def search_products(
        self,
        query: ProductSearchQuery,
    ) -> List[RawProduct]:
        """
        Search for products matching the query.

        Args:
            query: Search query with filters and parameters

        Returns:
            List of raw products from the store
        """
        pass

    @abstractmethod
    async def get_product_details(
        self,
        product_id: str,
    ) -> Optional[RawProduct]:
        """
        Get detailed information for a specific product.

        Args:
            product_id: Store-specific product identifier

        Returns:
            Raw product data or None if not found
        """
        pass

    @abstractmethod
    def normalize_product(
        self,
        raw_product: RawProduct,
    ) -> StandardizedHealthUnit:
        """
        Normalize a raw product to a standardized health unit.

        Args:
            raw_product: Raw product data from the store

        Returns:
            Standardized health unit for vector storage
        """
        pass

    async def search_and_normalize(
        self,
        query: ProductSearchQuery,
    ) -> List[StandardizedHealthUnit]:
        """
        Search for products and normalize results.

        This is a convenience method that combines search and normalization.

        Args:
            query: Search query with filters

        Returns:
            List of standardized health units
        """
        raw_products = await self.search_products(query)
        return [self.normalize_product(p) for p in raw_products]

    def _extract_category(
        self,
        raw_data: Dict[str, Any],
        default: HealthCategory = HealthCategory.OTHER,
    ) -> HealthCategory:
        """
        Extract health category from raw product data.

        Override in subclasses for store-specific category mapping.
        """
        category_mapping = {
            "vitamin": HealthCategory.VITAMIN,
            "vitamins": HealthCategory.VITAMIN,
            "mineral": HealthCategory.MINERAL,
            "minerals": HealthCategory.MINERAL,
            "supplement": HealthCategory.SUPPLEMENT,
            "supplements": HealthCategory.SUPPLEMENT,
            "herbal": HealthCategory.HERBAL,
            "herb": HealthCategory.HERBAL,
            "protein": HealthCategory.PROTEIN,
            "probiotic": HealthCategory.PROBIOTIC,
            "probiotics": HealthCategory.PROBIOTIC,
            "omega": HealthCategory.OMEGA,
            "fish oil": HealthCategory.OMEGA,
            "amino": HealthCategory.AMINO_ACID,
            "superfood": HealthCategory.SUPERFOOD,
            "meal replacement": HealthCategory.MEAL_REPLACEMENT,
            "sports": HealthCategory.SPORTS_NUTRITION,
            "wellness": HealthCategory.WELLNESS,
        }

        category_str = raw_data.get("category", "").lower()
        for key, cat in category_mapping.items():
            if key in category_str:
                return cat

        return default

    def _extract_dietary_tags(self, raw_data: Dict[str, Any]) -> List[str]:
        """
        Extract dietary tags from raw product data.

        Override in subclasses for store-specific tag extraction.
        """
        tags = []
        text = str(raw_data).lower()

        tag_keywords = {
            "vegan": "vegan",
            "vegetarian": "vegetarian",
            "gluten-free": "gluten_free",
            "gluten free": "gluten_free",
            "dairy-free": "dairy_free",
            "dairy free": "dairy_free",
            "organic": "organic",
            "non-gmo": "non_gmo",
            "non gmo": "non_gmo",
            "kosher": "kosher",
            "halal": "halal",
            "keto": "keto",
            "paleo": "paleo",
            "sugar-free": "sugar_free",
            "sugar free": "sugar_free",
        }

        for keyword, tag in tag_keywords.items():
            if keyword in text and tag not in tags:
                tags.append(tag)

        return tags

    def _calculate_quality_score(self, raw_product: RawProduct) -> float:
        """
        Calculate data quality score for a product.

        Higher scores indicate more complete/reliable data.
        """
        score = 0.0
        max_score = 0.0

        if raw_product.name:
            score += 0.2
        max_score += 0.2

        if raw_product.description and len(raw_product.description) > 50:
            score += 0.2
        max_score += 0.2

        if raw_product.price is not None:
            score += 0.15
        max_score += 0.15

        if raw_product.image_url:
            score += 0.1
        max_score += 0.1

        if raw_product.product_url:
            score += 0.1
        max_score += 0.1

        raw_data = raw_product.raw_data
        if raw_data.get("ingredients"):
            score += 0.15
        max_score += 0.15

        if raw_data.get("nutrition_facts") or raw_data.get("nutrients"):
            score += 0.1
        max_score += 0.1

        return score / max_score if max_score > 0 else 0.5
