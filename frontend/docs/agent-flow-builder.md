# Agent Flow Builder

The Agent Flow Builder is a visual, low-code interface for creating and deploying LLM agents in LangChef. It enables you to build complex agent workflows by connecting different components (LLMs, tools, etc.) in a flow-based interface.

## Features

- **Visual Canvas**: Drag and drop components to create agent workflows
- **Component Library**: Pre-built components for common agent building blocks
- **Node Configuration**: Configure each component's properties through a simple UI
- **Testing Console**: Test your agent flow in real-time
- **Deployment**: Deploy agent flows as API endpoints
- **Integration**: Seamlessly integrate with existing LangChef prompts and LLM configurations

## Components

### Language Models (LLMs)

Language model nodes represent the core LLM that will process inputs and generate responses. You can configure:

- **Model**: Choose from available models (GPT-4, GPT-3.5 Turbo, Claude 3, etc.)
- **Temperature**: Adjust creativity/randomness of outputs
- **System Prompt**: Define system instructions for the LLM

### Tools

Tool nodes provide additional capabilities to the agent:

- **Search Tool**: Enable web search capabilities
  - Configure search engine (Google, Bing, etc.)
  - Set number of results to return

More tools will be added in future updates.

## Getting Started

1. **Access the Agent Builder**:
   - Navigate to the "Agent Builder" section in the LangChef interface

2. **Create a New Flow**:
   - Start with a blank canvas
   - Drag components from the left panel onto the canvas

3. **Connect Components**:
   - Connect nodes by dragging from the output handle of one node to the input handle of another

4. **Configure Node Properties**:
   - Click on a node to select it
   - Use the properties panel on the right to customize its behavior

5. **Test Your Agent**:
   - Use the testing console to send test inputs
   - Review the agent's responses

6. **Deploy as API**:
   - Click the "Deploy as API" button
   - Your agent will be available as an API endpoint

## Example Workflow

A simple question-answering agent with search capabilities:

1. Create a Search Tool node and an LLM node
2. Connect the Search Tool output to the LLM input
3. Configure the Search Tool to use Google and return 3 results
4. Configure the LLM to use GPT-4 with a temperature of 0.7
5. Add a system prompt to the LLM: "You are a helpful assistant. Use the search results to answer the user's question."
6. Test with a question in the testing console
7. Deploy as an API

## API Integration

When you deploy an agent flow, it becomes available as an API endpoint that you can integrate into your applications:

```javascript
// Example API call to a deployed agent
const response = await fetch('https://your-langchef-instance.com/api/agents/your-agent-id', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_API_KEY'
  },
  body: JSON.stringify({
    input: "What is the capital of France?"
  })
});

const result = await response.json();
console.log(result.content);
```

## Best Practices

- **Start Simple**: Begin with a basic flow and add complexity incrementally
- **Test Frequently**: Test your agent after each significant change
- **Use System Prompts**: Provide clear instructions in the LLM's system prompt
- **Connect Tools Appropriately**: Consider how data flows between components
- **Validate Flows**: Ensure all nodes are connected properly before deployment 