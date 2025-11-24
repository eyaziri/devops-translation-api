FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api.py .
COPY prometheus_client /usr/local/lib/python3.11/site-packages/prometheus_client/

EXPOSE 5001

ENV REDIS_HOST=redis-service

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5001/health || exit 1

CMD ["python", "api.py"]