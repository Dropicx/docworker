# =============================================================================
# PP-StructureV3 OCR Server - Terraform Makefile
# =============================================================================

.PHONY: help init plan apply destroy destroy-keep-cert output ssh deploy redeploy logs health api-key clean

# SSH options for ephemeral servers (skip host key verification)
SSH_OPTS := -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null

help:
	@echo "PaddleOCR Terraform Commands"
	@echo "============================"
	@echo ""
	@echo "  make init              - Initialize Terraform"
	@echo "  make plan              - Preview changes"
	@echo "  make apply             - Create/update infrastructure (auto-deploys)"
	@echo "  make destroy-keep-cert - Destroy infra but KEEP SSL cert (recommended)"
	@echo "  make destroy           - Destroy ALL (will fail due to cert protection)"
	@echo "  make output            - Show outputs (IP, env vars, commands)"
	@echo "  make ssh N=1           - SSH into server N (1 or 2)"
	@echo "  make redeploy          - Re-run deploy.sh (git pull + rebuild)"
	@echo "  make logs N=1          - Tail docker-compose logs on server N"
	@echo "  make health            - Check service health"
	@echo "  make api-key           - Show API key"
	@echo "  make clean             - Remove Terraform files"
	@echo ""
	@echo "Quick start:"
	@echo "  1. cp terraform.tfvars.example terraform.tfvars"
	@echo "  2. Edit terraform.tfvars with your Hetzner token + GitHub token"
	@echo "  3. make init && make apply"
	@echo "  4. Wait ~10 minutes for auto-deployment"
	@echo "  5. Test: make health"
	@echo ""
	@echo "NOTE: Use 'make destroy-keep-cert' to avoid Let's Encrypt rate limits!"
	@echo ""

init:
	terraform init

plan:
	terraform plan

apply:
	terraform apply

destroy:
	terraform destroy

# Destroy everything EXCEPT the SSL certificate (avoids Let's Encrypt rate limits)
destroy-keep-cert:
	@echo "Destroying infrastructure but KEEPING SSL certificate..."
	@echo "(This avoids Let's Encrypt rate limit of 5 certs/domain/week)"
	@echo ""
	terraform destroy \
		-target=hcloud_server.paddleocr \
		-target=hcloud_firewall_attachment.paddleocr \
		-target=hcloud_firewall.paddleocr \
		-target=hcloud_load_balancer_target.paddleocr \
		-target=hcloud_load_balancer_service.https \
		-target=hcloud_load_balancer_service.http_redirect \
		-target=hcloud_load_balancer_network.paddleocr \
		-target=hcloud_load_balancer.paddleocr \
		-target=hcloud_zone_rrset.ocr \
		-target=hcloud_network_subnet.paddleocr \
		-target=hcloud_network.paddleocr \
		-target=random_password.root_password \
		-target=random_password.api_key

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
