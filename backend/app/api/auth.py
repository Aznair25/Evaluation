import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from authlib.integrations.starlette_client import OAuth

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse, UserOut
from app.core.auth import create_access_token, get_current_user

settings = get_settings()
router = APIRouter()

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/google")
async def google_login(request: Request):
    redirect_uri = settings.google_redirect_uri
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="OAuth authentication failed") from exc

    user_info = token.get("userinfo")
    if not user_info:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token['access_token']}"},
            )
            user_info = resp.json()

    google_id = user_info.get("sub")
    email = user_info.get("email")
    name = user_info.get("name", email)
    picture = user_info.get("picture")

    if not google_id or not email:
        raise HTTPException(status_code=400, detail="Could not retrieve user info from Google")

    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            picture_url=picture,
        )
        db.add(user)
    else:
        user.name = name
        user.picture_url = picture
        user.last_login = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(subject=user.id)
    redirect_url = f"{settings.frontend_url}/auth/callback?token={access_token}"
    return RedirectResponse(url=redirect_url)


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout", status_code=204)
async def logout():
    # Stateless JWT — client discards the token
    return None
