"use client";

import { useState, useRef } from "react";
import { UploadCloud, FileText, CheckCircle, AlertCircle, Loader2, X } from "lucide-react";

interface FileUploadProps {
  apiUrl: string;
  onUploadSuccess?: (chunksCount: number) => void;
}

export default function FileUpload({ apiUrl, onUploadSuccess }: FileUploadProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{
    type: "success" | "error" | null;
    message: string;
    chunksCount?: number;
  }>({ type: null, message: "" });

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files).filter((file) => {
        const ext = file.name.split(".").pop()?.toLowerCase();
        return ext === "pdf" || ext === "txt";
      });
      setSelectedFiles(newFiles);
      setUploadStatus({ type: null, message: "" });
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    setUploadStatus({ type: null, message: "" });

    const formData = new FormData();
    selectedFiles.forEach((file) => {
      formData.append("files", file);
    });

    try {
      const res = await fetch(`${apiUrl}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Upload failed with HTTP ${res.status}`);
      }

      const data = await res.json();
      setUploadStatus({
        type: "success",
        message: `Successfully indexed ${data.chunks_indexed} text chunk(s) into Qdrant Cloud.`,
        chunksCount: data.chunks_indexed,
      });
      setSelectedFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = "";
      if (onUploadSuccess) onUploadSuccess(data.chunks_indexed);
    } catch (err: any) {
      setUploadStatus({
        type: "error",
        message: err.message || "Failed to upload and index files.",
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <FileText className="w-5 h-5 text-indigo-600" />
        <h2 className="font-semibold text-slate-800 text-sm">Document Ingestion</h2>
      </div>

      <div
        onClick={() => fileInputRef.current?.click()}
        className="border-2 border-dashed border-slate-200 hover:border-indigo-400 rounded-lg p-5 text-center cursor-pointer transition bg-slate-50 hover:bg-indigo-50/30"
      >
        <UploadCloud className="w-8 h-8 text-indigo-500 mx-auto mb-2" />
        <p className="text-xs font-medium text-slate-700">
          Click or drop PDF / TXT files here
        </p>
        <p className="text-[11px] text-slate-400 mt-1">
          Supports single or multiple PDF and TXT documents
        </p>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt"
          multiple
          onChange={handleFileChange}
          className="hidden"
        />
      </div>

      {selectedFiles.length > 0 && (
        <div className="mt-3 space-y-1.5 max-h-36 overflow-y-auto">
          {selectedFiles.map((file, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between text-xs bg-slate-100/80 px-2.5 py-1.5 rounded-md text-slate-700"
            >
              <span className="truncate max-w-[200px]" title={file.name}>
                {file.name}
              </span>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-slate-400">
                  {(file.size / 1024).toFixed(1)} KB
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(idx);
                  }}
                  className="text-slate-400 hover:text-rose-500"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}

          <button
            onClick={handleUpload}
            disabled={isUploading}
            className="w-full mt-2 py-2 px-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white font-medium text-xs rounded-lg transition flex items-center justify-center gap-1.5 shadow-sm"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Chunking & Indexing...</span>
              </>
            ) : (
              <>
                <UploadCloud className="w-3.5 h-3.5" />
                <span>Upload to Qdrant Cloud ({selectedFiles.length})</span>
              </>
            )}
          </button>
        </div>
      )}

      {uploadStatus.type === "success" && (
        <div className="mt-3 p-2.5 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-start gap-2">
          <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
          <span>{uploadStatus.message}</span>
        </div>
      )}

      {uploadStatus.type === "error" && (
        <div className="mt-3 p-2.5 rounded-md bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <span>{uploadStatus.message}</span>
        </div>
      )}
    </div>
  );
}
