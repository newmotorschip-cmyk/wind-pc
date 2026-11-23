# WIND_DATA_CLASSIFICATION.md
> Fase 0 — criado 2026-11-23.

## Classificação

| Classe | Exemplos | Roteamento | Envio remoto | Retenção |
|---|---|---|---|---|
| **Público** | Documentação técnica, manuais abertos, legislação | Sem restrição | Permitido | Indefinida |
| **Pessoal (LGPD)** | Nome, CPF, telefone, e-mail, endereço, placa, VIN | Local por padrão | Só anonimizado + finalidade registrada + aprovação Guardian | Mínima necessária; exclusão a pedido |
| **Confidencial-cliente** | Diagnóstico, DTCs, histórico de serviço, arquivos de ECU do cliente | Local por padrão | Nunca identificado; dataset de ML = anonimizado + hash | Contrato com cliente |
| **Financeiro** | Faturas, pagamentos, extratos, notas de corretagem, chaves de API financeiras | Local por padrão | Regra explícita por operação + aprovação A4 | Mínima legal |
| **Secreto** | Chaves API (Claude, OpenAI), SSH, certificados, tokens OAuth | Nunca ao modelo | Nunca | Em vault — nunca em código ou log |

---

## Regras de roteamento por classe

### 1. Público
- Pode ir a qualquer modelo (local ou nuvem) sem filtro adicional.

### 2. Pessoal (LGPD)
- Antes de enviar a modelo remoto: remover nome, CPF, telefone, e-mail, placa, VIN.
- Registrar: `{ data_class: personal, purpose: "...", anonymized: true, timestamp }` no log de auditoria.
- Permitir exclusão total a pedido do titular.

### 3. Confidencial-cliente
- Nunca enviar identificadores de cliente a modelos remotos.
- Para treinamento/avaliação: usar hash anônimo do veículo, nunca placa ou VIN real.
- Integração com BoxControl: dados trafegam via contrato de interface local — sem cópia.

### 4. Financeiro
- Dados financeiros ficam no PC ou VPS (nunca em código ou prompt).
- Qualquer operação de escrita exige nível A4 (ver WIND_DECISIONS.md D-003) + 2FA.
- Chaves de corretoras/exchanges: sem permissão de saque por padrão.

### 5. Secreto
- Armazenado no OS secret store (Windows Credential Manager ou equivalente).
- Nunca em variáveis de ambiente visíveis em logs, nunca em código-fonte, nunca em mensagens ao modelo.
- Se detectado em saída de modelo ou código gerado: alerta imediato + bloqueio do envio.

---

## Checklist Guardian antes de chamada a modelo remoto
1. Classificar cada campo do contexto.
2. Se `personal` ou `confidential-client`: anonimizar ou remover.
3. Se `financial`: verificar aprovação A4.
4. Se `secret`: bloquear — nunca enviar.
5. Registrar `{ fields_sent, classes_present, anonymized_fields, timestamp, model_target }` no log de auditoria.
