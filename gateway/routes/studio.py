# gateway/routes/studio.py
"""
NotebookLM Studio generation & media download endpoints (Video, Slide Deck, Audio, Reports, Quizzes).
"""

import os
import tempfile
from typing import Optional, List
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader

from gateway.middleware import RateLimiter
from gateway.models import (
    GenerateVideoRequest,
    GenerateCinematicVideoRequest,
    GenerateSlideDeckRequest,
    GenerateAudioRequest,
    GenerateReportRequest,
    GenerateQuizRequest,
)

router = APIRouter(prefix="/notebooks", tags=["Studio"])
API_KEY_HEADER = APIKeyHeader(name="X-API-Key")


async def get_account_and_validate(request: Request, api_key: str = Depends(API_KEY_HEADER)) -> tuple:
    state = request.app.state.app_state
    try:
        key_data = await state.key_store.validate(api_key)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

    limiter = RateLimiter(state.redis)
    await limiter.check(api_key, key_data.rate_limit)

    if "studio" not in key_data.permissions and "write" not in key_data.permissions:
        raise HTTPException(status_code=403, detail="API key lacks 'studio' permission")

    return key_data.account_id, key_data


# ── List Studio Artifacts ─────────────────────────────────────────

@router.get("/{notebook_id}/studio/artifacts")
async def list_artifacts(
    notebook_id: str,
    request: Request,
    auth_info: tuple = Depends(get_account_and_validate),
):
    account_id, _ = auth_info
    state = request.app.state.app_state
    try:
        client = state.auth_mgr.get_client(account_id)
        async with client as nlm:
            artifacts = await nlm.artifacts.list(notebook_id)
            out = []
            for art in artifacts:
                out.append({
                    "id": getattr(art, "id", None),
                    "title": getattr(art, "title", "Untitled"),
                    "type": str(getattr(art, "type", "UNKNOWN")),
                    "created_at": str(getattr(art, "created_at", "")),
                })
            return {"notebook_id": notebook_id, "artifacts": out}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list artifacts: {exc}")


# ── Generate Video Overview ───────────────────────────────────────

@router.post("/{notebook_id}/studio/video")
async def generate_video(
    notebook_id: str,
    body: GenerateVideoRequest,
    request: Request,
    auth_info: tuple = Depends(get_account_and_validate),
):
    account_id, _ = auth_info
    state = request.app.state.app_state
    try:
        client = state.auth_mgr.get_client(account_id)
        async with client as nlm:
            status = await nlm.artifacts.generate_video(
                notebook_id=notebook_id,
                source_ids=body.source_ids,
                language=body.language,
                instructions=body.instructions,
                style_prompt=body.style_prompt,
            )
            task_id = getattr(status, "task_id", str(status))

            if body.wait_for_completion:
                await nlm.artifacts.wait_for_completion(notebook_id, task_id)
                return {
                    "status": "completed",
                    "task_id": task_id,
                    "notebook_id": notebook_id,
                    "type": "video",
                    "download_url": f"/v1/notebooks/{notebook_id}/studio/video/download",
                }

            return {
                "status": "pending",
                "task_id": task_id,
                "notebook_id": notebook_id,
                "type": "video",
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Video generation failed: {exc}")


@router.post("/{notebook_id}/studio/video/cinematic")
async def generate_cinematic_video(
    notebook_id: str,
    body: GenerateCinematicVideoRequest,
    request: Request,
    auth_info: tuple = Depends(get_account_and_validate),
):
    account_id, _ = auth_info
    state = request.app.state.app_state
    try:
        client = state.auth_mgr.get_client(account_id)
        async with client as nlm:
            status = await nlm.artifacts.generate_cinematic_video(
                notebook_id=notebook_id,
                source_ids=body.source_ids,
                language=body.language,
                instructions=body.instructions,
            )
            task_id = getattr(status, "task_id", str(status))

            if body.wait_for_completion:
                await nlm.artifacts.wait_for_completion(notebook_id, task_id)
                return {
                    "status": "completed",
                    "task_id": task_id,
                    "notebook_id": notebook_id,
                    "type": "cinematic_video",
                    "download_url": f"/v1/notebooks/{notebook_id}/studio/video/download",
                }

            return {
                "status": "pending",
                "task_id": task_id,
                "notebook_id": notebook_id,
                "type": "cinematic_video",
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Cinematic video generation failed: {exc}")


# ── Direct Stream / Download Video Overview ───────────────────────

@router.get("/{notebook_id}/studio/video/download")
async def download_video(
    notebook_id: str,
    request: Request,
    auth_info: tuple = Depends(get_account_and_validate),
):
    """Downloads and streams the generated Video Overview (.mp4) directly to caller."""
    account_id, _ = auth_info
    state = request.app.state.app_state
    temp_dir = tempfile.mkdtemp(prefix="nlm-video-")
    target_path = os.path.join(temp_dir, "video_overview.mp4")

    try:
        client = state.auth_mgr.get_client(account_id)
        async with client as nlm:
            output_file = await nlm.artifacts.download_video(notebook_id, output_path=target_path)
            if not output_file or not os.path.exists(output_file):
                raise HTTPException(status_code=404, detail="Video file not ready or not found")
            return FileResponse(
                path=output_file,
                filename="video_overview.mp4",
                media_type="video/mp4",
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to download video: {exc}")


# ── Generate Slide Deck ───────────────────────────────────────────

@router.post("/{notebook_id}/studio/slide-deck")
async def generate_slide_deck(
    notebook_id: str,
    body: GenerateSlideDeckRequest,
    request: Request,
    auth_info: tuple = Depends(get_account_and_validate),
):
    account_id, _ = auth_info
    state = request.app.state.app_state
    try:
        client = state.auth_mgr.get_client(account_id)
        async with client as nlm:
            status = await nlm.artifacts.generate_slide_deck(
                notebook_id=notebook_id,
                source_ids=body.source_ids,
                language=body.language,
                instructions=body.instructions,
            )
            task_id = getattr(status, "task_id", str(status))

            if body.wait_for_completion:
                await nlm.artifacts.wait_for_completion(notebook_id, task_id)
                return {
                    "status": "completed",
                    "task_id": task_id,
                    "notebook_id": notebook_id,
                    "type": "slide_deck",
                    "download_url": f"/v1/notebooks/{notebook_id}/studio/slide-deck/download",
                }

            return {
                "status": "pending",
                "task_id": task_id,
                "notebook_id": notebook_id,
                "type": "slide_deck",
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Slide deck generation failed: {exc}")


# ── Direct Stream / Download Slide Deck ───────────────────────────

@router.get("/{notebook_id}/studio/slide-deck/download")
async def download_slide_deck(
    notebook_id: str,
    request: Request,
    auth_info: tuple = Depends(get_account_and_validate),
):
    """Downloads and streams the generated Slide Deck (.pdf) directly to caller."""
    account_id, _ = auth_info
    state = request.app.state.app_state
    temp_dir = tempfile.mkdtemp(prefix="nlm-slides-")
    target_path = os.path.join(temp_dir, "slide_deck.pdf")

    try:
        client = state.auth_mgr.get_client(account_id)
        async with client as nlm:
            output_file = await nlm.artifacts.download_slide_deck(notebook_id, output_path=target_path)
            if not output_file or not os.path.exists(output_file):
                raise HTTPException(status_code=404, detail="Slide deck file not ready or not found")
            return FileResponse(
                path=output_file,
                filename="slide_deck.pdf",
                media_type="application/pdf",
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to download slide deck: {exc}")


# ── Generate Audio Overview ───────────────────────────────────────

@router.post("/{notebook_id}/studio/audio")
async def generate_audio(
    notebook_id: str,
    body: GenerateAudioRequest,
    request: Request,
    auth_info: tuple = Depends(get_account_and_validate),
):
    account_id, _ = auth_info
    state = request.app.state.app_state
    try:
        client = state.auth_mgr.get_client(account_id)
        async with client as nlm:
            status = await nlm.artifacts.generate_audio(
                notebook_id=notebook_id,
                source_ids=body.source_ids,
                language=body.language,
                instructions=body.instructions,
            )
            task_id = getattr(status, "task_id", str(status))

            if body.wait_for_completion:
                await nlm.artifacts.wait_for_completion(notebook_id, task_id)
                return {
                    "status": "completed",
                    "task_id": task_id,
                    "notebook_id": notebook_id,
                    "type": "audio",
                    "download_url": f"/v1/notebooks/{notebook_id}/studio/audio/download",
                }

            return {
                "status": "pending",
                "task_id": task_id,
                "notebook_id": notebook_id,
                "type": "audio",
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Audio overview generation failed: {exc}")


# ── Direct Stream / Download Audio Overview ───────────────────────

@router.get("/{notebook_id}/studio/audio/download")
async def download_audio(
    notebook_id: str,
    request: Request,
    auth_info: tuple = Depends(get_account_and_validate),
):
    """Downloads and streams the generated Audio Overview (.mp3) directly to caller."""
    account_id, _ = auth_info
    state = request.app.state.app_state
    temp_dir = tempfile.mkdtemp(prefix="nlm-audio-")
    target_path = os.path.join(temp_dir, "audio_overview.mp3")

    try:
        client = state.auth_mgr.get_client(account_id)
        async with client as nlm:
            output_file = await nlm.artifacts.download_audio(notebook_id, output_path=target_path)
            if not output_file or not os.path.exists(output_file):
                raise HTTPException(status_code=404, detail="Audio file not ready or not found")
            return FileResponse(
                path=output_file,
                filename="audio_overview.mp3",
                media_type="audio/mpeg",
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to download audio: {exc}")


# ── Generate Report ───────────────────────────────────────────────

@router.post("/{notebook_id}/studio/report")
async def generate_report(
    notebook_id: str,
    body: GenerateReportRequest,
    request: Request,
    auth_info: tuple = Depends(get_account_and_validate),
):
    account_id, _ = auth_info
    state = request.app.state.app_state
    try:
        client = state.auth_mgr.get_client(account_id)
        async with client as nlm:
            status = await nlm.artifacts.generate_report(
                notebook_id=notebook_id,
                source_ids=body.source_ids,
                language=body.language,
                instructions=body.instructions,
            )
            task_id = getattr(status, "task_id", str(status))

            if body.wait_for_completion:
                await nlm.artifacts.wait_for_completion(notebook_id, task_id)
                return {
                    "status": "completed",
                    "task_id": task_id,
                    "notebook_id": notebook_id,
                    "type": "report",
                }

            return {
                "status": "pending",
                "task_id": task_id,
                "notebook_id": notebook_id,
                "type": "report",
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}")
