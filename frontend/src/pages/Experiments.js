import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  Paper, 
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Chip
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';

const Experiments = () => {
  const navigate = useNavigate();
  const [experiments, setExperiments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [prompts, setPrompts] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [newExperiment, setNewExperiment] = useState({
    name: '',
    description: '',
    promptId: '',
    datasetId: '',
    parameters: JSON.stringify({
      temperature: 0.7,
      max_tokens: 100,
      top_p: 1.0
    }, null, 2)
  });

  useEffect(() => {
    fetchExperiments();
    fetchPromptsAndDatasets();
  }, []);

  const fetchExperiments = async () => {
    try {
      setLoading(true);
      // For now, use mock data since the backend might not be fully set up
      // In a real app, you would use: const response = await api.experiments.getAll();
      const mockExperiments = [
        { 
          id: 1, 
          name: 'Customer Support Test', 
          description: 'Testing customer support prompt with queries', 
          status: 'completed', 
          promptId: 1,
          promptName: 'Customer Support',
          datasetId: 1,
          datasetName: 'Customer Queries',
          runCount: 120,
          createdAt: '2025-03-04T12:00:00Z', 
          updatedAt: '2025-03-04T14:00:00Z' 
        },
        { 
          id: 2, 
          name: 'Product Description Generation', 
          description: 'Generating product descriptions from specs', 
          status: 'running', 
          promptId: 2,
          promptName: 'Product Description',
          datasetId: 2,
          datasetName: 'Product Specifications',
          runCount: 50,
          createdAt: '2025-03-04T13:00:00Z', 
          updatedAt: '2025-03-04T13:30:00Z' 
        },
        { 
          id: 3, 
          name: 'Code Generation Experiment', 
          description: 'Testing code generation capabilities', 
          status: 'failed', 
          promptId: 3,
          promptName: 'Code Generation',
          datasetId: 3,
          datasetName: 'Code Samples',
          runCount: 75,
          createdAt: '2025-03-04T11:00:00Z', 
          updatedAt: '2025-03-04T11:45:00Z' 
        },
      ];
      setExperiments(mockExperiments);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching experiments:', error);
      setLoading(false);
    }
  };

  const fetchPromptsAndDatasets = async () => {
    try {
      // For now, use mock data since the backend might not be fully set up
      // In a real app, you would use: 
      // const promptsData = await api.prompts.getAll();
      // const datasetsData = await api.datasets.getAll();
      
      const mockPrompts = [
        { id: 1, name: 'Customer Support' },
        { id: 2, name: 'Product Description' },
        { id: 3, name: 'Code Generation' },
      ];
      
      const mockDatasets = [
        { id: 1, name: 'Customer Queries' },
        { id: 2, name: 'Product Specifications' },
        { id: 3, name: 'Code Samples' },
      ];
      
      setPrompts(mockPrompts);
      setDatasets(mockDatasets);
    } catch (error) {
      console.error('Error fetching prompts and datasets:', error);
    }
  };

  const handleCreateExperiment = async () => {
    try {
      // In a real app, you would use: await api.experiments.create(newExperiment);
      console.log('Creating experiment:', newExperiment);
      setOpenDialog(false);
      // Refresh the list
      fetchExperiments();
      // Reset form
      setNewExperiment({
        name: '',
        description: '',
        promptId: '',
        datasetId: '',
        parameters: JSON.stringify({
          temperature: 0.7,
          max_tokens: 100,
          top_p: 1.0
        }, null, 2)
      });
    } catch (error) {
      console.error('Error creating experiment:', error);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'running':
        return 'primary';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    { field: 'name', headerName: 'Name', width: 200 },
    { field: 'description', headerName: 'Description', width: 250 },
    { 
      field: 'status', 
      headerName: 'Status', 
      width: 120,
      renderCell: (params) => (
        <Chip 
          label={params.value} 
          color={getStatusColor(params.value)} 
          size="small" 
        />
      ),
    },
    { field: 'promptName', headerName: 'Prompt', width: 150 },
    { field: 'datasetName', headerName: 'Dataset', width: 150 },
    { field: 'runCount', headerName: 'Runs', width: 80, type: 'number' },
    { field: 'createdAt', headerName: 'Created', width: 180, valueFormatter: (params) => new Date(params.value).toLocaleString() },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 120,
      renderCell: (params) => (
        <Button 
          variant="contained" 
          size="small" 
          onClick={() => navigate(`/experiments/${params.row.id}`)}
        >
          View
        </Button>
      ),
    },
  ];

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Experiments
        </Typography>
        <Button 
          variant="contained" 
          color="primary" 
          onClick={() => setOpenDialog(true)}
        >
          Create Experiment
        </Button>
      </Box>

      <Paper sx={{ width: '100%', overflow: 'hidden' }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        ) : (
          <DataGrid
            rows={experiments}
            columns={columns}
            pageSize={10}
            rowsPerPageOptions={[10]}
            autoHeight
            disableSelectionOnClick
          />
        )}
      </Paper>

      {/* Create Experiment Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Create New Experiment</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Name"
              value={newExperiment.name}
              onChange={(e) => setNewExperiment({ ...newExperiment, name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Description"
              value={newExperiment.description}
              onChange={(e) => setNewExperiment({ ...newExperiment, description: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
            <FormControl fullWidth required>
              <InputLabel>Prompt</InputLabel>
              <Select
                value={newExperiment.promptId}
                label="Prompt"
                onChange={(e) => setNewExperiment({ ...newExperiment, promptId: e.target.value })}
              >
                {prompts.map((prompt) => (
                  <MenuItem key={prompt.id} value={prompt.id}>{prompt.name}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth required>
              <InputLabel>Dataset</InputLabel>
              <Select
                value={newExperiment.datasetId}
                label="Dataset"
                onChange={(e) => setNewExperiment({ ...newExperiment, datasetId: e.target.value })}
              >
                {datasets.map((dataset) => (
                  <MenuItem key={dataset.id} value={dataset.id}>{dataset.name}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              label="Parameters (JSON)"
              value={newExperiment.parameters}
              onChange={(e) => setNewExperiment({ ...newExperiment, parameters: e.target.value })}
              fullWidth
              multiline
              rows={6}
              placeholder='{"temperature": 0.7, "max_tokens": 100}'
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button 
            onClick={handleCreateExperiment} 
            variant="contained" 
            color="primary"
            disabled={!newExperiment.name || !newExperiment.promptId || !newExperiment.datasetId}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Experiments; 