"""
Diet Insight Engine - FastAPI Application Package

Exports the main application and routers for SDO and HSA.
"""

from .main import app, create_app
from .routers import diet_insight_router

__all__ = [
    "app",
    "create_app",
    "diet_insight_router",
]
