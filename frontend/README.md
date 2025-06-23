# WorkMatch AI Chatbot (Frontend)

🚀 **This is the frontend UI for the WorkMatch AI Career Coaching System**  
It connects to a streaming backend via Server-Sent Events (SSE) and provides a responsive, dark-mode-enabled chat interface optimised for live AI conversations.

---

## ✨ Features

- ✅ Real-time conversational streaming with incremental rendering  
- ✅ Auto-triggered welcome message on initial load  
- ✅ Safe Markdown rendering (with sanitisation) for rich formatting  
- ✅ Mobile-friendly and accessible with preserved focus  
- ✅ Typing indicator with animated feedback  
- ✅ Dark mode default for sleek, modern presentation  
- ✅ Unique message IDs for persistent chat updates  

---

## 🌐 Architecture Overview

This repository contains **only the frontend app**, built with:

- **Next.js 15** + **custom `server.js`** for SSR support on Cloud Run
- Serverless-compatible API routes, including `/api/stream`, to proxy backend SSE calls
- Designed to work with a separate **Google Cloud Run backend** for job and coaching logic

---

## 🚀 Deployment to Google Cloud Run

This frontend is fully compatible with [Google Cloud Run](https://cloud.google.com/run), providing fast, scalable deployment.

### Prerequisites

- Google Cloud CLI (`gcloud`) installed and authenticated
- Project ID (e.g. `workmatch-hackathon`)
- Cloud Run and Cloud Build APIs enabled

### Build & Deploy Steps

1. Submit build to Google Cloud Build:

    gcloud builds submit --tag gcr.io/workmatch-hackathon/workmatch-ui

2. Deploy to Cloud Run:

    gcloud run deploy workmatch-ui \
      --image gcr.io/workmatch-hackathon/workmatch-ui \
      --platform managed \
      --region europe-west1 \
      --allow-unauthenticated

✅ Once deployed, your app will be live at a `https://<cloud-run-url>` endpoint.

---

## 🧱 Tech Stack

- **React 18** + **Next.js 15**
- **TailwindCSS** + **DaisyUI**
- **SSE via @microsoft/fetch-event-source**
- **React Markdown**, **rehype-sanitize** for secure rendering
- **Custom `server.js`** to enable streaming routes like `/api/stream`

---

## 📁 Key Files

- `Dockerfile` – Multi-stage build (build + runtime) for Cloud Run
- `server.js` – Starts the app with Node’s HTTP server (port 8080)
- `app/api/stream/route.ts` – Secure proxy to backend streaming API

---

## 🧩 Related Components

- 🧠 **Backend**: Not included here – deployed separately to handle career logic and SSE streaming.
- 🧾 If needed, see the [backend repo](#) (insert link if applicable).

---

## 📜 License

Licensed under the **Apache License 2.0**
