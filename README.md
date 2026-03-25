# Automacao Simulacar API

API para orquestrar simulacoes de financiamento em multiplos bancos de forma assincrona.

Hoje a API suporta:
- Itau
- C6 Bank

O fluxo e baseado em processamento por `job_id`:
- o cliente envia uma requisicao para iniciar a simulacao
- a API responde imediatamente com um identificador
- o processamento roda em background
- uma nova consulta retorna o status e os resultados por banco

## Versao

Versao atual da API: `1.1.0`

## Requisitos

- Python 3
- Ambiente virtual `.venv`
- Dependencias do `requirements.txt`
- Navegador `chromium` instalado via Playwright

## Instalacao

Criar ambiente virtual:

```bash
python3 -m venv .venv
```

Instalar dependencias:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

Instalar o navegador do Playwright:

```bash
.venv/bin/python -m playwright install chromium
```

## Executando a API

Subir o servidor local:

```bash
.venv/bin/uvicorn app.main:app --reload
```

Base URL local:

```text
http://127.0.0.1:8000
```

Documentacao interativa:

```text
http://127.0.0.1:8000/docs
```

## Fluxo da API

1. Chamar `POST /simulacoes`
2. Receber um `id` de processamento
3. Consultar `GET /simulacoes/{id}` ate o status final
4. Ler os resultados retornados por banco

## Endpoints

### GET `/health`

Verifica se a API esta ativa e retorna versao e horario atual do servidor.

Exemplo:

```bash
curl http://127.0.0.1:8000/health
```

Resposta:

```json
{
  "status": "ok",
  "version": "1.1.0",
  "current_time": "2026-03-25T20:01:36.377742-03:00",
  "timezone": "-03"
}
```

### POST `/simulacoes`

Cria um novo processamento de simulacao.

Regra:
- informe pelo menos um banco
- cada banco recebe seu proprio bloco de `config` e `client_data`
- o campo `enabled` permite ligar ou desligar um banco no payload

Exemplo:

```bash
curl -X POST http://127.0.0.1:8000/simulacoes \
  -H "Content-Type: application/json" \
  -d '{
    "itau": {
      "enabled": true,
      "config": {
        "base_url": "https://www.credlineitau.com.br/simulator",
        "email": "pravoceveiculos@icloud.com",
        "senha": "Veiculos$2025",
        "headless": false,
        "timeout_ms": 30000
      },
      "client_data": {
        "cpf": "410.011.088-09",
        "placa_veiculo": "TMJ6D14",
        "valor_financiamento": "139.900,00",
        "retorno_estrelas": "4"
      }
    },
    "c6bank": {
      "enabled": true,
      "config": {
        "base_url": "https://c6auto.com.br/originacaolojista/login",
        "email": "41001108809",
        "senha": "Carro$2025",
        "headless": false,
        "timeout_ms": 30000
      },
      "client_data": {
        "cpf": "410.011.088-09",
        "celular": "(19) 99386-2056",
        "data_nascimento": "24/08/1993",
        "uf": "SP",
        "placa_veiculo": "TMJ6D14",
        "valor_financiamento": "R$ 139.900,00",
        "valor_entrada": "0,00",
        "possui_cnh": true,
        "retorno_estrelas": "6"
      }
    }
  }'
```

Resposta:

```json
{
  "id": "9d5d5e4e-7ec8-4f24-a9c6-5c1ad2f9f1d0",
  "status": "pending"
}
```

### GET `/simulacoes/{id}`

Consulta o status de um processamento e retorna os resultados disponiveis.

Exemplo:

```bash
curl http://127.0.0.1:8000/simulacoes/9d5d5e4e-7ec8-4f24-a9c6-5c1ad2f9f1d0
```

Resposta enquanto processa:

```json
{
  "id": "9d5d5e4e-7ec8-4f24-a9c6-5c1ad2f9f1d0",
  "status": "processing",
  "created_at": "2026-03-25T20:10:00.000000+00:00",
  "started_at": "2026-03-25T20:10:01.000000+00:00",
  "finished_at": null,
  "banks": {
    "itau": {
      "bank": "itau",
      "status": "processing",
      "started_at": "2026-03-25T20:10:01.000000+00:00",
      "finished_at": null,
      "result": null,
      "error": null
    },
    "c6bank": {
      "bank": "c6bank",
      "status": "completed",
      "started_at": "2026-03-25T20:10:01.000000+00:00",
      "finished_at": "2026-03-25T20:10:40.000000+00:00",
      "result": [],
      "error": null
    }
  }
}
```

Resposta final com erro parcial:

```json
{
  "id": "9d5d5e4e-7ec8-4f24-a9c6-5c1ad2f9f1d0",
  "status": "completed_with_errors",
  "created_at": "2026-03-25T20:10:00.000000+00:00",
  "started_at": "2026-03-25T20:10:01.000000+00:00",
  "finished_at": "2026-03-25T20:11:00.000000+00:00",
  "banks": {
    "itau": {
      "bank": "itau",
      "status": "failed",
      "started_at": "2026-03-25T20:10:01.000000+00:00",
      "finished_at": "2026-03-25T20:10:35.000000+00:00",
      "result": null,
      "error": "timeout no login"
    },
    "c6bank": {
      "bank": "c6bank",
      "status": "completed",
      "started_at": "2026-03-25T20:10:01.000000+00:00",
      "finished_at": "2026-03-25T20:10:40.000000+00:00",
      "result": [],
      "error": null
    }
  }
}
```

## Status possiveis

Status do processamento:
- `pending`
- `processing`
- `completed`
- `completed_with_errors`
- `failed`

Status por banco:
- `pending`
- `processing`
- `completed`
- `failed`

## Estrutura atual

- [`app/main.py`](/Users/luizcarrijo/Fontes/LRCTech/automacao_simulacar/app/main.py): endpoints HTTP
- [`app/orchestrator.py`](/Users/luizcarrijo/Fontes/LRCTech/automacao_simulacar/app/orchestrator.py): cria jobs e executa bancos em paralelo
- [`app/store.py`](/Users/luizcarrijo/Fontes/LRCTech/automacao_simulacar/app/store.py): persistencia temporaria em memoria
- [`app/schemas.py`](/Users/luizcarrijo/Fontes/LRCTech/automacao_simulacar/app/schemas.py): contratos de entrada e saida
- [`app/banks.py`](/Users/luizcarrijo/Fontes/LRCTech/automacao_simulacar/app/banks.py): adaptadores dos bancos

## Observacoes importantes

- A API atual nao persiste em banco de dados ainda
- os resultados ficam em memoria enquanto a aplicacao estiver ativa
- o proximo passo planejado e integrar com Supabase
- a execucao real das simulacoes depende do Playwright e do navegador instalado

## Proximos passos sugeridos

- persistir jobs e resultados no Supabase
- adicionar autenticacao da API
- adicionar endpoint de prontidao, como `GET /ready`
- adicionar logs estruturados por `job_id`
