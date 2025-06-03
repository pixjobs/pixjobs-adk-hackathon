
# WorkMatch

**WorkMatch** is a multi-agent job search assistant built for the [Agent Development Kit Hackathon with Google Cloud](https://devpost.com/software/adk-hackathon). It showcases how autonomous agents can collaborate to analyse a user's background, search job listings, and iteratively improve results.

This project is a functional prototype built using the open-source [Agent Development Kit (ADK)](https://github.com/google/agent-development-kit), and runs on Google Cloud.

---

## 🔍 Summary

WorkMatch helps users discover job opportunities by uploading a CV. The system:

1. Understands their background
2. Searches and ranks matching roles
3. Offers feedback to refine future recommendations

The system demonstrates agent collaboration through message passing and orchestration in ADK, aligned with the hackathon’s focus on **automating complex processes** and **intelligent data-driven assistance**.

---

## 🧠 Multi-Agent Design

| Agent | Task |
|-------|------|
| `ProfileAgent` | Extracts structured data from a CV: skills, experience, goals |
| `QueryAgent` | Forms a search strategy based on the user profile |
| `RankingAgent` | Evaluates job matches and ranks them |
| `FeedbackAgent` | Reviews CV quality, highlights improvement areas, and explains why jobs are or aren't a good match |

Agents collaborate using ADK’s runtime environment, exchanging context and results to complete the job-matching process through structured interaction and orchestration.


## ⚙️ Technologies Used

- **Agent Development Kit (Python)**
- **Gemini API** for CV summarisation and job scoring
- **Google Cloud Run** for deployment
- **Secret Manager** for credentials and API keys
- **Optional**: **Pinecone** for scalable vector search
- **Frontend**: React + TypeScript

---

## 🚀 How to Run

```bash
git clone https://github.com/pixjobs/pixjobs-adk-hackathon.git
cd pixjobs-adk-hackathon
npm install
npm run dev
```

Ensure secrets are configured in Google Secret Manager, and the ADK environment is active.

---



## ✨ Learnings

Building WorkMatch showed the practical power of autonomous agents. By structuring the workflow around cooperative agent roles, we were able to:

- Separate concerns and logic cleanly
- Enable reusability of agent designs
- Leverage ADK’s tools and message routing for real collaboration
- Integrate Google Cloud services for deployment and scaling

This project could be extended in future with real-time job data, user authentication, and more complex agent negotiation workflows.

---

## 📝 License

This project is licensed under the [Apache 2.0 License](./LICENSE).

---

## 💬 Contact

Built for the **Agent Development Kit Hackathon with Google Cloud**.  
Project creator: Yang Pei — contact via GitHub only

Follow the project hashtag: `#adkhackathon`

---

## 🤖 Use of AI in Development

This project was accelerated using AI tools for tasks such as code generation, text summarisation, architecture drafting, and documentation support. However, all core concepts, agent design, use case refinement, and project direction were developed and curated by the PixJobs team.

---
