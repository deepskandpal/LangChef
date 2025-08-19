# LangChef Documentation

This directory contains comprehensive documentation for the LangChef project, organized for easy navigation by developers and Claude Code sub-agents.

## 📁 Directory Structure

```
docs/
├── README.md                     # This file
├── architecture/                 # System architecture & design
│   ├── overview.md
│   ├── backend-architecture.md
│   ├── frontend-architecture.md
│   └── database-schema.md
├── development/                  # Development guides
│   ├── getting-started.md
│   ├── development-workflow.md
│   ├── coding-standards.md
│   └── troubleshooting.md
├── features/                     # Feature documentation
│   ├── agent-flow-builder.md
│   ├── prompt-management.md
│   ├── dataset-management.md
│   ├── experiments.md
│   └── playground.md
├── api/                          # API documentation
│   ├── authentication.md
│   ├── endpoints.md
│   └── schemas.md
├── deployment/                   # Deployment & operations
│   ├── docker-setup.md
│   ├── aws-integration.md
│   ├── environment-config.md
│   └── monitoring.md
├── security/                     # Security documentation
│   ├── security-overview.md
│   ├── authentication-setup.md
│   └── best-practices.md
└── claude-agents/               # Claude Code agent guidance
    ├── agent-overview.md
    ├── backend-refactor-guide.md
    ├── frontend-refactor-guide.md
    ├── security-sweep-guide.md
    └── testing-guide.md
```

## 🎯 For Claude Code Sub-Agents

Each sub-agent should reference the appropriate documentation:

- **langchef-refactor-architect**: `/claude-agents/` + `/architecture/`
- **backend-fastapi-refactorer**: `/claude-agents/backend-refactor-guide.md` + `/api/`
- **frontend-react-refactorer**: `/claude-agents/frontend-refactor-guide.md` + `/features/`
- **security-sweeper**: `/security/` + `/claude-agents/security-sweep-guide.md`
- **tests-guardian**: `/claude-agents/testing-guide.md` + `/development/`

## 🚀 Quick Navigation

- **New to LangChef?** → [Getting Started](development/getting-started.md)
- **Setting up development?** → [Development Workflow](development/development-workflow.md)
- **Building features?** → [Features Documentation](features/)
- **Deploying?** → [Deployment Guides](deployment/)
- **Security concerns?** → [Security Documentation](security/)
- **Working with Claude Code?** → [Claude Agents Documentation](claude-agents/)

---
*This documentation is continuously updated to reflect the current state of the LangChef platform.*