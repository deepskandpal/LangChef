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
  CircularProgress
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { useNavigate } from 'react-router-dom';
import { promptsApi } from '../services/api';

const Prompts = () => {
  const navigate = useNavigate();
  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [newPrompt, setNewPrompt] = useState({
    name: '',
    description: '',
    template: '',
    type: 'text'
  });

  useEffect(() => {
    fetchPrompts();
  }, []);

  const fetchPrompts = async () => {
    try {
      setLoading(true);
      // Try to fetch from API first
      try {
        const response = await promptsApi.getAll();
        if (response && Array.isArray(response.data)) {
          setPrompts(response.data);
          return;
        }
      } catch (apiError) {
        console.error('API fetch failed, using mock data:', apiError);
      }
      
      // Fallback to mock data
      const mockPrompts = [
        { id: 1, name: 'Customer Support', description: 'Template for customer support responses', type: 'text', createdAt: '2025-03-04T12:00:00Z', updatedAt: '2025-03-04T12:00:00Z' },
        { id: 2, name: 'Product Description', description: 'Template for product descriptions', type: 'text', createdAt: '2025-03-04T12:00:00Z', updatedAt: '2025-03-04T12:00:00Z' },
        { id: 3, name: 'Code Generation', description: 'Template for generating code', type: 'code', createdAt: '2025-03-04T12:00:00Z', updatedAt: '2025-03-04T12:00:00Z' },
      ];
      setPrompts(mockPrompts);
    } catch (error) {
      console.error('Error fetching prompts:', error);
      setPrompts([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePrompt = async () => {
    try {
      // In a real app, you would use: await api.prompts.create(newPrompt);
      console.log('Creating prompt:', newPrompt);
      setOpenDialog(false);
      // Refresh the list
      fetchPrompts();
      // Reset form
      setNewPrompt({
        name: '',
        description: '',
        template: '',
        type: 'text'
      });
    } catch (error) {
      console.error('Error creating prompt:', error);
    }
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    { field: 'name', headerName: 'Name', width: 200 },
    { field: 'description', headerName: 'Description', width: 300 },
    { field: 'type', headerName: 'Type', width: 120 },
    { field: 'createdAt', headerName: 'Created', width: 180, valueFormatter: (params) => new Date(params.value).toLocaleString() },
    { field: 'updatedAt', headerName: 'Updated', width: 180, valueFormatter: (params) => new Date(params.value).toLocaleString() },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 120,
      renderCell: (params) => (
        <Button 
          variant="contained" 
          size="small" 
          onClick={() => navigate(`/prompts/${params.row.id}`)}
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
          Prompts
        </Typography>
        <Button 
          variant="contained" 
          color="primary" 
          onClick={() => setOpenDialog(true)}
        >
          Create Prompt
        </Button>
      </Box>

      <Paper sx={{ width: '100%', overflow: 'hidden' }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        ) : (
          <DataGrid
            rows={prompts}
            columns={columns}
            pageSize={10}
            rowsPerPageOptions={[10]}
            autoHeight
            disableSelectionOnClick
          />
        )}
      </Paper>

      {/* Create Prompt Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Create New Prompt</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Name"
              value={newPrompt.name}
              onChange={(e) => setNewPrompt({ ...newPrompt, name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Description"
              value={newPrompt.description}
              onChange={(e) => setNewPrompt({ ...newPrompt, description: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
            <FormControl fullWidth>
              <InputLabel>Type</InputLabel>
              <Select
                value={newPrompt.type}
                label="Type"
                onChange={(e) => setNewPrompt({ ...newPrompt, type: e.target.value })}
              >
                <MenuItem value="text">Text</MenuItem>
                <MenuItem value="code">Code</MenuItem>
                <MenuItem value="chat">Chat</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="Template"
              value={newPrompt.template}
              onChange={(e) => setNewPrompt({ ...newPrompt, template: e.target.value })}
              fullWidth
              multiline
              rows={6}
              placeholder="Enter your prompt template here..."
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button 
            onClick={handleCreatePrompt} 
            variant="contained" 
            color="primary"
            disabled={!newPrompt.name || !newPrompt.template}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Prompts; 