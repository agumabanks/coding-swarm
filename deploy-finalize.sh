#!/bin/bash
# Deploy Finalize Script - Part 1 (Setup & Configuration)
# Complete deployment finalization with verification and optimization
set -euo pipefail

# ============================================
# CONFIGURATION AND CONSTANTS
# ============================================
readonly SCRIPT_VERSION="1.0.0"
readonly SCRIPT_NAME="deploy-finalize"

# Environment variables
DOMAIN="${DOMAIN:-}"
PUBLIC_IP="${PUBLIC_IP:-$(curl -s ifconfig.me || echo '127.0.0.1')}"
OPENAI_API_KEY="${OPENAI_API_KEY:-}"
PRODUCTION_MODE="${PRODUCTION_MODE:-true}"
SKIP_OPTIMIZATION="${SKIP_OPTIMIZATION:-false}"
ENABLE_SSL="${ENABLE_SSL:-auto}"

# Paths
readonly INSTALL_DIR="/opt/coding-swarm"
readonly CONFIG_DIR="/etc/coding-swarm"
readonly LOG_DIR="/var/log/coding-swarm"
readonly PROJECT_DIR="/home/swarm/projects"
readonly BACKUP_DIR="/opt/backups/coding-swarm"
readonly FINALIZE_LOG="$LOG_DIR/finalization.log"

# Colors and formatting
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

# Progress tracking
declare -g TOTAL_FINALIZE_STEPS=15
declare -g CURRENT_FINALIZE_STEP=0
declare -g FINALIZE_START_TIME
declare -A FINALIZE_STATUS=()

# ============================================
# HELPER FUNCTIONS
# ============================================
check_dependencies() {
    local dependencies=("curl" "jq" "nginx" "redis-cli" "docker" "ufw" "bc" "systemctl" "ping" "certbot" "openssl" "sshd" "auditd" "fail2ban-client" "sqlite3" "netstat" "fuser" "htop" "top" "free" "df" "uptime" "ps" "grep" "awk" "sed" "bc" "tar" "md5sum" "find" "stat" "rsync" "aws" "journalctl" "docker stats" "vmstat" "nslookup" "ss")
    for dep in "${dependencies[@]}"; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            log_error "Missing dependency: $dep. Please install it."
            return 1
        fi
    done
    log_success "All dependencies verified"
}

ensure_directory() {
    local dir="$1"
    local owner="${2:-swarm:swarm}"
    local perms="${3:-755}"
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir" || { log_error "Failed to create directory: $dir"; return 1; }
    fi
    chown "$owner" "$dir" || { log_error "Failed to set ownership for $dir"; return 1; }
    chmod "$perms" "$dir" || { log_error "Failed to set permissions for $dir"; return 1; }
    log_info "Directory ensured: $dir"
}

backup_config() {
    local file="$1"
    if [[ -f "$file" ]]; then
        cp "$file" "${file}.$(date +%Y%m%d_%H%M%S).backup" || { log_error "Failed to backup $file"; return 1; }
        log_info "Backed up $file"
    fi
}

set_secure_permissions() {
    local paths=(
        "$CONFIG_DIR/secrets:700:swarm:swarm"
        "$CONFIG_DIR:755:swarm:swarm"
        "$LOG_DIR:750:swarm:swarm"
        "$BACKUP_DIR:700:swarm:swarm"
        "$PROJECT_DIR:755:swarm:swarm"
        "$INSTALL_DIR:755:swarm:swarm"
    )
    for path_info in "${paths[@]}"; do
        local path=$(echo "$path_info" | cut -d: -f1)
        local perms=$(echo "$path_info" | cut -d: -f2)
        local owner=$(echo "$path_info" | cut -d: -f3)
        if [[ -e "$path" ]]; then
            chmod "$perms" "$path" || log_error "Failed to set permissions for $path"
            chown "$owner" "$path" || log_error "Failed to set ownership for $path"
        fi
    done
    chmod 600 "$CONFIG_DIR/secrets"/* 2>/dev/null || true
    chmod 640 "$LOG_DIR"/*.log 2>/dev/null || true
    chown swarm:swarm "$LOG_DIR"/*.log 2>/dev/null || true
    chmod 755 "$INSTALL_DIR/scripts"/* 2>/dev/null || true
    log_success "Secure permissions set"
}

validate_domain() {
    if [[ -n "$DOMAIN" ]] && ! echo "$DOMAIN" | grep -E '^[a-zA-Z0-9.-]+$' >/dev/null; then
        log_error "Invalid domain format: $DOMAIN"
        return 1
    fi
    if [[ -n "$DOMAIN" ]]; then
        if ! ping -c 1 "$DOMAIN" >/dev/null 2>&1; then
            log_warning "Domain $DOMAIN is not resolvable, but proceeding"
        fi
    fi
    return 0
}

cleanup_temp_files() {
    rm -f /tmp/router_test.json /tmp/service_metrics_*.json /tmp/app_metrics_*.json /tmp/restore-*
    log_info "Cleaned up temporary files"
}

# ============================================
# LOGGING AND PROGRESS FUNCTIONS
# ============================================
setup_finalize_logging() {
    ensure_directory "$(dirname "$FINALIZE_LOG")"
    exec 1> >(tee -a "$FINALIZE_LOG")
    exec 2> >(tee -a "$FINALIZE_LOG" >&2)
    
    echo "=== DEPLOYMENT FINALIZATION STARTED ===" >> "$FINALIZE_LOG"
    echo "Timestamp: $(date -Iseconds)" >> "$FINALIZE_LOG"
    echo "Script Version: $SCRIPT_VERSION" >> "$FINALIZE_LOG"
    echo "Domain: ${DOMAIN:-$PUBLIC_IP}" >> "$FINALIZE_LOG"
    echo "Production Mode: $PRODUCTION_MODE" >> "$FINALIZE_LOG"
}

log_finalize() {
    local level="$1"
    local color="$2"
    local message="$3"
    local timestamp=$(date -Iseconds)
    message=$(echo "$message" | sed 's/\(Bearer \)[^ ]*/\1[REDACTED]/g; s/\(Key: \)[^ ]*/\1[REDACTED]/g')
    echo -e "${color}[$level]${NC} ${BOLD}[$timestamp]${NC} $message"
}

log_info() { log_finalize "INFO" "$BLUE" "$1"; }
log_success() { log_finalize "SUCCESS" "$GREEN" "✓ $1"; }
log_warning() { log_finalize "WARNING" "$YELLOW" "⚠ $1"; }
log_error() { log_finalize "ERROR" "$RED" "✗ $1"; }
log_critical() { log_finalize "CRITICAL" "$RED" "💥 $1"; }

progress_finalize() {
    local current=$1
    local total=$2
    local step_name="$3"
    local width=50
    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))
    
    printf "\r${CYAN}Finalizing:${NC} ["
    printf "%*s" $filled | tr ' ' '█'
    printf "%*s" $empty | tr ' ' '░'
    printf "] %d%% - %s" $percentage "$step_name"
    
    if [[ $current -eq $total ]]; then
        echo
    fi
}

update_finalize_progress() {
    local step_name="$1"
    local status="${2:-RUNNING}"
    
    CURRENT_FINALIZE_STEP=$((CURRENT_FINALIZE_STEP + 1))
    FINALIZE_STATUS["$step_name"]="$status"
    
    progress_finalize $CURRENT_FINALIZE_STEP $TOTAL_FINALIZE_STEPS "$step_name"
    
    if [[ "$status" == "COMPLETED" ]]; then
        log_success "Step $CURRENT_FINALIZE_STEP/$TOTAL_FINALIZE_STEPS: $step_name"
    elif [[ "$status" == "FAILED" ]]; then
        log_error "Step $CURRENT_FINALIZE_STEP/$TOTAL_FINALIZE_STEPS: $step_name FAILED"
    else
        log_info "Step $CURRENT_FINALIZE_STEP/$TOTAL_FINALIZE_STEPS: $step_name..."
    fi
}

# ============================================
# VALIDATION AND PREREQUISITES
# ============================================
validate_deployment_state() {
    log_info "Validating current deployment state..."
    
    local required_services=(
        "swarm-router"
        "swarm-orchestrator"
        "swarm-agent-laravel"
        "swarm-agent-react"
        "swarm-agent-flutter"
        "swarm-agent-testing"
    )
    
    local missing_services=()
    
    for service in "${required_services[@]}"; do
        if ! systemctl is-enabled "$service" >/dev/null 2>&1; then
            missing_services+=("$service (not enabled)")
        elif ! systemctl is-active "$service" >/dev/null 2>&1; then
            missing_services+=("$service (inactive)")
        fi
    done
    
    if [[ ${#missing_services[@]} -gt 0 ]]; then
        log_error "Missing required services: ${missing_services[*]}"
        return 1
    fi
    
    # Check if API keys exist
    if [[ ! -f "$CONFIG_DIR/secrets/router.key" ]] || [[ ! -f "$CONFIG_DIR/secrets/localmodel.key" ]]; then
        log_error "Missing API keys in $CONFIG_DIR/secrets/"
        return 1
    fi
    
    # Check if AI model exists (flexible)
    if [[ -z $(find "$INSTALL_DIR/models" -name "*.gguf" 2>/dev/null) ]]; then
        log_error "No AI model files found in $INSTALL_DIR/models/"
        return 1
    fi
    
    log_success "Deployment state validation passed"
    return 0
}

check_system_resources() {
    log_info "Checking system resources for optimization..."
    
    # CPU information
    local cpu_cores
    cpu_cores=$(nproc)
    log_info "CPU cores available: $cpu_cores"
    
    # Memory information
    local memory_total memory_available
    memory_total=$(free -h | awk 'NR==2{print $2}')
    memory_available=$(free -h | awk 'NR==2{print $7}')
    log_info "Memory: $memory_available available of $memory_total total"
    
    # Disk space information
    local disk_usage disk_available
    disk_usage=$(df -h / | awk 'NR==2{print $5}')
    disk_available=$(df -h / | awk 'NR==2{print $4}')
    log_info "Disk: $disk_available available (usage: $disk_usage)"
    
    # Network connectivity check
    if ! ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        log_warning "External network connectivity issues detected"
    else
        log_success "Network connectivity verified"
    fi
    
    return 0
}

# ============================================
# SSL CERTIFICATE SETUP
# ============================================
setup_ssl_certificates() {
    if [[ "$ENABLE_SSL" == "false" ]] || [[ -z "$DOMAIN" ]]; then
        log_info "SSL setup skipped (no domain or SSL disabled)"
        return 0
    fi
    
    if ! validate_domain; then
        return 1
    fi
    
    log_info "Setting up SSL certificates for domain: $DOMAIN"
    
    # Install Certbot if not present
    if ! command -v certbot >/dev/null 2>&1; then
        log_info "Installing Certbot..."
        apt-get update -qq
        apt-get install -y -qq certbot python3-certbot-nginx
    fi
    
    # Check if certificate already exists
    if [[ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]]; then
        log_success "SSL certificate already exists for $DOMAIN"
        return 0
    fi
    
    # Create SSL certificate with retry
    log_info "Requesting SSL certificate from Let's Encrypt..."
    
    if certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "admin@$DOMAIN" --redirect; then
        log_success "SSL certificate successfully created for $DOMAIN"
    else
        log_warning "SSL certificate creation failed, retrying once..."
        sleep 5
        if certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "admin@$DOMAIN" --redirect; then
            log_success "SSL certificate created on retry"
        else
            log_warning "SSL certificate creation failed, continuing without SSL"
            return 1
        fi
    fi
    
    # Setup automatic renewal
    if ! crontab -l 2>/dev/null | grep -q "certbot renew"; then
        (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
        log_success "SSL certificate auto-renewal configured"
    fi
    
    return 0
}

# ============================================
# NGINX OPTIMIZATION
# ============================================
optimize_nginx_configuration() {
    log_info "Optimizing Nginx configuration for production..."
    
    backup_config "/etc/nginx/sites-available/coding-swarm"
    
    # Create optimized Nginx configuration
    cat > /etc/nginx/sites-available/coding-swarm << EOF
# Optimized Nginx Configuration for Coding Swarm
# Generated by deploy-finalize.sh v$SCRIPT_VERSION

# Rate limiting with burst handling
limit_req_zone \$binary_remote_addr zone=api_limit:10m rate=100r/m;
limit_req_zone \$binary_remote_addr zone=orchestrator_limit:10m rate=20r/m;
limit_req_zone \$binary_remote_addr zone=health_limit:10m rate=200r/m;
limit_req_zone \$binary_remote_addr zone=login_limit:10m rate=5r/m;

# Connection limiting
limit_conn_zone \$binary_remote_addr zone=conn_limit_per_ip:10m;

# Upstream definitions with load balancing and health checks
upstream router_backend {
    least_conn;
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s weight=1;
    keepalive 32;
    keepalive_requests 100;
}

upstream orchestrator_backend {
    least_conn;
    server 127.0.0.1:9000 max_fails=3 fail_timeout=30s weight=1;
    keepalive 16;
    keepalive_requests 50;
}

# Main server block
server {
EOF

    # Add SSL or HTTP configuration based on setup
    if [[ "$ENABLE_SSL" != "false" ]] && [[ -n "$DOMAIN" ]] && [[ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]]; then
        cat >> /etc/nginx/sites-available/coding-swarm << EOF
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAIN;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/$DOMAIN/chain.pem;
    
    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    ssl_stapling on;
    ssl_stapling_verify on;
    
    # HSTS (Optional - uncomment for production)
    # add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
EOF
    else
        cat >> /etc/nginx/sites-available/coding-swarm << EOF
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN:-_};
EOF
    fi
    
    # Continue with common configuration
    cat >> /etc/nginx/sites-available/coding-swarm << 'EOF'
    
    # Security headers
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=(), speaker=(), notifications=(), push=(), vibrate=()" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https:; frame-ancestors 'none';" always;
    
    # Hide server information
    server_tokens off;
    more_clear_headers Server;
    
    # Connection limits
    limit_conn conn_limit_per_ip 20;
    
    # Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        application/rdf+xml
        image/svg+xml;
    
    # Brotli compression (if module available)
    brotli on;
    brotli_comp_level 6;
    brotli_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml;
    
    # Client settings
    client_max_body_size 50M;
    client_body_timeout 60s;
    client_header_timeout 60s;
    client_body_buffer_size 128k;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 4k;
    
    # Logging with detailed format
    log_format detailed '$remote_addr - $remote_user [$time_local] '
                       '"$request" $status $body_bytes_sent '
                       '"$http_referer" "$http_user_agent" '
                       'rt=$request_time uct="$upstream_connect_time" '
                       'uht="$upstream_header_time" urt="$upstream_response_time"';
    
    access_log /var/log/nginx/swarm-access.log detailed;
    error_log /var/log/nginx/swarm-error.log warn;
    
    # Router API (LiteLLM) with enhanced settings
    location /v1/ {
        limit_req zone=api_limit burst=50 nodelay;
        
        proxy_pass http://router_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header Connection "";
        
        # Timeouts
        proxy_connect_timeout 10s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 16k;
        proxy_buffers 32 16k;
        proxy_busy_buffers_size 64k;
        
        # Caching for static responses
        proxy_cache_valid 200 302 1m;
        proxy_cache_valid 404 1m;
        
        # Error handling
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;
        proxy_next_upstream_tries 2;
        proxy_next_upstream_timeout 10s;
        
        # Add monitoring headers
        add_header X-Upstream-Response-Time $upstream_response_time;
        add_header X-Request-ID $request_id;
    }
    
    # Orchestrator API with enhanced settings
    location /api/ {
        limit_req zone=orchestrator_limit burst=10 nodelay;
        
        proxy_pass http://orchestrator_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header Connection "";
        proxy_set_header X-Request-ID $request_id;
        
        # Extended timeouts for long-running tasks
        proxy_connect_timeout 10s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        
        # WebSocket support for real-time features
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        
        # CORS headers for API access
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type, X-Requested-With, X-Request-ID" always;
        add_header Access-Control-Expose-Headers "X-Request-ID, X-Upstream-Response-Time" always;
        add_header Access-Control-Max-Age 86400 always;
        
        # Handle preflight requests
        if ($request_method = 'OPTIONS') {
            return 204;
        }
        
        # Error handling
        proxy_next_upstream error timeout http_500 http_502 http_503 http_504;
        proxy_next_upstream_tries 2;
    }
    
    # Health check endpoint with minimal logging
    location /health {
        limit_req zone=health_limit burst=20 nodelay;
        access_log off;
        
        return 200 "OK\n";
        add_header Content-Type text/plain;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header X-Health-Check "true";
    }
    
    # Deep health check for monitoring systems
    location /health/detailed {
        limit_req zone=health_limit burst=5 nodelay;
        access_log off;
        
        proxy_pass http://orchestrator_backend/api/health;
        proxy_connect_timeout 5s;
        proxy_read_timeout 10s;
    }
    
    # Nginx status for monitoring (restricted access)
    location /nginx_status {
        allow 127.0.0.1;
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny all;
        
        stub_status on;
        access_log off;
    }
    
    # API documentation and dashboard
    location /docs {
        proxy_pass http://orchestrator_backend/api/docs;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Static assets with caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options nosniff;
        
        # Serve from upstream if not found locally
        try_files $uri @upstream;
    }
    
    location @upstream {
        proxy_pass http://orchestrator_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Security: Block common attack patterns
    location ~* /(wp-admin|wp-login|phpMyAdmin|admin|administrator|xmlrpc\.php|wp-config\.php) {
        limit_req zone=login_limit burst=2 nodelay;
        return 444;
    }
    
    # Security: Block file extensions that shouldn't be served
    location ~* \.(env|git|htaccess|ini|log|bak|sql|conf|key|pem|crt)$ {
        deny all;
        return 404;
    }
    
    # Security: Block hidden files
    location ~ /\. {
        deny all;
        return 404;
    }
    
    # API information endpoint
    location = / {
        return 200 '{
            "service": "Coding Swarm API",
            "version": "2.0.0",
            "status": "operational",
            "endpoints": {
                "router": "/v1/",
                "orchestrator": "/api/",
                "health": "/health",
                "detailed_health": "/health/detailed",
                "documentation": "/docs"
            },
            "features": [
                "Multi-agent AI development",
                "Real-time code generation",
                "Automated testing",
                "Project scaffolding",
                "Performance monitoring"
            ]
        }';
        add_header Content-Type application/json;
        add_header Cache-Control "no-cache";
    }
    
    # Redirect other requests to API documentation
    location / {
        return 302 /docs;
    }
}
EOF

    # Add HTTP to HTTPS redirect if SSL is enabled
    if [[ "$ENABLE_SSL" != "false" ]] && [[ -n "$DOMAIN" ]] && [[ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]]; then
        cat >> /etc/nginx/sites-available/coding-swarm << EOF

# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    
    # Security headers even for redirects
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    
    # Health check exception (for load balancers)
    location /health {
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }
    
    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}
EOF
    fi
    
    # Add map directive for WebSocket upgrade
    cat > /etc/nginx/conf.d/websocket.conf << 'EOF'
# WebSocket upgrade configuration
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}
EOF

    # Ensure include in nginx.conf if not present
    if ! grep -q "include /etc/nginx/conf.d/*.conf;" /etc/nginx/nginx.conf; then
        sed -i '/http {/a \    include /etc/nginx/conf.d/*.conf;' /etc/nginx/nginx.conf
    fi
    
    # Test Nginx configuration
    if nginx -t; then
        log_success "Nginx configuration optimized and validated"
        systemctl reload nginx
    else
        log_error "Nginx configuration test failed, restoring backup"
        if [[ -f /etc/nginx/sites-available/coding-swarm.backup ]]; then
            cp /etc/nginx/sites-available/coding-swarm.backup /etc/nginx/sites-available/coding-swarm
            if nginx -t; then
                log_success "Backup restored successfully"
                systemctl reload nginx
            else
                log_error "Backup restoration failed"
                return 1
            fi
        else
            log_error "No backup available to restore"
            return 1
        fi
    fi
    
    return 0
}

# ============================================
# SYSTEM OPTIMIZATION
# ============================================
optimize_system_performance() {
    if [[ "$SKIP_OPTIMIZATION" == "true" ]]; then
        log_info "System optimization skipped"
        return 0
    fi
    
    log_info "Applying system performance optimizations..."
    
    backup_config "/etc/sysctl.d/99-coding-swarm.conf"
    
    # Kernel parameter optimizations
    cat > /etc/sysctl.d/99-coding-swarm.conf << 'EOF'
# Coding Swarm System Optimizations

# Network optimizations
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 8192
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 1200
net.ipv4.tcp_keepalive_probes = 3
net.ipv4.tcp_keepalive_intvl = 15
net.ipv4.tcp_max_tw_buckets = 400000
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_congestion_control = bbr

# Memory management
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
vm.overcommit_memory = 1

# File system optimizations
fs.file-max = 1000000
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 512

# Security
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
EOF
    
    # Apply sysctl settings
    sysctl -p /etc/sysctl.d/99-coding-swarm.conf >/dev/null 2>&1 || log_warning "Failed to apply sysctl settings"
    
    # Optimize systemd services limits
    for service in swarm-router swarm-orchestrator; do
        ensure_directory "/etc/systemd/system/$service.service.d"
        cat > /etc/systemd/system/$service.service.d/limits.conf << 'EOF'
[Service]
LimitNOFILE=65536
LimitNPROC=32768
EOF
    done
    
    # Optimize for each agent
    for agent in laravel react flutter testing; do
        ensure_directory "/etc/systemd/system/swarm-agent-${agent}.service.d"
        cat > "/etc/systemd/system/swarm-agent-${agent}.service.d/limits.conf" << 'EOF'
[Service]
LimitNOFILE=32768
LimitNPROC=16384
EOF
    done
    
    # Reload systemd configuration
    systemctl daemon-reload || log_error "Failed to reload systemd"
    
    log_success "System performance optimizations applied"
    return 0
}

# ============================================
# SERVICE VERIFICATION AND HEALTH CHECKS
# ============================================
verify_all_services() {
    log_info "Performing comprehensive service verification..."
    
    local verification_results=()
    local router_key
    router_key=$(cat "$CONFIG_DIR/secrets/router.key")
    
    # Check systemd services
    local services=(
        "swarm-router:Router Service"
        "swarm-orchestrator:Orchestrator Service"
        "swarm-agent-laravel:Laravel Agent"
        "swarm-agent-react:React Agent"
        "swarm-agent-flutter:Flutter Agent"
        "swarm-agent-testing:Testing Agent"
        "nginx:Web Server"
        "redis-server:Redis Cache"
    )
    
    log_info "Checking systemd services..."
    for service_info in "${services[@]}"; do
        local service_name=$(echo "$service_info" | cut -d: -f1)
        local display_name=$(echo "$service_info" | cut -d: -f2)
        
        if systemctl is-active --quiet "$service_name" && systemctl is-enabled --quiet "$service_name"; then
            verification_results+=("✅ $display_name: Active and enabled")
        elif systemctl is-active --quiet "$service_name"; then
            verification_results+=("⚠️ $display_name: Active but not enabled")
        else
            verification_results+=("❌ $display_name: Inactive")
        fi
    done
    
    # Check API endpoints with detailed testing
    log_info "Testing API endpoints..."
    
    # Router API health check
    local router_response router_status
    router_response=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $router_key" \
        "http://127.0.0.1:8000/v1/models" -o /tmp/router_test.json 2>/dev/null || echo "000")
    
    if [[ "$router_response" == "200" ]]; then
        local model_count
        model_count=$(jq '.data | length' /tmp/router_test.json 2>/dev/null || echo "0")
        verification_results+=("✅ Router API: $model_count models available")
    else
        verification_results+=("❌ Router API: HTTP $router_response")
    fi
    
    # Orchestrator API health check
    local orchestrator_response
    orchestrator_response=$(curl -s "http://127.0.0.1:9000/api/health" 2>/dev/null || echo "{}")
    
    if echo "$orchestrator_response" | jq -e '.status == "healthy"' >/dev/null 2>&1; then
        local uptime active_tasks
        uptime=$(echo "$orchestrator_response" | jq -r '.uptime // "0"' | xargs printf "%.0f" || echo "0")
        active_tasks=$(echo "$orchestrator_response" | jq -r '.active_tasks // "0"' || echo "0")
        verification_results+=("✅ Orchestrator API: Healthy (uptime: ${uptime}s, tasks: $active_tasks)")
    else
        verification_results+=("❌ Orchestrator API: Unhealthy or invalid response")
    fi
    
    # Individual agent health checks (parallel)
    log_info "Testing individual AI agents..."
    local local_key
    local_key=$(cat "$CONFIG_DIR/secrets/localmodel.key")
    
    local agent_ports=("8001:Laravel" "8002:React" "8003:Flutter" "8004:Testing")
    local agent_results=()
    
    for agent_info in "${agent_ports[@]}"; do
        (
            local port=$(echo "$agent_info" | cut -d: -f1)
            local agent_name=$(echo "$agent_info" | cut -d: -f2)
            
            local agent_response agent_time
            agent_time=$(date +%s.%N)
            agent_response=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $local_key" \
                "http://127.0.0.1:$port/health" -o /dev/null 2>/dev/null || echo "000")
            agent_time=$(echo "$(date +%s.%N) - $agent_time" | bc -l 2>/dev/null | xargs printf "%.2f" 2>/dev/null || echo "N/A")
            
            if [[ "$agent_response" == "200" ]]; then
                echo "✅ $agent_name Agent: Healthy (${agent_time}s response)"
            else
                echo "❌ $agent_name Agent: HTTP $agent_response"
            fi
        ) &
    done
    wait
    for job in $(jobs -p); do
        agent_results+=($(wait $job))
    done
    verification_results+=("${agent_results[@]}")
    
    # Docker container verification
    log_info "Checking Docker containers..."
    if ! command -v docker >/dev/null 2>&1 || ! systemctl is-active --quiet docker; then
        verification_results+=("❌ Docker: Not installed or not running")
    else
        local container_status
        container_status=$(docker ps --filter "name=swarm-agent" --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "")
        
        if [[ -n "$container_status" ]]; then
            local container_count
            container_count=$(echo "$container_status" | tail -n +2 | wc -l)
            verification_results+=("✅ Docker Containers: $container_count running")
            
            # Check individual container health
            echo "$container_status" | tail -n +2 | while read -r name status; do
                if [[ "$status" =~ "healthy" ]] || [[ "$status" =~ "Up" ]]; then
                    verification_results+=("  ✅ $name: $status")
                else
                    verification_results+=("  ⚠️ $name: $status")
                fi
            done
        else
            verification_results+=("❌ Docker Containers: None found")
        fi
    fi
    
    # Database connectivity check
    log_info "Testing database connectivity..."
    if redis-cli ping >/dev/null 2>&1; then
        verification_results+=("✅ Redis: Connected and responsive")
    else
        verification_results+=("❌ Redis: Connection failed")
    fi
    
    # File system checks
    log_info "Verifying file system setup..."
    local fs_checks=(
        "$INSTALL_DIR:Installation directory"
        "$CONFIG_DIR:Configuration directory"
        "$LOG_DIR:Log directory"
        "$PROJECT_DIR:Project directory"
        "$BACKUP_DIR:Backup directory"
    )
    
    for fs_check in "${fs_checks[@]}"; do
        local path=$(echo "$fs_check" | cut -d: -f1)
        local description=$(echo "$fs_check" | cut -d: -f2)
        
        if [[ -d "$path" ]] && [[ -r "$path" ]] && [[ -w "$path" ]]; then
            verification_results+=("✅ $description: Accessible")
        else
            verification_results+=("❌ $description: Access issues")
        fi
    done
    
    # Network connectivity verification
    log_info "Testing external connectivity..."
    if curl -s --connect-timeout 5 https://httpbin.org/get >/dev/null 2>&1; then
        verification_results+=("✅ External Network: Connected")
    else
        verification_results+=("⚠️ External Network: Limited connectivity")
    fi
    
    # Print verification results
    echo
    log_info "=== VERIFICATION RESULTS ==="
    for result in "${verification_results[@]}"; do
        echo "  $result"
    done
    echo
    
    # Cleanup temporary files
    cleanup_temp_files
    
    # Return success if no critical failures
    local critical_failures
    critical_failures=$(printf '%s\n' "${verification_results[@]}" | grep -c "❌" || echo "0")
    
    if [[ $critical_failures -eq 0 ]]; then
        log_success "All verification checks passed!"
        return 0
    else
        log_warning "$critical_failures critical issues found"
        return 1
    fi
}

# ============================================
# PERFORMANCE TESTING
# ============================================
run_performance_tests() {
    log_info "Running performance tests..."
    
    local router_key
    router_key=$(cat "$CONFIG_DIR/secrets/router.key")
    
    # Test 1: Router API response time
    log_info "Testing Router API performance..."
    local router_times=()
    for i in {1..5}; do
        local start_time end_time response_time
        start_time=$(date +%s.%N)
        
        if curl --max-time 5 -s -H "Authorization: Bearer $router_key" \
           "http://127.0.0.1:8000/v1/models" >/dev/null 2>&1; then
            end_time=$(date +%s.%N)
            response_time=$(echo "$end_time - $start_time" | bc -l)
            router_times+=("$response_time")
            log_info "Router API test $i: ${response_time}s"
        else
            log_error "Router API test $i failed"
        fi
        sleep 2
    done
    
    if [[ ${#router_times[@]} -gt 0 ]]; then
        local avg_time
        avg_time=$(printf '%s\n' "${router_times[@]}" | awk '{sum+=$1} END {print sum/NR}')
        log_success "Router API average response time: $(printf "%.3f" "$avg_time")s"
    else
        log_error "Router API performance test failed"
    fi
    
    # Test 2: Orchestrator API response time
    log_info "Testing Orchestrator API performance..."
    local orchestrator_times=()
    for i in {1..5}; do
        local start_time end_time response_time
        start_time=$(date +%s.%N)
        
        if curl --max-time 5 -s "http://127.0.0.1:9000/api/health" >/dev/null 2>&1; then
            end_time=$(date +%s.%N)
            response_time=$(echo "$end_time - $start_time" | bc -l)
            orchestrator_times+=("$response_time")
            log_info "Orchestrator API test $i: ${response_time}s"
        else
            log_error "Orchestrator API test $i failed"
        fi
        sleep 2
    done
    
    if [[ ${#orchestrator_times[@]} -gt 0 ]]; then
        local avg_time
        avg_time=$(printf '%s\n' "${orchestrator_times[@]}" | awk '{sum+=$1} END {print sum/NR}')
        log_success "Orchestrator API average response time: $(printf "%.3f" "$avg_time")s"
    else
        log_error "Orchestrator API performance test failed"
    fi
    
    # Test 3: System resource usage under load
    log_info "Checking system resource usage..."
    local cpu_usage memory_usage load_avg
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')
    memory_usage=$(free | awk 'NR==2{printf "%.1f", $3*100/$2}')
    load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    
    log_info "Current system load: CPU ${cpu_usage}, Memory ${memory_usage}%, Load ${load_avg}"
    
    # Test 4: End-to-end API test
    log_info "Running end-to-end API test..."
    local test_response test_task_id
    test_response=$(curl -s -X POST "http://127.0.0.1:9000/api/tasks" \
        -H "Authorization: Bearer $router_key" \
        -H "Content-Type: application/json" \
        -d '{
            "description": "Performance test: Create a simple hello world function",
            "project_type": "laravel",
            "priority": "normal"
        }' 2>/dev/null || echo "{}")
    
    if echo "$test_response" | jq -e '.task_id' >/dev/null 2>&1; then
        test_task_id=$(echo "$test_response" | jq -r '.task_id')
        log_success "End-to-end test successful (Task ID: $test_task_id)"
        
        # Wait a moment and check task status
        sleep 3
        local task_status
        task_status=$(curl -s "http://127.0.0.1:9000/api/tasks/$test_task_id" \
            -H "Authorization: Bearer $router_key" 2>/dev/null || echo "{}")
        
        local status
        status=$(echo "$task_status" | jq -r '.status // "unknown"')
        log_info "Task status after 3s: $status"
    else
        log_error "End-to-end test failed"
    fi
    
    return 0
}

# ============================================
# MONITORING SETUP
# ============================================
setup_advanced_monitoring() {
    log_info "Setting up advanced monitoring and alerting..."
    
    ensure_directory "$CONFIG_DIR/monitoring"
    
    backup_config "$CONFIG_DIR/monitoring/alerts.conf"
    
    # Enhanced monitoring script with metrics collection
    cat > "$INSTALL_DIR/scripts/advanced-monitor.sh" << 'EOF'
#!/bin/bash
set -euo pipefail

# Advanced Monitoring Script for Coding Swarm
LOG_FILE="/var/log/coding-swarm/monitoring.log"
METRICS_FILE="/var/log/coding-swarm/metrics.json"
ALERT_FILE="/var/log/coding-swarm/alerts.log"

# Configuration
CPU_THRESHOLD=80
MEMORY_THRESHOLD=85
DISK_THRESHOLD=90
RESPONSE_TIME_THRESHOLD=5.0
ERROR_RATE_THRESHOLD=10

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$(dirname "$METRICS_FILE")"
mkdir -p "$(dirname "$ALERT_FILE")"

# Load API keys safely
if [[ -f "/etc/coding-swarm/secrets/router.key" ]]; then
    ROUTER_KEY=$(cat /etc/coding-swarm/secrets/router.key)
else
    echo "Error: Router key not found" >&2
    exit 1
fi

if [[ -f "/etc/coding-swarm/secrets/localmodel.key" ]]; then
    LOCAL_KEY=$(cat /etc/coding-swarm/secrets/localmodel.key)
else
    echo "Error: Local model key not found" >&2
    exit 1
fi

log_metric() {
    echo "[$(date -Iseconds)] $1" | tee -a "$LOG_FILE"
}

send_alert() {
    local severity="$1"
    local message="$2"
    local timestamp=$(date -Iseconds)
    
    echo "[$timestamp] [$severity] $message" >> "$ALERT_FILE"
    
    # Future: Add webhook/email notifications here
    # curl -X POST "$WEBHOOK_URL" -d "{\"severity\":\"$severity\",\"message\":\"$message\"}"
}

collect_system_metrics() {
    local timestamp=$(date -Iseconds)
    
    # CPU metrics
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//' | sed 's/\..*//')
    
    # Memory metrics
    local memory_info=($(free | awk 'NR==2{print $2,$3,$7}'))
    local memory_total=${memory_info[0]}
    local memory_used=${memory_info[1]}
    local memory_available=${memory_info[2]}
    local memory_percent=$(echo "scale=1; $memory_used * 100 / $memory_total" | bc -l)
    
    # Disk metrics
    local disk_info=($(df / | awk 'NR==2{print $2,$3,$4,$5}'))
    local disk_total=${disk_info[0]}
    local disk_used=${disk_info[1]}
    local disk_available=${disk_info[2]}
    local disk_percent=$(echo "${disk_info[3]}" | sed 's/%//')
    
    # Load average
    local load_avg=($(uptime | awk -F'load average:' '{print $2}' | sed 's/,//g'))
    
    # Network connections
    local tcp_connections=$(ss -t | wc -l)
    local established_connections=$(ss -t state established | wc -l)
    
    # Process counts
    local total_processes=$(ps aux | wc -l)
    local swarm_processes=$(ps aux | grep -c "[s]warm" || echo "0")
    
    # Generate JSON metrics
    cat > "$METRICS_FILE" << EOF
{
    "timestamp": "$timestamp",
    "system": {
        "cpu": {
            "usage_percent": $cpu_usage
        },
        "memory": {
            "total_bytes": $memory_total,
            "used_bytes": $memory_used,
            "available_bytes": $memory_available,
            "usage_percent": $memory_percent
        },
        "disk": {
            "total_kb": $disk_total,
            "used_kb": $disk_used,
            "available_kb": $disk_available,
            "usage_percent": $disk_percent
        },
        "load_average": {
            "1min": ${load_avg[0]},
            "5min": ${load_avg[1]},
            "15min": ${load_avg[2]}
        },
        "network": {
            "tcp_connections": $tcp_connections,
            "established_connections": $established_connections
        },
        "processes": {
            "total": $total_processes,
            "swarm_related": $swarm_processes
        }
    }
}
EOF
    
    # Check thresholds and send alerts
    if [[ ${cpu_usage:-0} -gt $CPU_THRESHOLD ]]; then
        send_alert "WARNING" "High CPU usage: ${cpu_usage}% > ${CPU_THRESHOLD}%"
    fi
    
    if [[ $(echo "$memory_percent > $MEMORY_THRESHOLD" | bc -l) -eq 1 ]]; then
        send_alert "WARNING" "High memory usage: ${memory_percent}% > ${MEMORY_THRESHOLD}%"
    fi
    
    if [[ ${disk_percent:-0} -gt $DISK_THRESHOLD ]]; then
        send_alert "CRITICAL" "High disk usage: ${disk_percent}% > ${DISK_THRESHOLD}%"
    fi
}

collect_service_metrics() {
    local temp_file="/tmp/service_metrics_$$.json"
    
    # Service status checks
    local services=("swarm-router" "swarm-orchestrator" "swarm-agent-laravel" "swarm-agent-react" "swarm-agent-flutter" "swarm-agent-testing")
    local service_status=()
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            service_status+=("\"$service\": true")
        else
            service_status+=("\"$service\": false")
            send_alert "CRITICAL" "Service $service is not running"
        fi
    done
    
    # API response time checks
    local router_time=$(curl -s -o /dev/null -w "%{time_total}" --max-time 10 \
        -H "Authorization: Bearer $ROUTER_KEY" \
        "http://127.0.0.1:8000/v1/models" 2>/dev/null || echo "0")
    
    local orchestrator_time=$(curl -s -o /dev/null -w "%{time_total}" --max-time 10 \
        "http://127.0.0.1:9000/api/health" 2>/dev/null || echo "0")
    
    # Check response time thresholds
    if [[ $(echo "$router_time > $RESPONSE_TIME_THRESHOLD" | bc -l) -eq 1 ]]; then
        send_alert "WARNING" "Router API slow response: ${router_time}s > ${RESPONSE_TIME_THRESHOLD}s"
    fi
    
    if [[ $(echo "$orchestrator_time > $RESPONSE_TIME_THRESHOLD" | bc -l) -eq 1 ]]; then
        send_alert "WARNING" "Orchestrator API slow response: ${orchestrator_time}s > ${RESPONSE_TIME_THRESHOLD}s"
    fi
    
    # Agent health checks
    local agent_metrics=()
    for port in 8001 8002 8003 8004; do
        local agent_time=$(curl -s -o /dev/null -w "%{time_total}" --max-time 5 \
            -H "Authorization: Bearer $LOCAL_KEY" \
            "http://127.0.0.1:$port/health" 2>/dev/null || echo "0")
        
        agent_metrics+=("\"port_$port\": $agent_time")
        
        if [[ $(echo "$agent_time == 0" | bc -l) -eq 1 ]]; then
            send_alert "CRITICAL" "Agent on port $port is not responding"
        fi
    done
    
    # Add service metrics to main metrics file
    jq --argjson services "{$(IFS=,; echo "${service_status[*]}")}" \
       --arg router_time "$router_time" \
       --arg orchestrator_time "$orchestrator_time" \
       --argjson agents "{$(IFS=,; echo "${agent_metrics[*]}")}" \
       '.services = {
           "status": $services,
           "response_times": {
               "router": ($router_time | tonumber),
               "orchestrator": ($orchestrator_time | tonumber),
               "agents": $agents
           }
       }' "$METRICS_FILE" > "$temp_file" && mv "$temp_file" "$METRICS_FILE"
}

collect_application_metrics() {
    local temp_file="/tmp/app_metrics_$$.json"
    
    # Docker container metrics
    local container_stats
    if command -v docker >/dev/null && docker ps --filter "name=swarm-agent" --format "{{.Names}}" | head -1 >/dev/null 2>&1; then
        container_stats=$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
            $(docker ps --filter "name=swarm-agent" --format "{{.Names}}") 2>/dev/null || echo "")
    else
        container_stats=""
    fi
    
    # Task queue metrics (if available)
    local active_tasks=0
    local queued_tasks=0
    
    local orchestrator_health
    orchestrator_health=$(curl -s "http://127.0.0.1:9000/api/health" 2>/dev/null || echo "{}")
    
    if echo "$orchestrator_health" | jq -e '.active_tasks' >/dev/null 2>&1; then
        active_tasks=$(echo "$orchestrator_health" | jq -r '.active_tasks')
    fi
    
    # Add application metrics
    jq --arg active_tasks "$active_tasks" \
       --arg queued_tasks "$queued_tasks" \
       --arg container_stats "$container_stats" \
       '.application = {
           "tasks": {
               "active": ($active_tasks | tonumber),
               "queued": ($queued_tasks | tonumber)
           },
           "containers": $container_stats
       }' "$METRICS_FILE" > "$temp_file" && mv "$temp_file" "$METRICS_FILE"
}

generate_monitoring_report() {
    local report_file="/var/log/coding-swarm/monitoring-report-$(date +%Y%m%d_%H%M).log"
    
    cat > "$report_file" << EOF
=== Coding Swarm Monitoring Report ===
Generated: $(date -Iseconds)

$(cat "$METRICS_FILE" | jq -r '
"System Metrics:",
"  CPU Usage: " + (.system.cpu.usage_percent | tostring) + "%",
"  Memory Usage: " + (.system.memory.usage_percent | tostring) + "%",
"  Disk Usage: " + (.system.disk.usage_percent | tostring) + "%",
"  Load Average: " + (.system.load_average."1min" | tostring),
"",
"Service Status:",
(.services.status | to_entries[] | "  " + .key + ": " + (if .value then "✓ Running" else "✗ Stopped" end)),
"",
"Response Times:",
"  Router API: " + (.services.response_times.router | tostring) + "s",
"  Orchestrator API: " + (.services.response_times.orchestrator | tostring) + "s",
"",
"Application:",
"  Active Tasks: " + (.application.tasks.active | tostring),
"  Queued Tasks: " + (.application.tasks.queued | tostring)
')

Recent Alerts:
$(tail -10 "$ALERT_FILE" 2>/dev/null || echo "No recent alerts")

EOF
    
    log_metric "Monitoring report generated: $report_file"
}

# Main execution
main() {
    log_metric "Starting advanced monitoring cycle"
    
    collect_system_metrics
    collect_service_metrics
    collect_application_metrics
    generate_monitoring_report
    
    log_metric "Monitoring cycle completed"
}

main "$@"
EOF
    
    chmod +x "$INSTALL_DIR/scripts/advanced-monitor.sh" || log_error "Failed to set executable permissions for advanced-monitor.sh"
    
    # Create monitoring dashboard script
    cat > "$INSTALL_DIR/scripts/dashboard.sh" << 'EOF'
#!/bin/bash
# Real-time monitoring dashboard
set -euo pipefail

METRICS_FILE="/var/log/coding-swarm/metrics.json"

show_dashboard() {
    clear
    echo "=============================================="
    echo "      CODING SWARM REAL-TIME DASHBOARD"
    echo "=============================================="
    echo "Last Update: $(date)"
    echo
    
    if [[ -f "$METRICS_FILE" ]] && [[ -s "$METRICS_FILE" ]]; then
        if jq empty "$METRICS_FILE" 2>/dev/null; then
            jq -r '
            "System Resources:",
            "  🖥️  CPU Usage: " + (.system.cpu.usage_percent | tostring) + "%",
            "  🧠  Memory: " + (.system.memory.usage_percent | tostring) + "% (" + ((.system.memory.used_bytes / 1024 / 1024) | floor | tostring) + "MB used)",
            "  💾  Disk: " + (.system.disk.usage_percent | tostring) + "% (" + ((.system.disk.available_kb / 1024 / 1024) | floor | tostring) + "GB free)",
            "  ⚡  Load: " + (.system.load_average."1min" | tostring),
            "",
            "Service Health:",
            (.services.status | to_entries[] | "  " + (if .value then "✅" else "❌" end) + "  " + .key),
            "",
            "API Performance:",
            "  🌐  Router: " + (.services.response_times.router * 1000 | floor | tostring) + "ms",
            "  🎯  Orchestrator: " + (.services.response_times.orchestrator * 1000 | floor | tostring) + "ms",
            "",
            "Application:",
            "  📝  Active Tasks: " + (.application.tasks.active | tostring),
            "  ⏳  Queued Tasks: " + (.application.tasks.queued | tostring)
            ' "$METRICS_FILE" 2>/dev/null
        else
            echo "Metrics file exists but contains invalid JSON"
            echo "Run the monitoring script to generate fresh metrics:"
            echo "  /opt/coding-swarm/scripts/advanced-monitor.sh"
        fi
    else
        echo "Metrics not available yet."
        echo
        echo "To start collecting metrics, run:"
        echo "  /opt/coding-swarm/scripts/advanced-monitor.sh"
        echo
        echo "Or wait for the automated collection (runs every minute)"
        echo
        echo "Basic system info:"
        echo "  Uptime: $(uptime | awk '{print $3,$4}' | sed 's/,//')"
        echo "  Load: $(uptime | awk -F'load average:' '{print $2}')"
        echo "  Memory: $(free -h | awk 'NR==2{print $3"/"$2}')"
        echo "  Disk: $(df -h / | awk 'NR==2{print $4" free ("$5" used)"}')"
    fi
    
    echo
    echo "=============================================="
    echo "Press Ctrl+C to exit | Refresh every 5 seconds"
}

# Check if running interactively
if [[ -t 0 ]]; then
    # Live dashboard
    trap 'echo -e "\n\nDashboard stopped."; exit 0' INT
    
    while true; do
        show_dashboard
        sleep 5
    done
else
    # Non-interactive mode, show once
    show_dashboard
fi
EOF
    
    chmod +x "$INSTALL_DIR/scripts/dashboard.sh" || log_error "Failed to set executable permissions for dashboard.sh"
    
    # Update cron jobs with advanced monitoring
    cat > /etc/cron.d/swarm-advanced-monitoring << 'EOF'
# Advanced Coding Swarm Monitoring

# Collect metrics every minute
* * * * * root /opt/coding-swarm/scripts/advanced-monitor.sh

# Generate hourly reports
0 * * * * root /opt/coding-swarm/scripts/advanced-monitor.sh && echo "Hourly report generated" >> /var/log/coding-swarm/monitoring.log

# Daily cleanup and rotation
0 0 * * * root find /var/log/coding-swarm -name "monitoring-report-*.log" -mtime +7 -delete
EOF
    
    # Create alert configuration template
    cat > "$CONFIG_DIR/monitoring/alerts.conf" << 'EOF'
# Alert Configuration for Coding Swarm
# Edit this file to configure alerting thresholds and channels

[thresholds]
cpu_warning=80
cpu_critical=95
memory_warning=85
memory_critical=95
disk_warning=90
disk_critical=95
response_time_warning=5.0
response_time_critical=10.0

[channels]
# webhook_url=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
# email_to=admin@your-domain.com
# email_from=swarm@your-domain.com
# smtp_server=smtp.your-domain.com

[notifications]
enable_webhook=false
enable_email=false
enable_log=true
EOF
    
    chown -R swarm:swarm "$INSTALL_DIR/scripts" || log_error "Failed to set ownership for scripts"
    
    log_success "Advanced monitoring setup completed"
    return 0
}

# ============================================
# BACKUP AND DISASTER RECOVERY SETUP
# ============================================
setup_disaster_recovery() {
    log_info "Setting up disaster recovery and backup systems..."
    
    ensure_directory "$CONFIG_DIR/backup"
    
    # Enhanced backup script with encryption and compression
    cat > "$INSTALL_DIR/scripts/disaster-recovery.sh" << 'EOF'
#!/bin/bash
set -euo pipefail

# Disaster Recovery Script for Coding Swarm
BACKUP_DIR="/opt/backups/coding-swarm"
REMOTE_BACKUP_DIR="${REMOTE_BACKUP_DIR:-}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
COMPRESSION_LEVEL="${BACKUP_COMPRESSION_LEVEL:-6}"

DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/var/log/coding-swarm/disaster-recovery.log"

log_backup() {
    echo "[$(date -Iseconds)] $1" | tee -a "$LOG_FILE"
}

create_full_backup() {
    local backup_name="full-backup-$DATE"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    log_backup "Creating full system backup: $backup_name"
    mkdir -p "$backup_path"
    
    # Backup configurations
    log_backup "Backing up configurations..."
    tar -czf "$backup_path/configs.tar.gz" \
        /etc/coding-swarm/ \
        /etc/systemd/system/swarm-*.service \
        /etc/nginx/sites-available/coding-swarm \
        /etc/cron.d/swarm-* \
        /etc/logrotate.d/coding-swarm \
        2>/dev/null || log_backup "Some config files missing"
    
    # Backup application code and data
    log_backup "Backing up application data..."
    tar -czf "$backup_path/application.tar.gz" \
        --exclude="*/models/*.gguf" \
        --exclude="*/node_modules" \
        --exclude="*/vendor" \
        --exclude="*/.git" \
        /opt/coding-swarm/ \
        2>/dev/null || log_backup "Some application files missing"
    
    # Backup projects
    log_backup "Backing up projects..."
    if [[ -d "/home/swarm/projects" ]]; then
        tar -czf "$backup_path/projects.tar.gz" \
            --exclude="*/node_modules" \
            --exclude="*/vendor" \
            --exclude="*/build" \
            --exclude="*/dist" \
            /home/swarm/projects/ \
            2>/dev/null || log_backup "No projects found"
    fi
    
    # Backup databases
    log_backup "Backing up databases..."
    mkdir -p "$backup_path/databases"
    
    # Redis backup
    if systemctl is-active --quiet redis-server; then
        redis-cli BGSAVE >/dev/null 2>&1 || true
        sleep 2
        if [[ -f "/var/lib/redis/dump.rdb" ]]; then
            cp "/var/lib/redis/dump.rdb" "$backup_path/databases/redis.rdb"
        fi
    fi
    
    # SQLite databases
    find /var/log/coding-swarm -name "*.db" -exec cp {} "$backup_path/databases/" \; 2>/dev/null || true
    find /home/swarm/projects -name "*.db" -exec cp {} "$backup_path/databases/" \; 2>/dev/null || true
    
    # Backup logs (recent only)
    log_backup "Backing up recent logs..."
    find /var/log/coding-swarm -name "*.log" -mtime -7 \
        -exec tar -czf "$backup_path/logs.tar.gz" {} + 2>/dev/null || true
    
    # Backup documentation
    log_backup "Backing up documentation..."
    tar -czf "$backup_path/documentation.tar.gz" "/home/swarm/projects/documentation" 2>/dev/null || true
    
    # Create backup manifest
    cat > "$backup_path/manifest.json" << EOF
{
    "backup_type": "full",
    "timestamp": "$(date -Iseconds)",
    "hostname": "$(hostname)",
    "version": "2.0.0",
    "files": [
        "configs.tar.gz",
        "application.tar.gz", 
        "projects.tar.gz",
        "databases/",
        "logs.tar.gz",
        "documentation.tar.gz"
    ],
    "size_bytes": $(du -sb "$backup_path" | cut -f1),
    "checksum": "$(find "$backup_path" -type f -exec md5sum {} \; | md5sum | cut -d' ' -f1)"
}
EOF
    
    # Encrypt backup if key provided
    if [[ -n "$ENCRYPTION_KEY" ]]; then
        if [[ ${#ENCRYPTION_KEY} -lt 8 ]]; then
            log_backup "Encryption key too short (minimum 8 characters)"
            return 1
        fi
        log_backup "Encrypting backup..."
        tar -czf - -C "$BACKUP_DIR" "$backup_name" | \
            openssl enc -aes-256-cbc -salt -k "$ENCRYPTION_KEY" \
            > "$backup_path.encrypted"
        rm -rf "$backup_path"
        backup_path="$backup_path.encrypted"
    fi
    
    # Upload to remote storage if configured
    if [[ -n "$REMOTE_BACKUP_DIR" ]]; then
        log_backup "Uploading to remote storage..."
        if command -v rsync >/dev/null; then
            if rsync -av "$backup_path" "$REMOTE_BACKUP_DIR/"; then
                log_backup "Remote backup upload successful"
            else
                log_backup "Remote backup upload failed"
                return 1
            fi
        elif command -v aws >/dev/null; then
            if aws s3 cp "$backup_path" "$REMOTE_BACKUP_DIR/"; then
                log_backup "S3 backup upload successful"
            else
                log_backup "S3 backup upload failed"
                return 1
            fi
        else
            log_backup "No remote backup tool available (rsync or aws required)"
            return 1
        fi
    fi
    
    log_backup "Full backup completed: $backup_path"
    return 0
}

create_incremental_backup() {
    local backup_name="incremental-backup-$DATE"
    local backup_path="$BACKUP_DIR/$backup_name"
    local last_backup
    
    # Find last full backup
    last_backup=$(find "$BACKUP_DIR" -name "full-backup-*" -type d | sort | tail -1)
    
    if [[ -z "$last_backup" ]]; then
        log_backup "No full backup found, creating full backup instead"
        create_full_backup
        return $?
    fi
    
    log_backup "Creating incremental backup since $(basename "$last_backup")"
    mkdir -p "$backup_path"
    
    # Find files changed since last backup
    local last_backup_time
    last_backup_time=$(stat -c %Y "$last_backup")
    
    # Backup changed configurations
    find /etc/coding-swarm /etc/systemd/system /etc/nginx/sites-available -newer "$last_backup" -type f \
        -exec tar -czf "$backup_path/configs-incremental.tar.gz" {} + 2>/dev/null || true
    
    # Backup changed application files
    find /opt/coding-swarm -newer "$last_backup" -type f ! -name "*.gguf" \
        -exec tar -czf "$backup_path/application-incremental.tar.gz" {} + 2>/dev/null || true
    
    # Backup changed projects
    find /home/swarm/projects -newer "$last_backup" -type f \
        ! -path "*/node_modules/*" ! -path "*/vendor/*" \
        -exec tar -czf "$backup_path/projects-incremental.tar.gz" {} + 2>/dev/null || true
    
    # Create incremental manifest
    cat > "$backup_path/manifest.json" << EOF
{
    "backup_type": "incremental",
    "timestamp": "$(date -Iseconds)",
    "hostname": "$(hostname)",
    "base_backup": "$(basename "$last_backup")",
    "files_changed": $(find /opt/coding-swarm /etc/coding-swarm /home/swarm/projects -newer "$last_backup" -type f | wc -l),
    "size_bytes": $(du -sb "$backup_path" | cut -f1)
}
EOF
    
    log_backup "Incremental backup completed: $backup_path"
    return 0
}

restore_from_backup() {
    local backup_path="$1"
    local restore_type="${2:-full}"
    
    if [[ ! -d "$backup_path" ]] && [[ ! -f "$backup_path" ]]; then
        log_backup "Backup not found: $backup_path"
        return 1
    fi
    
    log_backup "Starting restore from: $backup_path"
    
    # Stop services before restore
    log_backup "Stopping services..."
    systemctl stop swarm-* 2>/dev/null || true
    
    # Decrypt if needed
    if [[ -f "$backup_path" ]] && [[ "$backup_path" =~ \.encrypted$ ]]; then
        if [[ -z "$ENCRYPTION_KEY" ]]; then
            log_backup "Encryption key required for restore"
            return 1
        fi
        
        local temp_dir="/tmp/restore-$$"
        mkdir -p "$temp_dir"
        
        openssl enc -aes-256-cbc -d -salt -k "$ENCRYPTION_KEY" \
            -in "$backup_path" | tar -xzf - -C "$temp_dir"
        
        backup_path="$temp_dir/$(basename "$backup_path" .encrypted)"
    fi
    
    # Restore configurations
    if [[ -f "$backup_path/configs.tar.gz" ]]; then
        log_backup "Restoring configurations..."
        tar -xzf "$backup_path/configs.tar.gz" -C /
    fi
    
    # Restore application
    if [[ -f "$backup_path/application.tar.gz" ]]; then
        log_backup "Restoring application..."
        tar -xzf "$backup_path/application.tar.gz" -C /
    fi
    
    # Restore projects
    if [[ -f "$backup_path/projects.tar.gz" ]]; then
        log_backup "Restoring projects..."
        tar -xzf "$backup_path/projects.tar.gz" -C /
    fi
    
    # Restore databases
    if [[ -d "$backup_path/databases" ]]; then
        log_backup "Restoring databases..."
        
        # Restore Redis
        if [[ -f "$backup_path/databases/redis.rdb" ]]; then
            systemctl stop redis-server 2>/dev/null || true
            cp "$backup_path/databases/redis.rdb" /var/lib/redis/dump.rdb
            chown redis:redis /var/lib/redis/dump.rdb
            systemctl start redis-server
        fi
        
        # Restore SQLite databases
        find "$backup_path/databases" -name "*.db" -exec cp {} /var/log/coding-swarm/ \; 2>/dev/null || true
    fi
    
    # Restore documentation
    if [[ -f "$backup_path/documentation.tar.gz" ]]; then
        log_backup "Restoring documentation..."
        tar -xzf "$backup_path/documentation.tar.gz" -C /
    fi
    
    # Fix permissions
    chown -R swarm:swarm /opt/coding-swarm /home/swarm
    chown -R swarm:swarm /var/log/coding-swarm
    
    # Reload systemd and start services
    systemctl daemon-reload
    systemctl start swarm-router swarm-orchestrator
    systemctl start swarm-agent-{laravel,react,flutter,testing}
    
    log_backup "Restore completed successfully"
    return 0
}

cleanup_old_backups() {
    log_backup "Cleaning up backups older than $RETENTION_DAYS days"
    
    find "$BACKUP_DIR" -type d -name "*-backup-*" -mtime +$RETENTION_DAYS -exec rm -rf {} \; 2>/dev/null || true
    find "$BACKUP_DIR" -type f -name "*-backup-*.encrypted" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
    
    local deleted_count
    deleted_count=$(find "$BACKUP_DIR" -name "*.log" -mtime +$RETENTION_DAYS -delete -print | wc -l)
    
    log_backup "Cleanup completed, removed $deleted_count old backup files"
}

# Main execution
case "${1:-backup}" in
    "backup"|"full")
        create_full_backup
        ;;
    "incremental")
        create_incremental_backup
        ;;
    "restore")
        if [[ -z "${2:-}" ]]; then
            echo "Usage: $0 restore <backup_path>"
            exit 1
        fi
        restore_from_backup "$2"
        ;;
    "cleanup")
        cleanup_old_backups
        ;;
    *)
        echo "Usage: $0 {backup|incremental|restore|cleanup}"
        exit 1
        ;;
esac
EOF
    
    chmod +x "$INSTALL_DIR/scripts/disaster-recovery.sh" || log_error "Failed to set executable permissions for disaster-recovery.sh"
    
    # Create backup schedule
    cat > /etc/cron.d/swarm-disaster-recovery << 'EOF'
# Disaster Recovery Backup Schedule

# Full backup weekly (Sunday 3 AM)
0 3 * * 0 root /opt/coding-swarm/scripts/disaster-recovery.sh full

# Incremental backup daily (3:30 AM)
30 3 * * 1-6 root /opt/coding-swarm/scripts/disaster-recovery.sh incremental

# Cleanup monthly (1st of month, 4 AM)
0 4 1 * * root /opt/coding-swarm/scripts/disaster-recovery.sh cleanup
EOF
    
    log_success "Disaster recovery system configured"
    return 0
}

# ============================================
# SECURITY HARDENING
# ============================================
apply_security_hardening() {
    log_info "Applying security hardening measures..."
    
    ensure_directory "$CONFIG_DIR/security"
    
    # Enhanced firewall rules
    log_info "Configuring enhanced firewall..."
    
    # Reset and configure UFW with advanced rules
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    
    # SSH with rate limiting
    ufw limit 22/tcp comment "SSH with rate limiting"
    
    # HTTP/HTTPS
    ufw allow 80/tcp comment "HTTP"
    ufw allow 443/tcp comment "HTTPS"
    
    # Internal services (localhost only)
    ufw allow from 127.0.0.1 to any port 8000 comment "Router API (localhost)"
    ufw allow from 127.0.0.1 to any port 9000 comment "Orchestrator API (localhost)"
    ufw allow from 127.0.0.1 to any port 8001:8004 comment "Agent APIs (localhost)"
    ufw allow from 127.0.0.1 to any port 6379 comment "Redis (localhost)"
    
    # Enable firewall
    echo "y" | ufw --force enable
    
    # Fail2ban configuration for additional protection
    if ! command -v fail2ban-client >/dev/null 2>&1; then
        log_info "Installing Fail2ban..."
        if apt-get update -qq && apt-get install -y -qq fail2ban; then
            log_success "Fail2ban installed"
        else
            log_error "Failed to install Fail2ban"
            return 1
        fi
    fi
    
    log_info "Configuring Fail2ban..."
        
    cat > /etc/fail2ban/jail.d/coding-swarm.conf << 'EOF'
[coding-swarm-api]
enabled = true
port = 80,443
filter = coding-swarm-api
logpath = /var/log/nginx/swarm-access.log
maxretry = 10
bantime = 3600
findtime = 600

[ssh]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 5
bantime = 3600
EOF
        
    cat > /etc/fail2ban/filter.d/coding-swarm-api.conf << 'EOF'
[Definition]
failregex = ^<HOST> - .* "(POST|GET|PUT|DELETE) .* HTTP/.*" (4[0-9][0-9]|5[0-9][0-9]) .*$
ignoreregex =
EOF
        
    systemctl enable --now fail2ban
    systemctl restart fail2ban
    
    # Secure file permissions
    log_info "Setting secure file permissions..."
    set_secure_permissions
    
    # SSH hardening
    log_info "Hardening SSH configuration..."
    
    backup_config "/etc/ssh/sshd_config"
    
    if ! grep -q "Coding Swarm Security Hardening" /etc/ssh/sshd_config; then
        cat >> /etc/ssh/sshd_config << 'EOF'

# Coding Swarm Security Hardening
Protocol 2
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
PermitEmptyPasswords no
ChallengeResponseAuthentication no
UsePAM yes
X11Forwarding no
PrintMotd no
ClientAliveInterval 300
ClientAliveCountMax 2
MaxAuthTries 3
MaxSessions 2
LoginGraceTime 60
EOF
    fi
    
    # Validate SSH config
    if sshd -t; then
        systemctl restart sshd
        log_success "SSH configuration hardened"
    else
        log_error "SSH configuration test failed, restoring backup"
        cp /etc/ssh/sshd_config.*.backup /etc/ssh/sshd_config  # Use the latest backup
    fi
    
    # System audit logging
    log_info "Configuring audit logging..."
    
    if ! command -v auditd >/dev/null 2>&1; then
        apt-get update -qq
        apt-get install -y -qq auditd audispd-plugins
    fi
    
    # Audit rules for security monitoring
    cat > /etc/audit/rules.d/coding-swarm.rules << 'EOF'
# Coding Swarm Security Audit Rules

# Monitor configuration changes
-w /etc/coding-swarm/ -p wa -k config_change
-w /opt/coding-swarm/ -p wa -k app_change
-w /etc/systemd/system/swarm- -p wa -k service_change

# Monitor authentication
-w /var/log/auth.log -p wa -k auth_change
-w /etc/passwd -p wa -k passwd_change
-w /etc/group -p wa -k group_change
-w /etc/shadow -p wa -k shadow_change

# Monitor privilege escalation
-a always,exit -F arch=b64 -S execve -F euid=0 -F auid>=1000 -F auid!=4294967295 -k privilege_escalation
-a always,exit -F arch=b32 -S execve -F euid=0 -F auid>=1000 -F auid!=4294967295 -k privilege_escalation

# Monitor network connections
-a always,exit -F arch=b64 -S socket -F a0=2 -k network_connect
-a always,exit -F arch=b32 -S socket -F a0=2 -k network_connect
EOF
    
    systemctl enable --now auditd
    
    # Security scanning script
    cat > "$INSTALL_DIR/scripts/security-scan.sh" << 'EOF'
#!/bin/bash
set -euo pipefail

# Security Scanning Script
SCAN_LOG="/var/log/coding-swarm/security-scan.log"

log_scan() {
    echo "[$(date -Iseconds)] $1" | tee -a "$SCAN_LOG"
}

check_file_permissions() {
    log_scan "Checking file permissions..."
    
    # Check for world-writable files
    local world_writable
    world_writable=$(find /opt/coding-swarm /etc/coding-swarm -type f -perm -002 2>/dev/null || true)
    
    if [[ -n "$world_writable" ]]; then
        log_scan "WARNING: World-writable files found:"
        echo "$world_writable" | while read -r file; do
            log_scan "  $file"
        done
    else
        log_scan "✓ No world-writable files found"
    fi
    
    # Check secret file permissions
    local secret_perms
    secret_perms=$(find /etc/coding-swarm/secrets -type f ! -perm 600 2>/dev/null || true)
    
    if [[ -n "$secret_perms" ]]; then
        log_scan "WARNING: Secret files with incorrect permissions:"
        echo "$secret_perms" | while read -r file; do
            log_scan "  $file"
        done
    else
        log_scan "✓ Secret file permissions correct"
    fi
}

check_open_ports() {
    log_scan "Checking open ports..."
    
    local open_ports
    open_ports=$(ss -tuln | grep LISTEN | awk '{print $5}' | sed 's/.*://' | sort -n | uniq)
    
    log_scan "Open ports:"
    echo "$open_ports" | while read -r port; do
        case "$port" in
            22) log_scan "  $port - SSH (expected)" ;;
            80) log_scan "  $port - HTTP (expected)" ;;
            443) log_scan "  $port - HTTPS (expected)" ;;
            6379) log_scan "  $port - Redis (localhost only)" ;;
            8000) log_scan "  $port - Router API (localhost only)" ;;
            8001|8002|8003|8004) log_scan "  $port - Agent API (localhost only)" ;;
            9000) log_scan "  $port - Orchestrator API (localhost only)" ;;
            *) log_scan "  $port - UNKNOWN (investigate)" ;;
        esac
    done
}

check_failed_logins() {
    log_scan "Checking for failed login attempts..."
    
    local failed_ssh
    failed_ssh=$(grep "Failed password" /var/log/auth.log | tail -10 | wc -l)
    
    if [[ $failed_ssh -gt 0 ]]; then
        log_scan "WARNING: $failed_ssh recent failed SSH attempts"
        grep "Failed password" /var/log/auth.log | tail -5 | while read -r line; do
            log_scan "  $line"
        done
    else
        log_scan "✓ No recent failed SSH attempts"
    fi
}

check_system_integrity() {
    log_scan "Checking system integrity..."
    
    # Check for suspicious processes
    local suspicious_procs
    suspicious_procs=$(ps aux | grep -E "(nc|netcat|nmap|wget.*\.(sh|py)|curl.*\.(sh|py))" | grep -v grep || true)
    
    if [[ -n "$suspicious_procs" ]]; then
        log_scan "WARNING: Suspicious processes found:"
        echo "$suspicious_procs" | while read -r proc; do
            log_scan "  $proc"
        done
    else
        log_scan "✓ No suspicious processes found"
    fi
    
    # Check disk usage for anomalies
    local disk_usage
    disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [[ $disk_usage -gt 90 ]]; then
        log_scan "WARNING: High disk usage: $disk_usage%"
    else
        log_scan "✓ Disk usage normal: $disk_usage%"
    fi
}

generate_security_report() {
    local report_file="/var/log/coding-swarm/security-report-$(date +%Y%m%d_%H%M).log"
    
    {
        echo "=== Coding Swarm Security Report ==="
        echo "Generated: $(date -Iseconds)"
        echo "Hostname: $(hostname)"
        echo
        
        echo "=== Recent Security Events ==="
        tail -20 "$SCAN_LOG" 2>/dev/null || echo "No recent events"
        
        echo
        echo "=== System Status ==="
        echo "Uptime: $(uptime | awk '{print $3,$4}' | sed 's/,//')"
        echo "Load: $(uptime | awk -F'load average:' '{print $2}')"
        echo "Failed logins (24h): $(grep "Failed password" /var/log/auth.log 2>/dev/null | wc -l || echo "0")"
        
        echo
        echo "=== Service Status ==="
        systemctl is-active swarm-router swarm-orchestrator nginx redis-server | \
            paste <(echo -e "Router\nOrchestrator\nNginx\nRedis") - | \
            column -t
        
        echo
        echo "=== Firewall Status ==="
        ufw status numbered 2>/dev/null || echo "UFW not configured"
        
    } > "$report_file"
    
    log_scan "Security report generated: $report_file"
}

# Main execution
main() {
    log_scan "Starting security scan..."
    
    check_file_permissions
    check_open_ports
    check_failed_logins
    check_system_integrity
    generate_security_report
    
    log_scan "Security scan completed"
}

main "$@"
EOF
    
    chmod +x "$INSTALL_DIR/scripts/security-scan.sh" || log_error "Failed to set executable permissions for security-scan.sh"
    
    # Add security scan to cron
    cat > /etc/cron.d/swarm-security << 'EOF'
# Security scanning
0 2 * * * root /opt/coding-swarm/scripts/security-scan.sh
EOF
    
    log_success "Security hardening completed"
    return 0
}

# ============================================
# DOCUMENTATION AND FINAL SETUP
# ============================================
generate_documentation() {
    log_info "Generating deployment documentation..."
    
    local doc_dir="$PROJECT_DIR/documentation"
    ensure_directory "$doc_dir"
    
    # Main README
    local router_key_masked=$(cat "$CONFIG_DIR/secrets/router.key" | head -c 8)****
    local local_key_masked=$(cat "$CONFIG_DIR/secrets/localmodel.key" | head -c 8)****
    
    cat > "$doc_dir/README.md" << EOF
# Coding Swarm Deployment Documentation

## Overview
This document contains comprehensive information about your Coding Swarm deployment.

**Deployment Details:**
- Version: 2.0.0
- Deployed: $(date -Iseconds)
- Hostname: $(hostname)
- Domain: ${DOMAIN:-$PUBLIC_IP}
- Production Mode: $PRODUCTION_MODE

## Quick Reference

### API Endpoints
- **Router API**: http://${DOMAIN:-$PUBLIC_IP}/v1/
- **Orchestrator API**: http://${DOMAIN:-$PUBLIC_IP}/api/
- **Health Check**: http://${DOMAIN:-$PUBLIC_IP}/health
- **Documentation**: http://${DOMAIN:-$PUBLIC_IP}/docs

### Authentication
- **API Key**: $router_key_masked
- **Local Model Key**: $local_key_masked

### Management Commands
\`\`\`bash
# System status
swarm status

# Submit task
swarm task "Create a user authentication system" laravel

# View logs
swarm logs orchestrator --follow

# Run tests
swarm test laravel-project

# Create backup
swarm backup --verify

# Monitor performance
swarm metrics --live
\`\`\`

## Architecture

### Services
1. **Router (LiteLLM)** - API gateway and load balancer
2. **Orchestrator** - Task management and coordination
3. **Agents** - Specialized AI agents for different technologies
   - Laravel Agent (Port 8001)
   - React Agent (Port 8002)
   - Flutter Agent (Port 8003)
   - Testing Agent (Port 8004)
4. **Nginx** - Web server and reverse proxy
5. **Redis** - Caching and session storage

### File Structure
\`\`\`
/opt/coding-swarm/         # Application installation
├── models/                # AI models
├── agents/                # Agent configurations
├── router/                # LiteLLM router
├── orchestrator/          # Task orchestrator
├── context/               # Code indexing
└── scripts/               # Management scripts

/etc/coding-swarm/         # Configuration
├── secrets/               # API keys and certificates
├── backup/                # Backup configuration
├── monitoring/            # Monitoring configuration
└── security/              # Security configuration

/var/log/coding-swarm/     # Logs and metrics
/home/swarm/projects/      # Project workspaces
/opt/backups/coding-swarm/ # Backup storage
\`\`\`

## Operations

### Service Management
\`\`\`bash
# Start all services
systemctl start swarm-router swarm-orchestrator
systemctl start swarm-agent-{laravel,react,flutter,testing}

# Check service status
systemctl status swarm-*

# View service logs
journalctl -u swarm-router -f
\`\`\`

### Backup and Recovery
\`\`\`bash
# Create full backup
/opt/coding-swarm/scripts/disaster-recovery.sh full

# Create incremental backup
/opt/coding-swarm/scripts/disaster-recovery.sh incremental

# Restore from backup
/opt/coding-swarm/scripts/disaster-recovery.sh restore /path/to/backup

# Cleanup old backups
/opt/coding-swarm/scripts/disaster-recovery.sh cleanup
\`\`\`

### Monitoring
\`\`\`bash
# Real-time dashboard
/opt/coding-swarm/scripts/dashboard.sh

# Security scan
/opt/coding-swarm/scripts/security-scan.sh

# Performance monitoring
/opt/coding-swarm/scripts/advanced-monitor.sh
\`\`\`

## Troubleshooting

### Common Issues

1. **Service Won't Start**
   \`\`\`bash
   # Check service status
   systemctl status swarm-router
   
   # View logs
   journalctl -u swarm-router -n 50
   
   # Restart with dependencies
   swarm restart all
   \`\`\`

2. **API Not Responding**
   \`\`\`bash
   # Check nginx status
   systemctl status nginx
   
   # Test direct connection
   curl -H "Authorization: Bearer \$(cat /etc/coding-swarm/secrets/router.key)" \\
        http://127.0.0.1:8000/v1/models
   \`\`\`

3. **High Resource Usage**
   \`\`\`bash
   # Check system resources
   swarm metrics
   
   # View process usage
   htop
   
   # Check Docker containers
   docker stats
   \`\`\`

### Log Locations
- System logs: \`/var/log/coding-swarm/\`
- Service logs: \`journalctl -u swarm-*\`
- Nginx logs: \`/var/log/nginx/swarm-*.log\`
- Security logs: \`/var/log/coding-swarm/security-*.log\`

## Development

### VS Code Integration
1. Install the Continue extension
2. Configuration is at: \`$PROJECT_DIR/.continue/config.json\`
3. API endpoint: \`http://${DOMAIN:-$PUBLIC_IP}/v1\`
4. API key: \`$(cat "$CONFIG_DIR/secrets/router.key")\`

### GitHub Actions
CI/CD workflow is configured at: \`$PROJECT_DIR/.github/workflows/swarm-ci.yml\`

Set these repository secrets:
- \`SWARM_ROUTER_KEY\`: $(cat "$CONFIG_DIR/secrets/router.key")
- \`SWARM_DOMAIN\`: ${DOMAIN:-$PUBLIC_IP}

### Local Development
\`\`\`bash
# Start development environment
cd $PROJECT_DIR
docker-compose -f docker-compose.dev.yml up -d

# Setup project dependencies
./scripts/dev-setup.sh
\`\`\`

## Security

### Firewall Configuration
\`\`\`bash
# View current rules
ufw status numbered

# Add custom rule
ufw allow from [IP] to any port [PORT]
\`\`\`

### SSL Certificate (if configured)
- Certificate: \`/etc/letsencrypt/live/${DOMAIN:-example.com}/fullchain.pem\`
- Private key: \`/etc/letsencrypt/live/${DOMAIN:-example.com}/privkey.pem\`
- Auto-renewal: Configured via cron

### Security Monitoring
- Fail2ban: Monitors and blocks suspicious activity
- Audit logs: System events logged to \`/var/log/audit/\`
- Security scans: Automated daily scans

## Scaling and Performance

### Horizontal Scaling
To add more agent instances:
1. Update Docker Compose configuration
2. Add new upstream servers in Nginx
3. Update LiteLLM router configuration

### Performance Optimization
- Nginx: Configured with compression and caching
- System: Optimized kernel parameters applied
- Services: Resource limits and CPU affinity set

### Monitoring Metrics
- System metrics: CPU, memory, disk, network
- Service metrics: Response times, error rates, throughput
- Application metrics: Task queue, active sessions

## Maintenance

### Regular Tasks
- **Daily**: Automated backups and log rotation
- **Weekly**: Security scans and updates
- **Monthly**: Performance review and optimization

### Update Procedure
1. Create backup: \`swarm backup --verify\`
2. Stop services: \`systemctl stop swarm-*\`
3. Update application files
4. Test configuration: \`nginx -t\`
5. Start services: \`systemctl start swarm-*\`
6. Verify deployment: \`swarm health --detailed\`

### Health Checks
\`\`\`bash
# Comprehensive health check
swarm health --detailed

# Quick status
swarm status

# Performance metrics
swarm metrics
\`\`\`

## Support and Resources

### Documentation Links
- API Documentation: http://${DOMAIN:-$PUBLIC_IP}/docs
- Continue.dev Guide: https://continue.dev/docs
- LiteLLM Documentation: https://docs.litellm.ai/

### Log Analysis
\`\`\`bash
# Find errors in logs
grep -i error /var/log/coding-swarm/*.log

# Monitor real-time logs
tail -f /var/log/coding-swarm/*.log

# Search specific timeframe
journalctl --since "1 hour ago" -u swarm-*
\`\`\`

### Performance Tuning
- Adjust worker processes in \`/etc/nginx/nginx.conf\`
- Modify service resource limits in systemd files
- Configure AI model parameters in agent startup scripts

---

**Generated**: $(date -Iseconds)  
**Version**: 2.0.0  
**Hostname**: $(hostname)
EOF

    # API Reference
    cat > "$doc_dir/API_REFERENCE.md" << 'EOF'
# Coding Swarm API Reference

## Authentication
All API requests require an Authorization header: