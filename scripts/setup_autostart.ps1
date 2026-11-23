# ============================================================
#  WIND 2.0 — Registrar inicialização automática no Windows
#  Execute: powershell -ExecutionPolicy Bypass -File scripts\setup_autostart.ps1
#
#  Cria tarefa no Agendador de Tarefas do Windows para iniciar
#  a WIND automaticamente ao entrar no sistema.
#  Para desativar: schtasks /Delete /TN "WIND_AutoStart" /F
# ============================================================

$WIND_DIR  = Split-Path -Parent $PSScriptRoot
$TASK_NAME = "WIND_AutoStart"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  WIND 2.0 — Configurar inicialização automática" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se tarefa já existe
$existing = schtasks /Query /TN $TASK_NAME /FO LIST 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Tarefa '$TASK_NAME' já existe." -ForegroundColor Yellow
    $resp = Read-Host "  Deseja recriar? (s/N)"
    if ($resp -notmatch "^[sS]$") {
        Write-Host "  Cancelado." -ForegroundColor Gray
        exit 0
    }
    schtasks /Delete /TN $TASK_NAME /F | Out-Null
    Write-Host "  Tarefa anterior removida." -ForegroundColor Gray
}

# Criar script de inicialização minimalista
$startScript = Join-Path $WIND_DIR "scripts\start_wind_minimized.ps1"
$startContent = @"
# WIND 2.0 — Inicio automatico (gerado por setup_autostart.ps1)
Set-Location "$WIND_DIR"
python src\wind.py
"@
Set-Content -Path $startScript -Value $startContent -Encoding UTF8

# Registrar tarefa no Agendador de Tarefas
$action     = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-WindowStyle Minimized -ExecutionPolicy Bypass -File `"$startScript`"" `
    -WorkingDirectory $WIND_DIR

$trigger    = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings   = New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0 -MultipleInstances IgnoreNew
$principal  = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME -RunLevel Limited -LogonType Interactive

Register-ScheduledTask `
    -TaskName $TASK_NAME `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "WIND 2.0 - Iniciar ao entrar no Windows" `
    -Force | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "  ✅ WIND configurada para iniciar automaticamente ao login." -ForegroundColor Green
    Write-Host ""
    Write-Host "  Para desativar:" -ForegroundColor Gray
    Write-Host "    schtasks /Delete /TN `"$TASK_NAME`" /F" -ForegroundColor Gray
    Write-Host "  Ou: Gerenciador de Tarefas → Inicialização → WIND_AutoStart" -ForegroundColor Gray
} else {
    Write-Host "  ERRO: Falha ao registrar tarefa. Verifique permissões." -ForegroundColor Red
}
Write-Host ""
