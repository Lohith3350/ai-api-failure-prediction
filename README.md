# AI-Powered Real-Time API Failure Prediction

Predict API degradation before outages, explain probable causes, estimate cascading impact, and recommend preventive actions.

## Project Status

Starter scaffold for a six-member datathon team. Modules are intentionally lightweight placeholders and will be implemented in separate feature branches.

## Architecture

1. Simulated APIs and telemetry
2. Telemetry ingestion and storage
3. Feature engineering and machine learning prediction
4. Dependency graph and root-cause analysis
5. Risk and decision engine
6. FastAPI backend and React dashboard

## Team Ownership

- **Lohith:** Integration, API contracts, backend entry point, releases
- **Kishor:** API simulator and telemetry
- **Namith:** ML pipeline, feature engineering, and model evaluation
- **Medha:** Dependency graph and root-cause analysis
- **Meghana:** React dashboard
- **Parvathi:** Decision engine, testing, and evaluation

## Quick Start — Backend

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r backend/requirements.txt
```

Start the backend:

```powershell
uvicorn backend.app.main:app --reload
```

Open the API documentation at http://127.0.0.1:8000/docs.

## Branching Workflow

Create a separate feature branch for each module, such as `feature/telemetry-simulator`.

Push changes to the corresponding branch and open a pull request into `main`. Do not push feature changes directly to `main`.

## Important Design Rules

- Agree on API contracts before integrating modules.
- Use synthetic telemetry data during initial development.
- Evaluate the model before making claims about real-world prediction accuracy.
- Test integrations before merging pull requests into `main`.