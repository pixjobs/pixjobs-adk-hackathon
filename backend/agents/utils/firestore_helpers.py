import logging
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any

from google.cloud import firestore
from vertexai.language_models import TextEmbeddingModel

# --- Module-level Setup ---

# Setup logging to get clear output on the module's operations
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize Google Cloud clients once to be reused throughout the application
db = firestore.Client()
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-005")

# Define a centralized map for country codes to their currency for accurate data storage
COUNTRY_CURRENCY_MAP = {
    "gb": "GBP",
    "us": "USD",
    "de": "EUR",
    "fr": "EUR",
    "ca": "CAD",
    "au": "AUD",
    "in": "INR",
    # Add other countries as needed
}

# --- Core Helper Functions ---

def compute_embedding(text: str) -> List[float]:
    """
    Generates a 768-dimension embedding for a given text using a Vertex AI model.
    Handles errors and invalid input gracefully.
    """
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
    """Creates a stable SHA256 hash for a given string to use as a consistent ID."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def upsert_jobs_metadata_bulk(
    collection: str,
    jobs: List[Dict[str, Any]],
    country_code: str = "gb"
):
    """
    Batch upserts job metadata into Firestore with robust, intelligent deduplication.

    This function creates a canonical ID for each job based on its title, company,
    and normalized location. It then modifies the input 'jobs' list in-place by
    adding this 'canonical_id' to each job dictionary, making it available to the caller.
    This function does NOT handle vector embeddings.
    """
    batch = db.batch()
    upserted_count = 0
    skipped_count = 0
    processed_ids_in_batch = set()

    currency = COUNTRY_CURRENCY_MAP.get(country_code.lower(), "N/A")

    for job in jobs:
        # Create a canonical ID from core attributes for stable deduplication
        title = job.get("title", "").strip().lower()
        company_name = job.get("company", {}).get("display_name", "").strip().lower()
        location_name = job.get("location", {}).get("display_name", "").strip().lower()

        if not all([title, company_name, location_name]):
            skipped_count += 1
            continue

        # Normalize location to handle minor API variations (e.g., "London, UK" vs "London")
        normalized_location = location_name.split(',')[0].strip()
        composite_key = f"{title}|{company_name}|{normalized_location}"
        doc_id = hash_string(composite_key)

        # Skip processing if we've already handled this unique job in this batch
        if doc_id in processed_ids_in_batch:
            continue
        processed_ids_in_batch.add(doc_id)

        # IMPORTANT: Add the generated ID to the job dict for the agent to use with Pinecone
        job['canonical_id'] = doc_id

        doc_ref = db.collection(collection).document(doc_id)

        # Prepare the metadata document, excluding the vector embedding
        doc_data = {
            "source": "adzuna",
            "source_id": job.get("id"),
            "title": job.get("title"),
            "company": {"name": job.get("company", {}).get("display_name")},
            "location": {"raw_text": job.get("location", {}).get("display_name")},
            "salary": {
                "min": job.get("salary_min"),
                "max": job.get("salary_max"),
                "currency": currency,
                "is_predicted": job.get("salary_is_predicted", False),
            },
            "description": job.get("description", ""),
            "description_snippet": job.get("description", "")[:400],
            "url": job.get("redirect_url"),
            "category": {
                "tag": job.get("category", {}).get("tag"),
                "label": job.get("category", {}).get("label"),
            },
            "created_at_source_utc": job.get("created"),
            "processed_at_utc": datetime.now(timezone.utc)
        }

        # Use merge=True to create the document or update it if it already exists
        batch.set(doc_ref, doc_data, merge=True)
        upserted_count += 1

    if upserted_count > 0:
        batch.commit()

    logger.info(
        f"[firestore] Upserted metadata for {upserted_count} records to '{collection}'. "
        f"Skipped {skipped_count}."
    )


def get_jobs_by_ids(collection: str, ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetches multiple documents from Firestore based on a list of document IDs.
    This is the retrieval step for the RAG workflow after getting IDs from Pinecone.
    """
    if not ids:
        return []

    logger.info(f"[firestore] Retrieving {len(ids)} documents from '{collection}'.")
    docs = []
    for doc_id in ids:
        try:
            doc_ref = db.collection(collection).document(doc_id)
            doc = doc_ref.get()
            if doc.exists:
                docs.append(doc.to_dict())
            else:
                logger.warning(f"[firestore] Document with ID '{doc_id}' not found.")
        except Exception as e:
            logger.error(f"[firestore] Failed to retrieve doc '{doc_id}': {e}", exc_info=True)
    return docs