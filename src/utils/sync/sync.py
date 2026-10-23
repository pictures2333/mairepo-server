# We suppose that there is only 1 writer at the same time
# So we don't use any lock

from typing import Optional, List, Dict, Tuple
import pathlib
import asyncio
import re

from src.settings import settings
from src.utils.filename import random_filename
from src.utils import drive
from src.core import log
from src.database import database, model
from src import crud
from .sem import apply_sem

logger = log.get_logger("mairepo.sync")

# functions

async def _drive_get_chart_file_list() -> Dict[str, List[drive.DriveFileInfo]]:
    generation_folders = await drive.list_dir(
        settings.MAISQUARED_FOLDER_ID,
        "only-folder",
        None
    )

    chart_folder_results = await asyncio.gather(
        *(
            apply_sem(drive.list_dir(folder.id, "only-folder", folder.resource_key))
            for folder in generation_folders
            if parse_generation_name(folder.name) is not None
        ),
        return_exceptions=True
    )
    chart_folders:List[drive.DriveFileInfo] = []
    for result in chart_folder_results:
        if isinstance(result, BaseException):
            raise result
        chart_folders.extend(result)
    
    chart_file_results = await asyncio.gather(
        *(
            apply_sem(drive.list_dir(folder.id, "only-file", folder.resource_key))
            for folder in chart_folders
        ),
        return_exceptions=True
    )
    chart_files_by_name:Dict[str, List[drive.DriveFileInfo]] = {}
    for index, result in enumerate(chart_file_results):
        if isinstance(result, BaseException):
            raise result
        chart_files_by_name[chart_folders[index].name] = result

    return chart_files_by_name


async def _local_create_chart(chart_name:str, chart_files:List[drive.DriveFileInfo]) -> None:
    db_files = []

    try:
        # download
        for chart_file in chart_files:
            file_path, revision_id = await _download_and_verify_chart_file(
                chart_name,
                chart_file
            )

            db_files.append({
                "filename": chart_file.name,
                "filepath": str(file_path),
                "drive_file_id": chart_file.id,
                "drive_head_revision_id": revision_id
            })

        # database
        async with database.with_session() as session:
            async with session.begin():
                await crud.create_chart(session, chart_name, db_files)
    except Exception as exc:
        logger.warning(f"Failed to create chart {chart_name}, skipped: {str(exc)}")
        return

    return


async def _compare_exist_chart_file(chart_id:int, chart_name:str, chart_files:List[drive.DriveFileInfo]) -> None:
    async with database.with_session() as session:
        database_files = await crud.read_files_of_chart(session, chart_id)

    # compare
    drive_files_by_id = {
        drive_file.id: drive_file
        for drive_file in chart_files
    }
    database_files_by_drive_id = {
        database_file.drive_file_id: database_file
        for database_file in database_files
    }

    new_drive_files:List[drive.DriveFileInfo] = []
    deleted_database_files:List[model.File] = []
    changed_drive_files:List[drive.DriveFileInfo] = []
    renamed_drive_files:List[drive.DriveFileInfo] = []

    file_ids = drive_files_by_id.keys() | database_files_by_drive_id.keys()
    for file_id in file_ids:
        drive_file = drive_files_by_id.get(file_id)
        database_file = database_files_by_drive_id.get(file_id)

        if drive_file is None:
            if database_file is not None:
                deleted_database_files.append(database_file)
        elif database_file is None:
            new_drive_files.append(drive_file)
        elif drive_file.head_revision_id != database_file.drive_head_revision_id:
            changed_drive_files.append(drive_file)
        elif drive_file.name != database_file.filename:
            renamed_drive_files.append(drive_file)

    if (
        new_drive_files
        or deleted_database_files
        or changed_drive_files
        or renamed_drive_files
    ):
        logger.info(
            f"Chart {chart_name}: found {len(new_drive_files)} new files, "
            f"{len(deleted_database_files)} deleted files, "
            f"{len(changed_drive_files)} changed files, "
            f"{len(renamed_drive_files)} renamed files"
        )

    # download new and changed files
    downloaded_files:Dict[str, Tuple[pathlib.Path, str]] = {}

    try:
        for drive_file in new_drive_files + changed_drive_files:
            destination_path, revision_id = await _download_and_verify_chart_file(
                chart_name,
                drive_file
            )
            downloaded_files[drive_file.id] = (destination_path, revision_id)

        # update database
        async with database.with_session() as session:
            async with session.begin():
                for database_file in deleted_database_files:
                    await crud.delete_file(
                        session,
                        chart_id,
                        database_file.drive_file_id
                    )

                for drive_file in changed_drive_files:
                    destination_path, revision_id = downloaded_files[drive_file.id]
                    await crud.update_file(
                        session=session,
                        chart_id=chart_id,
                        drive_file_id=drive_file.id,
                        filename=drive_file.name,
                        blob_path=str(destination_path),
                        drive_head_revision_id=revision_id
                    )

                for drive_file in renamed_drive_files:
                    await crud.update_file(
                        session=session,
                        chart_id=chart_id,
                        drive_file_id=drive_file.id,
                        filename=drive_file.name
                    )

                for drive_file in new_drive_files:
                    destination_path, revision_id = downloaded_files[drive_file.id]
                    await crud.create_file(
                        session=session,
                        chart_id=chart_id,
                        filename=drive_file.name,
                        blob_path=str(destination_path),
                        drive_file_id=drive_file.id,
                        drive_head_revision_id=revision_id
                    )
    except Exception as exc:
        logger.warning(f"Failed to update chart {chart_name}, skipped: {str(exc)}")
        return

    return


async def sync_work() -> None:
    logger.info("Sync started.")

    chart_files_by_name = await _drive_get_chart_file_list()
    logger.info(f"Fetched {len(chart_files_by_name)} charts")

    async with database.with_session() as session:
        database_charts = await crud.read_charts(session)

    # compare drive and local
    drive_chart_names = chart_files_by_name.keys()
    database_charts_by_name = {
        chart.name: chart
        for chart in database_charts
    }

    new_chart_names = []
    existing_charts:List[Tuple[int, str]] = []
    for chart_name in drive_chart_names:
        database_chart = database_charts_by_name.get(chart_name)
        if database_chart is not None:
            existing_charts.append((database_chart.id, chart_name))
        else:
            new_chart_names.append(chart_name)

    deleted_chart_names = [
        chart_name
        for chart_name in database_charts_by_name
        if chart_name not in drive_chart_names
    ]
    
    logger.info(
        f"Found {len(new_chart_names)} new charts, "
        f"{len(deleted_chart_names)} deleted charts"
    )

    # delete charts
    async with database.with_session() as session:
        async with session.begin():
            for chart_name in deleted_chart_names:
                await crud.delete_chart(session, name=chart_name)

    # create charts
    await asyncio.gather(
        *(
            apply_sem(
                _local_create_chart(
                    chart_name,
                    chart_files_by_name[chart_name]
                )
            )
            for chart_name in new_chart_names
        )
    )

    # existed charts
    await asyncio.gather(
        *(
            apply_sem(
                _compare_exist_chart_file(
                    chart_id,
                    chart_name,
                    chart_files_by_name[chart_name]
                )
            )
            for chart_id, chart_name in existing_charts
        )
    )

    logger.info("Sync completed.")
    
    return


async def sync() -> None:
    try:
        await sync_work()
    except Exception as exc:
        logger.exception(f"Sync failed : {str(exc)}")
        raise


# helpers

async def _download_and_verify_chart_file(
    chart_name:str,
    drive_file:drive.DriveFileInfo
) -> Tuple[pathlib.Path, str]:
    destination_path = (
        pathlib.Path(settings.DIRECTORY) / random_filename()
    ).absolute()
    downloaded_file = await drive.download_file(
        drive_file.id,
        destination_path,
        drive_file.resource_key
    )

    if drive_file.md5_checksum != downloaded_file.md5_checksum or \
            drive_file.head_revision_id != downloaded_file.head_revision_id:
        raise RuntimeError(
            f"Google Drive file changed during sync "
            f"{chart_name} / {drive_file.name}"
        )

    revision_id = downloaded_file.head_revision_id
    if revision_id is None:
        raise RuntimeError(
            f"Google Drive file has no head revision ID: "
            f"{chart_name} / {drive_file.name}"
        )

    return destination_path, revision_id


def parse_generation_name(folder_name:str) -> Optional[str]:
    match = re.fullmatch(r"\d+(?:\.\d+)*[A-Za-z]*\.\s*(.+)", folder_name)
    return match.group(1) if match else None
