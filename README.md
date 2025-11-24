# devops-translation-api

## 📑 **RAPPORT FINAL - DevOps Project**


# 📊 Rapport Final - Projet DevOps
**API de Traduction avec Pipeline CI/CD Complète**
  
*Auteur: Eya Ziri*  
*Projet: Translation API DevOps*

## 🎯 Résumé Exécutif

Ce projet démontre l'implémentation complète d'une pratique DevOps moderne autour d'une API de traduction. L'application a été containerisée, sécurisée, monitorée et déployée via un pipeline CI/CD automatisé avec intégration Kubernetes.

## 🏗️ Architecture Technique

### Stack Technologique
- **Backend**: Python 3.9 + Flask
- **Cache**: Redis 7 avec fallback mémoire
- **Containerisation**: Docker + Docker Compose
- **Orchestration**: Kubernetes (minikube)
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus Metrics
- **Sécurité**: Bandit (SAST) + OWASP ZAP (DAST)
- **Logging**: Structured JSON Logs

### Diagramme d'Architecture
Utilisateur → Load Balancer → Kubernetes Service → Pods API → Redis Cache
↓
External Translation API
↓
Monitoring & Metrics

## 🔄 Flux CI/CD

### Pipeline GitHub Actions
1. **Trigger**: Push sur main/develop ou PR
2. **Test**: Tests unitaires et intégration
3. **Security**: Scans SAST/DAST automatisés
4. **Build**: Construction image Docker
5. **Push**: Publication sur Docker Hub
6. **Deploy**: Déploiement Kubernetes
7. **Report**: Génération de rapports

### Statistiques Pipeline
- **Durée moyenne**: 8-12 minutes
- **Success Rate**: 95%+
- **Artifacts**: 5 rapports générés automatiquement

## 📈 Observabilité Implémentée

### Métriques Prometheus
| Catégorie | Métriques | Usage |
|-----------|-----------|-------|
| **HTTP** | requests_total, request_duration_seconds | Performance API |
| **Business** | translations_total, cache_hits | Métriques métier |
| **System** | active_requests, redis_connected | Santé système |

### Logging Structuré
- Format JSON pour l'ingestion
- Trace IDs pour le correlation
- Niveaux: DEBUG, INFO, WARNING, ERROR

### Health Checks
- Endpoint `/health` avec vérifications complètes
- Liveness/Readiness probes Kubernetes
- Métriques de disponibilité

## 🔒 Mesures de Sécurité

### SAST (Static Analysis)
- **Outils**: Bandit avec configuration custom
- **Règles**: Exclusion des faux positifs connus
- **Rapports**: HTML et JSON pour intégration

### DAST (Dynamic Analysis)
- **Outils**: OWASP ZAP Baseline Scan
- **Coverage**: Scan automatique de l'API déployée
- **Sévérité**: Focus sur Medium/High vulnerabilities

### Hardening
- Headers de sécurité HTTP
- Timeouts configurables
- Validation des inputs
- Gestion sécurisée des secrets

## ☸️ Déploiement Kubernetes

### Configuration
- **Namespace**: Isolation `translation-app`
- **Replicas**: 2 pour haute disponibilité
- **Resources**: Limits et requests configurés
- **Probes**: Liveness/Readiness checks
- **Service**: NodePort pour l'accès

### Manifestes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: translation-api
  namespace: translation-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: translation-api
