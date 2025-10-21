# Pull Request

## Description

<!-- Provide a clear and concise description of your changes -->



## Type of Change

<!-- Mark the appropriate option with an "x" -->

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] 🎨 Code style update (formatting, renaming)
- [ ] ♻️ Code refactoring (no functional changes)
- [ ] ⚡ Performance improvement
- [ ] ✅ Test update
- [ ] 🔧 Configuration change
- [ ] 🔨 Build/CI update

## Related Issues

<!-- Link to related issues using "Closes #123" or "Related to #456" -->

Closes #
Related to #

## Changes Made

<!-- List the main changes made in this PR -->

-
-
-

## Testing

### Test Coverage

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] API tests added/updated
- [ ] Manual testing completed

### Test Results

<!-- Describe the testing you performed -->

```bash
# Example test output
pytest tests/test_feature.py
================================= test session starts =================================
collected 10 items

tests/test_feature.py .......... [100%]
================================= 10 passed in 2.34s ==================================
```

### Manual Testing Steps

<!-- If manual testing was performed, describe the steps -->

1.
2.
3.

## Code Quality Checklist

<!-- Ensure all items are checked before requesting review -->

- [ ] Code follows project style guidelines (ruff check passes)
- [ ] Code is formatted properly (ruff format applied)
- [ ] All tests pass locally
- [ ] New code has appropriate test coverage (aim for 80%+)
- [ ] Documentation has been updated (if needed)
- [ ] Commit messages follow conventional commits format
- [ ] No merge conflicts with base branch
- [ ] No new linting errors introduced
- [ ] Type hints added for all new functions

## Documentation

- [ ] README updated (if needed)
- [ ] API documentation updated (if needed)
- [ ] Inline code comments added for complex logic
- [ ] CHANGELOG.md updated (for releases)

## Security Considerations

<!-- Address any security implications of your changes -->

- [ ] No sensitive data exposed (API keys, passwords, etc.)
- [ ] User input is validated and sanitized
- [ ] No SQL injection vulnerabilities
- [ ] No hardcoded secrets
- [ ] Dependencies are up to date

## Performance Considerations

<!-- Describe any performance implications -->

- [ ] No performance regressions introduced
- [ ] Large database queries optimized (if applicable)
- [ ] Caching implemented where appropriate (if applicable)
- [ ] Async/await used for I/O operations (if applicable)

## Breaking Changes

<!-- If this is a breaking change, describe the migration path -->

### What breaks?

<!--
- API endpoint changes
- Database schema changes
- Configuration changes
- Dependency updates
-->

### Migration guide

<!--
Provide step-by-step instructions for users to migrate:
1. Update environment variables
2. Run database migrations
3. etc.
-->

## Screenshots / Videos

<!-- Add screenshots or videos for UI changes -->

<!-- Before: -->


<!-- After: -->


## Deployment Notes

<!-- Any special considerations for deployment? -->

- [ ] Database migrations required
- [ ] Environment variables need updating
- [ ] Configuration changes required
- [ ] Service restart required
- [ ] Cache clearing required

### Required Environment Variables

```bash
# If new environment variables are needed, list them here
NEW_VAR=example_value
```

## Additional Context

<!-- Add any other context about the PR here -->



## Reviewer Notes

<!-- Anything specific you want reviewers to focus on? -->



---

## Checklist for Reviewers

<!-- Reviewers should verify: -->

- [ ] Code is clear and maintainable
- [ ] Tests are comprehensive and pass
- [ ] Documentation is complete and accurate
- [ ] No security vulnerabilities introduced
- [ ] Performance is acceptable
- [ ] Breaking changes are clearly documented
- [ ] Code follows project conventions

---

**By submitting this PR, I confirm that:**

- [ ] I have read the [Contributing Guidelines](../CONTRIBUTING.md)
- [ ] My code follows the project's code style
- [ ] I have performed a self-review of my code
- [ ] I have commented my code where necessary
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix/feature works
- [ ] New and existing tests pass locally
- [ ] Any dependent changes have been merged and published
