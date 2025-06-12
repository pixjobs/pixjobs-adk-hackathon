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
    what_or: Optional[str] = None
) -> List[Dict[str, Any]]:
    what_query = " ".join(job_title.split())
    what_or_query = what_or or what_query

    jobs = adzuna_api.search_jobs(
        what=what_query,
        what_or=what_or_query,
        country=country_code,
        location=location,
        salary_min=salary_min,
        employment_type=employment_type
    ).get("results", [])

    if not jobs:
        logger.info(f"Retrying with fallback job_title only: {what_query}")
        jobs = adzuna_api.search_jobs(
            what=what_query,
            country=country_code
        ).get("results", [])

    return jobs


async def get_job_role_descriptions_function(
    job_title: str,
    country_code: str = "gb",
    location: Optional[str] = None,
    salary_min: Optional[int] = None,
    employment_type: Optional[str] = None
) -> dict:
    logger.info(f"[Tool] get_job_role_descriptions: {job_title}")
    
    current_salary_min = salary_min
    if "high paying" in job_title.lower():
        threshold = HIGH_PAYING_THRESHOLDS.get(country_code, DEFAULT_HIGH_PAYING_THRESHOLD)
        current_salary_min = max(salary_min or 0, threshold)

    job_title_query = job_title.replace("/", " ").replace("|", ",")
    
    jobs = await _search_jobs_with_backoff(
        job_title=job_title,
        what_or=job_title_query,
        country_code=country_code,
        location=location,
        salary_min=current_salary_min,
        employment_type=employment_type,
    )

    if not jobs:
        logger.warning(f"No results for job title: {job_title_query}")
        return {"message": f"I couldn't find any current openings for '{job_title}' or similar roles."}
    
    _ingest_jobs_data(jobs, country_code)

    examples = []
    for job in jobs[:5]:
        desc = job.get("description") or ""
        if not desc:
            continue
        examples.append({
            "title": job.get("title"),
            "company": job.get("company", {}).get("display_name", "Unknown"),
            "location": job.get("location", {}).get("display_name"),
            "description": desc.strip(),
            "url": job.get("redirect_url"),
        })

    if not examples:
        return {"message": f"I found some results for '{job_title}', but couldn't extract any descriptions."}

    return {"job_description_examples": examples}


async def explore_career_fields_function(
    keywords: str,
    country_code: str = "gb",
    location: Optional[str] = None,
    salary_min: Optional[int] = None,
    employment_type: Optional[str] = None
) -> dict:
    logger.info(f"[Tool] explore_career_fields: keywords='{keywords}'")

    current_salary_min = salary_min
    if "high paying" in keywords.lower():
        threshold = HIGH_PAYING_THRESHOLDS.get(country_code, DEFAULT_HIGH_PAYING_THRESHOLD)
        current_salary_min = max(salary_min or 0, threshold)

    jobs = await _search_jobs_with_backoff(
        job_title=keywords,
        what_or=keywords,
        country_code=country_code,
        location=location,
        salary_min=current_salary_min,
        employment_type=employment_type,
    )

    if not jobs:
        return {"message": f"No roles found matching '{keywords}'."}
    
    _ingest_jobs_data(jobs, country_code)

    titles = list(dict.fromkeys([j["title"].strip() for j in jobs if j.get("title")]))
    return {"suggested_job_titles": titles[:5]}


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
        what_or=what,
        country_code=country_code,
        location=location,
        salary_min=current_salary_min,
        employment_type=employment_type,
    )

    if not jobs:
        return {"message": f"No roles found for '{what}' in {location or country_code.upper()}."}

    _ingest_jobs_data(jobs, country_code)
    return {"message": f"Successfully ingested {len(jobs)} jobs for '{what}'"}
