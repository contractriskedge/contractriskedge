# AI Contract Risk Analyzer

A production-grade platform for AI-powered contract risk analysis, clause extraction, and compliance benchmarking.

## Architecture

```
contractriskanalyzer/
├── api/              # FastAPI Python backend (async)
├── frontend/         # Next.js 14 application
├── ml/               # ML model training & inference
├── infra/            # Terraform, Docker, DB schema
└── .github/          # CI/CD pipelines
```

## Tech Stack

| Layer       | Technology                                      |
|-------------|-------------------------------------------------|
| Backend     | FastAPI, SQLAlchemy 2.0 (async), Celery, Redis  |
| Database    | PostgreSQL 16 + pgvector                        |
| ML          | spaCy, PyMuPDF, scikit-learn, LangChain         |
| Frontend    | Next.js 14, TypeScript, Tailwind CSS            |
| Infra       | Docker, Terraform, GitHub Actions               |
| Auth        | Auth0 (JWT via OAuth2)                          |

## Quick Start

### Prerequisites

- Docker Desktop 4.25+
- Python 3.12+
- Node.js 20+
- Auth0 tenant (for local auth)

### Local Development

```bash
# 1. Start infrastructure
docker compose up -d postgres redis

# 2. Set up Python environment
cd api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Run database migrations
alembic upgrade head

# 4. Start API server (with hot reload)
uvicorn main:app --reload --port 8000

# 5. Start Celery worker (in another terminal)
cd api
source .venv/bin/activate
celery -A ingestion.tasks worker --loglevel=info --concurrency=4

# 6. Start frontend (in another terminal)
cd frontend
npm install
npm run dev
```

### Full Stack with Docker

```bash
docker compose up --build
```

- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Flower (Celery monitor): http://localhost:5555
- Frontend: http://localhost:3000

## Environment Variables

| Variable              | Required | Description                    |
|-----------------------|----------|--------------------------------|
| `DATABASE_URL`        | Yes      | PostgreSQL connection string   |
| `REDIS_URL`           | Yes      | Redis connection string        |
| `CELERY_BROKER_URL`   | Yes      | Celery broker URL              |
| `AUTH0_DOMAIN`        | Yes      | Auth0 tenant domain            |
| `AUTH0_AUDIENCE`      | Yes      | Auth0 API identifier           |
| `AUTH0_ISSUER`        | Yes      | Auth0 issuer URL               |
| `AWS_ACCESS_KEY_ID`   | No       | AWS credentials (Textract)     |
| `AWS_SECRET_ACCESS_KEY`| No      | AWS credentials (Textract)     |
| `AWS_REGION`          | No       | AWS region (default: us-east-1)|
| `LOG_LEVEL`           | No       | Logging level (default: INFO)  |

## API Endpoints

| Method | Path                        | Description                    |
|--------|-----------------------------|--------------------------------|
| POST   | `/api/v1/ingest/upload`     | Upload contract document       |
| GET    | `/api/v1/ingest/status/{id}`| Check ingestion status         |
| POST   | `/api/v1/contracts/search`  | Search contracts               |
| GET    | `/api/v1/contracts/{id}`    | Get contract details           |
| POST   | `/api/v1/risks/analyze`     | Run risk analysis              |
| GET    | `/api/v1/risks/{id}`        | Get risk report                |
| POST   | `/api/v1/redlines/compare`  | Compare contract versions      |
| GET    | `/api/v1/benchmarks/`       | Get compliance benchmarks      |
| GET    | `/api/v1/audit/logs`        | Query audit logs               |
| POST   | `/api/v1/webhooks/register` | Register webhook endpoint      |

## Testing

```bash
# API tests
cd api
pytest --cov=api/ --cov-report=term -v

# Frontend tests
cd frontend
npm test
```

## CI/CD

- **Pull Requests**: Lint → Type-check → Unit tests
- **Merge to main**: Build Docker images → Push to GHCR → Deploy to staging
- **Tags**: Promote to production

## License

Proprietary — All rights reserved.
