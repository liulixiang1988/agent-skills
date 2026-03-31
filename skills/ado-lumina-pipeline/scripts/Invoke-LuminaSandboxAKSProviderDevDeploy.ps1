<#
.SYNOPSIS
    Trigger the Lumina-SandboxAKSProvider-Service-Dev-Deploy pipeline via Azure CLI.

.DESCRIPTION
    This script triggers the AKS provider dev deploy pipeline with configurable parameters.
    Org:      O365exchange
    Project:  O365 Core
    Pipeline: Lumina-SandboxAKSProvider-Service-Dev-Deploy

.EXAMPLE
    # Deploy with profile a-1 (all components built by default, branch from upstream)
    .\Invoke-LuminaSandboxAKSProviderDevDeploy.ps1 -Profile "a-1"

.EXAMPLE
    # Deploy with profile b-2, skip building control plane and terminal shell
    .\Invoke-LuminaSandboxAKSProviderDevDeploy.ps1 -Profile "b-2" -BuildControlPlane $false -BuildTerminalShell $false

.EXAMPLE
    # Deploy with a custom branch
    .\Invoke-LuminaSandboxAKSProviderDevDeploy.ps1 -Profile "a-1" -Branch "u/lixiangliu/my-feature"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        "a-1","a-2","a-3","a-4","a-5",
        "b-1","b-2","b-3","b-4","b-5",
        "c-1","c-2","c-3","c-4","c-5",
        "d-1","d-2","d-3","d-4","d-5",
        "e-1","e-2","e-3","e-4","e-5",
        "f-1","f-2","f-3","f-4","f-5",
        "g-1","g-2","g-3","g-4","g-5"
    )]
    [string]$Profile,

    [string]$Branch,

    [string]$Region = "westus2",

    # --- Build flags (orchestrator and otel collector default to true) ---
    [bool]$BuildServiceApi = $false,
    [bool]$BuildProxyApi = $false,
    [bool]$BuildControlPlane = $false,
    [bool]$BuildControllerMain = $false,
    [bool]$BuildOperator = $false,
    [bool]$BuildTerminalShell = $false,
    [bool]$BuildDesktopBrowser = $false,
    [bool]$BuildDesktopLibreOffice = $false,
    [bool]$BuildSkillsAgent = $false,
    [bool]$BuildEgressProxy = $false,
    [bool]$BuildEgressLlm = $false,
    [bool]$BuildOtelCollector = $true,
    [bool]$BuildOrchestrator = $true,
    [bool]$BuildWorkspaceManager = $false,

    # --- BYO image overrides ---
    [string]$ByoServiceApiImage = "none",
    [string]$ByoProxyApiImage = "none",
    [string]$ByoControlPlaneImage = "none",

    # --- Convenience ---
    [switch]$BuildAll
)

# ── Resolve branch from upstream tracking if not specified ──
if (-not $Branch) {
    try {
        $Branch = git rev-parse --abbrev-ref '@{upstream}' 2>$null
        if (-not $Branch) { throw "no upstream" }
        # Strip remote prefix (e.g. "origin/u/user/feature" -> "u/user/feature")
        $Branch = $Branch -replace '^[^/]+/', ''
    } catch {
        Write-Host "❌ No branch specified and no upstream tracking branch found. Use -Branch to specify." -ForegroundColor Red
        exit 1
    }
}

# ── Constants ──
$Org     = "https://dev.azure.com/O365exchange"
$Project = "O365 Core"
$Pipeline = "Lumina-SandboxAKSProvider-Service-Dev-Deploy"

# ── Build parameter list ──
$params = @(
    "region=$Region"
    "profile=$Profile"
)

# Boolean build flags mapping
$buildFlags = @{
    "build_lumina_service_api"              = $BuildServiceApi -or $BuildAll
    "build_lumina_proxy_api"                = $BuildProxyApi -or $BuildAll
    "build_lumina_sandbox_control_plane"    = $BuildControlPlane -or $BuildAll
    "build_lumina_sandbox_controller_main"  = $BuildControllerMain -or $BuildAll
    "build_lumina_sandbox_operator"         = $BuildOperator -or $BuildAll
    "build_lumina_sandbox_terminal_shell"   = $BuildTerminalShell -or $BuildAll
    "build_lumina_sandbox_desktop_browser"  = $BuildDesktopBrowser -or $BuildAll
    "build_lumina_sandbox_desktop_libreoffice" = $BuildDesktopLibreOffice -or $BuildAll
    "build_lumina_sandbox_skills_agent"     = $BuildSkillsAgent -or $BuildAll
    "build_lumina_sandbox_egress_proxy"     = $BuildEgressProxy -or $BuildAll
    "build_lumina_sandbox_egress_llm"       = $BuildEgressLlm -or $BuildAll
    "build_lumina_sandbox_otel_collector"   = $BuildOtelCollector -or $BuildAll
    "build_lumina_sandbox_orchestrator"     = $BuildOrchestrator -or $BuildAll
    "build_lumina_sandbox_workspace_manager" = $BuildWorkspaceManager -or $BuildAll
}

foreach ($key in $buildFlags.Keys) {
    $params += "$key=$($buildFlags[$key].ToString().ToLower())"
}

# BYO image overrides
$params += "byo_lumina_service_api_image=$ByoServiceApiImage"
$params += "byo_lumina_proxy_api_image=$ByoProxyApiImage"
$params += "byo_lumina_sandbox_control_plane_image=$ByoControlPlaneImage"

# ── Summary ──
Write-Host "`n=== Pipeline Trigger Summary ===" -ForegroundColor Cyan
Write-Host "Pipeline : $Pipeline"
Write-Host "Branch   : $Branch"
Write-Host "Region   : $Region"
Write-Host "Profile  : $Profile"
Write-Host ""

$enabledBuilds = $buildFlags.GetEnumerator() | Where-Object { $_.Value } | ForEach-Object { $_.Key }
if ($enabledBuilds) {
    Write-Host "Build targets:" -ForegroundColor Yellow
    $enabledBuilds | ForEach-Object { Write-Host "  ✓ $_" -ForegroundColor Green }
} else {
    Write-Host "No build targets selected (deploy only)" -ForegroundColor Yellow
}
Write-Host ""

# ── Trigger ──
Write-Host "Triggering pipeline..." -ForegroundColor Cyan
az pipelines run `
    --name $Pipeline `
    --branch $Branch `
    --parameters @params `
    --org $Org `
    --project $Project `
    --output table

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Pipeline triggered successfully!" -ForegroundColor Green
} else {
    Write-Host "`n❌ Failed to trigger pipeline (exit code: $LASTEXITCODE)" -ForegroundColor Red
}
