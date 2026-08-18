import uuid
import unittest

from pydantic import ValidationError

from app.main import app
from app.models.transaction import Transaction
from app.schemas.integration import ChatGPTRecurringEntryCreate, ChatGPTTransactionCreate
from app.schemas.transaction import TransactionCreate
from app.services.chatgpt_openapi import build_chatgpt_action_openapi


class RecurrenceContractTests(unittest.TestCase):
    def setUp(self):
        self.account_id = uuid.uuid4()
        self.category_id = uuid.uuid4()

    def test_transaction_model_has_no_legacy_recurrence_columns(self):
        column_names = set(Transaction.__table__.columns.keys())
        self.assertNotIn("is_recurring", column_names)
        self.assertNotIn("recurrence_rule", column_names)
        self.assertNotIn("end_date", column_names)
        self.assertNotIn("parent_id", column_names)
        self.assertIn("recurring_entry_id", column_names)

    def test_standard_transaction_rejects_legacy_recurrence_fields(self):
        with self.assertRaises(ValidationError):
            TransactionCreate.model_validate(
                {
                    "account_id": self.account_id,
                    "category_id": self.category_id,
                    "type": "income",
                    "amount": 1900000,
                    "description": "Salario",
                    "date": "2026-09-01",
                    "is_recurring": True,
                    "recurrence_rule": "monthly",
                }
            )

    def test_chatgpt_transaction_rejects_legacy_recurrence_fields(self):
        with self.assertRaises(ValidationError):
            ChatGPTTransactionCreate.model_validate(
                {
                    "idempotency_key": "salary-legacy-001",
                    "account_id": self.account_id,
                    "category_id": self.category_id,
                    "type": "income",
                    "amount": 1900000,
                    "description": "Salario",
                    "date": "2026-09-01",
                    "is_recurring": True,
                    "recurrence_rule": "monthly",
                }
            )

    def test_chatgpt_recurring_entry_uses_canonical_contract(self):
        payload = ChatGPTRecurringEntryCreate.model_validate(
            {
                "idempotency_key": "salary-recurring-001",
                "type": "income",
                "amount": 1900000,
                "description": "Salario",
                "category_id": self.category_id,
                "frequency": "monthly",
                "start_date": "2026-09-01",
                "end_date": None,
                "active": True,
                "destination_type": "account",
                "account_id": self.account_id,
                "credit_card_id": None,
            }
        )
        self.assertEqual(payload.frequency, "monthly")
        self.assertEqual(payload.account_id, self.account_id)

    def test_chatgpt_openapi_exposes_recurring_actions_separately(self):
        schema = build_chatgpt_action_openapi("https://example.test/api/v1", app.openapi())
        recurring_path = schema["paths"]["/integrations/chatgpt/recurring-entries"]
        self.assertEqual(recurring_path["get"]["operationId"], "listRecurringEntries")
        self.assertEqual(recurring_path["post"]["operationId"], "createRecurringEntry")

        transaction_schema = schema["components"]["schemas"]["ChatGPTTransactionCreate"]
        properties = transaction_schema["properties"]
        self.assertNotIn("is_recurring", properties)
        self.assertNotIn("recurrence_rule", properties)
        self.assertNotIn("end_date", properties)


if __name__ == "__main__":
    unittest.main()
