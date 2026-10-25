import secrets

from fastapi import Request, HTTPException, status

from src.settings import settings


async def verify_security_token(request:Request) -> bool:
    if settings.TOKEN:
        user_token = request.headers.get("MAIREPO-TOKEN", "")
        if not secrets.compare_digest(
            user_token.encode("utf-8"),
            settings.TOKEN.encode("utf-8")
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid MAIREPO-TOKEN")

    return True
