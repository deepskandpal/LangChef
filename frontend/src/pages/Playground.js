import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  TextField, 
  Button, 
  CircularProgress, 
  FormControl, 
  Select, 
  MenuItem,
  Slider,
  Divider,
  Alert,
  Chip,
  Stack,
  IconButton,
  Card,
  CardContent,
  Container,
  AppBar,
  Toolbar,
  Link,
  Paper,
  List,
  ListItem,
  Grid
} from '@mui/material';
import ReactMarkdown from 'react-markdown';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { promptsApi, datasetsApi, modelsApi } from '../services/api';
import SendIcon from '@mui/icons-material/Send';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import HomeIcon from '@mui/icons-material/Home';
import AddIcon from '@mui/icons-material/Add';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { Link as RouterLink } from 'react-router-dom';

// API URL configuration - using the same base URL as in api.js
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Function to determine the model region based on the model ID
const getModelRegion = (modelId) => {
  // Default region for all models unless specified otherwise
  const defaultRegion = 'us-east-1';

  // All Claude models are in us-east-1 for now
  if (modelId && modelId.startsWith('anthropic.claude')) {
    return 'us-east-1';
  }
  
  // Add other model-specific regions as needed
  // Example: if (modelId.startsWith('ai21')) return 'us-west-2';
  
  return defaultRegion;
};

// Helper function to determine if error is related to AWS credentials
const isAwsCredentialError = (errorMessage) => {
  if (!errorMessage) return false;
  return errorMessage.includes('AWS credentials') || 
         errorMessage.includes('Bedrock models') || 
         errorMessage.includes('AWS account');
};

// Helper function to convert regular model IDs to inference profile IDs when needed
const getModelIdWithInferenceProfile = (modelId, region) => {
  // If the model already has a regional prefix (us. or eu.), return it as is
  if (modelId && (modelId.startsWith('us.') || modelId.startsWith('eu.'))) {
    return modelId;
  }
  
  // Specific mappings for models that require inference profiles
  const inferenceProfileMappings = {
    // Claude 3 models
    'anthropic.claude-3-haiku-20240307-v1:0': 'us.anthropic.claude-3-haiku-20240307-v1:0',
    'anthropic.claude-3-sonnet-20240229-v1:0': 'us.anthropic.claude-3-sonnet-20240229-v1:0',
    'anthropic.claude-3-opus-20240229-v1:0': 'us.anthropic.claude-3-opus-20240229-v1:0',
    
    // Claude 3.5 models
    'anthropic.claude-3-5-sonnet-20240620-v1:0': 'us.anthropic.claude-3-5-sonnet-20240620-v1:0',
    'anthropic.claude-3-5-haiku-20241022-v1:0': 'us.anthropic.claude-3-5-haiku-20241022-v1:0',
    
    // Claude 3.7 models
    'anthropic.claude-3-7-sonnet-20250219-v1:0': 'us.anthropic.claude-3-7-sonnet-20250219-v1:0',
    
    // Add more mappings as needed
  };
  
  // For EU regions, use EU inference profiles when available
  if (region && (region.startsWith('eu-'))) {
    const euMappings = {
      'anthropic.claude-3-haiku-20240307-v1:0': 'eu.anthropic.claude-3-haiku-20240307-v1:0',
      'anthropic.claude-3-sonnet-20240229-v1:0': 'eu.anthropic.claude-3-sonnet-20240229-v1:0',
      'anthropic.claude-3-opus-20240229-v1:0': 'eu.anthropic.claude-3-opus-20240229-v1:0',
      'anthropic.claude-3-5-sonnet-20240620-v1:0': 'eu.anthropic.claude-3-5-sonnet-20240620-v1:0',
      'anthropic.claude-3-5-haiku-20241022-v1:0': 'eu.anthropic.claude-3-5-haiku-20241022-v1:0',
      // Add more EU mappings as needed
    };
    
    if (euMappings[modelId]) {
      return euMappings[modelId];
    }
  }
  
  // Return the inference profile ID if a mapping exists, otherwise return the original model ID
  return inferenceProfileMappings[modelId] || modelId;
};

const Playground = () => {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const [loading, setLoading] = useState(false);
  const [prompts, setPrompts] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [selectedPrompt, setSelectedPrompt] = useState('');
  const [selectedDataset, setSelectedDataset] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [inputText, setInputText] = useState('');
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(1000);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState('');
  const [randomnessExpanded, setRandomnessExpanded] = useState(true);
  const [lengthExpanded, setLengthExpanded] = useState(true);
  const [savedItemsExpanded, setSavedItemsExpanded] = useState(true);
  const [showNewPromptForm, setShowNewPromptForm] = useState(false);
  const [newPromptName, setNewPromptName] = useState('');
  
  // Chat history state with localStorage persistence
  const [chatHistory, setChatHistory] = useState(() => {
    const savedHistory = localStorage.getItem('langchef_chat_history');
    if (savedHistory) {
      try {
        // Convert date strings back to Date objects when loading from localStorage
        const parsedHistory = JSON.parse(savedHistory);
        
        // Migrate old format history items to new format if needed
        const migratedHistory = parsedHistory.map(chat => {
          // Convert timestamp to Date object
          const chatWithDateObj = {
            ...chat,
            timestamp: new Date(chat.timestamp)
          };
          
          // Check if messages need migration
          if (chat.messages && chat.messages.length > 0) {
            const migratedMessages = chat.messages.map(message => {
              // If this is a direct API response (old format) without content property
              if (message.text && !message.content) {
                return {
                  content: message.text,
                  response_data: message
                };
              }
              return message;
            });
            
            return {
              ...chatWithDateObj,
              messages: migratedMessages
            };
          }
          
          return chatWithDateObj;
        });
        
        console.log('Loaded and migrated chat history:', migratedHistory);
        return migratedHistory;
      } catch (err) {
        console.error('Error parsing saved chat history:', err);
        return [];
      }
    }
    return [];
  });
  const [activeTab, setActiveTab] = useState('playground'); // 'playground' or 'history'
  const [selectedChatId, setSelectedChatId] = useState(null);

  // Save chat history to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('langchef_chat_history', JSON.stringify(chatHistory));
  }, [chatHistory]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchPrompts();
      fetchDatasets();
      fetchModels();
    }
  }, [isAuthenticated]);

  const fetchPrompts = async () => {
    try {
      const response = await promptsApi.getAll();
      setPrompts(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      console.error('Error fetching prompts:', err);
      setError('Failed to fetch prompts');
      setPrompts([]);
    }
  };

  const fetchDatasets = async () => {
    try {
      const response = await datasetsApi.getAll();
      // Ensure datasets is always an array
      setDatasets(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      console.error('Error fetching datasets:', err);
      setError('Failed to fetch datasets');
      setDatasets([]); // Set to empty array on error
    }
  };

  const fetchModels = async () => {
    try {
      setError(''); // Clear any previous errors
      setLoading(true);
      
      console.log('Fetching models with auth token:', localStorage.getItem('token') ? 'Token present' : 'No token');
      
      const response = await modelsApi.getAvailable();
      
      if (response.data && Array.isArray(response.data) && response.data.length > 0) {
        console.log('Models fetched successfully:', response.data.length);
        
        // Filter to only Claude models in AWS Bedrock
        let claudeModels = response.data.filter(
          model => model.provider === 'aws_bedrock' && model.id.includes('anthropic.claude')
        );
        
        // Deduplicate models by model name (keeping only the first occurrence)
        const seenNames = new Set();
        claudeModels = claudeModels.filter(model => {
          if (seenNames.has(model.name)) {
            console.log(`Skipping duplicate model: ${model.name} (${model.id})`);
            return false;
          }
          seenNames.add(model.name);
          return true;
        });
        
        console.log('Unique Claude models available:', claudeModels.length);
        
        if (claudeModels.length > 0) {
          // Sort models by name
          claudeModels.sort((a, b) => {
            // First sort by family (3.7 > 3.5 > 3 > 2)
            const aFamily = a.name.match(/Claude (\d+(\.\d+)?)/)?.[1] || '0';
            const bFamily = b.name.match(/Claude (\d+(\.\d+)?)/)?.[1] || '0';
            
            if (parseFloat(aFamily) !== parseFloat(bFamily)) {
              return parseFloat(bFamily) - parseFloat(aFamily); // Descending order by version
            }
            
            // Then sort by variant (Opus > Sonnet > Haiku)
            const variantOrder = { "Opus": 3, "Sonnet": 2, "Haiku": 1 };
            const aVariant = a.name.includes("Opus") ? "Opus" : 
                            a.name.includes("Sonnet") ? "Sonnet" : 
                            a.name.includes("Haiku") ? "Haiku" : "";
            const bVariant = b.name.includes("Opus") ? "Opus" : 
                            b.name.includes("Sonnet") ? "Sonnet" : 
                            b.name.includes("Haiku") ? "Haiku" : "";
            
            if (aVariant !== bVariant) {
              return (variantOrder[bVariant] || 0) - (variantOrder[aVariant] || 0);
            }
            
            // Finally, sort by version number (v2 > v1)
            const aVersion = a.name.match(/v(\d+)/)?.[1] || '0';
            const bVersion = b.name.match(/v(\d+)/)?.[1] || '0';
            return parseInt(bVersion) - parseInt(aVersion);
          });
          
          setModels(claudeModels);
          setSelectedModel(claudeModels[0].id);
          return true;
        } else {
          // If we have models but no Claude models
          const uniqueModels = response.data.filter((model, index, self) => {
            return index === self.findIndex(m => m.name === model.name);
          });
          setModels(uniqueModels);
          setSelectedModel(uniqueModels[0].id);
          return true;
        }
      }
      
      // If we get here, either no models or no Claude models
      console.error('No models returned from API');
      setModels([]);
      setError('No models available. Please check your AWS credentials and try again.');
      return false;
    } catch (err) {
      console.error('Error fetching models:', err);
      
      // Check for specific error types
      if (err.response?.status === 401) {
        // Authentication error
        console.error('Authentication error fetching models');
        localStorage.removeItem('token'); // Clear invalid token
        setError('Authentication error. Please log in again.');
        
        // Redirect to login after a short delay
        setTimeout(() => {
          window.location.href = '/login';
        }, 3000);
      } else {
        setError(isAwsCredentialError(err.message || err.response?.data?.detail) ?
          'AWS credentials are missing or invalid. Check your settings.' :
          'Failed to fetch available models. Please try refreshing the page.');
      }
      
      setModels([]);
      return false;
    } finally {
      setLoading(false);
    }
  };

  const handlePromptChange = (event) => {
    const promptId = event.target.value;
    setSelectedPrompt(promptId);
    
    if (promptId) {
      const selectedPrompt = prompts.find(p => p.id === promptId);
      setSystemPrompt(selectedPrompt ? selectedPrompt.text : '');
    } else {
      setSystemPrompt('');
    }
  };

  const handleDatasetChange = (event) => {
    const datasetId = event.target.value;
    setSelectedDataset(datasetId);
    
    if (datasetId) {
      // Here you could load a sample from the dataset
      setInputText('');
    }
  };

  const handleModelChange = (event) => {
    setSelectedModel(event.target.value);
  };

  const handleTemperatureChange = (event, newValue) => {
    setTemperature(newValue);
  };

  const handleMaxTokensChange = (event, newValue) => {
    setMaxTokens(newValue);
  };

  const saveNewPrompt = async () => {
    if (!newPromptName || !systemPrompt) {
      setError('Please provide both a name and content for your prompt');
      return;
    }
    
    try {
      const response = await promptsApi.create({
        name: newPromptName,
        text: systemPrompt
      });
      
      // Refresh the prompts list
      fetchPrompts();
      
      // Set the newly created prompt as selected
      setSelectedPrompt(response.data.id);
      
      // Hide the form
      setShowNewPromptForm(false);
      setNewPromptName('');
    } catch (err) {
      console.error('Error saving prompt:', err);
      setError('Failed to save prompt');
    }
  };

  const saveConversationToHistory = () => {
    if (response) {
      // Find the model info to get the name
      const modelInfo = models.find(m => m.id === selectedModel);
      
      // Ensure the response has text content (might be missing in error cases)
      const responseText = response.text || "No response content from model";
      
      // Create a message object with a content property that contains the response text
      const messageWithContent = {
        content: responseText,
        response_data: response
      };
      
      const newChat = {
        id: Date.now(),
        model: selectedModel,
        modelName: modelInfo?.name || 'Unknown Model',
        timestamp: new Date(),
        messages: [messageWithContent], // Use the formatted message
        config: {
          temperature,
          maxTokens,
          topP: 1.0,
          topK: 1.0
        }
      };
      
      console.log('Saving chat to history:', newChat);
      setChatHistory(prev => [newChat, ...prev]);
    }
  };

  const loadConversationFromHistory = (chatId) => {
    const selectedChat = chatHistory.find(chat => chat.id === chatId);
    if (selectedChat) {
      // Set the conversation details from history
      setInputText('');
      setSelectedModel(selectedChat.model);
      setTemperature(selectedChat.config.temperature);
      setMaxTokens(selectedChat.config.maxTokens);
      
      // If there's a message with content, display it
      if (selectedChat.messages && selectedChat.messages.length > 0) {
        const firstMessage = selectedChat.messages[0];
        
        // Set the response if available
        if (firstMessage.response_data) {
          setResponse(firstMessage.response_data);
        } 
        // Otherwise create a simple response object with the content
        else if (firstMessage.content) {
          setResponse({
            text: firstMessage.content,
            model: selectedChat.model,
            usage: { total_tokens: 0 },
            latency_ms: 0,
            cost: 0
          });
        }
      }
      
      setSelectedChatId(chatId);
      setActiveTab('playground');
    }
  };

  const startNewConversation = () => {
    setInputText('');
    setSelectedChatId(null);
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    setResponse(null);
    const token = localStorage.getItem('token');

    if (!token) {
      setError('Authentication required. Please login.');
      setLoading(false);
      return;
    }

    if (!selectedModel) {
      setError('Please select a model to continue.');
      setLoading(false);
      return;
    }

    try {
      // Find the selected model info
      const modelInfo = models.find(m => m.id === selectedModel);
      if (!modelInfo) {
        setError('Selected model information not found.');
        setLoading(false);
        return;
      }
      
      // Get the region for this model
      const region = getModelRegion(selectedModel);
      
      // Get the appropriate model ID, using inference profiles when needed
      const inferenceProfileModelId = getModelIdWithInferenceProfile(selectedModel, region);
      
      console.log(`Running model: ${modelInfo.name} (${selectedModel})`);
      if (inferenceProfileModelId !== selectedModel) {
        console.log(`Using inference profile: ${inferenceProfileModelId}`);
      }
      
      // Prepare payload for API call
      const payload = {
        prompt: systemPrompt,
        input: inputText,
        model_id: inferenceProfileModelId, // Use the inference profile ID when appropriate
        model_provider: modelInfo.provider,
        temperature: temperature,
        max_tokens: maxTokens,
        region: region
      };
      
      // Try using the modelsApi first
      let response;
      try {
        response = await modelsApi.runPlayground(payload);
        console.log('Model API response:', response.data);
        
        if (response.data) {
          setResponse(response.data);
          // Add to history when successful
          saveConversationToHistory();
        }
      } catch (apiError) {
        console.error('Error using modelsApi, falling back to direct fetch:', apiError);
        
        // Fallback to direct fetch if the modelsApi fails
        const fetchResponse = await fetch(`${API_URL}/api/models/playground/run`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });
        
        const data = await fetchResponse.json();
        
        if (!fetchResponse.ok) {
          throw { response: { data, status: fetchResponse.status } };
        }
        
        console.log('Model fetch response:', data);
        setResponse(data);
        // Add to history when successful
        saveConversationToHistory();
      }
    } catch (error) {
      console.error('Error running model:', error);
      
      // Check for specific validation errors related to on-demand throughput
      if (error.response?.data?.detail && typeof error.response.data.detail === 'string' &&
          error.response.data.detail.includes("on-demand throughput isn't supported")) {
        setError(`This model doesn't support on-demand throughput in the current region. The application will try to use inference profiles in the next request.`);
        
        // Force a refresh of the models
        fetchModels();
      }
      // Handle specific error cases with better messages
      else if (error.response?.data?.detail && typeof error.response.data.detail === 'string') {
        if (error.response.data.detail.includes("BedrockRuntime' object has no attribute 'converse'")) {
          setError('Error: The AWS SDK version in the backend is too old to support Claude 3 models. Please try a different model or contact support to update the AWS SDK.');
        } else if (error.response.data.detail.includes("AWS credentials")) {
          setError(`AWS credentials error: ${error.response.data.detail}. Please re-authenticate with AWS SSO.`);
        } else {
          setError(`Error: ${error.response.data.detail}`);
        }
      } else if (error.response?.status === 401) {
        setError('Authentication error. Please log in again.');
        
        // Check if AWS session expired
        const isAwsExpired = error.response.headers?.['x-aws-session-expired'] === 'true';
        if (isAwsExpired) {
          setError('Your AWS session has expired. Please log in again to refresh your credentials.');
        }
        
        // Redirect to login after a short delay
        setTimeout(() => {
          window.location.href = '/login';
        }, 3000);
      } else {
        setError(`Error: ${error.message || 'Failed to run model. Please try again.'}`);
      }
    } finally {
      setLoading(false);
    }
  };
  
  // Function to format cost as USD
  const formatCost = (cost) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 6,
      maximumFractionDigits: 6
    }).format(cost);
  };

  // Enhanced function to clear all history
  const clearAllHistory = () => {
    if (window.confirm('Are you sure you want to clear all conversation history? This cannot be undone.')) {
      setChatHistory([]);
      localStorage.removeItem('langchef_chat_history');
    }
  };

  if (authLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

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
    <Box sx={{ 
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
    }}>
      {/* Main Content */}
      <Box sx={{ 
        display: 'flex',
        flexGrow: 1,
        overflow: 'hidden'
      }}>
        {/* History Sidebar */}
        <Box sx={{ 
          width: 280, 
          flexShrink: 0, 
          borderRight: '1px solid #e0e0e0',
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'auto',
          backgroundColor: '#f8f8f8'
        }}>
          <Box sx={{ p: 3, borderBottom: '1px solid #e0e0e0' }}>
            <Typography variant="h6" gutterBottom>
              Chat History
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Your previous conversations
            </Typography>
          </Box>
          
          <List sx={{ overflow: 'auto' }}>
            {chatHistory.length > 0 ? (
              chatHistory.map((chat) => (
                <ListItem 
                  key={chat.id} 
                  button 
                  onClick={() => loadConversationFromHistory(chat.id)}
                  selected={selectedChatId === chat.id}
                  sx={{ 
                    borderBottom: '1px solid #eaeaea',
                    '&:hover': { backgroundColor: '#f0f0f0' },
                    backgroundColor: selectedChatId === chat.id ? '#e3f2fd' : 'transparent'
                  }}
                >
                  <Box sx={{ width: '100%' }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 'medium' }}>
                      {chat.messages[0]?.content?.substring(0, 30)}...
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                      Model: {chat.modelName}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {chat.timestamp.toLocaleString()}
                    </Typography>
                  </Box>
                </ListItem>
              ))
            ) : (
              <Box sx={{ p: 3, textAlign: 'center' }}>
                <Typography variant="body2" color="text.secondary">
                  No conversations yet.
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Start chatting to create history.
                </Typography>
              </Box>
            )}
          </List>
          
          <Box sx={{ p: 2, mt: 'auto' }}>
            <Button 
              variant="contained" 
              fullWidth 
              onClick={startNewConversation}
              sx={{ mb: 1 }}
            >
              New Conversation
            </Button>
          </Box>
        </Box>
        
        {/* Fixed Sidebar */}
        <Box sx={{ 
          width: 280, 
          flexShrink: 0, 
          borderRight: '1px solid #e0e0e0',
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'auto'
        }}>
          <Box sx={{ p: 3, borderBottom: '1px solid #e0e0e0' }}>
            <Typography variant="h6" gutterBottom>
              Configurations
            </Typography>
            {error && (
              <Alert 
                severity={isAwsCredentialError(error) ? "warning" : "error"} 
                sx={{ my: 2 }}
                action={
                  isAwsCredentialError(error) && (
                    <Button 
                      color="inherit" 
                      size="small" 
                      component={RouterLink} 
                      to="/settings"
                    >
                      Configure AWS
                    </Button>
                  )
                }
              >
                <Typography variant="body2" gutterBottom>
                  {error}
                </Typography>
                {isAwsCredentialError(error) && (
                  <Typography variant="caption" display="block">
                    To fix this, go to Settings and configure your AWS credentials with access to Bedrock models.
                  </Typography>
                )}
              </Alert>
            )}
          </Box>

          <Box sx={{ p: 3 }}>
            <Typography variant="subtitle1" fontWeight="medium" gutterBottom>
              Model
            </Typography>
            <FormControl fullWidth sx={{ mb: 3 }}>
              <Select
                value={selectedModel}
                onChange={handleModelChange}
                displayEmpty
                size="small"
              >
                <MenuItem value="" disabled>
                  <Typography color="text.secondary">Select a model</Typography>
                </MenuItem>
                {Array.isArray(models) && models.map((model) => (
                  <MenuItem key={model.id} value={model.id}>
                    {model.name || model.id}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <Divider sx={{ my: 2 }} />
            
            {/* Randomness Section */}
            <Box 
              sx={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                mb: 1,
                cursor: 'pointer',
              }}
              onClick={() => setRandomnessExpanded(!randomnessExpanded)}
            >
              <Typography variant="subtitle1" fontWeight="medium">
                Randomness and diversity
              </Typography>
              <IconButton size="small">
                {randomnessExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>
            
            {randomnessExpanded && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Temperature: {temperature}
                </Typography>
                <Slider
                  value={temperature}
                  onChange={handleTemperatureChange}
                  step={0.1}
                  min={0}
                  max={1}
                  valueLabelDisplay="auto"
                  sx={{ 
                    mb: 2,
                    '& .MuiSlider-thumb': {
                      width: 18, 
                      height: 18,
                      backgroundColor: '#1976d2',
                    },
                    '& .MuiSlider-track': {
                      backgroundColor: '#1976d2',
                    },
                    '& .MuiSlider-rail': {
                      opacity: 0.5,
                      backgroundColor: '#bfbfbf',
                    },
                  }}
                />
              </Box>
            )}
            
            <Divider sx={{ my: 2 }} />
            
            {/* Length Section */}
            <Box 
              sx={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                mb: 1,
                cursor: 'pointer',
              }}
              onClick={() => setLengthExpanded(!lengthExpanded)}
            >
              <Typography variant="subtitle1" fontWeight="medium">
                Length
              </Typography>
              <IconButton size="small">
                {lengthExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>
            
            {lengthExpanded && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Max Tokens: {maxTokens}
                </Typography>
                <Slider
                  value={maxTokens}
                  onChange={handleMaxTokensChange}
                  step={100}
                  min={100}
                  max={4000}
                  valueLabelDisplay="auto"
                  sx={{ 
                    mb: 2,
                    '& .MuiSlider-thumb': {
                      width: 18, 
                      height: 18,
                      backgroundColor: '#1976d2',
                    },
                    '& .MuiSlider-track': {
                      backgroundColor: '#1976d2',
                    },
                    '& .MuiSlider-rail': {
                      opacity: 0.5,
                      backgroundColor: '#bfbfbf',
                    },
                  }}
                />
              </Box>
            )}
            
            <Divider sx={{ my: 2 }} />

            {/* Saved Items Section */}
            <Box 
              sx={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                mb: 1,
                cursor: 'pointer',
              }}
              onClick={() => setSavedItemsExpanded(!savedItemsExpanded)}
            >
              <Typography variant="subtitle1" fontWeight="medium">
                Saved Items
              </Typography>
              <IconButton size="small">
                {savedItemsExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>
            
            {savedItemsExpanded && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mt: 2 }}>
                  Prompts
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <FormControl fullWidth sx={{ mr: 1 }}>
                    <Select
                      value={selectedPrompt}
                      onChange={handlePromptChange}
                      displayEmpty
                      size="small"
                    >
                      <MenuItem value="">
                        <Typography color="text.secondary">None</Typography>
                      </MenuItem>
                      {Array.isArray(prompts) && prompts.map((prompt) => (
                        <MenuItem key={prompt.id} value={prompt.id}>
                          {prompt.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <IconButton 
                    size="small" 
                    onClick={() => setShowNewPromptForm(!showNewPromptForm)}
                    sx={{ backgroundColor: '#f0f0f0', '&:hover': { backgroundColor: '#e0e0e0' } }}
                  >
                    <AddIcon fontSize="small" />
                  </IconButton>
                </Box>

                {/* New Prompt Form */}
                {showNewPromptForm && (
                  <Paper elevation={0} sx={{ p: 2, mb: 2, backgroundColor: '#f8f8f8', border: '1px solid #e0e0e0' }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Save Current Prompt
                    </Typography>
                    <TextField
                      fullWidth
                      size="small"
                      label="Prompt Name"
                      value={newPromptName}
                      onChange={(e) => setNewPromptName(e.target.value)}
                      sx={{ mb: 2 }}
                    />
                    <Button 
                      variant="contained" 
                      size="small" 
                      onClick={saveNewPrompt}
                      fullWidth
                    >
                      Save
                    </Button>
                  </Paper>
                )}
                
                <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mt: 2 }}>
                  Datasets
                </Typography>
                <FormControl fullWidth>
              <Select
                value={selectedDataset}
                onChange={handleDatasetChange}
                    displayEmpty
                    size="small"
              >
                <MenuItem value="">
                      <Typography color="text.secondary">None</Typography>
                </MenuItem>
                {Array.isArray(datasets) && datasets.map((dataset) => (
                  <MenuItem key={dataset.id} value={dataset.id}>
                    {dataset.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
              </Box>
            )}
          </Box>
        </Box>
        
        {/* Main Content Area */}
        <Box sx={{ 
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden',
          backgroundColor: '#f9f9f9'
        }}>
          {/* Tab Selection */}
          <Paper elevation={0} sx={{ backgroundColor: 'white' }}>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Box sx={{ display: 'flex', px: 3 }}>
                <Box 
                  onClick={() => setActiveTab('playground')}
                  sx={{ 
                    py: 2, 
                    px: 3, 
                    cursor: 'pointer',
                    borderBottom: activeTab === 'playground' ? '2px solid #1976d2' : '2px solid transparent',
                    color: activeTab === 'playground' ? '#1976d2' : 'inherit',
                    fontWeight: activeTab === 'playground' ? 'medium' : 'normal',
                  }}
                >
                  <Typography>Playground</Typography>
                </Box>
                <Box 
                  onClick={() => setActiveTab('history')}
                  sx={{ 
                    py: 2, 
                    px: 3, 
                    cursor: 'pointer',
                    borderBottom: activeTab === 'history' ? '2px solid #1976d2' : '2px solid transparent',
                    color: activeTab === 'history' ? '#1976d2' : 'inherit',
                    fontWeight: activeTab === 'history' ? 'medium' : 'normal',
                  }}
                >
                  <Typography>History</Typography>
                </Box>
              </Box>
            </Box>
          </Paper>
          
          {/* Removing the duplicate header */}
          {/* Content area */}
          {activeTab === 'playground' ? (
            /* Chat Content Area */
            <Box sx={{ 
              flexGrow: 1, 
              overflow: 'auto',
              p: 4,
              display: 'flex',
              flexDirection: 'column',
            }}>
              {/* System Prompt Section */}
              <Box sx={{ mb: 3 }}>
            <TextField
                  label="System Prompt"
              multiline
                  rows={3}
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
              variant="outlined"
              fullWidth
                  placeholder="Enter a system prompt to guide the model's behavior"
                  sx={{ mb: 2, backgroundColor: 'white' }}
                />
              </Box>
              
              {/* Error display */}
              {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                  {error}
                </Alert>
              )}
              
              {/* Conversation Area */}
              <Box sx={{ flexGrow: 1 }}>
                {/* User Input Card (if submitted) */}
                {inputText && response && (
                  <Card variant="outlined" sx={{ mb: 3, backgroundColor: '#f5f5f5', maxWidth: '80%', alignSelf: 'flex-end', ml: 'auto' }}>
                    <CardContent>
                      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                        User Input
                      </Typography>
                      <Typography variant="body1">
                        {inputText}
                      </Typography>
                    </CardContent>
                  </Card>
                )}
                
                {/* Loading Indicator */}
                {loading && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
                  <CircularProgress />
                </Box>
                )}
                
                {/* Response Card */}
                {response && !loading && (
                  <Card 
                    variant="outlined" 
                    sx={{ 
                      mb: 3, 
                      backgroundColor: 'white', 
                      maxWidth: '80%',
                      boxShadow: '0px 2px 4px rgba(0, 0, 0, 0.05)'
                    }}
                  >
                    <CardContent>
                      <Box sx={{ mb: 2 }}>
                        {response.text && response.text.trim() ? (
                          <ReactMarkdown>
                            {response.text}
                          </ReactMarkdown>
                        ) : (
                          <Typography color="error">
                            No response content was returned from the model. Please try again with a different prompt or model.
                          </Typography>
                        )}
                      </Box>
                  
                      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mt: 2 }}>
                        <Chip 
                          label={`Latency: ${Math.round(response.latency_ms)}ms`} 
                          size="small" 
                          color="default" 
                          variant="outlined" 
                        />
                        <Chip 
                          label={`Tokens: ${response.usage?.total_tokens || 0}`} 
                          size="small" 
                          color="primary" 
                          variant="outlined" 
                        />
                        <Chip 
                          label={`Cost: ${formatCost(response.cost)}`} 
                          size="small"
                          color="success" 
                          variant="outlined" 
                        />
                      </Box>
                    </CardContent>
                  </Card>
                )}
                
                {/* Empty State */}
                {!response && !loading && !error && (
                  <Box sx={{ 
                    display: 'flex', 
                    flexDirection: 'column',
                    justifyContent: 'center', 
                    alignItems: 'center', 
                    height: '100%', 
                    color: 'text.secondary',
                    gap: 2
                  }}>
                    <Alert severity="info" sx={{ width: '100%', maxWidth: 600 }}>
                      <Typography variant="body1">
                        Please enter a prompt or input
                      </Typography>
                    </Alert>
                  </Box>
                )}
              </Box>
            </Box>
          ) : (
            /* History Tab Content */
            <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h5">
                  Conversation History
                </Typography>
                {chatHistory.length > 0 && (
                  <Button 
                    variant="outlined" 
                    color="error" 
                    size="small"
                    onClick={clearAllHistory}
                  >
                    Clear All History
                  </Button>
                )}
              </Box>
              <Typography variant="body2" color="text.secondary" paragraph>
                Your previous conversations with AI models. Click on any conversation to view details.
              </Typography>
              
              {chatHistory.length > 0 ? (
                chatHistory.map((item) => (
                  <Paper 
                    key={item.id} 
                    elevation={1} 
                    sx={{ 
                      p: 3, 
                      mb: 3, 
                      borderRadius: '8px',
                      border: selectedChatId === item.id ? '2px solid #1976d2' : '1px solid #e0e0e0',
                    }}
                  >
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                      <Typography variant="subtitle1" fontWeight="medium">
                        {new Date(item.timestamp).toLocaleString()}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <Button 
                          size="small" 
                          variant="outlined"
                          onClick={() => loadConversationFromHistory(item.id)}
                        >
                          Load
                        </Button>
                        <Button 
                          size="small" 
                          variant="outlined" 
                          color="error"
                          onClick={() => setChatHistory(prev => prev.filter(chat => chat.id !== item.id))}
                        >
                          Delete
                        </Button>
                      </Box>
                    </Box>
                    
                    <Box sx={{ mb: 2, p: 2, bgcolor: '#f5f5f5', borderRadius: '4px' }}>
                      <Typography variant="subtitle2" gutterBottom>
                        Model Configuration
                      </Typography>
                      <Grid container spacing={2}>
                        <Grid item xs={6} sm={3}>
                          <Typography variant="body2" color="text.secondary">
                            Model
                          </Typography>
                          <Typography variant="body2" fontWeight="medium">
                            {item.modelName}
                          </Typography>
                        </Grid>
                        <Grid item xs={6} sm={3}>
                          <Typography variant="body2" color="text.secondary">
                            Temperature
                          </Typography>
                          <Typography variant="body2" fontWeight="medium">
                            {item.config.temperature}
                          </Typography>
                        </Grid>
                        <Grid item xs={6} sm={3}>
                          <Typography variant="body2" color="text.secondary">
                            Max Tokens
                          </Typography>
                          <Typography variant="body2" fontWeight="medium">
                            {item.config.maxTokens}
                          </Typography>
                        </Grid>
                        <Grid item xs={6} sm={3}>
                          <Typography variant="body2" color="text.secondary">
                            Top-P
                          </Typography>
                          <Typography variant="body2" fontWeight="medium">
                            {item.config.topP}
                          </Typography>
                        </Grid>
                      </Grid>
                    </Box>
                    
                    <Typography variant="subtitle2" gutterBottom>
                      Conversation Summary
                    </Typography>
                    <Box sx={{ maxHeight: '200px', overflow: 'auto', mb: 2, p: 2, bgcolor: '#f8f8f8', borderRadius: '4px' }}>
                      {item.messages.length > 0 ? (
                        item.messages.map((message, index) => (
                          <Box key={`${item.id}-msg-${index}`} sx={{ mb: 1 }}>
                            <Typography variant="body2" sx={{ wordBreak: 'break-word' }}>
                              {message.content && typeof message.content === 'string' 
                                ? message.content.substring(0, 150) + (message.content.length > 150 ? '...' : '')
                                : 'No content available'}
                            </Typography>
                          </Box>
                        ))
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          No messages in this conversation
                        </Typography>
                      )}
                    </Box>
                  </Paper>
                ))
              ) : (
                <Box sx={{ p: 5, textAlign: 'center', bgcolor: '#f8f8f8', borderRadius: '8px' }}>
                  <Typography variant="h6" gutterBottom>
                    No conversations yet
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Your conversation history will appear here once you start chatting with AI models.
                  </Typography>
                  <Button 
                    variant="contained" 
                    sx={{ mt: 2 }}
                    onClick={() => {
                      startNewConversation();
                      setActiveTab('playground');
                    }}
                  >
                    Start a new conversation
                  </Button>
                </Box>
              )}
            </Box>
          )}
          
          {/* Input Area */}
          <Box sx={{ 
            p: 3, 
            borderTop: '1px solid #e0e0e0',
            backgroundColor: 'white'
          }}>
            <Container maxWidth="md" disableGutters>
              <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: 2 }}>
                <TextField
                  label="Enter your prompt"
                  multiline
                  rows={1}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  variant="outlined"
                  fullWidth
                  sx={{ flexGrow: 1 }}
                />
                <Button
                  variant="contained"
                  color="primary"
                  onClick={handleSubmit}
                  disabled={loading}
                  endIcon={<SendIcon />}
                  sx={{ height: '56px', minWidth: '100px' }}
                >
                  {loading ? <CircularProgress size={24} /> : 'Send'}
                </Button>
              </Box>
              <Box sx={{ 
                display: 'flex', 
                justifyContent: 'space-between',
                mt: 1
              }}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <IconButton size="small">
                    <AttachFileIcon fontSize="small" />
                  </IconButton>
                  <Typography variant="caption" color="text.secondary">
                    Attach files (optional)
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Selected model: {models.find(m => m.id === selectedModel)?.name || 'None'}
                  </Typography>
                </Box>
              </Box>
            </Container>
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default Playground; 