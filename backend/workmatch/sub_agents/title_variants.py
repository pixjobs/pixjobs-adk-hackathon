from google.adk.agents import LlmAgent
from workmatch.utils.env import get_model
from ..prompt import TITLE_VARIANTS_PROMPT

title_variants_agent = LlmAgent(
    name="title_variants_agent",
    model=get_model(),
    description="Generates keyword-optimised and skill-based variants for job titles.",
    instruction=TITLE_VARIANTS_PROMPT,
    tools=[],
)