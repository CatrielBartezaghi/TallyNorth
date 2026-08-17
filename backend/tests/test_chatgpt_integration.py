import json
import unittest
import uuid
from datetime import date
from decimal import Decimal

from pydantic import ValidationError

from app.routers.chatgpt_actions import _optional_query_date, _optional_query_value
from app.schemas.integration import (
    DEFAULT_INTEGRATION_SCOPES,
    ChatGPTFinanceBatchCreate,
    ChatGPTTransactionCreate,
)
from app.services.chatgpt_openapi import build_chatgpt_action_openapi
from app.services.gpt_action_idempotency import action_request_hash
from app.services.integration_tokens import (
    TOKEN_PREFIX,
    generate_integration_token,
    hash_integration_token,
)


class IntegrationTokenTests(unittest.TestCase):
    def test_generated_tokens_are_prefixed_and_unique(self):
        first = generate_integration_token()
        second = generate_integration_token()

        self.assertTrue(first.startswith(TOKEN_PREFIX))
        self.assertNotEqual(first, second)
        self.assertEqual(len(hash_integration_token(first)), 64)


class ChatGPTActionSchemaTests(unittest.TestCase):
    def test_openapi_exposes_only_expected_actions(self):
        schema = build_chatgpt_action_openapi(
            "https://finance.example.com/api/v1"
        )

        self.assertEqual(
            schema["servers"][0]["url"],
            "https://finance.example.com/api/v1",
        )
        expected_paths = {
            "/integrations/chatgpt/context",
            "/integrations/chatgpt/summary",
            "/integrations/chatgpt/cashflow",
            "/integrations/chatgpt/entries",
            "/integrations/chatgpt/installments",
            "/integrations/chatgpt/transactions",
            "/integrations/chatgpt/purchases",
            "/integrations/chatgpt/entries/batch",
            "/integrations/chatgpt/budgets",
            "/integrations/chatgpt/saving-goals",
            "/integrations/chatgpt/saving-goal-progress",
            "/integrations/chatgpt/investments",
            "/integrations/chatgpt/investment-valuations",
            "/integrations/chatgpt/installment-payments",
            "/integrations/chatgpt/account-balances",
        }
        self.assertEqual(set(schema["paths"]), expected_paths)

        operation_ids = set()
        for path_item in schema["paths"].values():
            for method, operation in path_item.items():
                if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                    continue
                operation_ids.add(operation["operationId"])
                self.assertEqual(
                    operation["x-openai-isConsequential"],
                    method != "get",
                )

        self.assertEqual(len(operation_ids), 16)
        self.assertIn("getAccountBalances", operation_ids)
        self.assertIn("setAccountBalance", operation_ids)

    def test_optional_query_parameters_do_not_advertise_literal_null(self):
        schema = build_chatgpt_action_openapi(
            "https://finance.example.com/api/v1"
        )
        parameters = schema["paths"]["/integrations/chatgpt/summary"]["get"]["parameters"]

        for parameter in parameters:
            self.assertNotIn(
                {"type": "null"},
                parameter["schema"].get("anyOf", []),
            )

    def test_summary_query_values_accept_action_null_placeholders(self):
        for nullish in (None, "", " ", "null", "None", "undefined"):
            self.assertIsNone(_optional_query_value(nullish))
            self.assertIsNone(_optional_query_date(nullish, "date_from"))

        self.assertEqual(
            _optional_query_date("2026-07-27", "date_from"),
            date(2026, 7, 27),
        )

    def test_openapi_respects_gpt_action_limits(self):
        schema = build_chatgpt_action_openapi(
            "https://finance.example.com/api/v1"
        )

        self.assertLess(len(json.dumps(schema)), 100_000)
        for path_item in schema["paths"].values():
            for method, operation in path_item.items():
                if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                    continue
                self.assertLessEqual(len(operation.get("summary", "")), 300)
                self.assertLessEqual(len(operation.get("description", "")), 300)
                for parameter in operation.get("parameters", []):
                    self.assertLessEqual(len(parameter.get("description", "")), 700)

    def test_default_token_scopes_cover_expanded_actions(self):
        self.assertEqual(
            set(DEFAULT_INTEGRATION_SCOPES),
            {
                "context:read",
                "transactions:create",
                "purchases:create",
                "budgets:write",
                "saving_goals:write",
                "investments:write",
                "installments:pay",
            },
        )

    def test_batch_is_limited_to_fifty_entries(self):
        entry = {
            "kind": "transaction",
            "account_id": str(uuid.uuid4()),
            "type": "expense",
            "amount": 1,
            "description": "Test",
            "date": "2026-07-26",
        }
        with self.assertRaises(ValidationError):
            ChatGPTFinanceBatchCreate(
                idempotency_key="batch-limit-test",
                entries=[entry] * 51,
            )

    def test_idempotency_hash_excludes_the_key(self):
        common = {
            "account_id": uuid.uuid4(),
            "type": "expense",
            "amount": Decimal("123.45"),
            "description": "Test",
            "date": date(2026, 7, 26),
        }
        first = ChatGPTTransactionCreate(
            idempotency_key="request-0001",
            **common,
        )
        second = ChatGPTTransactionCreate(
            idempotency_key="request-0002",
            **common,
        )

        self.assertEqual(action_request_hash(first), action_request_hash(second))

    def test_recurring_transaction_requires_rule(self):
        with self.assertRaises(ValidationError):
            ChatGPTTransactionCreate(
                idempotency_key="request-0001",
                account_id=uuid.uuid4(),
                type="expense",
                amount=Decimal("123.45"),
                description="Test",
                date=date(2026, 7, 26),
                is_recurring=True,
            )


if __name__ == "__main__":
    unittest.main()
