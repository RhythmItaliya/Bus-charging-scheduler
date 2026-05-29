# Submission Checklist

**Purpose.** The final gate before submitting via the Google Form (deadline June 2).

## Code and data
- [ ] All code committed to a **public** GitHub repo
- [ ] `data/scenarios/` contains all five scenarios encoded **exactly from the PDF**
  - Verify KB operators: KB-01=freshbus, KB-02=flixbus, KB-03=kpn (NOT kpn/freshbus/flixbus)
  - Run `python3 -c "..."` scenario verification script or `pytest tests/test_e2e.py`
- [ ] `requirements.txt` installs cleanly (`pip install -r requirements.txt`)
- [ ] `pytest` is fully green (103 tests, ~0.7 s)
- [ ] `.gitignore` excludes `__pycache__`, `.venv`, `.pytest_cache`, `secrets.toml`

## Docs
- [ ] `README.md` covers: run-locally, how to change a weight (code example), how to add a rule (code example)
- [ ] `ARCHITECTURE.md` covers: framework choice + why, data-structure design, anticipated-changes table, weight-change example, add-a-rule example, assumptions
- [ ] `docs/` tree is included in the repo

## Hosting
- [ ] Public Streamlit URL (`https://share.streamlit.io/...`) loads and shows the scenario dropdown
- [ ] All five scenarios render all three views (Input, Per-Bus, Per-Station) without errors
- [ ] Verified in an incognito / private browser window
- [ ] No secrets or API keys in the repo

## Form fields (https://forms.gle/51xrFoUeGj9PD6KQA)
- Hosted Streamlit app URL (must be public)
- GitHub repo URL (must be public)
- Scheduling approach: *event-driven greedy + pluggable weighted rule registry; Strategy interface allows swap to CP-SAT without touching rules, data model, or UI*
- Brief build notes: *Python stdlib engine, Streamlit UI, 103 tests, 5 scenarios, all invariants validated post-schedule*

Re-submit if anything changes — the form accepts multiple submissions and uses the latest.

## Final sanity pass (do this on the live hosted URL, not localhost)
- [ ] Scenario 1: 20 buses, all have ≥ 2 charge events, no validation errors
- [ ] Scenario 2: bunched buses create visible wait times at inner stations
- [ ] Scenario 3: only 14 buses, 4 KB buses with wide spacing
- [ ] Scenario 4: operator weight=2.0 auto-loads; dragging slider changes objective breakdown
- [ ] Scenario 5: all 20 buses, maximum waits at B and C, no validation errors
- [ ] Reset button restores slider to scenario defaults
