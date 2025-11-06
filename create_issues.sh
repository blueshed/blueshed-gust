#!/bin/bash
# Script to create all GitHub issues from code review
# Run this after merging the PR

set -e

echo "Creating GitHub issues from code review templates..."

# Issue #1: CI/CD Pipeline
echo "Creating Issue #1: CI/CD Pipeline..."
gh issue create \
  --title "Add CI/CD Pipeline with GitHub Actions" \
  --body-file .github_issues/01_ci_cd_pipeline.md \
  --label "enhancement,infrastructure,high-priority"

# Issue #2: CHANGELOG
echo "Creating Issue #2: CHANGELOG.md..."
gh issue create \
  --title "Create CHANGELOG.md" \
  --body-file .github_issues/02_changelog.md \
  --label "documentation,high-priority"

# Issue #3: Error Handling
echo "Creating Issue #3: Error Handling..."
gh issue create \
  --title "Improve Error Handling and Response Standardization" \
  --body-file .github_issues/03_error_handling.md \
  --label "enhancement,refactoring,security,high-priority"

# Issue #4: JSON-RPC Error Constants
echo "Creating Issue #4: JSON-RPC Error Constants..."
gh issue create \
  --title "Add JSON-RPC Error Code Constants" \
  --body-file .github_issues/04_jsonrpc_error_constants.md \
  --label "enhancement,code-quality,medium-priority"

# Issue #5: Input Validation
echo "Creating Issue #5: Input Validation..."
gh issue create \
  --title "Add Optional Input Validation Support" \
  --body-file .github_issues/05_input_validation.md \
  --label "enhancement,validation,medium-priority"

# Issue #6: PostgreSQL Cache TTL
echo "Creating Issue #6: PostgreSQL Cache TTL..."
gh issue create \
  --title "Add PostgreSQL Function Signature Cache TTL" \
  --body-file .github_issues/06_postgres_cache_ttl.md \
  --label "enhancement,postgres,medium-priority"

# Issue #7: Test Coverage
echo "Creating Issue #7: Test Coverage..."
gh issue create \
  --title "Expand Test Coverage to 90%+" \
  --body-file .github_issues/07_test_coverage.md \
  --label "testing,quality,low-priority"

# Issue #8: Security Hardening
echo "Creating Issue #8: Security Hardening..."
gh issue create \
  --title "Security Hardening Enhancements" \
  --body-file .github_issues/08_security_hardening.md \
  --label "security,enhancement,low-priority"

# Issue #9: Documentation
echo "Creating Issue #9: Documentation Improvements..."
gh issue create \
  --title "Documentation Improvements" \
  --body-file .github_issues/09_documentation_improvements.md \
  --label "documentation,low-priority"

echo ""
echo "✅ All 9 issues created successfully!"
echo ""
echo "View issues at: https://github.com/blueshed/blueshed-gust/issues"
