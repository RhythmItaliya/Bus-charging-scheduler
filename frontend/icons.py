"""
frontend/icons.py — SVG icon library for the Bus Charging Scheduler UI.

All icons are Heroicons v2 / Feather Icons, viewBox="0 0 24 24", stroke-only.
No emoji, no external CDN — everything is self-contained inline SVG.

Usage:
    from frontend.icons import icon

    st.markdown(icon("bolt", "Bus Charging Scheduler"), unsafe_allow_html=True)
    st.markdown(icon("clock"), unsafe_allow_html=True)   # icon only, no label
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Raw SVG strings — keyed by semantic name.
# Width/height are set to 16×16 by default; bolt uses 20×20 for the header.
# ---------------------------------------------------------------------------

ICONS: dict[str, str] = {
    # ── Navigation / header ─────────────────────────────────────────────────
    "bolt": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>'
    ),
    "settings": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83'
        'l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0'
        'v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83'
        '-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4'
        'h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83'
        '-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0'
        'v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83'
        ' 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4'
        'h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>'
    ),
    "reset": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="1 4 1 10 7 10"/>'
        '<path d="M3.51 15a9 9 0 1 0 .49-3.5"/></svg>'
    ),
    "map_pin": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>'
        '<circle cx="12" cy="10" r="3"/></svg>'
    ),
    # ── Tab / section headers ────────────────────────────────────────────────
    "clipboard": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2'
        'V6a2 2 0 0 1 2-2h2"/>'
        '<rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>'
    ),
    "bus": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="1" y="3" width="15" height="13"/>'
        '<polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/>'
        '<circle cx="5.5" cy="18.5" r="2.5"/>'
        '<circle cx="18.5" cy="18.5" r="2.5"/></svg>'
    ),
    "zap": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>'
    ),
    # ── Status banners ───────────────────────────────────────────────────────
    "check_circle": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" '
        'viewBox="0 0 24 24" fill="none" stroke="#28a745" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>'
        '<polyline points="22 4 12 14.01 9 11.01"/></svg>'
    ),
    "alert": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" '
        'viewBox="0 0 24 24" fill="none" stroke="#dc3545" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/>'
        '<line x1="12" y1="8" x2="12" y2="12"/>'
        '<line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
    ),
    # ── Metrics ──────────────────────────────────────────────────────────────
    "clock": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/>'
        '<polyline points="12 6 12 12 16 14"/></svg>'
    ),
    "trending_up": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>'
        '<polyline points="17 6 23 6 23 12"/></svg>'
    ),
    "users": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>'
        '<circle cx="9" cy="7" r="4"/>'
        '<path d="M23 21v-2a4 4 0 0 0-3-3.87"/>'
        '<path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>'
    ),
    "activity": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>'
    ),
    # ── Section labels ───────────────────────────────────────────────────────
    "route": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="5" cy="6" r="3"/>'
        '<circle cx="19" cy="18" r="3"/>'
        '<path d="M5 9v12M5 9a6 6 0 0 0 6 6h3a6 6 0 0 1 6 6"/></svg>'
    ),
    "plug": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M18 6L6 18"/>'
        '<path d="M7 17H4a2 2 0 0 1-2-2v-4l3-3"/>'
        '<path d="M9.5 14.5L14 10l5 5"/>'
        '<path d="M17 7h3a2 2 0 0 1 2 2v4l-3 3"/>'
        '<line x1="8" y1="8" x2="8.01" y2="8"/>'
        '<line x1="16" y1="16" x2="16.01" y2="16"/></svg>'
    ),
}


# ---------------------------------------------------------------------------
# Rendering helper
# ---------------------------------------------------------------------------

# Default stroke colour for icons rendered inside st.html() iframes.
# st.html() creates a sandboxed shadow DOM so "currentColor" cannot inherit
# from the page's text colour — an explicit hex value is required.
_DEFAULT_STROKE = "#374151"  # Tailwind gray-700 — readable on white and light grey


def icon(name: str, label: str = "", size: int = 16, colour: str = _DEFAULT_STROKE) -> str:
    """Return an inline-flex HTML span with an SVG icon beside optional text.

    The SVG is given an explicit width/height (default 16 px) and
    ``vertical-align:middle`` so it sits on the text baseline regardless of
    the surrounding font size.  Gap between icon and label is 4 px.

    Works correctly in both ``st.markdown(unsafe_allow_html=True)`` and
    ``st.html()``.  Inside ``st.html()``, ``stroke="currentColor"`` cannot
    inherit from the page, so ``colour`` replaces it with an explicit hex.

    Args:
        name:   Key from the ICONS dict (e.g. "bolt", "bus").
        label:  Optional text to display to the right of the icon.
        size:   Icon width and height in pixels (default 16).
        colour: Explicit stroke colour (default #374151 dark grey).

    Returns:
        An HTML string containing an inline SVG span.
    """
    import re

    raw = ICONS.get(name, "")
    # Override width/height for size= parameter
    svg = re.sub(r'width="\d+"',  f'width="{size}"',  raw, count=1)
    svg = re.sub(r'height="\d+"', f'height="{size}"', svg, count=1)
    # Replace stroke="currentColor" with an explicit colour that works everywhere
    svg = svg.replace('stroke="currentColor"', f'stroke="{colour}"')
    # Ensure vertical alignment
    svg = svg.replace("<svg ", '<svg style="vertical-align:middle;flex-shrink:0" ', 1)

    base = "display:inline-flex;align-items:center;line-height:1.4"
    if label:
        return f'<span style="{base};gap:4px">{svg}<span>{label}</span></span>'
    return f'<span style="{base}">{svg}</span>'
