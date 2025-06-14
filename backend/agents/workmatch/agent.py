import logging
from google.adk.agents import Agent
from . import prompt
from .sub_agents.career_guidance import career_guidance_agent
from utils.env import load_env, get_model
from utils.tracing import init_tracer, get_langfuse, langfuse_span
from utils.traced_tools import TracedAgentTool

logger = logging.getLogger(__name__)

load_env()
otel_tracer_instance = init_tracer(service_name="workmatch-coordinator-agent")
langfuse_sdk = get_langfuse()
MODEL = get_model()

class TracedCoordinatorAgent(Agent):
    def run(self, input_data, *args, **kwargs):
        span_name = f"agent_run.{self.name}"
        span_input_dict = {"raw_input_str": str(input_data)}
        if isinstance(input_data, dict): span_input_dict = input_data
        elif isinstance(input_data, str): span_input_dict = {"text_input": input_data}

        with langfuse_span(span_name, input_data=span_input_dict) as span:
            logger.info(f"[trace] Running agent {self.name} with input: {input_data}")
            try:
                result = super().run(input_data, *args, **kwargs)
                if span and result is not None:
                    try: span.set_attribute("output.result_str", str(result)[:2048])
                    except Exception: pass
                return result
            except Exception as e:
                logger.error(f"[trace] Error in agent {self.name}: {e}")
                raise

def build_root_agent(use_traced_root_class: bool = True):
    agent_name = "workmatch_coordinator"
    description = "Your Workmatch assistant for helping you with your career journey. Let's make this part of your job search easy and engaging!"
    tools = [
        TracedAgentTool(agent=career_guidance_agent),
    ]
    agent_args = {
        "name": agent_name,
        "model": MODEL,
        "description": description,
        "instruction": prompt.WORKMATCH_ROOT_PROMPT,
        "tools": tools,
    }
    agent_class_to_use = TracedCoordinatorAgent if use_traced_root_class else Agent

    init_span_name = f"{agent_name}_init_otel_span"
    model_info_for_span = {"model_name": str(getattr(MODEL, 'name', str(MODEL)))}

    with langfuse_span(init_span_name, input_data=model_info_for_span) as init_otel_span:
        if init_otel_span:
            logger.info(f"[trace] Initializing {agent_name} within OTEL span.")
        else:
            logger.info(f"[trace] Initializing {agent_name} (OTEL span for init not created).")
        instance = agent_class_to_use(**agent_args)
    return instance

root_agent = build_root_agent(use_traced_root_class=True)
agent = root_agent