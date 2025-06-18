import logging
from typing import List, Dict, Any, Optional
import asyncio
from itertools import chain

from workmatch.utils.adzuna import get_adzuna_api, JobListing

logger = logging.getLogger(__name__)

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

async def get_job_listings_for_title(
    job_title: str,
    country_code: str,
    location: Optional[str],
    salary_min: Optional[int],
    employment_type: Optional[str]
) -> List[JobListing]:
    """
    Optimized function to fetch a small, clean list of jobs for a single title.
    """
    try:
        adzuna_api = get_adzuna_api()
        # Fetch a very small number of jobs to keep it fast
        response = adzuna_api.search_jobs(
            what=job_title,
            country=country_code,
            location=location,
            salary_min=salary_min,
            employment_type=employment_type,
            results_limit=3
        )
        return response.get("results", [])
    except Exception as e:
        logger.error(f"[Search] Error searching for '{job_title}': {e}", exc_info=True)
        return []

async def summarise_expanded_job_roles_tool(
    job_title: str,
    expanded_titles: List[str],
    country_code: str = "gb",
    location: Optional[str] = None,
    salary_min: Optional[int] = None,
    employment_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    A high-speed tool that fetches and synthesizes job data for multiple related titles.
    It relies on a distilled Adzuna client and returns a structured, backwards-compatible output.
    """
    country_code = country_code.lower()
    all_titles_to_search = [job_title] + expanded_titles
    logger.info(f"[Tool] Running high-speed search for {len(all_titles_to_search)} titles.")

    effective_salary = _apply_salary_threshold(job_title, salary_min, country_code)

    async def fetch_and_log(title: str):
        return await get_job_listings_for_title(
            job_title=title,
            country_code=country_code,
            location=location,
            salary_min=effective_salary,
            employment_type=employment_type
        )

    # Concurrently fetch clean, distilled job listings for all titles
    all_results = await asyncio.gather(*(fetch_and_log(title) for title in all_titles_to_search))

    # Map titles to their clean job listings
    listings_by_title = {
        title: listings
        for title, listings in zip(all_titles_to_search, all_results)
        if listings
    }

    # Combine all found listings into a single list
    all_combined_listings = list(chain.from_iterable(listings_by_title.values()))

    # Ensure a consistent limit for the final combined output
    final_listings_sample = all_combined_listings[:10]

    logger.info(f"[Tool] Completed search. Found {len(all_combined_listings)} total listings across {len(listings_by_title)} titles.")

    # Return the data in the exact same structure as before for backwards compatibility
    return {
        "job_title": job_title,
        "listings_by_title": listings_by_title,
        "all_listings": final_listings_sample,
        "total_titles_found": len(listings_by_title),
        "total_listings_found": len(all_combined_listings)
    }