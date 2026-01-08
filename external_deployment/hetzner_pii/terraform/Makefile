# =============================================================================
# SpaCy PII Service - Terraform Makefile
# =============================================================================

.PHONY: help init plan apply destroy output ssh logs health api-key clean redeploy test-pii

# SSH options for ephemeral servers
SSH_OPTS := -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null

help:
	@echo "SpaCy PII Service Terraform Commands"
	@echo "====================================="
	@echo ""
	@echo "  make init         - Initialize Terraform"
	@echo "  make plan         - Preview changes"
	@echo "  make apply        - Create/update infrastructure (auto-deploys)"
	@echo "  make destroy      - Destroy infrastructure"
	@echo "  make output       - Show outputs (IP, env vars)"
	@echo "  make ssh N=1      - SSH into server N (1 or 2)"
	@echo "  make logs N=1     - Tail docker logs on server N"
	@echo "  make deploy-logs  - Show deployment log on server N"
	@echo "  make health       - Check service health via LB"
	@echo "  make test-pii     - Test PII removal endpoint"
	@echo "  make redeploy     - Re-run deploy.sh on all servers"
	@echo "  make api-key      - Show API key"
	@echo "  make clean        - Remove Terraform files"
	@echo ""
	@echo "Quick start:"
	@echo "  1. cp terraform.tfvars.example terraform.tfvars"
	@echo "  2. Edit terraform.tfvars with your Hetzner token + GitHub token"
	@echo "  3. make init && make apply"
	@echo "  4. Wait ~15 minutes for auto-deployment (check: make deploy-logs N=1)"
	@echo "  5. Test: make health && make test-pii"
	@echo ""

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
	@echo "=== PII Service Info ==="
	@terraform output -raw api_endpoint 2>/dev/null || echo "Run 'make apply' first"
	@echo ""
	@echo ""
	@echo "=== Backend Environment Variables ==="
	@echo "EXTERNAL_PII_URL=$$(terraform output -raw api_endpoint 2>/dev/null)"
	@echo "EXTERNAL_PII_API_KEY=$$(terraform output -raw api_key 2>/dev/null)"
	@echo "USE_EXTERNAL_PII=true"
	@echo ""

ssh:
	@N=$${N:-1}; \
	IP=$$(terraform output -json server_public_ips | jq -r '.["pii-'$$N'"]') && \
	echo "Connecting to pii-$$N at $$IP..." && \
	ssh $(SSH_OPTS) root@$$IP

logs:
	@N=$${N:-1}; \
	IP=$$(terraform output -json server_public_ips | jq -r '.["pii-'$$N'"]') && \
	ssh $(SSH_OPTS) root@$$IP "cd /opt/pii && docker-compose logs -f"

health:
	@URL=$$(terraform output -raw api_endpoint) && \
	echo "Checking: $$URL/health" && \
	curl -s "$$URL/health" | python3 -m json.tool 2>/dev/null || curl -s "$$URL/health"

api-key:
	@terraform output -raw api_key

test-pii:
	@URL=$$(terraform output -raw api_endpoint) && \
	KEY=$$(terraform output -raw api_key) && \
	echo "Testing PII removal at $$URL..." && \
	curl -s -X POST "$$URL/remove-pii" \
		-H "X-API-Key: $$KEY" \
		-H "Content-Type: application/json" \
		-d '{"text": "Patient Max Mustermann, geboren 15.03.1985, wohnhaft Musterstraße 123, 12345 Berlin.", "language": "de"}' \
		| python3 -m json.tool

redeploy:
	@echo "Running deploy.sh on all servers (git pull + rebuild)..."
	@for i in 1 2; do \
		IP=$$(terraform output -json server_public_ips | jq -r '.["pii-'$$i'"]'); \
		if [ "$$IP" != "null" ] && [ -n "$$IP" ]; then \
			echo "=== Redeploying pii-$$i ($$IP) ==="; \
			ssh $(SSH_OPTS) root@$$IP "cd /opt/pii && ./deploy.sh" || echo "Failed on pii-$$i"; \
		fi; \
	done

deploy-logs:
	@N=$${N:-1}; \
	IP=$$(terraform output -json server_public_ips | jq -r '.["pii-'$$N'"]') && \
	echo "Showing deploy log for pii-$$N at $$IP..." && \
	ssh $(SSH_OPTS) root@$$IP "tail -100 /var/log/pii-deploy.log"

clean:
	rm -rf .terraform
	rm -f .terraform.lock.hcl
	rm -f terraform.tfstate*
