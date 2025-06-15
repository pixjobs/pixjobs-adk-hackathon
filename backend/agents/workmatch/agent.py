import logging
from google.adk.agents import LlmAgent
from workmatch.utils.env import load_env, get_model
from workmatch.utils.traced_tools import TracedAgentTool, TracedFunctionTool
from workmatch.utils.tracing import langfuse_span, get_langfuse, init_tracer

from .tools import (
    get_job_role_descriptions_function,
    ingest_jobs_from_adzuna,
)
from .sub_agents import (
    entry_level_agent,
    advanced_pathways_agent,
)
from .prompt import CAREER_GUIDANCE_PROMPT, TITLE_VARIANTS_PROMPT

# Setup
logger = logging.getLogger(__name__)
load_env()

langfuse_sdk = get_langfuse()
otel_tracer_instance = init_tracer(service_name="workmatch-coordinator-agent")
MODEL = get_model()

# Internal agent for job title variant expansion
title_variants_agent = LlmAgent(
    name="title_variants_agent",
    model=MODEL,
    description="Generates keyword-optimised and skill-based variants for job titles.",
    instruction=TITLE_VARIANTS_PROMPT,
    tools=[],
)

# Traced root agent definition
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
        TracedFunctionTool(func=get_job_role_descriptions_function),
        TracedFunctionTool(func=ingest_jobs_from_adzuna),
        TracedAgentTool(agent=title_variants_agent),
    ],
)

# Attach internal sub-agents
root_agent.sub_agents = [
    entry_level_agent,
    advanced_pathways_agent,
]

# Export root agent for use in app
agent = root_agent
