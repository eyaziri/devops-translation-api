import pytest
import requests
import time
import subprocess
import threading

BASE_URL = "http://localhost:5001"

def test_health_endpoint():
    """Test du endpoint health"""
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'healthy'
    assert 'timestamp' in data
    assert 'redis_connected' in data
    print("✅ Health endpoint test passed")

def test_translate_endpoint():
    """Test du endpoint translate"""
    payload = {
        "text": "hello world",
        "target_lang": "fr"
    }
    response = requests.post(f"{BASE_URL}/translate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert 'translated_text' in data
    assert 'trace_id' in data
    assert 'cached' in data
    print("✅ Translate endpoint test passed")

def test_translate_caching():
    """Test du cache"""
    payload = {
        "text": "test cache",
        "target_lang": "es"
    }
    
    # Premier appel (non caché)
    response1 = requests.post(f"{BASE_URL}/translate", json=payload)
    data1 = response1.json()
    assert data1['cached'] == False
    
    # Deuxième appel (caché)
    response2 = requests.post(f"{BASE_URL}/translate", json=payload)
    data2 = response2.json()
    assert data2['cached'] == True
    assert data1['translated_text'] == data2['translated_text']
    print("✅ Cache test passed")

def test_metrics_endpoints():
    """Test des endpoints de métriques"""
    # Métriques basiques
    response = requests.get(f"{BASE_URL}/metrics")
    assert response.status_code == 200
    data = response.json()
    assert 'total_requests' in data
    assert 'cache_hits' in data
    
    # Métriques Prometheus
    response = requests.get(f"{BASE_URL}/metrics/prometheus")
    assert response.status_code == 200
    assert 'http_requests_total' in response.text
    
    # Métriques détaillées
    response = requests.get(f"{BASE_URL}/metrics/detailed")
    assert response.status_code == 200
    data = response.json()
    assert 'application_metrics' in data
    assert 'system_metrics' in data
    print("✅ Metrics endpoints test passed")

def test_error_handling():
    """Test de la gestion des erreurs"""
    # Requête sans données
    response = requests.post(f"{BASE_URL}/translate", json={})
    assert response.status_code == 400
    
    # Texte vide
    response = requests.post(f"{BASE_URL}/translate", json={"text": ""})
    assert response.status_code == 400
    print("✅ Error handling test passed")

def test_multiple_languages():
    """Test avec différentes langues"""
    languages = ['fr', 'es', 'de']
    text = "hello"
    
    for lang in languages:
        payload = {"text": text, "target_lang": lang}
        response = requests.post(f"{BASE_URL}/translate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data['translated_text'] != text
        print(f"✅ {lang} translation test passed")

if __name__ == "__main__":
    # Ces tests supposent que l'API est déjà démarrée
    print("🔄 Running tests (make sure app.py is running on port 5001)...")
    
    # Exécuter les tests
    pytest.main([__file__, "-v"])