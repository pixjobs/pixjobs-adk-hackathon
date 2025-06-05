from google.adk.agents import Agent

def handle_cv_upload(file: bytes, file_type: str) -> dict:
    # Simplified version; add real parsing later
    preview = file[:300].decode("utf-8", errors="ignore")
    return {"status": "success", "source": "file", "preview": preview}

def handle_cv_text(text: str) -> dict:
    preview = text[:300]
    return {"status": "success", "source": "text", "preview": preview}

def handle_cv_conversation(conversation: str) -> dict:
    # Later this could feed into a CV draft or matching pipeline
    summary = "Got it! You said: " + conversation[:300]
    return {"status": "success", "source": "conversation", "preview": summary}

root_agent = Agent(
    name="cv_input_agent",
    model="gemini-2.0-flash",
    description="Conversational CV intake assistant",
    instruction=(a
        "You are a friendly assistant that helps users input their CVs.\n"
        "Greet the user when they arrive. Ask if they’d like to upload a file, paste their CV, "
        "or just tell you about their background in conversation.\n"
        "Use the right tool to extract and preview their CV content."
    ),
    tools=[handle_cv_upload, handle_cv_text, handle_cv_conversation],
)
