# 🚀 Stellar Gateway - Guia Completo de Setup no GCP

Este documento detalha **passo a passo** como configurar e deployar o Stellar Gateway no Google Cloud Platform, incluindo Firebase Authentication, Redis (Memorystore) e API Gateway.

---

## 📑 Índice

1. [Visão Geral da Arquitetura](#1-visão-geral-da-arquitetura)
2. [Pré-requisitos](#2-pré-requisitos)
3. [Fase 1: Configuração do Projeto GCP](#3-fase-1-configuração-do-projeto-gcp)
4. [Fase 2: Configuração do Firebase](#4-fase-2-configuração-do-firebase)
5. [Fase 3: Configuração do Redis (Memorystore)](#5-fase-3-configuração-do-redis-memorystore)
6. [Fase 4: Deploy no Cloud Run](#6-fase-4-deploy-no-cloud-run)
7. [Fase 5: Deploy do API Gateway](#7-fase-5-deploy-do-api-gateway)
8. [Fase 6: Testando a API](#8-fase-6-testando-a-api)
9. [Desenvolvimento Local](#9-desenvolvimento-local)
10. [Troubleshooting](#10-troubleshooting)
11. [Custos Estimados](#11-custos-estimados)
12. [Referência de Comandos](#12-referência-de-comandos)

---

## 1. Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GCP API GATEWAY                                      │
│  • Valida JWT do Firebase                                                   │
│  • Rate Limiting                                                            │
│  • Roteamento                                                               │
│  URL: https://stellar-gateway-XXXXX.uc.gateway.dev                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ X-Apigateway-Api-Userinfo (base64)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CLOUD RUN                                         │
│  • FastAPI Application                                                      │
│  • Business Logic                                                           │
│  • Data Enrichment                                                          │
│  URL: https://stellar-gateway-XXXXX.us-central1.run.app                     │
└─────────────────────────────────────────────────────────────────────────────┘
                        │                           │
                        ▼                           ▼
┌───────────────────────────────┐   ┌─────────────────────────────────────────┐
│      REDIS (MEMORYSTORE)      │   │              SWAPI                       │
│  • Cache com TTL 5min         │   │  • Star Wars API                        │
│  • VPC Connector              │   │  • https://swapi.dev/api                │
│  IP: 10.160.194.123:6379      │   │                                         │
└───────────────────────────────┘   └─────────────────────────────────────────┘
```

### Componentes

| Componente | Função |
|------------|--------|
| **API Gateway** | Ponto de entrada público, valida JWTs do Firebase |
| **Cloud Run** | Executa a aplicação FastAPI (serverless) |
| **Redis (Memorystore)** | Cache de dados da SWAPI |
| **Firebase Auth** | Gerencia autenticação de usuários |
| **SWAPI** | API externa de Star Wars |

---

## 2. Pré-requisitos

### 2.1 Ferramentas Necessárias

```bash
# Google Cloud CLI
# Instalação no Ubuntu/Debian:
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt update && sudo apt install google-cloud-cli

# Arch Linux:
sudo pacman -S google-cloud-cli

# Verificar instalação
gcloud version
```

```bash
# Python 3.12+
python3 --version  # Deve ser 3.12 ou superior

# Poetry (gerenciador de dependências)
curl -sSL https://install.python-poetry.org | python3 -
poetry --version  # Deve ser 2.x
```

### 2.2 Conta GCP

- Conta Google com acesso ao [Google Cloud Console](https://console.cloud.google.com)
- Billing habilitado (pode usar os $300 de crédito gratuito)
- Permissões de Owner ou Editor no projeto

### 2.3 Autenticação Local

```bash
# Login no GCP
gcloud auth login

# Login para Application Default Credentials (usado pelo SDK)
gcloud auth application-default login
```

---

## 3. Fase 1: Configuração do Projeto GCP

### 3.1 Criar Projeto

```bash
# Definir variáveis (ajuste conforme necessário)
export PROJECT_ID="stellar-gateway-$(date +%s | tail -c 6)"
export REGION="us-central1"
export BILLING_ACCOUNT=$(gcloud billing accounts list --format="value(name)" | head -1)

# Criar projeto
gcloud projects create $PROJECT_ID --name="Stellar Gateway"

# Definir como projeto padrão
gcloud config set project $PROJECT_ID

# Vincular billing account
gcloud billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT

# Verificar
gcloud projects describe $PROJECT_ID
```

### 3.2 Habilitar APIs Necessárias

```bash
# Habilitar todas as APIs necessárias
gcloud services enable \
  cloudfunctions.googleapis.com \
  cloudbuild.googleapis.com \
  apigateway.googleapis.com \
  servicemanagement.googleapis.com \
  servicecontrol.googleapis.com \
  redis.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  vpcaccess.googleapis.com \
  compute.googleapis.com

# Verificar APIs habilitadas
gcloud services list --enabled
```

> ⏱️ **Nota:** A habilitação pode levar alguns minutos.

---

## 4. Fase 2: Configuração do Firebase

### 4.1 Criar Projeto Firebase

1. Acesse o [Firebase Console](https://console.firebase.google.com)
2. Clique em **"Add project"**
3. Selecione o projeto GCP criado anteriormente (`stellar-gateway-XXXXX`)
4. Desative Google Analytics (opcional para este projeto)
5. Clique em **"Create project"**

### 4.2 Habilitar Autenticação

1. No Firebase Console, vá para **Build > Authentication**
2. Clique em **"Get started"**
3. Na aba **"Sign-in method"**, habilite:
   - **Email/Password** (para testes)
   - **Google** (opcional, para login social)

### 4.3 Gerar Service Account Key

```bash
# Verificar se a organização bloqueia criação de chaves
# Se sim, você precisa de permissão de admin para desabilitar a policy:
# gcloud resource-manager org-policies disable-enforce iam.disableServiceAccountKeyCreation --project=$PROJECT_ID

# Identificar o service account do Firebase
gcloud iam service-accounts list --filter="email:firebase-adminsdk"

# Criar a chave (substitua o email correto)
export FIREBASE_SA="firebase-adminsdk-fbsvc@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam service-accounts keys create serviceAccountKey.json \
  --iam-account=$FIREBASE_SA

# Verificar que o arquivo foi criado
ls -la serviceAccountKey.json
```

> ⚠️ **IMPORTANTE:** Nunca commite o arquivo `serviceAccountKey.json` no Git!

### 4.4 Obter Web API Key

1. No Firebase Console, clique no ícone de engrenagem ⚙️ > **Project settings**
2. Role até **"Your apps"** e clique em **"Add app"** > **Web** (ícone `</>`)
3. Registre um app com nome "Stellar Gateway Web"
4. Copie a `apiKey` exibida
5. Adicione ao arquivo `.env`:

```bash
# Adicionar ao .env
echo "FIREBASE_WEB_API_KEY=<sua-api-key>" >> .env
```

### 4.5 Atualizar .gitignore

```bash
# Garantir que credenciais não sejam commitadas
echo "serviceAccountKey.json" >> .gitignore
echo ".env" >> .gitignore
```

---

## 5. Fase 3: Configuração do Redis (Memorystore)

### 5.1 Criar VPC Connector

O Cloud Run precisa de um VPC Connector para acessar o Redis (que é uma rede privada).

```bash
# Criar o VPC Connector
gcloud compute networks vpc-access connectors create stellar-redis-connector \
  --region=$REGION \
  --range="10.8.0.0/28" \
  --network=default

# Verificar criação
gcloud compute networks vpc-access connectors describe stellar-redis-connector \
  --region=$REGION
```

> ⏱️ **Nota:** Pode levar 2-3 minutos.

### 5.2 Criar Instância Redis

```bash
# Criar instância Redis (Basic tier, 1GB)
gcloud redis instances create stellar-cache \
  --size=1 \
  --region=$REGION \
  --redis-version=redis_7_0 \
  --network=default

# Aguardar criação (pode levar 5-10 minutos)
gcloud redis instances describe stellar-cache --region=$REGION

# Obter o IP do Redis
export REDIS_HOST=$(gcloud redis instances describe stellar-cache \
  --region=$REGION \
  --format="value(host)")
export REDIS_PORT=$(gcloud redis instances describe stellar-cache \
  --region=$REGION \
  --format="value(port)")

echo "Redis: $REDIS_HOST:$REDIS_PORT"
```

> 💰 **Custo:** ~$35/mês para 1GB Basic tier

---

## 6. Fase 4: Deploy no Cloud Run

### 6.1 Preparar Arquivos

Verifique que os seguintes arquivos existem na raiz do projeto:

```bash
ls -la main.py Dockerfile requirements.txt .gcloudignore
```

**main.py** (entry point para Cloud Run):
```python
import os
import sys
from pathlib import Path

src_path = str(Path(__file__).parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

root_path = str(Path(__file__).parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import src.main as src_main
app = src_main.app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

**Dockerfile**:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY main.py ./
COPY serviceAccountKey.json ./

ENV PYTHONPATH=/app/src

RUN useradd --create-home appuser
USER appuser

ENV PORT=8080
EXPOSE 8080

CMD uvicorn main:app --host 0.0.0.0 --port $PORT
```

### 6.2 Gerar requirements.txt

```bash
# Exportar dependências do Poetry
poetry export -f requirements.txt --without-hashes -o requirements.txt
```

### 6.3 Deploy

```bash
# Deploy para Cloud Run
gcloud run deploy stellar-gateway \
  --source=. \
  --region=$REGION \
  --vpc-connector=stellar-redis-connector \
  --set-env-vars="ENVIRONMENT=prod,REDIS_HOST=$REDIS_HOST,REDIS_PORT=$REDIS_PORT" \
  --allow-unauthenticated \
  --memory=512Mi \
  --timeout=60s

# Obter URL do serviço
export CLOUDRUN_URL=$(gcloud run services describe stellar-gateway \
  --region=$REGION \
  --format="value(status.url)")

echo "Cloud Run URL: $CLOUDRUN_URL"
```

> ⏱️ **Nota:** O primeiro deploy pode levar 5-10 minutos (build da imagem).

### 6.4 Testar Cloud Run Diretamente

```bash
# Health check (deve funcionar sem auth)
curl $CLOUDRUN_URL/health

# Esperado: {"status":"healthy"}
```

---

## 7. Fase 5: Deploy do API Gateway

### 7.1 Gerar OpenAPI Spec a partir do Template

O projeto usa um arquivo template (`openapi.template.yaml`) com placeholders para evitar
hardcoded values. Você precisa gerar o `openapi.yaml` final:

```bash
# Definir variáveis de ambiente
export GCP_PROJECT_ID="$PROJECT_ID"
export CLOUD_RUN_URL="$CLOUDRUN_URL"

# Gerar openapi.yaml a partir do template
envsubst < openapi.template.yaml > openapi.yaml

# Verificar se os valores foram substituídos corretamente
cat openapi.yaml | grep -E "(host:|address:|x-google-issuer:|x-google-audiences:)"
```

**Saída esperada:**
```yaml
host: stellar-gateway-api.endpoints.YOUR-PROJECT-ID.cloud.goog
  x-google-issuer: "https://securetoken.google.com/YOUR-PROJECT-ID"
  x-google-audiences: "YOUR-PROJECT-ID"
  address: https://stellar-gateway-XXXXX.us-central1.run.app
```

> 💡 **Dica:** Se `envsubst` não estiver instalado, use: `sudo apt-get install gettext-base`

### 7.2 Criar API

```bash
# Criar a API
gcloud api-gateway apis create stellar-gateway-api \
  --display-name="Stellar Gateway API"

# Aguardar (pode levar alguns minutos)
gcloud api-gateway apis list
```

### 7.3 Criar API Config

```bash
# Criar configuração com o OpenAPI spec
gcloud api-gateway api-configs create stellar-gateway-config-v1 \
  --api=stellar-gateway-api \
  --openapi-spec=openapi.yaml \
  --backend-auth-service-account=$FIREBASE_SA

# Verificar
gcloud api-gateway api-configs list --api=stellar-gateway-api
```

> ⏱️ **Nota:** Pode levar 5-10 minutos.

### 7.4 Criar Gateway

```bash
# Criar o gateway
gcloud api-gateway gateways create stellar-gateway \
  --api=stellar-gateway-api \
  --api-config=stellar-gateway-config-v1 \
  --location=$REGION

# Obter URL do gateway
export GATEWAY_URL=$(gcloud api-gateway gateways describe stellar-gateway \
  --location=$REGION \
  --format="value(defaultHostname)")

echo "API Gateway URL: https://$GATEWAY_URL"
```

> ⏱️ **Nota:** Pode levar 5-10 minutos.

---

## 8. Fase 6: Testando a API

### 8.1 Gerar Token Firebase

```bash
# Gerar um token de teste
poetry run python scripts/get_token.py --uid test-user-001

# Copie o token gerado (linha que começa com eyJ...)
```

### 8.2 Salvar Token em Variável

```bash
# Copie o token e cole aqui
export TOKEN="eyJ..."
```

### 8.3 Testes Básicos

```bash
GATEWAY="https://$GATEWAY_URL"

# 1. Health Check (sem auth)
echo "=== Health Check ==="
curl -s "$GATEWAY/health" | jq .

# 2. Request sem token (deve falhar)
echo -e "\n=== Sem Token (401) ==="
curl -s "$GATEWAY/people" | jq .

# 3. /me - Info do usuário
echo -e "\n=== /me ==="
curl -s "$GATEWAY/me" -H "Authorization: Bearer $TOKEN" | jq .

# 4. /people/1 - Luke Skywalker
echo -e "\n=== /people/1 ==="
curl -s "$GATEWAY/people/1" -H "Authorization: Bearer $TOKEN" | jq .
```

### 8.4 Testes de Features

```bash
# Paginação
echo "=== Paginação (page=2) ==="
curl -s "$GATEWAY/people?page=2" -H "Authorization: Bearer $TOKEN" | jq '{count, next, previous}'

# Busca/Filtro
echo -e "\n=== Busca (search=vader) ==="
curl -s "$GATEWAY/people?search=vader" -H "Authorization: Bearer $TOKEN" | jq '.results[].name'

# Ordenação
echo -e "\n=== Ordenação (sort_by=name, desc) ==="
curl -s "$GATEWAY/planets?sort_by=name&sort_order=desc" -H "Authorization: Bearer $TOKEN" | jq '[.results[].name][:5]'

# Enrichment (dados correlacionados)
echo -e "\n=== Films com Characters Enriquecidos ==="
curl -s "$GATEWAY/films/1" -H "Authorization: Bearer $TOKEN" | jq '{title, characters: .characters[:5]}'

# Enrichment desabilitado
echo -e "\n=== Sem Enrichment (URLs brutas) ==="
curl -s "$GATEWAY/people/1?enrich=false" -H "Authorization: Bearer $TOKEN" | jq '{name, homeworld, films}'
```

### 8.5 Script de Teste Completo

Crie um script para testar tudo de uma vez:

```bash
#!/bin/bash
# test_api.sh

GATEWAY="https://stellar-gateway-XXXXX.uc.gateway.dev"
TOKEN="$1"

if [ -z "$TOKEN" ]; then
    echo "Uso: ./test_api.sh <TOKEN>"
    exit 1
fi

echo "=========================================="
echo "   STELLAR GATEWAY - TESTE COMPLETO"
echo "=========================================="

echo -e "\n[1/7] Health Check..."
curl -s "$GATEWAY/health" | jq -c .

echo -e "\n[2/7] Auth Test (sem token)..."
curl -s "$GATEWAY/people" | jq -c .

echo -e "\n[3/7] /me..."
curl -s "$GATEWAY/me" -H "Authorization: Bearer $TOKEN" | jq -c .

echo -e "\n[4/7] /people/1..."
curl -s "$GATEWAY/people/1" -H "Authorization: Bearer $TOKEN" | jq -c '{name, homeworld}'

echo -e "\n[5/7] Paginação..."
curl -s "$GATEWAY/people?page=2" -H "Authorization: Bearer $TOKEN" | jq -c '{count, results: (.results | length)}'

echo -e "\n[6/7] Busca..."
curl -s "$GATEWAY/people?search=luke" -H "Authorization: Bearer $TOKEN" | jq -c '[.results[].name]'

echo -e "\n[7/7] Ordenação..."
curl -s "$GATEWAY/planets?sort_by=name&sort_order=desc" -H "Authorization: Bearer $TOKEN" | jq -c '[.results[].name][:3]'

echo -e "\n=========================================="
echo "   TODOS OS TESTES CONCLUÍDOS!"
echo "=========================================="
```

---

## 9. Desenvolvimento Local

### 9.1 Setup Inicial

```bash
# Clonar repositório
git clone <repository-url>
cd stellar-gateway

# Instalar dependências
poetry install

# Copiar .env de exemplo
cp .env.example .env

# Editar .env com suas configurações
# ENVIRONMENT=dev permite usar mock-token
```

### 9.2 Rodar com Docker Compose

```bash
# Subir Redis + App
docker compose up --build

# A API estará disponível em http://localhost:8000
# Docs em http://localhost:8000/docs
```

### 9.3 Rodar sem Docker

```bash
# Terminal 1: Redis
docker run -p 6379:6379 redis:alpine

# Terminal 2: API
poetry run uvicorn src.main:app --reload --port 8000
```

### 9.4 Testar Localmente

```bash
# Com mock-token (apenas em ENVIRONMENT=dev)
curl http://localhost:8000/people/1 -H "Authorization: Bearer mock-token"

# Ou gerar token real
poetry run python scripts/get_token.py --uid dev-user
```

### 9.5 Rodar Testes

```bash
# Todos os testes
poetry run pytest

# Com coverage
poetry run pytest --cov=src --cov-report=html

# Apenas testes unitários
poetry run pytest tests/unit/

# Apenas testes de integração
poetry run pytest tests/integration/
```

---

## 10. Troubleshooting

### Erro: "Container failed to start"

**Sintoma:** Cloud Run retorna erro 503 ou logs mostram container não iniciou.

**Soluções:**
1. Verificar logs:
   ```bash
   gcloud run services logs read stellar-gateway --region=$REGION --limit=50
   ```
2. Verificar se `serviceAccountKey.json` está sendo copiado no Dockerfile
3. Verificar se `requirements.txt` está atualizado

### Erro: "Jwt is missing" no API Gateway

**Sintoma:** Endpoints protegidos retornam 401.

**Soluções:**
1. Verificar se o token está sendo enviado:
   ```bash
   curl -v "$GATEWAY/me" -H "Authorization: Bearer $TOKEN"
   ```
2. Verificar se o token não expirou (válido por 1 hora)
3. Gerar novo token:
   ```bash
   poetry run python scripts/get_token.py --uid test-user
   ```

### Erro: "Invalid ID token" no Cloud Run

**Sintoma:** API Gateway passa, mas Cloud Run rejeita.

**Soluções:**
1. Verificar se `serviceAccountKey.json` está correto
2. Verificar se o projeto Firebase está linkado ao GCP
3. Verificar se `GOOGLE_APPLICATION_CREDENTIALS` está configurado

### Erro: "Connection refused" para Redis

**Sintoma:** Timeout ou erro de conexão com Redis.

**Soluções:**
1. Verificar se VPC Connector está ativo:
   ```bash
   gcloud compute networks vpc-access connectors describe stellar-redis-connector --region=$REGION
   ```
2. Verificar IP do Redis:
   ```bash
   gcloud redis instances describe stellar-cache --region=$REGION
   ```
3. Verificar se Cloud Run está usando o VPC Connector:
   ```bash
   gcloud run services describe stellar-gateway --region=$REGION --format="yaml" | grep vpc
   ```

### Erro: "Permission denied" ao criar Service Account Key

**Sintoma:** Organização bloqueia criação de chaves.

**Solução:**
```bash
# Requer permissão de Organization Admin
gcloud resource-manager org-policies disable-enforce \
  iam.disableServiceAccountKeyCreation \
  --project=$PROJECT_ID
```

---

## 11. Custos Estimados

### Componentes e Preços (us-central1, Jan 2026)

| Componente | Especificação | Custo/Mês |
|------------|---------------|-----------|
| **Cloud Run** | 512MB, ~100k requests | ~$5-10 |
| **Redis (Memorystore)** | 1GB Basic | ~$35 |
| **API Gateway** | ~100k requests | ~$3-5 |
| **Artifact Registry** | ~1GB storage | ~$0.10 |
| **VPC Connector** | Mínimo | ~$7 |
| **Egress** | ~10GB | ~$1 |
| **TOTAL** | | **~$50-60/mês** |

### Free Tier / Créditos

- **$300 créditos** para novos usuários (90 dias)
- **Cloud Run:** 2M requests/mês grátis
- **Cloud Build:** 120 min/dia grátis

### Dicas de Economia

1. **Pausar Redis quando não usar:**
   ```bash
   # Não é possível pausar, mas pode deletar e recriar
   gcloud redis instances delete stellar-cache --region=$REGION
   ```

2. **Usar Cloud Run apenas quando necessário:**
   ```bash
   # Scale to zero automático (sem custo quando ocioso)
   ```

3. **Monitorar custos:**
   ```bash
   gcloud billing budgets create --billing-account=$BILLING_ACCOUNT \
     --display-name="Stellar Gateway Budget" \
     --budget-amount=50
   ```

---

## 12. Referência de Comandos

### Projeto GCP

```bash
# Listar projetos
gcloud projects list

# Mudar projeto
gcloud config set project PROJECT_ID

# Ver configuração atual
gcloud config list
```

### Cloud Run

```bash
# Listar serviços
gcloud run services list --region=$REGION

# Ver detalhes do serviço
gcloud run services describe stellar-gateway --region=$REGION

# Ver logs
gcloud run services logs read stellar-gateway --region=$REGION --limit=100

# Atualizar variáveis de ambiente
gcloud run services update stellar-gateway --region=$REGION \
  --set-env-vars="KEY=VALUE"

# Deletar serviço
gcloud run services delete stellar-gateway --region=$REGION
```

### API Gateway

```bash
# Listar gateways
gcloud api-gateway gateways list --location=$REGION

# Ver detalhes
gcloud api-gateway gateways describe stellar-gateway --location=$REGION

# Atualizar config (nova versão)
# Primeiro, gere o openapi.yaml atualizado:
# envsubst < openapi.template.yaml > openapi.yaml

gcloud api-gateway api-configs create stellar-gateway-config-v2 \
  --api=stellar-gateway-api \
  --openapi-spec=openapi.yaml \
  --backend-auth-service-account=$FIREBASE_SA

gcloud api-gateway gateways update stellar-gateway \
  --api=stellar-gateway-api \
  --api-config=stellar-gateway-config-v2 \
  --location=$REGION

# Deletar gateway
gcloud api-gateway gateways delete stellar-gateway --location=$REGION
```

### Redis (Memorystore)

```bash
# Listar instâncias
gcloud redis instances list --region=$REGION

# Ver detalhes
gcloud redis instances describe stellar-cache --region=$REGION

# Deletar instância
gcloud redis instances delete stellar-cache --region=$REGION
```

### Firebase

```bash
# Listar service accounts
gcloud iam service-accounts list

# Gerar nova chave
gcloud iam service-accounts keys create new-key.json \
  --iam-account=SERVICE_ACCOUNT_EMAIL

# Listar chaves existentes
gcloud iam service-accounts keys list \
  --iam-account=SERVICE_ACCOUNT_EMAIL
```

### Token de Teste

```bash
# Gerar token
poetry run python scripts/get_token.py --uid USER_ID

# Decodificar token (para debug)
echo $TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | jq .
```

---

## 📋 Checklist Final

Antes de considerar o setup completo, verifique:

- [ ] Projeto GCP criado e billing vinculado
- [ ] APIs habilitadas (run, redis, apigateway, vpcaccess)
- [ ] Firebase configurado com Email/Password auth
- [ ] `serviceAccountKey.json` gerado e no projeto
- [ ] `FIREBASE_WEB_API_KEY` no `.env`
- [ ] Redis (Memorystore) criado
- [ ] VPC Connector criado
- [ ] Cloud Run deployado e respondendo `/health`
- [ ] API Gateway criado e respondendo
- [ ] Token Firebase funcionando
- [ ] Todos os endpoints testados

---

## 🎉 Recursos Deployados (Este Projeto)

| Recurso | Valor |
|---------|-------|
| **GCP Project ID** | `stellar-gateway-10135` |
| **Region** | `us-central1` |
| **Cloud Run URL** | `https://stellar-gateway-165018665795.us-central1.run.app` |
| **API Gateway URL** | `https://stellar-gateway-23t3upfn.uc.gateway.dev` |
| **Redis Host** | `10.160.194.123:6379` |
| **VPC Connector** | `stellar-redis-connector` |
| **Firebase SA** | `firebase-adminsdk-fbsvc@stellar-gateway-10135.iam.gserviceaccount.com` |

---

## 📚 Documentação Adicional

- [ARCHITECTURE.md](ARCHITECTURE.md) - Arquitetura detalhada do sistema
- [TASKS.md](TASKS.md) - Roadmap e status de implementação
- [README.md](README.md) - Visão geral e quick start
- [openapi.template.yaml](openapi.template.yaml) - Template OpenAPI (use `envsubst` para gerar `openapi.yaml`)

---

**Última atualização:** Fevereiro 2026
