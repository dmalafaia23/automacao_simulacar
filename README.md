# Simulacao API (RPA Orchestrator)

API assíncrona para orquestrar robôs de simulação de financiamento veicular (Playwright), com persistência e rastreabilidade.

## Por que assíncrono
A automação leva ~4 minutos. Responder de forma síncrona bloquearia a requisição e poderia estourar timeouts de cliente/proxy. O modelo assíncrono permite:
- Retornar imediatamente um `simulation_id`.
- Processar em background via fila.
- Melhor escalabilidade e resiliência.
- Reprocessamento e auditoria por histórico.

## Stack
- Python 3.12+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- PostgreSQL
- Celery + Redis

## Estrutura
- `app/api` camada HTTP
- `app/schemas` validação e contratos
- `app/services` regras de negócio
- `app/repositories` acesso a dados
- `app/workers` tasks Celery
- `app/adapters` integração com robôs (mock hoje)
- `app/models` entidades do banco
- `app/core` settings/logs
- `migrations` SQL inicial

## Como subir
1. Copie `.env.example` para `.env` e ajuste se necessário.
2. Suba os serviços:

```bash
docker compose up --build
```

3. Rode a migração inicial:

```bash
docker compose exec -T db psql -U simulacao -d simulacao < migrations/001_init.sql
```

## Endpoints
- `POST /api/v1/simulations`
- `GET /api/v1/simulations/{simulation_id}`
- `GET /api/v1/simulations`
- `POST /api/v1/simulations/{simulation_id}/retry`
- `GET /health`

## Exemplo de criação
### C6 BANK
```bash
curl -X POST http://localhost:8000/api/v1/simulations \
  -H "Content-Type: application/json" \
  -d '{
    "bank": "c6bank",
    "input": {
      "cpf": "410.011.088-09",
      "celular": "(19) 99386-2056",
      "data_nascimento": "24/08/1993",
      "uf": "SP",
      "placa_veiculo": "TMJ6D14",
      "valor_financiamento": "R$ 139.900,00",
      "valor_entrada": "0,00",
      "possui_cnh": true,
      "retorno_estrelas": "6"
    },
    "idempotency_key": "cli-123"
  }'
```

### ITAU
```bash
curl -X POST http://localhost:8000/api/v1/simulations \
  -H "Content-Type: application/json" \
  -d '{
    "bank": "itau",
    "input": {
      "cpf": "410.011.088-09",
      "placa_veiculo": "TMJ6D14",
      "valor_financiamento": "139.900,00",
      "retorno_estrelas": "4"
    }
  }'
```

### Resposta
```json
{
  "simulation_id": "3a9e9c59-9b0f-4f2f-84d9-8d5a7d1d2e0b",
  "status": "PENDING"
}
```

## Consultar resultado
```bash
curl http://localhost:8000/api/v1/simulations/3a9e9c59-9b0f-4f2f-84d9-8d5a7d1d2e0b
```

### Resposta (exemplo)
```json
{
  "simulation_id": "3a9e9c59-9b0f-4f2f-84d9-8d5a7d1d2e0b",
  "bank": "c6bank",
  "status": "SUCCESS",
  "input": {
    "cpf": "410.011.088-09",
    "celular": "(19) 99386-2056",
    "data_nascimento": "24/08/1993",
    "uf": "SP",
    "placa_veiculo": "TMJ6D14",
    "valor_financiamento": "R$ 139.900,00",
    "valor_entrada": "0,00",
    "possui_cnh": true,
    "retorno_estrelas": "6"
  },
  "error_message": null,
  "created_at": "2026-03-12T12:00:00+00:00",
  "updated_at": "2026-03-12T12:00:05+00:00",
  "started_at": "2026-03-12T12:00:05+00:00",
  "finished_at": "2026-03-12T12:04:05+00:00",
  "result": {
    "raw_result": {
      "bank": "c6bank",
      "approved": true,
      "score_stars": 6,
      "simulation_value": "R$ 139.900,00",
      "down_payment": "0,00",
      "installments": [
        {"count": 36, "amount": "R$ 3.950,00"},
        {"count": 48, "amount": "R$ 3.120,00"}
      ]
    },
    "normalized_result": {
      "approved": true,
      "bank": "c6bank",
      "score_stars": 6,
      "simulation_value": "R$ 139.900,00",
      "down_payment": "0,00",
      "installments": [
        {"count": 36, "amount": "R$ 3.950,00"},
        {"count": 48, "amount": "R$ 3.120,00"}
      ],
      "observations": "Mocked response. Replace with real robot output."
    }
  }
}
```

## Onde plugar os robôs reais
- ITAU: `app/adapters/itau.py` no método `ItauSimulationExecutor.run`.
- C6 BANK: `app/adapters/c6bank.py` no método `C6BankSimulationExecutor.run`.

Substitua o retorno mockado pela chamada real do Playwright, mantendo o retorno `SimulationExecutionResult`.

## Logs e tratamento de erros
- Logs JSON via `python-json-logger`.
- Status possíveis: `RECEIVED`, `PENDING`, `RUNNING`, `SUCCESS`, `FAILED`, `TIMEOUT`, `CANCELLED`.
- Erros no worker atualizam `FAILED` e guardam `error_message`.
- Timeout usa `TIMEOUT` via time limit do Celery.

## Rastreabilidade
Campos disponíveis em `simulations`:
- `id`, `bank`, `input_payload`, `status`, `attempt_count`
- `error_message`, `correlation_id`, `idempotency_key`
- `created_at`, `updated_at`, `started_at`, `finished_at`

Tabela `simulation_events` mantém trilha de status.
Tabela `simulation_results` armazena retorno bruto e normalizado.

## Extensibilidade futura
- Webhook/callback: adicionar tabela de subscriptions e notificar após `SUCCESS/FAILED`.
- Novos bancos: criar novo executor e registrar no `ExecutorRegistry`.
- Reprocessamento: endpoint `/retry` já previsto.
- Auditoria: `simulation_events` + `correlation_id`.
