# WIND — AGENTS.md
> Equivalente do CLAUDE.md para o Codex. Regras idênticas; lido automaticamente pelo Codex a cada sessão.

## Identidade
Este repositório é a WIND. O Codex é uma ferramenta de codificação; a WIND decide e coordena.

## Regras obrigatórias (mesmas do CLAUDE.md)
- Nunca declare testado o que não executou.
- Nunca coloque credenciais em código, mensagem ou log.
- Nunca faça ação em produção, VPS, contas reais ou dados de clientes.
- Commits pequenos e reversíveis. Documentação atualizada.

## Protocolo de sessão
1. Leia `docs/WIND_IMPLEMENTATION_STATUS.md`.
2. Trabalhe apenas na fase autorizada.
3. Spikes somente em `spikes/` com dados sintéticos.
4. Ao terminar: atualize o status, faça commit pequeno.

## Escopo do Codex dentro da WIND
- Tarefas de codificação intensiva (geração de módulos, refactoring, scripts de análise).
- Nunca tomar decisões de arquitetura sem registrar em `docs/WIND_DECISIONS.md`.
- Para skills: seguir formato agentskills.io (SKILL.md + scripts).

## Mapa do repositório
Idêntico ao CLAUDE.md — ver `CLAUDE.md`.
