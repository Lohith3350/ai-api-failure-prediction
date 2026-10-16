# Team workflow

1. Lohith creates the GitHub repository and pushes this scaffold to `main`.
2. Each member clones the repository and creates a feature branch.
3. Members commit only their module and tests.
4. Push the branch and open a pull request to `main`.
5. Lohith reviews interfaces, runs tests, resolves conflicts, and merges.
6. Never commit `.env`, credentials, virtual environments, `node_modules`, or large raw datasets.

Branch names:
- `feature/telemetry-simulator`
- `feature/ml-prediction`
- `feature/root-cause`
- `feature/decision-engine`
- `feature/dashboard`
- `feature/integration`

Commands:
```bash
git switch main
git pull origin main
git switch -c feature/your-module
# make changes
git add .
git commit -m "Add <module>"
git push -u origin feature/your-module
```
