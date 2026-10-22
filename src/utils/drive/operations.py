from hashlib import md5
import os
from pathlib import Path
import tempfile
from typing import Literal, Optional
from urllib.parse import quote

from .constants import DRIVE_API_BASE_URL, FILE_FIELDS, FOLDER_MIME_TYPE
from .helpers import (
    build_resource_key_headers,
    escape_query_literal,
    get_session,
)
from .model import DriveFileInfo


async def list_dir(
    folder_id: str,
    mode: Optional[Literal["only-folder", "only-file"]] = None,
    resource_key: Optional[str] = None,
) -> list[DriveFileInfo]:
    """
    List the direct children of a Google Drive folder.

    Args:
        folder_id: Google Drive ID of the folder to list.
        mode: Optional filter for returning only folders or only files.
        resource_key: Optional key required for a link-shared folder.

    Returns:
        list[DriveFileInfo]: Metadata for every matching direct child.

    Raises:
        RuntimeError: The Google Drive client is not initialized.
        ValueError: The mode or Google Drive response is invalid.
        aiohttp.ClientError: The Google Drive request fails.
        TimeoutError: The Google Drive request times out.
    """
    # Build query
    client = get_session()
    query = f"'{escape_query_literal(folder_id)}' in parents and trashed = false"
    headers = build_resource_key_headers(folder_id, resource_key)

    if mode == "only-folder":
        query += f" and mimeType = '{FOLDER_MIME_TYPE}'"
    elif mode == "only-file":
        query += f" and mimeType != '{FOLDER_MIME_TYPE}'"
    elif mode is not None:
        raise ValueError(f"Unsupported list mode: {mode}")

    # Fetch pages
    files: list[DriveFileInfo] = []
    page_token: Optional[str] = None

    while True:
        params = {
            "q": query,
            "fields": f"nextPageToken,files({FILE_FIELDS})",
            "pageSize": "1000",
            "orderBy": "name",
            "spaces": "drive",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        if page_token is not None:
            params["pageToken"] = page_token

        async with client.get(
            DRIVE_API_BASE_URL,
            params=params,
            headers=headers,
        ) as response:
            response.raise_for_status()
            payload = await response.json()

        if not isinstance(payload, dict):
            raise ValueError("Google Drive returned an invalid file list.")

        items = payload.get("files", [])
        if not isinstance(items, list):
            raise ValueError("Google Drive returned an invalid files field.")

        files.extend(DriveFileInfo.model_validate(item) for item in items)

        next_page_token = payload.get("nextPageToken")
        if next_page_token is None:
            return files
        if not isinstance(next_page_token, str) or not next_page_token:
            raise ValueError("Google Drive returned an invalid page token.")

        page_token = next_page_token


async def download_file(
    file_id: str,
    destination: str | Path,
    verify_checksum: bool = True,
    resource_key: Optional[str] = None,
) -> DriveFileInfo:
    """
    Download a Google Drive file and return its metadata.

    Args:
        file_id: Google Drive ID of the file to download.
        destination: Local path where the downloaded file will be stored.
        verify_checksum: Whether to verify the downloaded content using MD5.
        resource_key: Optional key required for a link-shared file.

    Returns:
        DriveFileInfo: Metadata returned by Google Drive for the file.

    Raises:
        RuntimeError: The client is not initialized or checksum verification
            cannot be completed successfully.
        ValueError: Google Drive returns invalid file metadata.
        aiohttp.ClientError: A metadata or download request fails.
        TimeoutError: A metadata or download request times out.
        OSError: The destination file cannot be written or replaced.
    """
    # Build request
    client = get_session()
    encoded_file_id = quote(file_id, safe="")
    file_url = f"{DRIVE_API_BASE_URL}/{encoded_file_id}"
    headers = build_resource_key_headers(file_id, resource_key)

    # Read file metadata
    async with client.get(
        file_url,
        params={
            "fields": FILE_FIELDS,
            "supportsAllDrives": "true",
        },
        headers=headers,
    ) as response:
        response.raise_for_status()
        file_info = DriveFileInfo.model_validate(await response.json())

    checksum = md5(usedforsecurity=False) if verify_checksum else None

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
        # Download content
        async with client.get(
            file_url,
            params={
                "alt": "media",
                "supportsAllDrives": "true",
            },
            headers=headers,
        ) as response:
            response.raise_for_status()

            async for chunk in response.content.iter_chunked(64 * 1024):
                temporary_file.write(chunk)
                if checksum is not None:
                    checksum.update(chunk)

        # Verify checksum
        if checksum is not None:
            if file_info.md5_checksum is None:
                raise RuntimeError("Google Drive file has no MD5 checksum.")
            if checksum.hexdigest() != file_info.md5_checksum:
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
