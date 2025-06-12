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
        salary_min=salary_filter,
    )
    if "error" in response:
        return {"error": response["error"]}

    jobs = response.get("results", [])
    if not jobs:
        return {"message": "No roles found for that query."}

    titles = list({job.get("title") for job in jobs if job.get("title")})
    return {"suggested_job_titles": titles[:10]}


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
        salary_min=salary_filter,
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
        country=country_code,
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
