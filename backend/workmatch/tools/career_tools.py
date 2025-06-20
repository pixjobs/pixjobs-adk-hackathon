import logging
import asyncio
import random
from itertools import chain
from typing import List, Dict, Any, Optional

from workmatch.utils.adzuna import get_adzuna_api, JobListing

logger = logging.getLogger(__name__)

async def get_job_listings_for_title(
    job_title: str,
    country_code: str,
    location: Optional[str],
    salary_min: Optional[int],
    employment_type: Optional[str],
    results_offset: Optional[int] = None,    # backwards-compatible offset
    freshness_days: Optional[int] = 3,       # Default freshness to 3 days
    employer: Optional[str] = None,
) -> List[JobListing]:
    """
    Optimized function to fetch a small, clean list of jobs for a single title.
    Supports both 'results_offset' (legacy) and 'page' (new).
    """
    try:
        adzuna_api = get_adzuna_api()

        # Determine results_limit and override freshness if filtering by employer
        if employer:
            freshness_days = None
            results_limit = 20
        else:
            results_limit = 10

        # Calculate page number from results_offset (legacy) or default to 1
        if results_offset is not None:
            page = (results_offset // results_limit) + 1
        else:
            page = 1

        response = adzuna_api.search_jobs(
            what=job_title,
            country=country_code,
            page=page,
            results_limit=results_limit,
            location=location,
            salary_min=salary_min,
            employment_type=employment_type,
            freshness_days=freshness_days,
            employer=employer,
        )
        listings = response.get("results", [])

        # Smart randomization: shuffle per-title if no specific employer
        if listings and not employer:
            random.shuffle(listings)

        return listings

    except Exception as e:
        logger.error(f"[Search] Error searching for '{job_title}': {e}", exc_info=True)
        return []

async def summarise_expanded_job_roles_tool(
    job_title: str,
    expanded_titles: List[str],
    country_code: str = "gb",
    location: Optional[str] = None,
    salary_min: Optional[int] = None,
    employment_type: Optional[str] = None,
    results_offset: Optional[int] = None,    # backwards-compatible offset
    freshness_days: Optional[int] = 3,       # Default to 3-day freshness
    employer: Optional[str] = None,
) -> Dict[str, Any]:
    """
    A high-speed tool that fetches and synthesizes job data for
    multiple related titles. Backwards-compatible via results_offset,
    uses path-based paging and smart randomization.
    """
    country_code = country_code.lower()
    all_titles = [job_title] + expanded_titles

    if employer:
        per_title_limit = 10
    else:
        per_title_limit = 5

    if results_offset is not None:
        page = (results_offset // per_title_limit) + 1
    else:
        page = 1

    logger.info(f"[Tool] Searching {len(all_titles)} titles "
                f"(page={page}, freshness_days={freshness_days})")

    async def fetch(title: str):
        return await get_job_listings_for_title(
            job_title=title,
            country_code=country_code,
            location=location,
            salary_min=salary_min,
            employment_type=employment_type,
            results_offset=results_offset,
            freshness_days=freshness_days,
            employer=employer,
        )

    # Optionally randomize the order of titles searched for extra variety
    titles_to_search = list(all_titles)
    if not employer:
        random.shuffle(titles_to_search)

    # Fetch concurrently
    all_results = await asyncio.gather(*(fetch(t) for t in titles_to_search))

    # Build mapping and combine
    listings_by_title = {
        title: results
        for title, results in zip(titles_to_search, all_results)
        if results
    }
    combined = list(chain.from_iterable(listings_by_title.values()))

    # Final shuffle of combined list if no employer filter
    if not employer:
        random.shuffle(combined)

    # Take first 10 as sample
    sample = combined[:10]

    logger.info(f"[Tool] Found {len(combined)} listings "
                f"across {len(listings_by_title)} titles.")

    return {
        "job_title": job_title,
        "listings_by_title": listings_by_title,
        "all_listings": sample,
        "total_titles_found": len(listings_by_title),
        "total_listings_found": len(combined),
        "page": page,
    }
