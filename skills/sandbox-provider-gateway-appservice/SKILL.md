---
name: sandbox-provider-gateway-appservice
description: "Drive the CopilotLumina SandboxProviderGateway App Service workflow end-to-end: code/image coexistence changes, infra artifact build, SandboxACIInfra dev deploy pipeline 54477, App Service log diagnosis, health/API/business validation, and observability checks. Use this skill whenever the user mentions build\\pipelines\\infra\\deploy\\MOBR-Deployment.SandboxACIInfra.Dev.yml, SandboxProviderGateway, App Service image deployment, App Service code deployment, pipeline 54477, build/deploy/validation, App Service logs, or validating /healthz or /connect for the gateway."
---

# SandboxProviderGateway App Service Build / Deploy / Validate

Use this skill to modify, build, deploy, and validate `sources/dev/LuminaService/SandboxProviderGateway` App Service deployments in CopilotLumina. The workflow is intentionally end-to-end: do the code/infra change, build the infra artifact, deploy through the dev SandboxACIInfra pipeline, validate the running App Services, and diagnose failures from logs before declaring success.

## Core facts

| Item | Value |
|------|-------|
| Azure DevOps org | `https://dev.azure.com/O365exchange` / `https://o365exchange.visualstudio.com/DefaultCollection` |
| Project | `O365 Core` |
| Deploy pipeline | `54477` - `SandboxACIInfra-Deploy-Dev` / `MOBR-Deployment.SandboxACIInfra.Dev.yml` |
| Build pipeline | `51424` - infra build that produces `LuminaInfra-Build-Buddy` / `PrimaryArtifact` |
| Source service | `sources\dev\LuminaService\SandboxProviderGateway` |
| Deploy YAML | `build\pipelines\infra\deploy\MOBR-Deployment.SandboxACIInfra.Dev.yml` |
| Shared deploy template | `build\pipelines\infra\deploy\Template-DeploySandboxACIInfra.yml` |
| ARM template | `build\pipelines\infra\Ev2Artifacts\Templates\AppService.Template.json` |

The deploy pipeline consumes a previously built infra artifact. After changing Ev2, ARM, scripts, pipeline YAML, or the gateway zip packaging, run the build pipeline first, then run deploy pipeline 54477 with the fresh artifact/build number.

## When starting work

1. Inspect the current branch and local changes. Do not overwrite unrelated edits.
2. Read the relevant files before editing:
   - `build\pipelines\infra\deploy\MOBR-Deployment.SandboxACIInfra.Dev.yml`
   - `build\pipelines\infra\deploy\Template-DeploySandboxACIInfra.yml`
   - `build\pipelines\infra\build\Template-BuildInfra.yml`
   - `build\pipelines\infra\Ev2Artifacts\Templates\AppService.Template.json`
   - `build\pipelines\infra\Ev2Artifacts\Parameters\AppService.Parameters.json`
   - `build\pipelines\infra\Ev2Artifacts\ScopeBindings\sandboxaci-infra.scopebindings.json`
   - `build\pipelines\infra\Ev2Artifacts\ConfigStorePayload\Microsoft.Azure.SandboxACIInfra.ServiceScope.Config.json`
   - `build\pipelines\infra\Ev2Artifacts\Scripts\appservice_slot_swap.sh`
   - `build\pipelines\infra\Ev2Artifacts\Scripts\shellext.sh`
   - `sources\dev\LuminaService\SandboxProviderGateway\Hosting\Startup.cs`
   - `sources\dev\LuminaService\SandboxProviderGateway\Hosting\ContainerProxyHostBuilder.cs`
   - `sources\dev\LuminaService\SandboxProviderGateway\Configuration\ProxyRouteConfiguration.cs`
   - `sources\dev\LuminaService\SandboxProviderGateway\Yarp\ContainerAddressTransformer.cs`
   - `sources\dev\LuminaService\SandboxProviderGateway\Config\appsettings.json`
3. If the user asks to "trigger", "build deploy", or "deploy validation" after edits, assume they mean this build-then-deploy flow unless they explicitly name another pipeline.

## Implementation guidance

### Code and image App Service deployments must coexist

Do not model code deployment and image deployment as a switch that overwrites one instance. The intended shape is:

- Image App Service keeps the generated `appName`.
- Code App Service uses a distinct name, usually `appName + "-code"` via a configurable suffix such as `codeAppNameSuffix`.
- Code deployment has its own App Service Plan, App Service, and staging slot.
- The compiled gateway artifact is a zip deployed into the code App Service. It does not run in a container.

When touching the ARM template, keep image and code app settings separate enough that the two instances can be validated independently.

### Code App Service runtime requirements

For the code App Service and its staging slot, explicitly set:

```json
"netFrameworkVersion": "v8.0",
"use32BitWorkerProcess": false
```

The staging slot may not inherit these settings reliably. Missing slot runtime settings have caused `HTTP Error 500.30 - ASP.NET Core app failed to start` and CoreCLR load failures after zip deploy.

### Gateway behavior to preserve

`SandboxProviderGateway` exposes:

- `/healthz/ready`
- `/healthz/live`
- `/connect/{**catch-all}` reverse proxy route

The `/connect` route is behind R9/default authorization. It requires the `Container-Host` header, strips the `/connect` prefix, validates the host IP and port, removes the caller token and `Container-Host` header before forwarding, and proxies to `https://{ContainerHost}`. Do not weaken the SSRF protections while making deployment changes.

Important validation outcomes:

| Probe | Expected |
|-------|----------|
| No auth on `/` or `/connect` | `401` |
| Valid auth plus blocked IP `169.254.169.254:8002` | `400 ContainerHostBlocked` |
| Valid auth plus loopback `127.0.0.1:8002` | `400 ContainerHostBlocked` |
| Valid auth plus blocked port `10.0.0.4:443` | `400 PortBlocked` |
| Valid auth plus allowed private IP with no live target | `502 ProxyError` after forwarding attempt |
| Valid auth plus real sandbox private `IP:port` | Target API response |

If a request without `Container-Host` returns `404`, that can be YARP route matching behavior because the route requires the header. Use the other authenticated negative tests to prove the transformer is reached.

### Observability changes

When the user asks for App Service logs, monitor, App Insights, diagnostics, or common observability, wire all of these surfaces together:

- Log Analytics workspace for the deployment.
- App Insights components for image and code App Services.
- `APPLICATIONINSIGHTS_CONNECTION_STRING` and service-name app settings on production and staging slots.
- App Service application logs, HTTP logs, detailed errors, and failed request tracing.
- Diagnostic settings for App Service logs and `AllMetrics` into Log Analytics.
- Gateway code telemetry, preferably through OpenTelemetry Azure Monitor exporter when an App Insights connection string is present.

Avoid adding diagnostic categories that are SKU- or Defender-specific unless the target environment supports them.

## Build and deploy flow

### Local validation before pushing

Run only existing validations. At minimum:

```powershell
dotnet build sources\dev\LuminaService\SandboxProviderGateway\SandboxProviderGateway.csproj -c Release -p:Platform=x64 --no-incremental
git --no-pager diff --check
```

For JSON files touched under `build\pipelines\infra\Ev2Artifacts`, parse them:

```powershell
Get-ChildItem build\pipelines\infra\Ev2Artifacts -Recurse -Include *.json |
  ForEach-Object { Get-Content $_.FullName -Raw | ConvertFrom-Json | Out-Null }
```

If YAML files changed and the repo has an existing YAML validation command, run it. Do not introduce new tooling just for this workflow.

### Commit and push

Use the current worktree branch. Derive the upstream branch dynamically:

```powershell
git rev-parse --abbrev-ref --symbolic-full-name @{u}
```

If no upstream exists, ask the user where to push. Include the standard Copilot co-author trailer when committing unless the user said not to.

### Queue the build

Queue build pipeline `51424` on the pushed branch. Use Azure DevOps MCP tools if available; otherwise use Azure CLI:

```powershell
az pipelines run `
  --id 51424 `
  --branch "<branch>" `
  --organization "https://dev.azure.com/O365exchange" `
  --project "O365 Core" `
  --query "{id:id,buildNumber:buildNumber,status:status}" -o json
```

Wait for completion. Capture the build ID and build number/artifact version. The deploy pipeline should use this fresh artifact.

### Queue deploy pipeline 54477

Run deploy pipeline `54477` with the same branch and the fresh build artifact from pipeline `51424`. If the exact resource/parameter shape is unclear, inspect a recent successful run and replay its resources/template parameters while changing only the source branch and artifact build.

Using the Azure DevOps pipeline tool, prefer `run_pipeline` with `resources.pipelines` pointing at the successful build/artifact run. With Azure CLI/REST, post to the Builds API with `definition.id = 54477`, `sourceBranch = refs/heads/<branch>`, and the required `templateParameters`/artifact resources copied from the known-good run.

Do not treat rollout as successful until the deploy run reaches `status: completed` and `result: succeeded`. Ev2 monitoring or validation jobs can fail after ARM deployment appears complete.

## Runtime validation

After deploy succeeds, validate both code App Services in each deployed region.

1. Identify resource group and app names from deploy parameters, Ev2 output, or Azure resources. The code app normally ends in `-code`; image app keeps the base name.
2. Verify App Service state and runtime:

```powershell
az webapp show -g <resource-group> -n <app-name> --query "{state:state,hostNames:defaultHostName}" -o json
az webapp config show -g <resource-group> -n <app-name> --query "{netFrameworkVersion:netFrameworkVersion,use32BitWorkerProcess:use32BitWorkerProcess}" -o json
az webapp config show -g <resource-group> -n <app-name> --slot staging --query "{netFrameworkVersion:netFrameworkVersion,use32BitWorkerProcess:use32BitWorkerProcess}" -o json
```

3. Probe health:

```powershell
curl.exe -sS -i https://<code-app>.azurewebsites.net/healthz/ready
curl.exe -sS -i https://<code-app>.azurewebsites.net/healthz/live
```

Expected status is `200` for both.

4. Probe unauthenticated behavior:

```powershell
curl.exe -sS -i https://<code-app>.azurewebsites.net/
curl.exe -sS -i https://<code-app>.azurewebsites.net/connect/api/health
```

Expected status is `401` unless route matching returns `404` before auth because required headers are absent.

5. For business validation, acquire a Lumina token using the `lumina-eps-token` skill/helper rather than plain `az account get-access-token` when Azure CLI tokens are rejected by R9. Do not print full tokens. Then run the `/connect` matrix in the Gateway behavior section. A positive end-to-end validation requires a real reachable sandbox private `IP:port`; a synthetic allowed private IP can only prove the gateway attempts forwarding and should usually end in `502 ProxyError`.

## Log and failure diagnosis

When deploy or validation fails, inspect App Service logs before editing again:

```powershell
az webapp log download -g <resource-group> -n <app-name> --log-file <safe-output-path>.zip
az webapp log tail -g <resource-group> -n <app-name>
```

Also inspect the latest Kudu deployment status/logs when zip deploy is involved.

Common failure signatures:

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `HTTP Error 500.30` or CoreCLR load failure | Code app/slot is wrong runtime or 32-bit | Set `.NET v8.0` and 64-bit on both app and staging slot in ARM |
| Deploy succeeds but health stays old | Slot swap or zip deploy did not target code app/slot | Check code app suffix, slot names, shell script app name selection |
| `/connect` always `401` with Azure CLI token | Token audience/client not accepted by R9 | Use Lumina token helper; inspect claims without printing token |
| `/connect` blocked IP/port tests return expected `400` | Gateway business validation is working | Use a real sandbox private `IP:port` for positive proxy validation |
| Allowed private IP returns `502 ProxyError` | Gateway forwarded but target is absent/unreachable | Find an active sandbox container/service and retry |
| App Service logs/App Insights missing | ARM did not create diagnostics/app settings or settings were overwritten | Recheck App Insights connection string, diagnostic settings, and log config resources |

Report the exact failing layer: build, Ev2/ARM deployment, zip deployment, runtime startup, auth, gateway transform, or target sandbox reachability.

## Output style

When reporting back, lead with the result:

- If build/deploy succeeded, include build ID, deploy ID, artifact/build number, commit, and app names/resource groups.
- If validation succeeded, list the health/API statuses and any business matrix results.
- If blocked, state the missing prerequisite plainly, such as "need a real sandbox private IP:port for positive forwarding validation."
- Do not paste full bearer tokens, secret values, or raw credential-bearing logs.
