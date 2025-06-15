🧪 ADK Web Interface (WorkMatch)

To run the ADK Web interface locally within this folder (/backend), use:

adk web --host 0.0.0.0 --port 8000

Notes:

- ADK Web does not auto-reload on file changes. (See issue #102)

🔐 Environment Setup (GCP Secret Manager)

WorkMatch loads all environment variables from Google Secret Manager (no .env support). Before running locally or deploying, ensure the following secrets are set:

🚀 Required for Vertex AI (Gemini)

gcloud secrets create google-cloud-project --data-file=<(echo "workmatch-hackathon")
gcloud secrets create google-cloud-location --data-file=<(echo "global")
gcloud secrets create gemini-model --data-file=<(echo "gemini-2.5-pro-preview-06-05")

💡 gemini-api-key is not used — the system only supports Vertex AI (via project/location authentication).

🧪 Optional: Langfuse Tracing

gcloud secrets create enable-langfuse --data-file=<(echo "true")
gcloud secrets create langfuse-public-key --data-file=<(echo "YOUR_LANGFUSE_PUBLIC_KEY")
gcloud secrets create langfuse-secret-key --data-file=<(echo "YOUR_LANGFUSE_SECRET_KEY")

You can toggle Langfuse by updating the enable-langfuse secret to "false" or removing it.

💼 Adzuna Jobs API

gcloud secrets create adzuna-app-id \
  --replication-policy="automatic" \
  --data-file=<(echo -n "YOUR_ADZUNA_APP_ID")

gcloud secrets create adzuna-app-key \
  --replication-policy="automatic" \
  --data-file=<(echo -n "YOUR_ADZUNA_APP_KEY")

🧠 Pinecone Vector Store

gcloud secrets create pinecone-api-key \
  --replication-policy="automatic" \
  --data-file=<(echo -n "YOUR_PINECONE_API_KEY")

👤 Permissions

Ensure your service account or GCP VM has these roles:

- Vertex AI User
- Secret Manager Secret Accessor
- Cloud Datastore User (for Firestore)
- (Optional) Secret Manager Admin — for secret creation during dev
