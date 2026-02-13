#!/bin/sh
# Start rq worker in background, then uvicorn in foreground
cd /app
rq worker --url "${REDIS_URL}" aeval &
exec uvicorn orchestrator.api.main:app --host 0.0.0.0 --port "${ORCHESTRATOR_PORT:-8081}"
