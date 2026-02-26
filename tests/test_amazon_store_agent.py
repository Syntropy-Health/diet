"""
Tests for Amazon Store Agent

This module contains comprehensive tests for the Amazon product search
and affiliate link generation pipeline.
"""

import asyncio
import os
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

# Import using importlib for hyphenated directory names
import importlib.util
import sys

# Load modules directly
def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load all amazon-store-agent modules
agent_module = load_module("agent", "amazon-store-agent/agent.py")
affiliate_module = load_module("affiliate", "amazon-store-agent/affiliate.py")
search_module = load_module("search", "amazon-store-agent/search.py")
models_module = load_module("models", "amazon-store-agent/models.py")

# Extract classes and functions
AmazonStoreAgent = agent_module.AmazonStoreAgent
search_for_nutrient_deficiency = agent_module.search_for_nutrient_deficiency
AmazonAffiliateManager = affiliate_module.AmazonAffiliateManager
CommissionTracker = affiliate_module.CommissionTracker
AmazonSearchEngine = search_module.AmazonSearchEngine
ScamDetector = search_module.ScamDetector
NutritionMatcher = search_module.NutritionMatcher

# Extract model classes
ProductSearchQuery = models_module.ProductSearchQuery
ProductSearchResult = models_module.ProductSearchResult
AmazonProduct = models_module.AmazonProduct
AmazonProductPrice = models_module.AmazonProductPrice
AmazonProductReviews = models_module.AmazonProductReviews
AmazonProductReview = models_module.AmazonProductReview
ProductCategory = models_module.ProductCategory
ProductAvailability = models_module.ProductAvailability
ReviewVerification = models_module.ReviewVerification
NutritionFacts = models_module.NutritionFacts
AffiliateLink = models_module.AffiliateLink
SPAPICredentials = models_module.SPAPICredentials
NutrientDeficiency = models_module.NutrientDeficiency


@pytest.fixture
def mock_credentials():
    """Mock Amazon SP-API credentials for testing."""
    return SPAPICredentials(
        client_id="test_client_id",
        client_secret="test_client_secret",
        refresh_token="test_refresh_token",
        region="us-east-1",
        marketplace_id="ATVPDKIKX0DER",
        endpoint="https://sellingpartnerapi-na.amazon.com",
        associate_tag="test_associate_tag",
        access_key_id="test_access_key",
        secret_access_key="test_secret_key"
    )


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = AsyncMock()
    client.chat.completions.create.return_value = MagicMock()
    client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content="0.85"))
    ]
    return client


@pytest.fixture
def sample_product():
    """Sample Amazon product for testing."""
    price = AmazonProductPrice(
        amount=Decimal("29.99"),
        display_amount="$29.99",
        savings_amount=Decimal("5.00"),
        savings_percentage=14.3
    )

    reviews = AmazonProductReviews(
        total_reviews=1250,
        average_rating=4.5,
        verified_purchase_percentage=85.2,
        recent_reviews=[
            AmazonProductReview(
                review_id="R123456789",
                reviewer_name="Health Enthusiast",
                rating=5.0,
                title="Great iron supplement!",
                content="I've been taking this for 3 months and my energy levels have improved significantly.",
                date=datetime.now() - timedelta(days=30),
                verification_status=ReviewVerification.VERIFIED_PURCHASE,
                helpful_votes=25,
                total_votes=30
            )
        ]
    )

    nutrition_facts = NutritionFacts(
        serving_size="1 capsule",
        servings_per_container=90,
        nutrients={
            "Iron": "25mg (139% DV)",
            "Vitamin C": "60mg (67% DV)",
            "Folic Acid": "400mcg (100% DV)"
        },
        ingredients=["Iron Bisglycinate", "Vitamin C", "Cellulose", "Gelatin"]
    )

    return AmazonProduct(
        asin="B087TESTIR",
        title="Premium Iron Supplement with Vitamin C - 90 Capsules",
        brand="NutraLife",
        description="High-absorption iron supplement with vitamin C for enhanced bioavailability",
        category=ProductCategory.SUPPLEMENTS,
        price=price,
        availability=ProductAvailability.IN_STOCK,
        in_stock=True,
        reviews=reviews,
        image_urls=["https://images-na.ssl-images-amazon.com/images/I/test.jpg"],
        nutrition_facts=nutrition_facts,
        amazon_choice=True,
        best_seller=False
    )


class TestSPAPICredentials:
    """Test SP-API credentials validation."""

    def test_valid_credentials(self, mock_credentials):
        """Test valid credentials creation."""
        assert mock_credentials.client_id == "test_client_id"
        assert mock_credentials.associate_tag == "test_associate_tag"

    def test_invalid_credentials(self):
        """Test validation of invalid credentials."""
        with pytest.raises(ValueError, match="Credential field cannot be empty"):
            SPAPICredentials(
                client_id="",  # Empty client ID should fail
                client_secret="test_secret",
                refresh_token="test_token",
                associate_tag="test_tag",
                access_key_id="test_key",
                secret_access_key="test_secret"
            )


class TestAmazonProduct:
    """Test Amazon product model validation."""

    def test_valid_product(self, sample_product):
        """Test valid product creation."""
        assert sample_product.asin == "B087TESTIR"
        assert sample_product.reviews.average_rating == 4.5
        assert sample_product.nutrition_match_score == 0.0  # Default value

    def test_invalid_asin(self):
        """Test ASIN validation."""
        with pytest.raises(ValueError, match="ASIN must be exactly 10 characters"):
            AmazonProduct(
                asin="INVALID",  # Too short
                title="Test Product",
                description="Test description",
                category=ProductCategory.SUPPLEMENTS,
                price=AmazonProductPrice(amount=Decimal("10.00"), display_amount="$10.00"),
                availability=ProductAvailability.IN_STOCK,
                in_stock=True,
                reviews=AmazonProductReviews(total_reviews=10, average_rating=4.0)
            )

    def test_product_scores_validation(self, sample_product):
        """Test product score validation."""
        # Valid scores
        sample_product.search_relevance_score = 0.85
        sample_product.nutrition_match_score = 0.92

        # Invalid scores should raise validation error
        with pytest.raises(ValueError, match="Scores must be between 0.0 and 1.0"):
            sample_product.search_relevance_score = 1.5


class TestProductSearchQuery:
    """Test product search query validation."""

    def test_valid_query(self):
        """Test valid search query creation."""
        query = ProductSearchQuery(
            keywords=["iron", "supplement"],
            dietary_tags=["High Iron", "Easy Absorption"],
            min_rating=4.0,
            min_reviews=50,
            max_results=20
        )

        assert query.keywords == ["iron", "supplement"]
        assert query.min_rating == 4.0
        assert query.search_hops == 2

    def test_invalid_rating(self):
        """Test invalid rating validation."""
        with pytest.raises(ValueError, match="Minimum rating must be between 1.0 and 5.0"):
            ProductSearchQuery(
                keywords=["test"],
                min_rating=6.0  # Invalid rating
            )

    def test_invalid_max_results(self):
        """Test invalid max_results validation."""
        with pytest.raises(ValueError, match="Value must be positive"):
            ProductSearchQuery(
                keywords=["test"],
                max_results=0  # Invalid max_results
            )


class TestScamDetector:
    """Test scam detection functionality."""

    def test_clean_product(self, sample_product):
        """Test scam detection on a clean product."""
        indicators = ScamDetector.detect_scam_indicators(sample_product)
        assert indicators == 0  # Should be clean

    def test_scam_indicators(self):
        """Test detection of various scam indicators."""
        # Create a suspicious product
        scam_price = AmazonProductPrice(
            amount=Decimal("2.99"),  # Suspiciously low price
            display_amount="$2.99"
        )

        scam_reviews = AmazonProductReviews(
            total_reviews=5,  # Too few reviews
            average_rating=4.9,  # Suspiciously high rating
            verified_purchase_percentage=20.0  # Low verified percentage
        )

        scam_product = AmazonProduct(
            asin="B123SCAM99",
            title="MIRACLE Weight Loss Supplement - GUARANTEED Results!",  # Scam keywords
            brand="Generic",  # Suspicious brand
            description="Revolutionary breakthrough formula that doctors hate!",
            category=ProductCategory.SUPPLEMENTS,
            price=scam_price,
            availability=ProductAvailability.IN_STOCK,
            in_stock=True,
            reviews=scam_reviews
        )

        indicators = ScamDetector.detect_scam_indicators(scam_product)
        assert indicators > 3  # Should detect multiple scam indicators


class TestNutritionMatcher:
    """Test nutrition matching functionality."""

    @pytest.mark.asyncio
    async def test_nutrition_match_calculation(self, mock_openai_client, sample_product):
        """Test nutrition match score calculation."""
        matcher = NutritionMatcher(mock_openai_client)

        score = await matcher.calculate_nutrition_match_score(
            product=sample_product,
            dietary_tags=["High Iron"],
            target_nutrients=["Iron"]
        )

        assert 0.0 <= score <= 1.0
        mock_openai_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_nutrition_match_empty_requirements(self, mock_openai_client, sample_product):
        """Test nutrition matching with empty requirements."""
        matcher = NutritionMatcher(mock_openai_client)

        score = await matcher.calculate_nutrition_match_score(
            product=sample_product,
            dietary_tags=[],
            target_nutrients=[]
        )

        assert score == 0.0
        mock_openai_client.chat.completions.create.assert_not_called()


class TestAmazonAffiliateManager:
    """Test Amazon affiliate link management."""

    def test_affiliate_link_generation(self, mock_credentials, sample_product):
        """Test affiliate link generation."""
        manager = AmazonAffiliateManager(mock_credentials)

        link = manager.generate_affiliate_link(sample_product)

        assert link.asin == sample_product.asin
        assert mock_credentials.associate_tag in link.affiliate_url
        assert link.commission_rate > 0

    def test_bulk_affiliate_links(self, mock_credentials, sample_product):
        """Test bulk affiliate link generation."""
        manager = AmazonAffiliateManager(mock_credentials)

        products = [sample_product]
        links = manager.generate_bulk_affiliate_links(products)

        assert sample_product.asin in links
        assert links[sample_product.asin].affiliate_url is not None

    @pytest.mark.asyncio
    async def test_affiliate_link_validation(self, mock_credentials, sample_product):
        """Test affiliate link validation."""
        manager = AmazonAffiliateManager(mock_credentials)

        link = manager.generate_affiliate_link(sample_product)
        is_valid = await manager.validate_affiliate_link(link)

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_invalid_affiliate_link(self, mock_credentials):
        """Test validation of invalid affiliate link."""
        manager = AmazonAffiliateManager(mock_credentials)

        invalid_link = AffiliateLink(
            asin="B123TEST99",
            affiliate_url="https://invalid-url.com",  # Non-Amazon URL
            associate_tag="test_tag"
        )

        is_valid = await manager.validate_affiliate_link(invalid_link)
        assert is_valid is False


class TestCommissionTracker:
    """Test commission tracking functionality."""

    def test_commission_calculation(self, mock_credentials, sample_product):
        """Test commission calculation."""
        tracker = CommissionTracker(mock_credentials)

        commission = tracker.calculate_estimated_commission(sample_product, quantity=1)

        assert commission > 0
        assert isinstance(commission, float)

    def test_commission_analysis(self, mock_credentials, sample_product):
        """Test commission potential analysis."""
        tracker = CommissionTracker(mock_credentials)

        analysis = tracker.analyze_commission_potential([sample_product])

        assert "total_products" in analysis
        assert "total_commission_potential" in analysis
        assert analysis["total_products"] == 1


class TestAmazonSearchEngine:
    """Test Amazon search engine functionality."""

    @pytest.mark.asyncio
    async def test_search_products(self, mock_credentials, mock_openai_client):
        """Test product search pipeline."""
        async with AmazonSearchEngine(mock_credentials, mock_openai_client) as engine:
            query = ProductSearchQuery(
                keywords=["iron", "supplement"],
                min_rating=4.0,
                min_reviews=10,
                max_results=5
            )

            result = await engine.search_products(query)

            assert isinstance(result, ProductSearchResult)
            assert result.query == query
            assert len(result.products) <= query.max_results

    @pytest.mark.asyncio
    async def test_search_with_nutrition_requirements(self, mock_credentials, mock_openai_client):
        """Test search with nutritional requirements."""
        async with AmazonSearchEngine(mock_credentials, mock_openai_client) as engine:
            query = ProductSearchQuery(
                keywords=["iron"],
                dietary_tags=["High Iron"],
                nutrient_deficiencies=[NutrientDeficiency.IRON],
                max_results=3
            )

            result = await engine.search_products(query)

            assert isinstance(result, ProductSearchResult)
            # Products should have nutrition match scores calculated
            for product in result.products:
                assert 0.0 <= product.nutrition_match_score <= 1.0


class TestAmazonStoreAgent:
    """Test the main Amazon Store Agent."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self, mock_credentials):
        """Test agent initialization."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            agent = AmazonStoreAgent(sp_api_credentials=mock_credentials)
            assert agent.credentials == mock_credentials

    @pytest.mark.asyncio
    async def test_search_products_for_nutrients(self, mock_credentials):
        """Test nutrient-based product search."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            async with AmazonStoreAgent(sp_api_credentials=mock_credentials) as agent:
                result = await agent.search_products_for_nutrients(
                    dietary_tags=["High Iron"],
                    max_results=3
                )

                assert isinstance(result, ProductSearchResult)
                assert len(result.products) <= 3

    @pytest.mark.asyncio
    async def test_create_nutrition_bundle(self, mock_credentials):
        """Test nutrition bundle creation."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            async with AmazonStoreAgent(sp_api_credentials=mock_credentials) as agent:
                bundle = await agent.create_nutrition_bundle(
                    target_nutrients=["Iron", "Vitamin D"],
                    budget_limit=100.0
                )

                assert "bundle_items" in bundle
                assert "total_cost" in bundle
                assert "budget_compliant" in bundle

    @pytest.mark.asyncio
    async def test_find_supplement_alternatives(self, mock_credentials):
        """Test finding supplement alternatives."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            async with AmazonStoreAgent(sp_api_credentials=mock_credentials) as agent:
                result = await agent.find_supplement_alternatives(
                    primary_keywords=["iron"],
                    avoid_ingredients=["titanium dioxide"],
                    max_results=5
                )

                assert isinstance(result, ProductSearchResult)
                assert len(result.products) <= 5


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.mark.asyncio
    async def test_search_for_nutrient_deficiency(self, mock_credentials):
        """Test convenience function for nutrient deficiency search."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            result = await search_for_nutrient_deficiency(
                deficiency=NutrientDeficiency.IRON,
                credentials=mock_credentials,
                max_results=3
            )

            assert isinstance(result, ProductSearchResult)
            assert len(result.products) <= 3


class TestIntegration:
    """Integration tests for the complete pipeline."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_pipeline(self, mock_credentials):
        """Test the complete search-to-affiliate pipeline."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            async with AmazonStoreAgent(sp_api_credentials=mock_credentials) as agent:
                # Perform search
                result = await agent.search_products_for_nutrients(
                    dietary_tags=["High Iron", "Easy Absorption"],
                    max_results=2
                )

                # Verify search results
                assert isinstance(result, ProductSearchResult)
                assert len(result.products) <= 2

                # Verify affiliate links are generated
                for product in result.products:
                    assert product.asin in result.affiliate_links
                    affiliate_link = result.affiliate_links[product.asin]
                    assert "amazon.com" in affiliate_link["affiliate_url"]
                    assert mock_credentials.associate_tag in affiliate_link["affiliate_url"]

                # Verify quality filtering worked
                for product in result.products:
                    assert product.reviews.average_rating >= 4.0
                    assert product.reviews.total_reviews >= 10

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_market_analysis(self, mock_credentials):
        """Test market trend analysis."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            async with AmazonStoreAgent(sp_api_credentials=mock_credentials) as agent:
                analysis = await agent.analyze_market_trends(
                    product_category=ProductCategory.SUPPLEMENTS
                )

                assert "total_products_analyzed" in analysis
                assert "price_distribution" in analysis
                assert "rating_distribution" in analysis
                assert "commission_potential" in analysis


# Fixtures for running tests with different configurations
@pytest.fixture(params=[
    {"mock_apis": True, "rate_limit": False},
    {"mock_apis": True, "rate_limit": True},
])
def test_config(request):
    """Test configuration fixture."""
    return request.param


@pytest.mark.parametrize("dietary_tags,expected_min_results", [
    (["High Iron"], 1),
    (["High Iron", "Easy Absorption"], 1),
    (["Vitamin D", "High Potency"], 1),
    (["Omega 3", "Fish Oil"], 1),
])
@pytest.mark.asyncio
async def test_various_nutrient_searches(dietary_tags, expected_min_results, mock_credentials):
    """Test searches for various nutrient combinations."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
        async with AmazonStoreAgent(sp_api_credentials=mock_credentials) as agent:
            result = await agent.search_products_for_nutrients(
                dietary_tags=dietary_tags,
                max_results=5
            )

            assert len(result.products) >= expected_min_results

            # Verify all products have required fields
            for product in result.products:
                assert product.asin
                assert product.title
                assert product.price.amount > 0
                assert 1.0 <= product.reviews.average_rating <= 5.0
