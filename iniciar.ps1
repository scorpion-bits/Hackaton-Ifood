# Sobe tudo no Windows, SEM Docker.
#   powershell -ExecutionPolicy Bypass -File .\iniciar.ps1           compila o frontend e abre http://localhost:8000
#   powershell -ExecutionPolicy Bypass -File .\iniciar.ps1 -Dev      backend com reload + Vite (5173)
#   powershell -ExecutionPolicy Bypass -File .\iniciar.ps1 -Testes   testes do backend + tipos do frontend
param([switch]$Dev, [switch]$Testes)
$ErrorActionPreference = "Stop"
$Raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Raiz

function Checar($cmd, $msg) { if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { Write-Host $msg -ForegroundColor Red; exit 1 } }

# Python: prefere o lançador "py"; senão "python"
if (Get-Command py -ErrorAction SilentlyContinue) { $PyBase = "py" } else { Checar python "Falta Python 3.11+ (python.org, marque 'Add to PATH')"; $PyBase = "python" }
Checar npm "Falta Node.js 20+ (nodejs.org)"

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env"; Write-Host "Criei .env a partir de .env.example (modo mock)." }

$Py = Join-Path $Raiz "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
  Write-Host "Criando ambiente Python em backend\.venv ..."
  & $PyBase -m venv backend\.venv
  if ($LASTEXITCODE -ne 0) { throw "Falha ao criar o venv" }
}
& $Py -m pip install -q -r backend\requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Falha no pip install (veja o README, seção Windows)" }

if (-not (Test-Path "frontend\node_modules")) {
  Push-Location frontend; npm install --no-fund --no-audit; Pop-Location
  if ($LASTEXITCODE -ne 0) { throw "Falha no npm install" }
}

if ($Testes) {
  Push-Location backend; & $Py -m pytest -q; $r1 = $LASTEXITCODE; Pop-Location
  Push-Location frontend; npm run typecheck; $r2 = $LASTEXITCODE; Pop-Location
  exit [Math]::Max($r1, $r2)
}

if ($Dev) {
  Start-Process -FilePath $Py -ArgumentList "-m uvicorn app.main:app --reload --port 8000" -WorkingDirectory (Join-Path $Raiz "backend")
  Push-Location frontend; npm run dev; Pop-Location
  exit
}

Push-Location frontend; npm run build; Pop-Location
if ($LASTEXITCODE -ne 0) { throw "Falha no build do frontend" }
Write-Host "Subindo o servidor em http://localhost:8000 (na 1a vez pode levar ~30 s; Ctrl+C para parar)" -ForegroundColor Green
$Ip = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
  Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } | Select-Object -First 1).IPAddress
if ($Ip) { Write-Host "Celulares na mesma rede Wi-Fi: http://${Ip}:8000 (se o Windows perguntar, permita em rede privada)" }
# Abre o navegador só quando o servidor responder (antes abria após 4 s fixos e dava "conexão recusada")
Start-Job {
  for ($i = 0; $i -lt 90; $i++) {
    try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 "http://127.0.0.1:8000/api/saude" | Out-Null; Start-Process "http://localhost:8000"; return }
    catch { Start-Sleep -Seconds 1 }
  }
} | Out-Null
Push-Location backend
& $Py -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Pop-Location
