from typing import List, Dict, Any, Callable, Optional
from google.cloud import firestore
from vertexai.language_models import TextEmbeddingModel
import hashlib
import logging
import numpy as np
from datetime import datetime, timezone

# --- Setup ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

db = firestore.Client()
# CORRECTED: Using the specified embedding model 'text-embedding-005'
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-005")

# --- Helper Dictionaries ---
COUNTRY_CURRENCY_MAP = {
    "gb": "GBP",
    "us": "USD",
    "ca": "CAD",
    "au": "AUD",
    "de": "EUR",
    "fr": "EUR",
    # Add other countries as needed
}

# --- Core Functions ---

def compute_embedding(text: str) -> List[float]:
    """Generate embedding for input text, with error handling."""
    if not text or not isinstance(text, str):
        logger.warning("[embedding] Received empty or invalid text for embedding.")
        return []
    try:
        embeddings = embedding_model.get_embeddings([text])
        return embeddings[0].values
    except Exception as e:
        logger.error(f"[embedding] Failed to embed text: {e}", exc_info=True)
        return []

def hash_string(text: str) -> str:
    """Create a SHA256 hash for consistent IDs when a primary ID is not available."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def upsert_jobs_bulk(
    collection: str,
    jobs: List[Dict[str, Any]],
    country_code: str = "gb"
):
    """
    Batch embed and upsert job listings with robust, intelligent deduplication.

    This version normalizes location data to create a more reliable canonical ID,
    preventing duplicates from minor variations in API data.
    """
    batch = db.batch()
    upserted_count = 0
    skipped_count = 0
    processed_ids_in_batch = set()
    
    currency = COUNTRY_CURRENCY_MAP.get(country_code.lower(), "N/A")

    for job in jobs:
        # --- ROBUST CANONICAL ID LOGIC ---
        
        # 1. Extract and normalize core components
        title = job.get("title", "").strip().lower()
        company_name = job.get("company", {}).get("display_name", "").strip().lower()
        location_name = job.get("location", {}).get("display_name", "").strip().lower()

        if not all([title, company_name, location_name]):
            skipped_count += 1
            continue

        # 2. **Smarter Location Normalization:** Take only the first part of the location
        # This turns "woodditton, newmarket" into "woodditton" and "london, greater london" into "london".
        # This is the key change to handle location variations.
        normalized_location = location_name.split(',')[0].strip()

        # 3. Create the stable, composite key and hash it
        composite_key = f"{title}|{company_name}|{normalized_location}"
        doc_id = hash_string(composite_key)
        
        # Optional: Log the key for debugging to see what's being generated
        logger.debug(f"Generated composite key: '{composite_key}' -> doc_id: {doc_id}")

        if doc_id in processed_ids_in_batch:
            # We have already processed this exact job in this batch, so skip it.
            continue
        processed_ids_in_batch.add(doc_id)

        # --- Data Preparation ---
        full_description = job.get("description", "")
        if not full_description:
            skipped_count += 1
            continue

        vector = compute_embedding(full_description)
        if not vector:
            logger.warning(f"Skipping job {doc_id} due to embedding failure.")
            skipped_count += 1
            continue

        doc_ref = db.collection(collection).document(doc_id)

        # We choose the current job's data to be the version we save.
        # The `merge=True` will handle overwriting if this doc_id was from a previous run.
        doc_data = {
            "source": "adzuna",
            "source_id": job.get("id"),
            "title": job.get("title"),
            "company": { "name": job.get("company", {}).get("display_name") },
            "location": { "raw_text": job.get("location", {}).get("display_name") },
            "salary": {
                "min": job.get("salary_min"),
                "max": job.get("salary_max"),
                "currency": currency,
                "is_predicted": job.get("salary_is_predicted", False),
            },
            "description": full_description,
            "description_snippet": full_description[:400],
            "embedding": vector,
            "url": job.get("redirect_url"),
            "category": {
                "tag": job.get("category", {}).get("tag"),
                "label": job.get("category", {}).get("label"),
            },
            "created_at_source_utc": job.get("created"),
            "processed_at_utc": datetime.now(timezone.utc)
        }
        
        batch.set(doc_ref, doc_data, merge=True)
        upserted_count += 1

    if upserted_count > 0:
        batch.commit()
    
    logger.info(
        f"[firestore] Processed batch. Upserted: {upserted_count}. Skipped: {skipped_count}. "
        f"Unique jobs in batch: {len(processed_ids_in_batch)}."
    )


def query_similar_jobs(query: str, collection: str, top_k: int = 5) -> list:
    """
    Finds documents in a Firestore collection with embeddings similar to the query's embedding.

    *** CRITICAL SCALING WARNING ***
    This function fetches ALL documents from the collection and performs calculations in memory.
    This is INEFFICIENT and EXPENSIVE for large collections. It is suitable for prototypes ONLY.
    For production, you MUST use a dedicated vector database like Vertex AI Vector Search.
    """
    logger.info(f"Performing a low-efficiency similarity scan on '{collection}' for query: '{query}'")
    
    try:
        # Note: This re-initializes the model. For higher performance, you could pass the model object in.
        model = TextEmbeddingModel.from_pretrained("text-embedding-005")
        query_embedding = model.get_embeddings([query])[0].values
        if not query_embedding:
            logger.error("Could not generate embedding for query.")
            return []

        docs = db.collection(collection).stream()
        scored_docs = []

        for doc in docs:
            data = doc.to_dict()
            doc_embedding = data.get("embedding")
            if doc_embedding and isinstance(doc_embedding, list):
                similarity = np.dot(query_embedding, doc_embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding))
                scored_docs.append((similarity, data))

        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        return [match[1] for match in scored_docs[:top_k]]

    except Exception as e:
        logger.error(f"Failed during similarity query: {e}", exc_info=True)
        return []