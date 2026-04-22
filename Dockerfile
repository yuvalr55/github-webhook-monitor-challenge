# Use a slim Python image for efficiency
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /app

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
# We copy the entire app directory which now contains all our sub-packages
COPY app/ ./app/

# Create a non-root user for security and switch to it
RUN useradd -m myuser
USER myuser

# We don't specify CMD here, as it will be defined in docker-compose.yml
# for each service (server vs worker).
