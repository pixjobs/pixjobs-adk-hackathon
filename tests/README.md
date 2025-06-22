# 🧪 WorkMatch API Tests

This folder contains basic integration tests for the WorkMatch backend API.

These tests simulate full chat conversations with different user personas (e.g. new job seekers, career planners), showcasing the WorkMatch multi-agent orchestration, routing, and prompt behaviour.

---

## 🔐 Authentication Required

These tests are designed to run **against the deployed WorkMatch API on Cloud Run**, which requires a valid Google Cloud **identity token**.

You must authenticate using a permitted Google Cloud account. For example:

```bash
gcloud auth print-identity-token
```

Then export it:

```bash
export WORKMATCH_IDENTITY_TOKEN=$(gcloud auth print-identity-token)
```

---

## 🧰 Requirements

Install the required test dependencies:


pip install -r requirements-dev.txt


---

## ▶️ Run the Tests (Verbose Output)

To run the integration tests and **see full streamed chat responses**, use:

pytest -v -s


Where:
- `-v` enables verbose output (test names, progress)
- `-s` disables output capture (so streamed LLM responses appear in the console)

This is especially useful for validating:
- Persona dialogue flows
- Prompt routing (e.g. career guidance → entry-level agent)
- Real-time job listing display
- Motivational quote tool usage

---

## ⚠️ Note: Test Scope

These integration tests are designed for:
- **Demonstration** of the agent system behaviour
- **Prompt verification** and flow consistency
- **Realistic persona simulation**

They are *not* intended for:
- Deep backend validation
- Unit test coverage
- Assertion-heavy automated pipelines

Use these tests to understand how WorkMatch behaves end-to-end in realistic user scenarios — not as a substitute for full backend test coverage.

---
