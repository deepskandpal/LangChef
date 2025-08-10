import React from 'react';

const PropertiesPanel = ({ selectedNode, onNodeUpdate }) => {
  if (!selectedNode) {
    return (
      <div className="properties-panel">
        <h3>Properties</h3>
        <div className="no-selection">
          <p>Select a node to edit its properties</p>
        </div>
        
        <style jsx>{`
          .properties-panel {
            padding: 1rem;
            height: 50%;
            overflow-y: auto;
          }
          
          h3 {
            margin-top: 0;
            margin-bottom: 1rem;
            font-size: 1.2rem;
            font-weight: 600;
          }
          
          .no-selection {
            display: flex;
            height: 100px;
            align-items: center;
            justify-content: center;
            color: #718096;
            font-size: 0.9rem;
            border: 1px dashed #e2e8f0;
            border-radius: 6px;
          }
        `}</style>
      </div>
    );
  }

  const renderProperties = () => {
    // Based on node type, render different property editors
    if (selectedNode.type === 'llm') {
      return (
        <div className="property-group">
          <div className="property-field">
            <label>Model</label>
            <select 
              value={selectedNode.data.model} 
              onChange={(e) => selectedNode.data.onModelChange(e)}
            >
              {selectedNode.data.availableModels.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </select>
          </div>
          
          <div className="property-field">
            <label>Temperature</label>
            <div className="temperature-control">
              <input 
                type="range" 
                min="0" 
                max="2" 
                step="0.1" 
                value={selectedNode.data.temperature} 
                onChange={(e) => selectedNode.data.onTemperatureChange(e)} 
              />
              <span className="temperature-value">{selectedNode.data.temperature}</span>
            </div>
          </div>
          
          <div className="property-field">
            <label>System Prompt</label>
            <textarea
              rows="4"
              placeholder="Enter system instructions for the LLM..."
              value={selectedNode.data.systemPrompt || ''}
              onChange={(e) => onNodeUpdate({ systemPrompt: e.target.value })}
            ></textarea>
          </div>
        </div>
      );
    } else if (selectedNode.type === 'search') {
      return (
        <div className="property-group">
          <div className="property-field">
            <label>Search Engine</label>
            <select 
              value={selectedNode.data.engine} 
              onChange={(e) => selectedNode.data.onEngineChange(e)}
            >
              <option value="google">Google</option>
              <option value="bing">Bing</option>
              <option value="custom">Custom</option>
            </select>
          </div>
          
          <div className="property-field">
            <label>Results Count</label>
            <input 
              type="number" 
              min="1" 
              max="10" 
              value={selectedNode.data.resultCount} 
              onChange={(e) => selectedNode.data.onResultCountChange(e)} 
            />
          </div>
          
          {selectedNode.data.engine === 'custom' && (
            <div className="property-field">
              <label>API Endpoint</label>
              <input 
                type="text" 
                placeholder="https://api.example.com/search" 
                value={selectedNode.data.apiEndpoint} 
                onChange={(e) => selectedNode.data.onApiEndpointChange(e)} 
              />
            </div>
          )}
        </div>
      );
    } else {
      return <p>Unknown node type</p>;
    }
  };

  return (
    <div className="properties-panel">
      <h3>Properties: {selectedNode.type.toUpperCase()}</h3>
      {renderProperties()}
      
      <style jsx>{`
        .properties-panel {
          padding: 1rem;
          height: 50%;
          overflow-y: auto;
        }
        
        h3 {
          margin-top: 0;
          margin-bottom: 1rem;
          font-size: 1.2rem;
          font-weight: 600;
        }
        
        .property-group {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        
        .property-field {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }
        
        label {
          font-size: 0.85rem;
          font-weight: 500;
          color: #4a5568;
        }
        
        select, input, textarea {
          padding: 0.5rem;
          border: 1px solid #e2e8f0;
          border-radius: 4px;
          font-size: 0.9rem;
        }
        
        .temperature-control {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }
        
        .temperature-value {
          font-size: 0.9rem;
          min-width: 1.5rem;
        }
        
        textarea {
          resize: vertical;
          min-height: 80px;
        }
      `}</style>
    </div>
  );
};

export default PropertiesPanel; 