# 🚀 Roadmap de Implementação: Stellar Gateway

Este projeto segue a metodologia **TDD (Test Driven Development)** e mapeia diretamente os requisitos do Case Técnico.

**Prazo:** 05/02/2026 | **Última atualização:** 02/02/2026

---

## ✅ Critérios do desafio x Entregas

**Critérios de aceite**
- [x] **GCP (Cloud Run + API Gateway):** Fase 6 (OpenAPI + Deploy).
- [x] **Python como linguagem:** Base do projeto (Fases 1–7).
- [x] **Dados via SWAPI:** Fase 3 (SWAPI Client) + Fase 4 (Use Case).
- [x] **Endpoint(s) para consulta:** Fase 5 (Handler + `/me`) + Fase 4 (rota dinâmica genérica).
- [x] **Filtros por parâmetros:** Fase 4 (Mapeamento para `search`).

**Critérios de avaliação / extras**
- [x] **Boas práticas / Clean Architecture:** Fases 1–5.
- [x] **Autenticação:** Fase 2 + Fase 8 (CLI completo).
- [x] **Testes unitários:** Fase 7.
- [x] **Ordenação:** Fase 4 (Sorting).
- [x] **Dados correlacionados (enrichment):** Fase 4.
- [x] **Desenho de arquitetura:** Fase 1.
- [x] **Funcionalidades extras complexas:** Fase 8 (Auth CLI ✅, Rate Limiting ⏸️ adiado, Logs ✅).

---

## 🏗️ Fase 1: Fundação & Domínio ✅
- [x] Configurar Ambiente (Poetry, Docker, Linter).
- [x] Configuração Centralizada (`src/core/config.py`).
- [x] Definição de Arquitetura (`ARCHITECTURE.md`) **[EXTRA: Desenho Detalhado]**.
- [x] **TDD Domain:** Criar Model `Person` (com validação Pydantic).
- [x] **Generic Logic:** Garantir que a lógica suporte `planets`, `starships`, etc.

## 🔐 Fase 2: Segurança (Híbrida) ✅
- [x] Configurar Projeto Firebase (Console).
- [x] **Script:** Criar `scripts/get_token.py` **[CRITÉRIO: Auth]**.
- [x] **Implementação:** Criar dependency `get_current_user` (Fallback para testes locais).
- [x] **Teste:** Unitário do dependency mockando `firebase_admin`.

## 🔌 Fase 3: Adaptadores & Resiliência ✅
- [x] **SWAPI Client:**
    - [x] Implementar `tenacity` para Retry com Backoff Exponencial **[Resiliência]**.
    - [x] Tratamento de Timeout (Fail Fast).
- [x] **Redis Client:**
    - [x] Implementar Singleton Connection Pool.
    - [x] Teste de integração: Verificar se o cache está sendo gravado/lido corretamente.

## 🧠 Fase 4: Use Cases & Valor Agregado ✅
- [x] **Core Use Case:** Fluxo `GetResource` genérico.
- [x] **Paginação:** Repassar parâmetro `?page=` para a SWAPI **[CRITÉRIO: Listagem]**.
- [x] **Filtros:** Mapear `?name=Luke` para `?search=Luke` **[CRITÉRIO: Filtros]**.
- [x] **Ordenação (Sorting):**
    - [x] Implementar ordenação em memória (`?sort_by=name`) após o fetch **[EXTRA: Ordenação]**.
- [x] **Enrichment (Hidratação):**
    - [x] Detectar campos de URL (ex: `films`).
    - [x] `asyncio.gather` para buscar nomes dos filmes em paralelo **[EXTRA: Dados Correlacionados]**.

## ⚡ Fase 5: Entrypoint & Contrato da API ✅
- [x] **HTTP Handler:** Ler headers do Gateway (`X-Apigateway-Api-Userinfo`).
- [x] **Rota dinâmica:** Implementar `/<resource>/<id>` e `/<resource>/` (listagem).
- [x] **Endpoint `/me`:** Retornar dados do usuário.
- [x] **Error Handling:** Middleware para converter Exceptions em JSON RFC 7807.
- [x] **Contrato de filtros/ordenação:** Documentar `?search`, `?page`, `?sort_by` e campos permitidos por recurso.

## ☁️ Fase 6: Infraestrutura GCP ✅
- [x] **OpenAPI Spec:** Criar `openapi.yaml`.
    - [x] Configurar Security Definition (Firebase JWT).
    - [x] Documentar recursos dinâmicos (`/<resource>`) e parâmetros (`page`, `search`, `sort_by`).
- [x] **Deploy:** Cloud Run + API Gateway deployed and working.

## 🏁 Fase 7: Qualidade & Entrega ✅
- [x] Rodar bateria completa de testes (`poetry run pytest`) **[EXTRA: Testes Unitários]**.
- [x] Verificar cobertura (> 80%) - Atual: 94%.
- [x] Documentar endpoints e deploy no README.md.
- [x] Criar `GCP_SETUP_GUIDE.md` com tutorial completo.

---

## 🚀 Fase 8: Funcionalidades Extras ✅

### 8.1 Script CLI de Autenticação ✅
> Permitir cadastro e login de usuários reais via linha de comando.

- [x] **Criar `scripts/auth.py`:**
    - [x] Comando `signup` - Cadastrar novo usuário (email/senha)
    - [x] Comando `login` - Autenticar e retornar ID Token
    - [x] Comando `refresh` - Renovar token expirado
    - [x] Output formatado para uso direto com `curl`
- [x] **Documentar no README.md**
- [x] **Testes do script** (18 testes)

**Exemplo de uso:**
```bash
# Cadastrar
poetry run python scripts/auth.py signup --email user@test.com --password 123456

# Login
poetry run python scripts/auth.py login --email user@test.com --password 123456

# Usar token
TOKEN=$(poetry run python scripts/auth.py login -e user@test.com -p 123456 -q)
curl -H "Authorization: Bearer $TOKEN" https://stellar-gateway-xxx/people/1
```

### 8.2 Rate Limiting por Usuário ⏸️ (Adiado)
> Limitar requisições por usuário para evitar abuso e demonstrar resiliência.

**Status:** Investigado, mas não implementado devido a limitações do GCP API Gateway.

**Análise:**
O GCP API Gateway suporta rate limiting nativo, mas com restrições:
- Rate limiting **por usuário** (`1/min/{user}`) requer **API Keys** obrigatórias
- Com apenas Firebase JWT (OAuth), só suporta rate limiting **por projeto** (`1/min/{project}`)
- Adicionar API Keys mudaria a arquitetura de autenticação significativamente

**Decisão:**
Para este projeto, que já usa Firebase Authentication, adicionar API Keys criaria complexidade 
desnecessária. A proteção contra abuso fica a cargo de:
1. **Autenticação obrigatória** - Apenas usuários autenticados podem acessar
2. **Cloud Run auto-scaling** - Escala automaticamente conforme demanda
3. **SWAPI rate limiting** - A própria SWAPI limita requisições upstream

**Alternativa futura:**
Se rate limiting for crítico, implementar via código custom com Redis (Sliding Window Log)
ou migrar para outro API Gateway que suporte rate limiting por JWT claims.

### 8.3 Logs Estruturados (JSON) ✅
> Logs em formato JSON para melhor observabilidade em produção.

- [x] **Configurar logging estruturado:**
    - [x] Formato JSON em produção (`CloudRunJSONFormatter`)
    - [x] Formato texto colorido em desenvolvimento (`DevelopmentFormatter`)
    - [x] Campos: `timestamp`, `severity`, `message`, `request_id`, `user_id`, `httpRequest` (method, path, status, latency)
- [x] **Middleware de Request Logging:**
    - [x] Log de cada request com método, path, status e duração
    - [x] Correlation ID (`X-Request-ID`) - gerado automaticamente ou extraído do header
    - [x] Trace ID para correlação com Cloud Logging (`X-Cloud-Trace-Context`)
    - [x] Níveis de log apropriados (INFO para 2xx, WARNING para 4xx, ERROR para 5xx)
- [x] **Integração com Cloud Logging (GCP)**
    - [x] Campos especiais: `logging.googleapis.com/trace`, `logging.googleapis.com/sourceLocation`
    - [x] Captura automática via stdout (nativo do Cloud Run)
- [x] **Logging de erros nos exception handlers**
- [x] **Logs de lifecycle da aplicação (startup/shutdown)**
- [x] **Testes de configuração de logging (33 testes)**

**Arquivos criados/modificados:**
- `src/core/logging.py` - Formatters JSON e Development, setup_logging()
- `src/api/middleware.py` - RequestLoggingMiddleware
- `src/main.py` - Integração do middleware e logs de lifecycle
- `src/api/errors.py` - Logging nos exception handlers
- `src/core/config.py` - Adicionado GCP_PROJECT
- `tests/unit/test_logging.py` - 20 testes
- `tests/unit/test_middleware.py` - 13 testes

**Exemplo de log (produção):**
```json
{
  "severity": "INFO",
  "message": "GET /people/1 - 200",
  "timestamp": "2026-02-03T10:30:00.000000+00:00",
  "logger": "api.middleware",
  "logging.googleapis.com/trace": "projects/stellar-gateway-10135/traces/abc123",
  "logging.googleapis.com/sourceLocation": {
    "file": "middleware.py",
    "line": "65",
    "function": "dispatch"
  },
  "httpRequest": {
    "requestMethod": "GET",
    "requestUrl": "/people/1",
    "status": 200,
    "latency": "45.23ms"
  },
  "request_id": "abc12345",
  "user_id": "user-001"
}
```

**Exemplo de log (desenvolvimento):**
```
10:30:00 [INFO    ] GET /people/1 - 200 | method=GET path=/people/1 status=200 latency=45.23ms
```

---

## 📊 Recursos Deployados

| Recurso | URL/Identificador |
|---------|-------------------|
| **API Gateway** | `https://stellar-gateway-23t3upfn.uc.gateway.dev` |
| **Cloud Run** | `https://stellar-gateway-165018665795.us-central1.run.app` |
| **GCP Project** | `stellar-gateway-10135` |
| **Region** | `us-central1` |
| **Redis (Memorystore)** | `10.160.194.123:6379` |

---

## 📅 Cronograma Restante

| Data | Tarefa | Prioridade |
|------|--------|------------|
| 02/02 | ~~Script CLI Auth (`scripts/auth.py`)~~ | ✅ Concluído |
| 02/02 | ~~Rate Limiting por usuário~~ | ⏸️ Adiado (limitação API Gateway) |
| 02/02 | ~~Logs Estruturados (JSON)~~ | ✅ Concluído |
| 02/02 | ~~Redeploy no Cloud Run~~ | ✅ Concluído |
| 02/02 | ~~Testes finais e documentação~~ | ✅ Concluído |
| 05/02 | **Entrega** | 🔴 Alta |

---

## 📈 Métricas do Projeto

| Métrica | Valor |
|---------|-------|
| **Testes** | 144 |
| **Cobertura** | 95% |
| **Endpoints** | 13 rotas |
| **Recursos SWAPI** | 6 |
| **Linhas de código** | ~2800 |
| **Documentação** | 6 arquivos MD |
