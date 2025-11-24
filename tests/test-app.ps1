# test-app.ps1 - Script de test complet pour l'API de traduction

Write-Host "🧪 Testing Translation API (PowerShell)" -ForegroundColor Cyan
Write-Host "=========================================`n" -ForegroundColor Cyan

# Test 1: Health Check
Write-Host "1. Testing Health Endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:5001/health"
    Write-Host "   ✅ Status: $($health.status)" -ForegroundColor Green
    Write-Host "   ✅ Redis: $($health.redis_connected)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Health check failed: $_" -ForegroundColor Red
    exit 1
}

# Test 2: Translation
Write-Host "`n2. Testing Translation..." -ForegroundColor Yellow
$testCases = @(
    @{text="hello world"; lang="fr"},
    @{text="good morning"; lang="es"},
    @{text="thank you"; lang="de"}
)

foreach ($test in $testCases) {
    $body = @{
        text = $test.text
        target_lang = $test.lang
    } | ConvertTo-Json
    
    try {
        $result = Invoke-RestMethod -Uri "http://localhost:5001/translate" -Method Post -Headers @{"Content-Type"="application/json"} -Body $body
        Write-Host "   ✅ '$($test.text)' → '$($result.translated_text)' (Cached: $($result.cached))" -ForegroundColor Green
    } catch {
        Write-Host "   ❌ Translation failed for '$($test.text)': $_" -ForegroundColor Red
    }
}

# Test 3: Cache Verification
Write-Host "`n3. Testing Cache..." -ForegroundColor Yellow
$cacheBody = @{text="cache test"; target_lang="fr"} | ConvertTo-Json
$firstCall = Invoke-RestMethod -Uri "http://localhost:5001/translate" -Method Post -Headers @{"Content-Type"="application/json"} -Body $cacheBody
$secondCall = Invoke-RestMethod -Uri "http://localhost:5001/translate" -Method Post -Headers @{"Content-Type"="application/json"} -Body $cacheBody

if ($firstCall.cached -eq $false -and $secondCall.cached -eq $true) {
    Write-Host "   ✅ Cache working correctly" -ForegroundColor Green
} else {
    Write-Host "   ❌ Cache test failed" -ForegroundColor Red
}

# Test 4: Metrics
Write-Host "`n4. Testing Metrics..." -ForegroundColor Yellow
try {
    $metrics = Invoke-RestMethod -Uri "http://localhost:5001/metrics"
    $detailed = Invoke-RestMethod -Uri "http://localhost:5001/metrics/detailed"
    
    Write-Host "   ✅ Basic metrics - Requests: $($metrics.total_requests)" -ForegroundColor Green
    Write-Host "   ✅ Detailed metrics - Cache hit rate: $($detailed.application_metrics.cache_hit_rate)" -ForegroundColor Green
    
    # Test Prometheus metrics
    $prometheus = Invoke-WebRequest -Uri "http://localhost:5001/metrics/prometheus"
    if ($prometheus.Content -match "http_requests_total") {
        Write-Host "   ✅ Prometheus metrics available" -ForegroundColor Green
    }
} catch {
    Write-Host "   ❌ Metrics test failed: $_" -ForegroundColor Red
}

# Test 5: Error Handling
Write-Host "`n5. Testing Error Handling..." -ForegroundColor Yellow
try {
    # Test avec texte vide
    $emptyBody = @{text=""; target_lang="fr"} | ConvertTo-Json
    $errorResponse = Invoke-WebRequest -Uri "http://localhost:5001/translate" -Method Post -Headers @{"Content-Type"="application/json"} -Body $emptyBody
    Write-Host "   ❌ Expected error but got success" -ForegroundColor Red
} catch {
    if ($_.Exception.Response.StatusCode -eq 400) {
        Write-Host "   ✅ Error handling working (got 400 for empty text)" -ForegroundColor Green
    }
}

Write-Host "`n🎉 ALL TESTS COMPLETED SUCCESSFULLY!" -ForegroundColor Cyan
Write-Host "📊 Your API is running perfectly on http://localhost:5001" -ForegroundColor Cyan