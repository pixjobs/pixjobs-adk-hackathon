from google.adk.agents import Agent
from .prompt import CAREER_GUIDANCE_PROMPT
from .tools import (
    explore_career_fields_function,
    get_job_role_descriptions_function,
    suggest_next_level_roles_function,
    get_skill_suggestions_function,
    ingest_jobs_from_adzuna,
)
from utils.env import get_model

MODEL_INSTANCE = get_model()

career_guidance_agent = Agent(
    name="career_guidance_agent",
    model=MODEL_INSTANCE,
    description="A smart career coach that can explore job fields, find job descriptions, and suggest career advancements using real-time job data.",
    instruction=CAREER_GUIDANCE_PROMPT,
    tools=[
        explore_career_fields_function,
        get_job_role_descriptions_function,
        suggest_next_level_roles_function,
        get_skill_suggestions_function,
        ingest_jobs_from_adzuna,
    ]
)
