import ast
import logging
from typing import List, Dict, Any, Optional

from google.adk.agents import LlmAgent
from workmatch.utils.env import get_model
from workmatch.utils.traced_tools import TracedAgentTool, TracedFunctionTool

from .tools import (
    get_job_role_descriptions_function,
    ingest_jobs_from_adzuna,
)
from .sub_agents import (
    entry_level_agent,
    advanced_pathways_agent,
)
from .prompt import CAREER_GUIDANCE_PROMPT, TITLE_VARIANTS_PROMPT

# Sub-agent to generate job title variants
title_variants_agent = LlmAgent(
    name="title_variants_agent",
    model=get_model(),
    description="Generates keyword-optimised and skill-based variants for job titles.",
    instruction=TITLE_VARIANTS_PROMPT,
    tools=[]
)

# Main career guidance agent with traced tools
career_guidance_agent = LlmAgent(
    name="career_guidance_agent",
    model=get_model(),
    description="A smart career coach that can explore job fields, find job descriptions, and suggest career advancements using real-time job data.",
    instruction=CAREER_GUIDANCE_PROMPT,
    tools=[
        TracedFunctionTool(func=get_job_role_descriptions_function),
        TracedFunctionTool(func=ingest_jobs_from_adzuna),
        TracedAgentTool(agent=title_variants_agent),
    ],
)

career_guidance_agent.sub_agents = [
    entry_level_agent,
    advanced_pathways_agent,
]
