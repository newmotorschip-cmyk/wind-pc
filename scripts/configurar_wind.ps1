# ============================================================
#  WIND 2.0 — Configuração das integrações (Telegram + GitHub)
#  Execute: powershell -ExecutionPolicy Bypass -File scripts\configurar_wind.ps1
# ============================================================

function Test-EnvVar($name) {
    $m = [System.Environment]::GetEnvironmentVariable($name, "Machine")
    $u = [System.Environment]::GetEnvironmentVariable($name, "User")
    return ($m -or $u)
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  WIND 2.0 — Configuração de integrações" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ── Status atual ──────────────────────────────────────────────────────────────
Write-Host "Estado atual:" -ForegroundColor Yellow
$vars = @("ANTHROPIC_API_KEY","WIND_API_KEY","TELEGRAM_BOT_TOKEN","TELEGRAM_CHAT_ID","GITHUB_TOKEN")
foreach ($v in $vars) {
    if (Test-EnvVar $v) { Write-Host "  ✅ $v" -ForegroundColor Green }
    else                { Write-Host "  ❌ $v" -ForegroundColor Red }
}
Write-Host ""

# ── Telegram ──────────────────────────────────────────────────────────────────
if (-not (Test-EnvVar "TELEGRAM_BOT_TOKEN") -or -not (Test-EnvVar "TELEGRAM_CHAT_ID")) {
    Write-Host "[ Telegram — notificações no iPhone ]" -ForegroundColor Cyan
    Write-Host "  1. Abra o Telegram e procure por @BotFather"
    Write-Host "  2. Envie /newbot e siga as instruções"
    Write-Host "  3. Copie o token que o BotFather enviar"
    Write-Host "  4. Envie qualquer mensagem ao seu novo bot"
    Write-Host "  5. Acesse no navegador (substitua <TOKEN>):"
    Write-Host "     https://api.telegram.org/bot<TOKEN>/getUpdates" -ForegroundColor Gray
    Write-Host "  6. Copie o valor de 'id' dentro de 'chat'"
    Write-Host ""

    $tok = Read-Host "  Cole o token do bot (ou Enter para pular)"
    if ($tok.Trim()) {
        [System.Environment]::SetEnvironmentVariable("TELEGRAM_BOT_TOKEN", $tok.Trim(), "User")
        $env:TELEGRAM_BOT_TOKEN = $tok.Trim()
        Write-Host "  ✅ TELEGRAM_BOT_TOKEN salvo." -ForegroundColor Green

        $cid = Read-Host "  Cole o chat_id"
        if ($cid.Trim()) {
            [System.Environment]::SetEnvironmentVariable("TELEGRAM_CHAT_ID", $cid.Trim(), "User")
            $env:TELEGRAM_CHAT_ID = $cid.Trim()
            Write-Host "  ✅ TELEGRAM_CHAT_ID salvo." -ForegroundColor Green

            # Testar envio
            Write-Host "  Testando conexão..."
            $url   = "https://api.telegram.org/bot$($tok.Trim())/sendMessage"
            $body  = @{ chat_id = $cid.Trim(); text = "✅ WIND conectada ao Telegram!" } | ConvertTo-Json
            try {
                $r = Invoke-RestMethod -Uri $url -Method Post -ContentType "application/json" -Body $body
                if ($r.ok) { Write-Host "  ✅ Mensagem de teste enviada com sucesso!" -ForegroundColor Green }
                else       { Write-Host "  ⚠️  API retornou erro — verifique token e chat_id." -ForegroundColor Yellow }
            } catch {
                Write-Host "  ⚠️  Falha no teste: $_" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "  ⏭  Telegram pulado." -ForegroundColor Gray
    }
    Write-Host ""
} else {
    Write-Host "  ✓  Telegram já configurado." -ForegroundColor Green
    Write-Host ""
}

# ── GitHub ────────────────────────────────────────────────────────────────────
if (-not (Test-EnvVar "GITHUB_TOKEN")) {
    Write-Host "[ GitHub — acompanhar repositórios ]" -ForegroundColor Cyan
    Write-Host "  1. Acesse: github.com/settings/tokens/new"
    Write-Host "  2. Note: 'WIND personal token'"
    Write-Host "  3. Escopo mínimo: repo (ou public_repo para só públicos)"
    Write-Host "  4. Clique em 'Generate token' e copie"
    Write-Host ""

    $gt = Read-Host "  Cole o token GitHub (ou Enter para pular)"
    if ($gt.Trim()) {
        [System.Environment]::SetEnvironmentVariable("GITHUB_TOKEN", $gt.Trim(), "User")
        $env:GITHUB_TOKEN = $gt.Trim()
        Write-Host "  ✅ GITHUB_TOKEN salvo." -ForegroundColor Green

        # Testar autenticação
        try {
            $headers = @{ Authorization = "Bearer $($gt.Trim())"; Accept = "application/vnd.github+json" }
            $me = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $headers
            Write-Host "  ✅ Autenticado como: $($me.login)" -ForegroundColor Green
        } catch {
            Write-Host "  ⚠️  Falha na autenticação — verifique o token." -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ⏭  GitHub pulado." -ForegroundColor Gray
    }
    Write-Host ""
} else {
    Write-Host "  ✓  GitHub já configurado." -ForegroundColor Green
    Write-Host ""
}

# ── Resumo final ──────────────────────────────────────────────────────────────
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Configuração concluída. Estado final:" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
foreach ($v in $vars) {
    if (Test-EnvVar $v) { Write-Host "  ✅ $v" -ForegroundColor Green }
    else                { Write-Host "  ❌ $v — não configurado" -ForegroundColor Red }
}
Write-Host ""
Write-Host "Para iniciar a WIND:" -ForegroundColor Yellow
Write-Host "  python src\wind.py" -ForegroundColor White
Write-Host ""
Write-Host "Ou com voz ativa:" -ForegroundColor Yellow
Write-Host "  python src\wind.py --voz" -ForegroundColor White
Write-Host ""
