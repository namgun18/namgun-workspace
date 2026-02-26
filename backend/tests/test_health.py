"""Tests for the /api/health endpoint."""

import pytest


@pytest.mark.asyncio
async def test_health_returns_200(client):
    response = await client.get("/api/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_fields(client):
    response = await client.get("/api/health")
    data = response.json()

    assert "status" in data
    assert data["status"] == "ok"

    assert "service" in data
    assert isinstance(data["service"], str)

    assert "version" in data
    assert isinstance(data["version"], str)
