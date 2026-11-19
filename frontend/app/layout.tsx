import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Qdrant & Gemini RAG Assistant",
  description: "Next.js frontend for Qdrant Cloud RAG application with Gemini LLM",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased bg-slate-50 text-slate-900 min-h-screen">
        {children}
      </body>
    </html>
  );
}
