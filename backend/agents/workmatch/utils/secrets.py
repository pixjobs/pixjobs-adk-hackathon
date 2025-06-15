import os
import logging
from google.cloud import secretmanager
from dotenv import load_dotenv

if os.getenv("ENV") != "production":
    load_dotenv()

def load_env_from_secret(secret_map: dict, project_id: str):
    client = secretmanager.SecretManagerServiceClient()

    for env_var, secret_name in secret_map.items():
        if os.getenv(env_var):
            continue
        try:
            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            value = response.payload.data.decode("utf-8")
            os.environ[env_var] = value
        except Exception as e:
            logging.warning(f"[env] Could not load secret '{secret_name}' for '{env_var}': {e}")