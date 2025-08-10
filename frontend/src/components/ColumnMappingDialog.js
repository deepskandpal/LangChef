import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Grid,
  Paper,
  Divider,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Add as AddIcon,
  Remove as RemoveIcon,
  Check as CheckIcon,
  Info as InfoIcon,
  ArrowForward as ArrowForwardIcon
} from '@mui/icons-material';

const ColumnMappingDialog = ({ 
  open, 
  onClose, 
  onSubmit, 
  columns = [], 
  datasetId,
  datasetName
}) => {
  const [inputColumns, setInputColumns] = useState([]);
  const [outputColumns, setOutputColumns] = useState([]);
  const [metadataColumns, setMetadataColumns] = useState([]);
  const [unmappedColumns, setUnmappedColumns] = useState([...columns]);
  const [error, setError] = useState('');

  // Update unmapped columns when the dialog receives new columns
  useEffect(() => {
    setUnmappedColumns([...columns]);
    setInputColumns([]);
    setOutputColumns([]);
    setMetadataColumns([]);
  }, [columns]);

  const handleAddColumn = (column, type) => {
    setError('');
    
    // Remove from unmapped
    setUnmappedColumns(unmappedColumns.filter(c => c !== column));
    
    // Add to appropriate category
    switch (type) {
      case 'input':
        setInputColumns([...inputColumns, column]);
        break;
      case 'output':
        setOutputColumns([...outputColumns, column]);
        break;
      case 'metadata':
        setMetadataColumns([...metadataColumns, column]);
        break;
      default:
        break;
    }
  };

  const handleRemoveColumn = (column, type) => {
    // Remove from category
    switch (type) {
      case 'input':
        setInputColumns(inputColumns.filter(c => c !== column));
        break;
      case 'output':
        setOutputColumns(outputColumns.filter(c => c !== column));
        break;
      case 'metadata':
        setMetadataColumns(metadataColumns.filter(c => c !== column));
        break;
      default:
        break;
    }
    
    // Add back to unmapped
    setUnmappedColumns([...unmappedColumns, column]);
  };

  const handleSubmit = () => {
    // Validate
    if (inputColumns.length === 0) {
      setError('You must select at least one input column');
      return;
    }
    
    // Submit mapping
    onSubmit({
      dataset_id: datasetId,
      input_columns: inputColumns,
      output_columns: outputColumns,
      metadata_columns: metadataColumns,
      unmapped_columns: unmappedColumns
    });
  };

  // Render column chip with remove button
  const renderColumnChip = (column, type) => (
    <Chip
      key={column}
      label={column}
      onDelete={() => handleRemoveColumn(column, type)}
      sx={{ m: 0.5 }}
    />
  );

  return (
    <Dialog 
      open={open} 
      onClose={onClose}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle>
        <Typography variant="h6">
          Map Dataset Columns
        </Typography>
        <Typography variant="subtitle2" color="text.secondary">
          {datasetName || 'New Dataset'}
        </Typography>
      </DialogTitle>
      
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        
        <Alert severity="info" sx={{ mb: 3 }}>
          <Typography variant="body2">
            Map your CSV columns to appropriate categories to structure your dataset for LLM evaluation.
            At minimum, you must choose input columns.
          </Typography>
        </Alert>
        
        <Grid container spacing={3}>
          {/* Column Mapping Section */}
          <Grid item xs={12} md={8}>
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" fontWeight="medium" gutterBottom>
                Input
                <Tooltip title="Data that will be sent to the model as input">
                  <InfoIcon fontSize="small" sx={{ ml: 1, verticalAlign: 'middle', color: 'text.secondary' }} />
                </Tooltip>
              </Typography>
              <Paper variant="outlined" sx={{ p: 1.5, minHeight: '80px' }}>
                <Box sx={{ display: 'flex', flexWrap: 'wrap' }}>
                  {inputColumns.length > 0 ? (
                    inputColumns.map(col => renderColumnChip(col, 'input'))
                  ) : (
                    <Typography variant="body2" color="text.secondary" sx={{ p: 1 }}>
                      No input columns selected
                    </Typography>
                  )}
                </Box>
              </Paper>
            </Box>
            
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" fontWeight="medium" gutterBottom>
                Expected Output
                <Tooltip title="Reference data to compare with the model's actual output">
                  <InfoIcon fontSize="small" sx={{ ml: 1, verticalAlign: 'middle', color: 'text.secondary' }} />
                </Tooltip>
              </Typography>
              <Paper variant="outlined" sx={{ p: 1.5, minHeight: '80px' }}>
                <Box sx={{ display: 'flex', flexWrap: 'wrap' }}>
                  {outputColumns.length > 0 ? (
                    outputColumns.map(col => renderColumnChip(col, 'output'))
                  ) : (
                    <Typography variant="body2" color="text.secondary" sx={{ p: 1 }}>
                      No output columns selected
                    </Typography>
                  )}
                </Box>
              </Paper>
            </Box>
            
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" fontWeight="medium" gutterBottom>
                Metadata
                <Tooltip title="Additional information about the data point (not used directly in the model)">
                  <InfoIcon fontSize="small" sx={{ ml: 1, verticalAlign: 'middle', color: 'text.secondary' }} />
                </Tooltip>
              </Typography>
              <Paper variant="outlined" sx={{ p: 1.5, minHeight: '80px' }}>
                <Box sx={{ display: 'flex', flexWrap: 'wrap' }}>
                  {metadataColumns.length > 0 ? (
                    metadataColumns.map(col => renderColumnChip(col, 'metadata'))
                  ) : (
                    <Typography variant="body2" color="text.secondary" sx={{ p: 1 }}>
                      No metadata columns selected
                    </Typography>
                  )}
                </Box>
              </Paper>
            </Box>
          </Grid>
          
          {/* Available Columns Section */}
          <Grid item xs={12} md={4}>
            <Paper variant="outlined" sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Box sx={{ p: 2, borderBottom: '1px solid #e0e0e0' }}>
                <Typography variant="subtitle1" fontWeight="medium">
                  Available Columns
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {unmappedColumns.length} unmapped {unmappedColumns.length === 1 ? 'column' : 'columns'}
                </Typography>
              </Box>
              
              <List dense sx={{ overflow: 'auto', flexGrow: 1 }}>
                {unmappedColumns.length > 0 ? (
                  unmappedColumns.map(col => (
                    <ListItem key={col} divider>
                      <ListItemText primary={col} />
                      <Box>
                        <Tooltip title="Add as Input">
                          <IconButton 
                            size="small" 
                            onClick={() => handleAddColumn(col, 'input')}
                            color="primary"
                          >
                            <ArrowForwardIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        
                        <Tooltip title="Add as Output">
                          <IconButton 
                            size="small" 
                            onClick={() => handleAddColumn(col, 'output')}
                            color="secondary"
                          >
                            <ArrowForwardIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        
                        <Tooltip title="Add as Metadata">
                          <IconButton 
                            size="small" 
                            onClick={() => handleAddColumn(col, 'metadata')}
                            color="default"
                          >
                            <ArrowForwardIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </ListItem>
                  ))
                ) : (
                  <ListItem>
                    <ListItemText 
                      primary="All columns mapped" 
                      secondary="Remove columns from other categories to make them available again" 
                    />
                  </ListItem>
                )}
              </List>
            </Paper>
          </Grid>
        </Grid>
      </DialogContent>
      
      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={onClose} color="inherit">
          Cancel
        </Button>
        <Button 
          onClick={handleSubmit} 
          variant="contained" 
          color="primary"
          startIcon={<CheckIcon />}
          disabled={inputColumns.length === 0}
        >
          Apply Mapping
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ColumnMappingDialog; 