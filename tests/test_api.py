import pytest
import requests
import time

BASE_URL = "http://localhost:5001"

def test_health_endpoint():
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'healthy'

def test_translate_endpoint():
    payload = {
        "text": "hello world",
        "target_lang": "fr"
    }
    response = requests.post(f"{BASE_URL}/translate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert 'translated_text' in data
    assert 'trace_id' in data

def test_metrics_endpoint():
    response = requests.get(f"{BASE_URL}/metrics")
    assert response.status_code == 200
    data = response.json()
    assert 'total_requests' in data

def test_prometheus_metrics():
    response = requests.get(f"{BASE_URL}/metrics/prometheus")
    assert response.status_code == 200
    assert 'http_requests_total' in response.text

if __name__ == "__main__":
    pytest.main([__file__, "-v"])