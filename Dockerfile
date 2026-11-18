FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.115.12 uvicorn==0.34.2 prometheus-client==0.21.1
COPY demo demo
CMD ["uvicorn", "demo.app:app", "--host", "0.0.0.0", "--port", "8080"]
