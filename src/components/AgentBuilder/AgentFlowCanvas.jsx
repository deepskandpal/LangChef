import React, { useCallback, useState, useEffect } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';

// Import node types
import LLMNode from './nodes/LLMNode';
import SearchToolNode from './nodes/SearchToolNode';
import AgentNode from './nodes/AgentNode';
import CalculatorNode from './nodes/CalculatorNode';
import ChatInputNode from './nodes/ChatInputNode';
import ChatOutputNode from './nodes/ChatOutputNode';

import ComponentPanel from './ComponentPanel';
import PropertiesPanel from './PropertiesPanel';
import TestingConsole from './TestingConsole';

// Define node types mapping
const nodeTypes = {
  llm: LLMNode,
  search: SearchToolNode,
  agent: AgentNode,
  calculator: CalculatorNode,
  chatInput: ChatInputNode,
  chatOutput: ChatOutputNode,
};

// Define templates
const simpleAgentTemplate = {
  nodes: [
    {
      id: 'chatInput1',
      type: 'chatInput',
      position: { x: 150, y: 250 },
      data: { label: 'Chat Input' }
    },
    {
      id: 'agent1',
      type: 'agent',
      position: { x: 450, y: 250 },
      data: { 
        label: 'Tool-calling Agent',
        model: 'anthropic.claude-3-sonnet-20240229-v1:0',
        provider: 'aws_bedrock',
        toolCount: 2,
        agentType: 'tool_calling',
        temperature: 0.7,
        topP: 1.0,
        topK: 0,
        systemPrompt: 'You are a helpful assistant with access to tools. Use them to help the user.'
      }
    },
    {
      id: 'llm1',
      type: 'llm',
      position: { x: 450, y: 70 },
      data: { 
        label: 'LLM',
        model: 'anthropic.claude-3-sonnet-20240229-v1:0',
        provider: 'aws_bedrock',
        temperature: 0.7,
        topP: 1.0,
        topK: 0,
        availableModels: [
          { id: 'anthropic.claude-3-7-sonnet-20250219-v1:0', name: 'Claude 3.7 Sonnet v1', provider: 'aws_bedrock' },
          { id: 'anthropic.claude-3-5-sonnet-20240620-v1:0', name: 'Claude 3.5 Sonnet v1', provider: 'aws_bedrock' },
          { id: 'anthropic.claude-3-opus-20240229-v1:0', name: 'Claude 3 Opus v1', provider: 'aws_bedrock' },
          { id: 'anthropic.claude-3-sonnet-20240229-v1:0', name: 'Claude 3 Sonnet v1', provider: 'aws_bedrock' },
          { id: 'anthropic.claude-3-haiku-20240307-v1:0', name: 'Claude 3 Haiku v1', provider: 'aws_bedrock' },
          { id: 'openai/gpt-4', name: 'GPT-4', provider: 'openai' },
          { id: 'openai/gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'openai' },
        ],
        onModelChange: (e) => {},
        onTemperatureChange: (e) => {},
        onTopPChange: (e) => {},
        onTopKChange: (e) => {},
      }
    },
    {
      id: 'calculator1',
      type: 'calculator',
      position: { x: 250, y: 430 },
      data: { 
        label: 'Calculator',
        precision: 2
      }
    },
    {
      id: 'search1',
      type: 'search',
      position: { x: 650, y: 430 },
      data: { 
        label: 'Search Tool',
        engine: 'google',
        resultCount: 3,
        onEngineChange: (e) => {},
        onResultCountChange: (e) => {},
      }
    },
    {
      id: 'chatOutput1',
      type: 'chatOutput',
      position: { x: 750, y: 250 },
      data: { 
        label: 'Chat Output',
        format: 'text'
      }
    }
  ],
  edges: [
    { id: 'e1-2', source: 'chatInput1', target: 'agent1' },
    { id: 'e2-3', source: 'agent1', target: 'chatOutput1' },
    { id: 'e2-4', source: 'agent1', target: 'calculator1', animated: true, style: { stroke: '#f6ad55' } },
    { id: 'e2-5', source: 'agent1', target: 'search1', animated: true, style: { stroke: '#63b3ed' } },
    { id: 'e3-2', source: 'llm1', target: 'agent1', style: { stroke: '#9f7aea' } },
  ],
  description: 'A simple agent that can use a calculator and search tool'
};

const AgentFlowCanvas = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);
  const [templates, setTemplates] = useState([simpleAgentTemplate]);
  const [showTemplates, setShowTemplates] = useState(false);
  const [leftPanelCollapsed, setLeftPanelCollapsed] = useState(false);
  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [activeTab, setActiveTab] = useState('canvas'); // 'canvas', 'history'
  const [activeConfigTab, setActiveConfigTab] = useState('components'); // 'components', 'properties'
  const [zoom, setZoom] = useState(1);
  const [model, setModel] = useState('anthropic.claude-3-7-sonnet-20250219-v1:0');
  const [systemPrompt, setSystemPrompt] = useState('You are a helpful assistant with access to tools. Use them to help the user.');
  const [showModelDropdown, setShowModelDropdown] = useState(false);

  const availableModels = [
    { id: 'anthropic.claude-3-7-sonnet-20250219-v1:0', name: 'Claude 3.7 Sonnet v1', provider: 'aws_bedrock' },
    { id: 'anthropic.claude-3-5-sonnet-20240620-v1:0', name: 'Claude 3.5 Sonnet v2', provider: 'aws_bedrock' },
    { id: 'anthropic.claude-3-5-sonnet-20240620-v1:0', name: 'Claude 3.5 Sonnet v1', provider: 'aws_bedrock' },
    { id: 'anthropic.claude-3-haiku-20240307-v1:0', name: 'Claude 3.5 Haiku v1', provider: 'aws_bedrock' },
    { id: 'anthropic.claude-3-opus-20240229-v1:0', name: 'Claude 3 Opus v1', provider: 'aws_bedrock' },
    { id: 'anthropic.claude-3-sonnet-20240229-v1:0', name: 'Claude 3 Sonnet v1', provider: 'aws_bedrock' },
    { id: 'anthropic.claude-3-haiku-20240307-v1:0', name: 'Claude 3 Haiku v1', provider: 'aws_bedrock' },
  ];

  useEffect(() => {
    // Load the default template when the component mounts
    if (nodes.length === 0 && templates.length > 0) {
      loadTemplate(templates[0]);
    }
  }, []);

  useEffect(() => {
    // Fit the view whenever the layout changes
    if (reactFlowInstance && nodes.length > 0) {
      setTimeout(() => {
        reactFlowInstance.fitView({ padding: 0.1 });
      }, 100);
    }
  }, [reactFlowInstance, nodes.length, leftPanelCollapsed, rightPanelCollapsed, isFullscreen]);

  const onConnect = useCallback((params) => {
    setEdges((eds) => addEdge(params, eds));
  }, [setEdges]);

  const onNodeClick = useCallback((_, node) => {
    setSelectedNode(node);
    // If the right panel is collapsed, expand it when a node is selected
    if (rightPanelCollapsed) {
      setRightPanelCollapsed(false);
    }
    setActiveConfigTab('properties');
  }, [rightPanelCollapsed]);

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/reactflow');
      
      if (!type || !reactFlowInstance) {
        return;
      }

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const nodeId = `${type}-${Date.now()}`;
      let newNode = {
        id: nodeId,
        type,
        position,
        data: { label: type.toUpperCase() },
      };

      // Add type-specific data
      switch(type) {
        case 'llm':
          newNode.data = {
            ...newNode.data,
            model: model,
            provider: 'aws_bedrock',
            temperature: 0.7,
            topP: 1.0,
            topK: 0,
            availableModels: [
              { id: 'anthropic.claude-3-7-sonnet-20250219-v1:0', name: 'Claude 3.7 Sonnet v1', provider: 'aws_bedrock' },
              { id: 'anthropic.claude-3-5-sonnet-20240620-v1:0', name: 'Claude 3.5 Sonnet v1', provider: 'aws_bedrock' },
              { id: 'anthropic.claude-3-opus-20240229-v1:0', name: 'Claude 3 Opus v1', provider: 'aws_bedrock' },
              { id: 'anthropic.claude-3-sonnet-20240229-v1:0', name: 'Claude 3 Sonnet v1', provider: 'aws_bedrock' },
              { id: 'anthropic.claude-3-haiku-20240307-v1:0', name: 'Claude 3 Haiku v1', provider: 'aws_bedrock' },
              { id: 'openai/gpt-4', name: 'GPT-4', provider: 'openai' },
              { id: 'openai/gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'openai' },
            ],
            onModelChange: (e) => updateNodeData(nodeId, { model: e.target.value }),
            onTemperatureChange: (e) => updateNodeData(nodeId, { temperature: parseFloat(e.target.value) }),
            onTopPChange: (e) => updateNodeData(nodeId, { topP: parseFloat(e.target.value) }),
            onTopKChange: (e) => updateNodeData(nodeId, { topK: parseInt(e.target.value) }),
          };
          break;
        case 'search':
          newNode.data = {
            ...newNode.data,
            engine: 'google',
            resultCount: 3,
            apiEndpoint: '',
            onEngineChange: (e) => updateNodeData(nodeId, { engine: e.target.value }),
            onResultCountChange: (e) => updateNodeData(nodeId, { resultCount: parseInt(e.target.value, 10) }),
            onApiEndpointChange: (e) => updateNodeData(nodeId, { apiEndpoint: e.target.value }),
          };
          break;
        case 'agent':
          newNode.data = {
            ...newNode.data,
            agentType: 'tool_calling',
            model: model,
            provider: 'aws_bedrock',
            temperature: 0.7,
            topP: 1.0,
            topK: 0,
            toolCount: 0,
            systemPrompt: systemPrompt,
          };
          break;
        case 'calculator':
          newNode.data = {
            ...newNode.data,
            precision: 2
          };
          break;
        case 'chatInput':
          newNode.data = {
            ...newNode.data,
            defaultValue: ''
          };
          break;
        case 'chatOutput':
          newNode.data = {
            ...newNode.data,
            format: 'text'
          };
          break;
        default:
          break;
      }

      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance, setNodes, model, systemPrompt]
  );

  const updateNodeData = useCallback((nodeId, newData) => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === nodeId) {
          return {
            ...node,
            data: {
              ...node.data,
              ...newData,
            },
          };
        }
        return node;
      })
    );
  }, [setNodes]);

  const onNodeUpdate = useCallback((newData) => {
    if (selectedNode) {
      updateNodeData(selectedNode.id, newData);
    }
  }, [selectedNode, updateNodeData]);

  const handleSaveFlow = () => {
    // Save flow to backend
    console.log("Saving flow:", { nodes, edges });
    // API call would go here
  };

  const handleTestAgent = async (input) => {
    // This would be an API call to test the agent
    console.log("Testing agent with input:", input);
    // Mock response
    return {
      content: `This is a simulated response for: "${input}"`
    };
  };

  const handleDeployAgent = () => {
    // Deploy agent as API
    console.log("Deploying agent");
    // API call would go here
  };

  const loadTemplate = (template) => {
    setNodes(template.nodes);
    setEdges(template.edges);
    setShowTemplates(false);
  };

  const clearCanvas = () => {
    setNodes([]);
    setEdges([]);
    setSelectedNode(null);
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const zoomIn = () => {
    if (reactFlowInstance) {
      reactFlowInstance.zoomIn();
    }
  };

  const zoomOut = () => {
    if (reactFlowInstance) {
      reactFlowInstance.zoomOut();
    }
  };

  const fitView = () => {
    if (reactFlowInstance) {
      reactFlowInstance.fitView({ padding: 0.1 });
    }
  };

  const selectModel = (modelId) => {
    setModel(modelId);
    setShowModelDropdown(false);
  };

  return (
    <div className={`agent-flow-builder ${isFullscreen ? 'fullscreen' : ''}`}>
      <div className="agent-flow-header">
        <div className="left-header">
          <h2>Agent Flow Builder</h2>
          <div className="template-selector">
            <button onClick={() => setShowTemplates(!showTemplates)} className="template-button">
              Templates ▾
            </button>
            {showTemplates && (
              <div className="template-dropdown">
                <button onClick={clearCanvas}>Empty Canvas</button>
                {templates.map((template, index) => (
                  <button key={index} onClick={() => loadTemplate(template)}>
                    {template.description || `Template ${index + 1}`}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="actions">
          <button onClick={handleSaveFlow} className="action-button">Save Flow</button>
          <button onClick={handleDeployAgent} className="action-button deploy-button">Deploy as API</button>
          <button onClick={toggleFullscreen} className="action-button icon-button">
            {isFullscreen ? '⊙' : '⤢'}
          </button>
        </div>
      </div>

      <div className="tab-container">
        <div className="tabs">
          <button 
            className={`tab ${activeTab === 'canvas' ? 'active' : ''}`}
            onClick={() => setActiveTab('canvas')}
          >
            Playground
          </button>
          <button 
            className={`tab ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            History
          </button>
        </div>
      </div>
      
      <div className="agent-flow-content">
        <div className={`left-panel ${leftPanelCollapsed ? 'collapsed' : ''}`}>
          <button 
            className="collapse-button left" 
            onClick={() => setLeftPanelCollapsed(!leftPanelCollapsed)}
          >
            {leftPanelCollapsed ? '▶' : '◀'}
          </button>
          
          {!leftPanelCollapsed && (
            <div className="left-panel-content">
              <div className="config-tabs">
                <button 
                  className={`config-tab ${activeConfigTab === 'components' ? 'active' : ''}`}
                  onClick={() => setActiveConfigTab('components')}
                >
                  Components
                </button>
                <button 
                  className={`config-tab ${activeConfigTab === 'properties' ? 'active' : ''}`}
                  onClick={() => setActiveConfigTab('properties')}
                >
                  Properties
                </button>
              </div>

              <div className="config-content">
                {activeConfigTab === 'components' && <ComponentPanel />}
                {activeConfigTab === 'properties' && <PropertiesPanel selectedNode={selectedNode} onNodeUpdate={onNodeUpdate} />}
              </div>
            </div>
          )}
        </div>
        
        <div className="main-panel">
          <div className="config-section">
            <div className="model-selector">
              <div className="label">Model</div>
              <div className="dropdown-container">
                <div 
                  className="selected-model" 
                  onClick={() => setShowModelDropdown(!showModelDropdown)}
                >
                  {availableModels.find(m => m.id === model)?.name || model}
                  <span className="dropdown-arrow">▼</span>
                </div>
                {showModelDropdown && (
                  <div className="model-dropdown">
                    {availableModels.map(m => (
                      <div 
                        key={m.id} 
                        className="model-option"
                        onClick={() => selectModel(m.id)}
                      >
                        {m.name}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
            
            <div className="system-prompt">
              <div className="label">System Prompt</div>
              <textarea 
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                placeholder="Enter system instructions..."
              />
            </div>
          </div>

          {activeTab === 'canvas' && (
            <div className="canvas-container">
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onNodeClick={onNodeClick}
                onInit={(instance) => {
                  setReactFlowInstance(instance);
                  // Auto-load the template if no nodes are present
                  if (nodes.length === 0 && templates.length > 0) {
                    loadTemplate(templates[0]);
                  }
                }}
                onDrop={onDrop}
                onDragOver={onDragOver}
                nodeTypes={nodeTypes}
                fitView
                minZoom={0.1}
                maxZoom={4}
                onZoomChange={setZoom}
                defaultViewport={{ x: 0, y: 0, zoom: 1 }}
              >
                <Background color="#f0f0f0" gap={20} size={1} />
                <Controls showInteractive={false} />
                <MiniMap 
                  nodeStrokeColor={(n) => {
                    if (n.type === 'agent') return '#d0b0ff';
                    if (n.type === 'llm') return '#b0b0ff';
                    if (n.type === 'search') return '#b0d0ff';
                    if (n.type === 'calculator') return '#ffb0b0';
                    if (n.type === 'chatInput') return '#b0d0ff';
                    if (n.type === 'chatOutput') return '#b0ffc0';
                    return '#eee';
                  }}
                  nodeColor={(n) => {
                    if (n.type === 'agent') return '#f8f0ff';
                    if (n.type === 'llm') return '#f0f0ff';
                    if (n.type === 'search') return '#f0f8ff';
                    if (n.type === 'calculator') return '#fff0f0';
                    if (n.type === 'chatInput') return '#f0f8ff';
                    if (n.type === 'chatOutput') return '#f0fff4';
                    return '#fff';
                  }}
                  nodeBorderRadius={8}
                />
                
                <Panel position="top-center" className="zoom-controls">
                  <div className="zoom-buttons">
                    <button onClick={zoomOut}>−</button>
                    <span>{Math.round(zoom * 100)}%</span>
                    <button onClick={zoomIn}>+</button>
                    <button onClick={fitView} className="fit-button">⊡</button>
                  </div>
                </Panel>
              </ReactFlow>
            </div>
          )}
          
          {activeTab === 'history' && (
            <div className="history-container">
              <div className="empty-history">No saved agent flows yet</div>
            </div>
          )}

          <div className="testing-section">
            <TestingConsole onRunTest={handleTestAgent} />
          </div>
        </div>
        
        <div className={`right-panel ${rightPanelCollapsed ? 'collapsed' : ''}`}>
          <button 
            className="collapse-button right" 
            onClick={() => setRightPanelCollapsed(!rightPanelCollapsed)}
          >
            {rightPanelCollapsed ? '◀' : '▶'}
          </button>
          
          {!rightPanelCollapsed && (
            <div className="right-panel-content">
              <PropertiesPanel 
                selectedNode={selectedNode} 
                onNodeUpdate={onNodeUpdate} 
              />
            </div>
          )}
        </div>
      </div>
      
      <style jsx>{`
        .agent-flow-builder {
          display: flex;
          flex-direction: column;
          height: 100vh;
          width: 100%;
          overflow: hidden;
          position: relative;
          background-color: #f8f9fa;
        }
        
        .agent-flow-builder.fullscreen {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          z-index: 9999;
          background: white;
        }
        
        .agent-flow-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.75rem 1.25rem;
          border-bottom: 1px solid #e0e0e0;
          background-color: #f8f9fa;
          z-index: 10;
        }
        
        .left-header {
          display: flex;
          align-items: center;
          gap: 1.5rem;
        }
        
        h2 {
          margin: 0;
          font-size: 1.2rem;
          font-weight: 600;
        }
        
        .actions {
          display: flex;
          gap: 0.75rem;
          align-items: center;
        }
        
        .action-button {
          padding: 0.5rem 1rem;
          background-color: #4a90e2;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          transition: background-color 0.2s;
        }
        
        .action-button:hover {
          background-color: #3a80d2;
        }
        
        .icon-button {
          width: 34px;
          height: 34px;
          padding: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.2rem;
        }
        
        .deploy-button {
          background-color: #38a169;
        }
        
        .deploy-button:hover {
          background-color: #2f855a;
        }
        
        .template-selector {
          position: relative;
        }
        
        .template-button {
          background-color: #f8f9fa;
          border: 1px solid #dee2e6;
          color: #495057;
          padding: 0.5rem 1rem;
          border-radius: 4px;
          cursor: pointer;
        }
        
        .template-dropdown {
          position: absolute;
          top: 100%;
          left: 0;
          z-index: 10;
          background-color: white;
          border: 1px solid #e0e0e0;
          border-radius: 4px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
          display: flex;
          flex-direction: column;
          min-width: 220px;
        }
        
        .template-dropdown button {
          padding: 0.75rem 1rem;
          text-align: left;
          border: none;
          background: none;
          cursor: pointer;
          transition: background-color 0.2s;
        }
        
        .template-dropdown button:hover {
          background-color: #f5f5f5;
        }
        
        .tab-container {
          background-color: white;
          border-bottom: 1px solid #e0e0e0;
        }
        
        .tabs {
          display: flex;
          padding: 0 1.25rem;
        }
        
        .tab {
          padding: 0.75rem 1rem;
          background: none;
          border: none;
          border-bottom: 2px solid transparent;
          color: #718096;
          font-size: 0.9rem;
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .tab:hover {
          color: #4a5568;
        }
        
        .tab.active {
          color: #4a90e2;
          border-bottom-color: #4a90e2;
          font-weight: 500;
        }
        
        .agent-flow-content {
          display: flex;
          flex: 1;
          overflow: hidden;
          position: relative;
        }
        
        .left-panel {
          width: 250px;
          border-right: 1px solid #e0e0e0;
          transition: width 0.3s ease;
          position: relative;
          background-color: white;
          z-index: 5;
        }
        
        .left-panel.collapsed {
          width: 24px;
          overflow: hidden;
        }
        
        .left-panel-content {
          display: flex;
          flex-direction: column;
          height: 100%;
          width: 100%;
        }
        
        .config-tabs {
          display: flex;
          border-bottom: 1px solid #e0e0e0;
        }
        
        .config-tab {
          flex: 1;
          padding: 0.65rem 0.5rem;
          background: none;
          border: none;
          color: #718096;
          font-size: 0.85rem;
          cursor: pointer;
          text-align: center;
          transition: background-color 0.2s;
        }
        
        .config-tab:hover {
          background-color: #f7fafc;
        }
        
        .config-tab.active {
          background-color: #f7fafc;
          color: #4a5568;
          font-weight: 500;
        }
        
        .config-content {
          flex: 1;
          overflow-y: auto;
        }
        
        .main-panel {
          flex: 1;
          height: 100%;
          display: flex;
          flex-direction: column;
          position: relative;
          z-index: 1;
          overflow: hidden; /* Prevent overflow */
        }
        
        .config-section {
          padding: 0.75rem;
          border-bottom: 1px solid #e0e0e0;
          display: flex;
          gap: 1rem;
        }
        
        .model-selector {
          flex: 1;
        }
        
        .system-prompt {
          flex: 2;
        }
        
        .label {
          font-size: 0.85rem;
          font-weight: 500;
          color: #4a5568;
          margin-bottom: 0.5rem;
        }
        
        .dropdown-container {
          position: relative;
        }
        
        .selected-model {
          padding: 0.5rem 0.75rem;
          border: 1px solid #e2e8f0;
          border-radius: 4px;
          cursor: pointer;
          display: flex;
          justify-content: space-between;
          align-items: center;
          background-color: white;
        }
        
        .dropdown-arrow {
          font-size: 0.75rem;
          color: #a0aec0;
          margin-left: 0.5rem;
        }
        
        .model-dropdown {
          position: absolute;
          top: 100%;
          left: 0;
          right: 0;
          z-index: 100;
          background-color: white;
          border: 1px solid #e2e8f0;
          border-radius: 4px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
          max-height: 220px;
          overflow-y: auto;
        }
        
        .model-option {
          padding: 0.5rem 0.75rem;
          cursor: pointer;
          transition: background-color 0.2s;
        }
        
        .model-option:hover {
          background-color: #f7fafc;
        }
        
        .system-prompt textarea {
          width: 100%;
          height: 60px;
          padding: 0.5rem 0.75rem;
          border: 1px solid #e2e8f0;
          border-radius: 4px;
          resize: vertical;
          font-family: inherit;
          font-size: 0.9rem;
        }
        
        .right-panel {
          width: 300px;
          border-left: 1px solid #e0e0e0;
          transition: width 0.3s ease;
          position: relative;
          background-color: white;
          z-index: 5;
        }
        
        .right-panel.collapsed {
          width: 24px;
          overflow: hidden;
        }
        
        .right-panel-content {
          height: 100%;
          overflow-y: auto;
        }
        
        .collapse-button {
          position: absolute;
          top: 50%;
          width: 24px;
          height: 40px;
          background: rgba(240, 240, 240, 0.9);
          border: 1px solid #e0e0e0;
          border-radius: 4px;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          z-index: 10;
          transition: background-color 0.2s;
        }
        
        .collapse-button:hover {
          background-color: rgba(220, 220, 220, 0.9);
        }
        
        .collapse-button.left {
          right: -12px;
          transform: translateY(-50%);
          border-top-left-radius: 0;
          border-bottom-left-radius: 0;
        }
        
        .collapse-button.right {
          left: -12px;
          transform: translateY(-50%);
          border-top-right-radius: 0;
          border-bottom-right-radius: 0;
        }
        
        .canvas-container {
          flex: 1;
          position: relative;
          overflow: hidden;
        }
        
        .history-container {
          flex: 1;
          display: flex;
          justify-content: center;
          align-items: center;
          background-color: #f9fafb;
        }
        
        .empty-history {
          color: #a0aec0;
          font-size: 0.95rem;
        }
        
        .testing-section {
          padding: 0.75rem;
          border-top: 1px solid #e0e0e0;
          max-height: 180px;
        }
        
        .zoom-controls {
          background-color: white;
          border-radius: 6px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.15);
          padding: 0 !important; /* Override ReactFlow panel padding */
          overflow: hidden;
          margin-top: 10px;
        }
        
        .zoom-buttons {
          display: flex;
          align-items: center;
        }
        
        .zoom-buttons button {
          background: none;
          color: #333;
          width: 34px;
          height: 34px;
          font-size: 16px;
          padding: 0;
          margin: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 0;
          transition: background-color 0.2s;
          border: none;
          cursor: pointer;
        }
        
        .zoom-buttons button:hover {
          background-color: #f0f0f0;
        }
        
        .zoom-buttons span {
          padding: 0 0.75rem;
          font-size: 0.85rem;
          white-space: nowrap;
        }
        
        .fit-button {
          border-left: 1px solid #e0e0e0;
        }
      `}</style>
    </div>
  );
};

export default AgentFlowCanvas; 