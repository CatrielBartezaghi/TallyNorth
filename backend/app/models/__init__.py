"""
SQLAlchemy models package.
Import all models here so Alembic can detect them automatically.
"""

from app.models.currency import Currency  # noqa: F401
from app.models.category import Category  # noqa: F401
from app.models.account import Account  # noqa: F401
from app.models.credit_card import CreditCard  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401
from app.models.purchase import CreditCardPurchase  # noqa: F401
from app.models.installment import Installment  # noqa: F401
from app.models.budget import Budget  # noqa: F401
from app.models.saving_goal import SavingGoal  # noqa: F401
from app.models.investment import Investment  # noqa: F401
from app.models.exchange_rate import ExchangeRate  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.integration_token import GptActionRequest, IntegrationToken  # noqa: F401
