"""
Health Store Adapters

This package contains store-specific adapters for integrating
various health/wellness stores into the Syntropy system.
"""

from .amazon_adapter import AmazonStoreAdapter
from .shop_adapter import ShopStoreAdapter

__all__ = [
    "ShopStoreAdapter",
    "AmazonStoreAdapter",
]
