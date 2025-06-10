import logging
from typing import List, Dict, Any, Optional

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
from utils.env import get_model
from utils.adzuna import adzuna_api

MODEL_INSTANCE = get_model()
logger = logging.getLogger(__name__)
pinecone_job_index = get_index("job-postings")

COUNTRY_CURRENCY_MAP = {
    "gb": "GBP", "us": "USD", "de": "EUR", "fr": "EUR",
    "ca": "CAD", "au": "AUD", "in": "INR",
}
HIGH_PAYING_THRESHOLDS = {
    "gb": 50000, "us": 85000, "de": 65000, "fr": 60000,
    "ca": 80000, "au": 90000, "in": 1500000,
}
DEFAULT_HIGH_PAYING_THRESHOLD = 50000

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
        prompt = (
            f"Given the job title '{job_title}', generate a list of up to 6 keyword-friendly alternatives optimized for job search APIs like Adzuna. "
            f"Include commonly used titles and skills-based variants, and return them as a comma-separated string."
        )
        response = await MODEL_INSTANCE.generate_content_async(prompt)
        keywords = [s.strip() for s in response.text.split(',') if s.strip()]
        return " OR ".join(keywords)
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

async def get_job_role_descriptions_function(
    job_title: str, country_code: str = "gb",
    location: Optional[str] = None, salary_min: Optional[int] = None,
    employment_type: Optional[str] = None
) -> dict:
    logger.info(f"[Tool] get_job_role_descriptions: job_title={job_title}, country_code={country_code}, location={location}, salary_min={salary_min}, employment_type={employment_type}")
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

    if not jobs and location:
        logger.info("No jobs found with location, retrying without location...")
        jobs = adzuna_api.search_jobs(
            what=what_query, what_or=what_or_query, country=country_code,
            salary_min=current_salary_min, employment_type=employment_type
        ).get("results", [])

    if not jobs:
        logger.warning("No job results returned from Adzuna API.")
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

async def suggest_next_level_roles_function(current_title: str) -> dict:
    logger.info(f"[Tool] suggest_next_level_roles: current_title={current_title}")
    try:
        prompt = (
            f"Suggest 3 next-level job roles that would be a promotion or skill advancement from the title '{current_title}'. "
            f"Return only the upgraded job titles in a comma-separated list."
        )
        response = await MODEL_INSTANCE.generate_content_async(prompt)
        titles = [t.strip() for t in response.text.split(',') if t.strip()]
        return {"next_level_roles": titles}
    except Exception as e:
        logger.error(f"LLM failed to generate next-level roles: {e}")
        return {"next_level_roles": []}

async def get_skill_suggestions_function(job_title: str) -> dict:
    logger.info(f"[Tool] get_skill_suggestions: job_title={job_title}")
    try:
        prompt = (
            f"List the top 5 technical and soft skills most relevant to someone aiming to be a successful '{job_title}'. "
            f"Present them as a dictionary with 'technical_skills' and 'soft_skills'."
        )
        response = await MODEL_INSTANCE.generate_content_async(prompt)
        return eval(response.text.strip()) if response and response.text.strip().startswith('{') else {"skills": response.text.strip()}
    except Exception as e:
        logger.error(f"LLM failed to generate skill suggestions: {e}")
        return {"skills": []}

async def ingest_jobs_from_adzuna(
    what: str, country_code: str = "gb", location: Optional[str] = None,
    salary_min: Optional[int] = None, employment_type: Optional[str] = None
) -> dict:
    logger.info(f"[Tool] ingest_jobs_from_adzuna: what={what}, country_code={country_code}, location={location}, salary_min={salary_min}, employment_type={employment_type}")

    what = what.strip()
    what_or = await _expand_job_title(what)

    current_salary_min = salary_min
    if "high paying" in what.lower():
        threshold = HIGH_PAYING_THRESHOLDS.get(country_code, DEFAULT_HIGH_PAYING_THRESHOLD)
        current_salary_min = max(current_salary_min or 0, threshold)

    jobs = adzuna_api.search_jobs(
        what=what, what_or=what_or, country=country_code, location=location,
        salary_min=current_salary_min, employment_type=employment_type
    ).get("results", [])

    if not jobs:
        logger.warning("No jobs returned from Adzuna for ingest_jobs_from_adzuna.")
        return {"message": f"No roles found for '{what}' in {location or country_code.upper()}."}

    _ingest_jobs_data(jobs, country_code)
    return {"message": f"Successfully ingested {len(jobs)} jobs for '{what}'"}

async def explore_career_fields_function(
    keywords: str, country_code: str = "gb",
    location: Optional[str] = None, salary_min: Optional[int] = None,
    employment_type: Optional[str] = None
) -> dict:
    logger.info(f"[Tool] explore_career_fields_function() called with: keywords='{keywords}', location='{location}', country='{country_code}', employment='{employment_type}'")

    what_or = await _expand_job_title(keywords)
    what = keywords

    if "high paying" in keywords.lower():
        threshold = HIGH_PAYING_THRESHOLDS.get(country_code, DEFAULT_HIGH_PAYING_THRESHOLD)
        salary_min = max(salary_min or 0, threshold)

    jobs = adzuna_api.search_jobs(
        what=what,
        what_or=what_or,
        country=country_code,
        location=location,
        salary_min=salary_min,
        employment_type=employment_type
    ).get("results", [])

    if not jobs and location:
        logger.info("[Tool] No results, retrying without location...")
        jobs = adzuna_api.search_jobs(
            what=what,
            what_or=what_or,
            country=country_code,
            salary_min=salary_min,
            employment_type=employment_type
        ).get("results", [])

    if not jobs:
        return {"message": f"No roles found matching '{keywords}'."}

    _ingest_jobs_data(jobs, country_code)
    titles = list(dict.fromkeys([j["title"].strip() for j in jobs if j.get("title")]))
    return {"suggested_job_titles": titles[:5]}
