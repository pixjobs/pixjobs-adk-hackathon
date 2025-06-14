# WorkMatch

**WorkMatch** is a multi-agent career guidance assistant built for the [Agent Development Kit Hackathon with Google Cloud](https://devpost.com/software/adk-hackathon). It demonstrates how intelligent agents can collaborate to provide structured, personalised job coaching using real-time listings and skill logic — without generating fiction or fluff.

This project is built with the open-source [Agent Development Kit (ADK)](https://github.com/google/agent-development-kit) and deployed on Google Cloud infrastructure.

---

## 🔍 Summary

WorkMatch helps users explore careers, identify opportunities, and plan next steps using a proactive agent-led approach. Instead of content generation or customer service, the system focuses on **automating complex human-centred processes**, such as:

- Finding jobs based on interests or goals
- Recommending accessible or growth-aligned career paths
- Suggesting beginner skills and certifications
- Delivering empathetic, action-oriented guidance for early or advancing professionals

At its core, WorkMatch is a **career coach that thinks in structured flows**, powered by dynamic agent orchestration and tool-assisted decision-making.

---

## 🧠 Agent Orchestration

The architecture centres around a `career_guidance_agent`, which delegates work to a suite of purpose-built sub-agents and function tools depending on user goals.

| Agent | Role |
|-------|------|
| `career_guidance_agent` | Main orchestrator: routes based on user intent (beginner, advanced, goal-seeking) |
| `entry_level_agent` | Synthesises beginner guidance, coordinating starter roles, skills, job descriptions, and motivation |
| `advanced_pathways_agent` | Delivers promotion/pivot plans, calling multiple sub-agents to produce structured blueprints |
| `title_variants_agent` | Expands job title queries with synonyms and adjacent labels |
| `starter_titles_agent` | Suggests beginner-friendly job titles from vague inputs |
| `job_overview_agent` | Explains day-to-day tasks in plain terms |
| `beginner_skills_agent` | Recommends technical and soft skills for entry-level users |
| `entry_motivation_agent` | Adds emotional encouragement and resilience tips |
| `next_level_roles_agent` | Suggests step-up titles from a given job |
| `skill_suggestions_agent` | Recommends upskilling targets for progression |
| `leadership_agent` | Evaluates readiness and actions for leadership |
| `lateral_pivot_agent` | Suggests adjacent roles for career transitions |
| `certification_agent` | Recommends career-boosting certifications |

This modular design supports contextual, zero-friction interactions — each user message is interpreted and routed by the primary agent to assemble a meaningful, grounded response.

---

## ⚙️ Technologies Used

- **Agent Development Kit (Python)**
- **Gemini 2.5 Pro Preview 06-05** (Set via the Secret Manager)
- **Gemini 2.0 Flash** as fallback
- **Google Cloud Run** for backend orchestration
- **Google Secret Manager** for secure API key handling
- **Pinecone** for job title embedding and vector-based discovery
- **React + TypeScript frontend** for chat UI

Agents are wrapped with custom `TracedAgentTool` and `TracedFunctionTool` classes for logging, tool visibility in ADK Web, and **Langfuse**-powered tracing.

---

## 🧭 Hackathon Focus

WorkMatch fits into the **Automation of Complex Processes** category.

It automates the nuanced, multi-step process of career navigation by:
- Synthesising information from real job listings
- Mapping user intent to practical suggestions
- Dynamically invoking agents for exploration, upskilling, and guidance

This is not a content generator — it is a reasoning-led coaching tool that **reduces search friction and decision fatigue** through tool-enhanced workflows and ADK-powered autonomy.

---

## ✨ Learnings

WorkMatch showcases how multi-agent systems can:

- Drive adaptive, high-context conversations without scripted flows
- Automate advisory tasks that require emotional intelligence and structure
- Support orchestration that mimics human coaches — but with speed, clarity, and grounded logic

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
WorkMatch currently runs through the ADK Web interface in the /backend folder.

If you're looking to test or extend the agent workflows locally, please refer to /backend/README.md for full setup and run instructions — including:

How to launch ADK Web

Required Google Cloud Secret Manager setup

Vertex AI + Pinecone integration details

This structure allows future packaging of the backend into a deployable service while keeping development flows modular and manageable.



