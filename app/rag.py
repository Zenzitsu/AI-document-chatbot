import os
from typing import Any, Dict, List
from openai import OpenAI

from app.config import settings
from app.vector_store import (
    COLLECTION_NAME,
    client as qdrant_client,
    embedding_model,
)

# Initialize OpenAI client configured for Gemini (or standard OpenAI)
def get_llm_client() -> OpenAI:
    """Configures the OpenAI client with Gemini or OpenAI credentials."""
    api_key = (
        settings.GEMINI_API_KEY
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    )
    base_url = settings.GEMINI_BASE_URL

    # If only OPENAI_API_KEY is provided and not Gemini, use default OpenAI base_url
    if not (settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
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
        # Search Qdrant Cloud collection
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
    model_name = settings.GEMINI_MODEL or "gemini-1.5-flash"

    try:
        response = llm_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        answer = response.choices[0].message.content or "I do not know."
        answer = answer.strip()
    except Exception as e:
        answer = f"Error generating answer: {e}"

    return {
        "answer": answer,
        "sources": sources,
    }


# ---------------------------------------------------------------------------
# Test Block: Run a test query against the RAG pipeline
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n--- Testing RAG Pipeline ---")
    test_question = "What is this application about?"
    print(f"Query: {test_question}")

    try:
        result = generate_answer(query=test_question)
        print("\n[Result]")
        print(f"Answer : {result['answer']}")
        print(f"Sources: {result['sources']}")
    except Exception as exc:
        print(f"\n[Test Error] {exc}")
        print("Ensure Qdrant Cloud and Gemini API credentials are set in .env.")
