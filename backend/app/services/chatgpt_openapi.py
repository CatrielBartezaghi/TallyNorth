from copy import deepcopy


ACTION_ROOT = "/integrations/chatgpt"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}

# Keep the Custom GPT surface intentionally small. Other integration endpoints may
# remain available internally without being advertised to the GPT.
ALLOWED_OPERATION_IDS = {
    "getFinanceContext",
    "getFinancialSummary",
    "getCashflowProjection",
    "searchFinanceEntries",
    "getUpcomingInstallments",
    "getAccountBalances",
    "createTransaction",
    "createCreditCardPurchase",
    "createFinanceEntriesBatch",
    "setAccountBalance",
    "createCategory",
}


def _schema_names(value) -> set[str]:
    names: set[str] = set()
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/components/schemas/"):
            names.add(reference.rsplit("/", 1)[-1])
        for child in value.values():
            names.update(_schema_names(child))
    elif isinstance(value, list):
        for child in value:
            names.update(_schema_names(child))
    return names


def _required_schemas(source_schema: dict, paths: dict) -> dict:
    available = source_schema.get("components", {}).get("schemas", {})
    pending = list(_schema_names(paths))
    selected: dict = {}
    while pending:
        name = pending.pop()
        if name in selected or name not in available:
            continue
        selected[name] = deepcopy(available[name])
        pending.extend(_schema_names(available[name]) - selected.keys())
    return selected


def _remove_query_nullability(operation: dict) -> None:
    """Optional query values are represented by omission, never JSON null."""
    for parameter in operation.get("parameters", []):
        if parameter.get("in") != "query" or parameter.get("required", False):
            continue
        schema = parameter.get("schema")
        if not isinstance(schema, dict) or "anyOf" not in schema:
            continue
        non_null = [
            candidate
            for candidate in schema["anyOf"]
            if candidate.get("type") != "null"
        ]
        if len(non_null) != 1:
            continue
        parameter["schema"] = {
            **non_null[0],
            **{key: value for key, value in schema.items() if key != "anyOf"},
        }


def build_chatgpt_action_openapi(
    server_url: str,
    source_schema: dict | None = None,
) -> dict:
    """Return only the API surface intentionally imported by a Custom GPT."""
    if source_schema is None:
        from app.main import app

        source_schema = app.openapi()

    selected_paths: dict = {}
    for source_path, path_item in source_schema.get("paths", {}).items():
        root_index = source_path.find(ACTION_ROOT)
        if root_index < 0 or source_path.endswith("/openapi.json"):
            continue

        selected_operations = {
            method: deepcopy(operation)
            for method, operation in path_item.items()
            if method.lower() in HTTP_METHODS
            and isinstance(operation, dict)
            and operation.get("operationId") in ALLOWED_OPERATION_IDS
        }
        if not selected_operations:
            continue

        normalized_path = source_path[root_index:]
        selected_paths[normalized_path] = selected_operations

    for path_item in selected_paths.values():
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS:
                continue
            operation["security"] = [{"bearerAuth": []}]
            _remove_query_nullability(operation)

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "TallyNorth GPT Actions",
            "description": (
                "Consulta finanzas y registra movimientos, compras, categorías y "
                "ajustes de saldo confirmados para el usuario autenticado."
            ),
            "version": "1.3.0",
        },
        "servers": [{"url": server_url.rstrip("/")}],
        "security": [{"bearerAuth": []}],
        "paths": selected_paths,
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "TallyNorth integration token with tn_gpt_ prefix.",
                }
            },
            "schemas": _required_schemas(source_schema, selected_paths),
        },
    }
