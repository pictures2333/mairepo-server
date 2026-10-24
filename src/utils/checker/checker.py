from typing import List, Optional, Tuple

from src.core import log
from src.database import database
from src.utils.storage import resolve_storage_directory, resolve_storage_file
from src import crud

logger = log.get_logger("mairepo.checker")


# Functions

async def check_work() -> None:
    logger.info("Integrity check started.")
    resolve_storage_directory()

    # Find blobs that do not point to an available storage file
    async with database.with_session() as session:
        blobs = await crud.read_blobs(session)

    invalid_blobs:List[Tuple[int, Optional[int]]] = []
    for blob in blobs:
        if resolve_storage_file(blob.path) is None:
            invalid_blobs.append((blob.id, blob.file_id))

    # Delete invalid blobs and repair their files
    affected_file_ids = {
        file_id
        for _, file_id in invalid_blobs
        if file_id is not None
    }
    repaired_file_count = 0
    deleted_file_count = 0

    async with database.with_session() as session:
        async with session.begin():
            for blob_id, _ in invalid_blobs:
                await crud.delete_blob(session, blob_id)

            for file_id in affected_file_ids:
                remaining_blobs = await crud.read_blobs(
                    session=session,
                    file_id=file_id
                )
                if not remaining_blobs:
                    await crud.delete_file(session=session, id=file_id)
                    deleted_file_count += 1
                    continue

                latest_blob = max(
                    remaining_blobs,
                    key=lambda blob: (blob.created_at, blob.id)
                )
                await crud.update_file(
                    session=session,
                    id=file_id,
                    drive_head_revision_id=latest_blob.drive_revision_id
                )
                repaired_file_count += 1

    logger.info(
        f"Removed {len(invalid_blobs)} invalid blobs, "
        f"repaired {repaired_file_count} files, and "
        f"deleted {deleted_file_count} files."
    )
    logger.info("Integrity check completed.")

    return


async def check() -> None:
    try:
        await check_work()
    except Exception as exc:
        logger.error(f"Integrity check failed : {str(exc)}")
        raise
