# =============================================================================
# PP-StructureV3 OCR Server - Hetzner Terraform Configuration
# =============================================================================
# Usage:
#   1. Set HCLOUD_TOKEN environment variable or create terraform.tfvars
#   2. terraform init
#   3. terraform plan
#   4. terraform apply
#
# After deployment:
#   1. SSH to server: terraform output -raw ssh_command
#   2. Deploy: ./deploy.sh
#   3. Get API key: terraform output -raw api_key
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
  description = "Hetzner server type (CPX51 = 16 vCPU, 32GB RAM for PP-StructureV3)"
  type        = string
  default     = "cpx51"  # cpx51 = 16 vCPU, 32GB RAM, ~€67/mo - good for PP-StructureV3 CPU
}

variable "github_repo" {
  description = "GitHub repository URL for doctranslator"
  type        = string
  default     = "https://github.com/Dropicx/doctranslator.git"
}

variable "github_branch" {
  description = "Git branch to deploy"
  type        = string
  default     = "dev"
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
          PP-StructureV3 OCR Server
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

      - path: /opt/paddleocr/deploy.sh
        content: |
          #!/bin/bash
          set -e

          echo "=========================================="
          echo "PP-StructureV3 Deployment Script"
          echo "=========================================="

          cd /opt/paddleocr

          # Clone or update repo
          if [ ! -d "doctranslator" ]; then
              echo "📥 Cloning repository..."
              git clone -b ${var.github_branch} ${var.github_repo} doctranslator
          else
              echo "📥 Updating repository..."
              cd doctranslator && git pull origin ${var.github_branch} && cd ..
          fi

          # Copy paddleocr_service files to /opt/paddleocr
          echo "📁 Copying service files..."
          cp -r doctranslator/paddleocr_service/* /opt/paddleocr/

          # Build Docker image (CPU mode)
          echo "🔨 Building Docker image (CPU mode)..."
          echo "   This will take 5-10 minutes on first build..."
          docker build --build-arg USE_GPU=false -t ppstructure:cpu .

          # Stop old container if running
          docker-compose down 2>/dev/null || true

          # Start service
          echo "🚀 Starting service..."
          docker-compose up -d

          echo ""
          echo "⏳ Waiting for PP-StructureV3 to start..."
          echo "   (First startup downloads ~2GB of models)"

          for i in {1..30}; do
              if curl -sf http://localhost:9124/health > /dev/null 2>&1; then
                  echo ""
                  echo "✅ Service is healthy!"
                  curl -s http://localhost:9124/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:9124/health
                  break
              fi
              echo "   Waiting... ($i/30)"
              sleep 10
          done

          # Final check
          if ! curl -sf http://localhost:9124/health > /dev/null 2>&1; then
              echo "⚠️  Service not responding yet. Check logs:"
              echo "   docker-compose logs -f"
              exit 1
          fi

          echo ""
          echo "=========================================="
          echo "✅ Deployment complete!"
          echo "=========================================="
          echo ""
          echo "📋 Add these to your backend environment:"
          echo ""
          echo "   EXTERNAL_OCR_URL=http://$$(curl -s ifconfig.me):9124"
          echo "   EXTERNAL_API_KEY=$$(cat /opt/paddleocr/API_KEY.txt)"
          echo "   USE_EXTERNAL_OCR=true"
          echo ""
          echo "📊 Useful commands:"
          echo "   View logs:  docker-compose logs -f"
          echo "   Restart:    docker-compose restart"
          echo "   Stop:       docker-compose down"
          echo "   Update:     ./deploy.sh"
        permissions: '0755'

      - path: /opt/paddleocr/docker-compose.yml
        content: |
          version: '3.8'

          services:
            ppstructure:
              image: ppstructure:cpu
              container_name: ppstructure
              ports:
                - "9124:9124"
              env_file:
                - .env
              environment:
                - PYTHONUNBUFFERED=1
                - PADDLEOCR_DEFAULT_MODE=structured
              volumes:
                - paddle_models:/home/appuser/.paddlex
              restart: unless-stopped
              deploy:
                resources:
                  limits:
                    memory: 28G
              healthcheck:
                test: ["CMD", "curl", "-f", "http://localhost:9124/health"]
                interval: 30s
                timeout: 10s
                retries: 5
                start_period: 300s

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
      - mkdir -p /opt/paddleocr
      - chown -R root:root /opt/paddleocr
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

    final_message: "PP-StructureV3 VM ready! SSH in and run: cd /opt/paddleocr && ./deploy.sh"
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
    description = "Allow PP-StructureV3 API"
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
