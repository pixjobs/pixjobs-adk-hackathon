import os
import base64
import logging
from functools import lru_cache
from google.cloud import secretmanager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Secret Manager Mappings ---
DEFAULT_SECRET_MAP = {
    "GOOGLE_GENAI_USE_VERTEXAI": "google-genai-use-vertexai",
    "GOOGLE_CLOUD_PROJECT": "google-cloud-project",
    "GOOGLE_CLOUD_LOCATION": "google-cloud-location",
    "GEMINI_MODEL": "gemini-model",
    "ENABLE_LANGFUSE": "enable-langfuse",
    "LANGFUSE_SECRET_KEY": "langfuse-secret-key",
    "LANGFUSE_PUBLIC_KEY": "langfuse-public-key",
    "ADZUNA_APP_ID": "adzuna-app-id",
    "ADZUNA_APP_KEY": "adzuna-app-key",
}

def load_env(project_id: str = "workmatch-hackathon", secret_map: dict = None):
    """
    Force-load environment variables from GCP Secret Manager.
    """
    secret_map = secret_map or DEFAULT_SECRET_MAP
    client = secretmanager.SecretManagerServiceClient()

    logger.info("[env] Loading all secrets from Secret Manager...")

    for env_var, secret_name in secret_map.items():
        try:
            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            value = response.payload.data.decode("utf-8").strip()
            os.environ[env_var] = value
            logger.info(f"[env] Loaded {env_var} from Secret Manager.")
        except Exception as e:
            logger.error(f"[env] Failed to load {env_var} from secret '{secret_name}': {e}")
            raise RuntimeError(f"Missing or inaccessible secret: {secret_name}")

    # Optional: Langfuse setup
    if os.getenv("ENABLE_LANGFUSE", "").lower() == "true":
        pub = os.getenv("LANGFUSE_PUBLIC_KEY")
        sec = os.getenv("LANGFUSE_SECRET_KEY")
        if pub and sec:
            auth = base64.b64encode(f"{pub}:{sec}".encode()).decode()
            os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {auth}"
            os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://cloud.langfuse.com/api/public/otel"
            logger.info("[env] Langfuse telemetry enabled.")
        else:
            logger.warning("[env] Langfuse enabled but keys are missing.")

@lru_cache(maxsize=1)
def get_model(default: str = "gemini-2.5-flash") -> str:
    """
    Memoized getter for Gemini model name from environment, fallback to default.
    Used for ADK (expects string).
    """
    model = os.getenv("GEMINI_MODEL", default)
    logger.info(f"[env] Using Gemini model: {model}")
    return model
