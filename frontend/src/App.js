import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';

// Layout components
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

// Pages
import Dashboard from './pages/Dashboard';
import Prompts from './pages/Prompts';
import PromptDetail from './pages/PromptDetail';
import Datasets from './pages/Datasets';
import DatasetDetail from './pages/DatasetDetail';
import Experiments from './pages/Experiments';
import ExperimentDetail from './pages/ExperimentDetail';
import Playground from './pages/Playground';
import Traces from './pages/Traces';
import TraceDetail from './pages/TraceDetail';
import Login from './pages/Login';
import NotFound from './pages/NotFound';

// Context providers
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';

function App() {
  return (
    <AuthProvider>
      <Box sx={{ display: 'flex' }}>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          
          {/* Protected routes */}
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="prompts" element={<Prompts />} />
              <Route path="prompts/:id" element={<PromptDetail />} />
              <Route path="datasets" element={<Datasets />} />
              <Route path="datasets/:id" element={<DatasetDetail />} />
              <Route path="experiments" element={<Experiments />} />
              <Route path="experiments/:id" element={<ExperimentDetail />} />
              <Route path="playground" element={<Playground />} />
              <Route path="traces" element={<Traces />} />
              <Route path="traces/:id" element={<TraceDetail />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Route>
        </Routes>
      </Box>
    </AuthProvider>
  );
}

export default App; 