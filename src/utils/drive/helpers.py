from typing import Optional

import aiohttp

from . import client


def get_session() -> aiohttp.ClientSession:
    if client.session is None or client.session.closed:
        raise RuntimeError("Google Drive client is not initialized.")

    return client.session


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
