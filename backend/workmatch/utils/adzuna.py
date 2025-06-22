import os
import requests
from typing import Optional, List, Dict, Any, TypedDict


class JobListing(TypedDict):
    id: str
    title: str
    company: str
    location: str
    employment_type: str
    salary: str
    description_snippet: str
    url: str


ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"


class AdzunaAPI:
    def __init__(self, app_id: str, app_key: str):
        if not app_id or not app_key:
            raise ValueError("Adzuna App ID and App Key are required.")
        self.app_id = app_id
        self.app_key = app_key

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Internal GET request with error handling and timeout."""
        default_params = {"app_id": self.app_id, "app_key": self.app_key}
        try:
            response = requests.get(url, params={**default_params, **(params or {})}, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[AdzunaAPI] Request error: {e}")
            return {"results": []}

    def _format_job_listing(self, job: Dict[str, Any]) -> JobListing:
        """Extract and clean up job details into a compact, LLM-ready object."""
        # Salary formatting
        s_min = job.get("salary_min")
        s_max = job.get("salary_max")
        salary = "Not listed"
        if s_min and s_max:
            salary = f"£{int(s_min):,} - £{int(s_max):,}"
        elif s_min:
            salary = f"From £{int(s_min):,}"
        if job.get("salary_is_predicted") == "1" and salary != "Not listed":
            salary += " (est.)"

        # Employment type
        contract_map = {
            "full_time": "Full-time",
            "part_time": "Part-time",
            "contract": "Contract"
        }
        employment_type = contract_map.get(job.get("contract_time"), "Permanent")

        # Description snippet (~20 words)
        desc_words = (job.get("description") or "").strip().split()
        snippet = " ".join(desc_words[:20]) + ("..." if len(desc_words) > 20 else "")

        return {
            "id": job.get("id", ""),
            "title": job.get("title", ""),
            "company": job.get("company", {}).get("display_name", "N/A"),
            "location": job.get("location", {}).get("display_name", "N/A"),
            "employment_type": employment_type,
            "salary": salary,
            "description_snippet": snippet,
            "url": job.get("redirect_url", ""),
        }

    def search_jobs(
        self,
        what: str,
        country: str = "gb",
        page: int = 1,
        results_limit: int = 5,
        salary_min: Optional[int] = None,
        location: Optional[str] = None,
        employment_type: Optional[str] = None,
        freshness_days: Optional[int] = None,
        employer: Optional[str] = None,
    ) -> Dict[str, List[JobListing]]:
        """
        Fetches up to `results_limit` jobs matching the criteria and returns formatted listings.
        """
        url = f"{ADZUNA_BASE_URL}/{country}/search/{page}"
        params: Dict[str, Any] = {
            "what": what,
            "results_per_page": results_limit
        }
        if salary_min:
            params["salary_min"] = salary_min
        if location:
            params["where"] = location
        if freshness_days:
            params["max_days_old"] = freshness_days
        if employer:
            params["company"] = employer
        if employment_type in {"full_time", "part_time", "contract", "permanent"}:
            params[employment_type] = 1

        raw_results = self._get(url, params).get("results", [])
        return {
            "results": [
                self._format_job_listing(job)
                for job in raw_results[:results_limit]
            ]
        }


def get_adzuna_api() -> AdzunaAPI:
    """Helper to instantiate API with env vars."""
    return AdzunaAPI(
        os.getenv("ADZUNA_APP_ID"),
        os.getenv("ADZUNA_APP_KEY")
    )
