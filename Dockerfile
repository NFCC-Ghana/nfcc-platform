FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV GDAL_CONFIG=/usr/bin/gdal-config

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gdal-bin \
    libgdal-dev \
    libproj-dev \
    libgeos-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt .

# Upgrade pip
RUN pip install --upgrade pip

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Expose API port
EXPOSE 8000

# Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8000/health || exit 1

# Start API
CMD ["uvicorn", "src.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000"]
