# Contributing to DocTranslator

Thank you for your interest in contributing to DocTranslator! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Code Review Process](#code-review-process)

---

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive criticism
- Accept feedback gracefully
- Put the project's best interests first

### Unacceptable Behavior

- Harassment or discriminatory language
- Personal attacks
- Publishing others' private information
- Trolling or insulting comments
- Other unprofessional conduct

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher (for frontend)
- PostgreSQL 14 or higher
- Git

### Quick Start

1. **Fork the Repository**
   ```bash
   # Click "Fork" on GitHub
   git clone https://github.com/YOUR_USERNAME/doctranslator.git
   cd doctranslator
   ```

2. **Set Up Backend**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Set Up Frontend**
   ```bash
   cd frontend
   npm install
   ```

4. **Run Tests**
   ```bash
   cd backend
   pytest
   ```

---

## Development Setup

### Backend Development

```bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 9122
```

### Frontend Development

```bash
cd frontend
npm run dev
```

### Database Setup

```bash
cd backend
python app/database/init_db.py
python app/database/unified_seed.py
```

### Running with Docker

```bash
docker-compose up -d
docker-compose logs -f
```

---

## Code Style

### Python Code Style

We use **Ruff** for linting and formatting:

```bash
# Check for issues
python3 -m ruff check app/

# Auto-fix issues
python3 -m ruff check app/ --fix

# Format code
python3 -m ruff format app/
```

#### Style Rules

- **Line length**: 100 characters maximum
- **Imports**: Sorted alphabetically, grouped by type
- **Type hints**: Required for all public functions
- **Docstrings**: Google-style for all public APIs
- **Naming**:
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - `UPPER_CASE` for constants

#### Example

```python
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.connection import get_session

router = APIRouter()


def process_document(
    document_id: str,
    db: Session = Depends(get_session)
) -> dict[str, str]:
    """
    Process a document and return the result.

    Args:
        document_id: The ID of the document to process
        db: Database session

    Returns:
        Dictionary containing processing result

    Raises:
        HTTPException: If document not found

    Example:
        >>> result = process_document("doc-123")
        >>> print(result["status"])
        completed
    """
    # Implementation
    return {"status": "completed"}
```

### TypeScript Code Style

We use **ESLint** and **Prettier**:

```bash
# Lint
npm run lint

# Fix issues
npm run lint:fix

# Format
npm run format
```

### Commit Message Format

Use conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(api): add document classification endpoint

Implements new endpoint for automatic document type detection
using LLM-based classification.

Closes #123

---

fix(ocr): handle corrupt PDF files gracefully

Previously the application would crash when encountering
corrupted PDF files. Now returns a clear error message.

Fixes #456
```

---

## Making Changes

### Branching Strategy

- `main` - Production-ready code
- `dev` - Development branch
- `feature/feature-name` - Feature branches
- `fix/bug-name` - Bug fix branches

### Workflow

1. **Create a Branch**
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write code following style guidelines
   - Add tests for new functionality
   - Update documentation as needed

3. **Test Your Changes**
   ```bash
   # Backend tests
   cd backend
   pytest

   # Frontend tests
   cd frontend
   npm test

   # Linting
   python3 -m ruff check app/
   npm run lint
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat(scope): description of changes"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   # Create Pull Request on GitHub
   ```

---

## Testing

### Writing Tests

- **Unit Tests**: Test individual functions/classes
- **Integration Tests**: Test component interactions
- **API Tests**: Test HTTP endpoints
- **Coverage**: Aim for 80%+ coverage

### Test Structure

```python
# tests/test_feature.py
import pytest
from app.services.feature import FeatureService


class TestFeatureService:
    """Test suite for FeatureService."""

    def test_feature_success(self):
        """Test successful feature execution."""
        service = FeatureService()
        result = service.process()
        assert result.success is True

    def test_feature_error_handling(self):
        """Test error handling in feature."""
        service = FeatureService()
        with pytest.raises(ValueError):
            service.process(invalid_input=True)
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_feature.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run only fast tests
pytest -m "not slow"
```

### Test Markers

```python
@pytest.mark.slow
def test_long_running_operation():
    """Test that takes a long time."""
    pass

@pytest.mark.integration
def test_database_integration():
    """Test with real database."""
    pass
```

---

## Submitting Changes

### Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New code has tests (80%+ coverage)
- [ ] Documentation is updated
- [ ] Commit messages follow convention
- [ ] No merge conflicts with base branch
- [ ] PR description explains changes clearly

### PR Description Template

```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe testing performed:
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Related Issues
Closes #123
Related to #456

## Screenshots (if applicable)
Add screenshots for UI changes.

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests pass
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

---

## Code Review Process

### As an Author

1. **Respond to Feedback**
   - Address all comments
   - Ask for clarification if needed
   - Make requested changes promptly

2. **Keep PRs Small**
   - Aim for < 400 lines changed
   - Split large changes into multiple PRs
   - One feature/fix per PR

3. **Update Tests**
   - Ensure CI passes
   - Fix failing tests immediately
   - Add tests for edge cases

### As a Reviewer

1. **Be Constructive**
   - Explain reasoning for change requests
   - Suggest specific improvements
   - Acknowledge good work

2. **Check Thoroughly**
   - Code quality and style
   - Test coverage
   - Documentation completeness
   - Performance implications
   - Security considerations

3. **Approval Criteria**
   - All tests passing
   - No linting errors
   - Adequate test coverage
   - Documentation updated
   - Changes make sense

---

## Development Guidelines

### Security

- Never commit secrets or API keys
- Use environment variables for sensitive data
- Validate all user input
- Use parameterized queries (no SQL injection)
- Keep dependencies updated

### Performance

- Profile before optimizing
- Use async/await for I/O operations
- Implement caching where appropriate
- Monitor database query performance
- Set appropriate timeouts

### Error Handling

```python
# Good
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise HTTPException(status_code=500, detail="Operation failed")

# Bad
try:
    result = risky_operation()
except:  # Too broad
    pass  # Silent failure
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate levels
logger.debug("Detailed information for debugging")
logger.info("General information about application flow")
logger.warning("Something unexpected but handled")
logger.error("Error that needs attention")
logger.critical("Critical error, system may be unstable")
```

### Documentation

- Document all public APIs
- Use clear, concise language
- Include examples
- Keep docs up to date with code changes
- Add inline comments for complex logic

---

## Getting Help

### Resources

- **Documentation**: [docs/](docs/)
- **API Reference**: [docs/API.md](docs/API.md)
- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **GitHub Issues**: https://github.com/Dropicx/doctranslator/issues

### Communication

- **Bug Reports**: Create a GitHub issue
- **Feature Requests**: Create a GitHub issue
- **Questions**: Start a GitHub Discussion
- **Security Issues**: Email (don't create public issue)

### Issue Templates

When creating an issue, provide:

**For Bugs:**
- Description of the problem
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details
- Relevant logs/screenshots

**For Features:**
- Use case description
- Proposed solution
- Alternatives considered
- Impact on existing functionality

---

## License

By contributing to DocTranslator, you agree that your contributions will be licensed under the same license as the project.

---

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Credited in release notes
- Acknowledged in commit messages (Co-Authored-By)

---

## Thank You!

Your contributions make DocTranslator better for everyone. We appreciate your time and effort!

For questions about contributing, please create a GitHub issue or discussion.
