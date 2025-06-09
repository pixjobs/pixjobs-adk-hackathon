🧪 ADK Web Interface (WorkMatch)
To run the ADK Web interface locally, use:

adk web --host 0.0.0.0 --port 8000
Notes:

ADK Web does not auto-reload on file changes. (See issue #102)

Ensure your agents and relative imports are correct — ADK will throw errors like “module not found” or “root_agent not defined” if the structure is incorrect.

🔐 Environment Setup (GCP Secret Manager)
WorkMatch loads environment variables from Google Secret Manager. Set them using the following commands:

gcloud secrets create gemini-api-key --data-file=<(echo "YOUR_API_KEY_HERE")
gcloud secrets create google-cloud-project --data-file=<(echo "workmatch-hackathon")
gcloud secrets create google-cloud-location --data-file=<(echo "us-central1")
gcloud secrets create gemini-model --data-file=<(echo "gemini-2.5-pro-preview-05-06")

To enable Langfuse tracing, you must also set the following:

gcloud secrets create enable-langfuse --data-file=<(echo "true")
gcloud secrets create langfuse-public-key --data-file=<(echo "YOUR_LANGFUSE_PUBLIC_KEY")
gcloud secrets create langfuse-secret-key --data-file=<(echo "YOUR_LANGFUSE_SECRET_KEY")

ℹ️ You can toggle tracing by changing the enable-langfuse value to "false" or deleting the secret.

To use Adzuna Jobs Data, register for an API key and then add the credentials to the Secret Manager:

gcloud secrets create adzuna-app-id \
  --replication-policy="automatic" \
  --data-file=<(echo -n "YOUR_ADZUNA_APP_ID")

gcloud secrets create adzuna-app-key \
  --replication-policy="automatic" \
  --data-file=<(echo -n "YOUR_ADZUNA_APP_KEY")

The pinecone API key can be added using

gcloud secrets create pinecone-api-key \
  --replication-policy="automatic" \
  --data-file=<(echo -n "YOUR_PINECONE_APP_KEY")


👤 Permissions
Ensure the service account or GCP VM has the following permissions:

Cloud Datastore User
Secret Manager Admin (only if using Workbench AI or Console)
Secret Manager Secret Accessor
Vertex AI user

You can attach these via IAM or custom roles as required.

