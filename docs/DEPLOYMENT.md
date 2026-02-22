# Deployment & Operations

This project can be deployed as separate frontend and backend services.

## Local runtime assumptions

- Backend listens on port `5000`.
- Frontend dev server listens on port `5173` and proxies `/api` to backend.

---

## Environment variables

### Backend

- `GROQ_API_KEY` (optional): enables real-world pro/con fact generation.

No other runtime env vars are required currently.

---

## Production considerations

1. **Persisted state**
   - Current backend stores one debate in global process memory.
   - For multi-user deployment, replace with per-user/session persistence.

2. **Concurrency**
   - Run backend behind a WSGI server (`gunicorn`, `uwsgi`, etc.).
   - Add request limits/timeouts to control compute-heavy searches.

3. **CORS and routing**
   - Restrict CORS origins in production.
   - If hosting frontend and backend on different domains, configure `API_BASE` accordingly.

4. **Secret management**
   - Store `GROQ_API_KEY` via platform secret manager (not in source).

5. **Observability**
   - Add structured logs for `/api/start` latency and fallback rate (`facts_from_api`).

---

## Suggested deployment model

- Frontend: static hosting (Vercel/Netlify/S3+CDN)
- Backend: containerized Flask app (Render/Fly.io/railway/self-hosted VM)

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

