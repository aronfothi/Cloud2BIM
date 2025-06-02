# Use Python 3.10 as the base image per project requirements
FROM python:3.10-slim

# Set environment variables to improve Python behavior in Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV HOST=nipg30.inf.elte.hu

# Install system dependencies required for OpenCV, Open3D and other packages
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    wget \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install base Python dependencies first
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir numpy>=1.24.0

RUN pip install --no-cache-dir pye57

# Install the remaining requirements with error handling for problematic packages
RUN pip install --no-cache-dir -r requirements.txt 

# Handle IfcOpenShell installation specifically
RUN pip install --no-cache-dir ifcopenshell 
# Install additional required packages that were commented out in requirements.txt
RUN pip install --no-cache-dir pye57

#RUN pip install --no-cache-dir pdal
# Copy the application code
COPY . .

# Create directory for job storage
RUN mkdir -p jobs && chmod 777 jobs

# Create volume mount points
VOLUME ["/app/jobs"]

# Expose the port the app runs on
EXPOSE 8001

# Health check to ensure service is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://${HOST}:8001/debug/test || exit 1

# Command to run the application using Uvicorn with recommended settings
CMD ["sh", "-c", "uvicorn main:app --host ${HOST} --port 8001 --workers 1"]