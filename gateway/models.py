# gateway/models.py
"""
Pydantic data models for NotebookLM FastAPI Gateway.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    TEXT = "text"
    URL = "url"
    FILE = "file"
    YOUTUBE = "youtube"


class VideoFormat(str, Enum):
    CINEMATIC = "cinematic"
    EXPLAINER = "explainer"
    SHORT = "short"


class VideoStyle(str, Enum):
    AUTO_SELECT = "auto_select"
    ANIME = "anime"
    CINEMATIC_REAL = "cinematic_real"
    MINIMAL_2D = "minimal_2d"
    CUSTOM = "custom"


class SlideDeckLength(str, Enum):
    SHORT = "short"
    DETAILED = "detailed"


class AudioFormat(str, Enum):
    PODCAST = "podcast"
    DEEP_DIVE = "deep_dive"
    BRIEF = "brief"


class ReportFormat(str, Enum):
    BRIEFING_DOC = "briefing_doc"
    STUDY_GUIDE = "study_guide"
    BLOG_POST = "blog_post"


# ── Request Models ────────────────────────────────────────────────

class CreateNotebookRequest(BaseModel):
    title: str = "New Notebook"


class AddTextSourceRequest(BaseModel):
    text: str
    title: str = "Text Source"


class AddURLSourceRequest(BaseModel):
    url: str


class ChatRequest(BaseModel):
    message: str
    source_ids: Optional[List[str]] = None


# ── Studio Generation Requests ────────────────────────────────────

class GenerateVideoRequest(BaseModel):
    source_ids: Optional[List[str]] = None
    language: str = "en"
    instructions: Optional[str] = None
    video_format: Optional[VideoFormat] = VideoFormat.EXPLAINER
    video_style: Optional[VideoStyle] = VideoStyle.AUTO_SELECT
    style_prompt: Optional[str] = None
    wait_for_completion: bool = True


class GenerateCinematicVideoRequest(BaseModel):
    source_ids: Optional[List[str]] = None
    language: str = "en"
    instructions: Optional[str] = None
    wait_for_completion: bool = True


class GenerateSlideDeckRequest(BaseModel):
    source_ids: Optional[List[str]] = None
    language: str = "en"
    instructions: Optional[str] = None
    length: Optional[SlideDeckLength] = SlideDeckLength.DETAILED
    wait_for_completion: bool = True


class GenerateAudioRequest(BaseModel):
    source_ids: Optional[List[str]] = None
    language: str = "en"
    instructions: Optional[str] = None
    audio_format: Optional[AudioFormat] = AudioFormat.PODCAST
    wait_for_completion: bool = True


class GenerateReportRequest(BaseModel):
    source_ids: Optional[List[str]] = None
    language: str = "en"
    instructions: Optional[str] = None
    report_format: Optional[ReportFormat] = ReportFormat.BRIEFING_DOC
    wait_for_completion: bool = True


class GenerateQuizRequest(BaseModel):
    source_ids: Optional[List[str]] = None
    language: str = "en"
    instructions: Optional[str] = None
    wait_for_completion: bool = True


# ── Admin Request Models ──────────────────────────────────────────

class SetupCookiesRequest(BaseModel):
    account_id: str = "main"
    cookies: Union[Dict[str, str], List[Dict[str, Any]]]
    description: Optional[str] = None


class CreateAPIKeyRequest(BaseModel):
    account_id: str = "main"
    name: str
    permissions: List[str] = ["read", "write", "chat", "studio"]
    rate_limit: int = 60


# ── Response / Entity Models ──────────────────────────────────────

class APIKey(BaseModel):
    key: str
    name: str
    account_id: str
    permissions: List[str] = ["read", "write", "chat", "studio"]
    rate_limit: int = 60
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    total_requests: int = 0
    is_active: bool = True
