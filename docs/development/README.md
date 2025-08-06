# Development Documentation - DocTranslator

## Table of Contents
1. [Development Setup](#development-setup)
2. [Project Structure](#project-structure)
3. [Development Workflow](#development-workflow)
4. [Code Standards](#code-standards)
5. [Testing Guide](#testing-guide)
6. [Debugging](#debugging)
7. [API Development](#api-development)
8. [Frontend Development](#frontend-development)
9. [Contributing Guidelines](#contributing-guidelines)

## Development Setup

### Prerequisites

- **Operating System**: Linux, macOS, or Windows with WSL2
- **Node.js**: Version 20.x or higher
- **Python**: Version 3.11 or higher
- **Docker**: Version 24.x or higher
- **Docker Compose**: Version 2.x or higher
- **Git**: Latest version

### Quick Start

#### 1. Clone the Repository

```bash
git clone <repository-url>
cd doctranslator
```

#### 2. Install Ollama (Local Development)

```bash
# Linux/macOS
curl -fsSL https://ollama.ai/install.sh | sh

# Pull required models
ollama pull mistral-nemo:latest
ollama pull llama3.2:latest
```

#### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-asyncio black flake8 mypy

# Run backend in development mode
uvicorn app.main:app --reload --host 0.0.0.0 --port 9122
```

#### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

#### 5. Docker Development Setup

```bash
# Build and run all services
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Environment Variables

#### Backend (.env)
```env
# Environment
ENVIRONMENT=development

# Ollama Configuration
OLLAMA_URL=http://localhost:11434

# Security
SECRET_KEY=your-secret-key-here

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60

# Logging
LOG_LEVEL=DEBUG
```

#### Frontend (.env.local)
```env
# API Configuration
VITE_API_URL=http://localhost:9122/api

# Feature Flags
VITE_ENABLE_DEBUG=true
```

## Project Structure

### Overall Structure
```
doctranslator/
├── backend/                  # FastAPI backend application
│   ├── app/
│   │   ├── main.py          # Application entry point
│   │   ├── models/          # Pydantic models
│   │   ├── routers/         # API endpoints
│   │   └── services/        # Business logic
│   ├── tests/               # Backend tests
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                # React frontend application
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── services/        # API services
│   │   ├── types/           # TypeScript types
│   │   └── App.tsx         # Main component
│   ├── public/             # Static assets
│   ├── Dockerfile
│   └── package.json
│
├── docs/                   # Documentation
├── scripts/                # Utility scripts
└── docker-compose.yml      # Docker orchestration
```

### Backend Structure Details
```
backend/app/
├── __init__.py
├── main.py                 # FastAPI app configuration
├── models/
│   ├── __init__.py
│   └── document.py        # Data models and schemas
├── routers/
│   ├── __init__.py
│   ├── health.py          # Health check endpoints
│   ├── process.py         # Processing endpoints
│   └── upload.py          # Upload endpoints
└── services/
    ├── __init__.py
    ├── cleanup.py         # Cleanup service
    ├── file_validator.py  # File validation
    ├── ollama_client.py   # AI integration
    └── text_extractor.py  # OCR and text extraction
```

### Frontend Structure Details
```
frontend/src/
├── components/
│   ├── FileUpload.tsx        # Upload component
│   ├── ProcessingStatus.tsx  # Status display
│   └── TranslationResult.tsx # Result display
├── services/
│   └── api.ts               # API client
├── types/
│   └── api.ts               # TypeScript interfaces
├── App.tsx                  # Main application
├── index.tsx               # Entry point
└── index.css               # Global styles
```

## Development Workflow

### Git Workflow

#### Branch Strategy
```
main                    # Production-ready code
├── develop            # Integration branch
    ├── feature/*      # New features
    ├── bugfix/*       # Bug fixes
    ├── hotfix/*       # Emergency fixes
    └── release/*      # Release preparation
```

#### Commit Convention
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build/config changes

**Example:**
```bash
git commit -m "feat(upload): add progress indicator for file uploads"
```

### Development Cycle

1. **Create Feature Branch**
```bash
git checkout -b feature/new-feature develop
```

2. **Develop and Test Locally**
```bash
# Backend testing
cd backend
pytest tests/

# Frontend testing
cd frontend
npm test
```

3. **Code Quality Checks**
```bash
# Backend
black app/
flake8 app/
mypy app/

# Frontend
npm run lint
npm run type-check
```

4. **Create Pull Request**
- Target: `develop` branch
- Include tests
- Update documentation
- Pass CI/CD checks

## Code Standards

### Python Code Standards

#### Style Guide
- Follow PEP 8
- Use Black for formatting
- Maximum line length: 88 characters
- Use type hints

#### Example
```python
from typing import Optional, Dict, Any
from fastapi import HTTPException
from pydantic import BaseModel


class DocumentProcessor:
    """Processes medical documents for translation."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.ollama_client = OllamaClient(config.get("ollama_url"))
    
    async def process_document(
        self, 
        content: bytes, 
        document_type: str
    ) -> Optional[str]:
        """
        Process a document and return translated text.
        
        Args:
            content: Document content in bytes
            document_type: Type of document (pdf, image)
            
        Returns:
            Translated text or None if processing fails
            
        Raises:
            HTTPException: If processing fails
        """
        try:
            text = await self.extract_text(content, document_type)
            translated = await self.ollama_client.translate(text)
            return translated
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
```

### TypeScript/React Standards

#### Style Guide
- Use functional components
- Prefer hooks over class components
- Use TypeScript strict mode
- Props interface naming: `ComponentNameProps`

#### Example
```typescript
import React, { useState, useCallback } from 'react';

interface FileUploadProps {
  onUploadSuccess: (response: UploadResponse) => void;
  onUploadError: (error: string) => void;
  maxSize?: number;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onUploadSuccess,
  onUploadError,
  maxSize = 10485760, // 10MB default
}) => {
  const [uploading, setUploading] = useState<boolean>(false);
  
  const handleUpload = useCallback(async (file: File) => {
    if (file.size > maxSize) {
      onUploadError(`File size exceeds ${maxSize / 1048576}MB`);
      return;
    }
    
    setUploading(true);
    try {
      const response = await uploadFile(file);
      onUploadSuccess(response);
    } catch (error) {
      onUploadError(error.message);
    } finally {
      setUploading(false);
    }
  }, [maxSize, onUploadSuccess, onUploadError]);
  
  return (
    <div className="upload-container">
      {/* Component JSX */}
    </div>
  );
};
```

## Testing Guide

### Backend Testing

#### Unit Tests
```python
# tests/test_file_validator.py
import pytest
from app.services.file_validator import FileValidator


class TestFileValidator:
    @pytest.mark.asyncio
    async def test_valid_pdf_file(self):
        """Test validation of valid PDF file."""
        mock_file = create_mock_pdf_file()
        is_valid, message = await FileValidator.validate_file(mock_file)
        assert is_valid is True
        assert message == ""
    
    @pytest.mark.asyncio
    async def test_oversized_file(self):
        """Test rejection of oversized file."""
        mock_file = create_mock_file(size=11 * 1024 * 1024)  # 11MB
        is_valid, message = await FileValidator.validate_file(mock_file)
        assert is_valid is False
        assert "too large" in message.lower()
```

#### Integration Tests
```python
# tests/test_api.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] in ["healthy", "degraded"]


def test_upload_document():
    """Test document upload."""
    with open("tests/fixtures/sample.pdf", "rb") as f:
        response = client.post(
            "/api/upload",
            files={"file": ("test.pdf", f, "application/pdf")}
        )
    assert response.status_code == 200
    assert "processing_id" in response.json()
```

### Frontend Testing

#### Component Tests
```typescript
// src/components/__tests__/FileUpload.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { FileUpload } from '../FileUpload';

describe('FileUpload Component', () => {
  it('should accept valid file types', () => {
    const onSuccess = jest.fn();
    const onError = jest.fn();
    
    render(
      <FileUpload 
        onUploadSuccess={onSuccess}
        onUploadError={onError}
      />
    );
    
    const input = screen.getByLabelText(/upload/i);
    const file = new File(['content'], 'test.pdf', { 
      type: 'application/pdf' 
    });
    
    fireEvent.change(input, { target: { files: [file] } });
    
    expect(onError).not.toHaveBeenCalled();
  });
});
```

### Running Tests

```bash
# Backend tests
cd backend
pytest                           # Run all tests
pytest tests/test_api.py        # Run specific file
pytest -v                       # Verbose output
pytest --cov=app                # With coverage

# Frontend tests
cd frontend
npm test                        # Run all tests
npm test -- --coverage         # With coverage
npm test -- --watch           # Watch mode
```

## Debugging

### Backend Debugging

#### Using VS Code
```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--port", "9122"
      ],
      "jinja": true,
      "justMyCode": false
    }
  ]
}
```

#### Debug Utilities
```python
# backend/debug_ollama.py
import asyncio
from app.services.ollama_client import OllamaClient


async def test_ollama():
    client = OllamaClient()
    
    # Test connection
    connected = await client.check_connection()
    print(f"Connected: {connected}")
    
    # List models
    models = await client.list_models()
    print(f"Available models: {models}")
    
    # Test translation
    text = "Patient leidet an Hypertonie"
    result = await client.translate_medical_text(text)
    print(f"Translation: {result}")


if __name__ == "__main__":
    asyncio.run(test_ollama())
```

### Frontend Debugging

#### Browser DevTools
```javascript
// Add debug logging
console.group('API Request');
console.log('Endpoint:', endpoint);
console.log('Payload:', payload);
console.log('Headers:', headers);
console.groupEnd();

// Conditional debugging
if (process.env.NODE_ENV === 'development') {
  console.debug('Debug info:', data);
}
```

#### React DevTools
- Install React Developer Tools extension
- Inspect component props and state
- Profile performance
- Track re-renders

## API Development

### Adding New Endpoints

1. **Define Models** (models/document.py)
```python
class NewFeatureRequest(BaseModel):
    field1: str
    field2: Optional[int] = None
    
class NewFeatureResponse(BaseModel):
    id: str
    result: str
```

2. **Create Router** (routers/new_feature.py)
```python
from fastapi import APIRouter, HTTPException
from app.models.document import NewFeatureRequest, NewFeatureResponse

router = APIRouter()

@router.post("/new-feature", response_model=NewFeatureResponse)
async def process_new_feature(request: NewFeatureRequest):
    # Implementation
    return NewFeatureResponse(id="123", result="success")
```

3. **Register Router** (main.py)
```python
from app.routers import new_feature

app.include_router(
    new_feature.router, 
    prefix="/api", 
    tags=["new-feature"]
)
```

### API Documentation

FastAPI automatically generates OpenAPI documentation:
- Swagger UI: `http://localhost:9122/docs`
- ReDoc: `http://localhost:9122/redoc`

## Frontend Development

### Component Development

#### Creating New Components
```typescript
// src/components/NewComponent.tsx
import React from 'react';

interface NewComponentProps {
  title: string;
  onAction: () => void;
}

export const NewComponent: React.FC<NewComponentProps> = ({ 
  title, 
  onAction 
}) => {
  return (
    <div className="component-container">
      <h2>{title}</h2>
      <button onClick={onAction}>Action</button>
    </div>
  );
};
```

#### Using Tailwind CSS
```tsx
<div className="max-w-4xl mx-auto px-4 py-8">
  <div className="bg-white rounded-lg shadow-lg p-6">
    <h1 className="text-2xl font-bold text-gray-900 mb-4">
      Title
    </h1>
    <p className="text-gray-600 leading-relaxed">
      Content
    </p>
  </div>
</div>
```

### State Management

Currently using React's built-in state. For complex state:

```typescript
// Using Context API
const AppContext = React.createContext<AppContextType>(null);

export const AppProvider: React.FC = ({ children }) => {
  const [state, setState] = useState(initialState);
  
  return (
    <AppContext.Provider value={{ state, setState }}>
      {children}
    </AppContext.Provider>
  );
};

// Using the context
const { state, setState } = useContext(AppContext);
```

## Contributing Guidelines

### Before Contributing

1. **Check existing issues** for duplicates
2. **Discuss major changes** in an issue first
3. **Follow code standards** outlined above
4. **Write tests** for new features
5. **Update documentation** as needed

### Pull Request Process

1. **Fork and Clone**
```bash
git clone https://github.com/your-username/doctranslator.git
```

2. **Create Feature Branch**
```bash
git checkout -b feature/amazing-feature
```

3. **Make Changes**
- Write clean, documented code
- Add tests
- Update documentation

4. **Test Thoroughly**
```bash
# Run all tests
./scripts/test-all.sh
```

5. **Submit PR**
- Clear description
- Reference related issues
- Include screenshots for UI changes
- Ensure CI passes

### Code Review Checklist

- [ ] Code follows project standards
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] No security vulnerabilities
- [ ] Performance impact considered
- [ ] Error handling is comprehensive
- [ ] Logging is appropriate

---

*Development Documentation Version: 1.0.0 | Last Updated: January 2025*