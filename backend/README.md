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

    gcloud secrets create adzuna-app-id       --replication-policy="automatic"       --data-file=<(echo -n "YOUR_ADZUNA_APP_ID")

    gcloud secrets create adzuna-app-key       --replication-policy="automatic"       --data-file=<(echo -n "YOUR_ADZUNA_APP_KEY")

👤 Required IAM Roles

Ensure your service account or Cloud Shell user has the following roles:
- Vertex AI User
- Secret Manager Secret Accessor
- Cloud Datastore User (for Firestore)
- Cloud Run Admin
- Service Account User
- Artifact Registry Writer
- Storage Admin (required to create staging buckets for Cloud Run source deploy)
- (Optional) Secret Manager Admin — for secret creation during dev

🚀 Deploying to Cloud Run

Use the ADK CLI to deploy WorkMatch directly to Google Cloud Run.

Deploy with UI enabled:

    adk deploy cloud_run \
      --project=workmatch-hackathon \
      --region=europe-west2 \
      --service_name=workmatch \
      --app_name=workmatch \
      --with_ui \
      ./workmatch

🙅‍♂️ Common Errors

If you see:
    PERMISSION_DENIED: Permission denied to enable service [run.googleapis.com]

It means your active identity (e.g. Cloud Shell or VM default service account) lacks the required permissions. You must either:
- Assign the **Service Usage Admin** role
- Or ask a GCP project owner to enable the `run.googleapis.com` service manually

If you see:
    PERMISSION_DENIED: Permission 'artifactregistry.repositories.get' denied

You need to grant the `Artifact Registry Writer` role to your service account.

If you see:
    PERMISSION_DENIED: Permission 'storage.buckets.create' denied

You must assign the `Storage Admin` role to allow creation of a temporary staging bucket during deployment.

✅ After Deployment

Once deployed, you'll receive a public URL like:

    https://workmatch-abc123xyz-ew.a.run.app

Visit this in your browser to access the WorkMatch agent with the ADK dev UI.

🌐 **Using WorkMatch as a Web API for React or External Clients**

If you'd like to deploy WorkMatch as a **server-only backend** (without the ADK Web UI) and connect it to a frontend like React:

### ✅ Deployment (API-only mode)

Use this CLI command to deploy the service without the interactive UI:


adk deploy cloud_run \
  --project=workmatch-hackathon \
  --region=europe-west2 \
  --service_name=workmatch-api \
  --app_name=workmatch \
  ./workmatch


This will deploy a Cloud Run service that accepts POST requests to:

https://workmatch-api-xxxxxx-ew.a.run.app/adk/invoke

Authentication is enforced by default.

---

### 🔐 Authenticating API Requests

To call the endpoint from your React app or other frontend, you’ll need to configure identity-based access:

1. **Create a dedicated service account for frontend access (optional but recommended):**


gcloud iam service-accounts create workmatch-web-client \
  --display-name="WorkMatch Web Client"


2. **Grant Cloud Run Invoker permissions:**


gcloud run services add-iam-policy-binding workmatch-api \
  --region=europe-west2 \
  --project=workmatch-hackathon \
  --member="serviceAccount:workmatch-web-client@workmatch-hackathon.iam.gserviceaccount.com" \
  --role="roles/run.invoker"


3. **Generate and pass an ID token:**

- For testing, you can run:

gcloud auth print-identity-token


- In production, you'll likely use a signed ID token from your frontend via Firebase Auth or OAuth2.

4. **Make a request to the API:**


curl -X POST \
  -H "Authorization: Bearer YOUR_ID_TOKEN" \
  https://workmatch-api-xxxxxx-ew.a.run.app/adk/invoke

---
s
You can now integrate this backend API with any frontend, mobile app, or authenticated third-party system.

