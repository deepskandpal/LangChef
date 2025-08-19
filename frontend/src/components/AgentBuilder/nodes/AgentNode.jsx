import React, { memo } from 'react';
import { Handle } from 'reactflow';

const AgentNode = ({ data }) => {
  const { 
    label, 
    model = 'anthropic.claude-3-sonnet-20240229-v1:0',
    provider = 'aws_bedrock',
    agentType = 'tool_calling',
    temperature = 0.7,
    topP = 1.0,
    topK = 0,
    toolCount = 0,
    systemPrompt 
  } = data;

  // Get provider display name
  const getProviderDisplay = (provider) => {
    return provider === 'aws_bedrock' ? 'Bedrock' : 
           provider === 'openai' ? 'OpenAI' : 
           provider;
  };

  // Truncate system prompt for display
  const truncatePrompt = (prompt, maxLength = 30) => {
    if (!prompt) return '';
    return prompt.length > maxLength ? prompt.substring(0, maxLength) + '...' : prompt;
  };

  return (
    <div className="agent-node">
      <Handle
        type="target"
        position="left"
        id="input"
        style={{ background: '#d0b0ff' }}
      />
      
      <Handle
        type="target"
        position="top"
        id="llm_input"
        style={{ background: '#9f7aea' }}
      />
      
      <div className="header">
        <div className="title">
          {label || 'Agent'}
          <div className="provider-badge" data-provider={provider}>
            {getProviderDisplay(provider)}
          </div>
        </div>
      </div>
      
      <div className="content">
        <div className="model-info">
          <div className="model-type">
            <span className="agent-type">{agentType}</span>
            <span className="tool-count">{toolCount} tools</span>
          </div>
          
          <div className="model-name">{model.split('.').pop().split('-').slice(0, 2).join(' ')}</div>
          
          <div className="model-params">
            <span>Temp: {temperature}</span>
            <span>Top-P: {topP}</span>
            {topK > 0 && <span>Top-K: {topK}</span>}
          </div>
          
          {systemPrompt && (
            <div className="system-prompt">
              <div className="prompt-label">System prompt:</div>
              <div className="prompt-text">{truncatePrompt(systemPrompt)}</div>
            </div>
          )}
        </div>
      </div>
      
      <Handle
        type="source"
        position="right"
        id="output"
        style={{ background: '#d0b0ff' }}
      />
      
      {/* Tool handles at the bottom */}
      <Handle
        type="source"
        position="bottom"
        id="tool_1"
        style={{ background: '#f6ad55', left: '33%' }}
      />
      
      <Handle
        type="source"
        position="bottom"
        id="tool_2"
        style={{ background: '#63b3ed', left: '67%' }}
      />

      <style jsx>{`
        .agent-node {
          border: 1px solid #d0b0ff;
          border-radius: 8px;
          background-color: #f8f0ff;
          width: 220px;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        .header {
          background-color: #d0b0ff;
          color: #44337a;
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
          gap: 6px;
        }

        .model-type {
          display: flex;
          justify-content: space-between;
          font-size: 12px;
        }

        .agent-type {
          color: #44337a;
          font-weight: 500;
          background-color: #e9d8fd;
          padding: 2px 6px;
          border-radius: 4px;
        }

        .tool-count {
          color: #718096;
          font-weight: 500;
          background-color: #edf2f7;
          padding: 2px 6px;
          border-radius: 4px;
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

        .system-prompt {
          margin-top: 4px;
          border-top: 1px solid #e9d8fd;
          padding-top: 6px;
          font-size: 11px;
        }

        .prompt-label {
          font-weight: 500;
          color: #6b46c1;
          margin-bottom: 3px;
        }

        .prompt-text {
          color: #4a5568;
          word-break: break-word;
          font-size: 11px;
          line-height: 1.4;
        }
      `}</style>
    </div>
  );
};

export default memo(AgentNode);