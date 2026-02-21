# Deployment & Operations

This project is configured to deploy on Vercel with frontend and backend either:
- as **separate Vercel projects** (recommended), or
- as a single project with custom routing.

The safest path for this repo is **separate projects**.

## Local runtime assumptions

- Backend listens on port `5000`.
- Frontend dev server listens on port `5173` and proxies `/api` to backend.

---

## Environment variables

### Backend

- `GROQ_API_KEY` (optional): enables real-world pro/con fact generation.

### Frontend

- `VITE_API_BASE_URL` (required for separate frontend deployment):
  - Example: `https://debateai-backend.vercel.app`
  - Frontend will call `${VITE_API_BASE_URL}/api/*`
  - If omitted, frontend defaults to relative `/api/*`.

---

## Vercel deployment (recommended: separate projects)

## 1) Deploy backend (`/backend`)

This repo includes `backend/vercel.json` that routes all requests to Flask app entrypoint:
- build target: `app.py`
- route passthrough: `/(.*)` -> `app.py`

Steps:
1. Create a new Vercel project.
2. Set **Root Directory** to `backend`.
3. Add env var `GROQ_API_KEY` (optional).
4. Deploy.
5. Verify endpoints:
   - `GET https://<backend>.vercel.app/api/state`
   - `POST https://<backend>.vercel.app/api/start`

## 2) Deploy frontend (`/frontend`)

This repo includes `frontend/vercel.json` SPA rewrites so client-side navigation does not return 404.

Steps:
1. Create a second Vercel project.
2. Set **Root Directory** to `frontend`.
3. Add env var:
   - `VITE_API_BASE_URL=https://<backend>.vercel.app`
4. Deploy.
5. Open frontend URL and run a debate.

---

## Preventing 404 and 405 in production

- **404 for client routes**: handled by frontend rewrite to `index.html`.
- **404 for API requests**: avoid relative `/api` when frontend/backend are split; set `VITE_API_BASE_URL`.
- **405 for API methods**:
  - `/api/start` must be `POST`
  - `/api/state` must be `GET`
  - `/api/summary` supports `GET` and `POST`
- Ensure frontend sends methods exactly as above (already implemented in `frontend/src/api.js`).

---

## Production considerations

1. **Persisted state**
   - Current backend stores one debate in global process memory.
   - In serverless environments this state may reset between invocations.
   - For strict persistence, move state to an external store.

2. **Concurrency**
   - Current design is educational/single-state oriented.
   - For multi-user sessions, add per-user storage and identifiers.

3. **CORS and routing**
   - Current backend enables CORS broadly.
   - For tighter security, restrict allowed origins to your frontend domain.

4. **Secret management**
   - Store `GROQ_API_KEY` via platform secret manager (not in source).

5. **Observability**
   - Add structured logs for `/api/start` latency and fallback rate (`facts_from_api`).

---

## Health checks (manual)

After deploy:

```bash
curl https://<backend-host>/api/state
curl -X POST https://<backend-host>/api/start -H "Content-Type: application/json" -d '{"topic":"Nuclear energy"}'
curl https://<backend-host>/api/summary
```

Expected:
- `state` null before first run,
- successful start with populated state,
- summary available after start.

