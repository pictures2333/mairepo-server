from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import model


async def read_files_of_chart(
    session:AsyncSession,
    chart_id:int,
    id:Optional[int]=None,
    drive_file_id:Optional[str]=None
) -> List[model.File]:
    stmt = select(model.File).where(model.File.chart_id == chart_id)

    if id is not None:
        stmt = stmt.where(model.File.id == id)

    if drive_file_id is not None:
        stmt = stmt.where(model.File.drive_file_id == drive_file_id)

    return list(await session.scalars(stmt))


async def create_file(
    session:AsyncSession,
    chart_id:int,
    filename:str,
    blob_path:str,
    drive_file_id:str,
    drive_head_revision_id:str
) -> model.File:
    database_file = model.File(
        chart_id=chart_id,
        filename=filename,
        drive_file_id=drive_file_id,
        drive_head_revision_id=drive_head_revision_id,
        blobs=[
            model.Blob(
                path=blob_path,
                drive_revision_id=drive_head_revision_id
            )
        ]
    )
    session.add(database_file)
    await session.flush()
    await session.refresh(database_file)

    return database_file


async def delete_file(
    session:AsyncSession,
    chart_id:Optional[int]=None,
    drive_file_id:Optional[str]=None,
    id:Optional[int]=None
) -> None:
    """
    Delete a file by database ID or by chart ID and Drive file ID.

    `id` takes precedence when provided. Otherwise, `chart_id` and
    `drive_file_id` must both be provided.

    Raises:
        ValueError: If no valid filter combination is provided.
    """
    stmt = delete(model.File)
    if id is not None:
        stmt = stmt.where(model.File.id == id)
    elif chart_id is not None and drive_file_id is not None:
        stmt = stmt.where(
            model.File.chart_id == chart_id,
            model.File.drive_file_id == drive_file_id
        )
    else:
        raise ValueError(
            "id or both chart_id and drive_file_id must be provided."
        )

    await session.execute(stmt)

    return None


async def update_file(
    session:AsyncSession,
    id:Optional[int]=None,
    chart_id:Optional[int]=None,
    drive_file_id:Optional[str]=None,
    filename:Optional[str]=None,
    blob_path:Optional[str]=None,
    drive_head_revision_id:Optional[str]=None
) -> None:
    """
    Update a file by database ID or by chart ID and Drive file ID.

    `id` takes precedence when provided. Otherwise, `chart_id` and
    `drive_file_id` must both be provided. `filename` and
    `drive_head_revision_id` may be updated independently. Providing
    `blob_path` also creates a blob and requires `drive_head_revision_id`.

    Args:
        session: Database session used for the update.
        id: Optional database file ID filter.
        chart_id: Chart ID used with `drive_file_id` when `id` is omitted.
        drive_file_id: Drive file ID used with `chart_id` when `id` is omitted.
        filename: Optional new filename.
        blob_path: Optional path for a new blob.
        drive_head_revision_id: Optional new Drive head revision ID.

    Returns:
        None.

    Raises:
        ValueError: If the update arguments are invalid or the file does not
            exist.
    """
    if id is not None:
        filters = (model.File.id == id,)
    elif chart_id is not None and drive_file_id is not None:
        filters = (
            model.File.chart_id == chart_id,
            model.File.drive_file_id == drive_file_id
        )
    else:
        raise ValueError(
            "id or both chart_id and drive_file_id must be provided."
        )

    if blob_path is not None and drive_head_revision_id is None:
        raise ValueError(
            "drive_head_revision_id must be provided with blob_path."
        )
    if filename is None and drive_head_revision_id is None:
        raise ValueError("At least one file field must be updated.")

    update_values = {}
    if filename is not None:
        update_values["filename"] = filename
    if drive_head_revision_id is not None:
        update_values["drive_head_revision_id"] = drive_head_revision_id

    stmt = (
        update(model.File)
        .where(*filters)
        .values(**update_values)
        .returning(model.File.id)
    )
    resolved_file_id = await session.scalar(stmt)
    if resolved_file_id is None:
        raise ValueError("File does not exist.")

    if blob_path is not None and drive_head_revision_id is not None:
        session.add(
            model.Blob(
                file_id=resolved_file_id,
                path=blob_path,
                drive_revision_id=drive_head_revision_id
            )
        )
        await session.flush()

    return None
