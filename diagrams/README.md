# 🧭 WorkMatch Visual Documentation

This repository includes [Mermaid](https://mermaid.js.org/) diagrams that visualise both the **architecture** and **workflow** of the WorkMatch AI career guidance system.

These diagrams are designed to support developer onboarding, prompt understanding, and system explainability for hackathons, demos, and ongoing iteration.

---

## 📐 Architecture Diagram

The architecture diagram outlines the high-level components of the WorkMatch system.

### How to Generate

1. Install Mermaid CLI (if not already installed)

   npm install -g @mermaid-js/mermaid-cli

2. Generate the SVG diagram

   mmdc -i workmatch_architecture.mmd -o workmatch_architecture.svg

3. (Optional) Generate a PNG instead

   mmdc -i workmatch_architecture.mmd -o workmatch_architecture.png

   You can also customise the theme and resolution, for example:

   mmdc -i workmatch_architecture.mmd -o workmatch_architecture.svg -t forest -w 1400

### File Info

- Source: `workmatch_architecture.mmd`
- Output: `workmatch_architecture.svg` or `workmatch_architecture.png`

### Visual Coverage

- User Interface → HTTP Endpoint → Cloud Run → Root Agent
- Root orchestration: `career_guidance_agent`
- Sub-agents: `entry_level_agent`, `advanced_pathways_agent`
- Shared tools: `title_variants_agent`, `expanded_insights_agent`, `get_motivational_quote`
- External APIs and services: Adzuna, Google Search, Langfuse (if integrated)

---

## 🔄 Workflow Diagram

The workflow diagram models the full agent-user interaction flow, based on the `CAREER_GUIDANCE_PROMPT` and related sub-agent prompt files.

### How to Generate

1. Install Mermaid CLI (if not already installed)

   npm install -g @mermaid-js/mermaid-cli

2. Generate the SVG diagram

   mmdc -i workmatch_workflow.mmd -o workmatch_workflow.svg

3. (Optional) Generate a PNG instead

   mmdc -i workmatch_workflow.mmd -o workmatch_workflow.png

### File Info

- Source: `workmatch_workflow.mmd`
- Output: `workmatch_workflow.svg` or `workmatch_workflow.png`

### Visual Coverage

- Main entry routing: menu options 1–8
- `entry_level_agent` flow: beginner roles, job overviews, skills, motivation
- `advanced_pathways_agent` flow: career ladders, leadership, certifications, pivots, networking
- Job search logic: title expansion → location inference → real-time listings
- Motivation quote branch
- Re-routing back to main menu at appropriate stages

---

## 🧰 Tools & Editing

- Use [Mermaid Live Editor](https://mermaid.live/edit) to quickly test or tweak `.mmd` files
- For local editing: VS Code with **Markdown Preview Mermaid Support** extension is recommended
- Re-generate the diagrams whenever `.mmd` content is updated

---

## 📝 Contribution Notes

If you update prompts, agent logic, or add new tools, please:

- Update the `.mmd` files accordingly
- Re-run the diagram generation steps
- Commit the updated `.svg` or `.png` outputs

This ensures WorkMatch remains easy to understand for contributors and collaborators.
