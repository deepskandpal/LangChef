import React from 'react';
import { Handle, Position } from 'reactflow';

const SearchToolNode = ({ data, isConnectable }) => {
  return (
    <div className="search-tool-node">
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={isConnectable}
      />
      
      <div className="node-content">
        <div className="node-header">
          <div className="node-icon">🔍</div>
          <div className="node-title">Search Tool</div>
        </div>
        
        <div className="node-body">
          <div className="node-property">
            <span className="property-label">Engine:</span>
            <span className="property-value">{data.engine}</span>
          </div>
          <div className="node-property">
            <span className="property-label">Results:</span>
            <span className="property-value">{data.resultCount}</span>
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
        .search-tool-node {
          padding: 12px;
          background-color: #f0fff4;
          border: 1px solid #9ae6b4;
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

export default SearchToolNode; 