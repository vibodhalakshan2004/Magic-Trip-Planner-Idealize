from dataclasses import dataclass

from google.auth.exceptions import TransportError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token

from app.core.config import settings


class InvalidGoogleCredentialError(ValueError):
    pass


class GoogleIdentityUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str
    name: str
    hosted_domain: str | None

    @property
    def google_is_authoritative_for_email(self) -> bool:
        return self.email.endswith("@gmail.com") or bool(self.hosted_domain)


def verify_google_credential(credential: str) -> GoogleIdentity:
    client_id = settings.GOOGLE_AUTH_CLIENT_ID
    if not client_id:
        raise GoogleIdentityUnavailableError("Google sign-in is not configured")

    try:
        claims = id_token.verify_oauth2_token(
            credential,
            GoogleRequest(),
            client_id,
        )
    except TransportError as exc:
        raise GoogleIdentityUnavailableError("Google identity verification is unavailable") from exc
    except (TypeError, ValueError) as exc:
        raise InvalidGoogleCredentialError("Invalid Google credential") from exc

    subject = str(claims.get("sub") or "").strip()
    email = str(claims.get("email") or "").strip().lower()
    email_verified = claims.get("email_verified") is True or claims.get("email_verified") == "true"
    if not subject or len(subject) > 255 or not email or not email_verified:
        raise InvalidGoogleCredentialError("Google did not provide a verified identity")

    raw_name = " ".join(str(claims.get("name") or "").split())
    fallback_name = email.split("@", 1)[0].replace(".", " ").replace("_", " ").strip()
    name = (raw_name or fallback_name or "Google traveler")[:100]
    if len(name) < 2:
        name = "Google traveler"

    hosted_domain = str(claims.get("hd") or "").strip().lower() or None
    return GoogleIdentity(
        subject=subject,
        email=email,
        name=name,
        hosted_domain=hosted_domain,
    )
