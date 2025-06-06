from google.adk.agents import Agent
from utils.env import get_model # Assuming utils is in your PYTHONPATH or at root
from .prompt import CAREER_GUIDANCE_PROMPT

MODEL_INSTANCE = get_model()

career_guidance_agent = Agent(
    name="career_guidance_agent",
    model=MODEL_INSTANCE,
    description="A guide to help users explore passions, skills, and values for career clarity through reflective conversation.",
    instruction=CAREER_GUIDANCE_PROMPT,
    tools=[], # Its tool is its conversational ability for now
)