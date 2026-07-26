# TallyNorth

> [!IMPORTANT]
> TallyNorth includes JWT authentication and user-scoped financial data. Before exposing an instance publicly, configure a strong `JWT_SECRET_KEY`, HTTPS, restricted CORS origins, production database credentials, and backups. The project has not been security-audited.

Full-stack personal finance platform for tracking day-to-day finances and turning them into useful projections and analytics. It supports accounts, transactions, credit cards and installments, budgets, saving goals, investments, multiple currencies, and market exchange rates.

## Features

- Email/password registration and JWT sessions stored in an `HttpOnly` cookie.
- Per-user isolation across financial resources.
- Accounts, income and expense transactions, custom categories, and recurring transactions.
- Credit cards with closing/due dates and automatic installment generation.
- Individual and bulk credit-card purchase creation and installment payment tracking.
- Monthly cash-flow projections, budgets, saving goals, and investments.
- Fiat and crypto currencies with manual and market-synced exchange rates.
- Scheduled USD-to-ARS exchange-rate synchronization.
- Dashboard in USD or ARS with KPIs and interactive charts.
- Spanish and English interface with a persistent language preference.
- Responsive dark UI.

The dashboard consolidates income, expenses, net savings, wealth, account balances, upcoming installments, investments, budget usage, and saving-goal progress. When a direct exchange rate is unavailable, the backend can use an inverse rate or a cross-rate through ARS.

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript |
| UI | Tailwind CSS 4, shadcn/ui, Base UI, Lucide React, Recharts |
| Backend | FastAPI, Python 3.12, Pydantic 2 |
| ORM and migrations | SQLAlchemy 2, Alembic |
| Database | PostgreSQL 16 |
| Authentication | JWT, OAuth2 Bearer, bcrypt, `HttpOnly` cookies |
| Market data | Yahoo Finance chart endpoint |
| Local environment | Docker Compose, pgAdmin |

## Architecture

```text
Next.js / React / TypeScript
        | typed API client + session cookie
        v
FastAPI / Pydantic
        | authentication + REST resources
        v
Domain services
        | installments, cash flow, dashboard, exchange rates
        v
SQLAlchemy / PostgreSQL ----> Yahoo Finance
```

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 4.x or newer.
- Node.js 20+, Python 3.12+, and PostgreSQL 16 for development without Docker.

---

## Quick Start (Docker)

```bash
# 1. Clone the repository
git clone <repo-url>
cd finance-tracker

# 2. Create and edit the backend environment file
cp backend/.env.example backend/.env
# Set a long random JWT_SECRET_KEY in backend/.env

# 3. Build and start all services
docker compose up --build

# 4. Apply all database migrations
docker compose exec backend alembic upgrade head
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health check | http://localhost:8000/health |
| pgAdmin | http://localhost:5050 |

Create a user at http://localhost:3000/register or load the optional demo data:

```bash
docker compose exec backend python scripts/seed_demo.py
```

Demo credentials: `demo@finance.com` / `demo123`.

> [!WARNING]
> The demo credentials are public and intended only for local/demo environments.

---

## Local Development (without Docker)

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Copy and configure env
cp .env.example .env
# Set DATABASE_URL and JWT_SECRET_KEY in .env

# Run migrations
alembic upgrade head

# Start dev server (hot reload)
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend

npm install
npm run dev
```

The frontend defaults to `http://localhost:8000`. To override it, create `frontend/.env.local`:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
SERVER_API_URL=http://localhost:8000
```

`SERVER_API_URL` is used by Next.js authentication route handlers. `NEXT_PUBLIC_API_URL` is used by browser-side API requests.

---

## Environment variables

### Backend

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | Local PostgreSQL URL | SQLAlchemy database connection |
| `ENVIRONMENT` | `development` | Controls development and deployment behavior |
| `JWT_SECRET_KEY` | Insecure development fallback | Signs access tokens; required for production |
| `FRONTEND_URL` | Empty | Adds the deployed frontend origin to CORS |
| `ALLOW_ALL_ORIGINS` | `False` | Allows every CORS origin only when explicitly enabled |
| `APP_TIMEZONE` | `America/Buenos_Aires` | Resolves relative dates exposed to GPT Actions |
| `CHATGPT_ACTION_BASE_URL` | Empty | Public HTTPS API base such as `https://example.com/api/v1` |
| `EXCHANGE_RATE_CRON_ENABLED` | `True` | Enables scheduled rate synchronization |
| `EXCHANGE_RATE_CRON_HOURS` | `0,8,16` | Local server hours used by the scheduler |
| `EXCHANGE_RATE_SYNC_TO` | `ARS` | Target currency for scheduled synchronization |
| `EXCHANGE_RATE_SYNC_FROM` | `USD` | Comma-separated source currencies |

### Frontend

| Variable | Development default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL used in the browser |
| `SERVER_API_URL` | Falls back to the public URL | Backend URL used by Next.js route handlers |

## Database Migrations

```bash
# Inside the backend directory (or via Docker exec)
alembic upgrade head          # Apply all pending migrations
alembic downgrade -1          # Roll back one migration
alembic revision --autogenerate -m "your message"   # Generate new migration
```

---

## Project Structure

```
finance-tracker/
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI app, CORS, lifecycle, and routers
│   │   ├── config.py       # Environment-based settings
│   │   ├── database.py     # SQLAlchemy engine and sessions
│   │   ├── models/         # SQLAlchemy domain models
│   │   ├── schemas/        # Pydantic API contracts
│   │   ├── routers/        # Authentication and REST endpoints
│   │   └── services/       # Financial rules and integrations
│   ├── alembic/            # Database migrations
│   ├── scripts/seed_demo.py
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/            # Pages and auth route handlers
│   │   ├── components/     # Navigation and reusable UI
│   │   └── lib/            # API client, auth, and i18n
│   └── Dockerfile
├── docker-compose.yml
├── vercel.json
└── README.md
```

---

## API Overview

Financial endpoints require an authenticated user. In local development, the main API prefix is `/api/v1` and authentication is under `/api/auth`.

| Resource | Endpoints |
|---|---|
| Authentication | Register, login, logout, and current-user endpoints under `/api/auth` |
| Accounts | `GET/POST /api/v1/accounts/` - `GET/PUT/DELETE /api/v1/accounts/{id}` |
| Categories | CRUD under `/api/v1/categories` |
| Credit Cards | `GET/POST /api/v1/credit-cards/` - `GET/PUT/DELETE /api/v1/credit-cards/{id}` - `GET /api/v1/credit-cards/{id}/installments` |
| Transactions | `GET/POST /api/v1/transactions/` - `GET/PUT/DELETE /api/v1/transactions/{id}` |
| Purchases | CRUD and bulk creation under `/api/v1/purchases` |
| Installments | Update payment state under `/api/v1/installments/{id}` |
| Cashflow | `GET /api/v1/cashflow/projection` - `GET /api/v1/cashflow/summary` - `GET /api/v1/cashflow/dashboard` |
| Budgets | CRUD under `/api/v1/budgets` |
| Saving goals | CRUD under `/api/v1/saving-goals` |
| Investments | CRUD under `/api/v1/investments` |
| Currencies | CRUD under `/api/v1/currencies` |
| Exchange rates | CRUD, quote lookup, and market sync under `/api/v1/exchange-rates` |
| Dashboard | Consolidated summary under `/api/v1/dashboard/summary` |
| Integration tokens | Issue, list, and revoke scoped tokens under `/api/v1/integration-tokens` |
| ChatGPT Actions | Curated context and create-only endpoints under `/api/v1/integrations/chatgpt` |

Full interactive docs at **http://localhost:8000/docs**.

---

## ChatGPT GPT Actions

TallyNorth can be connected to a private Custom GPT using a dedicated, revocable
Bearer token and a curated OpenAPI schema. The integration exposes context
lookup, transaction creation, and credit-card purchase creation without exposing
update or delete operations.

See [backend/CHATGPT_ACTIONS.md](backend/CHATGPT_ACTIONS.md) for deployment,
token issuance, the exact GPT configuration, and copy-ready GPT instructions.

---

## Credit Card Installment Logic

The installment service follows the standard Argentine convention:

- If `purchase_date.day <= closing_day` -> first installment due on `due_day` of the **same** month.
- If `purchase_date.day > closing_day` -> first installment due on `due_day` of the **next** month.

Subsequent installments advance one calendar month each.

If a due day does not exist in a shorter month, it is clamped to that month's final day. Amounts use decimal arithmetic and `ROUND_HALF_UP` to two decimal places.

---

## Exchange-rate synchronization

Rates can be entered manually or fetched from Yahoo Finance. A configurable asynchronous scheduler starts with the FastAPI lifecycle and, by default, attempts to update USD to ARS at 00:00, 08:00, and 16:00 in the server's local timezone.

Synchronization updates an existing record for the currency pair and date instead of creating duplicates. Yahoo Finance is an external dependency; production deployments should evaluate a provider with appropriate licensing and availability guarantees.

## Authentication and authorization

- Passwords are hashed with bcrypt.
- Login returns a signed JWT with a seven-day expiration.
- The backend accepts the token from a Bearer header or the `token` cookie.
- Next.js stores browser sessions in an `HttpOnly`, `SameSite=Lax` cookie.
- Protected routes redirect unauthenticated users to login.
- Backend queries scope financial resources to the authenticated user.

## Production considerations

Before storing real financial data on a public server:

- use a long random `JWT_SECRET_KEY` and HTTPS;
- configure a precise `FRONTEND_URL` and keep `ALLOW_ALL_ORIGINS=False`;
- replace the default PostgreSQL and pgAdmin credentials;
- do not expose PostgreSQL or pgAdmin publicly;
- use encrypted storage and automated backups;
- add rate limiting, monitoring, and security scanning;
- run automated tests and review proxy, cookie, CORS, and route-prefix behavior;
- conduct a security review.

## Current limitations

- No automated test suite or CI/CD workflow is currently included.
- Investment values are entered manually; there is no historical price series.
- Scheduled jobs run in the API process rather than a dedicated worker.
- Payments and bank integrations are not implemented.
- Deployment-oriented configuration exists, but production operation is not guaranteed.
