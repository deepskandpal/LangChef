import React from 'react';
import { Handle, Position } from 'reactflow';

const ChatInputNode = ({ data, isConnectable }) => {
  return (
    <div className="chat-input-node">
      <div className="node-content">
        <div className="node-header">
          <div className="node-icon">💬</div>
          <div className="node-title">Chat Input</div>
        </div>
        
        <div className="node-body">
          <div className="node-description">
            User's input to the agent
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
        .chat-input-node {
          padding: 12px;
          background-color: #f0f8ff;
          border: 1px solid #b0d0ff;
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

export default ChatInputNode;