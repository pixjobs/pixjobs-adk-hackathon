import os
import requests
from typing import Optional
from utils.env import load_env

load_env()
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"

class AdzunaAPI:
    def __init__(self, app_id: str, app_key: str):
        if not app_id or not app_key:
            raise ValueError("Adzuna App ID and Key are required.")
        self.app_id = app_id
        self.app_key = app_key

    def _get(self, url: str, params: dict = None) -> dict:
        default_params = {"app_id": self.app_id, "app_key": self.app_key}
        request_params = {**default_params, **(params or {})}
        try:
            r = requests.get(url, params=request_params, timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def search_jobs(
        self, what: str, country: str = "gb", results: int = 10,
        salary_min: Optional[int] = None, location: Optional[str] = None,
        category: Optional[str] = None, what_or: Optional[str] = None,
        employment_type: Optional[str] = None
    ) -> dict:
        url = f"{ADZUNA_BASE_URL}/{country}/search/1"
        params = {"what": what, "results_per_page": results}
        if what_or:    params["what_or"] = what_or
        if salary_min: params["salary_min"] = salary_min
        if location:   params["where"] = location
        if category:   params["category"] = category
        if employment_type in ['permanent', 'contract']:
            params["contract_type"] = employment_type
        return self._get(url, params)

adzuna_api = AdzunaAPI(ADZUNA_APP_ID, ADZUNA_APP_KEY)
