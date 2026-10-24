from typing import Optional, Union
import pathlib

from src.core import log
from src.settings import settings

logger = log.get_logger("mairepo")


def resolve_storage_directory() -> pathlib.Path:
    """
    Resolve the configured storage directory.

    Returns:
        pathlib.Path: Resolved storage directory.

    Raises:
        RuntimeError: If the configured storage directory is unavailable.
    """
    try:
        storage_directory = pathlib.Path(settings.DIRECTORY).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        logger.fatal(f"Storage directory is unavailable: {str(exc)}")
        raise RuntimeError("Storage directory is unavailable.") from exc

    if not storage_directory.is_dir():
        logger.fatal("Storage path is not a directory.")
        raise RuntimeError("Storage path is not a directory.")

    return storage_directory


def resolve_storage_file(
    file_path:Union[str, pathlib.Path]
) -> Optional[pathlib.Path]:
    """
    Resolve an available regular file within the storage directory.

    Args:
        file_path: File path to validate.

    Returns:
        Optional[pathlib.Path]: Resolved file path, or None when unavailable.

    Raises:
        RuntimeError: If the configured storage directory is unavailable.
    """
    storage_directory = resolve_storage_directory()

    try:
        resolved_path = pathlib.Path(file_path).resolve(strict=True)
    except (OSError, RuntimeError):
        return None

    if (
        not resolved_path.is_relative_to(storage_directory)
        or not resolved_path.is_file()
    ):
        return None

    return resolved_path
