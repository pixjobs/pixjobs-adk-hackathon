import logging
from typing import List, Dict, Any, Optional
import asyncio
from itertools import chain

from workmatch.utils.adzuna import get_adzuna_api
from workmatch.utils.firestore_helpers import upsert_jobs_metadata_bulk

logger = logging.getLogger(__name__)

COUNTRY_CURRENCY_MAP = {
    "gb": "GBP", "us": "USD", "de": "EUR", "fr": "EUR",
    "ca": "CAD", "au": "AUD", "in": "INR",
}
HIGH_PAYING_THRESHOLDS = {
    "gb": 60000, "us": 85000, "de": 65000, "fr": 60000,
    "ca": 80000, "au": 90000, "in": 1500000,
}
DEFAULT_HIGH_PAYING_THRESHOLD = 60000

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
    currency = salary_data.get("currency", "GBP")

    if not (salary_min or salary_max):
        return "Not listed"

    try:
        salary_min_val = round(float(salary_min)) if salary_min is not None else None
        salary_max_val = round(float(salary_max)) if salary_max is not None else None

        if salary_min_val and salary_max_val and salary_min_val != salary_max_val:
            range_str = f"{currency} {salary_min_val:,.0f} – {salary_max_val:,.0f}"
        else:
            value = salary_max_val or salary_min_val
            range_str = f"{currency} {value:,.0f}" if value else "Not listed"

        if salary_data.get("is_predicted") == "1":
            return f"{range_str} (est.)"

        return range_str

    except Exception:
        return "Not listed"

def _format_employment_type(job: Dict[str, Any]) -> str:
    contract_type = job.get("contract_type", "").capitalize()
    contract_time = job.get("contract_time", "").replace("_", " ").capitalize()
    if contract_type and contract_time:
        return f"{contract_type}, {contract_time}"
    return contract_type or contract_time or "N/A"

def _format_jobs_for_output(jobs: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, str]]:
    seen = set()
    output = []
    for job in jobs:
        key = job.get("redirect_url")
        if key and key in seen:
            continue
        seen.add(key)
        output.append({
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
        })
        if len(output) >= limit:
            break
    return output

def _ingest_jobs_data(jobs: List[Dict[str, Any]], country_code: str):
    if jobs:
        upsert_jobs_metadata_bulk("job-postings", jobs, country_code=country_code)

async def _search_jobs_with_backoff(
    job_title: str,
    country_code: str,
    location: Optional[str],
    salary_min: Optional[int],
    employment_type: Optional[str],
    results_limit: int = 25
) -> List[Dict[str, Any]]:
    try:
        what_query = " ".join(job_title.strip().split())
        logger.info(f"[Adzuna] Query → what: '{what_query}'")

        adzuna_api = get_adzuna_api()
        jobs = adzuna_api.search_jobs(
            what=what_query,
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

async def ingest_jobs_from_adzuna(
    what: str,
    country_code: str = "gb",
    location: Optional[str] = None,
    salary_min: Optional[int] = None,
    employment_type: Optional[str] = None
) -> dict:
    logger.info(f"[Tool] ingest_jobs_from_adzuna: '{what}'")

    country_code = country_code.lower()
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

async def get_job_role_descriptions_function(
    job_title: str,
    country_code: str = "gb",
    location: Optional[str] = None,
    salary_min: Optional[int] = None,
    employment_type: Optional[str] = None,
    expanded_titles: Optional[List[str]] = None
) -> dict:
    logger.info(f"[Tool] get_job_role_descriptions: '{job_title}'")

    country_code = country_code.lower()
    effective_salary = _apply_salary_threshold(job_title, salary_min, country_code)

    logger.debug(f"[Tool] Using country_code='{country_code}', effective_salary='{effective_salary}'")

    jobs = await _search_jobs_with_backoff(
        job_title=job_title,
        country_code=country_code,
        location=location,
        salary_min=effective_salary,
        employment_type=employment_type,
        results_limit=50
    )

    if jobs:
        logger.info(f"[Adzuna] Found {len(jobs)} results for '{job_title}'")
        _ingest_jobs_data(jobs, country_code)
        return {"result": jobs, "count": len(jobs), "source": "adzuna"}

    logger.warning(f"[Tool] No results found for '{job_title}'")
    return {"result": [], "count": 0, "source": "adzuna"}


async def summarise_expanded_job_roles_tool(
    job_title: str,
    expanded_titles: List[str],
    country_code: str = "gb",
    location: Optional[str] = None,
    salary_min: Optional[int] = None,
    employment_type: Optional[str] = None
) -> dict:
    country_code = country_code.lower()
    all_titles = [job_title] + expanded_titles

    logger.info(f"[Tool] Running summarise_expanded_job_roles_tool for {len(all_titles)} titles.")

    async def fetch_title_data(title: str):
        logger.info(f"[Tool] Fetching jobs for: '{title}'")
        res = await get_job_role_descriptions_function(
            job_title=title,
            country_code=country_code,
            location=location,
            salary_min=salary_min,
            employment_type=employment_type,
            expanded_titles=[]
        )
        logger.debug(f"[Tool] Got {res.get('count', 0)} results for '{title}'")
        return res

    results = await asyncio.gather(*(fetch_title_data(title) for title in all_titles))

    title_listing_map = {
        title: res["result"]
        for title, res in zip(all_titles, results)
        if res and res.get("result")
    }

    all_combined = list(chain.from_iterable(title_listing_map.values()))
    logger.info(f"[Tool] Total combined listings: {len(all_combined)}")

    formatted_combined = _format_jobs_for_output(all_combined, limit=10)

    return {
        "job_title": job_title,
        "listings_by_title": title_listing_map,
        "all_listings": formatted_combined,
        "total_titles": len(title_listing_map),
        "total_listings": len(all_combined)
    }
