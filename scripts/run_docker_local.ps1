# Script to run the Docker container locally

# Change to the src directory
cd ../src

# Build the Docker image
Write-Host "Building Docker image..."
docker build -t tcg-agent .

# Run the Docker container
Write-Host "Running Docker container..."
docker run -p 8000:8000 --env-file ../.env tcg-agent

# Note: This script assumes that a .env file exists in the root directory
# If the .env file is in a different location, update the --env-file parameter
