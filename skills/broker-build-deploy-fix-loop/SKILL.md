---
name: broker-build-deploy-fix-loop
description: "Run an autonomous build → deploy → validate → fix loop for the Lumina Sandbox Broker service in Azure DevOps (org O365exchange, project 'O365 Core'). Use when the user says things like '修改好后开始build, deploy, validation, fix循环', 'start the broker loop', 'keep iterating broker until it deploys and serves HTTP', or asks to drive broker build 54428 / deploy 54444 until the public URL returns a real response instead of the App Service holding page. Also use to resume the loop in a later session."
---

# Lumina Sandbox Broker — Build / Deploy / Validate / Fix Loop

Autonomously iterates on the LuminaSandboxBroker pipelines until the dev App Service serves the container (not the App Service holding page). On each iteration: push changes → queue build → queue deploy → HTTP-validate → diagnose failures → edit → repeat.

## How to run the loop

Schedule a recurring prompt so you get woken up every 3 minutes to make progress, then execute the first iteration immediately:

```
CronCreate(cron="*/3 * * * *",
           prompt="修改好后开始build, deploy, validation, fix循环",
           recurring=true)
```

Tell the user the job ID and that recurring tasks auto-expire after 7 days. The user can also paste `修改好后开始build, deploy, validation, fix循环` at any time to drive one iteration by hand.

**Per-iteration flow:**
1. Check current ADO build/deploy status (see pipeline IDs below).
2. If nothing is running and there are local edits → commit, push, queue build.
3. If build succeeded and no deploy running → queue deploy with the new image tag.
4. If deploy succeeded → HTTP-validate the public URL.
5. If any step failed → read logs, diagnose root cause, edit files, commit, push.
6. If everything is healthy → delete the cron job and report success.

**Deploy success requires BOTH jobs checked — not just `ReleaseJob_AgentRolloutJob`.** Ev2 deploys have a separate `ReleaseJob_Monitoring` job that runs post-rollout validation; it can have already failed while the overall state still shows `inProgress`. Do NOT wait for Monitoring to reach `completed` — inspect its log while it is running. Per deploy-check iteration:
1. Confirm `ReleaseJob_AgentRolloutJob` = succeeded via `get_build_timeline`.
2. Open the `ReleaseJob_Monitoring` / `Ev2Agentless` task log NOW (even while `inProgress`) and scan for error / failure lines. If errors are present, treat the deploy as failed immediately — do not keep waiting.
Skipping step 2, or waiting for Monitoring to "finish" before looking, has previously caused false "deploy succeeded" conclusions and wasted loop cycles.

## Pipelines & resources

| Item | Value |
|------|-------|
| Org | `https://dev.azure.com/o365exchange` |
| Project | `O365 Core` |
| Build pipeline | `54428` — `Lumina-SandboxBroker-Service-Build-Official` |
| Deploy pipeline (dev) | `54444` — `Lumina-SandboxBroker-Service-Dev-Deploy` |
| Deploy pipeline (test) | (separate; see README) |
| Branch (push target) | `u/lixiangliu/broker-pipeline` — repo policy rejects `marsiwe/*` refs, so push worktree branch to this namespace with `git push origin HEAD:refs/heads/u/lixiangliu/broker-pipeline` |
| Image tag format | `mcr.microsoft.com/luminasandboxservice/sandbox-broker:<build.number>-windows` |
| Dev App Service | `lumina-sandbox-broker-dev-westus2` (westus2) |
| Dev App Service URL | `https://lumina-sandbox-broker-dev-westus2.azurewebsites.net/` |
| Dev auth probe cert | Key Vault `lumina-dev` (subscription `e75c95f3-27b4-410f-a40e-2b9153a807dd`, RG `browser-tools`), secret `SelfSignedToken` — OneCertV2 leaf `CN=lumina.dev.azclient.ms` chained to CCME. Used by `probe_broker_auth.py` to mint x5c+token. |
| Resource Group | `LuminaBroker` (westus2) |
| ServiceTreeId | `b45dd1cf-bd2f-470b-a4fa-5f46dd07a3af` |
| Ev2 Service Connection (dev) | `LuminaSandbox-CORP-EV2-ServiceConnection` (Ev2Endpoint, bypasses Lockbox) |
| Dev subscription | `068366ea-b878-4e40-93a2-65ac7cf88f5b` |

## Key files (read before editing)

### Pipeline / deploy wiring
- `build/pipelines/sandbox/broker/README.md` — authoritative guide. Note: `queue_build` MCP tool rejects `--parameters`; use `az pipelines run` instead.
- `build/pipelines/sandbox/broker/release-pipelines/Deploy_LuminaSandboxBroker_Service.Dev.yml` — dev deploy entrypoint (NonOfficial template, Ev2 Test infra).
- `build/pipelines/sandbox/broker/release-pipelines/Deploy_LuminaSandboxBroker_Service.Test.yml` — test deploy entrypoint (Microsoft.Official + Lockbox).
- `build/pipelines/sandbox/broker/release-pipelines/Template-DeploySandboxBroker.yml` — shared stage. Uses `Ev2RARollout@2` with `ArtifactsVersionOverride: '$(build.BuildNumber)'`. Passes `ConfigurationOverrides` JSON containing `SubscriptionWorkload`, `ResourceGroup`, `AppService.{Name,PlanName,DockerImage}`.
- `build/pipelines/sandbox/broker/Ev2Artifacts/Templates/BrokerAppService.Template.json` — ARM template. Creates both `Microsoft.Web/serverfarms` (P3v3 Windows Container, `hyperV:true`) and `Microsoft.Web/sites` (kind `app,container,windows`, `windowsFxVersion: DOCKER|<image>`). App settings include `WEBSITES_ENABLE_APP_SERVICE_STORAGE=false` and `WEBSITES_PORT=8080`.
- `build/pipelines/sandbox/broker/Ev2Artifacts/ConfigStorePayload/Microsoft.Azure.SandboxBroker.ServiceScope.Config.json` — Ev2 config shell; values injected via `ConfigurationOverrides` in the deploy template.
- `build/pipelines/sandbox/broker/Ev2Artifacts/Parameters/*.Parameters.json` — per-ring ARM parameter files.
- `build/pipelines/sandbox/broker/Ev2Artifacts/sandbox-broker.rolloutspec.json` — rollout spec (targets BrokerAppService service resource).

### Container source
- `sources/dev/LuminaService/LuminaSandboxBroker/DockerBuildConfigs/Dockerfile` — Windows Server Core 2022 + .NET 8 ASP.NET base. **Must have `EXPOSE 8080`** and `CONFIG_PATH=appsettings.json` / `SECRETS_PATH=appsecrets.json` (the `.dev.json` variants don't exist in `Config/`).
- `sources/dev/LuminaService/LuminaSandboxBroker/Entrypoint.ps1` — runs `dotnet LuminaSandboxBroker.dll --config-path $env:CONFIG_PATH --development`.
- `sources/dev/LuminaService/LuminaSandboxBroker/Config/` — only `appsettings.json`, `appsettings.local.json`, `appsecrets.json`, `appsecrets.local.json` exist.
- `sources/dev/LuminaService/LuminaSandboxBroker/Config/appsettings.json` — `LBProbePort:8080`, `SSLPort:443`, YARP catch-all → `https://localhost:8443`.

## Commands cheat-sheet

```bash
# Commit + push (to allowed u/ namespace)
git add -u && git commit -m "<msg>"
git push origin HEAD:refs/heads/u/lixiangliu/broker-pipeline

# Queue build
az pipelines run --org https://dev.azure.com/o365exchange --project "O365 Core" \
  --id 54428 --branch u/lixiangliu/broker-pipeline \
  --query "{id:id,buildNumber:buildNumber,status:status}" -o json

# Check build
az pipelines build show --org https://dev.azure.com/o365exchange --project "O365 Core" \
  --id <build-id> --query "{status:status,result:result,buildNumber:buildNumber}" -o json

# Queue dev deploy (dockerImage REQUIRED — empty value → windowsFxVersion "DOCKER|" → ARM failure)
az pipelines run --org https://dev.azure.com/o365exchange --project "O365 Core" \
  --id 54444 --branch u/lixiangliu/broker-pipeline \
  --parameters dockerImage=mcr.microsoft.com/luminasandboxservice/sandbox-broker:<build-number>-windows \
  --query "{id:id,status:status}" -o json

# Validate HTTP (anonymous — expect 401 from the broker's auth handler)
curl -sS -o /dev/null -w "%{http_code}\n" https://lumina-sandbox-broker-dev-westus2.azurewebsites.net/

# Authenticated x5c+token probe — expect HTTP 200 "Healthy"
# Mints a JWT from the dev SelfSignedToken Key Vault cert and calls /healthz/ready
# with x-ms-lumina-target-host / x-ms-lumina-sandbox-broker-token / x-ms-lumina-x5c.
python "$CLAUDE_SKILL_DIR/probe_broker_auth.py"

# Extended auth regression matrix — 14 scenarios (happy path, missing headers,
# claim mismatches, expired/nbf-future, tampered sig/claims, unknown kid,
# orchestrator RBAC). Imports probe_broker_auth.py as a module. Expect 14/14.
# Needs PYTHONIOENCODING=utf-8 on Windows consoles (cp1252 can't encode arrows).
PYTHONIOENCODING=utf-8 python "$CLAUDE_SKILL_DIR/broker_auth_matrix.py"

# Pull platform / container logs when deploy succeeds but URL returns holding page
az webapp log download --resource-group LuminaBroker --name lumina-sandbox-broker-dev-westus2 --log-file logs.zip

# Stream container stdout/stderr live (captures dotnet output after the entrypoint fix)
az webapp log tail --resource-group LuminaBroker --name lumina-sandbox-broker-dev-westus2
```

## Known failure modes & fixes (for the "fix" phase)

| Symptom | Root cause | Fix |
|---------|-----------|-----|
| Build: `unauthorized` pushing to ACR | Missing serviceConnection for ACR | Use `1ES.PushContainerImage` pattern with `obsprdue2oe1.azurecr.io` regional endpoint. See commits `afcc14e6f`, `38f5fb495`. |
| Deploy: `ArtifactsVersion is required` | Ev2RARollout needs explicit version | `ArtifactsVersionOverride: '$(build.BuildNumber)'` in `Template-DeploySandboxBroker.yml`. |
| Deploy: Lockbox approval prompt in dev | dev ring was using LockboxService | For `ring == 'dev'` use `EndpointProviderType: Ev2Endpoint` + `ConnectedServiceName: 'LuminaSandbox-CORP-EV2-ServiceConnection'`. |
| Deploy: `InternalSubscriptionIsOverQuotaForSku` / PremiumV3 VMs limit 0 | eastus2 has no P3v3 quota in dev subscription | Switched region defaults to `westus2`. |
| Deploy: ARM `windowsFxVersion: "DOCKER|"` error | Empty `dockerImage` parameter | Always pass `dockerImage=<full-tag>` to pipeline 54444. |
| Public URL returns 202 "App Service Container" holding page forever | Container has no exposed port → App Service treats as background worker | `EXPOSE 8080` in Dockerfile + `WEBSITES_PORT=8080` app setting in ARM template. |
| Container entrypoint exits ~30s after start | `CONFIG_PATH=appsettings.dev.json` doesn't exist in image | Dockerfile must set `CONFIG_PATH=appsettings.json` and `SECRETS_PATH=appsecrets.json`. |
| After deploy: HTTP 502 even though dotnet started and served 1–2 requests | Entrypoint.ps1 was redirecting dotnet stdout/stderr to SMB-mounted `C:\home\LogFiles`; transient share I/O errors killed PowerShell+dotnet, and the old `while($true) Sleep` loop kept the container alive with nothing on port 8080 | Entrypoint.ps1 must (a) NOT pipe dotnet streams to `$logFile` and (b) wrap dotnet in a relaunch loop so a crash re-binds 8080. See commit `3812383f1`. |
| Authenticated probe returns 401 "x5c certificate chain validation failed" or "Subject does not match" | New dev/test CN not in `ValidSubjectNames`, or `RootCACertCache` reading wrong JSON field | Add CN to `appsettings.{env-region}.json` overlay (loaded via `LUMINA_CONFIG_SUFFIX` env var). Verify `RootCACertCache` reads `PEM` field from `https://issuer.pki.azure.com/dsms/issuercertificates?getissuersv3&cloudName=public&appType=clientauth` (NOT `Certificate`). |

## Success criteria

Loop exits (and the cron job should be deleted with `CronDelete`) when all of the following hold:
1. Latest build of 54428 on the target branch is `succeeded`.
2. Latest deploy of 54444 is `succeeded`.
3. `curl https://lumina-sandbox-broker-dev-westus2.azurewebsites.net/` returns a non-holding-page response (status code from the app itself, e.g. 401/200/404 from YARP — NOT the 202 "App Service Container" HTML page).
4. `python probe_broker_auth.py` (in this skill dir) returns HTTP 200 "Healthy" — this exercises the full auth path: x5c chain parse, root CA cache lookup (`PEM` field), subject allowlist from the `LUMINA_CONFIG_SUFFIX` overlay, JWT signature + issuer/audience check, then YARP forward to `/healthz/ready`. If (3) is green but (4) fails with 401/403, the broker is serving traffic but auth config is broken — debug `X5cChainValidator`, `RootCACertCache`, or the overlay `ValidSubjectNames` rather than the platform.
5. (Optional, for auth-touching changes) `PYTHONIOENCODING=utf-8 python broker_auth_matrix.py` reports 14/14 passed. This covers negative paths (missing headers, expired/nbf-future tokens, tampered sig/claims, unknown kid, wrong aud/iss, orchestrator RBAC) so a regression that accidentally accepts invalid auth is caught. Run whenever touching `X5cChainValidator`, `RootCACertCache`, token validation, or the overlay `ValidSubjectNames`.

## Notes

- Today's worktree path may change across sessions; always re-derive from `pwd`. Skill assumes you're inside a `CopilotLumina` worktree.
- If you land on the `master` branch, create a fresh `u/lixiangliu/broker-pipeline` branch before pushing.
- The user has confirmed region flip to westus2 is acceptable; don't ask again.
- The user prefers terse status updates per iteration — one sentence: what you checked, what you did next.
