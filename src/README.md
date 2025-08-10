# Agent Flow Builder - LangChef Integration

This directory contains the Agent Flow Builder components integrated with the LangChef application. The Agent Flow Builder provides a visual, low-code interface for creating and deploying LLM agents.

## Directory Structure

- `components/AgentBuilder/` - Frontend React components for the visual editor
- `models/` - Backend data models for agent flows
- `controllers/` - Backend controllers for flow execution
- `routes/` - API routes for the Agent Flow Builder
- `server.js` - Express server for the Agent Flow API

## Docker Integration

The Agent Flow Builder is fully integrated into the LangChef Docker environment through a robust containerized setup:

### 1. Frontend Container (`frontend/Dockerfile.dev`)

The frontend container includes the Agent Flow Builder UI components and handles their integration:

```dockerfile
# Key elements of the frontend Dockerfile
FROM node:18-alpine
# ...
# Install dependencies including Agent Flow Builder requirements
RUN npm install reactflow @emotion/react @emotion/styled --legacy-peer-deps
# ...
# Automatically integrate Agent Builder into navigation and routes
RUN sed -i '...' src/components/Layout.js
RUN sed -i '...' src/App.js
```

This approach:
- Integrates the Agent Builder into the main navigation at build time
- Automatically adds the required routes
- Installs all dependencies needed for the visual editor
- Requires no manual file editing or post-startup scripts

### 2. Agent API Container (`agent-api/Dockerfile`)

A dedicated container for the backend Agent Flow API:

```dockerfile
# Key elements of the agent-api Dockerfile
FROM node:18-alpine
# ...
# Create necessary directories and install dependencies
RUN npm install express cors body-parser
# ...
# Copy Agent Flow API files
COPY src/models/AgentFlow.js models/
COPY src/controllers/agentFlowController.js controllers/
```

This provides:
- Isolated API service dedicated to Agent Flow operations
- Proper CORS handling for frontend communication
- Clear separation of concerns between frontend and API

### 3. Docker Compose Configuration

The `docker-compose.yml` ties everything together:

```yaml
frontend:
  build:
    context: .
    dockerfile: frontend/Dockerfile.dev
  # Volume mounts for development
  volumes:
    - ./frontend/src:/app/src
    - ./src/components/AgentBuilder:/app/src/components/AgentBuilder
  environment:
    - REACT_APP_AGENT_API_URL=http://localhost:5001

agent-api:
  build:
    context: .
    dockerfile: agent-api/Dockerfile
  # ...other configuration
```

## Development Workflow

1. All components are automatically integrated - just run:
   ```
   docker-compose up -d
   ```

2. Navigate to http://localhost:3001 and click "Agent Builder" in the sidebar

3. For live development:
   - Edit files directly - volume mounts enable hot-reloading
   - For structural changes: `docker-compose up -d --build`

4. The Agent Flow API is available at http://localhost:5001/api/agent-flows

## Documentation

For more details on using the Agent Flow Builder, see `docs/agent-flow-builder.md` 