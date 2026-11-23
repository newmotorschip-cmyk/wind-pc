# ============================================================
#  WIND 2.0 — Instalador Windows
#  Execute como: powershell -ExecutionPolicy Bypass -File install_wind.ps1
# ============================================================

$ErrorActionPreference = "Stop"
$WIND_DIR = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  WIND 2.0 — Instalador" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Verificar Python ────────────────────────────────────────────────────────
Write-Host "[1/7] Verificando Python..." -ForegroundColor Yellow
try {
    $pyver = python --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Python nao encontrado" }
    Write-Host "  OK: $pyver" -ForegroundColor Green

    $pyminor = [int]($pyver -replace ".*3\.(\d+).*", '$1')
    if ($pyminor -lt 10) {
        Write-Host "  AVISO: Python 3.10+ recomendado (encontrado 3.$pyminor)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ERRO: Python nao encontrado. Instale em https://python.org" -ForegroundColor Red
    exit 1
}

# ── 2. Instalar dependencias core ─────────────────────────────────────────────
Write-Host ""
Write-Host "[2/7] Instalando dependencias core..." -ForegroundColor Yellow
Set-Location $WIND_DIR

$core_packages = @(
    "anthropic>=0.40.0",
    "openai>=1.50.0",
    "psutil>=5.9.0",
    "requests>=2.31.0"
)

foreach ($pkg in $core_packages) {
    Write-Host "  pip install $pkg" -ForegroundColor Gray
    python -m pip install $pkg --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  AVISO: falha ao instalar $pkg" -ForegroundColor Yellow
    }
}
Write-Host "  Dependencias core instaladas." -ForegroundColor Green

# ── 3. Instalar dependencias de automacao (Fase 11) ───────────────────────────
Write-Host ""
Write-Host "[3/7] Instalando dependencias de automacao (voz, desktop)..." -ForegroundColor Yellow

$auto_packages = @(
    "pyautogui>=0.9.54",
    "pyperclip>=1.8.2",
    "pygetwindow>=0.0.9",
    "SpeechRecognition>=3.10.0"
)

foreach ($pkg in $auto_packages) {
    Write-Host "  pip install $pkg" -ForegroundColor Gray
    python -m pip install $pkg --quiet 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  AVISO: $pkg falhou (opcional)" -ForegroundColor Yellow
    }
}

# pyaudio: instalacao especial no Windows
Write-Host "  Tentando instalar pyaudio..." -ForegroundColor Gray
python -m pip install pyaudio --quiet 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  AVISO: pyaudio falhou via pip. Tentando pipwin..." -ForegroundColor Yellow
    python -m pip install pipwin --quiet 2>$null
    python -m pipwin install pyaudio 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  AVISO: pyaudio nao instalado. Voz nativa desativada." -ForegroundColor Yellow
        Write-Host "  Para instalar manualmente: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio" -ForegroundColor Gray
    } else {
        Write-Host "  pyaudio instalado via pipwin." -ForegroundColor Green
    }
} else {
    Write-Host "  pyaudio instalado." -ForegroundColor Green
}

# ── 4. Configurar chaves de API ───────────────────────────────────────────────
Write-Host ""
Write-Host "[4/7] Configurando chaves de API..." -ForegroundColor Yellow

$existing_anthropic = [System.Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY", "User")
$existing_openai    = [System.Environment]::GetEnvironmentVariable("OPENAI_API_KEY", "User")
$existing_wind      = [System.Environment]::GetEnvironmentVariable("WIND_API_KEY", "User")

if ($existing_anthropic) {
    Write-Host "  ANTHROPIC_API_KEY: ja configurada." -ForegroundColor Green
} else {
    Write-Host "  ANTHROPIC_API_KEY nao encontrada." -ForegroundColor Yellow
    $key = Read-Host "  Cole sua chave Anthropic (Enter para pular)"
    if ($key) {
        [System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", $key, "User")
        Write-Host "  ANTHROPIC_API_KEY configurada." -ForegroundColor Green
    }
}

if ($existing_openai) {
    Write-Host "  OPENAI_API_KEY: ja configurada." -ForegroundColor Green
} else {
    $key = Read-Host "  Cole sua chave OpenAI (Enter para pular)"
    if ($key) {
        [System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", $key, "User")
        Write-Host "  OPENAI_API_KEY configurada." -ForegroundColor Green
    }
}

if (-not $existing_wind) {
    # Gerar chave aleatoria para API server
    $wind_key = [System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
    $wind_key = $wind_key -replace "[/+=]", ""
    [System.Environment]::SetEnvironmentVariable("WIND_API_KEY", $wind_key, "User")
    # Salvar no .env.wind tambem
    Set-Content -Path "$WIND_DIR\.env.wind" -Value "WIND_API_KEY=$wind_key" -Encoding UTF8
    Write-Host "  WIND_API_KEY gerada e salva." -ForegroundColor Green
} else {
    Write-Host "  WIND_API_KEY: ja configurada." -ForegroundColor Green
}

# ── 5. Criar pasta de dados ───────────────────────────────────────────────────
Write-Host ""
Write-Host "[5/7] Criando estrutura de dados..." -ForegroundColor Yellow
$data_dir = Join-Path $WIND_DIR "data"
if (-not (Test-Path $data_dir)) {
    New-Item -ItemType Directory -Path $data_dir | Out-Null
}
Write-Host "  OK: $data_dir" -ForegroundColor Green

# ── 6. Criar atalho na area de trabalho ──────────────────────────────────────
Write-Host ""
Write-Host "[6/7] Criando atalho na area de trabalho..." -ForegroundColor Yellow

$desktop     = [System.Environment]::GetFolderPath("Desktop")
$shortcut    = Join-Path $desktop "WIND.lnk"
$wind_script = Join-Path $WIND_DIR "src\wind.py"
$start_bat   = Join-Path $WIND_DIR "scripts\start_wind.bat"

# Criar start_wind.bat atualizado
$bat_content = @"
@echo off
title WIND 2.0
cd /d "$WIND_DIR"
python src\wind.py
pause
"@
Set-Content -Path $start_bat -Value $bat_content -Encoding ASCII

$wsh = New-Object -ComObject WScript.Shell
$lnk = $wsh.CreateShortcut($shortcut)
$lnk.TargetPath       = "powershell.exe"
$lnk.Arguments        = "-ExecutionPolicy Bypass -NoExit -Command `"cd '$WIND_DIR'; python src\wind.py`""
$lnk.WorkingDirectory = $WIND_DIR
$lnk.Description      = "WIND 2.0 - IA Pessoal"
$lnk.Save()
Write-Host "  Atalho criado: $shortcut" -ForegroundColor Green

# ── 7. Verificar instalacao ───────────────────────────────────────────────────
Write-Host ""
Write-Host "[7/7] Verificando instalacao..." -ForegroundColor Yellow
Set-Location $WIND_DIR
$health = python -c "
import sys
sys.path.insert(0, '.')
try:
    from src.core.orchestrator import Orchestrator
    orc = Orchestrator()
    st = orc.status()
    models = list(st['router']['models_available'].keys())
    print('OK: modelos=' + str(models))
except Exception as e:
    print('ERRO: ' + str(e))
" 2>&1
Write-Host "  $health" -ForegroundColor $(if ($health -like "OK*") { "Green" } else { "Yellow" })

# ── Resumo ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Instalacao concluida!" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Para iniciar a WIND:" -ForegroundColor White
Write-Host "    - Duplo clique no atalho 'WIND' na area de trabalho" -ForegroundColor Gray
Write-Host "    - Ou: python src\wind.py" -ForegroundColor Gray
Write-Host "    - Com voz: python src\wind.py --voz" -ForegroundColor Gray
Write-Host "    - Com iPhone: .\scripts\start_wind_ngrok.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "  IMPORTANTE: Feche e reabra o PowerShell para as variaveis" -ForegroundColor Yellow
Write-Host "  de ambiente entrarem em vigor." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
