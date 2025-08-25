#!/usr/bin/env bash
# cswarm-project.sh — clone a repo, plan/code/test in a loop using your local llama.cpp agent,
# apply unified-diff patches, commit, and optionally push.
# Requires: docker up with llama.cpp server, curl, jq, git.

set -euo pipefail

# ---------------- Config (override by env/flags) ----------------
API_BASE="${API_BASE:-http://127.0.0.1:8080/v1}"   # llama.cpp OpenAI-compatible base
MODEL_NAME="${MODEL_NAME:-qwen2.5-coder-7b-instruct-q4_k_m}" # label only; llama.cpp uses loaded model
WORK_ROOT="${WORK_ROOT:-/home/swarm/projects}"
MAX_ITERS="${MAX_ITERS:-5}"
BRANCH_PREFIX="${BRANCH_PREFIX:-swarm/auto}"
COMMIT_PREFIX="${COMMIT_PREFIX:-AI:}"
PUSH="${PUSH:-false}"
PORTS=(8080 8081 8082 8083)
API_PORT="${API_PORT:-9101}"         # your swarm-api (not used for patching, only health print)
NGINX_HOST="${NGINX_HOST:-45.94.58.252}" # public check (optional)

# ---------------- UI helpers ----------------
bold()  { echo -e "\033[1m$*\033[0m"; }
green() { echo -e "\033[32m$*\033[0m"; }
yellow(){ echo -e "\033[33m$*\033[0m"; }
red()   { echo -e "\033[31m$*\033[0m"; }
bar()   { local cur=$1 tot=$2; local w=40; local f=$(( cur * w / tot )); printf "["; printf "%0.s█" $(seq 1 $f); printf "%0.s░" $(seq $((f+1)) $w); printf "]"; }

stepn=0; steps=12
step() { stepn=$((stepn+1)); echo; printf "%s (%s/%s) %s\n" "$(bar "$stepn" "$steps")" "$stepn" "$steps" "$(bold "$1")"; }

die() { red "✗ $1"; exit 1; }

# ---------------- Arg parsing ----------------
usage() {
  cat <<USAGE
Usage:
  sudo $0 init   --repo <url> [--goal "..."] [--branch my-branch] [--push]
  sudo $0 run    --dir  </home/swarm/projects/name> --goal "Implement X" [--iters 5] [--push]
  sudo $0 health

Flags:
  --repo URL            Git URL, e.g. https://github.com/agumabanks/sanaa-website
  --dir PATH            Existing working tree (under $WORK_ROOT)
  --goal "text"         High level objective for the agent loop
  --branch NAME         Create/use branch (default: ${BRANCH_PREFIX}/<slug>)
  --iters N             Max iterations (default: ${MAX_ITERS})
  --push                Push branch to origin after successful commit(s)
  --api-base URL        OpenAI-compatible base (default: ${API_BASE})
  --model NAME          Cosmetic "model" name in JSON (llama.cpp uses the loaded model)
  --help                This text

Examples:
  sudo $0 init --repo https://github.com/agumabanks/sanaa-website --goal "Create clean blog page"
  sudo $0 run  --dir  /home/swarm/projects/sanaa-website --goal "Add contact form" --iters 3 --push
USAGE
}

cmd="${1:-}"; shift || true
repo=""; workdir=""; goal=""; branch=""; iters="$MAX_ITERS"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)       repo="$2"; shift 2;;
    --dir)        workdir="$2"; shift 2;;
    --goal)       goal="$2"; shift 2;;
    --branch)     branch="$2"; shift 2;;
    --iters)      iters="$2"; shift 2;;
    --push)       PUSH="true"; shift 1;;
    --api-base)   API_BASE="$2"; shift 2;;
    --model)      MODEL_NAME="$2"; shift 2;;
    --help|-h)    usage; exit 0;;
    *)            echo "Unknown flag: $1"; usage; exit 1;;
  esac
done

[[ -n "${cmd}" ]] || { usage; exit 1; }

# ---------------- Syscheck ----------------
health_check() {
  bold "Quick health:"
  # llama server health (200=ready, 503=loading)
  for p in "${PORTS[@]}"; do
    echo -n " - llama /health on $p ... "
    if curl -fsS "http://127.0.0.1:${p}/health" >/dev/null 2>&1; then
      green "OK"
      break
    else
      # read body to see if it's 503
      code=$(curl -s -o /tmp/h.$$ -w "%{http_code}" "http://127.0.0.1:${p}/health" || true)
      if [[ "$code" == "503" ]]; then yellow "LOADING (503)"; else red "FAIL"; fi
    fi
  done

  echo -n " - swarm-api on ${API_PORT} ... "
  curl -fsS "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1 && green "OK" || yellow "WARN"

  echo -n " - public via Nginx (/info) ... "
  curl -fsS "http://${NGINX_HOST}/info" >/dev/null 2>&1 && green "OK" || yellow "SKIP/FAIL"
}

# ---------------- Git utils ----------------
ensure_git_identity() {
  git -C "$1" config user.name  >/dev/null || git -C "$1" config user.name  "Coding Swarm Bot"
  git -C "$1" config user.email >/dev/null || git -C "$1" config user.email "swarm@localhost"
}

slugify() { echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g;s/^-+|-+$//g'; }

create_branch() {
  local dir="$1" name="$2"
  ensure_git_identity "$dir"
  git -C "$dir" fetch --all --prune || true
  if git -C "$dir" rev-parse --verify "$name" >/dev/null 2>&1; then
    git -C "$dir" checkout "$name"
  else
    git -C "$dir" checkout -b "$name"
  fi
}

# ---------------- Project detection ----------------
detect_stack() {
  local dir="$1"
  if [[ -f "$dir/package.json" ]]; then echo "node"; return; fi
  if [[ -f "$dir/composer.json" ]]; then echo "php"; return; fi
  echo "generic"
}

install_deps() {
  local dir="$1" kind; kind=$(detect_stack "$dir")
  case "$kind" in
    node)
      (cd "$dir" && { npm ci || npm install; }) || true
      ;;
    php)
      command -v composer >/dev/null 2>&1 && (cd "$dir" && composer install) || true
      ;;
    *)
      : ;;
  esac
}

run_tests() {
  local dir="$1" kind; kind=$(detect_stack "$dir")
  case "$kind" in
    node)
      (cd "$dir" && npm run -s test) || true
      ;;
    php)
      (cd "$dir" && { php -v >/dev/null 2>&1 || true; vendor/bin/phpunit -v || true; }) || true
      ;;
    *)
      return 0 ;;
  esac
}

# ---------------- Prompting ----------------
SYSTEM_PROMPT=$'You are an elite code agent working on a live repository.\n\
You MUST output edits as a single unified diff (git patch) between triple backticks using the `diff` fence, like:\n\
```diff\n\
diff --git a/path/file.ext b/path/file.ext\n\
--- a/path/file.ext\n\
+++ b/path/file.ext\n\
@@\n\
... lines added/removed ...\n\
```\n\
Rules:\n\
- Only include changed files in the diff.\n\
- Keep changes minimal and focused on the user GOAL.\n\
- Do not include commentary outside the code fence.\n\
- If no changes are needed, output exactly: ```diff\n# no-op\n```\n'

compose_user_prompt() {
  local repo_name="$1" goal_text="$2" git_status="$3" test_summary="$4"
  cat <<EOF
Repository: ${repo_name}
Goal: ${goal_text}

Repo status:
${git_status}

Test/Build summary:
${test_summary}

Please propose the smallest set of changes to achieve the goal.
Return ONLY a unified diff in a single \`\`\`diff fenced block.
EOF
}

# ---------------- Model call (OpenAI-compatible chat) ----------------
call_model() {
  local system="$1" user="$2"
  # Build JSON safely with jq
  local payload
  payload=$(jq -n --arg sys "$system" --arg usr "$user" --arg m "$MODEL_NAME" '{
    model: $m,
    temperature: 0.2,
    messages: [
      {role:"system", content:$sys},
      {role:"user",   content:$usr}
    ]
  }')

  curl -sS -X POST \
    -H "Content-Type: application/json" \
    -d "$payload" \
    "${API_BASE}/chat/completions"
}

# Extract fenced ```diff ... ``` from model content
extract_patch() {
  # reads full JSON from stdin
  jq -r '
    .choices[0].message.content // "" |
    capture("```diff\\n(?<patch>.*)```"; "ms") .patch // empty
  ' || true
}

# ---------------- Patch application ----------------
apply_patch() {
  local dir="$1" patch_file="$2"
  local ok=0
  # p0 first; if fails, try p1
  if git -C "$dir" apply --index --whitespace=fix -p0 "$patch_file" 2>/tmp/giterr.$$; then
    ok=1
  elif git -C "$dir" apply --index --whitespace=fix -p1 "$patch_file" 2>/tmp/giterr.$$; then
    ok=1
  else
    ok=0
  fi
  return "$ok"
}

# ---------------- Commands ----------------
do_init() {
  [[ -n "$repo" ]] || die "--repo is required for init"
  local name; name=$(basename -s .git "$repo")
  local dest="${WORK_ROOT}/${name}"
  step "Create workspace ${dest}"
  mkdir -p "$WORK_ROOT"
  if [[ -d "$dest/.git" ]]; then
    yellow "Repo exists, pulling latest..."
    (cd "$dest" && git pull --rebase || true)
  else
    git clone --depth 1 "$repo" "$dest"
  fi

  step "Create working branch"
  local slug_goal branch_name
  slug_goal=$(slugify "${goal:-bootstrap}")
  branch_name="${branch:-${BRANCH_PREFIX}/${slug_goal}}"
  create_branch "$dest" "$branch_name"

  step "Install dependencies (best effort)"
  install_deps "$dest"

  step "First build/test (best effort)"
  run_tests "$dest" || true

  step "Summary"
  green "Workspace: $dest"
  green "Branch:    $branch_name"
  echo
  yellow "Next:"
  echo "  sudo $0 run --dir \"$dest\" --goal \"${goal:-Your task here}\" --iters 3 --push"
}

do_run() {
  [[ -n "$workdir" ]] || die "--dir is required for run"
  [[ -d "$workdir/.git" ]] || die "Not a git repo: $workdir"
  [[ -n "$goal" ]] || die "--goal is required for run"
  [[ -n "$iters" ]] || iters="$MAX_ITERS"

  health_check

  step "Ensure branch"
  local slug_goal branch_name
  slug_goal=$(slugify "$goal")
  branch_name="${branch:-${BRANCH_PREFIX}/${slug_goal}}"
  create_branch "$workdir" "$branch_name"

  step "Install deps & baseline tests"
  install_deps "$workdir"
  local test_out
  test_out="$(run_tests "$workdir" 2>&1 || true)"

  for ((i=1; i<=iters; i++)); do
    step "Iteration $i / $iters — plan & patch"
    local status; status="$(git -C "$workdir" status --porcelain=v1 -uall)"
    local prompt; prompt="$(compose_user_prompt "$(basename "$workdir")" "$goal" "$status" "$test_out")"
    local resp patch
    resp="$(call_model "$SYSTEM_PROMPT" "$prompt")" || true
    patch="$(echo "$resp" | extract_patch)"

    if [[ -z "$patch" ]]; then
      yellow "No patch returned; raw content:"
      echo "$resp" | jq -r '.choices[0].message.content // ""'
      continue
    fi

    tmp_patch="$(mktemp)"
    printf "%s\n" "$patch" > "$tmp_patch"
    echo "----- PATCH (first 40 lines) -----"
    head -n 40 "$tmp_patch" || true
    echo "----------------------------------"

    if apply_patch "$workdir" "$tmp_patch"; then
      green "Patch applied."
    else
      red "Patch failed to apply."
      echo "----- git-apply errors -----"
      sed -n '1,120p' /tmp/giterr.$$ || true
      echo "----------------------------"
      continue
    fi

    step "Commit changes"
    if ! git -C "$workdir" diff --cached --quiet; then
      git -C "$workdir" commit -m "${COMMIT_PREFIX} ${goal} (iter ${i})"
      green "Committed."
      if [[ "$PUSH" == "true" ]]; then
        step "Push branch"
        if git -C "$workdir" push -u origin "$branch_name"; then
          green "Pushed to origin/$branch_name"
        else
          yellow "Push failed (auth or perms). Configure a PAT or SSH and re-run."
        fi
      fi
    else
      yellow "No staged changes; skipping commit."
    fi

    step "Re-run tests/build"
    test_out="$(run_tests "$workdir" 2>&1 || true)"
    echo "$test_out" | tail -n 80 || true
  done

  step "Done"
  green "Branch: $branch_name"
  echo "Tip: open a PR on GitHub when ready."
}

do_health() { health_check; }

# ---------------- Main dispatch ----------------
case "$cmd" in
  init)   do_init;;
  run)    do_run;;
  health) do_health;;
  *)      usage; exit 1;;
esac
