#!/usr/bin/env python3
"""End-to-end verification of the Lumina terminal app-hosting scenario (v1 legacy Agent API).

Flow (mirrors docs/partner-sandbox/in-sandbox/terminal-app-hosting.md, driven via v1):
  1. Acquire a Lumina bearer token (LuminaServiceAPI audience).
  2. Create a sandbox:        POST /api/agent/computer/initialize       -> computerId
  3. Write server.py:         POST /api/agent/container/exec (heredoc)
  4. Start FastAPI server:    POST /api/agent/container/exec (nohup ... &)
  5. Register the app:        POST /api/agent/container/exec -> curl ${EGRESS_LLM_API_ENDPOINT}/app/register/agent
  6. Report registered_app_id + app_url.

Defaults target luminaserviceapi-test-centralus.copilotlumina.com, which does NOT
require x-ms-lumina-* headers and whose egress-llm does NOT require x-egress-token.

The bearer token is read, in order:
  --bearer-token  >  --token-file  >  $LUMINA_BEARER_TOKEN  >  the bundled get-lumina-token.ts helper.

Examples:
  python verify_app_hosting.py
  python verify_app_hosting.py --host luminaserviceapi-test-centralus.copilotlumina.com
  python verify_app_hosting.py --token-file C:/path/auth_token.txt --keep-sandbox
  python verify_app_hosting.py --repo-root C:/Users/me/work/CopilotLumina
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import uuid

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed. Run: uv run --with requests python verify_app_hosting.py ...")
    sys.exit(3)

DEFAULT_HOST = "luminaserviceapi-test-centralus.copilotlumina.com"

SERVER_CODE = """from fastapi import FastAPI
import uvicorn
import sys

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "service": "app-host-demo"}

@app.get("/health")
def health():
    return {"healthy": True}

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 19101
    uvicorn.run(app, host="0.0.0.0", port=port)
"""


def log(step, msg):
    print(f"[{step}] {msg}", flush=True)


# ----- token acquisition -------------------------------------------------

def find_token_helper(repo_root):
    """Locate get-lumina-token.ts within a CopilotLumina worktree."""
    candidate = os.path.join(
        repo_root, "sources", "dev", "SandboxService", "AIAgents",
        "ts-agents", "egress-llm", "scripts", "get-lumina-token.ts",
    )
    return candidate if os.path.exists(candidate) else None


def acquire_token(args):
    if args.bearer_token:
        return args.bearer_token.strip()
    if args.token_file and os.path.exists(args.token_file):
        return open(args.token_file, encoding="utf-8").read().strip()
    env = os.environ.get("LUMINA_BEARER_TOKEN")
    if env:
        return env.strip()

    helper = find_token_helper(args.repo_root)
    if not helper:
        print("ERROR: No token provided and get-lumina-token.ts not found under --repo-root.")
        print("       Pass --bearer-token / --token-file / set LUMINA_BEARER_TOKEN, or point --repo-root at a CopilotLumina worktree.")
        sys.exit(3)

    log("token", f"Acquiring via {helper} (browser sign-in may open)...")
    bun = os.path.expanduser(os.path.join("~", ".bun", "bin", "bun"))
    bun = bun if os.path.exists(bun) else "bun"
    proc = subprocess.run([bun, helper], capture_output=True, text=True, timeout=180)
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("ey") and line.count(".") == 2:
            return line
    print("ERROR: could not parse token from helper output.")
    print(proc.stdout[-500:])
    print(proc.stderr[-500:])
    sys.exit(3)


# ----- v1 API client -----------------------------------------------------

class V1Client:
    def __init__(self, host, token):
        if not host.startswith("http"):
            host = "https://" + host
        self.host = host.rstrip("/")
        self.headers = {"Content-Type": "application/json", "Authorization": "Bearer " + token}

    def post(self, path, body, timeout=200):
        r = requests.post(self.host + path, json=body, headers=self.headers, timeout=timeout)
        return r

    def initialize(self, computer_id):
        return self.post("/api/agent/computer/initialize", {"computerId": computer_id})

    def exec(self, computer_id, bash, timeout_ms=30000):
        r = self.post("/api/agent/container/exec",
                      {"cmd": ["bash", "-c", bash], "computerId": computer_id, "timeout": timeout_ms})
        r.raise_for_status()
        data = r.json()
        content = data.get("content", {})
        return content.get("stdout", ""), content.get("stderr", ""), content.get("exit_code")

    def release(self, computer_id):
        return self.post("/api/agent/computer/release", {"computerId": computer_id})


# ----- verification steps ------------------------------------------------

def run(args):
    token = acquire_token(args)
    log("token", f"Token acquired (len={len(token)}).")

    client = V1Client(args.host, token)
    cid = args.computer_id or f"app-host-verify-{uuid.uuid4().hex[:8]}"

    results = {"host": client.host, "computerId": cid}

    # Step 2: create sandbox
    if args.computer_id:
        log("sandbox", f"Reusing computerId={cid}")
    else:
        log("sandbox", f"Creating sandbox computerId={cid} ...")
        r = client.initialize(cid)
        if r.status_code >= 300 or '"status":"error"' in r.text:
            print(f"FAIL: initialize -> {r.status_code} {r.text[:400]}")
            sys.exit(1)
        log("sandbox", "Sandbox created.")

    # Inspect hosting env
    out, _, _ = client.exec(cid, "echo EGRESS=$EGRESS_LLM_API_ENDPOINT; echo START=$APP_HOSTING_PORT_RANGE_START; echo END=$APP_HOSTING_PORT_RANGE_END")
    log("env", out.strip().replace("\n", "  "))
    if "EGRESS=" not in out or "START=" not in out:
        print("FAIL: hosting env vars not present (is this a terminal-capable sandbox?)")
        _cleanup(client, cid, args)
        sys.exit(1)

    # Steps 3+4: write server.py and start it (single exec to avoid cross-session drift)
    log("server", "Writing server.py and starting it...")
    combined = (
        'cat << "PYEOF" > /home/oai/share/server.py\n' + SERVER_CODE + 'PYEOF\n'
        'echo WROTE:; ls -l /home/oai/share/server.py; '
        'nohup python /home/oai/share/server.py ${APP_HOSTING_PORT_RANGE_START} > /tmp/server.log 2>&1 & '
        'disown; sleep 5; echo LOG:; cat /tmp/server.log; '
        'echo HEALTH:; curl -s http://localhost:${APP_HOSTING_PORT_RANGE_START}/health; echo'
    )
    out, err, code = client.exec(cid, combined, timeout_ms=60000)
    print(out)
    if '"healthy":true' not in out.replace(" ", ""):
        print(f"FAIL: local health check did not return healthy (exit={code}). stderr={err[:300]}")
        _cleanup(client, cid, args)
        sys.exit(1)
    log("server", "Server up; local /health OK.")

    # Step 5: register via egress-llm (doc-exact curl; no token header needed on this host)
    log("register", "Registering app via egress-llm...")
    reg_cmd = (
        "curl -s -X POST ${EGRESS_LLM_API_ENDPOINT}/app/register/agent "
        "-H 'Content-Type: application/json' "
        "-d '{\"feature_kind\": \"terminal\", \"feature_name\": \"terminal-shell\", "
        "\"port\": '${APP_HOSTING_PORT_RANGE_START}', \"path\": \"/\"}'"
    )
    out, err, code = client.exec(cid, reg_cmd)
    out = out.strip()
    print("  raw:", out)
    try:
        app = json.loads(out)
    except Exception:
        print(f"FAIL: registration did not return JSON. stderr={err[:300]}")
        _cleanup(client, cid, args)
        sys.exit(1)

    if "Unauthorized" in out or "error" in app:
        print("FAIL: registration rejected (this host's egress-llm may require x-egress-token).")
        _cleanup(client, cid, args)
        sys.exit(1)

    results["registered_app_id"] = app.get("registered_app_id")
    results["app_url"] = app.get("app_url")

    print("\n=== VERIFICATION PASSED ===")
    print(f"computerId:        {cid}")
    print(f"registered_app_id: {results['registered_app_id']}")
    print(f"app_url:           {results['app_url']}")
    print("\nNote: app_url is fronted by an AAD gateway. An external GET with a")
    print("LuminaServiceAPI-audience token returns the Entra sign-in page, not the")
    print("service body — the in-sandbox chain (server + register) is what this verifies.")

    if args.json_out:
        open(args.json_out, "w").write(json.dumps(results, indent=2))
        log("output", f"Wrote {args.json_out}")

    _cleanup(client, cid, args)
    return 0


def _cleanup(client, cid, args):
    if args.keep_sandbox or args.computer_id:
        log("cleanup", f"Keeping sandbox {cid}")
        return
    try:
        client.release(cid)
        log("cleanup", f"Released sandbox {cid}")
    except Exception as e:
        log("cleanup", f"release failed (non-fatal): {e}")


def main():
    p = argparse.ArgumentParser(description="Verify Lumina terminal app-hosting scenario via v1 API.")
    p.add_argument("--host", default=DEFAULT_HOST, help=f"LuminaServiceAPI host (default: {DEFAULT_HOST})")
    p.add_argument("--bearer-token", help="Bearer token (overrides all other sources)")
    p.add_argument("--token-file", help="Path to a file containing the bearer token")
    p.add_argument("--repo-root", default=os.getcwd(), help="CopilotLumina worktree root (for the token helper). Default: cwd")
    p.add_argument("--computer-id", help="Reuse an existing computerId instead of creating one (implies --keep-sandbox)")
    p.add_argument("--keep-sandbox", action="store_true", help="Do not release the sandbox at the end")
    p.add_argument("--json-out", help="Write results JSON to this path")
    args = p.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
