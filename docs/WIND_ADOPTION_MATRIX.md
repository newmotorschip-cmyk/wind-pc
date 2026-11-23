# WIND_ADOPTION_MATRIX.md
> Fase 0 — criado 2026-11-23. Atualizar a cada fase quando testes forem executados.

Legenda — Decisão: **Adotar** (integrar como dependência), **Referenciar** (inspiração sem vínculo), **Descartar**.

---

## 1. OpenJarvis (Stanford / Hazy Research)
| Campo | Detalhe |
|---|---|
| Problema que resolve | Framework modular de IA pessoal on-device com cinco primitivas intercambiáveis |
| Componentes úteis | Primitivas (Intelligence, Engine, Agentic Logic, Memory, Learning), telemetria por chamada (custo/latência/energia), trace-driven feedback, registry decorador, sandbox Docker/Podman |
| Riscos | Versão em dev builds (1.0.3.dev*), router interno não documentado, foco em on-device pode conflitar com arquitetura híbrida local+nuvem da WIND |
| Licença | Apache 2.0 |
| Compatibilidade com PC | Python — compatível |
| Testes feitos | Nenhum — não instalado nesta sessão |
| Decisão | **Referenciar** — adotar o padrão de cinco primitivas e telemetria; construir router próprio pois a lógica de roteamento local/nuvem é diferencial da WIND e não está documentada no OpenJarvis |
| Fonte verificada | https://scalingintelligence.stanford.edu/blogs/openjarvis (2026), https://open-jarvis.github.io/OpenJarvis/architecture/overview |

---

## 2. Hermes Agent (Nous Research)
| Campo | Detalhe |
|---|---|
| Problema que resolve | Ciclo fechado de aprendizado: cria skills após tarefas não triviais, melhora no uso, memória entre sessões com FTS5 |
| Componentes úteis | Síntese de skills, busca FTS5, formato agentskills.io, 40+ skills built-in, retroalimentação de desempenho |
| Riscos | Lançado fevereiro 2026 — ainda inicial; documentação parcialmente em espelhos de terceiros |
| Licença | MIT |
| Compatibilidade com PC | Python — compatível |
| Testes feitos | Nenhum |
| Decisão | **Referenciar** para o ciclo de aprendizado; **Adotar agentskills.io** como formato de skills da WIND (ver item 3) |
| Fonte verificada | https://hermes-agent.nousresearch.com/docs (2026-02) |

---

## 3. Padrão agentskills.io (Agentic AI Foundation / Linux Foundation)
| Campo | Detalhe |
|---|---|
| Problema que resolve | Formato portável de skills entre agentes (SKILL.md + scripts + arquivos de referência) |
| Componentes úteis | Formato SKILL.md, hub com 1M+ skills, suporte declarado em 70+ plataformas incluindo Claude Code e Codex |
| Riscos | Especificação jovem (dez 2025); 341 skills maliciosas relatadas em fóruns — não verificado em fonte primária; campo `allowed-tools` experimental |
| Licença | Apache 2.0 + CC BY 4.0 |
| Compatibilidade com PC | Independe de runtime |
| Testes feitos | Nenhum |
| Decisão | **Adotar** como formato de skills da WIND; toda skill nova da WIND deve seguir este formato para portabilidade |
| Fonte verificada | https://www.anthropic.com/news/donating-agent-skills-to-the-agentic-ai-foundation, https://aaif.io |

---

## 4. Claude Agent SDK (Anthropic)
| Campo | Detalhe |
|---|---|
| Problema que resolve | Integração programática com Claude — sessões, tools, MCP, cancelamento, custo |
| Componentes úteis | Transports MCP (stdio/HTTP/in-process), tool search, output limits com file dump, sessões |
| Riscos | A partir de 15/06/2026, uso na assinatura consome créditos mensais do Agent SDK — impacto no orçamento; OAuth2 MCP não totalmente suportado |
| Licença | Termos de uso Anthropic |
| Compatibilidade com PC | Python SDK — Python 3.12 instalado ✅ |
| Testes feitos | Ativo nesta sessão (Claude Code) |
| Decisão | **Adotar** — ferramenta primária para tarefas Claude; monitorar impacto de créditos após 15/06/2026 |
| Fonte verificada | https://code.claude.com/docs/en/agent-sdk/overview.md |

---

## 5. OpenAI Codex SDK + CLI
| Campo | Detalhe |
|---|---|
| Problema que resolve | Integração programática com Codex para tarefas de codificação intensiva |
| Componentes úteis | TypeScript SDK (@openai/codex-sdk) via JSONL, Python SDK via JSON-RPC; `codex exec` para scripting |
| Riscos | Python SDK em beta (status variável); MCP server deprecado — usar App Server; Node.js 18+ obrigatório para TS SDK |
| Licença | Termos de uso OpenAI |
| Compatibilidade com PC | Node.js e Python — verificar instalação |
| Testes feitos | Nenhum programático — Codex Desktop instalado (visto em estado global) |
| Decisão | **Adotar** como ferramenta secundária para codificação pesada; priorizar TS SDK sobre Python SDK até beta ser confirmado estável |
| Fonte verificada | https://developers.openai.com/codex/sdk (2026) |

---

## 6. MCP — Model Context Protocol
| Campo | Detalhe |
|---|---|
| Problema que resolve | Protocolo único de integração entre WIND e ferramentas externas (Ghidra, browsers, DBs, serviços) |
| Componentes úteis | Transports stdio/HTTP/in-process, tool definitions com schemas, output handling |
| Riscos | OAuth2 MCP não suportado em client (pode limitar integrações de serviços externos) |
| Licença | Open standard |
| Compatibilidade com PC | Já em uso nesta sessão |
| Testes feitos | Ativo em produção (esta sessão usa MCP) |
| Decisão | **Adotar** como protocolo padrão de integração — cada conector da WIND expõe uma interface MCP |
| Fonte verificada | https://code.claude.com/docs/en/agent-sdk/mcp |

---

## 7. Ghidra 12.1.4
| Campo | Detalhe |
|---|---|
| Problema que resolve | Disassembly e decompilação de firmware automotivo |
| Componentes úteis | Suporte a TriCore (TC172x, TC176x, TC29x), PowerPC+VLE, SuperH (SH-1, SH-2, SH-2A), V850, ARM, HCS12 — tudo verificado no diretório Processors/ |
| **Ausente** | C166 / XC2000 — precisa de módulo SLEIGH personalizado |
| Riscos | C166/XC2000 ausente bloqueia análise de ECUs antigas Bosch (ME7.x, etc.); loaders automotivos proprietários não verificados |
| Licença | Apache 2.0 |
| Compatibilidade com PC | Instalado em C:\Users\Repro\Documents\ghidra_12.1.4_PUBLIC ✅ |
| Testes feitos | Verificação de Processors/ — lista completa confirmada |
| Decisão | **Adotar** como ferramenta principal de RE; primeira tarefa do Pacote 6.2 = verificar loaders + planejar módulo SLEIGH para C166/XC2000 |

---

## 8. PyGhidra
| Campo | Detalhe |
|---|---|
| Problema que resolve | Bridge Python–Ghidra via jpype; modo headless sem GUI |
| Componentes úteis | Análise headless de firmware, scripting Python dentro do contexto Ghidra, integração com pyghidra-mcp |
| Riscos | Requer Python 3.10–3.13; jpype pode ter problemas de compatibilidade com JDK 25 instalado no PC |
| Licença | Apache 2.0 |
| Compatibilidade com PC | Python 3.12 instalado ✅; JDK 25 instalado — testar compatibilidade |
| Testes feitos | Nenhum |
| Decisão | **Adotar** para scripting headless; spike de compatibilidade com JDK 25 necessário na Fase 4 |

---

## 9. pyghidra-mcp (clearbluejar) / GhidraMCP (LaurieWired)
| Campo | Detalhe |
|---|---|
| Problema que resolve | Expõe Ghidra via MCP — permite Claude analisar firmware diretamente |
| Componentes úteis | Multi-binary support (pyghidra-mcp), 1-para-1 binário (GhidraMCP), integração com Ghidra 12.1.4 |
| Riscos | Múltiplos forks concorrentes; maturidade variada; ReVa, MCPyGhidra e outros também existem |
| Licença | Varia por fork — verificar |
| Compatibilidade com PC | Python 3.10+ e Ghidra instalados |
| Testes feitos | Nenhum |
| Decisão | **Avaliar** pyghidra-mcp (clearbluejar) como primeira opção na Fase 4 — cobre multi-binário; GhidraMCP como fallback |
| Fonte verificada | https://clearbluejar.github.io/posts/pyghidra-mcp-headless-ghidra-mcp-server-for-project-wide-multi-binary-analysis |

---

## Gaps críticos da Fase 0
1. C166/XC2000 não suportado no Ghidra — bloqueia análise de ECUs antigas.
2. VPS (provedor, SO, serviços, acesso SSH) = **[PREENCHER]** — bloqueia design de camadas VPS vs PC.
3. Node.js instalado? — necessário para Codex TS SDK. Não verificado.
4. JDK 25 vs PyGhidra — compatibilidade não testada.
