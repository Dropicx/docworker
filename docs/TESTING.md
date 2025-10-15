# Testing Guide for DocTranslator

Comprehensive guide to running, writing, and maintaining tests for the DocTranslator project.

## Table of Contents

- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Types](#test-types)
- [Writing Tests](#writing-tests)
- [CI/CD Integration](#cicd-integration)
- [Coverage Reports](#coverage-reports)
- [Best Practices](#best-practices)

---

## Test Structure

Our test suite is organized into three main categories:

```
backend/tests/
├── unit/                  # Unit tests (fast, isolated)
│   ├── services/          # Service layer tests
│   ├── models/            # Data model tests
│   └── utils/             # Utility function tests
├── integration/           # Integration tests (components working together)
│   ├── api/               # API endpoint tests
│   ├── database/          # Database integration tests
│   └── worker/            # Celery worker tests
├── e2e/                   # End-to-end tests (complete workflows)
│   └── flows/             # User workflow tests
├── fixtures/              # Test data and mocks
│   ├── sample_documents/  # Sample PDFs, images
│   └── mock_data/         # Mock API responses
└── conftest.py            # Shared pytest fixtures

frontend/src/
├── components/
│   └── __tests__/         # Component tests
├── services/
│   └── __tests__/         # Service/API client tests
└── test/
    └── setup.ts           # Test configuration
```

---

## Running Tests

### Backend Tests

#### Run All Tests
```bash
cd backend
pytest
```

#### Run Specific Test Types
```bash
# Unit tests only (fast)
pytest tests/unit/

# Integration tests
pytest tests/integration/

# E2E tests
pytest tests/e2e/ -m e2e

# Specific test file
pytest tests/integration/api/test_pipeline_api.py

# Specific test function
pytest tests/unit/test_error_handling.py::test_validation_error
```

#### Run with Coverage
```bash
# Generate coverage report
pytest --cov=app --cov-report=html --cov-report=term-missing

# View HTML report
open htmlcov/index.html
```

#### Run Tests in Parallel
```bash
# Install pytest-xdist
pip install pytest-xdist

# Run with 4 workers
pytest -n 4
```

### Frontend Tests

#### Run All Tests
```bash
cd frontend
npm test
```

#### Run with Coverage
```bash
npm run test:coverage
```

#### Watch Mode (for development)
```bash
npm run test:watch
```

#### Run Specific Test
```bash
npm test -- UploadZone.test.tsx
```

---

## Test Types

### 1. Unit Tests

**Purpose**: Test individual functions/classes in isolation

**Location**: `backend/tests/unit/`

**Example**:
```python
def test_privacy_filter_removes_names():
    """Test that AdvancedPrivacyFilter removes personal names"""
    filter = AdvancedPrivacyFilter()
    text = "Patient: Max Mustermann, Age: 45"

    result = filter.remove_pii(text)

    assert "Max Mustermann" not in result
    assert "[NAME]" in result
```

**Characteristics**:
- Fast (< 1ms per test)
- No external dependencies (mocked)
- High coverage target (80%+)

### 2. Integration Tests

**Purpose**: Test component interactions and API endpoints

**Location**: `backend/tests/integration/`

**Example**:
```python
def test_create_pipeline_step(client, mock_auth, seed_test_data):
    """Test POST /api/pipeline/steps"""
    new_step = {
        "name": "Test Step",
        "order": 1,
        "prompt_template": "Process: {input_text}",
        "selected_model_id": 1,
        "temperature": 0.7,
    }

    response = client.post("/api/pipeline/steps", json=new_step)

    assert response.status_code == 201
    assert response.json()["name"] == "Test Step"
```

**Characteristics**:
- Moderate speed (10-100ms per test)
- Uses TestClient with in-memory database
- Tests real FastAPI routes

### 3. E2E Tests

**Purpose**: Test complete user workflows from start to finish

**Location**: `backend/tests/e2e/flows/`

**Example**:
```python
@pytest.mark.e2e
def test_complete_document_processing_flow(client, seed_full_pipeline):
    """E2E Test: Upload → OCR → Processing → Result"""

    # 1. Upload document
    response = client.post("/api/upload", files={"file": img_file})
    processing_id = response.json()["processing_id"]

    # 2. Check status
    response = client.get(f"/api/status/{processing_id}")
    assert response.json()["status"] == "pending"

    # 3. Wait for completion (simulated)
    # ... simulate processing ...

    # 4. Get result
    response = client.get(f"/api/result/{processing_id}")
    assert "translated_text" in response.json()
```

**Characteristics**:
- Slow (100ms - 5s per test)
- Tests complete workflows
- Uses mocked external services (OCR, AI)

---

## Writing Tests

### Backend Testing Best Practices

#### 1. Use Fixtures for Setup
```python
@pytest.fixture
def sample_document_class(db_session):
    """Create a sample document class for testing"""
    doc_class = DocumentClassDB(
        class_key="TEST_CLASS",
        display_name="Test Class",
        is_enabled=True
    )
    db_session.add(doc_class)
    db_session.commit()
    return doc_class
```

#### 2. Mock External Services
```python
@patch('app.services.ovh_client.OVHAIClient.create_completion')
def test_ai_translation(mock_completion):
    mock_completion.return_value = "Translated text"

    result = translator.translate("Original text")

    assert result == "Translated text"
    mock_completion.assert_called_once()
```

#### 3. Test Error Conditions
```python
def test_invalid_file_type_raises_error():
    with pytest.raises(FileValidationError, match="Invalid file type"):
        FileValidator.validate_file("invalid.txt")
```

#### 4. Use Descriptive Test Names
```python
# ❌ Bad
def test_1():
    pass

# ✅ Good
def test_privacy_filter_removes_email_addresses():
    pass
```

### Frontend Testing Best Practices

#### 1. Test User Interactions
```typescript
it('calls onUpload when file is selected', async () => {
  const mockOnUpload = vi.fn();
  render(<UploadZone onUpload={mockOnUpload} />);

  const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
  const input = screen.getByTestId('file-input');

  fireEvent.change(input, { target: { files: [file] } });

  await waitFor(() => {
    expect(mockOnUpload).toHaveBeenCalledWith(file);
  });
});
```

#### 2. Test Component Rendering
```typescript
it('renders upload zone with correct text', () => {
  render(<UploadZone onUpload={vi.fn()} />);

  expect(screen.getByText(/Dokument hochladen/i)).toBeInTheDocument();
  expect(screen.getByText(/PDF, JPG/i)).toBeInTheDocument();
});
```

#### 3. Test Error States
```typescript
it('shows error for invalid file type', async () => {
  render(<UploadZone onUpload={vi.fn()} />);

  const invalidFile = new File(['test'], 'test.txt', { type: 'text/plain' });
  fireEvent.change(input, { target: { files: [invalidFile] } });

  await waitFor(() => {
    expect(screen.getByText(/Ungültiger Dateityp/i)).toBeInTheDocument();
  });
});
```

---

## CI/CD Integration

### GitHub Actions Workflow

Our CI/CD pipeline runs automatically on every push and pull request:

**Backend Tests** (`backend-tests` job):
- Runs pytest with coverage
- Uploads coverage to Codecov
- Fails if tests fail

**Frontend Tests** (when implemented):
- Runs Vitest
- Checks coverage thresholds
- Fails if tests fail

### Configuration

See `.github/workflows/quality.yml`:

```yaml
backend-tests:
  runs-on: arc-runner-set
  steps:
    - name: Run pytest
      run: |
        pytest --cov=app --cov-report=xml --cov-report=term-missing --junitxml=pytest-report.xml

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v4
      with:
        file: ./backend/coverage.xml
```

### Required Checks

All tests must pass before merging to `main` or `dev` branches.

---

## Coverage Reports

### Viewing Coverage Locally

#### Backend
```bash
cd backend
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

#### Frontend
```bash
cd frontend
npm run test:coverage
open coverage/index.html
```

### Coverage Targets

- **Backend**: 80%+ overall coverage
- **Frontend**: 70%+ overall coverage
- **Critical paths**: 90%+ coverage (auth, payment, data processing)

### Codecov Integration

Coverage reports are automatically uploaded to Codecov on every CI run:
- View reports at: https://codecov.io/gh/Dropicx/doctranslator
- Coverage trends tracked over time
- Pull requests show coverage diff

---

## Best Practices

### General Guidelines

1. **Write tests first (TDD)**: When fixing bugs or adding features
2. **Keep tests independent**: No test should depend on another
3. **Use descriptive names**: Test names should explain what they test
4. **Test edge cases**: Not just the happy path
5. **Mock external services**: Don't make real API calls in tests
6. **Keep tests fast**: Unit tests < 1ms, integration < 100ms

### Test Naming Convention

```python
def test_<function_name>_<scenario>_<expected_result>():
    """
    Format: test_what_when_then

    Examples:
    - test_privacy_filter_removes_pii_from_medical_text
    - test_upload_endpoint_returns_400_for_invalid_file
    - test_pipeline_executor_skips_disabled_steps
    """
    pass
```

### Fixture Organization

- **Shared fixtures**: In `conftest.py`
- **Test-specific fixtures**: In the test file
- **Reusable test data**: In `fixtures/mock_data/`

### Mocking Strategy

1. **Mock at the boundary**: Mock external services (APIs, databases in unit tests)
2. **Use real implementations** when possible in integration tests
3. **Don't mock what you're testing**

### Test Data Management

- Use `factories` or `fixtures` for test data creation
- Store sample documents in `fixtures/sample_documents/`
- Use `faker` library for generating realistic test data

---

## Troubleshooting

### Common Issues

#### Tests fail with "Database locked"
**Solution**: Use in-memory SQLite or ensure proper session cleanup

#### Tests are too slow
**Solution**:
- Use mocks instead of real services
- Run unit tests separately from integration tests
- Use pytest-xdist for parallel execution

#### Coverage is too low
**Solution**:
- Identify uncovered code: `pytest --cov=app --cov-report=term-missing`
- Write tests for critical paths first
- Focus on business logic, not boilerplate

#### Frontend tests can't find components
**Solution**:
- Check test setup in `src/test/setup.ts`
- Ensure proper imports
- Use `data-testid` for hard-to-query elements

---

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Vitest Documentation](https://vitest.dev/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

---

## Contributing

When contributing tests:

1. Follow the existing structure
2. Write tests for new features
3. Update tests when modifying existing code
4. Ensure all tests pass before submitting PR
5. Maintain or improve coverage

For questions or issues, open a GitHub issue or contact the team.
