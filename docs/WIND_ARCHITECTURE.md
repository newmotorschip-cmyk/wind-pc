# WIND_ARCHITECTURE.md
> Fase 0 — criado 2026-11-23. Atualizar a cada fase.

## 1. Onde cada peça roda

| Componente | Local | Justificativa |
|---|---|---|
| Core / Orquestrador | VPS (always-on) | PC normalmente desligado; VPS recebe requests e enfileira |
| Router de modelos | VPS (decisão) + PC (execução local) | VPS decide, aciona WoL se precisar de modelo local |
| Guardian | Ambos — VPS (filtro de entrada) + PC (filtro de saída) | Independente do modelo, camada de segurança dupla |
| Memória (sessão, episódica) | VPS | Acesso rápido, não sai da máquina |
| Memória (semântica, procedural, skills) | PC (volume, embeddings) | GPU para indexação e busca semântica |
| Motor de missões | VPS | Filas, checkpoints, retomada durável |
| Modelos locais (triagem, resumo) | PC (RTX 3080 10 GB) | Apenas quando PC ligado |
| Ghidra / RE | PC | GPU + RAM necessários; ferramenta local |
| Integrações externas (Claude SDK, Codex SDK) | VPS | Chamadas de API saem da VPS |
| BoxControl | Separado — acesso via contrato | Não duplicar dados |
| Cliente / UX | iPhone (cliente leve) | Envia requests à VPS |

---

## 2. Camadas e contratos

### Camada 1 — Núcleo (Core)
**Módulos:** Identity & Persona, Session Manager, Orchestrator, Model Router, Context Manager  
**Contrato de entrada:** `CoreRequest { session_id, user_id, payload, metadata }`  
**Contrato de saída:** `CoreResponse { session_id, result, cost_telemetry, audit_ref }`  
**Regra:** Toda request passa pelo Guardian antes de chegar ao Orchestrator.

### Camada 2 — Memória
**Tipos:** Sessão · Episódica (casos) · Semântica (conhecimento técnico) · Procedural (skills) · Por projeto · Por pessoa/cliente · Registro de evidências  
**Metadados obrigatórios em cada item:** `{ origin, created_at, confidence, valid_until, state: hypothesis|proposed|validated|obsolete }`  
**Contrato:** `MemoryQuery { type, filters, limit }` → `MemoryResult { items[], source_refs[] }`  
**Regra:** Dados de classe `personal` ou `client` nunca saem para busca remota sem anonimização.

### Camada 3 — Aprendizado
**Módulos:** Case Recorder, Skill Synthesizer, Skill Evaluator, Retrospective Engine  
**Contrato de entrada:** `CaseRecord { vehicle?, project?, input, actions[], outcome, duration_s, cost_usd, lessons }`  
**Regra:** Skill nova entra com `state: proposed`; sobe para `validated` somente após aprovação do Felipe ou teste objetivo. Nunca altera Guardian, Core ou permissões.

### Camada 4 — Autonomia
**Módulos:** Mission Engine (filas, checkpoints, idempotência), Decision Engine (nível A0–A4)  
**Contrato de decisão:** `Decision { request, options[], risk_level, reversible, confidence, requires_level }` → `DecisionRecord { choice, approved_by, outcome }`  
**Níveis:**
- A0: só responde
- A1: lê e pesquisa
- A2: executa em ambiente isolado (reversível)
- A3: altera projetos autorizados com commit/rollback
- A4: age fora (mensagens, publicações, compras) — aprovação por operação, autenticação reforçada

### Camada 5 — Pacotes de especialista
Cada pacote tem interface definida e é carregado sob demanda. Ver `docs/WIND_MASTER_SPEC.md` seções 6.1–6.7.

### Camada 6 — Integrações
**Padrão:** cada conector expõe ou consome interface MCP.  
**Conectores:** Claude Agent SDK · Codex SDK · Ghidra (pyghidra-mcp) · BoxControl API · Agenda/e-mail · Redes sociais · iPhone (push/APNS) · WoL

### Camada 7 — Guardian
**Regras:** deny-by-default, privilégio mínimo, approve-by-operation, secrets vault, auditoria append-only, revogação, botão de emergência.  
**Classificação de dados tratada aqui:** ver `docs/WIND_DATA_CLASSIFICATION.md`  
**Imutável pelo modelo durante missão.**

### Camada 8 — Experiência
**Canais:** texto (chat), voz (iPhone), notificações push, aprovações com 2FA, acompanhamento de missões.  
**Língua:** português do Brasil por padrão.

---

## 3. Cinco fluxos de ponta a ponta

### Fluxo 1 — Continuar um projeto
```
iPhone
  → [request: "continue o projeto BoxControl"]
VPS (Core, A1)
  → Guardian verifica permissão e classifica dados
  → Memory: recupera ficha do projeto BoxControl (stack, estado, decisões, branch, último commit)
  → Decision Engine: PC necessário? se sim → WoL
PC (Core, A2/A3)
  → Claude Agent SDK: cria sessão com contexto do projeto
  → Resultado retorna via VPS → iPhone
```
**Ponto de aprovação:** se ação envolver commit ou push (A3), Felipe confirma no iPhone antes.

### Fluxo 2 — Abrir um novo serviço de oficina
```
PC / tablet da oficina
  → WIND: "abrir serviço — Corolla 2020, DTC P0300"
Guardian
  → dados do cliente: anonymize placa/nome → não sai do PC sem filtro
Memory
  → busca casos similares (Corolla 2020, ECU semelhante, P0300)
  → retorna top-3 casos com o que funcionou e o que falhou
Case Recorder
  → cria CaseRecord com state=open
BoxControl (via contrato)
  → abre OS vinculada
```
**Ponto de aprovação:** fechamento do caso requer confirmação do Felipe (3 perguntas curtas).

### Fluxo 3 — Analisar um firmware
```
PC (Ghidra disponível)
  → Felipe: "analise este firmware — 03L906012FF"
Guardian
  → verifica: arquivo não é software comercial pirata? origem verificada?
  → se não verificado: pergunta ao Felipe
Pipeline RE
  → backup + hash do original (somente leitura)
  → Ghidra headless via pyghidra-mcp: identifica arquitetura, base address, funções candidatas
  → resultados: strings, referências cruzadas, hipóteses
  → relatório com evidências; hipóteses marcadas como não validadas
Memory
  → armazena relatório com state=hypothesis
```
**Ponto de aprovação:** hipóteses sobem para `validated` apenas com confirmação do Felipe.

### Fluxo 4 — Operação financeira com escrita
```
iPhone / PC
  → Felipe: "pagar fornecedor R$ 1.200 — conta X"
Guardian (nível A4 obrigatório)
  → classifica: financeiro + escrita = A4 + autenticação reforçada
  → Decision Engine: monta DecisionRecord {valor, destino, reversível: depende}
  → notifica Felipe no iPhone com detalhes completos (valor, destino, taxa se houver, reversibilidade)
  → aguarda confirmação em canal separado (2FA / Face ID)
  → se confirmado: executa via conector oficial da instituição
  → auditoria append-only: grava tudo
```
**Ponto de aprovação:** obrigatório em canal separado antes de qualquer ação.

### Fluxo 5 — Request do iPhone com PC desligado
```
iPhone
  → Felipe: "resumo do projeto Arena BR"
VPS (Core)
  → Memory: recupera ficha do projeto Arena BR (apenas dados em memória VPS)
  → Decision Engine: PC necessário para esta task? não — só leitura de memória
  → Claude via API (nuvem): gera resumo com contexto do projeto
  → responde no iPhone
---
  Alternativa — task precisa do PC:
  VPS
  → enfileira a missão com checkpoint
  → envia WoL para o PC
  → PC inicializa, Core local retoma a missão
  → resultado retorna via VPS → iPhone
```

---

## 4. Itens aguardando [PREENCHER]
- Provedor VPS, SO, IP, serviços em execução — impacta design de filas e comunicação VPS↔PC
- Modelo iPhone — impacta design de notificações (APNS vs outro)
- Roteador de rede local para WoL — verificar se há suporte
