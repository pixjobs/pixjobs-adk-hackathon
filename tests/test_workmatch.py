import uuid
import json
import time
import re
import random
from typing import Optional, Any

import httpx
import pytest
from tqdm import tqdm

# GCP SDKs and Auth Libraries
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from google.cloud import secretmanager
from google.api_core import exceptions as gcp_exceptions
import google.auth
import google.auth.transport.requests
import google.oauth2.id_token

# === Step 1: Secret Config Loader ===
BOOTSTRAP_PROJECT_ID = "workmatch-hackathon"
def get_secret(project_id: str, secret_id: str, version_id: str = "latest") -> Optional[str]:
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        print(f"✅ Fetched secret: '{secret_id}'")
        return response.payload.data.decode("UTF-8").strip()
    except Exception as e:
        print(f"🚨 Error fetching secret '{secret_id}': {e}")
        return None
print(f"\n🔑 Loading config from Secret Manager ({BOOTSTRAP_PROJECT_ID})...")
GCP_PROJECT_ID = get_secret(BOOTSTRAP_PROJECT_ID, "google-cloud-project")
TEST_AGENT_MODEL = "gemini-2.5-pro"

# === Step 2: The Definitive Auth Setup ===
BASE_URL = "https://workmatch-api-718117052413.europe-west2.run.app"
APP_NAME = "workmatch"
BEARER_TOKEN = None
try:
    print("🔐 Fetching Google OIDC Identity Token (the correct way for Cloud Run)...")
    credentials, _ = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    BEARER_TOKEN = google.oauth2.id_token.fetch_id_token(auth_req, audience=BASE_URL)
    print(f"✅ Identity Token fetched successfully for audience: {BASE_URL}")
except Exception as e:
    print(f"🚨 Auth token fetch failed: {e}")
HEADERS = {"Authorization": f"Bearer {BEARER_TOKEN}"}

# === Step 3: Test Skips ===
pytestmark = [
    pytest.mark.skipif(not GCP_PROJECT_ID, reason="Missing GCP Project"),
    pytest.mark.skipif(BEARER_TOKEN is None, reason="Google Identity Token creation failed"),
]

# === Step 4: Advanced Persona Generator ===
def generate_user_personas(num_personas: int) -> list[dict]:
    vertex_ai_region = "europe-west4"
    print(f"\n🤖 Generating {num_personas} diverse user personas in region '{vertex_ai_region}' using {TEST_AGENT_MODEL}...")
    try:
        vertexai.init(project=GCP_PROJECT_ID, location=vertex_ai_region)
        model = GenerativeModel(TEST_AGENT_MODEL)
        industries = "creative, manufacturing, technology, finance, consulting, healthcare, education, retail, hospitality"
        prompt = (
            f"You are a test data generator. Generate exactly {num_personas} diverse user personas for testing a career coach chatbot.\n"
            f"Ensure the personas come from a wide range of industries, including but not limited to: {industries}.\n"
            "Also include a mix of experience levels: entry-level/new graduate, mid-career switchers, and senior professionals looking to advance.\n"
            "Each persona's goal should be a specific, actionable request.\n\n"
            "Return ONLY a valid JSON object in this format:\n"
            "{\n  \"personas\": [\n    {\"name\": \"Entry-Level Graphic Designer\", \"goal\": \"I just graduated with a design degree and I'm looking for my first job as a graphic designer.\"},\n    {\"name\": \"Mid-Career Accountant to Tech\", \"goal\": \"I've been an accountant for 8 years and want to move into a data analyst role in the tech industry.\"},\n    ...\n  ]\n}"
        )
        generation_config = GenerationConfig(response_mime_type="application/json")
        response = model.generate_content(prompt, generation_config=generation_config)
        data = json.loads(response.text)
        personas = data.get("personas", [])
        print(f"✅ Parsed {len(personas)} diverse user personas.")
        return personas
    except Exception as e:
        print(f"🚨 Failed to generate user personas: {e}")
        return []

USER_PERSONAS = generate_user_personas(3)
if not USER_PERSONAS:
    print("⚠️ Using fallback user persona.")
    USER_PERSONAS = [{"name": "Fallback Persona", "goal": "I need a job as a data analyst in Berlin."}]

# === Helper Function ===
def generate_next_turn(conversation_history: str, user_goal: str) -> str:
    print("...pytest agent is thinking of the next turn...")
    model = GenerativeModel(TEST_AGENT_MODEL)
    prompt = (
        "You are a user testing a career coach chatbot. Your overall goal is: '{user_goal}'.\n"
        "Here is the conversation so far:\n{conversation_history}\n\n"
        "Based on the chatbot's last response and your goal, what is the most logical and concise next thing you would say? "
        "Reply with ONLY the user's message, nothing else."
    )
    response = model.generate_content(prompt.format(user_goal=user_goal, conversation_history=conversation_history))
    return response.text.strip()

# === Step 5: The Dynamic Test Function ===

@pytest.mark.parametrize("persona", USER_PERSONAS)
def test_dynamic_conversation_flow(persona):
    user_id = f"pytest-dynamic-user-{uuid.uuid4().hex[:8]}"
    session_id = f"s_{uuid.uuid4().hex[:12]}"
    name = persona["name"]
    goal = persona["goal"]
    conversation_history = ""
    num_turns = 3

    print(f"\n\n📘 Running DYNAMIC scenario: '{name}' (Goal: {goal})")

    create_response = httpx.post(
        f"{BASE_URL}/apps/{APP_NAME}/users/{user_id}/sessions/{session_id}",
        headers=HEADERS,
        json={"state": {"testing": True, "scenario_name": name}},
        timeout=30
    )
    assert create_response.status_code == 200, f"Session creation failed: {create_response.text}"
    print(f"🟢 Session Created [{create_response.status_code}]")

    current_turn_text = "Hi"

    for i in range(num_turns):
        print(f"\n🗣️  Turn {i+1}: {current_turn_text}")
        conversation_history += f"User: {current_turn_text}\n"
        payload = {"appName": APP_NAME, "userId": user_id, "sessionId": session_id, "newMessage": {"role": "user", "parts": [{"text": current_turn_text}]}}
        
        # The /run endpoint is synchronous and returns the full result directly
        run_response = httpx.post(f"{BASE_URL}/run", headers=HEADERS, json=payload, timeout=120) # Increased timeout for long agent turns
        
        # --- THE FIX IS HERE: Display the raw output immediately ---
        print(f"🤖 Raw /run response [{run_response.status_code}]:")
        try:
            # Try to pretty-print if it's JSON, otherwise print raw text
            print(json.dumps(run_response.json(), indent=2))
        except json.JSONDecodeError:
            print(run_response.text)

        assert run_response.status_code == 200, f"Initial /run request failed for turn {i+1}: {run_response.text}"
        
        # --- THE FIX IS HERE: Parse the direct response, no polling needed ---
        response_data = run_response.json()
        
        # Concatenate all text parts from all AI events in the response
        agent_reply = "".join(
            part.get("text", "") 
            for event in response_data 
            if event.get("author") == "workmatch_root_agent"
            for part in event.get("content", {}).get("parts", [])
            if "text" in part
        )
        
        print(f"💬 Assistant reply {i+1}: {agent_reply[:700]}...")
        assert agent_reply.strip(), f"Agent returned an empty reply on turn {i+1}"
        conversation_history += f"Assistant: {agent_reply}\n"

        if i < num_turns - 1:
            thinking_time = random.uniform(2, 5)
            print(f"...simulating human thinking time for {thinking_time:.1f} seconds...")
            time.sleep(thinking_time)

            if i == 0:
                current_turn_text = goal
            else:
                current_turn_text = generate_next_turn(conversation_history, goal)

    print(f"✅ Dynamic Scenario '{name}' completed successfully.")