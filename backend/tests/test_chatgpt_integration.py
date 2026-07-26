import unittest
import uuid
from datetime import date
from decimal import Decimal

from pydantic import ValidationError

from app.schemas.integration import ChatGPTTransactionCreate
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
        self.assertEqual(
            set(schema["paths"]),
            {
                "/integrations/chatgpt/context",
                "/integrations/chatgpt/transactions",
                "/integrations/chatgpt/purchases",
            },
        )
        self.assertFalse(
            schema["paths"]["/integrations/chatgpt/context"]["get"][
                "x-openai-isConsequential"
            ]
        )
        self.assertTrue(
            schema["paths"]["/integrations/chatgpt/transactions"]["post"][
                "x-openai-isConsequential"
            ]
        )
        self.assertTrue(
            schema["paths"]["/integrations/chatgpt/purchases"]["post"][
                "x-openai-isConsequential"
            ]
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
