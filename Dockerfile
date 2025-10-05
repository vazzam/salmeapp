# syntax = docker/dockerfile:1

# Adjust NODE_VERSION as desired
ARG NODE_VERSION=20.18.0
FROM node:${NODE_VERSION}-slim as base

LABEL fly_launch_runtime="Node.js"

# Node.js app lives here
WORKDIR /app

# Set production environment
ENV NODE_ENV="production"

# Install Python and system dependencies for PyAudio
RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y \
    python3 \
    python3-pip \
    python3-venv \
    portaudio19-dev \
    python3-pyaudio \
    gcc \
    g++ \
    make \
    libasound2-dev \
    libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

# Create Python virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Throw-away build stage to reduce size of final image
FROM base as build

# Install packages needed to build node modules
RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y build-essential node-gyp pkg-config python-is-python3

# Install node modules
COPY package-lock.json package.json ./
RUN npm ci --include=dev

# Copy application code
COPY . .

# Install Python dependencies
COPY requirements.txt ./
RUN /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Build application (if needed)
# RUN npm run build

# Remove development dependencies
RUN npm prune --omit=dev


# Final stage for app image
FROM base

# Copy built application
COPY --from=build /app /app
COPY --from=build /opt/venv /opt/venv

# Ensure virtual environment is in PATH
ENV PATH="/opt/venv/bin:$PATH"

# Expose port (adjust as needed for your application)
EXPOSE 8501

# Start the server by default, this can be overwritten at runtime
CMD [ "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0" ]
