def build_chatgpt_action_openapi(server_url: str) -> dict:
    """Return the intentionally small API surface imported by a Custom GPT."""

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "TallyNorth GPT Actions",
            "description": (
                "Consulta el contexto financiero del usuario autenticado y crea "
                "movimientos o compras con tarjeta solamente después de su confirmación."
            ),
            "version": "1.0.0",
        },
        "servers": [{"url": server_url.rstrip("/")}],
        "security": [{"bearerAuth": []}],
        "paths": {
            "/integrations/chatgpt/context": {
                "get": {
                    "operationId": "getFinanceContext",
                    "summary": "Obtener cuentas, categorías y tarjetas",
                    "description": (
                        "Consultá este contexto antes de cargar una operación para usar "
                        "identificadores válidos del usuario."
                    ),
                    "x-openai-isConsequential": False,
                    "responses": {
                        "200": {
                            "description": "Contexto financiero disponible",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/FinanceContext"
                                    }
                                }
                            },
                        },
                        "401": {"description": "Token inválido o vencido"},
                        "403": {"description": "Token sin permiso context:read"},
                    },
                }
            },
            "/integrations/chatgpt/transactions": {
                "post": {
                    "operationId": "createTransaction",
                    "summary": "Crear un ingreso o gasto",
                    "description": (
                        "Crea una transacción confirmada. No llamar si falta algún dato, "
                        "hay ambigüedad o el usuario todavía no confirmó el resumen exacto."
                    ),
                    "x-openai-isConsequential": True,
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/TransactionCreate"
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Transacción creada o reintento reconocido",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/TransactionResult"
                                    }
                                }
                            },
                        },
                        "401": {"description": "Token inválido o vencido"},
                        "403": {
                            "description": "Token sin permiso transactions:create"
                        },
                        "404": {
                            "description": "Cuenta o categoría no encontrada para el usuario"
                        },
                        "409": {
                            "description": "Clave de idempotencia reutilizada con otros datos"
                        },
                        "422": {"description": "Datos inválidos o incompatibles"},
                    },
                }
            },
            "/integrations/chatgpt/purchases": {
                "post": {
                    "operationId": "createCreditCardPurchase",
                    "summary": "Crear una compra con tarjeta",
                    "description": (
                        "Crea una compra confirmada y sus cuotas. No llamar si falta algún "
                        "dato, hay ambigüedad o el usuario no confirmó el resumen exacto."
                    ),
                    "x-openai-isConsequential": True,
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/PurchaseCreate"
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Compra creada o reintento reconocido",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/PurchaseResult"
                                    }
                                }
                            },
                        },
                        "401": {"description": "Token inválido o vencido"},
                        "403": {"description": "Token sin permiso purchases:create"},
                        "404": {
                            "description": "Tarjeta o categoría no encontrada para el usuario"
                        },
                        "409": {
                            "description": "Clave de idempotencia reutilizada con otros datos"
                        },
                        "422": {"description": "Datos inválidos o incompatibles"},
                    },
                }
            },
        },
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": (
                        "Token de integración de TallyNorth con prefijo tn_gpt_."
                    ),
                }
            },
            "schemas": {
                "Account": {
                    "type": "object",
                    "required": ["id", "name", "type", "currency"],
                    "properties": {
                        "id": {"type": "string", "format": "uuid"},
                        "name": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": ["checking", "savings", "cash"],
                        },
                        "currency": {"type": "string"},
                    },
                },
                "Category": {
                    "type": "object",
                    "required": ["id", "name", "type"],
                    "properties": {
                        "id": {"type": "string", "format": "uuid"},
                        "name": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": ["income", "expense", "both"],
                        },
                    },
                },
                "CreditCard": {
                    "type": "object",
                    "required": [
                        "id",
                        "name",
                        "currency",
                        "closing_day",
                        "due_day",
                    ],
                    "properties": {
                        "id": {"type": "string", "format": "uuid"},
                        "name": {"type": "string"},
                        "currency": {"type": "string"},
                        "closing_day": {"type": "integer"},
                        "due_day": {"type": "integer"},
                    },
                },
                "FinanceContext": {
                    "type": "object",
                    "required": [
                        "current_date",
                        "timezone",
                        "accounts",
                        "categories",
                        "credit_cards",
                    ],
                    "properties": {
                        "current_date": {"type": "string", "format": "date"},
                        "timezone": {"type": "string"},
                        "accounts": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Account"},
                        },
                        "categories": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Category"},
                        },
                        "credit_cards": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/CreditCard"},
                        },
                    },
                },
                "TransactionCreate": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "idempotency_key",
                        "account_id",
                        "type",
                        "amount",
                        "description",
                        "date",
                    ],
                    "properties": {
                        "idempotency_key": {
                            "type": "string",
                            "minLength": 8,
                            "maxLength": 128,
                            "description": (
                                "UUID nuevo por operación confirmada; conservarlo al "
                                "reintentar exactamente la misma solicitud."
                            ),
                        },
                        "account_id": {"type": "string", "format": "uuid"},
                        "category_id": {"type": "string", "format": "uuid"},
                        "type": {
                            "type": "string",
                            "enum": ["income", "expense"],
                        },
                        "amount": {
                            "type": "number",
                            "exclusiveMinimum": 0,
                            "description": "Importe positivo, sin símbolo de moneda.",
                        },
                        "description": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 255,
                        },
                        "date": {"type": "string", "format": "date"},
                        "is_recurring": {
                            "type": "boolean",
                            "default": False,
                        },
                        "recurrence_rule": {
                            "type": "string",
                            "enum": ["monthly", "weekly", "yearly"],
                        },
                        "end_date": {"type": "string", "format": "date"},
                    },
                },
                "PurchaseCreate": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "idempotency_key",
                        "credit_card_id",
                        "description",
                        "total_amount",
                        "installments",
                        "purchase_date",
                    ],
                    "properties": {
                        "idempotency_key": {
                            "type": "string",
                            "minLength": 8,
                            "maxLength": 128,
                            "description": (
                                "UUID nuevo por operación confirmada; conservarlo al "
                                "reintentar exactamente la misma solicitud."
                            ),
                        },
                        "credit_card_id": {"type": "string", "format": "uuid"},
                        "category_id": {"type": "string", "format": "uuid"},
                        "description": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 255,
                        },
                        "total_amount": {
                            "type": "number",
                            "exclusiveMinimum": 0,
                        },
                        "installments": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 120,
                        },
                        "starting_installment": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 1,
                        },
                        "purchase_date": {"type": "string", "format": "date"},
                    },
                },
                "Transaction": {
                    "type": "object",
                    "required": [
                        "id",
                        "account_id",
                        "type",
                        "amount",
                        "description",
                        "date",
                        "created_at",
                    ],
                    "properties": {
                        "id": {"type": "string", "format": "uuid"},
                        "account_id": {"type": "string", "format": "uuid"},
                        "category_id": {"type": "string", "format": "uuid"},
                        "type": {
                            "type": "string",
                            "enum": ["income", "expense"],
                        },
                        "amount": {
                            "anyOf": [
                                {"type": "number"},
                                {"type": "string"},
                            ]
                        },
                        "description": {"type": "string"},
                        "date": {"type": "string", "format": "date"},
                        "created_at": {
                            "type": "string",
                            "format": "date-time",
                        },
                    },
                },
                "Purchase": {
                    "type": "object",
                    "required": [
                        "id",
                        "credit_card_id",
                        "description",
                        "total_amount",
                        "installments",
                        "installment_amount",
                        "purchase_date",
                        "first_installment_date",
                        "created_at",
                    ],
                    "properties": {
                        "id": {"type": "string", "format": "uuid"},
                        "credit_card_id": {
                            "type": "string",
                            "format": "uuid",
                        },
                        "category_id": {"type": "string", "format": "uuid"},
                        "description": {"type": "string"},
                        "total_amount": {
                            "anyOf": [
                                {"type": "number"},
                                {"type": "string"},
                            ]
                        },
                        "installments": {"type": "integer"},
                        "installment_amount": {
                            "anyOf": [
                                {"type": "number"},
                                {"type": "string"},
                            ]
                        },
                        "purchase_date": {
                            "type": "string",
                            "format": "date",
                        },
                        "first_installment_date": {
                            "type": "string",
                            "format": "date",
                        },
                        "created_at": {
                            "type": "string",
                            "format": "date-time",
                        },
                    },
                },
                "TransactionResult": {
                    "type": "object",
                    "required": ["status", "message", "transaction"],
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["created", "already_processed"],
                        },
                        "message": {"type": "string"},
                        "transaction": {
                            "$ref": "#/components/schemas/Transaction"
                        },
                    },
                },
                "PurchaseResult": {
                    "type": "object",
                    "required": ["status", "message", "purchase"],
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["created", "already_processed"],
                        },
                        "message": {"type": "string"},
                        "purchase": {"$ref": "#/components/schemas/Purchase"},
                    },
                },
            },
        },
    }
