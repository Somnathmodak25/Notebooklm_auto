# gateway/routes/notebooks.py
"""
Notebook management endpoints.
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Header
from fastapi.security import APIKeyHeader
from gateway.middleware import RateLimiter
from gateway.models import CreateNotebookRequest, APIKey

router = APIRouter(prefix="/notebooks", tags=["Notebooks"])
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


@router.get("")
async def list_notebooks(
    request: Request,
    auth_info: tuple = Depends(get_account_and_validate),
):
    account_id, _ = auth_info
    state = request.app.state.app_state
    try:
        client = state.auth_mgr.get_client(account_id)
        async with client as nlm:
            notebooks = await nlm.notebooks.list()
            return {
                "notebooks": [
                    {
                        "id": getattr(nb, "id", str(nb)),
                        "title": getattr(nb, "title", "Untitled"),
                    }
                    for nb in notebooks
                ]
            }
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=401, detail=str(fnf))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list notebooks: {exc}")


@router.post("")
async def create_notebook(
    body: CreateNotebookRequest,
    request: Request,
    auth_info: tuple = Depends(get_account_and_validate),
):
    account_id, _ = auth_info
    state = request.app.state.app_state
    try:
        client = state.auth_mgr.get_client(account_id)
        async with client as nlm:
            nb = await nlm.notebooks.create(body.title)
            return {
                "id": getattr(nb, "id", str(nb)),
                "title": getattr(nb, "title", body.title),
                "status": "created",
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create notebook: {exc}")


@router.get("/{notebook_id}")
async def get_notebook(
    notebook_id: str,
    request: Request,
    auth_info: tuple = Depends(get_account_and_validate),
):
    account_id, _ = auth_info
    state = request.app.state.app_state
    try:
        client = state.auth_mgr.get_client(account_id)
        async with client as nlm:
            nb = await nlm.notebooks.get(notebook_id)
            return {
                "id": getattr(nb, "id", notebook_id),
                "title": getattr(nb, "title", "Notebook"),
                "sources_count": len(getattr(nb, "sources", [])),
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get notebook: {exc}")


@router.delete("/{notebook_id}")
async def delete_notebook(
    notebook_id: str,
    request: Request,
    auth_info: tuple = Depends(get_account_and_validate),
):
    account_id, _ = auth_info
    state = request.app.state.app_state
    try:
        client = state.auth_mgr.get_client(account_id)
        async with client as nlm:
            await nlm.notebooks.delete(notebook_id)
            return {"deleted": True, "notebook_id": notebook_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete notebook: {exc}")
