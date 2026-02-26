"""
Amazon Store Adapter

This adapter provides integration with Amazon's product catalog
for health/wellness product recommendations.
"""

import logging
from typing import List, Optional

from diet.health_store_agent.base_adapter import AbstractStoreAdapter
from diet.health_store_agent.factory import HealthStoreFactory, StoreConfig
from diet.health_store_agent.normalizer import get_product_normalizer
from diet.models.health_units import (
    ProductSearchQuery,
    RawProduct,
    StandardizedHealthUnit,
)
from diet.models.store import StoreType

logger = logging.getLogger(__name__)


@HealthStoreFactory.register(StoreType.AMAZON)
class AmazonStoreAdapter(AbstractStoreAdapter):
    """
    Adapter for Amazon store integration.

    This adapter wraps the existing amazon_store_agent functionality
    to provide a consistent interface through the HSA factory pattern.
    """

    def __init__(self, config: Optional[StoreConfig] = None):
        self.config = config or StoreConfig()
        self.logger = logging.getLogger(f"{__name__}.AmazonStoreAdapter")
        self._initialized = False
        self._normalizer = get_product_normalizer()
        self._amazon_agent = None

    @property
    def store_type(self) -> StoreType:
        return StoreType.AMAZON

    @property
    def store_name(self) -> str:
        return "Amazon"

    async def initialize(self) -> None:
        """Initialize the Amazon adapter."""
        if self._initialized:
            return

        self.logger.info("Initializing Amazon Store Adapter")

        try:
            from diet.amazon_store_agent.agent import AmazonProductAgent
            self._amazon_agent = AmazonProductAgent()
            await self._amazon_agent.initialize()
        except ImportError:
            self.logger.warning("Amazon store agent not available, using mock mode")
            self._amazon_agent = None
        except Exception as e:
            self.logger.error(f"Failed to initialize Amazon agent: {e}")
            self._amazon_agent = None

        self._initialized = True

    async def shutdown(self) -> None:
        """Clean up adapter resources."""
        self.logger.info("Shutting down Amazon Store Adapter")
        if self._amazon_agent:
            try:
                await self._amazon_agent.shutdown()
            except Exception as e:
                self.logger.error(f"Error shutting down Amazon agent: {e}")
        self._amazon_agent = None
        self._initialized = False

    async def search_products(
        self,
        query: ProductSearchQuery,
    ) -> List[RawProduct]:
        """
        Search for products on Amazon.

        Args:
            query: Search query with filters

        Returns:
            List of raw products
        """
        if not self._initialized:
            await self.initialize()

        self.logger.debug(f"Searching Amazon for: {query.query_text}")

        if self._amazon_agent is None:
            self.logger.warning("Amazon agent not available, returning empty results")
            return []

        try:
            search_text = query.query_text or ""
            if query.symptoms:
                search_text += " " + " ".join(query.symptoms)
            if query.deficiencies:
                search_text += " " + " ".join(query.deficiencies)

            results = await self._amazon_agent.search(
                query=search_text.strip(),
                category="Health & Personal Care",
                max_results=query.limit,
            )

            raw_products = []
            for item in results:
                raw_product = RawProduct(
                    source_store=StoreType.AMAZON,
                    source_product_id=item.get("asin", ""),
                    raw_data=item,
                    name=item.get("title"),
                    description=item.get("description", ""),
                    price=item.get("price"),
                    currency="USD",
                    image_url=item.get("image_url"),
                    product_url=item.get("detail_page_url"),
                )
                raw_products.append(raw_product)

            return raw_products

        except Exception as e:
            self.logger.error(f"Amazon search failed: {e}")
            return []

    async def get_product_details(
        self,
        product_id: str,
    ) -> Optional[RawProduct]:
        """
        Get detailed product information from Amazon.

        Args:
            product_id: Amazon ASIN

        Returns:
            Raw product data or None
        """
        if not self._initialized:
            await self.initialize()

        if self._amazon_agent is None:
            return None

        try:
            item = await self._amazon_agent.get_product(product_id)
            if item:
                return RawProduct(
                    source_store=StoreType.AMAZON,
                    source_product_id=product_id,
                    raw_data=item,
                    name=item.get("title"),
                    description=item.get("description", ""),
                    price=item.get("price"),
                    currency="USD",
                    image_url=item.get("image_url"),
                    product_url=item.get("detail_page_url"),
                )
        except Exception as e:
            self.logger.error(f"Failed to get Amazon product {product_id}: {e}")

        return None

    def normalize_product(
        self,
        raw_product: RawProduct,
    ) -> StandardizedHealthUnit:
        """
        Normalize an Amazon product to a standardized health unit.

        Args:
            raw_product: Raw product from Amazon

        Returns:
            Standardized health unit
        """
        return self._normalizer.normalize(raw_product)
