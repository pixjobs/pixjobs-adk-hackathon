import logging
from google.adk.agents import LlmAgent 
from workmatch.utils.env import load_env, get_model
from workmatch.utils.traced_tools import TracedAgentTool
from workmatch.utils.tracing import langfuse_span, get_langfuse, init_tracer

from .sub_agents import (
    entry_level_agent,
    advanced_pathways_agent,
    expanded_insights_agent, 
    title_variants_agent,   
)

from .tools.motivational_quotes_tool import get_motivational_quote

from .prompt import CAREER_GUIDANCE_PROMPT 

# Setup
logger = logging.getLogger(__name__)
load_env()

langfuse_sdk = get_langfuse()
otel_tracer_instance = init_tracer(service_name="workmatch-coordinator-agent")
MODEL = get_model()

class TracedWorkmatchAgent(LlmAgent):
    def run(self, input_data, *args, **kwargs):
        span_name = f"agent_run.{self.name}"
        span_input_dict = {"raw_input_str": str(input_data)}
        if isinstance(input_data, dict):
            span_input_dict = input_data
        elif isinstance(input_data, str):
            span_input_dict = {"text_input": input_data}

        with langfuse_span(span_name, input_data=span_input_dict) as span:
            logger.info(f"[trace] Running agent {self.name} with input: {input_data}")
            try:
                result = super().run(input_data, *args, **kwargs)
                if span and result is not None:
                    try:
                        span.set_attribute("output.result_str", str(result)[:2048])
                    except Exception:
                        pass
                return result
            except Exception as e:
                logger.error(f"[trace] Error in agent {self.name}: {e}")
                raise

# Instantiate the root Workmatch agent
root_agent = TracedWorkmatchAgent(
    name="workmatch_root_agent",
    model=MODEL,
    description="Workmatch: your smart, supportive career coach powered by real-time listings, sub-agent guidance, and structured exploration.",
    instruction=CAREER_GUIDANCE_PROMPT,
    tools=[
        TracedAgentTool(agent=title_variants_agent),     
        TracedAgentTool(agent=expanded_insights_agent), 
        TracedAgentTool(agent=entry_level_agent),
        TracedAgentTool(agent=advanced_pathways_agent),
        get_motivational_quote     
    ],
)

agent = root_agent