# Precise-HBR

Precise-HBR is a Flask-based Clinical Decision Support (CDS) application focused on precise cardiovascular risk estimation and tradeoff modeling. It integrates clinical calculators, a FHIR client, risk classifiers, and web APIs to support risk communication and clinical decision workflows.

## Overview
- Purpose: provide cardiovascular risk calculations, risk classification, and tradeoff model endpoints + web UI.
- Stack: Python, Flask, FHIR (REST), Jinja2 templates, Docker (optional).
- Key components: clinical calculators (`services/precise_hbr_calculator.py`), FHIR client (`services/fhir_client_service.py`), risk classifier (`services/risk_classifier.py`), tradeoff model (`services/tradeoff_model_calculator.py`), REST API (`routes/api_routes.py`).

## Repository layout (selected)
```
Precise-HBR/
├── APP.py                   # Flask application entry point
├── requirements.txt         # Python dependencies
├── config/                  # Configuration templates and environment examples
├── services/                # Core business logic and calculators
├── routes/                  # API and web route definitions
├── templates/               # Jinja2 HTML templates
├── static/                  # Static assets (css/js/images)
├── docs/                    # Documentation, verification & compliance
├── scripts/                 # Helper scripts (tests, perf)
└── README_en.md
```

Key files and directories
- `APP.py`: loads configuration and starts the Flask app.
- `config/local.env.template`: example env file — copy to `.env` and fill secrets/URLs.
- `services/`: implementations for calculators, FHIR integration, unit conversion, classifiers.
- `routes/`: contains `api_routes.py` (REST API) and `web_routes.py` (UI routes).

## Environment & prerequisites
- Python 3.8+ (3.10+ recommended)
- pip
- (Optional) Docker & Docker Compose for containerized deployment

## Quick start (recommended for Windows developers)
1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # PowerShell
# or on CMD:
# \.venv\Scripts\activate.bat
```

2. Install dependencies

```powershell
pip install -r requirements.txt
```

3. Create local environment file

```powershell
Copy-Item config\local.env.template .env
# Edit .env to add FHIR server URL, API keys, and other secrets
```

4. Run the application (development)

```powershell
python APP.py
# The Flask server and port will be displayed in the console
```

5. (Optional) Start with Docker

```powershell
docker-compose up --build
```

6. Run tests

```powershell
pytest
# or use the included test scripts: scripts\run_tests.ps1
```

## Configuration details
- FHIR and external endpoints: configure in `.env` (from `config/local.env.template`) or `config/*.json` as needed.
- Logging & audit: `services/audit_logger.py` provides audit logging utilities.
- Sessions: session data resides under `flask_session/` and `instance/flask_session/` for local testing.

## Development notes
- Add calculators or models: implement modules under `services/` and expose them via `routes/api_routes.py`.
- UI templates: modify `templates/` (Jinja2) to extend or add new pages.
- Tests: add unit tests to `tests/` and run with `pytest`.

## Deployment recommendations
- Development: `python APP.py` is sufficient for local development.
- Production: use `docker-compose.prod.yml` or run behind a WSGI server (gunicorn/uvicorn) in containers. Provide secrets via `.env` or an environment manager.
- CI: see `.github/workflows/` for example workflows.

## Troubleshooting & common issues
- FHIR connection failures: ensure `FHIR_SERVER_URL` and credentials in `.env` are correct; test connectivity with `services/fhir_client_service.py`.
- Dependency conflicts: use a fresh virtual environment and `pip install -r requirements.txt`.
- Session or upload issues: check disk space and permissions for `instance/` and `flask_session/`.

## Documentation
- User and verification documents are in `docs/`.
  - `docs/PRECISE-HBR.md`
  - `docs/PreciseHBR_Verification_Report.md`

## Next steps I can help with
- Translate this file into the primary `README.md` (overwrite) or keep both versions.
- Add example API calls (cURL / Postman collection) to demonstrate requests to `routes/api_routes.py`.
- Expand Docker deployment examples and production WSGI configuration.

If you'd like, I can now add cURL examples for the main API endpoints or produce an English-to-Chinese synchronized README pairing.
