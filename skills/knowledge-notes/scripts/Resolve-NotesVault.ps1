#requires -Version 7.0
<#
.SYNOPSIS
Resolve the current user's existing Obsidian vault without changing files.
.PARAMETER VaultPath
An explicit absolute vault directory; overrides KNOWLEDGE_NOTES_VAULT.
.OUTPUTS
One absolute filesystem directory. Throws on missing or ambiguous candidates.
#>
[CmdletBinding()]
param(
    [string]$VaultPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-ExistingDirectory {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path) -or
        -not [System.IO.Path]::IsPathFullyQualified($Path)) {
        return
    }
    if (Test-Path -LiteralPath $Path -PathType Container) {
        $resolved = Resolve-Path -LiteralPath $Path
        if ($resolved.Provider.Name -eq 'FileSystem') {
            $resolved.ProviderPath
        }
    }
}

$explicitPath = $env:KNOWLEDGE_NOTES_VAULT
if ($PSBoundParameters.ContainsKey('VaultPath')) {
    $explicitPath = $VaultPath
}
if ($PSBoundParameters.ContainsKey('VaultPath') -or
    -not [string]::IsNullOrWhiteSpace($explicitPath)) {
    $resolved = Get-ExistingDirectory -Path $explicitPath
    if (-not $resolved) {
        throw 'The explicit notes vault must be an existing absolute directory. No fallback was used.'
    }
    return $resolved
}

$profileOneDrive = $null
if (-not [string]::IsNullOrWhiteSpace($env:USERPROFILE) -and
    [System.IO.Path]::IsPathFullyQualified($env:USERPROFILE)) {
    $profileOneDrive = Join-Path $env:USERPROFILE 'OneDrive'
    $preferred = Get-ExistingDirectory -Path (Join-Path $profileOneDrive '文档/notes')
    if ($preferred -and (Test-Path -LiteralPath (Join-Path $preferred '.obsidian') -PathType Container)) {
        return $preferred
    }
}

$roots = @(
    $env:OneDriveConsumer
    $env:OneDrive
    $env:OneDriveCommercial
    $profileOneDrive
) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique

$candidates = @(
    foreach ($root in $roots) {
        if (-not [System.IO.Path]::IsPathFullyQualified($root)) {
            continue
        }
        foreach ($documents in @('文档', 'Documents')) {
            $candidate = Get-ExistingDirectory -Path (Join-Path $root "$documents/notes")
            if ($candidate -and (Test-Path -LiteralPath (Join-Path $candidate '.obsidian') -PathType Container)) {
                $candidate
            }
        }
    }
) | Sort-Object -Unique

$candidates = @($candidates)
if ($candidates.Count -eq 1) {
    return $candidates[0]
}
if ($candidates.Count -gt 1) {
    throw "Multiple notes vaults found. Select one with -VaultPath or KNOWLEDGE_NOTES_VAULT: $($candidates -join '; ')"
}
throw 'No existing OneDrive notes vault with an .obsidian directory was found. Supply -VaultPath or set KNOWLEDGE_NOTES_VAULT to the intended existing vault.'
