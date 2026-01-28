# Dify Setup Guide for Frag die Leitlinie

> Configuration guide for the Dify RAG backend

## Overview

Dify is an open-source LLM application development platform that powers the "Frag die Leitlinie" chatbot. This guide covers the complete setup for the RAG-based medical guideline assistant.

---

## Prerequisites

- Hetzner Cloud Server (CX31 or higher recommended)
- Docker & Docker Compose
- Domain with SSL certificate
- Mistral AI API key
- AWS Bedrock access (for Titan Embeddings & Rerank)

---

## Installation

### 1. Clone Dify

```bash
git clone https://github.com/langgenius/dify.git
cd dify/docker
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# Core Settings
SECRET_KEY=your-random-secret-key
CONSOLE_API_URL=https://dify.yourdomain.de
SERVICE_API_URL=https://dify.yourdomain.de

# Database
DB_USERNAME=dify
DB_PASSWORD=secure-password
DB_HOST=db
DB_PORT=5432
DB_DATABASE=dify

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis-password

# Vector Database (choose one)
VECTOR_STORE=weaviate
WEAVIATE_ENDPOINT=http://weaviate:8080

# File Storage
STORAGE_TYPE=local
STORAGE_LOCAL_PATH=/app/api/storage
```

### 3. Start Services

```bash
docker compose up -d
```

---

## Model Configuration

### Mistral AI (LLM)

1. Go to **Settings → Model Providers**
2. Add **Mistral AI**
3. Enter API key
4. Select models:
   - `mistral-large-latest` (primary)
   - `mistral-medium` (fallback)

**Recommended Parameters:**

| Parameter | Value | Reason |
|-----------|-------|--------|
| Temperature | 0.2 | Low creativity for factual accuracy |
| Top P | 0.9 | Slightly constrained sampling |
| Max Tokens | 4096-8192 | Sufficient for detailed answers |
| Frequency Penalty | 0 | No repetition penalty needed |

### Amazon Bedrock (Embeddings)

1. Go to **Settings → Model Providers**
2. Add **Amazon Bedrock**
3. Configure AWS credentials:
   - Region: `eu-central-1` (Frankfurt)
   - Access Key ID
   - Secret Access Key

4. Enable models:
   - `amazon.titan-embed-text-v2:0` (Embeddings)
   - `amazon.rerank-v1:0` (Reranking)

---

## Knowledge Base Setup

### 1. Create Knowledge Base

1. Go to **Knowledge → Create Knowledge Base**
2. Name: "AWMF Leitlinien"
3. Description: "Deutsche medizinische Leitlinien"

### 2. Configure Indexing

| Setting | Value |
|---------|-------|
| Embedding Model | Amazon Titan Embed v2 |
| Chunk Size | 1000 tokens |
| Chunk Overlap | 200 tokens |
| Retrieval Mode | Hybrid (Vector + Keyword) |

### 3. Upload Documents

**Supported Formats:**
- PDF (recommended for guidelines)
- DOCX
- TXT
- Markdown

**Document Naming Convention:**
```
S3-Leitlinie_Mammakarzinom_2024.pdf
DEGAM-Leitlinie_Husten_2023.pdf
NVL_Asthma_2024.pdf
```

### 4. Configure Retrieval

| Setting | Value |
|---------|-------|
| Top K | 5-8 |
| Score Threshold | 0.5 |
| Reranking | Amazon Rerank |
| Rerank Top N | 3-5 |

---

## Application Setup

### 1. Create Chat Application

1. Go to **Studio → Create Application**
2. Type: **Chat**
3. Name: "Frag die Leitlinie"

### 2. Configure System Prompt

Copy the prompt from `docs/dify-guidelines-prompt.md`:

```markdown
Du bist ein AWMF-Leitlinien-Experte für medizinisches Fachpersonal.

## AUFGABE
Beantworte medizinische Fragen basierend auf den bereitgestellten Leitlinien-Auszügen...
```

### 3. Link Knowledge Base

1. In application settings, go to **Context**
2. Add "AWMF Leitlinien" knowledge base
3. Configure retrieval settings:
   - Top K: 5
   - Reranking: Enabled

### 4. Configure Features

| Feature | Setting |
|---------|---------|
| Suggested Questions | Enabled |
| Conversation History | 10 turns |
| File Upload | Disabled |
| Web Search | Disabled |
| Citation | Enabled |

### 5. Generate API Key

1. Go to **API Access**
2. Create new API key
3. Copy key for frontend configuration

---

## API Integration

### Endpoint Configuration

```
Base URL: https://dify.yourdomain.de/v1
API Key: app-xxxxxxxxxxxxxxxxxxxx
```

### Chat Messages Endpoint

```bash
POST /v1/chat-messages
Content-Type: application/json
Authorization: Bearer app-xxxxxxxxxxxxxxxxxxxx

{
  "inputs": {},
  "query": "Was sind die Empfehlungen bei Diabetes Typ 2?",
  "response_mode": "streaming",
  "conversation_id": "",
  "user": "user-123"
}
```

### Response Format (SSE)

```
event: message
data: {"answer": "Bei Diabetes", "conversation_id": "abc123"}

event: message
data: {"answer": " Typ 2 empfiehlt", "conversation_id": "abc123"}

event: message_end
data: {
  "metadata": {
    "retriever_resources": [
      {
        "document_name": "NVL Typ-2-Diabetes",
        "score": 0.89,
        "content": "..."
      }
    ]
  }
}

event: message
data: {"suggested_questions": ["Wie wird Metformin dosiert?", ...]}
```

### Feedback Endpoint

```bash
POST /v1/messages/{message_id}/feedbacks
Authorization: Bearer app-xxxxxxxxxxxxxxxxxxxx

{
  "rating": "like",
  "user": "user-123"
}
```

---

## Monitoring

### Health Check

```bash
curl https://dify.yourdomain.de/health
```

### Logs

```bash
# Application logs
docker compose logs -f api

# Worker logs
docker compose logs -f worker
```

### Metrics

Dify provides built-in analytics:
- Message count
- Token usage
- Response latency
- Feedback statistics

---

## Backup & Recovery

### Database Backup

```bash
docker compose exec db pg_dump -U dify dify > backup.sql
```

### Knowledge Base Export

1. Go to Knowledge Base settings
2. Click **Export**
3. Download as ZIP (includes documents + embeddings metadata)

### Full Backup

```bash
# Stop services
docker compose down

# Backup volumes
tar -czvf dify-backup.tar.gz \
  ./volumes/db/data \
  ./volumes/weaviate \
  ./volumes/app/storage

# Restart
docker compose up -d
```

---

## Performance Tuning

### Database

```sql
-- Add indexes for common queries
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_created ON messages(created_at);
```

### Vector Database

For Weaviate:
```yaml
# docker-compose.yml
weaviate:
  environment:
    QUERY_DEFAULTS_LIMIT: 100
    PERSISTENCE_DATA_PATH: /var/lib/weaviate
```

### Caching

```bash
# .env
REDIS_MAX_MEMORY=512mb
REDIS_MAX_MEMORY_POLICY=allkeys-lru
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| No retrieval results | Check embedding model, reindex documents |
| Slow responses | Increase worker count, optimize chunk size |
| Memory errors | Increase Docker memory limits |
| SSL issues | Verify certificate chain, check Caddy/nginx config |

### Debug Mode

```bash
# .env
LOG_LEVEL=DEBUG
```

### Reset Knowledge Base

```bash
# Delete and recreate embeddings
docker compose exec api flask reset-knowledge-base --id <kb_id>
```

---

## Security Hardening

### API Rate Limiting

Configure in reverse proxy (Caddy):

```
rate_limit {
    zone dify {
        key {remote_host}
        events 100
        window 1m
    }
}
```

### Network Security

```yaml
# docker-compose.yml
networks:
  dify-internal:
    internal: true
  dify-external:
    driver: bridge
```

### Access Control

- Disable public signup
- Use API keys for all external access
- Enable audit logging

---

## Updates

### Upgrade Dify

```bash
cd dify/docker
git pull
docker compose pull
docker compose up -d
```

### Backup Before Upgrade

Always backup database and volumes before upgrading.

---

## Related Documentation

- [Chatbot Documentation](./CHATBOT.md)
- [Architecture Overview](./ARCHITECTURE.md)
- [Dify System Prompt](./dify-guidelines-prompt.md)
- [Dify Official Docs](https://docs.dify.ai)

---

*Last updated: January 2025*
