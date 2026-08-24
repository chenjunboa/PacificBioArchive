param(
    [Parameter(Mandatory = $true)]
    [string]$DetectorPath,

    [Parameter(Mandatory = $true)]
    [string]$ClassifierPath
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$detector = Resolve-Path -LiteralPath $DetectorPath
$classifier = Resolve-Path -LiteralPath $ClassifierPath
$labels = Join-Path $repositoryRoot "labels.txt"
$manifestTemplate = Join-Path $repositoryRoot "model-manifest.json"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$bundle = Join-Path $repositoryRoot ".model-bundles\$timestamp"

New-Item -ItemType Directory -Path $bundle | Out-Null
Copy-Item -LiteralPath $detector -Destination (Join-Path $bundle "mdv5a.pt")
Copy-Item -LiteralPath $classifier -Destination (Join-Path $bundle "model.pt")

# Git's canonical labels file uses LF. Produce the same bytes on Windows and Linux.
$labelText = [System.IO.File]::ReadAllText($labels).Replace("`r`n", "`n").Replace("`r", "`n")
$utf8WithoutBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText((Join-Path $bundle "labels.txt"), $labelText, $utf8WithoutBom)

$manifest = Get-Content -LiteralPath $manifestTemplate -Raw | ConvertFrom-Json
$manifest.detector.path = "mdv5a.pt"
$manifest.classifier.path = "model.pt"
$manifest.labels.path = "labels.txt"
$manifest.detector.sha256 = (Get-FileHash (Join-Path $bundle "mdv5a.pt") -Algorithm SHA256).Hash.ToLower()
$manifest.classifier.sha256 = (Get-FileHash (Join-Path $bundle "model.pt") -Algorithm SHA256).Hash.ToLower()
$manifest.labels.sha256 = (Get-FileHash (Join-Path $bundle "labels.txt") -Algorithm SHA256).Hash.ToLower()
$manifestJson = $manifest | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText(
    (Join-Path $bundle "model-manifest.json"),
    $manifestJson,
    $utf8WithoutBom
)

Write-Host "Prepared model bundle: $bundle"
$hashes = Get-FileHash (Join-Path $bundle "mdv5a.pt"), (Join-Path $bundle "model.pt"), (Join-Path $bundle "labels.txt") -Algorithm SHA256
$hashes | Format-Table | Out-Host
Write-Output $bundle
