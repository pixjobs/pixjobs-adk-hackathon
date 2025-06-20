import os
import base64
import logging
from functools import lru_cache
from google.cloud import secretmanager
from dotenv import load_dotenv

# --- Logging setup ---
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

_env_loaded = False


def load_env(project_id: str = "workmatch-hackathon", secret_map: dict = None):
    """Loads secrets into environment variables once per runtime."""
    global _env_loaded
    if _env_loaded:
        logger.debug("[env] Already loaded; skipping.")
        return

    if os.path.exists(".env"):
        load_dotenv()
        logger.debug("[env] Loaded local .env file.")
    else:
        logger.debug("[env] No .env file found.")

    secret_map = secret_map or DEFAULT_SECRET_MAP
    client = secretmanager.SecretManagerServiceClient()

    logger.debug("[env] Fetching secrets from Secret Manager...")
    for env_var, secret_name in secret_map.items():
        try:
            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            os.environ[env_var] = response.payload.data.decode("utf-8").strip()
            logger.debug(f"[env] Loaded {env_var} from Secret Manager.")
        except Exception as e:
            logger.warning(f"[env] Failed to load {env_var} from '{secret_name}': {e}")

    if os.getenv("ENABLE_LANGFUSE", "").lower() == "true":
        pub, sec = os.getenv("LANGFUSE_PUBLIC_KEY"), os.getenv("LANGFUSE_SECRET_KEY")
        if pub and sec:
            auth = base64.b64encode(f"{pub}:{sec}".encode()).decode()
            os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {auth}"
            os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://cloud.langfuse.com/api/public/otel"
            logger.info("[env] Langfuse telemetry enabled.")
        else:
            logger.warning("[env] Langfuse enabled but keys are missing.")

    _env_loaded = True


@lru_cache(maxsize=1)
def get_model(default: str = "gemini-2.5-flash") -> str:
    """Returns Gemini model from environment or fallback."""
    model = os.getenv("GEMINI_MODEL", default)
    logger.debug(f"[env] Using Gemini model: {model}")
    return model


# Safe preload (optional for ADK Web usage)
try:
    load_env()
except Exception as e:
    logger.warning(f"[env] Could not load secrets on import: {e}")
