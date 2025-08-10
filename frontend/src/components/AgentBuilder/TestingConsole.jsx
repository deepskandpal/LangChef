import React, { useState } from 'react';

const TestingConsole = ({ onRunTest }) => {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleTest = async () => {
    if (!input.trim()) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await onRunTest(input);
      setResult(response);
    } catch (err) {
      setError(err.message || 'An error occurred during testing');
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="testing-console">
      <h3>Testing Console</h3>
      
      <div className="input-section">
        <textarea
          placeholder="Enter a test input for your agent..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isLoading}
        ></textarea>
        
        <button 
          onClick={handleTest}
          disabled={isLoading || !input.trim()}
        >
          {isLoading ? 'Running...' : 'Run Test'}
        </button>
      </div>
      
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}
      
      {result && (
        <div className="result-section">
          <h4>Result</h4>
          <div className="result-content">
            {result.content}
          </div>
        </div>
      )}
      
      <style jsx>{`
        .testing-console {
          padding: 1rem;
          height: 50%;
          display: flex;
          flex-direction: column;
          border-top: 1px solid #e2e8f0;
        }
        
        h3 {
          margin-top: 0;
          margin-bottom: 1rem;
          font-size: 1.2rem;
          font-weight: 600;
        }
        
        .input-section {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          margin-bottom: 1rem;
        }
        
        textarea {
          padding: 0.75rem;
          border: 1px solid #e2e8f0;
          border-radius: 4px;
          resize: none;
          min-height: 80px;
          font-size: 0.9rem;
        }
        
        button {
          padding: 0.75rem;
          background-color: #4a90e2;
          color: white;
          border: none;
          border-radius: 4px;
          font-weight: 500;
          cursor: pointer;
          transition: background-color 0.2s;
        }
        
        button:hover:not(:disabled) {
          background-color: #3a80d2;
        }
        
        button:disabled {
          background-color: #cbd5e0;
          cursor: not-allowed;
        }
        
        .error-message {
          padding: 0.75rem;
          background-color: #fff5f5;
          border: 1px solid #feb2b2;
          border-radius: 4px;
          color: #c53030;
          font-size: 0.9rem;
          margin-bottom: 1rem;
        }
        
        .result-section {
          flex: 1;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        
        h4 {
          margin-top: 0;
          margin-bottom: 0.5rem;
          font-size: 1rem;
          font-weight: 500;
        }
        
        .result-content {
          padding: 0.75rem;
          background-color: #f7fafc;
          border: 1px solid #e2e8f0;
          border-radius: 4px;
          overflow-y: auto;
          flex: 1;
          font-size: 0.9rem;
          white-space: pre-wrap;
        }
      `}</style>
    </div>
  );
};

export default TestingConsole; 