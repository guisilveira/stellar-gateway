# 🏛️ Stellar Gateway - System Architecture Document

**Versão:** 1.2.0 (Production Ready)
**Data:** 02/02/2026

---

## 1. Visão Geral (Overview)

O **Stellar Gateway** é um middleware serverless de alta performance e segurança, projetado para atuar como um *Proxy Inteligente* sobre a API pública do Star Wars (SWAPI).

### 1.1 O Problema
A SWAPI é uma excelente fonte de dados, mas apresenta desafios para aplicações profissionais:
* **Latência e Confiabilidade:** Respostas lentas e sem SLA garantido.
* **Over-fetching/Under-fetching:** Dados relacionais (ex: filmes de um personagem) são retornados apenas como URLs, exigindo múltiplas requisições do frontend.
* **Segurança:** A API é pública, sem controle de quem acessa.

### 1.2 A Solução
Uma arquitetura em nuvem no **Google Cloud Platform (GCP)** que oferece:
1.  **Segurança em Camadas:** Autenticação via **Firebase** gerenciada pelo **GCP API Gateway** (Offloading).
2.  **Performance Extrema:** Estratégia de Cache-Aside com **Redis**.
3.  **Data Enrichment:** O backend "hidrata" dados automaticamente (busca nomes de filmes em paralelo) para entregar um JSON pronto ao frontend.

---

## 2. System Design (Infraestrutura)

A solução utiliza uma topologia **Serverless** moderna, onde a validação de segurança é delegada para a infraestrutura (Gateway), deixando a computação (Cloud Run) focada apenas em regras de negócio.

```mermaid
flowchart LR
    Client[📱 Client / Frontend] -->|HTTPS + JWT| Gateway[🛡️ GCP API Gateway]
    
    subgraph "Google Cloud Platform"
        Gateway -.->|1. Valida Token Auto| Firebase[🔥 Firebase Auth]
        
        Gateway -->|2. Token OK + User Headers| CloudRun[⚡ Cloud Run]
        Gateway --x|Token Inválido 401| Client
        
        CloudRun <-->|3. Cache Hit Miss| Redis[(🧠 Redis)]
        CloudRun -->|4. Fetch Data| SWAPI[☁️ SWAPI Externa]
    end

    style Gateway fill:#00C853,stroke:#333,stroke-width:2px,color:white
    style CloudRun fill:#4285F4,stroke:#333,stroke-width:2px,color:white
    style Firebase fill:#FFCA28,stroke:#333,stroke-width:2px,color:black
    style Redis fill:#D8342F,stroke:#333,stroke-width:2px,color:white
```
### 2.1 Componentes da Arquitetura
* **GCP API Gateway:** Ponto de entrada único. Responsável por roteamento e **Autenticação (Gatekeeper)**. Ele rejeita requisições inválidas antes que elas gerem custo computacional.
* **Google Cloud Run:** Executa a aplicação FastAPI (Python). Recebe requisições já autenticadas. Escala automaticamente de 0 a N instâncias.
* **Redis (Memorystore):** Cache de baixa latência. Utiliza conexão persistente (*Singleton Pool*) para suportar alta concorrência.
* **Firebase Auth:** Provedor de Identidade (IdP). Gerencia usuários e tokens OAuth (Google/Email).

---

## 3. Arquitetura de Software (Clean Architecture)

O microsserviço Python segue estritamente a **Arquitetura Hexagonal (Ports & Adapters)** para desacoplar a lógica de negócio das ferramentas externas.

### 3.1 Diagrama de Camadas

```mermaid
graph TD
    subgraph "Drivers External Interface"
        Main[main.py / FastAPI Handler]
    end

    subgraph "Adapters Interface Impl"
        RedisClient[Redis Adapter]
        SwapiClient[Http Adapter]
    end

    subgraph "Application Use Cases"
        GetResource[Get Resource UseCase]
        EnrichData[Enrich Data Logic]
    end

    subgraph "Domain Core"
        Models[Pydantic Models: Person, Film]
    end

    Main --> GetResource
    GetResource --> Models
    GetResource --> RedisClient
    GetResource --> SwapiClient
```

### 3.2 Segurança (Estratégia Híbrida)

A segurança adota uma abordagem de Defesa em Profundidade:

* **Produção (GCP API Gateway):** É a barreira principal. Rejeita tokens inválidos antes de invocar o Cloud Run (economia de custo).
* **Desenvolvimento/Aplicação (Python Dependency):** Mantemos um dependency `get_current_user` no código.
    * **Motivo 1 (Dev):** Permite rodar e testar a API localmente (`uvicorn`) sem precisar subir um API Gateway na nuvem a cada mudança.
    * **Motivo 2 (Prod):** Atua como segunda camada de validação caso a configuração do Gateway falhe ou seja contornada acidentalmente (rotas públicas expostas).

### 3.3 Responsabilidades
| Camada | Diretório | Função |
| :--- | :--- | :--- |
| **Domain** | `src/domain` | Regras Universais. Define *como* um dado deve ser (`Person`). Ignora banco de dados e APIs. |
| **Use Cases** | `src/use_cases` | Orquestração. Define o fluxo: "Busque no Cache -> Se falhar, busque na API -> Enriqueça -> Salve". |
| **Adapters** | `src/adapters` | Tradutores. Sabem falar com o Redis (`set/get`) e com a SWAPI (`httpx`). |
| **Drivers** | `src/main.py` | Entrada. Lê headers injetados pelo Gateway, decodifica usuário e chama o Use Case. |

---

## 4. Fluxos de Dados (Sequence Diagrams)

### 4.1 Fluxo de Autenticação (Via Gateway)
Demonstra como o código Python é protegido pela infraestrutura.

```mermaid
sequenceDiagram
    participant User
    participant Gateway as GCP API Gateway
    participant Firebase
    participant CloudRun as Cloud Run

    User->>Gateway: GET /people/1 (Bearer JWT)
    Gateway->>Firebase: Valida Assinatura JWT
    
    alt Token Inválido
        Firebase-->>Gateway: Invalid
        Gateway-->>User: 401 Unauthorized (Fim)
    else Token Válido
        Firebase-->>Gateway: OK (User Data)
        Gateway->>CloudRun: Forward Request + Header 'X-User-Info'
        CloudRun->>CloudRun: Decodifica Header
        CloudRun-->>User: 200 OK
    end
```

### 4.2 Fluxo de Busca e Enriquecimento (Data Enrichment)
Demonstra a estratégia de performance para resolver o problema de "N+1 requests".

```mermaid
sequenceDiagram
    participant CloudRun as Use Case
    participant Redis
    participant SWAPI

    CloudRun->>Redis: GET swapi:people:1
    
    alt Cache HIT 🟢
        Redis-->>CloudRun: JSON Completo (Person + Nomes dos Filmes)
    else Cache MISS 🔴
        Redis-->>CloudRun: None
        CloudRun->>SWAPI: GET /people/1
        SWAPI-->>CloudRun: JSON Raw (apenas URLs dos filmes)
        
        par Async Fetch Enrichment
            CloudRun->>SWAPI: GET /films/1
            CloudRun->>SWAPI: GET /films/2
        end
        
        CloudRun->>CloudRun: Merge dos Nomes dos Filmes no Modelo
        CloudRun->>Redis: SET swapi:people:1 (TTL 5min)
    end
```
## 5. Decisões de Arquitetura (ADRs)

### ADR 001: API Gateway como Guardião
* **Decisão:** Mover a validação de JWT do código Python para o GCP API Gateway.
* **Motivo:** Redução de custos (evita *Cold Starts* em chamadas não autorizadas) e desacoplamento de responsabilidade. O código foca em negócio, a infra foca em segurança.

### ADR 002: Cache-Aside com TTL Fixo
* **Decisão:** Cachear respostas da SWAPI por 5 minutos.
* **Motivo:** Dados de Star Wars são praticamente estáticos. O padrão Cache-Aside garante que o sistema se cure sozinho (self-healing) se o cache for limpo.

### ADR 003: Tratamento de Filtros (Smart Proxy)
* **Decisão:** Mapear filtros de domínio (`name`, `model`) para o parâmetro `search` da SWAPI. Rejeitar filtros não suportados (`eye_color`) com **400 Bad Request**.
* **Motivo:** Evitar a complexidade e lentidão de baixar todos os dados para filtrar em memória.

---

## 6. Especificação da API

**Base URL (Produção):** `https://stellar-gateway-23t3upfn.uc.gateway.dev`
**Base URL (Cloud Run Direto):** `https://stellar-gateway-165018665795.us-central1.run.app`

### Endpoints Principais

| Método | Rota | Descrição | Feature |
| :--- | :--- | :--- | :--- |
| `GET` | `/{resource}/{id}` | Busca recurso por ID | **Enrichment:** Hidrata campos correlacionados (ex.: filmes). |
| `GET` | `/{resource}/` | Lista paginada de recursos | **Search/Sorting:** Suporta filtros e ordenação. |
| `GET` | `/me` | Perfil do Usuário | Retorna dados do JWT (Google/Email). |

**Recursos suportados (`{resource}`):** `people`, `planets`, `starships`, `films`, `species`, `vehicles`.

**Parâmetros de consulta (lista):**
* `page`: paginação (repasse direto para a SWAPI).
* `search`: busca genérica (mapeada a partir de filtros de domínio).
* `sort_by`: ordenação em memória (ex.: `name`, `title`, `model`).

**Filtros de domínio (mapeados para `search`):**
* `people`: `name`
* `planets`: `name`
* `starships`: `name`, `model`
* `films`: `title`
* `species`: `name`
* `vehicles`: `name`, `model`

### Padrão de Resposta de Erro (RFC 7807)
```json
{
  "title": "Resource Not Found",
  "status": 404,
  "detail": "Person ID 99 does not exist.",
  "instance": "/people/99"
}
```

## 7. Estrutura de Pastas do Projeto

```text
.
├── src/
│   ├── adapters/          # Clientes HTTP (SWAPI) e Redis
│   ├── api/               # Rotas, middlewares e error handlers
│   │   ├── routes.py      # Endpoints da API
│   │   ├── errors.py      # Exception handlers (RFC 7807)
│   │   ├── middleware.py  # Request logging middleware
│   │   └── dependencies.py # Dependency injection
│   ├── core/              # Configurações, segurança e logging
│   │   ├── config.py      # Settings (Pydantic)
│   │   ├── security.py    # Firebase auth
│   │   └── logging.py     # Structured logging (JSON/Dev)
│   ├── domain/            # Modelos de Dados (Pydantic)
│   ├── interfaces/        # Abstract interfaces (Ports)
│   ├── use_cases/         # Lógica de Negócio (Orquestração)
│   └── main.py            # Entrypoint FastAPI (Lê headers do Gateway)
├── tests/                 # Testes Automatizados (144 testes, 95% coverage)
│   ├── unit/              # Testes unitários
│   └── integration/       # Testes de integração
├── scripts/               # Utilitários (auth.py, get_token.py)
├── openapi.yaml           # Configuração do GCP API Gateway
├── Dockerfile             # Container definition
├── ARCHITECTURE.md        # Documentação de Arquitetura
├── TASKS.md               # Plano de Execução
└── pyproject.toml         # Dependências (Poetry)
```