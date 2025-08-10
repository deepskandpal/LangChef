# LangChef - Active Context

## Current Focus
- Aligning project implementation with the LangChef sequence diagram workflow
- Continuing development of core components: Prompt Management, Dataset Management, LLM Integration, Experimentation
- **NEW**: Implementing the Agent Flow Builder component for visual agent creation
- **NEW**: Docker integration for the Agent Flow Builder

## Recent Changes
1. **Project Name**: Renamed project to "LangChef"
2. **Documentation Update**: Revised documentation to align with the sequence diagram workflow
3. **Implementation Status Assessment**: Identified existing components in the codebase
4. **Agent Flow Builder**: Implemented initial version of the visual agent flow builder
5. **Docker Integration**: Updated docker-compose.yml to properly include the Agent Flow Builder

## Current Architecture Alignment
From examining the codebase, we have found:

1. **Prompt Management**:
   - [x] Database models for prompts and versions exist
   - [x] Basic API routes for prompt operations implemented
   - [ ] Advanced features (templates, collaborative editing) pending

2. **Dataset Management**:
   - [x] Database models for datasets, items, and versions exist
   - [x] API routes for dataset operations implemented
   - [ ] Complete labeling interface pending

3. **LLM Integration**:
   - [x] Models support various providers (OpenAI, Anthropic, AWS Bedrock, etc.)
   - [x] Configuration options for model parameters implemented
   - [ ] Comprehensive provider-specific options pending

4. **Experimentation Framework**:
   - [x] Database models for experiments and results exist
   - [x] API routes for experiment operations implemented
   - [ ] Advanced visualization and comparison features pending

5. **Results & Analysis**:
   - [x] Basic result storage implemented
   - [ ] Comprehensive benchmarking tools pending
   - [ ] Advanced visualization features pending

6. **Agent Flow Builder**:
   - [x] Visual canvas for building agent flows implemented
   - [x] Basic component library with LLM and Search tool nodes
   - [x] Properties panel for configuring node properties
   - [x] Testing console for agent flow testing
   - [x] Backend models and routes for flow storage and execution
   - [x] Docker integration for development and deployment
   - [ ] Advanced tools and connectors pending
   - [ ] Flow deployment as production-ready API endpoints pending

## Next Steps
1. Complete implementations of core components to fully align with sequence diagram
2. Enhance UI for better experiment result visualization
3. Implement benchmarking tools for prompt refinement
4. Add comprehensive model parameter configuration options
5. Improve dataset management and labeling tools
6. Extend the Agent Flow Builder with additional tools and connectors
7. Implement production deployment of agent flows

## Blockers
- None identified at the moment

## Notes
- The existing backend code already covers most of the database models needed for the sequence diagram workflow
- Frontend components will need enhancement to better visualize the experiment workflow
- Focus should be on completing the feedback loop to use results for prompt refinement
- The Agent Flow Builder implementation currently uses ReactFlow for the visual canvas and provides a simple interface for creating and testing agent flows
- Documentation for the Agent Flow Builder has been added at docs/agent-flow-builder.md
- Docker integration has been updated to include a dedicated agent-api service and volume mounts for the Agent Flow Builder components
