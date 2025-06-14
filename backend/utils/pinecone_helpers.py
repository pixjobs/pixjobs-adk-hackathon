import os
import logging
from typing import List, Dict, Any, Tuple
from pinecone import Pinecone, ServerlessSpec
from google.cloud import secretmanager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DEFAULT_INDEX_DIMENSIONS = 768
DEFAULT_REGION = "us-east-1"
DEFAULT_METRIC = "cosine"


def load_pinecone_api_key(
    secret_name: str = "pinecone-api-key",
    project_id: str = "workmatch-hackathon"
) -> str:
    """Fetch Pinecone API key from Google Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8")


# ---- Singleton Pinecone client instance ----
_pc: Pinecone = None

def get_pinecone_client() -> Pinecone:
    """Initialise Pinecone client (singleton)."""
    global _pc
    if _pc is None:
        api_key = os.getenv("PINECONE_API_KEY") or load_pinecone_api_key()
        _pc = Pinecone(api_key=api_key)
        logger.info("[pinecone] Client initialized")
    return _pc


def ensure_pinecone_index(
    index_name: str,
    dimension: int = DEFAULT_INDEX_DIMENSIONS,
    metric: str = DEFAULT_METRIC
) -> None:
    """Ensure the Pinecone index exists. Creates it if missing (Serverless AWS, us-east-1)."""
    pc = get_pinecone_client()
    existing = [idx.name for idx in pc.list_indexes().indexes]
    if index_name in existing:
        logger.info(f"[pinecone] Index '{index_name}' already exists.")
        return

    logger.info(f"[pinecone] Creating index '{index_name}' (dim={dimension}, metric={metric})")
    pc.create_index(
        name=index_name,
        dimension=dimension,
        metric=metric,
        spec=ServerlessSpec(cloud="aws", region=DEFAULT_REGION)
    )
    logger.info(f"[pinecone] Index '{index_name}' created.")


def get_index(index_name: str) -> Any:
    """Return a Pinecone index object. Ensures the index exists first."""
    pc = get_pinecone_client()
    existing = [idx.name for idx in pc.list_indexes().indexes]
    if index_name not in existing:
        ensure_pinecone_index(index_name)
    # The object returned here does not have a .name attribute in the new SDK
    return pc.Index(index_name)


def upsert_vectors(
    index: Any,
    index_name: str, 
    items: List[Tuple[str, List[float], Dict[str, Any]]]
) -> None:
    """
    Upsert a batch of vectors into the Pinecone index.
    """
    if not items:
        logger.warning("[pinecone] No vectors to upsert.")
        return
    try:
        index.upsert(vectors=items)
        # Use the passed index_name here
        logger.info(f"[pinecone] Upserted {len(items)} vectors into '{index_name}'.") # <--- MODIFIED LINE
    except Exception as e:
        logger.error(f"[pinecone] Upsert failed: {e}", exc_info=True)


def query_vectors(
    index: Any,
    embedding: List[float],
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Query the Pinecone index using an embedding.
    Returns top_k matches with metadata.
    """
    try:
        resp = index.query(
            vector=embedding,
            top_k=top_k,
            include_metadata=True
        )
        return resp.matches
    except Exception as e:
        logger.error(f"[pinecone] Query failed: {e}", exc_info=True)
        return []