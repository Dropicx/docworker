# =============================================================================
# Dify RAG Service (AWMF Guidelines) - Terraform Makefile
# =============================================================================

.PHONY: help init plan apply destroy destroy-keep-cert destroy-keep-volume output ssh logs health clean redeploy deploy-logs test-rag env

# SSH options for ephemeral servers
SSH_OPTS := -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null

help:
	@echo "Dify RAG Service Terraform Commands"
	@echo "===================================="
	@echo ""
	@echo "  make init              - Initialize Terraform"
	@echo "  make plan              - Preview changes"
	@echo "  make apply             - Create/update infrastructure (auto-deploys)"
	@echo "  make destroy-keep-volume - Destroy infra but KEEP volume + cert (recommended)"
	@echo "  make destroy-keep-cert - Destroy infra but KEEP SSL cert"
	@echo "  make destroy           - Destroy ALL (will fail due to volume/cert protection)"
	@echo "  make output            - Show outputs (IP, URL)"
	@echo "  make env               - Show backend environment variables"
	@echo "  make ssh               - SSH into server"
	@echo "  make logs              - Tail docker logs"
	@echo "  make deploy-logs       - Show deployment log"
	@echo "  make health            - Check service health via LB"
	@echo "  make test-rag          - Test RAG query endpoint (requires DIFY_APP_KEY)"
	@echo "  make redeploy          - Re-run deploy.sh on server"
	@echo "  make clean             - Remove Terraform files"
	@echo ""
	@echo "Quick start:"
	@echo "  1. Create Object Storage bucket 'awmf-guidelines' in Hetzner Console"
	@echo "  2. cp terraform.tfvars.example terraform.tfvars"
	@echo "  3. Edit terraform.tfvars with your credentials"
	@echo "  4. make init && make apply"
	@echo "  5. Wait ~5 minutes for auto-deployment (check: make deploy-logs)"
	@echo "  6. Test: make health"
	@echo ""
	@echo "Post-deploy (one-time via Dify UI):"
	@echo "  1. Log into https://rag.fra-la.de with init password"
	@echo "  2. Add Mistral as model provider"
	@echo "  3. Create Knowledge Base 'AWMF Leitlinien'"
	@echo "  4. Upload PDFs: python scripts/dify_upload_pdfs.py"
	@echo "  5. Create Chat App, get API key for backend"
	@echo ""
	@echo "NOTE: Use 'make destroy-keep-volume' to preserve data across rebuilds!"
	@echo ""

init:
	terraform init

plan:
	terraform plan

apply:
	terraform apply

destroy:
	terraform destroy

# Destroy everything EXCEPT the persistent volume and SSL certificate
# This preserves: postgres data, weaviate vectors, redis, and avoids LE rate limits
destroy-keep-volume:
	@echo "Destroying infrastructure but KEEPING volume and SSL certificate..."
	@echo "(This preserves your knowledge base data and avoids Let's Encrypt rate limits)"
	@echo ""
	terraform destroy \
		-target=hcloud_volume_attachment.rag_data \
		-target=hcloud_server.rag \
		-target=hcloud_firewall_attachment.rag \
		-target=hcloud_firewall.rag \
		-target=hcloud_load_balancer_target.rag \
		-target=hcloud_load_balancer_service.https \
		-target=hcloud_load_balancer_service.http_redirect \
		-target=hcloud_load_balancer_network.rag \
		-target=hcloud_load_balancer.rag \
		-target=hcloud_zone_rrset.rag \
		-target=hcloud_network_subnet.rag \
		-target=hcloud_network.rag \
		-target=random_password.root_password

# Destroy everything EXCEPT the SSL certificate (still destroys volume!)
destroy-keep-cert:
	@echo "Destroying infrastructure but KEEPING SSL certificate..."
	@echo "WARNING: This WILL destroy the persistent volume and all data!"
	@echo ""
	terraform destroy \
		-target=hcloud_volume_attachment.rag_data \
		-target=hcloud_volume.rag_data \
		-target=hcloud_server.rag \
		-target=hcloud_firewall_attachment.rag \
		-target=hcloud_firewall.rag \
		-target=hcloud_load_balancer_target.rag \
		-target=hcloud_load_balancer_service.https \
		-target=hcloud_load_balancer_service.http_redirect \
		-target=hcloud_load_balancer_network.rag \
		-target=hcloud_load_balancer.rag \
		-target=hcloud_zone_rrset.rag \
		-target=hcloud_network_subnet.rag \
		-target=hcloud_network.rag \
		-target=random_password.root_password

output:
	@echo ""
	@echo "=== Dify RAG Service Info ==="
	@terraform output -raw api_endpoint 2>/dev/null || echo "Run 'make apply' first"
	@echo ""
	@echo ""
	@terraform output -raw deploy_instructions 2>/dev/null || true

env:
	@echo ""
	@echo "=== Backend Environment Variables ==="
	@echo "DIFY_RAG_URL=$$(terraform output -raw api_endpoint 2>/dev/null)"
	@echo "DIFY_RAG_API_KEY=app-YOUR_DIFY_APP_KEY  # Get from Dify UI after creating Chat App"
	@echo "USE_DIFY_RAG=true"
	@echo ""

ssh:
	@IP=$$(terraform output -json server_public_ips | jq -r '.["dify-rag-1"]') && \
	echo "Connecting to dify-rag-1 at $$IP..." && \
	ssh $(SSH_OPTS) root@$$IP

logs:
	@IP=$$(terraform output -json server_public_ips | jq -r '.["dify-rag-1"]') && \
	ssh $(SSH_OPTS) root@$$IP "cd /opt/dify-rag/dify/docker && docker compose logs -f --tail=100"

deploy-logs:
	@IP=$$(terraform output -json server_public_ips | jq -r '.["dify-rag-1"]') && \
	echo "Showing deploy log for dify-rag-1 at $$IP..." && \
	ssh $(SSH_OPTS) root@$$IP "tail -100 /var/log/dify-rag-deploy.log"

health:
	@URL=$$(terraform output -raw api_endpoint) && \
	echo "Checking: $$URL/health" && \
	curl -s "$$URL/health" | python3 -m json.tool 2>/dev/null || curl -s "$$URL/health"

# Test RAG query - requires DIFY_APP_KEY environment variable
# Usage: DIFY_APP_KEY=app-xxx make test-rag
test-rag:
	@if [ -z "$$DIFY_APP_KEY" ]; then \
		echo "Error: Set DIFY_APP_KEY environment variable first"; \
		echo "Usage: DIFY_APP_KEY=app-xxx make test-rag"; \
		exit 1; \
	fi
	@URL=$$(terraform output -raw api_endpoint) && \
	echo "Testing RAG query at $$URL..." && \
	curl -s -X POST "$$URL/v1/chat-messages" \
		-H "Authorization: Bearer $$DIFY_APP_KEY" \
		-H "Content-Type: application/json" \
		-d '{"query": "Welche AWMF-Leitlinie gibt es zu Diabetes Typ 2?", "response_mode": "blocking", "user": "test"}' \
		| python3 -m json.tool

redeploy:
	@echo "Running deploy.sh on server (git pull + restart)..."
	@IP=$$(terraform output -json server_public_ips | jq -r '.["dify-rag-1"]') && \
	echo "=== Redeploying dify-rag-1 ($$IP) ===" && \
	ssh $(SSH_OPTS) root@$$IP "cd /opt/dify-rag && ./deploy.sh"

# Show Dify container status
status:
	@IP=$$(terraform output -json server_public_ips | jq -r '.["dify-rag-1"]') && \
	ssh $(SSH_OPTS) root@$$IP "cd /opt/dify-rag/dify/docker && docker compose ps"

# Show volume usage
volume:
	@IP=$$(terraform output -json server_public_ips | jq -r '.["dify-rag-1"]') && \
	ssh $(SSH_OPTS) root@$$IP "df -h /mnt/rag-data && echo '' && du -sh /mnt/rag-data/*"

clean:
	rm -rf .terraform
	rm -f .terraform.lock.hcl
	rm -f terraform.tfstate*
