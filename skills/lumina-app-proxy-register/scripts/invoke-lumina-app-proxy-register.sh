#!/usr/bin/env bash
# Register a custom HTTP service inside a Lumina sandbox and
# expose it through LuminaProxyAPI. POSIX equivalent of
# Invoke-LuminaAppProxyRegister.ps1.

set -euo pipefail

lumina_api_base="https://luminaserviceapi-b-4.luminadevaks-westus3.dev.copilotlumina.com"
computer_id=""
auth_token=""
feature_kind="terminal"
feature_name="terminal-shell"
server_port=19101
access_scope="owner"
skip_s2s=false

usage() {
  cat <<'EOF'
Usage: invoke-lumina-app-proxy-register.sh [options]

Required:
  --computer-id ID        Lumina sandbox ComputerId.
  --auth-token TOKEN      OBO/PFT bearer token.

Optional:
  --lumina-api-base URL   LuminaServiceAPI base URL (default: b-4 westus3 dev).
  --feature-kind KIND     terminal | agent | desktop | operator (default: terminal).
  --feature-name NAME     Logical service name (default: terminal-shell).
  --server-port PORT      Port within APP_HOSTING_PORT_RANGE (default: 19101).
  --access-scope SCOPE    owner | all (default: owner).
  --skip-s2s              Skip the post-register S2S verification call.
  -h, --help              Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --computer-id)      computer_id="$2"; shift 2 ;;
    --auth-token)       auth_token="$2"; shift 2 ;;
    --lumina-api-base)  lumina_api_base="$2"; shift 2 ;;
    --feature-kind)     feature_kind="$2"; shift 2 ;;
    --feature-name)     feature_name="$2"; shift 2 ;;
    --server-port)      server_port="$2"; shift 2 ;;
    --access-scope)     access_scope="$2"; shift 2 ;;
    --skip-s2s)         skip_s2s=true; shift ;;
    -h|--help)          usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$computer_id" || -z "$auth_token" ]]; then
  echo "--computer-id and --auth-token are required." >&2
  usage >&2
  exit 2
fi

if [[ "$access_scope" != "owner" && "$access_scope" != "all" ]]; then
  echo "--access-scope must be owner or all" >&2
  exit 2
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
  echo "python (3) is required for base64 encoding the server payload." >&2
  exit 1
fi

PYTHON_BIN="$(command -v python3 || command -v python)"

invoke_agent_api() {
  local path="$1"
  local body="$2"
  echo
  echo ">> POST $path"
  curl -sS \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${auth_token}" \
    --data "$body" \
    "${lumina_api_base}${path}"
}

# Step 1 — upload server.py
echo
echo "=== Step 1: Writing server.py to sandbox ==="

server_code=$(cat <<EOF
from fastapi import FastAPI
import uvicorn
import sys

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"healthy": True}

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else ${server_port}
    uvicorn.run(app, host="0.0.0.0", port=port)
EOF
)

server_code_b64=$("$PYTHON_BIN" -c "import base64,sys; print(base64.b64encode(sys.stdin.buffer.read()).decode())" <<<"$server_code")

upload_body=$("$PYTHON_BIN" -c "
import json, sys
body = {
    'computerId': sys.argv[1],
    'files': [
        {'path': '/home/oai/share/server.py', 'content': sys.argv[2], 'encoding': 'base64'}
    ]
}
print(json.dumps(body))
" "$computer_id" "$server_code_b64")

invoke_agent_api "/api/agent/storage/file/batchUpload" "$upload_body" >/dev/null
echo "File uploaded successfully."

# Step 2 — start server in session
echo
echo "=== Step 2: Starting server on port ${server_port} ==="

exec_body=$("$PYTHON_BIN" -c "
import json, sys
print(json.dumps({
    'cmd': ['bash'],
    'computerId': sys.argv[1],
    'sessionName': 'server-session',
    'sessionDuration': 2400,
}))
" "$computer_id")
invoke_agent_api "/api/agent/container/exec" "$exec_body" >/dev/null

feed_body=$("$PYTHON_BIN" -c "
import json, sys
print(json.dumps({
    'computerId': sys.argv[1],
    'sessionName': 'server-session',
    'chars': f'nohup python /home/oai/share/server.py {sys.argv[2]} &\\n',
    'yieldTimeMs': 3000,
}))
" "$computer_id" "$server_port")
invoke_agent_api "/api/agent/container/feedChars" "$feed_body" >/dev/null
echo "Server started on port ${server_port}."

# Step 3 — register via egress-llm
echo
echo "=== Step 3: Registering service via egress-llm (access_scope=${access_scope}) ==="

register_cmd="curl -s -X POST \${EGRESS_LLM_API_ENDPOINT}/app/register/agent \
-H 'Content-Type: application/json' \
-d '{\"feature_kind\": \"${feature_kind}\", \"feature_name\": \"${feature_name}\", \"port\": ${server_port}, \"path\": \"/\", \"access_scope\": \"${access_scope}\"}'"

register_body=$("$PYTHON_BIN" -c "
import json, sys
print(json.dumps({
    'cmd': ['bash', '-c', sys.argv[1]],
    'computerId': sys.argv[2],
}))
" "$register_cmd" "$computer_id")

step3_response=$(invoke_agent_api "/api/agent/container/exec" "$register_body")
echo
echo "Registration response:"
echo "$step3_response"

app_url=$("$PYTHON_BIN" -c "
import json, sys
resp = json.loads(sys.stdin.read())
stdout = resp.get('content', {}).get('stdout', '')
if not stdout:
    sys.exit('Registration stdout is empty.')
inner = json.loads(stdout)
url = inner.get('app_url', '')
if not url:
    sys.exit('app_url missing from registration stdout.')
print(url)
" <<<"$step3_response")

# Step 4 — print URL
echo
echo "=== Step 4: Service is ready ==="
echo "Service URL: ${app_url}"
echo "Health check:"
echo "  curl -s ${app_url}health"

# Step 5 — S2S verification (optional)
if [[ "$skip_s2s" == true ]]; then
  echo
  echo "(Skipping Step 5 because --skip-s2s was passed.)"
  exit 0
fi

echo
echo "=== Step 5: Test S2S call to Proxy API ==="

http_code=$(curl -s -o /tmp/lumina-app-proxy-s2s.txt -w "%{http_code}" \
  -H "Authorization: Bearer ${auth_token}" \
  --max-time 10 -k "${app_url}")

echo "S2S status code: ${http_code}"
echo "S2S response body:"
cat /tmp/lumina-app-proxy-s2s.txt
echo
rm -f /tmp/lumina-app-proxy-s2s.txt
