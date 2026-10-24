from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src import crud
from src.core import log, security
from src.database import database
from src.utils.storage import resolve_storage_file

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
    db_blobs = await crud.read_blobs(
        session,
        id=blob_id,
        file_id=crud.UNSET,
        limit_to_gc_keep=True
    )
    if not db_blobs or db_blobs[0].file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blob not found."
        )
    db_blob = db_blobs[0]

    # Validate storage path
    try:
        blob_path = resolve_storage_file(db_blob.path)
    except RuntimeError as exc:
        logger.error(f"Storage directory is unavailable: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage is temporarily unavailable."
        ) from exc

    if blob_path is None:
        logger.error(f"Blob {db_blob.id} points to an unavailable storage file")
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
