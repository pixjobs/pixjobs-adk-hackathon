# 🧪 WorkMatch API Tests

This folder contains basic integration tests for the WorkMatch backend API.

## 🔐 Authentication Required

These tests are designed to run **against the deployed API on Cloud Run**, which requires a valid Google Cloud **identity token** (`Authorization: Bearer <token>`).

Unless you are authenticated within the WorkMatch GCP project (e.g. using `gcloud auth print-identity-token` from a permitted account), you will **not** be able to run these tests successfully.

## 🧰 Requirements

To run the tests locally:

pip install -r requirements-dev.txt

export WORKMATCH_IDENTITY_TOKEN=$(gcloud auth print-identity-token)
pytest