#!/bin/bash

# Test script for ai.sanaa.co domain setup
# Verifies that the domain is properly configured and accessible

DOMAIN="ai.sanaa.co"
SANAA_PORT=9999

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔍 Testing ai.sanaa.co Domain Setup${NC}"
echo "====================================="

# Function to test endpoint
test_endpoint() {
    local url=$1
    local expected_code=$2
    local description=$3

    echo -n "Testing $description... "
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)

    if [ "$response" = "$expected_code" ]; then
        echo -e "${GREEN}✓ PASS${NC}"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected: $expected_code, Got: $response)"
        return 1
    fi
}

# Test DNS resolution
echo "Testing DNS resolution..."
if nslookup $DOMAIN >/dev/null 2>&1; then
    echo -e "${GREEN}✓ DNS resolution working${NC}"
else
    echo -e "${RED}✗ DNS resolution failed${NC}"
    echo "Please ensure DNS is configured:"
    echo "  A record: $DOMAIN -> $(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_SERVER_IP')"
fi

echo ""

# Test HTTP redirect
test_endpoint "http://$DOMAIN" "301" "HTTP to HTTPS redirect"

# Test HTTPS access
test_endpoint "https://$DOMAIN" "200" "HTTPS main page"

# Test health endpoint
test_endpoint "https://$DOMAIN/health" "200" "Health check endpoint"

# Test API endpoint
test_endpoint "https://$DOMAIN/api/status" "200" "API status endpoint"

echo ""

# Test SSL certificate
echo "Testing SSL certificate..."
ssl_info=$(openssl s_client -connect $DOMAIN:443 -servername $DOMAIN < /dev/null 2>/dev/null | openssl x509 -noout -dates 2>/dev/null)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ SSL certificate valid${NC}"
    echo "$ssl_info" | grep -E "(notBefore|notAfter)" | sed 's/^/  /'
else
    echo -e "${RED}✗ SSL certificate issue${NC}"
fi

echo ""

# Test local Sanaa service
echo "Testing local Sanaa service..."
if curl -s http://127.0.0.1:$SANAA_PORT/health >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Local Sanaa service running${NC}"
else
    echo -e "${RED}✗ Local Sanaa service not accessible${NC}"
    echo "Check if Sanaa is running: sudo systemctl status sanaa"
fi

echo ""

# Test Nginx configuration
echo "Testing Nginx configuration..."
if sudo nginx -t 2>/dev/null; then
    echo -e "${GREEN}✓ Nginx configuration valid${NC}"
else
    echo -e "${RED}✗ Nginx configuration invalid${NC}"
fi

echo ""

# Performance test
echo "Running performance test..."
echo "Response time for main page:"
time curl -s -o /dev/null -w "%{time_total}s\n" https://$DOMAIN

echo ""
echo -e "${BLUE}📊 Domain test completed!${NC}"
echo ""
echo "If all tests passed, your domain is properly configured."
echo "If any tests failed, check the troubleshooting section in the README."