# WIND_IMPLEMENTATION_STATUS.md
> Atualizado a cada fim de fase. Nunca inventar percentuais. Integração física não testada nunca é declarada funcional.

Estados válidos: `não-implementado` · `em-desenvolvimento` · `implementado-sem-teste` · `testado-dev` · `aguardando-validação-PC` · `validado-PC` · `aprovado-produção`

---

## Fase 0 — Estudo, decisões e base
**Estado geral:** ✅ Concluída — 2026-11-23

| Entregável | Estado |
|---|---|
| docs/WIND_MASTER_SPEC.md | ✅ criado |
| docs/WIND_ADOPTION_MATRIX.md | ✅ criado |
| docs/WIND_DECISIONS.md | ✅ criado |
| docs/WIND_ARCHITECTURE.md | ✅ criado |
| docs/WIND_DATA_CLASSIFICATION.md | ✅ criado |
| docs/WIND_EVALUATION_PLAN.md | ✅ criado |
| docs/WIND_IMPLEMENTATION_STATUS.md | ✅ criado (este arquivo) |
| CLAUDE.md | ✅ criado |
| AGENTS.md | ✅ criado |
| Verificação de processadores Ghidra | ✅ feito |
| Pesquisa de tecnologias (8 itens) | ✅ feito |

**Contexto descoberto automaticamente (2026-11-23):**
- Acervo ORI×MOD: `D:\Ori+Mod.ecu` (19 marcas + Damos pack 2020 9,6 GB) ✅
- Claude: plano Pro/Max (assinatura) ✅
- Codex: OpenAI API key (pago por uso) ✅
- Python 3.12, JDK 25, Ghidra 12.1.4: instalados ✅
- Node.js, Git, anthropic/openai Python: **não instalados** — Fase 1
- Ver docs/WIND_CONTEXT.md para detalhes completos

**Itens ainda bloqueados (aguardando Felipe):**
- Projetos (BoxControl, REPROTECH Native, GMap): não localizados no PC — podem estar na VPS
- Contas e serviços da empresa (Instagram, WhatsApp Business, e-mail, agenda)
- Conjunto de teste de português (50 perguntas) — a criar na Fase 1

**Contexto completo (nenhum [AGUARDANDO] crítico para Fase 1):**
- VPS: Hostinger Campinas, Ubuntu 24.04, root@187.41.126.171 ✅
- iPhone: iPhone 11, iOS 27 ✅

---

## Fase 1 — Inteligência e memória
**Estado:** `testado-dev` — 2026-11-23

| Módulo | Arquivo | Estado |
|---|---|---|
| Identidade e persona | src/core/identity.py | ✅ implementado |
| Sessão | src/core/session.py | ✅ implementado |
| Gerenciador de contexto/orçamento | src/core/context.py | ✅ implementado |
| Orquestrador | src/core/orchestrator.py | ✅ implementado |
| Especificações de modelos | src/router/models.py | ✅ implementado |
| Router com fallback e custo | src/router/router.py | ✅ implementado |
| Cliente Claude (anthropic SDK) | src/router/claude_client.py | ✅ implementado |
| Cliente OpenAI/Codex | src/router/openai_client.py | ✅ implementado |
| Stub modelo local | src/router/local_client.py | ✅ stub — Fase 4 |
| MemoryStore (SQLite + FTS5) | src/memory/store.py | ✅ implementado |
| Memória de sessão | src/memory/session_mem.py | ✅ implementado |
| Memória episódica | src/memory/episodic.py | ✅ implementado |
| Memória semântica | src/memory/semantic.py | ✅ implementado |
| Classificador de dados Guardian | src/guardian/classifier.py | ✅ implementado |
| Validador pré-chamada | src/guardian/validator.py | ✅ implementado |
| Audit log (JSONL append-only) | src/guardian/audit.py | ✅ implementado |
| CLI entrypoint | src/wind.py | ✅ implementado |
| Testes unitários (36 testes) | tests/unit/ | ✅ 36/36 passando |
| Framework avaliação PT-BR | tests/eval/portuguese_eval.py | ✅ framework pronto |
| Framework avaliação decisões | tests/eval/decision_eval.py | ✅ framework pronto |

**Validado ao vivo (2026-11-23):**
- ANTHROPIC_API_KEY configurada via setx ✅
- WIND responde em PT-BR com identidade correta ✅
- Roteamento para Haiku + custo rastreado (US$ 0,00028 / chamada) ✅
- 36/36 testes unitários passando ✅
- Bug FTS5 corrigido (sanitizador de query) ✅

**Pendências restantes:**
- [ ] Revogar e regenerar ANTHROPIC_API_KEY (chave exposta no chat)
- [ ] OPENAI_API_KEY configurada → testar fallback Codex
- [ ] Felipe criar 50 perguntas PT-BR (tests/eval/ptbr_questions.json) → rodar baseline
- [ ] Felipe criar 30 cenários de decisão (tests/eval/decision_scenarios.json) → rodar baseline
- [ ] Git instalado → fazer commit inicial da Fase 1
- [ ] Instalar Ollama + modelo local → habilitar local_client.py
- [ ] Ajustar heurística de nomes próprios no Guardian (falso positivo em "Felipe")

---

## Fase 2 — Missões e desenvolvimento
**Estado:** `testado-dev` — 2026-11-23

| Módulo | Arquivo | Estado |
|---|---|---|
| Dataclasses de missão | src/missions/mission.py | ✅ implementado |
| Fila persistida (SQLite) | src/missions/queue.py | ✅ implementado |
| Motor de execução | src/missions/engine.py | ✅ implementado |
| ProjectCard | src/projects/project.py | ✅ implementado |
| ProjectStore (SQLite) | src/projects/store.py | ✅ implementado |
| ProjectManager + fuzzy match | src/projects/manager.py | ✅ implementado |
| Adaptador Claude Code | src/adapters/claude_code.py | ✅ implementado |
| Adaptador Codex (o4-mini) | src/adapters/codex_adapter.py | ✅ implementado |
| Orquestrador atualizado | src/core/orchestrator.py | ✅ atualizado |
| CLI com /projetos /missoes /continuar | src/wind.py | ✅ atualizado |
| Testes unitários missões (20 testes) | tests/unit/test_missions.py | ✅ 20/20 passando |
| Testes unitários projetos (17 testes) | tests/unit/test_projects.py | ✅ 17/17 passando |

**Validado (2026-11-23):**
- 73/73 testes unitários passando (Fase 1 + Fase 2) ✅
- Motor de missões: checkpoint + retomada funcional ✅
- Fuzzy matching em project.find() ✅
- `/continuar X` injeta contexto do projeto no system prompt ✅

**Marco atingido:** "continue projeto X" funciona entre sessões (projeto salvo em SQLite, contexto injetado automaticamente no orquestrador).

---

## Fase 3 — Aprendizado por serviço
**Estado:** `testado-dev` — 2026-11-23

| Módulo | Arquivo | Estado |
|---|---|---|
| ServiceCase (veículo, ECU, DTCs, lições) | src/cases/case.py | ✅ implementado |
| CaseStore (SQLite + FTS5) | src/cases/store.py | ✅ implementado |
| CaseManager (open/close/similar) | src/cases/manager.py | ✅ implementado |
| Anonimizador LGPD | src/cases/anonymizer.py | ✅ implementado |
| Contrato BoxControl (stub + HTTP) | src/cases/boxcontrol.py | ✅ contrato + stub |
| Orquestrador atualizado | src/core/orchestrator.py | ✅ atualizado |
| CLI com /casos /caso /fechar-caso | src/wind.py | ✅ atualizado |
| Testes unitários (28 testes) | tests/unit/test_cases.py | ✅ 28/28 passando |

**Validado (2026-11-23):**
- 101/101 testes unitários passando (Fases 1+2+3) ✅
- Busca por similaridade via FTS5 (veículo+ECU+sintoma) ✅
- Anonimizador remove placa, VIN, CPF, CNPJ, fone ✅
- Fechamento com 3 perguntas estruturadas ✅
- Contexto de casos similares injetado automaticamente ao mencionar serviço ✅
- BoxControl: contrato definido, stub ativo (integração real pendente)

**Pendências:**
- [ ] Integração real com BoxControl (quando disponível na VPS/local)
- [ ] Síntese de skills procedurais a partir de casos repetidos (Fase 8)

**Marco atingido:** ao abrir um serviço, a WIND recupera automaticamente casos similares por veículo/ECU/sintoma e injeta o que funcionou e o que falhou no contexto. Dados de clientes (placa, VIN) ficam locais e nunca chegam ao modelo remoto.

---

## Fase 4 — Engenharia reversa
**Estado:** `testado-dev` — 2026-11-23

| Módulo | Arquivo | Estado |
|---|---|---|
| Matriz de suporte Ghidra (arq. automotivas) | src/re/arch_matrix.py | ✅ implementado |
| FileGuard (SHA-256 + read-only) | src/re/file_guard.py | ✅ implementado |
| GhidraClient (headless wrapper) | src/re/ghidra_client.py | ✅ implementado |
| Pipeline RE (identificar+importar+analisar) | src/re/pipeline.py | ✅ implementado |
| Interfaces REPROTECH Native (stubs) | src/re/repro_native.py | ✅ contrato + stubs |
| Orquestrador atualizado | src/core/orchestrator.py | ✅ atualizado |
| CLI com /re-matriz /re-analisar | src/wind.py | ✅ atualizado |
| Testes unitários (35 testes) | tests/unit/test_re.py | ✅ 35/35 passando |

**Matriz de suporte verificada na instalação real (Ghidra 12.1.4):**
| Família | Status |
|---|---|
| Infineon TriCore | ✅ SUPORTADO |
| PowerPC/VLE | ⚠️ PARCIAL (18 slaspec, incluindo VLE) |
| SuperH SH2/SH2A | ✅ SUPORTADO |
| NEC V850 | ⚠️ PARCIAL |
| ARM Cortex-M | ✅ SUPORTADO |
| ARM64 (AARCH64) | ✅ SUPORTADO |
| Renesas M16C | ✅ SUPORTADO |
| C166/XC2000 | ❌ AUSENTE (precisa módulo SLEIGH, ~2–4h) |

**analyzeHeadless:** não encontrado na pasta support/ desta instalação. Análise headless marcada como indisponível; módulos de identificação e FileGuard funcionam independentemente.

**Validado (2026-11-23):**
- 136/136 testes unitários passando (Fases 1–4) ✅
- Matriz construída lendo instalação real (nunca presumida) ✅
- FileGuard: hash SHA-256 + sidecar + tamper detection ✅
- Pipeline: detecta S-record, Intel HEX, ELF, PE, BIN raw ✅
- DTC detector stub encontra DTCs ASCII em binário sintético ✅

**Pendências:**
- [ ] analyzeHeadless: verificar se é necessário instalar componente extra do Ghidra
- [ ] Integração real REPROTECH Native quando REPRO_NATIVE_API_URL estiver configurada
- [ ] Módulo SLEIGH para C166/XC2000 (~2–4h, se necessário para o acervo)
- [ ] Avaliação com pares ORI×MOD reais (com aprovação do Felipe)

**Marco atingido:** `/re-matriz` mostra a matriz real da instalação. `/re-analisar fw.bin` executa o pipeline completo: hash + formato + arquitetura heurística + relatório estruturado.

---

## Fase 5 — Calibração e firmware
**Estado:** `testado-dev` — 2026-11-23

| Módulo | Arquivo | Estado |
|---|---|---|
| Base de famílias ECU (9 famílias) | src/calibration/ecu_families.py | ✅ implementado |
| Taxonomia de mapas + Guardian levels | src/calibration/map_taxonomy.py | ✅ implementado |
| CalibrationProposal + fluxo aprovação | src/calibration/proposal.py | ✅ implementado |
| Verificação de checksum | src/calibration/checksum.py | ✅ implementado |
| CalibrationStore (SQLite) | src/calibration/store.py | ✅ implementado |
| CalibrationManager | src/calibration/manager.py | ✅ implementado |
| Especificações de protocolos | src/firmware/protocols.py | ✅ implementado |
| Perfis de bootloader | src/firmware/bootloader.py | ✅ implementado |
| Interfaces hardware (SM2/BDM stubs) | src/firmware/interfaces.py | ✅ contrato + stubs |
| Orquestrador atualizado | src/core/orchestrator.py | ✅ atualizado |
| CLI com 5 novos comandos | src/wind.py | ✅ atualizado |
| Testes calibração (46 testes) | tests/unit/test_calibration.py | ✅ 46/46 passando |
| Testes firmware (28 testes) | tests/unit/test_firmware.py | ✅ 28/28 passando |

**Famílias ECU cobertas:** Bosch ME9/MED17/EDC16/EDC17, Continental SID208/PCR2.1, Delphi MT20U2, Denso SH7xxx, Marelli IAW5NF

**Regras de segurança implementadas:**
- Mapas Emission/Immobilizer/Odometer → Guardian 4 (legal_note obrigatória)
- Mapas Limiters/Diagnostic → Guardian 3
- CalibrationManager.create_proposal() recusa Guardian 4 sem legal_note
- FlashInterfaces: stubs sempre retornam not_available (sem hardware real)
- WIND propõe → Felipe aprova → Felipe grava; gravação NUNCA ocorre automaticamente

**Validado (2026-11-23):**
- 210/210 testes unitários passando (Fases 1–5) ✅
- CalibrationError levantado para mapa de emissão sem nota legal ✅
- Fluxo completo: criar → aprovar → mark_applied ✅
- Checksum: CRC32/SUM8/SUM16 calculados e comparados ✅

**Pendências:**
- [ ] Integração real com SM2 (quando SM2_DEVICE_PORT configurado)
- [ ] Parser A2L/DAMOS real (Fase 4 extended com REPROTECH Native)
- [ ] Fluxo completo de calibração com arquivo real (autorização Felipe)
- [ ] Avaliação com pares ORI×MOD reais (com aprovação do Felipe)

**Marco atingido:** `/cal-familias` lista 9 famílias. `/cal-mapas` mostra taxonomia com Guardian levels. Propostas com mapas de emissão/imobilizador/odômetro são bloqueadas sem nota legal — Guardian enforced em código.

---

## Fase 6 — iPhone, voz e experiência
**Estado:** `testado-dev` — 2026-11-23

| Módulo | Arquivo | Estado |
|---|---|---|
| Canais de notificação | src/notifications/channel.py | ✅ implementado |
| Gerenciador de notificações | src/notifications/manager.py | ✅ implementado |
| Resumo matinal | src/routines/morning.py | ✅ implementado |
| TTS — Console + Windows SAPI | src/voice/tts.py | ✅ implementado |
| STT stub | src/voice/stt.py | ✅ stub — integração futura |
| API HTTP REST | src/api/server.py | ✅ implementado |
| Orquestrador (Fase 6) | src/core/orchestrator.py | ✅ atualizado |
| CLI (Fase 6) | src/wind.py | ✅ atualizado |
| Testes Fase 6 | tests/unit/test_phase6.py | ✅ 33 testes |

**Arquitetura:**
- API HTTP via stdlib `http.server` — sem Flask, sem dependências extras
- Autenticação por header `X-API-Key` com `hmac.compare_digest` (constant-time)
- Servidor em thread daemon — não bloqueia o processo principal
- Porta efêmera (port=0) em testes — evita conflito de porta
- TTS: Windows SAPI via PowerShell subprocess — sem pyttsx3; ConsoleTTS como fallback universal
- Canais: ConsoleChannel (sempre on) + FileChannel (JSONL append) + TelegramStub (opcional)
- MorningSummary: consulta casos, missões, propostas, notificações, interfaces de hardware

**Acesso iOS Shortcuts:**
```
URL:     http://<IP-do-PC>:8765/chat
Method:  POST
Headers: X-API-Key: <WIND_API_KEY>
Body:    {"message": "quais casos estão abertos?"}
```

**Segurança:**
- `WIND_API_KEY` obrigatória via env — servidor retorna 503 se não configurada
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` opcionais — TelegramStub desativado sem elas
- Dados de classe `personal`/`confidential-client` nunca saem do PC pelo canal de notificação

**Marco atingido:** 243/243 testes passando — zero regressões

---

## Fase 7 — Finanças e contas (somente leitura)
**Estado:** `testado-dev` — 2026-11-23

| Módulo | Arquivo | Estado |
|---|---|---|
| Modelos de dados financeiros | src/finance/account.py | ✅ implementado |
| Parser de extratos OFX + CSV | src/finance/statement_parser.py | ✅ implementado |
| Armazenamento SQLite | src/finance/store.py | ✅ implementado |
| Analisador (somente leitura) | src/finance/analyzer.py | ✅ implementado |
| Orquestrador (Fase 7) | src/core/orchestrator.py | ✅ atualizado |
| CLI (Fase 7) | src/wind.py | ✅ atualizado |
| Testes Fase 7 | tests/unit/test_finance.py | ✅ 39 testes |

**Arquitetura:**
- Dados de classe `FINANCEIRO`: ficam em SQLite local — nunca ao modelo remoto
- `FinanceAnalyzer.context_for_orchestrator()` retorna apenas texto agregado (totais/categorias) — seguro para injetar no prompt
- Parser OFX (SGML e XML) + CSV genérico com detecção automática de formato
- Categorização de transações por palavras-chave + regex de palavra inteira para evitar falsos positivos
- Formato decimal auto-detectado: brasileiro (1.234,56) vs padrão (1234.56)

**Novos comandos CLI:**
```
/financas-contas           lista contas com saldo consolidado
/financas-resumo           resumo do mês atual por categoria
/financas-anual            resumo anual
/financas-alertas          alertas de variação de gastos vs mês anterior
/financas-importar <arq>   importa extrato OFX ou CSV
```

**Segurança:**
- Fase 7 = somente leitura — nenhuma operação de escrita financeira implementada
- Operações de escrita (pagamentos, transferências) exigem A4 — não implementadas nesta fase
- Chaves de corretoras não aceitas (nenhum campo para isso)
- Dados financeiros nunca aparecem em log nem em prompts de modelo

**Marco atingido:** 282/282 testes passando — zero regressões

---

## Fase 8 — Autonomia graduada e estudo contínuo
**Estado:** `testado-dev` — 2026-11-23

| Módulo | Arquivo | Estado |
|---|---|---|
| Níveis A0–A4 + AutonomyProfile | src/autonomy/level.py | ✅ implementado |
| DecisionRecord + DecisionStore | src/autonomy/decision.py | ✅ implementado |
| DecisionEngine (envelope, approve, audit) | src/autonomy/engine.py | ✅ implementado |
| LearningNote + NoteStore + NoteManager | src/learning/notes.py | ✅ implementado |
| Curriculum (10 tópicos padrão, JSON) | src/learning/curriculum.py | ✅ implementado |
| RetrospectiveGenerator | src/learning/retrospective.py | ✅ implementado |
| Orquestrador (Fase 8) | src/core/orchestrator.py | ✅ atualizado |
| CLI (Fase 8) | src/wind.py | ✅ atualizado |
| Testes autonomia (38 testes) | tests/unit/test_autonomy.py | ✅ 38/38 passando |
| Testes aprendizado (35 testes) | tests/unit/test_learning.py | ✅ 35/35 passando |

**Arquitetura — Autonomia:**
- Cinco níveis A0–A4 com envelope progressivo (risco máximo, confiança mínima, reversibilidade)
- A0: somente responde | A1: lê e pesquisa | A2: escrita reversível em isolado | A3: projetos autorizados | A4: externo com aprovação por operação
- `DecisionEngine.evaluate()` → APPROVED se dentro do envelope, PENDING se fora (aguarda Felipe)
- Regras invariantes codificadas: WIND nunca auto-eleva; A4 sempre PENDING; erro grave → auto-demote A1
- Histórico completo em `autonomy_profile.json` + tabela `decisions` (SQLite)

**Arquitetura — Aprendizado contínuo:**
- Toda nota nasce como PROPOSED — nunca auto-validada pela WIND
- Fluxo: PROPOSED → VALIDATED (Felipe valida) → OBSOLETE (superada)
- NoteManager.context_for_topic() injeta apenas notas VALIDATED no prompt do modelo
- Curriculum padrão: 10 tópicos (Bosch ME9/MED17/EDC17, Ghidra TriCore/SuperH, UDS, ISO-TP, A2L, Guardian, LLMs)
- RetrospectiveGenerator combina: nível de autonomia, decisões, notas e currículo em texto de 7 dias

**Novos comandos CLI:**
```
/autonomia        nível atual + histórico de alterações
/decisoes         decisões pendentes de aprovação do Felipe
/aprovar X        aprova decisão com prefixo de ID X
/notas            notas propostas aguardando validação
/validar-nota X   valida nota X (marcando como VALIDATED)
/curriculo        currículo de estudo (tópicos pendentes / concluídos)
/estudar X        marca tópico X como em andamento
/retrospectiva    retrospectiva dos últimos 7 dias
```

**Segurança / invariantes Guardian:**
- Dados financeiros continuam nunca chegando ao modelo (herdado Fase 7)
- Notas nunca auto-validadas — sempre exigem Felipe
- Nível de autonomia nunca auto-elevado — somente demote automático
- A4 sempre exige aprovação por operação, independente de risco/confiança

**Marco atingido:** 355/355 testes passando — zero regressões

---

## Fase 9 — Instalador, atualização, rollback e RC
**Estado:** `testado-dev` — 2026-11-23

| Módulo | Arquivo | Estado |
|---|---|---|
| Backup ZIP com rotação automática | src/installer/backup.py | ✅ implementado |
| Migrador de esquema SQLite | src/installer/updater.py | ✅ implementado |
| Health check / checklist RC | src/installer/health_check.py | ✅ implementado |
| Script de instalação interativo | install.py | ✅ implementado |
| .gitignore (protege data/, .env.wind) | .gitignore | ✅ criado |
| CLI (Fase 9) | src/wind.py | ✅ atualizado |
| Testes Fase 9 (33 testes) | tests/unit/test_installer.py | ✅ 33/33 passando |

**Arquitetura:**
- `install.py` (raiz): setup interativo — verifica Python, cria dirs, aplica migrações, gera WIND_API_KEY aleatória, exibe health check
- `BackupManager`: cria ZIP com data/wind.db + autonomy_profile.json + curriculum.json + .env.wind; rotação automática (20 backups máx); pre-backup automático antes de restaurar
- `Migrator`: versionamento de esquema SQLite; aplica migrações pendentes em ordem; idempotente
- `HealthChecker`: 12 verificações (Python, stdlib, dirs, DB, schema, chaves API, secrets, testes, docs, backups)
- Separação WIND_API_KEY: nunca hardcoded — gerada aleatoriamente, escrita em .env.wind, configurada via `setx`

**Resultado do health check real (2026-11-23):**
```
RC APROVADO ✅  —  9 ok / 0 falhas / 3 avisos
  ✅ Python >= 3.10 — 3.12.8
  ✅ Módulos stdlib obrigatórios — todos presentes
  ✅ Banco data/wind.db — presente (24 tabelas)
  ✅ Sem secrets hardcoded em src/
  ✅ Testes unitários — 388 testes coletados (≥300 ✅)
  ✅ Documentação obrigatória — toda presente
  ⚠️ ANTHROPIC_API_KEY — requer configuração via setx
  ⚠️ OPENAI_API_KEY — opcional (fallback)
  ⚠️ WIND_API_KEY — gerada em .env.wind, configurar via setx
```

**Novos comandos CLI:**
```
/saude        health check / checklist RC
/backup       cria backup ZIP do estado atual
/backups      lista backups disponíveis
/restaurar X  restaura backup X (nome ou índice da lista)
/migrar       aplica migrações de banco pendentes
```

**Marco atingido:** 388/388 testes passando — zero regressões  
**WIND 2.0 completa em todas as 9 fases.**

---

## Bugs corrigidos pós-integração (2026-11-23)

| Bug | Arquivo corrigido | Fix |
|---|---|---|
| `src/re/` shadow stdlib `re` | `src/re/` → `src/rev_eng/` + todos os imports | Renomear pacote |
| Migração 1: `missions` schema errado | `src/installer/updater.py` m001 + m003 | ALTER TABLE ADD COLUMN |
| Migração 1: `fin_accounts`/`fin_transactions` schema errado | `src/installer/updater.py` m001 + m004 | DROP + RECREATE |
| Migração 1: `service_cases` schema errado (`opened_at` em vez de `created_at`) | `src/installer/updater.py` m001 + m005 | DROP + RECREATE |
| `'ThinkingBlock' object has no attribute 'text'` | `src/router/claude_client.py` | Filtrar `hasattr(b, "text")` |
| Guardian falso positivo para "Claude Code" no system prompt | `src/guardian/validator.py` | PERSONAL só verificado em `messages` do usuário, não no system prompt |

**Teste E2E validado (2026-11-23):**
```
WIND responde: identidade correta, nível A1, custo rastreado (US$ 0,00062)
391/391 testes unitários passando (3 novos: Guardian fix + schema service_cases)
Sem [GUARDIAN AVISO] espúrio no stderr
```

**Commit inicial:** `34fbf25` — 114 arquivos, 14260 inserções  
Branch: `main` — `git` via GitKraken 2.56.1

---

## Fase 10 — App iPhone com voz + controle remoto do PC
**Estado:** `testado-dev` — 2026-11-23

| Módulo | Arquivo | Estado |
|---|---|---|
| Desktop Agent (Windows) | src/desktop/agent.py | ✅ implementado |
| Wake-on-LAN | src/desktop/wol.py | ✅ implementado |
| Package init desktop | src/desktop/__init__.py | ✅ |
| API: rota /desktop | src/api/server.py | ✅ estendido |
| API: rota /app/ (serve PWA) | src/api/server.py | ✅ estendido |
| PWA iPhone — interface de voz | web/wind_voice/index.html | ✅ implementado |
| PWA manifest | web/wind_voice/manifest.json | ✅ |
| PWA service worker | web/wind_voice/sw.js | ✅ |
| Script startup simples | scripts/start_wind.bat | ✅ |
| Script startup + ngrok | scripts/start_wind_ngrok.ps1 | ✅ |
| WoL para VPS | scripts/wol_from_vps.py | ✅ |
| Testes Fase 10 (22 testes) | tests/unit/test_desktop.py | ✅ 22/22 passando |

**Arquitetura:**

**DesktopAgent** — 5 comandos whitelistados (nunca código arbitrário):
- `open_app`: abre Claude Code, Codex, terminal, explorer, notepad, browser
- `search_web`: pesquisa no Google (URL gerada com `urllib.parse.quote_plus`)
- `open_url`: abre URL em qualquer browser (somente http:// e https://)
- `get_status`: retorna CPU%, RAM disponível (psutil opcional), nome do PC
- `wake_screen`: move mouse 1px para acordar proteção de tela (ctypes Windows)

**API /desktop** — recebe `{"command": "...", "app": "..."}` via POST autenticado:
```
POST /desktop
X-API-Key: <WIND_API_KEY>
{"command": "open_app", "app": "claude"}
→ {"ok": true, "result": "Claude sendo aberto..."}
```

**API /app/** — serve os arquivos do PWA diretamente pelo WIND API server:
```
GET http://<IP>:8765/app/
→ Abre o PWA no Safari do iPhone
```

**PWA iPhone (`web/wind_voice/index.html`):**
- Interface de voz push-to-talk (microfone grande)
- STT: `webkitSpeechRecognition` em pt-BR (requer HTTPS no iOS Safari)
- TTS: `SpeechSynthesisUtterance` em pt-BR (funciona em HTTP + HTTPS)
- Botões de ação rápida: Claude Code, Codex, Pesquisar, Status PC, Status WIND, Acordar tela
- Configuração por tela de settings (URL + API Key salvos em localStorage)
- Indicador de status (verde = conectado, vermelho = erro)
- "Adicionar à Tela de Início" para ícone no iPhone
- Design dark, mobile-first, safe-area aware para iPhone com notch

**Wake-on-LAN:**
- Magic packet: 6×0xFF + 16 repetições do MAC (102 bytes total)
- `scripts/wol_from_vps.py`: rodar no VPS para ligar o PC remotamente
- Pré-requisitos: WoL habilitado no BIOS + roteador encaminhando UDP porta 9

**Acesso pelo iPhone:**
1. Mesma rede Wi-Fi: `http://192.168.X.Y:8765/app/` (URL local do PC)
2. Rede externa: usar ngrok → `start_wind_ngrok.ps1` exibe a URL https://xxxx.ngrok-free.app

**Nota sobre STT e HTTPS:**  
O `webkitSpeechRecognition` do iOS Safari exige HTTPS para microfone.  
Na rede local sem HTTPS, a interface exibe "Voz requer HTTPS. Use texto ou ngrok."  
Com ngrok, a URL é automaticamente HTTPS e o microfone funciona normalmente.

**Validado (2026-11-23):**
- 413/413 testes unitários passando (22 novos: DesktopAgent + WoL)
- DesktopAgent: open_app rejeita apps não permitidos ✅
- DesktopAgent: search_web gera URL Google correta ✅
- DesktopAgent: open_url rejeita FTP, javascript:, vazio ✅
- WoL: magic packet 102 bytes, estrutura correta ✅
- MAC parser: aceita AA:BB, AA-BB, lowercase; rejeita formato inválido ✅

**Pendências (pré-produção):**
- [ ] Testar acesso real do iPhone (endereço IP local do Felipe)
- [ ] Configurar ngrok authtoken para acesso externo
- [ ] Instalar `psutil` para dados de CPU/RAM: `pip install psutil`
- [ ] WoL: descobrir MAC do PC (`getmac /v /fo list | findstr "Fisico"`) e anotar aqui

---

## Fase 11 — Instalador nativo + Autonomia completa
**Estado:** `testado-dev` — 2026-11-23

| Módulo | Arquivo | Estado |
|---|---|---|
| DesktopAgent expandido | src/desktop/agent.py | ✅ 11 novos comandos |
| VoiceListener (STT + wake word) | src/voice/listener.py | ✅ implementado |
| VoiceAgent (integra Orchestrator) | src/voice/voice_agent.py | ✅ implementado |
| Package init voice | src/voice/__init__.py | ✅ |
| Instalador Windows | scripts/install_wind.ps1 | ✅ implementado |
| Script startup com voz | scripts/start_wind_voice.ps1 | ✅ |
| CLI — 10 novos comandos | src/wind.py | ✅ atualizado |
| Testes Fase 11 (25 testes) | tests/unit/test_phase11.py | ✅ 25/25 passando |
| Fix Guardian: histórico contaminando sessão | src/guardian/validator.py | ✅ corrigido |

**DesktopAgent expandido — novos comandos:**

| Comando | Descrição |
|---|---|
| `run_command` | Executa exe da whitelist (git, python, pip, dir, etc.) |
| `take_screenshot` | Captura tela (salva PNG) |
| `type_text` | Digita texto na janela ativa (pyautogui) |
| `focus_window` | Traz janela para frente por título (pygetwindow) |
| `read_clipboard` | Lê área de transferência |
| `write_clipboard` | Escreve na área de transferência |
| `git_status` | git status --short --branch |
| `git_commit` | git add -A + commit |
| `git_diff` | git diff (staged ou unstaged) |
| `list_files` | Lista arquivos de um diretório (glob) |
| `read_file` | Lê conteúdo de arquivo (máx 1 MB) |
| `write_file` | Escreve arquivo (apenas em diretórios seguros) |

**VoiceListener — wake word:**
- Escuta contínua em thread background
- Wake words: "wind", "hey wind", "ei wind", "vento"
- Após wake word: escuta até 8s para o comando
- STT via Google Speech Recognition (pt-BR)
- Fallback offline: vosk (a instalar com modelo pt-BR)

**VoiceAgent:**
- Integra VoiceListener + Orchestrator + TTS SAPI
- Fluxo: microfone → STT → Orchestrator.process() → TTS fala a resposta
- Hook on_command(text, response) para logging
- Degradação graciosa: `start()` retorna False sem dependências

**Instalador (`scripts/install_wind.ps1`):**
1. Verifica Python 3.10+
2. Instala dependências core (anthropic, openai, psutil, requests)
3. Instala automação (pyautogui, pyperclip, pygetwindow, SpeechRecognition, pyaudio)
4. Configura ANTHROPIC_API_KEY / OPENAI_API_KEY / WIND_API_KEY (securo via Read-Host)
5. Cria pasta `data/`
6. Cria atalho na área de trabalho
7. Verifica instalação via health check

**Novos comandos CLI:**
```
/voz              ativa/desativa escuta por wake word "WIND"
/desktop <cmd>    executa ação desktop diretamente
/git-status       git status do diretório atual
/git-commit <msg> git add -A + commit
/git-diff         git diff
/ls [path]        lista arquivos
/ler <path>       lê conteúdo de arquivo
/screenshot       captura tela
/clipboard        lê área de transferência
/pc-status        status CPU, RAM, disco
```

**Para ativar voz:**
```powershell
pip install SpeechRecognition pyaudio
python src/wind.py --voz
# Ou:
.\scripts\start_wind_voice.ps1
```

**Validado (2026-11-23):**
- 438/438 testes unitários passando (25 novos Fase 11)
- run_command: whitelist enforced — exe não permitido bloqueado ✅
- write_file: apenas dentro de safe_dirs ✅
- VoiceAgent: start() retorna False sem pyaudio ✅
- VoiceAgent: command hook chamado com (text, response) ✅
- AuditLog: toda ação desktop registrada em data/audit.jsonl ✅
- Fix Guardian: SECRET verificado apenas na mensagem atual ✅

**Dependências opcionais (melhoram funcionalidade):**
```powershell
pip install pyautogui        # type_text, take_screenshot
pip install pygetwindow      # focus_window
pip install pyperclip        # clipboard (fallback ctypes disponível)
pip install SpeechRecognition pyaudio  # voz nativa
pip install psutil           # CPU/RAM no get_status
```
- [ ] Configurar WoL no BIOS se quiser ligar o PC remotamente
- [ ] Registrar service worker no index.html (adicionar `<script>if('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js')</script>`)
- [ ] git push para GitHub (executar no terminal do Felipe)
