FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Create logs directory
RUN mkdir -p /app/logs

# Make entrypoint.sh executable (in case chmod +x didn't work)
RUN chmod +x /app/entrypoint.sh

# Entrypoint setup
ENTRYPOINT ["/app/entrypoint.sh"]

# Run gunicorn with increased timeout and optimized worker config for RAM
CMD gunicorn financeos.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 1 \
    --threads 4 \
    --timeout 120 \
    --log-level info
