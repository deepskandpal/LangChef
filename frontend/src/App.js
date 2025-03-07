import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Box } from '@mui/material';

// Layout components
import Layout from './components/Layout';

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
import NotFound from './pages/NotFound';

function App() {
  return (
    <Box sx={{ display: 'flex' }}>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
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
      </Routes>
    </Box>
  );
}

export default App; 