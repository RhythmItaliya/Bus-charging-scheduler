from __future__ import annotations

import os
from typing import Any

from scheduler.config import CONFIG


from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme


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


_con = Console(theme=_THEME, highlight=False)


_LEVELS = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3}
_LOG_LEVEL = os.environ.get(CONFIG.log_level_env_var, CONFIG.default_log_level).upper()


def _should_log(level: str) -> bool:
    return _LEVELS.get(level, 1) >= _LEVELS.get(_LOG_LEVEL, 1)


def _extras_str(fields: dict) -> str:
    parts = [f"[label]{k}[/label]=[value]{v}[/value]" for k, v in fields.items()]
    return "  " + "  ".join(parts) if parts else ""


class _Logger:


    def debug(self, msg: str, **kw: Any) -> None:
        if not _should_log("DEBUG"):
            return
        _con.print(f"[debug]  [DBG] {msg}{_extras_str(kw)}[/debug]")

    def info(self, msg: str, **kw: Any) -> None:
        if not _should_log("INFO"):
            return
        _con.print(f"[info][INF][/info] {msg}{_extras_str(kw)}")

    def warn(self, msg: str, **kw: Any) -> None:
        if not _should_log("WARN"):
            return
        _con.print(f"[warn][WRN] {msg}{_extras_str(kw)}[/warn]")

    def error(self, msg: str, **kw: Any) -> None:
        if not _should_log("ERROR"):
            return
        _con.print(f"[error][ERR] {msg}{_extras_str(kw)}[/error]")

    def success(self, msg: str, **kw: Any) -> None:
        if not _should_log("INFO"):
            return
        _con.print(f"[success][ OK] {msg}{_extras_str(kw)}[/success]")


    def scenario(self, name: str, **kw: Any) -> None:
        if not _should_log("INFO"):
            return

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
        _con.print(
            Panel(
                f"[bold white]{title}[/bold white]",
                box=box.DOUBLE_EDGE,
                border_style="bright_blue",
                padding=(0, 2),
            )
        )

    def separator(self, title: str = "") -> None:
        if title:
            _con.rule(f"[dim]{title}[/dim]", style="dim white")
        else:
            _con.rule(style="dim white")

    def rule_check(self, rule: str, *, status: str, **kw: Any) -> None:
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
        if not _should_log("DEBUG"):
            return

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
        if not _should_log("INFO"):
            return
        _con.print(
            f"[metric][MET][/metric] [bold white]{name}[/bold white]"
            f"  [label]value[/label]=[metric]{value}[/metric]"
            + _extras_str(kw)
        )

    def schedule_table(self, station: str, slots: list) -> None:
        if not _should_log("INFO"):
            return
        if not slots:
            _con.print(f"  [dim]Station {station}: no charges[/dim]")
            return


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


log = _Logger()
