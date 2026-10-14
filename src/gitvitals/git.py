"""Introspection helpers built on the git CLI (standard library only)."""
from __future__ import annotations

import subprocess
from collections import Counter
from dataclasses import dataclass


@dataclass
class Commit:
    sha: str
    author_name: str
    author_email: str
    timestamp: int
    subject: str


class GitError(RuntimeError):
    """Raised when the target is not a git repo or git fails."""


def _run(path: str, *args: str) -> subprocess.CompletedProcess:
    try:
        proc = subprocess.run(
            ["git", "-C", path, *args],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError as exc:
        raise GitError("git executable not found on PATH") from exc
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {proc.stderr.strip()[:200]}")
    return proc


def is_repo(path: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", path, "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    return proc.returncode == 0


def toplevel(path: str) -> str:
    return _run(path, "rev-parse", "--show-toplevel").stdout.strip()


def commits(path: str, limit: int = 50000) -> list[Commit]:
    out = _run(
        path,
        "log",
        f"--max-count={limit}",
        "--no-merges",
        "--format=%H%x1f%an%x1f%ae%x1f%at%x1f%s",
    ).stdout
    result: list[Commit] = []
    for line in out.splitlines():
        parts = line.split("\x1f")
        if len(parts) != 5:
            continue
        sha, name, email, ts, subject = parts
        try:
            ts_int = int(ts)
        except ValueError:
            continue
        result.append(Commit(sha, name, email, ts_int, subject))
    return result


def files_changed_since(path: str, days: int) -> Counter:
    out = _run(
        path, "log", f"--since={days} days ago", "--no-merges",
        "--name-only", "--format=",
    ).stdout
    return Counter(line for line in out.splitlines() if line.strip())


def status_porcelain(path: str) -> list[str]:
    out = _run(path, "status", "--porcelain").stdout
    return [line for line in out.splitlines() if line.strip()]


def branches(path: str) -> list[str]:
    out = _run(path, "branch", "--format=%(refname:short)").stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


def large_tracked_files(
    path: str, min_bytes: int = 1_000_000, cap: int = 20000
) -> list[tuple[str, int]]:
    """Return (path, size) for tracked files >= min_bytes, biggest first."""
    out = _run(path, "ls-files", "-s", "-z").stdout
    entries: list[tuple[str, str]] = []
    for chunk in out.split("\x00"):
        if not chunk.strip():
            continue
        try:
            meta, fpath = chunk.split("\t", 1)
            sha = meta.split(" ")[1]
        except (ValueError, IndexError):
            continue
        entries.append((fpath, sha))
        if len(entries) >= cap:
            break
    if not entries:
        return []
    proc = subprocess.run(
        ["git", "-C", path, "cat-file", "--batch-check"],
        input="".join(sha + "\n" for _, sha in entries),
        capture_output=True,
        text=True,
        timeout=120,
    )
    sizes: dict[str, int] = {}
    for line in proc.stdout.splitlines():
        parts = line.split(" ")
        if len(parts) >= 3 and parts[1] == "blob":
            try:
                sizes[parts[0]] = int(parts[2])
            except ValueError:
                pass
    big = [(fpath, sizes[sha]) for fpath, sha in entries
           if sizes.get(sha, 0) >= min_bytes]
    return sorted(big, key=lambda item: item[1], reverse=True)


def grep_count(path: str, pattern: str, cap: int = 5000) -> int:
    """Count matches of an extended regex in tracked text files (0 if none)."""
    proc = subprocess.run(
        ["git", "-C", path, "grep", "-o", "-I", "-E", pattern, "--", "."],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        return 0  # exit 1 simply means "no matches"
    return min(len(proc.stdout.splitlines()), cap)


def remote_url(path: str, name: str = "origin") -> str | None:
    proc = subprocess.run(
        ["git", "-C", path, "remote", "get-url", name],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def root_file(path: str, names: list[str]) -> str | None:
    """First of `names` found at the repo root (case-insensitive), else None."""
    try:
        listed = _run(path, "ls-tree", "--name-only", "HEAD").stdout.splitlines()
    except GitError:
        return None
    lowered = {entry.lower(): entry for entry in listed}
    for want in names:
        if want.lower() in lowered:
            return lowered[want.lower()]
    return None
