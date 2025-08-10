// Agent Flow Model
// This represents the backend data structure for an agent flow

class AgentFlow {
  constructor(data = {}) {
    this.id = data.id || generateId();
    this.name = data.name || 'Untitled Agent';
    this.description = data.description || '';
    this.nodes = data.nodes || [];
    this.edges = data.edges || [];
    this.createdAt = data.createdAt || new Date().toISOString();
    this.updatedAt = data.updatedAt || new Date().toISOString();
    this.version = data.version || '1';
    this.creator = data.creator || '';
    this.isPublished = data.isPublished || false;
    this.apiEndpoint = data.apiEndpoint || '';
  }

  // Convert to JSON for storage
  toJSON() {
    return {
      id: this.id,
      name: this.name,
      description: this.description,
      nodes: this.nodes,
      edges: this.edges,
      createdAt: this.createdAt,
      updatedAt: this.updatedAt,
      version: this.version,
      creator: this.creator,
      isPublished: this.isPublished,
      apiEndpoint: this.apiEndpoint
    };
  }

  // Static method to create from JSON
  static fromJSON(json) {
    return new AgentFlow(json);
  }

  // Update flow with new data
  update(data) {
    Object.assign(this, {
      ...data,
      updatedAt: new Date().toISOString()
    });
    return this;
  }

  // Add a node to the flow
  addNode(node) {
    this.nodes.push(node);
    this.updatedAt = new Date().toISOString();
    return this;
  }

  // Add an edge to the flow
  addEdge(edge) {
    this.edges.push(edge);
    this.updatedAt = new Date().toISOString();
    return this;
  }

  // Remove a node from the flow
  removeNode(nodeId) {
    this.nodes = this.nodes.filter(node => node.id !== nodeId);
    // Also remove any edges connected to this node
    this.edges = this.edges.filter(edge => 
      edge.source !== nodeId && edge.target !== nodeId
    );
    this.updatedAt = new Date().toISOString();
    return this;
  }

  // Remove an edge from the flow
  removeEdge(edgeId) {
    this.edges = this.edges.filter(edge => edge.id !== edgeId);
    this.updatedAt = new Date().toISOString();
    return this;
  }

  // Publish the flow as an API
  publish() {
    this.isPublished = true;
    this.apiEndpoint = generateApiEndpoint(this.id);
    this.updatedAt = new Date().toISOString();
    return this;
  }

  // Unpublish the flow
  unpublish() {
    this.isPublished = false;
    this.updatedAt = new Date().toISOString();
    return this;
  }

  // Validate the flow structure
  validate() {
    // Example validation rules:
    // 1. Must have at least one node
    if (this.nodes.length === 0) {
      return { valid: false, error: 'Flow must have at least one node' };
    }

    // 2. Check for dangling nodes (no inputs or outputs)
    const connectedNodeIds = new Set();
    this.edges.forEach(edge => {
      connectedNodeIds.add(edge.source);
      connectedNodeIds.add(edge.target);
    });

    const danglingNodes = this.nodes.filter(node => !connectedNodeIds.has(node.id));
    if (danglingNodes.length > 0) {
      return { 
        valid: false, 
        error: 'Flow contains disconnected nodes', 
        nodes: danglingNodes 
      };
    }

    // 3. Check for cycles (not implemented here but would be important)
    
    return { valid: true };
  }
}

// Helper functions
function generateId() {
  return `flow_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
}

function generateApiEndpoint(id) {
  return `/api/agents/${id}`;
}

module.exports = AgentFlow; 