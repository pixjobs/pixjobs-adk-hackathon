import os
import logging
import requests
import asyncio # Import asyncio to use its features
from typing import List, Dict, Any, Optional

# --- Local Imports ---
from utils.env import load_env, get_model
from utils.firestore_helpers import (
    upsert_jobs_metadata_bulk,
    get_jobs_by_ids,
    compute_embedding
)
from utils.pinecone_helpers import (
    get_index,
    upsert_vectors,
    query_vectors
)
from google.adk.agents import Agent
from .prompt import CAREER_GUIDANCE_PROMPT

# --- Module-level Setup ---
load_env()
MODEL_INSTANCE = get_model()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(h)

print("--- career_guidance_agent module loaded (v4: Async-aware) ---")

# --- Adzuna API Client (No changes needed) ---
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"

class AdzunaAPI:
    # ... (class implementation remains the same)
    def __init__(self, app_id: str, app_key: str):
        if not app_id or not app_key:
            raise ValueError("Adzuna App ID and Key are required.")
        self.app_id = app_id
        self.app_key = app_key

    def _get(self, url: str, params: Dict[str, Any] = None) -> dict:
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

# --- Pinecone & Configuration (No changes needed) ---
pinecone_job_index = get_index("job-postings")
HIGH_PAYING_THRESHOLDS = {
    "gb": 50000, "us": 85000, "de": 65000, "fr": 60000,
    "ca": 80000, "au": 90000, "in": 1500000,
}
DEFAULT_HIGH_PAYING_THRESHOLD = 50000
COUNTRY_CURRENCY_MAP = {
    "gb": "GBP", "us": "USD", "de": "EUR", "fr": "EUR",
    "ca": "CAD", "au": "AUD", "in": "INR",
}

# --- Helper Functions (No changes needed, but _expand_job_title is now called with await) ---
def _format_salary(salary_data: Any) -> str:
    if not isinstance(salary_data, dict): return "Not listed"
    salary_min, salary_max, currency = salary_data.get('min'), salary_data.get('max'), salary_data.get('currency', 'N/A')
    if salary_max and salary_min and salary_max != salary_min: return f"{currency} {salary_min:,.0f} - {salary_max:,.0f}"
    value = salary_max or salary_min
    return f"{currency} {value:,.0f}" if value else "Not listed"

def _format_employment_type(job: Dict[str, Any]) -> str:
    contract_type = job.get('contract_type', '').capitalize()
    contract_time = job.get('contract_time', '').replace('_', ' ').capitalize()
    if contract_type and contract_time: return f"{contract_type}, {contract_time}"
    return contract_type or contract_time or "N/A"

async def _expand_job_title(job_title: str) -> str:
    logger.info(f"Expanding job title: '{job_title}'")
    try:
        prompt = f"List up to 4 alternative or synonymous job titles for '{job_title}'. Do not use the original title. Return only a comma-separated list. Example: UI Engineer, Web Developer, Frontend Engineer"
        response = await MODEL_INSTANCE.generate_content_async(prompt)
        synonyms = [s.strip() for s in response.text.split(',') if s.strip()]
        return " OR ".join(synonyms)
    except Exception as e:
        logger.error(f"Failed to expand job title with LLM: {e}")
        return ""

def _ingest_jobs_data(jobs: List[Dict[str, Any]], country_code: str):
    if not jobs: return
    upsert_jobs_metadata_bulk("job-postings", jobs, country_code=country_code)
    vectors_to_upsert = []
    for job in jobs:
        doc_id = job.get('canonical_id')
        if not doc_id: continue
        embedding = compute_embedding(job.get("description", ""))
        if embedding:
            vectors_to_upsert.append((doc_id, embedding, {"title": job.get("title", "")}))
    upsert_vectors(pinecone_job_index, vectors_to_upsert)

# --- Agent Tools ---

# CORRECTED: All tool functions are now `async def`
async def explore_career_fields_function(
    keywords: str, country_code: str = "gb",
    location: Optional[str] = None, salary_min: Optional[int] = None,
    employment_type: Optional[str] = None
) -> dict:
    logger.info(f"[Tool] explore_career_fields('{keywords}', type='{employment_type}')")
    
    terms = [t.strip() for t in keywords.split() if t.strip()]
    what = " ".join(terms)
    what_or = " OR ".join(terms) if len(terms) > 1 else None

    current_salary_min = salary_min
    if "high paying" in keywords.lower():
        threshold = HIGH_PAYING_THRESHOLDS.get(country_code, DEFAULT_HIGH_PAYING_THRESHOLD)
        current_salary_min = max(current_salary_min or 0, threshold)

    jobs = adzuna_api.search_jobs(
        what=what, what_or=what_or, country=country_code, location=location,
        salary_min=current_salary_min, employment_type=employment_type
    ).get("results", [])

    if not jobs:
        return {"message": f"No roles found matching '{keywords}'. I can try a broader search if you like."}

    _ingest_jobs_data(jobs, country_code)
    titles = list(dict.fromkeys([j["title"].strip() for j in jobs if j.get("title")]))
    return {"suggested_job_titles": titles[:5]}

async def get_job_role_descriptions_function(
    job_title: str, country_code: str = "gb",
    location: Optional[str] = None, salary_min: Optional[int] = None,
    employment_type: Optional[str] = None
) -> dict:
    logger.info(f"[Tool] get_job_role_descriptions('{job_title}', type='{employment_type}')")
    
    # CORRECTED: Use `await` instead of `asyncio.run()`
    what_or_query = await _expand_job_title(job_title)
    what_query = " ".join([t.strip() for t in job_title.split() if t.strip()])
    
    current_salary_min = salary_min
    if "high paying" in job_title.lower():
        threshold = HIGH_PAYING_THRESHOLDS.get(country_code, DEFAULT_HIGH_PAYING_THRESHOLD)
        current_salary_min = max(current_salary_min or 0, threshold)
        
    jobs = adzuna_api.search_jobs(
        what=what_query, what_or=what_or_query, country=country_code, location=location,
        salary_min=current_salary_min, employment_type=employment_type
    ).get("results", [])
    
    if not jobs:
        return {"message": f"I couldn't find any current openings for '{job_title}' or similar roles."}

    _ingest_jobs_data(jobs, country_code)

    examples = []
    for j in jobs[:10]:
        salary_map = {"min": j.get("salary_min"), "max": j.get("salary_max"), "currency": COUNTRY_CURRENCY_MAP.get(country_code, "N/A")}
        examples.append({
            "title": j["title"],
            "company": j.get("company", {}).get("display_name", "N/A"),
            "location": j.get("location", {}).get("display_name", "N/A"),
            "type": _format_employment_type(j),
            "salary": _format_salary(salary_map),
            "description_snippet": j.get("description", "")[:400] + "...",
            "url": j.get("redirect_url")
        })
    
    query_embedding = compute_embedding(job_title)
    if query_embedding:
        matches = query_vectors(pinecone_job_index, query_embedding, top_k=3)
        rag_ids = [match['id'] for match in matches]
        if rag_ids:
            rag_results = get_jobs_by_ids("job-postings", rag_ids)
            existing_titles = {e["title"] for e in examples}
            for r in rag_results:
                if r.get("title") not in existing_titles:
                    examples.append({
                        "title": r.get("title", "N/A"),
                        "company": r.get("company", {}).get("name", "RAG Result"),
                        "location": r.get("location", {}).get("raw_text", "N/A"),
                        "type": _format_employment_type(r),
                        "salary": _format_salary(r.get("salary")),
                        "description_snippet": r.get("description_snippet", "") + "...",
                        "url": r.get("url", "#")
                    })
    
    return {"job_description_examples": examples}

async def suggest_next_level_roles_function(
    current_title: str, country_code: str = "gb", location: Optional[str] = None,
    employment_type: Optional[str] = None
) -> dict:
    logger.info(f"[Tool] suggest_next_level_roles('{current_title}', type='{employment_type}')")
    
    search_query = f"senior {current_title} OR lead {current_title} OR {current_title} manager"
    
    jobs = adzuna_api.search_jobs(
        what=search_query, country=country_code, location=location,
        results=20, employment_type=employment_type
    ).get("results", [])

    if not jobs:
        return {"message": f"I couldn't find any clear next-level roles for '{current_title}'."}

    _ingest_jobs_data(jobs, country_code)
    next_level_titles = list(dict.fromkeys([
        j["title"] for j in jobs if current_title.lower() not in j.get("title", "").lower()
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