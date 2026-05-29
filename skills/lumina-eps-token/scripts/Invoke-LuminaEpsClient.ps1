param(
    [string]$RepoRoot = (Get-Location).Path,
    [string]$Description = "Hi",
    [string]$Url = "luminaserviceapi-b-4.luminadevaks-westus3.dev.copilotlumina.com",
    [ValidateSet("v1", "v3")]
    [string]$EpsVersion = "v1",
    [string]$BearerToken
)

$ErrorActionPreference = "Stop"

function Add-BunToPath {
    $bunBin = Join-Path $env:USERPROFILE ".bun\bin"
    if ((Test-Path $bunBin) -and (($env:PATH -split ";") -notcontains $bunBin)) {
        $env:PATH = "$bunBin;$env:PATH"
    }
}

function Ensure-Bun {
    Add-BunToPath
    if (Get-Command bun -ErrorAction SilentlyContinue) {
        return
    }

    Write-Host "bun not found; installing with official installer..."
    $installScript = Invoke-RestMethod https://bun.sh/install.ps1
    Invoke-Expression $installScript
    Add-BunToPath

    if (-not (Get-Command bun -ErrorAction SilentlyContinue)) {
        throw "bun was installed but is still not available in PATH. Restart the terminal or add $env:USERPROFILE\.bun\bin to PATH."
    }
}

function Find-EpsClient {
    param([string]$Root)

    $candidate = Join-Path $Root "sources\dev\SandboxService\AIAgents\ts-agents\skills-agent\scripts\eps_client.py"
    if (Test-Path $candidate) {
        return $candidate
    }

    $found = Get-ChildItem -Path $Root -Filter eps_client.py -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -like "*skills-agent*scripts*eps_client.py" } |
        Select-Object -First 1

    if ($found) {
        return $found.FullName
    }

    throw "Could not find skills-agent scripts\eps_client.py under $Root"
}

Ensure-Bun

$epsClient = Find-EpsClient -Root $RepoRoot
$scriptDir = Split-Path -Parent $epsClient

$clientArgs = @(".\eps_client.py", $Description, "--url", $Url, "--eps-version", $EpsVersion)
if ($BearerToken) {
    $clientArgs += @("--bearer-token", $BearerToken)
}

Push-Location $scriptDir
try {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        & uv run --with requests python @clientArgs
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python @clientArgs
    }
    elseif (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 @clientArgs
    }
    else {
        throw "No Python runtime found. Install Python or uv, then rerun this helper."
    }
}
finally {
    Pop-Location
}
