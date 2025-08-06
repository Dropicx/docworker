#!/bin/bash

echo "🔧 Fixing DNS configuration for Netcup servers..."

# Netcup DNS Server
NETCUP_DNS1="193.148.166.4"
NETCUP_DNS2="46.38.225.230"
NETCUP_DNS3="46.38.252.230"

# Test Netcup DNS servers
echo "Testing Netcup DNS servers..."
echo -n "Testing $NETCUP_DNS1: "
dig +short fra-la.de @$NETCUP_DNS1 +timeout=2 && echo "✅ Works!" || echo "❌ Failed"
echo -n "Testing $NETCUP_DNS2: "
dig +short fra-la.de @$NETCUP_DNS2 +timeout=2 && echo "✅ Works!" || echo "❌ Failed"
echo -n "Testing $NETCUP_DNS3: "
dig +short fra-la.de @$NETCUP_DNS3 +timeout=2 && echo "✅ Works!" || echo "❌ Failed"

# Test local DNS server
echo ""
echo "Testing local DNS resolver..."
echo -n "Testing 127.0.0.53: "
dig +short fra-la.de @127.0.0.53 +timeout=2 && echo "✅ Works!" || echo "❌ Failed"

# Get current nameserver from resolv.conf
echo ""
echo "Current system DNS configuration:"
cat /etc/resolv.conf | grep nameserver

echo ""
echo "Recommended: Use local resolver or Netcup DNS servers"