# Build a clean academic submission ZIP (excludes .venv, caches, bytecode, backups).
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$stage = Join-Path $env:TEMP "FastRoute_pack_$stamp"
$out = Join-Path $root "FastRoute_submission_$stamp.zip"

if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Path $stage | Out-Null

$include = @(
  'app.py', 'README.md', 'requirements.txt', 'CONTRIBUTIONS.md', '.gitignore',
  'src', 'tests', 'pages', 'benchmarks', 'docs', 'scripts', 'presentation', 'figures',
  'data\food_delivery_dataset.csv', 'data\grubhub.csv', '.streamlit'
)
foreach ($item in $include) {
  $src = Join-Path $root $item
  if (Test-Path $src) {
    $dest = Join-Path $stage $item
    $parent = Split-Path $dest -Parent
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    Copy-Item -Path $src -Destination $dest -Recurse -Force
  }
}

# Keep data/user structure without huge duplicate grubhub if present
$userData = Join-Path $root 'data\user'
if (Test-Path $userData) {
  $destUser = Join-Path $stage 'data\user'
  New-Item -ItemType Directory -Force -Path $destUser | Out-Null
  Get-ChildItem $userData -File | Where-Object { $_.Name -ne 'grubhub.csv' } | ForEach-Object {
    Copy-Item $_.FullName -Destination (Join-Path $destUser $_.Name) -Force
  }
}

Get-ChildItem $stage -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
if (Test-Path $out) { Remove-Item $out -Force }
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $out -CompressionLevel Optimal
Remove-Item $stage -Recurse -Force
Write-Host "Created $out"
