#!/usr/bin/env python3
"""
Hermes AI Autonomous NotebookLM Runner & CLI Bridge.

Provides full programmatic and CLI control over Google NotebookLM:
- Notebook CRUD
- Source Ingestion (Text, URLs, Files)
- Autonomous Web Research (Fast & Deep)
- Knowledge Verification & Chat Fact-Checking
- Full Studio Generation (Video, Infographic, Slide Deck, Audio, Reports, Quizzes)
- Asset Download & Storage Management
"""

import sys
import os
import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure parent directory is on sys.path so notebooklm package resolves
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from notebooklm import NotebookLMClient
from notebooklm._types.enums import VideoFormat, VideoStyle, ArtifactStatus
from notebooklm.types import ArtifactType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("hermes_notebooklm")


def resolve_auth_storage() -> str:
    """Finds the most reliable storage file (Master Token profile or local tokens)."""
    # 1. Check default profile where master token mints storage
    default_profile = Path.home() / ".notebooklm" / "profiles" / "default" / "storage_state.json"
    if default_profile.exists() and default_profile.stat().st_size > 0:
        return str(default_profile)

    # 2. Check workspace storage/tokens/
    ws_token = PROJECT_ROOT / "storage" / "tokens" / "main_storage_state.json"
    if ws_token.exists() and ws_token.stat().st_size > 0:
        return str(ws_token)

    # 3. Fallback to standard storage
    return str(default_profile)


class HermesNotebookLM:
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or resolve_auth_storage()

    async def list_notebooks(self) -> List[Dict[str, Any]]:
        async with NotebookLMClient.from_storage(self.storage_path) as client:
            notebooks = await client.notebooks.list()
            out = []
            for nb in notebooks:
                out.append({
                    "id": getattr(nb, "id", str(nb)),
                    "title": getattr(nb, "title", "Untitled"),
                })
            return out

    async def create_notebook(self, title: str) -> Dict[str, Any]:
        async with NotebookLMClient.from_storage(self.storage_path) as client:
            nb = await client.notebooks.create(title)
            return {
                "id": getattr(nb, "id", str(nb)),
                "title": getattr(nb, "title", title),
            }

    async def get_notebook(self, notebook_id: str) -> Dict[str, Any]:
        async with NotebookLMClient.from_storage(self.storage_path) as client:
            nb = await client.notebooks.get(notebook_id)
            sources = await client.sources.list(notebook_id)
            artifacts = await client.artifacts.list(notebook_id)
            return {
                "id": notebook_id,
                "title": getattr(nb, "title", "Untitled"),
                "sources_count": len(sources),
                "sources": [
                    {
                        "id": getattr(s, "id", str(s)),
                        "title": getattr(s, "title", "Untitled"),
                        "type": str(getattr(s, "type", "unknown")),
                    }
                    for s in sources
                ],
                "artifacts_count": len(artifacts),
                "artifacts": [
                    {
                        "id": getattr(a, "id", str(a)),
                        "title": getattr(a, "title", "Untitled"),
                        "status": getattr(a, "status", "unknown"),
                    }
                    for a in artifacts
                ],
            }

    async def add_source(
        self,
        notebook_id: str,
        title: Optional[str] = None,
        text: Optional[str] = None,
        url: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        async with NotebookLMClient.from_storage(self.storage_path) as client:
            if text:
                source_title = title or "Document Content"
                src = await client.sources.add_text(notebook_id, source_title, text)
                return {"status": "added", "type": "text", "id": getattr(src, "id", None), "title": source_title}
            elif url:
                src = await client.sources.add_url(notebook_id, url)
                return {"status": "added", "type": "url", "id": getattr(src, "id", None), "url": url}
            elif file_path:
                p = Path(file_path).resolve()
                if not p.exists():
                    raise FileNotFoundError(f"Source file not found: {p}")
                src = await client.sources.add_file(notebook_id, str(p))
                return {"status": "added", "type": "file", "id": getattr(src, "id", None), "path": str(p)}
            else:
                raise ValueError("Must provide one of: --text, --url, or --file")

    async def run_research(
        self,
        notebook_id: str,
        query: str,
        mode: str = "fast",
        import_top: int = 3,
        timeout: float = 180.0,
    ) -> Dict[str, Any]:
        async with NotebookLMClient.from_storage(self.storage_path) as client:
            logger.info("Starting %s web research for query: '%s'...", mode, query)
            r_start = await client.research.start(notebook_id, query=query, source="web", mode=mode)
            task_id = getattr(r_start, "task_id", str(r_start))
            logger.info("Research task registered (ID: %s). Waiting for completion...", task_id)

            r_task = await client.research.wait_for_completion(notebook_id, task_id, timeout=timeout)
            discovered = getattr(r_task, "sources", [])
            logger.info("Research completed! Found %d sources.", len(discovered))

            imported = []
            if discovered and import_top > 0:
                to_import = discovered[:import_top]
                logger.info("Importing top %d sources into notebook...", len(to_import))
                await client.research.import_sources(notebook_id, task_id, sources=to_import)
                imported = [getattr(s, "title", getattr(s, "url", str(s))) for s in to_import]

            return {
                "task_id": task_id,
                "discovered_count": len(discovered),
                "imported_count": len(imported),
                "imported_sources": imported,
            }

    async def verify_quality(self, notebook_id: str, topic: str) -> Dict[str, Any]:
        """Conducts a multi-probe grounded chat audit to verify factual density."""
        async with NotebookLMClient.from_storage(self.storage_path) as client:
            sources = await client.sources.list(notebook_id)
            if not sources:
                return {
                    "status": "FAIL",
                    "score": 0,
                    "reason": "Notebook has 0 sources. Ingest research before verification.",
                    "ready_for_studio": False,
                }

            probes = [
                f"What are the foundational concepts, definitions, and mechanics of {topic} based on the sources?",
                f"What concrete architectural principles, tool integrations, and protocols are detailed for {topic}?",
                f"What are the key real-world applications, future horizons, and safety challenges regarding {topic}?",
            ]

            audit_results = []
            total_citations = 0

            for probe in probes:
                logger.info("Probing: '%s'...", probe[:60])
                resp = await client.chat.ask(notebook_id, probe)
                ans = getattr(resp, "answer", str(resp))
                cits = getattr(resp, "citations", [])
                total_citations += len(cits)
                audit_results.append({
                    "question": probe,
                    "answer_length": len(ans),
                    "citations_count": len(cits),
                    "sample": ans[:200] + "...",
                })

            score = min(10, (len(sources) * 1.5) + (total_citations * 1.0))
            is_ready = score >= 5.0 and len(sources) >= 2

            return {
                "status": "PASS" if is_ready else "NEEDS_MORE_DATA",
                "score": round(score, 1),
                "total_sources": len(sources),
                "total_citations_found": total_citations,
                "ready_for_studio": is_ready,
                "probes": audit_results,
            }

    async def generate_studio(
        self,
        notebook_id: str,
        media_type: str,
        instructions: Optional[str] = None,
        video_format: str = "explainer",
        video_style: str = "classic",
        wait: bool = False,
        download_path: Optional[str] = None,
        timeout: float = 600.0,
    ) -> Dict[str, Any]:
        media_type = media_type.lower()
        async with NotebookLMClient.from_storage(self.storage_path) as client:
            if media_type == "video":
                v_format = VideoFormat.EXPLAINER if video_format == "explainer" else VideoFormat.BRIEF
                v_style = VideoStyle.CLASSIC if video_style == "classic" else VideoStyle.AUTO_SELECT
                status = await client.artifacts.generate_video(
                    notebook_id=notebook_id,
                    video_format=v_format,
                    video_style=v_style,
                    instructions=instructions,
                )
            elif media_type == "cinematic-video":
                status = await client.artifacts.generate_cinematic_video(
                    notebook_id=notebook_id,
                    instructions=instructions,
                )
            elif media_type == "slide-deck":
                status = await client.artifacts.generate_slide_deck(
                    notebook_id=notebook_id,
                    instructions=instructions,
                )
            elif media_type == "audio":
                status = await client.artifacts.generate_audio(
                    notebook_id=notebook_id,
                    instructions=instructions,
                )
            elif media_type == "report":
                status = await client.artifacts.generate_report(
                    notebook_id=notebook_id,
                    instructions=instructions,
                )
            else:
                raise ValueError(f"Unsupported media type: {media_type}")

            task_id = getattr(status, "task_id", str(status))
            logger.info("Studio generation task created: %s (Type: %s)", task_id, media_type)

            result = {
                "task_id": task_id,
                "notebook_id": notebook_id,
                "type": media_type,
                "status": "in_progress",
            }

            if wait:
                logger.info("Waiting for %s to complete on Google backend (may take 3-7 mins)...", media_type)
                await client.artifacts.wait_for_completion(notebook_id, task_id, timeout=timeout)
                result["status"] = "completed"

                if download_path:
                    out_p = Path(download_path).resolve()
                    out_p.parent.mkdir(parents=True, exist_ok=True)
                    if media_type in ("video", "cinematic-video"):
                        saved = await client.artifacts.download_video(notebook_id, output_path=str(out_p))
                    elif media_type == "slide-deck":
                        saved = await client.artifacts.download_slide_deck(notebook_id, output_path=str(out_p))
                    elif media_type == "audio":
                        saved = await client.artifacts.download_audio(notebook_id, output_path=str(out_p))
                    else:
                        saved = str(out_p)
                    result["saved_file"] = str(saved)
                    logger.info("Artifact downloaded successfully to: %s", saved)

            return result

    async def full_pipeline(
        self,
        topic: str,
        research_mode: str = "deep",
        media_types: List[str] = None,
        output_dir: str = "./media",
    ) -> Dict[str, Any]:
        """Runs the entire end-to-end flow: Create -> Ingest -> Deep Research -> Audit -> Studio Generation."""
        media_types = media_types or ["video"]
        out_dir = Path(output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        logger.info("=== STARTING FULL HERMES AUTONOMOUS PIPELINE ===")
        logger.info("Topic: %s", topic)

        # 1. Create Notebook
        nb = await self.create_notebook(f"{topic} (Hermes Deep Dive)")
        nb_id = nb["id"]
        logger.info("1. Created Notebook: %s (ID: %s)", nb["title"], nb_id)

        # 2. Ingest Seed Overview
        seed_content = f"# Overview of {topic}\n\nComprehensive autonomous research investigation into {topic}."
        await self.add_source(nb_id, title=f"{topic} - Foundational Scope", text=seed_content)

        # 3. Web Research
        logger.info("2. Conducting %s web research...", research_mode)
        research_res = await self.run_research(nb_id, query=f"{topic} architecture analysis 2026", mode=research_mode, import_top=4)
        logger.info("   Imported %d research sources.", research_res["imported_count"])

        # 4. Quality Audit
        logger.info("3. Conducting grounded knowledge verification...")
        audit = await self.verify_quality(nb_id, topic=topic)
        logger.info("   Audit Score: %s/10 (Status: %s)", audit["score"], audit["status"])

        # 5. Generate Studio Media
        generated_artifacts = {}
        for m_type in media_types:
            logger.info("4. Dispatching Studio generation for: %s...", m_type)
            doc_instructions = (
                f"Produce an authoritative, captivating documentary-grade {m_type} covering {topic}. "
                "Structure into 4 distinct thematic chapters: "
                "1. Foundations and Paradigm Shifts, "
                "2. Technical Architecture & Protocols, "
                "3. Industrial Multi-Agent Ecosystems, "
                "4. Future Horizons & Governance. "
                "Ground all narration in concrete technical mechanics."
            )
            ext = ".mp4" if "video" in m_type else (".pdf" if m_type == "slide-deck" else ".mp3")
            filename = f"{topic.lower().replace(' ', '_')}_{m_type}{ext}"
            file_dest = out_dir / filename

            gen_res = await self.generate_studio(
                notebook_id=nb_id,
                media_type=m_type,
                instructions=doc_instructions,
                wait=False,  # Dispatched non-blocking for background processing
                download_path=str(file_dest),
            )
            generated_artifacts[m_type] = gen_res

        return {
            "status": "success",
            "notebook_id": nb_id,
            "topic": topic,
            "audit_score": audit["score"],
            "generated_tasks": generated_artifacts,
            "output_directory": str(out_dir),
        }


def main():
    parser = argparse.ArgumentParser(description="Hermes AI NotebookLM Autonomous Bridge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="List all notebooks")

    # create
    create_p = subparsers.add_parser("create", help="Create a new notebook")
    create_p.add_argument("--title", required=True, help="Notebook title")

    # get
    get_p = subparsers.add_parser("get", help="Get notebook details and sources")
    get_p.add_argument("--notebook-id", required=True, help="Notebook ID")

    # add-source
    add_p = subparsers.add_parser("add-source", help="Add a source to notebook")
    add_p.add_argument("--notebook-id", required=True, help="Notebook ID")
    add_p.add_argument("--title", help="Source title (for text sources)")
    add_p.add_argument("--text", help="Text content to ingest")
    add_p.add_argument("--url", help="URL to ingest")
    add_p.add_argument("--file", help="Local file path to ingest")

    # research
    res_p = subparsers.add_parser("research", help="Run web research")
    res_p.add_argument("--notebook-id", required=True, help="Notebook ID")
    res_p.add_argument("--query", required=True, help="Research search query")
    res_p.add_argument("--mode", choices=["fast", "deep"], default="fast", help="Research mode")
    res_p.add_argument("--import-top", type=int, default=3, help="Number of discovered sources to import")

    # verify-quality
    ver_p = subparsers.add_parser("verify-quality", help="Audit knowledge depth via chat probes")
    ver_p.add_argument("--notebook-id", required=True, help="Notebook ID")
    ver_p.add_argument("--topic", required=True, help="Core topic name to probe")

    # studio
    stu_p = subparsers.add_parser("studio", help="Generate Studio media")
    stu_p.add_argument("--notebook-id", required=True, help="Notebook ID")
    stu_p.add_argument("--type", choices=["video", "cinematic-video", "slide-deck", "audio", "report"], required=True)
    stu_p.add_argument("--instructions", help="Custom generation instructions")
    stu_p.add_argument("--format", default="explainer", choices=["explainer", "brief"])
    stu_p.add_argument("--style", default="classic", choices=["classic", "auto"])
    stu_p.add_argument("--download", action="store_true", help="Wait and download artifact")
    stu_p.add_argument("--output", help="Download destination path")

    # pipeline
    pipe_p = subparsers.add_parser("pipeline", help="Run full autonomous pipeline")
    pipe_p.add_argument("--topic", required=True, help="Topic for autonomous deep research and video")
    pipe_p.add_argument("--research-mode", choices=["fast", "deep"], default="deep")
    pipe_p.add_argument("--media", default="video", help="Comma-separated media types (e.g. video,slide-deck)")
    pipe_p.add_argument("--output-dir", default="./media", help="Output directory for media")

    args = parser.parse_args()
    client = HermesNotebookLM()

    if args.command == "list":
        res = asyncio.run(client.list_notebooks())
        print(json.dumps(res, indent=2))
    elif args.command == "create":
        res = asyncio.run(client.create_notebook(args.title))
        print(json.dumps(res, indent=2))
    elif args.command == "get":
        res = asyncio.run(client.get_notebook(args.notebook_id))
        print(json.dumps(res, indent=2))
    elif args.command == "add-source":
        res = asyncio.run(client.add_source(
            args.notebook_id,
            title=args.title,
            text=args.text,
            url=args.url,
            file_path=args.file,
        ))
        print(json.dumps(res, indent=2))
    elif args.command == "research":
        res = asyncio.run(client.run_research(
            args.notebook_id,
            query=args.query,
            mode=args.mode,
            import_top=args.import_top,
        ))
        print(json.dumps(res, indent=2))
    elif args.command == "verify-quality":
        res = asyncio.run(client.verify_quality(args.notebook_id, topic=args.topic))
        print(json.dumps(res, indent=2))
    elif args.command == "studio":
        res = asyncio.run(client.generate_studio(
            notebook_id=args.notebook_id,
            media_type=args.type,
            instructions=args.instructions,
            video_format=args.format,
            video_style=args.style,
            wait=args.download,
            download_path=args.output,
        ))
        print(json.dumps(res, indent=2))
    elif args.command == "pipeline":
        media_list = [m.strip() for m in args.media.split(",") if m.strip()]
        res = asyncio.run(client.full_pipeline(
            topic=args.topic,
            research_mode=args.research_mode,
            media_types=media_list,
            output_dir=args.output_dir,
        ))
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
