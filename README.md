# LLM Workflow Platform

An end-to-end LLM workflow platform for prompt engineering, dataset management, experimentation, and evaluation.

## Overview

This platform provides a comprehensive solution for managing the entire lifecycle of LLM applications, from prompt engineering to evaluation. It's designed to help teams iterate faster, track experiments, and improve the quality of their LLM-powered applications.

Key features include:

- **Prompt Management**: Create, version, and organize prompts
- **Dataset Management**: Upload, manage, and version datasets for testing and evaluation
- **Experimentation**: Run experiments with different prompts, models, and datasets
- **Playground**: Interactive environment for testing prompts and models
- **Evaluation**: Track metrics and evaluate model performance
- **Tracing**: Monitor latency, token usage, and costs

## Architecture

The platform consists of two main components:

1. **Backend**: A Python FastAPI application that handles data storage, model interactions, and API endpoints
2. **Frontend**: A React application that provides a user-friendly interface for interacting with the platform

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 14+
- PostgreSQL

### Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/llm-workflow-platform.git
cd llm-workflow-platform
```

2. Set up the backend:

```bash
cd llm_workflow_platform/backend
pip install -r requirements.txt
```

3. Set up the database:

```bash
# Create a PostgreSQL database
createdb llm_workflow

# Run migrations
alembic upgrade head
```

4. Set up the frontend:

```bash
cd ../frontend
npm install
```

5. Create a `.env` file in the backend directory with the following variables:

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/llm_workflow
SECRET_KEY=your-secret-key-for-jwt
OPENAI_API_KEY=your-openai-api-key
```

### Running the Application

1. Start the backend:

```bash
cd llm_workflow_platform/backend
uvicorn main:app --reload
```

2. Start the frontend:

```bash
cd llm_workflow_platform/frontend
npm start
```

3. Access the application at http://localhost:3000

## Usage

### Prompt Management

- Create and manage prompts with versioning
- Organize prompts by categories or tags
- Track prompt performance across experiments

### Dataset Management

- Upload datasets in various formats (JSON, CSV, JSONL, text)
- Create and manage dataset versions
- Associate datasets with experiments

### Experimentation

- Run experiments with different prompts, models, and datasets
- Track metrics like latency, token usage, and cost
- Compare experiment results

### Playground

- Interactively test prompts and models
- Visualize results in real-time
- Save successful configurations as experiments

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Inspired by [Langfuse](https://github.com/langfuse/langfuse)
- Built with FastAPI, React, and Material-UI 