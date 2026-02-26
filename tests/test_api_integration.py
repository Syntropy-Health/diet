"""
Integration tests for the Diet Insight Engine API.

Tests cover:
- Symptom reporting endpoints
- Product search and add endpoints
- Store management endpoints
- Notification streaming endpoints
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


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "diet-insight-engine"
        assert "components" in data


class TestSymptomsAPI:
    """Integration tests for symptoms endpoints."""

    @pytest.mark.asyncio
    async def test_report_symptoms_success(self, client):
        """Test successful symptom reporting."""
        payload = {
            "user_id": "test_user_123",
            "symptoms": [
                {"name": "fatigue", "severity": 0.7},
                {"name": "headache", "severity": 0.5},
            ],
            "context": {
                "recent_foods": ["coffee", "salad"],
                "sleep_hours": 6.0,
            }
        }

        response = await client.post("/api/v1/symptoms", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["user_id"] == "test_user_123"
        assert "process_id" in data
        assert "analysis" in data
        assert "recommendations" in data

    @pytest.mark.asyncio
    async def test_report_symptoms_minimal(self, client):
        """Test symptom reporting with minimal data."""
        payload = {
            "user_id": "test_user_456",
            "symptoms": [
                {"name": "fatigue", "severity": 0.5},
            ],
        }

        response = await client.post("/api/v1/symptoms", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_report_symptoms_validation_error(self, client):
        """Test symptom reporting with invalid data."""
        payload = {
            "user_id": "test_user",
            "symptoms": [],
        }

        response = await client.post("/api/v1/symptoms", json=payload)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_batch_symptoms(self, client):
        """Test batch symptom processing."""
        payload = {
            "events": [
                {
                    "user_id": "user_1",
                    "symptoms": [{"name": "fatigue", "severity": 0.6}],
                },
                {
                    "user_id": "user_2",
                    "symptoms": [{"name": "headache", "severity": 0.4}],
                },
            ]
        }

        response = await client.post("/api/v1/symptoms/batch", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert "results" in data


class TestProductsAPI:
    """Integration tests for products endpoints."""

    @pytest.mark.asyncio
    async def test_search_products(self, client):
        """Test product search."""
        payload = {
            "query": "vitamin d",
            "store_types": ["shop"],
            "limit": 5,
        }

        response = await client.post("/api/v1/products/search", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total_results" in data
        assert "processing_time_ms" in data

    @pytest.mark.asyncio
    async def test_search_with_symptoms(self, client):
        """Test product search with symptom filtering."""
        payload = {
            "query": "supplement",
            "symptoms": ["fatigue", "low_energy"],
            "store_types": ["shop"],
            "limit": 10,
        }

        response = await client.post("/api/v1/products/search", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    @pytest.mark.asyncio
    async def test_add_product(self, client):
        """Test adding a product."""
        payload = {
            "store_type": "shop",
            "user_id": "admin_001",
            "product": {
                "name": "Test Vitamin C",
                "description": "High potency vitamin C supplement",
                "category": "vitamin",
                "price": 19.99,
            }
        }

        response = await client.post("/api/v1/products/add", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "event_id" in data
        assert "product_id" in data


class TestStoresAPI:
    """Integration tests for stores endpoints."""

    @pytest.mark.asyncio
    async def test_list_stores(self, client):
        """Test listing available stores."""
        response = await client.get("/api/v1/stores")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_store_info(self, client):
        """Test getting specific store info."""
        response = await client.get("/api/v1/stores/shop")

        assert response.status_code == 200
        data = response.json()
        assert data["store_type"] == "shop"
        assert "status" in data

    @pytest.mark.asyncio
    async def test_get_invalid_store(self, client):
        """Test getting non-existent store."""
        response = await client.get("/api/v1/stores/invalid_store")

        assert response.status_code == 422


class TestNotificationsAPI:
    """Integration tests for notifications endpoints."""

    @pytest.mark.asyncio
    async def test_get_notifications(self, client):
        """Test getting user notifications."""
        response = await client.get("/api/v1/notifications/test_user")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_notification_stream_headers(self, client):
        """Test SSE stream has correct headers."""
        async with client.stream("GET", "/api/v1/notifications/stream/test_user") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")


class TestEndToEndFlow:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    async def test_symptom_to_notification_flow(self, client):
        """Test complete flow from symptom report to notification."""
        symptom_payload = {
            "user_id": "e2e_user",
            "symptoms": [
                {"name": "fatigue", "severity": 0.8},
                {"name": "brain_fog", "severity": 0.6},
            ],
        }

        symptom_response = await client.post("/api/v1/symptoms", json=symptom_payload)
        assert symptom_response.status_code == 200
        symptom_data = symptom_response.json()

        assert symptom_data["success"] is True
        assert symptom_data["notification"] is not None

        notif_response = await client.get("/api/v1/notifications/e2e_user")
        assert notif_response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_and_add_flow(self, client):
        """Test product search and add flow."""
        search_payload = {
            "query": "iron supplement",
            "store_types": ["shop"],
            "deficiencies": ["iron"],
            "limit": 5,
        }

        search_response = await client.post("/api/v1/products/search", json=search_payload)
        assert search_response.status_code == 200

        add_payload = {
            "store_type": "shop",
            "user_id": "e2e_admin",
            "product": {
                "name": "Iron Bisglycinate 25mg",
                "description": "Gentle iron supplement",
                "category": "mineral",
                "price": 15.99,
                "target_deficiencies": ["iron"],
            }
        }

        add_response = await client.post("/api/v1/products/add", json=add_payload)
        assert add_response.status_code == 200
        assert add_response.json()["success"] is True
