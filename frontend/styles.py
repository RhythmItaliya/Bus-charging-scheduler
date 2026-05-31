"""
frontend/styles.py  —  Global CSS injection for the Bus Charging Scheduler UI.

Call inject_css() once at app startup (after st.set_page_config).
All styling decisions live here; no scattered inline style= strings elsewhere.

Icons on tabs use Heroicons v2 outline paths (same library as icons.py).
Streamlit tab labels only accept plain text, so we inject icons via
CSS ::before pseudo-elements keyed on [data-testid="stTab"]:nth-of-type(n).
"""

from __future__ import annotations

import streamlit as st

# ── Heroicons v2 SVG data-URIs for the 4 tab icons ───────────────────────────
# Tab 1 — Input:         ClipboardDocumentListIcon
# Tab 2 — Per-Bus:       TruckIcon
# Tab 3 — Per-Station:   BoltIcon
# Tab 4 — Architecture:  CubeTransparentIcon
#
# Each SVG is URL-encoded so it can be used as a CSS background-image data-URI.
# Colour = #374151 (Tailwind gray-700) — readable on both light and dark themes.
# ─────────────────────────────────────────────────────────────────────────────

def _tab_icon_uri(path_d: str) -> str:
    """
    Wrap a Heroicons v2 path in a full SVG and URL-encode it for use as
    a CSS background-image data URI.
    """
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='13' height='13' "
        "viewBox='0 0 24 24' fill='none' stroke='%23374151' "
        "stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'>"
        f"<path d='{path_d}'/>"
        "</svg>"
    )
    # Simple percent-encode for data URI (only the characters that break CSS)
    encoded = (
        svg
        .replace(" ", "%20")
        .replace("#", "%23")
        .replace("<", "%3C")
        .replace(">", "%3E")
        .replace("'", "%27")
        .replace('"', "%22")
    )
    return f"url(\"data:image/svg+xml,{encoded}\")"


# Heroicons v2 outline path data — same as icons.py (duplicated here to avoid import)
_TAB_PATHS = [
    # Tab 1 — ClipboardDocumentListIcon (Input)
    (
        "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108"
        "c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0"
        "c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 "
        "2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 "
        "1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 "
        "4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 "
        ".621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0"
        "-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008"
        "v.008H6.75V15Zm0 3h.008v.008H6.75V18Z"
    ),
    # Tab 2 — TruckIcon (Per-Bus Timetable)
    (
        "M8.25 18.75a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m3 0h6m-9 "
        "0H3.375a1.125 1.125 0 0 1-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 0 1-3 "
        "0m3 0a1.5 1.5 0 0 0-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 "
        "17.902 0 0 0-3.213-9.193 2.056 2.056 0 0 0-1.58-.86H14.25M16.5 "
        "18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 "
        "0 0 0-10.026 0 1.106 1.106 0 0 1-.987 1.106v7.635m12-6.677v6.677m0 "
        "4.5v-4.5m0 0h-12"
    ),
    # Tab 3 — BoltIcon (Per-Station Order)
    "m3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z",
    # Tab 4 — CubeTransparentIcon (Architecture)
    "m21 7.5-9-5.25L3 7.5m18 0-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9",
]


def _build_tab_css() -> str:
    """Build the CSS ::before rules for all 4 tab icons."""
    lines = []
    for i, path_d in enumerate(_TAB_PATHS, start=1):
        uri = _tab_icon_uri(path_d)
        lines.append(f"""
    [data-testid="stTab"]:nth-of-type({i}) p::before {{
        content: "";
        display: inline-block;
        width: 13px; height: 13px;
        margin-right: 5px;
        vertical-align: middle;
        background-repeat: no-repeat;
        background-size: contain;
        background-image: {uri};
    }}""")
    return "\n".join(lines)


_GLOBAL_CSS = f"""
<style>
/* ── Wait cell colour coding in the timetable dataframe ──────────────── */
.wait-yellow {{ background-color: #fff3cd; font-weight: bold; }}
.wait-red    {{ background-color: #f8d7da; font-weight: bold; }}

/* ── Shared icon-label helper: icon + text inline, no block margin ───── */
.icon-label {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    line-height: 1.4;
    font-weight: 600;
    margin: 0;
}}

/* ── Tighter metric cards ─────────────────────────────────────────────── */
[data-testid="stMetric"] {{ padding: 0.3rem 0.5rem; }}

/* ── Station expander heading bold ───────────────────────────────────── */
[data-testid="stExpander"] summary {{ font-weight: 600; }}

/* ── Score metric in sidebar — make it stand out ────────────────────── */
[data-testid="stSidebar"] [data-testid="stMetric"] {{
    background: rgba(59,130,246,0.08);
    border-radius: 6px;
    border: 1px solid rgba(59,130,246,0.2);
}}

{_build_tab_css()}
</style>
"""


def inject_css() -> None:
    """Inject all global CSS into the Streamlit page.

    Must be called once after st.set_page_config.
    Adds tab icons, wait-cell colour coding, metric card padding.
    """
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)
