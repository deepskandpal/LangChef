const express = require('express');
const router = express.Router();
const AgentFlow = require('../models/AgentFlow');
const agentFlowController = require('../controllers/agentFlowController');

// Sample in-memory store for development
const flowStore = {};

// Get all agent flows
router.get('/', async (req, res) => {
  try {
    const flows = Object.values(flowStore);
    res.json({ success: true, data: flows });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get a specific agent flow by ID
router.get('/:id', async (req, res) => {
  try {
    const flow = flowStore[req.params.id];
    if (!flow) {
      return res.status(404).json({ 
        success: false, 
        error: 'Agent flow not found' 
      });
    }
    
    res.json({ success: true, data: flow });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Create a new agent flow
router.post('/', async (req, res) => {
  try {
    const { name, description, nodes, edges } = req.body;
    
    const flow = new AgentFlow({
      name,
      description,
      nodes,
      edges,
      creator: req.user?.id || 'anonymous'
    });
    
    // Save to our store
    flowStore[flow.id] = flow.toJSON();
    
    res.status(201).json({ success: true, data: flow.toJSON() });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Update an existing agent flow
router.put('/:id', async (req, res) => {
  try {
    const flowData = flowStore[req.params.id];
    if (!flowData) {
      return res.status(404).json({ 
        success: false, 
        error: 'Agent flow not found' 
      });
    }
    
    const flow = AgentFlow.fromJSON(flowData);
    flow.update({
      name: req.body.name || flow.name,
      description: req.body.description || flow.description,
      nodes: req.body.nodes || flow.nodes,
      edges: req.body.edges || flow.edges,
    });
    
    // Update in our store
    flowStore[flow.id] = flow.toJSON();
    
    res.json({ success: true, data: flow.toJSON() });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Delete an agent flow
router.delete('/:id', async (req, res) => {
  try {
    const flow = flowStore[req.params.id];
    if (!flow) {
      return res.status(404).json({ 
        success: false, 
        error: 'Agent flow not found' 
      });
    }
    
    // Remove from our store
    delete flowStore[req.params.id];
    
    res.json({ 
      success: true, 
      message: 'Agent flow deleted successfully' 
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Publish an agent flow
router.post('/:id/publish', async (req, res) => {
  try {
    const flowData = flowStore[req.params.id];
    if (!flowData) {
      return res.status(404).json({ 
        success: false, 
        error: 'Agent flow not found' 
      });
    }
    
    const flow = AgentFlow.fromJSON(flowData);
    
    // Validate the flow before publishing
    const validation = flow.validate();
    if (!validation.valid) {
      return res.status(400).json({ 
        success: false, 
        error: 'Invalid flow structure', 
        details: validation 
      });
    }
    
    flow.publish();
    
    // Update in our store
    flowStore[flow.id] = flow.toJSON();
    
    res.json({ 
      success: true, 
      data: flow.toJSON(), 
      message: 'Agent flow published successfully' 
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Unpublish an agent flow
router.post('/:id/unpublish', async (req, res) => {
  try {
    const flowData = flowStore[req.params.id];
    if (!flowData) {
      return res.status(404).json({ 
        success: false, 
        error: 'Agent flow not found' 
      });
    }
    
    const flow = AgentFlow.fromJSON(flowData);
    flow.unpublish();
    
    // Update in our store
    flowStore[flow.id] = flow.toJSON();
    
    res.json({ 
      success: true, 
      data: flow.toJSON(), 
      message: 'Agent flow unpublished successfully' 
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Test an agent flow
router.post('/:id/test', async (req, res) => {
  try {
    const { input } = req.body;
    const flowData = flowStore[req.params.id];
    
    if (!flowData) {
      return res.status(404).json({ 
        success: false, 
        error: 'Agent flow not found' 
      });
    }
    
    // This would execute the flow in a real implementation
    // Here we're just returning a mock response
    const result = await agentFlowController.executeFlow(flowData, input);
    
    res.json({ 
      success: true, 
      data: result 
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;