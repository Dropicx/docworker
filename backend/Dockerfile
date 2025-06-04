# Python 3.11 with support for common packages
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-deu \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9122/api/health/simple || exit 1

# Expose port
EXPOSE 9122

# Environment variables
ENV PYTHONPATH=/app
ENV ENVIRONMENT=production

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9122"] 