# WorkMatch

**WorkMatch** is a multi-agent career guidance assistant built for the [Agent Development Kit Hackathon with Google Cloud](https://devpost.com/software/adk-hackathon). It demonstrates how intelligent agents can collaborate to provide structured, personalised job coaching using real-time listings and skill logic.

This project is built with the open-source [Agent Development Kit (ADK)](https://github.com/google/agent-development-kit) and deployed on Google Cloud infrastructure.

The hosted demo using Cloud Run can be found at: https://workmatch-718117052413.europe-west2.run.app

---

## 🔍 Summary

WorkMatch helps users explore careers, identify opportunities, and plan next steps using a proactive agent-led approach. Instead of content generation or customer service, the system focuses on **automating complex human-centred processes**, such as:

* Finding jobs based on interests or goals
* Recommending accessible or growth-aligned career paths
* Suggesting beginner skills and certifications
* Delivering empathetic, action-oriented guidance for early or advancing professionals

At its core, WorkMatch is a **career coach that thinks in structured flows**, powered by dynamic agent orchestration and tool-assisted decision-making.

---

## 🧠 Agent Orchestration

WorkMatch is powered by a **multi-agent orchestration architecture**. At the top is a `workmatch_root_agent` — the primary orchestrator that interacts with users directly and routes conversations to the appropriate sub-agent.

| Agent                     | Role                                                                                                                  |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `workmatch_root_agent`    | The main interface agent. Collects user intent, determines career stage, and routes to appropriate agents             |
| `career_guidance_agent`   | A structured career support agent: handles mid-level exploration, job discovery, and listings logic                   |
| `entry_level_agent`       | Synthesises beginner-friendly advice by orchestrating starter roles, skill guidance, real listings, and encouragement |
| `advanced_pathways_agent` | Generates multi-part career progression plans with structured steps (e.g. promotions, pivots, upskilling)             |
| `title_variants_agent`    | Expands job title queries with keyword-optimised and adjacent alternatives                                            |
| `starter_titles_agent`    | Suggests accessible starter roles from vague inputs (e.g. “I like people” → HR Assistant, Retail Advisor)             |
| `job_overview_agent`      | Explains job roles in clear, plain English (no jargon) with a focus on day-to-day responsibilities                    |
| `beginner_skills_agent`   | Recommends starter skills (technical + soft) tailored to early-career goals                                           |
| `entry_motivation_agent`  | Provides research-backed motivational coaching for discouraged or overwhelmed users                                   |
| `next_level_roles_agent`  | Suggests realistic next-step titles from a given current role (e.g. "Marketing Executive" → "Marketing Manager")      |
| `skill_suggestions_agent` | Recommends high-impact upskilling opportunities for career growth                                                     |
| `leadership_agent`        | Assesses leadership readiness and outlines preparation strategies                                                     |
| `lateral_pivot_agent`     | Identifies adjacent career paths for lateral movement or sector pivots                                                |
| `certification_agent`     | Recommends certifications that unlock new opportunities or boost credibility                                          |

This modular design supports contextual, zero-friction interactions — each user message is interpreted and routed by the primary agent to assemble a meaningful, grounded response.

---

## ⚙️ Technologies Used

* **Agent Development Kit (Python)**
* **Gemini 2.5 Flash** (Set via the Secret Manager)
* **Google Cloud Run** for backend orchestration
* **Google Secret Manager** for secure API key handling
* **Langfuse** for observability and tool tracing
* **Firestore Database** for storing of job listings for future searching and summarisation. The original implementation also included support for Pinecone vector search. However, this was removed due to to performance issues.

### 📌 Note on Frontend

While the current project relies on the ADK-provided web interface for local testing and development, a custom **React + TypeScript frontend** is planned for future implementation.

This future UI would allow:

* Branded deployment of the WorkMatch interface
* Seamless user interaction beyond the dev/test environment
* Integration of richer session control, input guidance, and results visualisation

For now, the backend is fully operational and deployable using ADK Web and Cloud Run.

---

## 🗝 How It Meets Hackathon Requirements

**Category: Automation of Complex Processes**

WorkMatch automates the nuanced, multi-step process of career navigation by:

* Mapping vague goals or interests to structured job searches
* Dynamically routing between beginner and advanced flows using user-aware logic
* Using sub-agents and function tools to deliver targeted advice, not hallucinated answers
* Synthesising multiple reasoning paths (exploration, listings, upskilling, motivational framing)

It is not a content generator — it is a reasoning-led assistant built for **practical discovery, progression planning, and resilience-building**.

### Key Qualities:

* **Multi-agent orchestration:** Dozens of tools and agents collaborate via live, streaming logic.
* **Real-world grounding:** All recommendations are supported by live job data via Adzuna.
* **Emotionally intelligent:** Supports discouraged users with structured encouragement.
* **ADK best practices:** Uses `TracedAgentTool`, `TracedFunctionTool`, and Secret Manager setup for security and observability.
* **Deployable:** Runs in Cloud Run with an optional UI.

---

## ✨ Learnings

WorkMatch showcases how multi-agent systems can:

* Drive adaptive, high-context conversations without scripted flows
* Automate advisory tasks that require emotional intelligence and structure
* Support orchestration that mimics human coaches — but with speed, clarity, and grounded logic
* Allow the rapid development of AI systems to solve real use cases.

In the initial stages the program also included support for Pinecone RAG databases for job listings. However, this was subsequently removed due to performance issues.

It demonstrates that agents, when carefully scoped and orchestrated, can act as intelligent intermediaries between users and the complexity of real-world job data.

---

## 📝 License

This project is licensed under the [Apache 2.0 License](./LICENSE).

---

## 💬 Contact

Created by **Yang Pei** for the [Agent Development Kit Hackathon with Google Cloud](https://devpost.com/software/adk-hackathon).
Follow updates via `#adkhackathon`.

---

## 🤖 Use of AI in Development

This project was accelerated using LLMs for tasks such as architecture drafting, tooling scaffolds, and summarisation. However, all core logic, agent orchestration, prompts, and UX flow design were developed by the PixJobs team through iterative engineering and real user needs analysis.

---

## 🧪 Running the Project

WorkMatch can be deployed as a backend service to **Google Cloud Run**, providing a scalable and accessible way to interact with the agent system.

Alternatively, for local development, testing, and exploring agent workflows, you can run WorkMatch using the **ADK Web interface** from the `/backend` folder.

**For comprehensive instructions on both deployment to Google Cloud Run and running locally, please refer to the detailed guide in `/backend/README.md`.**

This guide covers:

* **Deploying to Google Cloud Run**
* How to launch ADK Web locally
* Required Google Cloud Secret Manager setup for environment variables
* Vertex AI and other integration details

This structure allows the backend to be packaged as a deployable service while keeping development flows modular and manageable.
