from google.adk.agents import LlmAgent
from utils.env import get_model
from utils.agent_tool_logger import LoggingAgentTool

from ..prompt import (
    ADVANCED_PATHWAYS_PROMPT,
    NEXT_LEVEL_ROLES_PROMPT,
    SKILL_SUGGESTIONS_PROMPT,
    LEADERSHIP_PROMPT,
    LATERAL_PIVOT_PROMPT,
    CERTIFICATION_PROMPT,
    JOB_TITLE_EXPANSION_PROMPT,
)
from ..tools.career_tools import (
    get_job_role_descriptions_function,
    explore_career_fields_function,
)

# Sub-agent to suggest related job titles for fallback or exploration
job_title_expansion_agent = LlmAgent(
    name="job_title_expansion_agent",
    model=get_model(),
    description="Suggests related or alternative job titles based on user input (e.g. if no results found).",
    instruction=JOB_TITLE_EXPANSION_PROMPT,
    tools=[]
)

# Sub-agent to suggest next-level roles
next_level_roles_agent = LlmAgent(
    name="next_level_roles_agent",
    model=get_model(),
    description="Suggests career advancement titles based on the user's current role.",
    instruction=NEXT_LEVEL_ROLES_PROMPT,
    tools=[]
)

# Sub-agent to suggest skill improvements for a target role
skill_suggestions_agent = LlmAgent(
    name="skill_suggestions_agent",
    model=get_model(),
    description="Provides technical and soft skills for excelling in a target job role.",
    instruction=SKILL_SUGGESTIONS_PROMPT,
    tools=[]
)

# Sub-agent to advise on leadership preparation
leadership_agent = LlmAgent(
    name="leadership_agent",
    model=get_model(),
    description="Evaluates leadership readiness and outlines preparation steps for management or executive roles.",
    instruction=LEADERSHIP_PROMPT,
    tools=[]
)

# Sub-agent to recommend lateral career pivot options
lateral_pivot_agent = LlmAgent(
    name="lateral_pivot_agent",
    model=get_model(),
    description="Advises on lateral career pivots to related domains with strong growth opportunities.",
    instruction=LATERAL_PIVOT_PROMPT,
    tools=[]
)

# Sub-agent to recommend certifications for advancement
certification_agent = LlmAgent(
    name="certification_agent",
    model=get_model(),
    description="Suggests certifications or credentials to support job promotions and upskilling.",
    instruction=CERTIFICATION_PROMPT,
    tools=[]
)

# Main advanced pathways agent with event-logged tools
advanced_pathways_agent = LlmAgent(
    name="advanced_pathways_agent",
    model=get_model(),
    description="Guides users in career advancement, promotions, and future planning.",
    instruction=ADVANCED_PATHWAYS_PROMPT,
    tools=[
        LoggingAgentTool(agent=next_level_roles_agent),
        LoggingAgentTool(agent=skill_suggestions_agent),
        LoggingAgentTool(agent=leadership_agent),
        LoggingAgentTool(agent=lateral_pivot_agent),
        LoggingAgentTool(agent=certification_agent),
        get_job_role_descriptions_function,
        explore_career_fields_function,
    ]
)
