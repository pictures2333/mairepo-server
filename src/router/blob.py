import pathlib

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src import crud
from src.core import log, security
from src.database import database
from src.settings import settings

logger = log.get_logger("mairepo.router.blob")


# Router

router = APIRouter(prefix="/blob", tags=["blob"])


# Routes

@router.get("/{blob_id}", response_class=FileResponse)
async def get_blob(
    blob_id:int,
    session:AsyncSession = Depends(database.get_session),
    _:bool = Depends(security.verify_security_token),
) -> FileResponse:
    # Resolve blob metadata
    db_blob = await crud.read_blob(
        session,
        blob_id,
        limit_to_gc_keep=True
    )
    if db_blob is None or db_blob.file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blob not found."
        )

    # Validate storage path
    storage_directory = pathlib.Path(settings.DIRECTORY).resolve()
    try:
        blob_path = pathlib.Path(db_blob.path).resolve(strict=True)
    except OSError as exc:
        logger.error(
            f"Blob {db_blob.id} points to an unavailable file: {str(exc)}"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blob file is temporarily unavailable."
        ) from exc

    if not blob_path.is_relative_to(storage_directory):
        logger.error(f"Blob {db_blob.id} points outside the storage directory")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blob file is temporarily unavailable."
        )

    if not blob_path.is_file():
        logger.error(f"Blob {db_blob.id} does not point to a regular file")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blob file is temporarily unavailable."
        )

    # Return download response
    return FileResponse(
        path=blob_path,
        filename=db_blob.file.filename,
        media_type="application/octet-stream",
        content_disposition_type="attachment",
        headers={"Cache-Control": "private, no-cache"}
    )
