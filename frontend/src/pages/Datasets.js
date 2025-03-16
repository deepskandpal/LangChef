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
  Alert,
  Snackbar,
  IconButton,
  Chip,
  Tooltip,
  Grid,
  Collapse
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { useNavigate } from 'react-router-dom';
import { datasetsApi } from '../services/api';
import AddIcon from '@mui/icons-material/Add';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import Menu from '@mui/material/Menu';
import DatasetSchemaInfo from '../components/DatasetSchemaInfo';

const Datasets = () => {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [openDialog, setOpenDialog] = useState(false);
  const [openUploadDialog, setOpenUploadDialog] = useState(false);
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success'
  });
  const [newDataset, setNewDataset] = useState({
    name: '',
    description: '',
    type: 'text',
    metadata: {}
  });
  const [uploadData, setUploadData] = useState({
    name: '',
    description: '',
    file: null,
    fileType: 'json'
  });
  const [anchorEl, setAnchorEl] = useState(null);
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [schemaInfoOpen, setSchemaInfoOpen] = useState(false);

  useEffect(() => {
    fetchDatasets();
  }, []);

  // Update selectedDataset when selectedDatasetId changes
  useEffect(() => {
    if (selectedDatasetId) {
      const dataset = datasets.find(d => d.id === selectedDatasetId);
      setSelectedDataset(dataset || null);
    } else {
      setSelectedDataset(null);
    }
  }, [selectedDatasetId, datasets]);

  const fetchDatasets = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await datasetsApi.getAll();
      setDatasets(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('Error fetching datasets:', error);
      setError('Failed to fetch datasets. Please try again later.');
      // Fallback to mock data in development
      if (process.env.NODE_ENV === 'development') {
        const mockDatasets = [
          { id: 1, name: 'Customer Queries', description: 'Collection of customer support queries', type: 'text', itemCount: 120, createdAt: '2023-03-04T12:00:00Z', updatedAt: '2023-03-04T12:00:00Z' },
          { id: 2, name: 'Product Descriptions', description: 'Product descriptions for e-commerce', type: 'text', itemCount: 50, createdAt: '2023-03-04T12:00:00Z', updatedAt: '2023-03-04T12:00:00Z' },
          { id: 3, name: 'Code Samples', description: 'Programming code examples', type: 'code', itemCount: 75, createdAt: '2023-03-04T12:00:00Z', updatedAt: '2023-03-04T12:00:00Z' },
        ];
        setDatasets(mockDatasets);
      } else {
        setDatasets([]);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDataset = async () => {
    try {
      setError('');
      await datasetsApi.create(newDataset);
      setOpenDialog(false);
      setSnackbar({
        open: true,
        message: 'Dataset created successfully!',
        severity: 'success'
      });
      // Refresh the list
      fetchDatasets();
      // Reset form
      setNewDataset({
        name: '',
        description: '',
        type: 'text',
        metadata: {}
      });
    } catch (error) {
      console.error('Error creating dataset:', error);
      setError('Failed to create dataset. Please try again.');
    }
  };

  const handleUploadDataset = async () => {
    try {
      setError('');
      const formData = new FormData();
      formData.append('file', uploadData.file);
      formData.append('name', uploadData.name);
      formData.append('description', uploadData.description);
      formData.append('file_type', uploadData.fileType);

      let response;
      
      // Use the appropriate upload method based on file type
      if (uploadData.fileType.toLowerCase() === 'csv') {
        response = await datasetsApi.uploadCSV(formData);
      } else {
        response = await datasetsApi.upload(formData);
      }

      setOpenUploadDialog(false);
      setSnackbar({
        open: true,
        message: 'Dataset uploaded successfully!',
        severity: 'success'
      });
      // Reset form
      setUploadData({
        name: '',
        description: '',
        file: null,
        fileType: 'json'
      });
      // Refresh the list
      fetchDatasets();
    } catch (error) {
      console.error('Error uploading dataset:', error);
      // Close the dialog and show the error in a snackbar
      setOpenUploadDialog(false);
      const errorMessage = error.response?.data?.detail || 'Failed to upload dataset. Please try again.';
      setError(errorMessage);
      setSnackbar({
        open: true,
        message: errorMessage,
        severity: 'error'
      });
    }
  };

  const handleRunExperiment = (datasetId) => {
    navigate(`/experiments/new?datasetId=${datasetId}`);
  };

  const handleMenuOpen = (event, datasetId) => {
    setAnchorEl(event.currentTarget);
    setSelectedDatasetId(datasetId);
    const dataset = datasets.find(d => d.id === datasetId);
    setSelectedDataset(dataset || null);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedDatasetId(null);
    setSelectedDataset(null);
  };

  const handleDeleteClick = () => {
    if (window.confirm(`Are you sure you want to delete "${selectedDataset?.name}"?`)) {
      handleDelete();
    }
  };

  const handleDelete = async () => {
    if (!selectedDatasetId) return;
    
    try {
      setLoading(true);
      await datasetsApi.delete(selectedDatasetId);
      setSnackbar({
        open: true,
        message: 'Dataset deleted successfully!',
        severity: 'success'
      });
      await fetchDatasets();
    } catch (error) {
      console.error('Error deleting dataset:', error);
      setSnackbar({
        open: true,
        message: error.response?.data?.detail || 'Failed to delete dataset. Please try again.',
        severity: 'error'
      });
    } finally {
      setLoading(false);
      handleMenuClose();
    }
  };

  const handleCloseSnackbar = () => {
    setSnackbar({
      ...snackbar,
      open: false
    });
  };

  const columns = [
    { 
      field: 'name', 
      headerName: 'Name', 
      flex: 2,
      renderCell: (params) => (
        <Box sx={{ 
          display: 'flex', 
          alignItems: 'center',
          cursor: 'pointer',
          color: 'primary.main',
          '&:hover': { textDecoration: 'underline' }
        }}
        onClick={() => navigate(`/datasets/${params.row.id}`)}
        >
          {params.value}
        </Box>
      )
    },
    { field: 'description', headerName: 'Description', flex: 3 },
    { 
      field: 'type', 
      headerName: 'Type', 
      width: 120,
      renderCell: (params) => (
        <Chip 
          label={params.value} 
          size="small" 
          color={
            params.value === 'text' ? 'primary' :
            params.value === 'code' ? 'secondary' :
            'default'
          }
          variant="outlined"
        />
      )
    },
    { 
      field: 'items_count', 
      headerName: 'Items', 
      width: 100, 
      type: 'number',
      renderCell: (params) => (
        <Chip 
          label={params.value || 0} 
          size="small" 
          color="default"
        />
      )
    },
    { 
      field: 'created_at', 
      headerName: 'Created', 
      width: 170, 
      valueFormatter: (params) => new Date(params.value).toLocaleString() 
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 180,
      renderCell: (params) => (
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Run experiment on this dataset">
            <IconButton 
              size="small" 
              color="primary"
              onClick={() => handleRunExperiment(params.row.id)}
            >
              <PlayArrowIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="View details">
            <Button 
              variant="outlined" 
              size="small" 
              onClick={() => navigate(`/datasets/${params.row.id}`)}
            >
              View
            </Button>
          </Tooltip>
          <IconButton
            size="small"
            onClick={(e) => handleMenuOpen(e, params.row.id)}
          >
            <MoreVertIcon fontSize="small" />
          </IconButton>
        </Box>
      ),
    },
  ];

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Datasets
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button 
            variant="outlined" 
            color="primary" 
            startIcon={<UploadFileIcon />}
            onClick={() => setOpenUploadDialog(true)}
          >
            Upload Dataset
          </Button>
          <Button 
            variant="contained" 
            color="primary" 
            startIcon={<AddIcon />}
            onClick={() => setOpenDialog(true)}
          >
            Create Dataset
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Schema Information (Collapsible) */}
      <Box sx={{ mb: 3 }}>
        <Box 
          sx={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            p: 2, 
            bgcolor: '#f0f7ff', 
            borderRadius: '4px',
            cursor: 'pointer'
          }}
          onClick={() => setSchemaInfoOpen(!schemaInfoOpen)}
        >
          <Typography variant="subtitle1" sx={{ fontWeight: 'medium' }}>
            Understanding Dataset Workflows
          </Typography>
          <IconButton size="small">
            {schemaInfoOpen ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Box>
        <Collapse in={schemaInfoOpen}>
          <DatasetSchemaInfo />
        </Collapse>
      </Box>

      <Paper sx={{ width: '100%', overflow: 'hidden', mb: 4 }}>
        <Box sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Dataset Overview
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Create and manage datasets for testing and evaluating your LLM applications. 
            Run experiments on datasets to track performance and improvements over time.
          </Typography>

          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={4}>
              <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'background.default' }}>
                <Typography variant="h6">{datasets.length}</Typography>
                <Typography variant="body2" color="text.secondary">Total Datasets</Typography>
              </Paper>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'background.default' }}>
                <Typography variant="h6">
                  {datasets.reduce((total, dataset) => total + (dataset.itemCount || 0), 0)}
                </Typography>
                <Typography variant="body2" color="text.secondary">Total Items</Typography>
              </Paper>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'background.default' }}>
                <Typography variant="h6">
                  {datasets.filter(d => d.updatedAt && new Date(d.updatedAt) > new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)).length}
                </Typography>
                <Typography variant="body2" color="text.secondary">Updated This Week</Typography>
              </Paper>
            </Grid>
          </Grid>
        </Box>
        
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        ) : (
          <DataGrid
            rows={datasets}
            columns={columns}
            pageSize={10}
            rowsPerPageOptions={[5, 10, 25]}
            autoHeight
            disableSelectionOnClick
            sx={{ 
              '& .MuiDataGrid-cell:hover': {
                color: 'primary.main',
              },
            }}
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

      {/* Upload Dataset Dialog */}
      <Dialog open={openUploadDialog} onClose={() => setOpenUploadDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Upload Dataset</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Name"
              value={uploadData.name}
              onChange={(e) => setUploadData({ ...uploadData, name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Description"
              value={uploadData.description}
              onChange={(e) => setUploadData({ ...uploadData, description: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
            <FormControl fullWidth>
              <InputLabel>File Type</InputLabel>
              <Select
                value={uploadData.fileType}
                label="File Type"
                onChange={(e) => setUploadData({ ...uploadData, fileType: e.target.value })}
              >
                <MenuItem value="json">JSON</MenuItem>
                <MenuItem value="jsonl">JSONL</MenuItem>
                <MenuItem value="csv">CSV</MenuItem>
              </Select>
            </FormControl>
            <Button
              component="label"
              variant="outlined"
              startIcon={<CloudUploadIcon />}
              sx={{ mt: 1 }}
            >
              Upload File
              <input
                type="file"
                hidden
                onChange={(e) => setUploadData({ ...uploadData, file: e.target.files[0] })}
              />
            </Button>
            {uploadData.file && (
              <Typography variant="body2" sx={{ mt: 1 }}>
                Selected file: {uploadData.file.name}
              </Typography>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenUploadDialog(false)}>Cancel</Button>
          <Button 
            onClick={handleUploadDataset} 
            variant="contained" 
            color="primary"
            disabled={!uploadData.name || !uploadData.file}
          >
            Upload
          </Button>
        </DialogActions>
      </Dialog>

      {/* Actions Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => {
          navigate(`/datasets/${selectedDatasetId}`);
          handleMenuClose();
        }}>
          View Details
        </MenuItem>
        <MenuItem onClick={() => {
          handleRunExperiment(selectedDatasetId);
          handleMenuClose();
        }}>
          Run Experiment
        </MenuItem>
        <MenuItem onClick={handleDeleteClick} sx={{ color: 'error.main' }}>
          Delete
        </MenuItem>
      </Menu>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} sx={{ width: '100%' }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Datasets; 