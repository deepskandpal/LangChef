import React, { memo } from 'react';
import { Handle } from 'reactflow';

const LLMNode = ({ data }) => {
  const { 
    label, 
    model = 'anthropic.claude-3-sonnet-20240229-v1:0', 
    temperature = 0.7,
    topP = 1.0,
    topK = 0,
    availableModels = [], 
    onModelChange, 
    onTemperatureChange,
    onTopPChange,
    onTopKChange 
  } = data;

  // Get model name from ID for display
  const getModelName = (modelId) => {
    const foundModel = availableModels.find(m => m.id === modelId);
    return foundModel ? foundModel.name : modelId;
  };

  // Get provider for model badge
  const getModelProvider = (modelId) => {
    const foundModel = availableModels.find(m => m.id === modelId);
    return foundModel?.provider || 'unknown';
  };

  return (
    <div className="llm-node">
      <Handle
        type="source"
        position="bottom"
        id="output"
        style={{ background: '#9f7aea' }}
      />
      
      <div className="header">
        <div className="title">
          {label || 'LLM'}
          <div className="provider-badge" data-provider={getModelProvider(model)}>
            {getModelProvider(model) === 'aws_bedrock' ? 'Bedrock' : 
             getModelProvider(model) === 'openai' ? 'OpenAI' : 
             getModelProvider(model)}
          </div>
        </div>
      </div>
      
      <div className="content">
        <div className="model-info">
          <div className="model-name">{getModelName(model)}</div>
          <div className="model-params">
            <span>Temp: {temperature}</span>
            <span>Top-P: {topP}</span>
            {topK > 0 && <span>Top-K: {topK}</span>}
          </div>
        </div>
      </div>

      <style jsx>{`
        .llm-node {
          border: 1px solid #9f7aea;
          border-radius: 8px;
          background-color: #f8f0ff;
          width: 180px;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        .header {
          background-color: #9f7aea;
          color: white;
          padding: 8px 10px;
          border-top-left-radius: 7px;
          border-top-right-radius: 7px;
        }

        .title {
          font-weight: 600;
          font-size: 14px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .provider-badge {
          font-size: 10px;
          padding: 2px 6px;
          border-radius: 4px;
          background-color: white;
          color: #333;
          font-weight: 500;
        }

        .provider-badge[data-provider="aws_bedrock"] {
          background-color: #FF9900;
          color: #232F3E;
        }

        .provider-badge[data-provider="openai"] {
          background-color: #10a37f;
          color: white;
        }

        .content {
          padding: 10px;
        }

        .model-info {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .model-name {
          font-weight: 500;
          font-size: 13px;
          color: #4a5568;
        }

        .model-params {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          font-size: 11px;
          color: #718096;
        }

        .model-params span {
          background-color: #edf2f7;
          padding: 2px 6px;
          border-radius: 4px;
        }
      `}</style>
    </div>
  );
};

export default memo(LLMNode); 