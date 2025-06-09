import os
import logging
import requests
from typing import List, Dict, Any, Optional

# --- Local Imports ---
# Assumes your project structure allows these imports
from utils.env import load_env, get_model
from utils.firestore_helpers import upsert_jobs_bulk, query_similar_jobs
from google.adk.agents import Agent
from .prompt import CAREER_GUIDANCE_PROMPT

# --- Env & Logging Setup ---
load_env()
MODEL_INSTANCE = get_model()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Changed to INFO for production, DEBUG is very verbose
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(h)

print("--- career_guidance_agent module loaded (Firestore version) ---")

# --- Adzuna Config ---
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"
if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
    logger.warning("Missing Adzuna credentials; job searches will fail.")

# --- Adzuna Client ---
class AdzunaAPI:
    def __init__(self, app_id: str, app_key: str):
        if not app_id or not app_key:
            raise ValueError("Adzuna App ID and Key are required.")
        self.app_id = app_id
        self.app_key = app_key

    def _get(self, url: str, params: Dict[str, Any] = None) -> dict:
        # Default params including app_id and app_key
        default_params = {"app_id": self.app_id, "app_key": self.app_key}
        request_params = {**default_params, **(params or {})}
        try:
            r = requests.get(url, params=request_params, timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"[AdzunaAPI] Request failed: {e}", exc_info=True)
            return {"error": str(e)}

    def search_jobs(
        self,
        what: str,
        country: str = "gb",
        results: int = 10,
        salary_min: Optional[int] = None,
        location: Optional[str] = None,
        category: Optional[str] = None,
        what_or: Optional[str] = None
    ) -> dict:
        url = f"{ADZUNA_BASE_URL}/{country}/search/1"
        params = {"what": what, "results_per_page": results}
        if what_or:    params["what_or"] = what_or
        if salary_min: params["salary_min"] = salary_min
        if location:   params["where"] = location
        if category:   params["category"] = category
        return self._get(url, params)

adzuna_api = AdzunaAPI(ADZUNA_APP_ID, ADZUNA_APP_KEY)

# --- Helper Functions ---
def _format_salary(salary_data: Any, currency_symbol: str = "£") -> str:
    """Formats salary consistently from either a number or a Firestore map."""
    if isinstance(salary_data, (int, float)):
        return f"{currency_symbol}{salary_data:,.2f}"
    if isinstance(salary_data, dict):
        # Handle the structured salary from Firestore
        salary_min = salary_data.get('min')
        salary_max = salary_data.get('max')
        currency = salary_data.get('currency', 'GBP') # Default to GBP if not specified
        
        # Simple logic to display a range or single value
        if salary_max and salary_min:
            return f"{currency} {salary_min:,} - {salary_max:,}"
        elif salary_max:
            return f"{currency} {salary_max:,}"
        elif salary_min:
            return f"{currency} {salary_min:,}"
    return "Not listed"


# --- Agent Tools ---

def explore_career_fields_function(
    keywords: str,
    country_code: str = "gb",
    salary_min: Optional[int] = None
) -> dict:
    logger.info(f"[Tool] explore_career_fields('{keywords}', country='{country_code}')")
    
    terms = [t.strip() for t in keywords.split() if t.strip()]
    what = " ".join(terms)
    what_or = " OR ".join(terms) if len(terms) > 1 else None

    if "high paying" in keywords.lower():
        salary_min = max(salary_min or 0, 50000)

    jobs = adzuna_api.search_jobs(
        what=what, what_or=what_or, country=country_code, salary_min=salary_min
    ).get("results", [])

    if not jobs:
        return {"message": f"No roles found matching '{keywords}'. I can try a broader search if you like."}

    # NEW WORKFLOW: Upsert raw jobs to Firestore. This handles embedding and storage.
    upsert_jobs_bulk("job-postings", jobs, country_code=country_code)

    # Return unique job titles to the user
    titles = list(dict.fromkeys([j["title"].strip() for j in jobs if j.get("title")]))
    return {"suggested_job_titles": titles[:5]}
    

def get_job_role_descriptions_function(
    job_title: str,
    country_code: str = "gb",
    salary_min: Optional[int] = None
) -> dict:
    logger.info(f"[Tool] get_job_role_descriptions('{job_title}', salary_min={salary_min})")
    
    terms = [t.strip() for t in job_title.split() if t.strip()]
    what = " ".join(terms)
    
    current_salary_min = salary_min
    if "high paying" in job_title.lower():
        current_salary_min = max(current_salary_min or 0, 50000)
        
    jobs = adzuna_api.search_jobs(
        what=what, country=country_code, salary_min=current_salary_min
    ).get("results", [])
    
    if not jobs:
        return {"message": f"I couldn't find any current openings for '{job_title}'. Would you like me to search for related roles?"}

    # NEW WORKFLOW: Upsert results to Firestore to enrich our data
    upsert_jobs_bulk("job-postings", jobs, country_code=country_code)

    examples = []
    # 1. Format the fresh results from Adzuna
    for j in jobs[:10]:
        salary = j.get("salary_max") or j.get("salary_min")
        examples.append({
            "title": j["title"],
            "company": j.get("company", {}).get("display_name", "N/A"),
            "location": j.get("location", {}).get("display_name", "N/A"),
            "salary": _format_salary(salary),
            "description_snippet": j.get("description", "")[:400] + "...",
            "url": j.get("redirect_url")
        })
    
    # 2. Augment with similar jobs from our Firestore database (RAG)
    rag_results = query_similar_jobs(job_title, "job-postings", top_k=3)
    
    # Get existing titles to avoid showing duplicates
    existing_titles = {e["title"] for e in examples}
    for r in rag_results:
        if r.get("title") not in existing_titles:
            examples.append({
                "title": r.get("title", "N/A"),
                "company": r.get("company", {}).get("name", "RAG Result"),
                "location": r.get("location", {}).get("raw_text", "N/A"),
                "salary": _format_salary(r.get("salary")),
                "description_snippet": r.get("description_snippet", "") + "...",
                "url": r.get("url", "#")
            })
    
    return {"job_description_examples": examples}


def suggest_next_level_roles_function(current_title: str, country_code: str = "gb") -> dict:
    logger.info(f"[Tool] suggest_next_level_roles('{current_title}')")
    
    # Create a search query designed to find senior/lead roles
    search_query = f"senior {current_title} OR lead {current_title} OR {current_title} manager"
    
    jobs = adzuna_api.search_jobs(
        what=search_query,
        country=country_code,
        results=20 # Get a larger pool to find unique titles
    ).get("results", [])

    if not jobs:
        return {"message": f"I couldn't find any clear next-level roles for '{current_title}'. It might be a very specialized field."}

    # NEW WORKFLOW: Store these roles for future reference
    upsert_jobs_bulk("job-postings", jobs, country_code=country_code)

    # Filter out roles that are too similar to the current one and get unique titles
    next_level_titles = list(dict.fromkeys([
        j["title"] for j in jobs 
        if current_title.lower() not in j["title"].lower()
    ]))

    return {"next_level_roles": next_level_titles[:5]}


# --- Export Agent ---
career_guidance_agent = Agent(
    name="career_guidance_agent",
    model=MODEL_INSTANCE,
    description="A smart career coach that can explore job fields, find job descriptions, and suggest career advancements using real-time job data.",
    instruction=CAREER_GUIDANCE_PROMPT,
    tools=[
        explore_career_fields_function,
        get_job_role_descriptions_function,
        suggest_next_level_roles_function,
    ]
)