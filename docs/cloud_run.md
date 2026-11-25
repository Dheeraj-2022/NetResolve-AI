# Deploy the web application on one Cloud Run URL

The `Dockerfile` builds `frontend/` with Vite, copies the output into the Python
image, and starts the FastAPI application. FastAPI serves the React app at `/`
and the API at `/api/*`, so the browser and API use the same Cloud Run origin.
No frontend API URL or CORS configuration is needed for this deployment.

From the repository root, deploy the existing service in the same project and
region as the service shown in the deployment output:

```powershell
gcloud run deploy netresolve-backend `
  --source . `
  --region asia-south1 `
  --project netresolve-ai `
  --memory 4Gi `
  --cpu 2 `
  --max 1 `
  --set-env-vars "GOOGLE_CLOUD_PROJECT=netresolve-ai,NBT_REMEDIATION_MODE=simulate,NBT_DISABLE_EMBEDDINGS=1" `
  --allow-unauthenticated
```

Cloud Run builds the image from the root `Dockerfile` and returns the service
URL. Open that URL to use the React application. The deployment command from
the question set `GCP_PROJECT`; the Vertex AI integration reads
`GOOGLE_CLOUD_PROJECT`, so the command above sets the variable the code uses.
For Gemini, enable Vertex AI and assign the Cloud Run runtime service account
the `roles/aiplatform.user` role. Without that access the app uses its offline
reasoning fallback.

## Access control

`--allow-unauthenticated` makes the Cloud Run URL publicly reachable. In this
application, `/api/auth` is public and the rest of the API can be protected by
`NBT_API_KEY`. For a public demo, create a Secret Manager secret, grant the
Cloud Run runtime service account `roles/secretmanager.secretAccessor`, and
deploy with this additional flag (replace the secret name if needed):

```powershell
--set-secrets "NBT_API_KEY=netresolve-api-key:latest"
```

The UI prompts operators for the key and keeps it in that browser tab's
`sessionStorage`. Do not put it in a `VITE_*` variable or in source control. For
organization-only access, use Cloud Run IAM or an identity-aware access layer
instead of making the service public.

## Runtime limits to understand

- Cloud Run's writable filesystem is temporary. The Docker image places the
  remediation SQLite database under `/tmp`; remediation records and in-memory
  demo/telemetry state can be lost when an instance is replaced. `--max 1`
  avoids splitting the in-memory demo state across instances, but does not make
  that state durable. Production persistence needs a shared database and a
  corresponding application storage integration.
- The web container includes the FastAPI API and React UI. The telemetry agent,
  Kafka consumer, and privileged Linux/eBPF collection are separate processes
  in this repository; Cloud Run does not run those as part of this web service.
  Deploy agents on suitable Linux VMs and Kafka on a managed or separately
  operated broker if those data paths are required.
- Keep remediation in `simulate` mode unless the execution environment, host
  authorization, secrets, and approval process have been deliberately
  configured for live changes.
