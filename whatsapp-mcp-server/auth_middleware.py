import json
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import JSONResponse
from starlette.datastructures import Headers
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.auth.exceptions import GoogleAuthError

class OAuth2BearerMiddleware:
    def __init__(self, app: ASGIApp, google_client_id: str, enabled: bool = True):
        self.app = app
        self.google_client_id = google_client_id
        self.enabled = enabled

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if not self.enabled or scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        auth_header = headers.get("authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            response = JSONResponse({"error": "unauthorized", "message": "Missing or invalid Authorization header"}, status_code=401)
            await response(scope, receive, send)
            return

        token = auth_header[7:].strip()
        success, error, claims = verify_google_jwt_token(token, self.google_client_id)
        if not success:
            # Ensure error message doesn't contain token content
            safe_error = error if error and "token" not in error.lower() else "Token verification failed"
            response = JSONResponse({"error": "forbidden", "message": safe_error}, status_code=403)
            await response(scope, receive, send)
            return

        # Optionally, you could attach claims to scope for downstream use
        scope["user"] = claims
        await self.app(scope, receive, send)

def verify_google_jwt_token(token: str, client_id: str):
    """Verify a Google JWT token.

    Args:
        token: The JWT token to verify
        client_id: The Google OAuth Client ID (used for both signature verification and audience validation)

    Note: For Google ID tokens, the audience claim (aud) must equal the OAuth Client ID.
    The verify_oauth2_token function validates both the signature and the audience.
    """
    try:
        request = google_requests.Request()
        # verify_oauth2_token checks both signature and audience against client_id
        # For Google ID tokens, aud must equal the client_id
        claims = id_token.verify_oauth2_token(token, request, client_id)

        # Verify issuer is from Google
        if claims.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
            return False, "Invalid issuer claim", None

        # Note: Audience validation is already handled by verify_oauth2_token above
        # which ensures claims["aud"] == client_id

        return True, None, claims
    except ValueError as ve:
        return False, str(ve), None
    except GoogleAuthError as ge:
        return False, str(ge), None
    except Exception as e:
        return False, f"Unknown error: {str(e)}", None
