# Agent Flow Builder - Agent API

This is the Agent Flow API microservice for LangChef. It handles the execution of agent flows created in the visual Agent Flow Builder.

## Directory Structure

- `models/` - Backend data models for agent flows
- `controllers/` - Backend controllers for flow execution
- `routes/` - API routes for the Agent Flow Builder
- `server.js` - Express server for the Agent Flow API

## Installation

```bash
npm install
```

## Development

```bash
npm run dev
```

## Production

```bash
npm start
```

## API Endpoints

- `GET /api/agent-flows` - Get all agent flows
- `GET /api/agent-flows/:id` - Get a specific agent flow
- `POST /api/agent-flows` - Create a new agent flow
- `PUT /api/agent-flows/:id` - Update an agent flow
- `DELETE /api/agent-flows/:id` - Delete an agent flow
- `POST /api/agent-flows/:id/publish` - Publish an agent flow
- `POST /api/agent-flows/:id/unpublish` - Unpublish an agent flow
- `POST /api/agent-flows/:id/test` - Test an agent flow

## Environment Variables

- `PORT` - Server port (default: 5000)
- `NODE_ENV` - Environment (development/production)
- `CORS_ORIGIN` - CORS origin for API access