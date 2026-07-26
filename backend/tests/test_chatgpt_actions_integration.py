import os
import unittest
import uuid
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.credit_card import CreditCard
from app.models.currency import Currency
from app.models.installment import Installment
from app.models.integration_token import IntegrationToken
from app.models.investment import Investment
from app.models.purchase import CreditCardPurchase
from app.models.saving_goal import SavingGoal
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.integration import IntegrationTokenCreate
from app.services.auth import create_access_token
from app.services.integration_tokens import create_integration_token


@unittest.skipUnless(
    os.getenv("RUN_DB_INTEGRATION_TESTS") == "1",
    "Set RUN_DB_INTEGRATION_TESTS=1 against a disposable database",
)
class ChatGPTActionsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        currency = cls.db.query(Currency).filter(Currency.code == "ARS").one()
        cls.currency = currency
        cls.user = User(
            email=f"gpt-test-{uuid.uuid4()}@example.com",
            hashed_password="not-used",
        )
        cls.db.add(cls.user)
        cls.db.flush()

        cls.account = Account(
            user_id=cls.user.id,
            name="GPT Test Account",
            type="checking",
            currency_id=currency.id,
            initial_balance=0,
        )
        cls.category = Category(
            user_id=cls.user.id,
            name=f"GPT Test Expense {uuid.uuid4()}",
            type="expense",
            color="#000000",
            is_active=True,
        )
        cls.card = CreditCard(
            user_id=cls.user.id,
            name="GPT Test Card",
            closing_day=20,
            due_day=10,
            currency_id=currency.id,
        )
        cls.db.add_all([cls.account, cls.category, cls.card])
        cls.db.commit()
        cls.db.refresh(cls.account)
        cls.db.refresh(cls.category)
        cls.db.refresh(cls.card)

        cls.integration_token, cls.raw_token = create_integration_token(
            cls.db,
            cls.user.id,
            IntegrationTokenCreate(name="Integration test"),
        )
        cls.headers = {"Authorization": f"Bearer {cls.raw_token}"}
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.db.close()

    def test_00_account_can_issue_and_revoke_integration_token(self):
        account_jwt = create_access_token({"sub": str(self.user.id)})
        account_headers = {"Authorization": f"Bearer {account_jwt}"}

        created = self.client.post(
            "/api/v1/integration-tokens/",
            headers=account_headers,
            json={"name": "Issued through API"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertTrue(created.json()["token"].startswith("tn_gpt_"))

        revoked = self.client.delete(
            f"/api/v1/integration-tokens/{created.json()['id']}",
            headers=account_headers,
        )
        self.assertEqual(revoked.status_code, 204, revoked.text)

    def test_01_context_is_scoped_to_token_user(self):
        response = self.client.get(
            "/api/v1/integrations/chatgpt/context",
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(
            [account["name"] for account in payload["accounts"]],
            ["GPT Test Account"],
        )
        self.assertEqual(
            [card["name"] for card in payload["credit_cards"]],
            ["GPT Test Card"],
        )

    def test_02_transaction_is_idempotent(self):
        request_payload = {
            "idempotency_key": "integration-transaction-0001",
            "account_id": str(self.account.id),
            "category_id": str(self.category.id),
            "type": "expense",
            "amount": 1234.56,
            "description": "GPT integration test",
            "date": "2026-07-26",
        }

        first = self.client.post(
            "/api/v1/integrations/chatgpt/transactions",
            headers=self.headers,
            json=request_payload,
        )
        second = self.client.post(
            "/api/v1/integrations/chatgpt/transactions",
            headers=self.headers,
            json=request_payload,
        )

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json()["status"], "created")
        self.assertEqual(second.json()["status"], "already_processed")
        self.assertEqual(
            first.json()["transaction"]["id"],
            second.json()["transaction"]["id"],
        )
        transaction_count = (
            self.db.query(Transaction)
            .filter(
                Transaction.user_id == self.user.id,
                Transaction.description == "GPT integration test",
            )
            .count()
        )
        self.assertEqual(transaction_count, 1)

        conflicting = dict(request_payload, amount=9999)
        conflict_response = self.client.post(
            "/api/v1/integrations/chatgpt/transactions",
            headers=self.headers,
            json=conflicting,
        )
        self.assertEqual(conflict_response.status_code, 409)

    def test_03_purchase_generates_installments(self):
        response = self.client.post(
            "/api/v1/integrations/chatgpt/purchases",
            headers=self.headers,
            json={
                "idempotency_key": "integration-purchase-0001",
                "credit_card_id": str(self.card.id),
                "category_id": str(self.category.id),
                "description": "GPT purchase test",
                "total_amount": 3000,
                "installments": 3,
                "starting_installment": 1,
                "purchase_date": "2026-07-26",
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "created")
        purchase_id = response.json()["purchase"]["id"]
        purchase = (
            self.db.query(CreditCardPurchase)
            .filter(CreditCardPurchase.id == purchase_id)
            .one()
        )
        installment_count = (
            self.db.query(Installment)
            .filter(Installment.purchase_id == purchase.id)
            .count()
        )
        self.assertEqual(installment_count, 3)
        self.assertEqual(purchase.category_id, self.category.id)

    def test_04_mixed_batch_is_atomic_and_idempotent(self):
        payload = {
            "idempotency_key": "integration-batch-0001",
            "entries": [
                {
                    "kind": "transaction",
                    "account_id": str(self.account.id),
                    "category_id": str(self.category.id),
                    "type": "expense",
                    "amount": 321,
                    "description": "GPT batch transaction",
                    "date": "2026-07-26",
                },
                {
                    "kind": "credit_card_purchase",
                    "credit_card_id": str(self.card.id),
                    "category_id": str(self.category.id),
                    "description": "GPT batch purchase",
                    "total_amount": 600,
                    "installments": 2,
                    "starting_installment": 1,
                    "purchase_date": "2026-07-26",
                },
            ],
        }
        first = self.client.post(
            "/api/v1/integrations/chatgpt/entries/batch",
            headers=self.headers,
            json=payload,
        )
        second = self.client.post(
            "/api/v1/integrations/chatgpt/entries/batch",
            headers=self.headers,
            json=payload,
        )
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json()["status"], "created")
        self.assertEqual(second.json()["status"], "already_processed")
        self.assertEqual(first.json()["items"], second.json()["items"])

        invalid = {
            "idempotency_key": "integration-batch-invalid-0001",
            "entries": [
                dict(
                    payload["entries"][0],
                    description="GPT batch must rollback",
                ),
                dict(
                    payload["entries"][1],
                    credit_card_id=str(uuid.uuid4()),
                ),
            ],
        }
        rejected = self.client.post(
            "/api/v1/integrations/chatgpt/entries/batch",
            headers=self.headers,
            json=invalid,
        )
        self.assertEqual(rejected.status_code, 422, rejected.text)
        rollback_count = (
            self.db.query(Transaction)
            .filter(
                Transaction.user_id == self.user.id,
                Transaction.description == "GPT batch must rollback",
            )
            .count()
        )
        self.assertEqual(rollback_count, 0)

    def test_05_budget_goal_and_investment_actions(self):
        budget = self.client.post(
            "/api/v1/integrations/chatgpt/budgets",
            headers=self.headers,
            json={
                "idempotency_key": "integration-budget-0001",
                "category_id": str(self.category.id),
                "currency_id": str(self.currency.id),
                "period_month": "2026-07",
                "amount": 100000,
                "notes": "GPT budget",
            },
        )
        self.assertEqual(budget.status_code, 200, budget.text)
        self.assertEqual(budget.json()["status"], "created")
        budget_update = self.client.post(
            "/api/v1/integrations/chatgpt/budgets",
            headers=self.headers,
            json={
                "idempotency_key": "integration-budget-0002",
                "category_id": str(self.category.id),
                "currency_id": str(self.currency.id),
                "period_month": "2026-07",
                "amount": 120000,
                "expected_current_amount": 100000,
                "notes": "GPT budget updated",
            },
        )
        self.assertEqual(budget_update.status_code, 200, budget_update.text)
        self.assertEqual(budget_update.json()["status"], "updated")

        goal = self.client.post(
            "/api/v1/integrations/chatgpt/saving-goals",
            headers=self.headers,
            json={
                "idempotency_key": "integration-goal-0001",
                "name": "GPT Goal",
                "currency_id": str(self.currency.id),
                "target_amount": 500000,
                "current_amount": 50000,
                "target_date": "2027-01-01",
            },
        )
        self.assertEqual(goal.status_code, 200, goal.text)
        goal_id = goal.json()["saving_goal"]["id"]
        progress = self.client.post(
            "/api/v1/integrations/chatgpt/saving-goal-progress",
            headers=self.headers,
            json={
                "idempotency_key": "integration-goal-progress-0001",
                "goal_id": goal_id,
                "expected_current_amount": 50000,
                "new_current_amount": 75000,
            },
        )
        self.assertEqual(progress.status_code, 200, progress.text)
        self.assertEqual(progress.json()["saving_goal"]["current_amount"], "75000.00")

        investment = self.client.post(
            "/api/v1/integrations/chatgpt/investments",
            headers=self.headers,
            json={
                "idempotency_key": "integration-investment-0001",
                "name": "GPT Investment",
                "type": "fund",
                "currency_id": str(self.currency.id),
                "invested_amount": 200000,
                "current_value": 210000,
            },
        )
        self.assertEqual(investment.status_code, 200, investment.text)
        investment_id = investment.json()["investment"]["id"]
        valuation = self.client.post(
            "/api/v1/integrations/chatgpt/investment-valuations",
            headers=self.headers,
            json={
                "idempotency_key": "integration-investment-value-0001",
                "investment_id": investment_id,
                "expected_current_value": 210000,
                "new_current_value": 215000,
            },
        )
        self.assertEqual(valuation.status_code, 200, valuation.text)
        self.assertEqual(valuation.json()["investment"]["current_value"], "215000.00")

        self.assertEqual(
            self.db.query(Budget).filter(Budget.user_id == self.user.id).count(),
            1,
        )
        self.assertEqual(
            self.db.query(SavingGoal).filter(SavingGoal.user_id == self.user.id).count(),
            1,
        )
        self.assertEqual(
            self.db.query(Investment).filter(Investment.user_id == self.user.id).count(),
            1,
        )

    def test_06_queries_and_installment_payment(self):
        purchase_response = self.client.post(
            "/api/v1/integrations/chatgpt/purchases",
            headers=self.headers,
            json={
                "idempotency_key": "integration-payment-purchase-0001",
                "credit_card_id": str(self.card.id),
                "category_id": str(self.category.id),
                "description": "GPT installment payment test",
                "total_amount": 900,
                "installments": 1,
                "starting_installment": 1,
                "purchase_date": "2026-07-26",
            },
        )
        self.assertEqual(purchase_response.status_code, 200, purchase_response.text)
        purchase_id = purchase_response.json()["purchase"]["id"]
        installment = (
            self.db.query(Installment)
            .filter(Installment.purchase_id == purchase_id)
            .one()
        )

        listed = self.client.get(
            "/api/v1/integrations/chatgpt/installments",
            headers=self.headers,
            params={"status": "pending", "date_from": "2026-01-01"},
        )
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertIn(
            str(installment.id),
            [item["id"] for item in listed.json()["items"]],
        )

        paid = self.client.post(
            "/api/v1/integrations/chatgpt/installment-payments",
            headers=self.headers,
            json={
                "idempotency_key": "integration-installment-payment-0001",
                "installment_id": str(installment.id),
                "paid_account_id": str(self.account.id),
            },
        )
        self.assertEqual(paid.status_code, 200, paid.text)
        self.assertEqual(paid.json()["status"], "paid")

        searched = self.client.get(
            "/api/v1/integrations/chatgpt/entries",
            headers=self.headers,
            params={"q": "GPT", "limit": 50},
        )
        self.assertEqual(searched.status_code, 200, searched.text)
        self.assertTrue(searched.json()["items"])

        projection = self.client.get(
            "/api/v1/integrations/chatgpt/cashflow",
            headers=self.headers,
            params={"currency": "ARS", "months": 3},
        )
        self.assertEqual(projection.status_code, 200, projection.text)
        self.assertEqual(len(projection.json()["months"]), 3)

    def test_99_revoked_token_is_rejected(self):
        token = (
            self.db.query(IntegrationToken)
            .filter(IntegrationToken.id == self.integration_token.id)
            .one()
        )
        token.revoked_at = datetime.now(timezone.utc)
        self.db.commit()

        response = self.client.get(
            "/api/v1/integrations/chatgpt/context",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 401)
