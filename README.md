# TallyNorth

> [!IMPORTANT]
> TallyNorth includes JWT authentication and user-scoped financial data. Before exposing an instance publicly, configure a strong `JWT_SECRET_KEY`, HTTPS, restricted CORS origins, production database credentials, and backups. The project has not been security-audited.

Full-stack personal finance platform for tracking day-to-day finances and turning them into useful projections and analytics. It supports accounts, transactions, recurring entries, credit cards and installments, budgets, saving goals, investments, multiple currencies, and market exchange rates.

## Features

- Email/password registration and JWT sessions stored in an `HttpOnly` cookie.
- Per-user isolation across financial resources.
- Accounts, income and expense transactions, and custom categories.
- Unified recurring rules through `RecurringEntry` for account movements and credit-card expenses.
- Credit cards with closing/due dates and automatic installment generation.
- Individual and bulk credit-card purchase creation and installment payment tracking.
- Monthly cash-flow projections, budgets, saving goals, and investments.
- Fiat and crypto currencies with manual and market-synced exchange rates.
- Scheduled USD-to-ARS exchange-rate synchronization.
- Dashboard in USD or ARS with KPIs and interactive charts.
- Spanish and English interface with a persistent language preference.
- Responsive dark UI.
- Private ChatGPT Actions integration with scoped, revocable tokens.

A transaction is always a materialized movement. Recurrence configuration lives only in `recurring_entries`; generated transactions and purchases reference their originating rule through `recurring_entry_id`.

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
        | recurring entries, installments, cash flow, dashboard, exchange rates
        v
SQLAlchemy / PostgreSQL ----> Yahoo Finance
```

---

## Prerequisites

- Docker Desktop 4.x or newer.
- Node.js 20+, Python 3.12+, and PostgreSQL 16 for development without Docker.

## Quick Start (Docker)

```bash
git clone <repo-url>
cd TallyNorth
cp backend/.env.example backend/.env
# Set a long random JWT_SECRET_KEY in backend/.env

docker compose up --build
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

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
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

## Database migrations

```bash
cd backend
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "your message"
```

The current recurrence model uses `recurring_entries`. Legacy recurrence columns on `transactions` are removed by migration; new code must not add transaction-level recurrence flags back.

## Project structure

```text
TallyNorth/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routers/
│   │   └── services/
│   ├── alembic/
│   ├── scripts/seed_demo.py
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── proxy.ts
│   └── Dockerfile
├── docker-compose.yml
├── vercel.json
└── README.md
```

## API overview

Financial endpoints require an authenticated user. In local development, the main API prefix is `/api/v1` and authentication is under `/api/auth`.

| Resource | Endpoints |
|---|---|
| Authentication | Register, login, logout, and current-user endpoints under `/api/auth` |
| Accounts | `GET/POST /api/v1/accounts/` - `GET/PUT/DELETE /api/v1/accounts/{id}` |
| Categories | CRUD under `/api/v1/categories` |
| Credit Cards | `GET/POST /api/v1/credit-cards/` - `GET/PUT/DELETE /api/v1/credit-cards/{id}` - installments lookup |
| Transactions | `GET/POST /api/v1/transactions/` - `GET/PUT/DELETE /api/v1/transactions/{id}` |
| Recurring entries | `GET/POST /api/v1/recurring-entries/` - `PUT/DELETE /api/v1/recurring-entries/{id}` |
| Purchases | CRUD and bulk creation under `/api/v1/purchases` |
| Installments | Update payment state under `/api/v1/installments/{id}` |
| Cashflow | Projection, summary, and dashboard under `/api/v1/cashflow` |
| Budgets | CRUD under `/api/v1/budgets` |
| Saving goals | CRUD under `/api/v1/saving-goals` |
| Investments | CRUD under `/api/v1/investments` |
| Currencies | CRUD under `/api/v1/currencies` |
| Exchange rates | CRUD, quote lookup, and market sync under `/api/v1/exchange-rates` |
| Dashboard | Consolidated summary under `/api/v1/dashboard/summary` |
| Integration tokens | Issue, list, and revoke scoped tokens under `/api/v1/integration-tokens` |
| ChatGPT Actions | Curated endpoints under `/api/v1/integrations/chatgpt` |

Full interactive docs are available at **http://localhost:8000/docs**.

## ChatGPT Actions

TallyNorth can be connected to a private Custom GPT using a dedicated, revocable Bearer token and a curated OpenAPI schema.

The GPT surface currently exposes:

- context, summary, cashflow, movement, installment, recurring-rule, and account-balance queries;
- one-off transaction creation;
- recurring-entry creation;
- credit-card purchase creation;
- atomic batch creation for one-off movements and purchases;
- account-balance reconciliation;
- category creation.

Recurring rules are created with `createRecurringEntry`, never by adding recurrence fields to `createTransaction`.

See [backend/CHATGPT_ACTIONS.md](backend/CHATGPT_ACTIONS.md) for the exact contract and GPT instructions.

## Credit-card installment logic

- If `purchase_date.day <= closing_day`, the first installment is due on `due_day` of the same month.
- If `purchase_date.day > closing_day`, the first installment is due on `due_day` of the next month.
- Subsequent installments advance one calendar month.
- Missing due days in shorter months are clamped to the month's final day.
- Amounts use decimal arithmetic and `ROUND_HALF_UP` to two decimal places.

## Exchange-rate synchronization

Rates can be entered manually or fetched from Yahoo Finance. A configurable asynchronous scheduler starts with the FastAPI lifecycle and, by default, attempts to update USD to ARS at 00:00, 08:00, and 16:00 in the server's local timezone.

Synchronization updates an existing record for the currency pair and date instead of creating duplicates. Yahoo Finance is an external dependency; production deployments should evaluate a provider with appropriate licensing and availability guarantees.

## Authentication and authorization

- Passwords are hashed with bcrypt.
- Login returns a signed JWT with a seven-day expiration.
- The backend accepts the token from a Bearer header or the `token` cookie.
- Next.js stores browser sessions in an `HttpOnly`, `SameSite=Lax` cookie.
- Protected routes are handled by the Next.js 16 `proxy.ts` convention.
- Backend queries scope financial resources to the authenticated user.

## Tests and deployment

Backend tests live under `backend/tests/`. Database integration tests that mutate data require an explicitly configured disposable database. Vercel preview deployments compile both the Next.js frontend and Python backend for branch validation.

There is currently no repository-level CI workflow that automatically runs the full backend test suite on every push.

## Production considerations

Before storing real financial data on a public server:

- use a long random `JWT_SECRET_KEY` and HTTPS;
- configure a precise `FRONTEND_URL` and keep `ALLOW_ALL_ORIGINS=False`;
- replace default PostgreSQL and pgAdmin credentials;
- do not expose PostgreSQL or pgAdmin publicly;
- use encrypted storage and automated backups;
- add rate limiting, monitoring, and security scanning;
- run automated tests and review proxy, cookie, CORS, and route-prefix behavior;
- conduct a security review.

## Current limitations

- No repository-level CI workflow currently runs all tests automatically.
- Investment values are entered manually; there is no historical price series.
- Scheduled jobs run in the API process rather than a dedicated worker.
- Payments and bank integrations are not implemented.
- Deployment-oriented configuration exists, but production operation is not guaranteed.
