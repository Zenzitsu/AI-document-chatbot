import io
from typing import Any, Dict, List, Union
import pypdf


def split_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
    """
    Splits text into chunks of `chunk_size` characters with `chunk_overlap` characters overlap.
    
    Args:
        text: Input string to be split.
        chunk_size: Maximum characters per chunk (default: 500).
        chunk_overlap: Number of characters to overlap between adjacent chunks (default: 50).
        
    Returns:
        List of text chunks.
    """
    if not text:
        return []

    text = text.strip()
    if len(text) <= chunk_size:
        return [text]

    chunks: List[str] = []
    step = max(1, chunk_size - chunk_overlap)
    text_length = len(text)
    start = 0

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        if chunk:
            chunks.append(chunk)
        start += step

    return chunks


def read_txt(
    file_bytes: bytes,
    filename: str = "document.txt",
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> List[Dict[str, Any]]:
    """
    Reads plain text bytes, splits into chunks, and attaches metadata.
    
    Args:
        file_bytes: Raw bytes of the TXT file.
        filename: Name of the file for metadata tracking.
        chunk_size: Chunk character limit (default: 500).
        chunk_overlap: Overlap character limit (default: 50).
        
    Returns:
        List of chunk dictionaries with text and metadata.
    """
    text = file_bytes.decode("utf-8", errors="replace")
    text_chunks = split_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    chunks: List[Dict[str, Any]] = []
    for chunk in text_chunks:
        chunks.append({
            "text": chunk,
            "filename": filename,
            "page_number": 1,
            "metadata": {
                "filename": filename,
                "page_number": 1,
            },
        })

    return chunks


def read_pdf(
    file_bytes: bytes,
    filename: str = "document.pdf",
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> List[Dict[str, Any]]:
    """
    Reads PDF bytes using pypdf, splits text per page into chunks, and attaches metadata.
    
    Args:
        file_bytes: Raw bytes of the PDF file.
        filename: Name of the file for metadata tracking.
        chunk_size: Chunk character limit (default: 500).
        chunk_overlap: Overlap character limit (default: 50).
        
    Returns:
        List of chunk dictionaries with text and metadata (including page number).
    """
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    chunks: List[Dict[str, Any]] = []

    for page_idx, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        page_text = page_text.strip()
        if not page_text:
            continue

        text_chunks = split_text(page_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        for chunk in text_chunks:
            chunks.append({
                "text": chunk,
                "filename": filename,
                "page_number": page_idx,
                "metadata": {
                    "filename": filename,
                    "page_number": page_idx,
                },
            })

    return chunks


def process_file(
    file_bytes: bytes,
    filename: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> List[Dict[str, Any]]:
    """
    Inspects filename extension (PDF or TXT), parses content, and splits into chunks with metadata.
    
    Args:
        file_bytes: Raw bytes of the uploaded file.
        filename: Name of the file (e.g. sample.pdf or notes.txt).
        chunk_size: Chunk size in characters (default: 500).
        chunk_overlap: Overlap size in characters (default: 50).
        
    Returns:
        List of chunk dictionaries with text and metadata.
    """
    lower_filename = filename.lower()
    if lower_filename.endswith(".pdf"):
        return read_pdf(file_bytes, filename=filename, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    else:
        # Default to treating as plain text
        return read_txt(file_bytes, filename=filename, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
