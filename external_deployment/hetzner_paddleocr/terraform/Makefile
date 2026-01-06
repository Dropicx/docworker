# =============================================================================
# PP-StructureV3 OCR Server - Terraform Makefile
# =============================================================================

.PHONY: help init plan apply destroy output ssh deploy redeploy logs health api-key clean

# SSH options for ephemeral servers (skip host key verification)
SSH_OPTS := -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null

help:
	@echo "PP-StructureV3 Terraform Commands"
	@echo "=================================="
	@echo ""
	@echo "  make init      - Initialize Terraform"
	@echo "  make plan      - Preview changes"
	@echo "  make apply     - Create/update infrastructure (auto-deploys by default)"
	@echo "  make destroy   - Destroy infrastructure"
	@echo "  make output    - Show outputs (IP, env vars, commands)"
	@echo "  make ssh       - SSH into server"
	@echo "  make redeploy  - Re-run deploy.sh (git pull + rebuild)"
	@echo "  make logs      - Tail docker-compose logs"
	@echo "  make health    - Check service health"
	@echo "  make api-key   - Show API key"
	@echo "  make clean     - Remove Terraform files"
	@echo ""
	@echo "Quick start:"
	@echo "  1. cp terraform.tfvars.example terraform.tfvars"
	@echo "  2. Edit terraform.tfvars with your Hetzner token"
	@echo "  3. make init && make apply"
	@echo "  4. (deployment runs automatically with auto_deploy=true)"
	@echo ""
	@echo "Manual deployment (if auto_deploy=false):"
	@echo "  make ssh"
	@echo "  cd /opt/paddleocr && ./deploy.sh"

init:
	terraform init

plan:
	terraform plan

apply:
	terraform apply

destroy:
	terraform destroy

output:
	@echo ""
	@echo "=== Server Info ==="
	@terraform output -raw ssh_command 2>/dev/null || echo "Run 'make apply' first"
	@echo ""
	@echo ""
	@echo "=== Health Check ==="
	@terraform output -raw health_check_url 2>/dev/null || true
	@echo ""
	@echo ""
	@echo "=== Backend Environment Variables ==="
	@terraform output -raw backend_env_vars 2>/dev/null || true
	@echo ""

ssh:
	@IP=$$(terraform output -raw server_ip) && \
	ssh $(SSH_OPTS) root@$$IP

api-key:
	@terraform output -raw api_key

redeploy:
	@echo "Running deploy.sh on server (git pull + rebuild)..."
	@IP=$$(terraform output -raw server_ip) && \
	ssh $(SSH_OPTS) root@$$IP "cd /opt/paddleocr && ./deploy.sh"

logs:
	@IP=$$(terraform output -raw server_ip) && \
	ssh $(SSH_OPTS) root@$$IP "cd /opt/paddleocr && docker-compose logs -f"

health:
	@URL=$$(terraform output -raw health_check_url) && \
	curl -s "$$URL" | python3 -m json.tool 2>/dev/null || curl -s "$$URL"

clean:
	rm -rf .terraform
	rm -f .terraform.lock.hcl
	rm -f terraform.tfstate*
