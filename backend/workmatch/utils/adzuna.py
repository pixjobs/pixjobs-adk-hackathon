import os
import requests
from typing import Optional, List, Dict, Any

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

    def search_jobs(
        self,
        what: str,
        country: str = "gb",
        results_limit: int = 25,
        salary_min: Optional[int] = None,
        location: Optional[str] = None,
        category: Optional[str] = None,
        employment_type: Optional[str] = None,
        max_pages: int = 3
    ) -> Dict[str, Any]:
        all_results: List[Dict[str, Any]] = []
        seen_ids = set()
        results_per_page = 10
        page = 1

        while len(all_results) < results_limit and page <= max_pages:
            url = f"{ADZUNA_BASE_URL}/{country}/search/{page}"
            api_params: Dict[str, Any] = {
                "what": what,
                "results_per_page": results_per_page,
            }

            if salary_min:
                api_params["salary_min"] = salary_min
            if location:
                api_params["where"] = location
            if category:
                api_params["category"] = category
            if employment_type:
                valid_types = {"full_time", "part_time", "contract", "permanent"}
                if employment_type in valid_types:
                    api_params[employment_type] = 1
                else:
                    print(f"[AdzunaAPI] Warning: Invalid employment_type '{employment_type}'")

            response = self._get(url, api_params)

            if "error" in response and response.get("error"):
                print(f"[AdzunaAPI] Error on page {page}: {response['error']}")
                if not response.get("results"):
                    break

            page_results = response.get("results", [])
            if not page_results:
                break

            for job in page_results:
                if len(all_results) >= results_limit:
                    break
                job_id = job.get("canonical_id") or job.get("id")
                if job_id and job_id not in seen_ids:
                    all_results.append(job)
                    seen_ids.add(job_id)

            page += 1

        return {"results": all_results[:results_limit]}

def get_adzuna_api() -> AdzunaAPI:
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    return AdzunaAPI(app_id, app_key)
