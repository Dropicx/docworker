# =============================================================================
# PaddleOCR Terraform Makefile
# =============================================================================

.PHONY: help init plan apply destroy output ssh deploy clean

# SSH options for ephemeral servers (skip host key verification)
SSH_OPTS := -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null

help:
	@echo "PaddleOCR Terraform Commands"
	@echo "============================"
	@echo ""
	@echo "  make init      - Initialize Terraform"
	@echo "  make plan      - Preview changes"
	@echo "  make apply     - Create/update infrastructure"
	@echo "  make destroy   - Destroy infrastructure"
	@echo "  make output    - Show outputs (IP, commands)"
	@echo "  make ssh       - SSH into server"
	@echo "  make deploy    - Copy files and deploy service"
	@echo "  make api-key   - Show API key"
	@echo "  make clean     - Remove Terraform files"
	@echo ""
	@echo "Quick start:"
	@echo "  1. cp terraform.tfvars.example terraform.tfvars"
	@echo "  2. Edit terraform.tfvars with your Hetzner token"
	@echo "  3. make init && make apply"
	@echo "  4. make deploy"

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
	@echo "=== Copy Files Command ==="
	@terraform output -raw scp_command 2>/dev/null || true
	@echo ""
	@echo ""
	@echo "=== Railway Environment Variables ==="
	@terraform output -raw railway_env_vars 2>/dev/null || true
	@echo ""

ssh:
	@IP=$$(terraform output -raw server_ip) && \
	ssh $(SSH_OPTS) root@$$IP

api-key:
	@terraform output -raw api_key

deploy:
	@echo "Copying paddleocr_service files to server..."
	@IP=$$(terraform output -raw server_ip) && \
	scp $(SSH_OPTS) -r ../../paddleocr_service/* root@$$IP:/opt/paddleocr/
	@echo ""
	@echo "Running deploy.sh on server..."
	@IP=$$(terraform output -raw server_ip) && \
	ssh $(SSH_OPTS) root@$$IP "cd /opt/paddleocr && ./deploy.sh"

clean:
	rm -rf .terraform
	rm -f .terraform.lock.hcl
	rm -f terraform.tfstate*
