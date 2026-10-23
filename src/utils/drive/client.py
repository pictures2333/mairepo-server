from typing import Optional

from google.auth.transport.requests import Request
from google.auth.exceptions import GoogleAuthError
from google.oauth2 import service_account
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random
)
import asyncio
import aiohttp

from src.settings import settings
from .retry import should_retry
from . import constants

session:Optional[aiohttp.ClientSession] = None
session_lock = asyncio.Lock()
credentials = service_account.Credentials.from_service_account_file(
    settings.GOOGLE_SERVICE_ACCOUNT_CRED_FILE,
    scopes=[
        "https://www.googleapis.com/auth/drive.readonly"
    ]
)


# client lifecycle

async def init_drive() -> None:
    global session

    async with session_lock:
        if session is not None and not session.closed:
            return

        session = aiohttp.ClientSession()
        await _refresh_token_refresh()
    
    return


async def close_drive() -> None:
    global session

    async with session_lock:
        client = session
        session = None

    if client is not None:
        await client.close()

    return


# refresh

@retry(
    retry=retry_if_exception(should_retry),
    stop=stop_after_attempt(3),
    wait=wait_random(1, 3),
    reraise=True
)
async def _refresh_token_fail_test() -> bool:
    if session is None or session.closed:
        raise RuntimeError("Session is not initialized.")

    async with session.get(
        constants.DRIVE_API_BASE_URL,
        params = {
            "pageSize": "1",
            "fields": "files(id)",
        }
    ) as response:
        if response.status == 401:
            return False

        response.raise_for_status()
        return True


async def _refresh_token_refresh() -> None:
    global session
    
    if session is None or session.closed:
        raise RuntimeError("Session is not initialized.")

    try:
        await asyncio.to_thread(credentials.refresh, Request())
    except Exception:
        raise
    if credentials.token is None or not credentials.valid:
        raise GoogleAuthError

    session.headers["Authorization"] = f"Bearer {credentials.token}"
    return


async def refresh_drive_token() -> None:
    async with session_lock:
        if session is None or session.closed:
            raise RuntimeError("Session is not initialized.")

        if (await _refresh_token_fail_test()):
            return

        await _refresh_token_refresh()

    return


# helpers

def get_session() -> aiohttp.ClientSession:
    if session is None or session.closed:
        raise RuntimeError("Session is not initialized.")
    
    return session


async def request(method:str, url:str, **kwargs) -> aiohttp.ClientResponse:
    if session is None or session.closed:
        raise RuntimeError("Session is not initialized.")
    
    response = await session.request(method, url, **kwargs)
    if response.status == 401:
        response.release()
        await refresh_drive_token()
        response = await session.request(method, url, **kwargs)

    return response
