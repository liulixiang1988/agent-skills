function lumina_build_proxy_api_image() {
    if (-not $Env:MS_PATH) {
        throw "MS_PATH environment variable is not set. Set it to the CopilotLumina root."
    }

    $uniqueId = Get-Date -Format "yyyyMMddHHmmss"
    $dockerImageTag = "luminaacrdev.azurecr.io/lixiangliu/lumina-proxy-api:${uniqueId}"
    $projectRoot = Join-Path -Path $Env:MS_PATH -ChildPath "CopilotLumina/sources/dev/LuminaService"
    $solutionPath = Join-Path -Path $projectRoot -ChildPath "LuminaService.sln"
    $pfxPath = Join-Path -Path $projectRoot -ChildPath "LuminaProxyAPI/lumina-dev-lumina-search-20250703.pfx"
    $dockerFile = Join-Path -Path $projectRoot -ChildPath "LuminaProxyAPI/DockerBuildConfigs/Dockerfile.local"
    $dockerContext = Join-Path -Path $projectRoot -ChildPath "LuminaProxyAPI"

    # build solution
    dotnet build $solutionPath --interactive
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to build solution at $solutionPath"
        return
    }

    # prepare cert
    az keyvault secret show --name "lumina-search-dev-new" --vault-name "lumina-dev" --query "value" -o tsv > $pfxPath

    # docker build
    docker build --file $dockerFile --tag $dockerImageTag $dockerContext
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to build docker image: $dockerImageTag"
        return
    }

    # push to acr
    docker push $dockerImageTag
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to push docker image: $dockerImageTag"
        return
    }

    Write-Host "Docker image tag: $dockerImageTag"
}

function lumina_build_scp_api_image() {
    if (-not $Env:MS_PATH) {
        throw "MS_PATH environment variable is not set. Set it to the CopilotLumina root."
    }

    $uniqueId = Get-Date -Format "yyyyMMddHHmmss"
    $dockerImageTag = "luminaacrdev.azurecr.io/lixiangliu/lumina-scp-api:${uniqueId}"
    $projectRoot = Join-Path -Path $Env:MS_PATH -ChildPath "CopilotLumina/sources/dev/LuminaService"
    $projectPath = Join-Path -Path $projectRoot -ChildPath "SandboxControlPlane/SandboxControlPlane.csproj"
    $dockerFile = Join-Path -Path $projectRoot -ChildPath "SandboxControlPlane/DockerBuildConfigs/Dockerfile.local"
    $dockerContext = Join-Path -Path $projectRoot -ChildPath "SandboxControlPlane"

    # build project
    dotnet build $projectPath --interactive
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to build project at $projectPath"
        return
    }

    # docker build
    docker build --file $dockerFile --tag $dockerImageTag $dockerContext
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to build docker image: $dockerImageTag"
        return
    }

    # push to acr
    docker push $dockerImageTag
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to push docker image: $dockerImageTag"
        return
    }

    Write-Host "Docker image tag: $dockerImageTag"
}

function sandbox_build_agent_image() {
    if (-not $Env:MS_PATH) {
        throw "MS_PATH environment variable is not set. Set it to the CopilotLumina root."
    }
    $uniqueId = Get-Date -Format "yyyyMMddHHmmss"
    $dockerImageTag = "luminaacrdev.azurecr.io/lixiangliu/lumina-sandbox-agent:${uniqueId}"
    $projectRoot = Join-Path -Path $Env:MS_PATH -ChildPath "CopilotLumina/sources/dev/SandboxService"
    $dockerFile = Join-Path -Path $projectRoot -ChildPath "Docker/agent.Dockerfile"
    $dockerContext = $projectRoot

    # docker build
    docker build --file $dockerFile --tag $dockerImageTag $dockerContext
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to build docker image: $dockerImageTag"
        return
    }

    # push to acr
    docker push $dockerImageTag
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to push docker image: $dockerImageTag"
        return
    }

    Write-Host "Docker image tag: $dockerImageTag"
}
