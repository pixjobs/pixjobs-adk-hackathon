import os
import logging
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any, Tuple
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
    """Fetch Pinecone API key from Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8")

# ---- Create a single Pinecone client instance ----
_pc: Pinecone = None
def get_pinecone_client() -> Pinecone:
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
    """
    Ensure that a Pinecone index exists, creating it if needed.
    Uses aws/us-east-1 serverless spec.
    """
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

def get_index(index_name: str) -> Pinecone:
    """Return a Pinecone index handle, creating it if missing."""
    pc = get_pinecone_client()
    # list_indexes().names() returns list of names
    existing = [idx.name for idx in pc.list_indexes().indexes]
    if index_name not in existing:
        ensure_pinecone_index(index_name)
    return pc.Index(index_name)

def upsert_vectors(
    index,
    items: List[Tuple[str, List[float], Dict[str, Any]]]
) -> None:
    """
    Upsert vectors into Pinecone.
    items: [(id, vector, metadata), ...]
    """
    if not items:
        logger.warning("[pinecone] No vectors to upsert.")
        return
    try:
        index.upsert(vectors=items)
        logger.info(f"[pinecone] Upserted {len(items)} vectors into '{index.name}'.")
    except Exception as e:
        logger.error(f"[pinecone] Upsert failed: {e}", exc_info=True)

def query_vectors(
    index,
    embedding: List[float],
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Query Pinecone index with an embedding.
    Returns list of matches with metadata.
    """
    try:
        resp = index.query(vector=embedding, top_k=top_k, include_metadata=True)
        return resp.matches
    except Exception as e:
        logger.error(f"[pinecone] Query failed: {e}", exc_info=True)
        return []
