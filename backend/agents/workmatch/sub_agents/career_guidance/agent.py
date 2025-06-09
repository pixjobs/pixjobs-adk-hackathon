import os
import logging
import requests
from typing import List, Dict, Any, Optional

from utils.env import load_env, get_model
from utils.firestore_helpers import upsert_jobs_bulk, query_similar_jobs, compute_embedding, hash_string
from utils.pinecone_helpers import get_pinecone_client, ensure_pinecone_index, get_index, upsert_vectors
from google.adk.agents import Agent
from .prompt import CAREER_GUIDANCE_PROMPT

# --- Env & Logging Setup ---
load_env()
MODEL_INSTANCE = get_model()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(h)

print("--- career_guidance_agent module loaded ---")

# --- Adzuna Config ---
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"
if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
    logger.warning("Missing Adzuna credentials; searches may fail.")

# --- Pinecone Init & Indexes ---
pc = get_pinecone_client()
for idx_name in ("career-queries", "career-roles", "job-postings"):
    ensure_pinecone_index(idx_name)

# --- Adzuna Client ---
class AdzunaAPI:
    def __init__(self, app_id: str, app_key: str):
        if not app_id or not app_key:
            raise ValueError("Adzuna App ID and Key required.")
        self.app_id = app_id
        self.app_key = app_key

    def _get(self, url: str, params: Dict[str, Any] = None) -> dict:
        params = {**(params or {}), "app_id": self.app_id, "app_key": self.app_key}
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"[AdzunaAPI] {e}", exc_info=True)
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
        params = {"what": what, "results_per_page": results}
        if what_or:    params["what_or"] = what_or
        if salary_min: params["salary_min"] = salary_min
        if location:   params["where"] = location
        if category:   params["category"] = category
        return self._get(url, params)

adzuna_api = AdzunaAPI(ADZUNA_APP_ID, ADZUNA_APP_KEY)

# --- Tool: Explore Career Fields ---
def explore_career_fields_function(
    keywords: str,
    country_code: str = "gb",
    salary_min: Optional[int] = None
) -> dict:
    logger.info(f"[Tool] explore_career_fields('{keywords}', country_code='{country_code}', salary_min={salary_min})")
    
    terms = [t.strip() for t in keywords.split() if t.strip()]
    what = " ".join(terms)
    what_or = " OR ".join(terms) if len(terms) > 1 else None

    if "high paying" in keywords.lower():
        salary_min = max(salary_min or 0, 50000)

    jobs = adzuna_api.search_jobs(
        what=what,
        what_or=what_or,
        country=country_code,
        salary_min=salary_min
    ).get("results", [])

    if not jobs:
        return {"message": "No roles found."}

    upsert_jobs_bulk("job-postings", jobs)

    idx = get_index("career-queries")
    vectors = []
    for j in jobs:
        content = j.get("description", "")[:400]
        vec = compute_embedding(content)
        doc_id = hash_string(j.get("title", "") + j.get("company", {}).get("display_name", ""))
        vectors.append((doc_id, vec, {"title": j.get("title")}))
    upsert_vectors(idx, vectors)

    titles = list({j["title"].strip() for j in jobs if j.get("title")})
    return {"suggested_job_titles": titles[:5]}
    
# --- Tool: Get Job Role Descriptions + RAG ---
def get_job_role_descriptions_function(job_title: str, country_code: str = "gb") -> dict:
    logger.info(f"[Tool] get_job_role_descriptions('{job_title}')")
    terms = [t.strip() for t in job_title.split() if t.strip()]
    what    = " ".join(terms)
    what_or = " OR ".join(terms) if len(terms) > 1 else None
    salary_min = 50000 if "high paying" in job_title.lower() else None

    jobs = adzuna_api.search_jobs(
        what=what, what_or=what_or,
        country=country_code, salary_min=salary_min
    ).get("results", [])
    if not jobs:
        return {"message": f"No openings for '{job_title}'."}

    upsert_jobs_bulk("job-postings", jobs)
    idx = get_index("job-postings")
    vectors = []
    for j in jobs:
        desc = j.get("description","")[:400]
        vec = compute_embedding(desc)
        doc_id = hash_string(j.get("title","") + j.get("company",{}).get("display_name",""))
        vectors.append((doc_id, vec, {"title": j.get("title")}))
    upsert_vectors(idx, vectors)

    examples = []
    
    # Add Adzuna jobs first
    for j in jobs[:10]:
        salary = j.get("salary_max") or j.get("salary_min") or "Not listed"
        examples.append({
            "title": j["title"],
            "company": j["company"]["display_name"],
            "location": j["location"]["display_name"],
            "salary": f"£{salary:,.2f}" if isinstance(salary, (int, float)) else salary,
            "description_snippet": j["description"][:400],
            "url": j["redirect_url"]
        })
    
    # Optionally dedupe and tag RAG results
    rag = query_similar_jobs(job_title, "job-postings", top_k=3)
    rag_examples = [
        {
            "title": r["title"],
            "company": r.get("company", "RAG result"),
            "location": r.get("location", "N/A"),
            "salary": r.get("salary", "Not listed"),
            "description_snippet": r.get("content", "")[:400],
            "url": r.get("url", "#")
        }
        for r in rag
        if r.get("title") not in {e["title"] for e in examples}
    ]
    
    examples += rag_examples
    
    return {"job_description_examples": examples}

# --- Tool: Suggest Next-Level Roles + RAG ---
def suggest_next_level_roles_function(current_title: str, country_code: str = "gb") -> dict:
    logger.info(f"[Tool] suggest_next_level_roles('{current_title}')")
    enriched = f"{current_title} lead manager head senior"
    terms = enriched.split()
    what    = " ".join(terms)
    what_or = " OR ".join(terms)

    jobs = adzuna_api.search_jobs(...).get("results", [])
    roles = [j["title"] for j in jobs if current_title.lower() not in j["title"].lower()]
    
    if roles:
        return {"next_level_roles": roles[:5]}
    else:
        rag = query_similar_jobs(current_title, "job-postings", top_k=3)
        return {"next_level_roles": [r.get("title") for r in rag]}

    upsert_jobs_bulk("job-postings", jobs)
    idx = get_index("job-postings")
    vectors = []
    for j in jobs:
        vec = compute_embedding(j.get("description","")[:400])
        doc_id = hash_string(j.get("title","") + j.get("company",{}).get("display_name",""))
        vectors.append((doc_id, vec, {"title": j.get("title")}))
    upsert_vectors(idx, vectors)

    roles = [j["title"] for j in jobs if current_title.lower() not in j["title"].lower()]
    if not roles:
        rag = query_similar_jobs(current_title, "job-postings", top_k=3)
        roles = [r.get("title") for r in rag]

    return {"next_level_roles": roles[:5]}

# --- Export Agent ---
career_guidance_agent = Agent(
    name="career_guidance_agent",
    model=MODEL_INSTANCE,
    description="Smart RAG-powered career coach",
    instruction=CAREER_GUIDANCE_PROMPT,
    tools=[
        explore_career_fields_function,
        get_job_role_descriptions_function,
        suggest_next_level_roles_function,
    ]
)
