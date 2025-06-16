import os
import jwt
from jwt.algorithms import RSAAlgorithm
import time
import reflex as rx
from httpx import AsyncClient
import requests
from urllib.parse import urlparse, parse_qs
from .utils import generate_code_challenge, generate_code_verifier
import logging

logger = logging.getLogger(__name__)

# Config from environment variables
CLIENT_ID = os.getenv("DESCOPE_PROJECT_ID")
if not CLIENT_ID:
    raise RuntimeError("DESCOPE_PROJECT_ID environment variable is not set.")
REDIRECT_URI = os.getenv("DESCOPE_REDIRECT_URI", "http://localhost:3000/callback")
if not REDIRECT_URI:
    raise RuntimeError("DESCOPE_REDIRECT_URI environment variable is not set.")
FLOW_ID = os.getenv("DESCOPE_FLOW_ID", "sign-up-or-in")
if not FLOW_ID:
    raise RuntimeError("DESCOPE_FLOW_ID environment variable is not set.")
POST_LOGOUT_REDIRECT_URI = os.getenv("DESCOPE_LOGOUT_REDIRECT_URI", "http://localhost:3000")

# Descope OIDC enpoints (can be overridden by environment variables for custom deployments)
AUTH_URL = os.getenv("DESCOPE_AUTH_URL", "https://api.descope.com/oauth2/v1/authorize")
TOKEN_URL = os.getenv("DESCOPE_TOKEN_URL", "https://api.descope.com/oauth2/v1/token")
JWKS_URL = os.getenv("DESCOPE_JWKS_URL", f"https://api.descope.com/{CLIENT_ID}/.well-known/jwks.json")

# Secret for signing session token
SESSION_SECRET = os.getenv("SESSION_SECRET", "default-secret")

_jwks_cache = None
_jwks_cache_time = 0
JWKS_CACHE_TTL = 60 * 60 

def get_jwks():
    """Fetch and cache the JWKS from Descope."""
    global _jwks_cache, _jwks_cache_time

    now = time.time()
    if _jwks_cache and (now - _jwks_cache_time) < JWKS_CACHE_TTL:
        return _jwks_cache

    response = requests.get(JWKS_URL)
    response.raise_for_status()

    _jwks_cache = response.json()
    _jwks_cache_time = now
    return _jwks_cache

def get_public_key(token):
    """Get the public key from the JWKS for verifying the ID token."""
    jwks = get_jwks()
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    for key in jwks["keys"]:
        if key["kid"] == kid:
            return RSAAlgorithm.from_jwk(key)

    logger.error(f"Public key not found for kid={kid}")

def verify_id_token(id_token: str, client_id: str):
    """Verify the ID token and return the payload."""
    if not id_token or id_token.strip() == "":
        logger.warning("ID token is empty or invalid.")
        return None
    
    public_key = get_public_key(id_token)

    payload = jwt.decode(
        id_token,
        public_key,
        algorithms=["RS256"],
        audience=client_id,
        options={"verify_exp": True}
    )
    return payload

def set_client_id(client_id: str):
    global CLIENT_ID
    CLIENT_ID = client_id
    
def verify_token(token: str) -> dict:
    """Verify the session token and return the payload."""
    if not isinstance(token, str) or not token.strip() or token.count('.') != 2:
        return None
    
    try:
        payload = jwt.decode(
            token, 
            SESSION_SECRET, 
            algorithms=["HS256"],
            audience=CLIENT_ID,
            options={"verify_signature": True}
        )
        return payload
    except jwt.InvalidTokenError as e:
        print(f"Invalid token: {e}")
        return None


class DescopeAuthState(rx.State):
    """
    State management for Descope authentication using OIDC and PKCE.

    Handles login, logout, session management, and user info extraction.
    """
    
    session_token: str = rx.Cookie("session_token", secure=True, path="/")
    code_verifier: str = rx.Cookie("code_verifier", secure=True, path="/")
    state: str = rx.Cookie("state", secure=True, path="/")
    error_message: str = ""

    @rx.event
    def start_login(self):
        """
        Initiate the login process by generating PKCE code verifier/challenge,
        setting state, and redirecting to the Descope authorization endpoint.
        """
        self.error_message = "" # Clear any previous error messages
        self.code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(self.code_verifier)
        self.state = generate_code_verifier()

        auth_url = (
            f"{AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
            f"&scope=openid%20profile%20email&code_challenge={code_challenge}"
            f"&code_challenge_method=S256&state={self.state}&flow={FLOW_ID}"
        )

        return rx.redirect(auth_url)
    
    @rx.event
    async def finalize_auth(self):
        """
        Complete the authentication process after redirect from Descope.

        Exchanges the authorization code for tokens, verifies ID token,
        and creates a session token for the user.
        
        """
        self.error_message = ""  # Clear any previous error messages
        if self.logged_in:
            return
        
        parsed_url = urlparse(self.router.page.raw_path)
        query = parse_qs(parsed_url.query)
        code = query.get("code", [None])[0]
        query_state = query.get("state", [None])[0]

        # Ensure all required parameters are present
        if not all([code, query_state, self.state, self.code_verifier]):
            self.error_message = "Missing code, state, or verifier — skipping finalize_auth."
            return
        
        # Prevent CSRF by checking state
        if query_state != self.state:
            self.error_message = "State mismatch — possible CSRF or replay attack."
            return
        
        try:
            async with AsyncClient() as client:
                res = await client.post(
                    TOKEN_URL, 
                    json={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": REDIRECT_URI,
                        "client_id": CLIENT_ID,
                        "code_verifier": self.code_verifier,
                    }
                )
                res.raise_for_status()
                tokens = res.json()

                # Verify ID token and extract claims
                try:
                    claims = verify_id_token(
                        tokens["id_token"],
                        client_id=CLIENT_ID
                    )
                except Exception as e:
                    self.error_message = f"ID token verification failed: {e}"
                    return
                
                # Use refresh token's exp as session expiration
                refresh_claims = jwt.decode(tokens["refresh_token"], options={"verify_signature": False})
                session_exp = refresh_claims.get("exp")
                
                now = int(time.time())
                session_payload = {
                    **claims,
                    "iat": now,
                    "exp": session_exp,
                }
                
                self.session_token = jwt.encode(session_payload, SESSION_SECRET, algorithm="HS256")
        except Exception as e:
            self.error_message = f"Authentication failed: {e}"
            return
    
    @rx.var
    def logged_in(self) -> bool:
        """
        Check if the user is logged in by verifying the session token.

        Returns:
            bool: True if session token is valid, False otherwise.
        """
        try:
            payload = verify_token(self.session_token)
            return payload is not None
        except Exception as e:
            logger.error(f"Error checking logged_in: {e}")
            return False
        
    @rx.var
    def userinfo(self) -> dict:
        """
        Extract user information from the session token.

        Returns:
            dict: User info (email, name, sub, picture) if available, else empty dict.
        """
        try:
            payload = verify_token(self.session_token)
            if payload:
                return {
                    "email": payload.get("email"),
                    "name": payload.get("name"),
                    "sub": payload.get("sub"),
                    "picture": payload.get("picture"),
                }
            return {}
        except Exception as e:
            logger.error(f"Error fetching userinfo: {e}")
            return {}
        
    @rx.event
    def logout(self):
        """
        Log out the user by clearing session-related state and removing the session cookie.
        """
        self.code_verifier = ""
        self.state = ""
        self.session_token = ""
        self.error_message = ""
        rx.remove_cookie("session_token")
        rx.remove_cookie("code_verifier")
        rx.remove_cookie("state")
