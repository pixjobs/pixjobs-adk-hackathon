from google.adk import Agent
from google.genai import types
from utils.env import load_env, get_model
from . import prompt

profile_create_agent = Agent(
    model=get_model(),
    name="profile_create_agent",
    instruction=prompt.PROFILE_CREATE_PROMPT,
    output_key="profile_create_output",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2, # More deterministic output
        max_output_tokens=1500, # Generate longer profile for more comprehensive content
    )
)