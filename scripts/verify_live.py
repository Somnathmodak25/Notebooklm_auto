import asyncio
from notebooklm import NotebookLMClient

async def main():
    print("Testing connection to Google NotebookLM using your cookies...")
    try:
        async with NotebookLMClient.from_storage("storage/tokens/main_storage_state.json") as client:
            notebooks = await client.notebooks.list()
            print(f"SUCCESS: Connected to NotebookLM!")
            print(f"Total Notebooks found: {len(notebooks)}")
            for idx, nb in enumerate(notebooks, 1):
                nb_id = getattr(nb, "id", str(nb))
                nb_title = getattr(nb, "title", "Untitled")
                print(f"  {idx}. [{nb_title}] (ID: {nb_id})")

            # Try to get details on the first notebook if any exists
            if notebooks:
                first_nb_id = getattr(notebooks[0], "id", str(notebooks[0]))
                print(f"\nTesting reading notebook details for ID: {first_nb_id}...")
                details = await client.notebooks.get(first_nb_id)
                sources = getattr(details, "sources", [])
                print(f"Successfully retrieved notebook: '{getattr(details, 'title', 'Untitled')}' with {len(sources)} sources.")
                for s in sources:
                    print(f"  - Source: {getattr(s, 'title', getattr(s, 'id', str(s)))}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
