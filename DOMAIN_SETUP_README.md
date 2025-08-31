# 🌐 ai.sanaa.co Domain Setup Guide

This guide will help you set up the `ai.sanaa.co` domain for your Sanaa AI Development Assistant with Nginx reverse proxy and SSL certificates.

## 📋 Prerequisites

- Ubuntu/Debian server with root/sudo access
- Domain name `ai.sanaa.co` pointed to your server's IP
- Sanaa application running on port 9999
- Basic knowledge of Linux command line

## 🚀 Quick Setup

### 1. DNS Configuration

First, ensure your domain points to your server:

```bash
# Check your server's public IP
curl -s ifconfig.me

# Configure DNS records:
# A record: ai.sanaa.co -> YOUR_SERVER_IP
# CNAME record: www.ai.sanaa.co -> ai.sanaa.co
```

### 2. Run Automated Setup

```bash
# Navigate to your Sanaa directory
cd /opt/coding-swarm

# Make scripts executable
chmod +x setup_domain.sh test_domain.sh

# Run the automated setup
sudo ./setup_domain.sh
```

The setup script will:
- ✅ Install Nginx and Certbot
- ✅ Configure Nginx as reverse proxy
- ✅ Obtain SSL certificates from Let's Encrypt
- ✅ Set up automatic certificate renewal
- ✅ Create systemd service for Sanaa
- ✅ Configure security headers and rate limiting

### 3. Test the Setup

```bash
# Run the test script
./test_domain.sh
```

## 🔧 Manual Configuration

If you prefer manual setup, follow these steps:

### Install Required Packages

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
```

### Configure Nginx

```bash
# Copy the configuration
sudo cp nginx.conf /etc/nginx/sites-available/ai.sanaa.co

# Enable the site
sudo ln -s /etc/nginx/sites-available/ai.sanaa.co /etc/nginx/sites-enabled/

# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### SSL Certificate Setup

```bash
# Obtain SSL certificate
sudo certbot --nginx -d ai.sanaa.co -d www.ai.sanaa.co

# Set up auto-renewal
sudo crontab -l | { cat; echo "0 12 * * * /usr/bin/certbot renew --quiet"; } | sudo crontab -
```

### Create Systemd Service

```bash
# Create service file
sudo tee /etc/systemd/system/sanaa.service > /dev/null <<EOF
[Unit]
Description=Sanaa AI Development Assistant
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/opt/coding-swarm
Environment=PATH=/opt/coding-swarm/sanaa_env/bin
ExecStart=/opt/coding-swarm/sanaa_env/bin/python3 -c "import uvicorn; uvicorn.run('web.app:app', host='127.0.0.1', port=9999, reload=False)"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable sanaa
sudo systemctl start sanaa
```

## 🔍 Configuration Details

### Nginx Features

- **Reverse Proxy**: Forwards requests to Sanaa on port 9999
- **SSL/TLS**: Full HTTPS with Let's Encrypt certificates
- **Rate Limiting**: Protects against abuse
- **Caching**: Static file caching for performance
- **Security Headers**: XSS protection, CSP, etc.
- **WebSocket Support**: For real-time features
- **Gzip Compression**: Optimized content delivery

### Security Features

- HTTP to HTTPS redirect
- SSL certificate with auto-renewal
- Rate limiting on API endpoints
- Security headers (CSP, XSS protection, etc.)
- Blocked access to sensitive files
- DDoS protection measures

### Performance Optimizations

- Static file caching (1 year)
- API response caching
- Gzip compression
- Connection keep-alive
- Optimized buffer sizes

## 🧪 Testing

### Automated Testing

```bash
# Run comprehensive test
./test_domain.sh
```

### Manual Testing

```bash
# Test HTTP redirect
curl -I http://ai.sanaa.co

# Test HTTPS access
curl -I https://ai.sanaa.co

# Test health endpoint
curl https://ai.sanaa.co/health

# Test SSL certificate
openssl s_client -connect ai.sanaa.co:443 -servername ai.sanaa.co < /dev/null
```

## 📊 Monitoring

### Check Service Status

```bash
# Sanaa service
sudo systemctl status sanaa

# Nginx service
sudo systemctl status nginx

# SSL certificates
sudo certbot certificates
```

### View Logs

```bash
# Nginx access logs
sudo tail -f /var/log/nginx/sanaa_access.log

# Nginx error logs
sudo tail -f /var/log/nginx/sanaa_error.log

# Sanaa application logs
sudo journalctl -u sanaa -f
```

## 🔧 Troubleshooting

### Common Issues

#### DNS Not Resolving
```bash
# Check DNS
nslookup ai.sanaa.co

# Check if domain points to correct IP
dig ai.sanaa.co
```

#### SSL Certificate Issues
```bash
# Renew certificate manually
sudo certbot renew

# Check certificate status
sudo certbot certificates

# Reconfigure SSL
sudo certbot --nginx -d ai.sanaa.co
```

#### Nginx Configuration Errors
```bash
# Test configuration
sudo nginx -t

# Check syntax
sudo nginx -c /etc/nginx/nginx.conf

# Reload configuration
sudo systemctl reload nginx
```

#### Application Not Accessible
```bash
# Check if Sanaa is running
sudo systemctl status sanaa

# Check application logs
sudo journalctl -u sanaa -n 50

# Test local access
curl http://127.0.0.1:9999/health
```

### Performance Issues

```bash
# Clear Nginx cache
sudo rm -rf /var/cache/nginx/*

# Restart services
sudo systemctl restart sanaa
sudo systemctl restart nginx

# Check system resources
htop
df -h
```

## 🔄 Maintenance

### Certificate Renewal

Certificates auto-renew monthly, but you can manually renew:

```bash
sudo certbot renew
```

### Updates

```bash
# Update Sanaa
cd /opt/coding-swarm
git pull
sudo systemctl restart sanaa

# Update Nginx configuration
sudo cp nginx.conf /etc/nginx/sites-available/ai.sanaa.co
sudo nginx -t && sudo systemctl reload nginx
```

### Backup

```bash
# Backup configuration
sudo cp /etc/nginx/sites-available/ai.sanaa.co /etc/nginx/sites-available/ai.sanaa.co.backup

# Backup SSL certificates
sudo tar -czf /opt/ssl_backup.tar.gz /etc/letsencrypt/
```

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Run the test script: `./test_domain.sh`
3. Check logs for error messages
4. Verify DNS configuration
5. Ensure firewall allows ports 80 and 443

## 🎯 Success Metrics

After successful setup, you should have:

- ✅ HTTPS access to https://ai.sanaa.co
- ✅ Automatic SSL certificate renewal
- ✅ Fast loading times with caching
- ✅ Secure headers and rate limiting
- ✅ Real-time WebSocket support
- ✅ Automatic failover and restart

## 🚀 Next Steps

Once your domain is set up:

1. **Test thoroughly** with different browsers and devices
2. **Monitor performance** using the built-in metrics
3. **Set up monitoring** alerts for downtime
4. **Configure backups** for your application data
5. **Scale as needed** by adjusting Nginx configuration

Your Sanaa AI application is now professionally hosted and ready for production use! 🎉