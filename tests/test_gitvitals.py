"""Tests for gitvitals."""
import os
import subprocess
import time

import pytest

from gitvitals import git as _git
from gitvitals import github as _github
from gitvitals.checks import analyze
from gitvitals.scoring import score


def _git_cmd(path, *args, env=None):
    merged = dict(os.environ)
    merged.update(
        {
            "GIT_AUTHOR_NAME": "Ada",
            "GIT_AUTHOR_EMAIL": "ada@example.com",
            "GIT_COMMITTER_NAME": "Ada",
            "GIT_COMMITTER_EMAIL": "ada@example.com",
        }
    )
    if env:
        merged.update(env)
    subprocess.run(["git", "-C", path, *args], check=True,
                   capture_output=True, env=merged, timeout=30)


def _make_repo(tmp_path, commits):
    """Create a repo; commits = [(filename, author, email, days_ago), ...]."""
    _git_cmd(tmp_path, "init", "-q")
    _git_cmd(tmp_path, "config", "user.name", "test")
    _git_cmd(tmp_path, "config", "user.email", "test@example.com")
    now = int(time.time())
    for i, (fname, author, email, days_ago) in enumerate(commits):
        (tmp_path / fname).write_text(f"content {i}\n")
        _git_cmd(tmp_path, "add", fname)
        stamp = now - days_ago * 86400
        date = f"{stamp} +0000"
        _git_cmd(
            tmp_path, "commit", "-q", "-m", f"commit {i}",
            env={
                "GIT_AUTHOR_NAME": author,
                "GIT_AUTHOR_EMAIL": email,
                "GIT_COMMITTER_NAME": author,
                "GIT_COMMITTER_EMAIL": email,
                "GIT_AUTHOR_DATE": date,
                "GIT_COMMITTER_DATE": date,
            },
        )
    return str(tmp_path)


def test_analyze_basic(tmp_path):
    repo = _make_repo(
        tmp_path,
        [
            ("a.txt", "Ada", "ada@example.com", 200),
            ("b.txt", "Ada", "ada@example.com", 10),
            ("c.txt", "Bob", "bob@example.com", 5),
            ("d.txt", "Ada", "ada@example.com", 1),
        ],
    )
    metrics = analyze(repo, include_github=False)
    assert metrics["total_commits"] == 4
    assert metrics["contributor_count"] == 2
    assert metrics["bus_factor"] == 1  # Ada owns 75%
    assert metrics["commits_30d"] == 3
    assert metrics["days_since_last_commit"] == 1
    result = score(metrics)
    assert 0 <= result["total"] <= 100
    assert result["grade"] in "ABCDF"


def test_bus_factor_shared(tmp_path):
    repo = _make_repo(
        tmp_path,
        [
            ("a.txt", "Ada", "ada@example.com", 3),
            ("b.txt", "Bob", "bob@example.com", 2),
            ("c.txt", "Cid", "cid@example.com", 1),
        ],
    )
    metrics = analyze(repo, include_github=False)
    assert metrics["contributor_count"] == 3
    assert metrics["bus_factor"] == 2  # any 2 of 3 cover >= 50%


def test_not_a_repo(tmp_path):
    with pytest.raises(_git.GitError):
        analyze(str(tmp_path), include_github=False)


def test_score_bounds():
    base = {
        "total_commits": 100,
        "days_since_last_commit": 0,
        "commits_90d": 60,
        "contributor_count": 8,
        "bus_factor": 4,
        "readme": "README.md",
        "license_file": "LICENSE",
        "gitignore": True,
        "contributing": "CONTRIBUTING.md",
        "large_files": [],
        "uncommitted_count": 0,
        "todo_count": 0,
        "branch_count": 2,
    }
    assert score(base)["total"] == 100
    assert score(base)["grade"] == "A"

    dead = dict(base, total_commits=1, days_since_last_commit=900,
                commits_90d=0, contributor_count=1, bus_factor=1,
                readme=None, license_file=None, gitignore=False,
                contributing=None, large_files=[("x.bin", 5)],
                uncommitted_count=9, todo_count=99, branch_count=40)
    assert score(dead)["total"] < 40
    assert score(dead)["grade"] in ("D", "F")


def test_parse_github_repo():
    assert _github.parse_github_repo(
        "https://github.com/someone-rs/gitvitals.git"
    ) == ("someone-rs", "gitvitals")
    assert _github.parse_github_repo(
        "git@github.com:someone-rs/gitvitals.git"
    ) == ("someone-rs", "gitvitals")
    assert _github.parse_github_repo("https://gitlab.com/a/b.git") is None
    assert _github.parse_github_repo(None) is None


def test_cli_version():
    from gitvitals.cli import main

    assert main(["--version"]) == 0
