import os
from google.cloud import secretmanager
from dotenv import load_dotenv

# Optional .env for local dev
load_dotenv()

DEFAULT_SECRET_MAP = {
    "GOOGLE_GENAI_USE_VERTEXAI": "google-genai-use-vertexai",
    "GOOGLE_CLOUD_PROJECT": "google-cloud-project",
    "GOOGLE_CLOUD_LOCATION": "google-cloud-location",
    "GEMINI_API_KEY": "gemini-api-key",  # only needed if using Gemini directly
    "GEMINI_MODEL": "gemini-model",      # optional override
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
        if os.getenv(env_var):  # already set (e.g. by .env)
            continue
        try:
            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            os.environ[env_var] = response.payload.data.decode("utf-8")
        except Exception as e:
            print(f"[env] Warning: Failed to load {env_var} from {secret_name}: {e}")


def get_model(default="gemini-2.5-pro-preview-05-06") -> str:
    """
    Get model name from env, fallback to default.
    """
    return os.getenv("GEMINI_MODEL", default)
