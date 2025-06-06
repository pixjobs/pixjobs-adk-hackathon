import logging
import os
import base64
import json
from langfuse import Langfuse as LangfuseSDKInstance # Keep this alias
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource # <--- ADD THIS IMPORT
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from contextlib import contextmanager

logger = logging.getLogger(__name__)

langfuse_sdk_instance = None # Explicitly named SDK instance
otel_tracer = None

def init_tracer(service_name: str = "workmatch-adk"):
    global langfuse_sdk_instance, otel_tracer

    enable_langfuse_env_val = os.getenv("ENABLE_LANGFUSE")
    is_langfuse_enabled_str = str(enable_langfuse_env_val or "false").lower().strip()
    langfuse_should_be_enabled = is_langfuse_enabled_str == "true"

    if langfuse_should_be_enabled:
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        if public_key and secret_key:
            logger.info("[tracing] Langfuse telemetry will be enabled with keys.")
            auth_header = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
            os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {auth_header}"
            os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "https://cloud.langfuse.com/api/public/otel")
            try:
                # Use the aliased name here
                langfuse_sdk_instance = LangfuseSDKInstance(public_key=public_key, secret_key=secret_key, host="https://cloud.langfuse.com")
                logger.info("[tracing] Langfuse SDK initialised.")
            except Exception as e:
                logger.error(f"[tracing] Langfuse SDK init failed: {e}")
        else:
            logger.warning("[tracing] Langfuse should be enabled, but keys are missing.")
    else:
        logger.info("[tracing] Langfuse telemetry determined to be disabled.")

    try:
        resource = Resource.create({"service.name": service_name}) # Now Resource is defined
        provider = TracerProvider(resource=resource)
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

        if otlp_endpoint:
            logger.info(f"[tracing] Using OTLP exporter for endpoint: {otlp_endpoint}")
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        else:
            logger.info("[tracing] No OTLP endpoint. Using ConsoleSpanExporter for OTEL.")
            exporter = ConsoleSpanExporter()

        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        otel_tracer = trace.get_tracer(service_name)
        logger.info(f"[tracing] OTEL tracer initialised for service: {service_name}")
    except Exception as e:
        logger.error(f"[tracing] OTEL tracer init failed: {e}")
    return otel_tracer

def get_langfuse(): # This returns the Langfuse SDK instance
    return langfuse_sdk_instance

@contextmanager
def langfuse_span(name: str, input_data: dict = None, metadata: dict = None): # This creates an OTEL span
    if not otel_tracer:
        logger.warning(f"[trace] OTEL tracer not initialized. OTEL Span '{name}' will not be created.")
        yield None
        return

    with otel_tracer.start_as_current_span(name) as span:
        try:
            if input_data:
                for key, value in input_data.items():
                    try:
                        serialized_value = json.dumps(value) if isinstance(value, (dict, list, tuple)) else value
                        if serialized_value is not None: span.set_attribute(f"input.{key}", serialized_value)
                    except TypeError:
                        if value is not None: span.set_attribute(f"input.{key}", str(value))
            if metadata:
                for key, value in metadata.items():
                    try:
                        serialized_value = json.dumps(value) if isinstance(value, (dict, list, tuple)) else value
                        if serialized_value is not None: span.set_attribute(f"metadata.{key}", serialized_value)
                    except TypeError:
                        if value is not None: span.set_attribute(f"metadata.{key}", str(value))
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise