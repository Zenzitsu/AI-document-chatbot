import os
from typing import Any, Dict, List
from openai import OpenAI

from app.config import settings
from app.vector_store import (
    COLLECTION_NAME,
    client as qdrant_client,
    embedding_model,
)

from dotenv import dotenv_values, load_dotenv

# Initialize OpenAI client configured for Gemini (or standard OpenAI)
def get_llm_client() -> OpenAI:
    """Configures the OpenAI client with Gemini or OpenAI credentials, reading .env fresh."""
    load_dotenv(override=True)
    env_vals = dotenv_values(".env")

    api_key = (
        env_vals.get("GEMINI_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or settings.GEMINI_API_KEY
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    ).strip()

    base_url = (
        env_vals.get("GEMINI_BASE_URL")
        or os.getenv("GEMINI_BASE_URL")
        or settings.GEMINI_BASE_URL
        or "https://generativelanguage.googleapis.com/v1beta/openai/"
    ).strip()

    # Ensure trailing slash for proper OpenAI URL resolution
    if not base_url.endswith("/"):
        base_url += "/"

    # If only OPENAI_API_KEY is provided and not Gemini, use default OpenAI base_url
    if not (api_key.startswith("AIza") or "generativelanguage.googleapis.com" in base_url):
        if os.getenv("OPENAI_API_KEY"):
            base_url = None

    return OpenAI(
        api_key=api_key or "missing-key",
        base_url=base_url,
    )


def search_context(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Searches the Qdrant Cloud collection 'docs_rag' using FastEmbed vectors
    and returns the top matching snippets.
    
    Args:
        query: User question or search query string.
        top_k: Number of relevant snippets to retrieve (default: 3).
        
    Returns:
        List of dictionaries containing text, metadata, and similarity score.
    """
    if not query.strip():
        return []

    # Embed query using FastEmbed
    query_vector_gen = embedding_model.embed([query])
    query_vector = next(query_vector_gen)
    vector_list = (
        query_vector.tolist()
        if hasattr(query_vector, "tolist")
        else list(query_vector)
    )

    try:
        # Search Qdrant collection using query_points (qdrant-client >= 1.10) with fallback
        if hasattr(qdrant_client, "query_points"):
            response = qdrant_client.query_points(
                collection_name=COLLECTION_NAME,
                query=vector_list,
                limit=top_k,
            )
            search_results = response.points
        else:
            search_results = qdrant_client.search(
                collection_name=COLLECTION_NAME,
                query_vector=vector_list,
                limit=top_k,
            )
    except Exception as e:
        print(f"[RAG] Qdrant search error: {e}")
        return []

    snippets: List[Dict[str, Any]] = []
    for hit in search_results:
        payload = hit.payload or {}
        snippets.append({
            "text": payload.get("text", ""),
            "filename": payload.get("filename", "unknown"),
            "page_number": payload.get("page_number", 1),
            "score": round(hit.score, 4) if hit.score is not None else 0.0,
        })

    return snippets


def generate_answer(query: str, top_k: int = 3) -> Dict[str, Any]:
    """
    Takes retrieved snippets and generates an answer using Gemini / OpenAI LLM.
    Strictly follows context and cites document name and page number.
    
    Args:
        query: The user's input question.
        top_k: Number of context chunks to retrieve (default: 3).
        
    Returns:
        dict: {'answer': str, 'sources': list}
    """
    snippets = search_context(query=query, top_k=top_k)

    if not snippets:
        return {
            "answer": "I do not know.",
            "sources": [],
        }

    # Format retrieved context snippets with document citation metadata
    context_blocks: List[str] = []
    sources: List[Dict[str, Any]] = []

    for idx, s in enumerate(snippets, start=1):
        filename = s.get("filename", "unknown")
        page_number = s.get("page_number", "N/A")
        text = s.get("text", "").strip()

        context_blocks.append(
            f"[Source {idx}] Document: {filename} | Page: {page_number}\nContent:\n{text}"
        )
        sources.append({
            "filename": filename,
            "page_number": page_number,
            "score": s.get("score"),
            "snippet": text[:150] + "..." if len(text) > 150 else text,
        })

    context_str = "\n\n---\n\n".join(context_blocks)

    system_instruction = (
        "Answer strictly using this context. Cite document name and page number. "
        "If not found, say I do not know."
    )

    prompt = (
        f"Context:\n{context_str}\n\n"
        f"Question: {query}\n\n"
        f"Answer:"
    )

    llm_client = get_llm_client()
    env_vals = dotenv_values(".env")
    configured_model = (
        env_vals.get("GEMINI_MODEL")
        or os.getenv("GEMINI_MODEL")
        or settings.GEMINI_MODEL
        or "gemini-1.5-flash"
    ).strip()

    # Handle display names like "Gemini 2.5 Flash Lite"
    primary_model = configured_model
    if " " in primary_model:
        if "lite" in primary_model.lower():
            primary_model = "gemini-2.5-flash-lite"
        elif "2.5" in primary_model or "flash" in primary_model.lower():
            primary_model = "gemini-2.5-flash"
        elif "pro" in primary_model.lower():
            primary_model = "gemini-2.5-pro"
        else:
            primary_model = "gemini-2.5-flash"

    # Candidates list in priority order based on active Google API models
    candidate_models = [primary_model]
    for fallback in ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-flash-latest", "gemini-2.5-pro"]:
        if fallback not in candidate_models:
            candidate_models.append(fallback)

    answer = None
    last_error = None

    for m in candidate_models:
        try:
            response = llm_client.chat.completions.create(
                model=m,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )
            raw_answer = response.choices[0].message.content or "I do not know."
            answer = raw_answer.strip()
            break
        except Exception as e:
            last_error = e
            print(f"[RAG LLM Error] Tried model '{m}': {e}")
            # If it's a 404 (model not found), try next model in candidate_models
            if "404" in str(e):
                continue
            # For other errors (like auth or rate limit), don't loop endlessly
            break

    if answer is None:
        err_msg = str(last_error)
        if hasattr(last_error, "response") and last_error.response is not None:
            try:
                err_msg = last_error.response.text
            except Exception:
                pass
        answer = f"Error generating answer with Gemini: {err_msg}"

    return {
        "answer": answer,
        "sources": sources,
    }
