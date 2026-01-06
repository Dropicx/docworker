# =============================================================================
# PP-StructureV3 - Vast.ai Deployment Makefile
# =============================================================================

.PHONY: help build tag push all build-push setup-buildx health logs ssh

# Configuration - Update these for your setup
DOCKERHUB_USER ?= your-dockerhub-username
IMAGE_NAME ?= ppstructure
TAG ?= gpu
VASTAI_IP ?=

# Full image path
FULL_IMAGE = $(DOCKERHUB_USER)/$(IMAGE_NAME):$(TAG)

# Paths
PADDLEOCR_DIR = ../../paddleocr_service

help:
	@echo "PP-StructureV3 Vast.ai Deployment"
	@echo "=================================="
	@echo ""
	@echo "Configuration:"
	@echo "  DOCKERHUB_USER = $(DOCKERHUB_USER)"
	@echo "  IMAGE_NAME     = $(IMAGE_NAME)"
	@echo "  TAG            = $(TAG)"
	@echo "  FULL_IMAGE     = $(FULL_IMAGE)"
	@echo ""
	@echo "Commands:"
	@echo "  make setup-buildx       - Setup buildx for cross-platform builds (run once)"
	@echo "  make build              - Build GPU Docker image (linux/amd64)"
	@echo "  make tag                - Tag image for Docker Hub"
	@echo "  make push               - Push image to Docker Hub"
	@echo "  make all                - Build, tag, and push"
	@echo "  make build-push         - Build and push directly (faster)"
	@echo ""
	@echo "Instance commands (pass IP=x.x.x.x):"
	@echo "  make health IP=x.x.x.x  - Check instance health"
	@echo "  make ssh IP=x.x.x.x     - SSH into instance"
	@echo "  make logs IP=x.x.x.x    - View container logs"
	@echo ""
	@echo "Usage (from Apple Silicon Mac):"
	@echo "  1. make setup-buildx              (once)"
	@echo "  2. export DOCKERHUB_USER=yourusername"
	@echo "  3. docker login"
	@echo "  4. make build-push                (builds linux/amd64 & pushes)"
	@echo "  5. Create vast.ai template with: $(FULL_IMAGE)"
	@echo "  6. Rent instance, then: make health IP=<ip>"

build:
	@echo "Building GPU Docker image for linux/amd64..."
	@echo "(Cross-compiling from ARM64 to x86_64 - this may take a while)"
	cd $(PADDLEOCR_DIR) && docker buildx build --platform linux/amd64 --build-arg USE_GPU=true -t $(IMAGE_NAME):$(TAG) --load .
	@echo ""
	@echo "Built: $(IMAGE_NAME):$(TAG) (linux/amd64)"

tag:
	@echo "Tagging image for Docker Hub..."
	docker tag $(IMAGE_NAME):$(TAG) $(FULL_IMAGE)
	@echo ""
	@echo "Tagged: $(FULL_IMAGE)"

push:
	@echo "Pushing to Docker Hub..."
	docker push $(FULL_IMAGE)
	@echo ""
	@echo "Pushed: $(FULL_IMAGE)"

all: build tag push
	@echo ""
	@echo "=========================================="
	@echo "Done! Image available at: $(FULL_IMAGE)"
	@echo "=========================================="

# Faster: build and push directly without loading locally
build-push:
	@echo "Building and pushing GPU image for linux/amd64..."
	@echo "(This is faster than build+push as it doesn't load locally)"
	cd $(PADDLEOCR_DIR) && docker buildx build --platform linux/amd64 \
		--build-arg USE_GPU=true \
		-t $(FULL_IMAGE) \
		--push .
	@echo ""
	@echo "Pushed: $(FULL_IMAGE)"

# Setup buildx if not already configured
setup-buildx:
	@echo "Setting up Docker buildx for cross-platform builds..."
	docker buildx create --name multiarch --driver docker-container --use 2>/dev/null || docker buildx use multiarch
	docker buildx inspect --bootstrap
	@echo ""
	@echo "Buildx ready for cross-platform builds"

# Instance commands - pass IP=x.x.x.x
health:
ifndef IP
	@echo "Error: Set IP variable. Usage: make health IP=x.x.x.x"
	@exit 1
endif
	@curl -s "http://$(IP):9124/health" | python3 -m json.tool 2>/dev/null || curl -s "http://$(IP):9124/health"

ssh:
ifndef IP
	@echo "Error: Set IP variable. Usage: make ssh IP=x.x.x.x"
	@exit 1
endif
	ssh -o StrictHostKeyChecking=no root@$(IP)

logs:
ifndef IP
	@echo "Error: Set IP variable. Usage: make logs IP=x.x.x.x"
	@exit 1
endif
	ssh -o StrictHostKeyChecking=no root@$(IP) "docker logs -f ppstructure"
