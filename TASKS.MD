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
- [ ] **Funcionalidades extras complexas:** Fase 8 (Rate Limiting, Logs).

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

## 🚀 Fase 8: Funcionalidades Extras (Em Progresso)

### 8.1 Script CLI de Autenticação
> Permitir cadastro e login de usuários reais via linha de comando.

- [ ] **Criar `scripts/auth.py`:**
    - [ ] Comando `signup` - Cadastrar novo usuário (email/senha)
    - [ ] Comando `login` - Autenticar e retornar ID Token
    - [ ] Comando `refresh` - Renovar token expirado
    - [ ] Output formatado para uso direto com `curl`
- [ ] **Documentar no README.md**
- [ ] **Testes do script**

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

### 8.2 Rate Limiting por Usuário
> Limitar requisições por usuário para evitar abuso e demonstrar resiliência.

- [ ] **Implementar middleware de Rate Limiting:**
    - [ ] Usar Redis para armazenar contadores por `user_id`
    - [ ] Configuração: `RATE_LIMIT_REQUESTS` e `RATE_LIMIT_WINDOW` (segundos)
    - [ ] Algoritmo: Sliding Window Counter
    - [ ] Headers de resposta: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- [ ] **Retornar 429 Too Many Requests quando exceder limite**
- [ ] **Testes unitários do middleware**
- [ ] **Documentar comportamento**

**Configuração padrão:**
```python
RATE_LIMIT_REQUESTS = 100  # requests
RATE_LIMIT_WINDOW = 60     # segundos (1 minuto)
```

### 8.3 Logs Estruturados (JSON)
> Logs em formato JSON para melhor observabilidade em produção.

- [ ] **Configurar logging estruturado:**
    - [ ] Formato JSON em produção
    - [ ] Formato texto colorido em desenvolvimento
    - [ ] Campos: `timestamp`, `level`, `message`, `request_id`, `user_id`, `path`, `method`, `duration_ms`
- [ ] **Middleware de Request Logging:**
    - [ ] Log de entrada (request)
    - [ ] Log de saída (response com duration)
    - [ ] Correlation ID (`X-Request-ID`)
- [ ] **Integração com Cloud Logging (GCP)**
- [ ] **Testes de configuração de logging**

**Exemplo de log:**
```json
{
  "timestamp": "2026-02-02T19:30:00.000Z",
  "level": "INFO",
  "message": "Request completed",
  "request_id": "abc-123",
  "user_id": "user-001",
  "method": "GET",
  "path": "/people/1",
  "status_code": 200,
  "duration_ms": 45
}
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
| 02/02 | Script CLI Auth (`scripts/auth.py`) | 🔴 Alta |
| 02/02 | Rate Limiting por usuário | 🔴 Alta |
| 03/02 | Logs Estruturados (JSON) | 🟡 Média |
| 03/02 | Redeploy no Cloud Run | 🔴 Alta |
| 04/02 | Testes finais e documentação | 🟡 Média |
| 05/02 | **Entrega** | 🔴 Alta |

---

## 📈 Métricas do Projeto

| Métrica | Valor |
|---------|-------|
| **Testes** | 93 |
| **Cobertura** | 94% |
| **Endpoints** | 13 rotas |
| **Recursos SWAPI** | 6 |
| **Linhas de código** | ~2000 |
| **Documentação** | 5 arquivos MD |
