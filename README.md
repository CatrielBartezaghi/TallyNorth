# TallyNorth

> [!WARNING]
> **Security Notice:** This application does **not** have an authentication or login system. It is designed to be run locally (`localhost`) for personal use. **Do not deploy this application to a public server** (like Vercel, Render, VPS, etc.) without implementing your own security layer (e.g., Basic Auth proxy), otherwise your financial data will be publicly exposed to anyone on the internet.

Personal finance platform focused on monthly cashflow projection and credit card installment tracking.

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router) - TypeScript - Tailwind CSS - shadcn/ui |
| Backend | FastAPI - Python 3.12 - SQLAlchemy - Alembic |
| Database | PostgreSQL 16 |
| Local Env | Docker Compose |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) >= 4.x
- [Node.js](https://nodejs.org/) >= 20 (only needed for frontend local dev without Docker)
- [Python](https://www.python.org/) >= 3.12 (only needed for backend local dev without Docker)

---

## Quick Start (Docker)

```bash
# 1. Clone the repo
git clone <repo-url>
cd TallyNorth

# 2. Copy env file
cp backend/.env.example backend/.env

# 3. Start all services
docker compose up --build

# 4. Run database migrations (first time only)
docker compose exec backend alembic upgrade head
```

Services:
- **Frontend** -> http://localhost:3000
- **Backend API** -> http://localhost:8000
- **Swagger UI** -> http://localhost:8000/docs
- **ReDoc** -> http://localhost:8000/redoc

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
# Edit DATABASE_URL to point to your local Postgres instance

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

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local`.

---

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
TallyNorth/
frontend/                  # Next.js app
  src/
    app/                   # App Router pages
    components/            # Shared UI components
    lib/
      api.ts               # Typed API client
  Dockerfile

backend/                   # FastAPI app
  app/
    main.py                # FastAPI app + CORS + routers
    config.py              # Pydantic settings
    database.py            # SQLAlchemy engine + get_db
    models/                # ORM models (5 tables)
    schemas/               # Pydantic v2 schemas
    routers/               # API endpoints
    services/
      installment_service.py   # CC installment date logic
      cashflow_service.py      # Monthly projection engine
  alembic/                 # DB migrations
  Dockerfile

docker-compose.yml
README.md
```

---

## API Overview

| Resource | Endpoints |
|---|---|
| Accounts | `GET/POST /api/v1/accounts/` - `GET/PUT/DELETE /api/v1/accounts/{id}` |
| Credit Cards | `GET/POST /api/v1/credit-cards/` - `GET/PUT/DELETE /api/v1/credit-cards/{id}` - `GET /api/v1/credit-cards/{id}/installments` |
| Transactions | `GET/POST /api/v1/transactions/` - `GET/PUT/DELETE /api/v1/transactions/{id}` |
| Purchases | `GET/POST /api/v1/purchases/` - `GET/DELETE /api/v1/purchases/{id}` |
| Cashflow | `GET /api/v1/cashflow/projection` - `GET /api/v1/cashflow/summary` - `GET /api/v1/cashflow/dashboard` |

Full interactive docs at **http://localhost:8000/docs**.

---

## Credit Card Installment Logic

The installment service follows the standard Argentine convention:

- If `purchase_date.day <= closing_day` -> first installment due on `due_day` of the **same** month.
- If `purchase_date.day > closing_day` -> first installment due on `due_day` of the **next** month.

Subsequent installments advance one calendar month each.

---

## MVP Scope

- [x] Register financial accounts
- [x] Register income and expenses
- [x] Register credit cards (with closing/due day)
- [x] Register purchases in installments
- [x] Auto-calculate installment dates
- [x] Monthly cashflow projection
- [x] Dashboard with totals, upcoming dues, and future debt by card

## Out of Scope (for now)

- Authentication / multi-user
- Redis / caching
- AI / investment tracking
- Payments integration
- Production infrastructure
