# WIND_CONTEXT.md
> Contexto real da instalação — descoberto automaticamente + preenchido pelo Felipe.
> Atualizar este arquivo em vez de editar WIND_MASTER_SPEC.md.
> Última atualização: 2026-11-23

---

## Máquina principal (PC)

| Item | Valor | Fonte |
|---|---|---|
| OS | Windows 10 Pro 10.0.19045 | PowerShell |
| CPU | Ryzen 7 5700X | Felipe |
| GPU | RTX 3080 10 GB | Felipe |
| RAM | 32 GB | Felipe |
| Armazenamento | NVMe 2 TB (C:) + D: (disco com acervo) | disco |
| Status habitual | Normalmente desligado | Felipe |

---

## Runtime e ferramentas instaladas

| Ferramenta | Versão / Caminho | Status |
|---|---|---|
| Python | 3.12 (padrão do sistema) | ✅ instalado |
| JDK | 25.0.4 — `C:\Program Files\Eclipse Adoptium\jdk-25.0.4.101-hotspot` | ✅ instalado |
| Ghidra | 12.1.4 — `C:\Users\Repro\Documents\ghidra_12.1.4_PUBLIC` | ✅ instalado |
| Node.js | — | ❌ não instalado — instalar na Fase 1 |
| Git | — | ❌ não instalado — instalar na Fase 1 |
| anthropic (Python) | — | ❌ não instalado — instalar na Fase 1 |
| openai (Python) | — | ❌ não instalado — instalar na Fase 1 |
| WinOLS 4.7 | `C:\Users\Repro\Documents\4.7winols` | ✅ pasta presente |

---

## Chaves de API e acesso a modelos

| Item | Valor |
|---|---|
| Claude Code | Plano Pro/Max (assinatura) — sem ANTHROPIC_API_KEY configurada |
| Codex / OpenAI | API key paga por uso — OPENAI_API_KEY **ainda não configurada como env var** |
| Orçamento diário aprovado | US$ 2/dia (meta inicial) — revisar com medição real na Fase 1 |

**Ação pendente Fase 1:** configurar OPENAI_API_KEY em variável de ambiente (cofre de segredos, nunca em código).

---

## Acervo técnico (automotivo)

### ORI×MOD — principal
- **Caminho:** `D:\Ori+Mod.ecu`
- **Marcas:** AIRBAG, Audi, BMW, Chevrolet, EMS 23XX, EMS3134, Fiat, Ford, Hyundai, IVECO, Jeep, Mercedes, Mitsubishi, Nissan, Peugeot & Citroën, Porsche, Renault, Volkswagen
- **Extras:** pasta `SM2 ENVIAR` (upload Scanmatik), `Damos pack 2020.rar` (9,6 GB)
- **A2L/OLS:** não localizados na raiz — verificar subpastas por marca na Fase 4

### Especialidades (D:\)
- `D:\Abs` — arquivos ABS
- `D:\Airbag` — programação de airbag
- `D:\arquivos Tcm` — TCM (caixa de câmbio)
- `D:\Bcm` — BCM (módulo de carroceria)
- `D:\Immobilizador` — imobilizador
- `D:\DTS` — DTS Monaco / diagnóstico

### Software de calibração
- WinOLS 4.7: `C:\Users\Repro\Documents\4.7winols`

---

## Projetos encontrados na máquina

| Projeto | Caminho encontrado | Observação |
|---|---|---|
| CARTECH-NetShare | `C:\Users\Repro\Desktop\CARTECH-NetShare-2.0.0` | Pacote de deploy / instalador (v2.0.0) |
| BoxControl | — | Não localizado no PC — pode estar na VPS |
| REPROTECH Native | — | Não localizado no PC |
| GMap | — | Não localizado no PC |
| ViralCut AI | — | Não localizado no PC |
| Arena BR | — | Não localizado no PC |

---

## VPS

| Item | Valor |
|---|---|
| Provedor | Hostinger |
| Localização | Brazil — Campinas |
| Sistema operacional | Ubuntu 24.04 LTS |
| Hostname | srv2137886.hstgr.cloud |
| IPv4 | 187.41.126.171 |
| Usuário SSH | root |
| Backup atual | Semanal (Hostinger) |
| Serviços rodando | Jarvis antigo (a deletar) + [verificar na Fase 1] |
| Credencial SSH | **Não armazenada aqui** — configurar no cofre de segredos na Fase 1 |
| Ação pendente | Deletar Jarvis antigo + configurar como gateway/fila WIND |

---

## iPhone

| Item | Valor |
|---|---|
| Modelo | iPhone 11 |
| iOS | 27 |

---

## Contas e serviços da empresa

| Item | Valor |
|---|---|
| Instagram REPROTECH | [AGUARDANDO FELIPE] |
| WhatsApp Business | [AGUARDANDO FELIPE] |
| E-mail empresa | [AGUARDANDO FELIPE] |
| Agenda / calendário | [AGUARDANDO FELIPE] |
| Nuvem (backup) | [AGUARDANDO FELIPE] |
| Corretoras / exchanges | [AGUARDANDO FELIPE] |

---

## Dependências a instalar na Fase 1 (checklist)

- [ ] Git for Windows
- [ ] Node.js LTS (para Claude Agent SDK e scripts)
- [ ] `pip install anthropic openai` (ou `uv` / `venv`)
- [ ] Configurar OPENAI_API_KEY em variável de ambiente (cofre)
- [ ] Verificar compatibilidade jpype + JDK 25 (spike em spikes/)
