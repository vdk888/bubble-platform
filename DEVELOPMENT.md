# 🚀 Bubble Platform - VS Code Development Guide

## Quick Start

### 1. Open Project in VS Code
```bash
cd C:\Users\Joris\Documents\Unity\bubble-platform
code .
```

### 2. Install Recommended Extensions
- **Python** (ms-python.python)
- **Docker** (ms-azuretools.vscode-docker)
- **Pylance** (ms-python.vscode-pylance)
- **SQLite Viewer** (alexcvzz.vscode-sqlite)

## Development Options

### Option 1: Direct Python Development (Fastest for Testing)
```bash
# 1. Open VS Code integrated terminal (Ctrl + `)
cd backend

# 2. Install dependencies (if not already done)
pip install -r requirements.txt

# 3. Start the backend server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**VS Code Configuration:**
- Set Python interpreter to your global Python (Ctrl+Shift+P -> "Python: Select Interpreter")
- Use the integrated terminal for running commands
- SQLite database will be created at `backend/bubble_dev.db`

### Option 2: Docker Development (Production-like)
```bash
# 1. Start full environment
docker-compose up --build

# 2. Check container status
docker-compose ps

# 3. View logs
docker-compose logs backend -f
```

**VS Code Docker Integration:**
- Use Docker extension to view containers
- Right-click containers to view logs
- Attach VS Code to running containers for debugging

### Option 3: VS Code Dev Containers (Recommended for Team)
Create `.vscode/devcontainer.json`:
```json
{
    "name": "Bubble Platform Dev",
    "dockerComposeFile": "../docker-compose.yml",
    "service": "backend",
    "workspaceFolder": "/app",
    "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance"
    ]
}
```

## Testing Your Setup

### Health Check Endpoints
```bash
# Basic health check
curl http://localhost:8000/health/

# Readiness check (database connectivity)
curl http://localhost:8000/health/ready

# System metrics
curl http://localhost:8000/health/metrics

# Feature flags
curl http://localhost:8000/api/v1/features/

# API documentation
# Open http://localhost:8000/docs in browser
```

### Database Inspection
```bash
# SQLite database location
backend/bubble_dev.db

# View tables using VS Code SQLite extension
# Or use command line:
sqlite3 backend/bubble_dev.db ".tables"
```

## Debugging in VS Code

### Python Debugging Configuration
Create `.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI Server",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/backend",
            "module": "uvicorn",
            "args": [
                "app.main:app",
                "--host", "127.0.0.1",
                "--port", "8000",
                "--reload"
            ],
            "cwd": "${workspaceFolder}/backend",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/backend"
            },
            "console": "integratedTerminal"
        }
    ]
}
```

### Breakpoint Debugging
1. Set breakpoints in Python code
2. Press F5 or use "Run and Debug" panel
3. Test endpoints to hit breakpoints

## Database Migrations

### Alembic Commands (from backend directory)
```bash
# Generate migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# View migration history
alembic history

# Rollback migration
alembic downgrade -1
```

## Running Tests

### Backend Tests
```bash
cd backend

# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest app/tests/test_health.py -v
```

### Test Database
Tests use separate SQLite database: `backend/bubble_test.db`

## Environment Variables

### Development (.env file locations)
```bash
# Root level (for Docker)
.env

# Backend level (for direct Python)
backend/.env
```

### Key Variables for Development
```bash
SECRET_KEY=your-development-secret-key
DATABASE_URL=sqlite:///./bubble_dev.db
DATABASE_TEST_URL=sqlite:///./bubble_test.db
CLAUDE_API_KEY=your-claude-api-key
ALPACA_API_KEY=your-alpaca-key
ALPACA_SECRET_KEY=your-alpaca-secret
DEBUG=true
ENVIRONMENT=development
```

## VS Code Workspace Settings

Create `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.analysis.extraPaths": ["./backend"],
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestPath": "pytest",
    "python.testing.pytestArgs": ["backend"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "backend/bubble_*.db": true
    }
}
```

## Common Development Tasks

### Add New Model
1. Create model in `backend/app/models/your_model.py`
2. Import in `backend/app/models/__init__.py`
3. Generate migration: `alembic revision --autogenerate -m "Add YourModel"`
4. Apply migration: `alembic upgrade head`

### Add New API Endpoint
1. Create endpoint in `backend/app/api/v1/your_endpoint.py`
2. Include router in `backend/app/main.py`
3. Test with curl or Swagger UI at `http://localhost:8000/docs`

### Debug Database Issues
1. Check database file exists: `backend/bubble_dev.db`
2. Inspect with SQLite extension in VS Code
3. Check migration status: `alembic current`
4. View logs for SQLAlchemy errors

## Troubleshooting

### Common Issues

**Import errors:**
```bash
# Make sure you're in the right directory
cd backend

# Check Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Database connection errors:**
```bash
# Check if database file exists
ls -la backend/bubble_*.db

# Reset database (careful - loses data)
rm backend/bubble_dev.db
python -m uvicorn app.main:app --reload
```

**Port already in use:**
```bash
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process or use different port
python -m uvicorn app.main:app --port 8001 --reload
```

**Docker issues:**
```bash
# Clean up Docker resources
docker-compose down
docker system prune -f

# Rebuild from scratch
docker-compose up --build --force-recreate
```
