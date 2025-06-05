from google.adk import Agent
from . import prompt

MODEL = "gemini-2.0-flash"

profile_create_agent = Agent(
    model=MODEL,
    name="profile_create_agent",
    instruction=prompt.PROFILE_CREATE_PROMPT,
    output_key="profile_create_output",
)