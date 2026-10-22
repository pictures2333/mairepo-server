from typing import Optional

import aiohttp

from src.settings import settings

session: Optional[aiohttp.ClientSession] = None


async def init_drive() -> None:
    global session

    if session is not None and not session.closed:
        return

    session = aiohttp.ClientSession(
        headers={"X-Goog-Api-Key": settings.GOOGLE_DRIVE_API_KEY},
    )


async def close_drive() -> None:
    global session

    client = session
    session = None

    if client is not None:
        await client.close()
