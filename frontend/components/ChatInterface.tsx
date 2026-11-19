"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, BookOpen, ChevronDown, ChevronRight, Sparkles, Trash2, Loader2 } from "lucide-react";

interface Source {
  filename: string;
  page_number: number | string;
  score?: number;
  snippet?: string;
}

interface Message {
  id: string;
  sender: "user" | "assistant";
  content: string;
  sources?: Source[];
  timestamp: string;
}

interface ChatInterfaceProps {
  apiUrl: string;
}

export default function ChatInterface({ apiUrl }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      sender: "assistant",
      content: "Hello! I am your Qdrant & Gemini RAG assistant. Upload documents and ask me any questions based on your ingested content.",
      timestamp: "Just now",
    },
  ]);
  const [inputQuery, setInputQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [openSources, setOpenSources] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const toggleSource = (msgId: string) => {
    setOpenSources((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const handleSend = async (questionText?: string) => {
    const query = (questionText || inputQuery).trim();
    if (!query || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      sender: "user",
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputQuery("");
    setIsLoading(true);

    try {
      const res = await fetch(`${apiUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: query }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server responded with ${res.status}`);
      }

      const data = await res.json();

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: "assistant",
        content: data.answer || "I do not know.",
        sources: data.sources || [],
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: "assistant",
        content: `Error: ${err.message || "Failed to retrieve answer from server."}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: "welcome",
        sender: "assistant",
        content: "Chat cleared. Ask me any question about your indexed documents.",
        timestamp: "Just now",
      },
    ]);
  };

  const quickQuestions = [
    "Summarize the main points of the document",
    "What key findings or conclusions are mentioned?",
    "List the major sections discussed",
  ];

  return (
    <div className="flex flex-col h-[650px] bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Top Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-200 bg-slate-50/70">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-indigo-600" />
          <span className="font-semibold text-sm text-slate-800">Qdrant RAG Chat</span>
          <span className="text-[11px] bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full font-medium border border-indigo-100">
            Gemini 1.5 Flash
          </span>
        </div>

        {messages.length > 1 && (
          <button
            onClick={clearChat}
            className="text-xs text-slate-400 hover:text-slate-600 flex items-center gap-1 transition"
            title="Clear Chat History"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear</span>
          </button>
        )}
      </div>

      {/* Message List */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.sender === "assistant" && (
              <div className="w-7 h-7 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 mt-0.5 shadow-sm">
                <Bot className="w-4 h-4" />
              </div>
            )}

            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                msg.sender === "user"
                  ? "bg-indigo-600 text-white rounded-br-none"
                  : "bg-slate-100/90 text-slate-800 border border-slate-200/80 rounded-bl-none"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>

              {/* Source Citations */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 pt-2.5 border-t border-slate-200/60 text-xs">
                  <button
                    onClick={() => toggleSource(msg.id)}
                    className="flex items-center gap-1.5 font-medium text-indigo-700 hover:text-indigo-900 transition"
                  >
                    <BookOpen className="w-3.5 h-3.5" />
                    <span>
                      {msg.sources.length} Cited Source{msg.sources.length > 1 ? "s" : ""}
                    </span>
                    {openSources[msg.id] ? (
                      <ChevronDown className="w-3.5 h-3.5" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5" />
                    )}
                  </button>

                  {openSources[msg.id] && (
                    <div className="mt-2 space-y-2">
                      {msg.sources.map((src, i) => (
                        <div
                          key={i}
                          className="bg-white/80 p-2.5 rounded-lg border border-slate-200 text-[11px] text-slate-700 space-y-1"
                        >
                          <div className="flex items-center justify-between font-medium text-slate-800">
                            <span className="truncate max-w-[240px]">
                              📄 {src.filename} (Page {src.page_number})
                            </span>
                            {src.score !== undefined && (
                              <span className="text-[10px] text-indigo-600 font-mono">
                                Match: {(src.score * 100).toFixed(1)}%
                              </span>
                            )}
                          </div>
                          {src.snippet && (
                            <p className="italic text-slate-500 line-clamp-2">
                              &ldquo;{src.snippet}&rdquo;
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <span
                className={`block text-[10px] mt-1.5 ${
                  msg.sender === "user" ? "text-indigo-200 text-right" : "text-slate-400"
                }`}
              >
                {msg.timestamp}
              </span>
            </div>

            {msg.sender === "user" && (
              <div className="w-7 h-7 rounded-full bg-slate-700 text-white flex items-center justify-center shrink-0 mt-0.5 shadow-sm">
                <User className="w-4 h-4" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3 justify-start">
            <div className="w-7 h-7 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-sm">
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-slate-100 rounded-2xl rounded-bl-none px-4 py-3 text-sm text-slate-500 border border-slate-200 flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
              <span>Searching Qdrant & synthesizing answer...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Starters */}
      {messages.length <= 2 && (
        <div className="px-5 py-2 bg-slate-50 border-t border-slate-100 flex flex-wrap gap-1.5">
          {quickQuestions.map((q, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(q)}
              className="text-[11px] bg-white border border-slate-200 hover:border-indigo-400 hover:text-indigo-600 text-slate-600 px-2.5 py-1 rounded-full transition flex items-center gap-1 shadow-2xs"
            >
              <Sparkles className="w-3 h-3 text-indigo-500" />
              <span>{q}</span>
            </button>
          ))}
        </div>
      )}

      {/* Query Input Box */}
      <div className="p-3.5 border-t border-slate-200 bg-white">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder="Ask a question about your documents..."
            disabled={isLoading}
            className="flex-1 bg-slate-50 border border-slate-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition"
          />
          <button
            type="submit"
            disabled={isLoading || !inputQuery.trim()}
            className="p-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 disabled:text-slate-400 text-white rounded-lg transition shadow-sm"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
