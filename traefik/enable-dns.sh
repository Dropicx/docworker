#!/bin/bash

echo "🔧 Enabling outgoing DNS for Docker containers..."

# Allow outgoing DNS
echo "Adding UFW rules for DNS..."
sudo ufw allow out 53/udp comment 'Allow DNS UDP'
sudo ufw allow out 53/tcp comment 'Allow DNS TCP'

# Reload UFW
sudo ufw reload

echo "✅ DNS rules added"
echo ""
echo "Current UFW status:"
sudo ufw status numbered | grep 53

echo ""
echo "Testing DNS again..."
dig +short fra-la.de @127.0.0.53