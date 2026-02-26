"""
Health Store Agent (HSA) - Ingress Layer

A pluggable ingress abstraction that integrates health/wellness stores
into the Syntropy system, normalizing products into standardized health units.

Architecture:
    ┌─────────────────────────────────────────┐
    │         HealthStoreFactory              │
    │  (creates adapters based on store type) │
    └─────────────────┬───────────────────────┘
                      │
         ┌────────────┼────────────┐
         │            │            │
         ▼            ▼            ▼
    ┌─────────┐  ┌─────────┐  ┌─────────┐
    │  Shop   │  │ Amazon  │  │ Generic │
    │ Adapter │  │ Adapter │  │ Adapter │
    └────┬────┘  └────┬────┘  └────┬────┘
         │            │            │
         └────────────┼────────────┘
                      │
                      ▼
              ┌───────────────┐
              │  Normalizer   │
              │ (Raw → Unit)  │
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │  Vector DB    │
              │ (Embeddings)  │
              └───────────────┘

Usage:
    from diet.health_store_agent import (
        HealthStoreFactory,
        AbstractStoreAdapter,
        ShopStoreAdapter,
        ProductNormalizer,
    )

    factory = HealthStoreFactory()
    adapter = factory.create_adapter(StoreType.SHOP)
    products = await adapter.search_products(query)
"""

from .adapters import AmazonStoreAdapter, ShopStoreAdapter
from .base_adapter import AbstractStoreAdapter
from .factory import HealthStoreFactory, get_health_store_factory
from .normalizer import ProductNormalizer, get_product_normalizer

__all__ = [
    # Factory
    "HealthStoreFactory",
    "get_health_store_factory",
    # Base
    "AbstractStoreAdapter",
    # Normalizer
    "ProductNormalizer",
    "get_product_normalizer",
    # Adapters
    "ShopStoreAdapter",
    "AmazonStoreAdapter",
]
