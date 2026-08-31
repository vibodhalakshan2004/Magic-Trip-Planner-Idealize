import hashlib
import secrets
from datetime import UTC, datetime

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    File,
    Header,
    HTTPException,
    Response,
    UploadFile,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.user import (
    RegisterResponse,
    GoogleAuthConfigResponse,
    GoogleCredentialRequest,
    TokenResponse,
    UserCreate,
    UserPasswordUpdate,
    UserProfileUpdate,
    UserResponse,
)
from app.services.google_identity import (
    GoogleIdentityUnavailableError,
    InvalidGoogleCredentialError,
    verify_google_credential,
)

MAX_PROFILE_PICTURE_BYTES = 4 * 1024 * 1024
PROFILE_PICTURE_SIGNATURES = {
    "image/jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
    "image/png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/webp": lambda data: data.startswith(b"RIFF") and data[8:12] == b"WEBP",
    "image/gif": lambda data: data.startswith((b"GIF87a", b"GIF89a")),
}

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/register", response_model=RegisterResponse)
def register_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):

    normalized_email = str(user.email).strip().lower()
    existing_user = (
        db.query(User)
        .filter(func.lower(User.email) == normalized_email)
        .first()
    )

    if existing_user:

        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    new_user = User(
        name=user.name,
        email=normalized_email,
        password_hash=hash_password(user.password)
    )

    db.add(new_user)

    db.commit()

    db.refresh(new_user)

    return {
        "message": "User created successfully",
        "user_id": str(new_user.id)
    }



@router.post("/login", response_model=TokenResponse)
def login_user(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    normalized_email = form_data.username.strip().lower()
    user = (
        db.query(User)
        .filter(func.lower(User.email) == normalized_email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    if not verify_password(
        form_data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    return _create_session(response, user)


@router.get("/google/config", response_model=GoogleAuthConfigResponse)
def google_auth_config(response: Response):
    client_id = settings.GOOGLE_AUTH_CLIENT_ID
    response.headers["Cache-Control"] = "no-store"
    if not client_id:
        return {"enabled": False, "client_id": None, "csrf_token": None}

    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        key=settings.GOOGLE_AUTH_CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=settings.GOOGLE_AUTH_CSRF_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return {
        "enabled": True,
        "client_id": client_id,
        "csrf_token": csrf_token,
    }


@router.post("/google", response_model=TokenResponse)
def login_with_google(
    request: GoogleCredentialRequest,
    response: Response,
    csrf_cookie: str | None = Cookie(default=None, alias=settings.GOOGLE_AUTH_CSRF_COOKIE_NAME),
    db: Session = Depends(get_db),
):
    if not settings.GOOGLE_AUTH_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured")
    if not csrf_cookie or not secrets.compare_digest(csrf_cookie, request.csrf_token):
        raise HTTPException(status_code=403, detail="Google sign-in session expired. Please try again")

    try:
        identity = verify_google_credential(request.credential)
    except InvalidGoogleCredentialError as exc:
        raise HTTPException(status_code=401, detail="Google could not verify this account") from exc
    except GoogleIdentityUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Google sign-in is temporarily unavailable") from exc

    user = db.query(User).filter(User.google_subject == identity.subject).first()
    if user is None:
        user = (
            db.query(User)
            .filter(func.lower(User.email) == identity.email)
            .first()
        )
        if user is not None:
            linked_subject = getattr(user, "google_subject", None)
            if linked_subject and linked_subject != identity.subject:
                raise HTTPException(status_code=409, detail="This email is linked to another Google account")
            if not identity.google_is_authoritative_for_email:
                raise HTTPException(
                    status_code=409,
                    detail="Use email and password for this account. Automatic linking requires Gmail or Google Workspace",
                )
            user.google_subject = identity.subject
        else:
            user = User(
                name=identity.name,
                email=identity.email,
                password_hash=None,
                google_subject=identity.subject,
            )
            db.add(user)

        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            user = db.query(User).filter(User.google_subject == identity.subject).first()
            if user is None:
                raise HTTPException(status_code=409, detail="This Google account could not be linked") from exc
        db.refresh(user)

    response.delete_cookie(
        key=settings.GOOGLE_AUTH_CSRF_COOKIE_NAME,
        path="/",
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
    )
    return _create_session(response, user)


@router.post("/logout")
def logout_user(response: Response):
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
    )
    return {"message": "Logged out"}

@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user)
):

    return _user_response(current_user)


@router.patch("/me", response_model=UserResponse)
def update_me(
    update: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if update.email is not None:
        normalized_email = str(update.email).strip().lower()
        existing_user = (
            db.query(User)
            .filter(func.lower(User.email) == normalized_email, User.id != current_user.id)
            .first()
        )
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(status_code=409, detail="Email already registered")
        current_user.email = normalized_email

    if update.name is not None:
        current_user.name = update.name

    db.commit()
    db.refresh(current_user)
    return _user_response(current_user)


@router.put("/me/password")
def update_my_password(
    update: UserPasswordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(update.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if verify_password(update.new_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="New password must be different")

    current_user.password_hash = hash_password(update.new_password)
    db.commit()
    return {"message": "Password updated successfully"}


@router.put("/me/profile-picture", response_model=UserResponse)
async def update_my_profile_picture(
    picture: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content_type = (picture.content_type or "").lower()
    signature_check = PROFILE_PICTURE_SIGNATURES.get(content_type)
    if not signature_check:
        await picture.close()
        raise HTTPException(status_code=415, detail="Use a JPEG, PNG, WebP, or GIF image")

    try:
        content = await picture.read(MAX_PROFILE_PICTURE_BYTES + 1)
    finally:
        await picture.close()

    if not content:
        raise HTTPException(status_code=400, detail="The uploaded image is empty")
    if len(content) > MAX_PROFILE_PICTURE_BYTES:
        raise HTTPException(status_code=413, detail="Profile pictures must be 4 MB or smaller")
    if not signature_check(content):
        raise HTTPException(status_code=400, detail="The uploaded file does not match its image type")

    current_user.profile_picture = content
    current_user.profile_picture_content_type = content_type
    current_user.profile_picture_version = hashlib.sha256(content).hexdigest()[:20]
    current_user.profile_picture_updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(current_user)
    return _user_response(current_user)


@router.get("/me/profile-picture", response_class=Response)
def get_my_profile_picture(
    if_none_match: str | None = Header(default=None),
    current_user: User = Depends(get_current_user),
):
    content = getattr(current_user, "profile_picture", None)
    content_type = getattr(current_user, "profile_picture_content_type", None)
    version = getattr(current_user, "profile_picture_version", None)
    if not content or not content_type or not version:
        raise HTTPException(status_code=404, detail="Profile picture not found")

    etag = f'"{version}"'
    cache_headers = {
        "Cache-Control": "private, max-age=3600, must-revalidate",
        "ETag": etag,
        "X-Content-Type-Options": "nosniff",
    }
    if if_none_match == etag:
        return Response(status_code=304, headers=cache_headers)

    return Response(
        content=content,
        media_type=content_type,
        headers={**cache_headers, "Content-Length": str(len(content))},
    )


@router.delete("/me/profile-picture", response_model=UserResponse)
def delete_my_profile_picture(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.profile_picture = None
    current_user.profile_picture_content_type = None
    current_user.profile_picture_version = None
    current_user.profile_picture_updated_at = None
    db.commit()
    db.refresh(current_user)
    return _user_response(current_user)


def _user_response(user: User) -> dict:
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "profile_picture_version": getattr(user, "profile_picture_version", None),
        "has_password": bool(getattr(user, "password_hash", None)),
        "google_connected": bool(getattr(user, "google_subject", None)),
    }


def _create_session(response: Response, user: User) -> dict:
    token = create_access_token({"sub": str(user.id)})
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        path="/",
    )
    return {
        "access_token": token,
        "token_type": "bearer",
    }
