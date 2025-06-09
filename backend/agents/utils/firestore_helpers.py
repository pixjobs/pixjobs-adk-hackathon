from typing import List, Dict, Any, Callable
from google.cloud import firestore
from vertexai.language_models import TextEmbeddingModel
import hashlib
import logging
import numpy as np

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- Firestore & Embedding Setup ---
db = firestore.Client()
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-005")


def compute_embedding(text: str) -> List[float]:
    """Generate 768-dim embedding for input text."""
    try:
        return embedding_model.get_embeddings([text])[0].values
    except Exception as e:
        logger.error(f"[embedding] Failed to embed text: {e}", exc_info=True)
        return []


def hash_string(text: str) -> str:
    """Create a SHA256 hash for consistent IDs."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def store_job_vector(
    collection: str,
    job_id: str,
    content: str,
    metadata: Dict[str, Any]
) -> str:
    """Embed content and store full Firestore document."""
    vector = compute_embedding(content)
    doc_ref = db.collection(collection).document(job_id)
    doc_ref.set({
        "embedding": vector,
        "content": content,
        **metadata
    })
    logger.info(f"[firestore] Stored job vector for {job_id} in {collection}")
    return job_id


def upsert_jobs_bulk(
    collection: str,
    jobs: List[Dict[str, Any]],
    content_field: str = "description_snippet",
    id_fn: Callable[[Dict[str, Any]], str] = lambda job: hash_string(
        job.get("title", "") + job.get("company", {}).get("display_name", "")
    )
):
    """Batch embed + upsert Adzuna job listings into Firestore."""
    batch = db.batch()
    skipped = 0

    for job in jobs:
        content = job.get(content_field, "")
        if not content:
            skipped += 1
            continue

        doc_id = id_fn(job)
        vector = compute_embedding(content)
        doc_ref = db.collection(collection).document(doc_id)
        batch.set(doc_ref, {
            "embedding": vector,
            "content": content,
            "title": job.get("title"),
            "company": job.get("company", {}).get("display_name"),
            "location": job.get("location", {}).get("display_name"),
            "salary": job.get("salary_max") or job.get("salary_min"),
            "url": job.get("redirect_url"),
            "tags": job.get("category", {}).get("tag"),
            "label": job.get("category", {}).get("label"),
        })

    batch.commit()
    logger.info(f"[firestore] Upserted {len(jobs) - skipped} job records to {collection}, skipped {skipped}")

def query_similar_jobs(query: str, collection: str, top_k: int = 5, score_threshold: float = 0.75) -> list:
    model = TextEmbeddingModel.from_pretrained("text-embedding-005")
    query_embedding = model.get_embeddings([query])[0].values

    db = firestore.Client()
    docs = db.collection(collection).stream()

    scored = []
    for doc in docs:
        data = doc.to_dict()
        vec = data.get("embedding")
        if not vec:
            continue
        similarity = np.dot(query_embedding, vec) / (np.linalg.norm(query_embedding) * np.linalg.norm(vec))
        if similarity >= score_threshold:
            scored.append((similarity, data))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [match[1] for match in scored[:top_k]]
