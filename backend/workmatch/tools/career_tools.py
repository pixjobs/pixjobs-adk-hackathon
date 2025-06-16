import logging
from typing import List, Dict, Any, Optional

from workmatch.utils.adzuna import adzuna_api
from workmatch.utils.firestore_helpers import upsert_jobs_metadata_bulk

logger = logging.getLogger(__name__)

COUNTRY_CURRENCY_MAP = {
    "gb": "GBP", "us": "USD", "de": "EUR", "fr": "EUR",
    "ca": "CAD", "au": "AUD", "in": "INR",
}
HIGH_PAYING_THRESHOLDS = {
    "gb": 50000, "us": 85000, "de": 65000, "fr": 60000,
    "ca": 80000, "au": 90000, "in": 1500000,
}
DEFAULT_HIGH_PAYING_THRESHOLD = 50000


def _apply_salary_threshold(label: str, base: Optional[int], country_code: str) -> Optional[int]:
    if "high paying" in label.lower():
        threshold = HIGH_PAYING_THRESHOLDS.get(country_code, DEFAULT_HIGH_PAYING_THRESHOLD)
        return max(base or 0, threshold)
    return base


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


def _format_jobs_for_output(jobs: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    return [
        {
            "title": job.get("title"),
            "company": job.get("company", {}).get("display_name"),
            "location": job.get("location", {}).get("display_name"),
            "salary": _format_salary(job.get("salary")),
            "employment_type": _format_employment_type(job),
            "url": job.get("redirect_url"),
            "description_snippet": (
                job.get("description", "")[:200] + "..."
                if len(job.get("description", "")) > 200
                else job.get("description", "")
            )
        }
        for job in jobs[:5]
    ]


def _ingest_jobs_data(jobs: List[Dict[str, Any]], country_code: str):
    if jobs:
        upsert_jobs_metadata_bulk("job-postings", jobs, country_code=country_code)


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
        what_or_query = ", ".join(clean_variants[:3]) or what_query

        logger.info(f"[Adzuna] Query → what: '{what_query}' | OR: '{what_or_query}'")

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
        logger.error(f"[Search] Error during job search: {e}", exc_info=True)
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

    effective_salary = _apply_salary_threshold(job_title, salary_min, country_code)

    jobs = await _search_jobs_with_backoff(
        job_title=job_title,
        expanded_titles=expanded_titles,
        country_code=country_code,
        location=location,
        salary_min=effective_salary,
        employment_type=employment_type,
        results_limit=50
    )

    if jobs:
        logger.info(f"[Adzuna] Found {len(jobs)} results.")
        _ingest_jobs_data(jobs, country_code)
        return {
            "result": _format_jobs_for_output(jobs),
            "count": min(len(jobs), 5),
            "source": "adzuna"
        }

    logger.warning(f"[Tool] No results found for '{job_title}'.")
    return {"result": None, "message": f"No job matches found for '{job_title}'."}


async def ingest_jobs_from_adzuna(
    what: str,
    country_code: str = "gb",
    location: Optional[str] = None,
    salary_min: Optional[int] = None,
    employment_type: Optional[str] = None
) -> dict:
    logger.info(f"[Tool] ingest_jobs_from_adzuna: '{what}'")

    effective_salary = _apply_salary_threshold(what, salary_min, country_code)

    jobs = await _search_jobs_with_backoff(
        job_title=what,
        country_code=country_code,
        location=location,
        salary_min=effective_salary,
        employment_type=employment_type,
        results_limit=50
    )

    if not jobs:
        return {"message": f"No roles found for '{what}' in {location or country_code.upper()}."}

    _ingest_jobs_data(jobs, country_code)
    return {"message": f"Successfully ingested {len(jobs)} jobs for '{what}'."}

async def summarise_expanded_job_roles_tool(
    job_title: str,
    expanded_titles: List[str],
    country_code: str = "gb",
    location: Optional[str] = None,
    salary_min: Optional[int] = None,
    employment_type: Optional[str] = None
) -> dict:
    """
    Fetches real job listings for a title + its variants.
    Returns a structured map of job listings by title (no LLM summarisation).
    """
    title_listing_map: Dict[str, List[Dict[str, Any]]] = {}

    all_titles = [job_title] + expanded_titles
    for title in all_titles:
        result = await get_job_role_descriptions_function(
            job_title=title,
            country_code=country_code,
            location=location,
            salary_min=salary_min,
            employment_type=employment_type,
            expanded_titles=[]  # Prevent recursion
        )
        if result and result.get("result"):
            title_listing_map[title] = result["result"]

    return {
        "job_title": job_title,
        "listings_by_title": title_listing_map,
        "total_titles": len(title_listing_map)
    }