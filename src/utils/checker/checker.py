from typing import List, Optional, Tuple
import pathlib

from src.settings import settings
from src.core import log
from src.database import database
from src import crud

logger = log.get_logger("mairepo.checker")


# Functions

async def check_work() -> None:
    logger.info("Integrity check started.")

    storage_directory = pathlib.Path(settings.DIRECTORY).resolve(strict=True)
    if not storage_directory.is_dir():
        raise RuntimeError("Storage path is not a directory.")

    # Find blobs that do not point to an available storage file
    async with database.with_session() as session:
        blobs = await crud.read_blobs(session)

    invalid_blobs:List[Tuple[int, Optional[int]]] = []
    for blob in blobs:
        try:
            blob_path = pathlib.Path(blob.path).resolve(strict=True)
        except (OSError, RuntimeError):
            invalid_blobs.append((blob.id, blob.file_id))
            continue

        if (
            not blob_path.is_relative_to(storage_directory)
            or not blob_path.is_file()
        ):
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
        logger.exception(f"Integrity check failed : {str(exc)}")
        raise
