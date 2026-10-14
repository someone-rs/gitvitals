"""Compute the raw health metrics for a repository."""
from __future__ import annotations

import time
from collections import Counter

from . import git as _git
from . import github as _github

DAY = 86400
TODO_PATTERN = r"TODO|FIXME|XXX|HACK"


def _contributors(commits: list[_git.Commit]) -> tuple[list[dict], int]:
    """Aggregate commits by author email; return (people, bus_factor).

    Bus factor = fewest contributors whose commits cover >= 50% of history.
    """
    by_email: dict[str, dict] = {}
    for commit in commits:
        key = commit.author_email.strip().lower() or commit.author_name.strip().lower()
        entry = by_email.setdefault(
            key, {"emails": set(), "names": Counter(), "commits": 0}
        )
        entry["emails"].add(commit.author_email)
        entry["names"][commit.author_name] += 1
        entry["commits"] += 1

    people = []
    for entry in by_email.values():
        name = entry["names"].most_common(1)[0][0]
        people.append(
            {
                "name": name,
                "email": sorted(entry["emails"])[0],
                "commits": entry["commits"],
            }
        )
    people.sort(key=lambda person: person["commits"], reverse=True)

    total = sum(person["commits"] for person in people) or 1
    for person in people:
        person["share"] = person["commits"] / total

    covered, bus_factor = 0.0, 0
    for person in people:
        covered += person["share"]
        bus_factor += 1
        if covered >= 0.5:
            break
    return people, bus_factor


def _active_months(commits: list[_git.Commit], now: int, months: int = 12) -> int:
    buckets = set()
    for commit in commits:
        age_days = (now - commit.timestamp) / DAY
        if 0 <= age_days < months * 30.44:
            buckets.add(int(age_days // 30.44))
    return len(buckets)


def analyze(path: str, include_github: bool = True) -> dict:
    """Collect every metric gitvitals reports on. Raises GitError if not a repo."""
    if not _git.is_repo(path):
        raise _git.GitError(f"not a git repository: {path}")
    root = _git.toplevel(path)
    now = int(time.time())

    commits = _git.commits(root)
    total = len(commits)
    timestamps = [c.timestamp for c in commits]
    last_ts = max(timestamps) if timestamps else None
    first_ts = min(timestamps) if timestamps else None

    def _since(days: int) -> int:
        cutoff = now - days * DAY
        return sum(1 for ts in timestamps if ts >= cutoff)

    people, bus_factor = _contributors(commits)
    churn = _git.files_changed_since(root, 90)
    uncommitted = _git.status_porcelain(root)
    branches = _git.branches(root)

    gh_repo = _github.parse_github_repo(_git.remote_url(root)) if include_github else None
    gh_data = None
    gh_release = None
    if gh_repo:
        gh_data = _github.repo_info(*gh_repo)
        if gh_data:
            gh_release = _github.latest_release(*gh_repo)

    return {
        "path": root,
        "total_commits": total,
        "first_commit_ts": first_ts,
        "last_commit_ts": last_ts,
        "days_since_last_commit": (now - last_ts) // DAY if last_ts else None,
        "commits_30d": _since(30),
        "commits_90d": _since(90),
        "commits_365d": _since(365),
        "active_months_12": _active_months(commits, now),
        "contributors": people,
        "contributor_count": len(people),
        "bus_factor": bus_factor,
        "churn_90d_top": churn.most_common(10),
        "files_touched_90d": len(churn),
        "readme": _git.root_file(root, ["README.md", "README.rst", "README.txt", "README"]),
        "license_file": _git.root_file(root, ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"]),
        "contributing": _git.root_file(root, ["CONTRIBUTING.md", "CONTRIBUTING.rst", "CONTRIBUTING.txt"]),
        "gitignore": _git.root_file(root, [".gitignore"]) is not None,
        "large_files": _git.large_tracked_files(root),
        "uncommitted_count": len(uncommitted),
        "branch_count": len(branches),
        "todo_count": _git.grep_count(root, TODO_PATTERN),
        "github_repo": "/".join(gh_repo) if gh_repo else None,
        "github": gh_data,
        "github_latest_release": gh_release,
    }
