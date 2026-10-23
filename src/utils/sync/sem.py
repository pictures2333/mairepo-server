from typing import TypeVar, Awaitable
import asyncio

from src.settings import settings

sem = asyncio.Semaphore(settings.SYNC_CONCURRENCY)

T = TypeVar("T")

async def apply_sem(func:Awaitable[T]) -> T:
    """
    `await apply_sem(func(...))`
    `func` is an awaitable function
    """
    async with sem:
        return await func
