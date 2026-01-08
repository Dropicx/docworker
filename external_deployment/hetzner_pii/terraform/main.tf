# =============================================================================
# SpaCy PII Service - Hetzner Terraform Configuration
# =============================================================================
# High-availability PII removal service with:
# - 2x cpx32 servers in private network
# - Load balancer with managed SSL
# - Large SpaCy models (de_core_news_lg + en_core_web_lg)
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
  default     = "pii"
}

variable "server_type" {
  description = "Hetzner server type (cpx32 = 4 vCPU, 8GB RAM)"
  type        = string
  default     = "cpx32"
}

variable "server_count" {
  description = "Number of PII servers"
  type        = number
  default     = 2
}

variable "dns_zone" {
  description = "DNS zone (e.g., fra-la.de)"
  type        = string
}

variable "dns_subdomain" {
  description = "Subdomain for PII service (e.g., pii)"
  type        = string
  default     = "pii"
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
  description = "API key for PII service (optional - auto-generated if not set)"
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
  special = false
}

# -----------------------------------------------------------------------------
# Private Network (separate from PaddleOCR - uses 10.1.0.0/16)
# -----------------------------------------------------------------------------

resource "hcloud_network" "pii" {
  name     = "${var.server_name}-network"
  ip_range = "10.1.0.0/16"
}

resource "hcloud_network_subnet" "pii" {
  network_id   = hcloud_network.pii.id
  type         = "cloud"
  network_zone = var.network_zone
  ip_range     = "10.1.1.0/24"
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

chpasswd:
  list: |
    root:ROOT_PASSWORD_PLACEHOLDER
  expire: false

bootcmd:
  - mkdir -p /opt/pii

write_files:
  - path: /etc/motd
    content: |
      =====================================
      SpaCy PII Service (HA Cluster)
      Server: SERVER_NAME_PLACEHOLDER
      Managed by Terraform

      Service: /opt/pii
      Port: 9125

      Commands:
        systemctl status pii
        journalctl -u pii -f
        cd /opt/pii && docker-compose logs -f
      =====================================
    permissions: '0644'

  # Secrets: API key in .env only (no redundant files)
  - path: /opt/pii/.env
    content: |
      API_SECRET_KEY=${local.api_key}
    permissions: '0600'
    owner: root:root

  # GitHub token for auto-deploy (strict permissions)
  - path: /opt/pii/.github_token
    content: |
      ${var.github_token}
    permissions: '0600'
    owner: root:root

  - path: /opt/pii/.repo
    content: |
      ${var.github_repo}
    permissions: '0644'

  - path: /opt/pii/.branch
    content: |
      ${var.github_branch}
    permissions: '0644'

  - path: /opt/pii/deploy.sh
    encoding: b64
    content: ${filebase64("${path.module}/scripts/deploy.sh")}
    permissions: '0755'

  # Systemd service for auto-restart on reboot
  - path: /etc/systemd/system/pii.service
    content: |
      [Unit]
      Description=SpaCy PII Service
      Requires=docker.service
      After=docker.service

      [Service]
      Type=oneshot
      RemainAfterExit=yes
      WorkingDirectory=/opt/pii
      ExecStart=/usr/bin/docker compose up -d
      ExecStop=/usr/bin/docker compose down
      Restart=on-failure
      RestartSec=10

      [Install]
      WantedBy=multi-user.target
    permissions: '0644'

  # Watchdog script for self-healing
  - path: /opt/pii/watchdog.sh
    content: |
      #!/bin/bash
      # Watchdog: restart service if health check fails
      if ! curl -sf http://localhost:9125/health > /dev/null 2>&1; then
        echo "$(date) Health check failed, restarting..." >> /var/log/pii-watchdog.log
        cd /opt/pii && docker compose restart
      fi
    permissions: '0755'

  # Logrotate for audit logs (90-day retention)
  - path: /etc/logrotate.d/pii-audit
    content: |
      /var/log/pii-audit.log {
        daily
        rotate 90
        compress
        delaycompress
        missingok
        notifempty
        create 640 root root
        dateext
        dateformat -%Y%m%d
      }
    permissions: '0644'

  # Logrotate for deployment logs
  - path: /etc/logrotate.d/pii-deploy
    content: |
      /var/log/pii-deploy.log /var/log/pii-watchdog.log {
        daily
        rotate 7
        compress
        delaycompress
        missingok
        notifempty
        create 640 root root
      }
    permissions: '0644'

  - path: /opt/pii/docker-compose.yml
    content: |
      version: '3.8'

      services:
        pii:
          image: spacy-pii:cpu
          container_name: pii-service
          ports:
            - "9125:9125"
          env_file:
            - .env
          environment:
            - PYTHONUNBUFFERED=1
          volumes:
            - spacy_models:/app/models
            - /var/log:/var/log
          tmpfs:
            - /tmp:size=512M,mode=1777
          restart: unless-stopped
          deploy:
            resources:
              limits:
                memory: 6G
          healthcheck:
            test: ["CMD", "curl", "-f", "http://localhost:9125/health"]
            interval: 30s
            timeout: 10s
            retries: 5
            start_period: 180s
          logging:
            driver: "json-file"
            options:
              max-size: "50m"
              max-file: "5"

      volumes:
        spacy_models:
    permissions: '0644'

runcmd:
  # Docker setup
  - systemctl enable docker
  - systemctl start docker
  # Secure file ownership
  - chown -R root:root /opt/pii
  - chmod 755 /opt/pii/deploy.sh
  - chmod 600 /opt/pii/.env
  - chmod 600 /opt/pii/.github_token
  # NO SWAP - 8GB RAM is sufficient, prevents sensitive text data on disk
  # Fail2ban for security
  - systemctl enable fail2ban
  - systemctl start fail2ban
  # Enable systemd service for auto-restart on reboot
  - systemctl daemon-reload
  - systemctl enable pii.service
  # Watchdog cron - check health every 5 minutes
  - echo '*/5 * * * * /opt/pii/watchdog.sh' | crontab -
  # Auto-cleanup cron - delete audit logs older than 90 days (belt + suspenders with logrotate)
  - (crontab -l 2>/dev/null; echo "0 3 * * * find /var/log -name 'pii-audit*.log*' -mtime +90 -delete") | crontab -
  # Wait for Docker, then deploy and start systemd service
  - |
    until docker info >/dev/null 2>&1; do
      echo "Waiting for Docker..."
      sleep 5
    done
    echo "Docker ready, starting PII service deployment..."
    cd /opt/pii && ./deploy.sh >> /var/log/pii-deploy.log 2>&1
    # Start via systemd after initial deploy
    systemctl start pii.service

final_message: "PII service deployment complete! Service managed by systemd."
EOF
}

# -----------------------------------------------------------------------------
# Servers (Private Network Only)
# -----------------------------------------------------------------------------

resource "hcloud_server" "pii" {
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
    service = "pii"
    managed = "terraform"
    index   = tostring(count.index + 1)
  }

  public_net {
    ipv4_enabled = true
    ipv6_enabled = false
  }

  network {
    network_id = hcloud_network.pii.id
    ip         = "10.1.1.${count.index + 10}"
  }

  depends_on = [hcloud_network_subnet.pii]
}

# -----------------------------------------------------------------------------
# Firewall
# -----------------------------------------------------------------------------

resource "hcloud_firewall" "pii" {
  name = "${var.server_name}-firewall"

  rule {
    description = "Allow private network - all traffic"
    direction   = "in"
    protocol    = "tcp"
    port        = "any"
    source_ips  = ["10.1.0.0/16"]
  }

  rule {
    description = "Allow private network - ICMP"
    direction   = "in"
    protocol    = "icmp"
    source_ips  = ["10.1.0.0/16"]
  }
}

resource "hcloud_firewall_attachment" "pii" {
  firewall_id = hcloud_firewall.pii.id
  server_ids  = [for s in hcloud_server.pii : s.id]
}

# -----------------------------------------------------------------------------
# Load Balancer
# -----------------------------------------------------------------------------

resource "hcloud_load_balancer" "pii" {
  name               = "${var.server_name}-lb"
  load_balancer_type = "lb11"
  location           = var.location

  labels = {
    service = "pii"
    managed = "terraform"
  }
}

resource "hcloud_load_balancer_network" "pii" {
  load_balancer_id = hcloud_load_balancer.pii.id
  network_id       = hcloud_network.pii.id
  ip               = "10.1.1.2"

  depends_on = [hcloud_network_subnet.pii]
}

resource "hcloud_load_balancer_target" "pii" {
  count            = var.server_count
  type             = "server"
  load_balancer_id = hcloud_load_balancer.pii.id
  server_id        = hcloud_server.pii[count.index].id
  use_private_ip   = true

  depends_on = [hcloud_load_balancer_network.pii]
}

# Managed SSL Certificate
# IMPORTANT: prevent_destroy avoids Let's Encrypt rate limits (5 certs/domain/week)
resource "hcloud_managed_certificate" "pii" {
  name         = "${var.server_name}-cert"
  domain_names = [local.domain_name]

  labels = {
    service = "pii"
    managed = "terraform"
  }

  lifecycle {
    prevent_destroy = true
  }
}

# HTTPS Service
resource "hcloud_load_balancer_service" "https" {
  load_balancer_id = hcloud_load_balancer.pii.id
  protocol         = "https"
  listen_port      = 443
  destination_port = 9125

  http {
    certificates = [hcloud_managed_certificate.pii.id]
  }

  health_check {
    protocol = "http"
    port     = 9125
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
  load_balancer_id = hcloud_load_balancer.pii.id
  protocol         = "http"
  listen_port      = 80
  destination_port = 9125

  health_check {
    protocol = "http"
    port     = 9125
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

resource "hcloud_zone_rrset" "pii" {
  zone = var.dns_zone
  name = var.dns_subdomain
  type = "A"
  ttl  = 300
  records = [
    { value = hcloud_load_balancer.pii.ipv4 }
  ]
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "load_balancer_ip" {
  description = "Public IPv4 address of the load balancer"
  value       = hcloud_load_balancer.pii.ipv4
}

output "api_endpoint" {
  description = "API endpoint URL"
  value       = "https://${local.domain_name}"
}

output "api_key" {
  description = "API key for PII service"
  value       = local.api_key
  sensitive   = true
}

output "server_root_passwords" {
  description = "Root passwords for console access"
  value       = { for i, p in random_password.root_password : "${var.server_name}-${i + 1}" => p.result }
  sensitive   = true
}

output "server_private_ips" {
  description = "Private IPs of servers"
  value       = { for i, s in hcloud_server.pii : s.name => "10.1.1.${i + 10}" }
}

output "server_public_ips" {
  description = "Public IPs of servers"
  value       = { for s in hcloud_server.pii : s.name => s.ipv4_address }
}

output "deploy_instructions" {
  description = "Deployment instructions"
  value       = <<-EOF

    ============================================
    SpaCy PII Service HA Cluster Deployment
    ============================================

    DNS configured: ${local.domain_name} → ${hcloud_load_balancer.pii.ipv4}

    1. Check deployment logs on each server:
       - Go to: https://console.hetzner.cloud
       - Open each server's console
       - Login as root (get password: terraform output -json server_root_passwords)
       - Check: tail -f /var/log/pii-deploy.log

    2. Backend environment variables:
       EXTERNAL_PII_URL=https://${local.domain_name}
       EXTERNAL_PII_API_KEY=<run: terraform output -raw api_key>
       USE_EXTERNAL_PII=true

    3. Health check: https://${local.domain_name}/health

    ============================================
  EOF
}
