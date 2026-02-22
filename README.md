# DebateAI

DebateAI is a full-stack AI debate simulator (Flask backend + React frontend).

## Run locally

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
```
Backend: `http://127.0.0.1:5000`

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend: `http://localhost:5173`

## Environment variables

- `GROQ_API_KEY` (backend, optional): enables factual pro/con claims from Groq.
- `VITE_API_BASE_URL` (frontend, for separate deployment): backend base URL, e.g.
  `https://<backend>.vercel.app`

## API endpoints

- `POST /api/start`
- `GET /api/state`
- `GET|POST /api/summary`

## Vercel deployment (recommended)

Deploy as two projects:

1. **Backend project**
   - Root directory: `backend`
   - Uses `backend/vercel.json`
   - Optional env: `GROQ_API_KEY`

2. **Frontend project**
   - Root directory: `frontend`
   - Uses `frontend/vercel.json`
   - Env: `VITE_API_BASE_URL=https://<backend>.vercel.app`

## Notes

- If Groq key is missing/invalid, app falls back to template claims.
- Backend state is in-memory (single active debate).
