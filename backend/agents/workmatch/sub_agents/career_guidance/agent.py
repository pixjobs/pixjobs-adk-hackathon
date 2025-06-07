import logging
import os
from typing import List, Union, Optional

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from utils.env import get_model
from .prompt import CAREER_GUIDANCE_PROMPT

try:
    from google.cloud import talent_v4 as talent
    talent_solution_available = True
    logger = logging.getLogger(__name__)
except ImportError:
    talent_solution_available = False
    talent = None
    logger = logging.getLogger(__name__)
    logger.warning("google-cloud-talent library not found. Career exploration tools will be disabled.")

GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
MODEL_INSTANCE = get_model()

def _get_talent_client_and_parent() -> Union[tuple[talent.JobServiceClient, str], tuple[None, None]]:
    if not talent_solution_available or not GCP_PROJECT_ID:
        return None, None
    try:
        client = talent.JobServiceClient()
        parent = f"projects/{GCP_PROJECT_ID}"
        return client, parent
    except Exception as e:
        logger.error(f"[TalentAPI] Failed to initialize JobServiceClient: {e}", exc_info=True)
        return None, None

def _create_request_metadata(tool_name: str) -> Union[talent.types.RequestMetadata, None]:
    if not talent_solution_available: return None
    return talent.types.RequestMetadata(
        domain="workmatch-career-guidance",
        session_id=f"adk_session_{tool_name}",
        user_id="adk_user_guidance"
    )

def explore_career_fields_function(keywords: str, location: str = "") -> dict:
    """
    Suggests potential job titles or career fields based on keywords and an optional location.
    Use this to brainstorm roles related to user's interests or skills.

    Args:
        keywords (str): Keywords related to interests, skills, or desired job aspects.
        location (Optional[str], optional): A specific city, state, or country. Defaults to None.

    Returns:
        Dict: A dictionary containing suggested job titles or an error/message.
    """
    client, parent = _get_talent_client_and_parent()
    if not client:
        return {"error": "Talent Solution client not available or GCP_PROJECT_ID missing."}
    try:
        request_metadata = _create_request_metadata("explore_fields")
        job_query = talent.types.JobQuery(query=keywords)
        if location:
            job_query.location_filters.append(talent.types.LocationFilter(address=location))
        histogram_queries = [talent.types.HistogramQuery(histogram_query="JOB_TITLE")]
        request = talent.types.SearchJobsRequest(
            parent=parent, request_metadata=request_metadata, job_query=job_query,
            histogram_queries=histogram_queries, job_view=talent.types.JobView.JOB_VIEW_ID_ONLY, page_size=1
        )
        response = client.search_jobs(request=request)
        suggested_titles = []
        for histogram_result in response.histogram_query_results:
            if histogram_result.histogram == "JOB_TITLE":
                for title, _ in histogram_result.histogram_results.items():
                    if len(suggested_titles) < 5:
                        clean_title = title.replace("(Remote)", "").replace("- Remote", "").strip()
                        if clean_title and clean_title not in suggested_titles:
                             suggested_titles.append(clean_title)
        if not suggested_titles and len(keywords.split()) <= 4:
            request.job_view = talent.types.JobView.JOB_VIEW_SMALL
            request.page_size = 10 
            request.histogram_queries = []
            response_fallback = client.search_jobs(request=request)
            for result_item in response_fallback.matching_jobs:
                if len(suggested_titles) < 5:
                    clean_title = result_item.job.title.replace("(Remote)", "").replace("- Remote", "").strip()
                    if clean_title and clean_title not in suggested_titles:
                        suggested_titles.append(clean_title)
                else: break
        if not suggested_titles:
            return {"message": "Could not identify distinct career fields. Try different keywords."}
        return {"suggested_job_titles": suggested_titles}
    except Exception as e:
        logger.error(f"[explore_career_fields_function] API Error: {str(e)}", exc_info=True)
        return {"error": "An error occurred while exploring career fields."}

def get_job_role_descriptions_function(job_title: str, location: str = "") -> dict:
    """
    Fetches example job descriptions for a specific job title and optional location.
    The agent can then summarize insights from these descriptions.

    Args:
        job_title (str): The specific job title to get details for.
        location (Optional[str], optional): A specific city, state, or country. Defaults to None.

    Returns:
        Dict: A dictionary containing job description examples or an error/message.
    """
    client, parent = _get_talent_client_and_parent()
    if not client:
        return {"error": "Talent Solution client not available or GCP_PROJECT_ID missing."}
    try:
        request_metadata = _create_request_metadata("get_descriptions")
        job_query = talent.types.JobQuery(query=f'title:"{job_title}"')
        if location:
            job_query.location_filters.append(talent.types.LocationFilter(address=location))
        request = talent.types.SearchJobsRequest(
            parent=parent, request_metadata=request_metadata, job_query=job_query,
            job_view=talent.types.JobView.JOB_VIEW_FULL, page_size=2
        )
        response = client.search_jobs(request=request)
        if not response.matching_jobs:
            return {"message": f"No job postings found for '{job_title}'. Try a broader title or location."}
        descriptions = []
        for item in response.matching_jobs:
            job = item.job
            desc_for_llm = job.description[:3500] if job.description else "No description provided."
            primary_location = job.addresses[0] if job.addresses and job.addresses[0] else "N/A"
            company_name_str = "N/A"
            if job.company_display_name: company_name_str = job.company_display_name
            elif job.company_name: company_name_str = job.company_name.split('/')[-1]
            descriptions.append({
                "title": job.title, "company": company_name_str, "location_display": primary_location,
                "description_for_synthesis": desc_for_llm,
                "job_link": job.application_info.uris[0] if job.application_info and job.application_info.uris else "N/A"
            })
        return {"job_description_examples": descriptions}
    except Exception as e:
        logger.error(f"[get_job_role_descriptions_function] API Error: {str(e)}", exc_info=True)
        return {"error": "Error fetching job role descriptions."}

explore_fields_tool = FunctionTool(func=explore_career_fields_function)
get_role_details_tool = FunctionTool(func=get_job_role_descriptions_function)

career_guidance_agent = Agent(
    name="career_guidance_agent",
    model=MODEL_INSTANCE,
    description="A supportive guide to help users explore passions, skills, and values for career clarity. It can now use tools to explore relevant job titles and fetch example job descriptions to make the guidance more concrete, considering location if provided.",
    instruction=CAREER_GUIDANCE_PROMPT,
    tools=[
        explore_fields_tool,
        get_role_details_tool,
    ]
)