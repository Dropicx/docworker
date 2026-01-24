# =============================================================================
# Dify RAG Service - Hetzner Terraform Configuration
# =============================================================================
# Self-hosted Dify RAG service for AWMF medical guideline queries:
# - 1x cx43 server (8 vCPU, 16 GB RAM)
# - Persistent volume for runtime data (postgres, weaviate, redis)
# - Load balancer with managed SSL
# - PDFs stored separately in Hetzner Object Storage
#
# Usage:
#   1. Set variables in terraform.tfvars
#   2. terraform init
#   3. terraform apply
#   4. Wait for auto-deployment to complete
#
# Get credentials: terraform output -json server_root_passwords
# =============================================================================

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.56"
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
  default     = "dify-rag"
}

variable "server_type" {
  description = "Hetzner server type (cx43 = 8 vCPU, 16GB RAM)"
  type        = string
  default     = "cx43"
}

variable "server_count" {
  description = "Number of Dify RAG servers"
  type        = number
  default     = 1
}

variable "dns_zone" {
  description = "DNS zone (e.g., fra-la.de)"
  type        = string
}

variable "dns_subdomain" {
  description = "Subdomain for RAG service (e.g., rag)"
  type        = string
  default     = "rag"
}

locals {
  domain_name = "${var.dns_subdomain}.${var.dns_zone}"
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

# Dify-specific variables
variable "mistral_api_key" {
  description = "Mistral API key for Dify LLM + embedding provider"
  type        = string
  sensitive   = true
}

variable "dify_secret_key" {
  description = "Dify application secret key"
  type        = string
  sensitive   = true
}

variable "dify_init_password" {
  description = "Dify initial admin password"
  type        = string
  default     = "changeme123"
}

# Object Storage variables (for PDF source)
variable "s3_access_key" {
  description = "Hetzner Object Storage access key"
  type        = string
  sensitive   = true
}

variable "s3_secret_key" {
  description = "Hetzner Object Storage secret key"
  type        = string
  sensitive   = true
}

variable "s3_endpoint" {
  description = "Hetzner Object Storage endpoint URL"
  type        = string
  default     = "https://fsn1.your-objectstorage.com"
}

variable "s3_bucket" {
  description = "Object Storage bucket name for AWMF PDFs"
  type        = string
  default     = "awmf-guidelines"
}

# -----------------------------------------------------------------------------
# Generate Root Password
# -----------------------------------------------------------------------------

resource "random_password" "root_password" {
  count   = var.server_count
  length  = 32
  special = false
}

# -----------------------------------------------------------------------------
# Private Network (separate from PII - uses 10.2.0.0/16)
# -----------------------------------------------------------------------------

resource "hcloud_network" "rag" {
  name     = "${var.server_name}-network"
  ip_range = "10.2.0.0/16"
}

resource "hcloud_network_subnet" "rag" {
  network_id   = hcloud_network.rag.id
  type         = "cloud"
  network_zone = var.network_zone
  ip_range     = "10.2.1.0/24"
}

# -----------------------------------------------------------------------------
# Persistent Volume for Dify Runtime Data
# -----------------------------------------------------------------------------

resource "hcloud_volume" "rag_data" {
  name     = "${var.server_name}-data"
  size     = 30 # GB (postgres + weaviate vectors + redis, no raw PDFs)
  location = var.location
  format   = "ext4"

  lifecycle {
    prevent_destroy = true # Survives terraform destroy
  }
}

resource "hcloud_volume_attachment" "rag_data" {
  volume_id = hcloud_volume.rag_data.id
  server_id = hcloud_server.rag[0].id
  automount = true
}

# -----------------------------------------------------------------------------
# Cloud-Init Configuration
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
  - s3cmd

chpasswd:
  list: |
    root:ROOT_PASSWORD_PLACEHOLDER
  expire: false

bootcmd:
  - mkdir -p /mnt/rag-data
  - mkdir -p /opt/dify-rag

write_files:
  - path: /etc/motd
    content: |
      =====================================
      Dify RAG Service (AWMF Guidelines)
      Server: SERVER_NAME_PLACEHOLDER
      Managed by Terraform

      Service: /opt/dify-rag
      Port: 80 (Nginx -> Dify)

      Commands:
        systemctl status dify-rag
        journalctl -u dify-rag -f
        cd /opt/dify-rag && docker compose logs -f
      =====================================
    permissions: '0644'

  # Dify environment configuration
  - path: /opt/dify-rag/.env
    content: |
      # Dify Core Settings
      SECRET_KEY=${var.dify_secret_key}
      INIT_PASSWORD=${var.dify_init_password}
      CONSOLE_WEB_URL=https://${local.domain_name}
      SERVICE_API_URL=https://${local.domain_name}
      ALLOW_REGISTER=false
      UPLOAD_FILE_SIZE_LIMIT=50

      # Vector Store
      VECTOR_STORE=weaviate
      WEAVIATE_ENDPOINT=http://weaviate:8080

      # Database
      DB_USERNAME=dify
      DB_PASSWORD=${random_password.root_password[0].result}
      DB_HOST=db
      DB_PORT=5432
      DB_DATABASE=dify

      # Redis
      REDIS_HOST=redis
      REDIS_PORT=6379

      # Mistral API (LLM + Embeddings)
      MISTRAL_API_KEY=${var.mistral_api_key}
    permissions: '0600'
    owner: root:root

  # Docker Compose override for persistent volume paths
  - path: /opt/dify-rag/docker-compose.override.yml
    content: |
      version: '3.8'
      services:
        db:
          volumes:
            - /mnt/rag-data/postgres:/var/lib/postgresql/data
        weaviate:
          volumes:
            - /mnt/rag-data/weaviate:/var/lib/weaviate
        redis:
          volumes:
            - /mnt/rag-data/redis:/data
        api:
          volumes:
            - /mnt/rag-data/storage:/app/api/storage
        worker:
          volumes:
            - /mnt/rag-data/storage:/app/api/storage
    permissions: '0644'

  # S3 configuration for Object Storage access
  - path: /root/.s3cfg
    content: |
      [default]
      access_key = ${var.s3_access_key}
      secret_key = ${var.s3_secret_key}
      host_base = ${replace(var.s3_endpoint, "https://", "")}
      host_bucket = %(bucket)s.${replace(var.s3_endpoint, "https://", "")}
      use_https = True
    permissions: '0600'
    owner: root:root

  - path: /opt/dify-rag/deploy.sh
    encoding: b64
    content: ${filebase64("${path.module}/scripts/deploy.sh")}
    permissions: '0755'

  # Systemd service for auto-restart on reboot
  - path: /etc/systemd/system/dify-rag.service
    content: |
      [Unit]
      Description=Dify RAG Service
      Requires=docker.service
      After=docker.service

      [Service]
      Type=oneshot
      RemainAfterExit=yes
      WorkingDirectory=/opt/dify-rag/dify/docker
      ExecStart=/usr/bin/docker compose -f docker-compose.yaml -f /opt/dify-rag/docker-compose.override.yml up -d
      ExecStop=/usr/bin/docker compose -f docker-compose.yaml -f /opt/dify-rag/docker-compose.override.yml down
      Restart=on-failure
      RestartSec=10

      [Install]
      WantedBy=multi-user.target
    permissions: '0644'

  # Watchdog script for self-healing
  - path: /opt/dify-rag/watchdog.sh
    content: |
      #!/bin/bash
      # Watchdog: restart service if health check fails
      if ! curl -sf http://localhost:80/health > /dev/null 2>&1; then
        echo "$(date) Health check failed, restarting..." >> /var/log/dify-rag-watchdog.log
        cd /opt/dify-rag/dify/docker && docker compose -f docker-compose.yaml -f /opt/dify-rag/docker-compose.override.yml restart
      fi
    permissions: '0755'

  # Logrotate for deployment logs
  - path: /etc/logrotate.d/dify-rag
    content: |
      /var/log/dify-rag-deploy.log /var/log/dify-rag-watchdog.log {
        daily
        rotate 7
        compress
        delaycompress
        missingok
        notifempty
        create 640 root root
      }
    permissions: '0644'

runcmd:
  # Docker setup
  - systemctl enable docker
  - systemctl start docker
  # Mount volume if not already mounted
  - |
    if ! mountpoint -q /mnt/rag-data; then
      VOLUME_DEV=$(lsblk -o NAME,SIZE -b | grep -v "loop\|NAME" | awk '{if ($2 > 29000000000 && $2 < 35000000000) print "/dev/"$1}' | head -1)
      if [ -n "$VOLUME_DEV" ]; then
        mount "$VOLUME_DEV" /mnt/rag-data
        echo "$VOLUME_DEV /mnt/rag-data ext4 defaults 0 2" >> /etc/fstab
      fi
    fi
  # Create volume directories
  - mkdir -p /mnt/rag-data/postgres
  - mkdir -p /mnt/rag-data/weaviate
  - mkdir -p /mnt/rag-data/redis
  - mkdir -p /mnt/rag-data/storage
  # Secure file ownership
  - chown -R root:root /opt/dify-rag
  - chmod 755 /opt/dify-rag/deploy.sh
  - chmod 600 /opt/dify-rag/.env
  # Fail2ban for security
  - systemctl enable fail2ban
  - systemctl start fail2ban
  # Enable systemd service for auto-restart on reboot
  - systemctl daemon-reload
  - systemctl enable dify-rag.service
  # Watchdog cron - check health every 5 minutes
  - echo '*/5 * * * * /opt/dify-rag/watchdog.sh' | crontab -
  # Wait for Docker, then deploy and start systemd service
  - |
    until docker info >/dev/null 2>&1; do
      echo "Waiting for Docker..."
      sleep 5
    done
    echo "Docker ready, starting Dify RAG service deployment..."
    cd /opt/dify-rag && ./deploy.sh >> /var/log/dify-rag-deploy.log 2>&1
    # Start via systemd after initial deploy
    systemctl start dify-rag.service

final_message: "Dify RAG service deployment complete! Service managed by systemd."
EOF
}

# -----------------------------------------------------------------------------
# Servers (Private Network Only)
# -----------------------------------------------------------------------------

resource "hcloud_server" "rag" {
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
    service = "dify-rag"
    managed = "terraform"
    index   = tostring(count.index + 1)
  }

  public_net {
    ipv4_enabled = true
    ipv6_enabled = false
  }

  network {
    network_id = hcloud_network.rag.id
    ip         = "10.2.1.${count.index + 10}"
  }

  depends_on = [hcloud_network_subnet.rag]
}

# -----------------------------------------------------------------------------
# Firewall
# -----------------------------------------------------------------------------

resource "hcloud_firewall" "rag" {
  name = "${var.server_name}-firewall"

  rule {
    description = "Allow SSH from anywhere"
    direction   = "in"
    protocol    = "tcp"
    port        = "22"
    source_ips  = ["0.0.0.0/0", "::/0"]
  }

  rule {
    description = "Allow HTTP (for LB health checks)"
    direction   = "in"
    protocol    = "tcp"
    port        = "80"
    source_ips  = ["0.0.0.0/0", "::/0"]
  }

  rule {
    description = "Allow private network - all traffic"
    direction   = "in"
    protocol    = "tcp"
    port        = "any"
    source_ips  = ["10.2.0.0/16"]
  }

  rule {
    description = "Allow private network - ICMP"
    direction   = "in"
    protocol    = "icmp"
    source_ips  = ["10.2.0.0/16"]
  }
}

resource "hcloud_firewall_attachment" "rag" {
  firewall_id = hcloud_firewall.rag.id
  server_ids  = [for s in hcloud_server.rag : s.id]
}

# -----------------------------------------------------------------------------
# Load Balancer
# -----------------------------------------------------------------------------

resource "hcloud_load_balancer" "rag" {
  name               = "${var.server_name}-lb"
  load_balancer_type = "lb11"
  location           = var.location

  labels = {
    service = "dify-rag"
    managed = "terraform"
  }
}

resource "hcloud_load_balancer_network" "rag" {
  load_balancer_id = hcloud_load_balancer.rag.id
  network_id       = hcloud_network.rag.id
  ip               = "10.2.1.2"

  depends_on = [hcloud_network_subnet.rag]
}

resource "hcloud_load_balancer_target" "rag" {
  count            = var.server_count
  type             = "server"
  load_balancer_id = hcloud_load_balancer.rag.id
  server_id        = hcloud_server.rag[count.index].id
  use_private_ip   = true

  depends_on = [hcloud_load_balancer_network.rag]
}

# Managed SSL Certificate
resource "hcloud_managed_certificate" "rag" {
  name         = "${var.server_name}-cert"
  domain_names = [local.domain_name]

  labels = {
    service = "dify-rag"
    managed = "terraform"
  }

  lifecycle {
    prevent_destroy = true
  }
}

# HTTPS Service
resource "hcloud_load_balancer_service" "https" {
  load_balancer_id = hcloud_load_balancer.rag.id
  protocol         = "https"
  listen_port      = 443
  destination_port = 80

  http {
    certificates = [hcloud_managed_certificate.rag.id]
  }

  health_check {
    protocol = "http"
    port     = 80
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
  load_balancer_id = hcloud_load_balancer.rag.id
  protocol         = "http"
  listen_port      = 80
  destination_port = 80

  health_check {
    protocol = "http"
    port     = 80
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
# DNS Configuration
# -----------------------------------------------------------------------------

resource "hcloud_zone_rrset" "rag" {
  zone = var.dns_zone
  name = var.dns_subdomain
  type = "A"
  ttl  = 300
  records = [
    { value = hcloud_load_balancer.rag.ipv4 }
  ]
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "load_balancer_ip" {
  description = "Public IPv4 address of the load balancer"
  value       = hcloud_load_balancer.rag.ipv4
}

output "api_endpoint" {
  description = "API endpoint URL"
  value       = "https://${local.domain_name}"
}

output "server_root_passwords" {
  description = "Root passwords for console access"
  value       = { for i, p in random_password.root_password : "${var.server_name}-${i + 1}" => p.result }
  sensitive   = true
}

output "server_private_ips" {
  description = "Private IPs of servers"
  value       = { for i, s in hcloud_server.rag : s.name => "10.2.1.${i + 10}" }
}

output "server_public_ips" {
  description = "Public IPs of servers"
  value       = { for s in hcloud_server.rag : s.name => s.ipv4_address }
}

output "volume_id" {
  description = "Persistent volume ID"
  value       = hcloud_volume.rag_data.id
}

output "deploy_instructions" {
  description = "Deployment instructions"
  value       = <<-EOF

    ============================================
    Dify RAG Service (AWMF Guidelines)
    ============================================

    DNS configured: ${local.domain_name} -> ${hcloud_load_balancer.rag.ipv4}

    1. Check deployment logs:
       - Go to: https://console.hetzner.cloud
       - Open server console
       - Login as root (get password: terraform output -json server_root_passwords)
       - Check: tail -f /var/log/dify-rag-deploy.log

    2. Post-deploy manual steps (one-time via Dify UI):
       a. Log into https://${local.domain_name} with init password
       b. Add Mistral as model provider
       c. Create Knowledge Base "AWMF Leitlinien"
       d. Run bulk PDF upload script
       e. Create Chat App, get API key

    3. Backend environment variables:
       DIFY_RAG_URL=https://${local.domain_name}
       DIFY_RAG_API_KEY=app-YOUR_DIFY_APP_KEY
       USE_DIFY_RAG=true

    4. Health check: https://${local.domain_name}/health

    ============================================
  EOF
}
