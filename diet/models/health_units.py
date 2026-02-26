"""
Health Unit Models for the Health Store Agent (HSA)

Defines standardized health units for normalizing products
from different stores into a unified format for vector storage and search.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .store import StoreType


class HealthCategory(str, Enum):
    """Health product categories."""
    SUPPLEMENT = "supplement"
    VITAMIN = "vitamin"
    MINERAL = "mineral"
    HERBAL = "herbal"
    PROTEIN = "protein"
    PROBIOTIC = "probiotic"
    OMEGA = "omega"
    AMINO_ACID = "amino_acid"
    SUPERFOOD = "superfood"
    FUNCTIONAL_FOOD = "functional_food"
    MEAL_REPLACEMENT = "meal_replacement"
    SPORTS_NUTRITION = "sports_nutrition"
    WELLNESS = "wellness"
    OTHER = "other"


class DietaryTag(str, Enum):
    """Dietary restriction and preference tags."""
    VEGAN = "vegan"
    VEGETARIAN = "vegetarian"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    SOY_FREE = "soy_free"
    NUT_FREE = "nut_free"
    ORGANIC = "organic"
    NON_GMO = "non_gmo"
    KOSHER = "kosher"
    HALAL = "halal"
    KETO = "keto"
    PALEO = "paleo"
    WHOLE30 = "whole30"
    LOW_SODIUM = "low_sodium"
    SUGAR_FREE = "sugar_free"


class AvailabilityStatus(str, Enum):
    """Product availability status."""
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    PREORDER = "preorder"
    DISCONTINUED = "discontinued"
    UNKNOWN = "unknown"


class NutrientValue(BaseModel):
    """Represents a nutrient amount with unit."""
    amount: float = Field(..., description="Nutrient amount")
    unit: str = Field(..., description="Unit of measurement (mg, g, mcg, IU)")
    daily_value_percent: Optional[float] = Field(
        default=None, description="Percentage of daily value"
    )


class ServingSize(BaseModel):
    """Serving size information."""
    amount: float = Field(..., description="Serving amount")
    unit: str = Field(..., description="Serving unit")
    servings_per_container: Optional[int] = Field(
        default=None, description="Number of servings per container"
    )
    description: Optional[str] = Field(
        default=None, description="Serving description (e.g., '2 capsules')"
    )


class MoneyAmount(BaseModel):
    """Monetary amount with currency."""
    amount: float = Field(..., ge=0, description="Price amount")
    currency: str = Field(default="USD", description="Currency code")

    def __str__(self) -> str:
        return f"{self.currency} {self.amount:.2f}"


class RawProduct(BaseModel):
    """Raw product data from a store before normalization."""
    source_store: StoreType = Field(..., description="Source store type")
    source_product_id: str = Field(..., description="Original product ID from store")
    raw_data: Dict[str, Any] = Field(..., description="Raw product data from API")
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    price: Optional[float] = Field(default=None)
    currency: Optional[str] = Field(default="USD")
    image_url: Optional[str] = Field(default=None)
    product_url: Optional[str] = Field(default=None)


class StandardizedHealthUnit(BaseModel):
    """
    Standardized health/wellness product unit.

    This is the normalized format stored in the vector database,
    enabling semantic search across products from different stores.
    """
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique unit ID")
    source_store: StoreType = Field(..., description="Source store type")
    source_product_id: str = Field(..., description="Original product ID from store")

    name: str = Field(..., description="Product name")
    description: str = Field(default="", description="Product description")
    brand: Optional[str] = Field(default=None, description="Brand name")

    category: HealthCategory = Field(..., description="Primary health category")
    subcategory: Optional[str] = Field(default=None, description="Subcategory")

    nutrients: Dict[str, NutrientValue] = Field(
        default_factory=dict, description="Nutrient content map"
    )
    serving_size: Optional[ServingSize] = Field(default=None, description="Serving info")
    ingredients: List[str] = Field(default_factory=list, description="Ingredient list")

    health_claims: List[str] = Field(
        default_factory=list, description="Health benefit claims"
    )
    target_symptoms: List[str] = Field(
        default_factory=list, description="Target symptoms/conditions"
    )
    target_deficiencies: List[str] = Field(
        default_factory=list, description="Target nutritional deficiencies"
    )

    allergens: List[str] = Field(default_factory=list, description="Allergen warnings")
    dietary_tags: List[DietaryTag] = Field(
        default_factory=list, description="Dietary restriction tags"
    )

    embedding: Optional[List[float]] = Field(
        default=None, description="Vector embedding for semantic search"
    )
    embedding_model: Optional[str] = Field(
        default=None, description="Model used for embedding"
    )

    price: Optional[MoneyAmount] = Field(default=None, description="Current price")
    price_per_serving: Optional[MoneyAmount] = Field(
        default=None, description="Price per serving"
    )
    availability: AvailabilityStatus = Field(
        default=AvailabilityStatus.UNKNOWN, description="Stock status"
    )

    product_url: Optional[str] = Field(default=None, description="Product page URL")
    affiliate_link: Optional[str] = Field(default=None, description="Affiliate link")
    image_url: Optional[str] = Field(default=None, description="Product image URL")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    quality_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Data quality score"
    )

    class Config:
        use_enum_values = True

    def to_embedding_text(self) -> str:
        """Generate text for creating embeddings."""
        parts = [
            f"Product: {self.name}",
            f"Category: {self.category}",
        ]

        if self.brand:
            parts.append(f"Brand: {self.brand}")

        if self.description:
            parts.append(f"Description: {self.description[:500]}")

        if self.health_claims:
            parts.append(f"Benefits: {', '.join(self.health_claims[:10])}")

        if self.target_symptoms:
            parts.append(f"For symptoms: {', '.join(self.target_symptoms[:10])}")

        if self.target_deficiencies:
            parts.append(f"Addresses deficiencies: {', '.join(self.target_deficiencies[:10])}")

        if self.nutrients:
            nutrient_str = ", ".join(
                f"{k}: {v.amount}{v.unit}" for k, v in list(self.nutrients.items())[:10]
            )
            parts.append(f"Nutrients: {nutrient_str}")

        if self.dietary_tags:
            parts.append(f"Dietary: {', '.join(str(t) for t in self.dietary_tags[:5])}")

        return " | ".join(parts)


class ProductSearchQuery(BaseModel):
    """Query parameters for product search."""
    query_text: Optional[str] = Field(default=None, description="Free-text search query")
    symptoms: List[str] = Field(default_factory=list, description="Target symptoms")
    deficiencies: List[str] = Field(default_factory=list, description="Target deficiencies")
    categories: List[HealthCategory] = Field(
        default_factory=list, description="Category filters"
    )
    dietary_requirements: List[DietaryTag] = Field(
        default_factory=list, description="Dietary requirements"
    )
    exclude_allergens: List[str] = Field(
        default_factory=list, description="Allergens to exclude"
    )
    max_price: Optional[float] = Field(default=None, description="Maximum price")
    min_quality_score: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Minimum quality score"
    )
    limit: int = Field(default=10, ge=1, le=100, description="Result limit")
    store_filter: Optional[StoreType] = Field(
        default=None, description="Filter by store type"
    )


class ProductSearchResult(BaseModel):
    """Result of a product search."""
    query: ProductSearchQuery = Field(..., description="Original query")
    products: List[StandardizedHealthUnit] = Field(
        default_factory=list, description="Matched products"
    )
    scores: Dict[str, float] = Field(
        default_factory=dict, description="Relevance scores by product ID"
    )
    total_found: int = Field(default=0, description="Total matching products")
    search_time_ms: float = Field(default=0.0, description="Search time in milliseconds")
