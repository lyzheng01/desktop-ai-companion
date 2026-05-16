$ErrorActionPreference = 'Stop'

$repoRoot = 'E:\python\desktop-ai-companion'
$distDir = Join-Path $repoRoot 'backend-dist'
$workDir = Join-Path $repoRoot 'C:\Users\lenovo\AppData\Local\Temp\opencode'

if (-not (Test-Path -LiteralPath $distDir)) {
  New-Item -ItemType Directory -Path $distDir | Out-Null
}

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --name backend-service `
  --distpath $distDir `
  --workpath (Join-Path $repoRoot 'backend-build') `
  --specpath (Join-Path $repoRoot 'backend-build') `
  --paths $repoRoot `
  "$repoRoot\backend\server.py"
