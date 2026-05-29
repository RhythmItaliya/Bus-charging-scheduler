# Deployment Strategy

**Purpose.** Get a public, working app onto Streamlit Community Cloud and keep it reproducible.

## Build and dependency reproducibility
A single `requirements.txt` pins `streamlit` and `pandas` (and `ortools` only if the CP-SAT
strategy is enabled). Streamlit Community Cloud installs from this file automatically, so the
hosted environment matches local. No Dockerfile or system packages are needed; keep the
dependency list minimal to minimise cold-start install time.

## Deployment steps
Push a public GitHub repo containing all code, `data/scenarios/`, tests, `README.md`, and
`ARCHITECTURE.md`, with no secrets committed. On share.streamlit.io, connect the repo, set the
main file to `app.py` and branch to `main`, and deploy. Confirm the build log installs
requirements and the app boots on the dropdown. Verify anonymous access in an incognito window.

## Configuration
There is no runtime configuration to inject — the app is fully driven by the committed scenario
files. If secrets were ever needed, they would go in Streamlit secrets, never in the repo;
`.streamlit/secrets.toml` is gitignored.

## CI (optional but recommended)
A GitHub Actions workflow running `pip install -r requirements.txt` and `pytest` on push gives
a green signal before deploy and guards against regressions. It is not required by the spec but
demonstrates engineering hygiene.

## Rollback and updates
Streamlit Cloud redeploys on push to the tracked branch, so rollback is `git revert` + push.
Re-submission of the form is allowed and the latest submission wins, so iterating after an
initial submit is safe.
