FROM python:3.13-slim

WORKDIR /app

# Install orchestrator dependencies
COPY orchestrator/requirements.txt /app/orchestrator-requirements.txt
RUN pip install --no-cache-dir -r /app/orchestrator-requirements.txt

# Install aeval SDK from source
COPY sdk/ /app/sdk/
RUN pip install --no-cache-dir /app/sdk/

# Copy orchestrator source
COPY orchestrator/src/ /app/orchestrator/

# evals/ and datasets/ are mounted as volumes at runtime

# Start script: run uvicorn + rq worker in parallel
COPY orchestrator/start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
