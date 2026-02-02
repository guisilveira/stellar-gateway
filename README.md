# 🚀 Stellar Gateway

A serverless proxy for the Star Wars API (SWAPI) built with **Python**, **FastAPI**, **Firebase Authentication**, **Redis caching**, and deployed on **Google Cloud Run** with **API Gateway**.

## 📖 Overview

Stellar Gateway provides a secure, cached, and enriched interface to the Star Wars API. It demonstrates:

- **Clean Architecture** / Hexagonal Architecture
- **Firebase Authentication** with JWT validation
- **Redis caching** with Cache-Aside pattern
- **Data enrichment** (replacing URLs with resource names)
- **Filtering, pagination, and sorting**
- **Serverless deployment** on GCP

## 🌐 Live API

| Endpoint | URL |
|----------|-----|
| **API Gateway** (Production) | `https://stellar-gateway-23t3upfn.uc.gateway.dev` |
| **Cloud Run** (Direct) | `https://stellar-gateway-165018665795.us-central1.run.app` |

## 📚 API Endpoints

### Public Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (no auth required) |

### Protected Endpoints (Require Firebase JWT)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/me` | Get authenticated user info |
| GET | `/{resource}` | List resources (people, planets, films, species, vehicles, starships) |
| GET | `/{resource}/{id}` | Get a specific resource by ID |

### Query Parameters
| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `page` | int | Page number for pagination | `?page=2` |
| `search` | string | Search/filter query | `?search=luke` |
| `sort_by` | string | Field to sort by | `?sort_by=name` |
| `sort_order` | string | Sort direction (asc/desc) | `?sort_order=desc` |
| `enrich` | bool | Enable URL enrichment (default: true) | `?enrich=false` |

## 🔐 Authentication

All protected endpoints require a valid Firebase ID Token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer <FIREBASE_TOKEN>" https://stellar-gateway-23t3upfn.uc.gateway.dev/people/1
```

### Authentication CLI

The project includes a CLI tool for Firebase authentication:

```bash
# Create a new user account
poetry run python scripts/auth.py signup -e user@example.com -p password123

# Login and get an ID Token
poetry run python scripts/auth.py login -e user@example.com -p password123

# Login in quiet mode (only outputs token - great for scripting)
TOKEN=$(poetry run python scripts/auth.py login -e user@example.com -p password123 -q)
curl -H "Authorization: Bearer $TOKEN" https://stellar-gateway-23t3upfn.uc.gateway.dev/people/1

# Refresh an expired token
poetry run python scripts/auth.py refresh -t <refresh_token>
```

### Generating a Test Token (Admin SDK)

For testing without a real user, you can generate a token using the Firebase Admin SDK:

```bash
poetry run python scripts/get_token.py --uid test-user-001
```

> **Note:** This requires `serviceAccountKey.json` and is intended for development only.

## 🛠️ Local Development

### Prerequisites

- Python 3.12+
- Poetry 2.3.1+
- Docker & Docker Compose
- Redis (via Docker)

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd stellar-gateway

# Install dependencies
poetry install

# Copy environment file
cp .env.example .env

# Run Redis
docker compose up -d redis

# Run the API
poetry run uvicorn src.main:app --reload
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html
```

## 🚀 Deployment

### Prerequisites

- GCP Account with billing enabled
- gcloud CLI installed and authenticated
- Firebase project configured

### Deploy to Cloud Run

```bash
# Set project
gcloud config set project stellar-gateway-10135

# Deploy
gcloud run deploy stellar-gateway \
  --source=. \
  --region=us-central1 \
  --vpc-connector=stellar-redis-connector \
  --set-env-vars="ENVIRONMENT=prod,REDIS_HOST=10.160.194.123,REDIS_PORT=6379" \
  --allow-unauthenticated \
  --memory=512Mi \
  --timeout=60s
```

### Deploy API Gateway

```bash
# Create API
gcloud api-gateway apis create stellar-gateway-api \
  --display-name="Stellar Gateway API"

# Create API Config
gcloud api-gateway api-configs create stellar-gateway-config-v1 \
  --api=stellar-gateway-api \
  --openapi-spec=openapi.yaml \
  --backend-auth-service-account=firebase-adminsdk-fbsvc@stellar-gateway-10135.iam.gserviceaccount.com

# Create Gateway
gcloud api-gateway gateways create stellar-gateway \
  --api=stellar-gateway-api \
  --api-config=stellar-gateway-config-v1 \
  --location=us-central1
```

## 📁 Project Structure

```
stellar-gateway/
├── src/
│   ├── adapters/          # External service clients (Redis, SWAPI)
│   ├── api/               # FastAPI routes, dependencies, error handlers
│   ├── core/              # Configuration, security
│   ├── domain/            # Domain models and exceptions
│   ├── interfaces/        # Abstract interfaces (ports)
│   └── use_cases/         # Business logic
├── tests/
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── scripts/               # Utility scripts
├── main.py                # Cloud Run entry point
├── openapi.yaml           # API Gateway OpenAPI spec
├── Dockerfile             # Container definition
└── docker-compose.yml     # Local development setup
```

## 🏗️ Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

### Key Design Decisions

1. **Clean Architecture**: Separation of concerns with adapters, use cases, and domain layers
2. **Cache-Aside Pattern**: Redis caching with 5-minute TTL
3. **Data Enrichment**: URL fields are resolved to resource names in parallel
4. **Dual Auth Support**: Works with both API Gateway (X-Apigateway-Api-Userinfo) and direct Bearer tokens

## 📊 Test Coverage

```
Name                          Stmts   Miss  Cover
-------------------------------------------------
src/adapters/redis.py            32      0   100%
src/adapters/swapi.py            58      5    91%
src/api/dependencies.py          18      4    78%
src/api/errors.py                37      1    97%
src/api/routes.py                16      0   100%
src/core/config.py               13      0   100%
src/core/security.py             56      8    86%
src/domain/exceptions.py         18      0   100%
src/domain/models.py             10      0   100%
src/use_cases/get_resource.py    66      4    94%
src/use_cases/list_resources.py  48      1    98%
-------------------------------------------------
TOTAL                           415     23    94%
```

## 📄 License

MIT
