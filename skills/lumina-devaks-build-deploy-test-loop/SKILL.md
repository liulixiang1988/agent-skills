---
name: lumina-devaks-build-deploy-test-loop
description: "Run the CopilotLumina DevAKS a-2/westus3 develop → build → deploy → validate → diagnose → fix loop for Lumina.Api ApiDispatch and sandbox egress changes. Use this skill whenever the user asks to run or rerun the DevAKS ExpAks deploy from reference build 37538553, deploy branch changes to luminadevaks, create a sandbox through the a-2 endpoint, validate Graph profile-photo or AugLoop HTTP/SSE ApiDispatch via bash:runCommand, inspect lumina-api / egress-llm / egress-proxy logs, locally build and optionally replace the lumina-api image, or keep iterating until Graph/AugLoop dispatch works."
---

# Lumina DevAKS Build / Deploy / Validate / Fix Loop

Use this skill to drive the known CopilotLumina DevAKS validation loop for profile `a-2` in `westus3`. The loop is optimized for Lumina.Api ApiDispatch, SandboxProxy, and egress-llm changes:

1. inspect and fix code locally
2. run focused validation
3. commit and push the current branch
4. trigger the correct DevAKS pipeline with the known reference parameters
5. wait for deployment completion
6. create a sandbox through the DevAKS a-2 Lumina.Api endpoint
7. run bash Graph profile-photo and AugLoop HTTP/SSE workflow probes through the sandbox proxy chain
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
5. The goal is not just "pipeline passed"; the goal is a live sandbox request that exercises egress-proxy -> egress-llm -> Lumina.Api ApiDispatch and produces useful logs.

## Local development and focused checks

Before deploying, inspect the current branch and run targeted checks for the files touched by the fix.

Useful checks from the ApiDispatch workflow:

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

Open request body for the provider-neutral ApiDispatch contract:

```json
{}
```

`{}` is the preferred positive-case body: it omits `proxyOptions`, so Lumina.Api emits the server-authoritative `SandboxProxy:ApiDispatch` defaults into `sandbox_proxy_config.json`.

Use `{"proxyOptions":{"apiDispatch":{"enabled":true}}}` only when the test should assert that server-side ApiDispatch must be configured/enabled and should fail closed otherwise.

Use `{"proxyOptions":{"apiDispatch":{"enabled":false}}}` for the explicit-disable negative case.

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
  "description": "Validate ApiDispatch Graph profile photo access"
}
```

Important: escape `$value` in PowerShell/JSON contexts so the final URL sent inside bash is:

`https://graph.microsoft.com/v1.0/users/lixiangliu@microsoft.com/photo/$value`

If `$value` is not escaped, bash expands it to an empty environment variable and the request becomes `/photo/`, which is expected to fail catalog matching with `ApiDispatchOperationNotAllowed`.

## Run AugLoop HTTP and SSE workflow probes through bash

Use AugLoop workflow URLs, not `/files`, when validating SSE. The `/workflows/{workflowId}` catalog allows both `Http` and `Sse`; `/files` entries are HTTP-only.

HTTP workflow probe:

```json
{
  "command": "set -o pipefail; echo \"sandbox_augloop_http_start=$(date -Iseconds)\"; printf '{\"input\":\"hello from lumina internal dispatch validation\"}' > /tmp/augloop_workflow_request.json; curl -v -sS -X POST -H \"content-type: application/json\" -D /tmp/augloop_http_headers.txt -o /tmp/augloop_http_body.txt -w \"CURL_HTTP_CODE=%{http_code}\\nCURL_EXIT=%{exitcode}\\n\" --data-binary @/tmp/augloop_workflow_request.json --max-time 90 \"https://dogfood.augloop.svc.cloud.microsoft/workflows/lumina-internal-dispatch-validation\" 2>&1; rc=$?; echo \"COMMAND_EXIT=$rc\"; echo \"--- response headers ---\"; sed -n \"1,80p\" /tmp/augloop_http_headers.txt 2>/dev/null || true; echo \"--- response body preview ---\"; head -c 1000 /tmp/augloop_http_body.txt 2>/dev/null || true; echo; echo \"sandbox_augloop_http_end=$(date -Iseconds)\"; exit 0",
  "timeout": 120000,
  "description": "Validate ApiDispatch AugLoop workflow over HTTP"
}
```

SSE workflow probe:

```json
{
  "command": "set -o pipefail; echo \"sandbox_augloop_sse_start=$(date -Iseconds)\"; printf '{\"input\":\"hello from lumina internal dispatch sse validation\"}' > /tmp/augloop_sse_request.json; curl -N -v -sS -X POST -H \"accept: text/event-stream\" -H \"content-type: application/json\" -D /tmp/augloop_sse_headers.txt -o /tmp/augloop_sse_body.txt -w \"CURL_HTTP_CODE=%{http_code}\\nCURL_EXIT=%{exitcode}\\n\" --data-binary @/tmp/augloop_sse_request.json --max-time 90 \"https://dogfood.augloop.svc.cloud.microsoft/workflows/lumina-internal-dispatch-validation\" 2>&1; rc=$?; echo \"COMMAND_EXIT=$rc\"; echo \"--- response headers ---\"; sed -n \"1,80p\" /tmp/augloop_sse_headers.txt 2>/dev/null || true; echo \"--- response body preview ---\"; head -c 1000 /tmp/augloop_sse_body.txt 2>/dev/null || true; echo; echo \"sandbox_augloop_sse_end=$(date -Iseconds)\"; exit 0",
  "timeout": 120000,
  "description": "Validate ApiDispatch AugLoop workflow over SSE"
}
```

For Bearer-only sandboxes, success can be the missing-PFT mock: `HTTP 200`, `content-type: text/event-stream`, `x-ms-lumina-api-dispatch-mock: true`, and SSE frames like `event: message` followed by `event: done`. This proves the SSE route, transport classification, catalog match, and response shape; it does not prove real upstream AugLoop auth without a stored current PFT.

## Positive and negative ApiDispatch validation cases

Run these cases when validating provider-neutral ApiDispatch changes:

| Case | Open body | Probe | Expected evidence |
|---|---|---|---|
| Positive default | `{}` | Graph profile photo, AugLoop HTTP, AugLoop SSE | All return `HTTP 200`; Graph may return mock `image/png` with `x-ms-lumina-api-dispatch-mock: true` and `missing-pft`; SSE returns `content-type: text/event-stream` with `event: message` then `event: done`; egress-proxy rewrites to `/api/v3/internal/apiDispatch:invoke`; egress-llm logs `metadataDecoded=true`, `matchedRule=Graph` / `AugLoopDogfood`, `transport=Http` / `Sse`, and `upstreamStatus=200`. |
| Explicit disabled | `{"proxyOptions":{"apiDispatch":{"enabled":false}}}` | Graph profile photo with no Graph auth header | Request should not go through ApiDispatch. Expected direct Graph response is `HTTP 401` with Graph `InvalidAuthenticationToken`, no `x-ms-lumina-api-dispatch-mock` header, and no ApiDispatch rewrite/match logs for that sandbox. |
| Unsupported catalog/path | `{}` | `https://graph.microsoft.com/v1.0/this-path-should-not-match-lumina-api-dispatch-validation` | Request reaches ApiDispatch but fails closed with `HTTP 403`, `x-ms-error-code: ApiDispatchOperationNotAllowed`, and a Lumina correlation ID. |

DevAKS a-2 has a small pod pool. If sandbox open fails with `NoAvailablePods`, close prior test sandboxes and retry after replacement pods become ready.

## Inspect logs

Pull logs from the same AKS context and namespace.

Lumina.Api:

```powershell
kubectl --context luminadevaks-aks-westus3 -n lumina-agent-a logs deployment/lumina-api-a-2 --tail=500 |
  Select-String -Pattern "ApiDispatch|InternalDispatch|ApiDispatchNotEnabled|InternalDispatchNotEnabled|ApiDispatchOperationNotAllowed|InternalDispatchOperationNotAllowed|CatalogEntry|UpstreamRequestId|x-ms-lumina-correlation-id"
```

Sandbox egress-llm:

```powershell
kubectl --context luminadevaks-aks-westus3 -n lumina-agent-a logs -l app=lumina-sandbox-a-2 -c egress-llm --tail=800 |
  Select-String -Pattern "api:dispatch|apiDispatch|internal:dispatch|metadataDecoded|matchedRule|targetHost|targetPathHash|upstreamStatus|upstreamLuminaCorrelationId|Graph|AugLoop|transport|dogfood.augloop"
```

Sandbox egress-proxy:

```powershell
kubectl --context luminadevaks-aks-westus3 -n lumina-agent-a logs -l app=lumina-sandbox-a-2 -c egress-proxy --tail=800 |
  Select-String -Pattern "ApiDispatch|api_dispatch|InternalDispatch|Graph|AugLoop|graph.microsoft.com|dogfood.augloop|CONNECT|rewrite|text/event-stream"
```

Useful egress-llm fields that should appear for Graph and AugLoop probes:

- ApiDispatch dispatch operation log (`api:dispatch`, `apiDispatch`, or legacy `internal:dispatch` depending on branch)
- `metadataDecoded=true`
- `matchedRule=Graph` for profile-photo, `matchedRule=AugLoopDogfood` for the dogfood workflow probe
- `originalMethod=GET` for Graph, `originalMethod=POST` for AugLoop
- `transport=Http` for Graph/AugLoop HTTP, `transport=Sse` for AugLoop SSE
- `targetHost=graph.microsoft.com` or `targetHost=dogfood.augloop.svc.cloud.microsoft`
- `targetPathLength`
- `targetPathHash`
- `upstreamStatus`
- `upstreamLuminaCorrelationId`

## Interpret validation results

| Symptom | Meaning | Next action |
|---|---|---|
| `x-ms-error-code: ApiDispatchNotEnabled` | Lumina.Api registered or checked the disabled dispatch service. | Confirm `SandboxProxy:ApiDispatch:Enabled` is what the API binds for service registration and runtime checks; redeploy Lumina.Api. |
| `ApiDispatchOperationNotAllowed` | Metadata reached Lumina.Api but catalog/rule/path/method/transport did not match. | Check appsettings `SandboxProxy:ApiDispatch:Rules[*].Catalogs` includes Graph, `GET`, `Http`, `/v1.0/users/{userId}/photo/$value`, and hosts. |
| `ApiDispatchPftMissing` after egress-llm logs `matchedRule=Graph`, or `HTTP 200` with `x-ms-lumina-api-dispatch-mock: true` and `missing-pft` | The request reached Lumina.Api ApiDispatch and matched the Graph catalog, but the sandbox has no stored current PFT. This is expected for Bearer-only validation when mock responses are enabled. | Reopen or reconnect using a real MSAuth1.0 PFT request context, or report this as the current test-context blocker rather than an enablement/catalog failure. |
| AugLoop SSE returns `text/event-stream` with `x-ms-lumina-api-dispatch-mock: true` and `event: message` / `event: done` frames | The sandbox proxy classified `Accept: text/event-stream` as `Sse`, egress-llm forwarded it, Lumina.Api matched the AugLoop workflow catalog, and the SSE-specific missing-PFT mock response shape works. | Record this as successful SSE route/transport/shape validation; real upstream AugLoop still requires a current PFT. |
| AugLoop `/files` with SSE fails catalog matching | Expected: AugLoop file catalog entries are HTTP-only. | Use `/workflows/{workflowId}` for SSE validation. |
| egress-llm shows `metadataDecoded=false` or missing target fields | egress-llm did not decode or forward metadata as expected. | Inspect egress-llm ApiDispatch/internal-dispatch handler and tests. |
| egress-proxy logs show no Graph/ApiDispatch activity | Request may not be going through mitmproxy or rule matching failed before egress-llm. | Check sandbox proxy config inside the sandbox pod and `HTTP_PROXY` / `HTTPS_PROXY` env. |
| Graph returns 401/403 with Graph request IDs but no Lumina `ApiDispatchNotEnabled` | The relay path reached Graph; remaining issue is auth/PFT/AT_POP or Graph permission. | Inspect Lumina.Api `ApplyAuthorization` / PFT availability and upstream Graph headers. |
| HTTP 200 and a non-empty photo file | Best-case validation success. | Record sandbox ID, build ID, image tag, and log snippets as PR evidence. |

## Fix loop

When validation fails:

1. Classify the failure using logs and response headers.
2. Patch the smallest owning component:
   - Lumina.Api options/service registration/catalog/PFT/AT_POP logic
   - SandboxProxy ApiDispatch rule/config emission
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
- bash AugLoop HTTP and SSE probe status, response headers, and SSE frame preview when applicable
- key egress-llm fields
- key Lumina.Api logs/correlation IDs
- whether the final blocker is ApiDispatch config, catalog matching, auth/PFT, Graph/AugLoop permission, SSE response shape, or infrastructure
