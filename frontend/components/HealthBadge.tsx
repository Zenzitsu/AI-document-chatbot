"use client";

import { useEffect, useState } from "react";
import { Activity, CheckCircle2, RefreshCw, XCircle } from "lucide-react";

interface HealthBadgeProps {
  apiUrl: string;
}

export default function HealthBadge({ apiUrl }: HealthBadgeProps) {
  const [status, setStatus] = useState<"checking" | "connected" | "disconnected">("checking");
  const [lastChecked, setLastChecked] = useState<string>("");

  const checkHealth = async () => {
    setStatus("checking");
    try {
      const res = await fetch(`${apiUrl}/health`, { method: "GET" });
      if (res.ok) {
        const data = await res.json();
        if (data.status === "connected") {
          setStatus("connected");
        } else {
          setStatus("disconnected");
        }
      } else {
        setStatus("disconnected");
      }
    } catch {
      setStatus("disconnected");
    } finally {
      setLastChecked(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, [apiUrl]);

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-medium bg-white shadow-sm border-slate-200">
      <div className="flex items-center gap-1.5">
        {status === "checking" && (
          <>
            <Activity className="w-3.5 h-3.5 text-amber-500 animate-spin" />
            <span className="text-amber-700">Checking Qdrant...</span>
          </>
        )}
        {status === "connected" && (
          <>
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 ml-0.5" />
            <span className="text-emerald-700 font-semibold">Qdrant Cloud Connected</span>
          </>
        )}
        {status === "disconnected" && (
          <>
            <XCircle className="w-3.5 h-3.5 text-rose-500" />
            <span className="text-rose-700 font-semibold">Qdrant Offline</span>
          </>
        )}
      </div>

      <button
        onClick={checkHealth}
        title={`Click to recheck (Last check: ${lastChecked})`}
        className="ml-1 text-slate-400 hover:text-slate-600 transition"
      >
        <RefreshCw className="w-3 h-3" />
      </button>
    </div>
  );
}
