import React, { useState, useEffect, useCallback } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  Paper, 
  TextField,
  CircularProgress,
  Chip,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  MenuItem,
  List,
  ListItem,
  ListItemIcon,
  Card,
  CardContent
} from '@mui/material';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Edit as EditIcon, 
  Delete as DeleteIcon, 
  Add as AddIcon,
  Check as CheckIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  ArrowRight as ArrowRightIcon
} from '@mui/icons-material';
import { api } from '../services/api';

const TraceDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [trace, setTrace] = useState(null);
  const [spans, setSpans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editMode, setEditMode] = useState(false);
  const [editedTrace, setEditedTrace] = useState(null);
  const [openDeleteDialog, setOpenDeleteDialog] = useState(false);
  const [openAddSpanDialog, setOpenAddSpanDialog] = useState(false);
  const [newSpan, setNewSpan] = useState({
    name: '',
    type: 'llm',
    input: '',
    output: '',
    metadata: ''
  });

  const fetchTraceDetails = useCallback(async () => {
    try {
      setLoading(true);
      // For now, use mock data since the backend might not be fully set up
      // In a real app, you would use: 
      // const traceData = await api.traces.getById(id);
      // const spansData = await api.traces.getSpans(id);
      
      const mockTrace = {
        id: parseInt(id),
        name: 'Customer Support Interaction',
        description: 'Trace of customer support conversation',
        type: 'llm',
        status: 'completed',
        spanCount: 8,
        createdAt: '2025-03-04T12:00:00Z',
        updatedAt: '2025-03-04T12:05:00Z'
      };
      
      const mockSpans = [
        {
          id: 1,
          traceId: parseInt(id),
          name: 'Initial Query Processing',
          type: 'llm',
          status: 'completed',
          input: 'How do I reset my password?',
          output: 'User is asking about password reset procedure.',
          startTime: '2025-03-04T12:00:00Z',
          endTime: '2025-03-04T12:00:01Z',
          metadata: JSON.stringify({ tokens: 15, model: 'gpt-4' })
        },
        {
          id: 2,
          traceId: parseInt(id),
          name: 'Knowledge Base Lookup',
          type: 'function',
          status: 'completed',
          input: 'password reset',
          output: 'Found 3 articles about password reset.',
          startTime: '2025-03-04T12:00:01Z',
          endTime: '2025-03-04T12:00:02Z',
          metadata: JSON.stringify({ articles: [101, 102, 103] })
        },
        {
          id: 3,
          traceId: parseInt(id),
          name: 'Response Generation',
          type: 'llm',
          status: 'completed',
          input: 'Generate response for password reset query using articles 101, 102, 103',
          output: 'To reset your password, please follow these steps: 1. Go to the login page. 2. Click on "Forgot Password". 3. Enter your email address. 4. Follow the instructions sent to your email.',
          startTime: '2025-03-04T12:00:02Z',
          endTime: '2025-03-04T12:00:04Z',
          metadata: JSON.stringify({ tokens: 48, model: 'gpt-4' })
        },
        {
          id: 4,
          traceId: parseInt(id),
          name: 'User Satisfaction Check',
          type: 'llm',
          status: 'completed',
          input: 'Is the response helpful and complete?',
          output: 'Yes, the response provides clear step-by-step instructions for password reset.',
          startTime: '2025-03-04T12:00:04Z',
          endTime: '2025-03-04T12:00:05Z',
          metadata: JSON.stringify({ tokens: 20, model: 'gpt-4' })
        }
      ];
      
      setTrace(mockTrace);
      setSpans(mockSpans);
      setEditedTrace(mockTrace);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching trace details:', error);
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchTraceDetails();
  }, [fetchTraceDetails]);

  const handleEditToggle = () => {
    setEditMode(!editMode);
    if (!editMode) {
      setEditedTrace({...trace});
    }
  };

  const handleSaveChanges = async () => {
    try {
      // In a real app, you would use: await api.traces.update(id, editedTrace);
      console.log('Saving changes:', editedTrace);
      setTrace(editedTrace);
      setEditMode(false);
      // Refresh data
      fetchTraceDetails();
    } catch (error) {
      console.error('Error updating trace:', error);
    }
  };

  const handleDeleteTrace = async () => {
    try {
      // In a real app, you would use: await api.traces.delete(id);
      console.log('Deleting trace:', id);
      setOpenDeleteDialog(false);
      // Navigate back to traces list
      navigate('/traces');
    } catch (error) {
      console.error('Error deleting trace:', error);
    }
  };

  const handleAddSpan = async () => {
    try {
      // In a real app, you would use: await api.traces.addSpan(id, newSpan);
      console.log('Adding span:', newSpan);
      setOpenAddSpanDialog(false);
      // Refresh data
      fetchTraceDetails();
      // Reset form
      setNewSpan({
        name: '',
        type: 'llm',
        input: '',
        output: '',
        metadata: ''
      });
    } catch (error) {
      console.error('Error adding span:', error);
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

  const getSpanIcon = (type) => {
    switch (type) {
      case 'llm':
        return <InfoIcon />;
      case 'function':
        return <CheckIcon />;
      case 'error':
        return <ErrorIcon />;
      default:
        return <InfoIcon />;
    }
  };

  const getSpanColor = (type) => {
    switch (type) {
      case 'llm':
        return 'primary';
      case 'function':
        return 'success';
      case 'error':
        return 'error';
      default:
        return 'grey';
    }
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
          {editMode ? 'Edit Trace' : trace.name}
        </Typography>
        <Box>
          <Button 
            variant="outlined" 
            color="primary" 
            startIcon={<EditIcon />} 
            onClick={handleEditToggle}
            sx={{ mr: 1 }}
            disabled={trace.status === 'completed'}
          >
            {editMode ? 'Cancel' : 'Edit'}
          </Button>
          {editMode ? (
            <Button 
              variant="contained" 
              color="primary" 
              onClick={handleSaveChanges}
            >
              Save
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

      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            {editMode ? (
              <TextField
                fullWidth
                label="Name"
                value={editedTrace.name}
                onChange={(e) => setEditedTrace({...editedTrace, name: e.target.value})}
                margin="normal"
              />
            ) : (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle1" color="text.secondary">Name</Typography>
                <Typography variant="body1">{trace.name}</Typography>
              </Box>
            )}

            {editMode ? (
              <TextField
                fullWidth
                label="Description"
                value={editedTrace.description}
                onChange={(e) => setEditedTrace({...editedTrace, description: e.target.value})}
                margin="normal"
                multiline
                rows={3}
              />
            ) : (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle1" color="text.secondary">Description</Typography>
                <Typography variant="body1">{trace.description}</Typography>
              </Box>
            )}
          </Grid>
          <Grid item xs={12} md={6}>
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle1" color="text.secondary">Type</Typography>
              <Typography variant="body1">{trace.type}</Typography>
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle1" color="text.secondary">Status</Typography>
              <Chip 
                label={trace.status} 
                color={getStatusColor(trace.status)} 
                size="small" 
              />
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle1" color="text.secondary">Span Count</Typography>
              <Typography variant="body1">{trace.spanCount}</Typography>
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle1" color="text.secondary">Created At</Typography>
              <Typography variant="body1">{new Date(trace.createdAt).toLocaleString()}</Typography>
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle1" color="text.secondary">Updated At</Typography>
              <Typography variant="body1">{new Date(trace.updatedAt).toLocaleString()}</Typography>
            </Box>
          </Grid>
        </Grid>
      </Paper>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5">Spans</Typography>
        <Button 
          variant="contained" 
          color="primary" 
          startIcon={<AddIcon />}
          onClick={() => setOpenAddSpanDialog(true)}
          disabled={trace.status === 'completed'}
        >
          Add Span
        </Button>
      </Box>

      <Paper sx={{ p: 3 }}>
        {spans.length === 0 ? (
          <Typography variant="body1" align="center" sx={{ py: 3 }}>
            No spans found for this trace.
          </Typography>
        ) : (
          <List>
            {spans.map((span, index) => (
              <ListItem key={span.id} sx={{ mb: 2, display: 'block' }}>
                <Card variant="outlined" sx={{ mb: 2 }}>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <ListItemIcon>
                        {getSpanIcon(span.type)}
                      </ListItemIcon>
                      <Typography variant="h6">{span.name}</Typography>
                      <Chip 
                        label={span.type} 
                        color={getSpanColor(span.type)} 
                        size="small" 
                        sx={{ ml: 1 }}
                      />
                      <Box sx={{ flexGrow: 1 }} />
                      <Typography variant="caption">
                        {new Date(span.startTime).toLocaleTimeString()} - {new Date(span.endTime).toLocaleTimeString()}
                      </Typography>
                    </Box>
                    
                    <Box sx={{ pl: 6 }}>
                      <Typography variant="subtitle2" color="text.secondary">Input</Typography>
                      <Typography variant="body2" sx={{ mb: 1 }}>{span.input}</Typography>
                      
                      <Typography variant="subtitle2" color="text.secondary">Output</Typography>
                      <Typography variant="body2" sx={{ mb: 1 }}>{span.output}</Typography>
                      
                      {span.metadata && (
                        <>
                          <Typography variant="subtitle2" color="text.secondary">Metadata</Typography>
                          <Typography variant="body2" component="pre" sx={{ 
                            backgroundColor: 'background.paper', 
                            p: 1, 
                            borderRadius: 1,
                            overflow: 'auto'
                          }}>
                            {JSON.stringify(JSON.parse(span.metadata), null, 2)}
                          </Typography>
                        </>
                      )}
                    </Box>
                  </CardContent>
                </Card>
                {index < spans.length - 1 && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', my: 1 }}>
                    <ArrowRightIcon color="action" sx={{ transform: 'rotate(90deg)' }} />
                  </Box>
                )}
              </ListItem>
            ))}
          </List>
        )}
      </Paper>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={openDeleteDialog}
        onClose={() => setOpenDeleteDialog(false)}
      >
        <DialogTitle>Delete Trace</DialogTitle>
        <DialogContent>
          <Typography>Are you sure you want to delete this trace? This action cannot be undone.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDeleteDialog(false)}>Cancel</Button>
          <Button onClick={handleDeleteTrace} color="error">Delete</Button>
        </DialogActions>
      </Dialog>

      {/* Add Span Dialog */}
      <Dialog
        open={openAddSpanDialog}
        onClose={() => setOpenAddSpanDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Add Span</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Name"
            value={newSpan.name}
            onChange={(e) => setNewSpan({...newSpan, name: e.target.value})}
            margin="normal"
            required
          />
          <TextField
            select
            fullWidth
            label="Type"
            value={newSpan.type}
            onChange={(e) => setNewSpan({...newSpan, type: e.target.value})}
            margin="normal"
          >
            <MenuItem value="llm">LLM</MenuItem>
            <MenuItem value="function">Function</MenuItem>
            <MenuItem value="error">Error</MenuItem>
            <MenuItem value="other">Other</MenuItem>
          </TextField>
          <TextField
            fullWidth
            label="Input"
            value={newSpan.input}
            onChange={(e) => setNewSpan({...newSpan, input: e.target.value})}
            margin="normal"
            multiline
            rows={3}
          />
          <TextField
            fullWidth
            label="Output"
            value={newSpan.output}
            onChange={(e) => setNewSpan({...newSpan, output: e.target.value})}
            margin="normal"
            multiline
            rows={3}
          />
          <TextField
            fullWidth
            label="Metadata (JSON)"
            value={newSpan.metadata}
            onChange={(e) => setNewSpan({...newSpan, metadata: e.target.value})}
            margin="normal"
            multiline
            rows={3}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenAddSpanDialog(false)}>Cancel</Button>
          <Button 
            onClick={handleAddSpan} 
            color="primary" 
            disabled={!newSpan.name}
          >
            Add
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TraceDetail; 