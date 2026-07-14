import chromadb
from pathlib import Path
from openai import OpenAI
from config import config


def ingest():
    client     = OpenAI(api_key=config.OPENAI_API_KEY)
    chroma     = chromadb.HttpClient(
        host=config.CHROMA_HOST,
        port=config.CHROMA_PORT,
    )
    collection = chroma.get_or_create_collection(config.RUNBOOK_COLLECTION)

    runbook_dir   = Path("data/runbooks")
    runbook_files = list(runbook_dir.glob("*.md"))
    print(f"Found {len(runbook_files)} runbooks to ingest")

    for filepath in runbook_files:
        content = filepath.read_text(encoding="utf-8")
        title   = filepath.stem.replace("_", " ").title()

        response = client.embeddings.create(
            input=content,
            model=config.EMBEDDING_MODEL,
        )
        embedding = response.data[0].embedding

        collection.add(
            documents=[content],
            embeddings=[embedding],
            metadatas=[{"title": title, "filename": filepath.name}],
            ids=[filepath.stem],
        )
        print(f"  Ingested: {title}")

    print(f"\nDone. {len(runbook_files)} runbooks in '{config.RUNBOOK_COLLECTION}'")


if __name__ == "__main__":
    ingest()
