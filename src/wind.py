"""
WIND 2.0 — Entrypoint CLI
Uso: python src/wind.py [--voz]

  --voz    Ativa escuta contínua por wake word "WIND" (requer pyaudio)

Comandos especiais durante a conversa:
  /status           — mostra orçamento, modelos disponíveis e ID de sessão
  /memoria          — lista últimos itens na memória episódica
  /projetos         — lista projetos ativos
  /projeto X        — cria ou mostra projeto X
  /missoes          — lista missões ativas
  /continuar X      — retoma projeto X (injeta contexto)
  /casos            — lista casos de serviço em aberto
  /caso             — abre novo caso de serviço (modo interativo)
  /fechar-caso X    — fecha caso com 3 perguntas
  /re-matriz        — mostra matriz de suporte Ghidra (arquiteturas ECU)
  /re-analisar X    — analisa arquivo ECU no pipeline de engenharia reversa
  /cal-familias     — lista famílias de ECU conhecidas
  /cal-mapas        — lista taxonomia de mapas de calibração
  /cal-propostas    — lista propostas de calibração pendentes
  /fw-protocolos    — lista protocolos automotivos (CAN/UDS/KWP/K-Line)
  /fw-bootloaders   — lista perfis de bootloader conhecidos
  /resumo           — gera resumo matinal de todos os subsistemas
  /notificar X      — envia notificação com texto X para todos os canais
  /falar X          — síntese de voz com texto X (Windows SAPI)
  /api-start        — inicia servidor HTTP da WIND (padrão: porta 8765)
  /api-status       — mostra estado do servidor HTTP
  /financas-contas  — lista contas cadastradas com saldo consolidado
  /financas-resumo  — resumo financeiro do mês atual
  /financas-anual   — resumo anual do ano corrente
  /financas-alertas — alertas de variação de gastos
  /financas-importar X — importa extrato OFX ou CSV do arquivo X
  /autonomia        — mostra nível de autonomia atual e histórico
  /decisoes         — lista decisões pendentes de aprovação
  /aprovar X        — aprova decisão com ID (prefixo) X
  /notas            — lista notas de aprendizado propostas
  /validar-nota X   — valida nota com ID X (confirmação de aprendizado)
  /curriculo        — mostra currículo de estudo
  /estudar X        — marca tópico X (ID) como em andamento
  /retrospectiva    — gera retrospectiva dos últimos 7 dias
  /saude            — health check / checklist de Release Candidate
  /backup           — cria backup do estado (data/ + config)
  /backups          — lista backups existentes
  /restaurar X      — restaura backup (nome ou índice da lista)
  /migrar           — aplica migrações de banco pendentes
  /voz              — ativa/desativa escuta por wake word "WIND"
  /desktop <cmd>    — executa ação no desktop (open_app, git_status, etc.)
  /git-status [path]— git status do caminho (padrão: diretório atual)
  /git-commit <msg> — git add -A + commit com mensagem
  /git-diff         — git diff do diretório atual
  /ls [path]        — lista arquivos do caminho (padrão: diretório atual)
  /ler <path>       — lê conteúdo de arquivo
  /screenshot       — captura a tela e mostra o caminho do arquivo
  /clipboard        — lê conteúdo da área de transferência
  /pc-status        — status detalhado do PC (CPU, RAM, disco)
  /sair             — encerra
  /ajuda            — lista comandos
"""
from __future__ import annotations

import sys
import os

# Adicionar raiz do projeto ao path para imports relativos funcionarem
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.orchestrator import Orchestrator
from src.core.identity import NAME, VERSION, OWNER


HELP_TEXT = """
Comandos disponíveis:
  /status           — orçamento e modelos disponíveis
  /memoria          — últimas interações salvas
  /projetos         — lista projetos ativos
  /projeto X        — cria ou mostra projeto X
  /missoes          — lista missões ativas
  /continuar X      — retoma projeto X com contexto completo
  /casos            — lista casos de serviço em aberto
  /caso             — abre novo caso de serviço (modo interativo)
  /fechar-caso X    — fecha caso X com 3 perguntas
  /re-matriz        — matriz de suporte Ghidra (arquiteturas ECU)
  /re-analisar X    — analisa arquivo ECU (caminho completo)
  /cal-familias     — famílias de ECU conhecidas (Bosch, Continental, Delphi, Denso, Marelli)
  /cal-mapas        — taxonomia de mapas de calibração por categoria
  /cal-propostas    — propostas de calibração pendentes de aprovação
  /fw-protocolos    — protocolos automotivos (CAN, UDS, KWP2000, K-Line, OBD-II)
  /fw-bootloaders   — perfis de bootloader conhecidos por família de ECU
  /resumo           — resumo matinal de todos os subsistemas
  /notificar X      — envia notificação com texto X (todos os canais disponíveis)
  /falar X          — síntese de voz Windows SAPI com texto X
  /api-start        — inicia servidor HTTP da WIND (porta 8765 padrão)
  /api-status       — mostra estado e URL do servidor HTTP
  /financas-contas  — lista contas com saldo consolidado (somente leitura)
  /financas-resumo  — resumo do mês atual por categoria
  /financas-anual   — resumo anual do ano corrente
  /financas-alertas — alertas de variação de gastos vs mês anterior
  /financas-importar X — importa extrato OFX ou CSV (arquivo X)
  /saude            — health check / checklist de Release Candidate
  /backup           — cria backup ZIP do estado atual
  /backups          — lista backups disponíveis
  /restaurar X      — restaura backup X (nome ou índice)
  /migrar           — aplica migrações de banco pendentes
  /autonomia        — nível de autonomia atual e histórico de alterações
  /decisoes         — decisões pendentes de aprovação do Felipe
  /aprovar X        — aprova decisão com ID (prefixo) X
  /notas            — notas de aprendizado propostas aguardando validação
  /validar-nota X   — valida nota com ID X
  /curriculo        — currículo de estudo (tópicos pendentes / concluídos)
  /estudar X        — marca tópico (ID) X como em andamento
  /retrospectiva    — retrospectiva dos últimos 7 dias
  /voz              — ativa/desativa escuta contínua por wake word "WIND"
  /desktop <cmd>    — executa ação desktop (ex: /desktop open_app browser)
  /git-status [path]— git status (padrão: diretório atual)
  /git-commit <msg> — git add -A + commit
  /git-diff         — git diff do diretório atual
  /ls [path]        — lista arquivos
  /ler <path>       — lê conteúdo de arquivo
  /screenshot       — captura tela
  /clipboard        — lê área de transferência
  /pc-status        — status detalhado do PC (CPU, RAM, disco)
  /sair             — encerrar sessão
  /ajuda            — este texto
"""


def main() -> None:
    voice_mode = "--voz" in sys.argv

    print(f"\n{'='*50}")
    print(f"  {NAME} {VERSION} — Olá, {OWNER}!")
    print(f"{'='*50}\n")

    orc = Orchestrator()

    # Desktop agent compartilhado
    from src.desktop.agent import DesktopAgent
    desktop = DesktopAgent(project_root=".")

    # Voice agent (lazy — só inicia se solicitado)
    _voice_agent = None

    def _get_voice_agent():
        nonlocal _voice_agent
        if _voice_agent is None:
            from src.voice.voice_agent import VoiceAgent
            _voice_agent = VoiceAgent(orchestrator=orc)
        return _voice_agent

    # Verificar disponibilidade de modelos e avisar
    status = orc.status()
    unavailable = status["router"].get("models_unavailable", {})
    if unavailable:
        missing = []
        if any("anthropic" in k or "claude" in k.lower() for k in unavailable):
            missing.append("ANTHROPIC_API_KEY")
        if any("openai" in k or "o4" in k.lower() for k in unavailable):
            missing.append("OPENAI_API_KEY")
        if missing:
            print(
                f"⚠️  Modelos indisponíveis. Configure as chaves de API:\n"
                + "\n".join(f"  setx {k} <sua-chave>" for k in missing)
                + "\n"
            )

    available = status["router"].get("models_available", {})
    if available:
        print(f"Modelos prontos: {', '.join(available.keys())}")
    else:
        print("⚠️  Nenhum modelo disponível. Configure ANTHROPIC_API_KEY ou OPENAI_API_KEY.")
        print("Digite /ajuda para ver os comandos. Ctrl+C para sair.\n")

    print('Digite sua mensagem. "/ajuda" para comandos.\n')

    # Ativar voz se --voz passado na linha de comando
    if voice_mode:
        va = _get_voice_agent()
        if va.start():
            print("WIND: Voz ativa. Diga 'WIND' para ativar o microfone.\n")
        else:
            print(f"WIND: Voz indisponível.\n{va.install_hint()}\n")

    while True:
        try:
            user_input = input("Felipe: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nAté logo!")
            if _voice_agent:
                _voice_agent.stop()
            break

        if not user_input:
            continue

        # Comandos especiais
        if user_input == "/sair":
            print("WIND: Até logo!")
            break

        if user_input == "/ajuda":
            print(HELP_TEXT)
            continue

        if user_input == "/status":
            st = orc.status()
            budget = st["router"]["budget"]
            print(f"\n[Status da sessão]")
            print(f"  ID: {st['session_id'][:8]}...")
            print(f"  Mensagens: {st['messages']}")
            print(f"  Custo da sessão: US$ {st['session_cost_usd']:.5f}")
            print(f"  Orçamento diário: US$ {budget['daily_cost_usd']:.5f} / US$ {budget['daily_budget_usd']:.2f}")
            print(f"  Restante: US$ {budget['remaining_usd']:.5f}")
            print(f"  Modelos disponíveis: {list(st['router']['models_available'].keys())}")
            print(f"  Projetos ativos: {st.get('active_projects', 0)}")
            print(f"  Missões ativas: {st.get('active_missions', 0)}")
            print(f"  Casos em aberto: {st.get('open_cases', 0)}\n")
            continue

        if user_input == "/memoria":
            ep = orc._episodic.recent(5)
            if not ep:
                print("WIND: Memória episódica vazia.\n")
            else:
                print("\n[Últimas interações na memória]")
                for item in ep:
                    print(f"  [{item['id'][:8]}] {item['title'][:60]}")
                print()
            continue

        if user_input == "/projetos":
            projects = orc.projects.list_active()
            if not projects:
                print("WIND: Nenhum projeto ativo. Use '/projeto NomeDoProjeto' para criar.\n")
            else:
                print("\n[Projetos ativos]")
                for p in projects:
                    next_a = f" → {p.next_action[:50]}" if p.next_action else ""
                    print(f"  [{p.id[:8]}] {p.name}{next_a}")
                print()
            continue

        if user_input.startswith("/projeto "):
            name = user_input[9:].strip()
            if not name:
                print("WIND: Informe o nome do projeto. Ex: /projeto CARTECH\n")
                continue
            existing = orc.projects.find(name)
            if existing:
                print(f"\n[Projeto encontrado]\n{existing.summary()}\n")
            else:
                p = orc.projects.create(name)
                print(f"\nWIND: Projeto '{p.name}' criado (ID {p.id[:8]}).\n")
            continue

        if user_input == "/missoes":
            missions = orc.missions._queue.list_active()
            if not missions:
                print("WIND: Nenhuma missão ativa.\n")
            else:
                print("\n[Missões ativas]")
                for m in missions:
                    print(f"  [{m.id[:8]}] {m.title} [{m.status.value}] {m.progress}")
                print()
            continue

        if user_input.startswith("/continuar "):
            query = user_input[11:].strip()
            project = orc.projects.find(query)
            if not project:
                print(f"WIND: Projeto '{query}' não encontrado. Use /projetos para listar.\n")
                continue
            ctx = orc.projects.continuation_context(project)
            print(f"\n[Retomando: {project.name}]\n{ctx}\n")
            # Injeta intenção de retomada na conversa
            response = orc.process(f"Continue o projeto '{project.name}'. {ctx}")
            print(f"\nWIND: {response}\n")
            continue

        if user_input == "/casos":
            open_cases = orc.cases.list_open()
            if not open_cases:
                print("WIND: Nenhum caso em aberto. Use '/caso' para abrir um novo.\n")
            else:
                print("\n[Casos em aberto]")
                for c in open_cases:
                    dtc_str = f" DTCs:{','.join(c.dtcs)}" if c.dtcs else ""
                    print(f"  [{c.id[:8]}] {c.vehicle.marca} {c.vehicle.modelo} — {c.queixa[:50]}{dtc_str}")
                print()
            continue

        if user_input == "/caso":
            print("\n[Novo caso de serviço]")
            queixa = input("  Queixa/sintoma: ").strip()
            if not queixa:
                print("WIND: Queixa não pode ser vazia.\n")
                continue

            marca  = input("  Marca do veículo (Enter para pular): ").strip()
            modelo = input("  Modelo (Enter para pular): ").strip()
            ano_s  = input("  Ano (Enter para pular): ").strip()
            motor  = input("  Motor (Enter para pular): ").strip()
            placa  = input("  Placa (Enter para pular): ").strip()

            ecu_ref = input("  Referência da ECU (Enter para pular): ").strip()
            dtcs_s  = input("  DTCs separados por vírgula (Enter para pular): ").strip()

            from src.cases.case import VehicleInfo, EcuInfo
            vehicle = VehicleInfo(
                marca=marca, modelo=modelo,
                ano=int(ano_s) if ano_s.isdigit() else 0,
                motor=motor, placa=placa,
            )
            ecu  = EcuInfo(referencia=ecu_ref)
            dtcs = [d.strip() for d in dtcs_s.split(",") if d.strip()] if dtcs_s else []

            # Buscar casos similares antes de abrir
            similar = orc.cases.find_similar(queixa, vehicle, ecu)
            if similar:
                print(f"\n  WIND: encontrei {len(similar)} caso(s) similar(es):")
                for s in similar:
                    print(f"    [{s.id[:8]}] {s.vehicle.marca} {s.vehicle.modelo} — {s.queixa[:50]}")
                    if s.lessons:
                        print(f"    → Lições: {'; '.join(s.lessons[:2])}")
                print()

            case = orc.cases.open(queixa, vehicle, ecu, dtcs, session_id=orc.session_id)
            print(f"\nWIND: Caso [{case.id[:8]}] aberto.\n")
            continue

        if user_input.startswith("/fechar-caso "):
            case_id_prefix = user_input[13:].strip()
            # Busca por prefixo de ID
            open_cases = orc.cases.list_open()
            target = next((c for c in open_cases if c.id.startswith(case_id_prefix)), None)
            if not target:
                print(f"WIND: Caso '{case_id_prefix}' não encontrado nos casos abertos.\n")
                continue

            print(f"\n[Fechando caso {target.id[:8]}]")
            from src.cases.manager import CLOSING_QUESTIONS
            from src.cases.case import CaseResult
            answers = []
            for q in CLOSING_QUESTIONS:
                ans = input(f"  {q}: ").strip()
                answers.append(ans)

            resultado_s = input("  Resultado (success/partial/fail) [success]: ").strip() or "success"
            try:
                resultado = CaseResult(resultado_s)
            except ValueError:
                resultado = CaseResult.SUCCESS

            tempo_s = input("  Tempo gasto em minutos [0]: ").strip()
            custo_s = input("  Custo do serviço em R$ [0]: ").strip()

            orc.cases.close(
                target.id,
                result=resultado,
                what_worked=answers[0],
                what_surprised=answers[1],
                repeat_next_time=answers[2],
                time_minutes=int(tempo_s) if tempo_s.isdigit() else 0,
                cost_brl=float(custo_s.replace(",", ".")) if custo_s else 0.0,
            )
            print(f"\nWIND: Caso [{target.id[:8]}] fechado. Lições registradas.\n")
            continue

        if user_input == "/re-matriz":
            from src.rev_eng.arch_matrix import matrix_report, GHIDRA_PATH
            print(f"\n{matrix_report(GHIDRA_PATH)}\n")
            continue

        if user_input == "/cal-familias":
            families = orc.calibration.families()
            print(f"\n[Famílias de ECU conhecidas — {len(families)}]")
            for f in families:
                print(f"  [{f.id}] {f.summary_line()}")
            print()
            continue

        if user_input == "/cal-mapas":
            maps = orc.calibration.all_maps()
            from src.calibration.map_taxonomy import MapCategory
            print(f"\n[Taxonomia de mapas — {len(maps)} mapas]")
            current_cat = None
            for m in maps:
                if m.category != current_cat:
                    current_cat = m.category
                    print(f"\n  [{m.category.value.upper()}]")
                print(f"    {m.summary_line()}")
            print()
            continue

        if user_input == "/cal-propostas":
            pending = orc.calibration.list_pending()
            if not pending:
                print("WIND: Nenhuma proposta pendente.\n")
            else:
                print(f"\n[Propostas pendentes — {len(pending)}]")
                for p in pending:
                    legal = " ⚠️ LEGAL" if p.requires_legal_note else ""
                    print(f"  [{p.id[:8]}] {p.ecu_family_id} {p.vehicle_description} — "
                          f"Guardian {p.guardian_level}{legal}")
                print()
            continue

        if user_input == "/fw-protocolos":
            from src.firmware.protocols import list_protocols
            protos = list_protocols()
            print(f"\n[Protocolos automotivos — {len(protos)}]")
            for p in protos:
                bauds = "/".join(str(b) for b in p.typical_baud)
                print(f"  {p.name:10s} {p.standard:20s} {p.description[:55]}")
                print(f"             baud: {bauds} bps  serviços: {len(p.services)}")
            print()
            continue

        if user_input == "/fw-bootloaders":
            from src.firmware.bootloader import list_profiles
            profiles = list_profiles()
            print(f"\n[Perfis de bootloader — {len(profiles)}]")
            for p in profiles:
                bench = " (bancada)" if p.requires_bench else ""
                print(f"  [{p.id}]{bench}")
                print(f"    {p.summary()}")
                print(f"    Apagar: {p.typical_erase_time_s:.0f}s  Gravar: {p.typical_flash_time_s:.0f}s")
            print()
            continue

        if user_input == "/resumo":
            from src.routines.morning import MorningSummary
            summary = MorningSummary(orc).generate()
            print(f"\n{summary}\n")
            continue

        if user_input.startswith("/notificar "):
            text = user_input[11:].strip()
            if not text:
                print("WIND: Informe o texto da notificação.\n")
                continue
            results = orc.notifications.info("WIND", text)
            channels_ok = [ch for ch, ok in results.items() if ok]
            print(f"WIND: Notificação enviada via: {', '.join(channels_ok) if channels_ok else 'nenhum canal'}\n")
            continue

        if user_input.startswith("/falar "):
            text = user_input[7:].strip()
            if not text:
                print("WIND: Informe o texto para falar.\n")
                continue
            ok = orc.tts.speak(text)
            if not ok:
                print(f"WIND: TTS ({orc.tts.name()}) falhou.\n")
            continue

        if user_input == "/api-start":
            import os as _os
            api_key = _os.getenv("WIND_API_KEY", "")
            if not api_key:
                print("WIND: ⚠️  WIND_API_KEY não configurada.\n"
                      "  Configure: setx WIND_API_KEY <chave-secreta>\n")
                continue
            port = orc.start_api(port=8765, api_key=api_key)
            print(f"WIND: Servidor HTTP iniciado em {orc.api_status()['url']}\n")
            continue

        if user_input == "/api-status":
            api = orc.api_status()
            if api["running"]:
                print(f"WIND: API rodando em {api['url']}\n")
            else:
                print("WIND: API parada. Use /api-start para iniciar.\n")
            continue

        if user_input == "/financas-contas":
            print(f"\n{orc.finance.accounts_summary()}\n")
            continue

        if user_input == "/financas-resumo":
            print(f"\n{orc.finance.monthly_summary()}\n")
            continue

        if user_input == "/financas-anual":
            print(f"\n{orc.finance.yearly_summary()}\n")
            continue

        if user_input == "/financas-alertas":
            alerts = orc.finance.spending_alerts()
            if not alerts:
                print("WIND: Nenhum alerta financeiro detectado.\n")
            else:
                print(f"\n[Alertas financeiros — {len(alerts)}]")
                for a in alerts:
                    print(f"  {a}")
                print()
            continue

        if user_input.startswith("/financas-importar "):
            path_str = user_input[19:].strip()
            if not path_str:
                print("WIND: Informe o caminho do arquivo. Ex: /financas-importar D:\\extrato.ofx\n")
                continue
            print(f"WIND: Importando {path_str}...")
            result = orc.finance.import_statement(path_str)
            if result["ok"]:
                print(f"  Formato: {result['format']}")
                print(f"  Total: {result['total_transactions']} transações")
                print(f"  Importadas: {result['imported']} | Duplicatas ignoradas: {result['skipped']}")
                if result["errors"]:
                    print(f"  Avisos: {'; '.join(result['errors'][:3])}")
            else:
                print(f"  Erro: {'; '.join(result['errors'])}")
            print()
            continue

        if user_input.startswith("/re-analisar "):
            path_str = user_input[13:].strip()
            if not path_str:
                print("WIND: Informe o caminho do arquivo. Ex: /re-analisar D:\\fw.bin\n")
                continue
            from pathlib import Path as _Path
            arch_str = input("  Arquitetura (tricore/powerpc/superh/v850/arm/auto) [auto]: ").strip().lower() or "auto"
            from src.rev_eng.pipeline import IdentifiedArch as _IA
            force_arch = None
            arch_map = {
                "tricore": _IA.TRICORE, "powerpc": _IA.POWERPC,
                "superh": _IA.SUPERH, "v850": _IA.V850,
                "arm": _IA.ARM, "aarch64": _IA.AARCH64, "m16c": _IA.M16C,
            }
            if arch_str != "auto":
                force_arch = arch_map.get(arch_str)
                if not force_arch:
                    print(f"WIND: Arquitetura '{arch_str}' desconhecida. Use auto ou uma das opções.\n")
                    continue
            run_ghidra_s = input("  Executar análise Ghidra headless? (s/N) [N]: ").strip().lower()
            run_ghidra = run_ghidra_s in ("s", "sim", "y", "yes")
            print(f"\nWIND: Iniciando pipeline RE para {_Path(path_str).name}...")
            report = orc.re_pipeline.run(path_str, force_arch=force_arch, run_ghidra=run_ghidra)
            print(f"\n{report.summary()}\n")
            continue

        # ── Fase 9: Instalador / Manutenção ───────────────────────────────
        if user_input == "/saude":
            from src.installer.health_check import HealthChecker
            checker = HealthChecker(".")
            report  = checker.run()
            print(f"\n{report.summary()}\n")
            continue

        if user_input == "/backup":
            from src.installer.backup import BackupManager
            mgr  = BackupManager(".")
            info = mgr.create()
            print(f"WIND: Backup criado → {info.path.name}  ({info.size_bytes/1024:.0f} KB)\n")
            continue

        if user_input == "/backups":
            from src.installer.backup import BackupManager
            mgr     = BackupManager(".")
            backups = mgr.list()
            if not backups:
                print("WIND: Nenhum backup encontrado. Use /backup para criar.\n")
            else:
                print(f"\n[Backups disponíveis — {len(backups)}]")
                for i, b in enumerate(backups):
                    print(f"  [{i}] {b.label()}")
                print()
            continue

        if user_input.startswith("/restaurar "):
            ref = user_input[11:].strip()
            from src.installer.backup import BackupManager
            from pathlib import Path as _Path
            mgr     = BackupManager(".")
            backups = mgr.list()
            # Aceita índice numérico ou nome de arquivo
            target = None
            if ref.isdigit():
                idx = int(ref)
                if 0 <= idx < len(backups):
                    target = backups[idx].path
            else:
                match = next((b for b in backups if ref in b.path.name), None)
                if match:
                    target = match.path
                elif _Path(ref).exists():
                    target = _Path(ref)
            if not target:
                print(f"WIND: Backup '{ref}' não encontrado. Use /backups para listar.\n")
                continue
            confirm = input(f"  Restaurar {target.name}? Estado atual será salvo. (s/N): ").strip().lower()
            if confirm not in ("s", "sim", "y", "yes"):
                print("WIND: Restauração cancelada.\n")
                continue
            restored = mgr.restore(target)
            print(f"WIND: Restaurado — {len(restored)} arquivo(s): {', '.join(restored)}\n")
            continue

        if user_input == "/migrar":
            from src.installer.updater import Migrator
            m      = Migrator("data/wind.db")
            status = m.status()
            if status["up_to_date"]:
                print(f"WIND: Banco já está na versão {status['current_version']} — sem migrações pendentes.\n")
            else:
                applied = m.migrate()
                print(f"WIND: Migrações aplicadas: {applied} → versão {m.current_version()}\n")
            continue

        # ── Fase 8: Autonomia ─────────────────────────────────────────────
        if user_input == "/autonomia":
            eng  = orc.decision_engine
            prof = eng.profile
            level = prof.current_level
            print(f"\n[Autonomia WIND]")
            print(f"  Nível atual: {level.label()}")
            history = prof.history[-5:] if prof.history else []
            if history:
                print("  Histórico recente:")
                for h in history:
                    import time as _t
                    from datetime import datetime as _dt
                    ts  = _dt.fromtimestamp(float(h.get("timestamp", 0))).strftime("%d/%m %H:%M")
                    frm = h.get("from_level", "?")
                    to  = h.get("to_level", "?")
                    why = h.get("reason", "")[:60]
                    who = h.get("approved_by", "")
                    print(f"    {ts}  {frm}→{to}  [{who}] {why}")
            print()
            continue

        if user_input == "/decisoes":
            pending = orc.decision_engine._store.list_pending()
            if not pending:
                print("WIND: Nenhuma decisão pendente.\n")
            else:
                print(f"\n[Decisões pendentes — {len(pending)}]")
                for r in pending:
                    print(f"  {r.summary()}")
                print()
            continue

        if user_input.startswith("/aprovar "):
            prefix = user_input[9:].strip()
            pending = orc.decision_engine._store.list_pending()
            target  = next((r for r in pending if r.id.startswith(prefix)), None)
            if not target:
                print(f"WIND: Decisão '{prefix}' não encontrada entre as pendentes.\n")
                continue
            approved = orc.decision_engine.approve(target.id, approved_by="Felipe")
            if approved:
                print(f"WIND: Decisão [{approved.id[:8]}] aprovada.\n")
            continue

        if user_input == "/notas":
            proposed = orc.note_manager.list_proposed(limit=20)
            if not proposed:
                print("WIND: Nenhuma nota pendente de validação.\n")
            else:
                print(f"\n[Notas propostas — {len(proposed)}]")
                for n in proposed:
                    print(f"  {n.summary_line()}")
                    print(f"    {n.content[:80]}")
                print()
            continue

        if user_input.startswith("/validar-nota "):
            note_id = user_input[14:].strip()
            note = orc.note_manager.validate(note_id, validated_by="Felipe")
            if note:
                print(f"WIND: Nota [{note.id[:8]}] validada. '{note.topic[:50]}'\n")
            else:
                print(f"WIND: Nota '{note_id}' não encontrada.\n")
            continue

        if user_input == "/curriculo":
            print(f"\n{orc.curriculum.summary()}\n")
            continue

        if user_input.startswith("/estudar "):
            item_id = user_input[9:].strip()
            item = orc.curriculum.mark_in_progress(item_id)
            if item:
                print(f"WIND: '{item.topic}' marcado como em andamento.\n")
            else:
                print(f"WIND: Tópico '{item_id}' não encontrado. Use /curriculo para listar.\n")
            continue

        if user_input == "/retrospectiva":
            from src.learning.retrospective import RetrospectiveGenerator
            retro = RetrospectiveGenerator(
                db_path="data/wind.db",
                autonomy_engine=orc.decision_engine,
                note_manager=orc.note_manager,
                curriculum=orc.curriculum,
            )
            print(f"\n{retro.generate()}\n")
            continue

        # ── Fase 11: Voz e Autonomia ──────────────────────────────────────
        if user_input == "/voz":
            va = _get_voice_agent()
            if va.running:
                va.stop()
                print("WIND: Voz desativada.\n")
            else:
                if va.start():
                    print("WIND: Voz ativa. Diga 'WIND' para ativar o microfone.\n")
                else:
                    print(f"WIND: Voz indisponível.\n{va.install_hint()}\n")
            continue

        if user_input.startswith("/desktop "):
            parts = user_input[9:].strip().split(None, 1)
            if not parts:
                print("WIND: Use: /desktop <comando> [param=valor ...]\n")
                continue
            cmd = parts[0]
            kwargs: dict = {}
            if len(parts) > 1:
                for token in parts[1].split():
                    if "=" in token:
                        k, v = token.split("=", 1)
                        kwargs[k] = v
                    else:
                        # positional arg → passa como primeiro parâmetro relevante
                        for key in ("app", "query", "url", "text", "title", "path", "message", "cmd"):
                            if key not in kwargs:
                                kwargs[key] = token
                                break
            result = desktop.execute(cmd, **kwargs)
            if result.get("ok"):
                out = result.get("result") or result.get("output") or result.get("content") or "OK"
                print(f"WIND: {str(out)[:500]}\n")
            else:
                print(f"WIND: Erro — {result.get('error', '?')}\n")
            continue

        if user_input.startswith("/git-status"):
            path = user_input[12:].strip() or "."
            result = desktop.execute("git_status", path=path)
            print(f"\n{result.get('output', result.get('error', ''))}\n")
            continue

        if user_input.startswith("/git-commit "):
            msg = user_input[12:].strip()
            if not msg:
                print("WIND: Informe a mensagem de commit.\n")
                continue
            result = desktop.execute("git_commit", message=msg, path=".")
            if result.get("ok"):
                print(f"WIND: {result.get('output', 'Commit realizado.')}\n")
            else:
                print(f"WIND: Erro — {result.get('error')}\n")
            continue

        if user_input == "/git-diff":
            result = desktop.execute("git_diff", path=".")
            diff = result.get("output", "")
            print(f"\n{diff[:3000] if diff else '(sem alterações)'}\n")
            continue

        if user_input.startswith("/ls"):
            path = user_input[3:].strip() or "."
            result = desktop.execute("list_files", path=path)
            if result.get("ok"):
                print(f"\n[{path}]  ({result.get('count', 0)} itens)\n{result.get('output', '')}\n")
            else:
                print(f"WIND: {result.get('error')}\n")
            continue

        if user_input.startswith("/ler "):
            path = user_input[5:].strip()
            if not path:
                print("WIND: Informe o caminho do arquivo.\n")
                continue
            result = desktop.execute("read_file", path=path)
            if result.get("ok"):
                trunc = " [truncado]" if result.get("truncated") else ""
                print(f"\n[{path}]{trunc}\n{result['content']}\n")
            else:
                print(f"WIND: {result.get('error')}\n")
            continue

        if user_input == "/screenshot":
            result = desktop.execute("take_screenshot")
            if result.get("ok"):
                print(f"WIND: Screenshot salvo em {result['path']}  ({result.get('size')})\n")
            else:
                print(f"WIND: {result.get('error')}\n")
            continue

        if user_input == "/clipboard":
            result = desktop.execute("read_clipboard")
            if result.get("ok"):
                content = result.get("content", "")
                print(f"\n[Clipboard — {len(content)} chars]\n{content[:1000]}\n")
            else:
                print(f"WIND: {result.get('error')}\n")
            continue

        if user_input == "/pc-status":
            result = desktop.execute("get_status")
            if result.get("ok"):
                st = result["status"]
                print(f"\n[Status do PC]")
                for k, v in st.items():
                    print(f"  {k:20s}: {v}")
                print()
            else:
                print(f"WIND: {result.get('error')}\n")
            continue

        # Processar mensagem normal
        response = orc.process(user_input)
        print(f"\nWIND: {response}\n")


if __name__ == "__main__":
    main()
