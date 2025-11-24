from flask import Flask, request, jsonify
import requests
import redis
import time
import logging
from datetime import datetime, timezone
import os
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST, Gauge

# Configuration de l'application
app = Flask(__name__)

# ==================== METRIQUES PROMETHEUS ====================
# Compteurs
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status_code'])
TRANSLATION_COUNT = Counter('translations_total', 'Total Translations', ['target_lang', 'cached'])
ERROR_COUNT = Counter('errors_total', 'Total Errors', ['type'])

# Histogrammes (pour les durées)
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
TRANSLATION_DURATION = Histogram('translation_duration_seconds', 'Translation processing time')

# Jauges (pour les valeurs actuelles)
ACTIVE_REQUESTS = Gauge('active_requests', 'Currently active requests')
REDIS_CONNECTION_STATUS = Gauge('redis_connected', 'Redis connection status')
CACHE_SIZE = Gauge('cache_size', 'Number of cached translations')

# ==================== CONFIGURATION EXISTANTE ====================
# Configuration Redis avec gestion d'erreur
try:
    cache = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=6379,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    # Test de connexion
    cache.ping()
    REDIS_CONNECTION_STATUS.set(1)
    print("✅ Redis connecté avec succès!")
except redis.ConnectionError as e:
    print(f"❌ Erreur Redis: {e}")
    print("💡 Utilisation du cache en mémoire")
    REDIS_CONNECTION_STATUS.set(0)
    # Fallback: cache en mémoire
    class MemoryCache:
        def __init__(self):
            self._cache = {}
        
        def get(self, key):
            return self._cache.get(key)
        
        def setex(self, key, expire, value):
            self._cache[key] = value
        
        def ping(self):
            return False
        
        def keys(self, pattern):
            return [k for k in self._cache.keys() if pattern in k]
        
        def info(self, section):
            return {'used_memory_human': '0B'}
    
    cache = MemoryCache()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Métriques internes (backup)
metrics = {
    'total_requests': 0,
    'cache_hits': 0,
    'translation_errors': 0,
    'response_times': []
}

class TraceContext:
    def __init__(self):
        self.trace_id = f"trace_{int(time.time())}"

class TranslationService:
    @staticmethod
    def translate_text(text, target_lang='fr'):
        """Service de traduction avec fallback"""
        try:
            # Essayer MyMemory API
            response = requests.get(
                'https://api.mymemory.translated.net/get',
                params={
                    'q': text,
                    'langpair': f'en|{target_lang}'
                },
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                translated = result['responseData']['translatedText']
                
                if translated and "PLEASE SELECT" not in translated:
                    return translated
            
            # Fallback vers le mock
            return TranslationService.mock_translation(text, target_lang)
                
        except Exception as e:
            logger.warning(f"Translation service down, using mock: {str(e)}")
            ERROR_COUNT.labels(type='translation_api').inc()
            return TranslationService.mock_translation(text, target_lang)
    
    @staticmethod
    def mock_translation(text, target_lang):
        """Traduction mock pour les tests"""
        mock_translations = {
            'hello world': {'fr': 'bonjour le monde', 'es': 'hola mundo', 'de': 'hallo welt'},
            'hello': {'fr': 'bonjour', 'es': 'hola', 'de': 'hallo'},
            'good morning': {'fr': 'bonjour', 'es': 'buenos días', 'de': 'guten morgen'},
            'i love programming': {'fr': "j'adore programmer", 'es': 'me encanta programar', 'de': 'ich liebe Programmierung'},
            'thank you': {'fr': 'merci', 'es': 'gracias', 'de': 'danke'},
            'how are you': {'fr': 'comment ça va', 'es': 'cómo estás', 'de': 'wie geht es dir'},
            'goodbye': {'fr': 'au revoir', 'es': 'adiós', 'de': 'auf wiedersehen'}
        }
        
        text_lower = text.lower().strip()
        if text_lower in mock_translations and target_lang in mock_translations[text_lower]:
            return mock_translations[text_lower][target_lang]
        else:
            return f"[TEST] {text} → {target_lang}"

    @staticmethod
    def get_cache_key(text, target_lang):
        return f"translation:{target_lang}:{hash(text)}"

# ==================== MIDDLEWARE AMÉLIORÉ ====================
@app.before_request
def before_request():
    request.start_time = time.time()
    request.trace_ctx = TraceContext()
    ACTIVE_REQUESTS.inc()  # Incrémente les requêtes actives
    logger.info(f"Request: {request.method} {request.path}")

@app.after_request
def after_request(response):
    response_time = time.time() - request.start_time
    
    # Métriques Prometheus
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.path,
        status_code=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.path
    ).observe(response_time)
    
    ACTIVE_REQUESTS.dec()  # Décrémente les requêtes actives
    
    # Métriques internes (existantes)
    metrics['total_requests'] += 1
    metrics['response_times'].append(response_time)
    if len(metrics['response_times']) > 100:
        metrics['response_times'].pop(0)
        
    return response

# ==================== ROUTES AMÉLIORÉES ====================
@app.route('/translate', methods=['POST'])
def translate_text():
    metrics['total_requests'] += 1
    translation_start_time = time.time()
    
    try:
        data = request.get_json()
        if not data:
            ERROR_COUNT.labels(type='invalid_request').inc()
            return jsonify({'error': 'No JSON data provided'}), 400
            
        text = data.get('text', '').strip()
        target_lang = data.get('target_lang', 'fr')
        
        if not text:
            ERROR_COUNT.labels(type='invalid_request').inc()
            return jsonify({'error': 'Text is required'}), 400
        
        # Vérifier le cache
        cache_key = TranslationService.get_cache_key(text, target_lang)
        cached_result = cache.get(cache_key)
        
        if cached_result:
            metrics['cache_hits'] += 1
            TRANSLATION_COUNT.labels(target_lang=target_lang, cached='true').inc()
            TRANSLATION_DURATION.observe(time.time() - translation_start_time)
            logger.info(f"Cache hit: {text[:30]}...")
            return jsonify({
                'translated_text': cached_result,
                'cached': True,
                'trace_id': request.trace_ctx.trace_id
            })
        
        # Traduction
        translated = TranslationService.translate_text(text, target_lang)
        
        if translated:
            cache.setex(cache_key, 3600, translated)  # Cache 1 heure
            TRANSLATION_COUNT.labels(target_lang=target_lang, cached='false').inc()
            TRANSLATION_DURATION.observe(time.time() - translation_start_time)
            logger.info(f"New translation: {text[:30]}... → {translated[:30]}...")
            
            return jsonify({
                'translated_text': translated,
                'cached': False,
                'trace_id': request.trace_ctx.trace_id
            })
        else:
            metrics['translation_errors'] += 1
            ERROR_COUNT.labels(type='translation_failed').inc()
            return jsonify({'error': 'Translation failed'}), 500
            
    except Exception as e:
        metrics['translation_errors'] += 1
        ERROR_COUNT.labels(type='unexpected_error').inc()
        logger.error(f"Error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# ==================== NOUVELLES ROUTES OBSERVABILITÉ ====================
@app.route('/metrics/prometheus')
def prometheus_metrics():
    """Endpoint Prometheus pour le scraping"""
    # Met à jour la jauge de taille du cache
    try:
        cache_keys = len(cache.keys('translation:*'))
        CACHE_SIZE.set(cache_keys)
    except:
        CACHE_SIZE.set(0)
    
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/metrics/detailed')
def detailed_metrics():
    """Endpoint métriques détaillées combinées"""
    recent_times = metrics['response_times'][-10:]
    avg_time = sum(recent_times)/len(recent_times) if recent_times else 0
    cache_rate = metrics['cache_hits'] / metrics['total_requests'] if metrics['total_requests'] > 0 else 0
    
    return jsonify({
        'application_metrics': {
            'total_requests': metrics['total_requests'],
            'cache_hits': metrics['cache_hits'],
            'cache_hit_rate': round(cache_rate, 2),
            'translation_errors': metrics['translation_errors'],
            'avg_response_time_seconds': round(avg_time, 3),
            'redis_connected': cache.ping()
        },
        'prometheus_endpoint': '/metrics/prometheus',
        'health_endpoint': '/health'
    })

# ==================== ROUTES EXISTANTES ====================
@app.route('/metrics')
def get_metrics():
    """Endpoint pour les métriques (compatibilité)"""
    recent_times = metrics['response_times'][-10:]
    avg_time = sum(recent_times)/len(recent_times) if recent_times else 0
    cache_rate = metrics['cache_hits'] / metrics['total_requests'] if metrics['total_requests'] > 0 else 0
    
    return jsonify({
        'total_requests': metrics['total_requests'],
        'cache_hits': metrics['cache_hits'],
        'cache_hit_rate': round(cache_rate, 2),
        'translation_errors': metrics['translation_errors'],
        'avg_response_time_seconds': round(avg_time, 3),
        'redis_connected': cache.ping(),
        'prometheus_metrics': 'Available at /metrics/prometheus'
    })

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'redis_connected': cache.ping(),
        'observability': {
            'prometheus_endpoint': '/metrics/prometheus',
            'detailed_metrics': '/metrics/detailed'
        }
    })

@app.route('/')
def home():
    return jsonify({
        'message': '🚀 Translation API is running!',
        'version': '2.0.0',
        'features': [
            'REST API for translation',
            'Redis caching',
            'Advanced observability with Prometheus',
            'Health checks',
            'Performance metrics'
        ],
        'endpoints': {
            'POST /translate': 'Translate text',
            'GET /metrics': 'Basic metrics',
            'GET /metrics/prometheus': 'Prometheus metrics',
            'GET /metrics/detailed': 'Detailed metrics',
            'GET /health': 'Health check'
        }
    })

if __name__ == '__main__':
    print("🚀 Starting Translation API with Advanced Observability...")
    print("📊 Endpoints:")
    print("   POST http://localhost:5000/translate")
    print("   GET  http://localhost:5000/metrics") 
    print("   GET  http://localhost:5000/metrics/prometheus  ← NOUVEAU!")
    print("   GET  http://localhost:5000/metrics/detailed    ← NOUVEAU!")
    print("   GET  http://localhost:5000/health")
    print("\n💡 Test Prometheus metrics:")
    print('   curl http://localhost:5000/metrics/prometheus')
    print("\n🎯 Features added:")
    print("   ✅ Prometheus metrics integration")
    print("   ✅ Request counters and histograms")
    print("   ✅ Translation-specific metrics")
    print("   ✅ Error tracking by type")
    print("   ✅ Active requests monitoring")
    app.run(host='0.0.0.0', port=5001, debug=False)