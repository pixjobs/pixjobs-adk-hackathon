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

# --- Updated Secret Map ---
DEFAULT_SECRET_MAP = {
    "GOOGLE_CLOUD_PROJECT": "google-cloud-project",
    "GOOGLE_CLOUD_LOCATION": "google-cloud-location",
    "GEMINI_API_KEY": "gemini-api-key",        # Only needed if using Gemini directly
    "GEMINI_MODEL": "gemini-model",            # Optional override
    "ENABLE_LANGFUSE": "enable-langfuse",      # Toggle telemetry
    "LANGFUSE_SECRET_KEY": "langfuse-secret-key",
    "LANGFUSE_PUBLIC_KEY": "langfuse-public-key",

    # ✅ Adzuna API credentials
    "ADZUNA_APP_ID": "adzuna-app-id",
    "ADZUNA_APP_KEY": "adzuna-app-key",
}

def load_env(project_id: str = "workmatch-hackathon", secret_map: dict = None):
    """
    Load environment variables from Secret Manager or .env fallback.

    Args:
        project_id (str): GCP project ID
        secret_map (dict): ENV_VAR -> Secret Name mapping
    """
    secret_map = secret_map or DEFAULT_SECRET_MAP

    # Check if we can use Secret Manager
    try:
        client = secretmanager.SecretManagerServiceClient()
        can_use_secret_manager = True
        logger.info("[env] Secret Manager client initialized. Will attempt to load secrets from GCP.")
    except Exception as e:
        client = None
        can_use_secret_manager = False
        logger.warning(f"[env] Could not initialize Secret Manager client: {e}. Will rely on local .env file or pre-set environment variables.")

    for env_var, secret_name in secret_map.items():
        # Priority 1: Check if already set
        if os.getenv(env_var):
            logger.debug(f"[env] {env_var} already set, skipping lookup.")
            continue

        # Priority 2: Try Secret Manager
        if can_use_secret_manager:
            try:
                name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": name})
                value = response.payload.data.decode("utf-8")
                os.environ[env_var] = value
                logger.info(f"[env] Loaded {env_var} from Secret Manager.")
            except Exception as e:
                logger.warning(f"[env] Failed to load {env_var} from secret '{secret_name}': {e}")
        else:
            logger.debug(f"[env] {env_var} not found in environment and Secret Manager is unavailable.")

    # Langfuse OpenTelemetry header setup (optional)
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
