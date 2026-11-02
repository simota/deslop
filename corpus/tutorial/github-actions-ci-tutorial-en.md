# Setting Up GitHub Actions CI for a Python Project with pytest and ruff

This tutorial shows how to build a Continuous Integration (CI) pipeline with GitHub Actions. On every push and pull request, it will:

- **Lint** your code with `ruff check`
- **Check formatting** with `ruff format --check`
- **Run tests** with `pytest` on several Python versions

---

## Prerequisites

- A GitHub repository for your Python project
- Python 3.10 or later installed locally
- Basic familiarity with Git and the command line

---

## Step 1: Organize Your Project

This tutorial assumes a layout like the one below. Your layout can differ, but you'll need to adjust the paths to match.

```
my-project/
├── .github/
│   └── workflows/
│       └── ci.yml          # created in Step 5
├── src/
│   └── my_project/
│       ├── __init__.py
│       └── calculator.py
├── tests/
│   └── test_calculator.py
├── pyproject.toml
└── README.md
```

If you're starting from scratch, add a small module and a test so CI has something to run:

**`src/my_project/calculator.py`**

```python
def add(a: int, b: int) -> int:
    return a + b
```

**`tests/test_calculator.py`**

```python
from my_project.calculator import add


def test_add() -> None:
    assert add(2, 3) == 5
```

---

## Step 2: Declare Dependencies and Tool Configuration in `pyproject.toml`

When `pyproject.toml` holds your dependencies and tool settings, your machine and CI use the same configuration.

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "my-project"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "ruff>=0.6",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"

[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
# E/F: pycodestyle + Pyflakes, I: isort, B: bugbear, UP: pyupgrade
select = ["E", "F", "I", "B", "UP"]
```

> **Tip:** Pin exact versions (for example `ruff==0.x.y`) if you want CI to be fully reproducible. Ruff adds new rules over time, so an unpinned version can start failing CI without any change to your code.

---

## Step 3: Run Everything Locally First

Before you automate the checks, confirm that they pass on your machine:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

ruff check .
ruff format --check .
pytest
```

If `ruff format --check` reports files that need changes, run `ruff format .` and commit the result. If `ruff check` finds issues that can be fixed automatically, run `ruff check --fix .`.

---

## Step 4: Create the Workflow Directory

GitHub Actions only looks for workflow files in `.github/workflows/`:

```bash
mkdir -p .github/workflows
```

---

## Step 5: Write the Workflow File

Create **`.github/workflows/ci.yml`**:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:   # allows manual runs from the Actions tab

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    name: Lint (ruff)
    runs-on: ubuntu-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v5

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: pyproject.toml

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Ruff lint
        run: ruff check --output-format=github .

      - name: Ruff format check
        run: ruff format --check --diff .

  test:
    name: Test (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]
    steps:
      - name: Check out code
        uses: actions/checkout@v5

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v6
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
          cache-dependency-path: pyproject.toml

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run pytest
        run: pytest
```

> **Note:** Action versions change over time. Check the [actions/checkout](https://github.com/actions/checkout) and [actions/setup-python](https://github.com/actions/setup-python) repositories for the current major versions.

---

## Step 6: Understand the Workflow

| Section | Purpose |
|---|---|
| `on:` | Runs CI on pushes to `main`, on every pull request, and on manual runs. |
| `permissions: contents: read` | Gives the workflow token only the access it needs (least privilege). |
| `concurrency:` | Cancels older runs on the same branch when you push new commits, which saves runner minutes. |
| `jobs.lint` | Runs ruff once on a single Python version. Linting rarely depends on the Python version. |
| `--output-format=github` | Shows ruff errors as inline annotations in the pull request's "Files changed" tab. |
| `ruff format --check --diff` | Fails if any file isn't formatted and prints the exact diff. |
| `jobs.test` + `matrix` | Runs pytest once for each listed Python version, in parallel. |
| `fail-fast: false` | Lets the remaining matrix jobs finish when one fails, so you see every failing version. |
| `cache: pip` | Reuses downloaded packages between runs. `cache-dependency-path` tells the cache to invalidate when `pyproject.toml` changes. |

`lint` and `test` run in parallel because neither job depends on the other.

---

## Step 7: Commit and Push

```bash
git add .github/workflows/ci.yml pyproject.toml src tests
git commit -m "ci: add GitHub Actions workflow for ruff and pytest"
git push origin main
```

---

## Step 8: Verify the Run on GitHub

1. Open your repository on GitHub.
2. Click the **Actions** tab.
3. Select the latest **CI** run.
4. You should see one **Lint (ruff)** job and four **Test (Python 3.x)** jobs. Click a job to see its logs.

A green check mark means every step passed. A red ✗ means a step failed. Expand that step to see the error.

To check that failures get caught, open a pull request that introduces an unused import:

```python
import os  # F401: imported but unused
```

The lint job should fail and show an annotation on that line.

---

## Step 9: Require CI to Pass Before Merging (Recommended)

1. Go to **Settings → Branches** (or **Settings → Rules → Rulesets**).
2. Add a rule for the `main` branch.
3. Enable **Require status checks to pass before merging**.
4. Select the checks `Lint (ruff)` and each `Test (Python 3.x)` job.

> The checks only appear in the list after the workflow has run at least once.

From then on, pull requests can't be merged until CI passes.

---

## Step 10: Add a Status Badge (Optional)

Add this line to `README.md`, replacing `OWNER` and `REPO` with your values:

```markdown
![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)
```

---

## Optional Enhancements

### Use `uv` for Faster Installs

[uv](https://github.com/astral-sh/uv) installs dependencies much faster than pip. To use it, replace the setup and install steps in a job:

```yaml
      - name: Install uv
        uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true

      - name: Set up Python
        run: uv python install ${{ matrix.python-version }}

      - name: Install dependencies
        run: uv pip install --system -e ".[dev]"
```

> If the project uses a `uv.lock` file, use `uv sync --all-extras` followed by `uv run pytest` instead.

### Collect Test Coverage

Add `pytest-cov` to your `dev` extras, then change the test step:

```yaml
      - name: Run pytest with coverage
        run: pytest --cov=my_project --cov-report=term-missing --cov-report=xml
```

You can upload `coverage.xml` with `actions/upload-artifact` or send it to a coverage service.

### Test on Multiple Operating Systems

Expand the matrix:

```yaml
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.10", "3.13"]
```

### Run the Same Checks Before Committing

To catch problems before they reach CI, add a `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9   # match the ruff version you use
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

Then run `pip install pre-commit && pre-commit install`.

---

## Troubleshooting

| Symptom | Likely Cause and Fix |
|---|---|
| `ModuleNotFoundError: No module named 'my_project'` | The package isn't installed. Make sure the workflow runs `pip install -e .` and that `[tool.setuptools.packages.find]` points to `src`. |
| Workflow never starts | The file isn't at `.github/workflows/*.yml`, or the YAML is invalid. Check the Actions tab for a parsing error. |
| ruff passes locally but fails in CI | You have a different ruff version locally than in CI. Pin the version in `pyproject.toml`. |
| `ruff format --check` fails | Run `ruff format .` locally and commit the changes. |
| `pytest` exits with code 5 | pytest found no tests. Check `testpaths` and make sure test files are named `test_*.py`. |
| Cache never hits | `cache-dependency-path` must point to a file that exists, such as `pyproject.toml` or `requirements*.txt`. |

---

## Summary

You now have a CI pipeline that:

1. Runs on every push to `main` and on every pull request
2. Checks code quality with `ruff check` and inline annotations
3. Enforces consistent formatting with `ruff format --check`
4. Runs your pytest suite on several Python versions in parallel
5. Caches dependencies to speed up later runs
6. Can block merges until all checks pass
