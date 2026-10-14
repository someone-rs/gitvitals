# gitvitals

[![PyPI](https://img.shields.io/pypi/v/gitvitals)](https://pypi.org/project/gitvitals/)
[![Python](https://img.shields.io/pypi/pyversions/gitvitals)](https://pypi.org/project/gitvitals/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Health check for any git repository.** One command tells you whether a project
is alive, who really carries it, and what's rotting — with a 0–100 vitality
score.

Thinking about depending on a library, adopting a repo, or reviving an old
project? `gitvitals` answers in seconds, fully offline. No token, no config.

## Install

```bash
pip install gitvitals
```

Requires Python 3.9+ and `git` on your PATH.

## Quick start

```bash
gitvitals                    # analyze the current directory
gitvitals ~/code/myproject   # analyze any local repository
gitvitals --format json      # machine-readable output
gitvitals --format markdown  # paste it into issues, PRs, READMEs
gitvitals --no-github        # skip the GitHub API lookup
```

## Example

```text
$ gitvitals ~/code/myproject
╭────────────────── gitvitals  ·  /home/user/code/myproject ───────────────────╮
│ 66/100  grade C                                                              │
│ activity   ████████████░░░░░░ 23/35                                          │
│ community  ███████████░░░░░░░ 15/25                                          │
│ hygiene    █████████████░░░░░ 18/25                                          │
│ care       ████████████░░░░░░ 10/15                                          │
╰──────────────────────────────────────────────────────────────────────────────╯
              Activity
 total commits                   52
 first commit            2025-01-18
 last commit             2026-10-14
 days since last commit           0
 commits / 30d                   12
 commits / 90d                   12
 commits / 365d                  12
          Contributors (4)
┏━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┓
┃ name          ┃ commits ┃ share ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━┩
│ maintainer    │      33 │   63% │
│ contributor-1 │      12 │   23% │
│ contributor-2 │       4 │   8%  │
│ contributor-3 │       3 │   6%  │
└───────────────┴─────────┴───────┘
bus factor: 1 (contributors covering 50% of commits)
             Hygiene
 ✓ README               README.md
 ✓ LICENSE                LICENSE
 ✓ .gitignore             present
 ! CONTRIBUTING           missing
 ! large files (>1MB)    15 found
 ✓ uncommitted changes          0
 ✓ branches                     1
 ! TODO/FIXME markers          36
```

## What it checks

| Category | Weight | Signals |
|---|---|---|
| **Activity** | 35 | recency of the last commit, commit cadence over 90 days |
| **Community** | 25 | number of contributors, bus factor (who covers 50% of history) |
| **Hygiene** | 25 | README, LICENSE, `.gitignore`, CONTRIBUTING, no checked-in large files |
| **Care** | 15 | clean working tree, TODO/FIXME density, branch tidiness |

Grades: **A** ≥ 85, **B** ≥ 70, **C** ≥ 55, **D** ≥ 40, otherwise **F**.

When the repo's `origin` points at github.com, gitvitals also pulls public
metadata — stars, forks, open issues, license, latest release — no token
needed (falls back gracefully offline or on rate limits).

It also reports the **hottest files of the last 90 days**, so you can see
where the churn is before you dive in.

## Why

Repo metadata lies by omission: stars measure popularity, not maintenance.
`gitvitals` measures the things that actually predict whether a project will
still be alive next year — and it does it from the git history you already
have, without phoning home.

## Contributing

Issues and pull requests are welcome — new health checks especially. A good
check is cheap to compute from local git history, hard to game, and genuinely
predictive of project health. Run the tests with:

```bash
pip install pytest
pytest
```

## License

MIT — see [LICENSE](LICENSE).
