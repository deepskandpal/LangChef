#!/bin/bash

# Stop and remove existing containers
docker-compose down

# Rebuild and start the containers
docker-compose up -d --build

echo "Enhanced Agent Flow Builder has been updated in Docker" 