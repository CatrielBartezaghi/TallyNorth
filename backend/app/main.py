import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    accounts,
    assistant,
    budgets,
    cashflow,
    categories,
    chatgpt_account_actions,
    chatgpt_actions,
    chatgpt_category_actions,
    credit_cards,
    currencies,
    dashboard,
    exchange_rates,
    installments,
    integration_tokens,
    investments,
    purchases,
    recurring_entries,
    saving_goals,
    transactions,
    auth,
)
from app.services.exchange_rate_scheduler import start_exchange_rate_cron, stop_exchange_rate_cron


@asynccontextmanager
async def lifespan(app: FastAPI):
    exchange_rate_task = start_exchange_rate_cron()
    try:
        yield
    finally:
        await stop_exchange_rate_cron(exchange_rate_task)

app = FastAPI(
    title="TallyNorth API",
    description="Personal finance platform - cashflow projection and credit card installment tracking",
    version="0.1.0",
    lifespan=lifespan,
)

frontend_url = os.getenv("FRONTEND_URL", "")
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

if frontend_url:
    if not frontend_url.startswith("http"):
        allowed_origins.append(f"https://{frontend_url}")
    else:
        allowed_origins.append(frontend_url)

allow_all = os.getenv("ALLOW_ALL_ORIGINS", "False").lower() == "true"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else allowed_origins,
    allow_credentials=not allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

route_base = "" if settings.environment == "production" else "/api"
API_PREFIX = f"{route_base}/v1"

app.include_router(accounts.router, prefix=API_PREFIX)
app.include_router(assistant.router, prefix=API_PREFIX)
app.include_router(chatgpt_actions.router, prefix=API_PREFIX)
app.include_router(chatgpt_account_actions.router, prefix=API_PREFIX)
app.include_router(chatgpt_category_actions.router, prefix=API_PREFIX)
app.include_router(integration_tokens.router, prefix=API_PREFIX)
app.include_router(categories.router, prefix=API_PREFIX)
app.include_router(credit_cards.router, prefix=API_PREFIX)
app.include_router(transactions.router, prefix=API_PREFIX)
app.include_router(recurring_entries.router, prefix=API_PREFIX)
app.include_router(purchases.router, prefix=API_PREFIX)
app.include_router(installments.router, prefix=API_PREFIX)
app.include_router(cashflow.router, prefix=API_PREFIX)
app.include_router(currencies.router, prefix=API_PREFIX)
app.include_router(budgets.router, prefix=API_PREFIX)
app.include_router(saving_goals.router, prefix=API_PREFIX)
app.include_router(investments.router, prefix=API_PREFIX)
app.include_router(exchange_rates.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=route_base)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "tallynorth-backend"}
