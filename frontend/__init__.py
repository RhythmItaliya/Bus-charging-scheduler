"""
frontend/ — Streamlit UI components for the Bus Charging Scheduler.

Modules:
    icons   — SVG icon library + icon() helper
    styles  — Global CSS injection (inject_css)
    sidebar — Sidebar: scenario selector + weight sliders
    tabs    — Three main tab views (input, timetable, station)

All Streamlit imports stay inside this package.
The scheduler/ engine package has zero knowledge of this package.
"""
