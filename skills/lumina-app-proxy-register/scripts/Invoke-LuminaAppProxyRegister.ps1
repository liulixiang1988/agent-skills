# ============================================================
# Register a custom HTTP service inside a Lumina sandbox and
# expose it through LuminaProxyAPI (App Proxy).
#
# Equivalent to a 5-step run:
#   1. Upload a tiny FastAPI server.py into the sandbox.
#   2. Start it on a port in APP_HOSTING_PORT_RANGE.
#   3. Call egress-llm /app/register/agent to register and get
#      a public app_url under {appId}.{BaseDomain}.
#   4. Print the URL + health probe.
#   5. Make one S2S call back through the proxy with the bearer
#      token to confirm end-to-end (auth + cookie strip + routing).
#
# Prerequisites:
#   - A live Lumina sandbox (ComputerId already provisioned).
#   - An OBO/PFT bearer token whose oid matches the sandbox owner
#     when AccessScope is "owner".
#   - PowerShell 7+ (Invoke-WebRequest -SkipCertificateCheck).
# ============================================================

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ComputerId,

    [Parameter(Mandatory = $true)]
    [string]$AuthToken,

    [string]$LuminaApiBase = "https://luminaserviceapi-b-4.luminadevaks-westus3.dev.copilotlumina.com",

    [string]$FeatureKind = "terminal",

    [string]$FeatureName = "terminal-shell",

    [int]$ServerPort = 19101,

    [ValidateSet("owner", "all")]
    [string]$AccessScope = "owner",

    # Skip Step 5 if you only want the URL printed.
    [switch]$SkipS2STest
)

$ErrorActionPreference = "Stop"

$Headers = @{
    "Content-Type"  = "application/json"
    "Authorization" = "Bearer $AuthToken"
}

function Invoke-AgentApi {
    param(
        [string]$Path,
        [hashtable]$Body
    )
    $uri = "$LuminaApiBase$Path"
    $json = $Body | ConvertTo-Json -Depth 10
    Write-Host "`n>> POST $Path" -ForegroundColor Cyan
    return Invoke-RestMethod -Uri $uri -Method Post -Headers $Headers -Body $json
}

# ============================================================
# Step 1: Write server.py to the sandbox
# ============================================================
Write-Host "`n=== Step 1: Writing server.py to sandbox ===" -ForegroundColor Green

$serverCode = @"
from fastapi import FastAPI
import uvicorn
import sys

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"healthy": True}

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else $ServerPort
    uvicorn.run(app, host="0.0.0.0", port=port)
"@

$serverCodeBase64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($serverCode))

$null = Invoke-AgentApi -Path "/api/agent/storage/file/batchUpload" -Body @{
    computerId = $ComputerId
    files = @(
        @{
            path     = "/home/oai/share/server.py"
            content  = $serverCodeBase64
            encoding = "base64"
        }
    )
}
Write-Host "File uploaded successfully." -ForegroundColor Green

# ============================================================
# Step 2: Start the server via session mode
# ============================================================
Write-Host "`n=== Step 2: Starting server on port $ServerPort ===" -ForegroundColor Green

$null = Invoke-AgentApi -Path "/api/agent/container/exec" -Body @{
    cmd             = @("bash")
    computerId      = $ComputerId
    sessionName     = "server-session"
    sessionDuration = 2400
}

$null = Invoke-AgentApi -Path "/api/agent/container/feedChars" -Body @{
    computerId  = $ComputerId
    sessionName = "server-session"
    chars       = "nohup python /home/oai/share/server.py $ServerPort &`n"
    yieldTimeMs = 3000
}
Write-Host "Server started on port $ServerPort." -ForegroundColor Green

# ============================================================
# Step 3: Register the service & get public URL
# ============================================================
Write-Host "`n=== Step 3: Registering service via egress-llm (access_scope=$AccessScope) ===" -ForegroundColor Green

$registerCmd = "curl -s -X POST `${EGRESS_LLM_API_ENDPOINT}/app/register/agent " +
               "-H 'Content-Type: application/json' " +
               "-d '{""feature_kind"": ""$FeatureKind"", ""feature_name"": ""$FeatureName"", ""port"": $ServerPort, ""path"": ""/"", ""access_scope"": ""$AccessScope""}'"

$step3Response = Invoke-AgentApi -Path "/api/agent/container/exec" -Body @{
    cmd        = @("bash", "-c", $registerCmd)
    computerId = $ComputerId
}

Write-Host "Registration response:" -ForegroundColor Green
$step3Response | ConvertTo-Json -Depth 5 | Write-Host

$registeredApp = $null
if ($step3Response.content.stdout) {
    try {
        $registeredApp = $step3Response.content.stdout | ConvertFrom-Json
    }
    catch {
        Write-Host "Failed to parse registration stdout as JSON." -ForegroundColor Red
        throw
    }
}

$AppUrl = $registeredApp.app_url
if ([string]::IsNullOrWhiteSpace($AppUrl)) {
    throw "Registration succeeded but app_url is missing in stdout."
}

# ============================================================
# Step 4: Output the public URL
# ============================================================
Write-Host "`n=== Step 4: Service is ready ===" -ForegroundColor Green
Write-Host "Service URL: $AppUrl" -ForegroundColor Green
Write-Host "Health check:" -ForegroundColor Yellow
Write-Host "  curl -s ${AppUrl}health" -ForegroundColor Yellow

# ============================================================
# Step 5: Test S2S call to Proxy API with JWT token
# ============================================================
if ($SkipS2STest) {
    Write-Host "`n(Skipping Step 5 because -SkipS2STest was passed.)" -ForegroundColor Yellow
    return
}

Write-Host "`n=== Step 5: Test S2S call to Proxy API ===" -ForegroundColor Green

$s2sResponse = Invoke-WebRequest -Uri $AppUrl -Headers @{ Authorization = "Bearer $AuthToken" } -TimeoutSec 10 -SkipCertificateCheck
Write-Host "S2S status code: $($s2sResponse.StatusCode)" -ForegroundColor Green
Write-Host "S2S response body:" -ForegroundColor Green
$s2sResponse.Content | Write-Host
