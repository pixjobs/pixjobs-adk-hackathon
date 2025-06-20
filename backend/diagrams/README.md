🧭 Architecture Diagram
This repo includes a hand-written Mermaid diagram that visualises the architecture of the WorkMatch system.

📐 Generate the Diagram (SVG or PNG)
To convert the Mermaid file to an image for use in your documentation:

Install Mermaid CLI (if not already installed):

bash
Copy
Edit
npm install -g @mermaid-js/mermaid-cli
Generate the SVG diagram:

bash
Copy
Edit
mmdc -i workmatch_architecture.mmd -o workmatch_architecture.svg
(Optional) Generate a PNG instead:

bash
Copy
Edit
mmdc -i workmatch_architecture.mmd -o workmatch_architecture.png
📁 File Info
Diagram source: workmatch_architecture.mmd

Output format: SVG (workmatch_architecture.svg) or PNG

Visual coverage:

User Interface → HTTP Endpoint → Cloud Run → Root Agent

Core agents (EntryLevel, AdvancedPathways, etc.)

Shared tools and utilities

External systems (Adzuna API, Langfuse, etc.)

Feel free to update the .mmd file as the architecture evolves.

