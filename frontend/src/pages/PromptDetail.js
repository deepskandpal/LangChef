import React, { useState, useEffect, useCallback } from 'react';
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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import { useParams, useNavigate } from 'react-router-dom';
import { Edit as EditIcon, Delete as DeleteIcon, History as HistoryIcon } from '@mui/icons-material';
import { api } from '../services/api';

const PromptDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState(null);
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tabValue, setTabValue] = useState(0);
  const [editMode, setEditMode] = useState(false);
  const [editedPrompt, setEditedPrompt] = useState(null);
  const [openDeleteDialog, setOpenDeleteDialog] = useState(false);

  const fetchPromptDetails = useCallback(async () => {
    try {
      setLoading(true);
      // For now, use mock data since the backend might not be fully set up
      // In a real app, you would use: 
      // const promptData = await api.prompts.getById(id);
      // const versionsData = await api.prompts.getVersions(id);
      
      const mockPrompt = {
        id: parseInt(id),
        name: 'Customer Support',
        description: 'Template for customer support responses',
        template: 'You are a helpful customer support agent for {{company_name}}. The customer has the following question: {{question}}. Please provide a helpful, friendly, and accurate response.',
        type: 'text',
        createdAt: '2025-03-04T12:00:00Z',
        updatedAt: '2025-03-04T12:00:00Z'
      };
      
      setPrompt(mockPrompt);
      setEditedPrompt(mockPrompt);
      setVersions([
        { id: 1, version: 1, createdAt: '2023-02-15T10:30:00Z' },
        { id: 2, version: 2, createdAt: '2023-02-20T14:45:00Z' }
      ]);
    } catch (error) {
      console.error('Error fetching prompt details:', error);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchPromptDetails();
  }, [fetchPromptDetails]);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  const handleEditToggle = () => {
    setEditMode(!editMode);
    if (!editMode) {
      setEditedPrompt({...prompt});
    }
  };

  const handleSaveChanges = async () => {
    try {
      // In a real app, you would use: await api.prompts.update(id, editedPrompt);
      console.log('Saving changes:', editedPrompt);
      setPrompt(editedPrompt);
      setEditMode(false);
      // Refresh data
      fetchPromptDetails();
    } catch (error) {
      console.error('Error updating prompt:', error);
    }
  };

  const handleDeletePrompt = async () => {
    try {
      // In a real app, you would use: await api.prompts.delete(id);
      console.log('Deleting prompt:', id);
      setOpenDeleteDialog(false);
      // Navigate back to prompts list
      navigate('/prompts');
    } catch (error) {
      console.error('Error deleting prompt:', error);
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
          {editMode ? 'Edit Prompt' : prompt.name}
        </Typography>
        <Box>
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
              value={editedPrompt.name}
              onChange={(e) => setEditedPrompt({ ...editedPrompt, name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Description"
              value={editedPrompt.description}
              onChange={(e) => setEditedPrompt({ ...editedPrompt, description: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
            <TextField
              label="Template"
              value={editedPrompt.template}
              onChange={(e) => setEditedPrompt({ ...editedPrompt, template: e.target.value })}
              fullWidth
              multiline
              rows={6}
            />
          </Box>
        ) : (
          <>
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle1" color="text.secondary">
                Description
              </Typography>
              <Typography variant="body1">
                {prompt.description || 'No description provided'}
              </Typography>
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle1" color="text.secondary">
                Type
              </Typography>
              <Chip label={prompt.type} color="primary" size="small" />
            </Box>
            <Box>
              <Typography variant="subtitle1" color="text.secondary">
                Template
              </Typography>
              <Paper variant="outlined" sx={{ p: 2, backgroundColor: '#f5f5f5', mt: 1 }}>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                  {prompt.template}
                </Typography>
              </Paper>
            </Box>
          </>
        )}
      </Paper>

      <Box sx={{ width: '100%' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab label="Versions" icon={<HistoryIcon />} iconPosition="start" />
          </Tabs>
        </Box>
        <Box sx={{ p: 2 }}>
          {tabValue === 0 && (
            <Box>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Version History
              </Typography>
              {versions.map((version) => (
                <Paper key={version.id} variant="outlined" sx={{ p: 2, mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="subtitle1">
                      Version {version.version}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {new Date(version.createdAt).toLocaleString()}
                    </Typography>
                  </Box>
                  <Divider sx={{ mb: 2 }} />
                  <Paper variant="outlined" sx={{ p: 2, backgroundColor: '#f5f5f5' }}>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                      {version.template}
                    </Typography>
                  </Paper>
                </Paper>
              ))}
            </Box>
          )}
        </Box>
      </Box>

      {/* Delete Confirmation Dialog */}
      <Dialog open={openDeleteDialog} onClose={() => setOpenDeleteDialog(false)}>
        <DialogTitle>Confirm Deletion</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete the prompt "{prompt.name}"? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDeleteDialog(false)}>Cancel</Button>
          <Button onClick={handleDeletePrompt} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PromptDetail; 