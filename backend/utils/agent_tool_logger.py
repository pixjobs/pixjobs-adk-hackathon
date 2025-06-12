import datetime
from google.adk.tools.agent_tool import AgentTool
from google.adk.agents import LlmAgent


class LoggingAgentTool(AgentTool):
    def __init__(self, agent: LlmAgent):
        super().__init__(agent=agent)

    async def __call__(self, tool_input):
        timestamp = datetime.datetime.utcnow().isoformat()
        print(f"[EVENT TRACE] {timestamp} | Tool: {self.name} | Input: {tool_input.input}")

        try:
            output = await super().__call__(tool_input)
            print(f"[EVENT TRACE] {timestamp} | Tool: {self.name} | Output: {output.output}")
            return output
        except Exception as e:
            print(f"[ERROR] {timestamp} | Tool: {self.name} | Exception: {str(e)}")
            raise
