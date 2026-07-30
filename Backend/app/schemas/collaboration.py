from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr


class CollaboratorInvite(BaseModel):
    email: EmailStr
    role: Literal["viewer", "editor"] = "viewer"


class CollaboratorResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    email: EmailStr
    role: Literal["viewer", "editor"]
    created_at: datetime

