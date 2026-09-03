import asyncio
from notebooklm import NotebookLMClient

async def main():
    notebook_id = "958fae0b-7839-49be-ae3c-e01dc0f37463"
    print(f"Checking status for Notebook: {notebook_id}...")
    async with NotebookLMClient.from_storage("storage/tokens/main_storage_state.json") as client:
        # Check sources
        sources = await client.sources.list(notebook_id)
        print(f"\n--- Sources In Notebook ({len(sources)}) ---")
        for s in sources:
            print(f" - [{getattr(s, 'title', 'Untitled')}] (Type: {getattr(s, 'type', 'unknown')}, ID: {getattr(s, 'id', s)})")

        # Check video / artifacts
        artifacts = await client.artifacts.list(notebook_id)
        print(f"\n--- Artifacts In Notebook ({len(artifacts)}) ---")
        for a in artifacts:
            print(f" - [{getattr(a, 'title', 'Untitled')}] Type: {getattr(a, 'type', 'unknown')}, Status: {getattr(a, 'status', 'unknown')}, ID: {getattr(a, 'id', a)}")

if __name__ == "__main__":
    asyncio.run(main())
