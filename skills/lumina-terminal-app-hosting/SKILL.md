---
name: lumina-terminal-app-hosting
description: Verify the Lumina terminal app-hosting end-to-end scenario via the v1 legacy Agent API - acquire a Lumina bearer token, create a sandbox (POST /api/agent/computer/initialize), write and start a FastAPI server inside the terminal container, then register it with egress-llm (/app/register/agent) to obtain a public app_url. Use this skill when the user wants to test, validate, reproduce, or smoke-check the terminal-app-hosting flow described in docs/partner-sandbox/in-sandbox/terminal-app-hosting.md, when they mention registering an in-sandbox app or getting an app_url, or when checking whether a luminaserviceapi host can run this flow.
---

# Lumina Terminal App Hosting Verification

## Purpose

Run an end-to-end check of the Lumina **terminal app-hosting** scenario: stand up a custom HTTP
service inside a sandbox terminal container and register it through `egress-llm` to get a public
`app_url`. This mirrors `docs/partner-sandbox/in-sandbox/terminal-app-hosting.md`, driven via the
**v1 legacy Agent API** against a LuminaServiceAPI host.

## When to use

- The user asks to verify / test / reproduce the terminal-app-hosting flow, or to register an
  in-sandbox app and get an `app_url`.
- The user wants to confirm a given `luminaserviceapi-*` host can run this scenario.
- A change to the sandbox, egress-llm, or the doc needs a regression check.

## How to run

Prerequisites: `python` with `requests` (or `uv`), and either a bearer token or a CopilotLumina
worktree containing `get-lumina-token.ts` (plus `bun` for interactive sign-in).

The one-shot verifier is `scripts/verify_app_hosting.py`. It performs all steps and prints
`=== VERIFICATION PASSED ===` with the `app_url` on success, or `FAIL: ...` and a non-zero exit
on the first failing step.

Run from inside a CopilotLumina worktree so the token helper can be auto-located:

```bash
# Auto-acquire token via the bundled helper (browser sign-in may open):
python <skill>/scripts/verify_app_hosting.py --repo-root /path/to/CopilotLumina

# Reuse an existing token (no browser):
python <skill>/scripts/verify_app_hosting.py --token-file /path/to/auth_token.txt

# If requests is not installed:
uv run --with requests python <skill>/scripts/verify_app_hosting.py --token-file <file>
```

Useful flags: `--host <luminaserviceapi-host>` (default `luminaserviceapi-test-centralus.copilotlumina.com`),
`--computer-id <id>` to reuse an open sandbox, `--keep-sandbox` to skip release, `--json-out <path>`
to save results. The script releases the sandbox it created unless told to keep it.

## Critical facts (see `references/scenario.md` for full detail)

- **Use a LuminaServiceAPI host**, not a `luminaapi-*` (v3) host. v1 routes
  (`/api/agent/computer/initialize`, `/api/agent/container/exec`) are 404 on `luminaapi-*`.
- On `luminaserviceapi-test-centralus`, v1 `initialize` needs **no** `x-ms-lumina-*` headers, and
  egress-llm needs **no** `x-egress-token` — so the doc-exact registration curl works.
- The server must bind a port in `APP_HOSTING_PORT_RANGE_START`..`_END`; app code goes to
  `/home/oai/share/server.py`; register with `feature_kind="terminal"`, `feature_name="terminal-shell"`.
- Write-and-start the server in a **single** `exec` call, and avoid `pkill -f server.py` (it kills
  its own exec). These are real failure modes encountered and handled in the script.
- An external `GET app_url` returns the **Entra sign-in page** (the proxy is AAD-fronted, expecting a
  different audience). "Passing" therefore means the in-sandbox chain works: server healthy locally +
  registration returns `{registered_app_id, app_url}`.

Read `references/scenario.md` before adapting the flow to a new host or debugging a failure — it
records which hosts work, which don't, and why (egress token perms, region misroute, batchUpload 404).
