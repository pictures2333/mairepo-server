from typing import (
    Optional, Literal, Union,
    List, Dict, Tuple, BinaryIO
)
from urllib.parse import quote
from pathlib import Path
import hashlib
import tempfile
import os

from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential
)
from src.settings import settings
from .client import request
from .constants import FOLDER_MIME_TYPE, FILE_FIELDS, DRIVE_API_BASE_URL
from .helpers import escape_query_literal, build_resource_key_headers
from .model import DriveFileInfo
from .retry import should_retry

# list_dir

@retry(
    retry=retry_if_exception(should_retry),
    stop=stop_after_attempt(settings.MAX_ATTEMPTS),
    wait=wait_random_exponential(multiplier=1, max=10),
    reraise=True
)
async def _list_dir_fetch_page(
    params:Dict[str, str],
    headers:Dict[str, str],
    page_token:Optional[str] = None
) -> Tuple[List[DriveFileInfo], Optional[str]]:
    files = []

    # set pageToken
    _params = params
    if page_token is not None:
        _params["pageToken"] = page_token

    # request
    response = await request(
        "GET",
        DRIVE_API_BASE_URL,
        params=_params,
        headers=headers
    )
    response.raise_for_status()
    payload = await response.json()

    # check response
    if not isinstance(payload, dict):
        raise ValueError("Google Drive returned an invalid file list.")

    items = payload.get("files", [])
    if not isinstance(items, list):
        raise ValueError("Google Drive returned an invalid files field.")

    # response is valid
    files.extend(DriveFileInfo.model_validate(item) for item in items)

    # next page
    next_page_token = payload.get("nextPageToken")
    if next_page_token is not None:
        if not isinstance(next_page_token, str) or not next_page_token:
            raise ValueError("Google Drive returned an invalid page token.")
    
    return files, next_page_token


async def list_dir(
    folder_id:str,
    mode:Optional[Literal["only-folder", "only-file"]] = None,
    resource_key:Optional[str] = None
) -> List[DriveFileInfo]:
    # build query
    query = f"'{escape_query_literal(folder_id)}' in parents and trashed = false"
    headers = build_resource_key_headers(folder_id, resource_key)
    
    if mode == "only-folder":
        query += f" and mimeType = '{FOLDER_MIME_TYPE}'"
    elif mode == "only-file":
        query += f" and mimeType != '{FOLDER_MIME_TYPE}'"
    elif mode is not None:
        raise ValueError(f"Unsupported list mode: {mode}")

    # fetch pages
    files:List[DriveFileInfo] = []
    page_token:Optional[str] = None
    params = {
        "q": query,
        "fields": f"nextPageToken,files({FILE_FIELDS})",
        "pageSize": "1000",
        "orderBy": "name",
        "spaces": "drive",
        "supportsAllDrives": "true",
        "includeItemsFromAllDrives": "true",
    }
    while True:
        _files, page_token = await _list_dir_fetch_page(params, headers, page_token)
        files.extend(_files)
        if page_token is None:
            break

    return files


# download_file

@retry(
    retry=retry_if_exception(should_retry),
    stop=stop_after_attempt(settings.MAX_ATTEMPTS),
    wait=wait_random_exponential(multiplier=1, max=10),
    reraise=True
)
async def _download_file_get_file_metadata(file_url:str, headers:Dict[str, str]) -> DriveFileInfo:
    response = await request(
        "GET",
        file_url,
        params={
            "fields": FILE_FIELDS,
            "supportsAllDrives": "true",
        },
        headers=headers
    )
    async with response:
        response.raise_for_status()
        file_info = DriveFileInfo.model_validate(await response.json())

    return file_info


@retry(
    retry=retry_if_exception(should_retry),
    stop=stop_after_attempt(settings.MAX_ATTEMPTS),
    wait=wait_random_exponential(multiplier=1, max=10),
    reraise=True
)
async def _download_file(
    file_url:str,
    headers:Dict[str, str],
    temporary_file:BinaryIO
) -> str:
    temporary_file.seek(0)
    temporary_file.truncate(0)

    checksum = hashlib.md5(usedforsecurity=False)
    response = await request(
        "GET",
        file_url,
        params={
            "alt": "media",
            "supportsAllDrives": "true",
        },
        headers=headers
    )
    async with response:
        response.raise_for_status()

        async for chunk in response.content.iter_chunked(64 * 1024):
            temporary_file.write(chunk)
            checksum.update(chunk)

    return checksum.hexdigest()


async def download_file(
    file_id:str,
    destination:Union[str,Path],
    resource_key:Optional[str]=None
) -> DriveFileInfo:
    # build request
    encoded_file_id = quote(file_id, safe="")
    file_url = f"{DRIVE_API_BASE_URL}/{encoded_file_id}"
    headers = build_resource_key_headers(file_id, resource_key)

    # read file metadata
    file_info = await _download_file_get_file_metadata(file_url, headers)

    # Prepare temporary output
    destination_path = Path(destination)
    temporary_file = tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{destination_path.name}.",
        suffix=".tmp",
        dir=destination_path.parent,
        delete=False,
    )
    temporary_path = Path(temporary_file.name)
    
    try:
        checksum = await _download_file(file_url, headers, temporary_file)

        # Verify checksum
        if file_info.md5_checksum is None:
            raise RuntimeError("Google Drive file has no MD5 checksum.")
        if checksum != file_info.md5_checksum:
            raise RuntimeError("Downloaded file checksum verification failed.")
    
        # Commit download
        temporary_file.flush()
        temporary_file.close()
        os.replace(temporary_path, destination_path)
    except BaseException:
        # Remove incomplete download
        try:
            temporary_file.close()
        finally:
            temporary_path.unlink(missing_ok=True)
        raise
    
    return file_info
