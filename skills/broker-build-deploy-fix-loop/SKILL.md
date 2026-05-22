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

**Deploy success requires BOTH jobs checked — not just `ReleaseJob_AgentRolloutJob`.** Ev2 deploys have a separate `ReleaseJob_Monitoring` job that runs post-rollout validation; it can have already failed while the overall state still shows `inProgress`. Per deploy-check iteration:
1. Confirm `ReleaseJob_AgentRolloutJob` = succeeded via `get_build_timeline`.
2. Open the `ReleaseJob_Monitoring` / `Ev2Agentless` task log NOW (even while `inProgress`) and scan for error / failure lines.
   - **If errors are present** → treat the deploy as **failed immediately** — do not keep waiting.
   - **If the log is clean (no errors)** → this does NOT mean the deploy succeeded. It only means no failure yet. You MUST wait for the overall deploy build to reach `status: completed, result: succeeded` before proceeding to HTTP validation. Do NOT validate the endpoint early based on a clean Monitoring log — the Ev2 rollout (including slot swap, health checks, etc.) may still be in progress.
3. Only after the deploy build shows `completed` + `succeeded`, proceed to HTTP validation and auth probes.

Previously, treating "Monitoring log clean" as "deploy succeeded" caused premature validation — the endpoint happened to work because the previous deployment was still live, masking potential issues with the new rollout.

## Pipelines & resources

| Item | Value |
|------|-------|
| Org | `https://dev.azure.com/o365exchange` |
| Project | `O365 Core` |
| Build pipeline | `54428` — `Lumina-SandboxBroker-Service-Buddy-Build` (Test branch builds; old name was `-Test-Build`) |
| Deploy pipeline (dev) | `54444` — `Lumina-SandboxBroker-Service-Dev-Deploy` |
| Deploy pipeline (test) | (separate; see README) |
| Branch (push target) | Derive dynamically: run `git rev-parse --abbrev-ref --symbolic-full-name @{u}` to get the current branch's upstream, strip the `origin/` prefix, and use that as the push target. If no upstream is set, ask the user. Push with `git push origin HEAD:refs/heads/<upstream-branch>`. |
| Image tag format | `mcr.microsoft.com/luminasandboxservice/sandbox-broker:<build.number>-windows` (CDP semver since 2026-05; old `<yyyymmdd>.<n>` retired) |
| Dev App Service | `lumina-sandbox-broker-ase-dev-westus2` (ASE-hosted; old multi-tenant `lumina-sandbox-broker-dev-westus2` decommissioned) |
| Dev App Service URL | `https://lumina-sandbox-broker-ase-dev-westus2.lumina-broker-ase-dev-westus2.p.azurewebsites.net/` (note `.p.azurewebsites.net` — ASE v3 Site suffix, NOT `.appserviceenvironment.net` which is the ASE control-plane domain) |
| Dev ASE | `lumina-broker-ase-dev-westus2` (kind `ASEV3`, External VIP, RG `LuminaBroker`) |
| Dev VNet / NSG / Subnet | `lumina-broker-vnet-dev-westus2` / `lumina-broker-nsg-dev-westus2` / `ase-subnet` (10.50.0.0/24) |
| Dev BYO PIP (Phase B) | `lumina-broker-pip-dev-westus2` (only when `createAseInboundPip=true`; default off in dev) |
| Dev ASP | `lumina-sandbox-broker-plan-ase-dev-westus2` (IsolatedV2 I1v2, Windows hyperV) |
| Dev MI | `lumina-sandbox-broker-ase-dev-westus2-mi` (`<webapp>-mi` convention) |
| Dev auth probe cert | Key Vault `lumina-dev` (subscription `e75c95f3-27b4-410f-a40e-2b9153a807dd`, RG `browser-tools`), secret `SelfSignedToken` — OneCertV2 leaf `CN=lumina.dev.azclient.ms` chained to CCME. Used by `probe_broker_auth.py` to mint x5c+token. |
| Resource Group | `LuminaBroker` (westus2) |
| ServiceTreeId | `b45dd1cf-bd2f-470b-a4fa-5f46dd07a3af` |
| Ev2 Service Connection (dev) | `LuminaSandbox-CORP-EV2-ServiceConnection` (Ev2Endpoint, bypasses Lockbox) |
| Dev subscription | `068366ea-b878-4e40-93a2-65ac7cf88f5b` |

## Key files (read before editing)

### Pipeline / deploy wiring
- `build/pipelines/sandbox/broker/README.md` — authoritative guide. Note: `queue_build` MCP tool rejects `--parameters`; use `az pipelines run` instead.
- `build/pipelines/sandbox/broker/release-pipelines/Deploy_LuminaSandboxBroker_Service.Dev.yml` — dev deploy entrypoint (NonOfficial template, Ev2 Test infra). Has `createAseInboundPip` queue-time parameter (default `false`).
- `build/pipelines/sandbox/broker/release-pipelines/Deploy_LuminaSandboxBroker_Service.Test.yml` — test deploy entrypoint (Microsoft.Official + Lockbox). `createAseInboundPip` is a `readonly` compile-time variable locked to `true` (Phase B).
- `build/pipelines/sandbox/broker/release-pipelines/Deploy_LuminaSandboxBroker_Service.Official.yml` — official deploy (Test/SDF/MSIT/Prod, 18 ring/region call sites). Same variable-lock pattern.
- `build/pipelines/sandbox/broker/release-pipelines/Template-DeploySandboxBroker.yml` — shared stage. Uses `Ev2RARollout@2` with `ArtifactsVersionOverride: '$(build.BuildNumber)'`. `ConfigurationOverrides` JSON now includes both `AppService.{Name,PlanName,DockerImage,...}` AND `BrokerAseInfra.{VnetName,VnetAddressPrefix,AseSubnetName,AseSubnetPrefix,NsgName,AseName,AppServicePlanSku,AppServicePlanCapacity,AllowedSourceCidrs,CreateAseInboundPip,InboundPipName}`.
- `build/pipelines/sandbox/broker/Ev2Artifacts/Templates/BrokerAseInfra.Template.json` — ARM template for VNet + ase-subnet + NSG + ASE v3 + ASP. Conditional PIP resource (gated on `createAseInboundPip`) carries `ipTags=[{ipTagType:"FirstPartyUsage", tag:"/Lumina"}]`. ASE properties built via `if(createAseInboundPip, union(base, byo), base)`. **`virtualNetwork.id` MUST be the subnet resource ID, NOT the VNet ID** (ARM `Microsoft.Web/hostingEnvironments@2024-04-01` write-side requirement; contradicts schema reference doc). **`networkingConfiguration.inboundIpAddressOverride` MUST be FLAT** (no `.properties` wrapper); `.properties` wrapper causes ARM/CRP to silently drop the field.
- `build/pipelines/sandbox/broker/Ev2Artifacts/Templates/BrokerAppService.Template.json` — ARM template for Site (and optional staging slot). Site binds to ASE via `hostingEnvironmentProfile: { id: <ase-resource-id> }`. App Service Plan is created in `BrokerAseInfra` (NOT here). App settings include `WEBSITES_ENABLE_APP_SERVICE_STORAGE=false` and `WEBSITES_PORT=8080`.
- `build/pipelines/sandbox/broker/Ev2Artifacts/ConfigStorePayload/Microsoft.Azure.SandboxBroker.ServiceScope.Config.json` — Ev2 config shell; values injected via `ConfigurationOverrides` in the deploy template.
- `build/pipelines/sandbox/broker/Ev2Artifacts/Parameters/BrokerAseInfra.Parameters.json` — placeholders: `__VNET_NAME__`, `__ASE_NAME__`, `__ALLOWED_SOURCE_CIDRS__`, `__CREATE_ASE_INBOUND_PIP__`, `__INBOUND_PIP_NAME__`, etc. **Bool placeholder MUST be wrapped in `[bool(toLower('...'))]`** — Ev2 substitutes as `"False"` (capital F) via REST API queue path; ARM `bool()` only accepts lowercase.
- `build/pipelines/sandbox/broker/Ev2Artifacts/Parameters/BrokerAppService.Parameters.json` — per-ring ARM parameter file for Site. Must reference `__ASE_NAME__` for `hostingEnvironmentProfile`.
- `build/pipelines/sandbox/broker/Ev2Artifacts/sandbox-broker.scopebindings.json` — placeholder→config bindings. **`__ASE_NAME__` MUST be bound under BOTH `BrokerAseInfra` AND `BrokerAppService` scope tags** (cross-scope reference).
- `build/pipelines/sandbox/broker/Ev2Artifacts/sandbox-broker.rolloutspec.json` — rollout spec: `DeployBrokerAseInfra` → `DeployBrokerAppService` → `BrokerExecuteShell` (in order).

### Container source
- `sources/dev/LuminaService/LuminaSandboxBroker/DockerBuildConfigs/Dockerfile` — Windows Server Core 2022 + .NET 8 ASP.NET base. **Must have `EXPOSE 8080`** and `CONFIG_PATH=appsettings.json` / `SECRETS_PATH=appsecrets.json` (the `.dev.json` variants don't exist in `Config/`).
- `sources/dev/LuminaService/LuminaSandboxBroker/Entrypoint.ps1` — runs `dotnet LuminaSandboxBroker.dll --config-path $env:CONFIG_PATH --development`.
- `sources/dev/LuminaService/LuminaSandboxBroker/Config/` — only `appsettings.json`, `appsettings.local.json`, `appsecrets.json`, `appsecrets.local.json` exist.
- `sources/dev/LuminaService/LuminaSandboxBroker/Config/appsettings.json` — `LBProbePort:8080`, `SSLPort:443`, YARP catch-all → `https://localhost:8443`.

## Commands cheat-sheet

```bash
# Derive upstream branch name (strip origin/ prefix)
UPSTREAM=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} | sed 's|^origin/||')

# Commit + push (to upstream branch)
git add -u && git commit -m "<msg>"
git push origin HEAD:refs/heads/$UPSTREAM

# Queue build
az pipelines run --org https://dev.azure.com/o365exchange --project "O365 Core" \
  --id 54428 --branch $UPSTREAM \
  --query "{id:id,buildNumber:buildNumber,status:status}" -o json

# Check build
az pipelines build show --org https://dev.azure.com/o365exchange --project "O365 Core" \
  --id <build-id> --query "{status:status,result:result,buildNumber:buildNumber}" -o json

# Queue dev deploy (dockerImage REQUIRED — empty value → windowsFxVersion "DOCKER|" → ARM failure)
# Always pass enableSlotSwap=true for zero-downtime deploys.
# NOTE: `az pipelines run --parameters` concatenates all values into one string,
# corrupting the docker image tag. Use the REST API with templateParameters instead.
TOKEN=$(az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798 --query accessToken -o tsv)
curl -sS -X POST "https://dev.azure.com/o365exchange/O365%20Core/_apis/build/builds?api-version=7.1" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "definition":{"id":54444},
    "sourceBranch":"refs/heads/<UPSTREAM>",
    "templateParameters":{
      "dockerImage":"mcr.microsoft.com/luminasandboxservice/sandbox-broker:<build-number>-windows",
      "enableSlotSwap":"true"
    }
  }'

# Validate HTTP (anonymous — expect 401 from the broker's auth handler)
curl -sS -o /dev/null -w "%{http_code}\n" https://lumina-sandbox-broker-ase-dev-westus2.lumina-broker-ase-dev-westus2.p.azurewebsites.net/

# Authenticated x5c+token probe — expect HTTP 200 "Healthy"
# Mints a JWT from the dev SelfSignedToken Key Vault cert and calls /healthz/ready
# with x-ms-lumina-sandbox-target-uri / x-ms-lumina-sandbox-broker-token / x-ms-lumina-sandbox-broker-token-x5c.
# Override BROKER_HOST env var to target a different ring/ASE.
python "$CLAUDE_SKILL_DIR/probe_broker_auth.py"

# Extended auth regression matrix — 14 scenarios (happy path, missing headers,
# claim mismatches, expired/nbf-future, tampered sig/claims, unknown kid,
# orchestrator RBAC). Imports probe_broker_auth.py as a module. Expect 14/14.
# Needs PYTHONIOENCODING=utf-8 on Windows consoles (cp1252 can't encode arrows).
PYTHONIOENCODING=utf-8 python "$CLAUDE_SKILL_DIR/broker_auth_matrix.py"

# SSE end-to-end streaming probe — exercises broker auth + YARP SSE route with
# Accept: text/event-stream against a live SSE upstream. Expect HTTP 200,
# content-type text/event-stream, and first non-empty SSE line within 30s.
# Wikimedia rejects default Python urllib User-Agent with 403, so the script
# sends a named SSE probe User-Agent. Override SSE_TARGET_URI for a controlled
# upstream or BROKER_HOST for a different broker ring/region.
PYTHONIOENCODING=utf-8 python "$CLAUDE_SKILL_DIR/broker_sse_probe.py"

# Pull platform / container logs when deploy succeeds but URL returns holding page
az webapp log download --resource-group LuminaBroker --name lumina-sandbox-broker-ase-dev-westus2 --log-file logs.zip

# Stream container stdout/stderr live (captures dotnet output after the entrypoint fix)
az webapp log tail --resource-group LuminaBroker --name lumina-sandbox-broker-ase-dev-westus2

# ASE health check (Status, kind, internalLoadBalancingMode, inboundIpAddress)
az appservice ase show -g LuminaBroker -n lumina-broker-ase-dev-westus2 \
  --query "{status:status, kind:kind, ilbMode:internalLoadBalancingMode, vip:networkingConfiguration.externalInboundIpAddresses}" -o json

# Verify BYO PIP binding (only meaningful when createAseInboundPip=true was deployed)
az network public-ip show -g LuminaBroker -n lumina-broker-pip-dev-westus2 \
  --query "{ip:ipAddress, ipTags:ipTags, ipConfig:ipConfiguration.id}" -o json

# Find recent ARM deployments under LuminaBroker (use this when monitoring log shows "Failed" without specific error)
az deployment group list -g LuminaBroker --query "[0:5].{name:name, state:properties.provisioningState, ts:properties.timestamp, errorMsg:properties.error.message}" -o table
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
| Deploy: ARM `Cannot find hostingEnvironments with name __ASE_NAME__` | `__ASE_NAME__` placeholder bound only under `BrokerAseInfra` scope tag, but `BrokerAppService` SRD also references it | In `sandbox-broker.scopebindings.json`, duplicate the binding so `__ASE_NAME__` is bound under BOTH `BrokerAseInfra` AND `BrokerAppService` scope tags. |
| Deploy: ARM parameters JSON parse fails on `"value": "["AzureCloud"]"` | Ev2 placeholder substitution is literal string replacement; nested JSON arrays escape incorrectly | In ARM template, declare param as `string` and use `split(',')` to convert CSV at runtime (e.g. `allowedSourceCidrs` is `"0.0.0.0/0,10.0.0.0/8"` string, ARM splits to array). |
| Deploy: ARM "Expected a value of type 'Boolean', but received a value of type 'String'" on `createAseInboundPip` | Ev2 substitutes `__CREATE_ASE_INBOUND_PIP__` as `"False"` (capital F via REST API queue path); ARM `bool('False')` returns string, not bool (function only accepts lowercase `'true'`/`'false'` or `0`/`1`) | Wrap with `toLower()` in `BrokerAseInfra.Parameters.json`: `"value": "[bool(toLower('__CREATE_ASE_INBOUND_PIP__'))]"`. Case-insensitive across both ADO UI checkbox and REST API queue paths. |
| Deploy: NSG rule rejected "InvalidNetworkSecurityGroupSecurityRule" with `sourceAddressPrefix: AzureCloud` (or any other system Service Tag) | Azure NSG plural `sourceAddressPrefixes` (array) is **CIDR-only** — does NOT accept service tags; only the singular `sourceAddressPrefix` (string) accepts service tags, one per rule | Use CIDR list `0.0.0.0/0` initially, NSG flow logs to learn actual sandbox NAT egress, then narrow CIDR. For service-tag allow-list: emit one NSG rule per tag using singular `sourceAddressPrefix`. |
| Deploy: ARM "virtualNetwork.Id is invalid. For this api-version, the virtualNetwork.Id must refer to a subnet" on ASE create | Schema reference doc says `virtualNetwork.id` is the VNet ID with separate `.subnet` field; that's WRONG for write-side. ARM `Microsoft.Web/hostingEnvironments@2024-04-01` requires `virtualNetwork.id` to be the SUBNET resource ID directly | In ARM template: `"virtualNetwork": { "id": "[variables('subnetId')]" }` (NOT VNet ID). Confirmed via throwaway A/B deploy 2026-05-09. |
| Deploy: ASE comes up but `inboundIpAddressOverride` reads back as `null`; PIP unbound | `networkingConfiguration` was wrapped in `.properties` per ARM schema reference doc; that's read-side serialization only. ARM/CRP silently DROPS the field with the `.properties` wrapper | In ARM template, write FLAT: `"networkingConfiguration": { "inboundIpAddressOverride": "[variables('inboundPipId')]" }` (NOT `.networkingConfiguration.properties.inboundIpAddressOverride`). Confirmed via throwaway A/B deploy 2026-05-09. |
| Operator: ASE inbound IP needs to change after ASE create | `inboundIpAddressOverride` is **create-time-only** at the Microsoft.Web/hostingEnvironments resource | ASE must be deleted and recreated. Plan for ~30 min broker downtime per region OR stand up a parallel ASE on a different `aseName` and ConfigMap-swap traffic before deleting the old one. |
| Deploy: PIP create fails with `InvalidIpTag` referencing `/Lumina` | IPAM `/Lumina` reservation not yet `ReadyToUse` in this subscription; `ipTags=[{tag:/Lumina}]` requires the tag to be registered | Wait for IPAM `/Lumina` to reach `ReadyToUse` (or use a different pre-registered tag for testing). PR can sit merged — failure is a recoverable pipeline error per re-run. |
| Deploy: "ContainerImageError; Repository/Tag is invalid; NotFound" mid-week | MCR weekly Saturday cleanup deleted the buddy-build image tag (older than the most recent Saturday) | Re-build broker before re-deploying across a Saturday boundary. CDP semver image tags are like `1.0.03415.1-windows`. |
| Deploy: BrokerAseInfra step "Failed" in monitoring log but no detailed error | Ev2 monitoring log only surfaces "Status: Failed"; root cause is in Ev2 portal or ARM activity log | Open Ev2 portal: `https://ra.ev2portal.azure.net/#/rollouts/Test/<ServiceTreeId>/<ServiceGroup>/<RolloutId>` (rollout ID printed in build log). For ARM-level errors: `az deployment group list -g LuminaBroker --query "[0:5].{name,state:properties.provisioningState,errorMsg:properties.error.message}" -o table`. If the ARM deployment record is missing, the failure was at Ev2 layer (parameter binding / scope binding / config lookup) BEFORE ARM submission. |
| Operator: First ASE create takes much longer than initial deploy | Documentation says 60-90 min; actual measured ~30 min on dev (2026-05-09). Subsequent redeploys are ~9 min (idempotent ARM no-op) | Just wait. Pipeline shows "running" for 30+ min during first ASE create — DO NOT cancel. |

## Success criteria

Loop exits (and the cron job should be deleted with `CronDelete`) when all of the following hold:
1. Latest build of 54428 on the target branch is `succeeded`.
2. Latest deploy of 54444 is `succeeded` (BOTH `ReleaseJob_AgentRolloutJob` AND `ReleaseJob_Monitoring` clean — see deploy-success rule above).
3. `curl https://lumina-sandbox-broker-ase-dev-westus2.lumina-broker-ase-dev-westus2.p.azurewebsites.net/` returns a non-holding-page response (status code from the app itself, e.g. 401/200/404 from YARP — NOT the 202 "App Service Container" HTML page).
4. `python probe_broker_auth.py` returns HTTP 200 "Healthy" — exercises the full auth path. If (3) is green but (4) fails with 401/403, debug `X5cChainValidator`, `RootCACertCache`, or the overlay `ValidSubjectNames` rather than the platform.
5. (Optional, for auth-touching changes) `PYTHONIOENCODING=utf-8 python broker_auth_matrix.py` reports 14/14 passed.
6. (For SSE / streaming changes) `PYTHONIOENCODING=utf-8 python broker_sse_probe.py` reports `SSE probe passed` — this validates broker auth + YARP SSE route matching + non-buffered event delivery using a real `text/event-stream` upstream. If Wikimedia returns 403, keep the explicit probe User-Agent or set `SSE_TARGET_URI` to a controlled SSE endpoint.
7. (Phase B / IPAM-touching deploys only) `az network public-ip show -g LuminaBroker -n lumina-broker-pip-<ring>-<region>` returns `ipTags` containing `{ipTagType: FirstPartyUsage, tag: /Lumina}` AND `ipConfiguration` is non-null (bound to the ASE swift LB), AND `ipAddress` matches the ASE inbound VIP from `az appservice ase show`.

## Notes

- Today's worktree path may change across sessions; always re-derive from `pwd`. Skill assumes you're inside a `CopilotLumina` worktree.
- If you land on the `master` branch, create a fresh branch and set upstream before pushing.
- The user has confirmed region flip to westus2 is acceptable; don't ask again.
- The user prefers terse status updates per iteration — one sentence: what you checked, what you did next.
