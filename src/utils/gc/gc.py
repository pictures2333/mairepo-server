from typing import List
import os
import pathlib

from src.core import log
from src.database import database
from src import crud
from src.utils.storage import resolve_storage_directory, resolve_storage_file

logger = log.get_logger("mairepo.gc")

# functions

async def gc_work() -> None:
    logger.info("GC started.")

    storage_directory = resolve_storage_directory()

    # Remove orphan blobs and blobs beyond GC_MAX_KEEP
    delete_files:List[pathlib.Path] = []
    try:
        async with database.with_session() as session:
            async with session.begin():
                blobs_beyond_gc_max_keep = await crud.read_blobs(
                    session=session,
                    id=None,
                    file_id=crud.UNSET,
                    limit_to_gc_keep=False
                )
                blobs_orphan = await crud.read_blobs(
                    session=session,
                    id=None,
                    file_id=None,
                    limit_to_gc_keep=None
                )

                blobs_deleted = blobs_beyond_gc_max_keep + blobs_orphan
                for blob in blobs_deleted:
                    delete_files.append(pathlib.Path(blob.path).absolute())
                    await crud.delete_blob(session, blob.id)
    except Exception as exc:
        logger.exception(f"Failed to delete blobs in database : {str(exc)}")
    else:
        unlinked_count = 0
        skipped_count = 0

        for df in delete_files:
            if resolve_storage_file(df) is None:
                logger.warning(f"File is unavailable or outside storage, skipped: {df}")
                skipped_count += 1
                continue

            try:
                os.unlink(df)
            except Exception as exc:
                logger.warning(f"Failed to unlink {df} : {str(exc)}")
                skipped_count += 1
            else:
                unlinked_count += 1

        logger.info(
            f"Unlinked {unlinked_count} files and skipped {skipped_count} files "
            f"(orphan or beyond GC_MAX_KEEP)."
        )

    # Remove files not tracked by the database
    try:
        async with database.with_session() as session:
            db_paths = {
                pathlib.Path(blob.path).absolute()
                for blob in (await crud.read_blobs(session))
            }

        storage_paths = set()
        for path in storage_directory.iterdir():
            if path.is_file() or path.is_symlink():
                storage_paths.add(path.absolute())
            else:
                logger.warning(f"Unexpected directory in storage, skipped: {path}")

        untracked_paths:set[pathlib.Path] = storage_paths - db_paths
        unlinked_count = 0
        skipped_count = 0

        for path in untracked_paths:
            try:
                path.unlink()
            except Exception as exc:
                logger.warning(f"Failed to unlink {str(path)} : {str(exc)}")
                skipped_count += 1
            else:
                unlinked_count += 1

        logger.info(
            f"Unlinked {unlinked_count} files and skipped {skipped_count} files "
            f"(untracked)."
        )
    except Exception as exc:
        logger.exception(f"Failed to unlink untracked files : {str(exc)}")

    logger.info("GC completed.")

    return


async def gc() -> None:
    try:
        await gc_work()
    except Exception as exc:
        logger.exception(f"GC failed : {str(exc)}")
        raise
