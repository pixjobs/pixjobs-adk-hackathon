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
            raise ValueError("Adzuna App ID and Key are required.")
        self.app_id = app_id
        self.app_key = app_key

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        default_params = {"app_id": self.app_id, "app_key": self.app_key}
        request_params = {**default_params, **(params or {})}
        try:
            r = requests.get(url, params=request_params, timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            print(f"[AdzunaAPI] Request error: {e}")
            return {"error": str(e), "results": []}
        except ValueError as e:
            print(f"[AdzunaAPI] JSON decode error: {e}")
            return {"error": f"Failed to decode JSON: {e}", "results": []}

    def _format_job_listing(self, job: Dict[str, Any]) -> JobListing:
        salary_min = job.get('salary_min')
        salary_max = job.get('salary_max')
        is_predicted = job.get('salary_is_predicted') == "1"
        salary_str = "Not listed"

        if salary_min and salary_max:
            salary_str = f"£{salary_min:,} - £{salary_max:,}"
        elif salary_min:
            salary_str = f"From £{salary_min:,}"

        if is_predicted and salary_str != "Not listed":
            salary_str += " (est.)"

        employment_type = "Permanent"
        ct = job.get('contract_time')
        if ct == 'contract':
            employment_type = "Contract"
        elif ct == 'part_time':
            employment_type = "Part-time"
        elif ct == 'full_time':
            employment_type = "Full-time"

        return {
            "id": job.get("id"),
            "title": job.get("title"),
            "company": job.get("company", {}).get("display_name", "N/A"),
            "location": job.get("location", {}).get("display_name", "N/A"),
            "employment_type": employment_type,
            "salary": salary_str,
            "description_snippet": job.get("description", "")[:150].strip() + "...",
            "url": job.get("redirect_url"),
        }

    def search_jobs(
        self,
        what: str,
        country: str = "gb",
        page: int = 1,                         # ← new
        results_limit: int = 5,
        salary_min: Optional[int] = None,
        location: Optional[str] = None,
        employment_type: Optional[str] = None,
        freshness_days: Optional[int] = None,
        employer: Optional[str] = None,        # ← filter by employer
    ) -> Dict[str, List[JobListing]]:
        """
        Searches for jobs and returns a dictionary containing a list of clean,
        distilled job listings ready for LLM consumption.
        """
        # interpolate `page` into the path
        url = f"{ADZUNA_BASE_URL}/{country}/search/{page}"
        api_params: Dict[str, Any] = {
            "what": what,
            "results_per_page": results_limit,
        }
        if salary_min:
            api_params["salary_min"] = salary_min
        if location:
            api_params["where"] = location
        if employment_type in {"full_time", "part_time", "contract", "permanent"}:
            api_params[employment_type] = 1
        if freshness_days is not None:
            api_params["max_days_old"] = freshness_days
        if employer:
            api_params["company"] = employer

        response = self._get(url, api_params)
        raw_results = response.get("results", [])
        distilled_results = [self._format_job_listing(job) for job in raw_results]

        return {"results": distilled_results}

def get_adzuna_api() -> AdzunaAPI:
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    return AdzunaAPI(app_id, app_key)
