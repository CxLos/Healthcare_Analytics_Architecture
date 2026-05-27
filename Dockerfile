# FROM python:3.11-slim
FROM python:3.11-slim-bullseye


# Prevent .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (layer-cached), then upgrade vulnerable build tools
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --upgrade "wheel>=0.46.2" setuptools

# Copy application code
COPY . .

EXPOSE 8050

CMD ["gunicorn", "app.healthcare_analytics:server", "--workers=1", "--bind=0.0.0.0:8050"]
