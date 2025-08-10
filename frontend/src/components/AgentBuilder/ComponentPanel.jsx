import React from 'react';

const ComponentPanel = () => {
  const onDragStart = (event, nodeType) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="component-panel">
      <h3>Components</h3>
      
      <div className="component-section">
        <h4>Language Models</h4>
        <div 
          className="component-item"
          draggable
          onDragStart={(event) => onDragStart(event, 'llm')}
        >
          <div className="component-icon">🤖</div>
          <div className="component-label">LLM</div>
        </div>
      </div>
      
      <div className="component-section">
        <h4>Tools</h4>
        <div 
          className="component-item"
          draggable
          onDragStart={(event) => onDragStart(event, 'search')}
        >
          <div className="component-icon">🔍</div>
          <div className="component-label">Search Tool</div>
        </div>
      </div>
      
      <style jsx>{`
        .component-panel {
          padding: 1rem;
        }
        
        h3 {
          margin-top: 0;
          margin-bottom: 1rem;
          font-size: 1.2rem;
          font-weight: 600;
        }
        
        .component-section {
          margin-bottom: 1.5rem;
        }
        
        h4 {
          margin-top: 0;
          margin-bottom: 0.75rem;
          font-size: 1rem;
          font-weight: 500;
          color: #4a5568;
        }
        
        .component-item {
          display: flex;
          align-items: center;
          padding: 0.75rem;
          background-color: #f7fafc;
          border: 1px solid #e2e8f0;
          border-radius: 6px;
          margin-bottom: 0.5rem;
          cursor: move;
          transition: all 0.2s;
        }
        
        .component-item:hover {
          background-color: #edf2f7;
          border-color: #cbd5e0;
        }
        
        .component-icon {
          font-size: 1.25rem;
          margin-right: 0.75rem;
        }
        
        .component-label {
          font-size: 0.9rem;
          font-weight: 500;
        }
      `}</style>
    </div>
  );
};

export default ComponentPanel; 