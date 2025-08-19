<div align="center">
  <img src="lang-chef.png" alt="LangChef" width="120" height="120">
  <h1>LangChef</h1>
  <p><strong>End-to-end LLM workflow platform for prompt engineering, dataset management, and experimentation</strong></p>
</div>

## 🌐 Overview

LangChef streamlines the entire lifecycle of LLM applications, from initial prompt engineering to production evaluation. Built for teams who need to iterate fast and maintain quality in their AI workflows.

### ✨ Core Features

- 📝 **Prompt Management** - Create, version, and organize prompts with full lifecycle tracking
- 📁 **Dataset Management** - Upload and manage datasets in multiple formats (JSON, CSV, JSONL)
- 🧪 **Experimentation** - Run controlled experiments across prompts, models, and datasets
- 🎮 **Interactive Playground** - Real-time testing environment with multiple LLM providers
- 📈 **Performance Tracking** - Monitor latency, token usage, costs, and custom metrics
- 🔍 **Request Tracing** - Complete observability for production LLM applications

## 🏗️ Architecture

```mermaid
graph TB
    subgraph "Frontend (React + Material-UI)"
        UI[User Interface]
        PG[Playground]
        DS[Datasets]
        EX[Experiments]
    end
    
    subgraph "Backend (FastAPI + SQLAlchemy)"
        API[REST API]
        AUTH[Authentication]
        SVC[Services Layer]
    end
    
    subgraph "External Services"
        LLM[LLM Providers<br/>OpenAI, Anthropic, AWS Bedrock]
        AWS[AWS SSO]
    end
    
    subgraph "Data Layer"
        DB[(PostgreSQL)]
    end
    
    UI --> API
    PG --> API
    DS --> API
    EX --> API
    
    API --> AUTH
    API --> SVC
    SVC --> DB
    
    AUTH --> AWS
    SVC --> LLM
```

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+** & **Node.js 18+**
- **PostgreSQL 13+** 
- **[uv](https://github.com/astral-sh/uv)** package manager

### 🐳 Docker Setup (Recommended)

```bash
# Clone and start with Docker
git clone https://github.com/yourusername/langchef.git
cd langchef
docker-compose up -d

# Access at http://localhost:3000
```

### 🛠️ Manual Setup

<details>
<summary>Click to expand manual setup instructions</summary>

#### Backend Setup
```bash
cd backend
pip install uv
uv venv .venv && source .venv/bin/activate
uv pip install -e .

# Database setup
createdb langchef
alembic upgrade head

# Start backend (port 8000)
uvicorn main:app --reload
```

#### Frontend Setup
```bash
cd frontend
npm install

# Start frontend (port 3000)
npm start
```

#### Environment Configuration
Copy `.env.example` to `.env` and configure:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/langchef
SECRET_KEY=your-secure-secret-key  # Generate with: openssl rand -hex 32
OPENAI_API_KEY=sk-...

# Optional: AWS Integration
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
```

</details>

## 🎯 Key Workflows

<table>
<tr>
<td>

**📝 Prompt Engineering**
- Create & version prompts
- A/B test variations
- Performance tracking
- Template management

</td>
<td>

**📁 Dataset Operations** 
- Multi-format uploads
- Schema validation
- Version control
- Quality metrics

</td>
</tr>
<tr>
<td>

**🧪 Experimentation**
- Controlled testing
- Multi-model comparison
- Statistical significance
- Cost optimization

</td>
<td>

**🎮 Interactive Playground**
- Real-time testing
- Model comparison
- Configuration export
- Result visualization

</td>
</tr>
</table>

## 📄 Documentation

- **[Getting Started Guide](docs/development/getting-started.md)** - Comprehensive setup instructions
- **[API Documentation](docs/api/)** - Complete API reference
- **[Architecture Guide](docs/architecture/)** - System design and patterns
- **[Security Guide](docs/security/)** - Security best practices
- **[Claude Code Agents](docs/claude-agents/)** - AI assistant documentation

## 🤝 Contributing

We welcome contributions! See our [development workflow guide](docs/development/development-workflow.md) for details.

**Key Areas:**
- 🐛 Bug fixes and improvements
- 📚 Documentation enhancements  
- ✨ New feature development
- 🛡️ Security improvements

## 📜 License & Acknowledgements

**MIT License** - See [LICENSE](LICENSE) for details

**Built with:**
- 🔥 FastAPI + SQLAlchemy
- ⚛️ React + Material-UI
- 🐳 Docker + PostgreSQL
- 🤖 Claude Code integration

**Inspired by:** [Langfuse](https://github.com/langfuse/langfuse) and the broader LLMOps community