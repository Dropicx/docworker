# =============================================================================
# PaddleOCR 3.x HA Cluster - Hetzner Terraform Configuration
# =============================================================================
# High-availability OCR service with:
# - 2x cpx32 servers in private network
# - Load balancer with managed SSL
# - No public IPs on servers (console access only)
#
# Usage:
#   1. Set variables in terraform.tfvars
#   2. terraform init
#   3. terraform destroy (remove old single server)
#   4. terraform apply
#   5. Access each server via Hetzner Console, run: cd /opt/paddleocr && ./deploy.sh
#   6. Point your domain to the load balancer IP
#
# Get credentials: terraform output -json server_root_passwords
# =============================================================================

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.56" # DNS support added in 1.56.0
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
  }
}

# -----------------------------------------------------------------------------
# Provider Configuration
# -----------------------------------------------------------------------------

provider "hcloud" {
  token = var.hcloud_token
}

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------

variable "hcloud_token" {
  description = "Hetzner Cloud API Token (used for both Cloud and DNS)"
  type        = string
  sensitive   = true
}

variable "server_name" {
  description = "Base name for servers"
  type        = string
  default     = "paddleocr"
}

variable "server_type" {
  description = "Hetzner server type (cpx32 = 4 vCPU, 8GB RAM)"
  type        = string
  default     = "cpx32"
}

variable "server_count" {
  description = "Number of PaddleOCR servers"
  type        = number
  default     = 2
}

variable "dns_zone" {
  description = "DNS zone (e.g., fra-la.de)"
  type        = string
}

variable "dns_subdomain" {
  description = "Subdomain for OCR service (e.g., ocr)"
  type        = string
  default     = "ocr"
}

locals {
  domain_name = "${var.dns_subdomain}.${var.dns_zone}"
}

variable "github_repo" {
  description = "GitHub repository (format: owner/repo)"
  type        = string
  default     = "Dropicx/doctranslator"
}

variable "github_branch" {
  description = "Git branch to deploy"
  type        = string
  default     = "dev"
}

variable "github_token" {
  description = "GitHub Personal Access Token (for private repos)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "location" {
  description = "Hetzner datacenter location"
  type        = string
  default     = "fsn1"
}

variable "network_zone" {
  description = "Network zone for private network"
  type        = string
  default     = "eu-central"
}

# -----------------------------------------------------------------------------
# API Key (shared across all servers)
# -----------------------------------------------------------------------------

variable "api_key" {
  description = "API key for PaddleOCR service (optional - auto-generated if not set)"
  type        = string
  sensitive   = true
  default     = ""
}

resource "random_password" "api_key" {
  count   = var.api_key == "" ? 1 : 0
  length  = 64
  special = false
}

locals {
  api_key = var.api_key != "" ? var.api_key : random_password.api_key[0].result
}

# -----------------------------------------------------------------------------
# Generate Root Passwords (one per server for console access)
# -----------------------------------------------------------------------------

resource "random_password" "root_password" {
  count   = var.server_count
  length  = 32
  special = true
}

# -----------------------------------------------------------------------------
# Private Network
# -----------------------------------------------------------------------------

resource "hcloud_network" "paddleocr" {
  name     = "${var.server_name}-network"
  ip_range = "10.0.0.0/16"
}

resource "hcloud_network_subnet" "paddleocr" {
  network_id   = hcloud_network.paddleocr.id
  type         = "cloud"
  network_zone = var.network_zone
  ip_range     = "10.0.1.0/24"
}

# -----------------------------------------------------------------------------
# Cloud-Init Configuration (template for each server)
# -----------------------------------------------------------------------------

locals {
  cloud_init_template = <<-EOF
#cloud-config
package_update: true
package_upgrade: true

packages:
  - docker.io
  - docker-compose
  - git
  - curl
  - htop
  - fail2ban

chpasswd:
  list: |
    root:ROOT_PASSWORD_PLACEHOLDER
  expire: false

bootcmd:
  - mkdir -p /opt/paddleocr

write_files:
  - path: /etc/motd
    content: |
      =====================================
      PaddleOCR 3.x CPU Server (HA Cluster)
      Server: SERVER_NAME_PLACEHOLDER
      Managed by Terraform

      Service: /opt/paddleocr
      Port: 9124

      Commands:
        cd /opt/paddleocr
        ./deploy.sh          # First-time setup
        docker-compose up -d
        docker-compose logs -f
        docker-compose down
      =====================================
    permissions: '0644'

  - path: /opt/paddleocr/.env
    content: |
      API_SECRET_KEY=${local.api_key}
      USE_GPU=false
    permissions: '0600'

  - path: /opt/paddleocr/API_KEY.txt
    content: |
      ${local.api_key}
    permissions: '0600'

  - path: /opt/paddleocr/.github_token
    content: |
      ${var.github_token}
    permissions: '0600'

  - path: /opt/paddleocr/.repo
    content: |
      ${var.github_repo}
    permissions: '0644'

  - path: /opt/paddleocr/.branch
    content: |
      ${var.github_branch}
    permissions: '0644'

  - path: /opt/paddleocr/deploy.sh
    encoding: b64
    content: ${filebase64("${path.module}/scripts/deploy.sh")}
    permissions: '0755'

  - path: /opt/paddleocr/docker-compose.yml
    content: |
      version: '3.8'

      services:
        paddleocr:
          image: paddleocr:cpu
          container_name: paddleocr
          ports:
            - "9124:9124"
          env_file:
            - .env
          environment:
            - PYTHONUNBUFFERED=1
          volumes:
            - paddle_models:/home/appuser/.paddlex
          restart: unless-stopped
          deploy:
            resources:
              limits:
                memory: 6G
          healthcheck:
            test: ["CMD", "curl", "-f", "http://localhost:9124/health"]
            interval: 30s
            timeout: 10s
            retries: 5
            start_period: 120s

      volumes:
        paddle_models:
    permissions: '0644'

runcmd:
  - systemctl enable docker
  - systemctl start docker
  - chown -R root:root /opt/paddleocr
  - chmod 755 /opt/paddleocr/deploy.sh
  - fallocate -l 4G /swapfile
  - chmod 600 /swapfile
  - mkswap /swapfile
  - swapon /swapfile
  - echo '/swapfile none swap sw 0 0' >> /etc/fstab
  - echo 'vm.swappiness=10' >> /etc/sysctl.conf
  - sysctl -p
  - systemctl enable fail2ban
  - systemctl start fail2ban
  # Wait for Docker to be fully ready, then auto-deploy
  - |
    until docker info >/dev/null 2>&1; do
      echo "Waiting for Docker..."
      sleep 5
    done
    echo "Docker ready, starting PaddleOCR deployment..."
    cd /opt/paddleocr && ./deploy.sh >> /var/log/paddleocr-deploy.log 2>&1 &

final_message: "PaddleOCR deployment started! Check /var/log/paddleocr-deploy.log for progress."
EOF
}

# -----------------------------------------------------------------------------
# Servers (Private Network Only)
# -----------------------------------------------------------------------------

resource "hcloud_server" "paddleocr" {
  count       = var.server_count
  name        = "${var.server_name}-${count.index + 1}"
  image       = "ubuntu-24.04"
  server_type = var.server_type
  location    = var.location

  user_data = replace(
    replace(
      local.cloud_init_template,
      "ROOT_PASSWORD_PLACEHOLDER",
      random_password.root_password[count.index].result
    ),
    "SERVER_NAME_PLACEHOLDER",
    "${var.server_name}-${count.index + 1}"
  )

  labels = {
    service = "paddleocr"
    managed = "terraform"
    index   = tostring(count.index + 1)
  }

  # No public IP - private network only
  public_net {
    ipv4_enabled = false
    ipv6_enabled = false
  }

  network {
    network_id = hcloud_network.paddleocr.id
    ip         = "10.0.1.${count.index + 10}"
  }

  depends_on = [hcloud_network_subnet.paddleocr]
}

# -----------------------------------------------------------------------------
# Load Balancer
# -----------------------------------------------------------------------------

resource "hcloud_load_balancer" "paddleocr" {
  name               = "${var.server_name}-lb"
  load_balancer_type = "lb11"
  location           = var.location

  labels = {
    service = "paddleocr"
    managed = "terraform"
  }
}

# Attach LB to private network
resource "hcloud_load_balancer_network" "paddleocr" {
  load_balancer_id = hcloud_load_balancer.paddleocr.id
  network_id       = hcloud_network.paddleocr.id
  ip               = "10.0.1.2"

  depends_on = [hcloud_network_subnet.paddleocr]
}

# Add servers as targets
resource "hcloud_load_balancer_target" "paddleocr" {
  count            = var.server_count
  type             = "server"
  load_balancer_id = hcloud_load_balancer.paddleocr.id
  server_id        = hcloud_server.paddleocr[count.index].id
  use_private_ip   = true

  depends_on = [hcloud_load_balancer_network.paddleocr]
}

# Managed SSL Certificate
resource "hcloud_managed_certificate" "paddleocr" {
  name         = "${var.server_name}-cert"
  domain_names = [local.domain_name]

  labels = {
    service = "paddleocr"
    managed = "terraform"
  }
}

# HTTPS Service (terminates SSL, forwards to HTTP:9124)
resource "hcloud_load_balancer_service" "https" {
  load_balancer_id = hcloud_load_balancer.paddleocr.id
  protocol         = "https"
  listen_port      = 443
  destination_port = 9124

  http {
    certificates = [hcloud_managed_certificate.paddleocr.id]
  }

  health_check {
    protocol = "http"
    port     = 9124
    interval = 15
    timeout  = 10
    retries  = 3

    http {
      path         = "/health"
      status_codes = ["2??", "3??"]
    }
  }
}

# HTTP to HTTPS redirect
resource "hcloud_load_balancer_service" "http_redirect" {
  load_balancer_id = hcloud_load_balancer.paddleocr.id
  protocol         = "http"
  listen_port      = 80
  destination_port = 9124

  health_check {
    protocol = "http"
    port     = 9124
    interval = 15
    timeout  = 10
    retries  = 3

    http {
      path         = "/health"
      status_codes = ["2??", "3??"]
    }
  }
}

# -----------------------------------------------------------------------------
# DNS Configuration (Hetzner Cloud integrated DNS)
# -----------------------------------------------------------------------------

# Create A record for subdomain pointing to load balancer
# Note: Zone must already exist in Hetzner DNS (transferred domain)
resource "hcloud_zone_rrset" "ocr" {
  zone = var.dns_zone
  name = var.dns_subdomain
  type = "A"
  ttl  = 300
  records = [
    { value = hcloud_load_balancer.paddleocr.ipv4 }
  ]
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "load_balancer_ip" {
  description = "Public IPv4 address of the load balancer (point your DNS here)"
  value       = hcloud_load_balancer.paddleocr.ipv4
}

output "api_endpoint" {
  description = "API endpoint URL"
  value       = "https://${local.domain_name}"
}

output "api_key" {
  description = "API key for PaddleOCR service"
  value       = local.api_key
  sensitive   = true
}

output "server_root_passwords" {
  description = "Root passwords for console access (use Hetzner Console)"
  value       = { for i, p in random_password.root_password : "${var.server_name}-${i + 1}" => p.result }
  sensitive   = true
}

output "server_private_ips" {
  description = "Private IPs of servers"
  value       = { for i, s in hcloud_server.paddleocr : s.name => "10.0.1.${i + 10}" }
}

output "deploy_instructions" {
  description = "Deployment instructions"
  value       = <<-EOF

    ============================================
    PaddleOCR HA Cluster Deployment
    ============================================

    DNS automatically configured: ${local.domain_name} → ${hcloud_load_balancer.paddleocr.ipv4}

    1. Deploy each server via Hetzner Console:
       - Go to: https://console.hetzner.cloud
       - Open each server's console
       - Login as root (get password: terraform output -json server_root_passwords)
       - Run: cd /opt/paddleocr && ./deploy.sh

    2. Backend environment variables:
       EXTERNAL_OCR_URL=https://${local.domain_name}
       EXTERNAL_API_KEY=<run: terraform output -raw api_key>
       USE_EXTERNAL_OCR=true

    3. Health check: https://${local.domain_name}/health

    ============================================
  EOF
}
