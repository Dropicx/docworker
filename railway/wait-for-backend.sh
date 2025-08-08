#!/bin/sh
# Wait for backend to be ready before allowing health checks to pass

echo "Waiting for backend to start..."
for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:9122/api/health/simple > /dev/null 2>&1; then
        echo "Backend is ready!"
        exit 0
    fi
    echo "Waiting for backend... ($i/30)"
    sleep 2
done

echo "Backend failed to start within 60 seconds"
exit 1