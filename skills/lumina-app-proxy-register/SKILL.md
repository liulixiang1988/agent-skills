---
name: lumina-app-proxy-register
description: "Register and verify a sandbox-hosted HTTP service through Lumina App Proxy (LuminaProxyAPI). Use when the user wants to spin up a tiny FastAPI server inside a Lumina sandbox, expose it under {appId}.{BaseDomain}, hand the resulting URL to teammates, or compare access_scope=owner vs access_scope=all behavior of the AppProxyAuthHandler. Pairs with lumina-eps-token to acquire the bearer token and create the sandbox first."
---

# Lumina App Proxy Register

End-to-end workflow that takes a live Lumina sandbox and a bearer token, drops a minimal FastAPI server into the sandbox, registers it via `egress-llm`'s `/app/register/agent`, prints the public `{appId}.{BaseDomain}` URL, and verifies the round-trip through LuminaProxyAPI with one S2S call.

## When To Use

- User wants to publish a service from inside a Lumina sandbox without writing the 5-step register flow by hand.
- User is testing `AppProxyAuthHandler` (`AccessScope = owner` vs `all`) — for example to confirm a teammate's token is rejected on an owner-scoped URL.
- User is debugging the cookie-based OAuth state flow (`AppProxyAuthStateCookie`) end-to-end: the registered URL is the ideal target to hit in a fresh browser to trigger the AAD redirect.
- User asks to "create a terminal-proxy app", "register an app in the sandbox", or wants an `app_url` from `LuminaProxyAPI`.

## Pairs With

This skill needs a `ComputerId` and a bearer token. The easiest way to obtain both is the sibling `lumina-eps-token` skill:

1. Run `lumina-eps-token` to acquire the token (cached at `sources/dev/SandboxService/AIAgents/ts-agents/skills-agent/scripts/test_sessions/auth_token.txt`) and initialize a sandbox (it prints `Computer ID: skills-agent-<uuid>`).
2. Pass that `ComputerId` and the cached token to this skill.

## Required Parameters

| Param | Type | Description |
|---|---|---|
| `ComputerId` / `--computer-id` | string | The sandbox ID returned by `eps_client.py` (looks like `skills-agent-<uuid>` or `playground-<uuid>`). |
| `AuthToken` / `--auth-token` | string | OBO/PFT bearer token. For owner-scoped apps the token's `oid` claim must equal the sandbox owner's `oid`. |

## Optional Parameters

| Param | Default | Notes |
|---|---|---|
| `LuminaApiBase` / `--lumina-api-base` | `https://luminaserviceapi-b-4.luminadevaks-westus3.dev.copilotlumina.com` | Pick a different ring/region if needed. |
| `FeatureKind` / `--feature-kind` | `terminal` | One of `agent`, `desktop`, `operator`, `terminal` (validated by `RegisterAppService._supportedFeatureKinds`). |
| `FeatureName` / `--feature-name` | `terminal-shell` | Logical feature/service name. |
| `ServerPort` / `--server-port` | `19101` | Must fall inside the sandbox image's `APP_HOSTING_PORT_RANGE`. |
| `AccessScope` / `--access-scope` | `owner` | `owner` ⇒ requester only; `all` ⇒ any authenticated user. |
| `-SkipS2STest` / `--skip-s2s` | off | Skip Step 5 if you only need the URL printed. |

## Resolving the helper script path

Same convention as `lumina-eps-token`. The path varies per host install:

1. If the host exposes `CLAUDE_SKILL_DIR`, `SKILL_DIR`, `AGENT_SKILL_PATH`, or `AGENTS_SKILL_DIR`, use it.
2. If the current workspace is the skill source repository, check `skills/lumina-app-proxy-register` relative to the workspace root.
3. Otherwise search these roots for a `lumina-app-proxy-register` directory whose `scripts/` contains both helpers:
    - `$HOME/.agents/skills/lumina-app-proxy-register`
    - `$HOME/.claude/skills/lumina-app-proxy-register`
    - `$HOME/.codex/skills/lumina-app-proxy-register`
    - `$HOME/.gemini/skills/lumina-app-proxy-register`
    - `$HOME/.copilot/skills/lumina-app-proxy-register`
    - Any path matching `**/skills/lumina-app-proxy-register/SKILL.md` reachable from cwd or the project worktree.
4. As a last resort, ask the user.

On Windows, `$HOME` is `$env:USERPROFILE`.

## Invocation

### Windows PowerShell (PowerShell 7+)

```powershell
& "$skillDir\scripts\Invoke-LuminaAppProxyRegister.ps1" `
  -ComputerId "skills-agent-<uuid>" `
  -AuthToken (Get-Content "<repo>\sources\dev\SandboxService\AIAgents\ts-agents\skills-agent\scripts\test_sessions\auth_token.txt" -Raw).Trim() `
  -AccessScope "owner"
```

### macOS / Linux

```bash
TOKEN=$(cat "<repo>/sources/dev/SandboxService/AIAgents/ts-agents/skills-agent/scripts/test_sessions/auth_token.txt")
bash "$skillDir/scripts/invoke-lumina-app-proxy-register.sh" \
  --computer-id "skills-agent-<uuid>" \
  --auth-token "$TOKEN" \
  --access-scope owner
```

## What the script does (5 steps)

1. **Upload `server.py`** to `/home/oai/share/server.py` via `POST /api/agent/storage/file/batchUpload`. The payload is a minimal FastAPI app with `GET /` returning `{"status":"ok"}` and `GET /health` returning `{"healthy":true}`.
2. **Start the server**: open a PTY session named `server-session` via `POST /api/agent/container/exec` (`sessionDuration=2400`), then `feedChars` runs `nohup python /home/oai/share/server.py <port> &`.
3. **Register** the service: runs `curl -X POST ${EGRESS_LLM_API_ENDPOINT}/app/register/agent` from inside the sandbox with body `{"feature_kind", "feature_name", "port", "path": "/", "access_scope"}`. The egress-llm forwards to LuminaProxyAPI's `RegisterAppService.RegisterWebAppAsync`, which assigns a fresh `appId` (Guid) and returns `{registered_app_id, app_url}`.
4. **Print** the public URL — looks like `https://<appId>.luminaproxyapi-<ring>-<region>.<ring>.copilotlumina.com/`.
5. **S2S verify**: `Invoke-WebRequest`/`curl` the URL with `Authorization: Bearer <AuthToken>`; expect `200` `{"status":"ok"}` when the auth+proxy pipeline is healthy.

## AccessScope behaviour (important)

`AppProxyAuthHandler.AuthorizeSandboxAccessAsync` only enforces the owner check when `appContent.AccessScope == "owner"` (constant-time string comparison ignores case). Any other value — including the empty string — falls through to a 200.

| AccessScope on the registration | Same user (token oid == sandbox.ObjectId) | Different user |
|---|---|---|
| `owner` | 200 | **401 Unauthorized** |
| `all` | 200 | 200 |
| (unset on request) | falls back to `_appProxyOptions.Value.AccessScope` — **dev/test rings default to `"all"`**, prod/msit/sdf default to `"owner"`. |

Confusing observation: in dev/test, registering an app **without** passing `access_scope` produces an "all" app, not "owner". If you need to assert owner behaviour during a dev experiment, pass `-AccessScope owner` / `--access-scope owner` explicitly. The ring defaults live in `LuminaProxyAPI.Cosmic/Config/appsettings.<ring>.json` → `AppProxyOptions.AccessScope`.

## Resource lifetime

- The PTY session is created with `sessionDuration: 2400` seconds (~40 minutes). After that the `nohup` process may keep running but the session won't honour new `feedChars`/`exec` calls.
- The sandbox itself has its own lifetime governed by `ISandboxKeepAliveService` (touched once per `GetAppContentAsync` cache miss). Once the sandbox is gone, the `{appId}.{BaseDomain}` URL returns `404 Not Found` from the handler.
- The registered `appId` row in `AppContentRegistration` persists separately and is reused as long as the sandbox is alive.

## Known endpoint behavior

Tested against `luminaserviceapi-b-4.luminadevaks-westus3.dev.copilotlumina.com`:

- Without an `Authorization` header (or cookie), GETs to `https://<appId>.<BaseDomain>/` return `302` to `login.microsoftonline.com/.../oauth2/v2.0/authorize` with `state=<nonce>` (no `|`-separated returnUrl), confirming the cookie-based state flow (`AppProxyAuthStateCookie`) is live.
- With a valid bearer header, `GET /` returns `200 {"status":"ok"}`.
- `401` from the proxy → token oid mismatch on an `owner`-scoped app, or invalid/expired token.
- `404` from the proxy → `appId` no longer registered or the sandbox is gone.

## Environment requirements

- PowerShell 7+ on Windows (uses `Invoke-WebRequest -SkipCertificateCheck`).
- `curl` and Python 3 on macOS/Linux (Python is used only to base64-encode the server payload and to splice JSON safely).
- No Bun / Node required — registration is just curl from inside the sandbox.

## Sensitive Data Notes

- The bearer token is a real user-impersonation JWT. Do not print full tokens in chat output; truncate (`<first 40 chars>...`) when summarising.
- Do not commit the token cache or the registered `app_url` to source control with the token alongside.
- The `server.py` written to the sandbox is intentionally trivial. If you replace it with something else, remember the proxy will happily forward arbitrary requests once authorized, so don't expose anything you wouldn't expose publicly within the ring.
