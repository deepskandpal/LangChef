import React from 'react';
import { Handle, Position } from 'reactflow';

const ChatOutputNode = ({ data, isConnectable }) => {
  return (
    <div className="chat-output-node">
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={isConnectable}
      />
      
      <div className="node-content">
        <div className="node-header">
          <div className="node-icon">📤</div>
          <div className="node-title">Chat Output</div>
        </div>
        
        <div className="node-body">
          <div className="node-description">
            Agent's response to the user
          </div>
        </div>
      </div>
      
      <style jsx>{`
        .chat-output-node {
          padding: 12px;
          background-color: #f0fff4;
          border: 1px solid #b0ffc0;
          border-radius: 8px;
          width: 160px;
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
        
        .node-description {
          font-size: 0.8rem;
          color: #718096;
          margin-top: 4px;
        }
      `}</style>
    </div>
  );
};

export default ChatOutputNode; 