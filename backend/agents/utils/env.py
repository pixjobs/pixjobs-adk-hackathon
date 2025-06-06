import os
import base64
from google.cloud import secretmanager
from dotenv import load_dotenv
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Optional .env for local development
load_dotenv()

DEFAULT_SECRET_MAP = {
    "GOOGLE_CLOUD_PROJECT": "google-cloud-project",
    "GOOGLE_CLOUD_LOCATION": "google-cloud-location",
    "GEMINI_API_KEY": "gemini-api-key",        # Only needed if using Gemini directly
    "GEMINI_MODEL": "gemini-model",            # Optional override
    "ENABLE_LANGFUSE": "enable-langfuse",      # Toggle telemetry
    "LANGFUSE_SECRET_KEY": "langfuse-secret-key",
    "LANGFUSE_PUBLIC_KEY": "langfuse-public-key",
}

def load_env(project_id: str = "workmatch-hackathon", secret_map: dict = None):
    """
    Load environment variables from Secret Manager or .env fallback.

    Args:
        project_id (str): GCP project ID
        secret_map (dict): ENV_VAR -> Secret Name mapping
    """
    client = secretmanager.SecretManagerServiceClient()
    secret_map = secret_map or DEFAULT_SECRET_MAP

    for env_var, secret_name in secret_map.items():
        if os.getenv(env_var):  # Already set (e.g. by .env)
            logger.debug(f"[env] {env_var} already set, skipping Secret Manager lookup.")
            continue
        try:
            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            value = response.payload.data.decode("utf-8")
            os.environ[env_var] = value
            logger.info(f"[env] Loaded {env_var} from Secret Manager.")
        except Exception as e:
            logger.warning(f"[env] Failed to load {env_var} from {secret_name}: {e}")

    # Setup Langfuse OpenTelemetry headers if enabled
    if os.getenv("ENABLE_LANGFUSE", "").lower() == "true":
        pub = os.getenv("LANGFUSE_PUBLIC_KEY")
        sec = os.getenv("LANGFUSE_SECRET_KEY")
        if pub and sec:
            auth = base64.b64encode(f"{pub}:{sec}".encode()).decode()
            os.environ.setdefault("OTEL_EXPORTER_OTLP_HEADERS", f"Authorization=Basic {auth}")
            os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "https://cloud.langfuse.com/api/public/otel")
            logger.info("[env] Langfuse telemetry enabled.")
        else:
            logger.warning("[env] Langfuse enabled but missing public or secret key.")


def get_model(default="gemini-2.0-flash") -> str:
    """
    Get model name from env, fallback to default.
    """
    model = os.getenv("GEMINI_MODEL", default)
    logger.info(f"[env] Using Gemini model: {model}")
    return model
