from copy import deepcopy


ACTION_ROOT = "/integrations/chatgpt"


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
        normalized_path = source_path[root_index:]
        selected_paths[normalized_path] = deepcopy(path_item)

    for path_item in selected_paths.values():
        for method, operation in path_item.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            operation["security"] = [{"bearerAuth": []}]

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "TallyNorth GPT Actions",
            "description": (
                "Consulta información financiera y ejecuta cargas confirmadas "
                "para el usuario autenticado."
            ),
            "version": "1.1.0",
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
