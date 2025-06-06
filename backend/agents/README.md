# ADK Web Interface

To run the ADK Web interface, plesae use the following command.

adk web --host 0.0.0.0 --port 8000

Note:

1. It must be run at this level in the console.
2. The ADK Web DOES NOT refresh by itself (see https://github.com/google/adk-docs/issues/102)
3. The ADK will throw errors like module not found for code / reference errors 

The environment variables are configured in Secret Manager using:

gcloud secrets create gemini-api-key --data-file=<(echo "YOUR_API_KEY_HERE")
gcloud secrets create google-cloud-project --data-file=<(echo "workmatch-hackathon")
gcloud secrets create google-cloud-location --data-file=<(echo "us-central1")
gcloud secrets create gemini-model --data-file=<(echo "gemini-2.5-flash-preview-0409")

Please ensure that the IAM role has "Secret Manager Admin" privileges.