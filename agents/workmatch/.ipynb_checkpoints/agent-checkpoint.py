""" Root agent for Workmatch application """

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from . import prompt
from .sub_agents.profile_create import profile_create_agent

MODEL = "gemini-2.0-flash" 

workmatch_coordinator = Agent(
    name = "workmatch_coordinator",
    model=MODEL,
    description="Friendly assistant for generating professional bios and contact blocks",
    instruction=prompt.WORKMATCH_ROOT_PROMPT,
    tools=[
        AgentTool(agent=profile_create_agent),
    ],
)

root_agent = workmatch_coordinator