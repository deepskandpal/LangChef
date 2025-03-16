import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  Paper, 
  TextField,
  Tabs,
  Tab,
  Divider,
  CircularProgress,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Snackbar,
  Alert,
  Grid,
  Card,
  CardContent,
  Tooltip,
  Stack
} from '@mui/material';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Edit as EditIcon, 
  Delete as DeleteIcon, 
  Add as AddIcon,
  PlayArrow as PlayArrowIcon,
  FileDownload as FileDownloadIcon,
  OpenInNew as OpenInNewIcon
} from '@mui/icons-material';
import { datasetsApi, experimentsApi } from '../services/api';

// Simple component to display JSON data
const JsonViewer = ({ data, collapsed = true }) => {
  const [isCollapsed, setIsCollapsed] = useState(collapsed);
  
  // Parse the JSON if it's a string
  const jsonData = typeof data === 'string' ? JSON.parse(data) : data;
  
  // Format the JSON with indentation for display
  const formattedJson = JSON.stringify(jsonData, null, 2);
  
  return (
    <Box>
      <Button 
        variant="text" 
        size="small" 
        onClick={() => setIsCollapsed(!isCollapsed)}
        sx={{ mb: 1 }}
      >
        {isCollapsed ? 'Expand' : 'Collapse'}
      </Button>
      <Box 
        component="pre" 
        sx={{ 
          p: 1, 
          backgroundColor: '#f5f5f5', 
          borderRadius: 1,
          overflow: 'auto',
          maxHeight: isCollapsed ? '100px' : '400px',
          fontSize: '0.875rem',
          fontFamily: 'monospace'
        }}
      >
        {formattedJson}
      </Box>
    </Box>
  );
};

function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`dataset-tabpanel-${index}`}
      aria-labelledby={`dataset-tab-${index}`}
      {...other}
      style={{ height: '100%' }}
    >
      {value === index && (
        <Box sx={{ height: '100%' }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const DatasetDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [dataset, setDataset] = useState(null);
  const [items, setItems] = useState([]);
  const [experiments, setExperiments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tabValue, setTabValue] = useState(0);
  const [editMode, setEditMode] = useState(false);
  const [editedDataset, setEditedDataset] = useState(null);
  const [openDeleteDialog, setOpenDeleteDialog] = useState(false);
  const [openAddItemDialog, setOpenAddItemDialog] = useState(false);
  const [newItem, setNewItem] = useState({ 
    input: '', 
    expected_output: '', 
    metadata: '{}'
  });
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success'
  });
  const [error, setError] = useState('');
  const [stats, setStats] = useState({
    totalItems: 0,
    experimentsRun: 0,
    lastUpdated: null
  });
  const [openMetadataDialog, setOpenMetadataDialog] = useState(false);
  const [currentItemMetadata, setCurrentItemMetadata] = useState(null);

  // Memoize functions to avoid dependency issues
  const fetchDatasetDetails = React.useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      
      // Get dataset details
      const datasetResponse = await datasetsApi.getById(id);
      setDataset(datasetResponse.data);
      setEditedDataset(datasetResponse.data);
      
      // Get dataset items
      const itemsResponse = await datasetsApi.getItems(id);
      setItems(itemsResponse.data);
      
      // Update stats
      setStats({
        totalItems: itemsResponse.data.length,
        experimentsRun: 0, // Will be updated by fetchExperimentsForDataset
        lastUpdated: datasetResponse.data.updatedAt
      });
      
    } catch (error) {
      console.error('Error fetching dataset details:', error);
      setError('Failed to load dataset details. Please try again later.');
      
      // Use mock data in development for UI testing
      if (process.env.NODE_ENV === 'development') {
        const mockDataset = {
          id: parseInt(id),
          name: 'Customer Queries',
          description: 'Collection of customer support queries',
          type: 'text',
          itemCount: 120,
          createdAt: '2023-03-04T12:00:00Z',
          updatedAt: '2023-03-04T12:00:00Z'
        };
        
        const mockItems = Array.from({ length: 50 }, (_, i) => ({
          id: i + 1,
          datasetId: parseInt(id),
          input: `Sample customer query ${i + 1}`,
          expected_output: `Sample expected response for query ${i + 1}`,
          metadata: JSON.stringify({ source: 'mock', category: 'support' }),
          createdAt: '2023-03-04T12:00:00Z'
        }));
        
        setDataset(mockDataset);
        setItems(mockItems);
        setEditedDataset(mockDataset);
      }
    } finally {
      setLoading(false);
    }
  }, [id, setDataset, setEditedDataset, setItems, setStats, setError, setLoading]);

  const fetchExperimentsForDataset = React.useCallback(async () => {
    try {
      // In a real implementation, you would fetch experiments that used this dataset
      const response = await experimentsApi.getAll({ dataset_id: id });
      setExperiments(response.data);
      setStats(prev => ({
        ...prev,
        experimentsRun: response.data.length
      }));
    } catch (error) {
      console.error('Error fetching experiments:', error);
      
      // Mock data for development
      if (process.env.NODE_ENV === 'development') {
        const mockExperiments = [
          {
            id: 1,
            name: 'Test Experiment 1',
            description: 'Testing model performance on customer queries',
            model: 'Claude 3 Sonnet',
            createdAt: '2023-03-10T14:30:00Z',
            status: 'completed',
            metrics: { accuracy: 0.87, f1: 0.89 }
          },
          {
            id: 2,
            name: 'Test Experiment 2',
            description: 'Improved prompting for customer queries',
            model: 'Claude 3 Opus',
            createdAt: '2023-03-12T09:45:00Z',
            status: 'completed',
            metrics: { accuracy: 0.92, f1: 0.94 }
          }
        ];
        setExperiments(mockExperiments);
        setStats(prev => ({
          ...prev,
          experimentsRun: mockExperiments.length
        }));
      }
    }
  }, [id, setExperiments, setStats]);

  useEffect(() => {
    fetchDatasetDetails();
    fetchExperimentsForDataset();
  }, [id, fetchDatasetDetails, fetchExperimentsForDataset]);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  const handleEditToggle = () => {
    setEditMode(!editMode);
    if (!editMode) {
      setEditedDataset({...dataset});
    }
  };

  const handleSaveChanges = async () => {
    try {
      setError('');
      const response = await datasetsApi.update(id, editedDataset);
      setDataset(response.data);
      setEditMode(false);
      setSnackbar({
        open: true,
        message: 'Dataset updated successfully!',
        severity: 'success'
      });
      // Refresh data
      fetchDatasetDetails();
    } catch (error) {
      console.error('Error updating dataset:', error);
      setError('Failed to update dataset. Please try again.');
    }
  };

  const handleDeleteDataset = async () => {
    try {
      setError('');
      await datasetsApi.delete(id);
      setOpenDeleteDialog(false);
      setSnackbar({
        open: true,
        message: 'Dataset deleted successfully!',
        severity: 'success'
      });
      // Navigate back to datasets list after a short delay
      setTimeout(() => {
        navigate('/datasets');
      }, 1500);
    } catch (error) {
      console.error('Error deleting dataset:', error);
      setError('Failed to delete dataset. Please try again.');
      setOpenDeleteDialog(false);
    }
  };

  const handleAddItem = async () => {
    try {
      setError('');
      // Parse metadata to ensure it's valid JSON
      let parsedMetadata;
      try {
        parsedMetadata = JSON.parse(newItem.metadata);
      } catch (e) {
        setError('Invalid JSON in metadata field');
        return;
      }
      
      const itemToAdd = {
        ...newItem,
        metadata: parsedMetadata
      };
      
      await datasetsApi.createItem(id, itemToAdd);
      setOpenAddItemDialog(false);
      setSnackbar({
        open: true,
        message: 'Item added successfully!',
        severity: 'success'
      });
      // Refresh data
      fetchDatasetDetails();
      // Reset form
      setNewItem({ 
        input: '', 
        expected_output: '', 
        metadata: '{}'
      });
    } catch (error) {
      console.error('Error adding item:', error);
      setError('Failed to add item. Please try again.');
    }
  };

  const handleDeleteItem = async (itemId) => {
    if (!window.confirm('Are you sure you want to delete this item?')) return;
    
    try {
      setError('');
      await datasetsApi.deleteItem(id, itemId);
      setSnackbar({
        open: true,
        message: 'Item deleted successfully!',
        severity: 'success'
      });
      // Refresh data
      fetchDatasetDetails();
    } catch (error) {
      console.error('Error deleting item:', error);
      setError('Failed to delete item. Please try again.');
    }
  };

  const handleRunExperiment = () => {
    navigate(`/experiments/new?datasetId=${id}`);
  };

  const handleExportDataset = () => {
    try {
      // Create a JSON file with dataset items
      const datasetExport = {
        name: dataset.name,
        description: dataset.description,
        type: dataset.type,
        items: items.map(item => ({
          input: item.input,
          expected_output: item.expected_output,
          metadata: typeof item.metadata === 'string' ? JSON.parse(item.metadata) : item.metadata
        }))
      };
      
      // Create and download the file
      const blob = new Blob([JSON.stringify(datasetExport, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${dataset.name.replace(/\s+/g, '_').toLowerCase()}_export.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      setSnackbar({
        open: true,
        message: 'Dataset exported successfully!',
        severity: 'success'
      });
    } catch (error) {
      console.error('Error exporting dataset:', error);
      setError('Failed to export dataset. Please try again.');
    }
  };

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleCloseSnackbar = () => {
    setSnackbar({
      ...snackbar,
      open: false
    });
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, height: 'calc(100vh - 90px)', display: 'flex', flexDirection: 'column' }}>
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4" component="h1">
          {editMode ? 'Edit Dataset' : dataset.name}
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button 
            variant="outlined" 
            color="primary" 
            startIcon={<FileDownloadIcon />}
            onClick={handleExportDataset}
          >
            Export
          </Button>
          <Button 
            variant="outlined" 
            color="primary" 
            startIcon={<PlayArrowIcon />}
            onClick={handleRunExperiment}
          >
            Run Experiment
          </Button>
          <Button 
            variant="outlined" 
            color="primary" 
            startIcon={editMode ? null : <EditIcon />}
            onClick={handleEditToggle}
          >
            {editMode ? 'Cancel' : 'Edit'}
          </Button>
          {editMode ? (
            <Button 
              variant="contained" 
              color="primary" 
              onClick={handleSaveChanges}
            >
              Save Changes
            </Button>
          ) : (
            <Button 
              variant="outlined" 
              color="error" 
              startIcon={<DeleteIcon />}
              onClick={() => setOpenDeleteDialog(true)}
            >
              Delete
            </Button>
          )}
        </Box>
      </Box>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={4}>
          <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
            <Typography variant="subtitle2" color="text.secondary">Total Items</Typography>
            <Typography variant="h5">{stats.totalItems}</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
            <Typography variant="subtitle2" color="text.secondary">Experiments Run</Typography>
            <Typography variant="h5">{stats.experimentsRun}</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
            <Typography variant="subtitle2" color="text.secondary">Last Updated</Typography>
            <Typography variant="h5">
              {stats.lastUpdated ? new Date(stats.lastUpdated).toLocaleDateString() : 'N/A'}
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      <Paper sx={{ mb: 3, p: 3 }}>
        {editMode ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Name"
              value={editedDataset.name}
              onChange={(e) => setEditedDataset({ ...editedDataset, name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Description"
              value={editedDataset.description}
              onChange={(e) => setEditedDataset({ ...editedDataset, description: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
          </Box>
        ) : (
          <>
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle1" color="text.secondary">
                Description
              </Typography>
              <Typography variant="body1">
                {dataset.description || 'No description provided'}
              </Typography>
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle1" color="text.secondary">
                Type
              </Typography>
              <Chip label={dataset.type} color="primary" size="small" />
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle1" color="text.secondary">
                Created
              </Typography>
              <Typography variant="body1">
                {new Date(dataset.createdAt).toLocaleString()}
              </Typography>
            </Box>
            {dataset.metadata && Object.keys(dataset.metadata).length > 0 && (
              <Box>
                <Typography variant="subtitle1" color="text.secondary">
                  Metadata
                </Typography>
                <Paper variant="outlined" sx={{ p: 2, mt: 1, maxHeight: '200px', overflow: 'auto' }}>
                  <JsonViewer 
                    data={typeof dataset.metadata === 'string' ? JSON.parse(dataset.metadata) : dataset.metadata}
                    collapsed={true}
                  />
                </Paper>
              </Box>
            )}
          </>
        )}
      </Paper>

      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab label="Items" />
            <Tab label="Experiments" />
          </Tabs>
          {tabValue === 0 && (
            <Button 
              variant="contained" 
              color="primary" 
              startIcon={<AddIcon />}
              onClick={() => setOpenAddItemDialog(true)}
            >
              Add Item
            </Button>
          )}
        </Box>
        
        <Box sx={{ flexGrow: 1, overflow: 'auto', mt: 2 }}>
          <TabPanel value={tabValue} index={0}>
            {items.length === 0 ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                <Typography variant="h6" color="text.secondary">
                  No items in this dataset
                </Typography>
                <Button 
                  variant="contained" 
                  color="primary" 
                  startIcon={<AddIcon />}
                  onClick={() => setOpenAddItemDialog(true)}
                  sx={{ mt: 2 }}
                >
                  Add First Item
                </Button>
              </Box>
            ) : (
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>ID</TableCell>
                      <TableCell>Input</TableCell>
                      <TableCell>Expected Output</TableCell>
                      <TableCell>Metadata</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {items
                      .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                      .map((item) => (
                        <TableRow key={item.id}>
                          <TableCell>{item.id}</TableCell>
                          <TableCell sx={{ maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            <Tooltip title={item.input}>
                              <Typography variant="body2">
                                {item.input}
                              </Typography>
                            </Tooltip>
                          </TableCell>
                          <TableCell sx={{ maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            <Tooltip title={item.expected_output}>
                              <Typography variant="body2">
                                {item.expected_output || 'None'}
                              </Typography>
                            </Tooltip>
                          </TableCell>
                          <TableCell>
                            {item.metadata && (
                              <Tooltip title="View metadata">
                                <IconButton 
                                  size="small"
                                  onClick={() => {
                                    setOpenMetadataDialog(true);
                                    setCurrentItemMetadata(item.metadata);
                                  }}
                                >
                                  <OpenInNewIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            )}
                          </TableCell>
                          <TableCell>
                            <IconButton 
                              size="small" 
                              color="error"
                              onClick={() => handleDeleteItem(item.id)}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
                <TablePagination
                  rowsPerPageOptions={[5, 10, 25, 50]}
                  component="div"
                  count={items.length}
                  rowsPerPage={rowsPerPage}
                  page={page}
                  onPageChange={handleChangePage}
                  onRowsPerPageChange={handleChangeRowsPerPage}
                />
              </TableContainer>
            )}
          </TabPanel>
          
          <TabPanel value={tabValue} index={1}>
            {experiments.length === 0 ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                <Typography variant="h6" color="text.secondary">
                  No experiments have been run on this dataset yet
                </Typography>
                <Button 
                  variant="contained" 
                  color="primary" 
                  startIcon={<PlayArrowIcon />}
                  onClick={handleRunExperiment}
                  sx={{ mt: 2 }}
                >
                  Run New Experiment
                </Button>
              </Box>
            ) : (
              <Grid container spacing={3}>
                {experiments.map(experiment => (
                  <Grid item xs={12} md={6} key={experiment.id}>
                    <Card variant="outlined" sx={{ cursor: 'pointer' }} onClick={() => navigate(`/experiments/${experiment.id}`)}>
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          {experiment.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          {experiment.description}
                        </Typography>
                        <Box sx={{ mt: 2 }}>
                          <Stack direction="row" spacing={1} mb={1}>
                            <Chip label={`Model: ${experiment.model}`} size="small" />
                            <Chip 
                              label={experiment.status} 
                              size="small" 
                              color={experiment.status === 'completed' ? 'success' : 'warning'} 
                            />
                          </Stack>
                          <Typography variant="caption" display="block" color="text.secondary">
                            Run on {new Date(experiment.createdAt).toLocaleString()}
                          </Typography>
                        </Box>
                        {experiment.metrics && (
                          <Box sx={{ mt: 2, p: 1, bgcolor: 'background.default', borderRadius: 1 }}>
                            <Typography variant="subtitle2" gutterBottom>
                              Metrics
                            </Typography>
                            <Grid container spacing={1}>
                              {Object.entries(experiment.metrics).map(([key, value]) => (
                                <Grid item xs={6} key={key}>
                                  <Tooltip title={`${key}: ${value}`}>
                                    <Box>
                                      <Typography variant="caption" display="block" color="text.secondary">
                                        {key}
                                      </Typography>
                                      <Typography variant="body2" fontWeight="medium">
                                        {typeof value === 'number' ? value.toFixed(3) : value}
                                      </Typography>
                                    </Box>
                                  </Tooltip>
                                </Grid>
                              ))}
                            </Grid>
                          </Box>
                        )}
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}
          </TabPanel>
        </Box>
      </Box>

      {/* Delete Confirmation Dialog */}
      <Dialog open={openDeleteDialog} onClose={() => setOpenDeleteDialog(false)}>
        <DialogTitle>Delete Dataset</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete the dataset "{dataset.name}"? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDeleteDialog(false)}>Cancel</Button>
          <Button onClick={handleDeleteDataset} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Add Item Dialog */}
      <Dialog open={openAddItemDialog} onClose={() => setOpenAddItemDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Add Dataset Item</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Input"
              value={newItem.input}
              onChange={(e) => setNewItem({ ...newItem, input: e.target.value })}
              fullWidth
              required
              multiline
              rows={3}
              placeholder="The input text that will be sent to the model"
            />
            <TextField
              label="Expected Output"
              value={newItem.expected_output}
              onChange={(e) => setNewItem({ ...newItem, expected_output: e.target.value })}
              fullWidth
              multiline
              rows={3}
              placeholder="The expected output for evaluation (optional)"
            />
            <TextField
              label="Metadata (JSON)"
              value={newItem.metadata}
              onChange={(e) => setNewItem({ ...newItem, metadata: e.target.value })}
              fullWidth
              multiline
              rows={3}
              placeholder='{"key": "value"}'
              error={Boolean(error && error.includes('metadata'))}
              helperText={error && error.includes('metadata') ? error : ''}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenAddItemDialog(false)}>Cancel</Button>
          <Button 
            onClick={handleAddItem} 
            variant="contained" 
            color="primary"
            disabled={!newItem.input}
          >
            Add Item
          </Button>
        </DialogActions>
      </Dialog>

      {/* Metadata Viewing Dialog */}
      <Dialog 
        open={openMetadataDialog} 
        onClose={() => setOpenMetadataDialog(false)}
        maxWidth="md" 
        fullWidth
      >
        <DialogTitle>Item Metadata</DialogTitle>
        <DialogContent>
          {currentItemMetadata && (
            <JsonViewer 
              data={currentItemMetadata} 
              collapsed={false}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenMetadataDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>

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

export default DatasetDetail; 