"""
scheduler/logger.py — Coloured terminal logger for the Bus Charging Scheduler.

Designed for live assignment demonstrations: each log line is structured,
colour-coded by severity, and includes a timestamp so the terminal output
tells the full scheduling story at a glance.

Usage:
    from scheduler.logger import log, LOG_LEVEL
    log.info("Scheduler started")
    log.scenario("Scenario 1 — Even Spacing", buses=20, stations=4)
    log.rule_check("H1 No Overload", station="A", chargers=2, buses=4, status="PASS")
    log.schedule("bus-BK-01", station="A", wait=0, start="21:00", end="21:25")
    log.metric("Total objective", value=4579.3)
    log.success("All 103 tests passed")
    log.warn("Operator fairness weight is zero — S2 inactive")
    log.error("Hard rule H1 violated at station B")

No external dependencies — uses only Python stdlib ANSI codes.
Set LOG_LEVEL = "DEBUG" | "INFO" | "WARN" | "ERROR" to filter output.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------
# ANSI colour codes (auto-disabled on non-TTY / Windows without ANSI support)
# ---------------------------------------------------------------------------

_NO_COLOR = not sys.stdout.isatty() or os.environ.get("NO_COLOR", "")

def _c(code: str) -> str:
    return "" if _NO_COLOR else f"\033[{code}m"

# Foreground colours
_RESET  = _c("0")
_BOLD   = _c("1")
_DIM    = _c("2")

_GREY   = _c("90")
_RED    = _c("91")
_GREEN  = _c("92")
_YELLOW = _c("93")
_BLUE   = _c("94")
_MAGENTA= _c("95")
_CYAN   = _c("96")
_WHITE  = _c("97")

# Background highlights
_BG_RED    = _c("41")
_BG_GREEN  = _c("42")
_BG_YELLOW = _c("43")
_BG_BLUE   = _c("44")

# ---------------------------------------------------------------------------
# Log level filtering
# ---------------------------------------------------------------------------

_LEVELS = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3}
LOG_LEVEL: str = os.environ.get("BCS_LOG_LEVEL", "INFO").upper()


def _should_log(level: str) -> bool:
    return _LEVELS.get(level, 1) >= _LEVELS.get(LOG_LEVEL, 1)


# ---------------------------------------------------------------------------
# Timestamp helper
# ---------------------------------------------------------------------------

def _ts() -> str:
    return f"{_DIM}{datetime.now().strftime('%H:%M:%S')}{_RESET}"


# ---------------------------------------------------------------------------
# Core printer
# ---------------------------------------------------------------------------

def _print(level_tag: str, message: str, **fields: Any) -> None:
    """Format and print one log line."""
    extras = "  ".join(
        f"{_DIM}{k}{_RESET}={_CYAN}{v}{_RESET}"
        for k, v in fields.items()
    )
    line = f"{_ts()}  {level_tag}  {message}"
    if extras:
        line += f"  {extras}"
    print(line)


# ---------------------------------------------------------------------------
# Public log namespace
# ---------------------------------------------------------------------------

class _Logger:
    """Structured coloured logger — call log.<method>() anywhere."""

    # ── Severity levels ───────────────────────────────────────────────────

    def debug(self, msg: str, **kw: Any) -> None:
        if not _should_log("DEBUG"):
            return
        tag = f"{_GREY}[DBG]{_RESET}"
        _print(tag, f"{_GREY}{msg}{_RESET}", **kw)

    def info(self, msg: str, **kw: Any) -> None:
        if not _should_log("INFO"):
            return
        tag = f"{_BLUE}[INF]{_RESET}"
        _print(tag, msg, **kw)

    def warn(self, msg: str, **kw: Any) -> None:
        if not _should_log("WARN"):
            return
        tag = f"{_YELLOW}[WRN]{_RESET}"
        _print(tag, f"{_YELLOW}{msg}{_RESET}", **kw)

    def error(self, msg: str, **kw: Any) -> None:
        if not _should_log("ERROR"):
            return
        tag = f"{_RED}{_BOLD}[ERR]{_RESET}"
        _print(tag, f"{_RED}{_BOLD}{msg}{_RESET}", **kw)

    def success(self, msg: str, **kw: Any) -> None:
        if not _should_log("INFO"):
            return
        tag = f"{_GREEN}{_BOLD}[ OK]{_RESET}"
        _print(tag, f"{_GREEN}{_BOLD}{msg}{_RESET}", **kw)

    # ── Domain-specific structured log lines ──────────────────────────────

    def scenario(self, name: str, **kw: Any) -> None:
        """Log a scenario being loaded — shown prominently in the terminal."""
        if not _should_log("INFO"):
            return
        bar = f"{_MAGENTA}{'─' * 60}{_RESET}"
        print(bar)
        tag = f"{_MAGENTA}{_BOLD}[SCN]{_RESET}"
        _print(tag, f"{_MAGENTA}{_BOLD}{name}{_RESET}", **kw)
        print(bar)

    def rule_check(self, rule: str, *, status: str, **kw: Any) -> None:
        """Log the result of a hard or soft rule evaluation."""
        if not _should_log("INFO"):
            return
        if status.upper() in ("PASS", "OK", "✓"):
            colour = _GREEN
            mark = "✓"
        elif status.upper() in ("SKIP", "N/A"):
            colour = _GREY
            mark = "—"
        else:
            colour = _RED
            mark = "✗"
        tag = f"{colour}[RUL]{_RESET}"
        _print(tag, f"{colour}{mark} {rule}{_RESET}", status=status, **kw)

    def schedule(self, bus_id: str, *, station: str, wait: int, start: str, end: str, **kw: Any) -> None:
        """Log one bus charge event — used when streaming schedule output."""
        if not _should_log("DEBUG"):
            return
        wait_colour = _RED if wait > 30 else (_YELLOW if wait > 0 else _GREEN)
        tag = f"{_CYAN}[EVT]{_RESET}"
        _print(
            tag,
            f"{_WHITE}{bus_id}{_RESET} @ {_CYAN}{station}{_RESET}",
            wait=f"{wait_colour}{wait} min{_RESET}",
            start=start,
            end=end,
            **kw,
        )

    def metric(self, name: str, *, value: Any, **kw: Any) -> None:
        """Log a summary metric (objective score, wait, etc.)."""
        if not _should_log("INFO"):
            return
        tag = f"{_BLUE}[MET]{_RESET}"
        _print(tag, f"{_WHITE}{name}{_RESET}", value=f"{_YELLOW}{value}{_RESET}", **kw)

    def separator(self, title: str = "") -> None:
        """Print a visual separator — useful between scheduling phases."""
        if title:
            side = "─" * 20
            print(f"{_DIM}{side} {title} {side}{_RESET}")
        else:
            print(f"{_DIM}{'─' * 60}{_RESET}")

    def header(self, title: str) -> None:
        """Print a bold boxed header — use at demo start."""
        width = max(len(title) + 4, 52)
        border = "═" * width
        pad = " " * ((width - len(title) - 2) // 2)
        print(f"\n{_MAGENTA}{_BOLD}╔{border}╗{_RESET}")
        print(f"{_MAGENTA}{_BOLD}║{pad} {title} {pad}║{_RESET}")
        print(f"{_MAGENTA}{_BOLD}╚{border}╝{_RESET}\n")


# ---------------------------------------------------------------------------
# Module-level singleton — import and use directly
# ---------------------------------------------------------------------------

log = _Logger()
