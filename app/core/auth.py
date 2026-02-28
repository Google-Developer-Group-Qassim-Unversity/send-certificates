from fastapi import Depends, HTTPException, logger, status
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer
import logging
from app.core.config import is_dev, CLERK_DEV, CLERK_PROD


if is_dev:
    print("\t🆎 Running Clerk in development mode")
    clerk_config = ClerkConfig(jwks_url=CLERK_DEV)
else:
    print("\t🚀 Running Clerk in production mode")
    clerk_config = ClerkConfig(jwks_url=CLERK_PROD)

clerk_auth_guard = ClerkHTTPBearer(config=clerk_config)


def is_admin(credentials) -> bool:
    decoded = credentials.model_dump()["decoded"]
    metadata = decoded.get("metadata", {})
    return metadata.get("is_admin", False) or metadata.get("is_super_admin", False)


def is_super_admin(credentials) -> bool:
    decoded = credentials.model_dump()["decoded"]
    metadata = decoded.get("metadata", {})
    return metadata.get("is_super_admin", False)


def admin_guard(credentials=Depends(clerk_auth_guard)):
    print("User authenticated, checking admin privileges...")
    if not is_admin(credentials):
        metadata = credentials.model_dump().get("decoded", {}).get("metadata", {})
        print(f"Access Denied! User Metadata: {metadata}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return credentials


def super_admin_guard(credentials=Depends(clerk_auth_guard)):
    print("User authenticated, checking super admin privileges...")
    if not is_super_admin(credentials):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required",
        )
    return credentials
