# Add CI/CD Pipeline with GitHub Actions

**Labels:** `enhancement`, `infrastructure`, `high-priority`
**Milestone:** 0.1.0

## Overview
Add automated CI/CD pipeline using GitHub Actions to run tests, check formatting, and publish releases.

## Problems
- No automated testing on PRs
- Manual release process is error-prone
- No visibility into test failures before merge
- Missing code coverage reporting

## Requirements
- Run tests on every PR and push to main
- Check code formatting with ruff
- Generate and report test coverage
- Auto-publish to PyPI on release tags
- Cache dependencies for faster runs
- Add build status badge to README

## Implementation Steps

### 1. Create `.github/workflows/test.yml`
```yaml
name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12"]

    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install uv
      uses: astral-sh/setup-uv@v3

    - name: Install dependencies
      run: uv sync --all-extras

    - name: Run ruff format check
      run: uv run ruff format src/ --check

    - name: Run ruff linter
      run: uv run ruff check src/

    - name: Run tests with coverage
      run: uv run pytest

    - name: Upload coverage reports
      uses: codecov/codecov-action@v4
      with:
        file: .venv/cache/.coverage
```

### 2. Create `.github/workflows/publish.yml`
```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.12"

    - name: Install uv
      uses: astral-sh/setup-uv@v3

    - name: Install dependencies
      run: uv sync --all-extras

    - name: Build package
      run: uv run inv build

    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        password: ${{ secrets.PYPI_API_TOKEN }}
```

### 3. Update README.md with status badge
Add at the top of README.md:
```markdown
![Tests](https://github.com/blueshed/blueshed-gust/workflows/Tests/badge.svg)
![PyPI - Version](https://img.shields.io/pypi/v/blueshed-gust)
```

### 4. Configure branch protection
- Require status checks to pass before merging
- Require up-to-date branches before merging

## Acceptance Criteria
- [ ] All tests run automatically on PR
- [ ] Coverage report visible in PR (via Codecov)
- [ ] Releases published to PyPI automatically
- [ ] Build status badge in README
- [ ] Ruff formatting and linting enforced
- [ ] Documentation includes CI/CD setup guide

## Related
- Code review finding #9: No CI/CD configuration visible
- Addresses need for automated testing and releases

## Notes
- Requires `PYPI_API_TOKEN` secret configured in GitHub repo settings
- Consider adding Codecov integration for coverage reporting
- May want to add Python 3.13+ to test matrix in future
