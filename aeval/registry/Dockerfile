FROM python:3.13-slim

WORKDIR /app

COPY registry/requirements.txt /app/registry/requirements.txt
RUN pip install --no-cache-dir -r /app/registry/requirements.txt

COPY registry/ /app/registry/

EXPOSE 8082

CMD ["uvicorn", "registry.src.app:app", "--host", "0.0.0.0", "--port", "8082"]
