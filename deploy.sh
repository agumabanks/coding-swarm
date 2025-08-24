# FILE: /opt/coding-swarm/deploy.sh
#!/bin/bash
set -euo pipefail

# Configuration variables
DOMAIN="${DOMAIN:-}"
PUBLIC_IP="${PUBLIC_IP:-}"
OPENAI_API_KEY="${OPENAI_API_KEY:-}"

# Paths
INSTALL_DIR="/opt/coding-swarm"
CONFIG_DIR="/etc/coding-swarm"
LOG_DIR="/var/log/coding-swarm"
PROJECT_DIR="/home/swarm/projects"

# Create system user and directories
create_system() {
    id -u swarm &>/dev/null || useradd -r -s /bin/bash -m -d /home/swarm swarm
    usermod -aG docker swarm 2>/dev/null || true
    
    mkdir -p "$INSTALL_DIR"/{models,agents,router,orchestrator,context,scripts}
    mkdir -p "$CONFIG_DIR"/secrets
    mkdir -p "$LOG_DIR"/{agents,orchestrator}
    mkdir -p "$PROJECT_DIR"
    
    chown -R swarm:swarm "$INSTALL_DIR" "$LOG_DIR" "$PROJECT_DIR"
    chmod 700 "$CONFIG_DIR"/secrets
}

# Install dependencies
install_deps() {
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y \
        docker.io docker-compose-plugin \
        redis-server nginx \
        jq yq git curl unzip \
        ripgrep universal-ctags sqlite3 \
        python3-venv nodejs npm \
        php8.2 php8.2-cli php8.2-common php8.2-mbstring php8.2-xml composer
    
    # Install Flutter SDK
    if [ ! -d /opt/flutter ]; then
        cd /opt
        wget -q https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_3.16.5-stable.tar.xz
        tar xf flutter_linux_3.16.5-stable.tar.xz
        ln -sf /opt/flutter/flutter/bin/flutter /usr/local/bin/flutter
    fi
    
    systemctl enable --now redis-server docker
}

# Download model
download_model() {
    mkdir -p "$INSTALL_DIR/models"
    cd "$INSTALL_DIR/models"
    
    if [ ! -f "qwen2.5-coder-7b-instruct-q4_k_m.gguf" ]; then
        echo "Downloading Qwen2.5-Coder-7B model..."
        wget -q --show-progress \
            https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/qwen2.5-coder-7b-instruct-q4_k_m.gguf
    fi
    
    chown swarm:swarm *.gguf
}

# Generate secrets
generate_secrets() {
    if [ ! -f "$CONFIG_DIR/secrets/router.key" ]; then
        openssl rand -hex 32 > "$CONFIG_DIR/secrets/router.key"
    fi
    
    if [ ! -f "$CONFIG_DIR/secrets/localmodel.key" ]; then
        openssl rand -hex 32 > "$CONFIG_DIR/secrets/localmodel.key"
    fi
    
    chmod 600 "$CONFIG_DIR/secrets"/*.key
    chown swarm:swarm "$CONFIG_DIR/secrets"/*.key
}

# Main execution
create_system
install_deps
download_model
generate_secrets

# Install Python packages in venv
python3 -m venv "$INSTALL_DIR/orchestrator/venv"
"$INSTALL_DIR/orchestrator/venv/bin/pip" install -q \
    litellm fastapi uvicorn requests aiofiles gitpython \
    sqlite-vec sentence-transformers

echo "Deploy script completed. Creating configuration files..."

# FILE: /opt/coding-swarm/router/config.yaml
general_settings:
  master_key: os.environ/SWARM_API_KEY

model_list:
  - model_name: laravel-agent
    litellm_params:
      model: openai/laravel
      custom_llm_provider: openai
      api_base: http://127.0.0.1:8001/v1
      api_key: os.environ/LOCAL_MODEL_KEY
      
  - model_name: react-agent
    litellm_params:
      model: openai/react
      custom_llm_provider: openai
      api_base: http://127.0.0.1:8002/v1
      api_key: os.environ/LOCAL_MODEL_KEY
      
  - model_name: flutter-agent
    litellm_params:
      model: openai/flutter
      custom_llm_provider: openai
      api_base: http://127.0.0.1:8003/v1
      api_key: os.environ/LOCAL_MODEL_KEY
      
  - model_name: testing-agent
    litellm_params:
      model: openai/testing
      custom_llm_provider: openai
      api_base: http://127.0.0.1:8004/v1
      api_key: os.environ/LOCAL_MODEL_KEY
      
  - model_name: gpt-5-codex
    litellm_params:
      model: gpt-4
      api_key: os.environ/OPENAI_API_KEY

# FILE: /opt/coding-swarm/router/start.sh
#!/bin/bash
export SWARM_API_KEY=$(cat /etc/coding-swarm/secrets/router.key)
export LOCAL_MODEL_KEY=$(cat /etc/coding-swarm/secrets/localmodel.key)
[ -n "$OPENAI_API_KEY" ] && export OPENAI_API_KEY
cd /opt/coding-swarm/router
exec /opt/coding-swarm/orchestrator/venv/bin/litellm \
    --config config.yaml \
    --host 0.0.0.0 \
    --port 8000

# FILE: /opt/coding-swarm/agents/laravel_prompt.txt
You are a Laravel/PHP specialist. Output only unified diffs.
Focus: RESTful APIs, Eloquent models, migrations, authentication, testing with Pest.
Always use proper error handling and follow Laravel conventions.

# FILE: /opt/coding-swarm/agents/react_prompt.txt
You are a React/TypeScript specialist. Output only unified diffs.
Focus: Component architecture, hooks, state management, API integration, Vitest testing.
Follow React best practices and modern patterns.

# FILE: /opt/coding-swarm/agents/flutter_prompt.txt
You are a Flutter/Dart specialist. Output only unified diffs.
Focus: Widget composition, state management, platform integration, Flutter testing.
Follow Flutter conventions and Material Design guidelines.

# FILE: /opt/coding-swarm/agents/testing_prompt.txt
You are a testing/QA specialist. Output only unified diffs.
Focus: Unit tests, integration tests, e2e tests, test coverage, CI/CD.
Generate comprehensive test suites with edge cases.

# FILE: /opt/coding-swarm/agents/start_laravel.sh
#!/bin/bash
LOCAL_KEY=$(cat /etc/coding-swarm/secrets/localmodel.key)
exec docker run --rm \
    --name swarm-agent-laravel \
    -v /opt/coding-swarm/models:/models:ro \
    -v /opt/coding-swarm/agents:/prompts:ro \
    -p 127.0.0.1:8001:8080 \
    ghcr.io/ggerganov/llama.cpp:server \
    -m /models/qwen2.5-coder-7b-instruct-q4_k_m.gguf \
    --host 0.0.0.0 \
    --port 8080 \
    --api-key "$LOCAL_KEY" \
    --ctx-size 8192 \
    --threads $(($(nproc)/2)) \
    --parallel 2 \
    --system-prompt-file /prompts/laravel_prompt.txt \
    2>&1 | tee -a /var/log/coding-swarm/agents/laravel.log

# FILE: /opt/coding-swarm/agents/start_react.sh
#!/bin/bash
LOCAL_KEY=$(cat /etc/coding-swarm/secrets/localmodel.key)
exec docker run --rm \
    --name swarm-agent-react \
    -v /opt/coding-swarm/models:/models:ro \
    -v /opt/coding-swarm/agents:/prompts:ro \
    -p 127.0.0.1:8002:8080 \
    ghcr.io/ggerganov/llama.cpp:server \
    -m /models/qwen2.5-coder-7b-instruct-q4_k_m.gguf \
    --host 0.0.0.0 \
    --port 8080 \
    --api-key "$LOCAL_KEY" \
    --ctx-size 8192 \
    --threads $(($(nproc)/2)) \
    --parallel 2 \
    --system-prompt-file /prompts/react_prompt.txt \
    2>&1 | tee -a /var/log/coding-swarm/agents/react.log

# FILE: /opt/coding-swarm/agents/start_flutter.sh
#!/bin/bash
LOCAL_KEY=$(cat /etc/coding-swarm/secrets/localmodel.key)
exec docker run --rm \
    --name swarm-agent-flutter \
    -v /opt/coding-swarm/models:/models:ro \
    -v /opt/coding-swarm/agents:/prompts:ro \
    -p 127.0.0.1:8003:8080 \
    ghcr.io/ggerganov/llama.cpp:server \
    -m /models/qwen2.5-coder-7b-instruct-q4_k_m.gguf \
    --host 0.0.0.0 \
    --port 8080 \
    --api-key "$LOCAL_KEY" \
    --ctx-size 8192 \
    --threads $(($(nproc)/2)) \
    --parallel 2 \
    --system-prompt-file /prompts/flutter_prompt.txt \
    2>&1 | tee -a /var/log/coding-swarm/agents/flutter.log

# FILE: /opt/coding-swarm/agents/start_testing.sh
#!/bin/bash
LOCAL_KEY=$(cat /etc/coding-swarm/secrets/localmodel.key)
exec docker run --rm \
    --name swarm-agent-testing \
    -v /opt/coding-swarm/models:/models:ro \
    -v /opt/coding-swarm/agents:/prompts:ro \
    -p 127.0.0.1:8004:8080 \
    ghcr.io/ggerganov/llama.cpp:server \
    -m /models/qwen2.5-coder-7b-instruct-q4_k_m.gguf \
    --host 0.0.0.0 \
    --port 8080 \
    --api-key "$LOCAL_KEY" \
    --ctx-size 8192 \
    --threads $(($(nproc)/2)) \
    --parallel 2 \
    --system-prompt-file /prompts/testing_prompt.txt \
    2>&1 | tee -a /var/log/coding-swarm/agents/testing.log

# FILE: /opt/coding-swarm/orchestrator/main.py
#!/usr/bin/env python3
import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

import requests
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Coding Swarm Orchestrator")

class TaskRequest(BaseModel):
    description: str
    project_type: str = "laravel"
    context_files: List[str] = []

ROUTER_URL = "http://127.0.0.1:8000/v1/chat/completions"
ROUTER_KEY = None

def load_router_key():
    global ROUTER_KEY
    with open("/etc/coding-swarm/secrets/router.key", "r") as f:
        ROUTER_KEY = f.read().strip()

def get_agent_prompt(agent_type: str) -> str:
    prompt_file = f"/opt/coding-swarm/agents/{agent_type}_prompt.txt"
    with open(prompt_file, "r") as f:
        return f.read()

def build_context(project_path: Path, context_files: List[str]) -> str:
    context = []
    for file_path in context_files:
        full_path = project_path / file_path
        if full_path.exists() and full_path.stat().st_size < 50000:
            try:
                content = full_path.read_text()
                # Escape JSON properly
                content = json.dumps(content)
                context.append(f"File: {file_path}\n{content}")
            except Exception as e:
                logger.warning(f"Could not read {file_path}: {e}")
    return "\n".join(context)

async def call_agent(agent_type: str, task: str, context: str = "") -> Dict:
    system_prompt = get_agent_prompt(agent_type)
    
    user_message = f"Task: {task}"
    if context:
        user_message += f"\n\nContext:\n{context}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    headers = {"Authorization": f"Bearer {ROUTER_KEY}"}
    
    try:
        response = requests.post(
            ROUTER_URL,
            json={
                "model": f"{agent_type}-agent",
                "messages": messages,
                "max_tokens": 4000,
                "temperature": 0.3
            },
            headers=headers,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "content": result["choices"][0]["message"]["content"]
            }
        else:
            return {
                "success": False,
                "error": f"Agent returned {response.status_code}"
            }
    except Exception as e:
        return {"success": False, "error": str(e)}

def apply_patch(patch_content: str, project_path: Path) -> bool:
    try:
        patch_file = Path("/tmp") / f"patch_{os.getpid()}.patch"
        patch_file.write_text(patch_content)
        
        # Try git apply with 3-way merge first
        result = subprocess.run(
            ["git", "apply", "--3way", "--reject", str(patch_file)],
            cwd=project_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # Fallback to patch command
            result = subprocess.run(
                ["patch", "-p0"],
                input=patch_content,
                cwd=project_path,
                capture_output=True,
                text=True
            )
        
        if result.returncode == 0:
            # Commit changes
            subprocess.run(["git", "add", "."], cwd=project_path)
            subprocess.run(
                ["git", "commit", "-m", "AI: Applied patch"],
                cwd=project_path
            )
            return True
            
        patch_file.unlink()
        return False
    except Exception as e:
        logger.error(f"Patch application failed: {e}")
        return False

@app.on_event("startup")
async def startup():
    load_router_key()

@app.get("/api/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/tasks")
async def submit_task(task: TaskRequest, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    token = authorization.replace("Bearer ", "")
    if token != ROUTER_KEY:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    project_path = Path(f"/home/swarm/projects/{task.project_type}-project")
    context = build_context(project_path, task.context_files)
    
    result = await call_agent(task.project_type, task.description, context)
    
    if result["success"] and result.get("content"):
        patch_applied = apply_patch(result["content"], project_path)
        result["patch_applied"] = patch_applied
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9000)

# FILE: /opt/coding-swarm/context/indexer.py
#!/usr/bin/env python3
import sqlite3
import subprocess
from pathlib import Path
import sys

sys.path.insert(0, "/opt/coding-swarm/orchestrator/venv/lib/python3.*/site-packages")

class CodebaseIndexer:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.db_path = self.project_path / ".swarm" / "context.db"
        self.db_path.parent.mkdir(exist_ok=True, parents=True)
    
    def run_ctags(self):
        ctags_file = self.project_path / ".swarm" / "tags"
        subprocess.run([
            "ctags", "-R",
            "--exclude=node_modules",
            "--exclude=vendor",
            "--exclude=.git",
            f"-f={ctags_file}",
            str(self.project_path)
        ])
    
    def index_files(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY,
                file_path TEXT UNIQUE,
                content TEXT,
                file_type TEXT,
                last_modified REAL
            )
        """)
        
        extensions = {'.php', '.js', '.ts', '.tsx', '.dart', '.py', '.json', '.yaml'}
        
        for file_path in self.project_path.rglob("*"):
            if (file_path.suffix in extensions and 
                file_path.stat().st_size < 100000 and
                'node_modules' not in str(file_path) and
                'vendor' not in str(file_path)):
                
                try:
                    content = file_path.read_text()
                    rel_path = str(file_path.relative_to(self.project_path))
                    
                    conn.execute("""
                        INSERT OR REPLACE INTO files 
                        (file_path, content, file_type, last_modified)
                        VALUES (?, ?, ?, ?)
                    """, (rel_path, content, file_path.suffix, file_path.stat().st_mtime))
                except Exception as e:
                    print(f"Error indexing {file_path}: {e}")
        
        conn.commit()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        indexer = CodebaseIndexer(sys.argv[1])
        indexer.run_ctags()
        indexer.index_files()
        print(f"Indexed {sys.argv[1]}")

# FILE: /etc/nginx/sites-available/coding-swarm
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=60r/m;
limit_req_zone $binary_remote_addr zone=orchestrator_limit:10m rate=10r/m;

server {
    listen 80;
    server_name _;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Router API
    location /v1/ {
        limit_req zone=api_limit burst=20 nodelay;
        
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }
    
    # Orchestrator API
    location /api/ {
        limit_req zone=orchestrator_limit burst=5 nodelay;
        
        proxy_pass http://127.0.0.1:9000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 600s;
    }
    
    # Health check
    location /health {
        access_log off;
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }
}

# FILE: /etc/systemd/system/swarm-agent-laravel.service
[Unit]
Description=Swarm Laravel Agent
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=swarm
Group=swarm
WorkingDirectory=/opt/coding-swarm/agents
ExecStart=/opt/coding-swarm/agents/start_laravel.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# FILE: /etc/systemd/system/swarm-agent-react.service
[Unit]
Description=Swarm React Agent
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=swarm
Group=swarm
WorkingDirectory=/opt/coding-swarm/agents
ExecStart=/opt/coding-swarm/agents/start_react.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# FILE: /etc/systemd/system/swarm-agent-flutter.service
[Unit]
Description=Swarm Flutter Agent
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=swarm
Group=swarm
WorkingDirectory=/opt/coding-swarm/agents
ExecStart=/opt/coding-swarm/agents/start_flutter.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# FILE: /etc/systemd/system/swarm-agent-testing.service
[Unit]
Description=Swarm Testing Agent
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=swarm
Group=swarm
WorkingDirectory=/opt/coding-swarm/agents
ExecStart=/opt/coding-swarm/agents/start_testing.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# FILE: /etc/systemd/system/swarm-router.service
[Unit]
Description=Swarm LiteLLM Router
After=network.target swarm-agent-laravel.service swarm-agent-react.service

[Service]
Type=simple
User=swarm
Group=swarm
WorkingDirectory=/opt/coding-swarm/router
ExecStart=/opt/coding-swarm/router/start.sh
Restart=always
RestartSec=10
Environment=PATH=/opt/coding-swarm/orchestrator/venv/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target

# FILE: /etc/systemd/system/swarm-orchestrator.service
[Unit]
Description=Swarm Orchestrator
After=network.target swarm-router.service redis.service

[Service]
Type=simple
User=swarm
Group=swarm
WorkingDirectory=/opt/coding-swarm/orchestrator
ExecStart=/opt/coding-swarm/orchestrator/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# FILE: /etc/logrotate.d/coding-swarm
/var/log/coding-swarm/*.log /var/log/coding-swarm/*/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    create 0640 swarm swarm
}

# FILE: /opt/coding-swarm/scripts/monitor.sh
#!/bin/bash
LOG_FILE="/var/log/coding-swarm/monitor.log"

check_service() {
    local service=$1
    if systemctl is-active --quiet "$service"; then
        echo "[$(date -Iseconds)] ✓ $service running" >> "$LOG_FILE"
    else
        echo "[$(date -Iseconds)] ✗ $service down, restarting..." >> "$LOG_FILE"
        systemctl restart "$service"
    fi
}

# Check all services
for service in swarm-router swarm-orchestrator swarm-agent-{laravel,react,flutter,testing}; do
    check_service "$service"
done

# Log system resources
echo "[$(date -Iseconds)] CPU: $(uptime | awk -F'load average:' '{print $2}')" >> "$LOG_FILE"
echo "[$(date -Iseconds)] MEM: $(free -h | awk 'NR==2{print $3"/"$2}')" >> "$LOG_FILE"

# FILE: /opt/coding-swarm/scripts/backup.sh
#!/bin/bash
BACKUP_DIR="/opt/backups/coding-swarm"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup projects
tar -czf "$BACKUP_DIR/projects_$DATE.tar.gz" \
    -C /home/swarm \
    --exclude="*/node_modules" \
    --exclude="*/vendor" \
    projects/

# Backup configs
tar -czf "$BACKUP_DIR/configs_$DATE.tar.gz" \
    /etc/coding-swarm/ \
    /opt/coding-swarm/router/config.yaml \
    /opt/coding-swarm/agents/

# Clean old backups (30 days)
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

# FILE: /usr/local/bin/swarm
#!/bin/bash
set -euo pipefail

ROUTER_KEY=$(cat /etc/coding-swarm/secrets/router.key 2>/dev/null || echo "")
SWARM_API="http://127.0.0.1:9000/api"
ROUTER_API="http://127.0.0.1:8000/v1"

case "${1:-}" in
    task)
        if [ $# -lt 2 ]; then
            echo "Usage: swarm task \"description\" [project_type]"
            exit 1
        fi
        
        curl -s -X POST "$SWARM_API/tasks" \
            -H "Authorization: Bearer $ROUTER_KEY" \
            -H "Content-Type: application/json" \
            -d "{
                \"description\": \"$2\",
                \"project_type\": \"${3:-laravel}\"
            }" | jq .
        ;;
        
    status)
        echo "=== Swarm Status ==="
        for service in swarm-router swarm-orchestrator swarm-agent-{laravel,react,flutter,testing}; do
            if systemctl is-active --quiet "$service"; then
                echo "✓ $service: running"
            else
                echo "✗ $service: stopped"
            fi
        done
        
        echo ""
        echo "=== System Resources ==="
        echo "CPU Load: $(uptime | awk -F'load average:' '{print $2}')"
        echo "Memory: $(free -h | awk 'NR==2{print $3"/"$2" ("int($3/$2*100)"%)"}')"
        ;;
        
    logs)
        service="${2:-orchestrator}"
        case "$service" in
            laravel|react|flutter|testing)
                tail -f "/var/log/coding-swarm/agents/${service}.log"
                ;;
            orchestrator|router)
                journalctl -u "swarm-${service}" -f
                ;;
            *)
                echo "Unknown service: $service"
                exit 1
                ;;
        esac
        ;;
        
    restart)
        service="${2:-all}"
        if [ "$service" = "all" ]; then
            systemctl restart swarm-router swarm-orchestrator
            systemctl restart swarm-agent-{laravel,react,flutter,testing}
            echo "All services restarted"
        else
            systemctl restart "swarm-${service}"
            echo "Service swarm-${service} restarted"
        fi
        ;;
        
    index)
        project="${2:-}"
        if [ -z "$project" ]; then
            echo "Usage: swarm index <project>"
            exit 1
        fi
        
        project_path="/home/swarm/projects/${project}"
        if [ -d "$project_path" ]; then
            /opt/coding-swarm/orchestrator/venv/bin/python \
                /opt/coding-swarm/context/indexer.py "$project_path"
            echo "Indexed $project"
        else
            echo "Project not found: $project"
            exit 1
        fi
        ;;
        
    test)
        project="${2:-}"
        if [ -z "$project" ]; then
            echo "Usage: swarm test <project>"
            exit 1
        fi
        
        project_path="/home/swarm/projects/${project}"
        if [ ! -d "$project_path" ]; then
            echo "Project not found: $project"
            exit 1
        fi
        
        case "$project" in
            *laravel*|*api*)
                docker run --rm --network none \
                    -v "$project_path:/app" \
                    -w /app \
                    php:8.2-cli \
                    bash -c "composer install && php artisan test"
                ;;
            *react*|*web*)
                docker run --rm --network none \
                    -v "$project_path:/app" \
                    -w /app \
                    node:20 \
                    bash -c "npm ci && npm test -- --watch=false"
                ;;
            *flutter*|*mobile*)
                docker run --rm --network none \
                    -v "$project_path:/app" \
                    -w /app \
                    cirrusci/flutter:stable \
                    bash -c "flutter pub get && flutter test"
                ;;
            *)
                echo "Unknown project type"
                exit 1
                ;;
        esac
        ;;
        
    *)
        echo "Usage: swarm {task|status|logs|restart|index|test} [args]"
        exit 1
        ;;
esac

# FILE: /home/swarm/projects/.continue/config.json
{
  "models": [
    {
      "title": "Laravel Agent",
      "provider": "openai",
      "model": "laravel-agent",
      "apiBase": "http://127.0.0.1/v1",
      "apiKey": "ROUTER_KEY_PLACEHOLDER"
    },
    {
      "title": "React Agent",
      "provider": "openai",
      "model": "react-agent",
      "apiBase": "http://127.0.0.1/v1",
      "apiKey": "ROUTER_KEY_PLACEHOLDER"
    },
    {
      "title": "Flutter Agent",
      "provider": "openai",
      "model": "flutter-agent",
      "apiBase": "http://127.0.0.1/v1",
      "apiKey": "ROUTER_KEY_PLACEHOLDER"
    }
  ],
  "tabAutocompleteModel": {
    "title": "Swarm Autocomplete",
    "provider": "openai",
    "model": "laravel-agent",
    "apiBase": "http://127.0.0.1/v1",
    "apiKey": "ROUTER_KEY_PLACEHOLDER"
  },
  "embeddingsProvider": {
    "provider": "transformers.js"
  }
}

# FILE: /opt/coding-swarm/deploy-finalize.sh
#!/bin/bash
# Final deployment steps - run after creating all files above

set -euo pipefail

echo "Finalizing Coding Swarm deployment..."

# Make all scripts executable
chmod +x /opt/coding-swarm/deploy.sh
chmod +x /opt/coding-swarm/router/start.sh
chmod +x /opt/coding-swarm/agents/start_*.sh
chmod +x /opt/coding-swarm/orchestrator/main.py
chmod +x /opt/coding-swarm/context/indexer.py
chmod +x /opt/coding-swarm/scripts/*.sh
chmod +x /usr/local/bin/swarm

# Set proper ownership
chown -R swarm:swarm /opt/coding-swarm
chown -R swarm:swarm /home/swarm
chown swarm:swarm /usr/local/bin/swarm

# Configure UFW firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Enable and configure nginx
ln -sf /etc/nginx/sites-available/coding-swarm /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# Setup cron jobs
echo "*/5 * * * * root /opt/coding-swarm/scripts/monitor.sh" > /etc/cron.d/swarm-monitor
echo "0 2 * * * root /opt/coding-swarm/scripts/backup.sh" > /etc/cron.d/swarm-backup

# Initialize git repos in project directories
for project in laravel-project react-project flutter-project; do
    mkdir -p "/home/swarm/projects/$project"
    cd "/home/swarm/projects/$project"
    sudo -u swarm git init
    sudo -u swarm git config user.email "swarm@localhost"
    sudo -u swarm git config user.name "Coding Swarm"
done

# Update Continue config with actual router key
ROUTER_KEY=$(cat /etc/coding-swarm/secrets/router.key)
sed -i "s/ROUTER_KEY_PLACEHOLDER/$ROUTER_KEY/g" /home/swarm/projects/.continue/config.json

# Reload systemd and start services
systemctl daemon-reload

# Start services in order
systemctl start redis-server
sleep 2

echo "Starting agent services..."
systemctl start swarm-agent-laravel
systemctl start swarm-agent-react
systemctl start swarm-agent-flutter
systemctl start swarm-agent-testing
sleep 10

echo "Starting router service..."
systemctl start swarm-router
sleep 5

echo "Starting orchestrator service..."
systemctl start swarm-orchestrator
sleep 3

# Enable services for auto-start
systemctl enable swarm-agent-laravel swarm-agent-react swarm-agent-flutter swarm-agent-testing
systemctl enable swarm-router swarm-orchestrator

# Print deployment summary
echo ""
echo "=========================================="
echo "✅ CODING SWARM DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
echo "📍 Router Endpoint:"
echo "   Base URL: http://${DOMAIN:-$(hostname -I | awk '{print $1}')}/v1"
echo "   API Key: $ROUTER_KEY"
echo ""
echo "📋 Example Commands:"
echo ""
echo "1. Test router connectivity:"
echo "   curl -H \"Authorization: Bearer $ROUTER_KEY\" \\"
echo "        http://127.0.0.1/v1/models"
echo ""
echo "2. Submit a full-stack task:"
echo "   swarm task \"Scaffold a blog CRUD with API, React UI, and Flutter mobile app\""
echo ""
echo "3. Check system status:"
echo "   swarm status"
echo ""
echo "4. View logs:"
echo "   swarm logs orchestrator"
echo ""
echo "📂 Project Directories:"
echo "   /home/swarm/projects/laravel-project"
echo "   /home/swarm/projects/react-project"
echo "   /home/swarm/projects/flutter-project"
echo ""
echo "🔧 VS Code Integration:"
echo "   Continue config: /home/swarm/projects/.continue/config.json"
echo "   API Base: http://${DOMAIN:-127.0.0.1}/v1"
echo "   API Key: $ROUTER_KEY"
echo ""
echo "�� Your AI coding swarm is ready for production!"

# FILE: /home/swarm/projects/.github/workflows/swarm.yml
name: Swarm CI/CD
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  swarm-task:
    runs-on: ubuntu-latest
    if: ${{ secrets.SWARM_ROUTER_KEY != '' }}
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Trigger Swarm Task
        env:
          SWARM_KEY: ${{ secrets.SWARM_ROUTER_KEY }}
          DOMAIN: ${{ vars.SWARM_DOMAIN || '127.0.0.1' }}
        run: |
          response=$(curl -s -X POST "https://${DOMAIN}/api/tasks" \
            -H "Authorization: Bearer ${SWARM_KEY}" \
            -H "Content-Type: application/json" \
            -d '{
              "description": "Run tests and check code quality",
              "project_type": "testing",
              "context_files": []
            }')
          
          echo "$response" | jq .
          
          if echo "$response" | jq -e '.success == false' > /dev/null; then
            echo "Swarm task failed"
            exit 1
          fi
      
      - name: Run Project Tests
        if: always()
        run: |
          # Detect project type and run appropriate tests
          if [ -f "composer.json" ]; then
            composer install
            ./vendor/bin/pest || php artisan test
          elif [ -f "package.json" ]; then
            npm ci
            npm test -- --watch=false
          elif [ -f "pubspec.yaml" ]; then
            flutter pub get
            flutter test
          fi
