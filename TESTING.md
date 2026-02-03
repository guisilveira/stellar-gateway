# 🧪 Guia de Testes - Stellar Gateway

Este documento descreve como testar o projeto localmente, tanto com testes automatizados quanto com a API rodando.

---

## 📋 Índice

1. [Pré-requisitos](#pré-requisitos)
2. [Testes Automatizados (Pytest)](#1-testes-automatizados-pytest)
3. [Docker Compose Completo](#2-docker-compose-completo) ⭐ **Recomendado**
4. [API Local + Redis Docker](#3-api-local--redis-docker)
5. [Troubleshooting](#4-troubleshooting)

---

## 🎯 Qual Método Usar?

| Cenário | Método | Comando |
|---------|--------|---------|
| **Validar que tudo funciona** | Docker Compose | `docker compose up --build` |
| **Desenvolvimento ativo** | API Local + Redis | `poetry run uvicorn ...` |
| **CI/CD ou testes rápidos** | Pytest | `poetry run pytest` |

> **Dica:** Se você só quer testar a aplicação funcionando, use o **Docker Compose**. É o método mais simples e completo.

---

## Pré-requisitos

| Ferramenta | Versão Mínima | Verificar |
|------------|---------------|-----------|
| Python | 3.10+ | `python3 --version` |
| Poetry | 2.0+ | `poetry --version` |
| Docker | 20.0+ | `docker --version` |
| Docker Compose | 2.0+ | `docker compose version` |

---

## 1. Testes Automatizados (Pytest)

Os testes automatizados usam **mocks** e **fakeredis**, então **não precisam de serviços externos** rodando.

### 1.1 Instalar Dependências

```bash
# Instala todas as dependências (incluindo dev)
poetry install
```

### 1.2 Executar Todos os Testes

```bash
# Usando Poetry
poetry run pytest

# Ou usando Makefile
make test
```

**Saída esperada:**
```
========================= test session starts ==========================
collected 144 items

tests/integration/test_api_routes.py ............                [  8%]
tests/integration/test_redis_adapter.py ...............          [ 18%]
tests/integration/test_swapi_adapter.py .............            [ 27%]
tests/unit/test_auth_cli.py ..................                   [ 40%]
tests/unit/test_domain_models.py .......                         [ 45%]
tests/unit/test_get_person_use_case.py ..                        [ 46%]
tests/unit/test_get_resource_use_case.py ..............          [ 56%]
tests/unit/test_list_resources_use_case.py ....................  [ 70%]
tests/unit/test_logging.py ....................                  [ 84%]
tests/unit/test_middleware.py .............                      [ 93%]
tests/unit/test_sanity.py .                                      [ 93%]
tests/unit/test_security.py .........                            [100%]
========================= 144 passed in 4.52s ===========================
```

### 1.3 Executar Testes Específicos

```bash
# Apenas testes unitários
poetry run pytest tests/unit/

# Apenas testes de integração
poetry run pytest tests/integration/

# Um arquivo específico
poetry run pytest tests/unit/test_security.py

# Um teste específico
poetry run pytest tests/unit/test_security.py::TestVerifyToken::test_verify_token_accepts_mock_in_dev_environment
```

### 1.4 Cobertura de Código

```bash
# Rodar com relatório de cobertura (já configurado no pyproject.toml)
poetry run pytest

# Gerar relatório HTML detalhado
poetry run pytest --cov-report=html
# Abrir: htmlcov/index.html
```

### 1.5 Linting e Type Check

```bash
# Verificar estilo de código (Ruff)
make lint
# ou: poetry run ruff check .

# Verificar tipos (MyPy)
make type-check
# ou: poetry run mypy src

# Formatar código automaticamente
make format
# ou: poetry run ruff format .
```

---

## 2. Docker Compose Completo

> **⭐ Método recomendado para testar a aplicação de ponta a ponta.**
> 
> Sobe tudo containerizado (API + Redis) com um único comando. Ideal para:
> - Validar que a aplicação funciona corretamente
> - Testar antes de fazer deploy
> - Demonstrar a aplicação para outras pessoas

### 2.1 Build e Inicialização

```bash
# Build e start (mostra logs no terminal)
docker compose up --build

# Ou em background (detached)
docker compose up --build -d
```

### 2.2 Verificar Status

```bash
# Ver containers rodando
docker compose ps

# Ver logs em tempo real
docker compose logs -f

# Ver logs de um serviço específico
docker compose logs -f app
docker compose logs -f redis
```

### 2.3 Testar Endpoints

```bash
# Health check (sem autenticação)
curl http://localhost:8000/health
# Esperado: {"status":"healthy"}

# Documentação Swagger
# Abrir no browser: http://localhost:8000/docs

# Buscar pessoa por ID
curl -H "Authorization: Bearer mock-token" http://localhost:8000/people/1

# Listar pessoas
curl -H "Authorization: Bearer mock-token" "http://localhost:8000/people"

# Buscar com filtro
curl -H "Authorization: Bearer mock-token" "http://localhost:8000/people?search=Luke"

# Outros recursos: planets, starships, films, species, vehicles
curl -H "Authorization: Bearer mock-token" http://localhost:8000/planets/1
```

### 2.4 Acessar Shell do Container

```bash
# Shell da aplicação
docker compose exec app sh

# Shell do Redis (para verificar cache)
docker compose exec redis redis-cli
KEYS *
```

### 2.5 Rebuild após Mudanças no Código

```bash
# Rebuild completo
docker compose up --build

# Forçar rebuild sem cache (se tiver problemas)
docker compose build --no-cache && docker compose up
```

### 2.6 Cleanup

```bash
# Parar containers
docker compose down

# Parar e remover volumes (limpa dados do Redis)
docker compose down -v

# Remover imagens também
docker compose down --rmi local
```

---

## 3. API Local + Redis Docker

> **Use este método quando estiver desenvolvendo ativamente** e quiser:
> - **Hot-reload** (código atualiza automaticamente sem reiniciar)
> - **Debug com breakpoints** (IDE integrada)
> - **Logs detalhados** no terminal
> - **Editar e testar rapidamente**
>
> Se você só quer testar a aplicação funcionando, use o [Docker Compose Completo](#2-docker-compose-completo).

Este método roda a API diretamente na sua máquina, com apenas o Redis em container.

### 3.1 Configurar Ambiente

O arquivo `.env` já deve estar configurado com valores de desenvolvimento:

```env
# Ambiente (dev permite mock-token para autenticação)
ENVIRONMENT=dev

# Redis (container local - usar localhost pois a API roda fora do Docker)
REDIS_HOST=localhost
REDIS_PORT=6379

# SWAPI
SWAPI_BASE_URL=https://swapi.dev/api
```

### 3.2 Subir o Redis

```bash
# Usando docker-compose (recomendado - apenas o serviço redis)
docker compose up redis -d

# Verificar se está rodando
docker compose ps
```

### 3.3 Instalar Dependências

```bash
poetry install
```

### 3.4 Iniciar a API

```bash
# Com hot-reload (recomendado para desenvolvimento)
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Sem hot-reload
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

**Saída esperada:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345]
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 3.5 Testar Endpoints

Os mesmos comandos da seção Docker Compose funcionam:

```bash
# Health check
curl http://localhost:8000/health

# Buscar pessoa
curl -H "Authorization: Bearer mock-token" http://localhost:8000/people/1

# Swagger
# Abrir: http://localhost:8000/docs
```

### 3.6 Verificar Cache Redis

```bash
# Conectar ao Redis CLI
docker compose exec redis redis-cli

# Dentro do Redis CLI:
KEYS *              # Listar todas as chaves
GET swapi:people:1  # Ver valor de uma chave
TTL swapi:people:1  # Ver TTL de uma chave
EXIT                # Sair
```

### 3.7 Cleanup

```bash
# Parar a API: CTRL+C no terminal

# Parar o Redis
docker compose down
```

## 4. Troubleshooting

### Problemas Comuns

| Problema | Causa | Solução |
|----------|-------|---------|
| `Connection refused` ao conectar no Redis | Redis não está rodando | `docker compose up redis -d` |
| `ModuleNotFoundError: No module named 'xxx'` | Dependências não instaladas | `poetry install` |
| `401 Unauthorized` | Token inválido ou ausente | Use `Authorization: Bearer mock-token` em ambiente dev |
| `Firebase error` em ambiente dev | Não necessário em dev | Confirme `ENVIRONMENT=dev` no `.env` |
| Porta 8000 em uso | Outro processo usando a porta | `lsof -i :8000` para ver o processo |
| Build do Docker falha | Cache corrompido | `docker compose build --no-cache` |
| Variáveis de ambiente não carregadas | `.env` não existe ou vazio | Copiar de `.env.example` e preencher |

### Verificar Configuração

```bash
# Ver variáveis de ambiente carregadas (em Python)
poetry run python -c "from src.core.config import settings; print(settings.model_dump())"
```

### Limpar Cache e Recomeçar

```bash
# Limpar caches Python
make clean

# Limpar Docker completamente
docker compose down -v --rmi local
docker system prune -f
```

### Logs Detalhados

```bash
# Aumentar verbosidade do pytest
poetry run pytest -vvv

# Ver logs do Uvicorn em debug
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000 --log-level debug
```

---

## 📚 Referência Rápida

### Comandos Makefile

| Comando | Descrição |
|---------|-----------|
| `make install` | Instala dependências |
| `make test` | Roda pytest |
| `make lint` | Verifica estilo (Ruff) |
| `make format` | Formata código |
| `make type-check` | Verifica tipos (MyPy) |
| `make up` | Sobe docker-compose |
| `make down` | Para docker-compose |
| `make clean` | Limpa caches |

### Endpoints da API

| Método | Rota | Descrição | Auth |
|--------|------|-----------|------|
| GET | `/health` | Health check | ❌ |
| GET | `/docs` | Swagger UI | ❌ |
| GET | `/me` | Info do usuário | ✅ |
| GET | `/{resource}` | Lista recursos | ✅ |
| GET | `/{resource}/{id}` | Busca por ID | ✅ |

### Recursos SWAPI Suportados

`people`, `planets`, `films`, `species`, `vehicles`, `starships`

### Parâmetros de Query

| Parâmetro | Exemplo | Descrição |
|-----------|---------|-----------|
| `page` | `?page=2` | Paginação |
| `search` | `?search=Luke` | Busca textual |
| `sort_by` | `?sort_by=name` | Campo para ordenar |
| `sort_order` | `?sort_order=desc` | Direção (asc/desc) |
| `enrich` | `?enrich=false` | Desabilita hidratação |

---

## 5. Testando em Produção (GCP)

> **Ambiente de produção** - Testes contra a API deployada no Google Cloud Run com API Gateway.

### 5.1 URLs de Produção

| Endpoint | URL | Uso |
|----------|-----|-----|
| **API Gateway** | `https://stellar-gateway-23t3upfn.uc.gateway.dev` | Produção (com autenticação Firebase) |
| **Cloud Run** (Direto) | `https://stellar-gateway-165018665795.us-central1.run.app` | Acesso direto (bypass API Gateway) |

> ⚠️ **Importante:** Em produção, o `mock-token` NÃO funciona. Você precisa de um token Firebase real.

### 5.2 Gerando Token Firebase Real

#### Opção 1: Usando o Script `get_token.py` (Recomendado)

Este script usa o Firebase Admin SDK para gerar um token válido:

```bash
# Gerar token para um usuário de teste
poetry run python scripts/get_token.py --uid test-user-001
```

**Pré-requisitos:**
- Arquivo `serviceAccountKey.json` na raiz do projeto
- Variável `FIREBASE_WEB_API_KEY` configurada no `.env`

**Saída esperada:**
```
[1/3] Initializing Firebase Admin SDK...
      Firebase initialized successfully.
[2/3] Creating Custom Token for UID: test-user-001...
      Custom Token created (length: 1234 chars)
[3/3] Exchanging Custom Token for ID Token...

============================================================
SUCCESS! Firebase ID Token Generated
============================================================

Expires in: 3600 seconds

ID Token:
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Opção 2: Firebase Auth REST API (Sem SDK)

Se você tem um usuário criado no Firebase Console:

```bash
# Login com email/senha (necessita FIREBASE_WEB_API_KEY)
curl -X POST "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123","returnSecureToken":true}'
```

### 5.3 Testando Endpoints em Produção

```bash
# Salvar token em variável (substitua pelo seu token real)
export TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."

# Health check (sem autenticação)
curl https://stellar-gateway-23t3upfn.uc.gateway.dev/health
# Esperado: {"status":"healthy"}

# Informações do usuário autenticado
curl -H "Authorization: Bearer $TOKEN" \
  https://stellar-gateway-23t3upfn.uc.gateway.dev/me

# Buscar pessoa por ID
curl -H "Authorization: Bearer $TOKEN" \
  https://stellar-gateway-23t3upfn.uc.gateway.dev/people/1

# Listar pessoas com paginação
curl -H "Authorization: Bearer $TOKEN" \
  "https://stellar-gateway-23t3upfn.uc.gateway.dev/people?page=1"

# Buscar com filtro
curl -H "Authorization: Bearer $TOKEN" \
  "https://stellar-gateway-23t3upfn.uc.gateway.dev/people?search=Luke"

# Ordenação
curl -H "Authorization: Bearer $TOKEN" \
  "https://stellar-gateway-23t3upfn.uc.gateway.dev/people?sort_by=name&sort_order=desc"

# Desabilitar enrichment (retorna URLs ao invés de nomes)
curl -H "Authorization: Bearer $TOKEN" \
  "https://stellar-gateway-23t3upfn.uc.gateway.dev/people/1?enrich=false"
```

### 5.4 Verificando Logs no GCP

O Stellar Gateway usa **logs estruturados em formato JSON**, integrados com o Cloud Logging do GCP.

```bash
# Logs do Cloud Run (formato simplificado)
gcloud run services logs read stellar-gateway --region=us-central1 --limit=20

# Logs estruturados no Cloud Logging (JSON completo)
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="stellar-gateway"' \
  --project=stellar-gateway-10135 \
  --limit=10 \
  --format=json

# Filtrar apenas logs de requests HTTP (middleware)
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="stellar-gateway" AND jsonPayload.logger="api.middleware"' \
  --project=stellar-gateway-10135 \
  --limit=10 \
  --format='table(timestamp,severity,jsonPayload.message,jsonPayload.httpRequest.status)'

# Logs em tempo real (streaming)
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=stellar-gateway"

# Filtrar por erros (WARNING = 4xx, ERROR = 5xx)
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="stellar-gateway" AND severity>=WARNING' \
  --project=stellar-gateway-10135 \
  --limit=20

# Logs do API Gateway
gcloud logging read "resource.type=apigateway.googleapis.com/Gateway" \
  --limit=50
```

**Exemplo de log estruturado (produção):**
```json
{
  "severity": "INFO",
  "message": "GET /people/1 - 200",
  "timestamp": "2026-02-02T23:53:09.099706+00:00",
  "logger": "api.middleware",
  "logging.googleapis.com/trace": "projects/stellar-gateway-10135/traces/abc123",
  "httpRequest": {
    "requestMethod": "GET",
    "requestUrl": "/people/1",
    "status": 200,
    "latency": "45.23ms"
  },
  "request_id": "8d6cb3df-224b-4bb1-98d9-703887408317",
  "user_id": "test-user"
}
```

**Níveis de severidade:**
- `INFO` → Requests bem-sucedidos (2xx)
- `WARNING` → Erros do cliente (4xx)
- `ERROR` → Erros do servidor (5xx)

### 5.5 Verificando Métricas

```bash
# Status do Cloud Run
gcloud run services describe stellar-gateway \
  --region=us-central1 \
  --format="table(status.url,status.traffic)"

# Revisões ativas
gcloud run revisions list \
  --service=stellar-gateway \
  --region=us-central1
```

### 5.6 Troubleshooting Produção

| Problema | Causa Provável | Solução |
|----------|----------------|---------|
| `401 Unauthorized` | Token inválido ou expirado | Gerar novo token com `scripts/get_token.py` |
| `403 Forbidden` | API Gateway rejeitando token | Verificar se o token é do projeto correto |
| `502 Bad Gateway` | Cloud Run não respondendo | Verificar logs: `gcloud logging read ...` |
| `504 Gateway Timeout` | Redis ou SWAPI lento | Verificar conectividade do VPC Connector |
| `Connection refused` ao Redis | VPC Connector mal configurado | Verificar `gcloud run services describe` |
| Token expira rápido | Tokens Firebase duram 1 hora | Use `refresh_token` para renovar |

### 5.7 Testando Conectividade Redis (Produção)

Se suspeitar de problemas com Redis:

```bash
# Verificar se o serviço está usando o VPC Connector
gcloud run services describe stellar-gateway \
  --region=us-central1 \
  --format="value(spec.template.spec.containers[0].env,spec.template.metadata.annotations)"

# O output deve mostrar:
# - REDIS_HOST=10.160.194.123
# - run.googleapis.com/vpc-access-connector=stellar-redis-connector
```
