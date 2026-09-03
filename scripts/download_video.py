import asyncio
import os
from notebooklm import NotebookLMClient
from notebooklm._types.enums import ArtifactStatus

async def main():
    notebook_id = "958fae0b-7839-49be-ae3c-e01dc0f37463"
    output_path = os.path.abspath("frontier_ai_agents_documentary.mp4")
    print(f"Checking Video Overview progress for notebook: {notebook_id}...")
    
    async with NotebookLMClient.from_storage("storage/tokens/main_storage_state.json") as client:
        artifacts = await client.artifacts.list(notebook_id)
        video_art = None
        for a in artifacts:
            if getattr(a, "id", None) == "fc02dc2f-23b9-4868-b0ed-a5ff16332f13" or "video" in str(getattr(a, "type", "")).lower():
                video_art = a
                break

        if not video_art:
            print("No video artifact found yet.")
            return

        status_val = getattr(video_art, "status", None)
        print(f"Artifact Title: {getattr(video_art, 'title', 'Untitled')}")
        print(f"Status: {status_val} ({ArtifactStatus(status_val).name if isinstance(status_val, int) else status_val})")

        if status_val == ArtifactStatus.COMPLETED or status_val == 3:
            print(f"\nVideo is READY! Downloading to {output_path}...")
            file_saved = await client.artifacts.download_video(notebook_id, output_path=output_path)
            print(f"SUCCESS: Video downloaded to: {file_saved}")
        elif status_val == ArtifactStatus.PROCESSING or status_val == 2:
            print("\nVideo is currently being rendered by Google NotebookLM.")
            print("Google typically takes 3-7 minutes to synthesize the full documentary voiceover, visuals, and video.")
        else:
            print(f"Current status: {status_val}")

if __name__ == "__main__":
    asyncio.run(main())
