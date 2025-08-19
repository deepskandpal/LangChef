# Infrastructure Docker Security Audit

**Component**: Docker Configuration & Container Security  
**Priority**: 🟡 HIGH  
**Agent Assignment**: `security-sweeper`  
**Status**: ❌ Not Started

## 🔍 Security Issues Identified

### 1. Insecure Docker Compose Configuration (HIGH - 7.5/10)

**File**: `/docker-compose.yml` (inferred from architecture)  
**Issue**: Missing security configurations in Docker Compose setup

```yaml
# INSECURE DOCKER CONFIGURATION:
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8001:8000"  # Direct port mapping without security
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/langchef  # Hardcoded credentials
    # MISSING: security_opt configurations
    # MISSING: user specification (runs as root)
    # MISSING: resource limits
    # MISSING: health checks

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"  # Development port exposed
    # MISSING: security configurations
    # MISSING: non-root user

  db:
    image: postgres:13
    environment:
      POSTGRES_PASSWORD: postgres  # Weak default password
      # MISSING: custom user configuration
    # MISSING: volume security
    # MISSING: network isolation
```

**Risk**:
- Containers run as root by default (privilege escalation)
- Weak database credentials hardcoded in configuration
- No resource limits (potential DoS via resource exhaustion)
- Development ports exposed in production
- No security profiles or capabilities restrictions

### 2. Missing Container Security Profiles (HIGH - 7.0/10)

**Files**: Dockerfile configurations (inferred)  
**Issue**: No security profiles, AppArmor, or SELinux configurations

```dockerfile
# INSECURE DOCKERFILE PATTERNS:
FROM node:16
# MISSING: specific version tag (uses latest implicitly)
# MISSING: multi-stage builds for smaller attack surface
# MISSING: non-root user creation
# MISSING: security scanning

WORKDIR /app
COPY package*.json ./
RUN npm install  # No audit, potentially vulnerable packages
# MISSING: npm audit fix
# MISSING: package verification

COPY . .
# MISSING: .dockerignore to prevent sensitive file inclusion
# MISSING: file permission restrictions

EXPOSE 3000
# MISSING: USER directive (runs as root)
CMD ["npm", "start"]  # No security wrapper
```

**Risk**:
- Containers run with root privileges
- No protection against container escape attacks
- Vulnerable base images without security patches
- No capability restrictions or security profiles
- Large attack surface from unnecessary packages

### 3. Insecure Volume and Network Configuration (MEDIUM - 6.5/10)

**File**: Docker volume and network configurations  
**Issue**: No secure volume mounting or network isolation

```yaml
# INSECURE VOLUME CONFIGURATION:
volumes:
  postgres_data:
    # MISSING: access control specifications
    # MISSING: encryption at rest
    # MISSING: backup security

networks:
  default:
    # MISSING: custom network with security rules
    # MISSING: network segmentation
    # MISSING: encryption in transit
```

**Risk**:
- Database volumes accessible without proper permissions
- No network segmentation between services
- Unencrypted communication between containers
- Host system exposure through insecure volume mounts

### 4. Missing Container Image Security (MEDIUM - 6.0/10)

**Files**: Base image selection and configuration  
**Issue**: No image security scanning or verification

```dockerfile
# SECURITY ISSUES:
FROM node:16  # No specific digest or security scanning
FROM postgres:13  # No verification of image integrity

# MISSING security measures:
# - Image vulnerability scanning
# - Base image hardening
# - Image signing verification
# - Minimal base image usage (Alpine/distroless)
# - Regular base image updates
```

**Risk**:
- Vulnerable base images with known CVEs
- No verification of image integrity or authenticity
- Large attack surface from unnecessary packages
- No protection against supply chain attacks

### 5. Insufficient Container Runtime Security (MEDIUM - 5.5/10)

**File**: Container runtime configurations  
**Issue**: No runtime security monitoring or restrictions

```yaml
# MISSING RUNTIME SECURITY:
services:
  backend:
    # MISSING: security_opt configurations
    # MISSING: cap_drop and cap_add specifications
    # MISSING: read_only filesystem
    # MISSING: no_new_privs security option
    # MISSING: PID namespace restrictions
```

**Risk**:
- Containers can escalate privileges
- No protection against kernel exploits
- Unrestricted system call access
- No runtime behavior monitoring

### 6. Development Configuration in Production (LOW - 4.5/10)

**Files**: Docker configurations potentially used in production  
**Issue**: Development settings exposed in production environment

```yaml
# DEVELOPMENT CONFIGURATIONS:
frontend:
  ports:
    - "3000:3000"  # Development server exposed
  environment:
    - NODE_ENV=development  # Debug mode in production
    
backend:
  volumes:
    - .:/app  # Source code mounted (development only)
  environment:
    - DEBUG=true  # Debug logging enabled
```

**Risk**:
- Debug information exposed in production
- Source code accessible from containers
- Development tools available in production
- Sensitive development configurations leaked

## 🔧 Remediation Steps

### Fix 1: Implement Secure Docker Compose Configuration

**Create secure docker-compose.yml**:

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    ports:
      - "127.0.0.1:8001:8000"  # Bind to localhost only
    environment:
      - NODE_ENV=production
      - DATABASE_URL_FILE=/run/secrets/db_url  # Use secrets
    secrets:
      - db_url
      - jwt_secret
    user: "1000:1000"  # Non-root user
    read_only: true  # Read-only filesystem
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
    security_opt:
      - no-new-privileges:true  # Prevent privilege escalation
      - apparmor:docker-default  # Apply AppArmor profile
    cap_drop:
      - ALL  # Drop all capabilities
    cap_add:
      - NET_BIND_SERVICE  # Only allow binding to ports
    networks:
      - backend-network
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    ports:
      - "127.0.0.1:3000:3000"  # Bind to localhost only
    environment:
      - NODE_ENV=production
      - REACT_APP_API_URL=https://api.langchef.com
    user: "1001:1001"  # Non-root user
    read_only: true  # Read-only filesystem
    tmpfs:
      - /tmp:noexec,nosuid,size=50m
    security_opt:
      - no-new-privileges:true
      - apparmor:docker-default
    cap_drop:
      - ALL
    networks:
      - frontend-network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15.3-alpine@sha256:c5b72aacc6c6468b7c0a53912b1a8ddcb5d12c9b  # Pinned digest
    environment:
      POSTGRES_DB_FILE: /run/secrets/db_name
      POSTGRES_USER_FILE: /run/secrets/db_user
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
      POSTGRES_INITDB_ARGS: "--auth-host=scram-sha-256"
    secrets:
      - db_name
      - db_user
      - db_password
    user: "postgres"
    security_opt:
      - no-new-privileges:true
      - apparmor:docker-default
    cap_drop:
      - ALL
    cap_add:
      - SETUID
      - SETGID
      - DAC_OVERRIDE
    networks:
      - backend-network
    volumes:
      - postgres_data:/var/lib/postgresql/data:Z
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$(cat /run/secrets/db_user) -d $$(cat /run/secrets/db_name)"]
      interval: 30s
      timeout: 10s
      retries: 5

  reverse-proxy:
    image: nginx:1.24-alpine@sha256:c5c1a3f1a056e6ddf3a6b6a10c4fa9b54529e95d  # Pinned digest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - nginx_logs:/var/log/nginx
    networks:
      - frontend-network
      - backend-network
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    restart: unless-stopped
    depends_on:
      - backend
      - frontend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  backend-network:
    driver: bridge
    internal: true  # No external access
    ipam:
      config:
        - subnet: 172.20.0.0/16
  frontend-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/16

volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: none
      o: bind,uid=999,gid=999
      device: /opt/langchef/data
  nginx_logs:
    driver: local

secrets:
  db_url:
    file: ./secrets/db_url.txt
  jwt_secret:
    file: ./secrets/jwt_secret.txt
  db_name:
    file: ./secrets/db_name.txt
  db_user:
    file: ./secrets/db_user.txt
  db_password:
    file: ./secrets/db_password.txt
```

### Fix 2: Create Secure Dockerfiles

**Backend Dockerfile (Dockerfile.prod)**:

```dockerfile
# Multi-stage build for security and size optimization
FROM python:3.11.4-alpine3.18 AS base

# Security: Install security updates and create non-root user
RUN apk update && apk upgrade && \
    apk add --no-cache \
        dumb-init \
        su-exec \
        tini && \
    addgroup -g 1000 -S appgroup && \
    adduser -u 1000 -S appuser -G appgroup

# Install build dependencies in separate stage
FROM base AS builder

RUN apk add --no-cache --virtual .build-deps \
        gcc \
        musl-dev \
        postgresql-dev \
        libffi-dev \
        openssl-dev

WORKDIR /build

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user --no-warn-script-location -r requirements.txt

# Runtime stage
FROM base AS runtime

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Set up application directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appgroup . .

# Security: Remove unnecessary packages and files
RUN apk del .build-deps 2>/dev/null || true && \
    rm -rf /var/cache/apk/* && \
    rm -rf /tmp/* && \
    rm -rf /root/.cache

# Security: Set proper permissions
RUN chmod -R 755 /app && \
    chmod -R 644 /app/*.py

# Create necessary directories for non-root user
RUN mkdir -p /app/logs /app/tmp && \
    chown -R appuser:appgroup /app/logs /app/tmp

# Security: Switch to non-root user
USER appuser

# Set PATH for user-installed packages
ENV PATH="/home/appuser/.local/bin:$PATH"

# Security: Disable Python bytecode generation (prevents code injection)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)"

# Use tini for proper signal handling and zombie reaping
ENTRYPOINT ["tini", "--"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

**Frontend Dockerfile (Dockerfile.prod)**:

```dockerfile
# Multi-stage build for minimal runtime image
FROM node:18.17.0-alpine3.18 AS base

# Security: Install security updates
RUN apk update && apk upgrade && \
    apk add --no-cache dumb-init tini && \
    addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

# Build stage
FROM base AS builder

WORKDIR /build

# Copy package files for dependency installation
COPY package*.json ./

# Security: Audit and install dependencies
RUN npm audit --audit-level high && \
    npm ci --only=production --no-optional && \
    npm cache clean --force

# Copy source code and build
COPY . .
RUN npm run build && \
    npm prune --production

# Runtime stage with minimal footprint
FROM nginx:1.24-alpine AS runtime

# Security: Create non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

# Copy built application
COPY --from=builder /build/build /usr/share/nginx/html

# Security: Custom nginx configuration
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

# Security: Set proper ownership and permissions
RUN chown -R appuser:appgroup /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html && \
    chown -R appuser:appgroup /var/cache/nginx && \
    chown -R appuser:appgroup /var/log/nginx && \
    chown -R appuser:appgroup /etc/nginx/conf.d

# Create PID directory for non-root nginx
RUN mkdir -p /var/run/nginx && \
    chown -R appuser:appgroup /var/run/nginx

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Use tini for proper signal handling
ENTRYPOINT ["tini", "--"]
CMD ["nginx", "-g", "daemon off;"]
```

### Fix 3: Implement Container Security Scanning

**Create security scanning script**:

```bash
#!/bin/bash
# scripts/security-scan.sh

set -euo pipefail

echo "🔍 Starting Docker security scan..."

# Function to scan image for vulnerabilities
scan_image() {
    local image_name=$1
    echo "Scanning image: $image_name"
    
    # Trivy vulnerability scanner
    if command -v trivy &> /dev/null; then
        echo "Running Trivy scan..."
        trivy image --severity HIGH,CRITICAL --exit-code 1 "$image_name"
    else
        echo "⚠️  Trivy not installed. Please install: https://trivy.dev/getting-started/installation/"
    fi
    
    # Hadolint for Dockerfile linting
    if command -v hadolint &> /dev/null; then
        echo "Running Hadolint on Dockerfile..."
        hadolint backend/Dockerfile.prod
        hadolint frontend/Dockerfile.prod
    else
        echo "⚠️  Hadolint not installed. Please install: https://github.com/hadolint/hadolint"
    fi
    
    # Docker Bench Security
    if [ -f "docker-bench-security/docker-bench-security.sh" ]; then
        echo "Running Docker Bench Security..."
        cd docker-bench-security && ./docker-bench-security.sh
    else
        echo "⚠️  Docker Bench Security not found. Clone from: https://github.com/docker/docker-bench-security"
    fi
}

# Build images for scanning
echo "Building images for security scanning..."
docker build -t langchef-backend:latest -f backend/Dockerfile.prod backend/
docker build -t langchef-frontend:latest -f frontend/Dockerfile.prod frontend/

# Scan images
scan_image "langchef-backend:latest"
scan_image "langchef-frontend:latest"

# Scan base images
scan_image "python:3.11.4-alpine3.18"
scan_image "node:18.17.0-alpine3.18"
scan_image "nginx:1.24-alpine"
scan_image "postgres:15.3-alpine"

echo "✅ Security scan completed!"
```

### Fix 4: Create Docker Security Policies

**Create .dockerignore files**:

```dockerignore
# .dockerignore (for backend)
node_modules
npm-debug.log
Dockerfile*
.git
.gitignore
.env*
.vscode
.idea
*.md
tests/
docs/
.pytest_cache
__pycache__
*.pyc
*.pyo
*.pyd
.coverage
.nyc_output
.cache
secrets/
*.key
*.pem
*.p12
*.pfx
*.log
```

**Create container security policy**:

```json
{
  "container_security_policy": {
    "version": "1.0",
    "rules": {
      "base_images": {
        "allowed_registries": [
          "docker.io",
          "gcr.io",
          "quay.io"
        ],
        "required_scanning": true,
        "max_severity": "MEDIUM",
        "required_signatures": true
      },
      "runtime_security": {
        "run_as_root": false,
        "privileged_containers": false,
        "host_network": false,
        "host_pid": false,
        "host_ipc": false,
        "capabilities": {
          "drop": ["ALL"],
          "add": ["NET_BIND_SERVICE"]
        }
      },
      "resource_limits": {
        "memory_limit_required": true,
        "cpu_limit_required": true,
        "max_memory": "1G",
        "max_cpu": "1.0"
      },
      "network_security": {
        "custom_networks_required": true,
        "network_isolation": true,
        "port_binding_restrictions": {
          "bind_to_localhost_only": true
        }
      },
      "secrets_management": {
        "use_docker_secrets": true,
        "no_env_secrets": true,
        "secret_rotation": "90d"
      }
    }
  }
}
```

## ✅ Verification Methods

### Test Container Security:
```bash
# Test container runs as non-root
docker run --rm langchef-backend:latest whoami
# Should output: appuser

# Test security options
docker inspect langchef-backend:latest | jq '.[0].HostConfig.SecurityOpt'
# Should show security configurations

# Test resource limits
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### Test Network Isolation:
```bash
# Test network connectivity
docker network ls | grep langchef
docker network inspect langchef_backend-network
```

## 📊 Progress Tracking

- [ ] **Fix 1**: Implement secure Docker Compose configuration
- [ ] **Fix 2**: Create hardened Dockerfiles with multi-stage builds
- [ ] **Fix 3**: Set up container vulnerability scanning pipeline
- [ ] **Fix 4**: Implement container security policies
- [ ] **Fix 5**: Add runtime security monitoring
- [ ] **Fix 6**: Configure network isolation and secrets management
- [ ] **Testing**: Container security test suite
- [ ] **Documentation**: Docker security guidelines

## 🔗 Dependencies

- Trivy vulnerability scanner
- Hadolint Dockerfile linter
- Docker Bench Security
- Container runtime monitoring tools

## 🚨 Critical Actions Required

1. **Implement non-root users in all containers immediately**
2. **Add security profiles and capability restrictions**
3. **Set up vulnerability scanning in CI/CD pipeline**
4. **Configure proper network isolation between services**
5. **Implement secrets management instead of environment variables**
6. **Add resource limits to prevent DoS attacks**