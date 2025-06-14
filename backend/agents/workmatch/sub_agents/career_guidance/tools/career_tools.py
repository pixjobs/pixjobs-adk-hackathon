import logging
from typing import List, Dict, Any, Optional

from utils.adzuna import adzuna_api
from utils.env import get_model # Assuming this is for your embedding model setup
from utils.firestore_helpers import (
    upsert_jobs_metadata_bulk, get_jobs_by_ids, compute_embedding
)
from utils.pinecone_helpers import (
    get_index, upsert_vectors, query_vectors
)

logger = logging.getLogger(__name__)
MODEL_INSTANCE = get_model() # This is fine, but ensure get_model() returns the embedding model
pinecone_job_index = get_index("job-postings")

COUNTRY_CURRENCY_MAP = {
    "gb": "GBP", "us": "USD", "de": "EUR", "fr": "EUR",
    "ca": "CAD", "au": "AUD", "in": "INR",
}
HIGH_PAYING_THRESHOLDS = {
    "gb": 50000, "us": 85000, "de": 65000, "fr": 60000,
    "ca": 80000, "au": 90000, "in": 1500000,
}
DEFAULT_HIGH_PAYING_THRESHOLD = 50000


def _format_salary(salary_data: Any) -> str:
    if not isinstance(salary_data, dict):
        return "Not listed"
    salary_min = salary_data.get("min")
    salary_max = salary_data.get("max")
    currency = salary_data.get("currency", "N/A")
    if salary_max and salary_min and salary_max != salary_min:
        return f"{currency} {salary_min:,.0f} - {salary_max:,.0f}"
    value = salary_max or salary_min
    return f"{currency} {value:,.0f}" if value else "Not listed"


def _format_employment_type(job: Dict[str, Any]) -> str:
    contract_type = job.get("contract_type", "").capitalize()
    contract_time = job.get("contract_time", "").replace("_", " ").capitalize()
    if contract_type and contract_time:
        return f"{contract_type}, {contract_time}"
    return contract_type or contract_time or "N/A"


def _ingest_jobs_data(jobs: List[Dict[str, Any]], country_code: str):
    """Stores job metadata in Firestore and embeds/upserts to Pinecone."""
    if not jobs:
        return

    # Note: upsert_jobs_metadata_bulk modifies 'jobs' in-place by adding 'canonical_id'
    upsert_jobs_metadata_bulk("job-postings", jobs, country_code=country_code)

    vectors_to_upsert = []
    for job in jobs:
        doc_id = job.get("canonical_id")
        if not doc_id:
            # This job was skipped by firestore_helpers.upsert_jobs_metadata_bulk
            # due to missing title/company/location, so it won't have a canonical_id.
            # Skip embedding/upserting it to Pinecone as well.
            continue

        embedding = compute_embedding(job.get("description", ""))
        if not embedding:
            logger.warning(f"[_ingest_jobs_data] Skipping embedding for job {doc_id} due to empty description.")
            continue

        metadata = {
            "title": job.get("title", ""),
            "location": job.get("location", {}).get("display_name", ""),
            "contract_type": job.get("contract_type", ""),
            "contract_time": job.get("contract_time", ""),
            "currency": job.get("salary", {}).get("currency", COUNTRY_CURRENCY_MAP.get(country_code, "N/A")),
            "job_id": doc_id,
            "country_code": country_code,
        }

        vectors_to_upsert.append((doc_id, embedding, metadata))

    if vectors_to_upsert:
        # --- FIX APPLIED HERE ---
        # The 'upsert_vectors' function now expects the index name as the second argument
        upsert_vectors(pinecone_job_index, "job-postings", vectors_to_upsert)


async def _search_jobs_with_backoff(
    job_title: str,
    country_code: str,
    location: Optional[str],
    salary_min: Optional[int],
    employment_type: Optional[str],
    expanded_titles: Optional[List[str]] = None,
    results_limit: int = 25
) -> List[Dict[str, Any]]:
    try:
        what_query = " ".join(job_title.strip().split())
        variants = expanded_titles or []
        clean_variants = [v for v in variants if v.lower() != what_query.lower()]
        what_or_query = ", ".join(clean_variants[:3]) # Only take up to 3 variants for OR query
        if not what_or_query: # Ensure what_or is not empty if no variants
            what_or_query = what_query


        logger.info(f"[Adzuna] Query: what='{what_query}' | OR='{what_or_query}'")

        jobs = adzuna_api.search_jobs(
            what=what_query,
            what_or=what_or_query,
            country=country_code,
            location=location,
            salary_min=salary_min,
            employment_type=employment_type,
            results_limit=results_limit,
            max_pages=3
        ).get("results", [])

        return jobs or []
    except Exception as e:
        logger.error(f"[Search] Error during job search: {e}", exc_info=True) # Added exc_info
        return []


async def get_job_role_descriptions_function(
    job_title: str,
    country_code: str = "gb",
    location: Optional[str] = None,
    salary_min: Optional[int] = None,
    employment_type: Optional[str] = None,
    expanded_titles: Optional[List[str]] = None
) -> dict:
    logger.info(f"[Tool] get_job_role_descriptions: '{job_title}'")

    current_salary_min = salary_min
    # Ensure this check is robust and doesn't interfere with actual salary_min if present
    if "high paying" in job_title.lower() and (salary_min is None or salary_min == 0): # Added check for salary_min None or 0
        threshold = HIGH_PAYING_THRESHOLDS.get(country_code, DEFAULT_HIGH_PAYING_THRESHOLD)
        current_salary_min = threshold # Use threshold if no explicit salary_min or it's 0
    elif "high paying" in job_title.lower() and salary_min is not None:
        threshold = HIGH_PAYING_THRESHOLDS.get(country_code, DEFAULT_HIGH_PAYING_THRESHOLD)
        current_salary_min = max(salary_min, threshold) # If salary_min is given, take max


    jobs = await _search_jobs_with_backoff(
        job_title=job_title,
        expanded_titles=expanded_titles,
        country_code=country_code,
        location=location,
        salary_min=current_salary_min,
        employment_type=employment_type,
        results_limit=50
    )

    if jobs:
        logger.info(f"[Adzuna] Found {len(jobs)} results.")
        # Ensure job-postings is consistently passed as the collection name
        _ingest_jobs_data(jobs, country_code)
        # Return a list of dictionaries with relevant job info for the agent
        # Example of formatting the output:
        formatted_jobs = []
        for job in jobs[:5]: # Only return up to 5 detailed examples
            formatted_jobs.append({
                "title": job.get("title"),
                "company": job.get("company", {}).get("display_name"),
                "location": job.get("location", {}).get("display_name"),
                "salary": _format_salary(job.get("salary", {})),
                "employment_type": _format_employment_type(job),
                "url": job.get("redirect_url"),
                "description_snippet": job.get("description", "")[:200] + "..." if len(job.get("description", "")) > 200 else job.get("description", "")
            })
        return {"result": formatted_jobs}


    logger.info("[Fallback] Using Pinecone semantic search.")
    embedding = compute_embedding(job_title)
    if embedding:
        pinecone_results = query_vectors(pinecone_job_index, embedding, top_k=10)
        job_ids = [match["id"] for match in pinecone_results if match.get("id")]
        if job_ids:
            matched_jobs_metadata = get_jobs_by_ids("job-postings", job_ids)
            if matched_jobs_metadata:
                # Format matched jobs from metadata for the agent output
                formatted_matched_jobs = []
                for job_meta in matched_jobs_metadata[:5]: # Return up to 5 from fallback
                    formatted_matched_jobs.append({
                        "title": job_meta.get("title"),
                        "company": job_meta.get("company", {}).get("name"),
                        "location": job_meta.get("location", {}).get("raw_text"),
                        "salary": _format_salary(job_meta.get("salary", {})),
                        "employment_type": _format_employment_type(job_meta), # This might need adaptation if meta schema differs
                        "url": job_meta.get("url"),
                        "description_snippet": job_meta.get("description_snippet", "")
                    })
                return {"result": formatted_matched_jobs, "message": "Showing similar roles via AI match."}

    return {"result": None, "message": f"No job matches found for '{job_title}'."}


async def ingest_jobs_from_adzuna(
    what: str,
    country_code: str = "gb",
    location: Optional[str] = None,
    salary_min: Optional[int] = None,
    employment_type: Optional[str] = None
) -> dict:
    logger.info(f"[Tool] ingest_jobs_from_adzuna: '{what}'")

    current_salary_min = salary_min
    if "high paying" in what.lower() and (salary_min is None or salary_min == 0):
        threshold = HIGH_PAYING_THRESHOLDS.get(country_code, DEFAULT_HIGH_PAYING_THRESHOLD)
        current_salary_min = threshold
    elif "high paying" in what.lower() and salary_min is not None:
        threshold = HIGH_PAYING_THRESHOLDS.get(country_code, DEFAULT_HIGH_PAYING_THRESHOLD)
        current_salary_min = max(salary_min, threshold)

    jobs = await _search_jobs_with_backoff(
        job_title=what,
        country_code=country_code,
        location=location,
        salary_min=current_salary_min,
        employment_type=employment_type,
        results_limit=50
    )

    if not jobs:
        return {"message": f"No roles found for '{what}' in {location or country_code.upper()}."}

    _ingest_jobs_data(jobs, country_code)
    return {"message": f"Successfully ingested {len(jobs)} jobs for '{what}'."}