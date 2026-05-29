---
name: lumina-eps-token
description: "Acquire and validate Lumina EPS/LuminaServiceAPI bearer tokens using the CopilotLumina eps_client.py and get-lumina-token.ts helpers. Use when the user asks about Lumina token acquisition, EPS client authentication, testing luminaserviceapi hosts, running eps_client.py, validating v1/v3 EPS routes, resolving bundled helper script paths across .agents/.claude/.copilot installs, or fixing local Bun/Python/uv environment issues for these flows."
---

# Lumina EPS Token

Acquire a Microsoft Entra ID token for LuminaServiceAPI, then use it with `eps_client.py` to validate EPS/Lumina agent endpoints.

## When To Use

- User asks how Lumina/EPS tokens are acquired or whether a token can access a `luminaserviceapi-*` host.
- User wants to run `eps_client.py`, especially against `luminaserviceapi-b-4.luminadevaks-westus3.dev.copilotlumina.com`.
- User hits local environment issues such as missing `bun`, missing `python`, or missing `requests`.
- User asks whether token-related implementation contains sensitive information.

## Key Files In CopilotLumina

Resolve these relative to the current CopilotLumina worktree root:

- `sources/dev/SandboxService/AIAgents/ts-agents/skills-agent/scripts/eps_client.py`
- `sources/dev/SandboxService/AIAgents/ts-agents/egress-llm/scripts/get-lumina-token.ts`

`eps_client.py` calls `get-lumina-token.ts` when `--bearer-token` is not supplied. The TypeScript helper uses OAuth authorization code + PKCE against Microsoft Entra ID with:

- tenant: `72f988bf-86f1-41af-91ab-2d7cd011db47`
- client: `ac180c33-bd40-461a-bbfd-1a4ff964e8a0`
- scope: `api://ac180c33-bd40-461a-bbfd-1a4ff964e8a0/user_impersonate`

## Quick Run

From the CopilotLumina worktree, prefer the bundled helper because it handles Bun and Python command differences.

### Resolving the helper script path

The helpers live in this skill's own `scripts/` directory. The absolute path varies by host (for example, some agent hosts install skills under `~/.agents/skills/`, Claude Code `npx skill install` commonly uses `~/.claude/skills/`, and Copilot/Gemini/Codex installers may use their own roots). The skill may also be loaded directly from a source checkout such as an `agent-skills/skills/lumina-eps-token/` folder. Do not hardcode an install path. Instead, resolve it at run time using one of these strategies, in order:

1. If the host exposes the skill directory via env var (for example, `CLAUDE_SKILL_DIR`, `SKILL_DIR`, `AGENT_SKILL_PATH`, or `AGENTS_SKILL_DIR`), use it.
2. If the current workspace is the skill source repository, check `skills/lumina-eps-token` relative to the workspace root.
3. Otherwise, search the conventional roots for a `lumina-eps-token` directory containing this SKILL.md:
    - `$HOME/.agents/skills/lumina-eps-token`
    - `$HOME/.claude/skills/lumina-eps-token`
    - `$HOME/.codex/skills/lumina-eps-token`
    - `$HOME/.gemini/skills/lumina-eps-token`
    - `$HOME/.copilot/skills/lumina-eps-token`
    - Any path matching `**/skills/lumina-eps-token/SKILL.md` reachable from the current working directory or the project worktree.
4. As a last resort, ask the user where the skill is installed.

On Windows, treat `$HOME` as the user's home directory; in PowerShell that is usually `$env:USERPROFILE`.

Pick the first match that contains both `scripts/Invoke-LuminaEpsClient.ps1` and `scripts/invoke-lumina-eps-client.sh`, then invoke from there.

### Invocation once `$skillDir` is resolved

Windows PowerShell:

```powershell
& "$skillDir\scripts\Invoke-LuminaEpsClient.ps1" `
  -Description "Hi" `
  -Url "luminaserviceapi-b-4.luminadevaks-westus3.dev.copilotlumina.com" `
  -EpsVersion "v1"
```

macOS/Linux:

```bash
bash "$skillDir/scripts/invoke-lumina-eps-client.sh" \
  --description "Hi" \
  --url "luminaserviceapi-b-4.luminadevaks-westus3.dev.copilotlumina.com" \
  --eps-version "v1"
```

Both helpers default `--repo-root` / `-RepoRoot` to the current working directory, so run them from inside the CopilotLumina worktree (or pass `--repo-root <path>`).

Direct equivalent when environment is already ready:

```powershell
cd sources/dev/SandboxService/AIAgents/ts-agents/skills-agent/scripts
uv run --with requests python .\eps_client.py "Hi" --url luminaserviceapi-b-4.luminadevaks-westus3.dev.copilotlumina.com --eps-version v1
```

## Known Endpoint Behavior

For `luminaserviceapi-b-4.luminadevaks-westus3.dev.copilotlumina.com`, a valid token has been shown to work with `--eps-version v1`:

- initialize: `POST /api/agent/computer/initialize`
- stream: `POST /api/agent/sub-agent/a2a/message/stream`

The same host returned `404 Not Found` for the default v3 open route:

- `POST /api/v3/sandboxes/{sandboxId}:open`

Treat `401` or `403` as token/auth failures. Treat `404` as route availability or API version mismatch unless other evidence says otherwise.

## Environment Recovery

- If `bun` is missing, install it with the official PowerShell installer, then add `$env:USERPROFILE\.bun\bin` to the current process `PATH`.
- On macOS/Linux, install Bun with `curl -fsSL https://bun.sh/install | bash`, then add `$HOME/.bun/bin` to `PATH` for the current process.
- If `python` is missing but `uv` exists, run through `uv run --with requests python ...`.
- If both `python` and `uv` are missing, install or locate a Python runtime before continuing.

## Sensitive Data Notes

- Source code contains tenant/client/scope identifiers, not client secrets.
- Runtime caches contain real tokens and must not be committed:
  - `skills-agent/scripts/test_sessions/auth_token.txt`
  - `egress-llm/scripts/.cache.json` may include refresh tokens.
- The relevant `.gitignore` files currently ignore these cache paths. Do not print full tokens in final answers; summarize with prefixes only when necessary.
