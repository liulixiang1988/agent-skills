---
name: lumina-devaks-build-deploy-test-loop
description: "Run the CopilotLumina DevAKS a-2/westus3 develop → build → deploy → validate → diagnose → fix loop for Lumina.Api InternalDispatch and sandbox egress changes. Use this skill whenever the user asks to run or rerun the DevAKS ExpAks deploy from reference build 37538553, deploy branch changes to luminadevaks, create a sandbox through the a-2 endpoint, validate Graph profile-photo InternalDispatch via bash:runCommand, inspect lumina-api / egress-llm / egress-proxy logs, locally build and optionally replace the lumina-api image, or keep iterating until the Graph path no longer fails with InternalDispatchNotEnabled."
---

# Lumina DevAKS Build / Deploy / Validate / Fix Loop

Use this skill to drive the known CopilotLumina DevAKS validation loop for profile `a-2` in `westus3`. The loop is optimized for Lumina.Api InternalDispatch, SandboxProxy, and egress-llm changes:

1. inspect and fix code locally
2. run focused validation
3. commit and push the current branch
4. trigger the correct DevAKS pipeline with the known reference parameters
5. wait for deployment completion
6. create a sandbox through the DevAKS a-2 Lumina.Api endpoint
7. run a bash Graph profile-photo probe through the sandbox proxy chain
8. inspect Lumina.Api, egress-llm, and egress-proxy logs
9. diagnose, patch, and repeat

## Fixed environment for this workflow

| Item | Value |
|---|---|
| ADO org | `https://dev.azure.com/O365Exchange` |
| ADO project | `O365 Core` |
| Pipeline | `Lumina ExpAks Deploy` |
| Pipeline ID | `48192` |
| Reference build | `37538553` |
| Known good replay build | `37565519` |
| Profile | `a-2` |
| Region | `westus3` |
| AKS context | `luminadevaks-aks-westus3` |
| Namespace | `lumina-agent-a` |
| Lumina.Api deployment | `lumina-api-a-2` |
| Lumina.Api container | `lumina-api` |
| Sandbox deployment | `lumina-sandbox-a-2` |
| DevAKS Lumina.Api endpoint | `https://luminaapi-a-2.luminadevaks-westus3.dev.copilotlumina.com` |
| Partner header | `x-ms-lumina-partner: Lumina` |
| Scenario group header | `x-ms-lumina-scenariogroup: CUA` |
| Scenario header | `x-ms-lumina-scenario: dev-aks-westus2-2` |
| Sandbox provider observed | `DevAks` |

Do not use the public `luminaapi-eastus2.test.copilotlumina.com` endpoint for this validation loop unless the user explicitly asks for public routing validation. In this workflow it can route by partner scenario to a different region and obscure the a-2/westus3 result.

## Operating principles

1. Treat Azure DevOps, Kubernetes, and sandbox API calls as state-changing. Confirm with the user before manually replacing a Kubernetes image.
2. Never print bearer tokens, refresh tokens, Authorization headers, or token cache contents. It is fine to say a token was acquired.
3. Prefer the pipeline path for final validation. Local image replacement is useful for speed, but a running pipeline can overwrite a manual `kubectl set image`; cancel or wait for competing pipelines before relying on a manual image.
4. Keep validation artifacts outside the repo, such as under the session artifact directory.
5. The goal is not just "pipeline passed"; the goal is a live sandbox request that exercises egress-proxy -> egress-llm -> Lumina.Api InternalDispatch and produces useful logs.

## Local development and focused checks

Before deploying, inspect the current branch and run targeted checks for the files touched by the fix.

Useful checks from the InternalDispatch workflow:

```powershell
git --no-pager status --short --branch
git --no-pager diff --stat

dotnet build sources\dev\LuminaService\Lumina.Api\Lumina.Api.csproj --no-restore --verbosity minimal

dotnet test sources\dev\LuminaService\tests\Lumina.Api.Tests\Lumina.Api.Tests.csproj `
  --filter FullyQualifiedName~InternalDispatch `
  --no-restore `
  --verbosity minimal

Set-Location sources\dev\SandboxService\AIAgents\ts-agents\egress-llm
bun test tests\internal-dispatch.test.ts tests\eps-databroker.test.ts
```

If `dotnet build` and `dotnet test` run concurrently on Windows and one fails with a locked `obj` DLL, rerun the failed command sequentially before treating it as a real failure.

## Commit and push

Commit only relevant changes. Include the Copilot co-author trailer unless the user explicitly asks not to.

```powershell
git add <relevant-files>
git commit -m "<short message>" -m "Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>"
git push
```

If the current branch was merged with `origin/master`, push before triggering the pipeline so the build runs the exact merge commit.

## Trigger the DevAKS pipeline

Use pipeline ID `48192` (`Lumina ExpAks Deploy`), not the SandboxAKSProvider pipeline ID `53278`, for this a-2/westus3 Lumina.Api + sandbox component deployment.

When the user says "use the same parameters as build 37538553", fetch the template parameters from that reference build or from the known replay build `37565519`, then run the pipeline on the current pushed branch.

Known important parameters:

| Parameter | Value |
|---|---|
| `profile` | `a-2` |
| `region` | `westus3` |
| `agent_pool_override` | `default` |
| `build_lumina_api` | `true` |
| `build_lumina_sandbox_control_plane` | `true` |
| `build_lumina_sandbox_egress_llm` | `true` |
| `build_lumina_sandbox_egress_proxy` | `true` |
| `build_lumina_nginx_appservice` | `False` |
| `build_lumina_proxy_api` | `False` |
| `build_lumina_service_api` | `False` |
| `deploy_infra` | `False` |
| `restart_lumina_sandbox_only` | `False` |
| `sandbox_broker_enabled` | `False` |
| `scp_partner_override` | `CopilotResearcher` |
| `scp_sandbox_sku_override` | `cua` |
| `scp_sandbox_namespace_override` | `cua` |
| `byo_lumina_nginx_appservice_image` | `luminadevaks.azurecr.io/lumina-nginx-appservice:latest` |

PowerShell pattern:

```powershell
$org = "https://dev.azure.com/O365Exchange"
$project = "O365 Core"
$pipelineId = 48192
$referenceBuildId = 37538553
$branch = "refs/heads/$((git rev-parse --abbrev-ref HEAD).Trim())"

$paramsJson = az pipelines build show `
  --id $referenceBuildId `
  --org $org `
  --project $project `
  --query templateParameters `
  -o json

$params = $paramsJson | ConvertFrom-Json
$paramArgs = @()
foreach ($prop in $params.PSObject.Properties) {
  $paramArgs += ("{0}={1}" -f $prop.Name, $prop.Value)
}

$args = @(
  "pipelines", "run",
  "--id", $pipelineId,
  "--branch", $branch,
  "--org", $org,
  "--project", $project,
  "--parameters"
) + $paramArgs + @(
  "--query", "{id:id,name:name,state:state,result:result,url:url}",
  "-o", "json"
)

& az @args
```

After queueing, verify the run resolves to the intended branch and commit:

```powershell
az pipelines build show --id <run-id> --org $org --project $project `
  --query "{id:id,buildNumber:buildNumber,status:status,result:result,sourceBranch:sourceBranch,sourceVersion:sourceVersion,definition:definition.name,parameters:templateParameters}" -o json
```

## Wait for pipeline completion

Poll until `status == completed`. If `result != succeeded`, read logs before changing code.

```powershell
while ($true) {
  $build = az pipelines build show --id <run-id> --org $org --project $project `
    --query "{status:status,result:result,buildNumber:buildNumber}" -o json | ConvertFrom-Json
  $build | ConvertTo-Json -Compress
  if ($build.status -eq "completed") { break }
  Start-Sleep -Seconds 60
}
if ($build.result -ne "succeeded") { throw "Pipeline failed: $($build.result)" }
```

Capture the build number. Pipeline image tags commonly look like:

`<buildNumber>-1es-westus3-a-2-<shortSha>-data-broker-impl`

## Verify AKS rollout and image

Use the fixed context and namespace:

```powershell
$context = "luminadevaks-aks-westus3"
$ns = "lumina-agent-a"

kubectl --context $context -n $ns get deployment lumina-api-a-2 -o jsonpath="{range .spec.template.spec.containers[*]}{.name}{'|'}{.image}{'\n'}{end}"
kubectl --context $context -n $ns rollout status deployment/lumina-api-a-2 --timeout=10m
kubectl --context $context -n $ns get pods -l app=lumina-api-a-2 -o wide
```

If validating sandbox sidecars:

```powershell
kubectl --context $context -n $ns get pods -l app=lumina-sandbox-a-2 -o wide
kubectl --context $context -n $ns get deployment lumina-sandbox-a-2 -o jsonpath="{range .spec.template.spec.containers[*]}{.name}{'|'}{.image}{'\n'}{end}"
```

## Optional local Lumina.Api image acceleration

Use this only when the user wants speed before the final pipeline path. The pipeline can overwrite this manual image later.

Build and push a Windows Lumina.Api image using the same Dockerfile path used by the pipeline:

```powershell
$short = (git rev-parse --short=8 HEAD).Trim()
$tag = "local-$short-$(Get-Date -Format yyyyMMddHHmmss)"
$image = "luminadevaks.azurecr.io/devaks/lumina-api:$tag"
$project = "sources\dev\LuminaService\Lumina.Api\Lumina.Api.csproj"
$context = Join-Path (Get-Location) "sources\dev\LuminaService\Lumina.Api"
$dockerfile = Join-Path $context "DockerBuildConfigs\Dockerfile.dev"

dotnet build $project --no-restore --verbosity minimal
docker build --file $dockerfile --tag $image $context
docker push $image
if ($LASTEXITCODE -ne 0) {
  az acr login -n luminadevaks
  docker push $image
}
```

Before replacing the AKS image, ask the user to confirm all target values:

- kube context: `luminadevaks-aks-westus3`
- namespace: `lumina-agent-a`
- deployment: `lumina-api-a-2`
- container: `lumina-api`
- exact target image tag

Then ask for final confirmation before running:

```powershell
kubectl --context luminadevaks-aks-westus3 -n lumina-agent-a set image deployment/lumina-api-a-2 lumina-api=<image>
kubectl --context luminadevaks-aks-westus3 -n lumina-agent-a rollout status deployment/lumina-api-a-2 --timeout=10m
```

## Acquire a Lumina token

Use the `lumina-eps-token` skill or the repo helper. Do not print the full token.

Known helper:

`sources/dev/SandboxService/AIAgents/ts-agents/egress-llm/scripts/get-lumina-token.ts`

The helper may use a cache file containing real refresh/access tokens; do not commit or display it.

Bearer tokens are sufficient for opening a sandbox and running `bash:runCommand`, but they do not provide the current user PFT that InternalDispatch needs to mint AT_POP for Graph. A full Graph success requires the sandbox open or connection-info request to carry `Authorization: MSAuth1.0 ...` with the required agent identity headers so Lumina.Api can store the current sandbox PFT. When validating with Bearer-only auth, treat `InternalDispatchPftMissing` after a matched Graph rule as evidence that the InternalDispatch route is enabled and catalog-matched, with the remaining blocker being the missing PFT test context.

## Create a validation sandbox

Use the DevAKS a-2 endpoint:

`POST https://luminaapi-a-2.luminadevaks-westus3.dev.copilotlumina.com/api/v3/sandboxes/{sandboxId}:open`

Use a unique sandbox ID:

```powershell
$endpoint = "https://luminaapi-a-2.luminadevaks-westus3.dev.copilotlumina.com"
$sandboxId = "itest-internaldispatch-$(Get-Date -Format yyyyMMdd-HHmmss)"
```

Open request body:

```json
{
  "proxyOptions": {
    "internalDispatch": {
      "enabled": true,
      "rules": [
        {
          "name": "Graph",
          "hosts": [
            "graph.microsoft.com",
            "graph.microsoft-ppe.com"
          ]
        }
      ]
    }
  }
}
```

Headers:

```text
Authorization: Bearer <token>
Content-Type: application/json
x-ms-lumina-partner: Lumina
x-ms-lumina-scenariogroup: CUA
x-ms-lumina-scenario: dev-aks-westus2-2
```

Save the request/response JSON outside the repo.

## Run the Graph profile-photo probe through bash

Use:

`POST /api/v3/sandboxes/{sandboxId}/bash:runCommand`

Request body:

```json
{
  "command": "set -o pipefail; echo \"sandbox_graph_start=$(date -Iseconds)\"; echo \"--- proxy env ---\"; env | grep -i proxy || true; echo \"--- curl verbose ---\"; curl -v -sS -D /tmp/graph_headers.txt -o /tmp/graph_photo.bin -w \"CURL_HTTP_CODE=%{http_code}\\nCURL_EXIT=%{exitcode}\\n\" --max-time 90 \"https://graph.microsoft.com/v1.0/users/lixiangliu@microsoft.com/photo/\\$value\" 2>&1; rc=$?; echo \"COMMAND_EXIT=$rc\"; echo \"--- response headers ---\"; sed -n \"1,40p\" /tmp/graph_headers.txt 2>/dev/null || true; echo \"--- downloaded file ---\"; ls -l /tmp/graph_photo.bin 2>/dev/null || true; echo \"sandbox_graph_end=$(date -Iseconds)\"; exit 0",
  "timeout": 120000,
  "description": "Validate InternalDispatch Graph profile photo access"
}
```

Important: escape `$value` in PowerShell/JSON contexts so the final URL sent inside bash is:

`https://graph.microsoft.com/v1.0/users/lixiangliu@microsoft.com/photo/$value`

If `$value` is not escaped, bash expands it to an empty environment variable and the request becomes `/photo/`, which is expected to fail catalog matching with `InternalDispatchOperationNotAllowed`.

## Inspect logs

Pull logs from the same AKS context and namespace.

Lumina.Api:

```powershell
kubectl --context luminadevaks-aks-westus3 -n lumina-agent-a logs deployment/lumina-api-a-2 --tail=500 |
  Select-String -Pattern "InternalDispatch|InternalDispatchNotEnabled|InternalDispatchOperationNotAllowed|CatalogEntry|UpstreamRequestId|x-ms-lumina-correlation-id"
```

Sandbox egress-llm:

```powershell
kubectl --context luminadevaks-aks-westus3 -n lumina-agent-a logs -l app=lumina-sandbox-a-2 -c egress-llm --tail=800 |
  Select-String -Pattern "internal:dispatch|metadataDecoded|matchedRule|targetHost|targetPathHash|upstreamStatus|upstreamLuminaCorrelationId|Graph"
```

Sandbox egress-proxy:

```powershell
kubectl --context luminadevaks-aks-westus3 -n lumina-agent-a logs -l app=lumina-sandbox-a-2 -c egress-proxy --tail=800 |
  Select-String -Pattern "InternalDispatch|Graph|graph.microsoft.com|CONNECT|rewrite"
```

Useful egress-llm fields that should appear for the Graph probe:

- `operation=internal:dispatch`
- `metadataDecoded=true`
- `matchedRule=Graph`
- `originalMethod=GET`
- `transport=Http` or `transport=http`
- `targetHost=graph.microsoft.com`
- `targetPathLength`
- `targetPathHash`
- `upstreamStatus`
- `upstreamLuminaCorrelationId`

## Interpret validation results

| Symptom | Meaning | Next action |
|---|---|---|
| `x-ms-error-code: InternalDispatchNotEnabled` | Lumina.Api registered or checked the disabled dispatch service. | Confirm `SandboxProxy:InternalDispatch:Enabled` is what the API binds for service registration and runtime checks; redeploy Lumina.Api. |
| `InternalDispatchOperationNotAllowed` | Metadata reached Lumina.Api but catalog/rule/path/method/transport did not match. | Check appsettings `SandboxProxy.InternalDispatch.Rules[*].Catalogs` includes Graph, `GET`, `Http`, `/v1.0/users/{userId}/photo/$value`, and hosts. |
| `InternalDispatchPftMissing` after egress-llm logs `matchedRule=Graph` | The request reached Lumina.Api InternalDispatch and matched the Graph catalog, but the sandbox has no stored current PFT. This is expected for Bearer-only validation. | Reopen or reconnect using a real MSAuth1.0 PFT request context, or report this as the current test-context blocker rather than an enablement/catalog failure. |
| egress-llm shows `metadataDecoded=false` or missing target fields | egress-llm did not decode or forward metadata as expected. | Inspect egress-llm internal-dispatch handler and tests. |
| egress-proxy logs show no Graph/InternalDispatch activity | Request may not be going through mitmproxy or rule matching failed before egress-llm. | Check sandbox proxy config inside the sandbox pod and `HTTP_PROXY` / `HTTPS_PROXY` env. |
| Graph returns 401/403 with Graph request IDs but no Lumina `InternalDispatchNotEnabled` | The relay path reached Graph; remaining issue is auth/PFT/AT_POP or Graph permission. | Inspect Lumina.Api `ApplyAuthorization` / PFT availability and upstream Graph headers. |
| HTTP 200 and a non-empty photo file | Best-case validation success. | Record sandbox ID, build ID, image tag, and log snippets as PR evidence. |

## Fix loop

When validation fails:

1. Classify the failure using logs and response headers.
2. Patch the smallest owning component:
   - Lumina.Api options/service registration/catalog/PFT/AT_POP logic
   - SandboxProxy internal dispatch rule/config emission
   - egress-llm metadata forwarding/logging
   - egress-proxy CONNECT/rewrite behavior
3. Run focused tests for the changed component.
4. Commit and push.
5. Rerun the pipeline using the same reference parameters.
6. Recreate a fresh sandbox and rerun the Graph probe.

Stop and ask before broadening scope outside these components unless evidence clearly identifies another boundary.

## PR / handoff evidence

When the loop completes or blocks, report:

- branch and commit
- pipeline ID, run ID, build number, result
- image tag deployed to `lumina-api-a-2`
- sandbox ID
- bash Graph probe status and response headers
- key egress-llm fields
- key Lumina.Api logs/correlation IDs
- whether the final blocker is InternalDispatch config, catalog matching, auth/PFT, Graph permission, or infrastructure
