import React from 'react';

const PropertiesPanel = ({ selectedNode, onNodeUpdate }) => {
  if (!selectedNode) {
    return (
      <div className="properties-panel">
        <div className="panel-header">Properties</div>
        <div className="panel-empty">
          Select a node to edit its properties
        </div>
        <style jsx>{`
          .properties-panel {
            display: flex;
            flex-direction: column;
            height: 50%;
            overflow-y: auto;
            border-bottom: 1px solid #e0e0e0;
          }
          
          .panel-header {
            font-size: 16px;
            font-weight: 600;
            padding: 12px 16px;
            border-bottom: 1px solid #e0e0e0;
            background-color: #f8f9fa;
          }
          
          .panel-empty {
            padding: 16px;
            color: #718096;
            text-align: center;
            font-size: 14px;
            margin-top: 24px;
          }
        `}</style>
      </div>
    );
  }

  const renderProperties = () => {
    const type = selectedNode.type;
    const data = selectedNode.data;
    
    switch (type) {
      case 'llm':
        return (
          <div className="property-group">
            <div className="property-field">
              <label htmlFor="model">Model</label>
              <select 
                id="model" 
                value={data.model} 
                onChange={(e) => onNodeUpdate({ model: e.target.value })}
              >
                {data.availableModels.map(model => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))}
              </select>
            </div>
            
            <div className="property-field">
              <label htmlFor="temperature">Temperature</label>
              <div className="slider-container">
                <input 
                  type="range" 
                  id="temperature" 
                  min="0" 
                  max="1" 
                  step="0.01" 
                  value={data.temperature} 
                  onChange={(e) => onNodeUpdate({ temperature: parseFloat(e.target.value) })}
                />
                <span className="slider-value">{data.temperature}</span>
              </div>
            </div>
            
            <div className="property-field">
              <label htmlFor="topP">Top P</label>
              <div className="slider-container">
                <input 
                  type="range" 
                  id="topP" 
                  min="0" 
                  max="1" 
                  step="0.01" 
                  value={data.topP || 1.0} 
                  onChange={(e) => onNodeUpdate({ topP: parseFloat(e.target.value) })}
                />
                <span className="slider-value">{data.topP || 1.0}</span>
              </div>
            </div>
            
            <div className="property-field">
              <label htmlFor="topK">Top K</label>
              <div className="input-group">
                <input 
                  type="number" 
                  id="topK" 
                  min="0" 
                  max="100" 
                  value={data.topK || 0} 
                  onChange={(e) => onNodeUpdate({ topK: parseInt(e.target.value) })}
                />
                <span className="input-help">0 = disabled</span>
              </div>
            </div>
          </div>
        );
        
      case 'agent':
        return (
          <div className="property-group">
            <div className="property-field">
              <label htmlFor="agentType">Agent Type</label>
              <select 
                id="agentType" 
                value={data.agentType} 
                onChange={(e) => onNodeUpdate({ agentType: e.target.value })}
              >
                <option value="tool_calling">Tool-calling Agent</option>
                <option value="reasoning">Reasoning Agent</option>
                <option value="chat">Chat Agent</option>
              </select>
            </div>
            
            <div className="property-field">
              <label htmlFor="model">Model</label>
              <select 
                id="model" 
                value={data.model} 
                onChange={(e) => onNodeUpdate({ model: e.target.value })}
              >
                <option value="anthropic.claude-3-opus-20240229-v1:0">Claude 3 Opus</option>
                <option value="anthropic.claude-3-sonnet-20240229-v1:0">Claude 3 Sonnet</option>
                <option value="anthropic.claude-3-haiku-20240307-v1:0">Claude 3 Haiku</option>
                <option value="anthropic.claude-3-5-sonnet-20240620-v1:0">Claude 3.5 Sonnet</option>
                <option value="openai/gpt-4">GPT-4</option>
                <option value="openai/gpt-3.5-turbo">GPT-3.5 Turbo</option>
              </select>
            </div>
            
            <div className="property-field">
              <label htmlFor="temperature">Temperature</label>
              <div className="slider-container">
                <input 
                  type="range" 
                  id="temperature" 
                  min="0" 
                  max="1" 
                  step="0.01" 
                  value={data.temperature || 0.7} 
                  onChange={(e) => onNodeUpdate({ temperature: parseFloat(e.target.value) })}
                />
                <span className="slider-value">{data.temperature || 0.7}</span>
              </div>
            </div>
            
            <div className="property-field">
              <label htmlFor="topP">Top P</label>
              <div className="slider-container">
                <input 
                  type="range" 
                  id="topP" 
                  min="0" 
                  max="1" 
                  step="0.01" 
                  value={data.topP || 1.0} 
                  onChange={(e) => onNodeUpdate({ topP: parseFloat(e.target.value) })}
                />
                <span className="slider-value">{data.topP || 1.0}</span>
              </div>
            </div>
            
            <div className="property-field">
              <label htmlFor="topK">Top K</label>
              <div className="input-group">
                <input 
                  type="number" 
                  id="topK" 
                  min="0" 
                  max="100" 
                  value={data.topK || 0} 
                  onChange={(e) => onNodeUpdate({ topK: parseInt(e.target.value) })}
                />
                <span className="input-help">0 = disabled</span>
              </div>
            </div>
            
            <div className="property-field">
              <label htmlFor="systemPrompt">System Prompt</label>
              <textarea 
                id="systemPrompt" 
                value={data.systemPrompt || ''} 
                onChange={(e) => onNodeUpdate({ systemPrompt: e.target.value })}
                rows={4}
              />
            </div>
          </div>
        );
        
      case 'search':
        return (
          <div className="property-group">
            <div className="property-field">
              <label htmlFor="engine">Search Engine</label>
              <select 
                id="engine" 
                value={data.engine} 
                onChange={(e) => onNodeUpdate({ engine: e.target.value })}
              >
                <option value="google">Google</option>
                <option value="bing">Bing</option>
                <option value="duckduckgo">DuckDuckGo</option>
              </select>
            </div>
            
            <div className="property-field">
              <label htmlFor="resultCount">Result Count</label>
              <input 
                type="number" 
                id="resultCount" 
                min="1" 
                max="10" 
                value={data.resultCount} 
                onChange={(e) => onNodeUpdate({ resultCount: parseInt(e.target.value) })}
              />
            </div>
            
            <div className="property-field">
              <label htmlFor="apiEndpoint">API Endpoint (optional)</label>
              <input 
                type="text" 
                id="apiEndpoint" 
                value={data.apiEndpoint || ''} 
                onChange={(e) => onNodeUpdate({ apiEndpoint: e.target.value })}
                placeholder="Custom search API endpoint"
              />
            </div>
          </div>
        );
        
      case 'calculator':
        return (
          <div className="property-group">
            <div className="property-field">
              <label htmlFor="precision">Decimal Precision</label>
              <input 
                type="number" 
                id="precision" 
                min="0" 
                max="10" 
                value={data.precision} 
                onChange={(e) => onNodeUpdate({ precision: parseInt(e.target.value) })}
              />
            </div>
          </div>
        );
        
      case 'chatInput':
        return (
          <div className="property-group">
            <div className="property-field">
              <label htmlFor="defaultValue">Default Text (optional)</label>
              <textarea 
                id="defaultValue" 
                value={data.defaultValue || ''} 
                onChange={(e) => onNodeUpdate({ defaultValue: e.target.value })}
                rows={3}
                placeholder="Enter a default prompt here..."
              />
            </div>
          </div>
        );
        
      case 'chatOutput':
        return (
          <div className="property-group">
            <div className="property-field">
              <label htmlFor="format">Output Format</label>
              <select 
                id="format" 
                value={data.format || 'text'} 
                onChange={(e) => onNodeUpdate({ format: e.target.value })}
              >
                <option value="text">Plain Text</option>
                <option value="markdown">Markdown</option>
                <option value="html">HTML</option>
              </select>
            </div>
          </div>
        );
        
      default:
        return (
          <div className="panel-empty">
            No editable properties for this node type
          </div>
        );
    }
  };

  return (
    <div className="properties-panel">
      <div className="panel-header">
        Properties: {selectedNode.type.toUpperCase()}
      </div>
      
      <div className="panel-content">
        {renderProperties()}
      </div>
      
      <style jsx>{`
        .properties-panel {
          display: flex;
          flex-direction: column;
          height: 50%;
          overflow-y: auto;
          border-bottom: 1px solid #e0e0e0;
        }
        
        .panel-header {
          font-size: 16px;
          font-weight: 600;
          padding: 12px 16px;
          border-bottom: 1px solid #e0e0e0;
          background-color: #f8f9fa;
          position: sticky;
          top: 0;
          z-index: 1;
        }
        
        .panel-content {
          padding: 16px;
          overflow-y: auto;
        }
        
        .panel-empty {
          padding: 16px;
          color: #718096;
          text-align: center;
          font-size: 14px;
          margin-top: 24px;
        }
        
        .property-group {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        
        .property-field {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        
        .property-field label {
          font-size: 12px;
          font-weight: 500;
          color: #4a5568;
        }
        
        .property-field input,
        .property-field select,
        .property-field textarea {
          padding: 8px;
          border: 1px solid #e2e8f0;
          border-radius: 4px;
          font-size: 14px;
          background-color: white;
        }
        
        .property-field textarea {
          resize: vertical;
          min-height: 80px;
        }
        
        .slider-container {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        
        .slider-container input[type="range"] {
          flex: 1;
        }
        
        .slider-value {
          font-size: 12px;
          color: #4a5568;
          min-width: 30px;
          text-align: right;
        }
        
        .input-group {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        
        .input-help {
          font-size: 12px;
          color: #718096;
        }
      `}</style>
    </div>
  );
};

export default PropertiesPanel; 