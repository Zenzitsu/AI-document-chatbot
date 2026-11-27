import os
import uuid
from typing import Any, Dict, List, Optional, Union
from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models

from app.config import settings

# Collection and embedding configurations
COLLECTION_NAME = settings.QDRANT_COLLECTION_NAME or "rag_collection"
MODEL_NAME = settings.EMBEDDING_MODEL_NAME or "BAAI/bge-small-en-v1.5"
VECTOR_SIZE = 384  # Embedding dimension for BAAI/bge-small-en-v1.5

# Retrieve credentials from settings or environment variables
QDRANT_URL = settings.QDRANT_URL or os.getenv("QDRANT_URL", "")
QDRANT_API_KEY = settings.QDRANT_API_KEY or os.getenv("QDRANT_API_KEY", "")


def _init_qdrant_client() -> QdrantClient:
    """
    Initializes QdrantClient based on configuration:
    - If a valid remote URL is provided (not placeholder), connects to remote cluster.
    - If url is ':memory:' or 'memory', uses in-memory Qdrant.
    - Otherwise, falls back to embedded local storage ('./qdrant_data') so the app
      runs out of the box without requiring external cloud accounts.
    """
    url = (settings.QDRANT_URL or os.getenv("QDRANT_URL", "")).strip()
    api_key = (settings.QDRANT_API_KEY or os.getenv("QDRANT_API_KEY", "")).strip()

    is_placeholder = "your-cluster-id" in url or "your-qdrant-api-key" in api_key

    if url and not is_placeholder and url.lower() not in (":memory:", "memory", "local"):
        print(f"[Qdrant] Connecting to remote cluster at {url}...")
        return QdrantClient(url=url, api_key=api_key or None)

    if url.lower() in (":memory:", "memory"):
        print("[Qdrant] Running with in-memory storage (:memory:).")
        return QdrantClient(location=":memory:")

    # Local disk persistence mode (fallback for local development without cloud cluster)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    storage_dir = os.path.join(project_root, "qdrant_data")
    try:
        print(f"[Qdrant] Remote QDRANT_URL not configured or using placeholders. Using local storage at '{storage_dir}'.")
        return QdrantClient(path=storage_dir)
    except Exception as exc:
        print(f"[Qdrant Warning] Could not lock local storage ({exc}). Falling back to in-memory mode (:memory:).")
        return QdrantClient(location=":memory:")


# Initialize Qdrant Client
client = _init_qdrant_client()

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
