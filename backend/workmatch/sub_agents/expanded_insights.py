from google.adk.agents import LlmAgent
from workmatch.utils.env import get_model
from ..tools.career_tools import summarise_expanded_job_roles_tool

from ..prompt import EXPANDED_ROLE_INSIGHTS_PROMPT_WITH_LISTINGS

expanded_insights_agent = LlmAgent(
    name="expanded_insights_agent",
    model=get_model(),
    description="Test",
    instruction=EXPANDED_ROLE_INSIGHTS_PROMPT_WITH_LISTINGS,
    tools=[summarise_expanded_job_roles_tool]
)