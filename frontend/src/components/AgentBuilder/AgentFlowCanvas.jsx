import React, { useCallback, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';

import LLMNode from './nodes/LLMNode';
import SearchToolNode from './nodes/SearchToolNode';
import ComponentPanel from './ComponentPanel';
import PropertiesPanel from './PropertiesPanel';
import TestingConsole from './TestingConsole';

const nodeTypes = {
  llm: LLMNode,
  search: SearchToolNode,
};

const AgentFlowCanvas = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);

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
          model: 'gpt-4',
          temperature: 0.7,
          availableModels: [
            { id: 'gpt-4', name: 'GPT-4' },
            { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo' },
            { id: 'claude-3-opus', name: 'Claude 3 Opus' },
          ],
          onModelChange: (e) => updateNodeData(nodeId, { model: e.target.value }),
          onTemperatureChange: (e) => updateNodeData(nodeId, { temperature: parseFloat(e.target.value) }),
        };
      } else if (type === 'search') {
        newNode.data = {
          ...newNode.data,
          engine: 'google',
          resultCount: 3,
          apiEndpoint: '',
          onEngineChange: (e) => updateNodeData(nodeId, { engine: e.target.value }),
          onResultCountChange: (e) => updateNodeData(nodeId, { resultCount: parseInt(e.target.value, 10) }),
          onApiEndpointChange: (e) => updateNodeData(nodeId, { apiEndpoint: e.target.value }),
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