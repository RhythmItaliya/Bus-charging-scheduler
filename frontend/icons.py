"""
frontend/icons.py  —  SVG icon library using Heroicons v2 outline.

All icons are from Heroicons v2 (https://heroicons.com/)
License: MIT — free to use commercially and personally.
Style: outline (24×24 viewBox, stroke-width 1.5, no fill).

WHY HEROICONS?
  - Modern, clean aesthetic used by Tailwind CSS / major SaaS products
  - Consistent style across all icons (same stroke width, same rounding)
  - MIT license — no attribution required
  - All icons use the same 24×24 viewBox → easy to scale uniformly

USAGE:
    from frontend.icons import icon

    # Icon only (returns HTML span with SVG inside)
    html = icon("bolt")

    # Icon + label text
    html = icon("bolt", label="Scheduler", size=20)

    # Custom colour
    html = icon("check_circle", colour="#28a745")

    # Render it in Streamlit
    st.markdown(html, unsafe_allow_html=True)
"""

from __future__ import annotations

# ── Heroicons v2 outline path data (24×24 viewBox) ───────────────────────────
#
# Format per icon: dict mapping name → tuple of path "d" strings
# (some icons need 2 <path> elements, e.g. MapPinIcon, Cog6ToothIcon)
#
# Source: https://github.com/tailwindlabs/heroicons/tree/master/src/24/outline
# Commit: v2.x stable — all paths verified against heroicons.com
# ─────────────────────────────────────────────────────────────────────────────

_PATHS: dict[str, list[str]] = {

    # ── Navigation / header ──────────────────────────────────────────────────
    # BoltIcon — used for app title + zap (stations tab)
    "bolt": [
        "m3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z"
    ],

    # Cog6ToothIcon — used for Weight Controls + Architecture tab
    "settings": [
        "M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 "
        "1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 "
        "1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 "
        "0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 "
        "0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 "
        "2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076"
        ".124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 "
        "1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-"
        "1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196"
        "-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247"
        "a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 "
        "6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 "
        "0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356"
        ".133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644"
        "-.869l.214-1.28Z",
        "M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
    ],

    # ArrowPathIcon — used for Reset weights button
    "reset": [
        "M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 "
        "3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 "
        "13.803-3.7l3.181 3.182m0-4.991v4.99"
    ],

    # MapPinIcon — used for station labels
    "map_pin": [
        "M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
        "M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z",
    ],

    # ── Tab / section headers ────────────────────────────────────────────────
    # ClipboardDocumentListIcon — Input tab
    "clipboard": [
        "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 "
        "2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 "
        "0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a"
        ".75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 "
        "13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124"
        ".08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-"
        "1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 "
        "1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008"
        "H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z"
    ],

    # TruckIcon — Per-Bus Timetable tab
    "bus": [
        "M8.25 18.75a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m3 0h6m-9 "
        "0H3.375a1.125 1.125 0 0 1-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 0 1-3 "
        "0m3 0a1.5 1.5 0 0 0-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 "
        "17.902 0 0 0-3.213-9.193 2.056 2.056 0 0 0-1.58-.86H14.25M16.5 "
        "18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 "
        "0 0 0-10.026 0 1.106 1.106 0 0 1-.987 1.106v7.635m12-6.677v6.677m0 "
        "4.5v-4.5m0 0h-12"
    ],

    # BoltIcon (alias) — Per-Station Order tab
    "zap": [
        "m3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z"
    ],

    # CubeTransparentIcon — Architecture tab
    "cube": [
        "m21 7.5-9-5.25L3 7.5m18 0-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 "
        "7.5v9l9 5.25m0-9v9"
    ],

    # ── Status banners ───────────────────────────────────────────────────────
    # CheckCircleIcon — valid schedule banner
    "check_circle": [
        "M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
    ],

    # ExclamationCircleIcon — invalid/violations banner
    "alert": [
        "M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z"
    ],

    # ── Metrics ──────────────────────────────────────────────────────────────
    # ClockIcon — Total Wait metric
    "clock": [
        "M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
    ],

    # ArrowTrendingUpIcon — Max Wait metric
    "trending_up": [
        "M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22"
        "m0 0-5.94-2.281m5.94 2.28-2.28 5.941"
    ],

    # UsersIcon — Buses scheduled metric
    "users": [
        "M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 "
        "4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786"
        "-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645"
        "-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 "
        "3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 "
        "1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z"
    ],

    # SignalIcon — Makespan / Activity metric
    "activity": [
        "M9.348 14.652a3.75 3.75 0 0 1 0-5.304m5.304 0a3.75 3.75 0 0 1 0 "
        "5.304m-7.425 2.121a6.75 6.75 0 0 1 0-9.546m9.546 0a6.75 6.75 0 0 1 "
        "0 9.546M5.106 18.894c-3.808-3.807-3.808-9.98 0-13.788m13.788 0c3.808 "
        "3.807 3.808 9.98 0 13.788M12 12h.008v.008H12V12Z"
    ],

    # ── Section labels ───────────────────────────────────────────────────────
    # MapIcon — Route section
    "route": [
        "M9 6.75V15m6-6v8.25m.503 3.498 4.875-2.437c.381-.19.622-.58.622-1.006"
        "V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 "
        "0L9.503 3.252a1.125 1.125 0 0 0-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 "
        "6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 "
        "1.006 0l4.994 2.497c.317.158.69.158 1.006 0Z"
    ],

    # BoltIcon — Stations / Plug section (reuse bolt for charging)
    "plug": [
        "m3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z"
    ],
}

# Default stroke colour — dark grey works on both white and light-grey Streamlit backgrounds.
# We use an explicit hex instead of "currentColor" because st.markdown() renders inside
# a shadow DOM where "currentColor" cannot inherit the page text colour.
_DEFAULT_STROKE = "#374151"   # Tailwind gray-700


def icon(name: str, label: str = "", size: int = 16,
         colour: str = _DEFAULT_STROKE) -> str:
    """
    Return an inline-flex HTML span containing a Heroicons v2 SVG icon
    and an optional text label to its right.

    All icons use the Heroicons v2 outline style:
      - viewBox 0 0 24 24
      - fill none, stroke-width 1.5
      - stroke-linecap round, stroke-linejoin round

    Works inside both st.markdown(unsafe_allow_html=True) and st.html().

    Args:
        name:   Key from _PATHS (e.g. "bolt", "check_circle", "map_pin").
        label:  Optional text displayed to the right of the icon.
        size:   Icon width and height in pixels (default 16).
        colour: Explicit SVG stroke colour (default #374151 dark-grey).

    Returns:
        HTML string — a <span> containing an <svg> and optionally a <span> label.

    Example:
        st.markdown(icon("bolt", "Bus Charging Scheduler", size=20), unsafe_allow_html=True)
    """
    paths = _PATHS.get(name, [])
    if not paths:
        # Unknown icon — fall back to a simple dot so layout doesn't break
        paths = ["M12 12m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0"]

    # Build <path> elements
    path_els = " ".join(
        f'<path stroke-linecap="round" stroke-linejoin="round" d="{d}"/>'
        for d in paths
    )

    # Build complete SVG element
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" '
        f'fill="none" '
        f'stroke="{colour}" '
        f'stroke-width="1.5" '
        f'style="vertical-align:middle;flex-shrink:0">'
        f'{path_els}'
        f'</svg>'
    )

    base = "display:inline-flex;align-items:center;line-height:1.4"
    if label:
        return (
            f'<span style="{base};gap:5px">'
            f'{svg}<span>{label}</span>'
            f'</span>'
        )
    return f'<span style="{base}">{svg}</span>'
