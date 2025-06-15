import logging
import datetime
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import FunctionTool
from .tracing import langfuse_span

logger = logging.getLogger(__name__)


class TracedAgentTool(AgentTool):
    """
    Thread-safe AgentTool wrapper:
    - Langfuse span tracing
    - ADK Web-compatible tool naming
    - Clean console logging
    """
    def __init__(self, agent, name: str = None, description: str = None):
        super().__init__(agent=agent)
        self.name = name or getattr(agent, "name", "unnamed_tool_agent")
        self.description = description or getattr(agent, "description", f"Tool for agent '{self.name}'")

    async def __call__(self, tool_input):
        tool_name = self.name
        timestamp = datetime.datetime.utcnow().isoformat()
        input_payload = getattr(tool_input, "input", tool_input)

        logger.info(f"[tool:call] {timestamp} | {tool_name} | Input: {input_payload}")

        span_input = {"raw_input": str(input_payload)}
        if isinstance(input_payload, dict):
            span_input = input_payload
        elif isinstance(input_payload, str):
            span_input = {"text": input_payload}

        with langfuse_span(f"tool_call.{tool_name}", input_data=span_input) as span:
            try:
                output = await super().__call__(tool_input)
                logger.info(f"[tool:output] {timestamp} | {tool_name} | Output: {getattr(output, 'output', output)}")

                if span and output is not None:
                    span.set_attribute("output", str(getattr(output, "output", output))[:1024])
                return output
            except Exception as e:
                logger.error(f"[tool:error] {timestamp} | {tool_name} | {e}")
                if span:
                    span.set_attribute("error", str(e))
                    span.set_attribute("status", "error")
                raise


class TracedFunctionTool(FunctionTool):
    """
    Thread-safe FunctionTool wrapper:
    - Langfuse tracing
    - ADK tool name support
    - Clear logging
    """
    def __init__(self, func, name: str = None, description: str = None):
        super().__init__(func=func)
        self.name = name or getattr(func, '__name__', 'unnamed_function_tool')
        self.description = description or getattr(func, '__doc__', '') or f"Traced tool for {self.name}"

    def run(self, input_data, *args, **kwargs):
        tool_name = self.name
        timestamp = datetime.datetime.utcnow().isoformat()
        logger.info(f"[function_tool:call] {timestamp} | {tool_name} | Input: {input_data}")

        span_input = {"raw_input": str(input_data)}
        if isinstance(input_data, dict):
            span_input = input_data
        elif isinstance(input_data, str):
            span_input = {"text": input_data}

        with langfuse_span(f"tool_call.{tool_name}", input_data=span_input) as span:
            try:
                output = super().run(input_data, *args, **kwargs)
                logger.info(f"[function_tool:output] {timestamp} | {tool_name} | Output: {output}")
                if span and output is not None:
                    span.set_attribute("output", str(output)[:1024])
                return output
            except Exception as e:
                logger.error(f"[function_tool:error] {timestamp} | {tool_name} | {e}")
                if span:
                    span.set_attribute("error", str(e))
                    span.set_attribute("status", "error")
                raise
