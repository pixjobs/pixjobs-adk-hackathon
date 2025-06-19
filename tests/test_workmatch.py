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
def generate_user_personas(num_dynamic_personas: int) -> list[dict]:
    """
    Generates a list of user personas for testing.
    It includes a guaranteed set of senior roles and supplements them
    with dynamically generated personas from various industries.
    """
    vertex_ai_region = "europe-west4"
    persona_generator_model = "gemini-1.5-pro-001"
    
    print(f"\n🤖 Generating {num_dynamic_personas} dynamic user personas in region '{vertex_ai_region}' using {persona_generator_model}...")

    # --- Guaranteed personas as requested ---
    required_personas = [
        {"name": "Senior Business Analyst", "goal": "I'm a Senior Business Analyst with 10 years of experience looking for remote leadership opportunities in the financial sector."},
        {"name": "Product Owner (E-commerce to Fintech)", "goal": "I'm a Product Owner in the e-commerce space. I want to see what skills I need to move into a Product Owner role at a fintech company."},
        {"name": "Technical Product Owner (AI Focus)", "goal": "As a Technical Product Owner with a software engineering background, I want to find roles where I can work closely with both engineering and AI research teams."},
        {"name": "Senior Product Owner to Head of Product", "goal": "I'm a Senior Product Owner with a track record of launching successful products. Help me prepare for interviews for a Head of Product position."}
    ]
    
    dynamic_personas = []
    try:
        vertexai.init(project=GCP_PROJECT_ID, location=vertex_ai_region)
        model = GenerativeModel(persona_generator_model)
        industries = "creative, manufacturing, technology, finance, consulting, healthcare, education, retail, hospitality"
        prompt = (
            f"You are a test data generator. Generate exactly {num_dynamic_personas} diverse user personas for testing a career coach chatbot.\n"
            f"Ensure the personas come from a wide range of industries, including but not limited to: {industries}.\n"
            "Include a mix of experience levels: entry-level/new graduate and mid-career switchers.\n"
            "Each persona's goal should be a specific, actionable request.\n\n"
            "Return ONLY a valid JSON object in this format:\n"
            "{\n  \"personas\": [\n    {\"name\": \"Entry-Level UX Designer\", \"goal\": \"I just finished a UX bootcamp and I'm looking for my first job.\"},\n    {\"name\": \"Mid-Career Manufacturing Supervisor to Project Manager\", \"goal\": \"I've been a manufacturing supervisor for 12 years and want to become a project manager in the same industry.\"},\n    ...\n  ]\n}"
        )
        
        generation_config = GenerationConfig(response_mime_type="application/json")
        response = model.generate_content(prompt, generation_config=generation_config)
        data = json.loads(response.text)
        dynamic_personas = data.get("personas", [])
        print(f"✅ Parsed {len(dynamic_personas)} dynamic user personas.")
    except Exception as e:
        print(f"🚨 Failed to generate dynamic user personas: {e}")

    all_personas = required_personas + dynamic_personas
    print(f"✅ Total personas for testing: {len(all_personas)}")
    return all_personas

# We'll test the 4 required personas plus 1 dynamic one for a total of 5 tests.
USER_PERSONAS = generate_user_personas(1)
if not USER_PERSONAS:
    print("⚠️ Using fallback user persona.")
    USER_PERSONAS = [{"name": "Fallback Persona", "goal": "I need a job as a data analyst in Berlin."}]

# === Helper Function ===
def generate_next_turn(conversation_history: str, persona: dict) -> str:
    """
    Uses Gemini Pro to decide the next user message, acting in character
    based on the persona's role and goal.
    """
    print("...pytest agent is thinking of the next turn (acting as '{name}')...".format(**persona))
    model = GenerativeModel(TEST_AGENT_MODEL)
    
    prompt = (
        "You are a user testing a career coach chatbot. You must stay in character.\n"
        "Your Persona: '{name}'\n"
        "Your Ultimate Goal: '{goal}'\n\n"
        "## Conversation History:\n{conversation_history}\n\n"
        "## Your Task:\n"
        "Based on the chatbot's LAST response and your persona, what is the most logical and realistic next thing you would say? \n"
        "- If the chatbot asked a question, answer it directly and concisely.\n"
        "- If the chatbot gave information or options, ask a relevant follow-up question that moves you closer to your goal.\n"
        "- Keep your response natural and human-like.\n\n"
        "Reply with ONLY the user's message, nothing else."
    ).format(conversation_history=conversation_history, **persona)
    
    response = model.generate_content(prompt)
    return response.text.strip()

# === Step 5: The Dynamic Test Function ===

@pytest.mark.parametrize("persona", USER_PERSONAS)
def test_dynamic_conversation_flow(persona):
    """
    Simulates a deep, dynamic, multi-turn conversation where a 'pytest agent'
    reacts to the chatbot's responses with human-like delays.
    """
    user_id = f"pytest-dynamic-user-{uuid.uuid4().hex[:8]}"
    session_id = f"s_{uuid.uuid4().hex[:12]}"
    name = persona["name"]
    goal = persona["goal"]
    conversation_history = ""
    # --- Increased number of turns for a deeper conversation ---
    num_turns = 20

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
        print(f"\n🗣️  Turn {i+1}/{num_turns}: {current_turn_text}")
        conversation_history += f"User: {current_turn_text}\n"
        payload = {"appName": APP_NAME, "userId": user_id, "sessionId": session_id, "newMessage": {"role": "user", "parts": [{"text": current_turn_text}]}}
        
        # --- THE FIX IS HERE: No polling. The /run endpoint is synchronous. ---
        # We give it a long timeout to allow for complex tool use.
        run_response = httpx.post(f"{BASE_URL}/run", headers=HEADERS, json=payload, timeout=120)
        
        print(f"🤖 Raw /run response [{run_response.status_code}]:")
        try:
            response_data = run_response.json()
            print(json.dumps(response_data, indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            print(run_response.text)

        assert run_response.status_code == 200, f"The /run endpoint failed for turn {i+1}: {run_response.text}"
        
        response_data = run_response.json()
        
        # --- THE FIX IS HERE: Correctly parse the direct, synchronous response ---
        # This logic finds the final text reply from the agent, even after tool calls.
        agent_reply = "".join(
            part.get("text", "") 
            for event in response_data 
            if event.get("author") == "workmatch_root_agent"
            for part in event.get("content", {}).get("parts", [])
            if "text" in part
        )
        
        print(f"💬 Assistant reply {i+1}: {agent_reply[:700]}...")
        assert agent_reply.strip(), f"Agent returned an empty reply on turn {i+1}. This might indicate a backend bug where the agent timed out or failed to produce a text response."
        conversation_history += f"Assistant: {agent_reply}\n"

        if i < num_turns - 1:
            thinking_time = random.uniform(2, 5)
            print(f"...simulating human thinking time for {thinking_time:.1f} seconds...")
            time.sleep(thinking_time)

            # On the first real turn (i=0), the next turn is the persona's main goal.
            # On subsequent turns, the test agent thinks dynamically.
            if i == 0:
                current_turn_text = goal
            else:
                current_turn_text = generate_next_turn(conversation_history, persona)

    print(f"✅ Dynamic Scenario '{name}' completed successfully.")