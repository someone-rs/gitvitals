"""Best-effort public GitHub metadata (unauthenticated, graceful fallback)."""
from __future__ import annotations

import json
import re
import urllib.request

_SSH_RE = re.compile(r"git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$")
_HTTPS_RE = re.compile(
    r"https?://(?:www\.)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$"
)


def parse_github_repo(remote: str | None) -> tuple[str, str] | None:
    """Extract (owner, repo) from a git remote URL, or None if not GitHub."""
    if not remote:
        return None
    for rx in (_SSH_RE, _HTTPS_RE):
        match = rx.match(remote.strip())
        if match:
            return match.group("owner"), match.group("repo")
    return None


def _get(url: str, timeout: int = 10):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "gitvitals",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except Exception:  # noqa: BLE001 - any network/API failure -> unavailable
        return None


def repo_info(owner: str, repo: str) -> dict | None:
    data = _get(f"https://api.github.com/repos/{owner}/{repo}")
    if not data or "stargazers_count" not in data:
        return None
    license_info = data.get("license") or {}
    return {
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "open_issues": data.get("open_issues_count"),
        "watchers": data.get("subscribers_count"),
        "archived": data.get("archived"),
        "license": license_info.get("spdx_id"),
        "default_branch": data.get("default_branch"),
        "language": data.get("language"),
        "pushed_at": data.get("pushed_at"),
        "url": data.get("html_url"),
    }


def latest_release(owner: str, repo: str) -> str | None:
    data = _get(f"https://api.github.com/repos/{owner}/{repo}/releases/latest")
    if not data:
        return None
    return data.get("tag_name")
