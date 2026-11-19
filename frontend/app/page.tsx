"use client";

import { useState } from "react";
import FileUpload from "@/components/FileUpload";
import ChatInterface from "@/components/ChatInterface";
import HealthBadge from "@/components/HealthBadge";
import { Database, Sparkles, Layers } from "lucide-react";

export default function Home() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const [totalIndexed, setTotalIndexed] = useState<number>(0);

  const handleUploadSuccess = (chunksCount: number) => {
    setTotalIndexed((prev) => prev + chunksCount);
  };

  return (
    <main className="max-w-6xl mx-auto px-4 py-8">
      {/* Top Navbar */}
      <header className="flex flex-col md:flex-row md:items-center justify-between pb-6 mb-6 border-b border-slate-200 gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-600 rounded-lg text-white shadow-sm">
              <Database className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              FastAPI RAG Assistant
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Qdrant Cloud Vector Store &bull; FastEmbed (bge-small-en-v1.5) &bull; Google Gemini
          </p>
        </div>

        <div className="flex items-center gap-3">
          <HealthBadge apiUrl={apiUrl} />
        </div>
      </header>

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: File Upload & Info */}
        <aside className="lg:col-span-4 space-y-5">
          <FileUpload apiUrl={apiUrl} onUploadSuccess={handleUploadSuccess} />

          {/* Quick Stats / Info Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm text-xs text-slate-600 space-y-3">
            <div className="flex items-center gap-2 font-semibold text-slate-800">
              <Layers className="w-4 h-4 text-indigo-600" />
              <span>Pipeline Architecture</span>
            </div>
            <ul className="space-y-1.5 text-[11px] list-disc list-inside text-slate-500">
              <li>Chunks text into 500-char pieces (50-char overlap)</li>
              <li>Generates 384-dimensional FastEmbed embeddings</li>
              <li>Queries Qdrant Cloud using Cosine similarity</li>
              <li>Strict Gemini prompting citing Document & Page</li>
            </ul>

            {totalIndexed > 0 && (
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-indigo-700 font-medium">
                <span>Indexed in this session:</span>
                <span className="bg-indigo-50 px-2 py-0.5 rounded-full font-mono text-[11px]">
                  {totalIndexed} chunks
                </span>
              </div>
            )}
          </div>
        </aside>

        {/* Right Column: Chat Interface */}
        <section className="lg:col-span-8">
          <ChatInterface apiUrl={apiUrl} />
        </section>
      </div>
    </main>
  );
}
