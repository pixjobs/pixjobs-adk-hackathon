// components/CustomChat.tsx
"use client";

import React, { useState, useRef, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import { cn } from "@/lib/utils";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

const CustomChat: React.FC = () => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesRef = useRef<HTMLDivElement>(null);
  const abortController = useRef<AbortController | null>(null);

  useEffect(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const newUserMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: input.trim(),
    };

    setMessages((prev) => [...prev, newUserMessage]);
    setInput("");
    setIsLoading(true);

    const newAssistantMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
    };
    setMessages((prev) => [...prev, newAssistantMessage]);

    const controller = new AbortController();
    abortController.current = controller;

    await fetchEventSource("/api/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ newMessageContent: { parts: [{ type: "text", text: newUserMessage.content }] } }),
      signal: controller.signal,
      onmessage(ev) {
        if (ev.data === "[DONE]") {
          setIsLoading(false);
          return;
        }
        try {
          const parsed = JSON.parse(ev.data);
          const delta = parsed.choices?.[0]?.delta?.content ?? "";
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1].content += delta;
            return updated;
          });
        } catch (err) {
          console.error("Failed to parse SSE message:", ev.data);
        }
      },
      onerror(err) {
        console.error("SSE stream error:", err);
        controller.abort();
        setIsLoading(false);
      },
    });
  };

  return (
    <div className="flex flex-col h-[78vh] w-full max-w-screen-lg mx-auto bg-white border shadow-sm">
      <div
        ref={messagesRef}
        className="flex-grow p-4 overflow-y-auto space-y-4 custom-scrollbar"
        aria-live="polite"
      >
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn("w-full flex", msg.role === "assistant" ? "justify-start" : "justify-end")}
          >
            <div
              className={cn(
                "px-4 py-3 rounded-lg max-w-full lg:max-w-[75%] prose prose-sm",
                msg.role === "assistant"
                  ? "bg-gray-100 text-gray-800"
                  : "bg-blue-600 text-white"
              )}
            >
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeSanitize]}
              >
                {msg.content}
              </ReactMarkdown>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="px-4 py-3 rounded-lg bg-gray-100 text-gray-500">
              WorkMatch is typing...
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex items-center p-4 border-t bg-white">
        <Input
          placeholder="Type here…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isLoading}
          className="flex-grow"
        />
        <Button type="submit" disabled={!input.trim() || isLoading} className="ml-2">
          Send
        </Button>
      </form>
    </div>
  );
};

export default CustomChat;