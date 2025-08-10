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

// Process a single node in the flow
async function processNode(node, flowData, context) {
  switch (node.type) {
    case 'llm':
      // Prepare the prompt with any context from previous nodes
      let prompt = context.input;
      if (context.searchResults) {
        prompt = `Search results:\n${formatSearchResults(context.searchResults)}\n\nUser query: ${context.input}`;
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
    
    // Final response is either the LLM response or a default response
    const response = context.llmResponse || {
      content: "Flow execution completed, but no LLM node was found to generate a response."
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