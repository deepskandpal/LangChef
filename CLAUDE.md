# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend (Python FastAPI)
```bash
cd backend
# Install dependencies with uv
uv venv .venv && source .venv/bin/activate && uv pip install -e .

# Run development server
uvicorn main:app --reload

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"

# Development tools
black .                    # Format code
isort .                    # Sort imports
mypy .                     # Type checking
pytest                     # Run tests
```

### Frontend (React)
```bash
cd frontend
npm install               # Install dependencies
npm start                 # Start development server (port 3000)
npm run build            # Build for production
npm test                 # Run tests
```

### Docker Development
```bash
docker-compose up -d      # Start all services
docker-compose logs -f    # View logs
docker-compose down       # Stop services
```

## Architecture Overview

LangChef is an end-to-end LLM workflow platform with three main components:

### 1. Backend (`/backend`)
- **FastAPI** application serving REST API on port 8000 (8001 in Docker)
- **PostgreSQL** database with SQLAlchemy ORM and Alembic migrations
- **Authentication** via JWT tokens with user management
- **Key modules:**
  - `api/routes/` - API endpoints (prompts, datasets, experiments, traces, models, auth, chats)
  - `models/` - SQLAlchemy database models
  - `services/` - Business logic (auth_service.py, llm_service.py)
  - `config.py` - Environment configuration and settings

### 2. Frontend (`/frontend`)
- **React 18** with Material-UI components
- **React Router** for navigation with protected routes
- **Key features:**
  - Dashboard, Prompts, Datasets, Experiments, Playground, Traces
  - Agent Flow Builder (visual workflow editor using ReactFlow)
  - Authentication context and theme management
- **Main structure:**
  - `src/pages/` - Main application pages
  - `src/components/` - Reusable components including AgentBuilder
  - `src/contexts/` - React context providers (Auth, Theme)

### 3. Agent API (`/agent-api`)
- **Node.js/Express** microservice on port 5000 (5001 in Docker)
- Handles agent workflow execution and processing
- Integrated with frontend's Agent Flow Builder

## Key Configuration

### Environment Variables (.env)
```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/langchef

# Security
SECRET_KEY=your-secret-key-for-jwt

# LLM Providers
OPENAI_API_KEY=your-openai-api-key

# AWS (for Bedrock integration)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1

# AWS SSO
AWS_SSO_START_URL=https://d-xxxxxxxxxx.awsapps.com/start
AWS_SSO_ACCOUNT_ID=123456789012
AWS_SSO_ROLE_NAME=AdministratorAccess
```

### Database Setup
1. Create PostgreSQL database: `createdb langchef`
2. Run migrations: `cd backend && alembic upgrade head`

## Development Workflow

1. **Backend changes**: Always run `black .`, `isort .`, and `mypy .` before committing
2. **Database changes**: Use Alembic migrations (`alembic revision --autogenerate`)
3. **Frontend**: Components follow Material-UI patterns, check existing components for conventions
4. **Agent Builder**: Uses ReactFlow for visual workflow editing, see `/src/components/AgentBuilder/`

## API Structure

Backend serves API at `/api/*` endpoints:
- `/api/auth` - Authentication (login, register, token refresh)
- `/api/prompts` - Prompt management and versioning
- `/api/datasets` - Dataset upload and management
- `/api/experiments` - Experiment running and tracking
- `/api/traces` - Request tracing and metrics
- `/api/models` - LLM model configuration
- `/api/chats` - Chat history and management

Legacy routes without `/api` prefix are maintained for backward compatibility.

## Testing

- Backend: `pytest` (from backend directory)
- Frontend: `npm test` (from frontend directory)
- Integration: Use Docker Compose for full-stack testing

## Documentation Structure

LangChef documentation is organized in `/docs` for easy navigation by developers and Claude Code sub-agents:

```
docs/
├── README.md                     # Documentation overview
├── architecture/                 # System architecture & design
├── development/                  # Development guides & workflows
├── features/                     # Feature-specific documentation
├── api/                          # API documentation & schemas
├── deployment/                   # Deployment & operations
├── security/                     # Security documentation
└── claude-agents/               # Claude Code agent guidance
    ├── agent-overview.md        # Sub-agent coordination guide
    ├── backend-refactor-guide.md # Backend refactoring patterns
    ├── frontend-refactor-guide.md # Frontend refactoring patterns
    ├── security-sweep-guide.md   # Security audit procedures
    └── testing-guide.md         # Testing best practices
```

### For Claude Code Sub-Agents

Each sub-agent should reference the appropriate documentation:

- **langchef-refactor-architect**: `claude-agents/agent-overview.md` + `architecture/`
- **backend-fastapi-refactorer**: `claude-agents/backend-refactor-guide.md` + `api/`
- **frontend-react-refactorer**: `claude-agents/frontend-refactor-guide.md` + `features/`
- **security-sweeper**: `security/` + `claude-agents/security-sweep-guide.md`
- **tests-guardian**: `claude-agents/testing-guide.md` + `development/`

## Claude Code Integration

This project is optimized for Claude Code (claude.ai/code) with:

- **Specialized sub-agents** for different refactoring tasks
- **Comprehensive documentation** in `/docs/claude-agents/`
- **Clear architectural patterns** for consistent code quality
- **Security-first approach** with integrated vulnerability scanning
- **Automated testing guidance** for quality assurance

See `docs/claude-agents/agent-overview.md` for detailed sub-agent coordination.