from pydantic import BaseModel, EmailStr
from datetime import datetime
import uuid


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: str
    picture_url: str | None
    created_at: datetime
    last_login: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
