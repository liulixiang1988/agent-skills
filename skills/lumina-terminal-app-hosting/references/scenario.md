# Scenario Reference: Lumina Terminal App Hosting

Detailed notes for verifying the terminal app-hosting flow described in
`docs/partner-sandbox/in-sandbox/terminal-app-hosting.md`, driven via the **v1 legacy Agent API**.

## The flow

```
1. Acquire Lumina token  -> get-lumina-token.ts (LuminaServiceAPI audience)
2. Create sandbox        -> POST /api/agent/computer/initialize {computerId}
3. Write server.py       -> POST /api/agent/container/exec  (heredoc into /home/oai/share/server.py)
4. Start server          -> POST /api/agent/container/exec  (nohup python server.py $PORT &)
5. Register app          -> POST /api/agent/container/exec  -> curl ${EGRESS_LLM_API_ENDPOINT}/app/register/agent
6. Result                -> {registered_app_id, app_url}
```

## Endpoint choice matters

Use a **LuminaServiceAPI** host, e.g. `luminaserviceapi-test-centralus.copilotlumina.com`.

- On this host, v1 `initialize` works **without** any `x-ms-lumina-partner / -scenariogroup / -scenario`
  headers. Only `Content-Type` + `Authorization: Bearer <token>` are required.
- The `egress-llm` inside this sandbox image does **not** require an `x-egress-token` header, so the
  doc-exact registration curl (no auth header) succeeds.

### Hosts that do NOT work for this flow (observed)

- `luminaapi-b-4.luminadevaks-westus3.dev.copilotlumina.com` (and `luminaapi-*` generally):
  this is the **LuminaApi (v3)** surface. v1 routes like `/api/agent/computer/initialize` and
  `/api/agent/container/exec` return `404 "route is not registered on this service"`.
  v3 sandbox open works (`POST /api/v3/sandboxes/{id}:open`), but its egress-llm enforces
  `x-egress-token` auth, and the token file `/share/non_security/egress-llm-token` is
  `root:root 0600` — the in-terminal `oai` user gets `Permission denied`. So the doc-exact
  registration curl returns `{"type":"error","error":{"type":"authentication_error","message":"Unauthorized"}}`.
- `luminaserviceapi-b-4.luminadevaks-westus3.dev.copilotlumina.com`:
  v1 `initialize` returns `500 "Registration failed in Region=westus2 Collection=test"`
  (server-side pool/collection misroute, independent of request headers).

## Token

- Audience: `LuminaServiceAPI` (`api://67f912ef-...`). Acquired interactively via PKCE by
  `sources/dev/SandboxService/AIAgents/ts-agents/egress-llm/scripts/get-lumina-token.ts`.
- The helper needs its npm deps. If `bun get-lumina-token.ts` fails with
  `Cannot find package 'open'`, install deps from the ts-agents workspace:
  `pnpm install --filter egress-llm` (a bare `bun install` in the package dir can fail on the
  `@copilot-lumina/telemetry` workspace dependency).
- The helper prints the JWT after the line `Your access token:` and copies it to the clipboard.

## In-sandbox details

- App code path: `/home/oai/share/server.py`. The terminal user is `oai` (uid 1000).
- Hosting env vars present in the terminal container:
  - `EGRESS_LLM_API_ENDPOINT` — e.g. `http://egress-llm:9011` (v1 sandbox) or `http://localhost:9011`.
  - `APP_HOSTING_PORT_RANGE_START` / `_END` — e.g. `19101` / `19109`. The server **must** bind a
    port in this range or registration returns 400.
- Registration request body fields: `feature_kind="terminal"`, `feature_name="terminal-shell"`,
  `port=$APP_HOSTING_PORT_RANGE_START`, `path="/"`.
- Registration response: `{registered_app_id, app_url}`.

## Gotchas learned while building this

- **Do `pkill -f server.py` carefully.** A `bash -c` command line that contains the literal
  `server.py` matches its own process, so `pkill -f server.py` kills the running exec (exit `-15`).
  Prefer not killing, or match on a more specific pattern.
- **Write + start in one `exec` call.** Separate exec calls can land in different terminal
  sessions/mounts; a file written in call A may appear missing in call B. Combining the heredoc
  write and the `nohup` start in a single `bash -c` avoids this.
- **`files:write` (v3) is jailed to the working dir.** Writing to `/tmp/...` returns
  `403 PathNotInWorkingDIR`; use `/home/oai/share/...`. For the v1 flow, just use the exec heredoc.
- **v1 `batchUpload` (`/api/agent/storage/file/batchUpload`) returned 404** on
  `luminaserviceapi-test-centralus`. Use the exec/heredoc write (doc Option A) instead.
- **External `app_url` access returns the Entra sign-in page**, not the service body, when called
  with a LuminaServiceAPI-audience token. The proxy (`luminaproxyapi-*`) is fronted by an AAD
  gateway expecting a different audience. This is expected; the verification asserts the
  **in-sandbox** chain (server running + successful registration), not external proxy passthrough.

## What "passing" means

The scenario is verified when:
1. A token is obtained.
2. The sandbox is created (`initialize` 200, no `"status":"error"`).
3. The hosting env vars are present.
4. The local in-container `GET /health` returns `{"healthy":true}`.
5. Registration returns a JSON `{registered_app_id, app_url}` with no `error`/`Unauthorized`.
