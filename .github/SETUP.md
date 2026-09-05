# CI/CD Setup Instructions

This repository uses GitHub Actions for automated testing and publishing.

## What's Automated

### 1. Tests (runs on every PR and push to main)
- Automated testing with pytest
- Code formatting check with ruff
- Linting with ruff
- Coverage report printed in the job log (term-missing)

### 2. PyPI Publishing (runs on releases)
- Automated package building
- Publishing to PyPI

## Setup Required

### For PyPI Publishing

To enable automated PyPI publishing, you need to configure a PyPI API token:

1. **Create PyPI API Token**
   - Go to https://pypi.org/manage/account/token/
   - Click "Add API token"
   - Token name: `github-actions-blueshed-gust`
   - Scope: "Entire account" or "Project: blueshed-gust" (if package already exists)
   - Copy the token (starts with `pypi-`)

2. **Add Token to GitHub Secrets**
   - Go to https://github.com/blueshed/blueshed-gust/settings/secrets/actions
   - Click "New repository secret"
   - Name: `PYPI_API_TOKEN`
   - Value: Paste the token from step 1
   - Click "Add secret"

3. **Test the Setup**
   - Create a GitHub release
   - The workflow will automatically build and publish to PyPI

## Workflow Files

- `.github/workflows/test.yml` - Runs tests on PRs and pushes
- `.github/workflows/publish.yml` - Publishes to PyPI on releases

## Status Badge

The README includes a status badge showing the latest test results:

```markdown
![Tests](https://github.com/blueshed/blueshed-gust/workflows/Tests/badge.svg)
```

## Creating a Release

To publish a new version to PyPI:

1. Update version in `src/blueshed/gust/__init__.py`
2. Update CHANGELOG.md
3. Commit changes
4. Create a GitHub release:
   ```bash
   git tag v0.0.27
   git push origin v0.0.27
   ```
5. Create release on GitHub web interface
6. The publish workflow will automatically run and publish to PyPI

## Troubleshooting

### Tests Fail
- Check the Actions tab for detailed logs
- Ensure all tests pass locally with `pytest`

### PyPI Publishing Fails
- Verify `PYPI_API_TOKEN` secret is set correctly
- Check token has correct permissions
- Ensure version number is incremented (PyPI doesn't allow re-uploading same version)

