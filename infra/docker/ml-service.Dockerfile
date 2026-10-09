FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /workspace/apps/ml-service
RUN pip install --no-cache-dir uv==0.11.24
COPY apps/ml-service/pyproject.toml apps/ml-service/uv.lock ./
RUN uv sync --locked --no-dev
COPY apps/ml-service/app ./app
COPY docs/dataset /workspace/docs/dataset
RUN mkdir -p weights
EXPOSE 8001
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
