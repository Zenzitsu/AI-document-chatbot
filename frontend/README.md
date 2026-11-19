# Next.js RAG Frontend

A modern Next.js + Tailwind CSS interface integrated with the FastAPI Qdrant & Gemini RAG backend.

## Features
- **Document Ingestion**: Upload single or multiple PDF and TXT files directly to `POST /upload`.
- **Real-Time Health Status**: Automatically checks and pings Qdrant Cloud via `GET /health`.
- **RAG Chatbot**: Queries `POST /chat` and displays answers with expandable source citations (file name, page number, match score, and snippet).

## Getting Started

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Environment Variables
Make sure `.env.local` points to your running FastAPI backend:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Run Development Server
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.
