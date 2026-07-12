import chromadb
from openai import OpenAI
from config import config


def get_chroma_client():
    return chromadb.HttpClient(
        host=config.CHROMA_HOST,
        port=config.CHROMA_PORT,
    )


def embed_text(text: str) -> list[float]:
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.embeddings.create(
        input=text,
        model=config.EMBEDDING_MODEL,
    )
    return response.data[0].embedding


def search_runbooks(alert_description: str, top_k: int = 1) -> dict | None:
    """
    Embed the alert description and search ChromaDB for the most
    relevant runbook. Returns dict with 'title' and 'content', or None.
    """
    try:
        chroma     = get_chroma_client()
        collection = chroma.get_collection(config.RUNBOOK_COLLECTION)

        if collection.count() == 0:
            return None

        query_embedding = embed_text(alert_description)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
        )

        if not results["documents"] or not results["documents"][0]:
            return None

        return {
            "title":   results["metadatas"][0][0].get("title", "Unknown Runbook"), # type: ignore
            "content": results["documents"][0][0],
        }

    except Exception:
        return None
