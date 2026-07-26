import os
import unittest
import uuid
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models.account import Account
from app.models.category import Category
from app.models.credit_card import CreditCard
from app.models.currency import Currency
from app.models.installment import Installment
from app.models.integration_token import IntegrationToken
from app.models.purchase import CreditCardPurchase
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

    def test_04_revoked_token_is_rejected(self):
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
