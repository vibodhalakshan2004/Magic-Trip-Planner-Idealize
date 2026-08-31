from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class UserCreate(BaseModel):

    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Name must contain at least 2 characters")
        return value


class UserProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Name must contain at least 2 characters")
        return value

    @model_validator(mode="after")
    def require_change(self):
        if self.name is None and self.email is None:
            raise ValueError("Provide a name or email to update")
        return self


class UserPasswordUpdate(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=8, max_length=72)


class RegisterResponse(BaseModel):
    message: str
    user_id: str


class TokenResponse(BaseModel):

    access_token: str
    token_type: str


class GoogleAuthConfigResponse(BaseModel):
    enabled: bool
    client_id: str | None = None
    csrf_token: str | None = None


class GoogleCredentialRequest(BaseModel):
    credential: str = Field(min_length=100, max_length=8_192)
    csrf_token: str = Field(min_length=32, max_length=256)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: EmailStr
    profile_picture_version: str | None = None
    has_password: bool = True
    google_connected: bool = False
