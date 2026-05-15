from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    accounts,
    budgets,
    cashflow,
    categories,
    credit_cards,
    currencies,
    dashboard,
    exchange_rates,
    installments,
    investments,
    purchases,
    saving_goals,
    transactions,
    auth,
)

app = FastAPI(
    title="TallyNorth API",
    description="Personal finance platform - cashflow projection and credit card installment tracking",
    version="0.1.0",
)

import os

# ---------------------------------------------------------------------------
# CORS - allow the Next.js dev server and production domains
# ---------------------------------------------------------------------------
# In production, you can set FRONTEND_URL to your Vercel domain
frontend_url = os.getenv("FRONTEND_URL", "")
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

if frontend_url:
    # also allow variations like https://frontend_url and plain string
    if not frontend_url.startswith("http"):
        allowed_origins.append(f"https://{frontend_url}")
    else:
        allowed_origins.append(frontend_url)

# Set ALLOW_ALL_ORIGINS=True if you want a public API without credentials restrictions
allow_all = os.getenv("ALLOW_ALL_ORIGINS", "False").lower() == "true"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else allowed_origins,
    allow_credentials=not allow_all, # Can't be true if origins is ["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
# Vercel's multi-service automatically strips the '/api' prefix from the URL
# before sending it to the backend. In local development, we keep it.
route_base = "" if os.getenv("VERCEL") else "/api"
API_PREFIX = f"{route_base}/v1"

app.include_router(accounts.router, prefix=API_PREFIX)
app.include_router(categories.router, prefix=API_PREFIX)
app.include_router(credit_cards.router, prefix=API_PREFIX)
app.include_router(transactions.router, prefix=API_PREFIX)
app.include_router(purchases.router, prefix=API_PREFIX)
app.include_router(installments.router, prefix=API_PREFIX)
app.include_router(cashflow.router, prefix=API_PREFIX)
app.include_router(currencies.router, prefix=API_PREFIX)
app.include_router(budgets.router, prefix=API_PREFIX)
app.include_router(saving_goals.router, prefix=API_PREFIX)
app.include_router(investments.router, prefix=API_PREFIX)
app.include_router(exchange_rates.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=f"{route_base}/auth")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "tallynorth-backend"}
