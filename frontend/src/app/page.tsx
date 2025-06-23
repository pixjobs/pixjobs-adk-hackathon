"use client";

import React, { useState, useRef, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import { cn } from "@/lib/utils";
import { v4 as uuidv4 } from "uuid";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

const normalizeSpaces = (text: string) => {
  return text
    .split("\n")
    .map(line => line.replace(/\s+/g, " ").trim())
    .join("\n")
    .trim();
};

const ChatPage: React.FC = () => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortController = useRef<AbortController | null>(null);

  useEffect(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
    focusInput();
  }, [messages]);

  const focusInput = () => inputRef.current?.focus();

  useEffect(() => {
    focusInput();
  }, []);

  const hasFiredIntro = useRef(false);
  useEffect(() => {
    if (hasFiredIntro.current || messages.length > 0) return;
    hasFiredIntro.current = true;

    const fireIntro = async () => {
      await new Promise(res => setTimeout(res, 400));
      await sendMessage("hi");
    };

    fireIntro();
  }, [messages]);

  const sendMessage = async (text: string) => {
    const controller = new AbortController();
    abortController.current = controller;
    setIsLoading(true);

    const assistantId = uuidv4();
    setMessages(prev => [
      ...prev,
      { id: assistantId, role: "assistant", content: "" },
    ]);

    const maxRetries = 5;
    let attempt = 0;

    while (attempt < maxRetries) {
      try {
        const res = await fetch("/api/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            newMessageContent: { parts: [{ type: "text", text }] },
          }),
          signal: controller.signal,
        });

        const contentType = res.headers.get("Content-Type") || "";
        if (!res.ok || !res.body || !contentType.includes("text/event-stream")) {
          const errorText = await res.text();
          throw new Error(`SSE failed (status ${res.status}): ${errorText}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split(/\r?\n/);
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data:")) continue;
            const json = line.slice("data:".length).trim();
            if (!json || json === "[DONE]") continue;

            try {
              const parsed = JSON.parse(json);
              const delta = parsed?.choices?.[0]?.delta?.content ?? "";

              if (delta) {
                setMessages(prev =>
                  prev.map(msg =>
                    msg.id === assistantId
                      ? { ...msg, content: msg.content + delta }
                      : msg
                  )
                );
              }
            } catch (err) {
              console.error("SSE parse error:", json, err);
            }
          }
        }

        setIsLoading(false);
        focusInput();
        return;
      } catch (err) {
        console.error(`Retry ${attempt + 1} failed:`, err);
        attempt++;
        await new Promise(res => setTimeout(res, 500 * attempt));
      }
    }

    setIsLoading(false);
    focusInput();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: ChatMessage = {
      id: uuidv4(),
      role: "user",
      content: input.trim(),
    };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    await sendMessage(userMessage.content);
  };

  return (
    <div className="flex flex-col h-dvh w-full max-w-screen-md mx-auto bg-background text-text border border-border shadow-sm">
      <div
        ref={messagesRef}
        className="flex-grow p-4 overflow-y-auto space-y-3 custom-scrollbar"
        aria-live="polite"
      >
        {messages
          .filter(msg => msg.role !== "assistant" || msg.content.trim() !== "")
          .map(msg => (
            <div key={msg.id} className={cn("flex", msg.role === "assistant" ? "justify-start" : "justify-end")}>
              <div
                className={cn(
                  "px-4 py-2 rounded-2xl max-w-[85%] whitespace-pre-wrap break-words text-sm leading-snug shadow-sm border",
                  msg.role === "assistant"
                    ? "bg-[color:var(--bubble-assistant)] text-[color:var(--text-primary)] border-border"
                    : "bg-[color:var(--bubble-user)] text-white border-transparent"
                )}
              >
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeSanitize]}
                  className="max-w-none space-y-1"
                  // you can still define `components={renderers}` here
                >
                  {normalizeSpaces(msg.content)}
                </ReactMarkdown>
              </div>
            </div>
          ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="px-4 py-3 rounded-2xl bg-[color:var(--bubble-assistant)] text-[color:var(--text-primary)] border border-border shadow-sm text-sm leading-relaxed animate-pulse">
              WorkMatch is typing...
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex items-center p-4 border-t border-border bg-background gap-2">
        <Input
          placeholder="Type your message…"
          value={input}
          onChange={e => setInput(e.target.value)}
          disabled={isLoading}
          ref={inputRef}
          className="flex-grow rounded-full px-4 py-2 text-sm bg-transparent text-text border border-border"
          autoComplete="off"
        />
        <Button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="rounded-full px-4 py-2 text-sm bg-primary text-white"
        >
          Send
        </Button>
      </form>
    </div>
  );
};

export default ChatPage;
