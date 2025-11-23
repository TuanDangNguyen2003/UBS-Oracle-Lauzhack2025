"use client";

import { useState } from "react";

type Message = {
  role: "user" | "assistant";
  content: string;
};

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = async () => {
  const trimmed = input.trim();
  if (!trimmed || loading) return;

  // 👉 Clear chat if user typed "clear"
  if (trimmed.toLowerCase() === "clear") {
    setMessages([]);
    setInput("");
    return;
  }

  const newMessages = [...messages, { role: "user", content: trimmed }];
      setMessages(newMessages);
      setInput("");
      setLoading(true);
      setError(null);
    
      try {
        const res = await fetch("/api/ai-chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt: trimmed,
            history: newMessages,
          }),
        });
    
        const data = await res.json();
    
        if (!res.ok || data.error) {
          throw new Error(data.error || `Request failed with ${res.status}`);
        }
    
        const reply: string = data.reply ?? "";
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: reply },
        ]);
      } catch (err: any) {
        setError(err?.message ?? "Unknown error");
      } finally {
        setLoading(false);
      }
    };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

    return (
      <div className="min-h-screen bg-black text-white flex justify-center items-start py-12 px-4">
        <div className="w-full max-w-2xl flex flex-col gap-6">
    
          {/* Title & description */}
          <header className="text-center">
            <h1 className="text-4xl font-bold tracking-tight mb-2">Revealer</h1>
            <p className="text-zinc-400 text-sm">
              Check anyone, Check anything  
            </p>
          </header>
    
          {/* Chat container */}
          <div className="flex flex-col bg-zinc-900 border border-zinc-800 rounded-xl shadow-xl h-[500px] overflow-y-auto p-6 gap-4">
    
            {messages.length === 0 && (
              <p className="text-zinc-500 text-center text-sm mt-20">
                Your conversation will appear here.
              </p>
            )}
    
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`
                    max-w-[75%] px-4 py-3 rounded-2xl text-sm
                    ${msg.role === "user"
                      ? "bg-white text-black rounded-br-sm"
                      : "bg-zinc-800 text-white border border-zinc-700 rounded-bl-sm"
                    }
                  `}
                >
                  {msg.content}
                </div>
              </div>
            ))}
    
          </div>
    
          {/* Error message */}
          {error && (
            <div className="text-red-400 text-sm text-center">
              Error: {error}
            </div>
          )}
    
          {/* Input area */}
          <div className="flex gap-3 items-center">
            <input
              className="flex-1 rounded-xl border border-zinc-700 bg-zinc-950 px-4 py-3 text-sm text-white focus:border-white outline-none"
              placeholder="Type your message…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !loading && sendMessage()}
            />
            
            <button
              onClick={sendMessage}
              disabled={loading}
              className="px-5 py-3 text-sm font-semibold bg-white text-black rounded-xl shadow hover:bg-zinc-200 active:scale-95 transition disabled:opacity-50"
            >
              {loading ? "…" : "Send"}
            </button>
          </div>
    
        </div>
      </div>
    );
}
