# Copilot Instructions for ProjectDemo

These guidelines help AI coding agents work effectively in this repo.

## Architecture Overview
- **Backend stack**: Flask API (`backend/app.py`) with Blueprints under `backend/api/`, business logic in `backend/services/`, DB access via **two styles**:
  - **SQLAlchemy ORM**: `backend/db_orm.py`, models in `backend/models/models.py`, used by `analytic_service.py`.
  - **Raw MySQL (PyMySQL)**: helpers in `backend/db.py` (and `get_connection`/`get_cursor`), used by most `services/` and `api/` modules.
- **Routing pattern**: `backend/app.py` creates the Flask app, enables CORS, and mounts Blueprints:
  - `/api/auth` → `backend/api/auth_api.py`
  - `/api/events` → `backend/api/events_api.py`
  - `/api/registrations` → `backend/api/registration_api.py`
  - `/api/analytics` → `backend/api/analytics_api.py`
  - `/api/checkin` → `backend/api/checkin_api.py`
- **Domain breakdown**:
  - Auth & user identity: `auth_api.py`, `auth_service.py`, decorators in `auth_decorators.py`.
  - Events & sessions: `events_api.py`, `event_service.py` (create EVENT + EVENT_SESSION in one transaction).
  - Registration & waitlist: `registration_api.py`, `registration_service.py`.
  - Analytics/metrics: `analytics_api.py`, `analytic_service.py` (ORM-based reporting).
  - Check-in & QR: `checkin_api.py`, `user_penalty_service.py`, QR helpers in `utils/qrcode_utils.py`.

## Data & DB Conventions
- **DB schema** is defined in `backend/db/schema.sql`; initialisation scripts live at repo root (`init_db.py`, `seed_example_data.py`).
- **Mixed access pattern**:
  - For new **analytics/reporting** endpoints, prefer SQLAlchemy models in `backend/models/models.py` and sessions from `backend/db_orm.py`.
  - For existing **transactional flows** (registration, events, check-in), follow the existing raw-SQL style using `get_connection()` / `get_cursor()` in `backend/db.py`.
- **Key tables & concepts** (names taken from existing SQL): `EVENT`, `EVENT_SESSION`, `REGISTRATION`, `USER`.
- **Status fields**:
  - Registration status values: `"registered" | "waiting" | "cancelled"` (see `analytic_service.get_*` and `registration_service`).
  - Event session status commonly uses `"open"` for newly created sessions (`event_service.create_event_with_sessions`).

## API & Service Patterns
- **Blueprint style**:
  - Each file under `backend/api/` defines a `Blueprint` named `<name>_bp` and registers routes using `@<name>_bp.get/post/...`.
  - Responses are JSON via `flask.jsonify`, and errors use the global handlers in `backend/app.py` for HTTP 4xx/5xx where appropriate.
- **Service layer**:
  - Business rules live in `backend/services/*_service.py` and expose Python functions.
  - API modules call these functions and translate exceptions into HTTP errors.
  - Custom exception types per domain, e.g. `EventError`, `RegistrationError`, `AnalyticError`, are defined in their service modules and used to convey user-facing messages.
- **Auth & user context**:
  - Protected endpoints are decorated with `@login_required` from `backend/auth_decorators.py`.
  - After auth, the current user is available as `g.current_user` (a dict); do **not** rely on `user_id` from request body.
  - Example: `registration_api.create_registration()` obtains `user_id = g.current_user["user_id"]`.
- **Blocking / penalties**:
  - Some flows check `g.current_user["blocked_until"]` to prevent registrations for blocked users (see `registration_api.create_registration`).
  - When extending this, keep payload fields `message_zh` and `message_en` for bilingual error messages.

## Error Handling & Response Conventions
- **Global handlers** in `backend/app.py` standardize common HTTP codes (400/401/403/404/409/500) into JSON objects with `error` and `message` fields.
- **Per-endpoint errors** often use bilingual messages:
  - Keys: `"error"`, `"message_zh"`, `"message_en"`.
  - Example from `registration_api.create_registration` when registration fails with `RegistrationError`.
- **Do** raise domain-specific errors (`EventError`, `RegistrationError`, etc.) from services and catch them in the API layer, converting to 4xx responses.

## QR Code & Check-in Patterns
- **QR generation** is centralized in `backend/utils/qrcode_utils.py`:
  - Use `build_checkin_payload(user_id, session_id)` to build the JSON payload.
  - Use `generate_qr_png_bytes(data_str)` to generate PNG binary.
  - Return images via `send_qr_response(buffer, filename=...)` as in `registration_api.get_registration_qrcode`.
- **Check-in endpoints** (in `checkin_api.py`) should validate the payload, update `REGISTRATION.checkin_time`, and may call `user_penalty_service` for no-show handling.

## Running, Debugging, and Env
- **Dependencies**: install via `pip install -r backend/requirements.txt`.
- **Environment**:
  - Config uses `.env` (loaded by both `backend/app.py` and `backend/db.py`).
  - Important vars typically include DB connection info and `SECRET_KEY`, `FLASK_ENV`.
- **Run backend locally** from repo root:
  - `python -m backend.app` **or** `python backend/app.py`
- **CORS**: Frontend is expected to call `/api/*` endpoints directly; CORS is enabled in `backend/app.py` for all origins during development.

## When Adding or Modifying Code
- Follow existing **file layout**: new APIs under `backend/api/`, business logic in `backend/services/`, DB access via `db.py` or `db_orm.py` consistent with similar features.
- Reuse existing **status values**, table names, and error shapes to keep the analytics and front-end assumptions valid.
- Prefer Chinese+English messages for any new client-facing error JSON.
- For new analytics/reporting endpoints, mirror the patterns in `analytic_service.py` and `analytics_api.py` (grouping with `func.count`, using ORM joins, returning dicts/lists of primitive types).
