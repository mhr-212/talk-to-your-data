"""Integration tests for the Flask API."""
import pytest
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, init_services
from config import get_config


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_root_endpoint(client):
    """Test the root / endpoint serves the UI."""
    response = client.get('/')
    assert response.status_code == 200
    # Should contain HTML
    assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data


def test_health_endpoint_degraded(client):
    """Test health endpoint returns degraded without DB/LLM."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'status' in data
    assert 'services' in data
    assert 'features' in data


def test_query_without_question(client):
    """Test /query endpoint requires a question."""
    response = client.post('/query', json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


def test_query_empty_question(client):
    """Test /query endpoint rejects empty questions."""
    response = client.post('/query', json={"question": ""})
    assert response.status_code == 400


def test_query_requires_db(client):
    """Test /query fails gracefully if DB not configured."""
    # With no DB configured, should get a 503
    response = client.post('/query', json={"question": "test"})
    assert response.status_code in [503, 502, 500]
    data = json.loads(response.data)
    assert 'error' in data


def test_logs_endpoint(client):
    """Test GET /logs returns a list of logs."""
    response = client.get('/logs')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'logs' in data
    assert isinstance(data['logs'], list)
    assert 'count' in data


def test_static_files(client):
    """Test static file serving."""
    response = client.get('/static/app.js')
    assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
