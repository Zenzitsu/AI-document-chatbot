import os
import uuid
from typing import Any, Dict, List, Optional, Union
from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models

from app.config import settings

# Collection and embedding configurations
COLLECTION_NAME = "docs_rag"
MODEL_NAME = "BAAI/bge-small-en-v1.5"
VECTOR_SIZE = 384  # Embedding dimension for BAAI/bge-small-en-v1.5

# Retrieve credentials from settings or environment variables
QDRANT_URL = settings.QDRANT_URL or os.getenv("QDRANT_URL", "")
QDRANT_API_KEY = settings.QDRANT_API_KEY or os.getenv("QDRANT_API_KEY", "")

# Initialize Qdrant Client
# Connect to Qdrant Cloud using QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
client = QdrantClient(
    url=QDRANT_URL or None,
    api_key=QDRANT_API_KEY or None,
)

# Initialize FastEmbed text embedding model
embedding_model = TextEmbedding(model_name=MODEL_NAME)


def init_collection(
    collection_name: str = COLLECTION_NAME,
    vector_size: int = VECTOR_SIZE,
) -> bool:
    """
    Checks if the Qdrant collection exists. If not, initializes it
    configured for FastEmbed vectors (BAAI/bge-small-en-v1.5).
    """
    try:
        if not client.collection_exists(collection_name=collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE,
                ),
            )
            print(f"[Qdrant] Collection '{collection_name}' created successfully with {MODEL_NAME} ({vector_size}d).")
            return True
        return False
    except Exception as e:
        print(f"[Qdrant] Error checking/creating collection '{collection_name}': {e}")
        raise


def add_documents(
    chunks: Union[List[Union[Dict[str, Any], str]], Dict[str, Any], str],
    collection_name: str = COLLECTION_NAME,
) -> List[str]:
    """
    Embeds text chunks using FastEmbed and uploads them with metadata to Qdrant Cloud.
    
    Args:
        chunks: A single chunk or list of chunks. Each chunk can be a dictionary
                (with 'text' and optional 'metadata') or a raw text string.
        collection_name: Target collection name in Qdrant (defaults to docs_rag).
        
    Returns:
        List of generated point IDs uploaded to Qdrant.
    """
    # Ensure collection exists before inserting
    init_collection(collection_name=collection_name)

    # Normalize input to list of items
    chunk_list = [chunks] if isinstance(chunks, (dict, str)) else list(chunks)
    if not chunk_list:
        return []

    texts: List[str] = []
    payloads: List[Dict[str, Any]] = []

    for item in chunk_list:
        if isinstance(item, str):
            text = item
            payload = {"text": item}
        elif isinstance(item, dict):
            text = item.get("text", "")
            meta = item.get("metadata", {})
            payload = {"text": text}
            # Merge flat keys and nested metadata
            if isinstance(meta, dict):
                payload.update(meta)
            for k, v in item.items():
                if k not in ("text", "metadata"):
                    payload[k] = v
        else:
            text = getattr(item, "text", str(item))
            payload = {"text": text}
            if hasattr(item, "metadata") and isinstance(item.metadata, dict):
                payload.update(item.metadata)

        texts.append(text)
        payloads.append(payload)

    # Generate embeddings using FastEmbed
    embeddings_generator = embedding_model.embed(texts)
    embeddings = list(embeddings_generator)

    # Build Qdrant PointStruct instances
    points: List[models.PointStruct] = []
    point_ids: List[str] = []

    for embedding, payload in zip(embeddings, payloads):
        point_id = str(uuid.uuid4())
        point_ids.append(point_id)
        vector = embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)

        points.append(
            models.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        )

    # Upload documents to Qdrant Cloud
    client.upsert(
        collection_name=collection_name,
        points=points,
    )
    print(f"[Qdrant] Uploaded {len(points)} documents to '{collection_name}'.")

    return point_ids


# ---------------------------------------------------------------------------
# Test Block: Upload a dummy sentence to Qdrant Cloud
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n--- Testing Qdrant Cloud Vector Store ---")
    print(f"Connecting to Qdrant URL: {QDRANT_URL or 'Default/Local'}")
    print(f"Target Collection: {COLLECTION_NAME}")
    print(f"Embedding Model: {MODEL_NAME}")

    dummy_sentence = (
        "FastAPI with Qdrant Cloud and Gemini creates a high-performance RAG pipeline."
    )
    dummy_chunk = {
        "text": dummy_sentence,
        "metadata": {
            "filename": "test_document.txt",
            "page_number": 1,
            "source": "cli_test",
        },
    }

    try:
        print(f"\n[Test] Ingesting dummy sentence: '{dummy_sentence}'")
        point_ids = add_documents([dummy_chunk])
        print(f"[Test] Success! Uploaded Point ID(s): {point_ids}")

        # Verification query
        print("\n[Test] Running verification similarity search...")
        query_text = "Qdrant Cloud RAG pipeline"
        query_vector = next(embedding_model.embed([query_text]))
        vector_list = query_vector.tolist() if hasattr(query_vector, "tolist") else list(query_vector)

        search_results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=vector_list,
            limit=2,
        )

        print(f"[Test] Search returned {len(search_results)} result(s):")
        for idx, result in enumerate(search_results, start=1):
            print(f"  {idx}. Score: {result.score:.4f} | Text: {result.payload.get('text')} | Meta: {result.payload.get('filename')}")

    except Exception as exc:
        print(f"\n[Test] Error running test against Qdrant Cloud: {exc}")
        print("[Test] Please verify that QDRANT_URL and QDRANT_API_KEY in your .env file are valid.")
