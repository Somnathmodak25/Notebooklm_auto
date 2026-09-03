# gateway/routes/sources.py
"""
Source management endpoints.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.security import APIKeyHeader
from gateway.middleware import RateLimiter
from gateway.models import AddTextSourceRequest, AddURLSourceRequest

router = APIRouter(prefix="/notebooks", tags=["Sources"])
API_KEY_HEADER = APIKeyHeader(name="X-API-Key")


async def get_account_and_validate(request: Request, api_key: str = Depends(API_KEY_HEADER)) -> tuple:
    state = request.app.state.app_state
    try:
        key_data = await state.key_store.validate(api_key)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

    limiter = RateLimiter(state.redis)
    await limiter.check(api_key, key_data.rate_limit)
    return key_data.account_id, key_data


@router.post("/{notebook_id}/sources/text")
async def add_text_source(
    notebook_id: str,
    body: AddTextSourceRequest,
    request: Request,
    auth_info: tuple = Depends(get_account_and_validate),
):
    account_id, _ = auth_info
    state = request.app.state.app_state
    try:
        client = state.auth_mgr.get_client(account_id)
        async with client as nlm:
            source = await nlm.sources.add_text(
                notebook_id,
                body.title,
                body.text,
            )
            return {
                "status": "added",
                "source_id": getattr(source, "id", None),
                "title": body.title,
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to add text source: {exc}")


@router.post("/{notebook_id}/sources/url")
async def add_url_source(
    notebook_id: str,
    body: AddURLSourceRequest,
    request: Request,
    auth_info: tuple = Depends(get_account_and_validate),
):
    account_id, _ = auth_info
    state = request.app.state.app_state
    try:
        client = state.auth_mgr.get_client(account_id)
        async with client as nlm:
            source = await nlm.sources.add_url(notebook_id, body.url)
            return {
                "status": "added",
                "source_id": getattr(source, "id", None),
                "url": body.url,
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to add URL source: {exc}")


@router.delete("/{notebook_id}/sources/{source_id}")
async def delete_source(
    notebook_id: str,
    source_id: str,
    request: Request,
    auth_info: tuple = Depends(get_account_and_validate),
):
    account_id, _ = auth_info
    state = request.app.state.app_state
    try:
        client = state.auth_mgr.get_client(account_id)
        async with client as nlm:
            await nlm.sources.delete(notebook_id, source_id)
            return {"deleted": True, "source_id": source_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete source: {exc}")
