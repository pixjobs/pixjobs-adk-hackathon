import os
import logging
from typing import List, Dict, Any
import requests

# ✅ Ensure environment is loaded before anything else
from utils.env import load_env, get_model
load_env()

from google.adk.agents import Agent
from .prompt import CAREER_GUIDANCE_PROMPT

print("--- agent.py module is being loaded ---")

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# --- Load Adzuna credentials ---
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"

if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
    logger.critical("[startup] Missing ADZUNA_APP_ID or ADZUNA_APP_KEY in env.")
else:
    logger.info("[startup] Adzuna credentials loaded successfully.")

MODEL_INSTANCE = get_model()
logger.info(f"--- Agent is using Gemini model: {MODEL_INSTANCE} ---")

# --- AdzunaAPI Client ---
class AdzunaAPI:
    def __init__(self, app_id: str, app_key: str):
        if not app_id or not app_key:
            raise ValueError("Adzuna App ID and Key are required.")
        self.app_id = app_id
        self.app_key = app_key

    def _make_get_request(self, url, params=None):
        if params is None:
            params = {}
        params.update({"app_id": self.app_id, "app_key": self.app_key})
        try:
            logger.debug(f"[AdzunaAPI] GET {url} with params {params}")
            response = requests.get(url, params=params, timeout=10)
            logger.debug(f"[AdzunaAPI] Full URL: {response.url}")
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as http_err:
            logger.error(f"[AdzunaAPI] HTTP error: {http_err.response.status_code} - {http_err.response.text}", exc_info=True)
            return {"error": f"HTTP {http_err.response.status_code}: {http_err.response.text}"}
        except requests.RequestException as e:
            logger.error(f"[AdzunaAPI] Failed to fetch job data: {e}", exc_info=True)
            return {"error": str(e)}

    def search_jobs(
        self,
        what: str,
        country: str = "gb",
        results: int = 10,
        salary_min: int = None,
        location: str = None,
        category: str = None,
        what_or: str = None
    ) -> dict:
        url = f"{ADZUNA_BASE_URL}/{country}/search/1"
        params = {
            "what": what,
            "results_per_page": results
        }
        if what_or:
            params["what_or"] = what_or
        if salary_min:
            params["salary_min"] = salary_min
        if location:
            params["where"] = location
        if category:
            params["category"] = category
        return self._make_get_request(url, params)

    def get_categories(self, country="gb") -> dict:
        url = f"{ADZUNA_BASE_URL}/{country}/categories"
        return self._make_get_request(url)

    def get_salary_histogram(self, what: str, country="gb", location: str = None) -> dict:
        url = f"{ADZUNA_BASE_URL}/{country}/histogram"
        params = {"what": what}
        if location:
            params["location0"] = location
        return self._make_get_request(url, params)

    def get_top_companies(self, what: str, country="gb") -> dict:
        url = f"{ADZUNA_BASE_URL}/{country}/top_companies"
        params = {"what": what}
        return self._make_get_request(url, params)

adzuna_api = AdzunaAPI(app_id=ADZUNA_APP_ID, app_key=ADZUNA_APP_KEY)

# --- Tool: Explore Career Fields ---
def explore_career_fields_function(keywords: str, country_code: str = "gb") -> dict:
    logger.debug(f"--- Tool Call: explore_career_fields_function('{keywords}', '{country_code}') ---")
    salary_filter = 50000 if "high paying" in keywords.lower() else None
    keyword_list = [k.strip() for k in keywords.split() if k.strip()]
    what = " ".join(keyword_list)
    what_or = " OR ".join(keyword_list) if len(keyword_list) > 1 else None

    response = adzuna_api.search_jobs(
        what=what,
        what_or=what_or,
        country=country_code,
        salary_min=salary_filter
    )
    if "error" in response:
        return {"error": response["error"]}

    jobs = response.get("results", [])
    if not jobs:
        return {"message": "No roles found for that query."}

    titles = list({job.get("title") for job in jobs if job.get("title")})
    return {"suggested_job_titles": titles[:5]}


# --- Tool: Get Job Role Descriptions ---
def get_job_role_descriptions_function(job_title: str, country_code: str = "gb") -> dict:
    logger.debug(f"--- Tool Call: get_job_role_descriptions_function('{job_title}', '{country_code}') ---")
    salary_filter = 50000 if "high paying" in job_title.lower() else None
    keyword_list = [k.strip() for k in job_title.split() if k.strip()]
    what = " ".join(keyword_list)
    what_or = " OR ".join(keyword_list) if len(keyword_list) > 1 else None

    response = adzuna_api.search_jobs(
        what=what,
        what_or=what_or,
        country=country_code,
        salary_min=salary_filter
    )
    if "error" in response:
        return {"error": response["error"]}

    jobs = response.get("results", [])
    if not jobs:
        return {"message": f"No current openings found for '{job_title}'."}

    examples = []
    for job in jobs[:10]:
        salary = job.get("salary_max") or job.get("salary_min") or "Not listed"
        examples.append({
            "title": job.get("title"),
            "company": job.get("company", {}).get("display_name", "Unknown"),
            "location": job.get("location", {}).get("display_name", "N/A"),
            "salary": f"£{salary:,.2f}" if isinstance(salary, (int, float)) else salary,
            "description_snippet": job.get("description", "")[:400],
            "url": job.get("redirect_url")
        })
    return {"job_description_examples": examples}


# --- Tool: Discover Next Level Roles ---
def suggest_next_level_roles_function(current_title: str, country_code: str = "gb") -> dict:
    logger.debug(f"--- Tool Call: suggest_next_level_roles_function('{current_title}', '{country_code}') ---")
    next_keywords = f"{current_title} lead manager head senior"
    keyword_list = [k.strip() for k in next_keywords.split() if k.strip()]
    what = " ".join(keyword_list)
    what_or = " OR ".join(keyword_list) if len(keyword_list) > 1 else None

    response = adzuna_api.search_jobs(
        what=what,
        what_or=what_or,
        country=country_code
    )
    if "error" in response:
        return {"error": response["error"]}

    jobs = response.get("results", [])
    next_roles = list({
        job.get("title")
        for job in jobs
        if job.get("title") and current_title.lower() not in job.get("title").lower()
    })
    return {
        "next_level_roles": next_roles[:5] or ["No obvious next-level roles found."]
    }


# --- ADK Agent ---
career_guidance_agent = Agent(
    name="career_guidance_agent",
    model=MODEL_INSTANCE,
    description="Helps users explore career options, understand specific roles, and discover next-level jobs.",
    instruction=CAREER_GUIDANCE_PROMPT,
    tools=[
        explore_career_fields_function,
        get_job_role_descriptions_function,
        suggest_next_level_roles_function,
    ]
)