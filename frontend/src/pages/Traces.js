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
import { tracesApi } from '../services/api';

const Traces = () => {
  const navigate = useNavigate();
  const [traces, setTraces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [newTrace, setNewTrace] = useState({
    name: '',
    description: '',
    type: 'llm'
  });

  useEffect(() => {
    fetchTraces();
  }, []);

  const fetchTraces = async () => {
    try {
      setLoading(true);
      // Try to fetch from API first
      try {
        const response = await tracesApi.getAll();
        if (response && Array.isArray(response.data)) {
          setTraces(response.data);
          return;
        }
      } catch (apiError) {
        console.error('API fetch failed, using mock data:', apiError);
      }
      
      // Fallback to mock data
      const mockTraces = [
        { 
          id: 1, 
          name: 'Customer Support Interaction', 
          description: 'Trace of customer support conversation', 
          type: 'llm', 
          status: 'completed',
          spanCount: 8,
          createdAt: '2025-03-04T12:00:00Z', 
          updatedAt: '2025-03-04T12:05:00Z' 
        },
        { 
          id: 2, 
          name: 'Product Description Generation', 
          description: 'Trace of product description generation', 
          type: 'llm', 
          status: 'completed',
          spanCount: 5,
          createdAt: '2025-03-04T13:00:00Z', 
          updatedAt: '2025-03-04T13:02:00Z' 
        },
        { 
          id: 3, 
          name: 'Code Generation Process', 
          description: 'Trace of code generation process', 
          type: 'llm', 
          status: 'active',
          spanCount: 3,
          createdAt: '2025-03-04T14:00:00Z', 
          updatedAt: '2025-03-04T14:01:00Z' 
        },
      ];
      setTraces(mockTraces);
    } catch (error) {
      console.error('Error fetching traces:', error);
      setTraces([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTrace = async () => {
    try {
      // In a real app, you would use: await api.traces.create(newTrace);
      console.log('Creating trace:', newTrace);
      setOpenDialog(false);
      // Refresh the list
      fetchTraces();
      // Reset form
      setNewTrace({
        name: '',
        description: '',
        type: 'llm'
      });
    } catch (error) {
      console.error('Error creating trace:', error);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'active':
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
    { field: 'description', headerName: 'Description', width: 300 },
    { field: 'type', headerName: 'Type', width: 120 },
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
    { field: 'spanCount', headerName: 'Spans', width: 100, type: 'number' },
    { field: 'createdAt', headerName: 'Created', width: 180, valueFormatter: (params) => new Date(params.value).toLocaleString() },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 120,
      renderCell: (params) => (
        <Button 
          variant="contained" 
          size="small" 
          onClick={() => navigate(`/traces/${params.row.id}`)}
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
          Traces
        </Typography>
        <Button 
          variant="contained" 
          color="primary" 
          onClick={() => setOpenDialog(true)}
        >
          Create Trace
        </Button>
      </Box>

      <Paper sx={{ width: '100%', overflow: 'hidden' }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        ) : (
          <DataGrid
            rows={traces}
            columns={columns}
            pageSize={10}
            rowsPerPageOptions={[10]}
            autoHeight
            disableSelectionOnClick
          />
        )}
      </Paper>

      {/* Create Trace Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Create New Trace</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Name"
              value={newTrace.name}
              onChange={(e) => setNewTrace({ ...newTrace, name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Description"
              value={newTrace.description}
              onChange={(e) => setNewTrace({ ...newTrace, description: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
            <FormControl fullWidth>
              <InputLabel>Type</InputLabel>
              <Select
                value={newTrace.type}
                label="Type"
                onChange={(e) => setNewTrace({ ...newTrace, type: e.target.value })}
              >
                <MenuItem value="llm">LLM</MenuItem>
                <MenuItem value="function">Function</MenuItem>
                <MenuItem value="chain">Chain</MenuItem>
                <MenuItem value="agent">Agent</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button 
            onClick={handleCreateTrace} 
            variant="contained" 
            color="primary"
            disabled={!newTrace.name}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Traces; 