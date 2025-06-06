import os
from google.cloud import secretmanager
from dotenv import load_dotenv

# Optional: load local .env for development fallback
load_dotenv()

def load_env_from_secret(secret_map: dict, project_id: str):
    """
    Load environment variables from Secret Manager.

    Args:
        secret_map (dict): Map of ENV_VAR -> Secret Name
        project_id (str): GCP project ID
    """
    client = secretmanager.SecretManagerServiceClient()

    for env_var, secret_name in secret_map.items():
        if os.getenv(env_var):  # already set via .env or OS
            continue
        try:
            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            value = response.payload.data.decode("utf-8")
            os.environ[env_var] = value
        except Exception as e:
            print(f"[env] Warning: Could not load {secret_name}: {e}")
