"""
API contract tests for the Diet Insight Engine.

Tests cover:
- POST /symptoms response has expected fields
- POST /products/search response shape
- GET /docs returns valid OpenAPI JSON
- No embedding field in product search results
"""

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


class TestSymptomsContract:
    """Contract tests for the symptoms endpoint."""

    @pytest.mark.asyncio
    async def test_symptoms_response_has_expected_fields(self, client):
        """Test POST /symptoms response has all expected top-level fields."""
        payload = {
            "user_id": "contract_user",
            "symptoms": [
                {"name": "fatigue", "severity": 0.7},
            ],
        }
        response = await client.post("/api/v1/symptoms", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Top-level fields
        assert "process_id" in data
        assert "user_id" in data
        assert "success" in data
        assert "processing_time_ms" in data
        assert "analysis" in data
        assert "recommendations" in data
        assert "notification" in data

    @pytest.mark.asyncio
    async def test_symptoms_analysis_has_typed_structure(self, client):
        """Test that analysis field contains typed sub-fields."""
        payload = {
            "user_id": "contract_user",
            "symptoms": [
                {"name": "fatigue", "severity": 0.7},
            ],
        }
        response = await client.post("/api/v1/symptoms", json=payload)

        assert response.status_code == 200
        data = response.json()

        if data["analysis"] is not None:
            analysis = data["analysis"]
            assert "insights" in analysis
            assert "deficiencies" in analysis
            assert "patterns_detected" in analysis
            assert "severity_score" in analysis
            assert "confidence_score" in analysis
            assert isinstance(analysis["patterns_detected"], int)
            assert isinstance(analysis["severity_score"], (int, float))


class TestProductSearchContract:
    """Contract tests for the product search endpoint."""

    @pytest.mark.asyncio
    async def test_product_search_response_shape(self, client):
        """Test POST /products/search response has expected shape."""
        payload = {
            "query": "vitamin d",
            "store_types": ["shop"],
            "limit": 5,
        }
        response = await client.post("/api/v1/products/search", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert "query" in data
        assert "stores_searched" in data
        assert "total_results" in data
        assert "results" in data
        assert "processing_time_ms" in data
        assert isinstance(data["results"], list)
        assert isinstance(data["total_results"], int)

    @pytest.mark.asyncio
    async def test_no_embedding_in_search_results(self, client):
        """Test that embedding field is excluded from product search results."""
        payload = {
            "query": "vitamin d",
            "store_types": ["shop"],
            "limit": 10,
        }
        response = await client.post("/api/v1/products/search", json=payload)

        assert response.status_code == 200
        data = response.json()

        for result in data["results"]:
            assert "embedding" not in result, (
                "embedding field should be excluded from search results"
            )


class TestOpenAPIContract:
    """Contract tests for the OpenAPI schema."""

    @pytest.mark.asyncio
    async def test_openapi_json_is_valid(self, client):
        """Test that GET /openapi.json returns valid OpenAPI JSON."""
        response = await client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()

        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
        assert data["info"]["title"] == "Diet Insight Engine API"
        assert data["info"]["version"] == "0.2.0"

    @pytest.mark.asyncio
    async def test_openapi_has_all_endpoints(self, client):
        """Test that OpenAPI schema includes all expected endpoints."""
        response = await client.get("/openapi.json")

        assert response.status_code == 200
        paths = response.json()["paths"]

        expected_paths = [
            "/api/v1/symptoms",
            "/api/v1/symptoms/batch",
            "/api/v1/products/search",
            "/api/v1/products/add",
            "/api/v1/stores",
            "/api/v1/stores/{store_type}",
            "/api/v1/notifications/stream/{user_id}",
            "/api/v1/notifications/{user_id}",
            "/health",
        ]

        for path in expected_paths:
            assert path in paths, f"Missing endpoint in OpenAPI schema: {path}"

    @pytest.mark.asyncio
    async def test_openapi_has_problem_detail_schema(self, client):
        """Test that ProblemDetail schema is present in OpenAPI."""
        response = await client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()

        schemas = data.get("components", {}).get("schemas", {})
        assert "ProblemDetail" in schemas
