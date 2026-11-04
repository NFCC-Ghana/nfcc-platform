"""Scope of the full code review (31 Oct - 4 Nov 2026), file by file.

Every file in the repository that holds code or configuration is matched to
one review area below, with the depth at which it was reviewed. The report
generator (reference.py) builds Appendix A from this and stops with an error
if any tracked code or configuration file matches no area, so a file added
later cannot silently fall outside the stated scope.

Depths:
  line     every executable line read, comments and docstrings stripped
  config   read in full
  legacy   not deployed or imported by deployed code: checked for
           reachability and for invented data, not line by line
  tests    read for what each test file checks and what it mocks; individual
           assertions were not each re-verified
"""

import fnmatch
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# (area, depth, ledger batches, patterns). First match wins.
AREAS = [
    ("Platform configuration", "line", "1", ["src/config/*"]),
    ("Alerting: engine, tiers, cooldown, rate limit, providers", "line", "1, 2, 27",
     ["src/alerts/*", "src/alerts/providers/*"]),
    ("API application, access control and routes", "line", "3–11, 27",
     ["src/api/*", "src/api/routes/*", "src/api/v1/*", "src/utils/*"]),
    ("Community reports and channel subscriptions", "line", "9", ["src/community/*"]),
    ("AI copilot", "line", "10", ["src/copilot/*"]),
    ("Data quality control", "line", "10", ["src/data_quality/*"]),
    ("Persistence (SQLite)", "line", "11, 12", ["src/database/*"]),
    ("Exposure, district registry, shelters", "line", "12, 13", ["src/exposure/*"]),
    ("Data adapters (rain, river, dam, soil, radar, Flood Hub)", "line", "13–19",
     ["src/hydrology/*"]),
    ("Models: fusion, timelines, backtest, verification", "line", "15, 19, 20",
     ["src/models/*"]),
    ("Outcome verification clients", "line", "20", ["src/verification/*"]),
    ("Package markers", "line", "20", ["src/__init__.py", "**/__init__.py"]),
    ("Operator dashboard (deployed)", "line", "21, 22",
     ["hackathon/app/pages/*", "hackathon/app/modules/*", "hackathon/app/modules/v4/*",
      "hackathon/app/streamlit_app.py"]),
    ("Legacy dashboards and hackathon material", "legacy", "22",
     ["hackathon/archive/*", "hackathon/app/pages_disabled/*", "hackathon/*",
      "hackathon/datasets/*", "hackathon/docs/*"]),
    ("Scheduled jobs and operator scripts", "line", "23, 24, 27",
     ["scripts/*", "scripts/manual/*"]),
    ("Research framework", "line", "25, 27", ["research/flood_experiments/*.py"]),
    ("CI/CD workflows", "config", "26, 27", [".github/*", ".github/workflows/*"]),
    ("Container, deployment and tooling configuration", "config", "26, 27",
     ["Dockerfile", "Dockerfile.prod", "entrypoint.sh", "litestream.yml",
      "cloudbuild.yaml", "docker-compose.yml", "nginx.conf", "prometheus.yml",
      "pyproject.toml", "pytest.ini", ".flake8", ".pre-commit-config.yaml",
      ".dockerignore", ".gitignore", ".env*", "environment.yml", "requirements*.txt",
      ".streamlit/*", "test_environment.py", "Makefile"]),
    ("Notebooks (historical; not used by the system)", "line", "26", ["notebooks/*"]),
    ("Test suite", "tests", "26", ["tests/*", "tests/**"]),
]

CODE_SUFFIXES = {".py", ".sh", ".yml", ".yaml", ".toml", ".ini", ".conf", ".ipynb",
                 ".txt", ".cfg", ""}
NOT_CODE_DIRS = ("docs/", "data/", "research/flood_experiments/results/",
                 "research/flood_experiments/model/", "research/flood_experiments/data/")
DEPTH_LABEL = {
    "line": "Every executable line",
    "config": "Read in full",
    "legacy": "Reachability and invented data",
    "tests": "What is tested and what is mocked",
}


def tracked_files():
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.split("\n")
    return sorted(
        f for f in out
        if f and not f.startswith(NOT_CODE_DIRS)
        and (Path(f).suffix in CODE_SUFFIXES or Path(f).name.startswith((".env", "Dockerfile")))
        and not f.endswith(("README.md",))
    )


def area_of(path):
    for area, depth, batches, patterns in AREAS:
        if any(fnmatch.fnmatch(path, p) for p in patterns):
            return area, depth, batches
    return None


def coverage():
    """[(area, depth, batches, files, lines)] and the list of unmatched files."""
    by_area, unmatched = {}, []
    for f in tracked_files():
        a = area_of(f)
        if a is None:
            unmatched.append(f)
            continue
        try:
            n = sum(1 for _ in open(ROOT / f, encoding="utf-8", errors="ignore"))
        except FileNotFoundError:  # deleted in the working tree
            continue
        rec = by_area.setdefault(a, [0, 0, []])
        rec[0] += 1
        rec[1] += n
        rec[2].append(f)
    rows = [(a[0], a[1], a[2], v[0], v[1], v[2]) for a, v in by_area.items()]
    order = {a[0]: i for i, a in enumerate(AREAS)}
    rows.sort(key=lambda r: order[r[0]])
    return rows, unmatched


if __name__ == "__main__":
    rows, unmatched = coverage()
    for r in rows:
        print(f"{r[3]:4d} files {r[4]:6d} lines  {r[1]:7s} {r[0]}")
    print("unmatched:", unmatched)
