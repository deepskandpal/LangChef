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
import { api } from '../services/api';

const Datasets = () => {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [newDataset, setNewDataset] = useState({
    name: '',
    description: '',
    type: 'text'
  });

  useEffect(() => {
    fetchDatasets();
  }, []);

  const fetchDatasets = async () => {
    try {
      setLoading(true);
      // For now, use mock data since the backend might not be fully set up
      // In a real app, you would use: const response = await api.datasets.getAll();
      const mockDatasets = [
        { id: 1, name: 'Customer Queries', description: 'Collection of customer support queries', type: 'text', itemCount: 120, createdAt: '2025-03-04T12:00:00Z', updatedAt: '2025-03-04T12:00:00Z' },
        { id: 2, name: 'Product Descriptions', description: 'Product descriptions for e-commerce', type: 'text', itemCount: 50, createdAt: '2025-03-04T12:00:00Z', updatedAt: '2025-03-04T12:00:00Z' },
        { id: 3, name: 'Code Samples', description: 'Programming code examples', type: 'code', itemCount: 75, createdAt: '2025-03-04T12:00:00Z', updatedAt: '2025-03-04T12:00:00Z' },
      ];
      setDatasets(mockDatasets);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching datasets:', error);
      setLoading(false);
    }
  };

  const handleCreateDataset = async () => {
    try {
      // In a real app, you would use: await api.datasets.create(newDataset);
      console.log('Creating dataset:', newDataset);
      setOpenDialog(false);
      // Refresh the list
      fetchDatasets();
      // Reset form
      setNewDataset({
        name: '',
        description: '',
        type: 'text'
      });
    } catch (error) {
      console.error('Error creating dataset:', error);
    }
  };

  const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    { field: 'name', headerName: 'Name', width: 200 },
    { field: 'description', headerName: 'Description', width: 300 },
    { field: 'type', headerName: 'Type', width: 120 },
    { field: 'itemCount', headerName: 'Items', width: 100, type: 'number' },
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
          onClick={() => navigate(`/datasets/${params.row.id}`)}
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
          Datasets
        </Typography>
        <Button 
          variant="contained" 
          color="primary" 
          onClick={() => setOpenDialog(true)}
        >
          Create Dataset
        </Button>
      </Box>

      <Paper sx={{ width: '100%', overflow: 'hidden' }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        ) : (
          <DataGrid
            rows={datasets}
            columns={columns}
            pageSize={10}
            rowsPerPageOptions={[10]}
            autoHeight
            disableSelectionOnClick
          />
        )}
      </Paper>

      {/* Create Dataset Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Create New Dataset</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Name"
              value={newDataset.name}
              onChange={(e) => setNewDataset({ ...newDataset, name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Description"
              value={newDataset.description}
              onChange={(e) => setNewDataset({ ...newDataset, description: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
            <FormControl fullWidth>
              <InputLabel>Type</InputLabel>
              <Select
                value={newDataset.type}
                label="Type"
                onChange={(e) => setNewDataset({ ...newDataset, type: e.target.value })}
              >
                <MenuItem value="text">Text</MenuItem>
                <MenuItem value="code">Code</MenuItem>
                <MenuItem value="image">Image</MenuItem>
                <MenuItem value="audio">Audio</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button 
            onClick={handleCreateDataset} 
            variant="contained" 
            color="primary"
            disabled={!newDataset.name}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Datasets; 