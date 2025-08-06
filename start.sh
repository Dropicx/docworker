#!/bin/bash

# Intelligent Docker Compose Launcher for Doctranslator
# Automatically detects and configures GPU support

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}🚀 Doctranslator - Intelligent Startup Script${NC}"
echo -e "${BLUE}================================================${NC}"

# Check if docker and docker-compose are installed
echo ""
echo "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    echo "Please install Docker Compose first: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✅ Docker and Docker Compose are installed${NC}"

# Run NVIDIA check script
echo ""
echo "Checking GPU configuration..."
if bash scripts/check-nvidia.sh; then
    GPU_MODE=$([ -f docker-compose.gpu.yml ] && echo "gpu" || echo "cpu")
else
    GPU_MODE="cpu"
fi

# Determine which compose files to use
echo ""
echo -e "${BLUE}Starting services...${NC}"

COMPOSE_FILES="-f docker-compose.yml"

if [ "$GPU_MODE" = "gpu" ] && [ -f docker-compose.gpu.yml ]; then
    COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.gpu.yml"
    echo -e "${GREEN}🎮 Using GPU-accelerated configuration${NC}"
elif [ -f docker-compose.cpu.yml ]; then
    COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.cpu.yml"
    echo -e "${YELLOW}💻 Using CPU-only configuration${NC}"
fi

# Parse command line arguments
COMMAND="${1:-up}"
shift || true

# Handle different commands
case "$COMMAND" in
    up|start)
        echo ""
        echo "Starting all services..."
        docker-compose $COMPOSE_FILES up -d "$@"
        
        echo ""
        echo -e "${GREEN}✅ Services started successfully!${NC}"
        echo ""
        echo "📝 Service URLs:"
        echo "   - Frontend: http://localhost:9121"
        echo "   - Backend API: http://localhost:9122"
        echo "   - Ollama: http://localhost:7869"
        echo ""
        echo "📊 Check status with: docker-compose ps"
        echo "📜 View logs with: docker-compose logs -f"
        ;;
    
    down|stop)
        echo "Stopping all services..."
        docker-compose $COMPOSE_FILES down "$@"
        echo -e "${GREEN}✅ Services stopped${NC}"
        ;;
    
    restart)
        echo "Restarting all services..."
        docker-compose $COMPOSE_FILES restart "$@"
        echo -e "${GREEN}✅ Services restarted${NC}"
        ;;
    
    logs)
        docker-compose $COMPOSE_FILES logs "$@"
        ;;
    
    ps|status)
        docker-compose $COMPOSE_FILES ps "$@"
        ;;
    
    pull)
        echo "Pulling latest images..."
        docker-compose $COMPOSE_FILES pull "$@"
        echo -e "${GREEN}✅ Images updated${NC}"
        ;;
    
    build)
        echo "Building services..."
        docker-compose $COMPOSE_FILES build "$@"
        echo -e "${GREEN}✅ Build completed${NC}"
        ;;
    
    exec)
        docker-compose $COMPOSE_FILES exec "$@"
        ;;
    
    config)
        echo "Effective configuration:"
        docker-compose $COMPOSE_FILES config "$@"
        ;;
    
    gpu-status)
        echo "GPU Status:"
        if [ "$GPU_MODE" = "gpu" ]; then
            echo -e "${GREEN}GPU acceleration is ENABLED${NC}"
            nvidia-smi || echo -e "${RED}nvidia-smi not available${NC}"
        else
            echo -e "${YELLOW}Running in CPU-only mode${NC}"
        fi
        ;;
    
    models)
        echo "Checking Ollama models..."
        docker-compose $COMPOSE_FILES exec ollama ollama list || echo "Ollama container not running"
        ;;
    
    help|--help|-h)
        echo "Usage: $0 [COMMAND] [OPTIONS]"
        echo ""
        echo "Commands:"
        echo "  up, start     Start all services (default)"
        echo "  down, stop    Stop all services"
        echo "  restart       Restart all services"
        echo "  logs          View service logs"
        echo "  ps, status    Show service status"
        echo "  pull          Pull latest images"
        echo "  build         Build services"
        echo "  exec          Execute command in service"
        echo "  config        Show effective configuration"
        echo "  gpu-status    Show GPU status"
        echo "  models        List Ollama models"
        echo "  help          Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0                    # Start all services"
        echo "  $0 up -d              # Start in detached mode"
        echo "  $0 logs -f ollama     # Follow Ollama logs"
        echo "  $0 exec ollama bash   # Shell into Ollama container"
        echo "  $0 down -v            # Stop and remove volumes"
        ;;
    
    *)
        # Pass through any other docker-compose commands
        docker-compose $COMPOSE_FILES "$COMMAND" "$@"
        ;;
esac

# Show GPU status at the end if running
if [ "$COMMAND" = "up" ] || [ "$COMMAND" = "start" ]; then
    echo ""
    if [ "$GPU_MODE" = "gpu" ]; then
        echo -e "${GREEN}🎮 GPU acceleration is active${NC}"
        echo "Monitor GPU usage with: watch nvidia-smi"
    else
        echo -e "${YELLOW}💻 Running in CPU mode${NC}"
        echo "To enable GPU: Fix any issues shown above and restart"
    fi
fi