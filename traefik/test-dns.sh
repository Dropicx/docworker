#!/bin/bash

echo "==================================="
echo "🔍 DNS und Netcup API Test"
echo "==================================="
echo ""

# Test DNS-Auflösung vom Host
echo "1️⃣ Testing DNS from host system:"
echo -n "   Resolving fra-la.de: "
dig +short fra-la.de @1.1.1.1 || echo "FAILED"
echo ""

# Test DNS-Auflösung aus Docker Container
echo "2️⃣ Testing DNS from Docker container:"
docker run --rm alpine:latest sh -c "apk add --no-cache bind-tools >/dev/null 2>&1 && dig +short fra-la.de @1.1.1.1" || echo "FAILED"
echo ""

# Test mit Netcup DNS
echo "3️⃣ Testing with Netcup nameservers:"
echo -n "   NS records for fra-la.de: "
dig +short NS fra-la.de
echo ""

# Test ob Port 53 erreichbar ist
echo "4️⃣ Testing if DNS ports are accessible:"
nc -zv 1.1.1.1 53 2>&1 | grep -q succeeded && echo "   ✅ 1.1.1.1:53 is reachable" || echo "   ❌ 1.1.1.1:53 is NOT reachable"
nc -zv 8.8.8.8 53 2>&1 | grep -q succeeded && echo "   ✅ 8.8.8.8:53 is reachable" || echo "   ❌ 8.8.8.8:53 is NOT reachable"
echo ""

# Firewall Status prüfen
echo "5️⃣ Checking firewall status:"
if command -v ufw >/dev/null 2>&1; then
    sudo ufw status | grep -E "(53|80|443)" || echo "   No specific rules for DNS/HTTP/HTTPS"
else
    echo "   UFW not installed"
fi

if command -v iptables >/dev/null 2>&1; then
    echo ""
    echo "   Checking iptables for DNS blocks:"
    sudo iptables -L -n | grep -E "53" | head -5 || echo "   No DNS-specific iptables rules found"
fi
echo ""

# Docker Network Info
echo "6️⃣ Docker network configuration:"
docker network inspect traefik-proxy | grep -A 5 "IPAM"
echo ""

echo "==================================="
echo "📝 Recommendations:"
echo "==================================="
echo ""
echo "If DNS resolution fails from Docker:"
echo "1. Check if your server provider blocks outgoing DNS (port 53)"
echo "2. Try using HTTP challenge instead of DNS challenge"
echo "3. Check Docker daemon DNS settings in /etc/docker/daemon.json"
echo ""
echo "Alternative: Use HTTP Challenge instead of DNS Challenge"
echo "This requires port 80 to be accessible from the internet"