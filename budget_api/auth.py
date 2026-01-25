from datetime import datetime, timezone
from uuid import UUID
import os

from cognito_jwt_verifier import AsyncCognitoJwtVerifier
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budget_api import db
from budget_api.models import User
from budget_api.tables import UsersTable

ISSUER = os.environ["COGNITO_ISSUER"]
CLIENT_IDS = [
    client_id.strip()
    for client_id in os.environ["COGNITO_CLIENT_IDS"].split(",")
    if client_id.strip()
]

verifier = AsyncCognitoJwtVerifier(ISSUER, client_ids=CLIENT_IDS)

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{ISSUER}/oauth2/authorize",
    tokenUrl=f"{ISSUER}/oauth2/token",
)


async def get_or_create_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(db.get_session),
) -> User:
    try:
        claims = await verifier.verify_access_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = claims.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing email claim.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    normalized_email = email.strip().lower()
    cognito_sub = claims.get("sub")
    if not cognito_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing sub claim.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        cognito_user_id = UUID(cognito_sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has invalid sub claim.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    result = await session.execute(
        select(UsersTable).where(UsersTable.id == cognito_user_id)
    )
    user = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if user is None:
        user = UsersTable(
            id=cognito_user_id,
            email=normalized_email,
            created_at=now,
            last_seen_at=now,
        )
        session.add(user)
    else:
        user.last_seen_at = now

    await session.flush()
    await session.refresh(user)
    return User(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
        last_seen_at=user.last_seen_at,
    )
