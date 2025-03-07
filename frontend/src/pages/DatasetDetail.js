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
  TablePagination
} from '@mui/material';
import { useParams, useNavigate } from 'react-router-dom';
import { Edit as EditIcon, Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material';
import { api } from '../services/api';

const DatasetDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [dataset, setDataset] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tabValue, setTabValue] = useState(0);
  const [editMode, setEditMode] = useState(false);
  const [editedDataset, setEditedDataset] = useState(null);
  const [openDeleteDialog, setOpenDeleteDialog] = useState(false);
  const [openAddItemDialog, setOpenAddItemDialog] = useState(false);
  const [newItem, setNewItem] = useState({ input: '', output: '', metadata: '' });
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  useEffect(() => {
    fetchDatasetDetails();
  }, [id]);

  const fetchDatasetDetails = async () => {
    try {
      setLoading(true);
      // For now, use mock data since the backend might not be fully set up
      // In a real app, you would use: 
      // const datasetData = await api.datasets.getById(id);
      // const itemsData = await api.datasets.getItems(id);
      
      const mockDataset = {
        id: parseInt(id),
        name: 'Customer Queries',
        description: 'Collection of customer support queries',
        type: 'text',
        itemCount: 120,
        createdAt: '2025-03-04T12:00:00Z',
        updatedAt: '2025-03-04T12:00:00Z'
      };
      
      const mockItems = Array.from({ length: 50 }, (_, i) => ({
        id: i + 1,
        datasetId: parseInt(id),
        input: `Sample customer query ${i + 1}`,
        output: `Sample response for query ${i + 1}`,
        metadata: JSON.stringify({ source: 'mock', category: 'support' }),
        createdAt: '2025-03-04T12:00:00Z'
      }));
      
      setDataset(mockDataset);
      setItems(mockItems);
      setEditedDataset(mockDataset);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching dataset details:', error);
      setLoading(false);
    }
  };

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
      // In a real app, you would use: await api.datasets.update(id, editedDataset);
      console.log('Saving changes:', editedDataset);
      setDataset(editedDataset);
      setEditMode(false);
      // Refresh data
      fetchDatasetDetails();
    } catch (error) {
      console.error('Error updating dataset:', error);
    }
  };

  const handleDeleteDataset = async () => {
    try {
      // In a real app, you would use: await api.datasets.delete(id);
      console.log('Deleting dataset:', id);
      setOpenDeleteDialog(false);
      // Navigate back to datasets list
      navigate('/datasets');
    } catch (error) {
      console.error('Error deleting dataset:', error);
    }
  };

  const handleAddItem = async () => {
    try {
      // In a real app, you would use: await api.datasets.addItem(id, newItem);
      console.log('Adding item:', newItem);
      setOpenAddItemDialog(false);
      // Refresh data
      fetchDatasetDetails();
      // Reset form
      setNewItem({ input: '', output: '', metadata: '' });
    } catch (error) {
      console.error('Error adding item:', error);
    }
  };

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
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
          {editMode ? 'Edit Dataset' : dataset.name}
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
                Items
              </Typography>
              <Typography variant="body1">
                {dataset.itemCount} items
              </Typography>
            </Box>
            <Box>
              <Typography variant="subtitle1" color="text.secondary">
                Created
              </Typography>
              <Typography variant="body1">
                {new Date(dataset.createdAt).toLocaleString()}
              </Typography>
            </Box>
          </>
        )}
      </Paper>

      <Box sx={{ width: '100%' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab label="Items" />
          </Tabs>
          <Button 
            variant="contained" 
            color="primary" 
            startIcon={<AddIcon />}
            onClick={() => setOpenAddItemDialog(true)}
          >
            Add Item
          </Button>
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
                    {items
                      .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                      .map((item) => (
                        <TableRow key={item.id}>
                          <TableCell>{item.id}</TableCell>
                          <TableCell>{item.input.length > 50 ? `${item.input.substring(0, 50)}...` : item.input}</TableCell>
                          <TableCell>{item.output.length > 50 ? `${item.output.substring(0, 50)}...` : item.output}</TableCell>
                          <TableCell>{new Date(item.createdAt).toLocaleString()}</TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              </TableContainer>
              <TablePagination
                rowsPerPageOptions={[5, 10, 25]}
                component="div"
                count={items.length}
                rowsPerPage={rowsPerPage}
                page={page}
                onPageChange={handleChangePage}
                onRowsPerPageChange={handleChangeRowsPerPage}
              />
            </Box>
          )}
        </Box>
      </Box>

      {/* Delete Confirmation Dialog */}
      <Dialog open={openDeleteDialog} onClose={() => setOpenDeleteDialog(false)}>
        <DialogTitle>Confirm Deletion</DialogTitle>
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
        <DialogTitle>Add New Item</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Input"
              value={newItem.input}
              onChange={(e) => setNewItem({ ...newItem, input: e.target.value })}
              fullWidth
              multiline
              rows={3}
              required
            />
            <TextField
              label="Output"
              value={newItem.output}
              onChange={(e) => setNewItem({ ...newItem, output: e.target.value })}
              fullWidth
              multiline
              rows={3}
            />
            <TextField
              label="Metadata (JSON)"
              value={newItem.metadata}
              onChange={(e) => setNewItem({ ...newItem, metadata: e.target.value })}
              fullWidth
              multiline
              rows={2}
              placeholder='{"key": "value"}'
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
            Add
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DatasetDetail; 