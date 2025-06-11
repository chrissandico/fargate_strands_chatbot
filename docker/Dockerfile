FROM public.ecr.aws/docker/library/python:3.12-slim

WORKDIR /app

# Install system dependencies including Docker
RUN apt-get update && apt-get install -y \
    git \
    curl \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce docker-ce-cli containerd.io \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Copy requirements file
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ .
# Note: .env file is not needed in production as we use Parameter Store
# For local development, mount the .env file using docker run --env-file .env

# Create a non-root user to run the application
# Note: We're not switching to the non-root user because Docker requires root privileges
RUN useradd -m appuser
# USER appuser

# Add Docker group and add our user to it
RUN groupadd -f docker && usermod -aG docker appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application with Uvicorn
# - workers: 2 worker processes (adjust based on container resources)
# - host: Listen on all interfaces
# - port: 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
