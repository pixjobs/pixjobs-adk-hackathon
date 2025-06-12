import logging
from google.adk.tools.agent_tool import AgentTool
from .tracing import langfuse_span

logger = logging.getLogger(__name__)

class TracedAgentTool(AgentTool):
    def __init__(self, agent, name: str = None, description: str = None):
        super().__init__(agent=agent) # Call super with only 'agent'

        # Set self.name and self.description after super().__init__
        # Prioritize explicitly passed 'name' or 'description'
        effective_name = name or getattr(agent, 'name', 'unknown_tool_agent')
        effective_description = description or getattr(agent, 'description', f"Tool for agent {effective_name}")

        # Manually set them if the base class doesn't, or to ensure our values are used.
        # Some AgentTool versions might make these read-only after init.
        # This attempts to set them; if they are properties with setters, it works.
        # If they are direct attributes, it also works.
        try:
            self.name = effective_name
        except AttributeError: # In case self.name is a read-only property without a setter
            logger.warning(f"[trace] Could not set name for TracedAgentTool instance for agent {getattr(agent, 'name', 'unknown_agent')}. Using default if set by base class.")
            if not hasattr(self, 'name') or not self.name : # if base class didn't set it
                 # This is a fallback, but self.name might not be assignable here if it's a strict property
                 # For span naming, we'll use effective_name directly in run() if self.name is problematic.
                 pass


        try:
            self.description = effective_description
        except AttributeError:
            logger.warning(f"[trace] Could not set description for TracedAgentTool instance.")
            pass
        
        # Store the effective name for reliable use in run(), in case self.name is not settable
        self._trace_tool_name = effective_name


    def run(self, input_data, *args, **kwargs):
        # Use self._trace_tool_name for reliable span naming
        span_name = f"tool_call.{self._trace_tool_name}"

        span_input_dict = {"raw_input_str": str(input_data)}
        if isinstance(input_data, dict):
            span_input_dict = input_data
        elif isinstance(input_data, str):
            span_input_dict = {"text_input": input_data}
        
        with langfuse_span(span_name, input_data=span_input_dict) as span:
            logger.info(f"[trace] Running tool {self._trace_tool_name} with input: {input_data}")
            try:
                result = super().run(input_data, *args, **kwargs)
                if span and result is not None:
                    try:
                        span.set_attribute("output.result_str", str(result)[:1024])
                    except Exception:
                        pass
                return result
            except Exception as e:
                logger.error(f"[trace] Error in tool {self._trace_tool_name}: {e}")
                raise