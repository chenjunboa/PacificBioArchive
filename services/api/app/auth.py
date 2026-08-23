from datetime import UTC, datetime, timedelta
from functools import lru_cache
from uuid import NAMESPACE_URL, uuid5

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import Settings, get_settings
from .domain import User

bearer = HTTPBearer(auto_error=False)


class AuthService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def create_dev_token(self, email: str, given_name: str, family_name: str) -> str:
        if self.settings.app_env != "local":
            raise HTTPException(status_code=404, detail="Not found")
        now = datetime.now(UTC)
        claims = {
            "sub": str(uuid5(NAMESPACE_URL, email.lower())),
            "email": email.lower(),
            "given_name": given_name,
            "family_name": family_name,
            "iat": now,
            "exp": now + timedelta(hours=8),
            "iss": "pacific-bioarchive-local",
            "aud": "pacific-bioarchive-web",
        }
        return jwt.encode(claims, self.settings.local_jwt_secret, algorithm="HS256")

    def decode(self, token: str) -> User:
        try:
            if self.settings.app_env == "local":
                claims = jwt.decode(
                    token,
                    self.settings.local_jwt_secret,
                    algorithms=["HS256"],
                    audience="pacific-bioarchive-web",
                    issuer="pacific-bioarchive-local",
                )
            else:
                if not self.settings.cognito_issuer or not self.settings.cognito_client_id:
                    raise RuntimeError("Cognito configuration is incomplete")
                jwks = jwt.PyJWKClient(f"{self.settings.cognito_issuer}/.well-known/jwks.json")
                key = jwks.get_signing_key_from_jwt(token)
                claims = jwt.decode(
                    token,
                    key.key,
                    algorithms=["RS256"],
                    audience=self.settings.cognito_client_id,
                    issuer=self.settings.cognito_issuer,
                )
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Invalid or expired access token") from exc
        return User(
            sub=claims["sub"],
            email=claims.get("email", ""),
            given_name=claims.get("given_name", ""),
            family_name=claims.get("family_name", ""),
        )


@lru_cache
def get_auth_service() -> AuthService:
    return AuthService(get_settings())


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    auth: AuthService = Depends(get_auth_service),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required")
    return auth.decode(credentials.credentials)
