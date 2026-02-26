"""
Store Models

Generalized store configuration and integration schemas for the
Health Store Agent (HSA) factory pattern.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class StoreType(str, Enum):
    """Supported store types for HSA integration."""
    SHOP = "shop"
    AMAZON = "amazon"
    IHERB = "iherb"
    VITACOST = "vitacost"
    THRIVE_MARKET = "thrive_market"
    GENERIC = "generic"


class StoreConfig(BaseModel):
    """Configuration for a store adapter."""
    store_type: StoreType = Field(..., description="Type of store")
    api_key: Optional[str] = Field(default=None, description="API key for store access")
    api_secret: Optional[str] = Field(default=None, description="API secret")
    base_url: Optional[str] = Field(default=None, description="Base URL for store API")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Max retry attempts")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    enabled: bool = Field(default=True, description="Whether this store is enabled")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Extra configuration")

    class Config:
        use_enum_values = True


class StoreStatus(str, Enum):
    """Store adapter status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    INITIALIZING = "initializing"


class StoreInfo(BaseModel):
    """Information about a registered store."""
    store_type: StoreType
    store_name: str
    status: StoreStatus = StoreStatus.INACTIVE
    product_count: int = 0
    last_sync: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)


class StoreItemEvent(BaseModel):
    """Event for when a store item is added/updated."""
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    store_type: StoreType
    product_id: str
    action: str = Field(..., description="add, update, or remove")
    user_id: str
    product_data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[str] = None


class StoreSearchRequest(BaseModel):
    """Request to search products across stores."""
    query: str = Field(default="", description="Text search query")
    store_types: List[StoreType] = Field(default_factory=list, description="Stores to search")
    symptoms: List[str] = Field(default_factory=list, description="Target symptoms")
    deficiencies: List[str] = Field(default_factory=list, description="Nutrient deficiencies")
    dietary_requirements: List[str] = Field(default_factory=list)
    min_rating: Optional[float] = Field(default=None, ge=0, le=5)
    max_price: Optional[float] = Field(default=None, ge=0)
    limit: int = Field(default=10, ge=1, le=100)
    include_out_of_stock: bool = False


class StoreSearchResponse(BaseModel):
    """Response from store search."""
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    query: str
    stores_searched: List[StoreType]
    total_results: int
    results: List[Dict[str, Any]] = Field(default_factory=list)
    processing_time_ms: float = 0.0
