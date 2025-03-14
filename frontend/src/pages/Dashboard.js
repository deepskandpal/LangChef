import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Grid, 
  Paper, 
  Card, 
  CardContent, 
  CardHeader,
  CircularProgress,
  Button
} from '@mui/material';
import { 
  Chart as ChartJS, 
  CategoryScale, 
  LinearScale, 
  PointElement, 
  LineElement, 
  BarElement,
  Title, 
  Tooltip, 
  Legend, 
  ArcElement 
} from 'chart.js';
import { Line, Bar, Pie } from 'react-chartjs-2';
import { metricsApi } from '../services/api';
import { Refresh as RefreshIcon } from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const Dashboard = () => {
  const { user, sessionExpiry } = useAuth();
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);
  const [error, setError] = useState(null);

  // Mock data for demonstration
  const mockDashboardData = {
    total_experiments: 24,
    total_results: 1250,
    tokens: {
      input: 125000,
      output: 75000,
      total: 200000
    },
    cost: {
      total: 12.75
    },
    latency: {
      avg_ms: 850
    }
  };

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      // Use the metricsApi service instead of direct axios call
      const response = await metricsApi.getDashboard();
      setDashboardData(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      // Use mock data when API fails, but don't show error if it's a 404
      if (err.response && err.response.status === 404) {
        console.log('Using mock data for dashboard (API endpoint not implemented yet)');
        setError(null);
      } else {
        setError('Failed to load dashboard data. Using mock data instead.');
      }
      setDashboardData(mockDashboardData);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Use mock data if API call fails
  const data = dashboardData || mockDashboardData;

  // Chart data
  const tokenDistributionData = {
    labels: ['Input Tokens', 'Output Tokens'],
    datasets: [
      {
        label: 'Token Distribution',
        data: [data.tokens.input, data.tokens.output],
        backgroundColor: [
          'rgba(54, 162, 235, 0.6)',
          'rgba(255, 99, 132, 0.6)',
        ],
        borderColor: [
          'rgba(54, 162, 235, 1)',
          'rgba(255, 99, 132, 1)',
        ],
        borderWidth: 1,
      },
    ],
  };

  // Mock time series data for demonstration
  const timeSeriesData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [
      {
        label: 'Experiments',
        data: [4, 6, 8, 12, 16, 24],
        borderColor: 'rgba(75, 192, 192, 1)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
      },
    ],
  };

  // Mock model usage data
  const modelUsageData = {
    labels: ['GPT-4', 'GPT-3.5', 'Claude', 'Llama 2', 'Custom'],
    datasets: [
      {
        label: 'Model Usage',
        data: [30, 45, 15, 8, 2],
        backgroundColor: [
          'rgba(255, 99, 132, 0.6)',
          'rgba(54, 162, 235, 0.6)',
          'rgba(255, 206, 86, 0.6)',
          'rgba(75, 192, 192, 0.6)',
          'rgba(153, 102, 255, 0.6)',
        ],
        borderColor: [
          'rgba(255, 99, 132, 1)',
          'rgba(54, 162, 235, 1)',
          'rgba(255, 206, 86, 1)',
          'rgba(75, 192, 192, 1)',
          'rgba(153, 102, 255, 1)',
        ],
        borderWidth: 1,
      },
    ],
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          Dashboard
        </Typography>
        {error && (
          <Button 
            variant="outlined" 
            startIcon={<RefreshIcon />} 
            onClick={fetchDashboardData}
            size="small"
          >
            Refresh
          </Button>
        )}
      </Box>
      
      {error && (
        <Paper sx={{ p: 2, mb: 3, bgcolor: 'warning.light' }}>
          <Typography color="warning.dark">{error}</Typography>
        </Paper>
      )}
      
      {/* Session information */}
      {sessionExpiry && (
        <Paper sx={{ p: 2, mb: 3, bgcolor: 'info.light' }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
            Session Info: 
            <span style={{ marginLeft: '8px', fontWeight: 'normal' }}>
              {user?.username || 'Unknown user'} • 
              Expires: {new Date(sessionExpiry).toLocaleString()}
            </span>
          </Typography>
        </Paper>
      )}
      
      {/* Key Metrics */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Paper elevation={3} sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary">
              Total Experiments
            </Typography>
            <Typography variant="h3" color="primary">
              {data.total_experiments}
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper elevation={3} sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary">
              Total Results
            </Typography>
            <Typography variant="h3" color="primary">
              {data.total_results}
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper elevation={3} sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary">
              Total Tokens
            </Typography>
            <Typography variant="h3" color="primary">
              {(data.tokens.total / 1000).toFixed(1)}K
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper elevation={3} sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary">
              Total Cost
            </Typography>
            <Typography variant="h3" color="primary">
              ${data.cost.total.toFixed(2)}
            </Typography>
          </Paper>
        </Grid>
      </Grid>
      
      {/* Charts */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Experiments Over Time" />
            <CardContent>
              <Line 
                data={timeSeriesData} 
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  scales: {
                    y: {
                      beginAtZero: true
                    }
                  }
                }}
                height={300}
              />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Token Distribution" />
            <CardContent>
              <Pie 
                data={tokenDistributionData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                }}
                height={300}
              />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12}>
          <Card>
            <CardHeader title="Model Usage" />
            <CardContent>
              <Bar 
                data={modelUsageData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                }}
                height={300}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard; 