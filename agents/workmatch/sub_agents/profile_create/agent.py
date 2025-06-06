from google.adk import Agent
from google.genai import types

from . import prompt

MODEL = "gemini-2.5-pro-preview-05-06"

profile_create_agent = Agent(
    model=MODEL,
    name="profile_create_agent",
    instruction=prompt.PROFILE_CREATE_PROMPT,
    output_key="profile_create_output",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2, # More deterministic output
        max_output_tokens=2000, # Generate longer profile for more comprehensive content
    )
)