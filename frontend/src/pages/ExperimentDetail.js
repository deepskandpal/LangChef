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
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Edit as EditIcon, 
  Delete as DeleteIcon, 
  PlayArrow as RunIcon, 
  Stop as StopIcon,
  Assessment as ResultsIcon,
  Timeline as TracesIcon,
  ShowChart as MetricsIcon
} from '@mui/icons-material';
import { api } from '../services/api';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const ExperimentDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [experiment, setExperiment] = useState(null);
  const [results, setResults] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tabValue, setTabValue] = useState(0);
  const [editMode, setEditMode] = useState(false);
  const [editedExperiment, setEditedExperiment] = useState(null);
  const [openDeleteDialog, setOpenDeleteDialog] = useState(false);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  useEffect(() => {
    fetchExperimentDetails();
  }, [id]);

  const fetchExperimentDetails = async () => {
    try {
      setLoading(true);
      // For now, use mock data since the backend might not be fully set up
      // In a real app, you would use: 
      // const experimentData = await api.experiments.getById(id);
      // const resultsData = await api.experiments.getResults(id);
      // const metricsData = await api.experiments.getMetrics(id);
      
      const mockExperiment = {
        id: parseInt(id),
        name: 'Customer Support Test',
        description: 'Testing customer support prompt with queries',
        status: 'completed',
        promptId: 1,
        promptName: 'Customer Support',
        datasetId: 1,
        datasetName: 'Customer Queries',
        runCount: 120,
        parameters: {
          temperature: 0.7,
          max_tokens: 100,
          top_p: 1.0
        },
        createdAt: '2025-03-04T12:00:00Z',
        updatedAt: '2025-03-04T14:00:00Z'
      };
      
      const mockResults = Array.from({ length: 50 }, (_, i) => ({
        id: i + 1,
        experimentId: parseInt(id),
        input: `Sample customer query ${i + 1}`,
        output: `Sample response for query ${i + 1}`,
        metadata: JSON.stringify({ 
          tokens: Math.floor(Math.random() * 100) + 50,
          latency: Math.random() * 1000,
          success: Math.random() > 0.1
        }),
        createdAt: '2025-03-04T12:00:00Z'
      }));
      
      const mockMetrics = [
        { name: 'Latency (ms)', values: [120, 135, 118, 130, 125, 140, 132, 128, 122, 130] },
        { name: 'Token Count', values: [85, 92, 78, 88, 95, 82, 90, 87, 93, 89] },
        { name: 'Success Rate (%)', values: [100, 100, 90, 100, 100, 100, 90, 100, 100, 100] }
      ];
      
      setExperiment(mockExperiment);
      setResults(mockResults);
      setMetrics(mockMetrics);
      setEditedExperiment(mockExperiment);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching experiment details:', error);
      setLoading(false);
    }
  };

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  const handleEditToggle = () => {
    setEditMode(!editMode);
    if (!editMode) {
      setEditedExperiment({...experiment});
    }
  };

  const handleSaveChanges = async () => {
    try {
      // In a real app, you would use: await api.experiments.update(id, editedExperiment);
      console.log('Saving changes:', editedExperiment);
      setExperiment(editedExperiment);
      setEditMode(false);
      // Refresh data
      fetchExperimentDetails();
    } catch (error) {
      console.error('Error updating experiment:', error);
    }
  };

  const handleDeleteExperiment = async () => {
    try {
      // In a real app, you would use: await api.experiments.delete(id);
      console.log('Deleting experiment:', id);
      setOpenDeleteDialog(false);
      // Navigate back to experiments list
      navigate('/experiments');
    } catch (error) {
      console.error('Error deleting experiment:', error);
    }
  };

  const handleRunExperiment = async () => {
    try {
      // In a real app, you would use: await api.experiments.run(id);
      console.log('Running experiment:', id);
      // Update status
      setExperiment({...experiment, status: 'running'});
    } catch (error) {
      console.error('Error running experiment:', error);
    }
  };

  const handleStopExperiment = async () => {
    try {
      // In a real app, you would use: await api.experiments.stop(id);
      console.log('Stopping experiment:', id);
      // Update status
      setExperiment({...experiment, status: 'stopped'});
    } catch (error) {
      console.error('Error stopping experiment:', error);
    }
  };

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'running':
        return 'primary';
      case 'failed':
        return 'error';
      case 'stopped':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getChartData = (metric) => {
    return {
      labels: Array.from({ length: metric.values.length }, (_, i) => `Run ${i + 1}`),
      datasets: [
        {
          label: metric.name,
          data: metric.values,
          fill: false,
          backgroundColor: 'rgba(75,192,192,0.4)',
          borderColor: 'rgba(75,192,192,1)',
        },
      ],
    };
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Experiment Metrics',
      },
    },
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
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4" component="h1">
          {editMode ? 'Edit Experiment' : experiment.name}
        </Typography>
        <Box>
          {experiment.status === 'running' ? (
            <Button 
              variant="contained" 
              color="warning" 
              startIcon={<StopIcon />}
              onClick={handleStopExperiment}
              sx={{ mr: 1 }}
            >
              Stop
            </Button>
          ) : (
            <Button 
              variant="contained" 
              color="primary" 
              startIcon={<RunIcon />}
              onClick={handleRunExperiment}
              sx={{ mr: 1 }}
              disabled={experiment.status === 'completed'}
            >
              Run
            </Button>
          )}
          <Button 
            variant="outlined" 
            color="primary" 
            startIcon={editMode ? null : <EditIcon />}
            onClick={handleEditToggle}
            sx={{ mr: 1 }}
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

      <Paper sx={{ mb: 3, p: 3 }}>
        {editMode ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Name"
              value={editedExperiment.name}
              onChange={(e) => setEditedExperiment({ ...editedExperiment, name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Description"
              value={editedExperiment.description}
              onChange={(e) => setEditedExperiment({ ...editedExperiment, description: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
            <TextField
              label="Parameters (JSON)"
              value={typeof editedExperiment.parameters === 'object' 
                ? JSON.stringify(editedExperiment.parameters, null, 2) 
                : editedExperiment.parameters}
              onChange={(e) => setEditedExperiment({ 
                ...editedExperiment, 
                parameters: e.target.value 
              })}
              fullWidth
              multiline
              rows={6}
            />
          </Box>
        ) : (
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle1" color="text.secondary">
                  Description
                </Typography>
                <Typography variant="body1">
                  {experiment.description || 'No description provided'}
                </Typography>
              </Box>
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle1" color="text.secondary">
                  Status
                </Typography>
                <Chip label={experiment.status} color={getStatusColor(experiment.status)} />
              </Box>
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle1" color="text.secondary">
                  Prompt
                </Typography>
                <Typography variant="body1">
                  {experiment.promptName}
                </Typography>
              </Box>
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle1" color="text.secondary">
                  Dataset
                </Typography>
                <Typography variant="body1">
                  {experiment.datasetName}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} md={6}>
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle1" color="text.secondary">
                  Parameters
                </Typography>
                <Paper variant="outlined" sx={{ p: 2, backgroundColor: '#f5f5f5', mt: 1 }}>
                  <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                    {JSON.stringify(experiment.parameters, null, 2)}
                  </Typography>
                </Paper>
              </Box>
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle1" color="text.secondary">
                  Created
                </Typography>
                <Typography variant="body1">
                  {new Date(experiment.createdAt).toLocaleString()}
                </Typography>
              </Box>
              <Box>
                <Typography variant="subtitle1" color="text.secondary">
                  Last Updated
                </Typography>
                <Typography variant="body1">
                  {new Date(experiment.updatedAt).toLocaleString()}
                </Typography>
              </Box>
            </Grid>
          </Grid>
        )}
      </Paper>

      <Box sx={{ width: '100%' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab icon={<ResultsIcon />} iconPosition="start" label="Results" />
            <Tab icon={<MetricsIcon />} iconPosition="start" label="Metrics" />
            <Tab icon={<TracesIcon />} iconPosition="start" label="Traces" />
          </Tabs>
        </Box>
        <Box sx={{ p: 2 }}>
          {tabValue === 0 && (
            <Box>
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>ID</TableCell>
                      <TableCell>Input</TableCell>
                      <TableCell>Output</TableCell>
                      <TableCell>Created</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {results
                      .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                      .map((result) => (
                        <TableRow key={result.id}>
                          <TableCell>{result.id}</TableCell>
                          <TableCell>{result.input.length > 50 ? `${result.input.substring(0, 50)}...` : result.input}</TableCell>
                          <TableCell>{result.output.length > 50 ? `${result.output.substring(0, 50)}...` : result.output}</TableCell>
                          <TableCell>{new Date(result.createdAt).toLocaleString()}</TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              </TableContainer>
              <TablePagination
                rowsPerPageOptions={[5, 10, 25]}
                component="div"
                count={results.length}
                rowsPerPage={rowsPerPage}
                page={page}
                onPageChange={handleChangePage}
                onRowsPerPageChange={handleChangeRowsPerPage}
              />
            </Box>
          )}
          {tabValue === 1 && (
            <Box>
              <Grid container spacing={3}>
                {metrics.map((metric, index) => (
                  <Grid item xs={12} md={6} lg={4} key={index}>
                    <Paper sx={{ p: 2 }}>
                      <Line data={getChartData(metric)} options={chartOptions} />
                    </Paper>
                  </Grid>
                ))}
              </Grid>
            </Box>
          )}
          {tabValue === 2 && (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <Typography variant="body1">
                Trace visualization coming soon...
              </Typography>
            </Box>
          )}
        </Box>
      </Box>

      {/* Delete Confirmation Dialog */}
      <Dialog open={openDeleteDialog} onClose={() => setOpenDeleteDialog(false)}>
        <DialogTitle>Confirm Deletion</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete the experiment "{experiment.name}"? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDeleteDialog(false)}>Cancel</Button>
          <Button onClick={handleDeleteExperiment} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ExperimentDetail; 