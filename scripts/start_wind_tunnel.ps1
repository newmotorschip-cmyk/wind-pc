# start_wind_tunnel.ps1
# Inicia WIND API + Cloudflare Tunnel para acesso externo de qualquer WiFi.
#
# Uso:
#   .\scripts\start_wind_tunnel.ps1
#
# O que faz:
#   1. Verifica/instala cloudflared (via winget)
#   2. Inicia o servidor HTTP da WIND (porta 8765) em background
#   3. Abre um tunel Cloudflare publico com HTTPS
#   4. Exibe a URL — cole-a nas configuracoes do PWA no iPhone
#   5. Ctrl+C encerra API + tunel juntos

$ErrorActionPreference = "SilentlyContinue"

$RootDir = Split-Path $PSScriptRoot
Set-Location $RootDir

# ── Banner ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ██╗    ██╗██╗███╗   ██╗██████╗  " -ForegroundColor Cyan
Write-Host "  ██║    ██║██║████╗  ██║██╔══██╗ " -ForegroundColor Cyan
Write-Host "  ██║ █╗ ██║██║██╔██╗ ██║██║  ██║ " -ForegroundColor Cyan
Write-Host "  ██║███╗██║██║██║╚██╗██║██║  ██║ " -ForegroundColor Cyan
Write-Host "  ╚███╔███╔╝██║██║ ╚████║██████╔╝ " -ForegroundColor Cyan
Write-Host "   ╚══╝╚══╝ ╚═╝╚═╝  ╚═══╝╚═════╝  " -ForegroundColor Cyan
Write-Host "  Acesso externo via Cloudflare Tunnel" -ForegroundColor Gray
Write-Host ""

# ── 1. Verificar cloudflared ─────────────────────────────────────────────────
$cfPath = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cfPath) {
    Write-Host "[1/3] cloudflared nao encontrado. Instalando via winget..." -ForegroundColor Yellow
    winget install Cloudflare.cloudflared --silent --accept-package-agreements --accept-source-agreements

    # Atualizar PATH da sessao atual
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH","User")

    $cfPath = Get-Command cloudflared -ErrorAction SilentlyContinue
    if (-not $cfPath) {
        Write-Host ""
        Write-Host "[ERRO] cloudflared nao foi encontrado apos a instalacao." -ForegroundColor Red
        Write-Host "       Instale manualmente e reinicie o PowerShell:" -ForegroundColor Red
        Write-Host "       winget install Cloudflare.cloudflared" -ForegroundColor White
        Write-Host ""
        Read-Host "Pressione Enter para fechar"
        exit 1
    }
    Write-Host "[1/3] cloudflared instalado: $($cfPath.Source)" -ForegroundColor Green
} else {
    Write-Host "[1/3] cloudflared: OK ($($cfPath.Source))" -ForegroundColor Green
}

# ── 2. Iniciar WIND API em background ────────────────────────────────────────
Write-Host "[2/3] Iniciando WIND API (porta 8765)..." -ForegroundColor Cyan

$apiProc = Start-Process python `
    -ArgumentList "scripts\run_api.py" `
    -PassThru `
    -WindowStyle Minimized `
    -ErrorAction Stop

Write-Host "[2/3] API iniciada (PID $($apiProc.Id)). Aguardando 4s..." -ForegroundColor Green
Start-Sleep 4

# Verificar se a API subiu
$apiOk = $false
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:8765/status" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    $apiOk = $true
    Write-Host "[2/3] API respondendo: OK" -ForegroundColor Green
} catch {
    Write-Host "[2/3] API ainda carregando (continuando mesmo assim)..." -ForegroundColor Yellow
}

# ── 3. Iniciar Cloudflare Tunnel ─────────────────────────────────────────────
Write-Host "[3/3] Abrindo tunel Cloudflare..." -ForegroundColor Cyan
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  Procure a linha abaixo que contem 'trycloudflare.com':      " -ForegroundColor White
Write-Host "                                                               " -ForegroundColor White
Write-Host "  Exemplo:                                                     " -ForegroundColor Gray
Write-Host "  https://xxxx-xxxx-xxxx-xxxx.trycloudflare.com               " -ForegroundColor Yellow
Write-Host "                                                               " -ForegroundColor White
Write-Host "  Cole essa URL nas configuracoes do PWA no iPhone.           " -ForegroundColor White
Write-Host "  Ctrl+C encerra API + tunel.                                  " -ForegroundColor Gray
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

try {
    cloudflared tunnel --url http://localhost:8765
} finally {
    Write-Host ""
    Write-Host "Encerrando WIND API (PID $($apiProc.Id))..." -ForegroundColor Yellow
    if (-not $apiProc.HasExited) {
        Stop-Process -Id $apiProc.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Encerrado." -ForegroundColor Gray
    Write-Host ""
}
