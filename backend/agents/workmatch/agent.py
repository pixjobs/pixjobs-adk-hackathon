"""
Root agent for Workmatch application.

Workmatch is a comprehensive jobsearch, motivation and career planning tool.
We recognise that finding a job is painful and rejection is rife, 
hence we want to make the process fun and engaging, easy and not overpowering.
"""

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from . import prompt # Contains WORKMATCH_ROOT_PROMPT
from .sub_agents.profile_create import profile_create_agent
from .sub_agents.contact_block_create import contact_block_create_agent
from .sub_agents.career_guidance import career_guidance_agent
from utils.env import load_env, get_model

load_env()

MODEL = get_model()

workmatch_coordinator = Agent(
    name="workmatch_coordinator",
    model=MODEL,

    description="Your Workmatch assistant for helping you with your career journey. Let's make this part of your job search easy and engaging!",
    instruction=prompt.WORKMATCH_ROOT_PROMPT, 
    tools=[
        AgentTool(agent=profile_create_agent),
        AgentTool(agent=contact_block_create_agent),
        AgentTool(agent=career_guidance_agent),
    ],
)

root_agent = workmatch_coordinator