import aiohttp

def should_retry(error:BaseException) -> bool:
    # TLS failures normally require certificate or client configuration changes.
    # aiohttp.ClientSSLError and aiohttp.ServerFingerprintMismatch are inherit from aiohttp.ClientConnectionError
    # so check them first
    if isinstance(error, (aiohttp.ClientSSLError, aiohttp.ServerFingerprintMismatch)):
        return False

    # ContentTypeError inherits from ClientResponseError, so check it first.
    # A proxy or upstream service may temporarily return a non-JSON response.
    if isinstance(error, aiohttp.ContentTypeError):
        return True

    if isinstance(error, aiohttp.ClientResponseError):
        return error.status in (
            403,  # Access may be temporarily blocked by Google Drive rate limits.
            408,  # The server or proxy timed out while processing the request.
            429,  # The client exceeded a request or quota limit.
            500,  # Google encountered an internal server error.
            502,  # A gateway received an invalid response from an upstream server.
            503,  # Google Drive is temporarily unavailable or overloaded.
            504,  # A gateway timed out while waiting for an upstream server.
        )

    # Connection failures may recover when a new connection is established.
    if isinstance(error, aiohttp.ClientConnectionError):
        return True

    # The response body may have been truncated, malformed, or decompressed badly.
    if isinstance(error, aiohttp.ClientPayloadError):
        return True

    # The connection or response body may have exceeded the configured timeout.
    if isinstance(error, TimeoutError):
        return True

    # Only safe when the decorated helper validates remote response data.
    # This covers malformed JSON and invalid Google Drive response fields.
    if isinstance(error, ValueError):
        return True

    return False
