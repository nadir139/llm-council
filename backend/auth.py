"""
Authentication middleware using Supabase Auth

Verifies JWT tokens issued by Supabase and extracts user information.
Supabase uses HS256 (symmetric) JWT signing with a secret key.
"""
import jwt
import os
from typing import Optional
from fastapi import HTTPException, Header
from . import config

# Supabase JWT configuration
SUPABASE_JWT_SECRET = config.SUPABASE_JWT_SECRET


async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Verify JWT token from Supabase Auth and return user information.

    Supabase tokens contain:
    - sub: user ID (UUID)
    - email: user's email address
    - exp: expiration timestamp

    Args:
        authorization: Bearer token from request header (format: "Bearer <token>")

    Returns:
        dict: User information with user_id, email, first_name, last_name

    Raises:
        HTTPException: If token is invalid, expired, or missing
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header"
        )

    # Extract token from "Bearer <token>" format
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication scheme. Expected 'Bearer <token>'"
            )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected 'Bearer <token>'"
        )

    # Verify and decode the Supabase JWT token
    try:
        # Supabase uses HS256 (symmetric signing) with JWT secret
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}  # Supabase doesn't use audience claim
        )

        # Extract user information from JWT payload
        user_id = payload.get("sub")  # Supabase user ID (UUID)
        email = payload.get("email")  # User's email

        # Get user metadata (first_name, last_name) if available
        user_metadata = payload.get("user_metadata", {})
        first_name = user_metadata.get("first_name")
        last_name = user_metadata.get("last_name")

        return {
            "user_id": user_id,
            "email": email or "unknown@supabase.local",
            "first_name": first_name,
            "last_name": last_name
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired. Please sign in again."
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication error: {str(e)}"
        )


def get_admin_key(admin_key: Optional[str] = Header(None, alias="X-Admin-Key")):
    """
    Verify admin API key for administrative endpoints (e.g., Stage 2 analytics).

    Admin endpoints require a separate API key sent via X-Admin-Key header.
    This is independent of user authentication.

    Args:
        admin_key: Admin API key from X-Admin-Key header

    Returns:
        bool: True if valid admin key

    Raises:
        HTTPException: If admin key is invalid or missing
    """
    if not admin_key:
        raise HTTPException(
            status_code=403,
            detail="Admin key required. Please provide X-Admin-Key header."
        )

    expected_key = config.ADMIN_API_KEY
    if not expected_key:
        raise HTTPException(
            status_code=500,
            detail="Admin key not configured on server"
        )

    if admin_key != expected_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid admin key"
        )

    return True
