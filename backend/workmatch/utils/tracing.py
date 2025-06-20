import os
import json
import base64
import logging
from contextlib import contextmanager

from langfuse import Langfuse as LangfuseSDKInstance
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

logger = logging.getLogger(__name__)

# --- Globals ---
langfuse_sdk_instance = None
otel_tracer = None
_tracer_initialised = False


def init_tracer(service_name: str = "workmatch-adk"):
    """
    Initialise OTEL and Langfuse tracer setup.
    """
    global langfuse_sdk_instance, otel_tracer, _tracer_initialised
    if _tracer_initialised:
        logger.debug("[tracing] Tracer already initialised; skipping.")
        return otel_tracer

    # --- Langfuse setup ---
    if os.getenv("ENABLE_LANGFUSE", "").strip().lower() == "true":
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        if public_key and secret_key:
            logger.info("[tracing] Langfuse telemetry will be enabled with keys.")
            try:
                auth_header = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
                os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {auth_header}"
                os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "https://cloud.langfuse.com/api/public/otel")
                langfuse_sdk_instance = LangfuseSDKInstance(
                    public_key=public_key,
                    secret_key=secret_key,
                    host="https://cloud.langfuse.com"
                )
                logger.debug("[tracing] Langfuse SDK initialised.")
            except Exception as e:
                logger.error(f"[tracing] Langfuse SDK init failed: {e}")
        else:
            logger.warning("[tracing] Langfuse enabled but keys are missing.")
    else:
        logger.debug("[tracing] Langfuse is disabled via environment.")

    # --- OTEL setup ---
    try:
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)

        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if otlp_endpoint:
            logger.debug(f"[tracing] Using OTLP exporter for endpoint: {otlp_endpoint}")
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        else:
            logger.debug("[tracing] Using ConsoleSpanExporter.")
            exporter = ConsoleSpanExporter()

        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        otel_tracer = trace.get_tracer(service_name)
        logger.info(f"[tracing] OTEL tracer initialised for service: {service_name}")
        _tracer_initialised = True

    except Exception as e:
        logger.error(f"[tracing] OTEL tracer init failed: {e}")

    return otel_tracer


def get_langfuse():
    return langfuse_sdk_instance


@contextmanager
def langfuse_span(name: str, input_data: dict = None, metadata: dict = None):
    """
    Creates a traced OTEL span with optional metadata and input attribution.
    """
    if not otel_tracer:
        logger.warning(f"[trace] OTEL tracer not initialised. Skipping span: {name}")
        yield None
        return

    with otel_tracer.start_as_current_span(name) as span:
        try:
            _attach_data(span, "input", input_data)
            _attach_data(span, "metadata", metadata)
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise


def _attach_data(span, prefix: str, data: dict):
    if not data:
        return
    for key, value in data.items():
        try:
            if isinstance(value, (dict, list, tuple)):
                value = json.dumps(value)
            elif not isinstance(value, (str, int, float, bool)):
                value = str(value)
            span.set_attribute(f"{prefix}.{key}", value)
        except Exception:
            pass  # Silent fail for non-serialisable attributes
