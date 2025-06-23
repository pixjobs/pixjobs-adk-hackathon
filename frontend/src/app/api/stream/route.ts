// ⚠️ This config is for the Hackathon demo only

import { NextRequest, NextResponse } from "next/server";
import { GoogleAuth } from "google-auth-library";
import { v4 as uuidv4 } from "uuid";

const BASE_URL = "https://workmatch-api-718117052413.europe-west2.run.app";
const APP_NAME = "workmatch";

function headersToRecord(headers: HeadersInit): Record<string, string> {
  const result: Record<string, string> = {};
  for (const [key, value] of Object.entries(headers)) {
    result[key] = value;
  }
  return result;
}

async function createSession(
  userId: string,
  sessionId: string,
  headers: Record<string, string>
) {
  try {
    const res = await fetch(
      `${BASE_URL}/apps/${APP_NAME}/users/${userId}/sessions/${sessionId}`,
      {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ state: { frontend: true } }),
      }
    );

    if (res.status === 400) {
      const err = await res.text();
      if (!err.includes("Session already exists")) {
        throw new Error(`[Session] create failed: ${res.status} ${err}`);
      }
      return;
    }

    if (!res.ok && res.status !== 409) {
      const err = await res.text();
      throw new Error(`[Session] create failed: ${res.status} ${err}`);
    }

    await res.text(); // drain
  } catch (e) {
    console.error("[Proxy] Failed to create session:", e);
    throw e;
  }
}

type IncomingPayload = {
  newMessage?: { role: "user"; parts: { text: string }[] };
  newMessageContent?: { parts: { type: string; text: string }[] };
  userId?: string;
  sessionId?: string;
  [key: string]: any;
};

export async function POST(req: NextRequest) {
  try {
    const cookieUserId = req.cookies.get("userId")?.value;
    const cookieSessionId = req.cookies.get("sessionId")?.value;

    const payload = (await req.json()) as IncomingPayload;

    let parts: { text: string }[];
    if (payload.newMessage?.parts) {
      parts = payload.newMessage.parts.map((p) => ({ text: p.text }));
    } else if (payload.newMessageContent?.parts) {
      parts = payload.newMessageContent.parts.map((p) => ({ text: p.text }));
    } else {
      return NextResponse.json(
        { error: 'Invalid message format; expecting parts with "text"' },
        { status: 400 }
      );
    }

    const userId =
      cookieUserId || payload.userId || `frontend-${uuidv4().slice(0, 8)}`;
    const sessionId =
      cookieSessionId || payload.sessionId || `s_${uuidv4().slice(0, 12)}`;
    const isNewSession = !cookieSessionId || cookieSessionId !== sessionId;

    const auth = new GoogleAuth();
    const client = await auth.getIdTokenClient(BASE_URL);
    const headers = await client.getRequestHeaders();
    const headersRecord = headersToRecord(headers);

    await createSession(userId, sessionId, headersRecord);

    const proxyPayload = {
      appName: APP_NAME,
      userId,
      sessionId,
      newMessage: {
        role: "user",
        parts,
      },
    };

    const backendRes = await fetch(`${BASE_URL}/run_sse`, {
      method: "POST",
      headers: { ...headersRecord, "Content-Type": "application/json" },
      body: JSON.stringify(proxyPayload),
    });

    if (!backendRes.ok || !backendRes.body) {
      const err = await backendRes.text();
      return NextResponse.json({ error: err }, { status: backendRes.status });
    }

    const decoder = new TextDecoder();
    const encoder = new TextEncoder();

    const wrappedStream = new ReadableStream({
      async start(controller) {
        const reader = backendRes.body!.getReader();
        let buffer = "";

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunkStr = decoder.decode(value, { stream: true });
            buffer += chunkStr;

            const lines = buffer.split(/\r?\n/);
            buffer = lines.pop() ?? "";

            for (const line of lines) {
              const trimmed = line.trim();
              if (!trimmed.startsWith("data:")) continue;

              const jsonPart = trimmed.slice("data:".length).trim();
              if (jsonPart === "[DONE]") {
                controller.enqueue(encoder.encode("data: [DONE]\n\n"));
                controller.close();
                return;
              }

              try {
                if (!jsonPart.startsWith("{")) continue;

                const parsed = JSON.parse(jsonPart);
                const text = parsed?.content?.parts?.[0]?.text ?? "";

                if (text) {
                  const deltaChunk = {
                    id: uuidv4(),
                    object: "chat.completion.chunk",
                    choices: [
                      {
                        delta: { content: text },
                        index: 0,
                        finish_reason: null,
                      },
                    ],
                  };
                  controller.enqueue(
                    encoder.encode(`data: ${JSON.stringify(deltaChunk)}\n\n`)
                  );
                }
              } catch (err) {
                // Silently skip malformed chunks
              }
            }
          }

          if (buffer.trim()) {
            // Optional: handle or report trailing garbage
          }

          controller.enqueue(encoder.encode("data: [DONE]\n\n"));
          controller.close();
        } catch (e) {
          console.error("[Proxy] Streaming error:", e);
          controller.error(e);
        }
      },
    });

    const res = new NextResponse(wrappedStream, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });

    if (isNewSession) {
      res.cookies.set("userId", userId, { path: "/", httpOnly: true });
      res.cookies.set("sessionId", sessionId, { path: "/", httpOnly: true });
    }

    return res;
  } catch (err: any) {
    console.error("[Proxy] Fatal error:", err);
    return NextResponse.json(
      { error: err.message || "Internal error" },
      { status: 500 }
    );
  }
}
