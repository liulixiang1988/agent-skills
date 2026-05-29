#!/usr/bin/env bash
set -euo pipefail

repo_root="$(pwd)"
description="Hi"
url="luminaserviceapi-b-4.luminadevaks-westus3.dev.copilotlumina.com"
eps_version="v1"
bearer_token=""

usage() {
  cat <<'EOF'
Usage: invoke-lumina-eps-client.sh [options]

Options:
  --repo-root PATH        CopilotLumina worktree root. Defaults to current directory.
  --description TEXT      Prompt to send to the agent. Defaults to "Hi".
  --url HOST_OR_URL       LuminaServiceAPI host or URL.
  --eps-version v1|v3     EPS API version. Defaults to v1.
  --bearer-token TOKEN    Optional pre-acquired bearer token.
  -h, --help              Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root)
      repo_root="$2"
      shift 2
      ;;
    --description)
      description="$2"
      shift 2
      ;;
    --url)
      url="$2"
      shift 2
      ;;
    --eps-version)
      eps_version="$2"
      shift 2
      ;;
    --bearer-token)
      bearer_token="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$eps_version" != "v1" && "$eps_version" != "v3" ]]; then
  echo "--eps-version must be v1 or v3" >&2
  exit 2
fi

ensure_bun() {
  export PATH="$HOME/.bun/bin:$PATH"
  if command -v bun >/dev/null 2>&1; then
    return
  fi

  echo "bun not found; installing with official installer..."
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL https://bun.sh/install | bash
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- https://bun.sh/install | bash
  else
    echo "curl or wget is required to install bun automatically." >&2
    exit 1
  fi

  export PATH="$HOME/.bun/bin:$PATH"
  if ! command -v bun >/dev/null 2>&1; then
    echo "bun was installed but is still not available in PATH. Add $HOME/.bun/bin to PATH and retry." >&2
    exit 1
  fi
}

find_eps_client() {
  local root="$1"
  local candidate="$root/sources/dev/SandboxService/AIAgents/ts-agents/skills-agent/scripts/eps_client.py"
  if [[ -f "$candidate" ]]; then
    printf '%s\n' "$candidate"
    return
  fi

  local found
  found="$(find "$root" -path '*skills-agent*/scripts/eps_client.py' -type f 2>/dev/null | head -n 1 || true)"
  if [[ -n "$found" ]]; then
    printf '%s\n' "$found"
    return
  fi

  echo "Could not find skills-agent/scripts/eps_client.py under $root" >&2
  exit 1
}

ensure_bun

eps_client="$(find_eps_client "$repo_root")"
script_dir="$(dirname "$eps_client")"

client_args=("./eps_client.py" "$description" "--url" "$url" "--eps-version" "$eps_version")
if [[ -n "$bearer_token" ]]; then
  client_args+=("--bearer-token" "$bearer_token")
fi

cd "$script_dir"

if command -v uv >/dev/null 2>&1; then
  uv run --with requests python "${client_args[@]}"
elif command -v python3 >/dev/null 2>&1; then
  python3 "${client_args[@]}"
elif command -v python >/dev/null 2>&1; then
  python "${client_args[@]}"
else
  echo "No Python runtime found. Install Python or uv, then rerun this helper." >&2
  exit 1
fi
