import asyncio

from src.settings import settings
from src.utils.sync import sync
from src.utils.gc import gc


# Lock

scheduler_lock = asyncio.Lock()


# Scheduler

async def run_sync_scheduler() -> None:
    while True:
        async with scheduler_lock:
            try:
                await sync()
            except Exception:
                # sync() already logs its failure.
                pass

        await asyncio.sleep(settings.RUN_SYNC_INTERVAL)


async def run_gc_scheduler() -> None:
    while True:
        async with scheduler_lock:
            try:
                await gc()
            except Exception:
                # gc() already logs its failure.
                pass

        await asyncio.sleep(settings.RUN_GC_INTERVAL)

