from google.adk import Agent
from . import prompt

MODEL = "gemini-2.5-pro-preview-05-06"

contact_block__create_agent = Agent(
    model=MODEL,
    name="contact_block_agent",
    instruction=prompt.CONTACT_BLOCK_PROMPT,
    output_key="contact_block_output",
)