FROM node:18-alpine

WORKDIR /app

# Initialize a new Node.js project
RUN npm init -y

# Install dependencies
RUN npm install express cors body-parser

# Create necessary directories
RUN mkdir -p models controllers routes

# Copy Agent Flow API files
COPY src/models/AgentFlow.js models/
COPY src/controllers/agentFlowController.js controllers/
COPY src/routes/agentFlowRoutes.js routes/
COPY src/server.js .

# Expose the API port
EXPOSE 5000

# Run the server
CMD ["node", "server.js"] 