"""Integration tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def test_health_check_endpoint():
    """Verify health check endpoint returns 200 and expected status."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert data["engine"] == "ApexCore Full-Duplex AI"
    assert data["database_wal"] is True

def test_vitals_endpoint():
    """Verify system vitals returns proper performance metrics."""
    res = client.get("/api/tools/vitals")
    assert res.status_code == 200
    data = res.json()
    assert "cpu_usage_percent" in data
    assert "ram_percent" in data
    assert "disk_c_free_gb" in data

def test_processes_endpoint():
    """Verify top processes enumeration works via API."""
    res = client.get("/api/tools/processes?sort_by=memory&count=3")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) <= 3

def test_safe_sql_query_endpoint():
    """Verify query-db executes valid SELECT query."""
    res = client.post("/api/tools/query-db", json={"sql_query": "SELECT 1 as test_col;"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"][0]["test_col"] == 1

def test_sql_query_security_endpoint():
    """Verify malicious or write statements are rejected."""
    res = client.post("/api/tools/query-db", json={"sql_query": "DROP TABLE conversation_logs;"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert "Security constraint" in data["error"]
