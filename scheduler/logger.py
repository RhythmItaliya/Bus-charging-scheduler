"""
scheduler/logger.py  —  Beautiful coloured terminal logger using the 'rich' library.

WHY rich?
  The 'rich' library (already bundled with Streamlit) prints panels, tables,
  and coloured text to the terminal.  It makes the scheduling process very easy
  to read and explain — great for live demos in interviews.

HOW TO USE:
    from scheduler.logger import log

    log.info("Any message", key="value")       # blue  [INF]
    log.warn("Warning message", key="value")   # yellow [WRN]
    log.error("Error message")                 # red   [ERR]
    log.success("Done!")                       # green [ OK]
    log.scenario("Scenario name", buses=20)    # magenta panel
    log.schedule_table("A", slots)             # rich table
    log.separator("Section name")              # horizontal rule

PDF reference: The assignment asks for clear output showing the scheduling process.
               A good terminal log helps you explain each step in the interview.

Third-party tool: 'rich' (https://github.com/Textualize/rich)
  - Already installed as part of Streamlit's dependencies
  - Provides: Console, Panel, Table, Rule, Text, Spinner
  - Used here to make the scheduling process visually clear
"""

from __future__ import annotations

import os
from typing import Any

from scheduler.config import CONFIG

# ── rich imports ──────────────────────────────────────────────────────────────
# 'rich' is a Python library for beautiful terminal output.
# It is automatically installed when you install Streamlit.
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme

# ── Custom colour theme for this project ──────────────────────────────────────
# Each key is a style name we use in log messages like "[info]text[/info]".
# Colours chosen to match the assignment's green/red validation banner colours.
_THEME = Theme({
    "info":      "bold bright_blue",
    "warn":      "bold yellow",
    "error":     "bold red",
    "success":   "bold bright_green",
    "scenario":  "bold magenta",
    "metric":    "bold cyan",
    "schedule":  "white",
    "debug":     "dim white",
    "rule_pass": "bright_green",
    "rule_fail": "bold red",
    "label":     "dim white",
    "value":     "bright_cyan",
    "bus_id":    "bright_white bold",
    "station":   "bright_cyan",
    "wait_ok":   "bright_green",
    "wait_med":  "yellow",
    "wait_bad":  "bold red",
})

# One global Console — all output goes through this single object.
# stderr=False means output goes to stdout (normal terminal).
# highlight=False stops rich from auto-coloring numbers (we control colours).
_con = Console(theme=_THEME, highlight=False)

# ── Log level filtering ────────────────────────────────────────────────────────
# Env var name and default level come from CONFIG so they are one value, one place.
# Set BCS_LOG_LEVEL=DEBUG in your terminal to see debug messages.
_LEVELS = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3}
_LOG_LEVEL = os.environ.get(CONFIG.log_level_env_var, CONFIG.default_log_level).upper()


def _should_log(level: str) -> bool:
    """Return True if this level should be printed (based on CONFIG.log_level_env_var)."""
    return _LEVELS.get(level, 1) >= _LEVELS.get(_LOG_LEVEL, 1)


def _extras_str(fields: dict) -> str:
    """
    Convert keyword fields like bus='BK-01', wait=10 into a coloured string:
    '  [label]bus[/label]=[value]BK-01[/value]  [label]wait[/label]=[value]10[/value]'
    """
    parts = [f"[label]{k}[/label]=[value]{v}[/value]" for k, v in fields.items()]
    return "  " + "  ".join(parts) if parts else ""


# ── Logger class ──────────────────────────────────────────────────────────────

class _Logger:
    """
    Structured coloured logger for the Bus Charging Scheduler.

    Uses the 'rich' library to produce beautiful terminal output.
    Every method corresponds to one type of log event in the scheduling process.

    INTERVIEW TIP: When you run 'python -m scheduler.engine scenario_1.json',
    this logger shows exactly what the algorithm is doing at each step.
    You can point to each section and explain it to the interviewer.
    """

    # ── Standard severity levels ───────────────────────────────────────────

    def debug(self, msg: str, **kw: Any) -> None:
        """Print a debug message (only visible when BCS_LOG_LEVEL=DEBUG)."""
        if not _should_log("DEBUG"):
            return
        _con.print(f"[debug]  [DBG] {msg}{_extras_str(kw)}[/debug]")

    def info(self, msg: str, **kw: Any) -> None:
        """
        Print a blue informational message.

        Example output:
          [INF] Scenario loaded  name=Scenario 1  buses=20
        """
        if not _should_log("INFO"):
            return
        _con.print(f"[info][INF][/info] {msg}{_extras_str(kw)}")

    def warn(self, msg: str, **kw: Any) -> None:
        """Print a yellow warning message."""
        if not _should_log("WARN"):
            return
        _con.print(f"[warn][WRN] {msg}{_extras_str(kw)}[/warn]")

    def error(self, msg: str, **kw: Any) -> None:
        """Print a bold red error message."""
        if not _should_log("ERROR"):
            return
        _con.print(f"[error][ERR] {msg}{_extras_str(kw)}[/error]")

    def success(self, msg: str, **kw: Any) -> None:
        """Print a bold green success message."""
        if not _should_log("INFO"):
            return
        _con.print(f"[success][ OK] {msg}{_extras_str(kw)}[/success]")

    # ── Domain-specific structured log lines ──────────────────────────────

    def scenario(self, name: str, **kw: Any) -> None:
        """
        Print a magenta Panel box for a scenario being loaded.

        WHY A PANEL? — It makes the start of each scenario very visible in the
        terminal.  In an interview demo, the panel shows the interviewer exactly
        which scenario is running and what the parameters are.

        Example output:
        ╭─────── Scenario ────────────────────────────────────╮
        │  Scenario 1 — Even Spacing                          │
        │  buses = 20   stations = 4   weights = 1.0/1.0/1.0  │
        ╰─────────────────────────────────────────────────────╯
        """
        if not _should_log("INFO"):
            return
        # Build the content lines: name on top, then key=value pairs
        lines = [f"[bold white]{name}[/bold white]"]
        for k, v in kw.items():
            lines.append(f"  [label]{k}[/label] = [value]{v}[/value]")
        panel = Panel(
            "\n".join(lines),
            title="[scenario]Scenario[/scenario]",
            border_style="magenta",
            box=box.DOUBLE_EDGE,
            padding=(0, 1),
        )
        _con.print(panel)

    def header(self, title: str) -> None:
        """
        Print a bold panel at the start of a CLI run.

        Example output:
        ╔══════════════════════════════════════════╗
        ║   Bus Charging Scheduler — Engine Demo   ║
        ╚══════════════════════════════════════════╝
        """
        _con.print(
            Panel(
                f"[bold white]{title}[/bold white]",
                box=box.DOUBLE_EDGE,
                border_style="bright_blue",
                padding=(0, 2),
            )
        )

    def separator(self, title: str = "") -> None:
        """
        Print a horizontal dividing line with an optional label.

        Example output:  ──────── Validation ────────
        """
        if title:
            _con.rule(f"[dim]{title}[/dim]", style="dim white")
        else:
            _con.rule(style="dim white")

    def rule_check(self, rule: str, *, status: str, **kw: Any) -> None:
        """
        Print a coloured PASS / FAIL line for a hard rule check.

        PDF reference: Page 3 — "Hard rules that must always hold" (H1–H4)

        Green ✓ = rule passed.   Red ✗ = rule failed (schedule is invalid).

        Example output:
          ✓ H1 Range Rule   status=PASS
          ✗ H3 Charger Rule  status=FAIL  station=B  concurrent=2
        """
        if not _should_log("INFO"):
            return
        if status.upper() in ("PASS", "OK", "✓"):
            mark = "[rule_pass]✓[/rule_pass]"
            style = "rule_pass"
        else:
            mark = "[rule_fail]✗[/rule_fail]"
            style = "rule_fail"
        _con.print(f"  {mark} [{style}]{rule}[/{style}]{_extras_str(kw)}")

    def schedule(self, bus_id: str, *, station: str, wait: int,
                 start: str, end: str, **kw: Any) -> None:
        """
        Print one charge event: which bus, which station, how long it waited.

        PDF reference: Page 9 — "per-bus timetable: charging stations used,
                                  time at each, wait (if any), final arrival"

        Colour coding of wait time:
          Green  = 0 min wait  (bus charged immediately)
          Yellow = 1–30 min    (acceptable queue)
          Red    = >30 min     (long queue — high penalty in S1 rule)
        """
        if not _should_log("DEBUG"):
            return
        # Colour the wait based on how long it is (thresholds from CONFIG)
        if wait > CONFIG.wait_crit_min:
            wait_str = f"[wait_bad]{wait} min[/wait_bad]"
        elif wait >= CONFIG.wait_warn_min:
            wait_str = f"[wait_med]{wait} min[/wait_med]"
        else:
            wait_str = f"[wait_ok]{wait} min[/wait_ok]"

        _con.print(
            f"  [schedule][EVT][/schedule] "
            f"[bus_id]{bus_id}[/bus_id] "
            f"@ [station]{station}[/station]  "
            f"wait={wait_str}  "
            f"[label]start[/label]=[value]{start}[/value]  "
            f"[label]end[/label]=[value]{end}[/value]"
            + _extras_str(kw)
        )

    def metric(self, name: str, *, value: Any, **kw: Any) -> None:
        """
        Print a summary metric (objective score, total wait, etc.).

        PDF reference: Page 4 — "What to optimize for" — three soft rules:
          S1 Individual bus wait  →  IndividualWaitRule
          S2 Operator fairness    →  OperatorRule
          S3 Overall makespan     →  OverallRule

        Example output:
          [MET] IndividualWaitRule  value=900.0
          [MET] OperatorRule        value=2864.3
          [MET] TOTAL               value=4579.3
        """
        if not _should_log("INFO"):
            return
        _con.print(
            f"[metric][MET][/metric] [bold white]{name}[/bold white]"
            f"  [label]value[/label]=[metric]{value}[/metric]"
            + _extras_str(kw)
        )

    def schedule_table(self, station: str, slots: list) -> None:
        """
        Print a rich Table showing the charge order at one station.

        WHY A TABLE? — Tables make it very easy to read during a live demo.
        The interviewer can see at a glance: who charges, in what order,
        how long they waited.

        PDF reference: Page 9 — "per-station view: for each of A, B, C, D,
                                  show the order in which buses charged there"

        Example output:
        ┌────────────── Station A ──────────────┐
        │  # │ Bus ID      │ Wait │ Start  │ End  │
        │  1 │ bus-BK-01   │   0  │ 20:40  │ 21:05│
        │  2 │ bus-BK-02   │  10  │ 21:05  │ 21:30│
        └────────────────────────────────────────┘
        """
        if not _should_log("INFO"):
            return
        if not slots:
            _con.print(f"  [dim]Station {station}: no charges[/dim]")
            return

        # Import here to avoid circular import with physics module
        from scheduler.physics import minutes_to_hhmm

        table = Table(
            title=f"[station]Station {station}[/station]",
            box=box.SIMPLE_HEAD,
            border_style="dim white",
            header_style="bold cyan",
            show_edge=True,
        )
        table.add_column("#",          style="dim",          width=3,  justify="right")
        table.add_column("Bus ID",     style="bus_id",       width=14)
        table.add_column("Operator",   style="value",        width=10)
        table.add_column("Wait(min)",  style="yellow",       width=10, justify="right")
        table.add_column("Start",      style="bright_green", width=8)
        table.add_column("End",        style="bright_green", width=8)

        for i, slot in enumerate(slots, start=1):
            # Colour the wait cell based on CONFIG thresholds
            wait_val = slot.wait_min
            if wait_val > CONFIG.wait_crit_min:
                wait_cell = f"[wait_bad]{wait_val}[/wait_bad]"
            elif wait_val >= CONFIG.wait_warn_min:
                wait_cell = f"[wait_med]{wait_val}[/wait_med]"
            else:
                wait_cell = f"[wait_ok]{wait_val}[/wait_ok]"

            table.add_row(
                str(i),
                slot.bus_id,
                slot.operator.upper(),
                wait_cell,
                minutes_to_hhmm(slot.start_min),
                minutes_to_hhmm(slot.end_min),
            )
        _con.print(table)

    def bus_committed(self, bus_id: str, plan: tuple, wait: int,
                      arrival: str, operator: str) -> None:
        """
        Print a single line when the scheduler commits a bus to its charging plan.

        This is called once per bus as the greedy algorithm works through them.
        Watching this output in the terminal shows the scheduling happening in
        real time — great for explaining the algorithm step-by-step.

        Example output:
          ✓ bus-BK-01  KPN    plan=A→C    wait=0 min   arrives=04:50
          ✓ bus-BK-02  FBU    plan=A→C    wait=10 min  arrives=05:15
        """
        if not _should_log("INFO"):
            return
        plan_str = "→".join(plan) if plan else "(no charge)"
        if wait > CONFIG.wait_crit_min:
            wait_str = f"[wait_bad]{wait} min[/wait_bad]"
        elif wait >= CONFIG.wait_warn_min:
            wait_str = f"[wait_med]{wait} min[/wait_med]"
        else:
            wait_str = f"[wait_ok]{wait} min[/wait_ok]"

        _con.print(
            f"  [success]✓[/success] "
            f"[bus_id]{bus_id:<12}[/bus_id] "
            f"[value]{operator:<8}[/value] "
            f"[label]plan=[/label][station]{plan_str:<8}[/station]  "
            f"[label]wait=[/label]{wait_str:<20}  "
            f"[label]arrives=[/label][value]{arrival}[/value]"
        )

    def objective_table(self, breakdown: dict, total: float) -> None:
        """
        Print a rich Table showing the final objective score breakdown.

        PDF reference: Page 4 — "three soft rules" and weights.
          S1 IndividualWaitRule  =  w_ind × Σ(wait per bus)
          S2 OperatorRule        =  w_op  × Σ(variance per operator fleet)
          S3 OverallRule         =  w_all × makespan

        Lower total = better schedule.

        Example output:
        ┌──────────────────── Objective Score ─────────────────────┐
        │ Rule                 │  Penalty │ Meaning                 │
        │ IndividualWaitRule   │   900.0  │ total queue time        │
        │ OperatorRule         │  2864.3  │ operator wait variance  │
        │ OverallRule          │   815.0  │ network makespan        │
        │ TOTAL                │  4579.3  │ ← lower is better       │
        └──────────────────────────────────────────────────────────┘
        """
        if not _should_log("INFO"):
            return
        table = Table(
            title="[metric]Objective Score[/metric]",
            box=box.SIMPLE_HEAD,
            border_style="cyan",
            header_style="bold cyan",
        )
        table.add_column("Rule",        style="white",  width=24)
        table.add_column("Penalty",     style="yellow", width=10, justify="right")
        table.add_column("Meaning",     style="dim",    width=30)

        descriptions = {
            "IndividualWaitRule": "total queue time (S1, PDF p.4)",
            "OperatorRule":       "operator wait variance (S2, PDF p.4)",
            "OverallRule":        "network makespan (S3, PDF p.4)",
        }
        for rule_name, val in breakdown.items():
            table.add_row(
                rule_name,
                f"{val:,.1f}",
                descriptions.get(rule_name, ""),
            )
        table.add_section()
        table.add_row(
            "[bold]TOTAL[/bold]",
            f"[bold yellow]{total:,.1f}[/bold yellow]",
            "[dim]← lower is better[/dim]",
        )
        _con.print(table)


# ── Module-level singleton — import and use anywhere ─────────────────────────
#
# USAGE EXAMPLE:
#   from scheduler.logger import log
#   log.info("Loading scenario", path="data/scenarios/scenario_1.json")
#   log.success("Schedule is valid!")
#
log = _Logger()
