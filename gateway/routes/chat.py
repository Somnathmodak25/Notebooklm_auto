# gateway/routes/chat.py
"""
Chat and conversation endpoints.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.security import APIKeyHeader
from gateway.middleware import RateLimiter
from gateway.models import ChatRequest

router = APIRouter(prefix="/notebooks", tags=["Chat"])
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


@router.post("/{notebook_id}/chat")
async def chat(
    notebook_id: str,
    body: ChatRequest,
    request: Request,
    auth_info: tuple = Depends(get_account_and_validate),
):
    account_id, _ = auth_info
    state = request.app.state.app_state
    try:
        client = state.auth_mgr.get_client(account_id)
        async with client as nlm:
            res = await nlm.chat.ask(
                notebook_id,
                body.message,
            )
            return {
                "answer": getattr(res, "answer", str(res)),
                "citations": getattr(res, "citations", []),
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat query failed: {exc}")
