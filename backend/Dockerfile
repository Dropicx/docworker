# Python 3.11 with support for common packages
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*
# tesseract-ocr removed - OCR now happens in worker service

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ⚡ NOTE: spaCy models removed - PII filtering now happens in worker service
# This speeds up backend deployment and reduces image size

# Copy application code
COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

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

# Run migration then start uvicorn
# Migration is idempotent - safe to run every deploy
CMD sh -c '\
    echo "========================================"; \
    echo "🚀 Starting DocTranslator Backend..."; \
    echo "========================================"; \
    echo "🔑 Encryption Environment Check:"; \
    if [ -n "$ENCRYPTION_KEY" ]; then echo "   ENCRYPTION_KEY: ✅ Set"; else echo "   ENCRYPTION_KEY: ❌ NOT SET"; fi; \
    if [ -n "$ENCRYPTION_KEY_FERNET_LEGACY" ]; then echo "   ENCRYPTION_KEY_FERNET_LEGACY: ✅ Set"; else echo "   ENCRYPTION_KEY_FERNET_LEGACY: ❌ NOT SET"; fi; \
    if [ -n "$ENCRYPTION_KEY_FERNET_LEGACY" ]; then \
        echo "🔐 Running encryption migration..."; \
        python migrations/upgrade_encryption_to_aes256gcm.py 2>&1 || echo "⚠️ Migration completed or failed"; \
    else \
        echo "ℹ️ No legacy key, skipping migration"; \
    fi; \
    echo "========================================"; \
    echo "🌐 Starting uvicorn..."; \
    exec uvicorn app.main:app --host 0.0.0.0 --port 9122 \
' 