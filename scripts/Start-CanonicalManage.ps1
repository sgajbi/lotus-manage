param(
  [int]$Port = 8001,
  [string]$ListenHost = "0.0.0.0",
  [string]$PostgresContainerName = "lotus-manage-postgres-local",
  [int]$PostgresHostPort = 55433,
  [switch]$Foreground
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$python = if (Test-Path (Join-Path $repoRoot ".venv\\Scripts\\python.exe")) {
  Join-Path $repoRoot ".venv\\Scripts\\python.exe"
} else {
  "C:\\Python313\\python.exe"
}

function Test-PythonModule {
  param(
    [string]$PythonPath,
    [string]$ModuleName
  )

  try {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $PythonPath -c "import $ModuleName" *> $null
    return $LASTEXITCODE -eq 0
  } catch {
    return $false
  } finally {
    $ErrorActionPreference = $previousErrorActionPreference
  }
}

function Ensure-CanonicalPostgres {
  $backend = if ($env:DPM_SUPPORTABILITY_STORE_BACKEND) {
    $env:DPM_SUPPORTABILITY_STORE_BACKEND
  } else {
    "POSTGRES"
  }
  if ($backend.ToUpperInvariant() -ne "POSTGRES") {
    return
  }
  $env:DPM_SUPPORTABILITY_STORE_BACKEND = "POSTGRES"
  if ([string]::IsNullOrWhiteSpace($env:DPM_POLICY_PACK_CATALOG_BACKEND)) {
    $env:DPM_POLICY_PACK_CATALOG_BACKEND = "POSTGRES"
  }

  if (-not [string]::IsNullOrWhiteSpace($env:DPM_SUPPORTABILITY_POSTGRES_DSN)) {
    if ([string]::IsNullOrWhiteSpace($env:DPM_MANAGE_POSTGRES_DSN)) {
      $env:DPM_MANAGE_POSTGRES_DSN = $env:DPM_SUPPORTABILITY_POSTGRES_DSN
    }
    return
  }

  $existing = docker ps -a --format "{{.Names}}" | Where-Object { $_ -eq $PostgresContainerName }
  if (-not $existing) {
    docker run -d `
      --name $PostgresContainerName `
      -e POSTGRES_DB=manage_supportability `
      -e POSTGRES_USER=manage `
      -e POSTGRES_PASSWORD=manage `
      -p "${PostgresHostPort}:5432" `
      postgres:17.6 | Out-Null
  } else {
    docker start $PostgresContainerName | Out-Null
  }

  $ready = $false
  for ($i = 0; $i -lt 30; $i++) {
    docker exec $PostgresContainerName pg_isready -U manage -d manage_supportability *> $null
    if ($LASTEXITCODE -eq 0) {
      $ready = $true
      break
    }
    Start-Sleep -Seconds 2
  }
  if (-not $ready) {
    throw "lotus-manage canonical Postgres did not become ready on :$PostgresHostPort."
  }

  $dsn = "postgresql://manage:manage@127.0.0.1:$PostgresHostPort/manage_supportability"
  $env:DPM_SUPPORTABILITY_POSTGRES_DSN = $dsn
  $env:DPM_MANAGE_POSTGRES_DSN = $dsn
  if ([string]::IsNullOrWhiteSpace($env:DPM_POLICY_PACK_POSTGRES_DSN)) {
    $env:DPM_POLICY_PACK_POSTGRES_DSN = $dsn
  }
}

Ensure-CanonicalPostgres

if (
  $env:DPM_SUPPORTABILITY_STORE_BACKEND.ToUpperInvariant() -eq "POSTGRES" -and
  -not (Test-PythonModule -PythonPath $python -ModuleName "psycopg")
) {
  $globalPython = "C:\\Python313\\python.exe"
  if ((Test-Path $globalPython) -and (Test-PythonModule -PythonPath $globalPython -ModuleName "psycopg")) {
    $python = $globalPython
  } else {
    throw "lotus-manage canonical startup requires psycopg for POSTGRES supportability."
  }
}

if ($env:DPM_SUPPORTABILITY_STORE_BACKEND.ToUpperInvariant() -eq "POSTGRES") {
  & $python (Join-Path $repoRoot "scripts\\postgres_migrate.py") --target dpm
  if ($LASTEXITCODE -ne 0) {
    throw "lotus-manage canonical Postgres migration failed."
  }
}

$env:PYTHONPATH = Join-Path $repoRoot "src"
$arguments = @(
  "-m", "uvicorn",
  "src.api.main:app",
  "--host", $ListenHost,
  "--port", "$Port"
)

if ($Foreground) {
  Push-Location $repoRoot
  try {
    & $python @arguments
    exit $LASTEXITCODE
  } finally {
    Pop-Location
  }
}

try {
  $existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop |
    Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($pid in $existing) {
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
  }
} catch {
}

$stdout = Join-Path $repoRoot "manage-$Port.out.log"
$stderr = Join-Path $repoRoot "manage-$Port.err.log"
try { if (Test-Path $stdout) { Remove-Item $stdout -Force -ErrorAction Stop } } catch {}
try { if (Test-Path $stderr) { Remove-Item $stderr -Force -ErrorAction Stop } } catch {}

Start-Process -FilePath $python `
  -ArgumentList $arguments `
  -WorkingDirectory $repoRoot `
  -RedirectStandardOutput $stdout `
  -RedirectStandardError $stderr | Out-Null

Start-Sleep -Seconds 5
$response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health/ready" -UseBasicParsing -TimeoutSec 15
if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 300) {
  throw "lotus-manage canonical startup failed on port $Port."
}

Write-Host "lotus-manage canonical startup ready on http://127.0.0.1:$Port"
