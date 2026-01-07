# =============================================================================
# PaddleOCR 3.x CPU Server - Hetzner Terraform Configuration
# =============================================================================
# Lightweight OCR fallback server using PaddleOCR 3.x (standard mode)
#
# Usage:
#   1. Set HCLOUD_TOKEN environment variable or create terraform.tfvars
#   2. terraform init
#   3. terraform plan
#   4. terraform apply
#   5. SSH in and run: cd /opt/paddleocr && ./deploy.sh
#
# Get API key: terraform output -raw api_key
# =============================================================================

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
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
  description = "Hetzner Cloud API Token"
  type        = string
  sensitive   = true
}

variable "server_name" {
  description = "Name of the server"
  type        = string
  default     = "paddleocr"
}

variable "server_type" {
  description = "Hetzner server type (cpx21 = 3 vCPU, 4GB RAM - sufficient for PaddleOCR 3.x)"
  type        = string
  default     = "cpx21" # cpx21 = 3 vCPU, 4GB RAM, ~€8/mo - good for PaddleOCR 3.x CPU
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

variable "ssh_public_key_path" {
  description = "Path to SSH public key file"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "ssh_public_key" {
  description = "SSH public key content (overrides ssh_public_key_path if set)"
  type        = string
  default     = ""
}

# -----------------------------------------------------------------------------
# SSH Key
# -----------------------------------------------------------------------------

resource "hcloud_ssh_key" "paddleocr" {
  name       = "${var.server_name}-key"
  public_key = var.ssh_public_key != "" ? var.ssh_public_key : file(pathexpand(var.ssh_public_key_path))
}

# -----------------------------------------------------------------------------
# Generate API Key
# -----------------------------------------------------------------------------

resource "random_password" "api_key" {
  length  = 64
  special = false
}

# -----------------------------------------------------------------------------
# Cloud-Init Configuration
# -----------------------------------------------------------------------------

locals {
  cloud_init = <<-EOF
#cloud-config
package_update: true
package_upgrade: true

packages:
  - docker.io
  - docker-compose
  - git
  - curl
  - htop
  - ufw
  - fail2ban

bootcmd:
  - mkdir -p /opt/paddleocr

write_files:
  - path: /etc/motd
    content: |
      =====================================
      PaddleOCR 3.x CPU Server (Fallback)
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
      API_SECRET_KEY=${random_password.api_key.result}
      USE_GPU=false
    permissions: '0600'

  - path: /opt/paddleocr/API_KEY.txt
    content: |
      ${random_password.api_key.result}
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
                memory: 3G
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
  - ufw default deny incoming
  - ufw default allow outgoing
  - ufw allow 22/tcp
  - ufw allow 9124/tcp
  - ufw --force enable
  - chown -R root:root /opt/paddleocr
  - chmod 755 /opt/paddleocr/deploy.sh
  - fallocate -l 2G /swapfile
  - chmod 600 /swapfile
  - mkswap /swapfile
  - swapon /swapfile
  - echo '/swapfile none swap sw 0 0' >> /etc/fstab
  - echo 'vm.swappiness=10' >> /etc/sysctl.conf
  - sysctl -p
  - systemctl enable fail2ban
  - systemctl start fail2ban

final_message: "PaddleOCR VM ready! SSH in and run: cd /opt/paddleocr && ./deploy.sh"
EOF
}

# -----------------------------------------------------------------------------
# Server
# -----------------------------------------------------------------------------

resource "hcloud_server" "paddleocr" {
  name        = var.server_name
  image       = "ubuntu-24.04"
  server_type = var.server_type
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.paddleocr.id]
  user_data   = local.cloud_init

  labels = {
    service = "paddleocr"
    managed = "terraform"
  }

  public_net {
    ipv4_enabled = true
    ipv6_enabled = true
  }
}

# -----------------------------------------------------------------------------
# Firewall
# -----------------------------------------------------------------------------

resource "hcloud_firewall" "paddleocr" {
  name = "${var.server_name}-firewall"

  rule {
    description = "Allow SSH"
    direction   = "in"
    protocol    = "tcp"
    port        = "22"
    source_ips  = ["0.0.0.0/0", "::/0"]
  }

  rule {
    description = "Allow PaddleOCR API"
    direction   = "in"
    protocol    = "tcp"
    port        = "9124"
    source_ips  = ["0.0.0.0/0", "::/0"]
  }

  rule {
    description = "Allow ICMP"
    direction   = "in"
    protocol    = "icmp"
    source_ips  = ["0.0.0.0/0", "::/0"]
  }
}

resource "hcloud_firewall_attachment" "paddleocr" {
  firewall_id = hcloud_firewall.paddleocr.id
  server_ids  = [hcloud_server.paddleocr.id]
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "server_ip" {
  description = "Public IPv4 address of the server"
  value       = hcloud_server.paddleocr.ipv4_address
}

output "server_ipv6" {
  description = "Public IPv6 address of the server"
  value       = hcloud_server.paddleocr.ipv6_address
}

output "api_key" {
  description = "API key for PaddleOCR service"
  value       = random_password.api_key.result
  sensitive   = true
}

output "ssh_command" {
  description = "SSH command to connect to server"
  value       = "ssh root@${hcloud_server.paddleocr.ipv4_address}"
}

output "deploy_command" {
  description = "Command to deploy after SSH"
  value       = "cd /opt/paddleocr && ./deploy.sh"
}

output "backend_env_vars" {
  description = "Environment variables for your backend"
  value       = <<-EOF
    EXTERNAL_OCR_URL=http://${hcloud_server.paddleocr.ipv4_address}:9124
    EXTERNAL_API_KEY=<run: terraform output -raw api_key>
    USE_EXTERNAL_OCR=true
  EOF
}

output "health_check_url" {
  description = "Health check URL"
  value       = "http://${hcloud_server.paddleocr.ipv4_address}:9124/health"
}
