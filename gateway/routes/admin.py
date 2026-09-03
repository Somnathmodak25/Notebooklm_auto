# gateway/routes/admin.py
"""
Admin management endpoints (Cookie setup, API Key CRUD).
Protected by X-Admin-Token header.
"""

import os
from fastapi import APIRouter, Header, HTTPException, Request
from gateway.models import SetupCookiesRequest, CreateAPIKeyRequest

router = APIRouter(prefix="/admin", tags=["Admin"])


def verify_admin(token: str = Header(..., alias="X-Admin-Token")):
    expected = os.getenv("ADMIN_TOKEN", "default-admin-secret-key")
    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid admin token")


@router.post("/accounts/setup-cookies")
async def setup_cookies(
    body: SetupCookiesRequest,
    request: Request,
    admin_token: str = Header(..., alias="X-Admin-Token"),
):
    verify_admin(admin_token)
    state = request.app.state.app_state
    try:
        path = state.auth_mgr.save_cookies(body.account_id, body.cookies)
        return {
            "status": "ok",
            "account_id": body.account_id,
            "storage_state_path": str(path),
            "message": "Cookies saved and storage state created. Ready to create API key.",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to setup cookies: {exc}")


@router.get("/accounts")
async def list_accounts(
    request: Request,
    admin_token: str = Header(..., alias="X-Admin-Token"),
):
    verify_admin(admin_token)
    state = request.app.state.app_state
    accounts = state.auth_mgr.list_accounts()
    return {"accounts": accounts}


@router.post("/accounts/{account_id}/validate-cookies")
async def validate_cookies(
    account_id: str,
    request: Request,
    admin_token: str = Header(..., alias="X-Admin-Token"),
):
    """Validates if saved cookies are functional and contain required session tokens."""
    verify_admin(admin_token)
    state = request.app.state.app_state
    try:
        client = state.auth_mgr.get_client(account_id)
        async with client as nlm:
            notebooks = await nlm.notebooks.list()
            return {
                "account_id": account_id,
                "status": "valid",
                "notebooks_count": len(notebooks),
            }
    except Exception as exc:
        return {
            "account_id": account_id,
            "status": "invalid",
            "error": str(exc),
            "hint": "Ensure 'SID', 'HSID', 'APISID', 'SAPISID', '__Secure-1PSID', and '__Secure-3PSID' cookies are included.",
        }



@router.post("/api-keys")
async def create_api_key(
    body: CreateAPIKeyRequest,
    request: Request,
    admin_token: str = Header(..., alias="X-Admin-Token"),
):
    verify_admin(admin_token)
    state = request.app.state.app_state
    try:
        api_key = await state.key_store.create(
            account_id=body.account_id,
            name=body.name,
            permissions=body.permissions,
            rate_limit=body.rate_limit,
        )
        return {
            "api_key": api_key.key,
            "name": api_key.name,
            "account_id": api_key.account_id,
            "permissions": api_key.permissions,
            "rate_limit": api_key.rate_limit,
            "warning": "Save this API key now; it will not be displayed again.",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create API key: {exc}")


@router.get("/api-keys")
async def list_api_keys(
    request: Request,
    account_id: str = None,
    admin_token: str = Header(..., alias="X-Admin-Token"),
):
    verify_admin(admin_token)
    state = request.app.state.app_state
    keys = await state.key_store.list_keys(account_id)
    return {"api_keys": keys}


@router.delete("/api-keys/{key}")
async def revoke_api_key(
    key: str,
    request: Request,
    admin_token: str = Header(..., alias="X-Admin-Token"),
):
    verify_admin(admin_token)
    state = request.app.state.app_state
    await state.key_store.revoke(key)
    return {"status": "revoked"}
