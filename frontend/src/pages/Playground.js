import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Grid, 
  Paper, 
  TextField, 
  Button, 
  FormControl, 
  InputLabel, 
  Select, 
  MenuItem,
  Slider,
  CircularProgress,
  Card,
  CardContent,
  Divider,
  Chip,
  Stack,
  Alert
} from '@mui/material';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { materialDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

const Playground = () => {
  const { isAuthenticated, user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [prompts, setPrompts] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [models, setModels] = useState([]);
  const [loadingModels, setLoadingModels] = useState(true);
  
  const [selectedPrompt, setSelectedPrompt] = useState('');
  const [selectedDataset, setSelectedDataset] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [customPrompt, setCustomPrompt] = useState('');
  const [customInput, setCustomInput] = useState('');
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(1000);
  
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);
  const [metrics, setMetrics] = useState(null);

  // Check authentication
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    // Fetch prompts, datasets, and available models
    const fetchData = async () => {
      try {
        // Fetch prompts and datasets
        const promptsResponse = await axios.get('/api/prompts');
        setPrompts(promptsResponse.data);
        
        const datasetsResponse = await axios.get('/api/datasets');
        setDatasets(datasetsResponse.data);
        
        // Fetch available models
        setLoadingModels(true);
        try {
          const modelsResponse = await axios.get('/api/models/available');
          if (modelsResponse.data && Array.isArray(modelsResponse.data)) {
            setModels(modelsResponse.data);
            
            // Auto-select the first AWS Bedrock model if available
            const bedrockModels = modelsResponse.data.filter(m => m.provider === 'aws_bedrock');
            if (bedrockModels.length > 0 && !selectedModel) {
              setSelectedModel(bedrockModels[0].id);
            }
          } else {
            // Fallback to default models if API doesn't return expected format
            const defaultModels = getDefaultModels();
            setModels(defaultModels);
            
            // Auto-select the first AWS Bedrock model
            const bedrockModels = defaultModels.filter(m => m.provider === 'aws_bedrock');
            if (bedrockModels.length > 0 && !selectedModel) {
              setSelectedModel(bedrockModels[0].id);
            }
          }
        } catch (modelError) {
          console.error('Error fetching models:', modelError);
          // Fallback to default models
          const defaultModels = getDefaultModels();
          setModels(defaultModels);
          
          // Auto-select the first AWS Bedrock model
          const bedrockModels = defaultModels.filter(m => m.provider === 'aws_bedrock');
          if (bedrockModels.length > 0 && !selectedModel) {
            setSelectedModel(bedrockModels[0].id);
          }
        } finally {
          setLoadingModels(false);
        }
      } catch (err) {
        console.error('Error fetching data:', err);
        setError('Failed to load prompts and datasets. Using mock data instead.');
        
        // Mock data
        setPrompts([
          { id: 1, name: 'General Q&A', content: 'Answer the following question accurately and concisely.' },
          { id: 2, name: 'Text Summarization', content: 'Summarize the following text in 3-5 sentences.' },
          { id: 3, name: 'Code Generation', content: 'Generate code based on the following requirements.' }
        ]);
        
        setDatasets([
          { id: 1, name: 'Sample Questions', type: 'json' },
          { id: 2, name: 'News Articles', type: 'text' },
          { id: 3, name: 'Programming Tasks', type: 'json' }
        ]);
        
        // Set default models
        const defaultModels = getDefaultModels();
        setModels(defaultModels);
        
        // Auto-select the first AWS Bedrock model
        const bedrockModels = defaultModels.filter(m => m.provider === 'aws_bedrock');
        if (bedrockModels.length > 0 && !selectedModel) {
          setSelectedModel(bedrockModels[0].id);
        }
        
        setLoadingModels(false);
      }
    };
    
    if (isAuthenticated) {
      fetchData();
    }
  }, [isAuthenticated, selectedModel]);
  
  // Function to get default models if API call fails
  const getDefaultModels = () => {
    return [
      // Claude models available in AWS Bedrock
      { id: 'anthropic.claude-3-sonnet-20240229-v1:0', name: 'Claude 3 Sonnet', provider: 'aws_bedrock', regions: ['us-east-1', 'us-west-2', 'ap-northeast-1', 'ap-southeast-2', 'eu-central-1'] },
      { id: 'anthropic.claude-3-haiku-20240307-v1:0', name: 'Claude 3 Haiku', provider: 'aws_bedrock', regions: ['us-east-1', 'us-west-2', 'ap-northeast-1', 'ap-southeast-2', 'eu-central-1'] },
      { id: 'anthropic.claude-3-opus-20240229-v1:0', name: 'Claude 3 Opus', provider: 'aws_bedrock', regions: ['us-east-1', 'us-west-2'] },
      { id: 'anthropic.claude-instant-v1', name: 'Claude Instant v1', provider: 'aws_bedrock', regions: ['us-east-1', 'us-west-2', 'ap-northeast-1', 'eu-central-1'] },
      { id: 'anthropic.claude-v2', name: 'Claude v2', provider: 'aws_bedrock', regions: ['us-east-1', 'us-west-2', 'ap-northeast-1', 'eu-central-1'] },
      { id: 'anthropic.claude-v2:1', name: 'Claude v2.1', provider: 'aws_bedrock', regions: ['us-east-1', 'us-west-2', 'ap-northeast-1', 'eu-central-1'] },
      
      // Other popular models
      { id: 'meta.llama2-70b-chat-v1', name: 'Llama 2 (70B)', provider: 'aws_bedrock', regions: ['us-east-1', 'us-west-2', 'ap-northeast-1', 'eu-central-1'] },
      { id: 'meta.llama3-70b-instruct-v1:0', name: 'Llama 3 (70B)', provider: 'aws_bedrock', regions: ['us-east-1', 'us-west-2'] },
      { id: 'mistral.mistral-7b-instruct-v0:2', name: 'Mistral 7B', provider: 'aws_bedrock', regions: ['us-east-1', 'us-west-2', 'ap-northeast-1', 'eu-central-1'] },
      { id: 'mistral.mixtral-8x7b-instruct-v0:1', name: 'Mixtral 8x7B', provider: 'aws_bedrock', regions: ['us-east-1', 'us-west-2'] },
      
      // OpenAI models (for comparison)
      { id: 'gpt-4o', name: 'GPT-4o', provider: 'openai' },
      { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', provider: 'openai' },
      { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'openai' },
    ];
  };

  const handlePromptChange = (event) => {
    const promptId = event.target.value;
    setSelectedPrompt(promptId);
    
    if (promptId) {
      const prompt = prompts.find(p => p.id === promptId);
      if (prompt) {
        setCustomPrompt(prompt.content);
      }
    }
  };

  const handleDatasetChange = (event) => {
    setSelectedDataset(event.target.value);
  };

  const handleModelChange = (event) => {
    setSelectedModel(event.target.value);
  };

  const handleRun = async () => {
    if (!customPrompt.trim()) {
      setError('Please enter a prompt');
      return;
    }
    
    if (!selectedModel) {
      setError('Please select a model');
      return;
    }
    
    setLoading(true);
    setError(null);
    setResponse(null);
    setMetrics(null);
    
    try {
      // In a real implementation, this would call your API
      const selectedModelObj = models.find(m => m.id === selectedModel);
      
      if (!selectedModelObj) {
        throw new Error('Please select a model');
      }
      
      // Call the API to run the model
      const response = await axios.post('/api/models/playground/run', {
        prompt: customPrompt,
        input: customInput,
        model_id: selectedModelObj.id,
        model_provider: selectedModelObj.provider,
        temperature: temperature,
        max_tokens: maxTokens
      });
      
      if (response.data) {
        setResponse(response.data);
        
        // Set metrics if available
        if (response.data.metrics) {
          setMetrics(response.data.metrics);
        } else {
          // Create default metrics
          setMetrics({
            latency_ms: response.data.latency_ms || 0,
            tokens: response.data.usage || {
              prompt_tokens: 0,
              completion_tokens: 0,
              total_tokens: 0
            },
            cost: response.data.cost || 0
          });
        }
      }
    } catch (err) {
      console.error('Error running playground:', err);
      setError(err.response?.data?.detail || 'Failed to get a response. Please try again.');
      
      if (err.response?.status === 401) {
        // Authentication error - redirect to login
        navigate('/login');
        return;
      }
      
      // Fallback to mock response for demo purposes
      const selectedModelObj = models.find(m => m.id === selectedModel) || models[0];
      
      // Mock response
      const mockResponse = {
        text: generateMockResponse(customPrompt, customInput, selectedModelObj.name),
        model: selectedModelObj.id,
        usage: {
          prompt_tokens: customPrompt.length / 4 + customInput.length / 4,
          completion_tokens: 150,
          total_tokens: customPrompt.length / 4 + customInput.length / 4 + 150
        }
      };
      
      setResponse(mockResponse);
      
      // Mock metrics
      setMetrics({
        latency_ms: Math.floor(Math.random() * 1000) + 500,
        tokens: mockResponse.usage,
        cost: calculateMockCost(mockResponse.usage, selectedModelObj.id)
      });
    } finally {
      setLoading(false);
    }
  };
  
  // Helper function to generate mock responses
  const generateMockResponse = (prompt, input, model) => {
    if (prompt.includes('summarize') || prompt.includes('Summarize')) {
      return "This is a summarized version of the input text. The key points include the main arguments, supporting evidence, and conclusions. The summary maintains the original meaning while being concise and focused on the most important information.";
    } else if (prompt.includes('code') || prompt.includes('Code')) {
      return "```python\ndef calculate_fibonacci(n):\n    if n <= 0:\n        return 0\n    elif n == 1:\n        return 1\n    else:\n        return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)\n\n# Example usage\nresult = calculate_fibonacci(10)\nprint(f\"The 10th Fibonacci number is: {result}\")\n```";
    } else {
      return "This is a response generated by the " + model + " model based on your prompt and input. In a real implementation, this would be the actual response from the LLM API. The response would be more relevant to your specific prompt and input data.";
    }
  };
  
  // Helper function to calculate mock cost
  const calculateMockCost = (usage, modelId) => {
    const rates = {
      // Claude models
      'anthropic.claude-3-sonnet-20240229-v1:0': { input: 0.003, output: 0.015 },
      'anthropic.claude-3-haiku-20240307-v1:0': { input: 0.00025, output: 0.00125 },
      'anthropic.claude-3-opus-20240229-v1:0': { input: 0.015, output: 0.075 },
      'anthropic.claude-instant-v1': { input: 0.0008, output: 0.0024 },
      'anthropic.claude-v2': { input: 0.008, output: 0.024 },
      'anthropic.claude-v2:1': { input: 0.008, output: 0.024 },
      
      // Other models
      'meta.llama2-70b-chat-v1': { input: 0.00195, output: 0.00195 },
      'meta.llama3-70b-instruct-v1:0': { input: 0.00195, output: 0.00195 },
      'mistral.mistral-7b-instruct-v0:2': { input: 0.0002, output: 0.0002 },
      'mistral.mixtral-8x7b-instruct-v0:1': { input: 0.0007, output: 0.0007 },
      
      // OpenAI models
      'gpt-4o': { input: 0.005, output: 0.015 },
      'gpt-4-turbo': { input: 0.01, output: 0.03 },
      'gpt-3.5-turbo': { input: 0.0005, output: 0.0015 },
    };
    
    const rate = rates[modelId] || rates['gpt-3.5-turbo'];
    
    const inputCost = (usage.prompt_tokens / 1000) * rate.input;
    const outputCost = (usage.completion_tokens / 1000) * rate.output;
    
    return inputCost + outputCost;
  };

  // Group models by provider for the dropdown
  const groupedModels = models.reduce((acc, model) => {
    if (!acc[model.provider]) {
      acc[model.provider] = [];
    }
    acc[model.provider].push(model);
    return acc;
  }, {});

  if (!isAuthenticated) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning">
          Please log in to access the Playground.
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Playground
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}
      
      <Grid container spacing={3}>
        {/* Configuration Panel */}
        <Grid item xs={12} md={4}>
          <Paper elevation={3} sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Configuration
            </Typography>
            
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Saved Prompt</InputLabel>
              <Select
                value={selectedPrompt}
                label="Saved Prompt"
                onChange={handlePromptChange}
              >
                <MenuItem value="">
                  <em>None (Custom)</em>
                </MenuItem>
                {prompts.map((prompt) => (
                  <MenuItem key={prompt.id} value={prompt.id}>
                    {prompt.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Dataset</InputLabel>
              <Select
                value={selectedDataset}
                label="Dataset"
                onChange={handleDatasetChange}
              >
                <MenuItem value="">
                  <em>None (Custom Input)</em>
                </MenuItem>
                {datasets.map((dataset) => (
                  <MenuItem key={dataset.id} value={dataset.id}>
                    {dataset.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>Model</InputLabel>
              <Select
                value={selectedModel}
                label="Model"
                onChange={handleModelChange}
                disabled={loadingModels}
              >
                {loadingModels ? (
                  <MenuItem value="">
                    <em>Loading models...</em>
                  </MenuItem>
                ) : (
                  Object.entries(groupedModels).map(([provider, providerModels]) => [
                    <MenuItem key={provider} disabled divider>
                      {provider === 'aws_bedrock' ? 'AWS Bedrock' : 
                       provider === 'openai' ? 'OpenAI' : 
                       provider}
                    </MenuItem>,
                    ...providerModels.map((model) => (
                      <MenuItem key={model.id} value={model.id}>
                        {model.name}
                        {model.regions && model.provider === 'aws_bedrock' && (
                          <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                            ({model.regions.length} regions)
                          </Typography>
                        )}
                      </MenuItem>
                    ))
                  ]).flat()
                )}
              </Select>
            </FormControl>
            
            <Typography gutterBottom>Temperature: {temperature}</Typography>
            <Slider
              value={temperature}
              onChange={(e, newValue) => setTemperature(newValue)}
              min={0}
              max={1}
              step={0.1}
              marks
              valueLabelDisplay="auto"
              sx={{ mb: 3 }}
            />
            
            <Typography gutterBottom>Max Tokens: {maxTokens}</Typography>
            <Slider
              value={maxTokens}
              onChange={(e, newValue) => setMaxTokens(newValue)}
              min={100}
              max={4000}
              step={100}
              marks
              valueLabelDisplay="auto"
              sx={{ mb: 3 }}
            />
            
            <Button 
              variant="contained" 
              color="primary" 
              fullWidth 
              onClick={handleRun}
              disabled={loading || !selectedModel}
            >
              {loading ? <CircularProgress size={24} /> : 'Run'}
            </Button>
          </Paper>
        </Grid>
        
        {/* Prompt and Input */}
        <Grid item xs={12} md={8}>
          <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Prompt
            </Typography>
            <TextField
              fullWidth
              multiline
              rows={4}
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              placeholder="Enter your prompt here..."
              variant="outlined"
              sx={{ mb: 3 }}
            />
            
            <Typography variant="h6" gutterBottom>
              Input
            </Typography>
            <TextField
              fullWidth
              multiline
              rows={4}
              value={customInput}
              onChange={(e) => setCustomInput(e.target.value)}
              placeholder="Enter your input data here..."
              variant="outlined"
            />
          </Paper>
          
          {/* Response */}
          {(response || loading) && (
            <Paper elevation={3} sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Response
              </Typography>
              
              {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                  <CircularProgress />
                </Box>
              ) : (
                <>
                  <Box sx={{ mb: 2, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                    <ReactMarkdown
                      components={{
                        code({node, inline, className, children, ...props}) {
                          const match = /language-(\w+)/.exec(className || '')
                          return !inline && match ? (
                            <SyntaxHighlighter
                              style={materialDark}
                              language={match[1]}
                              PreTag="div"
                              {...props}
                            >
                              {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
                          ) : (
                            <code className={className} {...props}>
                              {children}
                            </code>
                          )
                        }
                      }}
                    >
                      {response.text}
                    </ReactMarkdown>
                  </Box>
                  
                  {metrics && (
                    <Box>
                      <Divider sx={{ my: 2 }} />
                      <Typography variant="subtitle2" gutterBottom>
                        Metrics
                      </Typography>
                      <Stack direction="row" spacing={2} sx={{ mb: 1 }}>
                        <Chip 
                          label={`Model: ${response.model}`} 
                          variant="outlined" 
                          color="primary"
                        />
                        <Chip 
                          label={`Latency: ${metrics.latency_ms}ms`} 
                          variant="outlined" 
                        />
                        <Chip 
                          label={`Cost: $${metrics.cost.toFixed(6)}`} 
                          variant="outlined" 
                          color="secondary"
                        />
                      </Stack>
                      <Stack direction="row" spacing={2}>
                        <Chip 
                          label={`Input Tokens: ${metrics.tokens.prompt_tokens}`} 
                          variant="outlined" 
                          size="small"
                        />
                        <Chip 
                          label={`Output Tokens: ${metrics.tokens.completion_tokens}`} 
                          variant="outlined" 
                          size="small"
                        />
                        <Chip 
                          label={`Total Tokens: ${metrics.tokens.total_tokens}`} 
                          variant="outlined" 
                          size="small"
                        />
                      </Stack>
                    </Box>
                  )}
                </>
              )}
            </Paper>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default Playground; 