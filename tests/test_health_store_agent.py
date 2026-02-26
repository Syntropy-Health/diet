"""
Tests for the Health Store Agent (HSA)

Tests cover:
- Factory pattern and adapter registration
- Shop adapter product search and normalization
- Product normalizer functionality
- Standardized health unit creation
"""

import asyncio
from datetime import datetime

import pytest

from diet.health_store_agent.adapters.shop_adapter import ShopStoreAdapter
from diet.health_store_agent.factory import (
    HealthStoreFactory,
    StoreConfig,
    get_health_store_factory,
)
from diet.health_store_agent.normalizer import (
    ProductNormalizer,
    get_product_normalizer,
)
from diet.models.health_units import (
    AvailabilityStatus,
    DietaryTag,
    HealthCategory,
    ProductSearchQuery,
    RawProduct,
    StandardizedHealthUnit,
)
from diet.models.store import StoreType


class TestHealthStoreFactory:
    """Tests for the HealthStoreFactory."""

    def test_shop_adapter_registered(self):
        """Test that Shop adapter is registered."""
        assert HealthStoreFactory.is_registered(StoreType.SHOP)

    def test_amazon_adapter_registered(self):
        """Test that Amazon adapter is registered."""
        assert HealthStoreFactory.is_registered(StoreType.AMAZON)

    def test_create_shop_adapter(self):
        """Test creating a Shop adapter."""
        adapter = HealthStoreFactory.create(StoreType.SHOP)
        assert adapter is not None
        assert adapter.store_type == StoreType.SHOP
        assert adapter.store_name == "Syntropy Shop"

    def test_singleton_behavior(self):
        """Test that singleton mode returns same instance."""
        HealthStoreFactory.clear_instances()

        adapter1 = HealthStoreFactory.create(StoreType.SHOP, singleton=True)
        adapter2 = HealthStoreFactory.create(StoreType.SHOP, singleton=True)

        assert adapter1 is adapter2

    def test_non_singleton_creates_new(self):
        """Test that non-singleton mode creates new instances."""
        HealthStoreFactory.clear_instances()

        adapter1 = HealthStoreFactory.create(StoreType.SHOP, singleton=False)
        adapter2 = HealthStoreFactory.create(StoreType.SHOP, singleton=False)

        assert adapter1 is not adapter2

    def test_available_stores(self):
        """Test listing available stores."""
        stores = HealthStoreFactory.get_available_stores()
        assert StoreType.SHOP in stores

    def test_unregistered_store_raises(self):
        """Test that creating unregistered store raises error."""
        with pytest.raises(ValueError):
            HealthStoreFactory.create(StoreType.GENERIC)

    def test_factory_singleton(self):
        """Test global factory singleton."""
        factory1 = get_health_store_factory()
        factory2 = get_health_store_factory()
        assert factory1 is factory2


class TestShopStoreAdapter:
    """Tests for the ShopStoreAdapter."""

    @pytest.fixture
    def adapter(self):
        HealthStoreFactory.clear_instances()
        return HealthStoreFactory.create(StoreType.SHOP, singleton=False)

    @pytest.mark.asyncio
    async def test_initialization(self, adapter):
        """Test adapter initialization."""
        await adapter.initialize()
        assert adapter._initialized
        assert len(adapter._mock_products) > 0

    @pytest.mark.asyncio
    async def test_search_by_text(self, adapter):
        """Test product search by text query."""
        await adapter.initialize()

        query = ProductSearchQuery(query_text="vitamin d")
        results = await adapter.search_products(query)

        assert len(results) > 0
        assert any("vitamin" in p.name.lower() for p in results)

    @pytest.mark.asyncio
    async def test_search_by_deficiency(self, adapter):
        """Test product search by deficiency."""
        await adapter.initialize()

        query = ProductSearchQuery(deficiencies=["iron"])
        results = await adapter.search_products(query)

        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_by_symptoms(self, adapter):
        """Test product search by symptoms."""
        await adapter.initialize()

        query = ProductSearchQuery(symptoms=["fatigue", "stress"])
        results = await adapter.search_products(query)

        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_limit(self, adapter):
        """Test that search respects limit parameter."""
        await adapter.initialize()

        query = ProductSearchQuery(query_text="", limit=3)
        results = await adapter.search_products(query)

        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_get_product_details(self, adapter):
        """Test getting product details by ID."""
        await adapter.initialize()

        product = await adapter.get_product_details("shop-001")

        assert product is not None
        assert product.source_product_id == "shop-001"
        assert product.name is not None

    @pytest.mark.asyncio
    async def test_get_nonexistent_product(self, adapter):
        """Test getting non-existent product returns None."""
        await adapter.initialize()

        product = await adapter.get_product_details("nonexistent-id")
        assert product is None

    @pytest.mark.asyncio
    async def test_normalize_product(self, adapter):
        """Test product normalization."""
        await adapter.initialize()

        raw_product = await adapter.get_product_details("shop-001")
        normalized = adapter.normalize_product(raw_product)

        assert isinstance(normalized, StandardizedHealthUnit)
        assert normalized.source_store == StoreType.SHOP
        assert normalized.name == raw_product.name

    @pytest.mark.asyncio
    async def test_search_and_normalize(self, adapter):
        """Test combined search and normalize."""
        await adapter.initialize()

        query = ProductSearchQuery(query_text="magnesium", limit=3)
        units = await adapter.search_and_normalize(query)

        assert all(isinstance(u, StandardizedHealthUnit) for u in units)

    @pytest.mark.asyncio
    async def test_shutdown(self, adapter):
        """Test adapter shutdown."""
        await adapter.initialize()
        await adapter.shutdown()

        assert not adapter._initialized
        assert len(adapter._mock_products) == 0


class TestProductNormalizer:
    """Tests for the ProductNormalizer."""

    @pytest.fixture
    def normalizer(self):
        return ProductNormalizer()

    @pytest.fixture
    def sample_raw_product(self):
        return RawProduct(
            source_store=StoreType.SHOP,
            source_product_id="test-001",
            raw_data={
                "brand": "Test Brand",
                "category": "vitamin",
                "ingredients": ["Vitamin D3", "MCT Oil"],
                "nutrients": {
                    "vitamin_d": {"amount": 5000, "unit": "IU", "daily_value_percent": 625}
                },
                "serving_size": {"amount": 1, "unit": "softgel", "servings_per_container": 60},
                "health_claims": ["Immune support", "Bone health"],
                "dietary_tags": ["gluten_free"],
                "in_stock": True,
            },
            name="Vitamin D3 5000 IU",
            description="High-potency vitamin D3 supplement for immune and bone health. Non-GMO, gluten-free formula.",
            price=19.99,
            currency="USD",
            image_url="https://example.com/vitamin-d.jpg",
            product_url="https://example.com/products/vitamin-d",
        )

    def test_normalize_basic_fields(self, normalizer, sample_raw_product):
        """Test normalization of basic product fields."""
        unit = normalizer.normalize(sample_raw_product)

        assert unit.name == sample_raw_product.name
        assert unit.description == sample_raw_product.description
        assert unit.source_store == StoreType.SHOP
        assert unit.source_product_id == "test-001"

    def test_category_extraction(self, normalizer, sample_raw_product):
        """Test category extraction from product."""
        unit = normalizer.normalize(sample_raw_product)

        assert unit.category == HealthCategory.VITAMIN

    def test_dietary_tag_extraction(self, normalizer, sample_raw_product):
        """Test dietary tag extraction."""
        unit = normalizer.normalize(sample_raw_product)

        assert DietaryTag.GLUTEN_FREE in unit.dietary_tags
        assert DietaryTag.NON_GMO in unit.dietary_tags

    def test_target_symptoms_extraction(self, normalizer, sample_raw_product):
        """Test target symptoms extraction."""
        unit = normalizer.normalize(sample_raw_product)

        assert "immune" in unit.target_symptoms

    def test_target_deficiencies_extraction(self, normalizer, sample_raw_product):
        """Test target deficiencies extraction."""
        unit = normalizer.normalize(sample_raw_product)

        assert "vitamin_d" in unit.target_deficiencies

    def test_nutrient_extraction(self, normalizer, sample_raw_product):
        """Test nutrient value extraction."""
        unit = normalizer.normalize(sample_raw_product)

        assert "vitamin_d" in unit.nutrients
        assert unit.nutrients["vitamin_d"].amount == 5000
        assert unit.nutrients["vitamin_d"].unit == "IU"

    def test_price_extraction(self, normalizer, sample_raw_product):
        """Test price extraction."""
        unit = normalizer.normalize(sample_raw_product)

        assert unit.price is not None
        assert unit.price.amount == 19.99
        assert unit.price.currency == "USD"

    def test_availability_extraction(self, normalizer, sample_raw_product):
        """Test availability status extraction."""
        unit = normalizer.normalize(sample_raw_product)

        assert unit.availability == AvailabilityStatus.IN_STOCK

    def test_quality_score_calculation(self, normalizer, sample_raw_product):
        """Test quality score is calculated."""
        unit = normalizer.normalize(sample_raw_product)

        assert unit.quality_score > 0.5

    def test_embedding_text_generation(self, normalizer, sample_raw_product):
        """Test embedding text generation."""
        unit = normalizer.normalize(sample_raw_product)
        text = unit.to_embedding_text()

        assert "Vitamin D3 5000 IU" in text
        assert "vitamin" in text.lower()

    def test_normalizer_singleton(self):
        """Test global normalizer singleton."""
        norm1 = get_product_normalizer()
        norm2 = get_product_normalizer()
        assert norm1 is norm2


class TestStandardizedHealthUnit:
    """Tests for the StandardizedHealthUnit model."""

    def test_unit_creation(self):
        """Test basic unit creation."""
        unit = StandardizedHealthUnit(
            source_store=StoreType.SHOP,
            source_product_id="test-001",
            name="Test Product",
            category=HealthCategory.SUPPLEMENT,
        )

        assert unit.id is not None
        assert unit.name == "Test Product"
        assert unit.category == HealthCategory.SUPPLEMENT

    def test_embedding_text_minimal(self):
        """Test embedding text with minimal data."""
        unit = StandardizedHealthUnit(
            source_store=StoreType.SHOP,
            source_product_id="test-002",
            name="Minimal Product",
            category=HealthCategory.OTHER,
        )

        text = unit.to_embedding_text()
        assert "Minimal Product" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
