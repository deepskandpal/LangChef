# LangChef - System Patterns

## LangChef Workflow
The core workflow of LangChef follows the sequence diagram:

```
[Prompt Design] → [Prompt Store] → [Experiment] → [Results/Benchmarks] → [Refinement Loop]
                     ↑                  ↑
                     |                  |
           [Labeled Dataset] ────→ [Dataset Store]
```

1. **Prompt Design**: Create, version, and test prompts against models and sample datapoints
2. **Dataset Management**: Create and store labeled datasets for experiments
3. **Experimentation**: Run experiments with specific model configurations (temp, top_p, top_k)
4. **Results Analysis**: Collect and analyze experiment results
5. **Refinement Loop**: Use results to refine prompts or upgrade LLM models

## Extended Workflow with Agent Builder
With the addition of the Agent Flow Builder, the workflow extends to:

```
                                      ┌─────────────────┐
                                      │                 │
                                      ▼                 │
[Prompt Store] ───┬──→ [Experiment] ──────→ [Results] ──┘
                  │
                  │
                  └──→ [Agent Flow Builder] ──→ [Deployed Agent APIs]
                         ↑           ↑
                         │           │
                    [LLM Config]  [Tools]
```

This allows for both traditional experimentation and low-code agent creation from the same prompt store.

## Architecture Overview

### System Components
```
[User Interface Layer]
    │
    ├── Prompt Management UI
    ├── Dataset Management UI
    ├── Experiment Configuration UI
    ├── Results & Analysis UI
    └── API Client Services

[API Layer]
    │
    ├── Prompt API
    ├── Dataset API
    ├── Experiment API
    ├── Results API
    └── Authentication & Authorization

[Core Services Layer]
    │
    ├── Prompt Management Service
    ├── Dataset Management Service
    ├── Experiment Orchestration Service
    ├── LLM Provider Service
    └── Results & Metrics Service

[Data Storage Layer]
    │
    ├── Prompt Store (Versioned)
    ├── Dataset Store (Versioned)
    ├── Experiment Configurations
    ├── Results Repository
    └── Metrics Database
```

### Agent Flow Builder Components
```
[Agent Flow Builder UI]
    │
    ├── Canvas (React Flow)
    │   ├── Node Management
    │   └── Connection Logic
    │
    ├── Component Panel
    │   ├── LLM Nodes
    │   └── Tool Nodes (Search, etc.)
    │
    ├── Properties Panel
    │   ├── Node Configuration
    │   └── Flow Properties
    │
    └── Testing Console
        ├── Agent Execution
        └── Debug Information

[Agent Flow API]
    │
    ├── Flow Storage/Retrieval
    ├── Agent Execution Engine
    └── API Endpoint Generation
```

## Design Patterns & Approaches

### Prompt Management Patterns
1. **Versioning Pattern**: Track prompt history with immutable versions
2. **Template Pattern**: Reusable prompt structures with variable substitution
3. **Effectiveness Measurement**: Metrics for evaluating prompt performance

### Dataset Management Patterns
1. **Dataset Versioning**: Track dataset evolution over time
2. **Labeling Workflow**: Structured approach to creating labeled datasets
3. **Golden Dataset Strategy**: Curate high-quality datasets for benchmarking

### Experimentation Patterns
1. **Configuration Management**: Structured storage of model parameters
2. **Batch Experimentation**: Run multiple configurations in parallel
3. **Reproducible Experiments**: Ensure experiments can be repeated consistently

### Results Analysis Patterns
1. **Comparative Analysis**: Side-by-side comparison of experiment outcomes
2. **Metric Visualization**: Standard approaches to visualizing performance
3. **Benchmark Repository**: Store and track benchmark results over time

### Refinement Loop Patterns
1. **Feedback Integration**: Using results to improve prompts
2. **A/B Testing Framework**: Systematically test prompt variations
3. **Continuous Improvement Cycle**: Iterative approach to optimization

### Agent Flow Builder Patterns
1. **Visual Programming**: Node-based interface for connecting components
2. **Component Abstraction**: Wrap complex LLM functionality in simple visual nodes
3. **Validation System**: Ensure valid connections between nodes
4. **Live Preview**: Test agent behavior directly in the builder
5. **Serialization Pattern**: Store flows as JSON for versioning and deployment

### Agent Integration Patterns
1. **LLM Configuration Reuse**: Leverage existing LLM configurations
2. **Prompt Template Integration**: Use versioned prompts in agent flows
3. **Tool Registration**: Simple interface for registering and configuring tools
4. **Agent Deployment**: Convert visual flows to API endpoints

## Data Flow Examples

### Prompt Design to Experiment
1. User creates/edits prompt in Prompt Management UI
2. System stores prompt version in Prompt Store
3. User creates experiment, selecting prompt version, dataset, and model configuration
4. System runs experiment against selected dataset using LLM Provider Service
5. Results are stored in Results Repository
6. User analyzes results in Results & Analysis UI
7. User refines prompt based on insights and creates new version

### Dataset Creation and Use
1. User imports or creates dataset in Dataset Management UI
2. System stores dataset in Dataset Store
3. User selects dataset for experiment
4. System includes dataset in experiment configuration
5. Experiment results reference specific dataset version used

### Agent Creation Flow
1. User opens Agent Flow Builder
2. User drags LLM node from component panel to canvas
3. User configures LLM node with model, temperature, etc.
4. User drags Search Tool node to canvas
5. User connects LLM node output to Search Tool input
6. User configures Search Tool parameters
7. User tests agent in the testing console
8. User deploys agent as API endpoint

## Key Implementation Considerations
1. **Versioning**: Immutable versioning for prompts and datasets
2. **Configuration Management**: Clear storage of model parameters
3. **Results Storage**: Efficient storage of potentially large experiment outputs
4. **Metrics Calculation**: Consistent approach to performance metrics
5. **Provider Integration**: Uniform API across different LLM providers
6. **Flow Serialization**: Efficient representation of flow structure
7. **Node Typing**: Clear contracts for node inputs/outputs
8. **Error Handling**: User-friendly validation and error messages
9. **Performance**: Efficient rendering of complex flows
