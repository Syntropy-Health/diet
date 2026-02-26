"""
Diet Insight API Router

Provides endpoints for:
- SDO (Symptom-Diet Optimizer): Symptom reporting and analysis
- HSA (Health Store Agent): Product search and management
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services import get_notification_service
from diet.health_store_agent import HealthStoreFactory
from diet.models import (
    AlertLevel,
    ProductSearchQuery,
    StoreType,
    SymptomInput,
    SymptomReportedEvent,
)
from diet.models.errors import ProblemDetail
from diet.models.responses import (
    RecommendationResponse,
    SymptomAnalysisResponse,
)
from diet.models.store import (
    StoreInfo,
    StoreItemEvent,
    StoreSearchRequest,
    StoreSearchResponse,
    StoreStatus,
)
from diet.sdo import get_sdo_engine

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class SymptomContext(BaseModel):
    """Context for symptom reporting."""
    recent_foods: List[str] = Field(default_factory=list)
    sleep_hours: Optional[float] = None
    stress_level: Optional[int] = Field(default=None, ge=1, le=10)
    exercise_minutes: Optional[int] = None


class SymptomReportRequest(BaseModel):
    """Request to report symptoms."""
    user_id: str = Field(..., description="User identifier")
    symptoms: List[SymptomInput] = Field(..., min_length=1)
    context: Optional[SymptomContext] = None


class SymptomReportResponse(BaseModel):
    """Response from symptom processing."""
    process_id: str
    user_id: str
    success: bool
    processing_time_ms: float
    analysis: Optional[SymptomAnalysisResponse] = None
    recommendations: Optional[RecommendationResponse] = None
    notification: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BatchSymptomRequest(BaseModel):
    """Batch symptom processing request."""
    events: List[SymptomReportRequest]


class BatchSymptomResponse(BaseModel):
    """Batch symptom processing response."""
    total: int
    successful: int
    failed: int
    results: List[SymptomReportResponse]


class ProductAddRequest(BaseModel):
    """Request to add a product."""
    store_type: StoreType
    user_id: str
    product: Dict[str, Any]


class ProductAddResponse(BaseModel):
    """Response from product addition."""
    success: bool
    event_id: str
    product_id: Optional[str] = None
    message: str
    standardized_unit: Optional[Dict[str, Any]] = None


# =============================================================================
# SDO Endpoints - Symptom Processing
# =============================================================================

async def _process_single_symptom(request: SymptomReportRequest) -> SymptomReportResponse:
    """
    Core symptom processing logic.

    Runs the SDO pipeline for a single symptom report and returns a structured response.
    Extracted to avoid the batch endpoint calling the route handler directly
    (which would bypass middleware/DI).
    """
    engine = get_sdo_engine()
    await engine.initialize()

    event = SymptomReportedEvent(
        user_id=request.user_id,
        symptoms=request.symptoms,
        recent_foods=request.context.recent_foods if request.context else [],
        sleep_hours=request.context.sleep_hours if request.context else None,
        stress_level=request.context.stress_level if request.context else None,
        exercise_minutes=request.context.exercise_minutes if request.context else None,
    )

    result = await engine.process_symptoms(event)

    response = SymptomReportResponse(
        process_id=result.process_id,
        user_id=result.user_id,
        success=result.success,
        processing_time_ms=result.processing_time_ms,
        error=result.error,
    )

    if result.analysis:
        response.analysis = SymptomAnalysisResponse(
            insights=[i.model_dump() for i in result.analysis.insights],
            deficiencies=[d.model_dump() for d in result.analysis.deficiencies],
            patterns_detected=len(result.analysis.patterns_detected),
            severity_score=result.analysis.severity_score,
            confidence_score=result.analysis.confidence_score,
        )

    if result.recommendations:
        response.recommendations = RecommendationResponse(
            dietary_recommendations=[
                r.model_dump() for r in result.recommendations.dietary_recommendations
            ],
            supplement_recommendations=[
                r.model_dump() for r in result.recommendations.supplement_recommendations
            ],
            lifestyle_recommendations=[
                r.model_dump() for r in result.recommendations.lifestyle_recommendations
            ],
            priority_actions=result.recommendations.priority_actions,
            overall_guidance=result.recommendations.overall_guidance,
        )

    if result.notification:
        response.notification = {
            "alert_level": result.notification.alert_level.value,
            "title": result.notification.title,
            "message": result.notification.message,
            "call_to_action": result.notification.call_to_action,
        }

    if result.success and result.notification:
        try:
            notif_service = get_notification_service()
            await notif_service.publish(result.notification)
        except Exception as e:
            logger.warning(f"Failed to publish notification: {e}")

    return response


@router.post(
    "/symptoms",
    response_model=SymptomReportResponse,
    summary="Report symptoms for analysis",
    description="Process user symptoms through the SDO pipeline to generate health insights, "
    "identify nutritional deficiencies, and produce personalized dietary recommendations.",
    responses={500: {"model": ProblemDetail, "description": "Processing error"}},
)
async def report_symptoms(request: SymptomReportRequest) -> SymptomReportResponse:
    """
    Report symptoms and receive dietary recommendations.

    The SDO engine will:
    1. Analyze symptoms using LLM
    2. Identify potential nutritional deficiencies
    3. Correlate patterns with historical data
    4. Generate personalized recommendations
    5. Classify alert level and create notification
    """
    try:
        return await _process_single_symptom(request)
    except Exception as e:
        logger.error(f"Symptom processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "PROCESSING_ERROR", "message": str(e)}
        )


@router.post(
    "/symptoms/batch",
    response_model=BatchSymptomResponse,
    summary="Batch process symptom reports",
    description="Process multiple symptom reports in a single request. Each report is processed "
    "independently; individual failures do not block the entire batch.",
    responses={500: {"model": ProblemDetail, "description": "Batch processing error"}},
)
async def report_symptoms_batch(request: BatchSymptomRequest) -> BatchSymptomResponse:
    """Process multiple symptom reports in batch."""
    results = []

    for req in request.events:
        try:
            result = await _process_single_symptom(req)
            results.append(result)
        except Exception as e:
            logger.error(f"Batch item processing failed for user {req.user_id}: {e}", exc_info=True)
            results.append(SymptomReportResponse(
                process_id=str(uuid4()),
                user_id=req.user_id,
                success=False,
                processing_time_ms=0,
                error=str(e),
            ))

    successful = sum(1 for r in results if r.success)

    return BatchSymptomResponse(
        total=len(results),
        successful=successful,
        failed=len(results) - successful,
        results=results,
    )


# =============================================================================
# HSA Endpoints - Product Search and Management
# =============================================================================

@router.post(
    "/products/search",
    response_model=StoreSearchResponse,
    summary="Search products across stores",
    description="Search for health products across integrated stores. Supports filtering by "
    "text query, target symptoms, nutrient deficiencies, dietary requirements, and price range.",
    responses={500: {"model": ProblemDetail, "description": "Search error"}},
)
async def search_products(request: StoreSearchRequest) -> StoreSearchResponse:
    """
    Search for health products across integrated stores.

    Supports filtering by:
    - Text query
    - Target symptoms
    - Nutrient deficiencies
    - Dietary requirements
    - Price range
    """
    start_time = datetime.utcnow()

    try:
        store_types = request.store_types or [StoreType.SHOP]
        all_results = []

        for store_type in store_types:
            if not HealthStoreFactory.is_registered(store_type):
                continue

            adapter = HealthStoreFactory.create(store_type)
            await adapter.initialize()

            query = ProductSearchQuery(
                query_text=request.query,
                symptoms=request.symptoms,
                deficiencies=request.deficiencies,
                dietary_requirements=request.dietary_requirements,
                limit=request.limit,
            )

            products = await adapter.search_and_normalize(query)

            for product in products:
                if request.max_price and product.price and product.price.amount > request.max_price:
                    continue

                all_results.append(product.model_dump(exclude={"embedding"}))

        all_results.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
        all_results = all_results[:request.limit]

        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds() * 1000

        return StoreSearchResponse(
            query=request.query,
            stores_searched=store_types,
            total_results=len(all_results),
            results=all_results,
            processing_time_ms=processing_time,
        )

    except Exception as e:
        logger.error(f"Product search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "SEARCH_ERROR", "message": str(e)}
        )


@router.post(
    "/products/add",
    response_model=ProductAddResponse,
    summary="Add a product to store",
    description="Add a new health product to the specified store. The product will be "
    "normalized into a StandardizedHealthUnit for future searches.",
    responses={
        404: {"model": ProblemDetail, "description": "Store not found"},
        500: {"model": ProblemDetail, "description": "Product add error"},
    },
)
async def add_product(request: ProductAddRequest) -> ProductAddResponse:
    """
    Add a new health product to the specified store.

    The product will be normalized into a StandardizedHealthUnit
    and stored for future searches.
    """
    try:
        if not HealthStoreFactory.is_registered(request.store_type):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "STORE_NOT_FOUND", "message": f"Store type {request.store_type} not registered"}
            )

        event = StoreItemEvent(
            store_type=request.store_type,
            product_id=request.product.get("id", str(uuid4())),
            action="add",
            user_id=request.user_id,
            product_data=request.product,
            timestamp=datetime.utcnow().isoformat(),
        )

        adapter = HealthStoreFactory.create(request.store_type)
        await adapter.initialize()

        from diet.health_store_agent.normalizer import get_product_normalizer
        from diet.models.health_units import RawProduct

        raw_product = RawProduct(
            source_store=request.store_type,
            source_product_id=event.product_id,
            raw_data=request.product,
            name=request.product.get("name"),
            description=request.product.get("description"),
            price=request.product.get("price"),
        )

        normalizer = get_product_normalizer()
        standardized = normalizer.normalize(raw_product)

        return ProductAddResponse(
            success=True,
            event_id=event.event_id,
            product_id=event.product_id,
            message="Product added successfully",
            standardized_unit={
                "id": standardized.id,
                "name": standardized.name,
                "category": standardized.category.value if hasattr(standardized.category, 'value') else str(standardized.category),
                "quality_score": standardized.quality_score,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Product add failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "ADD_ERROR", "message": str(e)}
        )


# =============================================================================
# Store Management Endpoints
# =============================================================================

@router.get(
    "/stores",
    response_model=List[StoreInfo],
    summary="List available stores",
    description="List all registered health stores with their current status and capabilities.",
)
async def list_stores() -> List[StoreInfo]:
    """List all registered health stores."""
    stores = []

    for store_type in HealthStoreFactory.get_available_stores():
        try:
            adapter = HealthStoreFactory.create(store_type)
            stores.append(StoreInfo(
                store_type=store_type,
                store_name=adapter.store_name,
                status=StoreStatus.ACTIVE if adapter._initialized else StoreStatus.INACTIVE,
                capabilities=["search", "normalize"],
            ))
        except Exception as e:
            logger.warning(f"Failed to get info for store {store_type}: {e}")
            stores.append(StoreInfo(
                store_type=store_type,
                store_name=str(store_type),
                status=StoreStatus.ERROR,
            ))

    return stores


@router.get(
    "/stores/{store_type}",
    response_model=StoreInfo,
    summary="Get store information",
    description="Get detailed information about a specific store, including its status and capabilities.",
    responses={
        404: {"model": ProblemDetail, "description": "Store not found"},
        500: {"model": ProblemDetail, "description": "Store error"},
    },
)
async def get_store(store_type: StoreType) -> StoreInfo:
    """Get information about a specific store."""
    if not HealthStoreFactory.is_registered(store_type):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "STORE_NOT_FOUND", "message": f"Store type {store_type} not registered"}
        )

    try:
        adapter = HealthStoreFactory.create(store_type)
        await adapter.initialize()

        return StoreInfo(
            store_type=store_type,
            store_name=adapter.store_name,
            status=StoreStatus.ACTIVE,
            capabilities=["search", "normalize"],
        )
    except Exception as e:
        logger.error(f"Failed to get store {store_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "STORE_ERROR", "message": str(e)}
        )


# =============================================================================
# Notification Streaming Endpoints
# =============================================================================

@router.get(
    "/notifications/stream/{user_id}",
    summary="Stream notifications via SSE",
    description="Server-Sent Events stream for real-time notifications",
)
async def stream_notifications(user_id: str):
    """
    Stream notifications for a user via Server-Sent Events.

    Connect to this endpoint to receive real-time notifications.
    Events include: connected, notification, ping
    """
    import asyncio
    import json

    from app.services import notification_stream

    async def safe_stream():
        try:
            async for event in notification_stream(user_id):
                yield event
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"SSE stream error for user {user_id}: {e}", exc_info=True)
            error_data = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        safe_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get(
    "/notifications/{user_id}",
    summary="Get stored notifications",
    description="Retrieve stored notifications for a user, ordered by most recent.",
    responses={500: {"model": ProblemDetail, "description": "Notification retrieval error"}},
)
async def get_notifications(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get stored notifications for a user."""
    try:
        service = get_notification_service()
        notifications = service.get_notifications(user_id, limit)
        return [
            {
                "notification_id": str(n.notification_id),
                "alert_level": n.alert_level.value,
                "title": n.title,
                "message": n.message,
                "read": n.read,
            }
            for n in notifications
        ]
    except Exception as e:
        logger.error(f"Failed to get notifications for {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "NOTIFICATION_ERROR", "message": str(e)},
        )
