# ProjectDemo

Open-source community event management system for art/exhibition spaces.

Backend: Flask (MySQL). Frontend: Vue 3 (Vite).

## Environment Setup

- Create your environment file by copying the example:
  ```bash
  cp .envexample .env
  ```
- Edit `.env` with your values. Common keys:
  - `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
  - `SECRET_KEY`
  - Optional CORS settings as needed.

## Backend Deployment (Flask)

1) Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

2) Initialize database schema
```bash
python ../init_db.py
```

3) Seed sample data (optional, for demo/testing)
```bash
python ../seed_example_data.py
```

4) Run production server (example)
```bash
gunicorn backend.app:app --bind 0.0.0.0:8000 --workers 4
```

Notes
- Ensure the Flask app can reach your MySQL instance.
- Tighten CORS in `backend/app.py` for production.
- Store secrets (`SECRET_KEY`, DB credentials) securely; do not commit them.

## Frontend Deployment (Vite + Vue)

1) Install dependencies
```bash
cd frontend
npm install
```

2) Build static assets
```bash
npm run build
```

3) Preview or serve the built site
```bash
npm run preview -- --host 0.0.0.0 --port 5173
```

Notes
- Create `frontend/.env.production` and set `VITE_API_BASE_URL` to your backend, e.g. `https://api.example.com/api`.
- Host `frontend/dist` via Nginx/CDN/object storage; reverse proxy `/api` to the Flask service.
- Use HTTPS for both frontend and backend for reliable QR scanning on mobile.

## Pytests & Local Testing

- Install test dependencies (already covered by `requirements.txt`).
- From the project root, run:
```bash
pytest -q
```
- Useful targeted runs (examples):
```bash
pytest tests/test_app_smoke.py -q
pytest tests/test_events_api_integration.py -q
pytest tests/test_api_full.py -q
```
- Before running tests, ensure `.env` is configured and DB schema initialized via `init_db.py`. Some tests may use seed data from `seed_example_data.py`.

## Infrastructure Recommendations

- Nginx/Traefik as reverse proxy: route `/api` → Flask, serve `/` from `frontend/dist`.
- Run Flask with Gunicorn under systemd/Supervisor/Docker.
- Use MySQL 8.x (or compatible) initialized with `init_db.py`.
- Add Redis if you plan to extend caching/rate-limiting.

## Operations Checklist

- `init_db.py` rebuilds tables; back up data before running on production.
- Seed only on staging/dev (`seed_example_data.py`) to avoid polluting production.
- Monitor backend and proxy logs; adjust logging level for production.
- `.env` is ignored by git; verify no secrets are committed.
