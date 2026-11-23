# WIND 2.0 — Iniciar com voz nativa ativada
# Uso: .\scripts\start_wind_voice.ps1

$WIND_DIR = Split-Path -Parent $PSScriptRoot
Set-Location $WIND_DIR

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  WIND 2.0 — Modo Voz" -ForegroundColor Cyan
Write-Host "  Diga 'WIND' para ativar o microfone" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

python src\wind.py --voz
