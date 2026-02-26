"""
Health Store Agent Factory

Creates store-specific adapters based on store type.
Follows the Factory Method pattern for extensibility.
"""

import logging
from typing import Any, Dict, List, Optional, Type

from diet.models.store import StoreType

logger = logging.getLogger(__name__)


class StoreConfig:
    """Configuration for a store adapter."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        cache_ttl: int = 3600,
        extra: Optional[Dict[str, Any]] = None,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.cache_ttl = cache_ttl
        self.extra = extra or {}


class HealthStoreFactory:
    """
    Factory for creating health store adapters.

    Usage:
        factory = HealthStoreFactory()
        adapter = factory.create(StoreType.SHOP)
        products = await adapter.search_products(query)
    """

    _adapters: Dict[StoreType, Type] = {}
    _instances: Dict[StoreType, Any] = {}

    @classmethod
    def register(cls, store_type: StoreType):
        """
        Decorator to register an adapter class for a store type.

        Usage:
            @HealthStoreFactory.register(StoreType.SHOP)
            class ShopAdapter(AbstractStoreAdapter):
                ...
        """
        def decorator(adapter_class: Type):
            cls._adapters[store_type] = adapter_class
            logger.debug(f"Registered adapter for {store_type}: {adapter_class.__name__}")
            return adapter_class
        return decorator

    @classmethod
    def create(
        cls,
        store_type: StoreType,
        config: Optional[StoreConfig] = None,
        singleton: bool = True,
    ):
        """
        Create an adapter instance for the specified store type.

        Args:
            store_type: The type of store to create an adapter for
            config: Optional configuration for the adapter
            singleton: If True, reuse existing instance

        Returns:
            Store adapter instance

        Raises:
            ValueError: If no adapter is registered for the store type
        """
        if singleton and store_type in cls._instances:
            return cls._instances[store_type]

        if store_type not in cls._adapters:
            available = list(cls._adapters.keys())
            raise ValueError(
                f"No adapter registered for store type: {store_type}. "
                f"Available adapters: {available}"
            )

        adapter_class = cls._adapters[store_type]
        adapter = adapter_class(config)

        if singleton:
            cls._instances[store_type] = adapter

        logger.info(f"Created adapter for {store_type}")
        return adapter

    @classmethod
    def get_available_stores(cls) -> List[StoreType]:
        """Return list of store types with registered adapters."""
        return list(cls._adapters.keys())

    @classmethod
    def is_registered(cls, store_type: StoreType) -> bool:
        """Check if an adapter is registered for the given store type."""
        return store_type in cls._adapters

    @classmethod
    def clear_instances(cls) -> None:
        """Clear all singleton instances (useful for testing)."""
        cls._instances.clear()


_factory_instance: Optional[HealthStoreFactory] = None


def get_health_store_factory() -> HealthStoreFactory:
    """Get or create the global factory instance."""
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = HealthStoreFactory()
    return _factory_instance


def _register_default_adapters():
    """Register the default adapters. Called on module import."""
    try:
        from .adapters import AmazonStoreAdapter, ShopStoreAdapter
    except ImportError:
        logger.warning("Could not import default adapters")


_register_default_adapters()
