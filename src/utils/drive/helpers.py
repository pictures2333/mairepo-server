from typing import Optional

def escape_query_literal(value: str) -> str:
    if not value:
        raise ValueError("Google Drive folder ID cannot be empty.")

    return value.replace("\\", "\\\\").replace("'", "\\'")


def build_resource_key_headers(
    resource_id: str,
    resource_key: Optional[str],
) -> dict[str, str]:
    if resource_key is None:
        return {}
    if not resource_key:
        raise ValueError("Google Drive resource key cannot be empty.")

    return {"X-Goog-Drive-Resource-Keys": f"{resource_id}/{resource_key}"}
