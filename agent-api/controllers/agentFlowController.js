// Agent Flow Controller
// This handles the execution of agent flows

const AgentFlow = require('../models/AgentFlow');

// Mock LLM call function (in a real app, this would call an actual LLM API)
async function callLLM(model, prompt, temperature) {
  console.log(`Calling LLM model: ${model}, temp: ${temperature}`);
  console.log(`Prompt: ${prompt}`);
  
  // Simulate API call delay
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  return {
    content: `This is a simulated response from ${model} for the prompt: "${prompt.substring(0, 50)}..."`
  };
}

// Mock search function (in a real app, this would call an actual search API)
async function performSearch(engine, query, resultCount) {
  console.log(`Searching with engine: ${engine}, results: ${resultCount}`);
  console.log(`Query: ${query}`);
  
  // Simulate API call delay
  await new Promise(resolve => setTimeout(resolve, 800));
  
  return {
    results: Array(resultCount).fill(null).map((_, i) => ({
      title: `Search result ${i + 1} for "${query.substring(0, 30)}..."`,
      snippet: `This is the snippet for result ${i + 1}`,
      url: `https://example.com/result${i + 1}`
    }))
  };
}

// Mock calculator function
async function performCalculation(expression, precision = 2) {
  console.log(`Calculating: ${expression} with precision: ${precision}`);
  
  try {
    // This is a simple and unsafe implementation - in a real app you would use a proper expression evaluator
    // with security measures
    const result = eval(expression);
    
    // Format according to precision
    const formattedResult = typeof result === 'number' 
      ? Number(result.toFixed(precision)) 
      : result;
    
    return {
      result: formattedResult,
      expression: expression
    };
  } catch (error) {
    return {
      error: `Error calculating expression: ${error.message}`,
      expression: expression
    };
  }
}

// Process a single node in the flow
async function processNode(node, flowData, context) {
  switch (node.type) {
    case 'llm':
      // Prepare the prompt with any context from previous nodes
      let prompt = context.input;
      if (context.searchResults) {
        prompt = `Search results:\n${formatSearchResults(context.searchResults)}\n\nUser query: ${context.input}`;
      }
      if (context.calculationResult) {
        prompt = `Calculation result: ${context.calculationResult.result}\nExpression: ${context.calculationResult.expression}\n\nUser query: ${context.input}`;
      }
      
      // Add system prompt if available
      if (node.data.systemPrompt) {
        prompt = `${node.data.systemPrompt}\n\n${prompt}`;
      }
      
      // Call the LLM
      const llmResponse = await callLLM(
        node.data.model, 
        prompt, 
        node.data.temperature
      );
      
      return {
        ...context,
        llmResponse: llmResponse
      };
      
    case 'search':
      // Perform search with the user input as query
      const searchResults = await performSearch(
        node.data.engine,
        context.input,
        node.data.resultCount
      );
      
      return {
        ...context,
        searchResults: searchResults.results
      };
      
    case 'calculator':
      // Perform calculation based on user input
      const calculationResult = await performCalculation(
        context.input,
        node.data.precision || 2
      );
      
      return {
        ...context,
        calculationResult
      };
      
    case 'agent':
      // Determine which tools to use based on input
      const agentPrompt = `
        You are a tool-calling agent. You have the following tools available:
        ${getConnectedTools(node.id, flowData).map(tool => 
          `- ${tool.type.toUpperCase()}: ${getToolDescription(tool.type)}`
        ).join('\n')}
        
        User query: ${context.input}
        
        Respond to the user query using the tools available. Format your response in a natural, conversational way.
      `;
      
      // Add agent system prompt if available
      const fullPrompt = node.data.systemPrompt 
        ? `${node.data.systemPrompt}\n\n${agentPrompt}` 
        : agentPrompt;
      
      // Call LLM to simulate agent reasoning
      const agentResponse = await callLLM(
        node.data.model || 'gpt-4',
        fullPrompt,
        0.7
      );
      
      return {
        ...context,
        agentResponse
      };
      
    case 'chatInput':
      // Just pass through the input
      return context;
      
    case 'chatOutput':
      // Format the response based on settings
      let outputContent = '';
      
      if (context.agentResponse) {
        outputContent = context.agentResponse.content;
      } else if (context.llmResponse) {
        outputContent = context.llmResponse.content;
      } else if (context.searchResults) {
        outputContent = formatSearchResults(context.searchResults);
      } else if (context.calculationResult) {
        outputContent = `Result: ${context.calculationResult.result}`;
      } else {
        outputContent = 'No response generated';
      }
      
      // Apply formatting if needed
      if (node.data.format === 'markdown') {
        outputContent = `\`\`\`markdown\n${outputContent}\n\`\`\``;
      } else if (node.data.format === 'html') {
        outputContent = `<div>${outputContent}</div>`;
      }
      
      return {
        ...context,
        finalOutput: {
          content: outputContent,
          format: node.data.format || 'text'
        }
      };
      
    default:
      throw new Error(`Unknown node type: ${node.type}`);
  }
}

// Helper function to format search results
function formatSearchResults(results) {
  return results.map((result, i) => 
    `[${i + 1}] ${result.title}\n${result.snippet}\n${result.url}`
  ).join('\n\n');
}

// Helper function to get connected tools for an agent
function getConnectedTools(agentId, flowData) {
  const targetNodeIds = flowData.edges
    .filter(edge => edge.source === agentId)
    .map(edge => edge.target);
    
  return flowData.nodes.filter(node => 
    targetNodeIds.includes(node.id) && 
    ['llm', 'search', 'calculator'].includes(node.type)
  );
}

// Helper function to get tool descriptions
function getToolDescription(toolType) {
  switch(toolType) {
    case 'llm':
      return 'Language model for generating text';
    case 'search':
      return 'Search the web for information';
    case 'calculator':
      return 'Perform mathematical calculations';
    default:
      return 'Unknown tool';
  }
}

// Find all starting nodes (nodes with no incoming edges)
function findStartingNodes(nodes, edges) {
  const nodesWithIncoming = new Set(
    edges.map(edge => edge.target)
  );
  
  return nodes.filter(node => !nodesWithIncoming.has(node.id));
}

// Find all nodes that follow a given node
function findNextNodes(nodeId, edges) {
  return edges
    .filter(edge => edge.source === nodeId)
    .map(edge => edge.target);
}

// Execute an agent flow
async function executeFlow(flowData, input) {
  try {
    // Convert flowData to AgentFlow instance if it's not already
    const flow = flowData instanceof AgentFlow 
      ? flowData 
      : AgentFlow.fromJSON(flowData);
    
    // Validate the flow
    const validation = flow.validate();
    if (!validation.valid) {
      throw new Error(`Invalid flow structure: ${validation.error}`);
    }
    
    // Initialize context with user input
    let context = { input };
    
    // Find starting nodes
    const startingNodeIds = findStartingNodes(flow.nodes, flow.edges);
    
    if (startingNodeIds.length === 0) {
      throw new Error('Flow has no starting nodes');
    }
    
    // Process nodes in sequence, following the graph
    // This is a simplified implementation for a basic flow
    // A real implementation would need to handle more complex flow structures
    
    let processedNodeIds = new Set();
    let nodesToProcess = [...startingNodeIds];
    
    while (nodesToProcess.length > 0) {
      const nodeId = nodesToProcess.shift();
      
      // Skip if already processed
      if (processedNodeIds.has(nodeId)) continue;
      
      // Find the node in the flow
      const node = flow.nodes.find(n => n.id === nodeId);
      if (!node) continue;
      
      // Process the node
      context = await processNode(node, flow, context);
      
      // Mark as processed
      processedNodeIds.add(nodeId);
      
      // Add next nodes to process
      const nextNodeIds = findNextNodes(nodeId, flow.edges);
      nodesToProcess.push(...nextNodeIds);
    }
    
    // Final response is either the final output, agent response, LLM response, or a default response
    const response = context.finalOutput || context.agentResponse || context.llmResponse || {
      content: "Flow execution completed, but no output was generated."
    };
    
    return response;
  } catch (error) {
    console.error('Error executing flow:', error);
    throw error;
  }
}

module.exports = {
  executeFlow
};