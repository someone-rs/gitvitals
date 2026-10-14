"""Turn raw metrics into a 0-100 vitality score with a letter grade."""
from __future__ import annotations

CATEGORY_MAX = {
    "activity": 35,
    "community": 25,
    "hygiene": 25,
    "care": 15,
}


def score(metrics: dict) -> dict:
    """Score a metrics dict from :func:`checks.analyze`."""
    breakdown: dict[str, float] = {}

    # --- Activity (35): is the project alive and moving? ---
    days = metrics.get("days_since_last_commit")
    if metrics.get("total_commits") and days is not None:
        recency = max(0.0, 15 * (1 - days / 365))
    else:
        recency = 0.0
    cadence = min(20.0, 20 * metrics.get("commits_90d", 0) / 30)
    breakdown["activity"] = round(recency + cadence, 1)

    # --- Community (25): is knowledge shared? ---
    people = metrics.get("contributor_count", 0)
    contributor_pts = min(15.0, 3 * people) if people else 0.0
    bus = metrics.get("bus_factor", 0)
    bus_pts = 10 if bus >= 3 else (7 if bus == 2 else (3 if bus == 1 else 0))
    breakdown["community"] = round(contributor_pts + bus_pts, 1)

    # --- Hygiene (25): does the repo look maintained? ---
    hygiene = 0
    if metrics.get("readme"):
        hygiene += 7
    if metrics.get("license_file"):
        hygiene += 7
    if metrics.get("gitignore"):
        hygiene += 4
    if metrics.get("contributing"):
        hygiene += 2
    if not metrics.get("large_files"):
        hygiene += 5
    breakdown["hygiene"] = hygiene

    # --- Care (15): day-to-day tidiness ---
    care = 0
    if metrics.get("uncommitted_count", 0) == 0:
        care += 5
    todos = metrics.get("todo_count", 0)
    care += 5 if todos == 0 else (3 if todos < 20 else 0)
    branch_count = metrics.get("branch_count", 0)
    care += 5 if branch_count <= 3 else (3 if branch_count <= 10 else 1)
    breakdown["care"] = care

    total = round(min(100.0, sum(breakdown.values())), 1)
    grade = (
        "A" if total >= 85
        else "B" if total >= 70
        else "C" if total >= 55
        else "D" if total >= 40
        else "F"
    )
    return {"total": total, "grade": grade, "breakdown": breakdown, "max": 100}
