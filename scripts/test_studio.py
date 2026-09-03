#!/usr/bin/env python3
# scripts/test_studio.py
"""
Standalone test script to verify NotebookLM Studio Video Overview and Slide Deck generation
using the notebooklm-py SDK.

Usage:
  python scripts/test_studio.py [--storage storage_state.json]
"""

import sys
import asyncio
import argparse
from pathlib import Path

try:
    from notebooklm import NotebookLMClient
except ImportError:
    print("❌ notebooklm-py is not installed. Run: pip install -e .")
    sys.exit(1)


async def main():
    parser = argparse.ArgumentParser(description="Test NotebookLM Studio Video & Slide Deck Generation")
    parser.add_argument(
        "--storage",
        default="storage/tokens/main_storage_state.json",
        help="Path to Playwright storage_state.json containing NotebookLM session cookies",
    )
    args = parser.parse_args()

    storage_path = Path(args.storage)
    if not storage_path.exists():
        print(f"⚠️ Storage state file not found at: {storage_path}")
        print("Creating dummy structure for demonstration. Populate with valid cookies to run live test.")
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        return

    print(f"🔑 Using storage state: {storage_path}")

    async with NotebookLMClient.from_storage(str(storage_path)) as client:
        print("1. Listing notebooks...")
        notebooks = await client.notebooks.list()
        print(f"Found {len(notebooks)} existing notebooks.")

        print("2. Creating test notebook for Studio Automation...")
        nb = await client.notebooks.create("Studio Automation Verification Test")
        nb_id = getattr(nb, "id", str(nb))
        print(f"✅ Created notebook ID: {nb_id}")

        print("3. Adding sample source text...")
        source = await client.sources.add_text(
            nb_id,
            "NotebookLM Studio allows users to automatically transform research documents into Video Overviews, "
            "Slide Decks, Podcast Audio Overviews, and Briefing Documents using advanced AI models.",
            title="NotebookLM Studio Capabilities"
        )
        print(f"✅ Source added: {getattr(source, 'id', 'added')}")

        print("4. Triggering Slide Deck Generation...")
        try:
            slide_status = await client.artifacts.generate_slide_deck(nb_id, language="en")
            task_id = getattr(slide_status, "task_id", str(slide_status))
            print(f"⏳ Slide deck generation initiated (Task ID: {task_id}). Waiting for completion...")
            await client.artifacts.wait_for_completion(nb_id, task_id)
            print("🎉 Slide Deck generation complete!")
        except Exception as e:
            print(f"❌ Slide deck generation error: {e}")

        print("5. Triggering Video Overview Generation...")
        try:
            video_status = await client.artifacts.generate_video(nb_id, language="en")
            task_id = getattr(video_status, "task_id", str(video_status))
            print(f"⏳ Video overview generation initiated (Task ID: {task_id}). Waiting for completion...")
            await client.artifacts.wait_for_completion(nb_id, task_id)
            print("🎉 Video Overview generation complete!")
        except Exception as e:
            print(f"❌ Video overview generation error: {e}")

        print("6. Listing generated artifacts...")
        artifacts = await client.artifacts.list(nb_id)
        for art in artifacts:
            print(f" - [{getattr(art, 'type', 'ARTIFACT')}] {getattr(art, 'title', 'Untitled')} (ID: {getattr(art, 'id', '-')})")


if __name__ == "__main__":
    asyncio.run(main())
