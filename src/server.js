const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const path = require('path');

// Determine if we're in the API container or frontend container
const isApiContainer = process.env.NODE_ENV === 'development' && process.env.CORS_ORIGIN;

// Import routes - adjust paths based on container environment
const agentFlowRoutes = isApiContainer 
  ? require('./routes/agentFlowRoutes') 
  : require('./routes/agentFlowRoutes');

// Create Express app
const app = express();
const PORT = process.env.PORT || 5000;

// CORS configuration
const corsOptions = {
  origin: isApiContainer ? process.env.CORS_ORIGIN : '*',
  optionsSuccessStatus: 200
};

// Middleware
app.use(cors(corsOptions));
app.use(bodyParser.json());

// API Routes
app.use('/api/agent-flows', agentFlowRoutes);

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', environment: process.env.NODE_ENV });
});

// In the API container, we don't need to serve static files
if (!isApiContainer) {
  app.use(express.static(path.join(__dirname, '../build')));
  
  // Serve React app for any other requests
  app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, '../build', 'index.html'));
  });
}

// Start server
app.listen(PORT, () => {
  console.log(`Agent Flow API Server is running on port ${PORT}`);
  console.log(`Environment: ${process.env.NODE_ENV}`);
  if (isApiContainer) {
    console.log(`CORS enabled for origin: ${process.env.CORS_ORIGIN}`);
  }
});

module.exports = app; 