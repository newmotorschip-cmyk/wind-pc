# start_wind_ngrok.ps1
# Inicia WIND + túnel ngrok para acesso externo pelo iPhone
# Uso: powershell -ExecutionPolicy Bypass -File scripts\start_wind_ngrok.ps1
#
# Pré-requisitos:
#   1. ngrok instalado (https://ngrok.com/download) e no PATH
#   2. Conta ngrok gratuita — faça login com: ngrok config add-authtoken <SEU_TOKEN>
#   3. WIND_API_KEY definida: setx WIND_API_KEY suachaveaqui
#
# Depois de iniciar, copie a URL https://xxxx.ngrok-free.app no iPhone:
#   URL: https://xxxx.ngrok-free.app
#   API Key: (mesma que WIND_API_KEY)

$windDir = Split-Path $PSScriptRoot -Parent
Set-Location $windDir

Write-Host ""
Write-Host "  ====================================" -ForegroundColor Cyan
Write-Host "   WIND + ngrok" -ForegroundColor Cyan
Write-Host "  ====================================" -ForegroundColor Cyan
Write-Host ""

# Verifica ngrok
$ngrokPath = Get-Command ngrok -ErrorAction SilentlyContinue
if ($ngrokPath) {
    Write-Host "  Iniciando ngrok na porta 8765..." -ForegroundColor Yellow
    Start-Process ngrok -ArgumentList "http 8765 --log=stdout" -WindowStyle Minimized
    Start-Sleep -Seconds 2

    # Busca URL do ngrok via API local
    try {
        $tunnels = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -TimeoutSec 3
        $url = ($tunnels.tunnels | Where-Object { $_.proto -eq "https" }).public_url
        if ($url) {
            Write-Host ""
            Write-Host "  URL para o iPhone:" -ForegroundColor Green
            Write-Host "  $url" -ForegroundColor White
            Write-Host ""
            Write-Host "  Configure no app WIND no iPhone:" -ForegroundColor Gray
            Write-Host "  URL: $url" -ForegroundColor Gray
            Write-Host "  Key: (sua WIND_API_KEY)" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  ngrok iniciado. Acesse http://localhost:4040 para ver a URL." -ForegroundColor Yellow
    }
} else {
    Write-Host "  ngrok nao encontrado. Iniciando WIND so na rede local." -ForegroundColor Yellow
    Write-Host "  Para acesso externo, instale ngrok: https://ngrok.com/download" -ForegroundColor Gray
    # Mostra IP local
    $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" -and $_.PrefixOrigin -eq "Dhcp" } | Select-Object -First 1).IPAddress
    if ($ip) {
        Write-Host ""
        Write-Host "  URL local para o iPhone (mesma rede Wi-Fi):" -ForegroundColor Green
        Write-Host "  http://${ip}:8765" -ForegroundColor White
    }
}

Write-Host ""
python src\wind.py
