import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Card, 
  CardContent, 
  Grid, 
  Chip, 
  CircularProgress,
  Paper,
  Divider,
  Alert
} from '@mui/material';
import axios from 'axios';

const Models = () => {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        setLoading(true);
        const response = await axios.get('/api/models/available');
        if (response.data && Array.isArray(response.data)) {
          setModels(response.data);
        } else {
          throw new Error('Invalid response format');
        }
        setError(null);
      } catch (err) {
        console.error('Error fetching models:', err);
        setError('Failed to load models. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchModels();
  }, []);

  // Group models by provider
  const groupedModels = models.reduce((acc, model) => {
    const provider = model.provider || 'other';
    if (!acc[provider]) {
      acc[provider] = [];
    }
    acc[provider].push(model);
    return acc;
  }, {});

  // Display name mapping for providers
  const providerDisplayNames = {
    'aws_bedrock': 'AWS Bedrock',
    'openai': 'OpenAI',
    'anthropic': 'Anthropic',
    'cohere': 'Cohere',
    'other': 'Other Providers'
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Available Models
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}
      
      {Object.keys(groupedModels).length === 0 && !loading && !error && (
        <Alert severity="info">
          No models available. Please check your AWS credentials or API configuration.
        </Alert>
      )}
      
      {Object.entries(groupedModels).map(([provider, providerModels]) => (
        <Box key={provider} sx={{ mb: 4 }}>
          <Paper sx={{ p: 2, mb: 2, bgcolor: 'background.paper' }}>
            <Typography variant="h5" gutterBottom>
              {providerDisplayNames[provider] || provider}
              <Chip 
                label={`${providerModels.length} ${providerModels.length === 1 ? 'model' : 'models'}`} 
                size="small" 
                sx={{ ml: 2 }} 
              />
            </Typography>
            <Divider sx={{ mb: 2 }} />
            
            <Grid container spacing={3}>
              {providerModels.map((model) => (
                <Grid item xs={12} sm={6} md={4} key={model.id}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        {model.name}
                        {model.unverified && (
                          <Chip 
                            label="Unverified" 
                            size="small" 
                            color="warning" 
                            sx={{ ml: 1 }} 
                          />
                        )}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        {model.description || `${model.id} model from ${providerDisplayNames[provider] || provider}`}
                      </Typography>
                      <Box sx={{ mt: 2 }}>
                        <Chip label={`ID: ${model.id}`} size="small" sx={{ mr: 1, mb: 1 }} />
                        {model.supported_features && model.supported_features.map(feature => (
                          <Chip 
                            key={feature} 
                            label={feature} 
                            size="small" 
                            color="primary" 
                            variant="outlined" 
                            sx={{ mr: 1, mb: 1 }} 
                          />
                        ))}
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Paper>
        </Box>
      ))}
    </Box>
  );
};

export default Models; 