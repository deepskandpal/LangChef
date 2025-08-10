import React from 'react';
import { Handle, Position } from 'reactflow';

const LLMNode = ({ data, isConnectable }) => {
  return (
    <div className="llm-node">
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={isConnectable}
      />
      
      <div className="node-content">
        <div className="node-header">
          <div className="node-icon">🤖</div>
          <div className="node-title">LLM</div>
        </div>
        
        <div className="node-body">
          <div className="node-property">
            <span className="property-label">Model:</span>
            <span className="property-value">{data.model}</span>
          </div>
          <div className="node-property">
            <span className="property-label">Temp:</span>
            <span className="property-value">{data.temperature}</span>
          </div>
        </div>
      </div>
      
      <Handle
        type="source"
        position={Position.Bottom}
        id="output"
        isConnectable={isConnectable}
      />
      
      <style jsx>{`
        .llm-node {
          padding: 12px;
          background-color: #f0f7ff;
          border: 1px solid #90cdf4;
          border-radius: 8px;
          width: 180px;
        }
        
        .node-content {
          display: flex;
          flex-direction: column;
        }
        
        .node-header {
          display: flex;
          align-items: center;
          margin-bottom: 8px;
          padding-bottom: 8px;
          border-bottom: 1px solid #e2e8f0;
        }
        
        .node-icon {
          font-size: 1.5rem;
          margin-right: 8px;
        }
        
        .node-title {
          font-weight: bold;
          font-size: 1rem;
        }
        
        .node-body {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        
        .node-property {
          display: flex;
          justify-content: space-between;
          font-size: 0.85rem;
        }
        
        .property-label {
          font-weight: 500;
          color: #4a5568;
        }
        
        .property-value {
          font-weight: 400;
          color: #1a202c;
        }
      `}</style>
    </div>
  );
};

export default LLMNode; 