"""
Tests for error handling across the Diet Insight Engine API.

Tests cover:
- Invalid JSON -> 422 with structured response
- Empty symptoms list -> 422
- Triggered 500 -> ProblemDetail response with correlation_id
- GET /health returns actual component status
"""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestValidationErrors:
    """Tests for request validation errors."""

    @pytest.mark.asyncio
    async def test_invalid_json_returns_422(self, client):
        """Test that invalid JSON body returns 422 with structured response."""
        response = await client.post(
            "/api/v1/symptoms",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422
        data = response.json()
        # FastAPI returns validation errors with detail field
        assert "detail" in data or "type" in data

    @pytest.mark.asyncio
    async def test_empty_symptoms_list_returns_422(self, client):
        """Test that an empty symptoms list returns 422."""
        payload = {
            "user_id": "test_user",
            "symptoms": [],
        }
        response = await client.post("/api/v1/symptoms", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_required_field_returns_422(self, client):
        """Test that missing required fields return 422."""
        payload = {
            "symptoms": [{"name": "fatigue", "severity": 0.5}],
        }
        response = await client.post("/api/v1/symptoms", json=payload)
        assert response.status_code == 422


class TestInternalErrors:
    """Tests for internal server error handling."""

    @pytest.mark.asyncio
    async def test_sdo_engine_failure_returns_problem_detail(self, client):
        """Test that SDO engine failure returns ProblemDetail with correlation_id."""
        with patch(
            "app.routers.diet_insight.get_sdo_engine"
        ) as mock_engine_fn:
            mock_engine = AsyncMock()
            mock_engine.initialize = AsyncMock()
            mock_engine.process_symptoms = AsyncMock(
                side_effect=RuntimeError("SDO pipeline exploded")
            )
            mock_engine_fn.return_value = mock_engine

            payload = {
                "user_id": "test_user",
                "symptoms": [{"name": "fatigue", "severity": 0.5}],
            }
            response = await client.post("/api/v1/symptoms", json=payload)

            assert response.status_code == 500
            data = response.json()
            # The global exception handler wraps HTTPException in ProblemDetail
            assert "correlation_id" in data
            assert "type" in data
            assert "status" in data
            assert data["status"] == 500

    @pytest.mark.asyncio
    async def test_correlation_id_in_response_header(self, client):
        """Test that correlation ID is set in response headers."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert "x-correlation-id" in response.headers


class TestHealthEndpoint:
    """Tests for the health check endpoint with component status."""

    @pytest.mark.asyncio
    async def test_health_returns_component_status(self, client):
        """Test that GET /health returns actual component status."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert "sdo" in data["components"]
        assert "status" in data["components"]["sdo"]
        assert "hsa" in data["components"]
        assert "status" in data["components"]["hsa"]
