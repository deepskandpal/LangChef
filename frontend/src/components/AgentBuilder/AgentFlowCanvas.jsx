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
        resultCount: 3
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
  ],
  description: 'A simple agent that can use a calculator and search tool'
};

const AgentFlowCanvas = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);
  const [templates] = useState([simpleAgentTemplate]);

  useEffect(() => {
    // Load the default template when the component mounts
    if (nodes.length === 0 && templates.length > 0) {
      loadTemplate(templates[0]);
    }
  }, []);

  const loadTemplate = useCallback((template) => {
    setNodes(template.nodes);
    setEdges(template.edges);
  }, [setNodes, setEdges]);

  const onConnect = useCallback((params) => {
    setEdges((eds) => addEdge(params, eds));
  }, [setEdges]);

  const onNodeClick = useCallback((_, node) => {
    setSelectedNode(node);
  }, []);

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
      if (type === 'llm') {
        newNode.data = {
          ...newNode.data,
          model: 'anthropic.claude-3-sonnet-20240229-v1:0',
          temperature: 0.7,
          topP: 1.0,
          topK: 0,
        };
      } else if (type === 'search') {
        newNode.data = {
          ...newNode.data,
          engine: 'google',
          resultCount: 3,
        };
      } else if (type === 'agent') {
        newNode.data = {
          ...newNode.data,
          model: 'anthropic.claude-3-sonnet-20240229-v1:0',
          provider: 'aws_bedrock',
          agentType: 'tool_calling',
          temperature: 0.7,
          topP: 1.0,
          topK: 0,
          toolCount: 0,
          systemPrompt: 'You are a helpful assistant.'
        };
      } else if (type === 'calculator') {
        newNode.data = {
          ...newNode.data,
          precision: 2,
        };
      }

      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance, setNodes]
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
  };

  const handleTestAgent = async (input) => {
    // This would be an API call to test the agent
    console.log("Testing agent with input:", input);
    return {
      content: `This is a simulated response for: "${input}"`
    };
  };

  const handleDeployAgent = () => {
    // Deploy agent as API
    console.log("Deploying agent");
  };

  return (
    <div className="agent-flow-builder">
      <div className="agent-flow-header">
        <h1>Agent Flow Builder</h1>
        <div className="actions">
          <button onClick={handleSaveFlow}>Save Flow</button>
          <button onClick={handleDeployAgent}>Deploy as API</button>
        </div>
      </div>
      
      <div className="agent-flow-content">
        <div className="left-panel">
          <ComponentPanel />
        </div>
        
        <div className="center-panel">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onInit={setReactFlowInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            nodeTypes={nodeTypes}
            fitView
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </div>
        
        <div className="right-panel">
          <PropertiesPanel 
            selectedNode={selectedNode} 
            onNodeUpdate={onNodeUpdate} 
          />
          <TestingConsole onRunTest={handleTestAgent} />
        </div>
      </div>
      
      <style jsx>{`
        .agent-flow-builder {
          display: flex;
          flex-direction: column;
          height: 100vh;
          width: 100%;
        }
        
        .agent-flow-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem;
          border-bottom: 1px solid #e0e0e0;
        }
        
        .agent-flow-content {
          display: flex;
          flex: 1;
          overflow: hidden;
        }
        
        .left-panel {
          width: 250px;
          border-right: 1px solid #e0e0e0;
          overflow-y: auto;
        }
        
        .center-panel {
          flex: 1;
          height: 100%;
        }
        
        .right-panel {
          width: 300px;
          border-left: 1px solid #e0e0e0;
          display: flex;
          flex-direction: column;
        }
        
        .actions {
          display: flex;
          gap: 1rem;
        }
        
        button {
          padding: 0.5rem 1rem;
          background-color: #4a90e2;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        }
        
        button:hover {
          background-color: #3a80d2;
        }
      `}</style>
    </div>
  );
};

export default AgentFlowCanvas; 