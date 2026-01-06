# =============================================================================
# PaddleOCR External Server - Hetzner Terraform Configuration
# =============================================================================
# Usage:
#   1. Set HCLOUD_TOKEN environment variable or create terraform.tfvars
#   2. terraform init
#   3. terraform plan
#   4. terraform apply
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
  description = "Hetzner server type (CPX62 = 16 vCPU, 32GB RAM)"
  type        = string
  default     = "cpx51"  # cpx51 = 16 vCPU, 32GB RAM, ~€67/mo
}

variable "location" {
  description = "Hetzner datacenter location"
  type        = string
  default     = "fsn1"  # Falkenstein, Germany (closest to most EU regions)
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

    write_files:
      - path: /etc/motd
        content: |
          =====================================
          PaddleOCR External Server
          Managed by Terraform

          Service: /opt/paddleocr
          Port: 9123

          Commands:
            cd /opt/paddleocr
            docker-compose up -d
            docker-compose logs -f
            docker-compose down
          =====================================
        permissions: '0644'

      - path: /opt/paddleocr/.env
        content: |
          API_SECRET_KEY=${random_password.api_key.result}
        permissions: '0600'

      - path: /opt/paddleocr/API_KEY.txt
        content: |
          ${random_password.api_key.result}
        permissions: '0600'

      - path: /opt/paddleocr/docker-compose.yml
        content: |
          version: '3.8'

          services:
            paddleocr:
              build: .
              container_name: paddleocr
              ports:
                - "9123:9123"
              environment:
                - API_SECRET_KEY=$${API_SECRET_KEY}
                - PYTHONUNBUFFERED=1
              volumes:
                - paddleocr_models:/home/appuser/.paddleocr
                - paddleocr_paddlex:/home/appuser/.paddlex
              restart: unless-stopped
              deploy:
                resources:
                  limits:
                    memory: 28G
              healthcheck:
                test: ["CMD", "curl", "-f", "http://localhost:9123/health"]
                interval: 30s
                timeout: 10s
                retries: 3
                start_period: 120s

          volumes:
            paddleocr_models:
            paddleocr_paddlex:
        permissions: '0644'

      - path: /opt/paddleocr/deploy.sh
        content: |
          #!/bin/bash
          set -e
          cd /opt/paddleocr

          if [ ! -f Dockerfile ]; then
              echo "Dockerfile not found! Copy paddleocr_service files first:"
              echo "  scp -r paddleocr_service/* root@$$(curl -s ifconfig.me):/opt/paddleocr/"
              exit 1
          fi

          echo "Building Docker image..."
          docker-compose build

          echo "Starting service..."
          docker-compose up -d

          echo "Waiting for service..."
          sleep 15

          for i in {1..10}; do
              if curl -sf http://localhost:9123/health > /dev/null 2>&1; then
                  echo "Service is healthy!"
                  break
              fi
              echo "Attempt $i/10 - waiting..."
              sleep 10
          done

          echo ""
          echo "Deployment complete!"
          echo "Railway environment variables:"
          echo "  EXTERNAL_OCR_URL=http://$$(curl -s ifconfig.me):9123"
          echo "  EXTERNAL_API_KEY=$$(cat /opt/paddleocr/API_KEY.txt)"
          echo "  USE_EXTERNAL_OCR=true"
        permissions: '0755'

    runcmd:
      - systemctl enable docker
      - systemctl start docker
      - ufw default deny incoming
      - ufw default allow outgoing
      - ufw allow 22/tcp
      - ufw allow 9123/tcp
      - ufw --force enable
      - mkdir -p /opt/paddleocr/app
      - fallocate -l 8G /swapfile
      - chmod 600 /swapfile
      - mkswap /swapfile
      - swapon /swapfile
      - ["sh", "-c", "echo '/swapfile none swap sw 0 0' >> /etc/fstab"]
      - ["sh", "-c", "echo 'vm.swappiness=10' >> /etc/sysctl.conf"]
      - ["sh", "-c", "echo 'vm.vfs_cache_pressure=50' >> /etc/sysctl.conf"]
      - sysctl -p
      - systemctl enable fail2ban
      - systemctl start fail2ban

    final_message: "PaddleOCR VM ready! SSH in and run ./deploy.sh"
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
    port        = "9123"
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

output "scp_command" {
  description = "SCP command to copy service files"
  value       = "scp -r paddleocr_service/* root@${hcloud_server.paddleocr.ipv4_address}:/opt/paddleocr/"
}

output "railway_env_vars" {
  description = "Environment variables for Railway"
  value       = <<-EOF
    EXTERNAL_OCR_URL=http://${hcloud_server.paddleocr.ipv4_address}:9123
    EXTERNAL_API_KEY=<run: terraform output -raw api_key>
    USE_EXTERNAL_OCR=true
  EOF
}
