---
name: ado-lumina-pipeline
description: "Trigger the Lumina-SandboxAKSProvider-Service-Dev-Deploy pipeline in Azure DevOps. Use this skill when the user wants to run/trigger/deploy the Lumina sandbox AKS pipeline, deploy sandbox orchestrator, deploy sandbox components, trigger a dev deploy, or run the dev pipeline. Also use when the user asks to re-run or reproduce a specific pipeline build."
---

# Lumina Sandbox AKS Provider - Dev Deploy Pipeline

Trigger the **Lumina-SandboxAKSProvider-Service-Dev-Deploy** pipeline via Azure CLI or the PowerShell helper script for CopilotLumina.

## Pipeline Info

| Item | Value |
|------|-------|
| **Org** | `https://dev.azure.com/O365exchange` |
| **Project** | `O365 Core` |
| **Pipeline Name** | `Lumina-SandboxAKSProvider-Service-Dev-Deploy` |
| **Pipeline ID** | `53278` |
| **Default Region** | `westus2` |

## Quick Start — PowerShell Script

The helper script is at `scripts/Invoke-LuminaSandboxAKSProviderDevDeploy.ps1` (relative to this skill's directory).

```powershell
# Deploy with default builds (orchestrator + otel collector), upstream branch, westus2
.\Invoke-LuminaSandboxAKSProviderDevDeploy.ps1 -Profile "a-1"

# Also build control plane and skills agent
.\Invoke-LuminaSandboxAKSProviderDevDeploy.ps1 -Profile "g-2" -BuildControlPlane $true -BuildSkillsAgent $true

# Build all components
.\Invoke-LuminaSandboxAKSProviderDevDeploy.ps1 -Profile "b-2" -BuildAll

# Use a BYO (bring-your-own) image
.\Invoke-LuminaSandboxAKSProviderDevDeploy.ps1 -Profile "c-1" -ByoControlPlaneImage "myacr.azurecr.io/cp:v1"
```

## Quick Start — Azure CLI

```bash
az pipelines run \
  --id 53278 \
  --branch "<branch>" \
  --organization "https://o365exchange.visualstudio.com/DefaultCollection" \
  --project "O365 Core" \
  --parameters \
    profile=<profile> \
    region=<region> \
    build_lumina_sandbox_orchestrator=true \
    build_lumina_sandbox_otel_collector=true
```

## Parameters

### Required

| Parameter | Description |
|-----------|-------------|
| `profile` | Dev profile name, e.g. `a-1` through `g-5` (35 total). |

### Optional

| Parameter | Default | Description |
|-----------|---------|-------------|
| `region` | `westus2` | Deployment region. |
| Branch (`--branch`) | upstream tracking branch | Git branch to run the pipeline on. Defaults to the upstream tracking branch of the current local branch (via `git rev-parse --abbrev-ref @{upstream}`). |

### Build Flags

All default to `False` except **Orchestrator** and **OTel Collector** which default to `True`. Set to `true`/`false` to toggle building that component's container image.

| Pipeline Parameter | PowerShell Switch | Component |
|--------------------|-------------------|-----------|
| `build_lumina_service_api` | `-BuildServiceApi` | Service API |
| `build_lumina_proxy_api` | `-BuildProxyApi` | Proxy API |
| `build_lumina_sandbox_control_plane` | `-BuildControlPlane` | Control Plane |
| `build_lumina_sandbox_controller_main` | `-BuildControllerMain` | Controller Main |
| `build_lumina_sandbox_operator` | `-BuildOperator` | Operator |
| `build_lumina_sandbox_terminal_shell` | `-BuildTerminalShell` | Terminal Shell |
| `build_lumina_sandbox_desktop_browser` | `-BuildDesktopBrowser` | Desktop Browser |
| `build_lumina_sandbox_desktop_libreoffice` | `-BuildDesktopLibreOffice` | Desktop LibreOffice |
| `build_lumina_sandbox_skills_agent` | `-BuildSkillsAgent` | Skills Agent |
| `build_lumina_sandbox_egress_proxy` | `-BuildEgressProxy` | Egress Proxy |
| `build_lumina_sandbox_egress_llm` | `-BuildEgressLlm` | Egress LLM |
| `build_lumina_sandbox_otel_collector` | `-BuildOtelCollector` | OTel Collector |
| `build_lumina_sandbox_orchestrator` | `-BuildOrchestrator` | Orchestrator |
| `build_lumina_sandbox_workspace_manager` | `-BuildWorkspaceManager` | Workspace Manager |
| `-BuildAll` (PowerShell only) | | Build all components |

### BYO (Bring Your Own) Images

Skip building and use a pre-built image:

| Pipeline Parameter | PowerShell Flag | Default |
|--------------------|-----------------|---------|
| `byo_lumina_service_api_image` | `-ByoServiceApiImage` | `none` |
| `byo_lumina_proxy_api_image` | `-ByoProxyApiImage` | `none` |
| `byo_lumina_sandbox_control_plane_image` | `-ByoControlPlaneImage` | `none` |
| `byo_lumina_nginx_appservice_image` | N/A | `luminadevaks.azurecr.io/lumina-nginx-appservice:latest` |

## Reproducing a Previous Build

To reproduce a previous pipeline run, use `az pipelines build show` to extract its parameters, then re-trigger:

```bash
# 1. Get the parameters from a previous build
az pipelines build show --id <BUILD_ID> \
  --org "https://o365exchange.visualstudio.com/DefaultCollection" \
  --project "O365 Core" \
  --query "{branch: sourceBranch, params: templateParameters}" -o json

# 2. Re-trigger with the same parameters
az pipelines run --id 53278 --branch "<branch>" \
  --org "https://o365exchange.visualstudio.com/DefaultCollection" \
  --project "O365 Core" \
  --parameters <key=value ...>
```

## Reserved Profiles

Do **NOT** use these profiles — they are reserved for automation:

| Profile | Purpose |
|---------|---------|
| `z` | Automation Scheduled Deploy |
| `it-3141592653` | Pi Integration Test |
| `it-271828` | Euler Integration Test |
| `orphan-cleanup` | Orphan Resource Cleanup |
| `all-cleanup` | Clean All Dev Namespaces |

## Prerequisites

1. Install [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
2. Install the Azure DevOps extension: `az extension add --name azure-devops`
3. Login: `az login`
