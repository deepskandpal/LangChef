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

const Playground = () => {
  const [loading, setLoading] = useState(false);
  const [prompts, setPrompts] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [models, setModels] = useState([
    { id: 'gpt-4', name: 'GPT-4', provider: 'openai' },
    { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'openai' },
    { id: 'anthropic.claude-v2', name: 'Claude v2', provider: 'aws_bedrock' },
    { id: 'meta.llama2-70b-chat-v1', name: 'Llama 2 (70B)', provider: 'aws_bedrock' },
  ]);
  
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

  useEffect(() => {
    // Fetch prompts and datasets
    const fetchData = async () => {
      try {
        const promptsResponse = await axios.get('/api/prompts');
        setPrompts(promptsResponse.data);
        
        const datasetsResponse = await axios.get('/api/datasets');
        setDatasets(datasetsResponse.data);
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
      }
    };
    
    fetchData();
  }, []);

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
    
    setLoading(true);
    setError(null);
    setResponse(null);
    setMetrics(null);
    
    try {
      // In a real implementation, this would call your API
      // For now, we'll simulate a response
      
      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 2000));
      
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
      
    } catch (err) {
      console.error('Error running playground:', err);
      setError('Failed to get a response. Please try again.');
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
      'gpt-4': { input: 0.03, output: 0.06 },
      'gpt-3.5-turbo': { input: 0.0015, output: 0.002 },
      'anthropic.claude-v2': { input: 0.008, output: 0.024 },
      'meta.llama2-70b-chat-v1': { input: 0.00195, output: 0.00195 }
    };
    
    const rate = rates[modelId] || rates['gpt-3.5-turbo'];
    
    const inputCost = (usage.prompt_tokens / 1000) * rate.input;
    const outputCost = (usage.completion_tokens / 1000) * rate.output;
    
    return inputCost + outputCost;
  };

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
              >
                {models.map((model) => (
                  <MenuItem key={model.id} value={model.id}>
                    {model.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <Typography gutterBottom>Temperature: {temperature}</Typography>
            <Slider
              value={temperature}
              onChange={(e, newValue) => setTemperature(newValue)}
              min={0}
              max={1}
              step={0.1}
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
              valueLabelDisplay="auto"
              sx={{ mb: 3 }}
            />
            
            <Button 
              variant="contained" 
              fullWidth 
              onClick={handleRun}
              disabled={loading}
            >
              {loading ? <CircularProgress size={24} /> : 'Run'}
            </Button>
          </Paper>
        </Grid>
        
        {/* Input/Output Panel */}
        <Grid item xs={12} md={8}>
          <Grid container spacing={3}>
            {/* Prompt */}
            <Grid item xs={12}>
              <Paper elevation={3} sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Prompt
                </Typography>
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  variant="outlined"
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  placeholder="Enter your prompt here..."
                />
              </Paper>
            </Grid>
            
            {/* Input */}
            <Grid item xs={12}>
              <Paper elevation={3} sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Input
                </Typography>
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  variant="outlined"
                  value={customInput}
                  onChange={(e) => setCustomInput(e.target.value)}
                  placeholder="Enter your input data here..."
                  disabled={selectedDataset !== ''}
                />
              </Paper>
            </Grid>
            
            {/* Response */}
            <Grid item xs={12}>
              <Paper elevation={3} sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Response
                </Typography>
                
                {loading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                    <CircularProgress />
                  </Box>
                ) : response ? (
                  <Box>
                    <Card variant="outlined" sx={{ mb: 2, p: 2, bgcolor: '#f5f5f5' }}>
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
                    </Card>
                    
                    {metrics && (
                      <Box>
                        <Divider sx={{ my: 2 }} />
                        <Typography variant="h6" gutterBottom>
                          Metrics
                        </Typography>
                        <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                          <Chip 
                            label={`Latency: ${metrics.latency_ms.toFixed(0)}ms`} 
                            color="primary" 
                            variant="outlined" 
                          />
                          <Chip 
                            label={`Tokens: ${metrics.tokens.total_tokens}`} 
                            color="primary" 
                            variant="outlined" 
                          />
                          <Chip 
                            label={`Cost: $${metrics.cost.toFixed(4)}`} 
                            color="primary" 
                            variant="outlined" 
                          />
                        </Stack>
                      </Box>
                    )}
                  </Box>
                ) : (
                  <Typography color="text.secondary" sx={{ p: 2 }}>
                    Response will appear here after you run the prompt.
                  </Typography>
                )}
              </Paper>
            </Grid>
          </Grid>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Playground; 