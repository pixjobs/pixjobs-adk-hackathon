import ast
import logging
from typing import List, Dict, Any, Optional

from utils.adzuna import adzuna_api
from utils.env import get_model
from utils.firestore_helpers import (
    upsert_jobs_metadata_bulk, get_jobs_by_ids, compute_embedding
)
from utils.pinecone_helpers import (
    get_index, upsert_vectors, query_vectors
)

logger = logging.getLogger(__name__)

MODEL_INSTANCE = get_model()
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
    salary_min = salary_data.get('min')
    salary_max = salary_data.get('max')
    currency = salary_data.get('currency', 'N/A')
    if salary_max and salary_min and salary_max != salary_min:
        return f"{currency} {salary_min:,.0f} - {salary_max:,.0f}"
    value = salary_max or salary_min
    return f"{currency} {value:,.0f}" if value else "Not listed"


def _format_employment_type(job: Dict[str, Any]) -> str:
    contract_type = job.get('contract_type', '').capitalize()
    contract_time = job.get('contract_time', '').replace('_', ' ').capitalize()
    if contract_type and contract_time:
        return f"{contract_type}, {contract_time}"
    return contract_type or contract_time or "N/A"


def _ingest_jobs_data(jobs: List[Dict[str, Any]], country_code: str):
    if not jobs:
        return
    upsert_jobs_metadata_bulk("job-postings", jobs, country_code=country_code)
    vectors_to_upsert = []
    for job in jobs:
        doc_id = job.get('canonical_id')
        if not doc_id:
            continue
        embedding = compute_embedding(job.get("description", ""))
        if embedding:
            vectors_to_upsert.append((doc_id, embedding, {"title": job.get("title", "")}))
    if vectors_to_upsert:
        upsert_vectors(pinecone_job_index, vectors_to_upsert)


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

        # Use passed-in expanded titles if present
        variants = expanded_titles or []
        clean_variants = [v for v in variants if v.lower() != what_query.lower()]
        what_or_query = ", ".join(clean_variants[:3]) or what_query  # Cap for safety

        logger.info(f"[Search] Adzuna query: what='{what_query}' | what_or='{what_or_query}'")

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

        if jobs:
            return jobs

        logger.info("[Search] No results found. Fallback logic could go here if needed.")
        return []

    except Exception as e:
        logger.error(f"[Search] Error during job search: {e}")
        return []

async def get_job_role_descriptions_function(
    job_title: str,
    country_code: str = "gb",
    location: Optional[str] = None,
    salary_min: Optional[int] = None,
    employment_type: Optional[str] = None,
    expanded_titles: Optional[List[str]] = None
) -> dict:
    logger.info(f"[Tool] get_job_role_descriptions: {job_title}")

    current_salary_min = salary_min
    if "high paying" in job_title.lower():
        threshold = HIGH_PAYING_THRESHOLDS.get(country_code, DEFAULT_HIGH_PAYING_THRESHOLD)
        current_salary_min = max(salary_min or 0, threshold)

    jobs = await _search_jobs_with_backoff(
        job_title=job_title,
        expanded_titles=expanded_titles,  # ✅ <-- pass this
        country_code=country_code,
        location=location,
        salary_min=current_salary_min,
        employment_type=employment_type,
        results_limit=50
    )

    logger.info(f"[JobSearch] Running for title='{job_title}' with variants={expanded_titles}")

    if not jobs:
        return {"result": None, "message": f"No job matches found for '{job_title}'."}

    _ingest_jobs_data(jobs, country_code)
    return {"result": jobs[:10]}

async def ingest_jobs_from_adzuna(
    what: str,
    country_code: str = "gb",
    location: Optional[str] = None,
    salary_min: Optional[int] = None,
    employment_type: Optional[str] = None
) -> dict:
    logger.info(f"[Tool] ingest_jobs_from_adzuna: what={what}")

    current_salary_min = salary_min
    if "high paying" in what.lower():
        threshold = HIGH_PAYING_THRESHOLDS.get(country_code, DEFAULT_HIGH_PAYING_THRESHOLD)
        current_salary_min = max(salary_min or 0, threshold)

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
    return {"message": f"Successfully ingested {len(jobs)} jobs for '{what}'"}