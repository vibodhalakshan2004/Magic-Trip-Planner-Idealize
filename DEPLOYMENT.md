# Production deployment

## Recommended topology

Deploy the Next.js application to Vercel and run the stateful services on Azure:

```text
Browser
  -> Vercel (Frontend/)
       -> /api/backend/* same-origin proxy
            -> Azure Container Apps: FastAPI API
                 -> Azure Database for PostgreSQL Flexible Server
            -> Azure Container Apps: planning worker (no public ingress)
```

This is the smallest production-safe fit for the current architecture. Vercel is an excellent host for the Next.js application and supports Python functions, but the planner uses a continuously running database-polling worker. That worker is not a request/response serverless function and must run as a persistent process. Azure Container Apps supports both the HTTP API and the continuously running worker.

The frontend proxy uses the server-only `BACKEND_API_URL` variable. Browser requests stay on the Vercel origin, so the HttpOnly session cookie remains first-party and the backend URL can change without rebuilding browser JavaScript.

## 1. Deploy the database and backend on Azure

Create these resources in the same Azure region when possible:

- Azure Container Registry
- Azure Container Apps environment
- Azure Database for PostgreSQL Flexible Server
- One externally accessible Container App for the API
- One Container App without ingress for the planning worker

Build both backend processes from `Backend/Dockerfile`. The image's default command starts the API and applies Alembic migrations. Override the worker Container App command with:

```text
python -m app.workers.planning_worker
```

Use these container settings for the first prototype deployment:

| Container App | Ingress | Target port | Minimum replicas | Maximum replicas | Health check |
| --- | --- | --- | --- | --- | --- |
| API | External HTTPS | `8000` | `1` | `1` | `GET /health` |
| Planning worker | Disabled | None | `1` | `1` | Process health/restart |

Keep the worker at exactly one replica. Jobs are claimed transactionally, but one always-running worker is sufficient for the prototype and avoids unnecessary provider usage. Keep the API at one replica while migrations run in the container startup command and rate limiting is stored in process memory. Before scaling the API horizontally, move migrations to a one-off deployment job and rate limiting to shared storage.

Set these Azure secrets and environment variables on **both** the API and worker unless noted:

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
SECRET_KEY=generate-a-unique-random-value-of-at-least-32-characters
ACCESS_TOKEN_EXPIRE_MINUTES=30
GEMINI_API_KEY=your-server-side-gemini-key
GEMINI_MODEL=gemini-2.5-flash

FRONTEND_ORIGINS=https://YOUR-PROJECT.vercel.app
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=lax
# API Container App only. This is a public Web OAuth client ID, not a secret.
GOOGLE_AUTH_CLIENT_ID=YOUR-WEB-CLIENT-ID.apps.googleusercontent.com
```

Add optional provider settings from `Backend/.env.example` only when needed. Never add backend secrets to Vercel as `NEXT_PUBLIC_*` variables.

### Enable Google account sign-in

Google sign-in uses Google Identity Services popup mode and the existing first-party session proxy. It needs a Web OAuth client ID but no OAuth client secret.

1. In [Google Auth Platform](https://console.cloud.google.com/auth/overview), configure **Branding** and **Audience**. Use External for a public prototype, and add your judges/testers while the app remains in Testing.
2. Create a **Web application** client under **Clients**.
3. Add the exact Vercel production origin under **Authorized JavaScript origins**, for example `https://YOUR-PROJECT.vercel.app`. Add the final custom domain separately if used.
4. Do not add a redirect URI for this popup-mode implementation.
5. Set the resulting client ID as `GOOGLE_AUTH_CLIENT_ID` on the Azure API Container App and create a new revision. It is not required on Vercel or the planning worker.

The button is configuration-gated: if the client ID is absent, email/password login continues normally and no Google script is loaded.
Google does not allow wildcard JavaScript origins; use the stable production/custom domain for Google sign-in instead of changing Vercel Preview URLs.

After the API revision starts, verify:

```text
https://YOUR-AZURE-API-HOST/health
https://YOUR-AZURE-API-HOST/health/providers
```

`/health` must report both `status: ok` and `database: ok`. The provider endpoint should report the expected enabled services without revealing any key.

## 2. Deploy the frontend on Vercel

Import this Git repository as a Vercel project and configure:

| Vercel setting | Value |
| --- | --- |
| Framework preset | Next.js |
| Root Directory | `Frontend` |
| Install command | `npm ci` (automatic) |
| Build command | `npm run build` (automatic) |
| Output directory | `.next` (automatic) |

The `Root Directory` setting is required. The repository root is not the Next.js application.

Add this Vercel environment variable to Production and Preview:

```dotenv
BACKEND_API_URL=https://YOUR-AZURE-API-HOST
```

Do not set `NEXT_PUBLIC_API_BASE_URL` for the recommended deployment. It is an optional direct-browser override and bypasses the same-origin session proxy.

Deploy, then replace `FRONTEND_ORIGINS` on Azure with the final Vercel production origin and restart both backend containers. Preview deployments continue to work through the same-origin proxy; add preview origins to backend CORS only if the browser will call the Azure API directly.

## 3. Public launch checks

Run these checks in a private/incognito browser before submitting the link:

1. Open the Vercel URL without being signed in to Vercel or Azure.
2. Check the landing page at desktop and mobile widths.
3. Register a new account, sign out, and sign in again.
4. If Google sign-in is enabled, sign in once with a Google test account, sign out, and repeat.
5. Create a trip and complete the manual workflow.
6. Start automatic planning and confirm that its status progresses beyond `queued`.
7. Refresh the page and verify the authenticated session and trip are restored.
8. Open an image-heavy planner page and confirm images and map tiles load.
9. Confirm there are no mixed-content, CORS, or cookie errors in the browser console.
10. Confirm `GET /health` still reports a healthy database after the workflow.

Profile uploads and proxied location images are limited to 4 MB because Vercel Functions enforce a 4.5 MB request/response payload ceiling.

The submission URL should be the Vercel production URL, not a preview URL that may be protected by Vercel Authentication.

## All-Azure alternative

The complete application can also run on Azure. Deploy `Frontend/Dockerfile` as a third Container App with external ingress on port `3000` and set its runtime environment variable to:

```dotenv
BACKEND_API_URL=http://YOUR-INTERNAL-API-HOST
```

The API and worker configuration remains the same. This option keeps all compute in one platform and can use internal networking, but Vercel is the simpler and better-optimized host for the current Next.js frontend.

## Why not Vercel-only?

The FastAPI request handlers can be adapted to Vercel's Python runtime, but the current application also requires:

- a continuously running planning worker;
- Alembic migrations coordinated with deployment;
- PostgreSQL;
- durable work that must continue after the HTTP request ends.

Deploying the repository only to Vercel would therefore leave automatic planning jobs queued unless the worker were redesigned around a managed queue or workflow system. Keep the API and worker on Azure for this release.

## References

- [Vercel monorepo root directories](https://vercel.com/docs/monorepos)
- [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python)
- [Vercel Functions limits](https://vercel.com/docs/functions/limitations)
- [Azure Container Apps jobs and continuously running apps](https://learn.microsoft.com/azure/container-apps/jobs)
- [Azure Container Apps scaling](https://learn.microsoft.com/azure/container-apps/scale-app)
- [Azure Database for PostgreSQL Flexible Server](https://learn.microsoft.com/azure/postgresql/flexible-server/overview)
