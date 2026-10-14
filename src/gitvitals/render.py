"""Render a health report as terminal output, JSON, or Markdown."""
from __future__ import annotations

import datetime
import json

GRADE_COLORS = {"A": "green", "B": "bright_green", "C": "yellow", "D": "orange1", "F": "red"}


def _fmt_date(ts: int | None) -> str:
    if ts is None:
        return "-"
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def _bar(value: float, maximum: float, width: int = 18) -> str:
    filled = int(round(width * min(1.0, value / maximum))) if maximum else 0
    return "█" * filled + "░" * (width - filled)


def render_terminal(metrics: dict, result: dict, no_color: bool = False) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console(no_color=no_color, highlight=False)
    grade = result["grade"]
    color = GRADE_COLORS.get(grade, "white")
    breakdown = result["breakdown"]

    console.print(
        Panel(
            f"[bold {color}]{result['total']:.0f}/100[/bold {color}]  "
            f"grade [bold {color}]{grade}[/bold {color}]\n"
            + "\n".join(
                f"{name:<10} {_bar(val, maxv)} {val:.0f}/{maxv}"
                for name, val, maxv in (
                    ("activity", breakdown["activity"], 35),
                    ("community", breakdown["community"], 25),
                    ("hygiene", breakdown["hygiene"], 25),
                    ("care", breakdown["care"], 15),
                )
            ),
            title=f"gitvitals  ·  {metrics['path']}",
            border_style=color,
        )
    )

    activity = Table(title="Activity", show_header=False, box=None)
    activity.add_column("metric", style="dim")
    activity.add_column("value", justify="right")
    last = metrics["days_since_last_commit"]
    activity.add_row("total commits", str(metrics["total_commits"]))
    activity.add_row("first commit", _fmt_date(metrics["first_commit_ts"]))
    activity.add_row("last commit", _fmt_date(metrics["last_commit_ts"]))
    activity.add_row(
        "days since last commit", str(last) if last is not None else "-"
    )
    activity.add_row("commits / 30d", str(metrics["commits_30d"]))
    activity.add_row("commits / 90d", str(metrics["commits_90d"]))
    activity.add_row("commits / 365d", str(metrics["commits_365d"]))
    activity.add_row("active months (12m)", str(metrics["active_months_12"]))
    console.print(activity)

    people = Table(title=f"Contributors ({metrics['contributor_count']})")
    people.add_column("name")
    people.add_column("commits", justify="right")
    people.add_column("share", justify="right")
    for person in metrics["contributors"][:8]:
        people.add_row(
            person["name"], str(person["commits"]), f"{person['share']:.0%}"
        )
    if metrics["contributor_count"] > 8:
        people.add_row("…", f"+{metrics['contributor_count'] - 8} more", "")
    console.print(people)
    console.print(f"[dim]bus factor: {metrics['bus_factor']} "
                  f"(contributors covering 50% of commits)[/dim]")

    hygiene = Table(title="Hygiene", show_header=False, box=None)
    hygiene.add_column("check")
    hygiene.add_column("status", justify="right")

    def _row(label: str, status: str, ok: bool) -> None:
        mark = "[green]✓[/green]" if ok else "[yellow]![/yellow]"
        hygiene.add_row(f"{mark} {label}", f"[dim]{status}[/dim]")

    _row("README", metrics["readme"] or "missing", bool(metrics["readme"]))
    _row("LICENSE", metrics["license_file"] or "missing",
         bool(metrics["license_file"]))
    _row(".gitignore", "present" if metrics["gitignore"] else "missing",
         metrics["gitignore"])
    _row("CONTRIBUTING", metrics["contributing"] or "missing",
         bool(metrics["contributing"]))
    n_large = len(metrics["large_files"])
    _row("large files (>1MB)",
         f"{n_large} found" if n_large else "none", n_large == 0)
    _row("uncommitted changes", str(metrics["uncommitted_count"]),
         metrics["uncommitted_count"] == 0)
    _row("branches", str(metrics["branch_count"]),
         metrics["branch_count"] <= 10)
    _row("TODO/FIXME markers", str(metrics["todo_count"]),
         metrics["todo_count"] == 0)
    console.print(hygiene)

    if metrics["churn_90d_top"]:
        churn = Table(title="Hottest files (90d)")
        churn.add_column("file", overflow="fold")
        churn.add_column("changes", justify="right")
        for fname, count in metrics["churn_90d_top"][:8]:
            churn.add_row(fname, str(count))
        console.print(churn)

    gh = metrics.get("github")
    if gh:
        gtable = Table(
            title=f"GitHub · {metrics['github_repo']}", show_header=False, box=None
        )
        gtable.add_column("metric", style="dim")
        gtable.add_column("value", justify="right")
        gtable.add_row("stars", str(gh["stars"]))
        gtable.add_row("forks", str(gh["forks"]))
        gtable.add_row("watchers", str(gh["watchers"]))
        gtable.add_row("open issues", str(gh["open_issues"]))
        gtable.add_row("archived", str(bool(gh["archived"])))
        gtable.add_row("license", str(gh["license"]))
        gtable.add_row("language", str(gh["language"]))
        if metrics.get("github_latest_release"):
            gtable.add_row("latest release", metrics["github_latest_release"])
        console.print(gtable)
    elif metrics.get("github_repo"):
        console.print("[dim]GitHub data unavailable "
                      f"({metrics['github_repo']})[/dim]")


def render_json(metrics: dict, result: dict) -> str:
    payload = {
        "score": result,
        "metrics": {
            key: value
            for key, value in metrics.items()
            if key not in ("contributors", "churn_90d_top", "large_files")
        },
        "contributors": metrics["contributors"],
        "churn_90d_top": [
            {"file": name, "changes": count}
            for name, count in metrics["churn_90d_top"]
        ],
        "large_files": [
            {"path": path, "bytes": size}
            for path, size in metrics["large_files"]
        ],
    }
    return json.dumps(payload, indent=2, default=str)


def render_markdown(metrics: dict, result: dict) -> str:
    lines = [
        f"# gitvitals report · `{metrics['path']}`",
        "",
        f"**Score: {result['total']:.0f}/100 (grade {result['grade']})**",
        "",
        "| Category | Score |",
        "|---|---|",
    ]
    for name, value in result["breakdown"].items():
        lines.append(f"| {name} | {value:.0f} |")
    lines += [
        "",
        "## Activity",
        "",
        f"- Total commits: {metrics['total_commits']}",
        f"- Last commit: {_fmt_date(metrics['last_commit_ts'])}",
        f"- Commits (30d / 90d / 365d): {metrics['commits_30d']} / "
        f"{metrics['commits_90d']} / {metrics['commits_365d']}",
        f"- Active months (12m): {metrics['active_months_12']}",
        "",
        "## Contributors",
        "",
        f"- Contributors: {metrics['contributor_count']}",
        f"- Bus factor: {metrics['bus_factor']}",
        "",
    ]
    for person in metrics["contributors"][:8]:
        lines.append(
            f"- {person['name']} — {person['commits']} commits "
            f"({person['share']:.0%})"
        )
    lines += [
        "",
        "## Hygiene",
        "",
        f"- README: {metrics['readme'] or 'missing'}",
        f"- LICENSE: {metrics['license_file'] or 'missing'}",
        f"- .gitignore: {'present' if metrics['gitignore'] else 'missing'}",
        f"- Large files (>1MB): {len(metrics['large_files'])}",
        f"- Uncommitted changes: {metrics['uncommitted_count']}",
        f"- TODO/FIXME markers: {metrics['todo_count']}",
        "",
        "_Generated by [gitvitals](https://github.com/someone-rs/gitvitals)_",
    ]
    return "\n".join(lines) + "\n"
