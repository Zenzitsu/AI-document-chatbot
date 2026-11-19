from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.ingestion import process_file
from app.rag import generate_answer
from app.vector_store import add_documents, client as qdrant_client, init_collection


# ---------------------------------------------------------------------------
# Swagger / OpenAPI Tags Metadata
# ---------------------------------------------------------------------------
tags_metadata = [
    {
        "name": "Health",
        "description": "Health checks and connectivity diagnostics for Qdrant Cloud.",
    },
    {
        "name": "Ingestion",
        "description": (
            "Document ingestion endpoints to upload, parse (PDF and TXT), "
            "split into 500-char chunks (with 50-char overlap), embed using FastEmbed, "
            "and store into Qdrant Cloud with metadata."
        ),
    },
    {
        "name": "RAG",
        "description": (
            "Retrieval-Augmented Generation endpoints to perform semantic search "
            "on Qdrant Cloud and generate context-grounded answers with LLM citations."
        ),
    },
]


# ---------------------------------------------------------------------------
# Application Lifespan (Startup / Shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Verifies and initializes the Qdrant Cloud collection on application startup."""
    try:
        init_collection()
        print("[Startup] Qdrant collection verified/initialized.")
    except Exception as e:
        print(f"[Startup Warning] Could not initialize Qdrant collection: {e}")
    yield


# ---------------------------------------------------------------------------
# FastAPI Initialization
# ---------------------------------------------------------------------------
app = FastAPI(
    title="FastAPI Qdrant RAG Service",
    description=(
        "Production-ready RAG application powered by FastAPI, Qdrant Cloud, "
        "FastEmbed (BAAI/bge-small-en-v1.5), and Google Gemini."
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS Middleware Configuration
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows requests from any origin; customize for production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
    expose_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        description="The user query or question for the RAG pipeline",
        example="What are the key points mentioned in the document?",
        min_length=1,
    )


class SourceSnippet(BaseModel):
    filename: str = Field(..., description="Source document filename")
    page_number: int = Field(..., description="Document page number")
    score: Optional[float] = Field(None, description="Cosine similarity score")
    snippet: Optional[str] = Field(None, description="Preview snippet of the chunk")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="Grounded answer synthesized by the LLM")
    sources: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of cited source chunks with metadata",
    )


class UploadResponse(BaseModel):
    status: str = Field(..., example="success")
    chunks_indexed: int = Field(..., example=12, description="Total number of chunks uploaded to Qdrant")


class HealthResponse(BaseModel):
    status: str = Field(..., example="connected")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check & Qdrant Cloud ping",
    description="Pings Qdrant Cloud cluster by requesting collections to verify network connectivity and valid credentials.",
    responses={
        200: {"description": "Qdrant Cloud is reachable and authenticated."},
        503: {"description": "Qdrant Cloud is unreachable or credentials are invalid."},
    },
)
def health_check():
    """
    Checks if FastAPI can ping Qdrant Cloud.
    Returns { 'status': 'connected' } if successful.
    """
    try:
        qdrant_client.get_collections()
        return {"status": "connected"}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to connect to Qdrant Cloud: {str(exc)}",
        )


@app.post(
    "/upload",
    response_model=UploadResponse,
    tags=["Ingestion"],
    summary="Upload & index PDF/TXT documents",
    description=(
        "Accepts single or multiple PDF or TXT files. Reads raw bytes, splits into "
        "500-character chunks with 50-character overlap (attaching page number and filename), "
        "computes FastEmbed vectors, and upserts points into Qdrant Cloud."
    ),
    responses={
        200: {"description": "Files processed and indexed successfully."},
        400: {"description": "No files provided in request."},
        422: {"description": "File parsing error."},
        500: {"description": "Error indexing into Qdrant Cloud."},
    },
)
async def upload_files(
    files: Optional[List[UploadFile]] = File(None, description="One or more PDF/TXT files to upload"),
    file: Optional[UploadFile] = File(None, description="Single PDF/TXT file parameter alternative"),
):
    """
    Accepts single or multiple PDF/TXT files via UploadFile, parses them with ingestion.py,
    and stores them into Qdrant Cloud with vector_store.py.
    """
    uploaded_files: List[UploadFile] = []
    if files:
        uploaded_files.extend(files)
    if file:
        uploaded_files.append(file)

    if not uploaded_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided. Please upload at least one PDF or TXT file using the 'files' or 'file' form field.",
        )

    all_chunks: List[Dict[str, Any]] = []

    for uploaded_file in uploaded_files:
        filename = uploaded_file.filename or "uploaded_document.txt"
        file_bytes = await uploaded_file.read()

        if not file_bytes:
            continue

        try:
            chunks = process_file(file_bytes=file_bytes, filename=filename)
            all_chunks.extend(chunks)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to process file '{filename}': {str(exc)}",
            )

    if not all_chunks:
        return {"status": "success", "chunks_indexed": 0}

    try:
        add_documents(all_chunks)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index documents into Qdrant Cloud: {str(exc)}",
        )

    return {
        "status": "success",
        "chunks_indexed": len(all_chunks),
    }


@app.post(
    "/chat",
    response_model=ChatResponse,
    tags=["RAG"],
    summary="Query the RAG pipeline",
    description=(
        "Retrieves relevant context snippets from Qdrant Cloud using FastEmbed "
        "similarity search, then prompts Gemini to generate a factual response "
        "with document and page number citations."
    ),
    responses={
        200: {"description": "Answer generated successfully with source citations."},
        400: {"description": "Empty question string."},
        500: {"description": "Error during retrieval or LLM generation."},
    },
)
def chat(request: ChatRequest):
    """
    Accepts { 'question': 'string' } and returns { 'answer': 'string', 'sources': [...] }
    using rag.py.
    """
    if not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question string cannot be empty.",
        )

    try:
        response = generate_answer(query=request.question)
        return response
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing question: {str(exc)}",
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
