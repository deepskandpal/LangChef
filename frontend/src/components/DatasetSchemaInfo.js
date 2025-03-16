import React from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  Divider, 
  List, 
  ListItem, 
  ListItemIcon, 
  ListItemText
} from '@mui/material';
import { 
  Circle as CircleIcon,
  ArrowForward as ArrowForwardIcon,
  Info as InfoIcon
} from '@mui/icons-material';

/**
 * A component that displays information about the dataset schema and workflow
 */
const DatasetSchemaInfo = () => {
  return (
    <Paper sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        Dataset Schema & Workflow
      </Typography>
      
      <Box sx={{ mb: 3 }}>
        <Typography variant="body2" paragraph>
          Datasets allow you to organize, test, and evaluate your LLM applications. Here's how they work:
        </Typography>
        
        <List dense>
          <ListItem>
            <ListItemIcon>
              <CircleIcon sx={{ fontSize: 10 }} />
            </ListItemIcon>
            <ListItemText 
              primary={
                <Typography variant="body2">
                  A <strong>Dataset</strong> consists of multiple <strong>DatasetItems</strong> with inputs and expected outputs
                </Typography>
              }
            />
          </ListItem>
          <ListItem>
            <ListItemIcon>
              <CircleIcon sx={{ fontSize: 10 }} />
            </ListItemIcon>
            <ListItemText 
              primary={
                <Typography variant="body2">
                  <strong>DatasetRunItem</strong> links a <strong>DatasetItem</strong> to a <strong>Trace</strong> created during an experiment
                </Typography>
              }
            />
          </ListItem>
          <ListItem>
            <ListItemIcon>
              <CircleIcon sx={{ fontSize: 10 }} />
            </ListItemIcon>
            <ListItemText 
              primary={
                <Typography variant="body2">
                  Evaluation metrics of a <strong>DatasetRun</strong> are based on <strong>Scores</strong> associated with the <strong>Traces</strong> linked to run
                </Typography>
              }
            />
          </ListItem>
        </List>
      </Box>
      
      <Divider sx={{ my: 2 }} />
      
      <Typography variant="subtitle1" gutterBottom>
        Dataset Workflow Example
      </Typography>
      
      <Box sx={{ mb: 2 }}>
        <Typography variant="body2" paragraph>
          This is a high-level example workflow of using datasets to continuously improve an LLM application:
        </Typography>
        
        <Box sx={{ pl: 2, borderLeft: '2px solid #e0e0e0' }}>
          <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 1 }}>
            <Box sx={{ minWidth: 24 }}>
              <Typography variant="body2" fontWeight="bold">1.</Typography>
            </Box>
            <Box>
              <Typography variant="body2">
                <strong>Create dataset items</strong> with inputs and expected outputs through:
              </Typography>
              <List dense sx={{ pl: 2 }}>
                <ListItem dense sx={{ py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 24 }}>
                    <ArrowForwardIcon sx={{ fontSize: 14 }} />
                  </ListItemIcon>
                  <ListItemText primary="Manual creation or import of test cases" />
                </ListItem>
                <ListItem dense sx={{ py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 24 }}>
                    <ArrowForwardIcon sx={{ fontSize: 14 }} />
                  </ListItemIcon>
                  <ListItemText primary="Synthetic generation of questions/responses" />
                </ListItem>
                <ListItem dense sx={{ py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 24 }}>
                    <ArrowForwardIcon sx={{ fontSize: 14 }} />
                  </ListItemIcon>
                  <ListItemText primary="Production app traces with issues that need attention" />
                </ListItem>
              </List>
            </Box>
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 1 }}>
            <Box sx={{ minWidth: 24 }}>
              <Typography variant="body2" fontWeight="bold">2.</Typography>
            </Box>
            <Typography variant="body2">
              <strong>Make changes to your application</strong> that you want to test
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 1 }}>
            <Box sx={{ minWidth: 24 }}>
              <Typography variant="body2" fontWeight="bold">3.</Typography>
            </Box>
            <Typography variant="body2">
              <strong>Run your application</strong> (or parts of it) on all dataset items
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 1 }}>
            <Box sx={{ minWidth: 24 }}>
              <Typography variant="body2" fontWeight="bold">4.</Typography>
            </Box>
            <Box>
              <Typography variant="body2">
                <strong>Evaluate results:</strong>
              </Typography>
              <List dense sx={{ pl: 2 }}>
                <ListItem dense sx={{ py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 24 }}>
                    <ArrowForwardIcon sx={{ fontSize: 14 }} />
                  </ListItemIcon>
                  <ListItemText primary="Compare against baseline/expected outputs if available" />
                </ListItem>
                <ListItem dense sx={{ py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 24 }}>
                    <ArrowForwardIcon sx={{ fontSize: 14 }} />
                  </ListItemIcon>
                  <ListItemText primary="Use custom evaluation metrics" />
                </ListItem>
                <ListItem dense sx={{ py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 24 }}>
                    <ArrowForwardIcon sx={{ fontSize: 14 }} />
                  </ListItemIcon>
                  <ListItemText primary="Leverage LLM-based evaluation" />
                </ListItem>
              </List>
            </Box>
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
            <Box sx={{ minWidth: 24 }}>
              <Typography variant="body2" fontWeight="bold">5.</Typography>
            </Box>
            <Box>
              <Typography variant="body2">
                <strong>Review aggregated results</strong> across the full dataset to:
              </Typography>
              <List dense sx={{ pl: 2 }}>
                <ListItem dense sx={{ py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 24 }}>
                    <ArrowForwardIcon sx={{ fontSize: 14 }} />
                  </ListItemIcon>
                  <ListItemText primary="Identify improvements" />
                </ListItem>
                <ListItem dense sx={{ py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 24 }}>
                    <ArrowForwardIcon sx={{ fontSize: 14 }} />
                  </ListItemIcon>
                  <ListItemText primary="Catch regressions" />
                </ListItem>
                <ListItem dense sx={{ py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 24 }}>
                    <ArrowForwardIcon sx={{ fontSize: 14 }} />
                  </ListItemIcon>
                  <ListItemText primary="Make data-driven decisions about releases" />
                </ListItem>
              </List>
            </Box>
          </Box>
        </Box>
      </Box>
      
      <Box sx={{ display: 'flex', alignItems: 'center', p: 2, bgcolor: '#f8f2ff', borderRadius: 1 }}>
        <InfoIcon color="primary" sx={{ mr: 1, fontSize: 20 }} />
        <Typography variant="body2">
          Using datasets to continuously test your LLM applications helps you identify issues, track improvements, and make data-driven decisions about your LLM workflow.
        </Typography>
      </Box>
    </Paper>
  );
};

export default DatasetSchemaInfo; 