"""
Diet Insight Engine - API Routers

Routes:
- /symptoms: SDO symptom processing endpoints
- /products: HSA product search and management
- /stores: Store information
"""

from .diet_insight import router as diet_insight_router

__all__ = [
    "diet_insight_router",
]
