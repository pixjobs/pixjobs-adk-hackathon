import ast
import logging
from typing import List, Dict, Any, Optional

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool

from .tools import (
    get_job_role_descriptions_function,
    ingest_jobs_from_adzuna,
)
from .sub_agents import (
    entry_level_agent,
    advanced_pathways_agent,
)
from .prompt import CAREER_GUIDANCE_PROMPT, TITLE_VARIANTS_PROMPT
from utils.env import get_model

title_variants_agent = LlmAgent(
    name="title_variants_agent",
    model=get_model(),
    description="Generates keyword-optimised and skill-based variants for job titles.",
    instruction=TITLE_VARIANTS_PROMPT,
    tools=[]
)

career_guidance_agent = LlmAgent(
    name="career_guidance_agent",
    model=get_model(),
    description="A smart career coach that can explore job fields, find job descriptions, and suggest career advancements using real-time job data.",
    instruction=CAREER_GUIDANCE_PROMPT,
    tools=[
        FunctionTool(func=get_job_role_descriptions_function),
        FunctionTool(func=ingest_jobs_from_adzuna),
        AgentTool(agent=title_variants_agent),
    ],
)

career_guidance_agent.sub_agents = [
    entry_level_agent,
    advanced_pathways_agent,
]
