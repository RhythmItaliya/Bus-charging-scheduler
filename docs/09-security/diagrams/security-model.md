# Diagram — Security Threat Model

```mermaid
flowchart TD
    subgraph Internet["Internet / Public"]
        Browser["Browser (anonymous user)"]
    end

    subgraph Cloud["Streamlit Community Cloud (managed hosting)"]
        App["app.py (read-only Streamlit process)"]
        subgraph Storage["Static assets (read-only)"]
            JSON["data/scenarios/*.json"]
            Py["scheduler/*.py"]
            Front["frontend/*.py"]
        end
    end

    subgraph Threats["Threat surface"]
        T1["T1: Malicious user input"]
        T2["T2: Dependency vulnerability"]
        T3["T3: Secret exposure"]
        T4["T4: Data exfiltration"]
        T5["T5: Denial of service"]
    end

    Browser -->|"HTTPS GET / WebSocket"| App
    App -->|reads| JSON
    App -->|imports| Py
    App -->|imports| Front

    T1 -.->|"mitigated: no user file upload;\n weights are float sliders only"| App
    T2 -.->|"mitigated: pinned requirements.txt;\n minimal deps (streamlit, pandas, rich)"| Py
    T3 -.->|"mitigated: .gitignore covers .env;\n no API keys, no auth"| Storage
    T4 -.->|"mitigated: no database, no PII;\n only pre-encoded scenario JSONs"| JSON
    T5 -.->|"mitigated: st.cache_data caches\n per (scenario,weights) tuple"| App
```

## Threat register

| ID | Threat | Status | Control |
|----|--------|--------|---------|
| T1 | Malicious user input | **Mitigated** | Weights are `st.slider` (float, min=0, max=5). No free-text input, no file upload. Scenario selection is a fixed dropdown from bundled files only. |
| T2 | Dependency vulnerability (CVE) | **Accepted (low risk)** | All three deps (streamlit, pandas, rich) are pinned in `requirements.txt`. No network calls inside engine. |
| T3 | Secret / credential exposure | **Mitigated** | `.gitignore` excludes `.env`, `secrets.toml`, `*.pem`. App requires zero API keys. |
| T4 | Data exfiltration | **N/A** | No user data is stored. Scenario files are static public JSON. No database, no auth, no PII. |
| T5 | DoS via expensive schedule runs | **Mitigated** | `@st.cache_data` on `_cached_schedule()` de-duplicates runs. Max 20 buses × 4 stations × ~4 plans each = bounded O(1) work. |

## If the threat surface grows

These controls would need revisiting if the app were extended to:

- Accept **user-uploaded JSON** → input sanitisation + size limit needed
- Expose a **REST API** → authentication + rate limiting needed
- Store **session data** → encryption at rest + GDPR review needed
- Move to **multi-tenant hosting** → process isolation needed
