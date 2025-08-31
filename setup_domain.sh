#!/bin/bash

# Sanaa AI Domain Setup Script
# Sets up ai.sanaa.co domain with Nginx reverse proxy and SSL

set -e

DOMAIN="ai.sanaa.co"
EMAIL="admin@sanaa.co"
SANAA_PORT=9999
NGINX_CONF="/opt/coding-swarm/nginx.conf"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Sanaa AI Domain Setup for ${DOMAIN}${NC}"
echo "========================================"

# Function to print status messages
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root. Please run as a regular user with sudo access."
   exit 1
fi

# Check if domain is accessible
echo "Checking domain accessibility..."
if ! nslookup $DOMAIN >/dev/null 2>&1; then
    print_warning "Domain $DOMAIN is not resolving. Please ensure DNS is configured:"
    echo "  1. Point $DOMAIN to this server's IP address"
    echo "  2. Add A record: $DOMAIN -> $(curl -s ifconfig.me)"
    echo "  3. Add CNAME record: www.$DOMAIN -> $DOMAIN"
    echo ""
    read -p "Press Enter to continue once DNS is configured..."
fi

# Install required packages
echo "Installing required packages..."
sudo apt update
sudo apt install -y certbot python3-certbot-nginx nginx

# Backup existing nginx configuration
if [ -f /etc/nginx/sites-enabled/default ]; then
    sudo cp /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/default.backup
    print_status "Backed up existing Nginx configuration"
fi

# Copy our nginx configuration
sudo cp $NGINX_CONF /etc/nginx/sites-available/$DOMAIN
sudo ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/

# Remove default nginx site
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
echo "Testing Nginx configuration..."
if sudo nginx -t; then
    print_status "Nginx configuration is valid"
else
    print_error "Nginx configuration has errors. Please check the configuration."
    exit 1
fi

# Create cache directories
echo "Creating cache directories..."
sudo mkdir -p /var/cache/nginx/health
sudo mkdir -p /var/cache/nginx/api
sudo mkdir -p /var/cache/nginx/static
sudo chown -R www-data:www-data /var/cache/nginx

# Create log directories
sudo mkdir -p /var/log/nginx
sudo touch /var/log/nginx/sanaa_access.log
sudo touch /var/log/nginx/sanaa_error.log
sudo chown -R www-data:www-data /var/log/nginx

# Start nginx
echo "Starting Nginx..."
sudo systemctl enable nginx
sudo systemctl start nginx

# Wait for nginx to start
sleep 2

# Test HTTP access
echo "Testing HTTP access..."
if curl -s -o /dev/null -w "%{http_code}" http://$DOMAIN/health | grep -q "200"; then
    print_status "HTTP access to $DOMAIN is working"
else
    print_warning "HTTP access to $DOMAIN may not be working yet"
fi

# Obtain SSL certificate
echo "Obtaining SSL certificate for $DOMAIN..."
sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --email $EMAIL --agree-tos --non-interactive

# Verify SSL certificate
echo "Verifying SSL certificate..."
if sudo certbot certificates | grep -q "$DOMAIN"; then
    print_status "SSL certificate obtained successfully"
else
    print_error "Failed to obtain SSL certificate"
    exit 1
fi

# Reload nginx with SSL
echo "Reloading Nginx with SSL configuration..."
sudo systemctl reload nginx

# Test HTTPS access
echo "Testing HTTPS access..."
if curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN/health | grep -q "200"; then
    print_status "HTTPS access to $DOMAIN is working"
else
    print_error "HTTPS access to $DOMAIN is not working"
fi

# Set up automatic certificate renewal
echo "Setting up automatic certificate renewal..."
sudo crontab -l | { cat; echo "0 12 * * * /usr/bin/certbot renew --quiet"; } | sudo crontab -

# Create systemd service for Sanaa (if not exists)
if [ ! -f /etc/systemd/system/sanaa.service ]; then
    echo "Creating Sanaa systemd service..."
    sudo tee /etc/systemd/system/sanaa.service > /dev/null <<EOF
[Unit]
Description=Sanaa AI Development Assistant
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/coding-swarm
Environment=PATH=/opt/coding-swarm/sanaa_env/bin
ExecStart=/opt/coding-swarm/sanaa_env/bin/python3 -c "import uvicorn; uvicorn.run('web.app:app', host='127.0.0.1', port=$SANAA_PORT, reload=False)"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable sanaa
    print_status "Created Sanaa systemd service"
fi

# Start Sanaa service
echo "Starting Sanaa service..."
sudo systemctl start sanaa

# Wait for service to start
sleep 5

# Test full application
echo "Testing full application..."
if curl -s -k https://$DOMAIN | grep -q "Sanaa"; then
    print_status "Sanaa application is accessible at https://$DOMAIN"
else
    print_warning "Sanaa application may not be fully accessible yet"
fi

# Print success message
echo ""
echo -e "${GREEN}🎉 Domain setup completed successfully!${NC}"
echo ""
echo "Your Sanaa AI application is now available at:"
echo "  🌐 https://$DOMAIN"
echo "  🔒 SSL Certificate: Let's Encrypt"
echo "  ⚡ Reverse Proxy: Nginx"
echo ""
echo "Next steps:"
echo "1. Update your DNS records if not done already"
echo "2. Test the application thoroughly"
echo "3. Monitor logs: sudo tail -f /var/log/nginx/sanaa_access.log"
echo "4. Check service status: sudo systemctl status sanaa"
echo ""
echo "SSL certificates will auto-renew monthly via cron job."
echo "To manually renew: sudo certbot renew"
echo ""
echo -e "${BLUE}🚀 Happy coding with Sanaa AI!${NC}"