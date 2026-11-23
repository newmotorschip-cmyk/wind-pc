# WIND_EVALUATION_PLAN.md
> Fase 0 — criado 2026-11-23. Executar os conjuntos de teste a cada mudança relevante.

## Princípio
Nenhuma melhoria é declarada sem número medido antes e depois. Nenhum conjunto de teste é alterado para fazer um modelo passar.

---

## 1. Compreensão em Português do Brasil

**Conjunto:** 50 perguntas cobrindo domínios: diagnóstico automotivo, calibração de ECU, engenharia reversa, gestão de oficina, finanças pessoais, conversação geral.  
**Formato:** pergunta aberta + resposta esperada (redigida pelo Felipe) + critérios de avaliação.  
**Métricas:**
- Acurácia semântica (avaliação humana 1–5): meta baseline ≥ 3,5
- Precisão técnica (terminologia correta): meta ≥ 90 %
- Adequação de registro (português BR informal mas preciso): meta ≥ 4,0

**Quando rodar:** antes de qualquer mudança de modelo ou prompt de identidade.  
**Responsável por criar o conjunto:** Felipe (Fase 1).

---

## 2. Memória — Recuperação de Casos

**Conjunto:** 20 casos sintéticos de serviço criados com dados de veículos fictícios.  
**Consultas:** 20 perguntas de recuperação ("qual serviço parecido com Corolla 2020 P0300?").  
**Métricas:**
- Recall@1 (caso correto no primeiro resultado): meta ≥ 0,80
- Recall@3: meta ≥ 0,95
- Latência de busca: meta ≤ 2 s por consulta

**Quando rodar:** a cada mudança no módulo de memória episódica (Fase 3+).

---

## 3. Engenharia Reversa — Identificação em Firmware

**Conjunto:** 10 arquivos de firmware com rótulos verificados pelo Felipe:
- Arquitetura correta (TriCore / PowerPC-VLE / SH / V850)
- Base address correto (quando conhecido)
- Mínimo 3 funções rotuladas por arquivo
- Pelo menos 2 mapas de calibração identificados por arquivo

**Fonte:** pares ORI×MOD existentes no acervo do Felipe (caminhos em [PREENCHER]).  
**Métricas:**
- Taxa de identificação correta de arquitetura: meta ≥ 0,95
- Precisão de base address: meta ≥ 0,80 (quando aplicável)
- F1 de identificação de mapas vs rótulos: meta ≥ 0,70

**Quando rodar:** a cada mudança no pipeline RE (Fase 4+).  
**Separação:** 7 treino / 3 teste; conjunto de teste não é usado em desenvolvimento.

---

## 4. Qualidade de Decisão — Motor de Autonomia

**Conjunto:** 30 cenários de decisão cobrindo todos os níveis A0–A4 e diferentes combinações de risco × reversibilidade × confiança.  
**Rótulos:** nível correto esperado por cenário + se deve escalar ou agir.  
**Métricas:**
- % de nível correto: meta ≥ 0,90
- % de escalações desnecessárias (falso positivo): meta ≤ 0,10
- % de escalações perdidas (falso negativo — age sem dever): meta ≤ 0,02

**Quando rodar:** a cada mudança no Decision Engine (Fase 1+).

---

## 5. Eficiência de Custo

**Conjuntos de benchmark:**
- 10 tarefas simples (pergunta + resposta direta)
- 5 tarefas de desenvolvimento (criar função, revisar código)
- 5 tarefas de engenharia reversa (identificar arquitetura)
- 5 tarefas de memória (recuperar + sintetizar caso)

**Métricas por tarefa:**
- Custo em USD
- Latência em segundos
- Tokens de entrada/saída
- Resultado correto (sim/não)

**Derivadas:**
- Custo por tarefa concluída corretamente
- % de tasks resolvidas pelo modelo local vs nuvem

**Quando rodar:** ao final de cada fase + a cada mudança de roteamento.  
**Meta inicial:** ≤ US$ 2/dia no total; revisar com dados reais.

---

## 6. Status dos conjuntos de teste

| Conjunto | Estado |
|---|---|
| Português BR (50 perguntas) | Aguardando criação — Felipe (Fase 1) |
| Memória — 20 casos sintéticos | Aguardando criação — Fase 3 |
| RE — 10 firmwares rotulados | Aguardando acervo ORI×MOD [PREENCHER] |
| Decisão — 30 cenários | Aguardando criação — Fase 1 |
| Benchmark de custo — 25 tasks | Aguardando criação — Fase 1 |
