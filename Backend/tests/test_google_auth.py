from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

import app.api.routes.auth as auth_routes
import app.services.google_identity as google_identity_module
from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models.user import User
from app.services.google_identity import GoogleIdentity, verify_google_credential


class SequencedUserQuery:
    def __init__(self, db):
        self.db = db

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.db.query_results.pop(0) if self.db.query_results else None


class GoogleAuthDB:
    def __init__(self, query_results=None):
        self.query_results = list(query_results or [])
        self.added = []

    def query(self, model):
        assert model is User
        return SequencedUserQuery(self)

    def add(self, user):
        if user.id is None:
            user.id = uuid4()
        self.added.append(user)

    def commit(self):
        return None

    def rollback(self):
        return None

    def refresh(self, instance):
        return None


def google_identity(email="traveler@gmail.com", hosted_domain=None):
    return GoogleIdentity(
        subject="google-subject-123",
        email=email,
        name="Google Traveler",
        hosted_domain=hosted_domain,
    )


def test_google_config_is_disabled_without_a_client_id(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_AUTH_CLIENT_ID", None)
    response = TestClient(app).get("/auth/google/config")

    assert response.status_code == 200
    assert response.json() == {"enabled": False, "client_id": None, "csrf_token": None}
    assert settings.GOOGLE_AUTH_CSRF_COOKIE_NAME not in response.cookies


def test_google_login_creates_an_oauth_only_user_and_session(monkeypatch):
    client_id = "123-example.apps.googleusercontent.com"
    monkeypatch.setattr(settings, "GOOGLE_AUTH_CLIENT_ID", client_id)
    monkeypatch.setattr(settings, "SESSION_COOKIE_SECURE", False)
    monkeypatch.setattr(auth_routes, "verify_google_credential", lambda credential: google_identity())
    fake_db = GoogleAuthDB([None, None])

    def override_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        config = client.get("/auth/google/config")
        csrf_token = config.json()["csrf_token"]
        response = client.post(
            "/auth/google",
            json={"credential": "x" * 200, "csrf_token": csrf_token},
        )

        assert config.json()["client_id"] == client_id
        assert response.status_code == 200
        assert len(fake_db.added) == 1
        assert fake_db.added[0].email == "traveler@gmail.com"
        assert fake_db.added[0].password_hash is None
        assert fake_db.added[0].google_subject == "google-subject-123"
        assert settings.SESSION_COOKIE_NAME in client.cookies
        assert settings.GOOGLE_AUTH_CSRF_COOKIE_NAME not in client.cookies
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_google_login_rejects_a_missing_or_mismatched_csrf_cookie(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_AUTH_CLIENT_ID", "123-example.apps.googleusercontent.com")
    response = TestClient(app).post(
        "/auth/google",
        json={"credential": "x" * 200, "csrf_token": "y" * 43},
    )

    assert response.status_code == 403
    assert "expired" in response.json()["detail"].lower()


def test_google_login_links_an_existing_gmail_password_account(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_AUTH_CLIENT_ID", "123-example.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "SESSION_COOKIE_SECURE", False)
    monkeypatch.setattr(auth_routes, "verify_google_credential", lambda credential: google_identity())
    existing_user = SimpleNamespace(
        id=uuid4(),
        name="Existing Traveler",
        email="traveler@gmail.com",
        password_hash=hash_password("StrongPass!2026"),
        google_subject=None,
    )
    fake_db = GoogleAuthDB([None, existing_user])

    def override_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        csrf_token = client.get("/auth/google/config").json()["csrf_token"]
        response = client.post(
            "/auth/google",
            json={"credential": "x" * 200, "csrf_token": csrf_token},
        )

        assert response.status_code == 200
        assert existing_user.google_subject == "google-subject-123"
        assert fake_db.added == []
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_google_login_does_not_auto_link_a_third_party_email(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_AUTH_CLIENT_ID", "123-example.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "SESSION_COOKIE_SECURE", False)
    monkeypatch.setattr(
        auth_routes,
        "verify_google_credential",
        lambda credential: google_identity(email="traveler@example.com"),
    )
    existing_user = SimpleNamespace(
        id=uuid4(),
        name="Existing Traveler",
        email="traveler@example.com",
        password_hash=hash_password("StrongPass!2026"),
        google_subject=None,
    )
    fake_db = GoogleAuthDB([None, existing_user])

    def override_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        csrf_token = client.get("/auth/google/config").json()["csrf_token"]
        response = client.post(
            "/auth/google",
            json={"credential": "x" * 200, "csrf_token": csrf_token},
        )

        assert response.status_code == 409
        assert existing_user.google_subject is None
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_google_id_token_verification_uses_the_configured_audience(monkeypatch):
    client_id = "123-example.apps.googleusercontent.com"
    captured = {}
    monkeypatch.setattr(settings, "GOOGLE_AUTH_CLIENT_ID", client_id)

    def verify(credential, request, audience):
        captured.update(credential=credential, audience=audience)
        return {
            "sub": "google-subject-123",
            "email": "traveler@gmail.com",
            "email_verified": True,
            "name": "Google Traveler",
        }

    monkeypatch.setattr(google_identity_module.id_token, "verify_oauth2_token", verify)
    identity = verify_google_credential("signed-google-token")

    assert captured == {"credential": "signed-google-token", "audience": client_id}
    assert identity.subject == "google-subject-123"
    assert identity.google_is_authoritative_for_email is True
