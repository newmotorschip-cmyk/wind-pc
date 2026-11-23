# WIND_DECISIONS.md
> Fase 0 — criado 2026-11-23. Registrar todas as decisões arquiteturais com alternativas e evidências.

Formato: cada decisão tem ID, estado, contexto, alternativas, evidência, escolha e o que reavaliar.

---

## D-001 — Base do núcleo da WIND
**Estado:** Decidido  
**Data:** 2026-11-23

**Contexto:**  
O prompt mestre lista três opções para o núcleo: fork do OpenJarvis, dependência do OpenJarvis, ou núcleo próprio inspirado nele.

**Alternativas:**
| Opção | Prós | Contras |
|---|---|---|
| Fork OpenJarvis | Ponto de partida maduro, telemetria incluída | Versão em dev, router não documentado, obriga acompanhar upstream |
| Dependência OpenJarvis | Menos código para manter | Presos ao roadmap deles, sem controle do router |
| Núcleo próprio inspirado no OpenJarvis | Controle total, router híbrido local/nuvem como diferencial | Mais trabalho inicial |

**Evidência:**  
OpenJarvis v1.0.3.dev* ainda instável; documentação de roteamento ausente; foco on-device conflita com arquitetura híbrida necessária (PC desligado na maior parte do tempo → VPS como gateway).

**Decisão:** **Núcleo próprio** seguindo o padrão de cinco primitivas do OpenJarvis (Intelligence, Engine, Agentic Logic, Memory, Learning) com telemetria trace-driven, mas com router local/nuvem próprio.

**Reavaliar:** quando OpenJarvis 1.1.x estável com documentação de roteamento — potencial migração para reduzir código mantido.

---

## D-002 — Ciclo de aprendizado e formato de skills
**Estado:** Decidido  
**Data:** 2026-11-23

**Contexto:**  
Hermes Agent oferece ciclo de aprendizado fechado (cria skills após tarefas não triviais, melhora no uso, memória FTS5). agentskills.io é o padrão portável de skills adotado por 70+ plataformas.

**Decisão:** 
- Ciclo de aprendizado: implementar **baseado no padrão Hermes** (registro de caso → síntese de skill → validação → promoção), sem depender do pacote Hermes.
- Skills: **adotar agentskills.io** (SKILL.md + scripts + refs) como formato canônico de todas as skills da WIND.

**Reavaliar:** se Hermes Agent ganhar estabilidade e documentação oficial — considerar integração direta.

---

## D-003 — Protocolo de integração entre módulos
**Estado:** Decidido  
**Data:** 2026-11-23

**Contexto:**  
Necessidade de protocolo único para conectar WIND a ferramentas (Ghidra, browsers, DBs, APIs externas, Claude, Codex).

**Decisão:** **MCP como protocolo padrão** para todos os conectores. Cada ferramenta externa expõe ou consome uma interface MCP. Fallback direto via SDK para ferramentas sem suporte MCP.

---

## D-004 — Roteamento de modelos (local vs nuvem)
**Estado:** Decidido  
**Data:** 2026-11-23

**Contexto:**  
RTX 3080 10 GB (PC normalmente desligado). Artigo OpenJarvis indica queda de 25–39 pontos em modelos locais vs nuvem; otimizações fecham para 3,2 pontos em média.

**Decisão:**
| Tarefa | Modelo |
|---|---|
| Triagem, classificação, resumo, extração, busca | Local (Ollama/LM Studio, RTX 3080) |
| Raciocínio difícil, decisões críticas, geração complexa | Claude via Agent SDK |
| Tarefas pesadas de codificação com contexto grande | Codex via SDK |
| Consultas rápidas (VPS, PC desligado) | Claude via Agent SDK (nuvem) |

Implementar **telemetria por chamada** (custo, latência, qualidade estimada) desde o início; revisar alocação com dados reais na Fase 8.

**Reavaliar:** a cada fase com base em métricas coletadas.

---

## D-005 — Ferramenta principal de engenharia reversa
**Estado:** Decidido  
**Data:** 2026-11-23

**Contexto:**  
Ghidra 12.1.4 instalado, suporte verificado para TriCore, PowerPC+VLE, SuperH, V850. C166/XC2000 ausente. Múltiplas opções de integração MCP (pyghidra-mcp, GhidraMCP, ReVa, MCPyGhidra).

**Decisão:**  
- Ghidra 12.1.4 como ferramenta principal de RE.
- Integração via **pyghidra-mcp** (clearbluejar) como primeira opção — avaliação na Fase 4.
- Módulo SLEIGH para C166/XC2000: pesquisar módulos existentes na comunidade antes de escrever do zero.
- Verificar compatibilidade PyGhidra + JDK 25 no primeiro spike (Fase 4).

---

## D-006 — Dados de clientes e LGPD
**Estado:** Decidido  
**Data:** 2026-11-23

**Contexto:**  
ECUs, placas, VINs, dados de serviço são dados potencialmente pessoais (LGPD). Modelos remotos (Claude, Codex) não devem receber dados identificáveis.

**Decisão:**  
- Dados pessoais ficam **locais por padrão**.
- Antes de qualquer envio remoto: remoção de identificadores (anonimização), registro da finalidade, aprovação via Guardian.
- Integração com BoxControl por **contrato de interface** — sem duplicação de dados.

---

## D-007 — Windows 10 sem suporte regular (Guardian)
**Estado:** Proposta pendente  
**Data:** 2026-11-23

**Contexto:**  
O Guardian do prompt mestre recomenda solução para Windows 10 sem suporte antes de conceder privilégios elevados.

**Decisão pendente:** Propor opções ao Felipe na Fase 1:
1. Upgrade para Windows 11 (hardware compatível — Ryzen 7 5700X ✅)
2. WSL2 com Ubuntu para isolamento de processos sensíveis
3. VM dedicada para operações privilegiadas

**Aguarda:** aprovação do Felipe antes de qualquer ação no sistema.

---

## D-008 — VPS como gateway (parcial — aguarda [PREENCHER])
**Estado:** Parcialmente decidido  
**Data:** 2026-11-23

**Contexto:**  
VPS = gateway e fila; PC = processamento pesado; iPhone = cliente. PC normalmente desligado → WoL necessário.

**Decidido:**  
- VPS não tem controle administrativo sobre o PC.
- Conexões partem do Core (PC inicia, não VPS).
- WoL por dispositivo na LAN.

**Aguarda:** provedor VPS, SO, serviços existentes e acesso SSH para concluir design.
