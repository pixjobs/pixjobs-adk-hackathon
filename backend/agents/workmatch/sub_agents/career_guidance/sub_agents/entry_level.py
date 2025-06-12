from google.adk.agents import LlmAgent
from utils.env import get_model
from utils.agent_tool_logger import LoggingAgentTool

from ..prompt import (
    ENTRY_LEVEL_PROMPT,
    STARTER_TITLES_PROMPT,
    BEGINNER_SKILLS_PROMPT,
    JOB_OVERVIEW_PROMPT,
    ENTRY_MOTIVATION_PROMPT,
)
from ..tools.career_tools import (
    get_job_role_descriptions_function,
    explore_career_fields_function,
)

# Sub-agent to recommend beginner-friendly job titles
starter_titles_agent = LlmAgent(
    name="starter_titles_agent",
    model=get_model(),
    description="Recommends beginner-friendly job titles based on a user's interests or keywords.",
    instruction=STARTER_TITLES_PROMPT,
    tools=[]
)

# Sub-agent to suggest beginner-appropriate skills
beginner_skills_agent = LlmAgent(
    name="beginner_skills_agent",
    model=get_model(),
    description="Suggests technical and soft skills useful for entry-level roles.",
    instruction=BEGINNER_SKILLS_PROMPT,
    tools=[]
)

# Sub-agent to explain job responsibilities
job_overview_agent = LlmAgent(
    name="job_overview_agent",
    model=get_model(),
    description="Provides easy-to-understand explanations of job responsibilities for entry-level roles.",
    instruction=JOB_OVERVIEW_PROMPT,
    tools=[]
)

# Sub-agent to provide motivational support to early-career users
entry_motivation_agent = LlmAgent(
    name="entry_motivation_agent",
    model=get_model(),
    description="Offers encouragement and mindset advice for users starting their career journey.",
    instruction=ENTRY_MOTIVATION_PROMPT,
    tools=[]
)

# Main entry-level agent with event-logging tools
entry_level_agent = LlmAgent(
    name="entry_level_agent",
    model=get_model(),
    description="Helps users explore beginner-friendly job roles, required skills, and job content while staying motivated.",
    instruction=ENTRY_LEVEL_PROMPT,
    tools=[
        LoggingAgentTool(agent=starter_titles_agent),
        LoggingAgentTool(agent=beginner_skills_agent),
        LoggingAgentTool(agent=job_overview_agent),
        LoggingAgentTool(agent=entry_motivation_agent),
        get_job_role_descriptions_function,
        explore_career_fields_function,
    ]
)
