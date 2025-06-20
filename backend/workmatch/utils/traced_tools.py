import logging
from datetime import datetime
from google.adk.tools.agent_tool import AgentTool
from .tracing import langfuse_span

logger = logging.getLogger(__name__)


def _now_iso():
    return datetime.utcnow().isoformat(timespec="seconds")


def _prepare_span_input(data):
    if isinstance(data, dict):
        return data
    if isinstance(data, str):
        return {"text": data}
    return {"raw_input": str(data)}


class TracedAgentTool(AgentTool):
    """
    Langfuse-traced AgentTool with clean naming, logging, and streaming support.
    """
    def __init__(self, agent, name: str = None, description: str = None):
        super().__init__(agent=agent)
        self.name = name or getattr(agent, "name", "unnamed_tool_agent")
        self.description = description or getattr(agent, "description", f"Tool for agent '{self.name}'")

    async def __call__(self, tool_input):
        tool_name = self.name
        timestamp = _now_iso()
        input_payload = getattr(tool_input, "input", tool_input)

        logger.debug(f"[tool:call] {timestamp} | {tool_name} | Input: {input_payload}")

        with langfuse_span(f"tool_call.{tool_name}", input_data=_prepare_span_input(input_payload)) as span:
            try:
                output = await super().__call__(tool_input)
                result_str = getattr(output, "output", output)

                logger.debug(f"[tool:output] {timestamp} | {tool_name} | Output: {result_str}")
                if span and result_str is not None:
                    span.set_attribute("output", str(result_str)[:2048])  # Allow longer trace
                return output
            except Exception as e:
                logger.error(f"[tool:error] {timestamp} | {tool_name} | {e}")
                if span:
                    span.set_attribute("error", str(e))
                    span.set_attribute("status", "error")
                raise
