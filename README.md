# AI-Powered Real-Time API Failure Prediction

Predict API degradation before outages, explain probable causes, estimate cascading impact, and recommend preventive actions.

## Project status
Starter scaffold for a six-member datathon team. Modules are intentionally lightweight placeholders; implement them in separate branches.

## Architecture
1. Simulated APIs and telemetry
2. Telemetry ingestion and storage
3. Feature engineering and ML prediction
4. Dependency graph and root-cause analysis
5. Risk/decision engine
6. FastAPI backend + React dashboard

## Team ownership
- Lohith: integration, API contracts, backend entry point, releases
- Kishor: simulator and telemetry
- Namith: ML pipeline and model evaluation
- Mdha: dependency graph and root-cause analysis
- Meghana: React dashboard
- Parvathi: decision engine, tests, evaluation

## Quick start (backend scaffold)
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```
Open `http://127.0.0.1:8000/docs`.

## Branching workflow
Create one branch per feature, e.g. `feature/telemetry-simulator`. Push changes and open a pull request into `main`. Do not push directly to `main` after the scaffold is established.

## Important design rule
Agree on API contracts before implementing integrations. Use synthetic data initially; do not claim real-world prediction performance until evaluated on appropriate data.
