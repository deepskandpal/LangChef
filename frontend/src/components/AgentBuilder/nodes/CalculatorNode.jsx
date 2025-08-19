import React from 'react';
import { Handle, Position } from 'reactflow';

const CalculatorNode = ({ data, isConnectable }) => {
  return (
    <div className="calculator-tool-node">
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={isConnectable}
      />
      
      <div className="node-content">
        <div className="node-header">
          <div className="node-icon">🧮</div>
          <div className="node-title">Calculator</div>
        </div>
        
        <div className="node-body">
          <div className="node-property">
            <span className="property-label">Precision:</span>
            <span className="property-value">{data.precision || 2}</span>
          </div>
          <div className="node-description">
            Performs basic arithmetic operations
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
        .calculator-tool-node {
          padding: 12px;
          background-color: #fff0f0;
          border: 1px solid #ffb0b0;
          border-radius: 8px;
          width: 180px;
          box-shadow: 0 2px 5px rgba(0,0,0,0.1);
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
        
        .node-description {
          font-size: 0.8rem;
          color: #718096;
          margin-top: 4px;
        }
      `}</style>
    </div>
  );
};

export default CalculatorNode;