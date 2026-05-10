param(
  [string]$Mode = ""
)

$ErrorActionPreference = "Stop"

try {
  $repoRoot = (& git rev-parse --show-toplevel 2>$null).Trim()
} catch {
  $repoRoot = ""
}

if (-not $repoRoot) {
  $repoRoot = (Get-Location).Path
}

$guardPath = Join-Path $repoRoot "scripts\guard.py"
$candidates = @()

if ($env:CODEX_PROJECT_PYTHON) {
  $candidates += $env:CODEX_PROJECT_PYTHON
}

$candidates += @(
  (Join-Path $repoRoot ".venv\Scripts\python.exe"),
  "python",
  "py"
)

foreach ($candidate in $candidates) {
  if (-not $candidate) {
    continue
  }

  $command = Get-Command $candidate -ErrorAction SilentlyContinue
  if (-not $command) {
    continue
  }

  if ($candidate -eq "py") {
    & py -3 $guardPath $Mode
  } else {
    & $candidate $guardPath $Mode
  }
  exit $LASTEXITCODE
}

Write-Warning "Python was not found; skipping Codex template guard."
exit 0
