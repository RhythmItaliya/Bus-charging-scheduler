# Security Considerations

**Purpose.** Right-size security for a public, read-only demo while documenting what would
change at production scale.

## Current threat surface
The app is a public, read-only Streamlit page with no authentication, no user data, no writes,
and no secrets. The only inputs are the committed scenario files and the in-app weight sliders;
there is no user-supplied file upload or free-text that reaches code execution. The practical
risk surface is therefore minimal: denial-of-service via repeated recompute (mitigated by
caching and the tiny problem size) and supply-chain risk from dependencies.

## Controls in place
Keep the dependency list minimal and pinned to reduce supply-chain exposure. Never commit
secrets; `.streamlit/secrets.toml` and `.env` are gitignored. The engine performs no `eval`,
no shell-outs, and no network calls, so a malicious scenario file cannot escalate beyond a
parse/validation error. Input validation rejects malformed scenarios before they reach the
engine.

## What would change at production scale
If scenarios became user-uploaded or the engine became a public API, add: strict schema
validation with size limits, authentication and per-key rate limiting, request/response logging
with PII review (none today), and dependency scanning in CI. These are explicitly out of scope
for the assignment but noted so the design is not naïve about them.

## Data privacy
No personal data is processed; bus and operator identifiers are synthetic. There is nothing to
anonymise or retain, so data-retention and privacy obligations do not apply to the current
system.
