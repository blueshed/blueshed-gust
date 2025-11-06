# Create CHANGELOG.md

**Labels:** `documentation`, `high-priority`
**Milestone:** 0.1.0

## Overview
Add CHANGELOG.md following Keep a Changelog format to track version history and help users understand what changed between versions.

## Problems
- No documented version history
- Users don't know what changed between versions
- No structured way to track breaking changes
- Release notes are not easily accessible

## Requirements
- Follow https://keepachangelog.com/en/1.0.0/ format
- Document changes from 0.0.1 to current (0.0.26)
- Include all standard sections:
  - Added
  - Changed
  - Deprecated
  - Removed
  - Fixed
  - Security
- Link to GitHub releases and compare views
- Update CHANGELOG as part of release process

## Implementation Steps

### 1. Create CHANGELOG.md template
```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Items to be included in next release

## [0.0.26] - 2025-XX-XX

### Added
- PostgreSQL RPC handler with function signature caching
- AuthPostgresRPC for automatic user injection

### Changed
- [List changes from git history]

### Fixed
- pytest-coverage → pytest-cov dependency fix
- Updated .gitignore with missing patterns

## [0.0.25] - YYYY-MM-DD

[Continue with previous versions...]

[Unreleased]: https://github.com/blueshed/blueshed-gust/compare/v0.0.26...HEAD
[0.0.26]: https://github.com/blueshed/blueshed-gust/compare/v0.0.25...v0.0.26
```

### 2. Review git history for version changes
```bash
# Get all version tags
git tag -l

# Review commits for each version
git log v0.0.25..v0.0.26 --oneline

# Look at version bumps in __init__.py
git log --all --oneline --follow src/blueshed/gust/__init__.py
```

### 3. Document changes for each version
- Group commits by type (Added, Changed, Fixed, etc.)
- Focus on user-facing changes
- Link to relevant PRs/issues when available
- Use semantic versioning for future releases

### 4. Update release process in tasks.py
Add CHANGELOG update reminder to release task:
```python
@task(lint)
def release(ctx, message, part='patch'):
    """release to pypi"""
    # Remind to update CHANGELOG
    print("⚠️  Remember to update CHANGELOG.md before releasing!")
    input("Press Enter to continue...")

    ctx.run(f'bump-my-version bump {part}', pty=True)
    docs(ctx)
    commit(ctx, message)
    build(ctx)
    ctx.run('twine upload dist/*', pty=True)
```

### 5. Link from README.md
Add CHANGELOG link to README:
```markdown
## Documentation

- [API Documentation](https://blueshed.github.io/blueshed-gust/)
- [CHANGELOG](CHANGELOG.md)
- [Contributing Guide](CONTRIBUTING.md)
```

## Acceptance Criteria
- [ ] CHANGELOG.md exists in repository root
- [ ] Follows Keep a Changelog format
- [ ] Documents versions 0.0.1 through 0.0.26
- [ ] Each version includes date and changes
- [ ] Links to GitHub compare views
- [ ] Linked from README.md
- [ ] Release process includes CHANGELOG update

## Migration Path
1. Create initial CHANGELOG with current version (0.0.26)
2. Add "See git history" note for older versions if details unavailable
3. Commit all future changes with proper categorization

## Related
- Code review documentation gaps
- Improves transparency for users
- Required for 1.0.0 release

## Resources
- https://keepachangelog.com/
- https://semver.org/
- Example: https://github.com/pytest-dev/pytest/blob/main/CHANGELOG.rst
