# Deployment (Vercel)

## Recommended architecture
Deploy as two separate Vercel projects:

- Backend project (root: `backend`)
- Frontend project (root: `frontend`)

## Backend setup
1. Import repo in Vercel.
2. Set root directory to `backend`.
3. Optional env var: `GROQ_API_KEY`.
4. Deploy.

Backend routing is handled by `backend/vercel.json` and exposes:
- `POST /api/start`
- `GET /api/state`
- `GET|POST /api/summary`

## Frontend setup
1. Create second Vercel project from same repo.
2. Set root directory to `frontend`.
3. Add env var:
   - `VITE_API_BASE_URL=https://<backend>.vercel.app`
4. Deploy.

Frontend SPA routing is handled by `frontend/vercel.json`.

## Health checks
```bash
curl https://<backend>.vercel.app/api/state
curl -X POST https://<backend>.vercel.app/api/start -H "Content-Type: application/json" -d '{"topic":"AI policy"}'
curl https://<backend>.vercel.app/api/summary
```
