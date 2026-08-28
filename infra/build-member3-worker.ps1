<#!
.SYNOPSIS
Builds the Docker-free Member 3 Lambda ZIP for AWS Lambda Python 3.12.

.DESCRIPTION
Requires uv on PATH.  It downloads a Linux-compatible Pillow wheel, copies
the handler, and writes build/member3-worker.zip.  Generated files remain
ignored by Git.
#>

$ErrorActionPreference = "Stop"
$infraRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $infraRoot
$buildRoot = Join-Path $infraRoot "build"
$staging = Join-Path $buildRoot "member3-worker-staging"
$archive = Join-Path $buildRoot "member3-worker.zip"

New-Item -ItemType Directory -Force -Path $staging | Out-Null
Remove-Item -Recurse -Force -LiteralPath $staging\* -ErrorAction SilentlyContinue
uv pip install --target $staging --python-platform x86_64-manylinux_2_17 --python-version 3.12 --only-binary :all: Pillow==11.3.0
Copy-Item -LiteralPath (Join-Path $projectRoot "services\worker\member3_lambda.py") -Destination $staging
Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $archive -Force
Write-Host "Built $archive"
